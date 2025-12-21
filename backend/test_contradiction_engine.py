"""
Test script for Phase-1 Contradiction Engine
Run: cd backend && python test_contradiction_engine.py
"""
import sys
sys.path.insert(0, '.')

from datetime import date, timedelta
from app.services.audit.contradiction_engine import detect_contradictions, ContradictionEngine


def test_t1_open_date_vs_dofd():
    """T1: DOFD cannot be before account opened."""
    print("\n=== T1: Open Date vs DOFD ===")

    # Should trigger T1: DOFD before open date
    account = {
        "account_id": "TEST-001",
        "creditor_name": "Test Creditor",
        "open_date": "2023-01-15",
        "dofd": "2022-06-01",  # Before open_date - IMPOSSIBLE
    }

    contradictions = detect_contradictions(account)
    t1_found = any(c.rule_code == "T1" for c in contradictions)
    print(f"  Account opened 01/2023, DOFD 06/2022")
    print(f"  T1 detected: {t1_found} (expected: True)")

    if t1_found:
        c = next(c for c in contradictions if c.rule_code == "T1")
        print(f"  Severity: {c.severity}")
        print(f"  Bureau claim: {c.bureau_claim}")
        print(f"  Contradiction: {c.contradiction}")

    return t1_found


def test_t2_payment_history_vs_age():
    """T2: Payment history cannot exceed account age."""
    print("\n=== T2: Payment History vs Account Age ===")

    # Account is 6 months old but has 24 months of history
    account = {
        "account_id": "TEST-002",
        "creditor_name": "Test Creditor",
        "open_date": date.today() - timedelta(days=180),  # 6 months ago
        "payment_history_months": 24,  # 24 months - IMPOSSIBLE
        "report_date": date.today(),
    }

    contradictions = detect_contradictions(account)
    t2_found = any(c.rule_code == "T2" for c in contradictions)
    print(f"  Account 6 months old, payment history spans 24 months")
    print(f"  T2 detected: {t2_found} (expected: True)")

    if t2_found:
        c = next(c for c in contradictions if c.rule_code == "T2")
        print(f"  Evidence: {c.evidence}")

    return t2_found


def test_t3_chargeoff_before_last_payment():
    """T3: Cannot charge off before last payment."""
    print("\n=== T3: Charge-Off Before Last Payment ===")

    account = {
        "account_id": "TEST-003",
        "creditor_name": "Test Creditor",
        "chargeoff_date": "2023-03-01",
        "last_payment_date": "2023-06-15",  # Payment AFTER chargeoff - IMPOSSIBLE
    }

    contradictions = detect_contradictions(account)
    t3_found = any(c.rule_code == "T3" for c in contradictions)
    print(f"  Charged off 03/2023, last payment 06/2023")
    print(f"  T3 detected: {t3_found} (expected: True)")

    if t3_found:
        c = next(c for c in contradictions if c.rule_code == "T3")
        print(f"  Days impossible: {c.evidence.get('days_impossible')}")

    return t3_found


def test_t4_delinquency_ladder_inversion():
    """T4: Delinquency must progress 30->60->90."""
    print("\n=== T4: Delinquency Ladder Inversion ===")

    # Payment history jumps from current to 90 days late
    account = {
        "account_id": "TEST-004",
        "creditor_name": "Test Creditor",
        "payment_history": [
            {"status": "C", "month": "01", "year": "2023"},
            {"status": "C", "month": "02", "year": "2023"},
            {"status": "90", "month": "03", "year": "2023"},  # Jumped to 90 - IMPOSSIBLE
        ],
    }

    contradictions = detect_contradictions(account)
    t4_found = any(c.rule_code == "T4" for c in contradictions)
    print(f"  Payment history: Current -> Current -> 90 days late")
    print(f"  T4 detected: {t4_found} (expected: True)")

    if t4_found:
        c = next(c for c in contradictions if c.rule_code == "T4")
        print(f"  Skipped levels: {c.evidence.get('skipped_levels')}")

    return t4_found


def test_d1_missing_dofd_negative_status():
    """D1: Negative accounts must have DOFD."""
    print("\n=== D1: Missing DOFD with Negative Status ===")

    account = {
        "account_id": "TEST-005",
        "creditor_name": "Test Creditor",
        "status": "Collection",
        "dofd": None,  # Missing - VIOLATION
    }

    contradictions = detect_contradictions(account)
    d1_found = any(c.rule_code == "D1" for c in contradictions)
    print(f"  Status: Collection, DOFD: None")
    print(f"  D1 detected: {d1_found} (expected: True)")

    return d1_found


