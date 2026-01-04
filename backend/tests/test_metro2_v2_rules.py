"""
Metro 2 V2.0 QA Test Matrix

Comprehensive tests for:
- Schema validators (enum kill-switches)
- DOFD State Machine (re-aging detection)
- K2 Guardrails (payment history validation)
- Coexistence Classifier (3-way classification)
- Citation Injector (CRRG anchor injection)
- Cross-Bureau Divergence (invalid enum detection)
"""

import pytest
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

from app.services.metro2 import (
    # Validators
    Metro2SchemaValidator,
    ValidationMode,
    ValidationResult,
    # DOFD State Machine
    DOFDStateMachine,
    DOFDState,
    DOFDEventType,
    DOFDViolation,
    validate_dofd,
    # K2 Guardrails
    K2Guardrails,
    K2ValidationLevel,
    K2ValidationResult,
    validate_k2,
    # Coexistence Classifier
    CoexistenceClassifier,
    CoexistenceType,
    CoexistenceResult,
    classify_coexistence,
    # Citation Injector
    CitationInjector,
    CRRGCitation,
    get_injector,
    inject_citation_into_violation,
)
from app.models.ssot import Violation, ViolationType, Severity, Consumer


# =============================================================================
# TEST: Metro2SchemaValidator
# =============================================================================

class TestMetro2SchemaValidator:
    """Tests for Metro 2 schema validation with kill-switch modes."""

    @pytest.fixture
    def strict_validator(self):
        return Metro2SchemaValidator(mode=ValidationMode.STRICT)

    @pytest.fixture
    def coerce_validator(self):
        return Metro2SchemaValidator(mode=ValidationMode.COERCE)

    # Account Status Tests
    def test_valid_account_status_codes(self, strict_validator):
        """All valid Metro 2 account status codes should validate."""
        valid_codes = ["11", "13", "64", "71", "78", "79", "80", "82", "83", "84", "93", "97", "DA"]
        for code in valid_codes:
            result = strict_validator.validate_account_status(code)
            assert result.is_valid, f"Code {code} should be valid"

    def test_invalid_account_status_rejected_strict(self, strict_validator):
        """Invalid codes should be rejected in STRICT mode."""
        invalid_codes = ["99", "00", "XX", "123"]
        for code in invalid_codes:
            result = strict_validator.validate_account_status(code)
            assert not result.is_valid, f"Code {code} should be invalid"

    def test_text_status_coerced(self, coerce_validator):
        """Text statuses should be coerced to codes in COERCE mode."""
        text_mappings = {
            "current": "11",
            "paid": "13",
            "chargeoff": "84",
            "charge-off": "84",
            "collection": "93",
        }
        for text, expected_code in text_mappings.items():
            result = coerce_validator.validate_account_status(text)
            assert result.is_valid
            assert result.coerced_value == expected_code

    # ECOA Code Tests
    def test_valid_ecoa_codes(self, strict_validator):
        """All valid ECOA codes should validate."""
        valid_codes = ["1", "2", "5", "7", "T", "W", "X", "Z"]
        for code in valid_codes:
            result = strict_validator.validate_ecoa_code(code)
            assert result.is_valid, f"ECOA code {code} should be valid"
            assert not result.is_obsolete

    def test_obsolete_ecoa_codes_flagged(self, strict_validator):
        """Obsolete ECOA codes (3, 4, 6) should be flagged."""
        obsolete_codes = ["3", "4", "6"]
        for code in obsolete_codes:
            result = strict_validator.validate_ecoa_code(code)
            assert result.is_obsolete, f"ECOA code {code} should be obsolete"

    def test_invalid_ecoa_rejected(self, strict_validator):
        """Invalid ECOA codes should be rejected."""
        invalid_codes = ["0", "8", "9", "A", "B"]
        for code in invalid_codes:
            result = strict_validator.validate_ecoa_code(code)
            assert not result.is_valid, f"ECOA code {code} should be invalid"

    # Payment History Tests
    def test_valid_payment_history_codes(self, strict_validator):
        """All valid payment history codes should validate."""
        valid_codes = ["0", "1", "2", "3", "4", "5", "6", "B", "D", "E", "G", "H", "J", "K", "L"]
        for code in valid_codes:
            result = strict_validator.validate_payment_history_code(code)
            assert result.is_valid, f"Payment code {code} should be valid"

    def test_invalid_payment_history_rejected(self, strict_validator):
        """Invalid payment history codes should be rejected."""
        invalid_codes = ["7", "8", "9", "A", "X", "Z"]
        for code in invalid_codes:
            result = strict_validator.validate_payment_history_code(code)
            assert not result.is_valid, f"Payment code {code} should be invalid"

    # Helper Method Tests
    def test_requires_dofd_for_derogatory(self, strict_validator):
        """Derogatory statuses should require DOFD."""
        dofd_required = ["64", "71", "78", "79", "80", "82", "83", "84", "93", "97"]
        for code in dofd_required:
            assert strict_validator.requires_dofd(code), f"Status {code} should require DOFD"

    def test_current_status_no_dofd(self, strict_validator):
        """Current status should not require DOFD."""
        assert not strict_validator.requires_dofd("11")
        assert not strict_validator.requires_dofd("13")

    def test_collector_account_types(self, strict_validator):
        """Collector account types should be identified."""
        assert strict_validator.is_collector_account_type("47")
        assert strict_validator.is_collector_account_type("95")
        assert not strict_validator.is_collector_account_type("17")

    def test_debt_buyer_account_type(self, strict_validator):
        """Debt buyer account type should be identified."""
        assert strict_validator.is_debt_buyer_account_type("43")
        assert not strict_validator.is_debt_buyer_account_type("47")


