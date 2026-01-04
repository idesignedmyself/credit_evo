"""
Violation → Block Compiler

Converts violations into deterministic letter blocks.
Each violation produces exactly ONE FACTUAL_INACCURACIES block.

Hard-locked template - NO deviation allowed:

    This account contains a factual reporting violation.

    Specifically, [FACTUAL FAILURE].

    This violates Metro 2 reporting requirements under
    [CRRG Field X, Page Y].

    Pursuant to FCRA §[statute], information that cannot be
    accurately verified must not be reported.
"""

from typing import Dict, List, Optional

from app.models.ssot import Violation, Severity
from app.models.letter_object import LetterBlock, LetterSection


# =============================================================================
# HARD-LOCKED TEMPLATES - NO MODIFICATION ALLOWED
# =============================================================================

FACTUAL_BLOCK_TEMPLATE = """This account contains a factual reporting violation.

Specifically, {factual_failure}.

This violates Metro 2 reporting requirements under {crrg_reference}.

Pursuant to {statute}, information that cannot be accurately verified must not be reported."""


# =============================================================================
# VIOLATION TYPE → FACTUAL FAILURE MAPPING
# =============================================================================

# Each violation type has a deterministic factual failure description.
# NO free-text. NO tone customization. NO storytelling.
# MISSING MAPPINGS WILL CAUSE HARD FAILURE - this is intentional.