def test_d2_dofd_vs_inferred():
    """D2: DOFD must match first late payment."""
    print("\n=== D2: DOFD vs Inferred First Late ===")

    account = {
        "account_id": "TEST-006",
        "creditor_name": "Test Creditor",
        "dofd": "2023-06-01",  # Reported DOFD
        "payment_history": [
            {"status": "C", "month": 1, "year": 2023},
            {"status": "30", "month": 2, "year": 2023},  # First late = 02/2023
            {"status": "60", "month": 3, "year": 2023},
        ],
    }

    contradictions = detect_contradictions(account)
    d2_found = any(c.rule_code == "D2" for c in contradictions)
    print(f"  Reported DOFD: 06/2023, First late in history: 02/2023")
    print(f"  D2 detected: {d2_found} (expected: True)")

    if d2_found:
        c = next(c for c in contradictions if c.rule_code == "D2")
        print(f"  Months difference: {c.evidence.get('months_difference')}")

    return d2_found


def test_d3_over_seven_years():
    """D3: Cannot report beyond 7 years from DOFD."""
    print("\n=== D3: Over-Reporting Beyond 7 Years ===")

    # DOFD is 8 years ago
    dofd = date.today() - timedelta(days=365 * 8)

    account = {
        "account_id": "TEST-007",
        "creditor_name": "Test Creditor",
        "dofd": dofd,
        "report_date": date.today(),
    }

    contradictions = detect_contradictions(account)
    d3_found = any(c.rule_code == "D3" for c in contradictions)
    print(f"  DOFD: {dofd}, Report date: {date.today()}")
    print(f"  D3 detected: {d3_found} (expected: True)")

    if d3_found:
        c = next(c for c in contradictions if c.rule_code == "D3")
        print(f"  Years since DOFD: {c.evidence.get('years_since_dofd')}")

    return d3_found


def test_m1_balance_exceeds_legal_max():
    """M1: Balance cannot exceed maximum with interest."""
    print("\n=== M1: Balance Exceeds Legal Maximum ===")

    # Original balance $1000, now showing $50,000 after 2 years - IMPOSSIBLE
    account = {
        "account_id": "TEST-008",
        "creditor_name": "Test Creditor",
        "open_date": date.today() - timedelta(days=730),  # 2 years ago
        "original_balance": 1000,
        "reported_balance": 50000,  # 50x original - IMPOSSIBLE
        "report_date": date.today(),
    }

    contradictions = detect_contradictions(account)
    m1_found = any(c.rule_code == "M1" for c in contradictions)
    print(f"  Original: $1,000, Reported: $50,000 after 2 years")
    print(f"  M1 detected: {m1_found} (expected: True)")

    if m1_found:
        c = next(c for c in contradictions if c.rule_code == "M1")
        print(f"  Max legal balance: ${c.evidence.get('max_legal_balance'):,.2f}")
        print(f"  Excess amount: ${c.evidence.get('excess_amount'):,.2f}")

    return m1_found


def test_m2_balance_increase_after_chargeoff():
    """M2: Balance cannot increase after chargeoff."""
    print("\n=== M2: Balance Increase After Charge-Off ===")

    account = {
        "account_id": "TEST-009",
        "creditor_name": "Test Creditor",
        "status": "Chargeoff",
        "chargeoff_balance": 5000,
        "reported_balance": 8000,  # 60% increase after chargeoff - IMPOSSIBLE
    }

    contradictions = detect_contradictions(account)
    m2_found = any(c.rule_code == "M2" for c in contradictions)
    print(f"  Chargeoff balance: $5,000, Current: $8,000")
    print(f"  M2 detected: {m2_found} (expected: True)")

    if m2_found:
        c = next(c for c in contradictions if c.rule_code == "M2")
        print(f"  Increase percentage: {c.evidence.get('increase_percentage')}%")

    return m2_found


def test_s1_paid_status_with_delinquencies():
    """S1: Paid status should not have late payments."""
    print("\n=== S1: Paid Status with Delinquencies ===")

    account = {
        "account_id": "TEST-010",
        "creditor_name": "Test Creditor",
        "status": "Paid",
        "payment_history": [
            {"status": "C", "month": 1, "year": 2023},
            {"status": "30", "month": 2, "year": 2023},  # Late
            {"status": "60", "month": 3, "year": 2023},  # Late
            {"status": "C", "month": 4, "year": 2023},
        ],
    }

    contradictions = detect_contradictions(account)
    s1_found = any(c.rule_code == "S1" for c in contradictions)
    print(f"  Status: Paid, but 2 late payments in history")
    print(f"  S1 detected: {s1_found} (expected: True)")

    if s1_found:
        c = next(c for c in contradictions if c.rule_code == "S1")
        print(f"  Late payment count: {c.evidence.get('late_payment_count')}")

    return s1_found


