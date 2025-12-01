"""
SWEEP A — CORE FUNCTIONALITY & ROBUSTNESS TEST
Legal Letter Generator (4-tone system)

Purpose:
    Validate structural correctness, generator stability,
    and ensure all tones + grouping strategies work without errors.

Tests:
    - All tones (strict_legal, professional, soft_legal, aggressive)
    - All grouping strategies
    - Multiple violation combinations
    - Missing fields (metro2_field=None, fcra_section=None)
    - MOV inclusion
    - Section headers
    - Stability under 50+ violations
    - Formatting: spacing, bureau address
"""

import pytest
from app.services.legal_letter_generator import generate_legal_letter


# Utility to create dummy violations for sweep
def make_violation(
    v_id,
    v_type="balance_error",
    creditor="TEST BANK",
    acct="XXXX1234",
    metro2_field=None,
    fcra_section=None,
    evidence="Test evidence for violation",
):
    """Create a violation dict matching the generator's expected format."""
    return {
        "id": v_id,
        "violation_type": v_type,
        "creditor_name": creditor,
        "account_number_masked": acct,
        "metro2_field": metro2_field,
        "fcra_section": fcra_section or "611",
        "evidence": evidence,
    }


# ---- Sweep Configurations ---- #
TONES = ["strict_legal", "professional", "soft_legal", "aggressive"]
GROUPING_STRATEGIES = ["by_fcra_section", "by_metro2_field", "by_creditor", "by_severity"]
VIOLATION_TYPES = [
    "balance_error",
    "incorrect_payment_status",
    "wrong_account_status",
    "payment_history_error",
    "incorrect_dates",
]
BUREAUS = ["transunion", "experian", "equifax"]


# ---------------------------------------------------------------------------
# SWEEP A — TEST BLOCK 1: ALL TONES
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("tone", TONES)
def test_all_tones_basic_generation(tone):
    """Test that all 4 tones generate valid letters."""
    violations = [
        make_violation("1", "balance_error", "GM FINANCIAL"),
        make_violation("2", "incorrect_payment_status", "BMW FIN SVC"),
    ]

    result = generate_legal_letter(
        violations=violations,
        consumer={"name": "TEST USER", "address": "123 TEST ST, CITY, ST 00000"},
        bureau="transunion",
        tone=tone,
        seed=42,
        grouping_strategy="by_fcra_section",
    )

    # Basic sanity checks
    assert result is not None
    assert result["is_valid"] is True
    assert isinstance(result["letter"], str)
    assert len(result["letter"]) > 500, f"Letter too short for tone {tone}"
    assert "TransUnion" in result["letter"]
    # Check for verification-related content
    letter_upper = result["letter"].upper()
    assert any(term in letter_upper for term in ["VERIFICATION", "VERIFY", "REINVESTIGATION"])


# ---------------------------------------------------------------------------
# SWEEP A — TEST BLOCK 2: ALL GROUPING STRATEGIES
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("strategy", GROUPING_STRATEGIES)
def test_grouping_strategies(strategy):
    """Test that all grouping strategies work correctly."""
    violations = [
        make_violation("1", "balance_error", fcra_section="611"),
        make_violation("2", "balance_error", fcra_section="611"),
        make_violation("3", "incorrect_payment_status", fcra_section="623"),
        make_violation("4", "wrong_account_status", fcra_section="605"),
    ]

    result = generate_legal_letter(
        violations=violations,
        consumer={"name": "TEST USER", "address": "123 TEST ST"},
        bureau="transunion",
        tone="professional",
        seed=5,
        grouping_strategy=strategy,
    )

    assert result is not None
    assert result["is_valid"] is True
    assert len(result["letter"]) > 500

    # MOV must always exist
    letter_upper = result["letter"].upper()
    assert "METHOD OF VERIFICATION" in letter_upper or "MOV" in letter_upper


# ---------------------------------------------------------------------------
# SWEEP A — TEST BLOCK 3: ALL BUREAUS
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("bureau", BUREAUS)
def test_all_bureaus(bureau):
    """Test that all bureaus get correct addressing."""
    violations = [make_violation("1", "balance_error")]

    result = generate_legal_letter(
        violations=violations,
        consumer={"name": "BUREAU TEST", "address": "456 MAIN ST"},
        bureau=bureau,
        tone="professional",
        seed=99,
    )

    assert result is not None
    assert result["is_valid"] is True

    # Check bureau name appears in letter
    bureau_names = {
        "transunion": "TransUnion",
        "experian": "Experian",
        "equifax": "Equifax",
    }
    assert bureau_names[bureau] in result["letter"]


