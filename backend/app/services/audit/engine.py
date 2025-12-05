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
    Account, BureauAccountData
)
from .rules import SingleBureauRules, FurnisherRules, TemporalRules
from .cross_bureau_rules import CrossBureauRules

logger = logging.getLogger(__name__)


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

    def audit(self, report: NormalizedReport) -> AuditResult:
        """
        Run all audit rules against a NormalizedReport.

        Args:
            report: NormalizedReport (SSOT #1) from parsing layer

        Returns:
            AuditResult (SSOT #2) - immutable, cannot be re-audited downstream
        """
        logger.info(f"Starting audit of report {report.report_id}")

        all_violations: List[Violation] = []
        clean_accounts: List[str] = []

        for account in report.accounts:
            account_violations = []

            # Check if account has multi-bureau data
            if hasattr(account, 'bureaus') and account.bureaus:
                # Audit each bureau's data separately
                for bureau, bureau_data in account.bureaus.items():
                    bureau_violations = self._audit_account_bureau(account, bureau, bureau_data)
                    account_violations.extend(bureau_violations)
            else:
                # Fallback for single-bureau accounts
                account_bureau = getattr(account, 'bureau', report.bureau)
                account_violations = self._audit_account(account, account_bureau)

            if account_violations:
                all_violations.extend(account_violations)
            else:
                clean_accounts.append(account.account_id)

        # Run cross-bureau analysis on accounts with 2+ bureaus
        all_discrepancies = self._audit_cross_bureau(report.accounts)

        # Build AuditResult (SSOT #2)
        result = AuditResult(
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
            f"{len(all_violations)} violations, "
            f"{len(all_discrepancies)} cross-bureau discrepancies, "
            f"{len(clean_accounts)} clean accounts"
        )

        return result

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

        logger.info(f"Cross-bureau analysis found {len(all_discrepancies)} discrepancies")
        return all_discrepancies

    def _convert_bureau_data_to_accounts(self, account: Account) -> Dict[Bureau, Account]:
        """
        Convert an Account with merged bureau data into separate Account-like objects
        for each bureau, compatible with CrossBureauRules.

        The cross_bureau_rules expect Dict[Bureau, Account] where each Account has
        bureau-specific fields. We create temporary Account objects from BureauAccountData.
        """
        from dataclasses import replace

        bureau_accounts: Dict[Bureau, Account] = {}

        for bureau, bureau_data in account.bureaus.items():
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
        """
        from dataclasses import replace

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

        return violations


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

def audit_report(report: NormalizedReport) -> AuditResult:
    """
    Factory function to audit a NormalizedReport.

    Args:
        report: NormalizedReport (SSOT #1)

    Returns:
        AuditResult (SSOT #2) - the single source of truth for violations
    """
    engine = AuditEngine()
    return engine.audit(report)