def test_s2_closed_account_with_activity():
    """S2: No activity after account closed."""
    print("\n=== S2: Closed Account with Activity ===")

    account = {
        "account_id": "TEST-011",
        "creditor_name": "Test Creditor",
        "date_closed": "2023-01-15",
        "date_last_activity": "2023-06-01",  # Activity after close - CONTRADICTION
    }

    contradictions = detect_contradictions(account)
    s2_found = any(c.rule_code == "S2" for c in contradictions)
    print(f"  Closed: 01/2023, Last activity: 06/2023")
    print(f"  S2 detected: {s2_found} (expected: True)")

    if s2_found:
        c = next(c for c in contradictions if c.rule_code == "S2")
        print(f"  Days after close: {c.evidence.get('days_after_close')}")

    return s2_found


def test_no_contradictions_clean_account():
    """Verify clean accounts return no contradictions."""
    print("\n=== Clean Account (No Contradictions Expected) ===")

    account = {
        "account_id": "CLEAN-001",
        "creditor_name": "Good Creditor",
        "open_date": "2020-01-01",
        "status": "Current",
        "reported_balance": 500,
        "original_balance": 1000,
        "payment_history": [
            {"status": "C", "month": 1, "year": 2024},
            {"status": "C", "month": 2, "year": 2024},
            {"status": "C", "month": 3, "year": 2024},
        ],
    }

    contradictions = detect_contradictions(account)
    print(f"  Clean account with valid data")
    print(f"  Contradictions found: {len(contradictions)} (expected: 0)")

    if contradictions:
        for c in contradictions:
            print(f"    Unexpected: {c.rule_code} - {c.description[:50]}...")

    return len(contradictions) == 0


def test_severity_sorting():
    """Verify contradictions are sorted by severity."""
    print("\n=== Severity Sorting ===")

    # Account with multiple issues of different severities
    account = {
        "account_id": "TEST-MULTI",
        "creditor_name": "Test Creditor",
        "open_date": "2023-01-15",
        "dofd": "2022-06-01",  # T1 - CRITICAL
        "status": "Paid",
        "payment_history": [
            {"status": "30", "month": 2, "year": 2023},  # S1 - MEDIUM
        ],
    }

    contradictions = detect_contradictions(account)
    print(f"  Account with multiple issues")
    print(f"  Contradictions found: {len(contradictions)}")

    if len(contradictions) >= 2:
        severities = [c.severity.value for c in contradictions]
        print(f"  Severity order: {severities}")
        # Check CRITICAL comes before MEDIUM
        critical_idx = next((i for i, c in enumerate(contradictions) if c.severity.value == "critical"), -1)
        medium_idx = next((i for i, c in enumerate(contradictions) if c.severity.value == "medium"), -1)
        sorted_correctly = critical_idx < medium_idx if critical_idx >= 0 and medium_idx >= 0 else True
        print(f"  Sorted correctly (CRITICAL before MEDIUM): {sorted_correctly}")
        return sorted_correctly

    return len(contradictions) > 0


def test_x1_stale_data():
    """X1: Stale data - activity older than status updates."""
    print("\n=== X1: Stale Data ===")

    # Status updated 90 days after last activity
    account = {
        "account_id": "TEST-X1",
        "creditor_name": "Test Creditor",
        "last_activity_date": "2023-01-01",
        "status_date": "2023-06-01",  # 151 days later - STALE
    }

    contradictions = detect_contradictions(account)
    x1_found = any(c.rule_code == "X1" for c in contradictions)
    print(f"  Last activity 01/2023, status updated 06/2023")
    print(f"  X1 detected: {x1_found} (expected: True)")

    if x1_found:
        c = next(c for c in contradictions if c.rule_code == "X1")
        print(f"  Days stale: {c.evidence.get('days_stale')}")

    return x1_found


def test_k1_missing_original_creditor_elevated():
    """K1: Missing original creditor for collection account."""
    print("\n=== K1: Missing Original Creditor Elevated ===")

    # Collection account without original creditor
    account = {
        "account_id": "TEST-K1",
        "creditor_name": "Midland Credit Management",  # Collection agency
        "status": "Collection",
        "original_creditor": None,  # Missing - ELEVATED
    }

    contradictions = detect_contradictions(account)
    k1_found = any(c.rule_code == "K1" for c in contradictions)
    print(f"  Collection account 'Midland Credit', no original creditor")
    print(f"  K1 detected: {k1_found} (expected: True)")

    if k1_found:
        c = next(c for c in contradictions if c.rule_code == "K1")
        print(f"  Is collection: {c.evidence.get('is_collection')}")

    return k1_found


