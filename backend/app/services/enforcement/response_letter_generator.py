"""
Credit Engine 2.0 - Response Letter Generator
Generates formal FCRA enforcement correspondence based on dispute responses.

ROLE: U.S. consumer credit compliance enforcement engine.
- Does NOT provide advice
- Generates formal regulatory correspondence asserting violations
- Cites statutes in canonical USC format only
- Treats all violations as assertions unless explicitly marked "resolved"
- Assumes recipient is legally sophisticated

Phase 2 Integration:
- VERIFIED and REJECTED letters support contradiction-first narratives
- Contradictions appear in "PROVABLE FACTUAL INACCURACIES" section after header
- NO_RESPONSE, REINSERTION, DELETED remain unchanged
"""

from datetime import datetime
from typing import Dict, List, Optional, Any, TYPE_CHECKING
from uuid import UUID
import textwrap

# Type hint for Contradiction without creating import dependency
if TYPE_CHECKING:
    from ..audit.contradiction_engine import Contradiction


# Canonical entity names (legal names for correspondence)
CANONICAL_ENTITY_NAMES = {
    # CRAs
    "transunion": "TransUnion LLC",
    "trans union": "TransUnion LLC",
    "tu": "TransUnion LLC",
    "equifax": "Equifax Inc.",
    "eq": "Equifax Inc.",
    "experian": "Experian LLC",
    "ex": "Experian LLC",
    "exp": "Experian LLC",
}


def canonicalize_entity_name(name: str) -> str:
    """
    Convert entity name to canonical legal name.

    Examples:
        "TransUnion" -> "TransUnion LLC"
        "transunion" -> "TransUnion LLC"
        "EQUIFAX" -> "Equifax Inc."
    """
    if not name:
        return name
    lookup = name.lower().strip()
    return CANONICAL_ENTITY_NAMES.get(lookup, name)


# Known acronyms that should stay uppercase in violation display
PRESERVE_ACRONYMS = {"dofd", "dla", "fcra", "fdcpa", "ecoa", "ssn", "oc", "au", "ncap", "udaap"}


def format_violation_display(violation_type: str) -> str:
    """
    Format violation type for display, preserving known acronyms.

    Examples:
        "missing_dofd" -> "Missing DOFD"
        "fcra_violation" -> "FCRA Violation"
        "balance_exceeds_credit_limit" -> "Balance Exceeds Credit Limit"
    """
    if not violation_type:
        return ""
    words = violation_type.replace("_", " ").split()
    formatted = []
    for word in words:
        if word.lower() in PRESERVE_ACRONYMS:
            formatted.append(word.upper())
        else:
            formatted.append(word.capitalize())
    return " ".join(formatted)


# Violation type to statute auto-assignment
# Maps violation types to their primary FCRA statute when not explicitly set
VIOLATION_STATUTE_DEFAULTS = {
    # Missing field violations -> §1681e(b) accuracy requirement
    "missing_dofd": "15 U.S.C. § 1681e(b)",
    "missing_date_opened": "15 U.S.C. § 1681e(b)",
    "missing_dla": "15 U.S.C. § 1681e(b)",
    "missing_payment_status": "15 U.S.C. § 1681e(b)",
    "missing_original_creditor": "15 U.S.C. § 1681e(b)",
    "missing_scheduled_payment": "15 U.S.C. § 1681e(b)",
    # Balance/amount violations -> §1681e(b)
    "negative_balance": "15 U.S.C. § 1681e(b)",
    "past_due_exceeds_balance": "15 U.S.C. § 1681e(b)",
    "balance_exceeds_high_credit": "15 U.S.C. § 1681e(b)",
    "balance_exceeds_credit_limit": "15 U.S.C. § 1681e(b)",
    # Date violations -> §1681e(b)
    "future_date": "15 U.S.C. § 1681e(b)",
    "dofd_after_date_opened": "15 U.S.C. § 1681e(b)",
    # Cross-bureau mismatches -> §1681e(b)
    "dofd_mismatch": "15 U.S.C. § 1681e(b)",
    "balance_mismatch": "15 U.S.C. § 1681e(b)",
    "status_mismatch": "15 U.S.C. § 1681e(b)",
    # Temporal violations -> §1681c(a) obsolescence
    "stale_reporting": "15 U.S.C. § 1681c(a)",
    "re_aging": "15 U.S.C. § 1681c(a)",
    "obsolete_account": "15 U.S.C. § 1681c(a)",
    # Default fallback
    "default": "15 U.S.C. § 1681e(b)",
}


def get_statute_for_violation(violation_type: str, explicit_statute: str = None) -> str:
    """
    Get the appropriate statute for a violation type.

    Uses explicit statute if provided and non-empty, otherwise auto-assigns
    based on violation type.
    """
    if explicit_statute and explicit_statute.strip():
        return explicit_statute

    v_type = violation_type.lower().replace(" ", "_") if violation_type else ""
    return VIOLATION_STATUTE_DEFAULTS.get(v_type, VIOLATION_STATUTE_DEFAULTS["default"])


# =============================================================================
# TIER 2: BASIS FOR NON-COMPLIANCE MAPPINGS
# =============================================================================
# These explain WHY verification was impossible (fact-based), not just
# that a statute was violated (law-based). This is the key to Tier-2 letters.

