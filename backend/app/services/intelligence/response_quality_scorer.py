"""
Response Quality Scorer (Tier 4)

Analyzes CRA/furnisher response quality to detect:
- Boilerplate responses
- Evidence ignored
- Timing anomalies

Consumes: ExecutionResponseDB (SOURCE 2)
Outputs: ResponseQualityScore (read-only intelligence)

Does NOT modify enforcement logic.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Set
from enum import Enum
import re
import hashlib

from sqlalchemy.orm import Session
from sqlalchemy import func

from ...models.db_models import (
    ExecutionEventDB,
    ExecutionResponseDB,
    CopilotSignalCacheDB,
)


# =============================================================================
# BOILERPLATE PATTERNS (Known CRA/Furnisher Template Responses)
# =============================================================================

BOILERPLATE_PATTERNS: List[str] = [
    r"we have verified this information",
    r"the information reported is accurate",
    r"our investigation is complete",
    r"after a thorough investigation",
    r"we have concluded our investigation",
    r"the account information has been verified",
    r"the information has been verified as accurate",
    r"we have investigated your dispute",
    r"no change will be made",
    r"the creditor has verified",
    r"the furnisher has verified",
    r"we contacted the data furnisher",
    r"the data furnisher confirmed",
    r"please be advised",
    r"thank you for contacting us",
]

# Compile patterns for efficiency
COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in BOILERPLATE_PATTERNS]


class TimingAnomalyType(str, Enum):
    """Types of timing anomalies in responses."""
    INSTANT_VERIFICATION = "instant_verification"  # < 24 hours
    RAPID_VERIFICATION = "rapid_verification"      # < 72 hours for complex disputes
    DEADLINE_EDGE = "deadline_edge"                # Response on day 29-30
    WEEKEND_VERIFICATION = "weekend_verification"  # Verified on weekend (unlikely real investigation)


@dataclass
class ResponseQualityScore:
    """
    Quality assessment of a CRA/furnisher response.

    All fields are read-only intelligence — not enforcement inputs.
    """
    # Identity
    execution_event_id: str
    response_id: str
    entity_name: str
    entity_type: str  # CRA, FURNISHER

    # Boilerplate Detection
    boilerplate_score: float  # 0.0 to 1.0 (1.0 = pure boilerplate)
    boilerplate_patterns_matched: List[str] = field(default_factory=list)
    unique_text_ratio: float = 0.0  # % of response that's not boilerplate

    # Evidence Analysis
    evidence_ignored_flag: bool = False
    evidence_addressed_count: int = 0
    evidence_total_count: int = 0
    contradiction_codes_sent: List[str] = field(default_factory=list)
    contradiction_codes_addressed: List[str] = field(default_factory=list)

    # Timing Analysis
    timing_anomaly_flag: bool = False
    timing_anomaly_type: Optional[TimingAnomalyType] = None
    response_hours: float = 0.0  # Hours from dispute to response
    expected_min_hours: float = 72.0  # Minimum expected for real investigation

    # Computed at score time
    scored_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict:
        """Convert to dictionary for storage/serialization."""
        return {
            "execution_event_id": self.execution_event_id,
            "response_id": self.response_id,
            "entity_name": self.entity_name,
            "entity_type": self.entity_type,
            "boilerplate_score": self.boilerplate_score,
            "boilerplate_patterns_matched": self.boilerplate_patterns_matched,
            "unique_text_ratio": self.unique_text_ratio,
            "evidence_ignored_flag": self.evidence_ignored_flag,
            "evidence_addressed_count": self.evidence_addressed_count,
            "evidence_total_count": self.evidence_total_count,
            "contradiction_codes_sent": self.contradiction_codes_sent,
            "contradiction_codes_addressed": self.contradiction_codes_addressed,
            "timing_anomaly_flag": self.timing_anomaly_flag,
            "timing_anomaly_type": self.timing_anomaly_type.value if self.timing_anomaly_type else None,
            "response_hours": self.response_hours,
            "expected_min_hours": self.expected_min_hours,
            "scored_at": self.scored_at.isoformat(),
        }


class ResponseQualityScorer:
    """
    Scores CRA/furnisher response quality.

    Tier-4 intelligence component. Reads from execution ledger,
    outputs read-only scores. Does NOT modify enforcement.

    Usage:
        scorer = ResponseQualityScorer(db)
        score = scorer.score_response(execution_event_id, response_id)
    """

    # Timing thresholds (hours)
    INSTANT_THRESHOLD_HOURS = 24
    RAPID_THRESHOLD_HOURS = 72
    DEADLINE_EDGE_START_DAYS = 29

    def __init__(self, db: Session):
        self.db = db

    def score_response(
        self,
        execution_event_id: str,
        response_id: str,
        response_text: Optional[str] = None,
    ) -> Optional[ResponseQualityScore]:
        """
        Score a single response.

        Args:
            execution_event_id: The execution event UUID
            response_id: The response UUID
            response_text: Optional raw response text for boilerplate analysis

        Returns:
            ResponseQualityScore or None if records not found
        """
        # Fetch execution event
        event = self.db.query(ExecutionEventDB).filter(
            ExecutionEventDB.id == execution_event_id
        ).first()

        if not event:
            return None

        # Fetch response
        response = self.db.query(ExecutionResponseDB).filter(
            ExecutionResponseDB.id == response_id
        ).first()

        if not response:
            return None

        # Build score
        score = ResponseQualityScore(
            execution_event_id=execution_event_id,
            response_id=response_id,
            entity_name=event.creditor_name or response.bureau or "Unknown",
            entity_type="CRA" if response.bureau else "FURNISHER",
        )

        # 1. Boilerplate analysis
        if response_text:
            self._score_boilerplate(score, response_text)

        # 2. Evidence analysis
        self._score_evidence(score, event, response)

        # 3. Timing analysis
        self._score_timing(score, event, response)

        return score

    def score_all_unscored(
        self,
        limit: int = 100,
    ) -> List[ResponseQualityScore]:
        """
        Score all responses that haven't been scored yet.

        For use in nightly batch processing.

        Args:
            limit: Maximum responses to score per run

        Returns:
            List of scored responses
        """
        # Get responses without quality scores
        responses = (
            self.db.query(ExecutionResponseDB)
            .join(ExecutionEventDB)
            .filter(ExecutionResponseDB.quality_score_computed.is_(False))
            .limit(limit)
            .all()
        )

        scores = []
        for response in responses:
            score = self.score_response(
                execution_event_id=response.execution_event_id,
                response_id=response.id,
                response_text=response.response_text,
            )
            if score:
                scores.append(score)

        return scores

    def _score_boilerplate(
        self,
        score: ResponseQualityScore,
        response_text: str,
    ) -> None:
        """
        Analyze response text for boilerplate patterns.

        Sets:
        - boilerplate_score (0.0 to 1.0)
        - boilerplate_patterns_matched
        - unique_text_ratio
        """
        if not response_text:
            return

        text_lower = response_text.lower()
        total_chars = len(response_text)
        matched_chars = 0

        for pattern, compiled in zip(BOILERPLATE_PATTERNS, COMPILED_PATTERNS):
            matches = compiled.findall(text_lower)
            if matches:
                score.boilerplate_patterns_matched.append(pattern)
                # Estimate characters matched
                for match in matches:
                    if isinstance(match, str):
                        matched_chars += len(match)

        # Calculate scores
        if total_chars > 0:
            score.boilerplate_score = min(1.0, matched_chars / total_chars)
            score.unique_text_ratio = 1.0 - score.boilerplate_score
        else:
            score.boilerplate_score = 0.0
            score.unique_text_ratio = 0.0

        # Boost boilerplate score based on pattern count
        pattern_count = len(score.boilerplate_patterns_matched)
        if pattern_count >= 3:
            score.boilerplate_score = min(1.0, score.boilerplate_score + 0.3)
        elif pattern_count >= 2:
            score.boilerplate_score = min(1.0, score.boilerplate_score + 0.2)

    def _score_evidence(
        self,
        score: ResponseQualityScore,
        event: ExecutionEventDB,
        response: ExecutionResponseDB,
    ) -> None:
        """
        Analyze whether response addressed sent evidence.

        Sets:
        - evidence_ignored_flag
        - evidence_addressed_count
        - evidence_total_count
        - contradiction_codes_sent/addressed
        """
        # Get contradiction codes sent in original dispute
        if event.contradiction_rule:
            score.contradiction_codes_sent = [event.contradiction_rule]
            score.evidence_total_count = 1

        # Check if response indicates evidence was addressed
        # (For now, we check if specific data changed)
        addressed = []

        if response.balance_changed:
            addressed.append("balance")
        if response.dofd_changed:
            addressed.append("dofd")
        if response.status_changed:
            addressed.append("status")

        score.evidence_addressed_count = len(addressed)

        # If VERIFIED but no data changed with evidence sent, flag as ignored
        if (
            event.contradiction_rule
            and response.response_type
            and response.response_type.value == "VERIFIED"
            and score.evidence_addressed_count == 0
        ):
            score.evidence_ignored_flag = True

    def _score_timing(
        self,
        score: ResponseQualityScore,
        event: ExecutionEventDB,
        response: ExecutionResponseDB,
    ) -> None:
        """
        Analyze response timing for anomalies.

        Sets:
        - timing_anomaly_flag
        - timing_anomaly_type
        - response_hours
        """
        if not event.executed_at or not response.response_received_at:
            return

        # Calculate response time
        delta = response.response_received_at - event.executed_at
        score.response_hours = delta.total_seconds() / 3600

        # Check for anomalies
        if score.response_hours < self.INSTANT_THRESHOLD_HOURS:
            score.timing_anomaly_flag = True
            score.timing_anomaly_type = TimingAnomalyType.INSTANT_VERIFICATION

        elif score.response_hours < self.RAPID_THRESHOLD_HOURS:
            # Rapid is only anomalous for complex disputes
            if event.contradiction_rule in {"T1", "T2", "T3", "T4", "M1", "M2"}:
                score.timing_anomaly_flag = True
                score.timing_anomaly_type = TimingAnomalyType.RAPID_VERIFICATION

        # Check for deadline edge responses
        response_days = score.response_hours / 24
        if response_days >= self.DEADLINE_EDGE_START_DAYS:
            score.timing_anomaly_flag = True
            score.timing_anomaly_type = TimingAnomalyType.DEADLINE_EDGE

        # Check for weekend verification (crude check)
        if response.response_received_at.weekday() >= 5:  # Saturday or Sunday
            if score.response_hours < self.RAPID_THRESHOLD_HOURS:
                score.timing_anomaly_flag = True
                score.timing_anomaly_type = TimingAnomalyType.WEEKEND_VERIFICATION

    def get_entity_quality_summary(
        self,
        entity_name: str,
        window_days: int = 90,
    ) -> Dict:
        """
        Get aggregate quality metrics for an entity.

        Read-only intelligence for Tier 4 profiles.

        Args:
            entity_name: CRA or furnisher name
            window_days: Lookback window

        Returns:
            Aggregate quality metrics
        """
        window_start = datetime.now(timezone.utc) - timedelta(days=window_days)

        # Query responses for this entity
        responses = (
            self.db.query(ExecutionResponseDB)
            .join(ExecutionEventDB)
            .filter(
                ExecutionEventDB.creditor_name == entity_name,
                ExecutionResponseDB.response_received_at >= window_start,
            )
            .all()
        )

        if not responses:
            return {"entity_name": entity_name, "sample_count": 0}

        # Score all responses
        scores = []
        for resp in responses:
            score = self.score_response(
                execution_event_id=resp.execution_event_id,
                response_id=resp.id,
                response_text=resp.response_text,
            )
            if score:
                scores.append(score)

        if not scores:
            return {"entity_name": entity_name, "sample_count": 0}

        # Compute aggregates
        avg_boilerplate = sum(s.boilerplate_score for s in scores) / len(scores)
        evidence_ignored_count = sum(1 for s in scores if s.evidence_ignored_flag)
        timing_anomaly_count = sum(1 for s in scores if s.timing_anomaly_flag)
        avg_response_hours = sum(s.response_hours for s in scores) / len(scores)

        return {
            "entity_name": entity_name,
            "sample_count": len(scores),
            "avg_boilerplate_score": round(avg_boilerplate, 3),
            "evidence_ignored_rate": round(evidence_ignored_count / len(scores), 3),
            "timing_anomaly_rate": round(timing_anomaly_count / len(scores), 3),
            "avg_response_hours": round(avg_response_hours, 1),
        }