def test_k1_original_creditor_present():
    """K1: Collection account WITH original creditor should NOT trigger."""
    print("\n=== K1: Original Creditor Present (No Violation) ===")

    # Collection account WITH original creditor - should NOT trigger
    account = {
        "account_id": "TEST-K1-OK",
        "creditor_name": "Portfolio Recovery Associates",
        "status": "Collection",
        "original_creditor": "Capital One",  # Present - OK
    }

    contradictions = detect_contradictions(account)
    k1_found = any(c.rule_code == "K1" for c in contradictions)
    print(f"  Collection account with original creditor 'Capital One'")
    print(f"  K1 detected: {k1_found} (expected: False)")

    return not k1_found


def test_p1_missing_scheduled_payment():
    """P1: Scheduled payment exists but no payment history."""
    print("\n=== P1: Missing Scheduled Payment ===")

    account = {
        "account_id": "TEST-P1",
        "creditor_name": "Test Lender",
        "scheduled_payment": 250.00,
        "payment_history": [],  # Empty - CONTRADICTION
        "status": "Open",
    }

    contradictions = detect_contradictions(account)
    p1_found = any(c.rule_code == "P1" for c in contradictions)
    print(f"  Scheduled payment $250, no payment history")
    print(f"  P1 detected: {p1_found} (expected: True)")

    if p1_found:
        c = next(c for c in contradictions if c.rule_code == "P1")
        print(f"  Evidence: {c.evidence}")

    return p1_found


def test_p1_with_history():
    """P1: Scheduled payment with history should NOT trigger."""
    print("\n=== P1: Scheduled Payment with History (No Violation) ===")

    account = {
        "account_id": "TEST-P1-OK",
        "creditor_name": "Test Lender",
        "scheduled_payment": 250.00,
        "payment_history": [
            {"status": "C", "month": 1, "year": 2024},
            {"status": "C", "month": 2, "year": 2024},
            {"status": "C", "month": 3, "year": 2024},
            {"status": "C", "month": 4, "year": 2024},
        ],  # Has history - OK
        "status": "Open",
    }

    contradictions = detect_contradictions(account)
    p1_found = any(c.rule_code == "P1" for c in contradictions)
    print(f"  Scheduled payment $250, has payment history")
    print(f"  P1 detected: {p1_found} (expected: False)")

    return not p1_found


def run_phase21_tests():
    """Run Phase 2.1 additional rule tests."""
    print("\n" + "=" * 60)
    print("PHASE-2.1 ADDITIONAL CONTRADICTION RULES")
    print("=" * 60)

    results = {
        "X1 (Stale Data)": test_x1_stale_data(),
        "K1 (Missing OC Elevated)": test_k1_missing_original_creditor_elevated(),
        "K1 (OC Present - No Violation)": test_k1_original_creditor_present(),
        "P1 (Missing Scheduled Payment)": test_p1_missing_scheduled_payment(),
        "P1 (Has History - No Violation)": test_p1_with_history(),
    }

    print("\n" + "=" * 60)
    print("PHASE-2.1 TEST RESULTS")
    print("=" * 60)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, passed_flag in results.items():
        status = "PASS" if passed_flag else "FAIL"
        print(f"  [{status}] {test_name}")

    print("\n" + "-" * 60)
    print(f"  TOTAL: {passed}/{total} tests passed")
    print("=" * 60)

    return passed == total


# =============================================================================
# PHASE 3: DEMAND PRIORITIZATION TESTS
# =============================================================================

def test_phase3_critical_severity_deletion():
    """Phase 3: CRITICAL severity → IMMEDIATE DELETION."""
    print("\n=== Phase 3: CRITICAL → IMMEDIATE DELETION ===")

    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "response_letter_generator",
        "app/services/enforcement/response_letter_generator.py"
    )
    rlg = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rlg)

    # T1 is CRITICAL severity
    account = {
        "account_id": "TEST-CRITICAL",
        "creditor_name": "Test Bank",
        "open_date": "2023-01-15",
        "dofd": "2022-06-01",  # Before open = CRITICAL
    }

    contradictions = detect_contradictions(account)
    remedy = rlg.determine_primary_remedy(contradictions)

    print(f"  1 CRITICAL contradiction")
    print(f"  Remedy: {remedy}")
    print(f"  Expected: IMMEDIATE_DELETION")

    return remedy == rlg.PrimaryRemedy.IMMEDIATE_DELETION