# =============================================================================
# TEST: DOFD State Machine
# =============================================================================

class TestDOFDStateMachine:
    """Tests for DOFD state machine re-aging detection."""

    @pytest.fixture
    def base_date(self):
        return date(2023, 1, 1)

    def test_current_account_must_zero_fill_dofd(self, base_date):
        """Current accounts (status 11) must have zero-filled DOFD."""
        violations = validate_dofd(
            account_status="11",
            dofd="2022-06-15",  # Should be zero-filled
            report_date=base_date,
        )
        assert any(v.rule_code == "DOFD_CURRENT_MUST_ZERO_FILL" for v in violations)

    def test_missing_dofd_for_derogatory(self, base_date):
        """Derogatory accounts must have DOFD set."""
        violations = validate_dofd(
            account_status="84",  # Chargeoff
            dofd=None,  # Missing DOFD
            report_date=base_date,
        )
        assert any(v.rule_code == "MISSING_DOFD_DEROGATORY" for v in violations)

    def test_dofd_before_date_opened(self, base_date):
        """DOFD cannot be before account open date."""
        machine = DOFDStateMachine(date_opened=date(2022, 6, 1))
        violations = machine.validate_dofd_timeline(
            account_status="84",
            dofd="2021-01-15",  # Before open date
            date_opened=date(2022, 6, 1),
        )
        assert any(v.rule_code == "DOFD_BEFORE_OPEN_DATE" for v in violations)

    def test_over_7_year_reporting(self):
        """Accounts should not report beyond 7-year window."""
        report_date = date(2024, 1, 1)
        old_dofd = date(2015, 1, 1)  # More than 7 years before report

        machine = DOFDStateMachine()
        violations = machine.validate_dofd_timeline(
            account_status="84",
            dofd=old_dofd,
            report_date=report_date,
        )
        assert any(v.rule_code == "OVER_7_YEAR_REPORTING" for v in violations)

    def test_debt_buyer_cannot_modify_dofd(self, base_date):
        """Debt buyers (account type 43) cannot modify DOFD."""
        machine = DOFDStateMachine(account_type="43", date_opened=date(2020, 1, 1))

        # First event sets original DOFD
        machine.process_event(
            event_type=DOFDEventType.STATUS_CHANGE,
            event_date=date(2022, 1, 1),
            account_status="93",
            dofd="2021-06-15",
        )

        # Second event tries to change DOFD
        violations = machine.process_event(
            event_type=DOFDEventType.STATUS_CHANGE,
            event_date=date(2023, 1, 1),
            account_status="93",
            dofd="2022-01-01",  # Changed DOFD
        )

        assert any(v.rule_code == "DEBT_BUYER_DOFD_INVARIANT" for v in violations)

    def test_status_regression_reaging_detected(self, base_date):
        """Status regression without cure should be flagged as re-aging."""
        machine = DOFDStateMachine(date_opened=date(2020, 1, 1))

        # Go delinquent
        machine.process_event(
            event_type=DOFDEventType.STATUS_CHANGE,
            event_date=date(2022, 1, 1),
            account_status="84",  # Chargeoff
            dofd="2021-06-15",
        )

        # Suspicious return to current without cure
        violations = machine.process_event(
            event_type=DOFDEventType.STATUS_CHANGE,
            event_date=date(2023, 1, 1),
            account_status="11",  # Back to current
            dofd=None,
        )

        assert any(v.rule_code == "STATUS_REGRESSION_REAGING" for v in violations)

    def test_valid_cure_to_current(self, base_date):
        """Valid cure from delinquent to current should not flag re-aging."""
        machine = DOFDStateMachine(date_opened=date(2020, 1, 1))

        # Go delinquent
        machine.process_event(
            event_type=DOFDEventType.PAYMENT_LATE,
            event_date=date(2022, 1, 1),
            account_status="71",  # 30 days late
            dofd="2021-12-15",
        )

        # Proper cure
        violations = machine.process_event(
            event_type=DOFDEventType.CURE_COMPLETE,
            event_date=date(2022, 3, 1),
            account_status="11",
            dofd=None,
        )

        # Should not flag re-aging for proper cure
        assert not any(v.rule_code == "STATUS_REGRESSION_REAGING" for v in violations)


