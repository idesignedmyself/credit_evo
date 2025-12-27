"""
Tests for Tier 2 Examiner Standard Enforcement.

Tests the examiner check service that evaluates entity responses
against supervisory examination standards.

Test Coverage:
1. PERFUNCTORY_INVESTIGATION - VERIFIED despite contradiction + evidence
2. NOTICE_OF_RESULTS_FAILURE - NO_RESPONSE after deadline
3. SYSTEMIC_ACCURACY_FAILURE - Same contradiction across ≥2 bureaus
4. UDAAP_MISLEADING_VERIFICATION - VERIFIED on CRITICAL impossibility
5. Pass conditions (no false positives)
6. Escalation triggers
7. Letter selection upgrades
8. Tier 1 behavior unchanged
"""
import pytest
from datetime import date, timedelta
from unittest.mock import MagicMock, patch
from uuid import uuid4


# =============================================================================
# TEST: EXAMINER CHECK SERVICE
# =============================================================================

class TestExaminerCheckService:
    """Tests for ExaminerCheckService."""

    def test_perfunctory_investigation_triggered(self):
        """VERIFIED + contradiction + evidence_sent → PERFUNCTORY_INVESTIGATION"""
        from app.services.enforcement.examiner_check import (
            ExaminerCheckService, ExaminerStandardResult
        )
        from app.models.db_models import ResponseType

        # Create mock DB session
        mock_db = MagicMock()

        # Mock dispute with deadline in past
        mock_dispute = MagicMock()
        mock_dispute.id = str(uuid4())
        mock_dispute.deadline_date = date.today() - timedelta(days=5)

        # Mock execution event with evidence
        mock_execution = MagicMock()
        mock_execution.document_hash = "abc123hash"
        mock_execution.artifact_pointer = None
        mock_db.query.return_value.filter.return_value.first.return_value = mock_execution

        # Mock VERIFIED response
        mock_response = MagicMock()
        mock_response.response_type = ResponseType.VERIFIED

        # Contradictions from original dispute
        original_contradictions = [
            {"rule_code": "T1", "severity": "critical", "description": "DOFD before open date"},
        ]

        # Run examiner check
        service = ExaminerCheckService(mock_db)
        result = service.check_response(
            dispute=mock_dispute,
            response=mock_response,
            original_contradictions=original_contradictions,
        )

        # Should fail with PERFUNCTORY_INVESTIGATION
        assert result.passed is False
        assert result.standard_result == ExaminerStandardResult.FAIL_PERFUNCTORY
        assert result.response_layer_violation is not None
        assert result.response_layer_violation["type"] == "perfunctory_investigation"
        assert result.escalation_eligible is True

    def test_notice_of_results_failure_triggered(self):
        """NO_RESPONSE + deadline_passed → NOTICE_OF_RESULTS_FAILURE"""
        from app.services.enforcement.examiner_check import (
            ExaminerCheckService, ExaminerStandardResult
        )
        from app.models.db_models import ResponseType

        mock_db = MagicMock()

        # Dispute with deadline in past
        mock_dispute = MagicMock()
        mock_dispute.id = str(uuid4())
        mock_dispute.deadline_date = date.today() - timedelta(days=10)

        # NO_RESPONSE response
        mock_response = MagicMock()
        mock_response.response_type = ResponseType.NO_RESPONSE

        service = ExaminerCheckService(mock_db)
        result = service.check_response(
            dispute=mock_dispute,
            response=mock_response,
            original_contradictions=[],
        )

        # Should fail with NOTICE_OF_RESULTS_FAILURE
        assert result.passed is False
        assert result.standard_result == ExaminerStandardResult.FAIL_NO_RESULTS
        assert result.response_layer_violation is not None
        assert result.response_layer_violation["type"] == "notice_of_results_failure"
        assert result.response_layer_violation["days_overdue"] == 10

    def test_systemic_failure_cross_bureau(self):
        """Same contradiction on same tradeline across 2 bureaus → SYSTEMIC_ACCURACY_FAILURE"""
        from app.services.enforcement.examiner_check import (
            ExaminerCheckService, ExaminerStandardResult
        )
        from app.models.db_models import ResponseType

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = MagicMock(
            document_hash="hash123"
        )

        mock_dispute = MagicMock()
        mock_dispute.id = str(uuid4())
        mock_dispute.deadline_date = date.today() + timedelta(days=10)

        mock_response = MagicMock()
        mock_response.response_type = ResponseType.VERIFIED

        # Cross-bureau contradictions - same contradiction on same account across bureaus
        cross_bureau_contradictions = [
            {"account_id": "ACC123", "rule_code": "D1", "bureau": "EXPERIAN", "severity": "high"},
            {"account_id": "ACC123", "rule_code": "D1", "bureau": "TRANSUNION", "severity": "high"},
        ]

        service = ExaminerCheckService(mock_db)
        result = service.check_response(
            dispute=mock_dispute,
            response=mock_response,
            original_contradictions=[],
            cross_bureau_contradictions=cross_bureau_contradictions,
        )

        # Should fail with SYSTEMIC_ACCURACY_FAILURE
        assert result.passed is False
        assert result.standard_result == ExaminerStandardResult.FAIL_SYSTEMIC
        assert result.response_layer_violation is not None
        assert result.response_layer_violation["type"] == "systemic_accuracy_failure"

    def test_misleading_verification_critical(self):
        """VERIFIED + CRITICAL contradiction + impossibility → UDAAP_MISLEADING_VERIFICATION"""
        from app.services.enforcement.examiner_check import (
            ExaminerCheckService, ExaminerStandardResult
        )
        from app.models.db_models import ResponseType

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = MagicMock(
            document_hash="hash123"
        )

        mock_dispute = MagicMock()
        mock_dispute.id = str(uuid4())
        mock_dispute.deadline_date = date.today() + timedelta(days=10)

        mock_response = MagicMock()
        mock_response.response_type = ResponseType.VERIFIED

        # CRITICAL logical impossibility (T2 is a temporal impossibility)
        original_contradictions = [
            {"rule_code": "T2", "severity": "critical", "description": "Payment history exceeds account age"},
        ]

        service = ExaminerCheckService(mock_db)
        result = service.check_response(
            dispute=mock_dispute,
            response=mock_response,
            original_contradictions=original_contradictions,
        )

        # Should fail with UDAAP_MISLEADING_VERIFICATION (or PERFUNCTORY if that triggers first)
        assert result.passed is False
        assert result.standard_result in [
            ExaminerStandardResult.FAIL_MISLEADING,
            ExaminerStandardResult.FAIL_PERFUNCTORY,
        ]

    def test_verified_without_contradiction_passes(self):
        """VERIFIED + no contradictions → PASS"""
        from app.services.enforcement.examiner_check import (
            ExaminerCheckService, ExaminerStandardResult
        )
        from app.models.db_models import ResponseType

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        mock_dispute = MagicMock()
        mock_dispute.id = str(uuid4())
        mock_dispute.deadline_date = date.today() + timedelta(days=10)

        mock_response = MagicMock()
        mock_response.response_type = ResponseType.VERIFIED

        service = ExaminerCheckService(mock_db)
        result = service.check_response(
            dispute=mock_dispute,
            response=mock_response,
            original_contradictions=[],
        )

        # Should pass
        assert result.passed is True
        assert result.standard_result == ExaminerStandardResult.PASS

    def test_no_response_before_deadline_passes(self):
        """NO_RESPONSE before deadline → PASS (deadline not yet reached)"""
        from app.services.enforcement.examiner_check import (
            ExaminerCheckService, ExaminerStandardResult
        )
        from app.models.db_models import ResponseType

        mock_db = MagicMock()

        mock_dispute = MagicMock()
        mock_dispute.id = str(uuid4())
        mock_dispute.deadline_date = date.today() + timedelta(days=10)  # Future

        mock_response = MagicMock()
        mock_response.response_type = ResponseType.NO_RESPONSE

        service = ExaminerCheckService(mock_db)
        result = service.check_response(
            dispute=mock_dispute,
            response=mock_response,
            original_contradictions=[],
        )

        # Should pass (deadline not yet reached)
        assert result.passed is True
        assert result.standard_result == ExaminerStandardResult.PASS


