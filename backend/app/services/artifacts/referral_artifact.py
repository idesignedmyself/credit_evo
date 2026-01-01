"""
Referral Artifact (Tier 5)

Minimal schema for attorney/regulatory referrals.

Contains:
- Violations summary
- Cure attempt record
- Failure mode classification

Designed to be machine-readable for intake systems.
No auto-sending — generation only.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from uuid import uuid4
from enum import Enum
import hashlib
import json

from sqlalchemy.orm import Session

from ...models.db_models import (
    DisputeDB,
    Tier2ResponseDB,
)


class ReferralType(str, Enum):
    """Types of referral destinations."""
    ATTORNEY = "attorney"
    CFPB = "cfpb"
    STATE_AG = "state_ag"
    FTC = "ftc"


class FailureMode(str, Enum):
    """Classification of how the entity failed."""
    REPEATED_VERIFICATION = "repeated_verification"  # Verified impossible data twice
    FRIVOLOUS_DEFLECTION = "frivolous_deflection"    # Rejected as frivolous
    NO_RESPONSE = "no_response"                       # Failed to respond
    PROCEDURAL_FAILURE = "procedural_failure"         # Failed investigation procedure
    REINSERTION = "reinsertion"                       # Reinserted deleted data


@dataclass
class ViolationSummary:
    """Minimal violation summary for referral."""
    violation_type: str
    severity: str
    statute: Optional[str] = None
    description: str = ""


@dataclass
class CureAttemptRecord:
    """Record of cure opportunity given."""
    tier2_notice_sent: bool = False
    tier2_notice_date: Optional[datetime] = None
    cure_window_days: int = 15
    response_received: bool = False
    response_type: Optional[str] = None
    response_date: Optional[datetime] = None


@dataclass
class ReferralArtifact:
    """
    Minimal referral artifact for attorney/regulatory intake.

    Designed to be compact and machine-readable.
    Contains only what's needed for intake decision.
    """
    # Identity
    artifact_id: str
    dispute_id: str
    referral_type: ReferralType

    # Parties (minimal)
    cra_name: str = ""
    furnisher_name: str = ""
    account_number_masked: str = ""

    # Violations (summarized)
    violations: List[ViolationSummary] = field(default_factory=list)
    violation_count: int = 0
    highest_severity: str = "MEDIUM"

    # Cure Attempt
    cure_attempt: Optional[CureAttemptRecord] = None

    # Failure Classification
    failure_mode: Optional[FailureMode] = None
    tier3_classification: str = ""

    # Statutes
    primary_statutes: List[str] = field(default_factory=list)

    # Timeline (minimal)
    first_dispute_date: Optional[datetime] = None
    tier3_promotion_date: Optional[datetime] = None
    days_in_dispute: int = 0

    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    artifact_hash: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "artifact_id": self.artifact_id,
            "dispute_id": self.dispute_id,
            "referral_type": self.referral_type.value,
            "cra_name": self.cra_name,
            "furnisher_name": self.furnisher_name,
            "account_number_masked": self.account_number_masked,
            "violations": [
                {
                    "violation_type": v.violation_type,
                    "severity": v.severity,
                    "statute": v.statute,
                    "description": v.description,
                }
                for v in self.violations
            ],
            "violation_count": self.violation_count,
            "highest_severity": self.highest_severity,
            "cure_attempt": {
                "tier2_notice_sent": self.cure_attempt.tier2_notice_sent,
                "tier2_notice_date": self.cure_attempt.tier2_notice_date.isoformat() if self.cure_attempt.tier2_notice_date else None,
                "cure_window_days": self.cure_attempt.cure_window_days,
                "response_received": self.cure_attempt.response_received,
                "response_type": self.cure_attempt.response_type,
                "response_date": self.cure_attempt.response_date.isoformat() if self.cure_attempt.response_date else None,
            } if self.cure_attempt else None,
            "failure_mode": self.failure_mode.value if self.failure_mode else None,
            "tier3_classification": self.tier3_classification,
            "primary_statutes": self.primary_statutes,
            "first_dispute_date": self.first_dispute_date.isoformat() if self.first_dispute_date else None,
            "tier3_promotion_date": self.tier3_promotion_date.isoformat() if self.tier3_promotion_date else None,
            "days_in_dispute": self.days_in_dispute,
            "created_at": self.created_at.isoformat(),
            "artifact_hash": self.artifact_hash,
        }

    def compute_hash(self) -> str:
        """Compute integrity hash."""
        content = {
            "dispute_id": self.dispute_id,
            "violation_count": self.violation_count,
            "failure_mode": self.failure_mode.value if self.failure_mode else None,
            "tier3_classification": self.tier3_classification,
        }
        json_str = json.dumps(content, sort_keys=True)
        return hashlib.sha256(json_str.encode()).hexdigest()[:16]


class ReferralArtifactBuilder:
    """
    Builds minimal referral artifacts from Tier-3 disputes.

    Tier-5 component. Read-only from ledger.
    No auto-sending — generation only.

    Usage:
        builder = ReferralArtifactBuilder(db)
        artifact = builder.build_artifact(dispute_id, ReferralType.ATTORNEY)
    """

    # Mapping from Tier-3 classification to failure mode
    CLASSIFICATION_TO_FAILURE_MODE = {
        "REPEATED_VERIFICATION_FAILURE": FailureMode.REPEATED_VERIFICATION,
        "FRIVOLOUS_DEFLECTION": FailureMode.FRIVOLOUS_DEFLECTION,
        "CURE_WINDOW_EXPIRED": FailureMode.NO_RESPONSE,
    }

    def __init__(self, db: Session):
        self.db = db

    def build_artifact(
        self,
        dispute_id: str,
        referral_type: ReferralType,
    ) -> Optional[ReferralArtifact]:
        """
        Build referral artifact for a Tier-3 dispute.

        Args:
            dispute_id: The dispute UUID
            referral_type: Target referral type

        Returns:
            ReferralArtifact or None if not eligible
        """
        # Fetch dispute
        dispute = self.db.query(DisputeDB).filter(
            DisputeDB.id == dispute_id
        ).first()

        if not dispute:
            return None

        # Must be Tier-3
        if dispute.tier_reached < 3:
            return None

        # Get Tier-2 response
        tier2_response = self.db.query(Tier2ResponseDB).filter(
            Tier2ResponseDB.dispute_id == dispute_id,
            Tier2ResponseDB.tier3_promoted == True,
        ).first()

        # Build artifact
        artifact = ReferralArtifact(
            artifact_id=str(uuid4()),
            dispute_id=dispute_id,
            referral_type=referral_type,
            cra_name=dispute.entity_name or "",
        )

        # 1. Extract violations
        self._extract_violations(artifact, dispute)

        # 2. Build cure attempt record
        self._build_cure_record(artifact, dispute, tier2_response)

        # 3. Classify failure mode
        if tier2_response:
            artifact.tier3_classification = tier2_response.tier3_classification or ""
            artifact.failure_mode = self.CLASSIFICATION_TO_FAILURE_MODE.get(
                artifact.tier3_classification
            )
            artifact.tier3_promotion_date = tier2_response.tier3_promotion_date

        # 4. Set timeline
        artifact.first_dispute_date = dispute.dispute_date
        if artifact.first_dispute_date and artifact.tier3_promotion_date:
            delta = artifact.tier3_promotion_date - datetime.combine(
                artifact.first_dispute_date,
                datetime.min.time()
            ).replace(tzinfo=timezone.utc)
            artifact.days_in_dispute = delta.days

        # 5. Determine primary statutes
        self._determine_statutes(artifact)

        # 6. Compute hash
        artifact.artifact_hash = artifact.compute_hash()

        return artifact

    def _extract_violations(
        self,
        artifact: ReferralArtifact,
        dispute: DisputeDB,
    ) -> None:
        """Extract violation summaries from dispute."""
        violation_data = dispute.original_violation_data or {}
        contradictions = violation_data.get("contradictions", [])

        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        highest_severity_rank = 3

        for contra in contradictions:
            summary = ViolationSummary(
                violation_type=contra.get("rule_code", "UNKNOWN"),
                severity=contra.get("severity", "MEDIUM"),
                statute=contra.get("primary_statute"),
                description=contra.get("description", "")[:200],  # Truncate for brevity
            )
            artifact.violations.append(summary)

            # Track highest severity
            rank = severity_order.get(summary.severity, 3)
            if rank < highest_severity_rank:
                highest_severity_rank = rank
                artifact.highest_severity = summary.severity

            # Extract furnisher and account
            if not artifact.furnisher_name:
                artifact.furnisher_name = contra.get("creditor_name", "")
            if not artifact.account_number_masked:
                artifact.account_number_masked = contra.get("account_number_masked", "")

        artifact.violation_count = len(artifact.violations)

    def _build_cure_record(
        self,
        artifact: ReferralArtifact,
        dispute: DisputeDB,
        tier2_response: Optional[Tier2ResponseDB],
    ) -> None:
        """Build cure attempt record."""
        cure = CureAttemptRecord(
            tier2_notice_sent=dispute.tier2_notice_sent or False,
            tier2_notice_date=dispute.tier2_notice_sent_at,
            cure_window_days=15,
        )

        if tier2_response:
            cure.response_received = True
            cure.response_type = tier2_response.response_type.value if tier2_response.response_type else None
            cure.response_date = tier2_response.response_date

        artifact.cure_attempt = cure

    def _determine_statutes(self, artifact: ReferralArtifact) -> None:
        """Determine primary statutes from violations and failure mode."""
        statutes = set()

        # From violations
        for v in artifact.violations:
            if v.statute:
                statutes.add(v.statute)

        # From failure mode
        failure_statutes = {
            FailureMode.REPEATED_VERIFICATION: "15 U.S.C. § 1681i(a)(1)(A)",
            FailureMode.FRIVOLOUS_DEFLECTION: "15 U.S.C. § 1681i(a)(3)",
            FailureMode.NO_RESPONSE: "15 U.S.C. § 1681i(a)(6)(A)",
            FailureMode.REINSERTION: "15 U.S.C. § 1681i(a)(5)(B)",
        }

        if artifact.failure_mode and artifact.failure_mode in failure_statutes:
            statutes.add(failure_statutes[artifact.failure_mode])

        artifact.primary_statutes = sorted(list(statutes))[:5]  # Limit to top 5

    def build_for_cfpb(self, dispute_id: str) -> Optional[ReferralArtifact]:
        """Convenience method for CFPB referral."""
        return self.build_artifact(dispute_id, ReferralType.CFPB)

    def build_for_attorney(self, dispute_id: str) -> Optional[ReferralArtifact]:
        """Convenience method for attorney referral."""
        return self.build_artifact(dispute_id, ReferralType.ATTORNEY)

    def build_for_state_ag(self, dispute_id: str) -> Optional[ReferralArtifact]:
        """Convenience method for State AG referral."""
        return self.build_artifact(dispute_id, ReferralType.STATE_AG)