BASIS_FOR_NON_COMPLIANCE = {
    # -------------------------------------------------------------------------
    # Missing Mandatory Fields - Cannot verify without required data
    # -------------------------------------------------------------------------
    "missing_dofd": """The disputed account is missing the Date of First Delinquency (DOFD), a mandatory compliance field required for the lawful reporting of delinquent accounts.

An account missing a required compliance field cannot be verified as accurate, as the absence of DOFD prevents confirmation of:
- Lawful aging of the account
- Compliance with reporting period limitations
- Accuracy and integrity controls required under the FCRA

Verification of an account lacking mandatory compliance data is logically and procedurally impossible.""",

    "chargeoff_missing_dofd": """The disputed account shows charge-off status but is missing the Date of First Delinquency (DOFD).

Under Metro 2 reporting standards, DOFD is mandatory for any account with derogatory status. A charge-off without DOFD cannot be verified because:
- The account aging cannot be validated
- FCRA §605(a) obsolescence cannot be confirmed
- The charge-off date itself may be fabricated

Verification of a charge-off account without its required DOFD field is procedurally impossible.""",

    "missing_date_opened": """The disputed account is missing the Date Opened field.

Without Date Opened, the following cannot be verified:
- Whether the account age is accurately represented
- Whether payment history is consistent with account timeline
- Whether the consumer was even legally capable of opening the account at the claimed time

Verification without Date Opened is logically impossible.""",

    "missing_original_creditor": """The disputed collection account is missing Original Creditor information.

Under FCRA §623(a)(7) and Metro 2 K1 segment requirements, debt collectors must identify the original creditor. Without chain of title documentation:
- Debt ownership cannot be established
- The consumer cannot verify the debt is legitimately theirs
- The accuracy of the claimed balance cannot be traced

Verification of a collection without original creditor is procedurally impossible.""",

    # -------------------------------------------------------------------------
    # Temporal Impossibilities (T-series) - Mathematically impossible
    # -------------------------------------------------------------------------
    "payment_history_exceeds_account_age": """The disputed account shows payment history that exceeds the account age - a temporal impossibility.

An account cannot have payment history for months before it existed. This is not a judgment call or disputed interpretation - it is mathematically impossible.

Verification of information that is temporally impossible evidences a perfunctory investigation rather than a reasonable reinvestigation as required by statute.""",

    "chargeoff_before_last_payment": """The disputed account shows a charge-off date that precedes the date of last payment.

An account cannot be charged off before the consumer's final payment was made. This chronological impossibility demonstrates that the reported data is fabricated or corrupted.

Verification of an impossible chronological sequence evidences a perfunctory investigation.""",

    "delinquency_ladder_inversion": """The disputed account shows delinquency dates in impossible sequence - the 90-day delinquency date precedes the 30-day delinquency date.

Delinquency progresses sequentially: 30 days → 60 days → 90 days → 120 days. An account cannot be 90 days late before it is 30 days late.

Verification of an inverted delinquency ladder is logically impossible.""",

    "impossible_timeline": """The disputed account contains dates that form an impossible timeline.

The reported dates are chronologically impossible and cannot represent actual account history. No reasonable investigation could verify data that violates basic chronological reality.""",

    # -------------------------------------------------------------------------
    # Mathematical Impossibilities (M-series) - Numbers don't add up
    # -------------------------------------------------------------------------
    "balance_exceeds_legal_max": """The disputed account shows a balance that exceeds the legal maximum based on the original debt amount plus allowable interest and fees.

Even with maximum statutory interest and all allowable fees, the balance cannot mathematically reach the reported amount. This indicates fabrication or unauthorized fee inflation.

Verification of a mathematically impossible balance evidences a perfunctory investigation.""",

    "balance_increase_after_chargeoff": """The disputed account shows a balance increase after the charge-off date without any new activity.

Once an account is charged off, the balance is frozen. It cannot increase without new credit extensions (which are impossible on a charged-off account) or collection activity that must be separately documented.

Verification of unexplained post-chargeoff balance increases is procedurally impossible.""",

    "past_due_exceeds_balance": """The disputed account shows a past-due amount that exceeds the total balance.

It is mathematically impossible for a consumer to owe more in past-due amounts than the total account balance. This is not a disputed interpretation - it is arithmetic impossibility.

Verification of mathematically impossible amounts evidences a perfunctory investigation.""",

    "balance_exceeds_credit_limit": """The disputed account shows a balance exceeding the credit limit by an amount inconsistent with allowable over-limit activity.

While minor over-limit balances can occur, the reported balance exceeds any mathematically possible scenario and indicates data corruption or fabrication.

Verification of an impossible balance-to-limit relationship evidences a perfunctory investigation.""",

    # -------------------------------------------------------------------------
    # Status/Field Contradictions (S-series) - Internal inconsistency
    # -------------------------------------------------------------------------
    "paid_status_with_balance": """The disputed account shows "Paid" status while reporting a balance greater than zero.

An account cannot simultaneously be paid in full and have an outstanding balance. These fields directly contradict each other.

Verification of internally contradictory data is logically impossible.""",

    "paid_status_with_delinquencies": """The disputed account shows "Paid" status while the payment history contains delinquency indicators.

If an account is marked as Paid, the payment history should reflect resolution. The presence of delinquency markers after paid status is internally inconsistent.

Verification of self-contradicting fields evidences a perfunctory investigation.""",

    "closed_account_post_activity": """The disputed account shows activity reported after the account closure date.

A closed account cannot have new activity. Activity reported after closure is either fabricated or indicates the closure date is inaccurate.

Verification of post-closure activity on a closed account is procedurally impossible.""",

    "status_payment_history_mismatch": """The disputed account shows a status code that contradicts the payment history.

The account status and payment history must be consistent. When they contradict each other, at least one field is inaccurate and verification requires resolving the discrepancy - not rubber-stamping it.

Verification of status/history contradictions requires investigation, not mere confirmation.""",

    # -------------------------------------------------------------------------
    # DOFD/Aging Contradictions (D-series)
    # -------------------------------------------------------------------------
    "dofd_inferred_mismatch": """The disputed account's reported Date of First Delinquency (DOFD) does not match the DOFD inferable from the payment history.

The first late marker in payment history should correspond to the DOFD. When they differ, the DOFD has been manipulated - likely to extend the reporting period beyond the 7-year FCRA limit.

Verification of a DOFD that contradicts the payment history evidences failure to investigate.""",

    "dofd_after_date_opened": """The disputed account shows a Date of First Delinquency that precedes the Date Opened.

An account cannot become delinquent before it exists. This chronological impossibility indicates data corruption.

Verification of an impossible DOFD/Date Opened relationship is logically impossible.""",

    # -------------------------------------------------------------------------
    # Cross-Bureau Contradictions
    # -------------------------------------------------------------------------
    "dofd_mismatch": """The disputed account shows different Dates of First Delinquency across credit bureaus.

DOFD is an objective historical fact - the date cannot differ based on which bureau is reporting. One or more bureaus are reporting inaccurate information.

Verification without reconciling cross-bureau discrepancies is procedurally inadequate.""",

    "balance_mismatch": """The disputed account shows significantly different balances across credit bureaus.

The balance at any point in time is an objective fact. Material discrepancies indicate at least one bureau is reporting inaccurate information.

Verification without investigating cross-bureau balance discrepancies evidences perfunctory investigation.""",

    "status_mismatch": """The disputed account shows conflicting account status across credit bureaus.

An account cannot simultaneously be open and closed, or current and delinquent. Cross-bureau status conflicts indicate inaccurate reporting.

Verification of conflicting status information requires investigation, not mere confirmation.""",

    "cross_bureau": """The disputed information contains a provable deficiency that prevents verification.

**A single tradeline cannot possess multiple values for the same field across consumer reporting agencies.** At least one reported value is necessarily inaccurate. Verification of information that is contradicted across bureaus is not a verification of accuracy, but a confirmation of defective data.

Accordingly, the claimed verification evidences a perfunctory investigation rather than a reasonable reinvestigation as required by statute.""",

    "date_opened_mismatch": """The disputed account shows different Date Opened values across credit bureaus.

**A single tradeline cannot possess multiple "Date Opened" values across consumer reporting agencies.** At least one reported value is necessarily inaccurate. Verification of information that is contradicted across bureaus is not a verification of accuracy, but a confirmation of defective data.

Accordingly, the claimed verification evidences a perfunctory investigation rather than a reasonable reinvestigation as required by statute.""",

    # -------------------------------------------------------------------------
    # Obsolescence and Re-aging
    # -------------------------------------------------------------------------
    "obsolete_account": """The disputed account has exceeded the 7-year FCRA reporting period based on the Date of First Delinquency.

Under 15 U.S.C. § 1681c(a), accounts more than 7 years past the DOFD must be deleted. An obsolete account cannot be verified as accurate because its continued presence is itself the violation.

Verification of an obsolete account is meaningless - the account must be deleted regardless of its accuracy.""",

    "re_aging": """The disputed account shows evidence of re-aging - manipulation of dates to extend the reporting period beyond FCRA limits.

Re-aging violates 15 U.S.C. § 1681c(a) and cannot be legitimized through verification. The manipulation of dates is itself the violation.

Verification of a re-aged account compounds the violation rather than resolving it.""",

    "stale_reporting": """The disputed account shows reporting activity inconsistent with its last activity date, indicating stale or outdated data.

When an account's reported data does not reflect current status, verification requires obtaining current information - not confirming stale data.""",

    # -------------------------------------------------------------------------
    # Collection-Specific
    # -------------------------------------------------------------------------
    "double_jeopardy": """The disputed debt appears on the credit report twice - once from the original creditor and once from a debt collector - with both reporting a balance.

This is prohibited double-counting that artificially inflates the consumer's total debt load. When a debt is transferred, the original creditor must zero the balance.

Verification of duplicate debt reporting is procedurally impossible - one entry must be deleted or zeroed.""",

    "collection_balance_inflation": """The disputed collection account shows a balance that exceeds the legally collectible amount.

Under FDCPA §1692f(1), collectors cannot add unauthorized amounts. A balance exceeding original debt plus allowable interest and fees is unauthorized.

Verification of an inflated collection balance would validate an FDCPA violation.""",

    # -------------------------------------------------------------------------
    # Identity and Fraud Indicators
    # -------------------------------------------------------------------------
    "deceased_indicator_error": """The disputed record shows a deceased indicator for a living consumer.

This is not a disputed interpretation - the consumer is alive. Verification of a deceased indicator for a living person is factually impossible and indicates a mixed file or fraud.

Continued reporting of a deceased indicator on a living consumer's file requires deletion, not verification.""",

    "child_identity_theft": """The disputed account was opened when the consumer was a minor (under 18).

Minors cannot legally enter into credit agreements. An account opened before the consumer's 18th birthday is either identity theft or a data error.

Verification of an account opened by a minor is procedurally impossible without proof of legal guardian authorization.""",
}


def get_basis_for_non_compliance(violation_type: str, violation_desc: str = "") -> str:
    """
    Returns explanation of WHY verification was impossible for this violation type.

    This is the key to Tier-2 Canonical letters: proving verification was
    logically or procedurally impossible, not just inadequate.

    Args:
        violation_type: The ViolationType enum value (e.g., "missing_dofd")
        violation_desc: Optional description for generic fallback

    Returns:
        Multi-paragraph explanation of why verification was impossible
    """
    v_type = violation_type.lower().replace(" ", "_") if violation_type else ""

    if v_type in BASIS_FOR_NON_COMPLIANCE:
        return BASIS_FOR_NON_COMPLIANCE[v_type]

    # Generic fallback for unmapped violation types
    return f"""The disputed information contains a provable deficiency that prevents verification.

The specific deficiency - {violation_desc or violation_type.replace('_', ' ')} - represents a data integrity failure that cannot be verified as accurate through any legitimate investigation process.

Verification of information with documented deficiencies requires correction of those deficiencies, not mere confirmation that the deficient data exists.

Accordingly, the claimed verification evidences a perfunctory investigation rather than a reasonable reinvestigation as required by statute."""


# Canonical statute citations
STATUTE_CITATIONS = {
    # FCRA - Credit Reporting Agency (CRA) obligations
    "fcra_611_a_1_A": "15 U.S.C. § 1681i(a)(1)(A)",
    "fcra_611_a_5_B": "15 U.S.C. § 1681i(a)(5)(B)",
    "fcra_611_a_3": "15 U.S.C. § 1681i(a)(3)",
    "fcra_611_a_3_A": "15 U.S.C. § 1681i(a)(3)(A)",
    "fcra_611_a_3_B": "15 U.S.C. § 1681i(a)(3)(B)",
    "fcra_605_a": "15 U.S.C. § 1681c(a)",
    "fcra_616": "15 U.S.C. § 1681n",
    "fcra_617": "15 U.S.C. § 1681o",
    "fcra_623_b_1": "15 U.S.C. § 1681s-2(b)(1)",
    "fcra_623_b_1_A": "15 U.S.C. § 1681s-2(b)(1)(A)",

    # FDCPA - Debt Collector obligations
    "fdcpa_1692g_b": "15 U.S.C. § 1692g(b)",
    "fdcpa_1692e": "15 U.S.C. § 1692e",
    "fdcpa_1692e_2_A": "15 U.S.C. § 1692e(2)(A)",
    "fdcpa_1692e_5": "15 U.S.C. § 1692e(5)",
    "fdcpa_1692e_8": "15 U.S.C. § 1692e(8)",
    "fdcpa_1692f": "15 U.S.C. § 1692f",
    "fdcpa_1692k": "15 U.S.C. § 1692k",
}

