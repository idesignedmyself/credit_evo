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
                    account_number_masked=ref_account.account_number_masked or "",
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
                    account_number_masked=ref_account.account_number_masked or "",
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
                    account_number_masked=ref_account.account_number_masked or "",
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
                account_number_masked=ref_account.account_number_masked or "",
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
                    account_number_masked=ref_account.account_number_masked or "",
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
                    account_number_masked=ref_account.account_number_masked or "",
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
                account_number_masked=ref_account.account_number_masked or "",
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
                    account_number_masked=ref_account.account_number_masked or "",
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
                    account_number_masked=ref_account.account_number_masked or "",
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

    @staticmethod
    def check_dispute_flag_mismatch(accounts: Dict[Bureau, Account]) -> List[CrossBureauDiscrepancy]:
        """
        Check if dispute flags are inconsistent across bureaus.

        Under FCRA §623(a)(3), furnishers must report dispute status to ALL bureaus.
        If one bureau shows "Account disputed by consumer" (XB code) but another
        bureau doesn't show this, the furnisher is failing to properly report
        the dispute across all bureaus.

        Detection Logic:
        - Parse Comments/Remarks field for dispute-related phrases
        - Active dispute indicators (XB): "disputed by consumer", "consumer disputes"
        - Resolved dispute indicators (XH/XC): "dispute resolved", "was in dispute"
        - If ANY bureau shows active dispute but another shows no dispute text,
          flag as DISPUTE_FLAG_MISMATCH
        """
        discrepancies = []

        # Dispute indicator phrases (from Comments field)
        # Active dispute (XB code translated to text)
        active_dispute_phrases = [
            'disputed by consumer',
            'consumer disputes',
            'account information disputed',
            'customer disputed',
            'consumer disputes this account',
            'account disputed',
        ]

        # Resolved dispute (XH/XC codes translated to text)
        resolved_dispute_phrases = [
            'dispute resolved',
            'was in dispute',
            'previously disputed',
            'dispute has been resolved',
            'now resolved',
        ]

        def has_dispute_text(remarks: Optional[str]) -> Tuple[bool, bool, str]:
            """
            Check if remarks contain dispute-related text.
            Returns: (has_active_dispute, has_resolved_dispute, matched_phrase)
            """
            if not remarks:
                return False, False, ""

            remarks_lower = remarks.lower()

            # Check for active dispute
            for phrase in active_dispute_phrases:
                if phrase in remarks_lower:
                    return True, False, phrase

            # Check for resolved dispute
            for phrase in resolved_dispute_phrases:
                if phrase in remarks_lower:
                    return False, True, phrase

            return False, False, ""

        # Get dispute status for each bureau
        dispute_status: Dict[Bureau, Dict] = {}

        for bureau, account in accounts.items():
            # Get remarks from bureau-specific data if available
            remarks = None
            if hasattr(account, 'bureaus') and account.bureaus and bureau in account.bureaus:
                bureau_data = account.bureaus[bureau]
                remarks = getattr(bureau_data, 'remarks', None)

            has_active, has_resolved, phrase = has_dispute_text(remarks)

            dispute_status[bureau] = {
                'has_active_dispute': has_active,
                'has_resolved_dispute': has_resolved,
                'has_any_dispute': has_active or has_resolved,
                'phrase': phrase,
                'remarks': remarks or "(no comments)"
            }

        # CRITICAL FIX: Only check for inconsistency when there's an ACTIVE dispute
        # "Resolved" vs "None" is NOT a violation - when investigation ends, bureaus may
        # either leave a "Dispute Resolved" note or simply remove the flag entirely.
        # Both are acceptable outcomes. We only care when an ACTIVE dispute exists
        # and other bureaus don't show it.

        # Check if ANY bureau has an ACTIVE dispute (XB code)
        has_active_dispute = any(s['has_active_dispute'] for s in dispute_status.values())

        # If no active disputes, don't flag anything (Resolved vs None is fine)
        if not has_active_dispute:
            return discrepancies

        # Now check: which bureaus are missing the active dispute flag?
        bureaus_with_active_dispute = [b for b, s in dispute_status.items() if s['has_active_dispute']]
        bureaus_without_dispute = [b for b, s in dispute_status.items() if not s['has_any_dispute']]

        # Only flag if at least one bureau shows ACTIVE dispute AND at least one shows nothing
        if len(bureaus_with_active_dispute) >= 1 and len(bureaus_without_dispute) >= 1:
            ref_account = list(accounts.values())[0]

            # Build description showing what each bureau has
            bureau_details = []
            for bureau, status in dispute_status.items():
                if status['has_active_dispute']:
                    bureau_details.append(f"{bureau.value}: DISPUTED ('{status['phrase']}')")
                elif status['has_resolved_dispute']:
                    bureau_details.append(f"{bureau.value}: Dispute Resolved ('{status['phrase']}')")
                else:
                    # Truncate long remarks
                    remarks_preview = status['remarks'][:50] + "..." if len(status['remarks']) > 50 else status['remarks']
                    bureau_details.append(f"{bureau.value}: NO DISPUTE FLAG ({remarks_preview})")

            discrepancies.append(CrossBureauDiscrepancy(
                violation_type=ViolationType.DISPUTE_FLAG_MISMATCH,
                creditor_name=ref_account.creditor_name,
                account_number_masked=ref_account.account_number_masked or "",
                account_fingerprint=create_account_fingerprint(ref_account),
                field_name="Dispute Status (Compliance Condition Code)",
                values_by_bureau={
                    b: "DISPUTED" if s['has_active_dispute'] else ("RESOLVED" if s['has_resolved_dispute'] else "NO FLAG")
                    for b, s in dispute_status.items()
                },
                description=(
                    f"Dispute flag inconsistent across bureaus for {ref_account.creditor_name}: "
                    f"{'; '.join(bureau_details)}. "
                    f"Under FCRA §623(a)(3), furnishers must report dispute status to ALL bureaus."
                ),
                severity=Severity.HIGH
            ))

        return discrepancies

    @staticmethod
    def check_ecoa_code_mismatch(accounts: Dict[Bureau, Account]) -> List[CrossBureauDiscrepancy]:
        """
        Check if ECOA code (liability designation) differs across bureaus.

        The ECOA Code (Metro 2 Field 6) defines the consumer's legal liability:
        - Individual (Code 1): Consumer is solely responsible
        - Joint (Code 2): Consumer shares liability with another party
        - Authorized User (Code 3): Consumer is NOT liable for the debt

        It is factually impossible to be both "Individual" and "Joint" liable for
        the same account simultaneously. If bureaus differ, one must be wrong.

        Legal Basis: FCRA §623(a)(1) - furnishers must report accurate information
        """
        discrepancies = []

        # Normalize ECOA codes for comparison
        # Common variations: "Individual", "Joint", "Authorized User", "Auth User", etc.
        def normalize_ecoa(code: Optional[str]) -> Optional[str]:
            if not code:
                return None
            code_lower = code.lower().strip()

            # Map to canonical values
            if 'individual' in code_lower:
                return 'Individual'
            elif 'joint' in code_lower:
                return 'Joint'
            elif 'authorized' in code_lower or 'auth user' in code_lower or code_lower == 'au':
                return 'Authorized User'
            elif 'co-signer' in code_lower or 'cosigner' in code_lower:
                return 'Co-Signer'
            elif 'maker' in code_lower:
                return 'Maker'
            else:
                return code.strip()  # Return as-is if unknown

        # Get ECOA code from each bureau
        ecoa_codes: Dict[Bureau, str] = {}
        raw_codes: Dict[Bureau, str] = {}

        for bureau, account in accounts.items():
            # Get bureau_code from bureau-specific data
            bureau_code = None
            if hasattr(account, 'bureaus') and account.bureaus and bureau in account.bureaus:
                bureau_data = account.bureaus[bureau]
                bureau_code = getattr(bureau_data, 'bureau_code', None)

            if bureau_code:
                normalized = normalize_ecoa(bureau_code)
                if normalized:
                    ecoa_codes[bureau] = normalized
                    raw_codes[bureau] = bureau_code

        # Need at least 2 bureaus reporting ECOA to compare
        if len(ecoa_codes) < 2:
            return discrepancies

        # Check for inconsistency
        unique_codes = set(ecoa_codes.values())
        if len(unique_codes) > 1:
            ref_account = list(accounts.values())[0]

            # Build description showing the conflict
            code_details = [f"{b.value}: {c}" for b, c in ecoa_codes.items()]

            discrepancies.append(CrossBureauDiscrepancy(
                violation_type=ViolationType.ECOA_CODE_MISMATCH,
                creditor_name=ref_account.creditor_name,
                account_number_masked=ref_account.account_number_masked or "",
                account_fingerprint=create_account_fingerprint(ref_account),
                field_name="ECOA Code / Liability Designation",
                values_by_bureau={b: c for b, c in ecoa_codes.items()},
                description=(
                    f"Inconsistent liability designation across bureaus for {ref_account.creditor_name}: "
                    f"{', '.join(code_details)}. "
                    f"A consumer cannot be both '{list(unique_codes)[0]}' and '{list(unique_codes)[1]}' "
                    f"liable for the same account simultaneously. "
                    f"Under FCRA §623(a)(1), furnishers must report accurate information to all bureaus."
                ),
                severity=Severity.HIGH
            ))

        return discrepancies

    @staticmethod
    def check_authorized_user_derogatory(accounts: Dict[Bureau, Account]) -> List[CrossBureauDiscrepancy]:
        """
        Check if Authorized User accounts have derogatory marks.

        Authorized Users (ECOA Code 3) are NOT contractually liable for the debt.
        Reporting late payments or derogatory status on an AU's file is improper
        because they cannot be legally delinquent on debt they don't owe.

        This is a single-bureau check but runs during cross-bureau analysis
        because we have access to bureau_code there.

        Legal Basis: FCRA §623(a)(1), Equal Credit Opportunity Act (ECOA)
        """
        discrepancies = []

        # Derogatory indicators in payment status
        derogatory_statuses = [
            'collection', 'chargeoff', 'charge-off', 'charged off',
            'delinquent', 'past due', 'late', '30 days', '60 days',
            '90 days', '120 days', 'foreclosure', 'repossession',
        ]

        # Late payment markers in payment history
        late_markers = ['30', '60', '90', '120', '150', '180', 'CO', 'FC', 'RP']

        for bureau, account in accounts.items():
            # Get bureau_code from bureau-specific data
            bureau_code = None
            payment_status = None
            payment_history = []

            if hasattr(account, 'bureaus') and account.bureaus and bureau in account.bureaus:
                bureau_data = account.bureaus[bureau]
                bureau_code = getattr(bureau_data, 'bureau_code', None)
                payment_status = getattr(bureau_data, 'payment_status', None)
                payment_history = getattr(bureau_data, 'payment_history', []) or []

            if not bureau_code:
                continue

            # Check if this is an Authorized User
            code_lower = bureau_code.lower()
            is_auth_user = (
                'authorized' in code_lower or
                'auth user' in code_lower or
                code_lower == 'au'
            )

            if not is_auth_user:
                continue

            # Check for derogatory indicators
            has_derogatory = False
            derog_reason = []

            # Check payment status
            if payment_status:
                status_lower = payment_status.lower()
                for derog in derogatory_statuses:
                    if derog in status_lower:
                        has_derogatory = True
                        derog_reason.append(f"Payment Status: '{payment_status}'")
                        break

            # Check payment history for late markers
            late_months = []
            for entry in payment_history:
                status = str(entry.get('status', '')).upper()
                for marker in late_markers:
                    if marker in status and status != 'OK':
                        late_months.append(f"{entry.get('month', '')} {entry.get('year', '')}: {status}")
                        has_derogatory = True
                        break

            if late_months:
                derog_reason.append(f"Late markers in payment history: {', '.join(late_months[:3])}")
                if len(late_months) > 3:
                    derog_reason.append(f"(+{len(late_months) - 3} more)")

            # Check account status
            if hasattr(account, 'account_status'):
                from ...models.ssot import AccountStatus
                if account.account_status in [AccountStatus.COLLECTION, AccountStatus.CHARGEOFF]:
                    has_derogatory = True
                    derog_reason.append(f"Account Status: {account.account_status.value}")

            if has_derogatory:
                ref_account = account
                discrepancies.append(CrossBureauDiscrepancy(
                    violation_type=ViolationType.AUTHORIZED_USER_DEROGATORY,
                    creditor_name=ref_account.creditor_name,
                    account_number_masked=ref_account.account_number_masked or "",
                    account_fingerprint=create_account_fingerprint(ref_account),
                    field_name="Authorized User with Derogatory Marks",
                    values_by_bureau={bureau: f"AU with derogatory: {'; '.join(derog_reason)}"},
                    description=(
                        f"Authorized User account with derogatory marks on {bureau.value} for "
                        f"{ref_account.creditor_name}: {'; '.join(derog_reason)}. "
                        f"As an Authorized User (ECOA Code 3), the consumer is NOT contractually liable "
                        f"for this debt. Reporting delinquency or negative marks on a non-liable party's "
                        f"credit file violates FCRA §623(a)(1) accuracy requirements and the ECOA."
                    ),
                    severity=Severity.HIGH
                ))

        return discrepancies

    @staticmethod
    def check_missing_tradelines(accounts: Dict[Bureau, Account]) -> List[CrossBureauDiscrepancy]:
        """
        Detects accounts that are reporting to some bureaus but missing from others.

        The Problem:
        - You have a Capital One card that shows up on TU and EXP
        - But it's completely missing from EQ
        - This explains "Why is my Equifax score 50 points lower?"
        - Missing positive history can significantly impact Credit Mix factor

        Note: This is rarely a legal violation (creditors are not required to report
        to all 3 bureaus). This is an INFORMATIONAL finding that explains score gaps.

        Args:
            accounts: Dict mapping Bureau to Account for a matched account group

        Returns:
            List of MISSING_TRADELINE_INCONSISTENCY discrepancies
        """
        discrepancies = []

        # Identify which bureaus are present for this account
        reporting_bureaus = list(accounts.keys())
        expected_bureaus = [Bureau.TRANSUNION, Bureau.EXPERIAN, Bureau.EQUIFAX]

        # Find the missing ones
        missing_bureaus = [b for b in expected_bureaus if b not in reporting_bureaus]

        # If it's on at least 1 but not all 3...
        if missing_bureaus and len(reporting_bureaus) >= 1:
            # Grab a representative account to attach the discrepancy to
            primary_account = list(accounts.values())[0]

            # Format bureau names for display
            reporting_names = [b.value.title() for b in reporting_bureaus]
            missing_names = [b.value.title() for b in missing_bureaus]

            discrepancies.append(CrossBureauDiscrepancy(
                violation_type=ViolationType.MISSING_TRADELINE_INCONSISTENCY,
                creditor_name=primary_account.creditor_name,
                account_number_masked=primary_account.account_number_masked or "",
                account_fingerprint=create_account_fingerprint(primary_account),
                field_name="Bureau Reporting Consistency",
                values_by_bureau={
                    **{b: "Reporting" for b in reporting_bureaus},
                    **{b: "MISSING" for b in missing_bureaus}
                },
                description=(
                    f"Inconsistent Bureau Reporting: This account ({primary_account.creditor_name}) "
                    f"is reported to {', '.join(reporting_names)} but is MISSING from "
                    f"{', '.join(missing_names)}. While creditors are not legally required to report "
                    f"to all three bureaus, missing positive payment history can cause significant "
                    f"score discrepancies. If this is a positive account with good payment history, "
                    f"consider contacting the creditor to request they report to all bureaus."
                ),
                severity=Severity.LOW  # Informational - not a legal violation
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