# ---------------------------------------------------------------------------
# SWEEP A — TEST BLOCK 4: MISSING FIELDS HANDLING
# ---------------------------------------------------------------------------
def test_missing_fields():
    """Test robustness when optional fields are missing."""
    violations = [
        make_violation(
            "1",
            "balance_error",
            metro2_field=None,
            fcra_section=None,
            evidence="Missing DOFD but no metro2 field",
        ),
        make_violation(
            "2",
            "incorrect_payment_status",
            metro2_field=None,
            fcra_section=None,
        ),
    ]

    result = generate_legal_letter(
        violations=violations,
        consumer={"name": "TEST USER", "address": "ADDR"},
        bureau="equifax",
        tone="professional",
        seed=12,
        grouping_strategy="by_fcra_section",
    )

    assert result is not None
    assert result["is_valid"] is True
    assert "Equifax" in result["letter"]


# ---------------------------------------------------------------------------
# SWEEP A — TEST BLOCK 5: LARGE VIOLATION LOAD (50+)
# ---------------------------------------------------------------------------
def test_large_violation_count():
    """Test stability with 50+ violations."""
    violations = [
        make_violation(
            str(i),
            v_type=VIOLATION_TYPES[i % len(VIOLATION_TYPES)],
            creditor=f"CREDITOR_{i}",
            acct=f"XXXX{i:04d}",
        )
        for i in range(1, 51)
    ]

    result = generate_legal_letter(
        violations=violations,
        consumer={"name": "LOAD TEST", "address": "BIG STREET"},
        bureau="experian",
        tone="professional",
        seed=999,
        grouping_strategy="by_creditor",
    )

    assert result is not None
    assert result["is_valid"] is True
    assert len(result["letter"]) > 2000, "Large letters should be long"
    assert "Experian" in result["letter"]


# ---------------------------------------------------------------------------
# SWEEP A — TEST BLOCK 6: SINGLE VIOLATION EDGE CASE
# ---------------------------------------------------------------------------
def test_single_violation():
    """Test that single violation still generates proper letter."""
    violations = [make_violation("1", "balance_error")]

    result = generate_legal_letter(
        violations=violations,
        consumer={"name": "SINGLE CASE", "address": "1 ROAD"},
        bureau="transunion",
        tone="professional",
        grouping_strategy="by_fcra_section",
        seed=3,
    )

    assert result is not None
    assert result["is_valid"] is True
    assert len(result["letter"]) > 300


# ---------------------------------------------------------------------------
# SWEEP A — TEST BLOCK 7: OUTPUT METADATA VALIDATION
# ---------------------------------------------------------------------------
def test_output_format_and_metadata():
    """Test that output contains expected metadata."""
    violations = [
        make_violation("1", "balance_error"),
        make_violation("2", "incorrect_payment_status"),
    ]

    result = generate_legal_letter(
        violations=violations,
        consumer={"name": "META TEST", "address": "META STREET"},
        bureau="transunion",
        tone="strict_legal",
        grouping_strategy="by_fcra_section",
        seed=44,
    )

    # Check metadata structure
    assert "metadata" in result
    assert "tone" in result["metadata"]
    assert result["metadata"]["tone"] == "strict_legal"
    assert "grouping_strategy" in result["metadata"]
    assert result["metadata"]["grouping_strategy"] == "by_fcra_section"
    assert "violation_count" in result["metadata"]
    assert result["metadata"]["violation_count"] == 2
    assert "bureau" in result["metadata"]
    assert result["metadata"]["bureau"] == "transunion"
    assert "generated_at" in result["metadata"]
    assert "seed" in result["metadata"]


# ---------------------------------------------------------------------------
# SWEEP A — TEST BLOCK 8: TONE-SPECIFIC CONTENT
# ---------------------------------------------------------------------------
def test_aggressive_tone_has_strong_language():
    """Test that aggressive tone includes demanding language."""
    violations = [make_violation("1", "balance_error")]

    result = generate_legal_letter(
        violations=violations,
        consumer={"name": "AGGRESSIVE TEST", "address": "123 ST"},
        bureau="transunion",
        tone="aggressive",
        seed=1,
    )

    assert result["is_valid"] is True
    letter_upper = result["letter"].upper()
    # Aggressive tone should have stronger language
    assert any(word in letter_upper for word in ["DEMAND", "IMMEDIATELY", "REQUIRED", "MUST"])


def test_soft_legal_tone_is_polite():
    """Test that soft_legal tone uses polite language."""
    violations = [make_violation("1", "balance_error")]

    result = generate_legal_letter(
        violations=violations,
        consumer={"name": "SOFT TEST", "address": "123 ST"},
        bureau="transunion",
        tone="soft_legal",
        seed=1,
    )

    assert result["is_valid"] is True
    letter_lower = result["letter"].lower()
    # Soft tone should have polite language
    assert any(word in letter_lower for word in ["please", "request", "appreciate"])


