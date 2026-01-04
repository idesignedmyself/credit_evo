"""
Credit Engine 2.0 - Audit Engine

Main orchestrator that runs all audit rules against NormalizedReport.
Output is AuditResult (SSOT #2) - downstream modules CANNOT re-audit.
"""
from __future__ import annotations
import logging
from datetime import datetime
from typing import List, Dict, Optional

from ...models.ssot import (
    NormalizedReport, AuditResult, Violation, Bureau, CrossBureauDiscrepancy,
    Account, BureauAccountData, FurnisherType, ViolationType, Severity
)
from .rules import SingleBureauRules, FurnisherRules, TemporalRules, InquiryRules, IdentityRules, PublicRecordRules
from .cross_bureau_rules import CrossBureauRules
from ..metro2 import get_injector

logger = logging.getLogger(__name__)


# =============================================================================
# BUREAU GHOST DETECTION (B6 - DATA BLEED FIX)
# =============================================================================

def is_bureau_ghost(bureau_data: BureauAccountData) -> bool:
    """
    Returns True if the bureau column represents a non-existent (ghost) tradeline,
    even if other bureaus reported the account.

    A bureau cannot violate FCRA/Metro 2 rules on data it never reported.
    Ghost criteria:
    1. No account data at all (all key fields are None/empty)
    2. No balance AND no dates AND no status - bureau didn't report this tradeline

    This prevents cross-bureau data bleed where validation rules fire incorrectly
    for bureaus that show empty columns in the merged account view.
    """
    # Check for ANY substantive data that indicates the bureau reported this account
    # Key fields that would be present if bureau actually reported the tradeline:

    # 1. Financial data
    has_balance = bureau_data.balance is not None and bureau_data.balance != 0
    has_high_credit = bureau_data.high_credit is not None and bureau_data.high_credit != 0
    has_credit_limit = bureau_data.credit_limit is not None and bureau_data.credit_limit != 0
    has_past_due = bureau_data.past_due_amount is not None and bureau_data.past_due_amount != 0

    # 2. Date fields - any date indicates bureau reported something
    has_date_opened = bureau_data.date_opened is not None
    has_date_closed = bureau_data.date_closed is not None
    has_date_reported = bureau_data.date_reported is not None
    has_date_last_activity = bureau_data.date_last_activity is not None
    has_dofd = bureau_data.date_of_first_delinquency is not None

    # 3. Status fields
    has_payment_status = bureau_data.payment_status is not None and str(bureau_data.payment_status).strip() != ""
    has_account_status = bureau_data.account_status_raw is not None and str(bureau_data.account_status_raw).strip() != ""

    # 4. Payment history (must have at least one non-empty status to count as real data)
    # Empty status strings like '' don't count - only actual values like 'OK', 'CO', '30', etc.
    has_payment_history = False
    if bureau_data.payment_history:
        for entry in bureau_data.payment_history:
            status = entry.get('status', '') if isinstance(entry, dict) else ''
            if status and str(status).strip():
                has_payment_history = True
                break

    # If ANY of these fields have data, the bureau actually reported this tradeline
    has_any_data = (
        has_balance or has_high_credit or has_credit_limit or has_past_due or
        has_date_opened or has_date_closed or has_date_reported or
        has_date_last_activity or has_dofd or
        has_payment_status or has_account_status or
        has_payment_history
    )

    # Ghost = NO substantive data from this bureau
    return not has_any_data


