"""
Tests for the multi-statute citation system.

Tests FDCPA/FCRA parity, citation normalization, and actor-aware routing.
"""
import pytest
import warnings


class TestFDCPAStatutes:
    """Tests for fdcpa_statutes.py"""

    def test_resolve_fdcpa_statute_basic(self):
        from app.services.legal_letter_generator.fdcpa_statutes import resolve_fdcpa_statute

        # Test basic section resolution
        assert resolve_fdcpa_statute("1692e(5)") == "15 U.S.C. § 1692e(5)"
        assert resolve_fdcpa_statute("1692f(1)") == "15 U.S.C. § 1692f(1)"
        assert resolve_fdcpa_statute("1692e(2)(A)") == "15 U.S.C. § 1692e(2)(A)"

    def test_resolve_fdcpa_statute_with_prefix(self):
        from app.services.legal_letter_generator.fdcpa_statutes import resolve_fdcpa_statute

        # Test with FDCPA prefix
        assert resolve_fdcpa_statute("FDCPA 1692e(5)") == "15 U.S.C. § 1692e(5)"
        assert resolve_fdcpa_statute("FDCPA§1692f(1)") == "15 U.S.C. § 1692f(1)"

    def test_get_fdcpa_statute_details(self):
        from app.services.legal_letter_generator.fdcpa_statutes import get_fdcpa_statute_details

        details = get_fdcpa_statute_details("1692e(5)")
        assert details["usc"] == "15 U.S.C. § 1692e(5)"
        assert "threat" in details["title"].lower()

    def test_fdcpa_actor_scope(self):
        from app.services.legal_letter_generator.fdcpa_statutes import FDCPA_ACTOR_SCOPE

        assert "collector" in FDCPA_ACTOR_SCOPE["applies_to"]
        assert "original_creditor" in FDCPA_ACTOR_SCOPE["excludes"]
        assert "bureau" in FDCPA_ACTOR_SCOPE["excludes"]


class TestViolationStatutes:
    """Tests for violation_statutes.py"""

    def test_get_violation_statutes_fdcpa_primary(self):
        from app.services.legal_letter_generator.violation_statutes import get_violation_statutes

        v = get_violation_statutes("time_barred_debt_risk")
        assert v is not None
        assert v.primary.statute_type.value == "fdcpa"
        assert v.primary.usc == "15 U.S.C. § 1692e(5)"
        assert v.secondary is not None
        assert len(v.secondary) >= 1

    def test_get_violation_statutes_fcra_primary(self):
        from app.services.legal_letter_generator.violation_statutes import get_violation_statutes

        v = get_violation_statutes("obsolete_account")
        assert v is not None
        assert v.primary.statute_type.value == "fcra"
        assert "1681c" in v.primary.usc

    def test_actor_aware_routing(self):
        from app.services.legal_letter_generator.violation_statutes import get_primary_statute

        # FDCPA applies to collectors
        assert get_primary_statute("time_barred_debt_risk", "collector") == "15 U.S.C. § 1692e(5)"

        # FCRA applies to bureaus
        assert "1681" in get_primary_statute("obsolete_account", "bureau")

    def test_statute_citation_applies_to_actor(self):
        from app.services.legal_letter_generator.violation_statutes import get_violation_statutes

        v = get_violation_statutes("time_barred_debt_risk")
        assert v.primary.applies_to_actor("collector") is True
        assert v.primary.applies_to_actor("original_creditor") is False


