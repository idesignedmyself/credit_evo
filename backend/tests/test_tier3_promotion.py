"""
Tests for Tier-2 Exhaustion → Tier-3 Promotion.

Tests the complete flow from Tier-2 supervisory response to Tier-3 promotion:
1. CURED response → Close as CURED_AT_TIER_2
2. REPEAT_VERIFIED → Auto-promote to Tier-3
3. DEFLECTION_FRIVOLOUS → Auto-promote to Tier-3
4. NO_RESPONSE_AFTER_CURE_WINDOW → Auto-promote to Tier-3
5. Tier-2 exhaustion enforced (only one response allowed)
6. Tier-3 locking prevents further changes
7. Tier-3 classification mapping
8. Immutable ledger entry creation
"""
import pytest
from datetime import date, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4


# =============================================================================
# TEST: TIER-3 PROMOTION SERVICE
# =============================================================================

class TestTier3PromotionService:
    """Tests for Tier3PromotionService."""

    def test_promote_to_tier3_repeat_verified(self):
        """REPEAT_VERIFIED → Tier-3 promotion with correct classification."""
        from app.services.enforcement.tier3_promotion import Tier3PromotionService
        from app.models.db_models import Tier2ResponseType

        mock_db = MagicMock()

        # Mock dispute
        mock_dispute = MagicMock()
        mock_dispute.id = str(uuid4())
        mock_dispute.entity_name = "TransUnion"
        mock_dispute.tier_reached = 2
        mock_dispute.locked = False
        mock_dispute.original_violation_data = {
            "contradictions": [
                {"creditor_name": "Verizon", "description": "Missing DOFD"}
            ]
        }

        # Mock Tier-2 response
        mock_tier2_response = MagicMock()
        mock_tier2_response.response_type = Tier2ResponseType.REPEAT_VERIFIED

        service = Tier3PromotionService(mock_db)
        ledger_entry = service.promote_to_tier3(mock_dispute, mock_tier2_response)

        # Verify dispute was locked
        assert mock_dispute.tier_reached == 3
        assert mock_dispute.locked is True

        # Verify classification
        assert mock_tier2_response.tier3_classification == "REPEATED_VERIFICATION_FAILURE"
        assert mock_tier2_response.tier3_promoted is True

        # Verify ledger entry
        assert ledger_entry["cra"] == "TransUnion"
        assert ledger_entry["furnisher"] == "Verizon"
        assert ledger_entry["violation"] == "Missing DOFD"
        assert ledger_entry["tier_reached"] == 3
        assert ledger_entry["tier_2_notice_sent"] is True
        assert ledger_entry["cure_opportunity_given"] is True
        assert ledger_entry["cure_outcome"] == "REPEAT_VERIFIED"
        assert ledger_entry["examiner_classification"] == "REPEATED_VERIFICATION_FAILURE"

    def test_promote_to_tier3_deflection_frivolous(self):
        """DEFLECTION_FRIVOLOUS → Tier-3 promotion with correct classification."""
        from app.services.enforcement.tier3_promotion import Tier3PromotionService
        from app.models.db_models import Tier2ResponseType

        mock_db = MagicMock()

        mock_dispute = MagicMock()
        mock_dispute.id = str(uuid4())
        mock_dispute.entity_name = "Equifax"
        mock_dispute.tier_reached = 2
        mock_dispute.locked = False
        mock_dispute.original_violation_data = {
            "contradictions": [
                {"creditor_name": "AT&T", "description": "Balance mismatch"}
            ]
        }

        mock_tier2_response = MagicMock()
        mock_tier2_response.response_type = Tier2ResponseType.DEFLECTION_FRIVOLOUS

        service = Tier3PromotionService(mock_db)
        ledger_entry = service.promote_to_tier3(mock_dispute, mock_tier2_response)

        # Verify classification is correct
        assert mock_tier2_response.tier3_classification == "FRIVOLOUS_DEFLECTION"
        assert ledger_entry["examiner_classification"] == "FRIVOLOUS_DEFLECTION"
        assert ledger_entry["cure_outcome"] == "DEFLECTION_FRIVOLOUS"

    def test_promote_to_tier3_no_response_cure_window(self):
        """NO_RESPONSE_AFTER_CURE_WINDOW → Tier-3 promotion with correct classification."""
        from app.services.enforcement.tier3_promotion import Tier3PromotionService
        from app.models.db_models import Tier2ResponseType

        mock_db = MagicMock()

        mock_dispute = MagicMock()
        mock_dispute.id = str(uuid4())
        mock_dispute.entity_name = "Experian"
        mock_dispute.tier_reached = 2
        mock_dispute.locked = False
        mock_dispute.original_violation_data = {
            "contradictions": [
                {"creditor_name": "Capital One", "description": "Late payment disputed"}
            ]
        }

        mock_tier2_response = MagicMock()
        mock_tier2_response.response_type = Tier2ResponseType.NO_RESPONSE_AFTER_CURE_WINDOW

        service = Tier3PromotionService(mock_db)
        ledger_entry = service.promote_to_tier3(mock_dispute, mock_tier2_response)

        # Verify classification is correct
        assert mock_tier2_response.tier3_classification == "CURE_WINDOW_EXPIRED"
        assert ledger_entry["examiner_classification"] == "CURE_WINDOW_EXPIRED"
        assert ledger_entry["cure_outcome"] == "NO_RESPONSE_AFTER_CURE_WINDOW"

    def test_ledger_entry_creates_paper_trail(self):
        """Verify that ledger write creates PaperTrailDB entry."""
        from app.services.enforcement.tier3_promotion import Tier3PromotionService
        from app.models.db_models import Tier2ResponseType

        mock_db = MagicMock()

        mock_dispute = MagicMock()
        mock_dispute.id = str(uuid4())
        mock_dispute.entity_name = "TransUnion"
        mock_dispute.tier_reached = 2
        mock_dispute.locked = False
        mock_dispute.original_violation_data = {"contradictions": []}

        mock_tier2_response = MagicMock()
        mock_tier2_response.response_type = Tier2ResponseType.REPEAT_VERIFIED

        service = Tier3PromotionService(mock_db)
        service.promote_to_tier3(mock_dispute, mock_tier2_response)

        # Verify db.add was called with PaperTrailDB
        assert mock_db.add.called
        added_obj = mock_db.add.call_args[0][0]
        assert added_obj.event_type == "tier3_promotion"
        assert "Tier-3" in added_obj.description