def test_phase3_two_high_severity_deletion():
    """Phase 3: 2+ HIGH severity → IMMEDIATE DELETION."""
    print("\n=== Phase 3: 2+ HIGH → IMMEDIATE DELETION ===")

    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "response_letter_generator",
        "app/services/enforcement/response_letter_generator.py"
    )
    rlg = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rlg)

    # Create account with 2 HIGH contradictions
    # D1 (missing DOFD) and M2 (balance increase after chargeoff) are both HIGH
    account = {
        "account_id": "TEST-TWO-HIGH",
        "creditor_name": "Collection Agency",
        "status": "Chargeoff",
        "dofd": None,  # D1 - HIGH
        "chargeoff_balance": 5000,
        "reported_balance": 8000,  # M2 - HIGH
    }

    contradictions = detect_contradictions(account)
    high_count = sum(1 for c in contradictions if c.severity.value.lower() == 'high')
    remedy = rlg.determine_primary_remedy(contradictions)

    print(f"  HIGH contradictions: {high_count}")
    print(f"  Remedy: {remedy}")
    print(f"  Expected: IMMEDIATE_DELETION (if 2+ HIGH)")

    return remedy == rlg.PrimaryRemedy.IMMEDIATE_DELETION and high_count >= 2


def test_phase3_one_high_correction():
    """Phase 3: 1 HIGH → CORRECTION WITH DOCUMENTATION."""
    print("\n=== Phase 3: 1 HIGH → CORRECTION ===")

    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "response_letter_generator",
        "app/services/enforcement/response_letter_generator.py"
    )
    rlg = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rlg)

    # Create account with only 1 HIGH contradiction (M2)
    # Note: Include dofd to avoid triggering D1 (missing DOFD)
    account = {
        "account_id": "TEST-ONE-HIGH",
        "creditor_name": "Test Creditor",
        "status": "Chargeoff",
        "dofd": "2023-01-01",  # Has DOFD to avoid D1
        "open_date": "2020-01-01",  # Open date before DOFD to avoid T1
        "chargeoff_balance": 5000,
        "reported_balance": 8000,  # M2 - HIGH (60% increase)
    }

    contradictions = detect_contradictions(account)
    high_count = sum(1 for c in contradictions if c.severity.value.lower() == 'high')
    remedy = rlg.determine_primary_remedy(contradictions)

    print(f"  HIGH contradictions: {high_count}")
    print(f"  Remedy: {remedy}")
    print(f"  Expected: CORRECTION_WITH_DOCUMENTATION (if exactly 1 HIGH)")

    return remedy == rlg.PrimaryRemedy.CORRECTION_WITH_DOCUMENTATION and high_count == 1


def test_phase3_medium_only_correction():
    """Phase 3: MEDIUM only → CORRECTION WITH DOCUMENTATION."""
    print("\n=== Phase 3: MEDIUM → CORRECTION ===")

    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "response_letter_generator",
        "app/services/enforcement/response_letter_generator.py"
    )
    rlg = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rlg)

    # Create account with only MEDIUM contradiction (S1 or X1)
    account = {
        "account_id": "TEST-MEDIUM",
        "creditor_name": "Test Creditor",
        "status": "Paid",
        "payment_history": [
            {"status": "30", "month": 1, "year": 2023},
        ],  # S1 - MEDIUM
    }

    contradictions = detect_contradictions(account)
    remedy = rlg.determine_primary_remedy(contradictions)

    print(f"  1 MEDIUM contradiction (S1)")
    print(f"  Remedy: {remedy}")
    print(f"  Expected: CORRECTION_WITH_DOCUMENTATION")

    return remedy == rlg.PrimaryRemedy.CORRECTION_WITH_DOCUMENTATION


def test_phase3_no_contradictions_standard():
    """Phase 3: No contradictions → STANDARD PROCEDURAL."""
    print("\n=== Phase 3: No Contradictions → STANDARD ===")

    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "response_letter_generator",
        "app/services/enforcement/response_letter_generator.py"
    )
    rlg = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rlg)

    remedy = rlg.determine_primary_remedy(None)

    print(f"  No contradictions")
    print(f"  Remedy: {remedy}")
    print(f"  Expected: STANDARD_PROCEDURAL")

    # Also test empty list
    remedy_empty = rlg.determine_primary_remedy([])
    print(f"  Empty list remedy: {remedy_empty}")

    return (remedy == rlg.PrimaryRemedy.STANDARD_PROCEDURAL and
            remedy_empty == rlg.PrimaryRemedy.STANDARD_PROCEDURAL)