# Response type to violation mapping for letter context
RESPONSE_VIOLATION_MAP = {
    "NO_RESPONSE": {
        "CRA": {
            "violation": "failure_to_investigate_within_30_days",
            "statute": "fcra_611_a_1_A",
            "description": "Failed to conduct investigation and provide results within 30 days"
        },
        "FURNISHER": {
            "violation": "failure_to_investigate_notice_of_dispute",
            "statute": "fcra_623_b_1_A",
            "description": "Failed to investigate notice of dispute from CRA"
        },
        "COLLECTOR": {
            "violation": "failure_to_provide_validation",
            "statute": "fdcpa_1692g_b",
            "description": "Failed to provide validation of debt"
        }
    },
    "VERIFIED": {
        "CRA": {
            "violation": "failure_to_conduct_reasonable_investigation",
            "statute": "fcra_611_a_1_A",
            "description": "Verified disputed information without conducting reasonable investigation"
        },
        "FURNISHER": {
            "violation": "failure_to_investigate",
            "statute": "fcra_623_b_1",
            "description": "Failed to conduct proper investigation upon notice of dispute"
        },
        "COLLECTOR": {
            "violation": "continued_collection_during_dispute",
            "statute": "fdcpa_1692g_b",
            "description": "Continued collection activity during dispute period"
        }
    },
    "REJECTED": {
        "CRA": {
            "violation": "invalid_frivolous_determination",
            "statute": "fcra_611_a_3",
            "description": "Improperly determined dispute to be frivolous or irrelevant"
        }
    },
    "REINSERTION_NO_NOTICE": {
        "CRA": {
            "violation": "reinsertion_without_notice",
            "statute": "fcra_611_a_5_B",
            "description": "Reinserted previously deleted information without required 5-day advance notice"
        }
    }
}


TEST_FOOTER = """
════════════════════════════════════════════════════════════════════════════════
                         TEST DOCUMENT – NOT MAILED
════════════════════════════════════════════════════════════════════════════════
This letter was generated in test mode for preview purposes only.
Do not mail, save to production records, or use for escalation.
════════════════════════════════════════════════════════════════════════════════
"""


# =============================================================================
# PHASE 2: CONTRADICTION NARRATIVE FORMATTER
# =============================================================================

# Severity display order (CRITICAL first)
SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def format_contradiction_section(contradictions: List[Any]) -> Optional[str]:
    """
    Format contradictions into "PROVABLE FACTUAL INACCURACIES" section.

    Args:
        contradictions: List of Contradiction objects or dicts with fields:
            - type, severity, description, impact, proof_hint (optional)

    Returns:
        Formatted section string, or None if no contradictions
    """
    if not contradictions:
        return None

    # Sort by severity (CRITICAL → HIGH → MEDIUM → LOW)
    def get_severity_key(c):
        if hasattr(c, 'severity'):
            sev = c.severity.value if hasattr(c.severity, 'value') else str(c.severity)
        elif isinstance(c, dict):
            sev = c.get('severity', 'low')
            sev = sev.value if hasattr(sev, 'value') else str(sev)
        else:
            sev = 'low'
        return SEVERITY_ORDER.get(sev.lower(), 99)

    sorted_contradictions = sorted(contradictions, key=get_severity_key)

    section = f"""PROVABLE FACTUAL INACCURACIES
{'=' * 50}

The following data elements reported by the furnisher are factually impossible and cannot be verified because they are demonstrably false:
"""

    for i, c in enumerate(sorted_contradictions, 1):
        # Extract fields (support both Contradiction objects and dicts)
        if hasattr(c, 'description'):
            # Contradiction dataclass
            severity = c.severity.value if hasattr(c.severity, 'value') else str(c.severity)
            description = c.description
            impact = c.impact
            proof_hint = getattr(c, 'proof_hint', None)
            rule_code = getattr(c, 'rule_code', None)
            bureau_claim = getattr(c, 'bureau_claim', None)
            contradiction = getattr(c, 'contradiction', None)
        else:
            # Dict format
            severity = c.get('severity', 'MEDIUM')
            severity = severity.value if hasattr(severity, 'value') else str(severity)
            description = c.get('description', '')
            impact = c.get('impact', '')
            proof_hint = c.get('proof_hint')
            rule_code = c.get('rule_code')
            bureau_claim = c.get('bureau_claim')
            contradiction = c.get('contradiction')

        severity_upper = severity.upper()

        section += f"\n{i}. [{severity_upper}] {description}"

        # Add bureau claim vs contradiction if available (facts first)
        if bureau_claim and contradiction:
            section += f"\n   • Reported: {bureau_claim}"
            section += f"\n   • Actual: {contradiction}"

        # Add impact
        if impact:
            section += f"\n   • Impact: {impact}"

        # Add proof hint if present (optional)
        if proof_hint:
            section += f"\n   • Evidence: {proof_hint}"

    section += f"""

These inaccuracies are not matters of interpretation or opinion. They represent mathematical or temporal impossibilities that cannot be verified through any reasonable investigation because they are objectively false."""

    return section


# =============================================================================
# PHASE 3: DETERMINISTIC DEMAND PRIORITIZATION
# =============================================================================

class PrimaryRemedy:
    """Primary remedy types determined by contradiction severity."""
    IMMEDIATE_DELETION = "IMMEDIATE_DELETION"
    CORRECTION_WITH_DOCUMENTATION = "CORRECTION_WITH_DOCUMENTATION"
    STANDARD_PROCEDURAL = "STANDARD_PROCEDURAL"


def determine_primary_remedy(
    contradictions: Optional[List[Any]],
    examiner_failure: bool = False,
    examiner_result: Optional[str] = None,
) -> str:
    """
    Determine primary remedy based on contradiction severity and examiner result.

    Rules (deterministic):
    1. If any contradiction has severity = CRITICAL → IMMEDIATE DELETION
    2. Else if 2+ contradictions have severity = HIGH → IMMEDIATE DELETION
    3. Else if 1 HIGH or any MEDIUM contradictions exist → CORRECTION WITH DOCUMENTATION
    4. Else → Fall back to standard procedural/statutory demands

    TIER 2 Enhancement:
    - Examiner FAIL always promotes to at least CORRECTION_WITH_DOCUMENTATION
    - FAIL_SYSTEMIC or FAIL_MISLEADING → IMMEDIATE_DELETION

    Args:
        contradictions: List of Contradiction objects or dicts
        examiner_failure: Whether Tier 2 examiner check failed
        examiner_result: The examiner result (FAIL_PERFUNCTORY, etc.)

    Returns:
        PrimaryRemedy constant string
    """
    # =========================================================================
    # TIER 2: Examiner failure upgrades remedy
    # =========================================================================
    if examiner_failure:
        if examiner_result in ["FAIL_SYSTEMIC", "FAIL_MISLEADING"]:
            # Systemic or misleading verification → immediate deletion
            return PrimaryRemedy.IMMEDIATE_DELETION
        else:
            # FAIL_PERFUNCTORY, FAIL_NO_RESULTS → at minimum correction
            # But check if contradictions would already push to deletion
            base_remedy = _calculate_base_remedy(contradictions)
            if base_remedy == PrimaryRemedy.IMMEDIATE_DELETION:
                return PrimaryRemedy.IMMEDIATE_DELETION
            return PrimaryRemedy.CORRECTION_WITH_DOCUMENTATION

    # =========================================================================
    # Tier 1: Original contradiction-based logic
    # =========================================================================
    return _calculate_base_remedy(contradictions)


def _calculate_base_remedy(contradictions: Optional[List[Any]]) -> str:
    """
    Calculate base remedy from contradictions only (Tier 1 logic).

    Internal helper function - preserves original logic.
    """
    if not contradictions:
        return PrimaryRemedy.STANDARD_PROCEDURAL

    # Count by severity
    critical_count = 0
    high_count = 0
    medium_count = 0

    for c in contradictions:
        # Extract severity (support both Contradiction objects and dicts)
        if hasattr(c, 'severity'):
            sev = c.severity.value if hasattr(c.severity, 'value') else str(c.severity)
        elif isinstance(c, dict):
            sev = c.get('severity', 'low')
            sev = sev.value if hasattr(sev, 'value') else str(sev)
        else:
            sev = 'low'

        sev_lower = sev.lower()

        if sev_lower == 'critical':
            critical_count += 1
        elif sev_lower == 'high':
            high_count += 1
        elif sev_lower == 'medium':
            medium_count += 1

    # Apply deterministic rules
    # Rule 1: Any CRITICAL → IMMEDIATE DELETION
    if critical_count > 0:
        return PrimaryRemedy.IMMEDIATE_DELETION

    # Rule 2: 2+ HIGH → IMMEDIATE DELETION
    if high_count >= 2:
        return PrimaryRemedy.IMMEDIATE_DELETION

    # Rule 3: 1 HIGH or any MEDIUM → CORRECTION WITH DOCUMENTATION
    if high_count >= 1 or medium_count >= 1:
        return PrimaryRemedy.CORRECTION_WITH_DOCUMENTATION

    # Rule 4: Fallback
    return PrimaryRemedy.STANDARD_PROCEDURAL