# =============================================================================
# TEST: DISPUTE SERVICE TIER-2 RESPONSE
# =============================================================================

class TestDisputeServiceTier2Response:
    """Tests for DisputeService.log_tier2_response."""

    def test_cured_response_closes_dispute(self):
        """CURED → Close as CURED_AT_TIER_2, tier_reached=2, not locked."""
        from app.services.enforcement.dispute_service import DisputeService
        from app.models.db_models import Tier2ResponseType, EscalationState

        mock_db = MagicMock()

        # Mock dispute query result
        mock_dispute = MagicMock()
        mock_dispute.id = str(uuid4())
        mock_dispute.tier_reached = 1
        mock_dispute.locked = False
        mock_db.query.return_value.filter.return_value.first.return_value = mock_dispute

        service = DisputeService(mock_db)

        # First call returns dispute, second returns None (no existing Tier-2 response)
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_dispute,  # First query: dispute lookup
            None,  # Second query: no existing tier2 response
        ]

        result = service.log_tier2_response(
            dispute_id=mock_dispute.id,
            response_type=Tier2ResponseType.CURED,
            response_date=date.today(),
        )

        assert result["status"] == "CURED_AT_TIER_2"
        assert result["tier_reached"] == 2
        assert result["locked"] is False
        assert mock_dispute.tier_reached == 2
        assert mock_dispute.current_state == EscalationState.RESOLVED_CURED

    def test_non_cured_promotes_to_tier3(self):
        """REPEAT_VERIFIED → Tier-3 promotion, locked=True."""
        from app.services.enforcement.dispute_service import DisputeService
        from app.models.db_models import Tier2ResponseType

        mock_db = MagicMock()

        mock_dispute = MagicMock()
        mock_dispute.id = str(uuid4())
        mock_dispute.tier_reached = 1
        mock_dispute.locked = False
        mock_dispute.entity_name = "TransUnion"
        mock_dispute.original_violation_data = {"contradictions": []}

        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_dispute,
            None,  # No existing tier2 response
        ]

        service = DisputeService(mock_db)
        result = service.log_tier2_response(
            dispute_id=mock_dispute.id,
            response_type=Tier2ResponseType.REPEAT_VERIFIED,
            response_date=date.today(),
        )

        assert result["status"] == "PROMOTED_TO_TIER_3"
        assert result["tier_reached"] == 3
        assert result["locked"] is True
        assert "ledger_entry" in result

    def test_tier2_exhaustion_enforced(self):
        """Second Tier-2 response should raise error."""
        from app.services.enforcement.dispute_service import DisputeService
        from app.models.db_models import Tier2ResponseType

        mock_db = MagicMock()

        mock_dispute = MagicMock()
        mock_dispute.id = str(uuid4())
        mock_dispute.tier_reached = 2
        mock_dispute.locked = False

        # Mock existing Tier-2 response
        mock_existing_response = MagicMock()

        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_dispute,
            mock_existing_response,  # Existing tier2 response found
        ]

        service = DisputeService(mock_db)

        with pytest.raises(ValueError) as exc_info:
            service.log_tier2_response(
                dispute_id=mock_dispute.id,
                response_type=Tier2ResponseType.CURED,
                response_date=date.today(),
            )

        assert "already logged" in str(exc_info.value).lower()
        assert "exhausted" in str(exc_info.value).lower()

    def test_locked_dispute_rejects_response(self):
        """Locked (Tier-3) dispute should reject Tier-2 response."""
        from app.services.enforcement.dispute_service import DisputeService
        from app.models.db_models import Tier2ResponseType

        mock_db = MagicMock()

        mock_dispute = MagicMock()
        mock_dispute.id = str(uuid4())
        mock_dispute.tier_reached = 3
        mock_dispute.locked = True

        mock_db.query.return_value.filter.return_value.first.return_value = mock_dispute

        service = DisputeService(mock_db)

        with pytest.raises(ValueError) as exc_info:
            service.log_tier2_response(
                dispute_id=mock_dispute.id,
                response_type=Tier2ResponseType.CURED,
                response_date=date.today(),
            )

        assert "locked" in str(exc_info.value).lower()

    def test_dispute_not_found_raises_error(self):
        """Non-existent dispute should raise error."""
        from app.services.enforcement.dispute_service import DisputeService
        from app.models.db_models import Tier2ResponseType

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        service = DisputeService(mock_db)

        with pytest.raises(ValueError) as exc_info:
            service.log_tier2_response(
                dispute_id="nonexistent",
                response_type=Tier2ResponseType.CURED,
                response_date=date.today(),
            )

        assert "not found" in str(exc_info.value).lower()


