"""
Furnisher Behavior Profile (Tier 4)

Aggregates CRA/furnisher behavior patterns across all users.

Computes:
- avg_response_time: Average hours to respond
- first_round_outcome_rate: % deleted on first dispute
- second_round_flip_rate: % that flip from VERIFIED to DELETED on second round
- reinsertion_rate: % of deletions that get reinserted

Consumes: ExecutionLedger (SOURCE 1-3)
Outputs: FurnisherBehaviorProfile (read-only intelligence)

Persisted nightly. Read-only usage — no enforcement changes.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from uuid import uuid4

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, case

from ...models.db_models import (
    ExecutionEventDB,
    ExecutionResponseDB,
    ExecutionOutcomeDB,
    FinalOutcome,
    Base,
)


@dataclass
class FurnisherBehaviorProfile:
    """
    Behavioral profile for a CRA or furnisher.

    Computed from ledger data across all users.
    Read-only intelligence — not used for enforcement decisions.
    """
    # Identity
    entity_name: str
    entity_type: str  # CRA, FURNISHER, CREDITOR

    # Volume metrics
    total_executions: int = 0
    total_responses: int = 0
    total_outcomes: int = 0

    # Response time (hours)
    avg_response_time_hours: float = 0.0
    median_response_time_hours: float = 0.0
    min_response_time_hours: float = 0.0
    max_response_time_hours: float = 0.0

    # First-round outcomes
    first_round_deletion_rate: float = 0.0
    first_round_verification_rate: float = 0.0
    first_round_update_rate: float = 0.0
    first_round_no_response_rate: float = 0.0

    # Second-round behavior (flip rates)
    second_round_flip_rate: float = 0.0  # VERIFIED → DELETED
    second_round_hold_rate: float = 0.0  # VERIFIED → VERIFIED again

    # Reinsertion behavior
    reinsertion_rate: float = 0.0
    avg_days_to_reinsertion: float = 0.0

    # Quality signals (from ResponseQualityScorer)
    avg_boilerplate_score: float = 0.0
    evidence_ignored_rate: float = 0.0
    timing_anomaly_rate: float = 0.0

    # Metadata
    sample_window_start: Optional[datetime] = None
    sample_window_end: Optional[datetime] = None
    computed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage/serialization."""
        return {
            "entity_name": self.entity_name,
            "entity_type": self.entity_type,
            "total_executions": self.total_executions,
            "total_responses": self.total_responses,
            "total_outcomes": self.total_outcomes,
            "avg_response_time_hours": round(self.avg_response_time_hours, 1),
            "median_response_time_hours": round(self.median_response_time_hours, 1),
            "min_response_time_hours": round(self.min_response_time_hours, 1),
            "max_response_time_hours": round(self.max_response_time_hours, 1),
            "first_round_deletion_rate": round(self.first_round_deletion_rate, 3),
            "first_round_verification_rate": round(self.first_round_verification_rate, 3),
            "first_round_update_rate": round(self.first_round_update_rate, 3),
            "first_round_no_response_rate": round(self.first_round_no_response_rate, 3),
            "second_round_flip_rate": round(self.second_round_flip_rate, 3),
            "second_round_hold_rate": round(self.second_round_hold_rate, 3),
            "reinsertion_rate": round(self.reinsertion_rate, 3),
            "avg_days_to_reinsertion": round(self.avg_days_to_reinsertion, 1),
            "avg_boilerplate_score": round(self.avg_boilerplate_score, 3),
            "evidence_ignored_rate": round(self.evidence_ignored_rate, 3),
            "timing_anomaly_rate": round(self.timing_anomaly_rate, 3),
            "sample_window_start": self.sample_window_start.isoformat() if self.sample_window_start else None,
            "sample_window_end": self.sample_window_end.isoformat() if self.sample_window_end else None,
            "computed_at": self.computed_at.isoformat(),
        }