def generate_demanded_actions(
    primary_remedy: str,
    entity_name: str,
    response_type: str = "VERIFIED",
) -> List[str]:
    """
    Generate demanded actions ordered by primary remedy.

    Args:
        primary_remedy: PrimaryRemedy constant
        entity_name: Canonical entity name for letter
        response_type: VERIFIED or REJECTED

    Returns:
        List of demanded action strings, ordered by priority
    """
    actions = []

    if primary_remedy == PrimaryRemedy.IMMEDIATE_DELETION:
        # Lead with deletion demand - no ambiguity
        actions.append(
            f"IMMEDIATE DELETION of the disputed tradeline(s) from {entity_name}'s consumer file. "
            f"The factual impossibilities documented herein cannot be corrected because they are "
            f"demonstrably false. Under 15 U.S.C. § 1681e(b), information that cannot be verified "
            f"as accurate must be deleted."
        )
        actions.append(
            "Written confirmation of deletion sent to consumer within five (5) business days"
        )
        actions.append(
            "Notification to all parties who received consumer reports containing the disputed "
            "information within the preceding six (6) months"
        )
        # Secondary demands
        if response_type == "VERIFIED":
            actions.append(
                "Disclosure of the purported verification method, if any was actually conducted"
            )
        elif response_type == "REJECTED":
            actions.append(
                "Withdrawal of the frivolous/irrelevant determination"
            )

    elif primary_remedy == PrimaryRemedy.CORRECTION_WITH_DOCUMENTATION:
        # Lead with correction demand + documentation requirement
        actions.append(
            "Immediate correction of the inaccurate data elements identified herein, with "
            "supporting documentation demonstrating the corrected information is complete and accurate"
        )
        actions.append(
            f"Production of all documents relied upon by {entity_name} in reporting the disputed information"
        )
        actions.append(
            "Identification of the furnisher(s) contacted and date(s) of contact during any investigation"
        )
        if response_type == "VERIFIED":
            actions.append(
                "Disclosure of the method of verification used for each disputed item"
            )
            actions.append(
                "Written results of reinvestigation"
            )
        elif response_type == "REJECTED":
            actions.append(
                "Withdrawal of the frivolous/irrelevant determination and immediate investigation "
                "of the disputed items in compliance with 15 U.S.C. § 1681i(a)(1)(A)"
            )
            actions.append(
                "Written results of investigation within thirty (30) days of original dispute submission"
            )

    else:
        # Standard procedural demands (fallback - no contradictions)
        if response_type == "VERIFIED":
            actions = [
                "Disclosure of the method of verification used for each disputed item",
                "Production of all documents relied upon in the purported verification",
                "Identification of the furnisher(s) contacted and date(s) of contact",
                "Immediate reinvestigation using procedures that constitute a reasonable investigation",
                "Written results of reinvestigation",
            ]
        elif response_type == "REJECTED":
            actions = [
                "Withdrawal of the frivolous/irrelevant determination",
                "Immediate investigation of the disputed items in compliance with 15 U.S.C. § 1681i(a)(1)(A)",
                "Written results of investigation within thirty (30) days of original dispute submission",
                "If maintaining frivolous determination: Written notice identifying SPECIFIC information "
                "required to investigate, as mandated by § 1681i(a)(3)(B)(ii)",
            ]

    return actions


def format_demanded_actions_section(actions: List[str]) -> str:
    """
    Format demanded actions into letter section.

    Args:
        actions: List of action strings

    Returns:
        Formatted section string
    """
    section = f"""DEMANDED ACTIONS
{'-' * 50}

The following actions are demanded **within fifteen (15) days of receipt of this notice as a good-faith cure period**:
"""

    for i, action in enumerate(actions, 1):
        section += f"\n\n{i}. {action}"

    return section


class ResponseLetterGenerator:
    """
    Generates formal FCRA enforcement letters based on dispute responses.
    """

    def __init__(self, test_context: bool = False):
        self.generated_at = datetime.now()
        self.test_context = test_context

    def generate_enforcement_letter(
        self,
        consumer: Dict[str, str],
        entity_type: str,
        entity_name: str,
        violations: List[Dict[str, Any]],
        demanded_actions: List[str],
        dispute_date: Optional[datetime] = None,
        response_date: Optional[datetime] = None,
        response_type: Optional[str] = None,
        deadline_date: Optional[datetime] = None,
        include_willful_notice: bool = False
    ) -> str:
        """
        Generate a formal enforcement letter.

        Args:
            consumer: Dict with 'name' and 'address' keys
            entity_type: CRA, FURNISHER, or COLLECTOR
            entity_name: Name of the entity (e.g., "TransUnion")
            violations: List of violation dicts with type, statute, facts
            demanded_actions: List of demanded remedial actions
            dispute_date: Date original dispute was sent
            response_date: Date response was received (if any)
            response_type: Type of response (NO_RESPONSE, VERIFIED, etc.)
            deadline_date: Statutory deadline date
            include_willful_notice: Include willful noncompliance notice (§616)

        Returns:
            Formatted letter as string
        """
        letter_parts = []

        # Header
        letter_parts.append(self._generate_header(consumer, entity_name))

        # Subject line
        letter_parts.append(self._generate_subject_line(entity_type, response_type))

        # Opening paragraph
        letter_parts.append(self._generate_opening(
            consumer, entity_type, entity_name, dispute_date, response_type
        ))

        # Violation assertions
        letter_parts.append(self._generate_violation_section(violations, entity_type))

        # Timeline facts (if applicable)
        if dispute_date or response_date or deadline_date:
            letter_parts.append(self._generate_timeline_section(
                dispute_date, response_date, deadline_date, response_type
            ))

        # Demands section
        letter_parts.append(self._generate_demands_section(demanded_actions))

        # Willful noncompliance notice (if applicable)
        if include_willful_notice:
            letter_parts.append(self._generate_willful_notice(entity_type))

        # Closing
        letter_parts.append(self._generate_closing(consumer))

        letter = "\n\n".join(filter(None, letter_parts))

        # Append test footer if in test mode
        if self.test_context:
            letter += TEST_FOOTER

        return letter

    def _generate_header(self, consumer: Dict[str, str], entity_name: str) -> str:
        """Generate letter header with date and addresses."""
        today = datetime.now().strftime("%B %d, %Y")

        consumer_block = f"""{consumer.get('name', '[CONSUMER NAME]')}
{consumer.get('address', '[CONSUMER ADDRESS]')}"""

        return f"""{consumer_block}

{today}

{entity_name}
Consumer Dispute Department
[ADDRESS ON FILE]

Via Certified Mail, Return Receipt Requested"""

    def _generate_subject_line(self, entity_type: str, response_type: Optional[str]) -> str:
        """Generate subject line based on entity and response type."""
        if response_type == "NO_RESPONSE":
            return "RE: FORMAL NOTICE OF STATUTORY VIOLATION - Failure to Respond Within Statutory Deadline"
        elif response_type == "VERIFIED":
            return "RE: FORMAL NOTICE OF STATUTORY VIOLATION - Verification Without Reasonable Investigation"
        elif response_type == "REJECTED":
            return "RE: FORMAL NOTICE OF STATUTORY VIOLATION - Improper Frivolous/Irrelevant Determination"
        elif response_type == "REINSERTION_NO_NOTICE":
            return "RE: FORMAL NOTICE OF STATUTORY VIOLATION - Reinsertion Without Required Notice"
        else:
            return "RE: FORMAL NOTICE OF STATUTORY VIOLATIONS"

    def _generate_opening(
        self,
        consumer: Dict[str, str],
        entity_type: str,
        entity_name: str,
        dispute_date: Optional[datetime],
        response_type: Optional[str]
    ) -> str:
        """Generate opening paragraph asserting the dispute context."""
        consumer_name = consumer.get('name', 'the undersigned consumer')

        if dispute_date:
            date_str = dispute_date.strftime("%B %d, %Y")
            dispute_context = f"On {date_str}, {consumer_name} submitted a written dispute"
        else:
            dispute_context = f"{consumer_name} previously submitted a written dispute"

        entity_role = {
            "CRA": "credit reporting agency",
            "FURNISHER": "furnisher of information",
            "COLLECTOR": "debt collector"
        }.get(entity_type, "entity")

        opening = f"""{dispute_context} to {entity_name} regarding inaccurate information appearing in {consumer_name}'s consumer file.

{entity_name}, as a {entity_role} subject to the Fair Credit Reporting Act (FCRA), 15 U.S.C. § 1681 et seq."""

        if entity_type == "COLLECTOR":
            opening += " and the Fair Debt Collection Practices Act (FDCPA), 15 U.S.C. § 1692 et seq."

        opening += ", bears specific statutory obligations upon receipt of a consumer dispute."

        if response_type == "NO_RESPONSE":
            opening += f"\n\n{entity_name} has failed to satisfy these obligations."
        elif response_type == "VERIFIED":
            opening += f"\n\n{entity_name}'s verification response fails to satisfy its statutory obligations and compounds its liability."
        elif response_type == "REJECTED":
            opening += f"\n\n{entity_name}'s determination that this dispute is frivolous or irrelevant fails to comply with statutory requirements."

        return opening

    def _generate_violation_section(
        self,
        violations: List[Dict[str, Any]],
        entity_type: str
    ) -> str:
        """Generate the violations assertion section."""
        if not violations:
            return ""

        section = "STATUTORY VIOLATIONS\n" + "=" * 50

        for i, violation in enumerate(violations, 1):
            v_type = violation.get("type", "UNKNOWN")
            statute_key = violation.get("statute", "")
            statute_citation = STATUTE_CITATIONS.get(statute_key, statute_key)
            facts = violation.get("facts", [])
            account = violation.get("account", {})

            creditor = account.get("creditor", "")
            account_mask = account.get("account_mask", "")
            account_str = f" ({creditor} {account_mask})" if creditor else ""

            section += f"\n\nViolation {i}: {self._format_violation_type(v_type)}{account_str}"
            section += f"\nStatute: {statute_citation}"

            if facts:
                section += "\n\nEstablished Facts:"
                for fact in facts:
                    section += f"\n    - {fact}"

        return section

    def _format_violation_type(self, v_type: str) -> str:
        """Format violation type for display."""
        return format_violation_display(v_type)

    def _generate_timeline_section(
        self,
        dispute_date: Optional[datetime],
        response_date: Optional[datetime],
        deadline_date: Optional[datetime],
        response_type: Optional[str]
    ) -> str:
        """Generate timeline section showing statutory breach."""
        section = "TIMELINE OF EVENTS\n" + "-" * 50

        if dispute_date:
            section += f"\n\nDispute Submitted: {dispute_date.strftime('%B %d, %Y')}"

        if deadline_date:
            section += f"\nStatutory Deadline: {deadline_date.strftime('%B %d, %Y')}"

        if response_type == "NO_RESPONSE":
            section += f"\nResponse Received: NONE"
            if deadline_date and datetime.now() > deadline_date:
                days_overdue = (datetime.now() - deadline_date).days
                section += f"\nDays Past Deadline: {days_overdue}"
        elif response_date:
            section += f"\nResponse Received: {response_date.strftime('%B %d, %Y')}"
            if deadline_date and response_date > deadline_date:
                days_late = (response_date - deadline_date).days
                section += f"\nDays Past Deadline: {days_late}"

        return section

    def _generate_demands_section(self, demanded_actions: List[str]) -> str:
        """Generate the demands section."""
        if not demanded_actions:
            return ""

        section = "DEMANDED ACTIONS\n" + "-" * 50
        section += "\n\nThe following actions are demanded within fifteen (15) days of receipt of this notice:"

        for i, action in enumerate(demanded_actions, 1):
            section += f"\n\n{i}. {action}"

        return section

    def _generate_willful_notice(self, entity_type: str) -> str:
        """Generate rights-preservation notice (single sentence, no damages lecture)."""
        return f"""RIGHTS PRESERVATION
{'-' * 50}

Nothing in this correspondence shall be construed as a waiver of any rights or remedies available under 15 U.S.C. §§ 1681n or 1681o for negligent or willful noncompliance."""

    def _generate_closing(self, consumer: Dict[str, str]) -> str:
        """Generate the closing and signature block (no regulatory cc at this stage)."""
        consumer_name = consumer.get('name', '[CONSUMER NAME]')

        return f"""RESPONSE REQUIRED
{'-' * 50}

A written response addressing each demanded action is required within fifteen (15) days of receipt of this notice. Failure to respond or inadequate response will be documented and may be submitted as evidence in subsequent proceedings.

All future correspondence regarding this matter should be directed to the undersigned at the address provided above.



Respectfully submitted,



____________________________________
{consumer_name}

Enclosures:
- Copy of original dispute letter
- Certified mail receipt
- Supporting documentation"""