FACTUAL_FAILURE_MAP: Dict[str, str] = {
    # Single-bureau violations
    "missing_dofd": "the Date of First Delinquency (DOFD) is missing from a derogatory account",
    "missing_date_opened": "the Date Opened field is missing or invalid",
    "missing_dla": "the Date of Last Activity is missing",
    "missing_payment_status": "the Payment Status field is missing",
    "missing_scheduled_payment": "the Scheduled Monthly Payment field is missing",
    "missing_original_creditor": "the Original Creditor name is missing from a collection account",
    "negative_balance": "a negative balance is reported, which is mathematically impossible",
    "negative_credit_limit": "a negative credit limit is reported, which is mathematically impossible",
    "past_due_exceeds_balance": "the Amount Past Due exceeds the Current Balance",
    "balance_exceeds_high_credit": "the Current Balance exceeds the High Credit/Original Amount",
    "balance_exceeds_credit_limit": "the Current Balance exceeds the Credit Limit",
    "future_date": "a future date is reported in a date field",
    "dofd_after_date_opened": "the Date of First Delinquency occurs before the account was opened",
    "invalid_metro2_code": "an invalid Metro 2 code is used",
    "closed_oc_reporting_balance": "a closed original creditor account is still reporting a balance",
    "closed_oc_reporting_past_due": "a closed original creditor account is still reporting an amount past due",
    "chargeoff_missing_dofd": "a charged-off account is missing the required Date of First Delinquency",
    "status_payment_history_mismatch": "the Account Status conflicts with the Payment History Profile",
    "phantom_late_payment": "late payment markers appear during periods with no payment due",
    "paid_status_with_balance": "the account shows Paid status but reports a balance greater than zero",
    "zero_balance_not_paid": "a collection account has zero balance but is not marked as Paid",
    "delinquency_jump": "the payment history shows an impossible delinquency progression",
    "stagnant_delinquency": "the payment history shows statically repeated delinquency levels",
    "double_jeopardy": "the same debt is reported with balances by both original creditor and collector",

    # Cross-bureau violations
    "dofd_mismatch": "the Date of First Delinquency differs between credit bureaus",
    "date_opened_mismatch": "the Date Opened differs between credit bureaus",
    "balance_mismatch": "the Current Balance differs between credit bureaus",
    "status_mismatch": "the Account Status differs between credit bureaus",
    "payment_history_mismatch": "the Payment History Profile differs between credit bureaus",
    "past_due_mismatch": "the Amount Past Due differs between credit bureaus",
    "closed_vs_open_conflict": "the account is reported as open on some bureaus and closed on others",
    "creditor_name_mismatch": "the Creditor Name differs between credit bureaus",
    "account_number_mismatch": "the Account Number differs between credit bureaus",
    "dispute_flag_mismatch": "the Dispute Flag differs between credit bureaus",
    "ecoa_code_mismatch": "the ECOA Code differs between credit bureaus",
    "authorized_user_derogatory": "an Authorized User has derogatory marks affecting their score",
    "invalid_enum_divergence": "Metro 2 codes are valid on some bureaus but invalid on others",
    "obsolete_ecoa_divergence": "ECOA codes are valid on some bureaus but obsolete on others",

    # Temporal violations
    "stale_reporting": "the account has not been updated within required timeframes",
    "re_aging": "the Date of First Delinquency has been modified after initial reporting",
    "dofd_replaced_with_date_opened": "the Date of First Delinquency was replaced with the Date Opened",
    "impossible_timeline": "the reported dates create an impossible chronological sequence",
    "obsolete_account": "the account has exceeded the FCRA 7-year reporting window",
    "time_barred_debt_risk": "a collection account past the statute of limitations is still reporting",

    # Metro 2 Portfolio Type
    "metro2_portfolio_mismatch": "the Portfolio Type does not match the account classification",

    # Phase-1 Deterministic Contradictions
    "payment_history_exceeds_account_age": "the Payment History contains more months than the account has existed",
    "chargeoff_before_last_payment": "the account was charged off before the last payment date",
    "delinquency_ladder_inversion": "the delinquency ladder dates are chronologically inverted",
    "dofd_inferred_mismatch": "the reported DOFD does not match the payment history-inferred DOFD",

    # DOFD State Machine violations
    "dofd_reage": "the Date of First Delinquency was illegally re-aged",
    "dofd_current_must_zero_fill": "a current account is not zero-filled in the DOFD field",
    "status_regression_reaging": "the account status regressed in a pattern indicating re-aging",
    "debt_buyer_dofd_invariant": "a debt buyer modified the locked Date of First Delinquency",
    "k2_prohibited_reporter_has_k2": "a prohibited reporter type is furnishing K2 segment data",
    "debt_buyer_chain_gap_k2_required": "a debt buyer chain gap exists without required K2 documentation",

    # Metro 2 V2.0 schema violations
    "invalid_account_status": "the Account Status code is invalid per Metro 2 specifications",
    "invalid_payment_history": "the Payment History Profile contains invalid codes",
    "obsolete_ecoa_code": "an obsolete ECOA code (3, 4, or 6) is still in use",
    "invalid_ecoa_code": "the ECOA code is invalid per Metro 2 specifications",
    "invalid_portfolio_type": "the Portfolio Type code is invalid per Metro 2 specifications",
    "invalid_account_type": "the Account Type code is invalid per Metro 2 specifications",
    "invalid_compliance_code": "the Compliance Condition Code is invalid",
    "cb_invalid_enum_divergence": "Metro 2 enumerations differ between bureaus in an invalid manner",
    "valid_coexistence": "original creditor and collector accounts are reporting conflicting data",
    "double_balance_violation": "duplicate balances are being reported for the same underlying debt",
    "ownership_conflict_doc_demand": "account ownership documentation is contradictory or missing",
}