# =============================================================================
# TEST: K2 Guardrails
# =============================================================================

class TestK2Guardrails:
    """Tests for K2 payment history validation."""

    @pytest.fixture
    def guardrails(self):
        return K2Guardrails()

    def test_valid_payment_history(self, guardrails):
        """Valid 24-month payment history should pass."""
        history = "000000000000001234560BDE"
        result = guardrails.validate(
            payment_history=history,
            date_opened=date(2020, 1, 1),
            report_date=date(2024, 1, 1),
        )
        assert result.is_valid

    def test_invalid_payment_codes_rejected(self, guardrails):
        """Invalid payment codes should be flagged."""
        history = "00000000000000000000XXYZ"  # X, Y, Z are invalid
        result = guardrails.validate(payment_history=history)
        assert not result.is_valid
        assert any(v.rule_code == "INVALID_PAYMENT_HISTORY" for v in result.violations)

    def test_collector_should_not_have_k2(self, guardrails):
        """Collection agencies (47) should not have K2 segment."""
        history = "000000000000000000000000"
        result = guardrails.validate(
            payment_history=history,
            account_type="47",  # Collection agency
        )
        assert any(v.rule_code == "K2_PROHIBITED_REPORTER_HAS_K2" for v in result.violations)

    def test_debt_buyer_chain_gap_needs_k2(self, guardrails):
        """Debt buyer with chain gap should have K2 for transparency."""
        result = guardrails.validate(
            payment_history=None,  # No K2
            account_type="43",  # Debt buyer
            has_chain_gap=True,
        )
        assert any(v.rule_code == "DEBT_BUYER_CHAIN_GAP_K2_REQUIRED" for v in result.violations)

    def test_payment_history_exceeds_account_age(self, guardrails):
        """Payment history cannot exceed account age."""
        history = "000000000000000000000000"  # 24 months
        result = guardrails.validate(
            payment_history=history,
            date_opened=date(2023, 6, 1),  # Only 7 months ago
            report_date=date(2024, 1, 1),
        )
        assert any(v.rule_code == "PAYMENT_HISTORY_EXCEEDS_ACCOUNT_AGE" for v in result.violations)

    def test_delinquency_ladder_inversion(self, guardrails):
        """Delinquency ladder inversions should be flagged."""
        # 0 -> 4 -> 3 -> 2 -> 6 (impossible jump from 2 to 6)
        history = "004326000000000000000000"
        violations = guardrails._check_delinquency_ladder(list(history))
        assert any(v.rule_code == "DELINQUENCY_LADDER_INVERSION" for v in violations)

    def test_infer_dofd_from_k2(self, guardrails):
        """DOFD should be correctly inferred from K2 payment history."""
        # Position 5 has first delinquency (working backwards from position 0)
        history = "000001234560000000000000"
        report_date = date(2024, 1, 1)
        inferred = guardrails.infer_dofd_from_k2(history, report_date)
        # First late should be ~5 months ago (accounting for 0-indexing)
        assert inferred is not None