# =============================================================================
# TEST: TIER-3 CLASSIFICATION MAPPING
# =============================================================================

class TestTier3Classification:
    """Tests for Tier-3 classification mapping."""

    def test_classification_mapping_complete(self):
        """Verify all Tier-2 response types have classifications."""
        from app.services.enforcement.tier3_promotion import TIER3_CLASSIFICATIONS
        from app.models.db_models import Tier2ResponseType

        # CURED should not be in classifications (it doesn't promote)
        for response_type in Tier2ResponseType:
            if response_type != Tier2ResponseType.CURED:
                assert response_type in TIER3_CLASSIFICATIONS, f"Missing classification for {response_type}"

    def test_classification_values_are_strings(self):
        """Verify all classifications are non-empty strings."""
        from app.services.enforcement.tier3_promotion import TIER3_CLASSIFICATIONS

        for response_type, classification in TIER3_CLASSIFICATIONS.items():
            assert isinstance(classification, str)
            assert len(classification) > 0


# =============================================================================
# TEST: LEDGER ENTRY FORMAT
# =============================================================================

class TestLedgerEntryFormat:
    """Tests for Tier-3 ledger entry format."""

    def test_ledger_entry_has_required_fields(self):
        """Ledger entry must contain all required fields from spec."""
        from app.services.enforcement.tier3_promotion import Tier3PromotionService
        from app.models.db_models import Tier2ResponseType

        mock_db = MagicMock()

        mock_dispute = MagicMock()
        mock_dispute.id = str(uuid4())
        mock_dispute.entity_name = "TransUnion"
        mock_dispute.tier_reached = 2
        mock_dispute.locked = False
        mock_dispute.original_violation_data = {
            "contradictions": [
                {"creditor_name": "Verizon", "description": "Missing DOFD"}
            ]
        }

        mock_tier2_response = MagicMock()
        mock_tier2_response.response_type = Tier2ResponseType.REPEAT_VERIFIED

        service = Tier3PromotionService(mock_db)
        ledger_entry = service.promote_to_tier3(mock_dispute, mock_tier2_response)

        # Verify all required fields from spec
        required_fields = [
            "cra",
            "furnisher",
            "violation",
            "tier_reached",
            "tier_2_notice_sent",
            "cure_opportunity_given",
            "cure_outcome",
            "date_closed",
        ]
        for field in required_fields:
            assert field in ledger_entry, f"Missing required field: {field}"

    def test_ledger_entry_tier_reached_is_3(self):
        """Ledger entry tier_reached must be 3."""
        from app.services.enforcement.tier3_promotion import Tier3PromotionService
        from app.models.db_models import Tier2ResponseType

        mock_db = MagicMock()

        mock_dispute = MagicMock()
        mock_dispute.id = str(uuid4())
        mock_dispute.entity_name = "Experian"
        mock_dispute.original_violation_data = {"contradictions": []}

        mock_tier2_response = MagicMock()
        mock_tier2_response.response_type = Tier2ResponseType.DEFLECTION_FRIVOLOUS

        service = Tier3PromotionService(mock_db)
        ledger_entry = service.promote_to_tier3(mock_dispute, mock_tier2_response)

        assert ledger_entry["tier_reached"] == 3