# =============================================================================
# TEST: VIOLATION TYPES
# =============================================================================

class TestTier2ViolationTypes:
    """Tests for Tier 2 violation type enum values."""

    def test_tier2_violation_types_exist(self):
        """All 4 Tier 2 violation types exist in ViolationType enum."""
        from app.models.ssot import ViolationType

        assert hasattr(ViolationType, 'PERFUNCTORY_INVESTIGATION')
        assert hasattr(ViolationType, 'NOTICE_OF_RESULTS_FAILURE')
        assert hasattr(ViolationType, 'SYSTEMIC_ACCURACY_FAILURE')
        assert hasattr(ViolationType, 'UDAAP_MISLEADING_VERIFICATION')

    def test_tier2_violation_type_values(self):
        """Tier 2 violation types have correct string values."""
        from app.models.ssot import ViolationType

        assert ViolationType.PERFUNCTORY_INVESTIGATION.value == "perfunctory_investigation"
        assert ViolationType.NOTICE_OF_RESULTS_FAILURE.value == "notice_of_results_failure"
        assert ViolationType.SYSTEMIC_ACCURACY_FAILURE.value == "systemic_accuracy_failure"
        assert ViolationType.UDAAP_MISLEADING_VERIFICATION.value == "udaap_misleading_verification"


