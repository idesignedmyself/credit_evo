"""
Credit Engine 2.0 - Copilot Batch Engine

Organizes enforcement actions into dispute batches (waves) per bureau.
Takes CopilotRecommendation and groups actions into strategic waves.

Batching Rules:
- Max 4 violations per batch (hard limit, optimal for bureau processing)
- Min 1 violation allowed (single-item batches are valid for escalations,
  MOV follow-ups, procedural challenges, litigation-ready demands, etc.)
- Preference: 2-4 violations per batch (heuristic, not enforced)
- Group by bureau first, then by action_type for strategy coherence
- Respect depends_on chains from Copilot engine
- Lock subsequent waves until previous wave responds (per-bureau scoped)

This is read-only with respect to disputes - it queries for lock detection
but never modifies dispute state.
"""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import uuid4

from app.models.copilot_models import (
    CopilotRecommendation,
    EnforcementAction,
    DisputeBatch,
    BatchedRecommendation,
)


class BatchEngine:
    """
    Groups enforcement actions into dispute batches.

    Batching strategy:
    1. Group actions by target bureau
    2. Within bureau, sort by sequence_order (from Copilot engine)
    3. Create waves of max 4 violations each (single-item batches allowed)
    4. Lock subsequent waves until previous wave completes (per-bureau)

    Single-item batches are valid for:
    - MOV follow-ups
    - Procedural verification challenges
    - Re-aging clarification demands
    - Furnisher-only escalations
    - CFPB/AG-prep waves
    - Litigation-ready demand isolation
    """

    MAX_VIOLATIONS_PER_BATCH = 4  # Hard limit
    PREFERRED_MIN_PER_BATCH = 2   # Soft preference (not enforced)
    DEFAULT_WINDOW_DAYS = 30
    EXTENDED_WINDOW_DAYS = 45

    BUREAU_NAMES = {
        "transunion": "TransUnion",
        "experian": "Experian",
        "equifax": "Equifax",
        "tu": "TransUnion",
        "exp": "Experian",
        "eq": "Equifax",
        "trans union": "TransUnion",
    }

    STRATEGY_LABELS = {
        "DELETE_DEMAND": "Deletion Request",
        "CORRECT_DEMAND": "Correction Request",
        "MOV_DEMAND": "Method of Verification",
        "OWNERSHIP_CHAIN_DEMAND": "Ownership Challenge",
        "DOFD_DEMAND": "DOFD Resolution",
        "PROCEDURAL_DEMAND": "Procedural Compliance",
        "DEFER": "Defer Action",
    }

    def create_batched_recommendation(
        self,
        recommendation: CopilotRecommendation,
        existing_pending_disputes: Optional[List[dict]] = None,
    ) -> BatchedRecommendation:
        """
        Convert a CopilotRecommendation into batches organized by bureau.

        Args:
            recommendation: The base copilot recommendation with prioritized actions
            existing_pending_disputes: Optional list of pending disputes for lock detection
                Each dict should have: violation_id, status, dispute_date

        Returns:
            BatchedRecommendation with actions grouped into waves per bureau
        """
        # Initialize result
        batched = BatchedRecommendation(
            base_recommendation=recommendation,
            skipped_violation_ids=[s.source_id for s in recommendation.skips],
        )

        # Group actions by bureau
        actions_by_bureau = self._group_actions_by_bureau(recommendation.actions)

        # Create batches for each bureau
        for bureau, actions in actions_by_bureau.items():
            bureau_batches = self._create_bureau_batches(
                bureau=bureau,
                actions=actions,
                goal=recommendation.goal,
                existing_disputes=existing_pending_disputes,
            )
            batched.batches_by_bureau[bureau] = bureau_batches
            batched.total_batches += len(bureau_batches)
            batched.total_violations_in_batches += sum(
                len(b.violation_ids) for b in bureau_batches
            )

        # Calculate lock summary
        for batches in batched.batches_by_bureau.values():
            for batch in batches:
                if batch.is_locked:
                    batched.locked_batches += 1
                else:
                    batched.active_batches += 1

        return batched

    def _group_actions_by_bureau(
        self,
        actions: List[EnforcementAction],
    ) -> Dict[str, List[EnforcementAction]]:
        """Group actions by their target bureau."""
        by_bureau: Dict[str, List[EnforcementAction]] = {}

        for action in actions:
            # Get bureau from action (may be on the action or need to be extracted)
            bureau_raw = getattr(action, "bureau", None) or "Unknown"
            bureau = self._normalize_bureau(bureau_raw)

            if bureau not in by_bureau:
                by_bureau[bureau] = []
            by_bureau[bureau].append(action)

        return by_bureau

    def _normalize_bureau(self, bureau: str) -> str:
        """Normalize bureau name to standard format."""
        if not bureau:
            return "Unknown"
        key = bureau.lower().strip()
        return self.BUREAU_NAMES.get(key, bureau.title())

    def _create_bureau_batches(
        self,
        bureau: str,
        actions: List[EnforcementAction],
        goal,
        existing_disputes: Optional[List[dict]],
    ) -> List[DisputeBatch]:
        """Create batches for a single bureau's actions."""
        batches = []

        # Sort actions by sequence_order (already set by copilot engine)
        sorted_actions = sorted(actions, key=lambda a: a.sequence_order)

        # Group into waves based on dependencies and batch size
        current_wave = 1
        current_batch_actions = []
        processed_action_ids = set()

        for action in sorted_actions:
            # Check if this action has unmet dependencies in the current batch
            current_ids = {a.action_id for a in current_batch_actions}
            has_unmet_deps = any(
                dep not in processed_action_ids and dep not in current_ids
                for dep in (action.depends_on or [])
            )

            # Start new batch if:
            # 1. Current batch is full (hard max of 4)
            # 2. Action has unmet dependencies from earlier batches
            # 3. Different action type for strategy coherence (no min check - single-item batches allowed)
            should_start_new = (
                len(current_batch_actions) >= self.MAX_VIOLATIONS_PER_BATCH
                or has_unmet_deps
                or (
                    current_batch_actions
                    and current_batch_actions[-1].action_type != action.action_type
                )
            )

            if should_start_new and current_batch_actions:
                # Finalize current batch
                batch = self._create_batch(
                    bureau=bureau,
                    batch_number=current_wave,
                    actions=current_batch_actions,
                    goal=goal,
                    existing_disputes=existing_disputes,
                    previous_batches=batches,
                )
                batches.append(batch)
                processed_action_ids.update(a.action_id for a in current_batch_actions)
                current_wave += 1
                current_batch_actions = []

            current_batch_actions.append(action)

        # Don't forget the last batch
        if current_batch_actions:
            batch = self._create_batch(
                bureau=bureau,
                batch_number=current_wave,
                actions=current_batch_actions,
                goal=goal,
                existing_disputes=existing_disputes,
                previous_batches=batches,
            )
            batches.append(batch)

        return batches

    def _create_batch(
        self,
        bureau: str,
        batch_number: int,
        actions: List[EnforcementAction],
        goal,
        existing_disputes: Optional[List[dict]],
        previous_batches: List[DisputeBatch],
    ) -> DisputeBatch:
        """Create a single batch from a list of actions."""
        # Determine primary strategy from actions
        action_types = [a.action_type.value for a in actions]
        primary_strategy = max(set(action_types), key=action_types.count)
        strategy_label = self.STRATEGY_LABELS.get(primary_strategy, primary_strategy)

        # Calculate risk level from average risk score
        avg_risk = sum(a.risk_score for a in actions) / len(actions) if actions else 0
        risk_level = "LOW" if avg_risk < 2 else "MEDIUM" if avg_risk < 4 else "HIGH"

        # Build goal summary
        goal_name = goal.value.replace("_", " ").title() if hasattr(goal, "value") else str(goal)
        goal_summary = f"Wave {batch_number}: {strategy_label} for {goal_name}"

        # Determine recommended window
        recommended_window = f"{self.DEFAULT_WINDOW_DAYS}-{self.EXTENDED_WINDOW_DAYS} days"

        # Check for existing pending disputes (for locking)
        is_locked = False
        lock_reason = None
        unlock_conditions = []

        # Get violation IDs for this batch
        violation_ids = [a.blocker_source_id for a in actions]

        if existing_disputes:
            # Check if any violation in this batch has pending dispute
            pending_for_batch = [
                d for d in existing_disputes
                if d.get("violation_id") in violation_ids
                and d.get("status") in ("OPEN", "DISPUTED", "PENDING")
            ]
            if pending_for_batch:
                is_locked = True
                lock_reason = "pending_response"
                unlock_conditions = [
                    "Bureau response logged",
                    f"{self.EXTENDED_WINDOW_DAYS}-day response window expires",
                    "User override",
                ]

        # Lock subsequent batches until previous wave completes
        depends_on_batch_ids = []
        if previous_batches:
            previous_batch = previous_batches[-1]
            depends_on_batch_ids.append(previous_batch.batch_id)

            # If previous batch hasn't received response, lock this one
            if not previous_batch.response_received_at and not is_locked:
                is_locked = True
                lock_reason = "pending_previous_wave"
                unlock_conditions = [
                    f"Wave {batch_number - 1} response logged",
                    f"{self.EXTENDED_WINDOW_DAYS}-day window expires",
                    "User override",
                ]

        # Annotate single-item batches (isolated escalation steps)
        is_single_item = len(actions) == 1

        return DisputeBatch(
            batch_id=str(uuid4()),
            bureau=bureau,
            batch_number=batch_number,
            goal_summary=goal_summary,
            strategy=primary_strategy,
            risk_level=risk_level,
            recommended_window=recommended_window,
            estimated_duration_days=self.DEFAULT_WINDOW_DAYS,
            violation_ids=violation_ids,
            actions=actions,
            is_single_item=is_single_item,
            is_locked=is_locked,
            lock_reason=lock_reason,
            unlock_conditions=unlock_conditions,
            depends_on_batch_ids=depends_on_batch_ids,
        )

    def unlock_batch(self, batch: DisputeBatch, reason: str) -> DisputeBatch:
        """
        Unlock a batch (typically after response received or override).

        Args:
            batch: The batch to unlock
            reason: Why it's being unlocked (response_received, time_expired, user_override)

        Returns:
            Updated batch with lock cleared
        """
        batch.is_locked = False
        batch.lock_reason = None
        batch.unlock_conditions = []

        if reason == "response_received":
            batch.response_received_at = datetime.utcnow()

        return batch