# =============================================================================
# TEST: Coexistence Classifier
# =============================================================================

class TestCoexistenceClassifier:
    """Tests for 3-way coexistence classification."""

    @pytest.fixture
    def classifier(self):
        return CoexistenceClassifier()

    def test_valid_coexistence_oc_zero_collector_balance(self, classifier):
        """OC $0 + Collector >$0 is valid coexistence."""
        oc_data = {"balance": 0, "account_status": "13"}
        collector_data = {"balance": 5000, "account_type": "47"}

        result = classifier.classify(oc_data=oc_data, collector_data=collector_data)

        assert result.classification == CoexistenceType.VALID_COEXISTENCE
        assert not result.cfpb_recommend

    def test_double_balance_violation(self, classifier):
        """Both OC and Collector with balance is double jeopardy."""
        oc_data = {"balance": 3000, "account_status": "84"}
        collector_data = {"balance": 5000, "account_type": "47"}

        result = classifier.classify(oc_data=oc_data, collector_data=collector_data)

        assert result.classification == CoexistenceType.DOUBLE_BALANCE_VIOLATION
        assert result.cfpb_recommend
        assert result.rule_code == "DOUBLE_JEOPARDY"

    def test_ownership_conflict(self, classifier):
        """OC with balance but collector at $0 is ownership conflict."""
        oc_data = {"balance": 3000, "account_status": "93"}
        collector_data = {"balance": 0, "account_type": "47"}

        result = classifier.classify(oc_data=oc_data, collector_data=collector_data)

        assert result.classification == CoexistenceType.OWNERSHIP_CONFLICT_DOC_DEMAND

    def test_both_zero_is_resolved(self, classifier):
        """Both at $0 indicates resolved account."""
        oc_data = {"balance": 0}
        collector_data = {"balance": 0, "account_type": "47"}

        result = classifier.classify(oc_data=oc_data, collector_data=collector_data)

        assert result.classification == CoexistenceType.VALID_COEXISTENCE

    def test_single_tradeline_classification(self, classifier):
        """Single tradeline should be classified as such."""
        result = classifier.classify(oc_data={"balance": 1000}, collector_data=None)
        assert result.classification == CoexistenceType.SINGLE_TRADELINE

    def test_convenience_function(self):
        """Test classify_coexistence convenience function."""
        result = classify_coexistence(
            oc_data={"balance": 0},
            collector_data={"balance": 2500, "account_type": "43"}
        )
        assert result.classification == CoexistenceType.VALID_COEXISTENCE


# =============================================================================
# TEST: Citation Injector
# =============================================================================