def generate_no_response_letter(
    consumer: Dict[str, str],
    entity_type: str,
    entity_name: str,
    original_violations: List[Dict[str, Any]],
    dispute_date: datetime,
    deadline_date: datetime,
    test_context: bool = False,
) -> str:
    """
    Generate Tier-2 Canonical enforcement letter for NO_RESPONSE scenario.

    TIER-2 CANONICAL STRUCTURE:
    - Fact-first, not statute-first
    - No hardcoded deadline math or "days past deadline"
    - No specific deadline date assertions (safe for test mode)
    - Proves failure to respond is a COMPLETED procedural failure
    - Frames as examiner failure, not consumer disagreement
    - Single statutory theory: Failure to Provide Results (§1681i(a)(1)(A), §1681i(a)(6)(A))

    Key sections:
    1. Header
    2. Subject: "STATUTORY NON-COMPLIANCE" with "Failure to Provide Results of Reinvestigation"
    3. Opening: Fact-focused (dispute submitted, no results provided)
    4. ESTABLISHED FACTS: Bullet points without specific dates
    5. BASIS FOR NON-COMPLIANCE: WHY failure to respond is non-compliant
    6. STATUTORY FRAMEWORK: Clean statement of law
    7. STATUTORY NON-COMPLIANCE: Summary with statute citations
    8. DEMANDED ACTIONS: Simplified, no redundant timeframes
    9. RIGHTS PRESERVATION
    10. RESPONSE REQUIRED + signature

    Args:
        test_context: If True, appends test footer.
    """
    # Canonicalize entity name
    canonical_entity = canonicalize_entity_name(entity_name)
    consumer_name = consumer.get('name', '[CONSUMER NAME]')
    consumer_address = consumer.get('address', '[CONSUMER ADDRESS]')
    today = datetime.now().strftime("%B %d, %Y")

    # Build the letter
    letter_parts = []

    # =========================================================================
    # HEADER
    # =========================================================================
    header = f"""{consumer_name}
{consumer_address}

{today}

{canonical_entity}
Consumer Dispute Department
[ADDRESS ON FILE]

Via Certified Mail, Return Receipt Requested"""
    letter_parts.append(header)

    # =========================================================================
    # SUBJECT LINE - "NON-COMPLIANCE" not "VIOLATION"
    # =========================================================================
    subject = """RE: FORMAL NOTICE OF STATUTORY NON-COMPLIANCE

Failure to Provide Results of Reinvestigation"""
    letter_parts.append(subject)

    # =========================================================================
    # OPENING PARAGRAPH - Fact-focused, no specific deadline dates
    # =========================================================================
    opening = f"""On {dispute_date.strftime('%B %d, %Y')}, {consumer_name} submitted a written dispute regarding inaccurate information appearing in their consumer file maintained by {canonical_entity}.

Pursuant to the Fair Credit Reporting Act, {canonical_entity} was required to conduct a reinvestigation and provide written notice of the results within the statutory timeframe.

As of the date of this correspondence, no results of reinvestigation have been provided.

This correspondence serves as formal notice that {canonical_entity} has failed to comply with mandatory procedural requirements governing dispute handling."""
    letter_parts.append(opening)

    # =========================================================================
    # ESTABLISHED FACTS - No specific dates, safe for test mode
    # =========================================================================
    established_facts = f"""ESTABLISHED FACTS
{'=' * 50}

• Written dispute submitted
• Statutory reinvestigation period elapsed
• No results of reinvestigation provided
• No notice of completion, extension, or findings issued"""
    letter_parts.append(established_facts)

    # =========================================================================
    # BASIS FOR NON-COMPLIANCE - The key Tier-2 addition
    # Proves failure to respond is a completed procedural failure
    # =========================================================================
    basis_section = f"""BASIS FOR NON-COMPLIANCE
{'=' * 50}

Under 15 U.S.C. § 1681i(a)(1)(A) and § 1681i(a)(6)(A), a consumer reporting agency must:

• Conduct a reasonable reinvestigation
• Provide written notice of the results within the statutory period

Where the statutory period expires without results, compliance becomes procedurally impossible.

Failure to provide results within the required timeframe constitutes a completed procedural failure rather than a curable delay."""
    letter_parts.append(basis_section)

    # =========================================================================
    # STATUTORY FRAMEWORK - Clean statement of law
    # =========================================================================
    statutory_framework = f"""STATUTORY FRAMEWORK
{'=' * 50}

Pursuant to 15 U.S.C. § 1681i(a)(1)(A) and § 1681i(a)(6)(A), consumer reporting agencies are required to complete reinvestigations and provide written notice of results within the statutory timeframe.

Failure to do so constitutes non-compliance."""
    letter_parts.append(statutory_framework)

    # =========================================================================
    # STATUTORY NON-COMPLIANCE - Summary
    # =========================================================================
    violation_section = f"""STATUTORY NON-COMPLIANCE
{'=' * 50}

Non-Compliance: Failure to Provide Results of Reinvestigation
Statutes: 15 U.S.C. § 1681i(a)(1)(A); § 1681i(a)(6)(A)

By failing to provide results of reinvestigation, {canonical_entity} did not comply with mandatory procedural requirements."""
    letter_parts.append(violation_section)

    # =========================================================================
    # DEMANDED ACTIONS - Simplified, no redundant timeframes
    # =========================================================================
    demands = f"""DEMANDED ACTIONS
{'=' * 50}

The following actions are required:

1. Immediate completion of the reinvestigation

2. Written results of reinvestigation

3. Correction or deletion of any information that cannot be verified

Failure to cure this non-compliance will be recorded as continued non-compliance and escalated accordingly."""
    letter_parts.append(demands)

    # =========================================================================
    # RIGHTS PRESERVATION
    # =========================================================================
    rights = f"""RIGHTS PRESERVATION
{'=' * 50}

Nothing in this correspondence shall be construed as a waiver of any rights or remedies available under 15 U.S.C. §§ 1681n or 1681o."""
    letter_parts.append(rights)

    # =========================================================================
    # RESPONSE REQUIRED + CLOSING
    # =========================================================================
    closing = f"""RESPONSE REQUIRED
{'=' * 50}

A written response addressing each demanded action is required.

All future correspondence regarding this matter should be directed to the address listed above.



Respectfully submitted,



____________________________________
{consumer_name}

Enclosures:
- Copy of original dispute
- Proof of mailing
- Supporting documentation"""
    letter_parts.append(closing)

    # =========================================================================
    # TEST MODE FOOTER (if applicable)
    # =========================================================================
    if test_context:
        test_footer = f"""{'═' * 80}
                         TEST DOCUMENT – NOT MAILED
{'═' * 80}
This document was generated in test mode for preview and validation purposes.
Do not mail, save to production records, or use for escalation.
{'═' * 80}"""
        letter_parts.append(test_footer)

    return "\n\n".join(letter_parts)


