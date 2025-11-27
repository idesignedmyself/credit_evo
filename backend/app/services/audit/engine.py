"""
Credit Engine 2.0 - Audit Engine

Main orchestrator that runs all audit rules against NormalizedReport.
Output is AuditResult (SSOT #2) - downstream modules CANNOT re-audit.
"""
from __future__ import annotations
import logging
from datetime import datetime
from typing import List

from ...models.ssot import (
    NormalizedReport, AuditResult, Violation, Bureau
)
from .rules import SingleBureauRules, FurnisherRules, TemporalRules

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
            # Use account's bureau (from multi-bureau reports) or fall back to report bureau
            account_bureau = getattr(account, 'bureau', report.bureau)
            account_violations = self._audit_account(account, account_bureau)

            if account_violations:
                all_violations.extend(account_violations)
            else:
                clean_accounts.append(account.account_id)

        # Build AuditResult (SSOT #2)
        result = AuditResult(
            report_id=report.report_id,
            bureau=report.bureau,
            violations=all_violations,
            discrepancies=[],  # Cross-bureau would be populated here
            clean_accounts=clean_accounts,
            total_accounts_audited=len(report.accounts),
            total_violations_found=len(all_violations)
        )

        logger.info(
            f"Audit complete: {len(report.accounts)} accounts, "
            f"{len(all_violations)} violations, "
            f"{len(clean_accounts)} clean accounts"
        )

        return result

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