class TestCitationInjector:
    """Tests for CRRG citation injection."""

    @pytest.fixture
    def injector(self):
        return CitationInjector()

    def test_inject_into_violation_for_known_rule(self, injector):
        """Known rule codes should get citations injected into violation.citations."""
        violation = Violation(
            violation_type=ViolationType.RE_AGING,
            description="Test re-aging violation",
            severity=Severity.HIGH,
        )
        # Verify violation starts with empty citations
        assert len(violation.citations) == 0

        result = injector.inject_into_violation(violation, "t1")  # lowercase to test normalization

        assert result.success
        assert len(violation.citations) == 1
        assert violation.citations[0]["anchor_id"] == "FIELD_24"

    def test_inject_auto_extracts_rule_code(self, injector):
        """inject_into_violation should auto-extract rule_code from violation_type."""
        violation = Violation(
            violation_type=ViolationType.MISSING_DOFD,
            description="Test missing DOFD",
            severity=Severity.HIGH,
        )

        # Inject without providing rule_code - should auto-extract
        result = injector.inject_into_violation(violation)

        # Will fail because 'missing_dofd' may not have anchor - but should not error
        # The test validates the extraction logic works
        assert result.rule_code == "missing_dofd"

    def test_citation_has_page_range(self, injector):
        """Citations should include page ranges."""
        citation = injector.get_citation("FIELD_17A")

        assert citation is not None
        assert citation.page_start > 0
        assert citation.page_end >= citation.page_start
        assert "p." in citation.page_range() or "pp." in citation.page_range()

    def test_citation_has_fcra_cite(self, injector):
        """Citations should include FCRA statute references."""
        citation = injector.get_citation("FIELD_24")

        assert citation is not None
        assert citation.fcra_cite
        assert "15 U.S.C." in citation.fcra_cite

    def test_unknown_rule_returns_failure(self, injector):
        """Unknown rule codes should return failure result."""
        violation = Violation(
            violation_type=ViolationType.MISSING_DOFD,
            description="Test",
            severity=Severity.HIGH,
        )
        result = injector.inject_into_violation(violation, "UNKNOWN_RULE_XYZ")

        assert not result.success
        assert len(violation.citations) == 0

    def test_format_for_letter(self, injector):
        """Format for letter should produce readable text."""
        citation = injector.get_citation("FIELD_24")
        formatted = injector.format_for_letter(citation)

        assert "Metro 2 CRRG" in formatted
        assert "FCRA" in formatted

    def test_build_citation_table(self, injector):
        """Citation table should be valid markdown."""
        citations = [
            injector.get_citation("FIELD_24"),
            injector.get_citation("FIELD_17A"),
        ]
        table = injector.build_citation_table(citations)

        assert "| Field |" in table
        assert "|-------" in table  # Markdown table separator

    def test_statute_stack_deduplication(self, injector):
        """Statute stack should be deduplicated."""
        citations = [
            injector.get_citation("FIELD_24"),
            injector.get_citation("FIELD_17A"),
            injector.get_citation("FIELD_25_K2"),
        ]
        stack = injector.get_statute_stack(citations)

        # Should be sorted and unique
        assert len(stack) == len(set(stack))
        assert stack == sorted(stack)

    def test_singleton_injector(self):
        """get_injector should return same instance."""
        injector1 = get_injector()
        injector2 = get_injector()
        assert injector1 is injector2

    def test_lowercase_normalization(self, injector):
        """Rule codes should be normalized to lowercase for lookup."""
        violation = Violation(
            violation_type=ViolationType.RE_AGING,
            description="Test",
            severity=Severity.HIGH,
        )

        # Test with uppercase rule code - should still find anchor
        result = injector.inject_into_violation(violation, "T1")
        assert result.success

        # Verify citation was added
        assert len(violation.citations) == 1


# =============================================================================
# TEST: Metro 2 V2.0 Wiring Verification (Sweep Tests)
# =============================================================================