class BlockCompiler:
    """
    Compiles violations into deterministic letter blocks.

    Rules:
    - Each violation → exactly one block
    - Each block → exactly one paragraph
    - Each paragraph → hard-locked template
    - No free-text, no tone customization, no deviation
    - Missing violation type mappings cause hard failure
    """

    def compile(self, violation: Violation) -> LetterBlock:
        """
        Compile a single violation into a letter block.

        Args:
            violation: The Violation object to compile

        Returns:
            LetterBlock containing the deterministic paragraph

        Raises:
            KeyError: If violation type has no factual failure mapping
        """
        # Extract violation type
        vtype = violation.violation_type
        vtype_str = vtype.value if hasattr(vtype, 'value') else str(vtype)
        vtype_key = vtype_str.lower()

        # Get factual failure description - HARD FAILURE if missing
        if vtype_key not in FACTUAL_FAILURE_MAP:
            raise KeyError(f"No factual failure mapping for violation type: {vtype_key}")
        factual_failure = FACTUAL_FAILURE_MAP[vtype_key]

        # Get CRRG reference from violation citations
        crrg_reference = self._format_crrg_reference(violation)

        # Get statute citation
        statute = self._format_statute(violation)

        # Build the deterministic paragraph
        text = FACTUAL_BLOCK_TEMPLATE.format(
            factual_failure=factual_failure,
            crrg_reference=crrg_reference,
            statute=statute,
        )

        # Extract anchors and statutes
        anchors = list(violation.citations) if violation.citations else []
        statutes = self._extract_statutes(violation)

        # Get metro2 field reference
        metro2_field = None
        if anchors:
            fields = anchors[0].get("fields", [])
            if fields:
                metro2_field = f"Field {fields[0]}"
        elif violation.metro2_field:
            metro2_field = violation.metro2_field

        # Deterministic block_id - NO randomness
        return LetterBlock(
            block_id=f"block_{violation.violation_id}",
            violation_id=violation.violation_id,
            severity=violation.severity,
            section=LetterSection.FACTUAL_INACCURACIES,
            text=text,
            anchors=anchors,
            statutes=statutes,
            metro2_field=metro2_field,
        )

    def compile_many(self, violations: List[Violation]) -> List[LetterBlock]:
        """
        Compile multiple violations into letter blocks.

        Args:
            violations: List of Violation objects

        Returns:
            List of LetterBlock objects, one per violation

        Raises:
            KeyError: If any violation type has no factual failure mapping
        """
        return [self.compile(v) for v in violations]

    def _format_crrg_reference(self, violation: Violation) -> str:
        """Format CRRG reference from violation citations."""
        if not violation.citations:
            return "Metro 2 CRRG specifications"

        citation = violation.citations[0]
        section_title = citation.get("section_title", "")
        page_start = citation.get("page_start")
        page_end = citation.get("page_end")

        if section_title and page_start:
            if page_end and page_end != page_start:
                return f"{section_title} (pp. {page_start}–{page_end})"
            return f"{section_title} (p. {page_start})"
        elif section_title:
            return section_title
        else:
            return "Metro 2 CRRG specifications"

    def _format_statute(self, violation: Violation) -> str:
        """Format statute citation from violation."""
        # Try primary_statute first
        if violation.primary_statute:
            return violation.primary_statute

        # Try citations
        if violation.citations:
            fcra_cite = violation.citations[0].get("fcra_cite", "")
            if fcra_cite:
                return fcra_cite

        # Default FCRA accuracy requirement
        return "15 U.S.C. § 1681s-2(a)(1)"

    def _extract_statutes(self, violation: Violation) -> List[str]:
        """Extract all applicable statutes from violation."""
        statutes = set()

        # Primary statute
        if violation.primary_statute:
            statutes.add(violation.primary_statute)

        # Secondary statutes
        if violation.secondary_statutes:
            statutes.update(violation.secondary_statutes)

        # From citations
        if violation.citations:
            for citation in violation.citations:
                if citation.get("fcra_cite"):
                    statutes.add(citation["fcra_cite"])
                if citation.get("ecoa_cite"):
                    statutes.add(citation["ecoa_cite"])

        # Ensure at least one statute
        if not statutes:
            statutes.add("15 U.S.C. § 1681s-2(a)(1)")

        return sorted(statutes)


# =============================================================================
# MODULE-LEVEL SINGLETON
# =============================================================================

_compiler: Optional[BlockCompiler] = None


def get_compiler() -> BlockCompiler:
    """Get or create the default block compiler singleton."""
    global _compiler
    if _compiler is None:
        _compiler = BlockCompiler()
    return _compiler


def compile_violation(violation: Violation) -> LetterBlock:
    """
    Convenience function to compile a violation using the default compiler.

    Args:
        violation: The Violation object to compile

    Returns:
        LetterBlock containing the deterministic paragraph

    Raises:
        KeyError: If violation type has no factual failure mapping
    """
    return get_compiler().compile(violation)


def compile_violations(violations: List[Violation]) -> List[LetterBlock]:
    """
    Convenience function to compile multiple violations.

    Args:
        violations: List of Violation objects

    Returns:
        List of LetterBlock objects

    Raises:
        KeyError: If any violation type has no factual failure mapping
    """
    return get_compiler().compile_many(violations)