def test_phase3_verified_letter_deletion_demand():
    """Phase 3: VERIFIED letter with CRITICAL → leads with IMMEDIATE DELETION."""
    print("\n=== Phase 3: VERIFIED Letter with Deletion Demand ===")

    from datetime import datetime, timedelta

    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "response_letter_generator",
        "app/services/enforcement/response_letter_generator.py"
    )
    rlg = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rlg)

    # T1 is CRITICAL
    account = {
        "account_id": "TEST-LETTER",
        "creditor_name": "Test Bank",
        "open_date": "2023-01-15",
        "dofd": "2022-06-01",
    }

    contradictions = detect_contradictions(account)

    letter = rlg.generate_verified_response_letter(
        consumer={"name": "Test User", "address": "123 Test St"},
        entity_type="CRA",
        entity_name="TransUnion",
        original_violations=[{"violation_type": "test", "creditor_name": "Test"}],
        dispute_date=datetime.now() - timedelta(days=45),
        response_date=datetime.now() - timedelta(days=10),
        contradictions=contradictions,
    )

    has_immediate_deletion = "IMMEDIATE DELETION" in letter
    deletion_before_other = letter.find("IMMEDIATE DELETION") < letter.find("Disclosure of")

    print(f"  Has 'IMMEDIATE DELETION': {has_immediate_deletion}")
    print(f"  Deletion is first demand: {deletion_before_other}")

    return has_immediate_deletion and deletion_before_other


def test_phase3_rejected_letter_correction_demand():
    """Phase 3: REJECTED letter with MEDIUM → leads with correction demand."""
    print("\n=== Phase 3: REJECTED Letter with Correction Demand ===")

    from datetime import datetime, timedelta

    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "response_letter_generator",
        "app/services/enforcement/response_letter_generator.py"
    )
    rlg = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rlg)

    # S1 is MEDIUM
    account = {
        "account_id": "TEST-MEDIUM-LETTER",
        "creditor_name": "Test Creditor",
        "status": "Paid",
        "payment_history": [{"status": "30", "month": 1, "year": 2023}],
    }

    contradictions = detect_contradictions(account)

    letter = rlg.generate_rejected_response_letter(
        consumer={"name": "Test User", "address": "123 Test St"},
        entity_type="CRA",
        entity_name="Experian",
        original_violations=[{"violation_type": "test", "creditor_name": "Test"}],
        dispute_date=datetime.now() - timedelta(days=30),
        rejection_date=datetime.now() - timedelta(days=5),
        contradictions=contradictions,
    )

    has_correction = "Immediate correction" in letter
    no_immediate_deletion = "IMMEDIATE DELETION" not in letter

    print(f"  Has 'Immediate correction': {has_correction}")
    print(f"  No 'IMMEDIATE DELETION': {no_immediate_deletion}")

    return has_correction and no_immediate_deletion


def run_phase3_tests():
    """Run Phase 3 demand prioritization tests."""
    print("\n" + "=" * 60)
    print("PHASE-3: DETERMINISTIC DEMAND PRIORITIZATION")
    print("=" * 60)

    results = {
        "CRITICAL → IMMEDIATE_DELETION": test_phase3_critical_severity_deletion(),
        "2+ HIGH → IMMEDIATE_DELETION": test_phase3_two_high_severity_deletion(),
        "1 HIGH → CORRECTION": test_phase3_one_high_correction(),
        "MEDIUM → CORRECTION": test_phase3_medium_only_correction(),
        "No contradictions → STANDARD": test_phase3_no_contradictions_standard(),
        "VERIFIED letter deletion demand": test_phase3_verified_letter_deletion_demand(),
        "REJECTED letter correction demand": test_phase3_rejected_letter_correction_demand(),
    }

    print("\n" + "=" * 60)
    print("PHASE-3 TEST RESULTS")
    print("=" * 60)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, passed_flag in results.items():
        status = "PASS" if passed_flag else "FAIL"
        print(f"  [{status}] {test_name}")

    print("\n" + "-" * 60)
    print(f"  TOTAL: {passed}/{total} tests passed")
    print("=" * 60)

    return passed == total