class AuditEngine:
    """
    Main audit engine that runs all rules against a NormalizedReport.

    This is the ONLY place where violations are computed.
    AuditResult (SSOT #2) is immutable after creation.
    """

    def __init__(self):
        """Initialize the audit engine with all rule sets."""
        self.single_bureau_rules = SingleBureauRules()
        self.furnisher_rules = FurnisherRules()
        self.temporal_rules = TemporalRules()
        self.cross_bureau_rules = CrossBureauRules()
        self.citation_injector = get_injector()

    def audit(self, report: NormalizedReport, user_profile: Optional[Dict] = None) -> AuditResult:
        """
        Run all audit rules against a NormalizedReport.

        Args:
            report: NormalizedReport (SSOT #1) from parsing layer
            user_profile: Optional dict with user's profile data (first_name, last_name,
                         suffix, ssn_last_4, state, etc.) for identity checks

        Returns:
            AuditResult (SSOT #2) - immutable, cannot be re-audited downstream
        """
        logger.info(f"Starting audit of report {report.report_id}")

        all_violations: List[Violation] = []
        clean_accounts: List[str] = []

        for account in report.accounts:
            account_violations = []

            # DEBUG: Check which path is taken
            has_bureaus = hasattr(account, 'bureaus') and account.bureaus
            print(f"[DEBUG] Account '{account.creditor_name}': has_bureaus={has_bureaus}, bureaus={list(account.bureaus.keys()) if has_bureaus else 'N/A'}")

            # Check if account has multi-bureau data
            if has_bureaus:
                # Audit each bureau's data separately
                for bureau, bureau_data in account.bureaus.items():
                    bureau_violations = self._audit_account_bureau(account, bureau, bureau_data)
                    account_violations.extend(bureau_violations)
            else:
                # Fallback for single-bureau accounts (NO GHOST GUARD HERE!)
                print(f"[DEBUG] FALLBACK PATH - no bureaus dict for '{account.creditor_name}'")
                account_bureau = getattr(account, 'bureau', report.bureau)
                account_violations = self._audit_account(account, account_bureau)

            if account_violations:
                all_violations.extend(account_violations)
            else:
                clean_accounts.append(account.account_id)

        # Run cross-bureau analysis on accounts with 2+ bureaus
        all_discrepancies = self._audit_cross_bureau(report.accounts)

        # Run cross-tradeline checks (Double Jeopardy - OC + Collector both with balance)
        double_jeopardy_violations = self._check_double_jeopardy(report.accounts)
        all_violations.extend(double_jeopardy_violations)

        # Run time-barred debt checks (SOL expired)
        # Use user profile state for SOL calculations if available (default NY if not set)
        user_state = (user_profile.get("state") if user_profile else None) or "NY"
        time_barred_violations = self._check_time_barred_debts(report.accounts, user_state)
        all_violations.extend(time_barred_violations)

        # Run inquiry audits (FCRA §604 - Permissible Purpose)
        inquiry_violations = InquiryRules.audit_inquiries(report.inquiries, report.accounts)
        all_violations.extend(inquiry_violations)

        # Run identity integrity checks (User Profile vs Credit Report Header)
        if user_profile:
            identity_violations = IdentityRules.check_identity_integrity(report, user_profile)
            all_violations.extend(identity_violations)
            logger.info(f"Identity integrity check found {len(identity_violations)} violations")

        # Run consumer-level deceased indicator check (CRITICAL - "Death on Credit" error)
        # This is separate from account-level checks - it scans all accounts and creates
        # a single consumer-level violation if ANY deceased indicator is found
        deceased_violations = IdentityRules.check_deceased_indicator_consumer(report)
        all_violations.extend(deceased_violations)
        if deceased_violations:
            logger.warning(f"CRITICAL: Deceased indicator found - {len(deceased_violations)} consumer-level violation(s)")

        # Run Child Identity Theft check (Account opened while consumer was a minor)
        # This requires comparing account Date Opened vs consumer's DOB from profile
        if user_profile and user_profile.get("date_of_birth"):
            try:
                # Parse DOB from profile - handle both date objects and strings
                dob_raw = user_profile["date_of_birth"]
                if isinstance(dob_raw, str):
                    user_dob = datetime.strptime(dob_raw, "%Y-%m-%d").date()
                else:
                    user_dob = dob_raw  # Already a date object

                # Check each account for child identity theft
                child_id_violations = []
                for account in report.accounts:
                    # Run check on each bureau's data
                    if hasattr(account, 'bureaus') and account.bureaus:
                        for bureau, bureau_data in account.bureaus.items():
                            # B6 GHOST GUARD: Skip ghost bureaus
                            if is_bureau_ghost(bureau_data):
                                continue
                            child_id_violations.extend(
                                self.single_bureau_rules.check_child_identity_theft(account, bureau, user_dob)
                            )
                    else:
                        # Single-bureau fallback
                        account_bureau = getattr(account, 'bureau', report.bureau)
                        child_id_violations.extend(
                            self.single_bureau_rules.check_child_identity_theft(account, account_bureau, user_dob)
                        )

                all_violations.extend(child_id_violations)
                if child_id_violations:
                    logger.warning(f"CRITICAL: Child Identity Theft detected - {len(child_id_violations)} violation(s)")

            except (ValueError, TypeError) as e:
                logger.debug(f"Could not parse DOB for child ID theft check: {e}")

        # Run Public Records audit (Bankruptcies, Judgments, Liens)
        # This checks for NCAP violations, satisfied-but-reporting-balance, and obsolete bankruptcies
        if report.public_records:
            public_record_violations = PublicRecordRules.audit_public_records(report.public_records)
            all_violations.extend(public_record_violations)
            if public_record_violations:
                logger.info(f"Public Records audit found {len(public_record_violations)} violation(s)")

        # Run Medical Debt Compliance check (NCAP 2022/2023 Bureau Policy)
        # Catches: 1) Unpaid medical < $500, 2) Paid medical still reporting
        medical_violations = []
        for account in report.accounts:
            # Check each bureau the account appears in
            if hasattr(account, 'bureaus') and account.bureaus:
                for bureau, bureau_data in account.bureaus.items():
                    # B6 GHOST GUARD: Skip ghost bureaus
                    if is_bureau_ghost(bureau_data):
                        continue
                    medical_violations.extend(
                        self.single_bureau_rules.check_medical_debt_compliance(account, bureau)
                    )
            else:
                # Single-bureau fallback
                account_bureau = getattr(account, 'bureau', report.bureau)
                medical_violations.extend(
                    self.single_bureau_rules.check_medical_debt_compliance(account, account_bureau)
                )
        all_violations.extend(medical_violations)
        if medical_violations:
            logger.info(f"Medical Debt Compliance check found {len(medical_violations)} violation(s)")

        # Inject CRRG citations into all violations (attach to violation.citations)
        citations_injected = 0
        citations_missing = []
        for violation in all_violations:
            result = self.citation_injector.inject_into_violation(violation)
            if result.success:
                citations_injected += 1
            else:
                # Track violations without citations for debugging
                rule_code = violation.violation_type.value if hasattr(violation.violation_type, 'value') else str(violation.violation_type)
                citations_missing.append(rule_code)

        logger.info(f"CRRG citations: {citations_injected}/{len(all_violations)} violations have citations")
        if citations_missing:
            # Log unique missing rules (not every instance)
            unique_missing = list(set(citations_missing))
            logger.warning(f"Missing CRRG anchors for rules: {unique_missing[:10]}{'...' if len(unique_missing) > 10 else ''}")

        # GUARD: Metro 2 V2.0 violations MUST have at least one CRRG citation
        self._guard_metro2_v2_citations(all_violations)

        # Build AuditResult (SSOT #2)
        audit_result = AuditResult(
            report_id=report.report_id,
            bureau=report.bureau,
            violations=all_violations,
            discrepancies=all_discrepancies,
            clean_accounts=clean_accounts,
            total_accounts_audited=len(report.accounts),
            total_violations_found=len(all_violations)
        )

        logger.info(
            f"Audit complete: {len(report.accounts)} accounts, "
            f"{len(report.inquiries)} inquiries, "
            f"{len(all_violations)} violations, "
            f"{len(all_discrepancies)} cross-bureau discrepancies, "
            f"{len(clean_accounts)} clean accounts, "
            f"{len(inquiry_violations)} inquiry violations"
        )

        return audit_result

    def _guard_metro2_v2_citations(self, violations: List[Violation]) -> None:
        """
        Ensure all Metro 2 V2.0 violations have at least one CRRG citation.

        Raises RuntimeError if any Metro 2 V2.0 violation has no citations.
        This is a hard fail to ensure citation wiring is complete.
        """
        for violation in violations:
            if violation.is_metro2_v2 and not violation.citations:
                rule_code = (
                    violation.violation_type.value
                    if hasattr(violation.violation_type, "value")
                    else str(violation.violation_type)
                )
                raise RuntimeError(
                    f"Metro 2 V2.0 violation '{rule_code.lower()}' has no CRRG citation. "
                    f"Add mapping to crrg_anchors.json for rule: {rule_code.lower()}"
                )

    def _audit_cross_bureau(self, accounts: List[Account]) -> List[CrossBureauDiscrepancy]:
        """
        Run cross-bureau checks on accounts that have data from 2+ bureaus.

        This uses the merged Account.bureaus dict to detect discrepancies
        without needing separate bureau reports.
        """
        all_discrepancies: List[CrossBureauDiscrepancy] = []

        for account in accounts:
            # Only check accounts with data from 2+ bureaus
            if not hasattr(account, 'bureaus') or len(account.bureaus) < 2:
                continue

            # Convert BureauAccountData to Account-like objects for rule compatibility
            bureau_accounts = self._convert_bureau_data_to_accounts(account)

            if len(bureau_accounts) < 2:
                continue

            # Run all cross-bureau rules
            all_discrepancies.extend(self.cross_bureau_rules.check_dofd_mismatch(bureau_accounts))
            all_discrepancies.extend(self.cross_bureau_rules.check_date_opened_mismatch(bureau_accounts))
            all_discrepancies.extend(self.cross_bureau_rules.check_balance_mismatch(bureau_accounts))
            all_discrepancies.extend(self.cross_bureau_rules.check_status_mismatch(bureau_accounts))
            all_discrepancies.extend(self.cross_bureau_rules.check_payment_history_mismatch(bureau_accounts))
            all_discrepancies.extend(self.cross_bureau_rules.check_past_due_mismatch(bureau_accounts))
            all_discrepancies.extend(self.cross_bureau_rules.check_closed_vs_open_conflict(bureau_accounts))
            # Dispute flag mismatch (requires access to remarks from original account.bureaus)
            all_discrepancies.extend(self.cross_bureau_rules.check_dispute_flag_mismatch(bureau_accounts))
            # ECOA code mismatch (liability designation: Individual vs Joint vs Authorized User)
            all_discrepancies.extend(self.cross_bureau_rules.check_ecoa_code_mismatch(bureau_accounts))
            # Authorized User with derogatory marks (AU is not liable, shouldn't have negative marks)
            all_discrepancies.extend(self.cross_bureau_rules.check_authorized_user_derogatory(bureau_accounts))
            # Missing tradelines (account on some bureaus but not others - explains score gaps)
            all_discrepancies.extend(self.cross_bureau_rules.check_missing_tradelines(bureau_accounts))
            # Metro 2 invalid enum divergence (valid codes on some bureaus, invalid on others)
            all_discrepancies.extend(self.cross_bureau_rules.check_invalid_enum_divergence(bureau_accounts))

        logger.info(f"Cross-bureau analysis found {len(all_discrepancies)} discrepancies")
        return all_discrepancies

    def _convert_bureau_data_to_accounts(self, account: Account) -> Dict[Bureau, Account]:
        """
        Convert an Account with merged bureau data into separate Account-like objects
        for each bureau, compatible with CrossBureauRules.

        The cross_bureau_rules expect Dict[Bureau, Account] where each Account has
        bureau-specific fields. We create temporary Account objects from BureauAccountData.

        B6 FIX: Excludes ghost bureaus from cross-bureau analysis. A bureau that didn't
        report the tradeline cannot be compared against bureaus that did.
        """
        from dataclasses import replace

        bureau_accounts: Dict[Bureau, Account] = {}

        for bureau, bureau_data in account.bureaus.items():
            # B6 GHOST GUARD: Skip ghost bureaus in cross-bureau analysis
            if is_bureau_ghost(bureau_data):
                continue

            # Create a copy of the account with this bureau's specific data
            bureau_account = replace(
                account,
                bureau=bureau,
                date_opened=bureau_data.date_opened,
                date_closed=bureau_data.date_closed,
                date_of_first_delinquency=bureau_data.date_of_first_delinquency,
                date_last_activity=bureau_data.date_last_activity,
                date_last_payment=bureau_data.date_last_payment,
                date_reported=bureau_data.date_reported,
                balance=bureau_data.balance,
                credit_limit=bureau_data.credit_limit,
                high_credit=bureau_data.high_credit,
                past_due_amount=bureau_data.past_due_amount,
                scheduled_payment=bureau_data.scheduled_payment,
                monthly_payment=bureau_data.monthly_payment,
                payment_status=bureau_data.payment_status,
                payment_pattern=bureau_data.payment_pattern,
            )
            bureau_accounts[bureau] = bureau_account

        return bureau_accounts

    def _audit_account(self, account, bureau: Bureau) -> List[Violation]:
        """Run all rules against a single account."""
        violations = []

        # Single-bureau rules
        violations.extend(self.single_bureau_rules.check_missing_dofd(account, bureau))
        violations.extend(self.single_bureau_rules.check_missing_date_opened(account, bureau))
        violations.extend(self.single_bureau_rules.check_negative_balance(account, bureau))
        violations.extend(self.single_bureau_rules.check_past_due_exceeds_balance(account, bureau))
        violations.extend(self.single_bureau_rules.check_future_dates(account, bureau))
        violations.extend(self.single_bureau_rules.check_dofd_after_date_opened(account, bureau))
        # NEW rules
        violations.extend(self.single_bureau_rules.check_missing_scheduled_payment(account, bureau))
        violations.extend(self.single_bureau_rules.check_balance_exceeds_high_credit(account, bureau))
        violations.extend(self.single_bureau_rules.check_balance_exceeds_credit_limit(account, bureau))
        violations.extend(self.single_bureau_rules.check_negative_credit_limit(account, bureau))
        violations.extend(self.single_bureau_rules.check_missing_dla(account, bureau))
        violations.extend(self.single_bureau_rules.check_student_loan_portfolio_mismatch(account, bureau))
        # Deceased indicator check (CRITICAL - score = 0 if present)
        violations.extend(self.single_bureau_rules.check_deceased_indicator(account, bureau))

        # Furnisher rules
        violations.extend(self.furnisher_rules.check_closed_oc_reporting_balance(account, bureau))
        violations.extend(self.furnisher_rules.check_collector_missing_original_creditor(account, bureau))
        # NEW furnisher rules
        violations.extend(self.furnisher_rules.check_chargeoff_missing_dofd(account, bureau))
        violations.extend(self.furnisher_rules.check_closed_oc_reporting_past_due(account, bureau))

        # Temporal rules
        violations.extend(self.temporal_rules.check_obsolete_account(account, bureau))
        violations.extend(self.temporal_rules.check_stale_reporting(account, bureau))
        violations.extend(self.temporal_rules.check_impossible_timeline(account, bureau))

        return violations

    def _audit_account_bureau(self, account, bureau: Bureau, bureau_data) -> List[Violation]:
        """
        Run all rules against bureau-specific data within a merged account.

        Creates a temporary account-like object with bureau-specific fields
        so existing rules can operate on per-bureau data.

        B6 FIX: Skips "ghost" tradelines where the bureau didn't actually report
        the account (empty columns). A bureau cannot violate FCRA/Metro 2 rules
        on data it never reported.
        """
        from dataclasses import replace

        # B6 GHOST GUARD: Skip validation if this bureau didn't actually report the tradeline
        # This prevents false positives from cross-bureau data bleed
        if is_bureau_ghost(bureau_data):
            return []

        # Create a modified copy of the account with bureau-specific fields
        # This allows existing rules to work without modification
        account_for_bureau = replace(
            account,
            bureau=bureau,
            # Override date fields from bureau_data
            date_opened=bureau_data.date_opened,
            date_closed=bureau_data.date_closed,
            date_of_first_delinquency=bureau_data.date_of_first_delinquency,
            date_last_activity=bureau_data.date_last_activity,
            date_last_payment=bureau_data.date_last_payment,
            date_reported=bureau_data.date_reported,
            # Override balance fields from bureau_data
            balance=bureau_data.balance,
            credit_limit=bureau_data.credit_limit,
            high_credit=bureau_data.high_credit,
            past_due_amount=bureau_data.past_due_amount,
            scheduled_payment=bureau_data.scheduled_payment,
            monthly_payment=bureau_data.monthly_payment,
            # Override payment status
            payment_status=bureau_data.payment_status,
        )

        # Run all the same rules against the bureau-specific data
        violations = self._audit_account(account_for_bureau, bureau)

        # Run rules that need bureau_data (payment_history, etc.)
        violations.extend(self.single_bureau_rules.check_status_payment_history_mismatch(
            account_for_bureau, bureau, bureau_data
        ))
        violations.extend(self.single_bureau_rules.check_phantom_late_payment(
            account_for_bureau, bureau, bureau_data
        ))
        violations.extend(self.single_bureau_rules.check_illogical_delinquency_progression(
            account_for_bureau, bureau, bureau_data
        ))
        violations.extend(self.furnisher_rules.check_paid_collection_contradiction(
            account_for_bureau, bureau, bureau_data
        ))

        # Post-settlement zombie reporting check (late markers after account closed)
        violations.extend(self.single_bureau_rules.check_post_settlement_reporting(
            account_for_bureau, bureau, bureau_data
        ))

        return violations

    def _check_double_jeopardy(self, accounts: List[Account]) -> List[Violation]:
        """
        Check for 'Double Jeopardy': When an Original Creditor (OC) and a Debt Collector
        BOTH report a balance for the same debt.

        This artificially doubles the consumer's debt load, destroying DTI ratios.
        Under Metro 2 transfer logic, when an OC sells a debt, they MUST update
        their balance to $0 and status to "Transferred/Sold".

        This check runs per-bureau since the matching needs to happen within
        the same bureau's data.
        """
        from ..audit.cross_bureau_rules import normalize_creditor_name

        violations: List[Violation] = []

        # We need to check per-bureau to find OC-Collector pairs
        # Group accounts by bureau for per-bureau analysis
        for account in accounts:
            if not hasattr(account, 'bureaus') or not account.bureaus:
                continue

            for bureau, bureau_data in account.bureaus.items():
                # B6 GHOST GUARD: Skip ghost bureaus in double jeopardy check
                if is_bureau_ghost(bureau_data):
                    continue

                # Only process collection accounts with original_creditor info
                if account.furnisher_type != FurnisherType.COLLECTOR:
                    continue

                oc_name_ref = (account.original_creditor or "").strip()
                if not oc_name_ref:
                    continue  # No OC to match against (caught by MISSING_ORIGINAL_CREDITOR)

                coll_balance = bureau_data.balance if bureau_data.balance is not None else 0

                # Skip if collector has $0 balance (already paid/settled)
                if coll_balance <= 0:
                    continue

                # Normalize the OC name from the collection for matching
                oc_name_normalized = normalize_creditor_name(oc_name_ref)

                # Now search all OTHER accounts for a matching OC with balance
                for other_account in accounts:
                    if other_account.account_id == account.account_id:
                        continue  # Skip self

                    # Only match against non-collector accounts
                    if other_account.furnisher_type == FurnisherType.COLLECTOR:
                        continue

                    # Check if this account's creditor name matches the OC reference
                    other_creditor = (other_account.creditor_name or "").strip()
                    other_creditor_normalized = normalize_creditor_name(other_creditor)

                    # Match check: substring or exact normalized match
                    is_match = (
                        oc_name_normalized and other_creditor_normalized and
                        (oc_name_normalized in other_creditor_normalized or
                         other_creditor_normalized in oc_name_normalized or
                         oc_name_normalized == other_creditor_normalized)
                    )

                    if not is_match:
                        continue

                    # Check if the OC account has bureau data for this same bureau
                    if not hasattr(other_account, 'bureaus') or bureau not in other_account.bureaus:
                        continue

                    other_bureau_data = other_account.bureaus[bureau]

                    # B6 GHOST GUARD: Skip if OC's bureau data is a ghost
                    if is_bureau_ghost(other_bureau_data):
                        continue

                    oc_balance = other_bureau_data.balance if other_bureau_data.balance is not None else 0

                    # DOUBLE JEOPARDY: Both have balance > $0
                    if oc_balance > 0:
                        violations.append(Violation(
                            violation_type=ViolationType.DOUBLE_JEOPARDY,
                            severity=Severity.HIGH,
                            # Flag the OC account (usually easier to get deleted/updated)
                            account_id=other_account.account_id,
                            creditor_name=other_account.creditor_name,
                            account_number_masked=other_account.account_number_masked,
                            furnisher_type=other_account.furnisher_type,
                            bureau=bureau,
                            description=(
                                f"Double Jeopardy: This debt is being reported twice with active balances. "
                                f"Collection Agency '{account.creditor_name}' reports a balance of ${coll_balance:,.2f}, "
                                f"but the Original Creditor '{other_account.creditor_name}' ALSO reports a balance of ${oc_balance:,.2f}. "
                                f"When a debt is sold/transferred to collections, the Original Creditor must update "
                                f"their balance to $0. Reporting it twice artificially doubles the consumer's debt load."
                            ),
                            expected_value=f"OC Balance: $0.00 (debt was sold to {account.creditor_name})",
                            actual_value=f"OC Balance: ${oc_balance:,.2f} + Collector Balance: ${coll_balance:,.2f}",
                            fcra_section="607(b)",
                            metro2_field="21 (Balance)",
                            evidence={
                                "collector_name": account.creditor_name,
                                "collector_account_id": account.account_id,
                                "collector_balance": coll_balance,
                                "original_creditor_name": other_account.creditor_name,
                                "oc_account_id": other_account.account_id,
                                "oc_balance": oc_balance,
                                "bureau": bureau.value
                            }
                        ))

        logger.info(f"Double Jeopardy check found {len(violations)} duplicate debt violations")
        return violations

    def _check_time_barred_debts(self, accounts: List[Account], user_state: str = "NY") -> List[Violation]:
        """
        Check all accounts for time-barred debt (SOL expired).

        This runs once per account (not per-bureau) since SOL is based on
        the account's dates, not bureau-specific data.

        Args:
            accounts: List of accounts to check
            user_state: Consumer's state for SOL lookup (defaults to NY for now,
                        will be dynamic from User Profile later)

        Returns:
            List of TIME_BARRED_DEBT_RISK violations
        """
        violations: List[Violation] = []

        for account in accounts:
            # The check_time_barred_debt rule handles filtering for collections/chargeoffs
            time_barred = self.single_bureau_rules.check_time_barred_debt(account, user_state)
            violations.extend(time_barred)

        logger.info(f"Time-barred debt check found {len(violations)} SOL-expired accounts")
        return violations


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

def audit_report(report: NormalizedReport, user_profile: Optional[Dict] = None) -> AuditResult:
    """
    Factory function to audit a NormalizedReport.

    Args:
        report: NormalizedReport (SSOT #1)
        user_profile: Optional dict with user's profile data for identity checks
                     and SOL calculations (state, suffix, ssn_last_4, etc.)

    Returns:
        AuditResult (SSOT #2) - the single source of truth for violations
    """
    engine = AuditEngine()
    return engine.audit(report, user_profile)
