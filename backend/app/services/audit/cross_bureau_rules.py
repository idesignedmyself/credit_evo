"""
Credit Engine 2.0 - Cross-Bureau Rules

Detects discrepancies when the same account is reported differently across bureaus.
These rules compare matched accounts from TU, EX, and EQ.
"""
from __future__ import annotations
import logging
import re
from datetime import date, timedelta
from typing import List, Dict, Optional, Tuple
from difflib import SequenceMatcher

from ...models.ssot import (
    Account, NormalizedReport, CrossBureauDiscrepancy, Violation,
    ViolationType, Severity, Bureau
)

logger = logging.getLogger(__name__)


# =============================================================================
# ACCOUNT MATCHING
# =============================================================================

def normalize_creditor_name(name: str) -> str:
    """Normalize creditor name for matching."""
    if not name:
        return ""
    # Remove common suffixes, punctuation, extra spaces
    name = name.upper()
    name = re.sub(r'\b(LLC|INC|CORP|CO|BANK|NA|FSB|CREDIT|CARD|SERVICES?)\b', '', name)
    name = re.sub(r'[^A-Z0-9]', '', name)
    return name.strip()


def normalize_account_number(acct_num: str) -> str:
    """Get last 4 digits of account number for matching."""
    if not acct_num:
        return ""
    # Remove non-alphanumeric
    cleaned = re.sub(r'[^A-Z0-9]', '', acct_num.upper())
    return cleaned[-4:] if len(cleaned) >= 4 else cleaned


def create_account_fingerprint(account: Account) -> str:
    """
    Create a fingerprint for matching accounts across bureaus.
    Uses: normalized creditor name + last 4 of account + date_opened month/year
    """
    parts = []
    parts.append(normalize_creditor_name(account.creditor_name))
    parts.append(normalize_account_number(account.account_number))
    if account.date_opened:
        parts.append(f"{account.date_opened.year}{account.date_opened.month:02d}")
    return "|".join(parts)


def match_accounts_across_bureaus(
    reports: Dict[Bureau, NormalizedReport]
) -> List[Dict[Bureau, Account]]:
    """
    Match accounts across multiple bureau reports.

    Returns list of matched account groups, where each group contains
    the same account as reported by different bureaus.
    """
    # Build fingerprint -> (bureau, account) mapping
    fingerprints: Dict[str, List[Tuple[Bureau, Account]]] = {}

    for bureau, report in reports.items():
        for account in report.accounts:
            fp = create_account_fingerprint(account)
            if fp not in fingerprints:
                fingerprints[fp] = []
            fingerprints[fp].append((bureau, account))

    # Only return groups with accounts from 2+ bureaus
    matched_groups = []
    for fp, bureau_accounts in fingerprints.items():
        if len(bureau_accounts) >= 2:
            group = {bureau: account for bureau, account in bureau_accounts}
            matched_groups.append(group)

    return matched_groups


# =============================================================================
# CROSS-BUREAU RULES
# =============================================================================

