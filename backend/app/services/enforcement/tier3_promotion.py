"""
Tier-3 Promotion Service

Handles promotion from Tier-2 exhaustion to Tier-3.

TIER-3 SCOPE (STRICT):
- Lock violation record
- Classify examiner failure
- Write immutable ledger entry

TIER-3 DOES NOT:
- Generate new letters
- Contact regulators
- Trigger litigation
- Implement Tier-4–6 logic
"""

from datetime import datetime, timezone
from typing import Dict, Any
from uuid import uuid4

from sqlalchemy.orm import Session

from ...models.db_models import (
    DisputeDB,
    Tier2ResponseDB,
    Tier2ResponseType,
    PaperTrailDB,
    ActorType,
)


# =============================================================================
# TIER-3 CLASSIFICATION MAPPING
# =============================================================================

TIER3_CLASSIFICATIONS = {
    Tier2ResponseType.REPEAT_VERIFIED: "REPEATED_VERIFICATION_FAILURE",
    Tier2ResponseType.DEFLECTION_FRIVOLOUS: "FRIVOLOUS_DEFLECTION",
    Tier2ResponseType.NO_RESPONSE_AFTER_CURE_WINDOW: "CURE_WINDOW_EXPIRED",
}


class Tier3PromotionService:
    """
    Tier-3 promotion logic.

    Tier-3 does ONLY:
    - Lock violation record (prevent further edits)
    - Classify examiner failure
    - Write immutable ledger entry

    Tier-3 does NOT:
    - Generate letters
    - Contact regulators
    - Trigger litigation
    """

    def __init__(self, db: Session):
        self.db = db

    def promote_to_tier3(
        self,
        dispute: DisputeDB,
        tier2_response: Tier2ResponseDB,
    ) -> Dict[str, Any]:
        """
        Promote violation to Tier-3.

        Args:
            dispute: The dispute being promoted
            tier2_response: The final Tier-2 response

        Returns:
            Ledger entry data containing all required fields
        """
        # 1. Lock violation record (prevent further edits)
        dispute.tier_reached = 3
        dispute.locked = True

        # 2. Classify examiner failure
        classification = self._classify_failure(tier2_response.response_type)
        tier2_response.tier3_classification = classification
        tier2_response.tier3_promoted = True
        tier2_response.tier3_promotion_date = datetime.now(timezone.utc)

        # 3. Write immutable ledger entry
        ledger_entry = self._write_tier3_ledger(dispute, tier2_response, classification)

        return ledger_entry

    def _classify_failure(self, response_type: Tier2ResponseType) -> str:
        """
        Classify the examiner failure type.

        Mappings:
        - REPEAT_VERIFIED → REPEATED_VERIFICATION_FAILURE
        - DEFLECTION_FRIVOLOUS → FRIVOLOUS_DEFLECTION
        - NO_RESPONSE_AFTER_CURE_WINDOW → CURE_WINDOW_EXPIRED
        """
        return TIER3_CLASSIFICATIONS.get(response_type, "UNKNOWN")

    def _write_tier3_ledger(
        self,
        dispute: DisputeDB,
        tier2_response: Tier2ResponseDB,
        classification: str,
    ) -> Dict[str, Any]:
        """
        Write Tier-3 promotion ledger entry.

        Creates immutable record with minimum required fields:
        - cra: Entity name
        - furnisher: Creditor from violation
        - violation: Description of violation
        - tier_reached: 3
        - tier_2_notice_sent: true
        - cure_opportunity_given: true
        - cure_outcome: The Tier-2 response type
        - date_closed: Timestamp
        """
        # Extract violation details from dispute's original data
        # Handle both list and dict formats
        raw_violation_data = dispute.original_violation_data
        if isinstance(raw_violation_data, list):
            # If it's a list, use first item as primary violation
            primary_violation = raw_violation_data[0] if raw_violation_data else {}
            contradictions = []
        elif isinstance(raw_violation_data, dict):
            contradictions = raw_violation_data.get("contradictions", [])
            primary_violation = contradictions[0] if contradictions else raw_violation_data
        else:
            primary_violation = {}
            contradictions = []

        # Build ledger entry with required fields
        ledger_entry = {
            "cra": dispute.entity_name,
            "furnisher": primary_violation.get("creditor_name", "Unknown"),
            "violation": primary_violation.get("description", "Unknown"),
            "tier_reached": 3,
            "tier_2_notice_sent": True,
            "cure_opportunity_given": True,
            "cure_outcome": tier2_response.response_type.value,
            "examiner_classification": classification,
            "date_closed": datetime.now(timezone.utc).isoformat(),
        }

        # Create PaperTrailDB entry (immutable)
        paper_trail = PaperTrailDB(
            id=str(uuid4()),
            dispute_id=dispute.id,
            event_type="tier3_promotion",
            actor=ActorType.SYSTEM,
            description=f"Violation promoted to Tier-3: {classification}",
            event_metadata=ledger_entry,
        )
        self.db.add(paper_trail)

        return ledger_entry