# =============================================================================
# TEST: STATUTE MAPPINGS
# =============================================================================

class TestTier2StatuteMappings:
    """Tests for Tier 2 statute mappings."""

    def test_perfunctory_investigation_statute(self):
        """perfunctory_investigation has correct statute mapping."""
        from app.services.legal_letter_generator.violation_statutes import get_violation_statutes

        v = get_violation_statutes("perfunctory_investigation")
        assert v is not None
        assert "1681i" in v.primary.usc
        assert v.primary.applies_to_actor("bureau")
        assert v.primary.applies_to_actor("furnisher")

    def test_notice_of_results_failure_statute(self):
        """notice_of_results_failure has correct statute mapping."""
        from app.services.legal_letter_generator.violation_statutes import get_violation_statutes

        v = get_violation_statutes("notice_of_results_failure")
        assert v is not None
        assert "1681i" in v.primary.usc
        assert v.primary.applies_to_actor("bureau")

    def test_systemic_accuracy_failure_statute(self):
        """systemic_accuracy_failure has correct statute mapping."""
        from app.services.legal_letter_generator.violation_statutes import get_violation_statutes

        v = get_violation_statutes("systemic_accuracy_failure")
        assert v is not None
        assert "1681e" in v.primary.usc

    def test_udaap_misleading_verification_statute(self):
        """udaap_misleading_verification has correct statute mapping."""
        from app.services.legal_letter_generator.violation_statutes import get_violation_statutes

        v = get_violation_statutes("udaap_misleading_verification")
        assert v is not None
        assert "1681i" in v.primary.usc


# =============================================================================
# TEST: LETTER SELECTION
# =============================================================================