class CrossBureauRules:
    """
    Rules that detect discrepancies between bureau reports for the same account.
    """

    @staticmethod
    def check_dofd_mismatch(accounts: Dict[Bureau, Account]) -> List[CrossBureauDiscrepancy]:
        """Check if DOFD differs across bureaus."""
        discrepancies = []

        dofds = {
            bureau: acc.date_of_first_delinquency
            for bureau, acc in accounts.items()
            if acc.date_of_first_delinquency is not None
        }

        if len(dofds) >= 2:
            unique_dofds = set(dofds.values())
            if len(unique_dofds) > 1:
                # Get any account for reference info
                ref_account = list(accounts.values())[0]
                discrepancies.append(CrossBureauDiscrepancy(
                    violation_type=ViolationType.DOFD_MISMATCH,
                    creditor_name=ref_account.creditor_name,
                    account_fingerprint=create_account_fingerprint(ref_account),
                    field_name="Date of First Delinquency",
                    values_by_bureau={b: str(d) for b, d in dofds.items()},
                    description=(
                        f"DOFD differs across bureaus for {ref_account.creditor_name}: "
                        f"{', '.join(f'{b.value}={d}' for b, d in dofds.items())}"
                    ),
                    severity=Severity.HIGH
                ))

        return discrepancies

    @staticmethod
    def check_date_opened_mismatch(accounts: Dict[Bureau, Account]) -> List[CrossBureauDiscrepancy]:
        """
        Check if Date Opened differs across bureaus.

        Zero tolerance - FCRA requires "maximum possible accuracy".
        The same furnisher should report the same date to all bureaus.
        """
        discrepancies = []

        dates = {
            bureau: acc.date_opened
            for bureau, acc in accounts.items()
            if acc.date_opened is not None
        }

        if len(dates) >= 2:
            unique_dates = set(dates.values())

            # Zero tolerance - any difference is a violation
            if len(unique_dates) > 1:
                ref_account = list(accounts.values())[0]
                date_list = list(dates.values())
                max_diff = max(abs((d1 - d2).days) for i, d1 in enumerate(date_list) for d2 in date_list[i+1:])

                discrepancies.append(CrossBureauDiscrepancy(
                    violation_type=ViolationType.DATE_OPENED_MISMATCH,
                    creditor_name=ref_account.creditor_name,
                    account_fingerprint=create_account_fingerprint(ref_account),
                    field_name="Date Opened",
                    values_by_bureau={b: str(d) for b, d in dates.items()},
                    description=(
                        f"Date Opened inconsistent across bureaus for {ref_account.creditor_name}: "
                        f"{', '.join(f'{b.value}={d}' for b, d in dates.items())}. "
                        f"FCRA §623(a)(1) requires furnishers to report accurate information to all bureaus."
                    ),
                    severity=Severity.MEDIUM
                ))

        return discrepancies

    @staticmethod
    def check_balance_mismatch(accounts: Dict[Bureau, Account]) -> List[CrossBureauDiscrepancy]:
        """
        Check if balance differs across bureaus.

        Zero tolerance - FCRA requires "maximum possible accuracy".
        Balance reported on the same date should be identical across all bureaus.
        """
        discrepancies = []

        balances = {
            bureau: acc.balance
            for bureau, acc in accounts.items()
            if acc.balance is not None
        }

        if len(balances) >= 2:
            unique_balances = set(balances.values())

            # Zero tolerance - any difference is a violation
            if len(unique_balances) > 1:
                ref_account = list(accounts.values())[0]
                balance_list = list(balances.values())
                max_balance = max(balance_list)
                min_balance = min(balance_list)
                diff = max_balance - min_balance

                discrepancies.append(CrossBureauDiscrepancy(
                    violation_type=ViolationType.BALANCE_MISMATCH,
                    creditor_name=ref_account.creditor_name,
                    account_fingerprint=create_account_fingerprint(ref_account),
                    field_name="Balance",
                    values_by_bureau={b: f"${v:,.2f}" for b, v in balances.items()},
                    description=(
                        f"Balance inconsistent across bureaus for {ref_account.creditor_name}: "
                        f"{', '.join(f'{b.value}=${v:,.2f}' for b, v in balances.items())} "
                        f"(${diff:,.2f} difference). "
                        f"FCRA §623(a)(1) requires furnishers to report accurate information to all bureaus."
                    ),
                    severity=Severity.MEDIUM
                ))

        return discrepancies

    @staticmethod
    def check_status_mismatch(accounts: Dict[Bureau, Account]) -> List[CrossBureauDiscrepancy]:
        """Check if account status differs across bureaus."""
        discrepancies = []

        statuses = {
            bureau: acc.account_status
            for bureau, acc in accounts.items()
        }

        unique_statuses = set(statuses.values())
        if len(unique_statuses) > 1:
            ref_account = list(accounts.values())[0]
            discrepancies.append(CrossBureauDiscrepancy(
                violation_type=ViolationType.STATUS_MISMATCH,
                creditor_name=ref_account.creditor_name,
                account_fingerprint=create_account_fingerprint(ref_account),
                field_name="Account Status",
                values_by_bureau={b: s.value for b, s in statuses.items()},
                description=(
                    f"Account status differs across bureaus for {ref_account.creditor_name}"
                ),
                severity=Severity.MEDIUM
            ))

        return discrepancies

    @staticmethod
    def check_payment_history_mismatch(accounts: Dict[Bureau, Account]) -> List[CrossBureauDiscrepancy]:
        """Check if payment history differs across bureaus."""
        discrepancies = []

        histories = {
            bureau: acc.payment_pattern
            for bureau, acc in accounts.items()
            if acc.payment_pattern
        }

        if len(histories) >= 2:
            unique_histories = set(histories.values())
            if len(unique_histories) > 1:
                ref_account = list(accounts.values())[0]
                discrepancies.append(CrossBureauDiscrepancy(
                    violation_type=ViolationType.PAYMENT_HISTORY_MISMATCH,
                    creditor_name=ref_account.creditor_name,
                    account_fingerprint=create_account_fingerprint(ref_account),
                    field_name="Payment History",
                    values_by_bureau=histories,
                    description=(
                        f"Payment history differs across bureaus for {ref_account.creditor_name}"
                    ),
                    severity=Severity.MEDIUM
                ))

        return discrepancies

    @staticmethod
    def check_past_due_mismatch(accounts: Dict[Bureau, Account]) -> List[CrossBureauDiscrepancy]:
        """Check if past due amount differs across bureaus."""
        discrepancies = []

        past_dues = {
            bureau: acc.past_due_amount
            for bureau, acc in accounts.items()
            if acc.past_due_amount is not None
        }

        if len(past_dues) >= 2:
            unique_values = set(past_dues.values())
            if len(unique_values) > 1:
                ref_account = list(accounts.values())[0]
                discrepancies.append(CrossBureauDiscrepancy(
                    violation_type=ViolationType.PAST_DUE_MISMATCH,
                    creditor_name=ref_account.creditor_name,
                    account_fingerprint=create_account_fingerprint(ref_account),
                    field_name="Past Due Amount",
                    values_by_bureau={b: f"${v:,.2f}" for b, v in past_dues.items()},
                    description=(
                        f"Past due amount differs across bureaus for {ref_account.creditor_name}"
                    ),
                    severity=Severity.MEDIUM
                ))

        return discrepancies

    @staticmethod
    def check_closed_vs_open_conflict(accounts: Dict[Bureau, Account]) -> List[CrossBureauDiscrepancy]:
        """Check if one bureau shows closed while another shows open."""
        discrepancies = []

        from ...models.ssot import AccountStatus

        statuses = {bureau: acc.account_status for bureau, acc in accounts.items()}

        has_open = any(s in [AccountStatus.OPEN] for s in statuses.values())
        has_closed = any(s in [AccountStatus.CLOSED, AccountStatus.PAID] for s in statuses.values())

        if has_open and has_closed:
            ref_account = list(accounts.values())[0]
            discrepancies.append(CrossBureauDiscrepancy(
                violation_type=ViolationType.CLOSED_VS_OPEN_CONFLICT,
                creditor_name=ref_account.creditor_name,
                account_fingerprint=create_account_fingerprint(ref_account),
                field_name="Open/Closed Status",
                values_by_bureau={b: s.value for b, s in statuses.items()},
                description=(
                    f"Account shows as OPEN on some bureaus but CLOSED on others for "
                    f"{ref_account.creditor_name}"
                ),
                severity=Severity.HIGH
            ))

        return discrepancies

    @staticmethod
    def check_creditor_name_mismatch(accounts: Dict[Bureau, Account]) -> List[CrossBureauDiscrepancy]:
        """Check if creditor names are materially different across bureaus."""
        discrepancies = []

        names = {bureau: acc.creditor_name for bureau, acc in accounts.items()}
        normalized = {bureau: normalize_creditor_name(name) for bureau, name in names.items()}

        # Check if normalized names differ significantly
        norm_list = list(normalized.values())
        if len(set(norm_list)) > 1:
            # Use sequence matcher to check similarity
            all_similar = True
            for i, n1 in enumerate(norm_list):
                for n2 in norm_list[i+1:]:
                    ratio = SequenceMatcher(None, n1, n2).ratio()
                    if ratio < 0.7:  # Less than 70% similar
                        all_similar = False
                        break

            if not all_similar:
                ref_account = list(accounts.values())[0]
                discrepancies.append(CrossBureauDiscrepancy(
                    violation_type=ViolationType.CREDITOR_NAME_MISMATCH,
                    creditor_name=ref_account.creditor_name,
                    account_fingerprint=create_account_fingerprint(ref_account),
                    field_name="Creditor Name",
                    values_by_bureau=names,
                    description=(
                        f"Creditor name differs significantly across bureaus"
                    ),
                    severity=Severity.LOW
                ))

        return discrepancies

    @staticmethod
    def check_account_number_mismatch(accounts: Dict[Bureau, Account]) -> List[CrossBureauDiscrepancy]:
        """Check if account numbers (last 4) differ across bureaus."""
        discrepancies = []

        acct_nums = {
            bureau: normalize_account_number(acc.account_number)
            for bureau, acc in accounts.items()
            if acc.account_number
        }

        if len(acct_nums) >= 2:
            unique_nums = set(acct_nums.values())
            if len(unique_nums) > 1:
                ref_account = list(accounts.values())[0]
                discrepancies.append(CrossBureauDiscrepancy(
                    violation_type=ViolationType.ACCOUNT_NUMBER_MISMATCH,
                    creditor_name=ref_account.creditor_name,
                    account_fingerprint=create_account_fingerprint(ref_account),
                    field_name="Account Number (last 4)",
                    values_by_bureau=acct_nums,
                    description=(
                        f"Account number (last 4) differs across bureaus for "
                        f"{ref_account.creditor_name}"
                    ),
                    severity=Severity.LOW
                ))

        return discrepancies