# =============================================================================
# INTEGRATION TEST
# =============================================================================

class TestTier3Integration:
    """Integration tests for the complete Tier-3 flow."""

    def test_end_to_end_tier3_promotion(self):
        """Complete flow: Tier-2 response → Tier-3 promotion → locked state."""
        from app.services.enforcement.dispute_service import DisputeService
        from app.models.db_models import Tier2ResponseType

        mock_db = MagicMock()

        # Create initial dispute at Tier-1
        mock_dispute = MagicMock()
        mock_dispute.id = str(uuid4())
        mock_dispute.entity_name = "TransUnion"
        mock_dispute.tier_reached = 1
        mock_dispute.locked = False
        mock_dispute.original_violation_data = {
            "contradictions": [
                {"creditor_name": "Verizon", "description": "Missing DOFD"}
            ]
        }

        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_dispute,
            None,  # No existing tier2 response
        ]

        service = DisputeService(mock_db)

        # Log REPEAT_VERIFIED Tier-2 response
        result = service.log_tier2_response(
            dispute_id=mock_dispute.id,
            response_type=Tier2ResponseType.REPEAT_VERIFIED,
            response_date=date.today(),
        )

        # Verify complete promotion
        assert result["status"] == "PROMOTED_TO_TIER_3"
        assert result["tier_reached"] == 3
        assert result["locked"] is True

        # Verify ledger entry
        ledger = result["ledger_entry"]
        assert ledger["cra"] == "TransUnion"
        assert ledger["furnisher"] == "Verizon"
        assert ledger["tier_2_notice_sent"] is True
        assert ledger["cure_opportunity_given"] is True
        assert ledger["examiner_classification"] == "REPEATED_VERIFICATION_FAILURE"

        # Verify dispute state was updated
        assert mock_dispute.tier_reached == 3
        assert mock_dispute.locked is True