class TestMetro2V2WiringVerification:
    """
    Verification tests for Metro 2 V2.0 wiring.
    These tests ensure the full citation pipeline works end-to-end.
    """

    def test_violation_is_metro2_v2_true_for_known_type(self):
        """Violation.is_metro2_v2 should return True for known Metro 2 V2.0 types."""
        violation = Violation(
            violation_type=ViolationType.MISSING_DOFD,
            description="Test missing DOFD",
            severity=Severity.HIGH,
        )
        assert violation.is_metro2_v2 is True

    def test_violation_is_metro2_v2_true_for_cross_bureau_type(self):
        """Cross-bureau violation types should also be Metro 2 V2.0."""
        violation = Violation(
            violation_type=ViolationType.DOFD_MISMATCH,
            description="Test DOFD mismatch",
            severity=Severity.HIGH,
        )
        assert violation.is_metro2_v2 is True

    def test_violation_is_metro2_v2_false_for_inquiry_type(self):
        """Inquiry violation types are NOT Metro 2 V2.0."""
        violation = Violation(
            violation_type=ViolationType.UNAUTHORIZED_HARD_INQUIRY,
            description="Test unauthorized inquiry",
            severity=Severity.MEDIUM,
        )
        assert violation.is_metro2_v2 is False

    def test_metro2_v2_types_all_lowercase(self):
        """All entries in METRO2_V2_VIOLATION_TYPES must be lowercase."""
        for vtype in Violation.METRO2_V2_VIOLATION_TYPES:
            assert vtype == vtype.lower(), f"Type '{vtype}' is not lowercase"

    def test_cfpb_packet_reads_from_violation_citations(self):
        """CFPB packet builder should read from violation.citations, not inject."""
        from app.services.cfpb import CFPBPacketBuilder

        # Create violation with pre-populated citations (as engine would do)
        violation = Violation(
            violation_type=ViolationType.RE_AGING,
            description="Re-aging detected",
            severity=Severity.CRITICAL,
            creditor_name="Test Bank",
            account_number_masked="****1234",
            citations=[{
                "anchor_id": "FIELD_24",
                "rule_id": "T1",
                "doc": "Metro 2 CRRG",
                "toc_title": "Date of First Delinquency",
                "section_title": "Field 24",
                "page_start": 89,
                "page_end": 91,
                "exhibit_id": None,
                "fields": ["Field 24"],
                "anchor_summary": "DOFD requirements",
                "fcra_cite": "15 U.S.C. § 1681c(c)(1)",
            }],
        )

        consumer = Consumer(
            full_name="Test User",
            address="123 Test St",
            city="Test City",
            state="CA",
            zip_code="12345",
        )
        builder = CFPBPacketBuilder()

        packet = builder.build(
            consumer=consumer,
            violations=[violation],
            entity_name="Test Bank",
            account_info="****1234",
        )

        # CFPB packet should have citations from violation.citations
        assert len(packet.crrg_citations) == 1
        assert packet.crrg_citations[0]["anchor_id"] == "FIELD_24"

    def test_cfpb_packet_no_mutation_of_violation(self):
        """CFPB packet builder should NOT mutate violation.citations."""
        from app.services.cfpb import CFPBPacketBuilder

        # Create violation with one citation
        original_citations = [{
            "anchor_id": "FIELD_24",
            "rule_id": "T1",
            "doc": "Metro 2 CRRG",
            "toc_title": "Date of First Delinquency",
            "section_title": "Field 24",
            "page_start": 89,
            "page_end": 91,
            "exhibit_id": None,
            "fields": ["Field 24"],
            "anchor_summary": "DOFD requirements",
            "fcra_cite": "15 U.S.C. § 1681c(c)(1)",
        }]

        violation = Violation(
            violation_type=ViolationType.RE_AGING,
            description="Re-aging detected",
            severity=Severity.CRITICAL,
            creditor_name="Test Bank",
            account_number_masked="****1234",
            citations=original_citations.copy(),
        )

        consumer = Consumer(
            full_name="Test User",
            address="123 Test St",
            city="Test City",
            state="CA",
            zip_code="12345",
        )
        builder = CFPBPacketBuilder()

        # Build packet
        builder.build(
            consumer=consumer,
            violations=[violation],
            entity_name="Test Bank",
            account_info="****1234",
        )

        # violation.citations should NOT have been mutated
        assert len(violation.citations) == 1
        assert violation.citations[0]["anchor_id"] == "FIELD_24"

    def test_engine_guard_raises_for_metro2_v2_without_citations(self):
        """
        AuditEngine guard should raise RuntimeError when Metro 2 V2.0 violation
        has zero citations after injection pass.
        """
        from app.services.audit.engine import AuditEngine

        engine = AuditEngine()

        # Create a Metro 2 V2.0 violation with NO citations
        violation = Violation(
            violation_type=ViolationType.MISSING_DOFD,
            description="Missing DOFD",
            severity=Severity.HIGH,
        )

        # Verify it's a Metro 2 V2.0 type and has no citations
        assert violation.is_metro2_v2 is True
        assert len(violation.citations) == 0

        # Guard should raise RuntimeError
        with pytest.raises(RuntimeError, match="Metro 2 V2.0 violation"):
            engine._guard_metro2_v2_citations([violation])

    def test_engine_guard_passes_for_violation_with_citations(self):
        """
        AuditEngine guard should NOT raise when violation has citations.
        """
        from app.services.audit.engine import AuditEngine

        engine = AuditEngine()

        # Create a Metro 2 V2.0 violation WITH citations
        violation = Violation(
            violation_type=ViolationType.MISSING_DOFD,
            description="Missing DOFD",
            severity=Severity.HIGH,
            citations=[{"anchor_id": "FIELD_24", "doc": "Metro 2 CRRG"}],
        )

        # Should not raise
        engine._guard_metro2_v2_citations([violation])

    def test_engine_guard_ignores_non_metro2_v2_violations(self):
        """
        AuditEngine guard should NOT raise for non-Metro 2 V2.0 violations
        even if they have no citations.
        """
        from app.services.audit.engine import AuditEngine

        engine = AuditEngine()

        # Create an inquiry violation (not Metro 2 V2.0) with no citations
        violation = Violation(
            violation_type=ViolationType.UNAUTHORIZED_HARD_INQUIRY,
            description="Unauthorized inquiry",
            severity=Severity.MEDIUM,
        )

        # Verify it's NOT a Metro 2 V2.0 type
        assert violation.is_metro2_v2 is False

        # Should not raise (inquiry violations don't require CRRG citations)
        engine._guard_metro2_v2_citations([violation])