def run_all_tests():
    """Run all contradiction engine tests."""
    print("=" * 60)
    print("PHASE-1 CONTRADICTION ENGINE TEST SUITE")
    print("=" * 60)

    results = {
        "T1 (Open Date vs DOFD)": test_t1_open_date_vs_dofd(),
        "T2 (Payment History vs Age)": test_t2_payment_history_vs_age(),
        "T3 (Chargeoff Before Payment)": test_t3_chargeoff_before_last_payment(),
        "T4 (Delinquency Ladder)": test_t4_delinquency_ladder_inversion(),
        "D1 (Missing DOFD)": test_d1_missing_dofd_negative_status(),
        "D2 (DOFD vs Inferred)": test_d2_dofd_vs_inferred(),
        "D3 (Over 7 Years)": test_d3_over_seven_years(),
        "M1 (Balance Exceeds Max)": test_m1_balance_exceeds_legal_max(),
        "M2 (Balance After Chargeoff)": test_m2_balance_increase_after_chargeoff(),
        "S1 (Paid with Delinquencies)": test_s1_paid_status_with_delinquencies(),
        "S2 (Closed with Activity)": test_s2_closed_account_with_activity(),
        "Clean Account": test_no_contradictions_clean_account(),
        "Severity Sorting": test_severity_sorting(),
    }

    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, passed_flag in results.items():
        status = "PASS" if passed_flag else "FAIL"
        print(f"  [{status}] {test_name}")

    print("\n" + "-" * 60)
    print(f"  TOTAL: {passed}/{total} tests passed")
    print("=" * 60)

    return passed == total


def test_phase2_verified_letter_with_contradictions():
    """Test VERIFIED letter includes PROVABLE FACTUAL INACCURACIES section."""
    print("\n=== Phase 2: VERIFIED Letter with Contradictions ===")

    from datetime import datetime, timedelta

    # Direct import to avoid SQLAlchemy dependency chain
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "response_letter_generator",
        "app/services/enforcement/response_letter_generator.py"
    )
    rlg = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rlg)
    generate_verified_response_letter = rlg.generate_verified_response_letter

    from app.services.audit.contradiction_engine import detect_contradictions

    # Create account with contradictions
    account = {
        "account_id": "VERIZON-123",
        "creditor_name": "Verizon Wireless",
        "account_number_masked": "****5678",
        "open_date": "2023-01-15",
        "dofd": "2022-06-01",  # T1: Before open date
        "status": "Collection",
    }

    contradictions = detect_contradictions(account)
    print(f"  Contradictions found: {len(contradictions)}")

    # Generate letter with contradictions
    letter = generate_verified_response_letter(
        consumer={"name": "John Doe", "address": "123 Main St"},
        entity_type="CRA",
        entity_name="TransUnion",
        original_violations=[{
            "violation_type": "dofd_after_date_opened",
            "creditor_name": "Verizon Wireless",
            "account_number_masked": "****5678",
        }],
        dispute_date=datetime.now() - timedelta(days=45),
        response_date=datetime.now() - timedelta(days=10),
        contradictions=contradictions,
    )

    # Check for contradiction section
    has_section = "PROVABLE FACTUAL INACCURACIES" in letter
    has_critical = "[CRITICAL]" in letter
    has_contradiction_text = "mathematically or temporally impossible" in letter.lower()

    print(f"  Has PROVABLE FACTUAL INACCURACIES section: {has_section}")
    print(f"  Has [CRITICAL] severity marker: {has_critical}")
    print(f"  Has contradiction narrative: {has_contradiction_text}")

    return has_section and has_critical


def test_phase2_verified_letter_without_contradictions():
    """Test VERIFIED letter without contradictions falls back to normal."""
    print("\n=== Phase 2: VERIFIED Letter without Contradictions ===")

    from datetime import datetime, timedelta

    # Direct import to avoid SQLAlchemy dependency chain
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "response_letter_generator",
        "app/services/enforcement/response_letter_generator.py"
    )
    rlg = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rlg)
    generate_verified_response_letter = rlg.generate_verified_response_letter

    # Generate letter without contradictions
    letter = generate_verified_response_letter(
        consumer={"name": "John Doe", "address": "123 Main St"},
        entity_type="CRA",
        entity_name="Equifax",
        original_violations=[{
            "violation_type": "missing_dofd",
            "creditor_name": "Some Creditor",
            "account_number_masked": "****1234",
        }],
        dispute_date=datetime.now() - timedelta(days=45),
        response_date=datetime.now() - timedelta(days=10),
        contradictions=None,  # No contradictions
    )

    # Check that contradiction section is NOT present
    has_section = "PROVABLE FACTUAL INACCURACIES" in letter
    has_statutory = "STATUTORY FRAMEWORK" in letter
    has_violation = "STATUTORY VIOLATION" in letter

    print(f"  Has PROVABLE FACTUAL INACCURACIES section: {has_section} (expected: False)")
    print(f"  Has STATUTORY FRAMEWORK section: {has_statutory}")
    print(f"  Has STATUTORY VIOLATION section: {has_violation}")

    return not has_section and has_statutory and has_violation


