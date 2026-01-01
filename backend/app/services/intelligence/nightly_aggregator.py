"""
Tier 4 Nightly Aggregator

Orchestrates nightly computation of all Tier-4 intelligence signals.

Runs:
1. LedgerSignalAggregator (existing B7 job)
2. FurnisherBehaviorProfileService.compute_all_profiles()
3. ResponseQualityScorer.score_all_unscored()

All outputs persisted to CopilotSignalCacheDB.
Read-only intelligence — no enforcement changes.
"""

from datetime import datetime, timezone
from typing import Dict, Any
import logging

from sqlalchemy.orm import Session

from ..enforcement.ledger_signal_aggregator import LedgerSignalAggregator
from .furnisher_behavior_profile import FurnisherBehaviorProfileService
from .response_quality_scorer import ResponseQualityScorer


logger = logging.getLogger(__name__)


class Tier4NightlyAggregator:
    """
    Orchestrates all Tier-4 nightly jobs.

    Usage:
        aggregator = Tier4NightlyAggregator(db)
        result = aggregator.run()
    """

    def __init__(self, db: Session):
        self.db = db

    def run(
        self,
        window_days: int = 90,
    ) -> Dict[str, Any]:
        """
        Run all Tier-4 nightly aggregation jobs.

        Args:
            window_days: Lookback window for aggregation

        Returns:
            Summary of all jobs run
        """
        started_at = datetime.now(timezone.utc)
        results = {
            "started_at": started_at.isoformat(),
            "window_days": window_days,
            "jobs": {},
        }

        # 1. Run existing ledger signal aggregation (B7)
        try:
            ledger_agg = LedgerSignalAggregator(self.db)
            ledger_result = ledger_agg.run_aggregation(window_days=window_days)
            results["jobs"]["ledger_signals"] = {
                "status": "success",
                "signals_computed": ledger_result,
            }
            logger.info(f"Ledger signal aggregation complete: {ledger_result}")
        except Exception as e:
            results["jobs"]["ledger_signals"] = {
                "status": "error",
                "error": str(e),
            }
            logger.error(f"Ledger signal aggregation failed: {e}")

        # 2. Compute furnisher behavior profiles
        try:
            profile_service = FurnisherBehaviorProfileService(self.db)
            profiles = profile_service.compute_all_profiles(window_days=window_days)
            persisted = profile_service.persist_profiles(profiles)
            results["jobs"]["behavior_profiles"] = {
                "status": "success",
                "profiles_computed": len(profiles),
                "signals_persisted": persisted,
            }
            logger.info(f"Behavior profiles computed: {len(profiles)}, persisted: {persisted}")
        except Exception as e:
            results["jobs"]["behavior_profiles"] = {
                "status": "error",
                "error": str(e),
            }
            logger.error(f"Behavior profile computation failed: {e}")

        # 3. Score unscored responses
        try:
            scorer = ResponseQualityScorer(self.db)
            scores = scorer.score_all_unscored(limit=500)
            results["jobs"]["response_quality"] = {
                "status": "success",
                "responses_scored": len(scores),
            }
            logger.info(f"Response quality scores computed: {len(scores)}")
        except Exception as e:
            results["jobs"]["response_quality"] = {
                "status": "error",
                "error": str(e),
            }
            logger.error(f"Response quality scoring failed: {e}")

        # 4. Cleanup expired signals
        try:
            ledger_agg = LedgerSignalAggregator(self.db)
            expired = ledger_agg.cleanup_expired_signals()
            results["jobs"]["cleanup"] = {
                "status": "success",
                "expired_removed": expired,
            }
            logger.info(f"Expired signals cleaned up: {expired}")
        except Exception as e:
            results["jobs"]["cleanup"] = {
                "status": "error",
                "error": str(e),
            }
            logger.error(f"Signal cleanup failed: {e}")

        # Final summary
        completed_at = datetime.now(timezone.utc)
        results["completed_at"] = completed_at.isoformat()
        results["duration_seconds"] = (completed_at - started_at).total_seconds()

        return results


def run_tier4_nightly(db: Session, window_days: int = 90) -> Dict[str, Any]:
    """
    Convenience function to run Tier-4 nightly aggregation.

    Args:
        db: Database session
        window_days: Lookback window

    Returns:
        Aggregation results
    """
    aggregator = Tier4NightlyAggregator(db)
    return aggregator.run(window_days=window_days)