class TestCitationUtils:
    """Tests for citation_utils.py"""

    def test_normalize_citation_fdcpa(self):
        from app.services.legal_letter_generator.citation_utils import normalize_citation

        assert normalize_citation("FDCPA 1692e(5)") == "15 U.S.C. § 1692e(5)"
        assert normalize_citation("1692f(1)") == "15 U.S.C. § 1692f(1)"

    def test_normalize_citation_fcra(self):
        from app.services.legal_letter_generator.citation_utils import normalize_citation

        assert normalize_citation("FCRA 611(a)") == "15 U.S.C. § 1681i(a)"
        assert normalize_citation("605(a)") == "15 U.S.C. § 1681c(a)"

    def test_normalize_citation_already_canonical(self):
        from app.services.legal_letter_generator.citation_utils import normalize_citation

        assert normalize_citation("15 U.S.C. § 1692e(5)") == "15 U.S.C. § 1692e(5)"

    def test_get_statute_name(self):
        from app.services.legal_letter_generator.citation_utils import get_statute_name

        assert get_statute_name("15 U.S.C. § 1692e(5)") == "Fair Debt Collection Practices Act"
        assert get_statute_name("15 U.S.C. § 1681i") == "Fair Credit Reporting Act"

    def test_get_statute_abbreviation(self):
        from app.services.legal_letter_generator.citation_utils import get_statute_abbreviation

        assert get_statute_abbreviation("15 U.S.C. § 1692e(5)") == "FDCPA"
        assert get_statute_abbreviation("15 U.S.C. § 1681i") == "FCRA"

    def test_is_fdcpa_citation(self):
        from app.services.legal_letter_generator.citation_utils import is_fdcpa_citation

        assert is_fdcpa_citation("15 U.S.C. § 1692e(5)") is True
        assert is_fdcpa_citation("15 U.S.C. § 1681i") is False

    def test_is_fcra_citation(self):
        from app.services.legal_letter_generator.citation_utils import is_fcra_citation

        assert is_fcra_citation("15 U.S.C. § 1681i") is True
        assert is_fcra_citation("15 U.S.C. § 1692e(5)") is False


class TestViolationModelBackwardCompat:
    """Tests for Violation model backward compatibility"""

    def test_new_style_violation(self):
        from app.models.ssot import Violation, ViolationType, Severity

        v = Violation(
            violation_type=ViolationType.TIME_BARRED_DEBT_RISK,
            severity=Severity.HIGH,
            primary_statute="15 U.S.C. § 1692e(5)",
            primary_statute_type="fdcpa",
            secondary_statutes=["15 U.S.C. § 1681s-2(a)(1)"]
        )
        assert v.primary_statute == "15 U.S.C. § 1692e(5)"
        assert v.primary_statute_type == "fdcpa"
        # fcra_section should be synced
        assert v.fcra_section == "15 U.S.C. § 1692e(5)"

    def test_legacy_style_violation_migration(self):
        from app.models.ssot import Violation, ViolationType, Severity

        v = Violation(
            violation_type=ViolationType.MISSING_DOFD,
            severity=Severity.MEDIUM,
            fcra_section="FDCPA 1692e(5)"  # Old non-canonical format
        )
        # Should normalize and migrate to new fields
        assert v.primary_statute == "15 U.S.C. § 1692e(5)"
        assert v.primary_statute_type == "fdcpa"

    def test_fcra_legacy_migration(self):
        from app.models.ssot import Violation, ViolationType, Severity

        v = Violation(
            violation_type=ViolationType.STALE_REPORTING,
            severity=Severity.MEDIUM,
            fcra_section="611(a)"  # Old FCRA format
        )
        assert v.primary_statute == "15 U.S.C. § 1681i(a)"
        assert v.primary_statute_type == "fcra"


class TestDiversityEngine:
    """Tests for diversity engine FDCPA support"""

    def test_get_fdcpa_citation(self):
        from app.services.legal_letter_generator.diversity import DiversityEngine

        engine = DiversityEngine(seed=42)
        citation = engine.get_fdcpa_citation("1692e(5)")
        # Should be one of the variants
        assert any(x in citation for x in ["1692e(5)", "prohibited threats"])

    def test_get_statute_citation_auto_detect(self):
        from app.services.legal_letter_generator.diversity import DiversityEngine

        engine = DiversityEngine(seed=42)

        # Should detect FDCPA from section number
        fdcpa_citation = engine.get_statute_citation("1692f(1)")
        assert any(x in fdcpa_citation for x in ["1692f(1)", "unauthorized amounts"])

        # Should detect FCRA from section number
        fcra_citation = engine.get_statute_citation("611(a)")
        assert any(x in fcra_citation for x in ["611", "1681i", "reinvestigation"])


class TestDeprecationWarnings:
    """Tests for deprecation warnings"""

    def test_get_violation_fcra_section_deprecated(self):
        from app.services.legal_letter_generator.grouping_strategies import get_violation_fcra_section

        with pytest.warns(DeprecationWarning):
            result = get_violation_fcra_section("time_barred_debt_risk")
        assert result is not None