def generate_verified_response_letter(
    consumer: Dict[str, str],
    entity_type: str,
    entity_name: str,
    original_violations: List[Dict[str, Any]],
    dispute_date: datetime,
    response_date: datetime,
    contradictions: Optional[List[Any]] = None,
) -> str:
    """
    Generate Tier-2 Canonical enforcement letter for VERIFIED response scenario.

    TIER-2 CANONICAL STRUCTURE:
    - Fact-first, not statute-first
    - Proves verification was IMPOSSIBLE, not just inadequate
    - Frames as examiner failure, not consumer disagreement
    - Single statutory theory: Verification Without Reasonable Investigation (§611(a)(1)(A))

    Key sections:
    1. Header
    2. Subject: "STATUTORY NON-COMPLIANCE" (not "VIOLATION")
    3. Opening: Fact-focused (dispute submitted, verification claimed)
    4. STATUTORY FRAMEWORK: Clean statement of law
    5. ESTABLISHED FACTS: Bullet points of what happened
    6. DISPUTED ITEM: Furnisher, Account, Violation format
    7. BASIS FOR NON-COMPLIANCE: WHY verification was impossible
    8. STATUTORY VIOLATION: Summary with statute citation
    9. DEMANDED ACTIONS: Dynamic based on severity
    10. RIGHTS PRESERVATION
    11. RESPONSE REQUIRED + signature
    """
    # Canonicalize entity name
    canonical_entity = canonicalize_entity_name(entity_name)
    consumer_name = consumer.get('name', '[CONSUMER NAME]')
    consumer_address = consumer.get('address', '[CONSUMER ADDRESS]')
    today = datetime.now().strftime("%B %d, %Y")

    # Extract primary violation for BASIS section
    primary_violation = original_violations[0] if original_violations else {}
    primary_v_type = primary_violation.get("violation_type", primary_violation.get("type", ""))
    primary_creditor = primary_violation.get("creditor_name", "Unknown Furnisher")
    primary_account = primary_violation.get("account_number_masked", "[ACCOUNT]")
    primary_desc = primary_violation.get("description", format_violation_display(primary_v_type) if primary_v_type else "Disputed information")

    # Auto-assign statute
    explicit_statute = primary_violation.get("primary_statute", primary_violation.get("statute", ""))
    primary_statute = get_statute_for_violation(primary_v_type, explicit_statute)

    # Build the letter
    letter_parts = []

    # =========================================================================
    # HEADER
    # =========================================================================
    header = f"""{consumer_name}
{consumer_address}

{today}

{canonical_entity}
Consumer Dispute Department
[ADDRESS ON FILE]

Via Certified Mail, Return Receipt Requested"""
    letter_parts.append(header)

    # =========================================================================
    # SUBJECT LINE - "NON-COMPLIANCE" not "VIOLATION"
    # =========================================================================
    subject = """RE: FORMAL NOTICE OF STATUTORY NON-COMPLIANCE

Verification Without Reasonable Investigation & Failure to Assure Accuracy"""
    letter_parts.append(subject)

    # =========================================================================
    # OPENING PARAGRAPH - Fact-focused, establishes what happened
    # =========================================================================
    opening = f"""On {dispute_date.strftime('%B %d, %Y')}, {consumer_name} submitted a written dispute regarding inaccurate information appearing in their consumer file maintained by {canonical_entity}.

On {response_date.strftime('%B %d, %Y')}, {canonical_entity} responded by claiming the disputed information was "VERIFIED."

This correspondence serves as formal notice that the claimed verification fails to satisfy the statutory requirements of a reasonable reinvestigation and the duty to assure maximum possible accuracy."""
    letter_parts.append(opening)

    # =========================================================================
    # STATUTORY FRAMEWORK - Clean statement of law
    # =========================================================================
    statutory_framework = f"""STATUTORY FRAMEWORK
{'=' * 50}

Pursuant to **15 U.S.C. § 1681i(a)(1)(A)**, upon receipt of a consumer dispute, a consumer reporting agency is required to conduct a reasonable reinvestigation to determine whether the disputed information is inaccurate.

Additionally, pursuant to **15 U.S.C. § 1681e(b)**, a consumer reporting agency must follow reasonable procedures to assure **maximum possible accuracy** of the information reported. Information that contains cross-bureau inconsistencies is not capable of maximum possible accuracy and therefore cannot be verified as accurate."""
    letter_parts.append(statutory_framework)

    # =========================================================================
    # ESTABLISHED FACTS - Bullet points
    # =========================================================================
    established_facts = f"""ESTABLISHED FACTS
{'=' * 50}

• Written dispute submitted on {dispute_date.strftime('%B %d, %Y')}
• Response received on {response_date.strftime('%B %d, %Y')} asserting verification
• Disputed tradeline remains unchanged
• Mandatory compliance data remains missing or deficient"""
    letter_parts.append(established_facts)

    # =========================================================================
    # DISPUTED ITEM - Clean format
    # =========================================================================
    disputed_item = f"""DISPUTED ITEM
{'=' * 50}

• Furnisher: {primary_creditor}
• Account: {primary_account}
• Violation: {primary_desc}"""

    # Add additional items if multiple violations
    if len(original_violations) > 1:
        disputed_item += "\n\nAdditional Disputed Items:"
        for v in original_violations[1:]:
            v_creditor = v.get("creditor_name", "Unknown")
            v_account = v.get("account_number_masked", "[ACCOUNT]")
            v_type = v.get("violation_type", v.get("type", ""))
            v_desc = v.get("description", format_violation_display(v_type) if v_type else "Disputed information")
            disputed_item += f"\n• {v_creditor} ({v_account}) - {v_desc}"

    letter_parts.append(disputed_item)

    # =========================================================================
    # BASIS FOR NON-COMPLIANCE - The key Tier-2 addition
    # Explains WHY verification was impossible
    # =========================================================================
    basis_text = get_basis_for_non_compliance(primary_v_type, primary_desc)

    basis_section = f"""BASIS FOR NON-COMPLIANCE
{'=' * 50}

{basis_text}"""
    letter_parts.append(basis_section)

    # =========================================================================
    # STATUTORY VIOLATION - Summary
    # =========================================================================
    violation_section = f"""STATUTORY VIOLATION
{'=' * 50}

**Violation:** Verification Without Reasonable Investigation and Failure to Assure Maximum Possible Accuracy
**Statutes:** 15 U.S.C. §§ 1681i(a)(1)(A), 1681e(b)

By verifying information that is logically impossible and substantiated as inaccurate by cross-bureau data, {canonical_entity} failed to conduct a reasonable reinvestigation and is in statutory non-compliance."""
    letter_parts.append(violation_section)

    # =========================================================================
    # DEMANDED ACTIONS - Dynamic based on severity
    # =========================================================================
    primary_remedy = determine_primary_remedy(contradictions)
    actions = generate_demanded_actions(primary_remedy, canonical_entity, "VERIFIED")
    demands = format_demanded_actions_section(actions)
    letter_parts.append(demands)

    # =========================================================================
    # RIGHTS PRESERVATION
    # =========================================================================
    rights = f"""RIGHTS PRESERVATION
{'=' * 50}

Nothing in this correspondence shall be construed as a waiver of any rights or remedies available under 15 U.S.C. §§ 1681n or 1681o for negligent or willful non-compliance."""
    letter_parts.append(rights)

    # =========================================================================
    # RESPONSE REQUIRED + CLOSING
    # =========================================================================
    closing = f"""RESPONSE REQUIRED
{'=' * 50}

A written response addressing each demanded action is required.

Failure to cure this violation or to produce substantiating documentation will be recorded as continued non-compliance and escalated accordingly.

All future correspondence regarding this matter should be directed to the address listed above.



Respectfully submitted,



____________________________________
{consumer_name}

Enclosures:
- Copy of original dispute
- Proof of mailing
- Supporting documentation"""
    letter_parts.append(closing)

    return "\n\n".join(letter_parts)