# =============================================================================
# TEST: TIER-2 NOTICE SENT TRACKING
# =============================================================================

class TestMarkTier2NoticeSent:
    """Tests for mark_tier2_notice_sent functionality."""

    def test_mark_tier2_notice_sent_success(self):
        """Successfully mark Tier-2 notice as sent."""
        from app.services.enforcement.dispute_service import DisputeService

        mock_db = MagicMock()

        mock_dispute = MagicMock()
        mock_dispute.id = str(uuid4())
        mock_dispute.tier_reached = 1
        mock_dispute.locked = False
        mock_dispute.tier2_notice_sent = False

        mock_db.query.return_value.filter.return_value.first.return_value = mock_dispute

        service = DisputeService(mock_db)
        result = service.mark_tier2_notice_sent(dispute_id=mock_dispute.id)

        assert result["status"] == "TIER2_NOTICE_SENT"
        assert result["tier2_notice_sent"] is True
        assert result["tier_reached"] == 2
        assert mock_dispute.tier2_notice_sent is True
        assert mock_dispute.tier_reached == 2

    def test_mark_tier2_notice_sent_already_sent_raises_error(self):
        """Cannot mark as sent if already sent."""
        from app.services.enforcement.dispute_service import DisputeService

        mock_db = MagicMock()

        mock_dispute = MagicMock()
        mock_dispute.id = str(uuid4())
        mock_dispute.tier_reached = 2
        mock_dispute.locked = False
        mock_dispute.tier2_notice_sent = True  # Already sent

        mock_db.query.return_value.filter.return_value.first.return_value = mock_dispute

        service = DisputeService(mock_db)

        with pytest.raises(ValueError) as exc_info:
            service.mark_tier2_notice_sent(dispute_id=mock_dispute.id)

        assert "already" in str(exc_info.value).lower()

    def test_mark_tier2_notice_sent_locked_dispute_raises_error(self):
        """Cannot mark as sent if dispute is locked at Tier-3."""
        from app.services.enforcement.dispute_service import DisputeService

        mock_db = MagicMock()

        mock_dispute = MagicMock()
        mock_dispute.id = str(uuid4())
        mock_dispute.tier_reached = 3
        mock_dispute.locked = True
        mock_dispute.tier2_notice_sent = False

        mock_db.query.return_value.filter.return_value.first.return_value = mock_dispute

        service = DisputeService(mock_db)

        with pytest.raises(ValueError) as exc_info:
            service.mark_tier2_notice_sent(dispute_id=mock_dispute.id)

        assert "locked" in str(exc_info.value).lower()

    def test_mark_tier2_notice_sent_dispute_not_found_raises_error(self):
        """Error when dispute not found."""
        from app.services.enforcement.dispute_service import DisputeService

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        service = DisputeService(mock_db)

        with pytest.raises(ValueError) as exc_info:
            service.mark_tier2_notice_sent(dispute_id="nonexistent")

        assert "not found" in str(exc_info.value).lower()

    def test_tier2_response_requires_notice_sent(self):
        """Tier-2 response cannot be logged without tier2_notice_sent = True."""
        from app.services.enforcement.dispute_service import DisputeService
        from app.models.db_models import Tier2ResponseType

        mock_db = MagicMock()

        mock_dispute = MagicMock()
        mock_dispute.id = str(uuid4())
        mock_dispute.tier_reached = 1
        mock_dispute.locked = False
        mock_dispute.tier2_notice_sent = False  # Not sent yet

        mock_db.query.return_value.filter.return_value.first.return_value = mock_dispute

        service = DisputeService(mock_db)

        with pytest.raises(ValueError) as exc_info:
            service.log_tier2_response(
                dispute_id=mock_dispute.id,
                response_type=Tier2ResponseType.CURED,
                response_date=date.today(),
            )

        assert "not been marked as sent" in str(exc_info.value).lower()
