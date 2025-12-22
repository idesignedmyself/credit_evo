"""
Credit Engine 2.0 - Copilot Engine Tests

Tests for:
1. Goal mapping → target state
2. DOFD stability gate triggers correctly
3. Ownership gate triggers for collections/debt buyers
4. Impact scoring is goal-relative (NOT severity-relative)
5. Skip codes are FCRA-native only (NO SOL references)
6. Employment goal blocks on public records
7. Full recommendation flow
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.models.copilot_models import (
    CreditGoal,
    GOAL_REQUIREMENTS,
    SkipCode,
    ActionType,
    DELETABILITY_WEIGHTS,
)
from app.services.copilot.copilot_engine import CopilotEngine


def test_goal_requirements_mapping():
    """Test that all goals have proper target state requirements."""
    print("\n" + "=" * 60)
    print("TEST: Goal Requirements Mapping")
    print("=" * 60)

    engine = CopilotEngine()
    passed = 0
    failed = 0

    # Check all goals are defined
    for goal in CreditGoal:
        if goal in GOAL_REQUIREMENTS:
            target = GOAL_REQUIREMENTS[goal]
            print(f"  [PASS] {goal.value} has target state defined")
            passed += 1
        else:
            print(f"  [FAIL] {goal.value} missing target state")
            failed += 1

    # Check EMPLOYMENT has zero public records required
    emp_target = GOAL_REQUIREMENTS[CreditGoal.EMPLOYMENT]
    if emp_target.zero_public_records_required:
        print(f"  [PASS] EMPLOYMENT has zero_public_records_required=True")
        passed += 1
    else:
        print(f"  [FAIL] EMPLOYMENT should have zero_public_records_required=True")
        failed += 1

    if emp_target.public_records_allowed == 0:
        print(f"  [PASS] EMPLOYMENT has public_records_allowed=0")
        passed += 1
    else:
        print(f"  [FAIL] EMPLOYMENT should have public_records_allowed=0")
        failed += 1

    # Check MORTGAGE has strict requirements
    mtg_target = GOAL_REQUIREMENTS[CreditGoal.MORTGAGE]
    if mtg_target.zero_collection_required and mtg_target.zero_chargeoff_required:
        print(f"  [PASS] MORTGAGE has zero collection and chargeoff required")
        passed += 1
    else:
        print(f"  [FAIL] MORTGAGE should have zero collection/chargeoff")
        failed += 1

    print(f"\n  Total: {passed}/{passed + failed} passed")
    return passed, failed


def test_dofd_stability_gate():
    """Test DOFD stability gate triggers correctly."""
    print("\n" + "=" * 60)
    print("TEST: DOFD Stability Gate")
    print("=" * 60)

    engine = CopilotEngine()
    passed = 0
    failed = 0

    # Test with D1 contradiction (DOFD missing on derogatory)
    contradictions = [
        {
            "id": "c1",
            "rule_code": "D1",
            "severity": "CRITICAL",
            "description": "Missing DOFD on derogatory account",
            "account_id": "acct_1",
            "creditor_name": "Test Creditor",
        },
        {
            "id": "c2",
            "rule_code": "M2",
            "severity": "HIGH",
            "description": "Balance increased after chargeoff",
            "account_id": "acct_1",
            "creditor_name": "Test Creditor",
            "category": "balance",
        },
    ]

    result = engine.analyze(
        goal=CreditGoal.MORTGAGE,
        contradictions=contradictions,
    )

    # Check DOFD gate is active
    if result.dofd_gate_active:
        print(f"  [PASS] DOFD gate active when D1 contradiction present")
        passed += 1
    else:
        print(f"  [FAIL] DOFD gate should be active with D1 contradiction")
        failed += 1

    # Check D1 blocker has gate_priority=1
    d1_blocker = next((b for b in result.blockers if b.rule_code == "D1"), None)
    if d1_blocker and d1_blocker.gate_priority == 1:
        print(f"  [PASS] D1 blocker has gate_priority=1")
        passed += 1
    else:
        print(f"  [FAIL] D1 blocker should have gate_priority=1")
        failed += 1

    # Check balance blocker is suppressed (gate_priority=99)
    balance_blocker = next((b for b in result.blockers if b.category == "balance"), None)
    if balance_blocker and balance_blocker.gate_priority == 99:
        print(f"  [PASS] Balance blocker suppressed (gate_priority=99)")
        passed += 1
    else:
        print(f"  [FAIL] Balance blocker should be suppressed until DOFD resolved")
        failed += 1

    # Check actions are ordered correctly (DOFD first)
    if result.actions:
        first_action = result.actions[0]
        if first_action.action_type == ActionType.DOFD_DEMAND:
            print(f"  [PASS] First action is DOFD_DEMAND")
            passed += 1
        else:
            print(f"  [FAIL] First action should be DOFD_DEMAND, got {first_action.action_type}")
            failed += 1

    print(f"\n  Total: {passed}/{passed + failed} passed")
    return passed, failed


def test_ownership_gate():
    """Test ownership gate triggers for collections/debt buyers."""
    print("\n" + "=" * 60)
    print("TEST: Ownership Gate")
    print("=" * 60)

    engine = CopilotEngine()
    passed = 0
    failed = 0

    # Test with collection account missing original creditor
    violations = [
        {
            "id": "v1",
            "violation_type": "collection_balance_inflation",
            "severity": "HIGH",
            "description": "Collection balance exceeds original debt",
            "account_id": "acct_1",
            "creditor_name": "Midland Credit",
            "furnisher_type": "COLLECTION",
            "has_original_creditor": False,
            "category": "collection",
        },
    ]

    result = engine.analyze(
        goal=CreditGoal.MORTGAGE,
        violations=violations,
    )

    # Check ownership gate is active
    if result.ownership_gate_active:
        print(f"  [PASS] Ownership gate active for collection without OC")
        passed += 1
    else:
        print(f"  [FAIL] Ownership gate should be active for collection without OC")
        failed += 1

    # Check blocker has requires_ownership_first=True
    blocker = result.blockers[0] if result.blockers else None
    if blocker and blocker.requires_ownership_first:
        print(f"  [PASS] Blocker has requires_ownership_first=True")
        passed += 1
    else:
        print(f"  [FAIL] Blocker should require ownership first")
        failed += 1

    # Check action type is OWNERSHIP_CHAIN_DEMAND
    if result.actions:
        first_action = result.actions[0]
        if first_action.action_type == ActionType.OWNERSHIP_CHAIN_DEMAND:
            print(f"  [PASS] Action type is OWNERSHIP_CHAIN_DEMAND")
            passed += 1
        else:
            print(f"  [FAIL] Should get OWNERSHIP_CHAIN_DEMAND, got {first_action.action_type}")
            failed += 1

    print(f"\n  Total: {passed}/{passed + failed} passed")
    return passed, failed


def test_goal_relative_impact():
    """Test impact scoring is goal-relative, NOT severity-relative."""
    print("\n" + "=" * 60)
    print("TEST: Goal-Relative Impact Scoring")
    print("=" * 60)

    engine = CopilotEngine()
    passed = 0
    failed = 0

    # Same collection violation, different goals
    collection_violation = {
        "id": "v1",
        "violation_type": "collection",
        "severity": "MEDIUM",  # Severity is MEDIUM
        "description": "Collection account",
        "account_id": "acct_1",
        "creditor_name": "Test Collection",
        "category": "collection",
        "is_derogatory": True,
    }

    # Test MORTGAGE goal - collection should have impact 10
    mtg_result = engine.analyze(
        goal=CreditGoal.MORTGAGE,
        violations=[collection_violation],
    )
    mtg_blocker = mtg_result.blockers[0] if mtg_result.blockers else None
    if mtg_blocker and mtg_blocker.impact_score == 10:
        print(f"  [PASS] MORTGAGE: collection impact=10 (blocks goal)")
        passed += 1
    else:
        impact = mtg_blocker.impact_score if mtg_blocker else "N/A"
        print(f"  [FAIL] MORTGAGE: collection should have impact=10, got {impact}")
        failed += 1

    # Test APARTMENT goal - collection should have impact 6
    apt_result = engine.analyze(
        goal=CreditGoal.APARTMENT_RENTAL,
        violations=[collection_violation],
    )
    apt_blocker = apt_result.blockers[0] if apt_result.blockers else None
    if apt_blocker and apt_blocker.impact_score == 6:
        print(f"  [PASS] APARTMENT: collection impact=6 (one allowed)")
        passed += 1
    else:
        impact = apt_blocker.impact_score if apt_blocker else "N/A"
        print(f"  [FAIL] APARTMENT: collection should have impact=6, got {impact}")
        failed += 1

    # Test EMPLOYMENT - public record should have impact 10
    pr_violation = {
        "id": "v2",
        "violation_type": "judgment",
        "severity": "LOW",  # Severity is LOW
        "description": "Civil judgment",
        "account_id": "acct_2",
        "creditor_name": "Test Court",
        "category": "public_record",
        "is_derogatory": True,
    }
    emp_result = engine.analyze(
        goal=CreditGoal.EMPLOYMENT,
        violations=[pr_violation],
    )
    emp_blocker = emp_result.blockers[0] if emp_result.blockers else None
    if emp_blocker and emp_blocker.impact_score == 10:
        print(f"  [PASS] EMPLOYMENT: public_record impact=10 (critical for employment)")
        passed += 1
    else:
        impact = emp_blocker.impact_score if emp_blocker else "N/A"
        print(f"  [FAIL] EMPLOYMENT: public_record should have impact=10, got {impact}")
        failed += 1

    # Verify impact is NOT based on severity
    # The LOW severity judgment should still be impact=10 for EMPLOYMENT
    if emp_blocker and emp_blocker.impact_score == 10:
        print(f"  [PASS] Impact is goal-relative, not severity-relative")
        passed += 1
    else:
        print(f"  [FAIL] Impact should be goal-relative, not severity-relative")
        failed += 1

    print(f"\n  Total: {passed}/{passed + failed} passed")
    return passed, failed


def test_fcra_native_skip_codes():
    """Test skip codes are FCRA-native only, NO SOL references."""
    print("\n" + "=" * 60)
    print("TEST: FCRA-Native Skip Codes (NO SOL)")
    print("=" * 60)

    engine = CopilotEngine()
    passed = 0
    failed = 0

    # Verify no SOL-related skip codes exist
    valid_codes = {
        "DOFD_UNSTABLE",
        "REINSERTION_LIKELY",
        "POSITIVE_LINE_LOSS",
        "UTILIZATION_SHOCK",
        "TACTICAL_VERIFICATION_RISK",
    }

    for code in SkipCode:
        if code.value in valid_codes:
            print(f"  [PASS] {code.value} is FCRA-native")
            passed += 1
        else:
            print(f"  [FAIL] {code.value} is not in approved FCRA-native list")
            failed += 1

    # Check that SOL codes don't exist
    forbidden_terms = ["SOL", "STATUTE", "LIMITATIONS", "EXPIRED", "TOLLED"]
    for code in SkipCode:
        has_forbidden = any(term in code.value.upper() for term in forbidden_terms)
        if not has_forbidden:
            print(f"  [PASS] {code.value} has no SOL terminology")
            passed += 1
        else:
            print(f"  [FAIL] {code.value} contains SOL-related terminology")
            failed += 1

    print(f"\n  Total: {passed}/{passed + failed} passed")
    return passed, failed


def test_employment_public_records():
    """Test Employment goal blocks on public records."""
    print("\n" + "=" * 60)
    print("TEST: Employment Goal - Public Records Blocking")
    print("=" * 60)

    engine = CopilotEngine()
    passed = 0
    failed = 0

    # Test with public record violation
    pr_violations = [
        {
            "id": "v1",
            "violation_type": "judgment",
            "severity": "MEDIUM",
            "description": "Civil judgment",
            "account_id": "acct_1",
            "creditor_name": "Court",
            "category": "public_record",
            "is_derogatory": True,
        },
        {
            "id": "v2",
            "violation_type": "bankruptcy",
            "severity": "LOW",
            "description": "Chapter 7 bankruptcy",
            "account_id": "acct_2",
            "creditor_name": "Court",
            "category": "public_record",
            "is_derogatory": True,
        },
    ]

    result = engine.analyze(
        goal=CreditGoal.EMPLOYMENT,
        violations=pr_violations,
    )

    # Check public records are hard blockers
    pr_blockers = [b for b in result.blockers if b.category == "public_record"]
    all_blocking = all(b.blocks_goal for b in pr_blockers)

    if all_blocking and len(pr_blockers) == 2:
        print(f"  [PASS] Both public records are hard blockers for EMPLOYMENT")
        passed += 1
    else:
        print(f"  [FAIL] Public records should be hard blockers for EMPLOYMENT")
        failed += 1

    # Check impact is 10 for all public records
    all_impact_10 = all(b.impact_score == 10 for b in pr_blockers)
    if all_impact_10:
        print(f"  [PASS] Public records have impact=10 for EMPLOYMENT")
        passed += 1
    else:
        print(f"  [FAIL] Public records should have impact=10 for EMPLOYMENT")
        failed += 1

    # Check achievability is affected
    if result.goal_achievability in {"CHALLENGING", "UNLIKELY"}:
        print(f"  [PASS] Goal achievability correctly reflects public records: {result.goal_achievability}")
        passed += 1
    else:
        print(f"  [FAIL] Goal achievability should be CHALLENGING or UNLIKELY with public records")
        failed += 1

    print(f"\n  Total: {passed}/{passed + failed} passed")
    return passed, failed


def test_full_recommendation_flow():
    """Test complete recommendation generation."""
    print("\n" + "=" * 60)
    print("TEST: Full Recommendation Flow")
    print("=" * 60)

    engine = CopilotEngine()
    passed = 0
    failed = 0

    # Mix of contradictions and violations
    contradictions = [
        {
            "id": "c1",
            "rule_code": "T1",
            "severity": "CRITICAL",
            "description": "DOFD before open date - temporal impossibility",
            "account_id": "acct_1",
            "creditor_name": "Test Bank",
            "category": "temporal",
        },
    ]

    violations = [
        {
            "id": "v1",
            "violation_type": "collection",
            "severity": "HIGH",
            "description": "Collection account",
            "account_id": "acct_2",
            "creditor_name": "Midland Credit",
            "category": "collection",
            "is_derogatory": True,
            "furnisher_type": "COLLECTION",
            "has_original_creditor": True,
        },
        {
            "id": "v2",
            "violation_type": "late_payment",
            "severity": "MEDIUM",
            "description": "30-day late payment",
            "account_id": "acct_3",
            "creditor_name": "Chase",
            "category": "late",
            "is_derogatory": True,
        },
    ]

    result = engine.analyze(
        goal=CreditGoal.MORTGAGE,
        contradictions=contradictions,
        violations=violations,
        user_id="test_user",
        report_id="test_report",
    )

    # Check recommendation structure
    if result.recommendation_id:
        print(f"  [PASS] Recommendation ID generated")
        passed += 1
    else:
        print(f"  [FAIL] Missing recommendation ID")
        failed += 1

    if result.goal == CreditGoal.MORTGAGE:
        print(f"  [PASS] Goal correctly set to MORTGAGE")
        passed += 1
    else:
        print(f"  [FAIL] Goal should be MORTGAGE")
        failed += 1

    if result.target_state:
        print(f"  [PASS] Target state populated")
        passed += 1
    else:
        print(f"  [FAIL] Missing target state")
        failed += 1

    if len(result.blockers) == 3:
        print(f"  [PASS] All 3 items converted to blockers")
        passed += 1
    else:
        print(f"  [FAIL] Expected 3 blockers, got {len(result.blockers)}")
        failed += 1

    if result.actions:
        print(f"  [PASS] Actions generated: {len(result.actions)}")
        passed += 1
    else:
        print(f"  [FAIL] No actions generated")
        failed += 1

    if result.sequencing_rationale:
        print(f"  [PASS] Sequencing rationale provided")
        passed += 1
    else:
        print(f"  [FAIL] Missing sequencing rationale")
        failed += 1

    if result.current_gap_summary:
        print(f"  [PASS] Gap summary: {result.current_gap_summary}")
        passed += 1
    else:
        print(f"  [FAIL] Missing gap summary")
        failed += 1

    # Check priority scoring makes sense
    if result.actions:
        # Actions should be sorted by priority
        priorities = [a.priority_score for a in result.actions]
        is_sorted = priorities == sorted(priorities, reverse=True)
        if is_sorted:
            print(f"  [PASS] Actions sorted by priority score")
            passed += 1
        else:
            print(f"  [FAIL] Actions should be sorted by priority score")
            failed += 1

    print(f"\n  Total: {passed}/{passed + failed} passed")
    return passed, failed


def test_priority_formula():
    """Test priority formula: impact × deletability ÷ (1 + risk)."""
    print("\n" + "=" * 60)
    print("TEST: Priority Formula Calculation")
    print("=" * 60)

    engine = CopilotEngine()
    passed = 0
    failed = 0

    # High impact, high deletability, low risk = high priority
    high_priority_violation = {
        "id": "v1",
        "violation_type": "collection",
        "severity": "CRITICAL",
        "description": "Collection with temporal impossibility",
        "account_id": "acct_1",
        "creditor_name": "Test",
        "category": "collection",
        "is_derogatory": True,
        "has_temporal_impossibility": True,  # HIGH deletability
    }

    # Low impact, low deletability, high risk = low priority
    low_priority_violation = {
        "id": "v2",
        "violation_type": "inquiry",
        "severity": "LOW",
        "description": "Hard inquiry",
        "account_id": "acct_2",
        "creditor_name": "Test",
        "category": "inquiry",
        "is_derogatory": False,
        "reinsertion_risk": True,  # Adds risk
    }

    result = engine.analyze(
        goal=CreditGoal.MORTGAGE,
        violations=[high_priority_violation, low_priority_violation],
    )

    if len(result.actions) >= 1:
        # First action should be the high priority one
        first = result.actions[0]
        if first.blocker_source_id == "v1":
            print(f"  [PASS] High-priority item (collection) ranked first")
            passed += 1
        else:
            print(f"  [FAIL] High-priority item should be ranked first")
            failed += 1

        # Check priority score is reasonable
        # impact=10, deletability=1.0 (HIGH), risk=0 → priority = 10 * 1.0 / 1 = 10
        if first.priority_score > 5:
            print(f"  [PASS] High-priority score: {first.priority_score}")
            passed += 1
        else:
            print(f"  [FAIL] Priority score should be high, got {first.priority_score}")
            failed += 1

    print(f"\n  Total: {passed}/{passed + failed} passed")
    return passed, failed


def run_all_tests():
    """Run all Copilot Engine tests."""
    print("\n" + "=" * 60)
    print("COPILOT ENGINE TEST SUITE")
    print("=" * 60)

    total_passed = 0
    total_failed = 0

    tests = [
        test_goal_requirements_mapping,
        test_dofd_stability_gate,
        test_ownership_gate,
        test_goal_relative_impact,
        test_fcra_native_skip_codes,
        test_employment_public_records,
        test_full_recommendation_flow,
        test_priority_formula,
    ]

    for test_fn in tests:
        try:
            passed, failed = test_fn()
            total_passed += passed
            total_failed += failed
        except Exception as e:
            print(f"\n  [ERROR] {test_fn.__name__}: {e}")
            total_failed += 1

    print("\n" + "=" * 60)
    print("COPILOT ENGINE TEST RESULTS")
    print("=" * 60)
    print(f"  Total Passed: {total_passed}")
    print(f"  Total Failed: {total_failed}")
    print(f"  Success Rate: {total_passed}/{total_passed + total_failed} ({100 * total_passed / (total_passed + total_failed):.1f}%)")
    print("=" * 60)

    return total_failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