# =============================================================================
# MAIN CROSS-BUREAU AUDIT FUNCTION
# =============================================================================

def audit_cross_bureau(
    reports: Dict[Bureau, NormalizedReport]
) -> List[CrossBureauDiscrepancy]:
    """
    Run all cross-bureau rules against matched accounts.

    Args:
        reports: Dict mapping Bureau to NormalizedReport

    Returns:
        List of CrossBureauDiscrepancy objects
    """
    if len(reports) < 2:
        logger.info("Need at least 2 bureau reports for cross-bureau analysis")
        return []

    all_discrepancies: List[CrossBureauDiscrepancy] = []
    rules = CrossBureauRules()

    # Match accounts across bureaus
    matched_groups = match_accounts_across_bureaus(reports)
    logger.info(f"Found {len(matched_groups)} account groups across bureaus")

    # Run all rules on each matched group
    for accounts in matched_groups:
        all_discrepancies.extend(rules.check_dofd_mismatch(accounts))
        all_discrepancies.extend(rules.check_date_opened_mismatch(accounts))
        all_discrepancies.extend(rules.check_balance_mismatch(accounts))
        all_discrepancies.extend(rules.check_status_mismatch(accounts))
        all_discrepancies.extend(rules.check_payment_history_mismatch(accounts))
        all_discrepancies.extend(rules.check_past_due_mismatch(accounts))
        all_discrepancies.extend(rules.check_closed_vs_open_conflict(accounts))
        all_discrepancies.extend(rules.check_creditor_name_mismatch(accounts))
        all_discrepancies.extend(rules.check_account_number_mismatch(accounts))

    logger.info(f"Found {len(all_discrepancies)} cross-bureau discrepancies")
    return all_discrepancies