class FurnisherBehaviorProfileService:
    """
    Computes and persists furnisher behavior profiles.

    Tier-4 intelligence component.
    Runs nightly to aggregate behavioral signals from ledger.
    Read-only profiles — no enforcement decisions.

    Usage:
        service = FurnisherBehaviorProfileService(db)
        profiles = service.compute_all_profiles()
        service.persist_profiles(profiles)
    """

    # Default lookback window
    DEFAULT_WINDOW_DAYS = 90

    # Minimum sample size for meaningful profiles
    MIN_SAMPLE_SIZE = 5

    def __init__(self, db: Session):
        self.db = db

    def compute_profile(
        self,
        entity_name: str,
        entity_type: str = "CREDITOR",
        window_days: int = DEFAULT_WINDOW_DAYS,
    ) -> Optional[FurnisherBehaviorProfile]:
        """
        Compute behavioral profile for a single entity.

        Args:
            entity_name: CRA or furnisher name
            entity_type: CRA, FURNISHER, CREDITOR
            window_days: Lookback window

        Returns:
            FurnisherBehaviorProfile or None if insufficient data
        """
        window_start = datetime.now(timezone.utc) - timedelta(days=window_days)
        window_end = datetime.now(timezone.utc)

        profile = FurnisherBehaviorProfile(
            entity_name=entity_name,
            entity_type=entity_type,
            sample_window_start=window_start,
            sample_window_end=window_end,
        )

        # 1. Compute volume metrics
        self._compute_volume_metrics(profile, entity_name, window_start, window_end)

        if profile.total_executions < self.MIN_SAMPLE_SIZE:
            return None

        # 2. Compute response time metrics
        self._compute_response_time_metrics(profile, entity_name, window_start, window_end)

        # 3. Compute first-round outcome rates
        self._compute_first_round_rates(profile, entity_name, window_start, window_end)

        # 4. Compute second-round flip rates
        self._compute_second_round_rates(profile, entity_name, window_start, window_end)

        # 5. Compute reinsertion metrics
        self._compute_reinsertion_metrics(profile, entity_name, window_start, window_end)

        return profile

    def compute_all_profiles(
        self,
        window_days: int = DEFAULT_WINDOW_DAYS,
    ) -> List[FurnisherBehaviorProfile]:
        """
        Compute profiles for all entities with sufficient data.

        For nightly batch processing.

        Args:
            window_days: Lookback window

        Returns:
            List of computed profiles
        """
        profiles = []

        # Get all distinct entities
        entities = self._get_active_entities(window_days)

        for entity_name, entity_type in entities:
            profile = self.compute_profile(
                entity_name=entity_name,
                entity_type=entity_type,
                window_days=window_days,
            )
            if profile:
                profiles.append(profile)

        return profiles

    def _compute_volume_metrics(
        self,
        profile: FurnisherBehaviorProfile,
        entity_name: str,
        window_start: datetime,
        window_end: datetime,
    ) -> None:
        """Compute execution/response/outcome counts."""
        # Executions
        profile.total_executions = (
            self.db.query(ExecutionEventDB)
            .filter(
                ExecutionEventDB.creditor_name == entity_name,
                ExecutionEventDB.executed_at >= window_start,
                ExecutionEventDB.executed_at <= window_end,
            )
            .count()
        )

        # Responses
        profile.total_responses = (
            self.db.query(ExecutionResponseDB)
            .join(ExecutionEventDB)
            .filter(
                ExecutionEventDB.creditor_name == entity_name,
                ExecutionResponseDB.response_received_at >= window_start,
                ExecutionResponseDB.response_received_at <= window_end,
            )
            .count()
        )

        # Outcomes
        profile.total_outcomes = (
            self.db.query(ExecutionOutcomeDB)
            .join(ExecutionEventDB)
            .filter(
                ExecutionEventDB.creditor_name == entity_name,
                ExecutionOutcomeDB.resolved_at >= window_start,
                ExecutionOutcomeDB.resolved_at <= window_end,
            )
            .count()
        )

    def _compute_response_time_metrics(
        self,
        profile: FurnisherBehaviorProfile,
        entity_name: str,
        window_start: datetime,
        window_end: datetime,
    ) -> None:
        """Compute response time statistics."""
        # Get all response times
        results = (
            self.db.query(
                ExecutionEventDB.executed_at,
                ExecutionResponseDB.response_received_at,
            )
            .join(ExecutionResponseDB)
            .filter(
                ExecutionEventDB.creditor_name == entity_name,
                ExecutionEventDB.executed_at >= window_start,
                ExecutionResponseDB.response_received_at.isnot(None),
            )
            .all()
        )

        if not results:
            return

        # Calculate hours for each response
        hours_list = []
        for executed_at, response_at in results:
            if executed_at and response_at:
                delta = response_at - executed_at
                hours = delta.total_seconds() / 3600
                if hours >= 0:  # Sanity check
                    hours_list.append(hours)

        if not hours_list:
            return

        # Compute statistics
        hours_list.sort()
        profile.avg_response_time_hours = sum(hours_list) / len(hours_list)
        profile.min_response_time_hours = min(hours_list)
        profile.max_response_time_hours = max(hours_list)

        # Median
        mid = len(hours_list) // 2
        if len(hours_list) % 2 == 0:
            profile.median_response_time_hours = (hours_list[mid - 1] + hours_list[mid]) / 2
        else:
            profile.median_response_time_hours = hours_list[mid]

    def _compute_first_round_rates(
        self,
        profile: FurnisherBehaviorProfile,
        entity_name: str,
        window_start: datetime,
        window_end: datetime,
    ) -> None:
        """Compute first-round outcome rates."""
        # Get first-round outcomes (dispute_round = 1 or NULL)
        outcomes = (
            self.db.query(ExecutionOutcomeDB.final_outcome)
            .join(ExecutionEventDB)
            .filter(
                ExecutionEventDB.creditor_name == entity_name,
                ExecutionOutcomeDB.resolved_at >= window_start,
                ExecutionOutcomeDB.resolved_at <= window_end,
                or_(
                    ExecutionEventDB.dispute_round == 1,
                    ExecutionEventDB.dispute_round.is_(None),
                ),
            )
            .all()
        )

        if not outcomes:
            return

        total = len(outcomes)
        deleted = sum(1 for o in outcomes if o[0] == FinalOutcome.DELETED)
        verified = sum(1 for o in outcomes if o[0] == FinalOutcome.VERIFIED)
        updated = sum(1 for o in outcomes if o[0] == FinalOutcome.UPDATED)

        profile.first_round_deletion_rate = deleted / total
        profile.first_round_verification_rate = verified / total
        profile.first_round_update_rate = updated / total
        profile.first_round_no_response_rate = (total - deleted - verified - updated) / total

    def _compute_second_round_rates(
        self,
        profile: FurnisherBehaviorProfile,
        entity_name: str,
        window_start: datetime,
        window_end: datetime,
    ) -> None:
        """
        Compute second-round flip rates.

        Flip rate = % of round 1 VERIFIED that became DELETED in round 2.
        """
        # Get second-round outcomes
        second_round_outcomes = (
            self.db.query(
                ExecutionEventDB.account_fingerprint,
                ExecutionOutcomeDB.final_outcome,
            )
            .join(ExecutionOutcomeDB)
            .filter(
                ExecutionEventDB.creditor_name == entity_name,
                ExecutionOutcomeDB.resolved_at >= window_start,
                ExecutionOutcomeDB.resolved_at <= window_end,
                ExecutionEventDB.dispute_round == 2,
            )
            .all()
        )

        if not second_round_outcomes:
            return

        total_second_round = len(second_round_outcomes)
        flipped = sum(1 for _, outcome in second_round_outcomes if outcome == FinalOutcome.DELETED)
        held = sum(1 for _, outcome in second_round_outcomes if outcome == FinalOutcome.VERIFIED)

        profile.second_round_flip_rate = flipped / total_second_round if total_second_round > 0 else 0.0
        profile.second_round_hold_rate = held / total_second_round if total_second_round > 0 else 0.0

    def _compute_reinsertion_metrics(
        self,
        profile: FurnisherBehaviorProfile,
        entity_name: str,
        window_start: datetime,
        window_end: datetime,
    ) -> None:
        """Compute reinsertion rate and average time to reinsertion."""
        # Count deletions
        deleted_count = (
            self.db.query(ExecutionOutcomeDB)
            .join(ExecutionEventDB)
            .filter(
                ExecutionEventDB.creditor_name == entity_name,
                ExecutionOutcomeDB.resolved_at >= window_start,
                ExecutionOutcomeDB.resolved_at <= window_end,
                ExecutionOutcomeDB.final_outcome == FinalOutcome.DELETED,
            )
            .count()
        )

        if deleted_count == 0:
            return

        # Count reinsertions
        reinserted = (
            self.db.query(ExecutionOutcomeDB)
            .join(ExecutionEventDB)
            .filter(
                ExecutionEventDB.creditor_name == entity_name,
                ExecutionOutcomeDB.resolved_at >= window_start,
                ExecutionOutcomeDB.resolved_at <= window_end,
                ExecutionOutcomeDB.final_outcome == FinalOutcome.REINSERTED,
            )
            .all()
        )

        profile.reinsertion_rate = len(reinserted) / deleted_count if deleted_count > 0 else 0.0

        # Average days to reinsertion
        if reinserted:
            days_list = [
                r.days_until_reinsertion
                for r in reinserted
                if r.days_until_reinsertion is not None
            ]
            if days_list:
                profile.avg_days_to_reinsertion = sum(days_list) / len(days_list)

    def _get_active_entities(
        self,
        window_days: int,
    ) -> List[tuple]:
        """
        Get all entities with activity in the window.

        Returns list of (entity_name, entity_type) tuples.
        """
        window_start = datetime.now(timezone.utc) - timedelta(days=window_days)

        # Get creditors
        creditors = (
            self.db.query(ExecutionEventDB.creditor_name)
            .filter(
                ExecutionEventDB.creditor_name.isnot(None),
                ExecutionEventDB.executed_at >= window_start,
            )
            .distinct()
            .all()
        )

        # Get bureaus
        bureaus = (
            self.db.query(ExecutionEventDB.bureau)
            .filter(
                ExecutionEventDB.bureau.isnot(None),
                ExecutionEventDB.executed_at >= window_start,
            )
            .distinct()
            .all()
        )

        entities = []
        entities.extend((c[0], "CREDITOR") for c in creditors if c[0])
        entities.extend((b[0], "CRA") for b in bureaus if b[0])

        return entities

    def persist_profiles(
        self,
        profiles: List[FurnisherBehaviorProfile],
    ) -> int:
        """
        Persist profiles to CopilotSignalCacheDB as behavior_profile signals.

        Args:
            profiles: List of computed profiles

        Returns:
            Number of profiles persisted
        """
        from ...models.db_models import CopilotSignalCacheDB

        persisted = 0
        expires_at = datetime.now(timezone.utc) + timedelta(hours=25)

        for profile in profiles:
            # Delete existing profile signals for this entity
            self.db.query(CopilotSignalCacheDB).filter(
                CopilotSignalCacheDB.scope_type == "ENTITY_PROFILE",
                CopilotSignalCacheDB.scope_value == profile.entity_name,
            ).delete()

            # Persist key metrics as individual signals
            metrics = [
                ("first_round_deletion_rate", profile.first_round_deletion_rate),
                ("first_round_verification_rate", profile.first_round_verification_rate),
                ("second_round_flip_rate", profile.second_round_flip_rate),
                ("reinsertion_rate", profile.reinsertion_rate),
                ("avg_response_time_hours", profile.avg_response_time_hours),
            ]

            for signal_type, signal_value in metrics:
                cache_entry = CopilotSignalCacheDB(
                    id=str(uuid4()),
                    scope_type="ENTITY_PROFILE",
                    scope_value=profile.entity_name,
                    signal_type=signal_type,
                    signal_value=signal_value,
                    sample_count=profile.total_executions,
                    window_start=profile.sample_window_start,
                    window_end=profile.sample_window_end,
                    expires_at=expires_at,
                )
                self.db.add(cache_entry)
                persisted += 1

        self.db.commit()
        return persisted

    def get_profile(self, entity_name: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached profile for an entity.

        Args:
            entity_name: CRA or furnisher name

        Returns:
            Profile dict or None if not cached
        """
        from ...models.db_models import CopilotSignalCacheDB

        signals = (
            self.db.query(CopilotSignalCacheDB)
            .filter(
                CopilotSignalCacheDB.scope_type == "ENTITY_PROFILE",
                CopilotSignalCacheDB.scope_value == entity_name,
                CopilotSignalCacheDB.expires_at > datetime.now(timezone.utc),
            )
            .all()
        )

        if not signals:
            return None

        profile = {
            "entity_name": entity_name,
            "sample_count": signals[0].sample_count if signals else 0,
        }

        for signal in signals:
            profile[signal.signal_type] = signal.signal_value

        return profile