def generate_rejected_response_letter(
    consumer: Dict[str, str],
    entity_type: str,
    entity_name: str,
    original_violations: List[Dict[str, Any]],
    dispute_date: datetime,
    rejection_date: datetime,
    rejection_reason: str = None,
    has_5_day_notice: bool = False,
    has_specific_reason: bool = False,
    contradictions: Optional[List[Any]] = None,
) -> str:
    """
    Generate Tier-2 Canonical enforcement letter for REJECTED (Frivolous/Irrelevant) response.

    TIER-2 CANONICAL STRUCTURE:
    - Fact-first, not statute-first
    - Proves frivolous determination was PROCEDURALLY INVALID
    - Frames as examiner failure, not consumer disagreement
    - Single statutory theory: Improper Frivolous Determination (§1681i(a)(3)(B))

    Key sections:
    1. Header
    2. Subject: "STATUTORY NON-COMPLIANCE" with "Improper Frivolous/Irrelevant Determination"
    3. Opening: Fact-focused (dispute submitted, frivolous designation made)
    4. ESTABLISHED FACTS: Bullet points of what happened
    5. DISPUTED ITEM: Furnisher, Account, Violation format
    6. BASIS FOR NON-COMPLIANCE: WHY frivolous determination was invalid
    7. STATUTORY FRAMEWORK: Clean statement of law
    8. STATUTORY NON-COMPLIANCE: Summary with statute citation
    9. DEMANDED ACTIONS: Dynamic based on severity
    10. RIGHTS PRESERVATION
    11. RESPONSE REQUIRED + signature
    """
    # Canonicalize entity name
    canonical_entity = canonicalize_entity_name(entity_name)
    consumer_name = consumer.get('name', '[CONSUMER NAME]')
    consumer_address = consumer.get('address', '[CONSUMER ADDRESS]')
    today = datetime.now().strftime("%B %d, %Y")

    # Extract primary violation for DISPUTED ITEM section
    primary_violation = original_violations[0] if original_violations else {}
    primary_v_type = primary_violation.get("violation_type", primary_violation.get("type", ""))
    primary_creditor = primary_violation.get("creditor_name", "Unknown Furnisher")
    primary_account = primary_violation.get("account_number_masked", "[ACCOUNT]")
    primary_desc = primary_violation.get("description", format_violation_display(primary_v_type) if primary_v_type else "Disputed information")

    # Build the letter
    letter_parts = []

    # =========================================================================
    # HEADER
    # =========================================================================
    header = f"""{consumer_name}
{consumer_address}

{today}

{canonical_entity}
Consumer Dispute Department
[ADDRESS ON FILE]

Via Certified Mail, Return Receipt Requested"""
    letter_parts.append(header)

    # =========================================================================
    # SUBJECT LINE - "NON-COMPLIANCE" not "VIOLATION"
    # =========================================================================
    subject = """RE: FORMAL NOTICE OF STATUTORY NON-COMPLIANCE

Improper Frivolous / Irrelevant Determination"""
    letter_parts.append(subject)

    # =========================================================================
    # OPENING PARAGRAPH - Fact-focused, establishes what happened
    # =========================================================================
    opening = f"""On {dispute_date.strftime('%B %d, %Y')}, {consumer_name} submitted a written dispute regarding inaccurate information appearing in their consumer file maintained by {canonical_entity}.

{canonical_entity} subsequently designated the dispute as frivolous or irrelevant.

This correspondence serves as formal notice that the frivolous determination fails to satisfy statutory prerequisites and constitutes a distinct compliance failure."""
    letter_parts.append(opening)

    # =========================================================================
    # ESTABLISHED FACTS - Bullet points
    # =========================================================================
    established_facts = f"""ESTABLISHED FACTS
{'=' * 50}

• Written dispute submitted on {dispute_date.strftime('%B %d, %Y')}
• Dispute designated as frivolous or irrelevant on {rejection_date.strftime('%B %d, %Y')}
• No written notice identifying specific deficiencies was provided
• No identification of information required to investigate was provided"""
    letter_parts.append(established_facts)

    # =========================================================================
    # DISPUTED ITEM - Clean format
    # =========================================================================
    disputed_item = f"""DISPUTED ITEM
{'=' * 50}

• Furnisher: {primary_creditor}
• Account: {primary_account}
• Violation: {primary_desc}"""

    # Add additional items if multiple violations
    if len(original_violations) > 1:
        disputed_item += "\n\nAdditional Disputed Items:"
        for v in original_violations[1:]:
            v_creditor = v.get("creditor_name", "Unknown")
            v_account = v.get("account_number_masked", "[ACCOUNT]")
            v_type = v.get("violation_type", v.get("type", ""))
            v_desc = v.get("description", format_violation_display(v_type) if v_type else "Disputed information")
            disputed_item += f"\n• {v_creditor} ({v_account}) - {v_desc}"

    letter_parts.append(disputed_item)

    # =========================================================================
    # BASIS FOR NON-COMPLIANCE - The key Tier-2 addition
    # Proves frivolous determination was procedurally invalid
    # =========================================================================
    basis_section = f"""BASIS FOR NON-COMPLIANCE
{'=' * 50}

A consumer reporting agency may treat a dispute as frivolous or irrelevant only if the statutory prerequisites of 15 U.S.C. § 1681i(a)(3)(B) are satisfied.

Specifically, the agency must:
• Identify the basis for the frivolous or irrelevant determination
• Specify what information is required to investigate the disputed item

In this case, {canonical_entity} failed to:
• Identify which portion of the dispute was allegedly frivolous or deficient
• Identify any specific information required to conduct an investigation

Absent these disclosures, a frivolous or irrelevant determination could not have been lawfully made.

A determination lacking required notice and specificity is procedurally invalid and evidences examiner non-compliance rather than a discretionary judgment."""
    letter_parts.append(basis_section)

    # =========================================================================
    # STATUTORY FRAMEWORK - Clean statement of law
    # =========================================================================
    statutory_framework = f"""STATUTORY FRAMEWORK
{'=' * 50}

Pursuant to 15 U.S.C. § 1681i(a)(3)(B), a consumer reporting agency may reject a dispute as frivolous or irrelevant only if statutory notice and disclosure requirements are satisfied.

Failure to meet these prerequisites renders the determination invalid."""
    letter_parts.append(statutory_framework)

    # =========================================================================
    # STATUTORY NON-COMPLIANCE - Summary
    # =========================================================================
    violation_section = f"""STATUTORY NON-COMPLIANCE
{'=' * 50}

Non-Compliance: Improper Frivolous / Irrelevant Determination
Statute: 15 U.S.C. § 1681i(a)(3)(B)

By rejecting the dispute without satisfying mandatory procedural requirements, {canonical_entity} failed to comply with statutory obligations."""
    letter_parts.append(violation_section)

    # =========================================================================
    # DEMANDED ACTIONS - Dynamic based on severity
    # =========================================================================
    demands = f"""DEMANDED ACTIONS
{'=' * 50}

The following actions are required:

1. Withdrawal of the frivolous / irrelevant determination

2. Immediate investigation of the disputed item in compliance with 15 U.S.C. § 1681i(a)(1)(A)

3. Written results of investigation

4. If maintaining the frivolous determination: written notice identifying specific information required to investigate, as mandated by statute

Failure to cure this non-compliance or to produce substantiating documentation will be recorded as continued non-compliance and escalated accordingly."""
    letter_parts.append(demands)

    # =========================================================================
    # RIGHTS PRESERVATION
    # =========================================================================
    rights = f"""RIGHTS PRESERVATION
{'=' * 50}

Nothing in this correspondence shall be construed as a waiver of any rights or remedies available under 15 U.S.C. §§ 1681n or 1681o for negligent or willful non-compliance."""
    letter_parts.append(rights)

    # =========================================================================
    # RESPONSE REQUIRED + CLOSING
    # =========================================================================
    closing = f"""RESPONSE REQUIRED
{'=' * 50}

A written response addressing each demanded action is required.

All future correspondence regarding this matter should be directed to the address listed above.



Respectfully submitted,



____________________________________
{consumer_name}

Enclosures:
- Copy of original dispute
- Proof of mailing
- Supporting documentation"""
    letter_parts.append(closing)

    return "\n\n".join(letter_parts)