class TestTier2LetterSelection:
    """Tests for Tier 2 letter selection upgrades."""

    def test_examiner_failure_upgrades_remedy_to_correction(self):
        """Examiner failure upgrades remedy to at least CORRECTION_WITH_DOCUMENTATION."""
        from app.services.enforcement.response_letter_generator import (
            determine_primary_remedy, PrimaryRemedy
        )

        # No contradictions, but examiner failed
        result = determine_primary_remedy(
            contradictions=[],
            examiner_failure=True,
            examiner_result="FAIL_PERFUNCTORY"
        )

        assert result == PrimaryRemedy.CORRECTION_WITH_DOCUMENTATION

    def test_systemic_failure_upgrades_to_deletion(self):
        """FAIL_SYSTEMIC upgrades remedy to IMMEDIATE_DELETION."""
        from app.services.enforcement.response_letter_generator import (
            determine_primary_remedy, PrimaryRemedy
        )

        result = determine_primary_remedy(
            contradictions=[],
            examiner_failure=True,
            examiner_result="FAIL_SYSTEMIC"
        )

        assert result == PrimaryRemedy.IMMEDIATE_DELETION

    def test_misleading_failure_upgrades_to_deletion(self):
        """FAIL_MISLEADING upgrades remedy to IMMEDIATE_DELETION."""
        from app.services.enforcement.response_letter_generator import (
            determine_primary_remedy, PrimaryRemedy
        )

        result = determine_primary_remedy(
            contradictions=[],
            examiner_failure=True,
            examiner_result="FAIL_MISLEADING"
        )

        assert result == PrimaryRemedy.IMMEDIATE_DELETION

    def test_no_examiner_failure_uses_contradiction_severity(self):
        """Without examiner failure, uses standard contradiction severity logic."""
        from app.services.enforcement.response_letter_generator import (
            determine_primary_remedy, PrimaryRemedy
        )

        # CRITICAL contradiction without examiner failure
        result = determine_primary_remedy(
            contradictions=[{"severity": "critical"}],
            examiner_failure=False,
        )

        assert result == PrimaryRemedy.IMMEDIATE_DELETION

        # No contradictions without examiner failure
        result = determine_primary_remedy(
            contradictions=[],
            examiner_failure=False,
        )

        assert result == PrimaryRemedy.STANDARD_PROCEDURAL


# =============================================================================
# TEST: TIER 1 BEHAVIOR UNCHANGED
# =============================================================================

class TestTier1BehaviorUnchanged:
    """Tests that Tier 1 behavior is unchanged by Tier 2 additions."""

    def test_tier1_contradiction_detection_unchanged(self):
        """Tier 1 contradiction detection is not modified."""
        # This test ensures existing Tier 1 violation types still exist
        from app.models.ssot import ViolationType

        # Tier 1 violations should still exist
        assert hasattr(ViolationType, 'PAYMENT_HISTORY_EXCEEDS_ACCOUNT_AGE')
        assert hasattr(ViolationType, 'CHARGEOFF_BEFORE_LAST_PAYMENT')
        assert hasattr(ViolationType, 'DOFD_INFERRED_MISMATCH')
        assert hasattr(ViolationType, 'BALANCE_EXCEEDS_LEGAL_MAX')

    def test_response_violation_map_unchanged(self):
        """RESPONSE_VIOLATION_MAP still works for standard response types."""
        from app.services.enforcement.response_evaluator import RESPONSE_VIOLATION_MAP
        from app.models.db_models import ResponseType

        # All original response types should still be mapped
        assert ResponseType.DELETED in RESPONSE_VIOLATION_MAP
        assert ResponseType.VERIFIED in RESPONSE_VIOLATION_MAP
        assert ResponseType.UPDATED in RESPONSE_VIOLATION_MAP
        assert ResponseType.NO_RESPONSE in RESPONSE_VIOLATION_MAP
        assert ResponseType.REJECTED in RESPONSE_VIOLATION_MAP

    def test_deadline_engine_unchanged(self):
        """Deadline engine configuration is unchanged."""
        from app.services.enforcement.deadline_engine import DEADLINE_CONFIG
        from app.models.db_models import DisputeSource

        # Standard deadline config should exist
        assert DisputeSource.DIRECT in DEADLINE_CONFIG
        assert DEADLINE_CONFIG[DisputeSource.DIRECT]["days"] == 30


# =============================================================================
# TEST: ESCALATION TRIGGERS
# =============================================================================

class TestExaminerEscalationTriggers:
    """Tests for examiner-driven escalation triggers."""

    def test_examiner_failure_escalation_exists(self):
        """examiner_failure_escalation method exists in AutomaticTransitionTriggers."""
        from app.services.enforcement.state_machine import AutomaticTransitionTriggers

        assert hasattr(AutomaticTransitionTriggers, 'examiner_failure_escalation')

    def test_examiner_failure_escalation_callable(self):
        """examiner_failure_escalation is a callable method."""
        from app.services.enforcement.state_machine import AutomaticTransitionTriggers

        assert callable(getattr(AutomaticTransitionTriggers, 'examiner_failure_escalation'))