def test_phase2_rejected_letter_with_contradictions():
    """Test REJECTED letter includes PROVABLE FACTUAL INACCURACIES section."""
    print("\n=== Phase 2: REJECTED Letter with Contradictions ===")

    from datetime import datetime, timedelta

    # Direct import to avoid SQLAlchemy dependency chain
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "response_letter_generator",
        "app/services/enforcement/response_letter_generator.py"
    )
    rlg = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rlg)
    generate_rejected_response_letter = rlg.generate_rejected_response_letter

    from app.services.audit.contradiction_engine import detect_contradictions

    # Create account with multiple contradictions
    account = {
        "account_id": "MIDLAND-456",
        "creditor_name": "Midland Credit",
        "account_number_masked": "****9999",
        "open_date": date.today() - timedelta(days=180),
        "payment_history_months": 24,  # T2: More months than account age
        "status": "Chargeoff",
        "chargeoff_balance": 5000,
        "reported_balance": 8000,  # M2: Balance increased after chargeoff
    }

    contradictions = detect_contradictions(account)
    print(f"  Contradictions found: {len(contradictions)}")

    # Generate letter with contradictions
    letter = generate_rejected_response_letter(
        consumer={"name": "Jane Smith", "address": "456 Oak Ave"},
        entity_type="CRA",
        entity_name="Experian",
        original_violations=[{
            "violation_type": "balance_increase_after_chargeoff",
            "creditor_name": "Midland Credit",
            "account_number_masked": "****9999",
        }],
        dispute_date=datetime.now() - timedelta(days=30),
        rejection_date=datetime.now() - timedelta(days=5),
        contradictions=contradictions,
    )

    # Check for contradiction section
    has_section = "PROVABLE FACTUAL INACCURACIES" in letter
    has_frivolous_context = "cannot be deemed \"frivolous\"" in letter

    print(f"  Has PROVABLE FACTUAL INACCURACIES section: {has_section}")
    print(f"  Has frivolous-contradiction context: {has_frivolous_context}")

    return has_section


def test_phase2_no_response_unchanged():
    """Test NO_RESPONSE letter is unchanged (no contradictions support)."""
    print("\n=== Phase 2: NO_RESPONSE Letter Unchanged ===")

    from datetime import datetime, timedelta

    # Direct import to avoid SQLAlchemy dependency chain
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "response_letter_generator",
        "app/services/enforcement/response_letter_generator.py"
    )
    rlg = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rlg)
    generate_no_response_letter = rlg.generate_no_response_letter

    letter = generate_no_response_letter(
        consumer={"name": "Test User", "address": "789 Pine St"},
        entity_type="CRA",
        entity_name="TransUnion",
        original_violations=[{
            "violation_type": "missing_dofd",
            "creditor_name": "Test Creditor",
        }],
        dispute_date=datetime.now() - timedelta(days=45),
        deadline_date=datetime.now() - timedelta(days=15),
    )

    # NO_RESPONSE should NOT have contradiction section (unchanged behavior)
    has_section = "PROVABLE FACTUAL INACCURACIES" in letter
    has_no_response = "Failure to Respond" in letter

    print(f"  Has PROVABLE FACTUAL INACCURACIES section: {has_section} (expected: False)")
    print(f"  Has NO_RESPONSE content: {has_no_response}")

    return not has_section and has_no_response


def run_phase2_tests():
    """Run Phase 2 integration tests."""
    print("\n" + "=" * 60)
    print("PHASE 2: CONTRADICTION-FIRST LETTER INTEGRATION TESTS")
    print("=" * 60)

    results = {
        "VERIFIED with contradictions": test_phase2_verified_letter_with_contradictions(),
        "VERIFIED without contradictions": test_phase2_verified_letter_without_contradictions(),
        "REJECTED with contradictions": test_phase2_rejected_letter_with_contradictions(),
        "NO_RESPONSE unchanged": test_phase2_no_response_unchanged(),
    }

    print("\n" + "=" * 60)
    print("PHASE 2 TEST RESULTS")
    print("=" * 60)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, passed_flag in results.items():
        status = "PASS" if passed_flag else "FAIL"
        print(f"  [{status}] {test_name}")

    print("\n" + "-" * 60)
    print(f"  TOTAL: {passed}/{total} tests passed")
    print("=" * 60)

    return passed == total


if __name__ == "__main__":
    # Run Phase 1 tests
    phase1_success = run_all_tests()

    # Run Phase 2.1 tests (new rules)
    phase21_success = run_phase21_tests()

    # Run Phase 3 tests (demand prioritization)
    phase3_success = run_phase3_tests()

    # Run Phase 2 tests (letter integration)
    phase2_success = run_phase2_tests()

    # Exit with success only if all tests pass
    all_passed = phase1_success and phase21_success and phase3_success and phase2_success
    sys.exit(0 if all_passed else 1)