# ---------------------------------------------------------------------------
# SWEEP A — TEST BLOCK 9: DETERMINISTIC OUTPUT (SAME SEED = SAME OUTPUT)
# ---------------------------------------------------------------------------
def test_deterministic_output():
    """Test that same seed produces same output."""
    violations = [make_violation("1", "balance_error")]
    consumer = {"name": "SEED TEST", "address": "123 ST"}

    result1 = generate_legal_letter(
        violations=violations,
        consumer=consumer,
        bureau="transunion",
        tone="professional",
        seed=12345,
    )

    result2 = generate_legal_letter(
        violations=violations,
        consumer=consumer,
        bureau="transunion",
        tone="professional",
        seed=12345,
    )

    # Same seed should produce identical letters
    assert result1["letter"] == result2["letter"]


# ---------------------------------------------------------------------------
# SWEEP A — TEST BLOCK 10: ALL VIOLATION TYPES
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("v_type", VIOLATION_TYPES)
def test_all_violation_types(v_type):
    """Test that all violation types are handled."""
    violations = [make_violation("1", v_type)]

    result = generate_legal_letter(
        violations=violations,
        consumer={"name": "TYPE TEST", "address": "123 ST"},
        bureau="transunion",
        tone="professional",
        seed=1,
    )

    assert result is not None
    assert result["is_valid"] is True
    assert len(result["letter"]) > 300


# ---------------------------------------------------------------------------
# SWEEP A — TEST BLOCK 11: MIXED VIOLATION TYPES
# ---------------------------------------------------------------------------
def test_mixed_violation_types():
    """Test letter generation with all violation types combined."""
    violations = [
        make_violation(str(i), v_type, fcra_section=["611", "623", "605", "607"][i % 4])
        for i, v_type in enumerate(VIOLATION_TYPES)
    ]

    result = generate_legal_letter(
        violations=violations,
        consumer={"name": "MIXED TEST", "address": "123 ST"},
        bureau="experian",
        tone="strict_legal",
        seed=777,
        grouping_strategy="by_fcra_section",
    )

    assert result is not None
    assert result["is_valid"] is True
    assert len(result["letter"]) > 1000


# ---------------------------------------------------------------------------
# SWEEP A — TEST BLOCK 12: CONSUMER INFO IN LETTER
# ---------------------------------------------------------------------------
def test_consumer_info_appears_in_letter():
    """Test that consumer name and address appear in the letter."""
    violations = [make_violation("1", "balance_error")]

    result = generate_legal_letter(
        violations=violations,
        consumer={"name": "JOHN DOE TESTNAME", "address": "999 UNIQUE STREET"},
        bureau="transunion",
        tone="professional",
        seed=1,
    )

    assert result["is_valid"] is True
    assert "JOHN DOE TESTNAME" in result["letter"]
    assert "999 UNIQUE STREET" in result["letter"]


# ---------------------------------------------------------------------------
# SWEEP A — TEST BLOCK 13: CREDITOR NAME IN LETTER
# ---------------------------------------------------------------------------
def test_creditor_name_appears_in_letter():
    """Test that creditor names appear in the letter."""
    violations = [
        make_violation("1", "balance_error", creditor="UNIQUE_CREDITOR_ABC"),
        make_violation("2", "balance_error", creditor="ANOTHER_BANK_XYZ"),
    ]

    result = generate_legal_letter(
        violations=violations,
        consumer={"name": "TEST", "address": "ADDR"},
        bureau="transunion",
        tone="professional",
        seed=1,
    )

    assert result["is_valid"] is True
    assert "UNIQUE_CREDITOR_ABC" in result["letter"]
    assert "ANOTHER_BANK_XYZ" in result["letter"]


# ---------------------------------------------------------------------------
# SWEEP A — TEST BLOCK 14: VALIDATION ISSUES STRUCTURE
# ---------------------------------------------------------------------------
def test_validation_issues_structure():
    """Test that validation_issues is properly structured."""
    violations = [make_violation("1", "balance_error")]

    result = generate_legal_letter(
        violations=violations,
        consumer={"name": "VAL TEST", "address": "123 ST"},
        bureau="transunion",
        tone="professional",
        seed=1,
    )

    assert "validation_issues" in result
    assert isinstance(result["validation_issues"], list)

    # If there are issues, verify structure
    for issue in result["validation_issues"]:
        assert "level" in issue
        assert "message" in issue
        assert issue["level"] in ["error", "warning", "info"]