def generate_reinsertion_letter(
    consumer: Dict[str, str],
    entity_name: str,
    account: Dict[str, str],
    deletion_date: datetime,
    reinsertion_date: datetime,
    notice_received: bool = False
) -> str:
    """
    DEPRECATED: Use generate_reinsertion_response_letter() for production letters.

    Generate enforcement letter for reinsertion without notice.
    Under FCRA §611(a)(5)(B), CRAs must provide 5-day advance written notice
    before reinserting previously deleted information.
    """
    generator = ResponseLetterGenerator()

    facts = [
        f"Disputed tradeline was deleted on or about {deletion_date.strftime('%B %d, %Y')}",
        f"Same tradeline was reinserted on or about {reinsertion_date.strftime('%B %d, %Y')}",
    ]

    if not notice_received:
        facts.append("No written notice of reinsertion was received by consumer")
        facts.append("No notice was received within five (5) business days prior to reinsertion as required by statute")
    else:
        facts.append("Notice received was not provided within the required five (5) business day advance period")

    violations = [{
        "type": "REINSERTION_NO_NOTICE",
        "statute": "fcra_611_a_5_B",
        "facts": facts,
        "account": account
    }]

    demanded_actions = [
        "Immediate deletion of the reinserted tradeline",
        "Written confirmation of deletion within five (5) business days",
        "Disclosure of the furnisher certification relied upon for reinsertion, if any",
        "Identification of the individual(s) responsible for reinsertion decision"
    ]

    return generator.generate_enforcement_letter(
        consumer=consumer,
        entity_type="CRA",
        entity_name=entity_name,
        violations=violations,
        demanded_actions=demanded_actions,
        response_type="REINSERTION_NO_NOTICE",
        include_willful_notice=True
    )


def generate_reinsertion_response_letter(
    consumer: Dict[str, str],
    entity_type: str,
    entity_name: str,
    original_violations: List[Dict[str, Any]],
    reinsertion_date: datetime,
    deletion_date: datetime = None,
    notice_received_date: datetime = None,
) -> str:
    """
    Generate Tier-2 Canonical enforcement letter for REINSERTION scenario.

    TIER-2 CANONICAL STRUCTURE:
    - Fact-first, not statute-first
    - Proves lawful reinsertion was PROCEDURALLY IMPOSSIBLE
    - Frames as examiner failure, not consumer disagreement
    - Single statutory theory: Reinsertion Without Required Certification and Notice (§1681i(a)(5)(B))

    Key sections:
    1. Header
    2. Subject: "STATUTORY NON-COMPLIANCE" with "Reinsertion Without Required Certification and Notice"
    3. Opening: Fact-focused (deletion occurred, reinsertion detected)
    4. ESTABLISHED FACTS: Bullet points without asserting specific compliance failures
    5. REINSERTED ITEM: Clean format
    6. BASIS FOR NON-COMPLIANCE: WHY lawful reinsertion could not have occurred
    7. STATUTORY FRAMEWORK: Clean statement of law
    8. STATUTORY NON-COMPLIANCE: Summary with statute citation
    9. DEMANDED ACTIONS: Simplified, no redundant timeframes
    10. RIGHTS PRESERVATION
    11. RESPONSE REQUIRED + signature
    """
    # Canonicalize entity name
    canonical_entity = canonicalize_entity_name(entity_name)
    consumer_name = consumer.get('name', '[CONSUMER NAME]')
    consumer_address = consumer.get('address', '[CONSUMER ADDRESS]')
    today = datetime.now().strftime("%B %d, %Y")

    # Build reinserted items list
    reinserted_items = []
    for v in original_violations:
        creditor = v.get("creditor_name", "")
        account_mask = v.get("account_number_masked", "")
        reinserted_items.append({
            "creditor": creditor if creditor else "Unknown Furnisher",
            "account": account_mask if account_mask else "[ACCOUNT]"
        })

    # Build the letter
    letter_parts = []

    # =========================================================================
    # HEADER
    # =========================================================================
    header = f"""{consumer_name}
{consumer_address}

{today}

{canonical_entity}
Consumer Dispute Department
[ADDRESS ON FILE]

Via Certified Mail, Return Receipt Requested"""
    letter_parts.append(header)

    # =========================================================================
    # SUBJECT LINE - "NON-COMPLIANCE" not "VIOLATION"
    # =========================================================================
    subject = """RE: FORMAL NOTICE OF STATUTORY NON-COMPLIANCE

Reinsertion Without Required Certification and Notice"""
    letter_parts.append(subject)

    # =========================================================================
    # OPENING PARAGRAPH - Fact-focused
    # =========================================================================
    opening = f"""{consumer_name} previously disputed inaccurate information appearing in their consumer file maintained by {canonical_entity}.

Following {canonical_entity}'s prior deletion of the disputed information, the same information was subsequently reinserted into the consumer file.

This correspondence serves as formal notice that the reinsertion failed to satisfy mandatory statutory prerequisites and constitutes a distinct compliance failure."""
    letter_parts.append(opening)

    # =========================================================================
    # ESTABLISHED FACTS - Clean bullet points
    # =========================================================================
    established_facts = f"""ESTABLISHED FACTS
{'=' * 50}

• Disputed information was previously deleted from the consumer file
• The same information was later reinserted
• No written notice of reinsertion was received
• No certification of accuracy was provided"""
    letter_parts.append(established_facts)

    # =========================================================================
    # REINSERTED ITEM - Clean format
    # =========================================================================
    reinserted_section = f"""REINSERTED ITEM
{'=' * 50}"""

    for item in reinserted_items:
        reinserted_section += f"""

• Furnisher: {item['creditor']}
• Account: {item['account']}"""

    letter_parts.append(reinserted_section)

    # =========================================================================
    # BASIS FOR NON-COMPLIANCE - The key Tier-2 addition
    # Proves lawful reinsertion could not have occurred
    # =========================================================================
    basis_section = f"""BASIS FOR NON-COMPLIANCE
{'=' * 50}

Under 15 U.S.C. § 1681i(a)(5)(B), a consumer reporting agency may reinsert previously deleted information only if specific statutory prerequisites are satisfied.

Those prerequisites include:

• Certification that the information is complete and accurate
• Written notice to the consumer within five (5) business days of reinsertion
• Identification of the furnisher that provided the information
• Notice of the consumer's right to add a dispute statement

In this case, {canonical_entity} failed to provide:

• Any certification of accuracy
• Any written notice of reinsertion
• Any identification of the furnisher or furnisher address
• Any notice of the consumer's right to add a statement

Absent these mandatory disclosures, a lawful reinsertion could not have occurred.

Reinsertion without certification and notice is procedurally invalid and evidences examiner non-compliance rather than a discretionary reporting action."""
    letter_parts.append(basis_section)

    # =========================================================================
    # STATUTORY FRAMEWORK - Clean statement of law
    # =========================================================================
    statutory_framework = f"""STATUTORY FRAMEWORK
{'=' * 50}

Pursuant to 15 U.S.C. § 1681i(a)(5)(B), reinsertion of previously deleted information is permitted only when statutory certification and notice requirements are satisfied.

Failure to meet these prerequisites renders the reinsertion invalid."""
    letter_parts.append(statutory_framework)

    # =========================================================================
    # STATUTORY NON-COMPLIANCE - Summary
    # =========================================================================
    violation_section = f"""STATUTORY NON-COMPLIANCE
{'=' * 50}

Non-Compliance: Reinsertion Without Required Certification and Notice
Statute: 15 U.S.C. § 1681i(a)(5)(B)

By reinserting previously deleted information without satisfying mandatory procedural requirements, {canonical_entity} failed to comply with statutory obligations."""
    letter_parts.append(violation_section)

    # =========================================================================
    # DEMANDED ACTIONS - Simplified, no redundant timeframes
    # =========================================================================
    demands = f"""DEMANDED ACTIONS
{'=' * 50}

The following actions are required:

1. Immediate removal or blocking of the reinserted item

2. Written certification identifying the source and basis for reinsertion

3. Identification of the furnisher, including name and address

4. Written confirmation of corrective action

Failure to cure this non-compliance will be recorded as continued non-compliance and escalated accordingly."""
    letter_parts.append(demands)

    # =========================================================================
    # RIGHTS PRESERVATION
    # =========================================================================
    rights = f"""RIGHTS PRESERVATION
{'=' * 50}

Nothing in this correspondence shall be construed as a waiver of any rights or remedies available under 15 U.S.C. §§ 1681n or 1681o."""
    letter_parts.append(rights)

    # =========================================================================
    # RESPONSE REQUIRED + CLOSING
    # =========================================================================
    closing = f"""RESPONSE REQUIRED
{'=' * 50}

A written response addressing each demanded action is required.

All future correspondence regarding this matter should be directed to the address listed above.



Respectfully submitted,



____________________________________
{consumer_name}

Enclosures:
- Prior dispute results showing deletion
- Evidence of reinsertion
- Proof of mailing"""
    letter_parts.append(closing)

    return "\n\n".join(letter_parts)
