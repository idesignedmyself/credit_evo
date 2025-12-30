"""
Credit Engine 2.0 - Copilot Batch Engine

Organizes enforcement actions into dispute batches (waves) per bureau.
Takes CopilotRecommendation and groups actions into strategic waves.

CORE INVARIANT: One batch = one letter = one furnisher.

Batching Rules:
- Group by: bureau → furnisher → enforcement theory (in that order!)
- Max 4 violations per batch (hard limit, optimal for bureau processing)
- Min 1 violation allowed (single-item batches valid for escalations)
- Lock subsequent waves until previous wave responds (per-bureau scoped)

A valid batch satisfies ALL:
1. One bureau
2. One furnisher
3. One enforcement theory (action type)
4. 1-4 violations

This is read-only with respect to disputes - it queries for lock detection
but never modifies dispute state.
"""

from datetime import datetime, timezone
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

    CRITICAL GROUPING ORDER: bureau → furnisher → enforcement theory
    This order ensures one furnisher per letter. Never group by
    enforcement theory before furnisher.

    Batching strategy:
    1. Group actions by target bureau
    2. Within bureau, group by furnisher (creditor_name)
    3. Within furnisher, group by action_type (enforcement theory)
    4. Create waves of max 4 violations each
    5. Lock subsequent waves until previous wave completes (per-bureau)

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
        "DELETE_DEMAND": "Deletion",
        "CORRECT_DEMAND": "Correction",
        "MOV_DEMAND": "Verification",
        "OWNERSHIP_CHAIN_DEMAND": "Ownership",
        "DOFD_DEMAND": "DOFD",
        "PROCEDURAL_DEMAND": "Procedural",
        "DEFER": "Defer",
    }

    def create_batched_recommendation(
        self,
        recommendation: CopilotRecommendation,
        existing_pending_disputes: Optional[List[dict]] = None,
    ) -> BatchedRecommendation:
        """
        Convert a CopilotRecommendation into batches organized by bureau.

        Grouping order: bureau → furnisher → enforcement theory
        Each leaf in this hierarchy produces separate batches (letters).

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

        # Group actions by bureau → furnisher
        actions_by_bureau_furnisher = self._group_actions_by_bureau_and_furnisher(
            recommendation.actions
        )

        # Create batches for each bureau
        for bureau, furnisher_groups in actions_by_bureau_furnisher.items():
            bureau_batches = []
            wave_number = 1

            # Process each furnisher separately (CRITICAL: one furnisher per letter)
            for furnisher, actions in furnisher_groups.items():
                furnisher_batches = self._create_furnisher_batches(
                    bureau=bureau,
                    furnisher=furnisher,
                    actions=actions,
                    goal=recommendation.goal,
                    existing_disputes=existing_pending_disputes,
                    start_wave_number=wave_number,
                    previous_bureau_batches=bureau_batches,
                )
                bureau_batches.extend(furnisher_batches)
                # Wave numbers continue sequentially across furnishers
                if furnisher_batches:
                    wave_number = furnisher_batches[-1].batch_number + 1

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

    def _get_furnisher_key(self, action: EnforcementAction) -> str:
        """
        Normalize furnisher name for grouping.

        Uses creditor_name from the action, defaulting to "Unknown" if not set.
        Normalizes to uppercase for consistent grouping.
        """
        furnisher = getattr(action, "creditor_name", None) or "Unknown"
        return furnisher.strip().upper() if furnisher else "Unknown"

    def _group_actions_by_bureau_and_furnisher(
        self,
        actions: List[EnforcementAction],
    ) -> Dict[str, Dict[str, List[EnforcementAction]]]:
        """
        Group actions by bureau, then by furnisher within each bureau.

        CRITICAL: This establishes the grouping hierarchy that ensures
        one furnisher per letter. Never flatten this structure.

        CROSS-BUREAU HANDLING:
        For cross-bureau discrepancies (actions with `bureaus` list populated),
        "explode" the action to ALL reporting bureaus. This ensures:
        - Each bureau gets a letter citing the cross-bureau inconsistency
        - Leverage from cross-bureau data is maximized
        - No discrepancy falls into an "Unknown" bucket

        Returns:
            {
                "Equifax": {
                    "JPMCB CARD": [action1, action2],
                    "NAVY FCU": [action3]
                },
                "TransUnion": { ... }
            }
        """
        by_bureau_furnisher: Dict[str, Dict[str, List[EnforcementAction]]] = {}

        for action in actions:
            # Determine target bureaus for this action
            target_bureaus = []

            # Check for cross-bureau action (multiple bureaus)
            bureaus_list = getattr(action, "bureaus", None) or []
            if bureaus_list and len(bureaus_list) > 0:
                # CROSS-BUREAU: Explode to all reporting bureaus
                for bureau_raw in bureaus_list:
                    bureau = self._normalize_bureau(bureau_raw)
                    if bureau != "Unknown":
                        target_bureaus.append(bureau)
            else:
                # Single bureau action (or no bureaus list)
                bureau_raw = getattr(action, "bureau", None)
                if bureau_raw:
                    bureau = self._normalize_bureau(bureau_raw)
                    if bureau != "Unknown":
                        target_bureaus.append(bureau)

            # Skip if no valid bureaus found
            if not target_bureaus:
                continue

            # Level 2: Furnisher (same for all bureau copies)
            furnisher = self._get_furnisher_key(action)

            # Add action to each target bureau
            for bureau in target_bureaus:
                if bureau not in by_bureau_furnisher:
                    by_bureau_furnisher[bureau] = {}
                if furnisher not in by_bureau_furnisher[bureau]:
                    by_bureau_furnisher[bureau][furnisher] = []

                by_bureau_furnisher[bureau][furnisher].append(action)

        return by_bureau_furnisher

    def _normalize_bureau(self, bureau: str) -> str:
        """Normalize bureau name to standard format."""
        if not bureau:
            return "Unknown"
        key = bureau.lower().strip()
        return self.BUREAU_NAMES.get(key, bureau.title())

    def _create_furnisher_batches(
        self,
        bureau: str,
        furnisher: str,
        actions: List[EnforcementAction],
        goal,
        existing_disputes: Optional[List[dict]],
        start_wave_number: int,
        previous_bureau_batches: List[DisputeBatch],
    ) -> List[DisputeBatch]:
        """
        Create batches for a single furnisher's actions within a bureau.

        Groups by action_type (enforcement theory) to maintain strategy coherence.
        Each resulting batch = one letter = one furnisher.
        """
        batches = []

        # Sort actions by sequence_order (already set by copilot engine)
        sorted_actions = sorted(actions, key=lambda a: a.sequence_order)

        # Group into waves based on dependencies, action type, and batch size
        current_wave = start_wave_number
        current_batch_actions = []
        processed_action_ids = set()

        for action in sorted_actions:
            # Check if this action has unmet dependencies
            current_ids = {a.action_id for a in current_batch_actions}
            has_unmet_deps = any(
                dep not in processed_action_ids and dep not in current_ids
                for dep in (action.depends_on or [])
            )

            # Start new batch if:
            # 1. Current batch is full (hard max of 4)
            # 2. Action has unmet dependencies from earlier batches
            # 3. Different action type (enforcement theory coherence)
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
                    furnisher=furnisher,
                    batch_number=current_wave,
                    actions=current_batch_actions,
                    goal=goal,
                    existing_disputes=existing_disputes,
                    previous_batches=previous_bureau_batches + batches,
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
                furnisher=furnisher,
                batch_number=current_wave,
                actions=current_batch_actions,
                goal=goal,
                existing_disputes=existing_disputes,
                previous_batches=previous_bureau_batches + batches,
            )
            batches.append(batch)

        return batches

    def _create_batch(
        self,
        bureau: str,
        furnisher: str,
        batch_number: int,
        actions: List[EnforcementAction],
        goal,
        existing_disputes: Optional[List[dict]],
        previous_batches: List[DisputeBatch],
    ) -> DisputeBatch:
        """
        Create a single batch from a list of actions.

        INVARIANT: All actions must be for the same furnisher.
        This is enforced by assertion to prevent silent regressions.
        """
        # SAFETY ASSERTION: Enforce one furnisher per batch
        furnisher_names = {
            (getattr(a, "creditor_name", None) or "Unknown").strip().upper()
            for a in actions
        }
        assert len(furnisher_names) == 1, (
            f"Batch contains multiple furnishers: {furnisher_names}. "
            "This violates the one-furnisher-per-letter invariant."
        )

        # Determine primary strategy from actions
        action_types = [a.action_type.value for a in actions]
        primary_strategy = max(set(action_types), key=action_types.count)
        strategy_label = self.STRATEGY_LABELS.get(primary_strategy, primary_strategy)

        # Calculate risk level from average risk score
        avg_risk = sum(a.risk_score for a in actions) / len(actions) if actions else 0
        risk_level = "LOW" if avg_risk < 2 else "MEDIUM" if avg_risk < 4 else "HIGH"

        # Build goal summary with furnisher name
        goal_name = goal.value.replace("_", " ").title() if hasattr(goal, "value") else str(goal)
        # Format furnisher for display (title case)
        display_furnisher = furnisher.title() if furnisher != "Unknown" else "Unknown Furnisher"
        goal_summary = f"Wave {batch_number}: {display_furnisher} — {strategy_label} for {goal_name}"

        # Determine recommended window
        recommended_window = f"{self.DEFAULT_WINDOW_DAYS}-{self.EXTENDED_WINDOW_DAYS} days"

        # Check for existing pending disputes (for locking)
        is_locked = False
        lock_reason = None
        unlock_conditions = []

        # Get UNIQUE violation IDs for this batch (only actual violations, not contradictions)
        violation_ids = list(set(
            a.blocker_source_id for a in actions
            if a.source_type == "VIOLATION"
        ))

        # Get UNIQUE contradiction IDs (cross-bureau discrepancies)
        contradiction_ids = list(set(
            a.blocker_source_id for a in actions
            if a.source_type == "CONTRADICTION"
        ))

        if existing_disputes:
            # Check if any violation in this batch has pending dispute
            pending_for_batch = [
                d for d in existing_disputes
                if d.get("violation_id") in violation_ids
                and d.get("status") in ("OPEN",)  # Only OPEN is pending
            ]
            if pending_for_batch:
                is_locked = True
                lock_reason = "pending_response"
                unlock_conditions = [
                    "Bureau response logged",
                    f"{self.EXTENDED_WINDOW_DAYS}-day response window expires",
                    "User override",
                ]

        # Lock subsequent batches until previous wave completes (per-bureau)
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
            furnisher_name=furnisher,  # Track furnisher explicitly
            batch_number=batch_number,
            goal_summary=goal_summary,
            strategy=primary_strategy,
            risk_level=risk_level,
            recommended_window=recommended_window,
            estimated_duration_days=self.DEFAULT_WINDOW_DAYS,
            violation_ids=violation_ids,
            contradiction_ids=contradiction_ids,
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
            batch.response_received_at = datetime.now(timezone.utc)

        return batch
