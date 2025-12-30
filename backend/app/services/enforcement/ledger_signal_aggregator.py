"""
Ledger Signal Aggregator (B7)

Nightly job that computes aggregated signals from the execution ledger
and stores them in CopilotSignalCacheDB.

Signals computed:
- reinsertion_rate: % of deletions that saw reinsertion
- dofd_change_rate: % of responses where DOFD changed
- verification_spike_rate: % of VERIFIED (not DELETED) responses
- deletion_durability: Average durability score

Note: Suppression frequency is NOT exposed to Copilot (admin-only).
"""
from uuid import uuid4
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from sqlalchemy.orm import Session
from sqlalchemy import func, case, and_, or_

from ...models.db_models import (
    ExecutionEventDB,
    ExecutionResponseDB,
    ExecutionOutcomeDB,
    CopilotSignalCacheDB,
    FinalOutcome,
    ExecutionStatus,
)


@dataclass
class SignalResult:
    """Result of signal computation."""
    signal_type: str
    signal_value: float
    sample_count: int
    scope_type: str
    scope_value: Optional[str]


class LedgerSignalAggregator:
    """
    Computes aggregated signals from the execution ledger.

    Run nightly to update CopilotSignalCacheDB.
    Copilot reads only from this cache, never from raw ledger data.

    Signal Types:
    - reinsertion_rate: How often deletions get reinserted
    - dofd_change_rate: How often DOFD changes on response
    - verification_spike_rate: Rate of VERIFIED vs DELETED
    - deletion_durability: Average durability of deletions

    Scope Types:
    - GLOBAL: System-wide aggregates
    - BUREAU: Per-bureau (EXPERIAN, EQUIFAX, TRANSUNION)
    - FURNISHER_TYPE: By furnisher type (COLLECTION, DEBT_BUYER, etc.)
    - CREDITOR: By specific creditor name
    """

    # Default lookback window for aggregation
    DEFAULT_WINDOW_DAYS = 90

    # Minimum sample size for meaningful signals
    MIN_SAMPLE_SIZE = 5

    # Signal expiration (hours after computation)
    SIGNAL_TTL_HOURS = 25  # Slightly more than 24h to avoid gaps

    def __init__(self, db: Session):
        self.db = db

    def run_aggregation(
        self,
        window_days: int = DEFAULT_WINDOW_DAYS,
    ) -> Dict[str, int]:
        """
        Run full aggregation job.

        Computes all signals at all scope levels and updates the cache.

        Args:
            window_days: Days to look back for aggregation

        Returns:
            Summary of signals computed by scope type
        """
        window_start = datetime.now(timezone.utc) - timedelta(days=window_days)
        window_end = datetime.now(timezone.utc)

        summary = {
            "GLOBAL": 0,
            "BUREAU": 0,
            "FURNISHER_TYPE": 0,
            "CREDITOR": 0,
        }

        # Compute GLOBAL signals
        global_signals = self._compute_all_signals(
            scope_type="GLOBAL",
            scope_value=None,
            window_start=window_start,
            window_end=window_end,
        )
        self._save_signals(global_signals, window_start, window_end)
        summary["GLOBAL"] = len(global_signals)

        # Compute per-BUREAU signals
        bureaus = self._get_distinct_bureaus()
        for bureau in bureaus:
            bureau_signals = self._compute_all_signals(
                scope_type="BUREAU",
                scope_value=bureau,
                window_start=window_start,
                window_end=window_end,
            )
            self._save_signals(bureau_signals, window_start, window_end)
            summary["BUREAU"] += len(bureau_signals)

        # Compute per-FURNISHER_TYPE signals
        furnisher_types = self._get_distinct_furnisher_types()
        for ftype in furnisher_types:
            ftype_signals = self._compute_all_signals(
                scope_type="FURNISHER_TYPE",
                scope_value=ftype,
                window_start=window_start,
                window_end=window_end,
            )
            self._save_signals(ftype_signals, window_start, window_end)
            summary["FURNISHER_TYPE"] += len(ftype_signals)

        # Compute per-CREDITOR signals (top creditors by volume)
        top_creditors = self._get_top_creditors(limit=50)
        for creditor in top_creditors:
            creditor_signals = self._compute_all_signals(
                scope_type="CREDITOR",
                scope_value=creditor,
                window_start=window_start,
                window_end=window_end,
            )
            self._save_signals(creditor_signals, window_start, window_end)
            summary["CREDITOR"] += len(creditor_signals)

        self.db.commit()
        return summary

    def _compute_all_signals(
        self,
        scope_type: str,
        scope_value: Optional[str],
        window_start: datetime,
        window_end: datetime,
    ) -> List[SignalResult]:
        """
        Compute all signal types for a given scope.

        Args:
            scope_type: GLOBAL, BUREAU, FURNISHER_TYPE, CREDITOR
            scope_value: Value for the scope
            window_start: Start of aggregation window
            window_end: End of aggregation window

        Returns:
            List of computed signals
        """
        signals = []

        # Reinsertion rate
        reinsertion = self._compute_reinsertion_rate(
            scope_type, scope_value, window_start, window_end
        )
        if reinsertion:
            signals.append(reinsertion)

        # DOFD change rate
        dofd = self._compute_dofd_change_rate(
            scope_type, scope_value, window_start, window_end
        )
        if dofd:
            signals.append(dofd)

        # Verification spike rate
        verification = self._compute_verification_spike_rate(
            scope_type, scope_value, window_start, window_end
        )
        if verification:
            signals.append(verification)

        # Deletion durability
        durability = self._compute_deletion_durability(
            scope_type, scope_value, window_start, window_end
        )
        if durability:
            signals.append(durability)

        return signals

    def _compute_reinsertion_rate(
        self,
        scope_type: str,
        scope_value: Optional[str],
        window_start: datetime,
        window_end: datetime,
    ) -> Optional[SignalResult]:
        """
        Compute reinsertion rate: % of deletions that saw reinsertion.

        Formula: reinserted_count / deleted_count
        """
        query = self._build_outcome_query(scope_type, scope_value, window_start, window_end)

        # Count total deletions
        deleted_count = query.filter(
            ExecutionOutcomeDB.final_outcome == FinalOutcome.DELETED
        ).count()

        if deleted_count < self.MIN_SAMPLE_SIZE:
            return None

        # Count reinsertions
        reinserted_count = query.filter(
            ExecutionOutcomeDB.final_outcome == FinalOutcome.REINSERTED
        ).count()

        rate = reinserted_count / deleted_count if deleted_count > 0 else 0.0

        return SignalResult(
            signal_type="reinsertion_rate",
            signal_value=rate,
            sample_count=deleted_count,
            scope_type=scope_type,
            scope_value=scope_value,
        )

    def _compute_dofd_change_rate(
        self,
        scope_type: str,
        scope_value: Optional[str],
        window_start: datetime,
        window_end: datetime,
    ) -> Optional[SignalResult]:
        """
        Compute DOFD change rate: % of responses where DOFD changed.

        Formula: dofd_changed_count / total_responses
        """
        query = self._build_response_query(scope_type, scope_value, window_start, window_end)

        total_count = query.count()

        if total_count < self.MIN_SAMPLE_SIZE:
            return None

        dofd_changed_count = query.filter(
            ExecutionResponseDB.dofd_changed == True
        ).count()

        rate = dofd_changed_count / total_count if total_count > 0 else 0.0

        return SignalResult(
            signal_type="dofd_change_rate",
            signal_value=rate,
            sample_count=total_count,
            scope_type=scope_type,
            scope_value=scope_value,
        )

    def _compute_verification_spike_rate(
        self,
        scope_type: str,
        scope_value: Optional[str],
        window_start: datetime,
        window_end: datetime,
    ) -> Optional[SignalResult]:
        """
        Compute verification spike rate: % of VERIFIED vs DELETED outcomes.

        Formula: verified_count / (verified_count + deleted_count)
        """
        query = self._build_outcome_query(scope_type, scope_value, window_start, window_end)

        # Count verified and deleted
        verified_count = query.filter(
            ExecutionOutcomeDB.final_outcome == FinalOutcome.VERIFIED
        ).count()

        deleted_count = query.filter(
            ExecutionOutcomeDB.final_outcome == FinalOutcome.DELETED
        ).count()

        total = verified_count + deleted_count

        if total < self.MIN_SAMPLE_SIZE:
            return None

        rate = verified_count / total if total > 0 else 0.0

        return SignalResult(
            signal_type="verification_spike_rate",
            signal_value=rate,
            sample_count=total,
            scope_type=scope_type,
            scope_value=scope_value,
        )

    def _compute_deletion_durability(
        self,
        scope_type: str,
        scope_value: Optional[str],
        window_start: datetime,
        window_end: datetime,
    ) -> Optional[SignalResult]:
        """
        Compute deletion durability: average durability score of deletions.

        Only considers DELETED outcomes with durability scores.
        """
        query = self._build_outcome_query(scope_type, scope_value, window_start, window_end)

        result = query.filter(
            ExecutionOutcomeDB.final_outcome == FinalOutcome.DELETED,
            ExecutionOutcomeDB.durability_score.isnot(None),
        ).with_entities(
            func.avg(ExecutionOutcomeDB.durability_score),
            func.count(ExecutionOutcomeDB.id),
        ).first()

        avg_durability, count = result

        if not count or count < self.MIN_SAMPLE_SIZE:
            return None

        return SignalResult(
            signal_type="deletion_durability",
            signal_value=float(avg_durability) if avg_durability else 0.0,
            sample_count=count,
            scope_type=scope_type,
            scope_value=scope_value,
        )

    def _build_outcome_query(
        self,
        scope_type: str,
        scope_value: Optional[str],
        window_start: datetime,
        window_end: datetime,
    ):
        """Build base query for outcome aggregation with scope filters."""
        query = (
            self.db.query(ExecutionOutcomeDB)
            .join(ExecutionEventDB)
            .filter(
                ExecutionOutcomeDB.resolved_at >= window_start,
                ExecutionOutcomeDB.resolved_at <= window_end,
            )
        )

        if scope_type == "BUREAU" and scope_value:
            query = query.filter(ExecutionEventDB.bureau == scope_value)
        elif scope_type == "FURNISHER_TYPE" and scope_value:
            query = query.filter(ExecutionEventDB.furnisher_type == scope_value)
        elif scope_type == "CREDITOR" and scope_value:
            query = query.filter(ExecutionEventDB.creditor_name == scope_value)

        return query

    def _build_response_query(
        self,
        scope_type: str,
        scope_value: Optional[str],
        window_start: datetime,
        window_end: datetime,
    ):
        """Build base query for response aggregation with scope filters."""
        query = (
            self.db.query(ExecutionResponseDB)
            .join(ExecutionEventDB)
            .filter(
                ExecutionResponseDB.response_received_at >= window_start,
                ExecutionResponseDB.response_received_at <= window_end,
            )
        )

        if scope_type == "BUREAU" and scope_value:
            query = query.filter(
                or_(
                    ExecutionEventDB.bureau == scope_value,
                    ExecutionResponseDB.bureau == scope_value,
                )
            )
        elif scope_type == "FURNISHER_TYPE" and scope_value:
            query = query.filter(ExecutionEventDB.furnisher_type == scope_value)
        elif scope_type == "CREDITOR" and scope_value:
            query = query.filter(ExecutionEventDB.creditor_name == scope_value)

        return query

    def _get_distinct_bureaus(self) -> List[str]:
        """Get list of distinct bureaus with executions."""
        results = (
            self.db.query(ExecutionEventDB.bureau)
            .filter(ExecutionEventDB.bureau.isnot(None))
            .distinct()
            .all()
        )
        return [r[0] for r in results if r[0]]

    def _get_distinct_furnisher_types(self) -> List[str]:
        """Get list of distinct furnisher types with executions."""
        results = (
            self.db.query(ExecutionEventDB.furnisher_type)
            .filter(ExecutionEventDB.furnisher_type.isnot(None))
            .distinct()
            .all()
        )
        return [r[0] for r in results if r[0]]

    def _get_top_creditors(self, limit: int = 50) -> List[str]:
        """Get top creditors by execution volume."""
        results = (
            self.db.query(
                ExecutionEventDB.creditor_name,
                func.count(ExecutionEventDB.id).label('count'),
            )
            .filter(ExecutionEventDB.creditor_name.isnot(None))
            .group_by(ExecutionEventDB.creditor_name)
            .order_by(func.count(ExecutionEventDB.id).desc())
            .limit(limit)
            .all()
        )
        return [r[0] for r in results if r[0]]

    def _save_signals(
        self,
        signals: List[SignalResult],
        window_start: datetime,
        window_end: datetime,
    ) -> None:
        """
        Save computed signals to the cache.

        Deletes existing signals for the same scope before inserting.
        """
        expires_at = datetime.now(timezone.utc) + timedelta(hours=self.SIGNAL_TTL_HOURS)

        for signal in signals:
            # Delete existing signal for this scope/type
            self.db.query(CopilotSignalCacheDB).filter(
                CopilotSignalCacheDB.scope_type == signal.scope_type,
                CopilotSignalCacheDB.scope_value == signal.scope_value,
                CopilotSignalCacheDB.signal_type == signal.signal_type,
            ).delete()

            # Insert new signal
            cache_entry = CopilotSignalCacheDB(
                id=str(uuid4()),
                scope_type=signal.scope_type,
                scope_value=signal.scope_value,
                signal_type=signal.signal_type,
                signal_value=signal.signal_value,
                sample_count=signal.sample_count,
                window_start=window_start,
                window_end=window_end,
                expires_at=expires_at,
            )
            self.db.add(cache_entry)

    def cleanup_expired_signals(self) -> int:
        """
        Remove expired signals from the cache.

        Returns:
            Number of signals deleted
        """
        result = self.db.query(CopilotSignalCacheDB).filter(
            CopilotSignalCacheDB.expires_at < datetime.now(timezone.utc)
        ).delete()
        self.db.commit()
        return result