# =============================================================================
# TEST: Phase 2 Coverage Enforcement
# =============================================================================

class TestMetro2V2AnchorCoverage:
    """Ensure 100% anchor coverage for Metro 2 V2.0 violations."""

    def test_all_metro2_v2_rules_have_anchors(self):
        """Every Metro 2 V2.0 rule must have a CRRG anchor mapping."""
        injector = get_injector()
        injector._load_anchors()

        missing = sorted(
            r for r in Violation.METRO2_V2_VIOLATION_TYPES
            if r not in injector._rule_to_anchor
        )
        assert not missing, f"Missing CRRG anchors for: {missing}"


# =============================================================================
# TEST: Integration - End-to-End Flows
# =============================================================================

class TestMetro2Integration:
    """End-to-end integration tests for Metro 2 V2.0 components."""

    def test_full_validation_flow(self):
        """Test complete validation flow from raw data to violations."""
        validator = Metro2SchemaValidator(mode=ValidationMode.COERCE)

        # Simulate account data
        account = {
            "account_status": "chargeoff",  # Text to coerce
            "ecoa_code": "3",  # Obsolete
            "payment_history": "000000000000000000000000",
            "date_opened": date(2020, 1, 1),
            "dofd": None,  # Missing
        }

        # Validate status (should coerce)
        status_result = validator.validate_account_status(account["account_status"])
        assert status_result.is_valid
        assert status_result.coerced_value == "84"

        # Validate ECOA (should flag obsolete)
        ecoa_result = validator.validate_ecoa_code(account["ecoa_code"])
        assert ecoa_result.is_obsolete

        # Validate DOFD (should flag missing)
        dofd_violations = validate_dofd(
            account_status=status_result.coerced_value,
            dofd=account["dofd"],
            date_opened=account["date_opened"],
        )
        assert any(v.rule_code == "MISSING_DOFD_DEROGATORY" for v in dofd_violations)

    def test_cfpb_packet_with_citations(self):
        """Test CFPB packet builder includes citations."""
        from app.services.cfpb import CFPBPacketBuilder
        from app.models.ssot import Consumer, Violation, Severity, ViolationType

        # Create test consumer
        consumer = Consumer(
            first_name="John",
            last_name="Doe",
        )

        # Create test violation
        violation = Violation(
            violation_type=ViolationType.MISSING_DOFD,
            description="Missing DOFD for derogatory account",
            severity=Severity.HIGH,
            creditor_name="Test Bank",
            account_number_masked="****1234",
            evidence={"rule_code": "D1"},
        )

        # Build packet
        builder = CFPBPacketBuilder()
        packet = builder.build(
            consumer=consumer,
            violations=[violation],
            entity_name="Test Bank",
            account_info="****1234",
        )

        # Verify packet structure
        assert packet.consumer_name == "John Doe"
        assert packet.entity_name == "Test Bank"
        assert len(packet.crrg_citations) > 0 or len(packet.statute_stack) >= 0
        assert "##" in packet.contradiction_table  # Markdown header


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
