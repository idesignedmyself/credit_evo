"""
Credit Engine 2.0 - Audit Rules

Deterministic rule-based violation detection.
NO LLMs used here - pure logic only.

Rule Categories:
1. Single-Bureau Rules - violations within one bureau's data
2. Furnisher Rules - rules based on furnisher type classification
3. Temporal Rules - date-based violations (obsolescence, re-aging)
"""
from __future__ import annotations
import logging
from datetime import date, datetime, timedelta
from typing import List

from ...models.ssot import (
    Account, NormalizedReport, Violation, BureauAccountData, Inquiry, PublicRecord,
    ViolationType, Severity, FurnisherType, AccountStatus, Bureau
)
from typing import Dict, Any
from typing import Optional

logger = logging.getLogger(__name__)


def _add_years(d: date, years: int) -> date:
    """Add years to a date, handling leap years."""
    try:
        return d.replace(year=d.year + years)
    except ValueError:
        # Feb 29 in leap year -> Feb 28
        return d.replace(month=2, day=28, year=d.year + years)


# =============================================================================
# SINGLE-BUREAU RULES
# =============================================================================

class SingleBureauRules:
    """
    Rules that check individual account data within a single bureau.
    These detect Metro-2 field violations and data quality issues.
    """

    @staticmethod
    def check_missing_dofd(account: Account, bureau: Bureau) -> List[Violation]:
        """
        Check for missing Date of First Delinquency on derogatory accounts.

        FCRA §605(c)(1) requires DOFD for the 7-year reporting period.
        """
        violations = []

        # Only applies to derogatory accounts
        if account.account_status not in [AccountStatus.CHARGEOFF, AccountStatus.COLLECTION, AccountStatus.DEROGATORY]:
            return violations

        if account.date_of_first_delinquency is None:
            violations.append(Violation(
                violation_type=ViolationType.MISSING_DOFD,
                severity=Severity.HIGH,
                account_id=account.account_id,
                creditor_name=account.creditor_name,
                account_number_masked=account.account_number_masked,
                furnisher_type=account.furnisher_type,
                bureau=bureau,
                description=(
                    f"This {account.account_status.value} account is missing the Date of First "
                    f"Delinquency (DOFD) in Metro 2 Field 25. Without DOFD, the 7-year reporting "
                    f"period cannot be determined."
                ),
                expected_value="Valid DOFD date",
                actual_value="Missing/Not Reported",
                fcra_section="605(c)(1)",
                metro2_field="25",
                evidence={
                    "status": account.account_status.value,
                    "balance": account.balance
                }
            ))

        return violations

    @staticmethod
    def check_missing_date_opened(account: Account, bureau: Bureau) -> List[Violation]:
        """Check for missing Date Opened."""
        violations = []

        if account.date_opened is None:
            violations.append(Violation(
                violation_type=ViolationType.MISSING_DATE_OPENED,
                severity=Severity.MEDIUM,
                account_id=account.account_id,
                creditor_name=account.creditor_name,
                account_number_masked=account.account_number_masked,
                furnisher_type=account.furnisher_type,
                bureau=bureau,
                description=(
                    f"This account is missing the Date Opened field. This is a required "
                    f"Metro 2 field that establishes when the account relationship began."
                ),
                expected_value="Valid date opened",
                actual_value="Missing/Not Reported",
                fcra_section="611(a)",
                metro2_field="10",
                evidence={}
            ))

        return violations

    @staticmethod
    def check_negative_balance(account: Account, bureau: Bureau) -> List[Violation]:
        """Check for negative balance which is invalid."""
        violations = []

        if account.balance is not None and account.balance < 0:
            violations.append(Violation(
                violation_type=ViolationType.NEGATIVE_BALANCE,
                severity=Severity.HIGH,
                account_id=account.account_id,
                creditor_name=account.creditor_name,
                account_number_masked=account.account_number_masked,
                furnisher_type=account.furnisher_type,
                bureau=bureau,
                description=(
                    f"This account reports a negative balance of ${account.balance:,.2f}. "
                    f"Negative balances are invalid under Metro 2 reporting standards."
                ),
                expected_value="Non-negative balance",
                actual_value=f"${account.balance:,.2f}",
                fcra_section="611(a)",
                metro2_field="17A",
                evidence={"balance": account.balance}
            ))

        return violations

    @staticmethod
    def check_past_due_exceeds_balance(account: Account, bureau: Bureau) -> List[Violation]:
        """Check if past due amount exceeds total balance."""
        violations = []

        if account.past_due_amount is not None and account.balance is not None:
            if account.past_due_amount > account.balance and account.balance > 0:
                violations.append(Violation(
                    violation_type=ViolationType.PAST_DUE_EXCEEDS_BALANCE,
                    severity=Severity.MEDIUM,
                    account_id=account.account_id,
                    creditor_name=account.creditor_name,
                    account_number_masked=account.account_number_masked,
                    furnisher_type=account.furnisher_type,
                    bureau=bureau,
                    description=(
                        f"Past due amount (${account.past_due_amount:,.2f}) exceeds total balance "
                        f"(${account.balance:,.2f}). This is a mathematical impossibility."
                    ),
                    expected_value=f"Past due ≤ ${account.balance:,.2f}",
                    actual_value=f"${account.past_due_amount:,.2f}",
                    fcra_section="611(a)",
                    metro2_field="17B",
                    evidence={
                        "past_due": account.past_due_amount,
                        "balance": account.balance
                    }
                ))

        return violations

    @staticmethod
    def check_future_dates(account: Account, bureau: Bureau) -> List[Violation]:
        """Check for dates in the future."""
        violations = []
        today = date.today()

        date_fields = [
            ("date_opened", "Date Opened", "10"),
            ("date_closed", "Date Closed", None),
            ("date_of_first_delinquency", "DOFD", "25"),
            ("date_last_activity", "Date Last Activity", None),
            ("date_reported", "Date Reported", None),
        ]

        for field_name, display_name, metro_field in date_fields:
            field_value = getattr(account, field_name, None)
            if field_value and field_value > today:
                violations.append(Violation(
                    violation_type=ViolationType.FUTURE_DATE,
                    severity=Severity.HIGH,
                    account_id=account.account_id,
                    creditor_name=account.creditor_name,
                    account_number_masked=account.account_number_masked,
                    furnisher_type=account.furnisher_type,
                    bureau=bureau,
                    description=(
                        f"{display_name} is set to a future date ({field_value}). "
                        f"Future dates are invalid and indicate unverified data."
                    ),
                    expected_value=f"Date ≤ {today}",
                    actual_value=str(field_value),
                    fcra_section="611(a)",
                    metro2_field=metro_field,
                    evidence={field_name: str(field_value)}
                ))

        return violations

    @staticmethod
    def check_dofd_after_date_opened(account: Account, bureau: Bureau) -> List[Violation]:
        """Check if DOFD is before Date Opened (impossible)."""
        violations = []

        if account.date_opened and account.date_of_first_delinquency:
            if account.date_of_first_delinquency < account.date_opened:
                violations.append(Violation(
                    violation_type=ViolationType.DOFD_AFTER_DATE_OPENED,
                    severity=Severity.HIGH,
                    account_id=account.account_id,
                    creditor_name=account.creditor_name,
                    account_number_masked=account.account_number_masked,
                    furnisher_type=account.furnisher_type,
                    bureau=bureau,
                    description=(
                        f"Date of First Delinquency ({account.date_of_first_delinquency}) is before "
                        f"Date Opened ({account.date_opened}). A delinquency cannot occur before "
                        f"the account existed."
                    ),
                    expected_value=f"DOFD ≥ {account.date_opened}",
                    actual_value=str(account.date_of_first_delinquency),
                    fcra_section="611(a)",
                    metro2_field="25",
                    evidence={
                        "dofd": str(account.date_of_first_delinquency),
                        "date_opened": str(account.date_opened)
                    }
                ))

        return violations

    @staticmethod
    def check_missing_scheduled_payment(account: Account, bureau: Bureau) -> List[Violation]:
        """Check for missing scheduled payment on OC non-charge-off accounts."""
        violations = []

        if account.furnisher_type == FurnisherType.OC_NON_CHARGEOFF:
            if account.scheduled_payment is None and account.account_status == AccountStatus.OPEN:
                violations.append(Violation(
                    violation_type=ViolationType.MISSING_SCHEDULED_PAYMENT,
                    severity=Severity.LOW,
                    account_id=account.account_id,
                    creditor_name=account.creditor_name,
                    account_number_masked=account.account_number_masked,
                    furnisher_type=account.furnisher_type,
                    bureau=bureau,
                    description=(
                        f"This open original creditor account is missing the Scheduled Payment field "
                        f"(Metro 2 Field 15). This omission violates the duty under 15 U.S.C. § 1681e(b) "
                        f"to maintain reasonable procedures to assure maximum possible accuracy."
                    ),
                    expected_value="Valid scheduled payment amount",
                    actual_value="Not Reported",
                    fcra_section="611(a)",
                    metro2_field="15",
                    evidence={}
                ))

        return violations

    @staticmethod
    def check_student_loan_portfolio_mismatch(account: Account, bureau: Bureau) -> List[Violation]:
        """
        Detects Student Loans reported as 'Open' or 'Revolving' instead of 'Installment'.

        Under Metro 2 standards, Educational Loans are Installment contracts (Portfolio Type I)
        with fixed terms and amortization schedules. Reporting them as 'Open Account' (Type O)
        or 'Revolving' is factually incorrect and damages the Credit Mix scoring factor (10% of FICO).

        Example from screenshot: US DEPT ED reported as "Open Account" but Detail shows "Educational"
        This is a violation - student loans should be "Installment".
        """
        violations = []

        # 1. Identify if this is a Student Loan
        # Check account_type, account_type_detail from bureau data, and creditor name
        account_type = (account.account_type or "").lower()
        creditor_text = (account.creditor_name or "").lower()

        # Get account_type_detail from bureau data if available
        account_type_detail = ""
        bureau_data = account.get_bureau_data(bureau)
        if bureau_data:
            if hasattr(bureau_data, 'account_type_detail') and bureau_data.account_type_detail:
                account_type_detail = bureau_data.account_type_detail.lower()

        # Student loan identifiers
        student_loan_keywords = [
            "educational", "student loan", "student", "dept of ed", "dept ed",
            "nelnet", "navient", "mohela", "fedloan", "sallie mae", "great lakes",
            "acs education", "edfinancial", "pheaa", "ecmc"
        ]

        is_student_loan = any(k in account_type_detail for k in student_loan_keywords) or \
                          any(k in creditor_text for k in student_loan_keywords) or \
                          any(k in account_type for k in student_loan_keywords)

        if not is_student_loan:
            return violations

        # 2. Check if the Account Type is wrong (should be Installment, not Open/Revolving)
        # Account Type should contain "installment" for student loans
        if "open" in account_type or "revolving" in account_type:
            violations.append(Violation(
                violation_type=ViolationType.METRO2_PORTFOLIO_MISMATCH,
                severity=Severity.MEDIUM,
                account_id=account.account_id,
                creditor_name=account.creditor_name,
                account_number_masked=account.account_number_masked,
                furnisher_type=account.furnisher_type,
                bureau=bureau,
                description=(
                    f"Student Loan (Educational) is misclassified as '{account.account_type}'. "
                    f"Under Metro 2 standards, Educational loans are defined as Installment "
                    f"(Portfolio Type I) because they have fixed terms and payment schedules. "
                    f"Reporting this as an 'Open Account' (Portfolio Type O) is factually incorrect "
                    f"and negatively impacts the Credit Mix scoring factor (10% of FICO). "
                    f"Detail: {account_type_detail or 'Educational'}"
                ),
                expected_value="Account Type: Installment",
                actual_value=f"Account Type: {account.account_type}",
                fcra_section="623(a)(1)",
                metro2_field="Field 8 (Portfolio Type)",
                evidence={
                    "account_type": account.account_type,
                    "account_type_detail": account_type_detail,
                    "creditor_name": account.creditor_name,
                    "issue": "student_loan_as_open_account"
                }
            ))

        return violations

    @staticmethod
    def check_balance_exceeds_high_credit(account: Account, bureau: Bureau) -> List[Violation]:
        """Check if balance exceeds high credit (invalid)."""
        violations = []

        if account.balance is not None and account.high_credit is not None:
            if account.balance > account.high_credit and account.high_credit > 0:
                violations.append(Violation(
                    violation_type=ViolationType.BALANCE_EXCEEDS_HIGH_CREDIT,
                    severity=Severity.MEDIUM,
                    account_id=account.account_id,
                    creditor_name=account.creditor_name,
                    account_number_masked=account.account_number_masked,
                    furnisher_type=account.furnisher_type,
                    bureau=bureau,
                    description=(
                        f"Current balance (${account.balance:,.2f}) exceeds high credit "
                        f"(${account.high_credit:,.2f}), which is inconsistent."
                    ),
                    expected_value=f"Balance ≤ ${account.high_credit:,.2f}",
                    actual_value=f"${account.balance:,.2f}",
                    fcra_section="611(a)",
                    metro2_field="17A",
                    evidence={
                        "balance": account.balance,
                        "high_credit": account.high_credit
                    }
                ))

        return violations

    @staticmethod
    def check_balance_exceeds_credit_limit(account: Account, bureau: Bureau) -> List[Violation]:
        """
        Check if balance exceeds credit limit without explanation.

        For OPEN revolving accounts, balance should not exceed credit limit.
        If it does, this suggests inaccurate reporting.

        EXCLUSIONS (balance > limit is expected/normal for these):
        - Charged-off accounts (fees/interest added push balance over limit)
        - Collection accounts (transferred balances include fees)
        - Accounts with OC_CHARGEOFF furnisher type
        - Accounts with payment_status indicating chargeoff/collection
        """
        violations = []

        if account.balance is not None and account.credit_limit is not None:
            if account.balance > account.credit_limit and account.credit_limit > 0:
                # EXCLUDE charged-off and collection accounts - balance > limit is expected
                # because late fees, interest, and over-limit fees get added to the balance
                excluded_statuses = {AccountStatus.CHARGEOFF, AccountStatus.COLLECTION, AccountStatus.DEROGATORY}
                if account.account_status in excluded_statuses:
                    return violations

                # Also check furnisher type - OC chargeoffs are excluded
                if account.furnisher_type == FurnisherType.OC_CHARGEOFF:
                    return violations

                # Also check payment_status string for chargeoff/collection indicators
                if account.payment_status:
                    payment_lower = account.payment_status.lower()
                    chargeoff_indicators = ['chargeoff', 'charge-off', 'charge off', 'collection', 'charged off']
                    if any(indicator in payment_lower for indicator in chargeoff_indicators):
                        return violations

                # Only flag OPEN accounts where balance > limit is actually problematic
                violations.append(Violation(
                    violation_type=ViolationType.BALANCE_EXCEEDS_CREDIT_LIMIT,
                    severity=Severity.MEDIUM,
                    account_id=account.account_id,
                    creditor_name=account.creditor_name,
                    account_number_masked=account.account_number_masked,
                    furnisher_type=account.furnisher_type,
                    bureau=bureau,
                    description=(
                        f"Current balance (${account.balance:,.2f}) exceeds the reported "
                        f"credit limit (${account.credit_limit:,.2f}). For an open account, "
                        f"this is contradictory - the balance should not exceed the credit limit "
                        f"without explanation. This suggests inaccurate reporting."
                    ),
                    expected_value=f"Balance ≤ ${account.credit_limit:,.2f}",
                    actual_value=f"${account.balance:,.2f}",
                    fcra_section="623(a)(1)",
                    metro2_field="17A/21",
                    evidence={
                        "balance": account.balance,
                        "credit_limit": account.credit_limit,
                        "over_limit_amount": account.balance - account.credit_limit,
                        "account_status": str(account.account_status)
                    }
                ))

        return violations

    @staticmethod
    def check_negative_credit_limit(account: Account, bureau: Bureau) -> List[Violation]:
        """Check for negative credit limit (invalid)."""
        violations = []

        if account.credit_limit is not None and account.credit_limit < 0:
            violations.append(Violation(
                violation_type=ViolationType.NEGATIVE_CREDIT_LIMIT,
                severity=Severity.MEDIUM,
                account_id=account.account_id,
                creditor_name=account.creditor_name,
                account_number_masked=account.account_number_masked,
                furnisher_type=account.furnisher_type,
                bureau=bureau,
                description=(
                    f"This account reports a negative credit limit of ${account.credit_limit:,.2f}. "
                    f"Negative credit limits are invalid."
                ),
                expected_value="Non-negative credit limit",
                actual_value=f"${account.credit_limit:,.2f}",
                fcra_section="611(a)",
                metro2_field=None,
                evidence={"credit_limit": account.credit_limit}
            ))

        return violations

    @staticmethod
    def check_missing_dla(account: Account, bureau: Bureau) -> List[Violation]:
        """Check for missing Date Last Activity."""
        violations = []

        if account.date_last_activity is None and account.account_status != AccountStatus.UNKNOWN:
            violations.append(Violation(
                violation_type=ViolationType.MISSING_DLA,
                severity=Severity.LOW,
                account_id=account.account_id,
                creditor_name=account.creditor_name,
                account_number_masked=account.account_number_masked,
                furnisher_type=account.furnisher_type,
                bureau=bureau,
                description=(
                    f"This account is missing the Date Last Activity field, which indicates "
                    f"when the account was last updated."
                ),
                expected_value="Valid date last activity",
                actual_value="Not Reported",
                fcra_section="611(a)",
                metro2_field=None,
                evidence={}
            ))

        return violations

    @staticmethod
    def check_status_payment_history_mismatch(
        account: Account,
        bureau: Bureau,
        bureau_data: Optional[BureauAccountData] = None
    ) -> List[Violation]:
        """
        Check if Payment Status contradicts Payment History.

        FCRA §623(a)(1) requires accurate reporting. A charged-off account
        cannot have 24 consecutive months of "OK" (current) payment history.

        IMPORTANT: This rule ONLY fires when the Payment Status field explicitly
        indicates chargeoff/collection/derogatory. Comments alone (like "Closed by
        Credit Grantor") are NOT sufficient to trigger this violation, as a bank
        can legitimately close an unused account with all-OK history.

        Example violations (VALID):
        1. Payment Status = "Collection/Chargeoff" but History = all OK
        2. Payment Status = "Charge-off" but History = all OK
        3. Payment Status contains "Recovery" but History = all OK

        Example NON-violations (FALSE POSITIVES to avoid):
        1. Comments = "Closed by Credit Grantor" but Status = "Paid" and History = OK
           (This is a legitimate bank closure of unused account)
        """
        violations = []

        # Get payment history and remarks from bureau_data if provided
        payment_history = []
        remarks = ""
        if bureau_data:
            if hasattr(bureau_data, 'payment_history'):
                payment_history = bureau_data.payment_history or []
            if hasattr(bureau_data, 'remarks'):
                remarks = bureau_data.remarks or ""

        # Skip if no payment history to analyze
        if not payment_history:
            return violations

        # Check if payment_status indicates chargeoff/collection/derogatory
        payment_status = account.payment_status or ""
        payment_status_lower = payment_status.lower()
        remarks_lower = remarks.lower()

        # PRIMARY TRIGGER: Payment Status must explicitly indicate derogatory status
        # These are the "slam dunk" indicators that MUST be present in payment_status
        primary_derogatory_indicators = [
            'chargeoff', 'charge-off', 'charge off', 'charged off',
            'collection', 'derogatory', 'unpaid', 'bad debt',
            'written off', 'profit and loss', 'recovery',
            'repossession', 'repo', 'foreclosure'
        ]

        # BENIGN indicators - if these are in payment_status WITHOUT primary indicators,
        # do NOT fire even if comments mention "closed by credit grantor"
        benign_status_indicators = [
            'paid', 'closed', 'current', 'transferred'
        ]

        # Check if payment_status has a PRIMARY derogatory indicator
        is_derogatory_status = any(ind in payment_status_lower for ind in primary_derogatory_indicators)

        # Check if payment_status is benign (paid/closed without derogatory)
        is_benign_status = (
            any(ind in payment_status_lower for ind in benign_status_indicators) and
            not is_derogatory_status
        )

        # ONLY fire if payment_status explicitly indicates derogatory
        # Do NOT fire based on comments alone (avoids "Closed by Credit Grantor" false positives)
        if not is_derogatory_status:
            return violations

        # Additional check: If status is derogatory but also says "Paid", might be resolved
        # e.g., "Charge off - Paid" is a resolved chargeoff, still contradicts OK history though

        # Extract status codes from payment history
        # Format: [{"month": "Jan", "year": 2024, "status": "OK"}, ...]
        status_codes = []
        for entry in payment_history:
            if isinstance(entry, dict) and 'status' in entry:
                status_codes.append(entry.get('status', '').upper())

        if not status_codes:
            return violations

        # Count how many are "OK" (current/on-time)
        ok_count = sum(1 for s in status_codes if s in ('OK', 'C', 'CURRENT', '0', '-'))
        total_count = len(status_codes)

        # If 80%+ of the payment history shows "OK" but status indicates chargeoff,
        # that's a contradiction
        if total_count >= 6 and ok_count >= (total_count * 0.8):
            # Build source description - always payment_status, optionally include comments
            chargeoff_source = [f"Payment Status: \"{payment_status}\""]

            # Check if comments provide additional supporting evidence (but not sole trigger)
            comment_derog_indicators = [
                'charged off', 'charge off', 'collection', 'recovery',
                'bad debt', 'written off', 'profit and loss'
            ]
            has_supporting_comments = any(ind in remarks_lower for ind in comment_derog_indicators)
            if has_supporting_comments and remarks:
                chargeoff_source.append(f"Comments: \"{remarks[:100]}{'...' if len(remarks) > 100 else ''}\"")

            source_text = " and ".join(chargeoff_source)
            violations.append(Violation(
                violation_type=ViolationType.STATUS_PAYMENT_HISTORY_MISMATCH,
                severity=Severity.HIGH,
                account_id=account.account_id,
                creditor_name=account.creditor_name,
                account_number_masked=account.account_number_masked,
                furnisher_type=account.furnisher_type,
                bureau=bureau,
                description=(
                    f"{source_text} indicates chargeoff/collection, but Payment History shows "
                    f"{ok_count} out of {total_count} months as current/OK. This is internally "
                    f"inconsistent - a charged-off account cannot have a mostly-current payment "
                    f"history. A charge-off requires prior delinquency (typically 120-180 days late)."
                ),
                expected_value="Payment history consistent with charged-off status (should show delinquency)",
                actual_value=f"{ok_count}/{total_count} months showing 'OK' despite chargeoff indication",
                fcra_section="623(a)(1)",
                metro2_field="17A/25",
                evidence={
                    "payment_status": payment_status,
                    "comments": remarks[:200] if remarks else None,
                    "ok_months": ok_count,
                    "total_months": total_count,
                    "history_sample": status_codes[:12],  # First 12 months
                    "chargeoff_source": chargeoff_source
                }
            ))

        return violations

    @staticmethod
    def check_phantom_late_payment(
        account: Account,
        bureau: Bureau,
        bureau_data: Optional[BureauAccountData] = None
    ) -> List[Violation]:
        """
        Check for "Phantom Late Payments" - late markers reported during periods
        when no payment was due ($0 scheduled payment or forbearance/deferment).

        FCRA §623(a)(1) requires accurate reporting. A consumer cannot be reported
        as 30/60/90 days late if:
        1. The scheduled payment was $0 (no payment required)
        2. The account was in forbearance, deferment, or hardship program
        3. The account had COVID-related payment pause

        This is especially common with:
        - Student loans during in-school deferment or forbearance
        - Mortgages during COVID forbearance (CARES Act)
        - Auto loans with payment deferrals
        - Credit cards with hardship programs

        Detection Logic:
        1. Check if scheduled_payment == 0 OR remarks indicate forbearance
        2. Look for ANY late markers (30, 60, 90, 120+) in payment history
        3. If both conditions met, fire violation
        """
        violations = []

        # Get payment history and remarks from bureau_data if provided
        payment_history = []
        remarks = ""
        scheduled_payment = account.scheduled_payment

        if bureau_data:
            if hasattr(bureau_data, 'payment_history'):
                payment_history = bureau_data.payment_history or []
            if hasattr(bureau_data, 'remarks'):
                remarks = bureau_data.remarks or ""
            if hasattr(bureau_data, 'scheduled_payment') and bureau_data.scheduled_payment is not None:
                scheduled_payment = bureau_data.scheduled_payment

        # Skip if no payment history to analyze
        if not payment_history:
            return violations

        remarks_lower = remarks.lower() if remarks else ""

        # CONDITION 1: Check for forbearance/deferment indicators in remarks
        forbearance_indicators = [
            'forbearance', 'deferment', 'deferred', 'defer',
            'hardship', 'hardship program', 'payment plan',
            'covid', 'cares act', 'pandemic', 'disaster',
            'natural disaster', 'payment pause', 'payment holiday',
            'temporary hardship', 'modification', 'loan mod',
            'in school', 'in-school', 'grace period',
            'military', 'servicememember', 'scra',
            'unemployment deferment', 'economic hardship'
        ]
        has_forbearance_remarks = any(ind in remarks_lower for ind in forbearance_indicators)

        # CONDITION 2: Check if scheduled payment is $0 (no payment required)
        has_zero_payment_due = scheduled_payment is not None and scheduled_payment == 0

        # If neither condition is met, no phantom late payment possible
        if not has_forbearance_remarks and not has_zero_payment_due:
            return violations

        # CONDITION 3: Check for late markers in payment history
        # Format: [{"month": "Jan", "year": 2024, "status": "OK"}, ...]
        late_markers = []
        late_statuses = ['30', '60', '90', '120', '150', '180', 'CO', 'FC', 'RP']

        for entry in payment_history:
            if isinstance(entry, dict):
                status = str(entry.get('status', '')).upper().strip()
                # Check if status indicates late payment (30, 60, 90, etc.)
                if any(late in status for late in late_statuses):
                    month = entry.get('month', '')
                    year = entry.get('year', '')
                    late_markers.append({
                        'month': month,
                        'year': year,
                        'status': status
                    })

        # If no late markers found, no violation
        if not late_markers:
            return violations

        # BUILD VIOLATION
        # Determine the triggering condition for clearer messaging
        trigger_reason = []
        if has_zero_payment_due:
            trigger_reason.append(f"Scheduled Payment: $0 (no payment required)")
        if has_forbearance_remarks:
            # Extract the specific forbearance indicator found
            found_indicators = [ind for ind in forbearance_indicators if ind in remarks_lower]
            if found_indicators:
                trigger_reason.append(f"Account remarks indicate: {found_indicators[0]}")

        trigger_text = " and ".join(trigger_reason)

        # Format late markers for description
        late_marker_text = ", ".join([
            f"{m['month']} {m['year']}: {m['status']}" for m in late_markers[:5]
        ])
        if len(late_markers) > 5:
            late_marker_text += f" (and {len(late_markers) - 5} more)"

        violations.append(Violation(
            violation_type=ViolationType.PHANTOM_LATE_PAYMENT,
            severity=Severity.HIGH,
            account_id=account.account_id,
            creditor_name=account.creditor_name,
            account_number_masked=account.account_number_masked,
            furnisher_type=account.furnisher_type,
            bureau=bureau,
            description=(
                f"This account shows late payment markers ({late_marker_text}) during a period "
                f"when no payment was due. {trigger_text}. Under FCRA §623(a)(1), a furnisher "
                f"cannot report a consumer as delinquent for failing to make a payment that "
                f"was not required. These phantom late markers must be removed."
            ),
            expected_value="No late markers during $0 due or forbearance periods",
            actual_value=f"{len(late_markers)} late marker(s) found: {late_marker_text}",
            fcra_section="623(a)(1)",
            metro2_field="25",  # Payment History Profile
            evidence={
                "scheduled_payment": scheduled_payment,
                "has_forbearance": has_forbearance_remarks,
                "forbearance_remarks": remarks[:200] if remarks else None,
                "late_markers": late_markers,
                "late_marker_count": len(late_markers),
                "trigger_reason": trigger_reason
            }
        ))

        return violations

    @staticmethod
    def check_illogical_delinquency_progression(
        account: Account,
        bureau: Bureau,
        bureau_data: Optional[BureauAccountData] = None
    ) -> List[Violation]:
        """
        Check for illogical delinquency progression in payment history.

        Metro 2 delinquency is a PROGRESSION, not a static state:
        - If you miss a payment, you are 30 days late
        - If you miss the next, you MUST become 60 days late
        - You cannot skip levels (0→60 is impossible without first being 30)

        Two violation types:
        1. DELINQUENCY_JUMP (HIGH): History jumps levels (0→60, 1→90) - physically impossible
        2. STAGNANT_DELINQUENCY (MEDIUM): Same late level for consecutive months (30→30)
           - "Rolling lates" are rare; if balance didn't decrease, it's logically impossible

        Legal Basis: FCRA §623(a)(1) - accurate reporting requirement
        Metro 2: Field 18 (Payment History Profile) must reflect logical progression
        """
        violations = []

        # Get payment history from bureau_data
        payment_history = []
        if bureau_data and hasattr(bureau_data, 'payment_history'):
            payment_history = bureau_data.payment_history or []

        if not payment_history or len(payment_history) < 2:
            return violations  # Need at least 2 months to check progression

        # Define delinquency severity levels
        # 0 = Current, 1 = 30 days, 2 = 60 days, etc.
        severity_map = {
            '0': 0, 'C': 0, 'OK': 0, 'CURRENT': 0, '': 0, '-': 0,
            '1': 1, '30': 1,
            '2': 2, '60': 2,
            '3': 3, '90': 3,
            '4': 4, '120': 4,
            '5': 5, '150': 5,
            '6': 6, '180': 6,
        }

        # Human-readable level names
        level_names = {
            0: 'Current',
            1: '30 Days Late',
            2: '60 Days Late',
            3: '90 Days Late',
            4: '120 Days Late',
            5: '150 Days Late',
            6: '180+ Days Late'
        }

        # Track found issues for combining into single violations
        jumps_found = []
        stagnant_runs = []

        # Process history (newest to oldest typically, but we compare consecutive pairs)
        # Payment history format: [{"month": "Jan", "year": 2024, "status": "OK"}, ...]
        for i in range(len(payment_history) - 1):
            current_entry = payment_history[i]
            prior_entry = payment_history[i + 1]  # Older month

            if not isinstance(current_entry, dict) or not isinstance(prior_entry, dict):
                continue

            current_status = str(current_entry.get('status', '')).upper().strip()
            prior_status = str(prior_entry.get('status', '')).upper().strip()

            # Skip non-standard statuses (CO, FC, RP handled differently)
            if current_status not in severity_map or prior_status not in severity_map:
                continue

            curr_level = severity_map[current_status]
            prev_level = severity_map[prior_status]

            # Get month/year for reporting
            curr_month = current_entry.get('month', '')
            curr_year = current_entry.get('year', '')
            prev_month = prior_entry.get('month', '')
            prev_year = prior_entry.get('year', '')

            # ================================================================
            # SCENARIO 1: "Skipped Rung" - Jumping levels (HIGH SEVERITY)
            # You can only increase by 1 level per month maximum
            # Example: 0→60 (skipped 30), 30→90 (skipped 60)
            # ================================================================
            if curr_level > (prev_level + 1):
                jumps_found.append({
                    'from_level': prev_level,
                    'to_level': curr_level,
                    'from_name': level_names.get(prev_level, f'Level {prev_level}'),
                    'to_name': level_names.get(curr_level, f'Level {curr_level}'),
                    'from_period': f"{prev_month} {prev_year}",
                    'to_period': f"{curr_month} {curr_year}"
                })

            # ================================================================
            # SCENARIO 2: "Stagnant Late" - Same delinquency level (MEDIUM SEVERITY)
            # Reporting same late status for consecutive months is suspicious
            # Example: 30→30, 60→60 (staying at same late level)
            # ================================================================
            elif curr_level > 0 and curr_level == prev_level:
                stagnant_runs.append({
                    'level': curr_level,
                    'level_name': level_names.get(curr_level, f'Level {curr_level}'),
                    'from_period': f"{prev_month} {prev_year}",
                    'to_period': f"{curr_month} {curr_year}"
                })

        # Create DELINQUENCY_JUMP violation if any jumps found
        if jumps_found:
            jump_details = "; ".join([
                f"{j['from_name']} ({j['from_period']}) → {j['to_name']} ({j['to_period']})"
                for j in jumps_found[:3]  # Limit to first 3 for readability
            ])
            if len(jumps_found) > 3:
                jump_details += f" (and {len(jumps_found) - 3} more)"

            violations.append(Violation(
                violation_type=ViolationType.DELINQUENCY_JUMP,
                severity=Severity.HIGH,
                account_id=account.account_id,
                creditor_name=account.creditor_name,
                account_number_masked=account.account_number_masked,
                furnisher_type=account.furnisher_type,
                bureau=bureau,
                description=(
                    f"Payment History shows impossible delinquency progression: {jump_details}. "
                    f"A consumer cannot jump from Current to 60 days late without first being 30 days late. "
                    f"Metro 2 requires reporting the full delinquency ladder. This gap indicates "
                    f"corrupted or incomplete data."
                ),
                expected_value="Sequential delinquency progression (Current→30→60→90)",
                actual_value=f"Jumped levels: {jump_details}",
                fcra_section="623(a)(1)",
                metro2_field="18",  # Payment History Profile
                evidence={
                    "jumps": jumps_found,
                    "jump_count": len(jumps_found)
                }
            ))

        # Create STAGNANT_DELINQUENCY violation if stagnant runs found
        # Only flag if there are multiple consecutive same-level entries (indicates pattern)
        if len(stagnant_runs) >= 2:
            stagnant_details = "; ".join([
                f"{s['level_name']} for {s['from_period']} → {s['to_period']}"
                for s in stagnant_runs[:3]
            ])
            if len(stagnant_runs) > 3:
                stagnant_details += f" (and {len(stagnant_runs) - 3} more)"

            violations.append(Violation(
                violation_type=ViolationType.STAGNANT_DELINQUENCY,
                severity=Severity.MEDIUM,
                account_id=account.account_id,
                creditor_name=account.creditor_name,
                account_number_masked=account.account_number_masked,
                furnisher_type=account.furnisher_type,
                bureau=bureau,
                description=(
                    f"Payment History shows duplicate delinquency levels for consecutive months: {stagnant_details}. "
                    f"To maintain the same 'days late' status, the consumer must make a payment equal to "
                    f"exactly one month's installment. If no payment was made (balance unchanged), "
                    f"the status should have progressed to the next delinquency level. "
                    f"This pattern suggests a data mapping error."
                ),
                expected_value="Delinquency should progress (30→60→90) if no payment made",
                actual_value=f"Stagnant at same level: {stagnant_details}",
                fcra_section="623(a)(1)",
                metro2_field="18",
                evidence={
                    "stagnant_runs": stagnant_runs,
                    "run_count": len(stagnant_runs)
                }
            ))

        return violations

    @staticmethod
    def _infer_dofd_from_payment_history(account: Account) -> Optional[date]:
        """
        Correctly infers DOFD by finding the start of the *current* contiguous delinquency.

        CRITICAL: Under FCRA and Metro 2® standards, DOFD is defined as the
        "commencement of the delinquency which IMMEDIATELY PRECEDED the collection
        activity or charge-off."

        This means if a consumer was late in 2018, caught up (cured) in 2019,
        and defaulted again in 2021, the DOFD is 2021 - NOT 2018.

        Algorithm: "Reverse Contiguous Chain"
        1. Flatten all payment history entries across bureaus
        2. Sort by date (newest to oldest)
        3. Walk backwards from today until hitting an "OK/Current" status
        4. Return the oldest date in the unbroken delinquency chain

        This prevents false "time-barred" findings that could expose users to lawsuits.
        """
        from datetime import date

        # Month name to number mapping
        month_to_num = {
            'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
            'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
        }

        # 1. Flatten and collect all payment history entries across bureaus
        all_entries = []

        for bureau_data in account.bureaus.values():
            payment_history = getattr(bureau_data, 'payment_history', None)
            if not payment_history:
                continue

            for entry in payment_history:
                if not isinstance(entry, dict):
                    continue

                month_str = str(entry.get("month", "")).lower()[:3]
                year = entry.get("year")

                if month_str in month_to_num and year:
                    try:
                        # Create date object (1st of month)
                        d = date(int(year), month_to_num[month_str], 1)
                        status = str(entry.get("status", "")).upper()
                        all_entries.append({"date": d, "status": status})
                    except (ValueError, TypeError):
                        continue

        if not all_entries:
            return None

        # 2. Sort: Newest First (reverse chronological)
        all_entries.sort(key=lambda x: x["date"], reverse=True)

        # 3. Walk backwards to find the "Break Point" (cured status)
        # OK statuses that indicate the account was current/cured
        ok_statuses = {"OK", "C", "0", "", "-", "CURRENT"}

        potential_dofd = None

        for entry in all_entries:
            status = entry["status"]

            # ND = No Data - treat as neutral/skip
            is_delinquent = status not in ok_statuses and status != "ND"

            if is_delinquent:
                # This date is part of the delinquency chain; track it
                potential_dofd = entry["date"]
            else:
                # HIT A CURED POINT!
                # If we already found a delinquency chain, stop here.
                # The potential_dofd we hold is the start of the CURRENT chain.
                if potential_dofd:
                    break

        return potential_dofd

    @staticmethod
    def get_sol_category(account: Account) -> str:
        """
        Infers the Legal Debt Category (Open, Written, Promissory)
        based on Metro 2 fields and text descriptions.

        Categories:
        - "open": Open-ended revolving credit (credit cards, lines of credit)
        - "written": Written contracts (auto loans, personal loans, retail installment)
        - "promissory": Promissory notes (mortgages, student loans)

        Returns the most appropriate category for SOL lookup.
        """
        # Get relevant fields for inference
        account_type = (account.account_type or "").lower()
        creditor_name = (account.creditor_name or "").lower()
        original_creditor = (account.original_creditor or "").lower()

        # Get account_type_detail from bureau data if available
        account_type_detail = ""
        for bureau_data in account.bureaus.values():
            if hasattr(bureau_data, 'account_type_detail') and bureau_data.account_type_detail:
                account_type_detail = bureau_data.account_type_detail.lower()
                break

        combined_text = f"{account_type} {account_type_detail} {creditor_name} {original_creditor}"

        # PROMISSORY NOTE indicators (mortgages, student loans, formal notes)
        promissory_indicators = [
            'mortgage', 'home loan', 'real estate', 'heloc', 'home equity',
            'student loan', 'education loan', 'student', 'sallie mae', 'navient',
            'great lakes', 'nelnet', 'fedloan', 'mohela', 'dept of education',
            'promissory', 'secured note'
        ]
        if any(ind in combined_text for ind in promissory_indicators):
            return "promissory"

        # OPEN ACCOUNT indicators (revolving credit, credit cards)
        open_indicators = [
            'credit card', 'revolving', 'charge card', 'line of credit',
            'loc', 'visa', 'mastercard', 'amex', 'american express',
            'discover', 'capital one', 'chase', 'citi', 'bank of america',
            'wells fargo', 'synchrony', 'store card', 'retail card'
        ]
        if any(ind in combined_text for ind in open_indicators):
            return "open"

        # WRITTEN CONTRACT indicators (installment loans, auto, personal)
        written_indicators = [
            'auto', 'car loan', 'vehicle', 'installment', 'personal loan',
            'consumer loan', 'signature loan', 'unsecured loan', 'medical',
            'dental', 'hospital', 'utility', 'phone', 'wireless', 'cable',
            'internet', 'collection', 'charged off'
        ]
        if any(ind in combined_text for ind in written_indicators):
            return "written"

        # Default: Collections and unknown accounts default to "written"
        # (most conservative - typically shortest SOL)
        if account.furnisher_type == FurnisherType.COLLECTOR:
            return "written"

        # Fallback default
        return "written"

    @staticmethod
    def is_sol_tolled_by_bankruptcy(account: Account) -> bool:
        """
        Checks if SOL is paused (tolled) due to active Bankruptcy.

        During bankruptcy proceedings, the SOL clock is typically paused.
        This prevents false "time-barred" findings on accounts in BK.

        Metro 2 Bankruptcy Compliance Condition Codes:
        - D/A = Petition Filed
        - E/H = Discharged
        - L/I = Dismissed
        - Q/Z = BK Flag
        """
        # Check compliance condition codes across bureaus
        bk_codes = {'A', 'D', 'E', 'H', 'I', 'L', 'Q', 'Z'}

        for bureau_data in account.bureaus.values():
            # Check compliance_condition_code if available
            ccc = getattr(bureau_data, 'compliance_condition_code', None)
            if ccc and str(ccc).upper() in bk_codes:
                return True

            # Check remarks for bankruptcy language
            remarks = (getattr(bureau_data, 'remarks', '') or '').lower()
            if any(term in remarks for term in ['bankruptcy', 'chapter 7', 'chapter 13', 'chapter 11', 'bk filed']):
                return True

        return False

    @staticmethod
    def check_governing_law_opportunity(account: Account) -> Dict[str, Any]:
        """
        Checks if the debt might be governed by a state with a different SOL.

        Many national banks are headquartered in states with different SOL:
        - Delaware (DE): 3 years for most debt
        - South Dakota (SD): 6 years
        - Virginia (VA): 5 years written, 3 years oral
        - Utah (UT): 6 years

        If cardholder agreement has Choice of Law clause, the bank's
        home state SOL may apply instead of the consumer's state.
        """
        # Bank → Headquarters State mapping
        bank_matrix = {
            "chase": "DE",
            "jp morgan": "DE",
            "jpmorgan": "DE",
            "discover": "DE",
            "barclays": "DE",
            "american express": "UT",
            "amex": "UT",
            "capital one": "VA",
            "citi": "SD",
            "citibank": "SD",
            "wells fargo": "SD",
            "synchrony": "UT",
            "goldman sachs": "UT",  # Apple Card
        }

        # Check creditor name and original creditor
        creditor = (account.creditor_name or '').lower()
        oc = (account.original_creditor or '').lower()
        combined = f"{creditor} {oc}"

        for bank, state in bank_matrix.items():
            if bank in combined:
                return {
                    "detected": True,
                    "bank": bank.title(),
                    "governing_state": state,
                    "strategy": f"Check Cardholder Agreement for {state} Choice of Law clause. "
                               f"If applicable, {state} SOL may govern instead of your state."
                }

        return {"detected": False}

    @staticmethod
    def check_zombie_revival_risk(
        account: Account,
        anchor_date: date,
        sol_years: int
    ) -> Optional[Dict[str, str]]:
        """
        Detects if a recent payment might have accidentally 'revived' a Time-Barred Debt.

        In many states, making ANY payment on a time-barred debt can restart
        the SOL clock (called "zombie debt revival"). This is a trap many
        consumers fall into.

        Returns a warning if payment was made AFTER the SOL would have expired.
        """
        # Check for date_last_payment across bureaus
        date_last_payment = None

        for bureau_data in account.bureaus.values():
            dlp = getattr(bureau_data, 'date_last_payment', None)
            if dlp:
                # Take the most recent payment date
                if date_last_payment is None or dlp > date_last_payment:
                    date_last_payment = dlp

        if not date_last_payment or not anchor_date:
            return None

        # Calculate: How old was the debt when the last payment was made?
        years_at_payment = (date_last_payment - anchor_date).days / 365.25

        # If payment was made AFTER the SOL had already expired...
        if years_at_payment > sol_years:
            return {
                "risk": "HIGH",
                "warning": (
                    f"ZOMBIE DEBT RISK: A payment was recorded on {date_last_payment.strftime('%B %d, %Y')}, "
                    f"which was {years_at_payment:.1f} years after the anchor date. "
                    f"The {sol_years}-year SOL had already expired. Depending on your state laws, "
                    f"this payment may have RESTARTED the limitation period."
                ),
                "payment_date": str(date_last_payment),
                "years_at_payment": round(years_at_payment, 2)
            }

        return None

    @staticmethod
    def check_time_barred_debt(account: Account, user_state: str = "NY") -> List[Violation]:
        """
        MASTER FUNCTION: Detects Time-Barred Debt Risks.

        Integrates:
        - Bankruptcy tolling checks (SOL paused during BK)
        - Zombie debt revival risk detection
        - Choice of Law / Governing Law opportunities
        - Re-aging trap detection for debt buyers

        FUTURE PROOFING: 'user_state' defaults to "NY" (Source of Truth for now),
        but can be passed dynamically later from the User Profile page.

        A debt is "time-barred" when the Statute of Limitations (SOL) has expired,
        meaning the creditor loses the legal right to sue for collection.

        IMPORTANT: Under FDCPA, threatening legal action on time-barred debt is
        a per se violation. This makes time-barred debt a CRITICAL finding.

        Legal Basis:
        - FDCPA §1692e(2)(A) - False representation of legal status of debt
        - FDCPA §1692e(5) - Threat to take action that cannot legally be taken
        - State-specific SOL statutes
        """
        from .sol_data import SOL_DATA

        violations = []
        today = date.today()

        # Only check collection accounts and chargeoffs
        if account.furnisher_type not in [FurnisherType.COLLECTOR, FurnisherType.OC_CHARGEOFF]:
            return violations

        if account.account_status not in [AccountStatus.COLLECTION, AccountStatus.CHARGEOFF, AccountStatus.DEROGATORY]:
            return violations

        # =====================================================================
        # BANKRUPTCY CHECK (The Stop Sign)
        # If active bankruptcy, SOL is tolled (paused). Do not flag as Time-Barred.
        # =====================================================================
        if SingleBureauRules.is_sol_tolled_by_bankruptcy(account):
            return violations

        # =====================================================================
        # ANCHOR DATE SELECTION
        # For Debt Buyers: MUST use DOFD (they can't re-age with their Date Opened)
        # For OCs: Can use DOFD or Date Opened as fallback
        # =====================================================================
        anchor_date = None
        anchor_source = ""
        is_debt_buyer = account.furnisher_type == FurnisherType.COLLECTOR

        if account.date_of_first_delinquency:
            anchor_date = account.date_of_first_delinquency
            anchor_source = "Date of First Delinquency"
        else:
            # Try to infer DOFD from payment history (across all bureaus)
            inferred_dofd = SingleBureauRules._infer_dofd_from_payment_history(account)
            if inferred_dofd:
                anchor_date = inferred_dofd
                anchor_source = "Date of First Delinquency (inferred from payment history)"
            elif not is_debt_buyer and account.date_opened:
                # OC can use date_opened as fallback, but debt buyers CANNOT
                anchor_date = account.date_opened
                anchor_source = "Date Opened (OC fallback)"
            elif account.date_last_activity:
                anchor_date = account.date_last_activity
                anchor_source = "Date Last Activity"
            elif account.date_last_payment:
                anchor_date = account.date_last_payment
                anchor_source = "Date Last Payment"
            else:
                # No date to calculate from - can't determine SOL
                return violations

        # =====================================================================
        # STATE & CATEGORY LOOKUP
        # =====================================================================
        state_upper = user_state.upper()
        if state_upper not in SOL_DATA["states"]:
            logger.warning(f"Unknown state '{user_state}' for SOL lookup, defaulting to NY")
            state_upper = "NY"

        state_sol = SOL_DATA["states"][state_upper]
        state_name = state_sol["state_name"]

        # Determine debt category using inference
        debt_category = SingleBureauRules.get_sol_category(account)

        # Get SOL years for this category
        sol_info = state_sol["statutes"].get(debt_category, state_sol["statutes"]["written"])
        sol_years = sol_info["years"]
        sol_citation = sol_info["citation"]

        # =====================================================================
        # CALCULATE AGE & CHECK IF TIME-BARRED
        # =====================================================================
        years_since_anchor = (today - anchor_date).days / 365.25

        if years_since_anchor >= sol_years:
            # SOL has expired - this is time-barred debt
            months_past_sol = int((years_since_anchor - sol_years) * 12)

            # -----------------------------------------------------------------
            # Check for legal threat indicators in remarks
            # -----------------------------------------------------------------
            has_legal_threats = False
            threat_text = ""
            for bureau_data in account.bureaus.values():
                remarks = (getattr(bureau_data, 'remarks', '') or "").lower()
                legal_threat_indicators = [
                    'legal action', 'lawsuit', 'court', 'judgment', 'attorney',
                    'litigation', 'sue', 'summons', 'complaint', 'garnish'
                ]
                if any(ind in remarks for ind in legal_threat_indicators):
                    has_legal_threats = True
                    threat_text = bureau_data.remarks[:100] if bureau_data.remarks else ""
                    break

            # -----------------------------------------------------------------
            # Check for Governing Law Opportunity (Bank Loophole)
            # -----------------------------------------------------------------
            gov_law = SingleBureauRules.check_governing_law_opportunity(account)

            # -----------------------------------------------------------------
            # Check for Zombie Revival Risk
            # -----------------------------------------------------------------
            zombie_risk = SingleBureauRules.check_zombie_revival_risk(account, anchor_date, sol_years)

            # -----------------------------------------------------------------
            # Severity: CRITICAL if legal threats detected (FDCPA violation)
            # HIGH if just time-barred without threats
            # -----------------------------------------------------------------
            severity = Severity.CRITICAL if has_legal_threats else Severity.HIGH

            # -----------------------------------------------------------------
            # Build description
            # -----------------------------------------------------------------
            description = (
                f"This {debt_category} debt has exceeded the {state_name} Statute of Limitations. "
                f"The {anchor_source} of {anchor_date.strftime('%B %d, %Y')} was {years_since_anchor:.1f} years ago. "
                f"Under {sol_citation}, the SOL for {debt_category} accounts is {sol_years} years. "
                f"This debt became time-barred {months_past_sol} months ago. "
            )

            if has_legal_threats:
                description += (
                    f"\n\nWARNING: Account remarks indicate potential legal threats ('{threat_text}'). "
                    f"Under FDCPA §1692e(5), threatening to sue on time-barred debt is a per se violation."
                )
            else:
                description += (
                    f"While the debt may still be reported, the collector has lost the legal right to sue. "
                    f"Any threat of legal action on this debt would violate FDCPA §1692e(5)."
                )

            # Append Governing Law strategy if detected
            if gov_law.get("detected"):
                description += (
                    f"\n\nSTRATEGY: Original Creditor is {gov_law['bank']}. "
                    f"{gov_law['strategy']}"
                )

            # Append Zombie Risk warning if detected
            if zombie_risk:
                description += f"\n\n{zombie_risk['warning']}"

            violations.append(Violation(
                violation_type=ViolationType.TIME_BARRED_DEBT_RISK,
                severity=severity,
                account_id=account.account_id,
                creditor_name=account.creditor_name,
                account_number_masked=account.account_number_masked,
                furnisher_type=account.furnisher_type,
                bureau=account.bureau,  # Use account's primary bureau
                description=description,
                expected_value=f"SOL expired: Cannot sue after {sol_years} years under {sol_citation}",
                actual_value=f"{years_since_anchor:.1f} years since {anchor_source}",
                fcra_section="FDCPA 1692e(5)",
                metro2_field="N/A",
                evidence={
                    "anchor_date": str(anchor_date),
                    "anchor_source": anchor_source,
                    "years_since_anchor": round(years_since_anchor, 2),
                    "sol_years": sol_years,
                    "sol_citation": sol_citation,
                    "debt_category": debt_category,
                    "state": state_upper,
                    "state_name": state_name,
                    "months_past_sol": months_past_sol,
                    "has_legal_threats": has_legal_threats,
                    "threat_text": threat_text if has_legal_threats else None,
                    "is_debt_buyer": is_debt_buyer,
                    "governing_law": gov_law if gov_law.get("detected") else None,
                    "zombie_risk": zombie_risk
                }
            ))

        return violations

    @staticmethod
    def check_deceased_indicator(account: Account, bureau: Bureau) -> List[Violation]:
        """
        Detects erroneous Deceased Indicator on a tradeline.

        Metro 2 Field 37 (ECOA Code) value 'X' = Deceased
        Metro 2 Field 38 (Consumer Information Indicator) - 'X', 'Y', 'Z' for deceased statuses

        If a living consumer has a "Deceased" indicator on their credit report,
        their score effectively drops to 0 and no creditor will lend to them.
        This is a CRITICAL "Death on Credit" error.

        Detection approach (since ECOA/compliance fields aren't explicitly stored):
        1. Check bureau_code for 'X' or 'Deceased'
        2. Check remarks for 'deceased' keywords
        3. Check payment_status for deceased indicators
        4. Check raw_data for any deceased-related fields
        """
        violations = []
        bureau_data = account.get_bureau_data(bureau)

        if not bureau_data:
            return violations

        # Deceased indicator keywords
        deceased_keywords = ["deceased", "death", "died", "decedent"]

        # Check 1: Bureau code contains deceased indicator (ECOA Code X)
        bureau_code = (bureau_data.bureau_code or "").lower().strip()
        ecoa_deceased = bureau_code == "x" or "deceased" in bureau_code

        # Check 2: Remarks contain deceased language
        remarks = (bureau_data.remarks or "").lower()
        remarks_deceased = any(kw in remarks for kw in deceased_keywords)

        # Check 3: Payment status contains deceased indicator
        payment_status = (bureau_data.payment_status or "").lower()
        status_deceased = any(kw in payment_status for kw in deceased_keywords)

        # Check 4: Account status raw contains deceased
        account_status_raw = (bureau_data.account_status_raw or "").lower()
        status_raw_deceased = any(kw in account_status_raw for kw in deceased_keywords)

        # Check 5: Raw data fields (some parsers store ecoa_code or compliance codes here)
        raw_data = account.raw_data or {}
        raw_deceased = False
        ecoa_from_raw = str(raw_data.get("ecoa_code", "")).lower().strip()
        compliance_code = str(raw_data.get("compliance_condition_code", "")).lower().strip()
        consumer_info_indicator = str(raw_data.get("consumer_information_indicator", "")).lower().strip()

        if ecoa_from_raw == "x" or "deceased" in ecoa_from_raw:
            raw_deceased = True
        if compliance_code in ["x", "y", "z"] or "deceased" in compliance_code:
            raw_deceased = True
        if consumer_info_indicator in ["x", "y", "z"] or "deceased" in consumer_info_indicator:
            raw_deceased = True

        # If any indicator found, create violation
        if ecoa_deceased or remarks_deceased or status_deceased or status_raw_deceased or raw_deceased:
            # Build evidence of what triggered detection
            triggers = []
            if ecoa_deceased:
                triggers.append(f"Bureau Code: '{bureau_data.bureau_code}'")
            if remarks_deceased:
                triggers.append(f"Remarks: '{bureau_data.remarks}'")
            if status_deceased:
                triggers.append(f"Payment Status: '{bureau_data.payment_status}'")
            if status_raw_deceased:
                triggers.append(f"Account Status: '{bureau_data.account_status_raw}'")
            if raw_deceased:
                triggers.append(f"Raw Data Codes: ecoa={ecoa_from_raw}, compliance={compliance_code}")

            violations.append(Violation(
                violation_type=ViolationType.DECEASED_INDICATOR_ERROR,
                severity=Severity.CRITICAL,  # CRITICAL - score drops to 0
                account_id=account.account_id,
                creditor_name=account.creditor_name,
                account_number_masked=account.account_number_masked,
                furnisher_type=account.furnisher_type,
                bureau=bureau,
                description=(
                    f"CRITICAL: This account shows a 'Deceased' indicator, but the consumer is alive. "
                    f"Under Metro 2 standards, ECOA Code 'X' or Consumer Information Indicator codes "
                    f"'X', 'Y', 'Z' mark a consumer as deceased. This error causes the credit score "
                    f"to effectively drop to 0, preventing ALL credit access. "
                    f"Detected via: {'; '.join(triggers)}. "
                    f"This is a 'Death on Credit' error requiring immediate correction under "
                    f"FCRA §611 (disputes) and §623(a)(2) (duty to correct)."
                ),
                expected_value="No Deceased Indicator (Consumer is alive)",
                actual_value=f"Deceased indicator detected via: {triggers[0]}",
                fcra_section="611(a), 623(a)(2)",
                metro2_field="Field 37 (ECOA Code) / Field 38 (Consumer Information Indicator)",
                evidence={
                    "triggers": triggers,
                    "bureau_code": bureau_data.bureau_code,
                    "remarks": bureau_data.remarks,
                    "payment_status": bureau_data.payment_status,
                    "account_status_raw": bureau_data.account_status_raw,
                    "ecoa_from_raw": ecoa_from_raw if ecoa_from_raw else None,
                    "compliance_code": compliance_code if compliance_code else None,
                    "consumer_info_indicator": consumer_info_indicator if consumer_info_indicator else None
                }
            ))

        return violations

    @staticmethod
    def check_child_identity_theft(account: Account, bureau: Bureau, user_dob: Optional[date]) -> List[Violation]:
        """
        Detects accounts opened before the consumer turned 18 (Age of Majority).
        Minors generally lack the legal capacity to enter into binding contracts.

        CRITICAL EXCEPTION: Authorized Users (ECOA Code 3) are allowed to be minors.
        Parents often add children as AUs to help build credit history - this is LEGAL.
        This rule targets 'Individual' or 'Joint' liability assigned to a minor.

        Args:
            account: The Account to check
            bureau: The bureau being checked
            user_dob: The consumer's date of birth from their profile

        Returns:
            List of CHILD_IDENTITY_THEFT violations (0 or 1)
        """
        violations = []

        # 1. Safety Checks: Need valid dates to proceed
        if not user_dob or not account.date_opened:
            return violations

        # 2. Convert string dates to objects if needed (Data hygiene)
        acct_date = account.date_opened
        if isinstance(acct_date, str):
            try:
                acct_date = datetime.strptime(acct_date, "%Y-%m-%d").date()
            except ValueError:
                return violations

        # 3. Check Liability (The Safety Valve)
        # Parents often add kids as Authorized Users (ECOA Code 3). This is LEGAL.
        # We only flag if the child is liable (Individual/Joint).
        # Check bureau_data.bureau_code which holds the ECOA/responsibility code
        bureau_data = account.get_bureau_data(bureau)
        if bureau_data:
            bureau_code = (bureau_data.bureau_code or "").lower()
            # ECOA Code 3 = Authorized User, also check for keywords
            if "3" in str(bureau_data.bureau_code) or "authorized" in bureau_code:
                return violations

        # Also check raw_data for ecoa_code if available
        raw_ecoa = account.raw_data.get("ecoa_code", "") if account.raw_data else ""
        if str(raw_ecoa) == "3" or "authorized" in str(raw_ecoa).lower():
            return violations

        # 4. Calculate Age at Opening
        # Logic: (Open Date - DOB) / 365.25 (accounting for leap years)
        age_at_opening = (acct_date - user_dob).days / 365.25

        # 5. The Trigger (Under 18)
        if age_at_opening < 18:
            # Calculate when the consumer turned 18
            try:
                date_turned_18 = user_dob.replace(year=user_dob.year + 18)
            except ValueError:
                # Feb 29 edge case
                date_turned_18 = user_dob.replace(month=2, day=28, year=user_dob.year + 18)

            violations.append(Violation(
                violation_type=ViolationType.CHILD_IDENTITY_THEFT,
                severity=Severity.CRITICAL,
                account_id=account.account_id,
                creditor_name=account.creditor_name,
                account_number_masked=account.account_number_masked,
                furnisher_type=account.furnisher_type,
                bureau=bureau,
                description=(
                    f"POSSIBLE CHILD IDENTITY THEFT: This account was opened on {acct_date}, "
                    f"when the consumer was approximately {int(age_at_opening)} years old. "
                    f"Minors generally lack the legal capacity to enter into binding contracts. "
                    f"Since this consumer is listed as liable (not an Authorized User), this is a strong "
                    f"indicator of identity theft or synthetic fraud. The consumer turned 18 on "
                    f"{date_turned_18}, which is AFTER this account was opened."
                ),
                expected_value=f"Account opened after age 18 (on or after {date_turned_18})",
                actual_value=f"Opened at age {int(age_at_opening)} on {acct_date}",
                fcra_section="Contract Law / Capacity to Contract",
                metro2_field="Field 10 (Date Opened) / Field 5 (ECOA Code)",
                evidence={
                    "dob": str(user_dob),
                    "date_opened": str(acct_date),
                    "age_at_opening": round(age_at_opening, 1),
                    "date_turned_18": str(date_turned_18)
                }
            ))

        return violations


# =============================================================================
# FURNISHER RULES
# =============================================================================

class FurnisherRules:
    """
    Rules that depend on furnisher type classification.
    Uses the SSOT FurnisherType set during parsing.
    """

    @staticmethod
    def check_closed_oc_reporting_balance(account: Account, bureau: Bureau) -> List[Violation]:
        """
        Check if a closed original creditor (non-chargeoff) is reporting a balance.

        If OC closed the account (not chargeoff) and sold/transferred it,
        they should NOT report a balance - the collector now owns the debt.
        """
        violations = []

        # Only applies to closed OC non-chargeoff accounts
        if account.furnisher_type != FurnisherType.OC_NON_CHARGEOFF:
            return violations

        if account.account_status != AccountStatus.CLOSED:
            return violations

        if account.balance is not None and account.balance > 0:
            violations.append(Violation(
                violation_type=ViolationType.CLOSED_OC_REPORTING_BALANCE,
                severity=Severity.HIGH,
                account_id=account.account_id,
                creditor_name=account.creditor_name,
                account_number_masked=account.account_number_masked,
                furnisher_type=account.furnisher_type,
                bureau=bureau,
                description=(
                    f"This closed original creditor account is reporting a balance of "
                    f"${account.balance:,.2f}. If the debt was sold or transferred, the OC "
                    f"should report $0 balance. Only the current debt holder may report a balance."
                ),
                expected_value="$0.00 (closed account)",
                actual_value=f"${account.balance:,.2f}",
                fcra_section="611(a)(5)(A)",
                metro2_field="17A",
                evidence={
                    "furnisher_type": account.furnisher_type.value,
                    "status": account.account_status.value,
                    "balance": account.balance
                }
            ))

        return violations

    @staticmethod
    def check_collector_missing_original_creditor(account: Account, bureau: Bureau) -> List[Violation]:
        """
        Check if a collection account identifies the Original Creditor (K1 Segment).

        Without this, the 'Chain of Title' is broken, making the debt unverifiable.
        Under Metro 2 standards, the K1 Segment (Original Creditor Name) is mandatory
        for Account Type 48 (Collection) or 0C (Debt Purchaser) to establish lineage.
        """
        violations = []

        # Target: Collections & Debt Buyers ONLY
        if account.furnisher_type != FurnisherType.COLLECTOR:
            return violations

        # The Check: Is the Original Creditor Name missing?
        # Clean the string to ensure it's not just whitespace
        oc_name = (account.original_creditor or "").strip()

        if not oc_name:
            violations.append(Violation(
                violation_type=ViolationType.MISSING_ORIGINAL_CREDITOR,
                # HIGH severity: Chain of Title violation is a deletion candidate
                severity=Severity.HIGH,
                account_id=account.account_id,
                creditor_name=account.creditor_name,
                account_number_masked=account.account_number_masked,
                furnisher_type=account.furnisher_type,
                bureau=bureau,
                # Chain of Title description for legal weight
                description=(
                    "Collection account fails to identify the Original Creditor. "
                    "For Account Type 48 (Collection) or 0C (Debt Purchaser), the K1 Segment "
                    "(Original Creditor Name) is mandatory to establish the 'Chain of Title'. "
                    "Without this link, the debt ownership is legally unverifiable."
                ),
                expected_value="Original Creditor Name (K1 Segment) populated",
                actual_value="Missing/Blank",
                # Specific FCRA citation for furnisher accuracy duty
                fcra_section="623(a)(7)",
                # Metro 2 field reference
                metro2_field="K1 Segment",
                evidence={"furnisher_type": account.furnisher_type.value}
            ))

        return violations

    @staticmethod
    def check_chargeoff_missing_dofd(account: Account, bureau: Bureau) -> List[Violation]:
        """
        Check if a charge-off account is missing DOFD.

        Charge-offs MUST have DOFD for proper 7-year calculation.
        """
        violations = []

        if account.furnisher_type == FurnisherType.OC_CHARGEOFF:
            if account.date_of_first_delinquency is None:
                violations.append(Violation(
                    violation_type=ViolationType.CHARGEOFF_MISSING_DOFD,
                    severity=Severity.HIGH,
                    account_id=account.account_id,
                    creditor_name=account.creditor_name,
                    account_number_masked=account.account_number_masked,
                    furnisher_type=account.furnisher_type,
                    bureau=bureau,
                    description=(
                        f"This charge-off account is missing the Date of First Delinquency. "
                        f"DOFD is mandatory for charge-offs to determine the 7-year reporting period."
                    ),
                    expected_value="Valid DOFD date",
                    actual_value="Not Reported",
                    fcra_section="605(c)(1)",
                    metro2_field="25",
                    evidence={"furnisher_type": account.furnisher_type.value}
                ))

        return violations

    @staticmethod
    def check_closed_oc_reporting_past_due(account: Account, bureau: Bureau) -> List[Violation]:
        """
        Check if a closed OC non-charge-off is reporting past due amount.

        Closed OC accounts should report $0 past due.
        """
        violations = []

        if account.furnisher_type != FurnisherType.OC_NON_CHARGEOFF:
            return violations

        if account.account_status != AccountStatus.CLOSED:
            return violations

        if account.past_due_amount is not None and account.past_due_amount > 0:
            violations.append(Violation(
                violation_type=ViolationType.CLOSED_OC_REPORTING_PAST_DUE,
                severity=Severity.HIGH,
                account_id=account.account_id,
                creditor_name=account.creditor_name,
                account_number_masked=account.account_number_masked,
                furnisher_type=account.furnisher_type,
                bureau=bureau,
                description=(
                    f"This closed original creditor account is reporting a past due amount of "
                    f"${account.past_due_amount:,.2f}. Closed OC accounts should report $0 past due."
                ),
                expected_value="$0.00 (closed account)",
                actual_value=f"${account.past_due_amount:,.2f}",
                fcra_section="611(a)(5)(A)",
                metro2_field="17B",
                evidence={
                    "furnisher_type": account.furnisher_type.value,
                    "status": account.account_status.value,
                    "past_due": account.past_due_amount
                }
            ))

        return violations

    @staticmethod
    def check_paid_collection_contradiction(
        account: Account,
        bureau: Bureau,
        bureau_data: Optional[BureauAccountData] = None
    ) -> List[Violation]:
        """
        Check for contradictions between 'Paid' status and Balance/Past Due amounts.

        This is a "State Consistency" rule - two mutually exclusive states cannot exist:
        - State A: "The Debt is Settled/Paid" (Status = Paid)
        - State B: "Money is Still Owed" (Balance > $0)

        SCENARIO 1: Status says "Paid" but balance > $0 or past_due > $0
        - Clear contradiction: if paid, balance must be $0

        SCENARIO 2: Balance = $0 but Status doesn't say "Paid" (collection accounts only)
        - If a collection has $0 balance, it should be marked "Paid Collection"
        - EXCEPTION: Sold/Transferred accounts have $0 balance but aren't "Paid"

        Legal Basis: FCRA §623(a)(1) requires accurate reporting.
        Metro 2: Balance field must match account status.
        """
        violations = []

        # Get remarks from bureau_data if available
        remarks = ""
        if bureau_data and hasattr(bureau_data, 'remarks'):
            remarks = bureau_data.remarks or ""

        # Normalize for comparison
        status_lower = (account.payment_status or "").lower()
        remarks_lower = remarks.lower()

        # Check for "paid" or "settled" indicators
        paid_indicators = ['paid', 'settled', 'satisfied', 'paid in full', 'paid collection']
        is_marked_paid = any(ind in status_lower for ind in paid_indicators)

        # Check for sold/transferred indicators (to avoid false positives in Scenario 2)
        sold_indicators = ['sold', 'transferred', 'purchased by', 'assigned to']
        is_sold = any(ind in status_lower for ind in sold_indicators) or \
                  any(ind in remarks_lower for ind in sold_indicators)

        # Identify if this is a collection account
        account_type_lower = (account.account_type or "").lower()
        creditor_lower = (account.creditor_name or "").lower()
        is_collection = (
            account.furnisher_type == FurnisherType.COLLECTOR or
            account.account_status == AccountStatus.COLLECTION or
            'collection' in status_lower or
            'collection' in account_type_lower or
            'collection' in creditor_lower
        )

        # Get balance and past_due values
        balance = account.balance if account.balance is not None else 0
        past_due = account.past_due_amount if account.past_due_amount is not None else 0

        # ================================================================
        # SCENARIO 1: Status says "Paid" but balance > $0 or past_due > $0
        # ================================================================
        if is_marked_paid:
            has_balance = balance > 0
            has_past_due = past_due > 0

            if has_balance or has_past_due:
                # Build description based on what's wrong
                issues = []
                if has_balance:
                    issues.append(f"Balance: ${balance:,.2f}")
                if has_past_due:
                    issues.append(f"Past Due: ${past_due:,.2f}")

                violations.append(Violation(
                    violation_type=ViolationType.PAID_STATUS_WITH_BALANCE,
                    severity=Severity.HIGH,
                    account_id=account.account_id,
                    creditor_name=account.creditor_name,
                    account_number_masked=account.account_number_masked,
                    furnisher_type=account.furnisher_type,
                    bureau=bureau,
                    description=(
                        f"This account is marked as \"{account.payment_status}\" but still reports "
                        f"{' and '.join(issues)}. A paid account must reflect $0.00 owed. "
                        f"This is an internal contradiction - the status and balance fields are mutually exclusive."
                    ),
                    expected_value="Balance: $0.00, Past Due: $0.00 (for paid account)",
                    actual_value=f"Balance: ${balance:,.2f}, Past Due: ${past_due:,.2f}, Status: {account.payment_status}",
                    fcra_section="623(a)(1)",
                    metro2_field="17A/10",
                    evidence={
                        "payment_status": account.payment_status,
                        "balance": balance,
                        "past_due": past_due,
                        "is_collection": is_collection
                    }
                ))

        # ================================================================
        # SCENARIO 2: Balance = $0 on collection but Status not "Paid"
        # ================================================================
        # Only check collections - open credit cards can have $0 balance and be "Current"
        elif is_collection and balance == 0 and past_due == 0:
            # Skip if sold/transferred (explains $0 balance without "Paid" status)
            if not is_sold and not is_marked_paid:
                violations.append(Violation(
                    violation_type=ViolationType.ZERO_BALANCE_NOT_PAID,
                    severity=Severity.MEDIUM,
                    account_id=account.account_id,
                    creditor_name=account.creditor_name,
                    account_number_masked=account.account_number_masked,
                    furnisher_type=account.furnisher_type,
                    bureau=bureau,
                    description=(
                        f"This collection account reports a $0.00 balance but Payment Status is "
                        f"\"{account.payment_status}\". If the debt has been satisfied (balance = $0), "
                        f"the status should be updated to \"Paid Collection\" to accurately reflect "
                        f"the account state."
                    ),
                    expected_value="Status: Paid Collection (for $0 balance)",
                    actual_value=f"Status: {account.payment_status}, Balance: $0.00",
                    fcra_section="623(a)(2)",
                    metro2_field="17A",
                    evidence={
                        "payment_status": account.payment_status,
                        "balance": balance,
                        "past_due": past_due,
                        "is_sold": is_sold
                    }
                ))

        return violations


# =============================================================================
# TEMPORAL RULES
# =============================================================================

class TemporalRules:
    """
    Rules that check time-based violations.
    """

    @staticmethod
    def _has_delinquent_payment_history(account: Account) -> bool:
        """
        Check if account has ANY delinquent entries in payment history.
        Returns False if all payments are OK/Current (positive account).
        Returns True if there's any 30/60/90/120/CO/etc marker.
        """
        # Get payment history from the primary bureau's data
        payment_history = []
        if account.bureau in account.bureaus:
            bureau_data = account.bureaus[account.bureau]
            payment_history = bureau_data.payment_history if bureau_data.payment_history else []

        if not payment_history:
            return False  # No history = can't confirm delinquency

        # OK/Current statuses - these are NOT delinquent
        ok_statuses = {"OK", "ok", "Ok", "C", "c", "Current", "current", "", "-", None}

        for entry in payment_history:
            status = entry.get("status", "")
            if status not in ok_statuses:
                # Found a delinquent marker (30, 60, 90, 120, CO, etc.)
                return True

        return False  # All OK = positive account

    @staticmethod
    def check_obsolete_account(account: Account, bureau: Bureau) -> List[Violation]:
        """
        Check if account has exceeded 7-year reporting limit.

        FCRA §605(a) limits reporting to 7 years from DOFD.
        IMPORTANT: Only applies to ADVERSE information!
        - Accounts with all-OK payment history are POSITIVE and NOT subject to 7-year rule
        - Closed/Paid accounts with good history HELP credit scores
        """
        violations = []
        today = date.today()

        # CRITICAL CHECK: If payment history is all "OK", this is a POSITIVE account
        # FCRA 605(a) does NOT apply to positive information - it can stay forever
        if not TemporalRules._has_delinquent_payment_history(account):
            # Check payment status as backup - payment_status is a string, not an enum
            positive_statuses = ["current", "paid", "ok", "as agreed", None, ""]
            ps_lower = account.payment_status.lower() if account.payment_status else None
            if ps_lower in positive_statuses or account.payment_status is None:
                return violations  # Positive account - do NOT flag as obsolete

        # Derogatory statuses that are subject to FCRA 605(a) 7-year limit
        # NOTE: CLOSED is NOT derogatory - a closed account with good history is POSITIVE
        # Only actual adverse statuses should trigger 7-year rule
        derogatory_statuses = [
            AccountStatus.CHARGEOFF, AccountStatus.COLLECTION,
            AccountStatus.DEROGATORY
        ]

        # First try: Use DOFD if available
        if account.date_of_first_delinquency:
            if account.account_status in [AccountStatus.CHARGEOFF, AccountStatus.COLLECTION, AccountStatus.DEROGATORY]:
                dofd = account.date_of_first_delinquency
                obsolete_date = _add_years(dofd, 7)

                if obsolete_date < today:
                    # Calculate days/months past the 7-year limit
                    days_past_limit = (today - obsolete_date).days
                    months_past_limit = days_past_limit // 30

                    # Calculate TOTAL time since DOFD
                    total_days_since_dofd = (today - dofd).days
                    total_years_since_dofd = round(total_days_since_dofd / 365, 1)

                    violations.append(Violation(
                        violation_type=ViolationType.OBSOLETE_ACCOUNT,
                        severity=Severity.HIGH,
                        account_id=account.account_id,
                        creditor_name=account.creditor_name,
                        account_number_masked=account.account_number_masked,
                        furnisher_type=account.furnisher_type,
                        bureau=bureau,
                        description=(
                            f"This account has a Date of First Delinquency (DOFD) of {dofd.strftime('%B %d, %Y')} "
                            f"({total_days_since_dofd:,} days ago / {total_years_since_dofd} years). Under FCRA Section 605(a), "
                            f"adverse information must be deleted 7 years after the DOFD. The reporting period expired on "
                            f"{obsolete_date.strftime('%B %d, %Y')} ({months_past_limit} months ago). This account must be deleted immediately."
                        ),
                        expected_value=f"Deletion required by {obsolete_date.strftime('%B %d, %Y')} (7 years after DOFD)",
                        actual_value=f"Still reporting {total_years_since_dofd} years after DOFD",
                        fcra_section="605(a)",
                        metro2_field="25",
                        evidence={
                            "dofd": str(dofd),
                            "obsolete_date": str(obsolete_date),
                            "days_past": days_past_limit,
                            "months_past": months_past_limit,
                            "total_days_since_dofd": total_days_since_dofd,
                            "years_since_dofd": total_years_since_dofd
                        }
                    ))
                    return violations  # Don't double-count

        # Fallback: Use date_opened for closed accounts without DOFD
        # This catches accounts >7 years old that may have negative info
        # IMPORTANT: FCRA 605(a) only applies to ADVERSE information!
        # Positive closed accounts (paid, current, no delinquencies) are NOT subject to 7-year rule
        if account.date_opened and not account.date_of_first_delinquency:
            # Check if account has ACTUAL derogatory indicators
            # Do NOT flag accounts just because balance == 0 (that's often a good thing!)
            is_potentially_obsolete = (
                account.account_status in derogatory_statuses
                # Only consider closed accounts if they have negative comments/indicators
            )

            if is_potentially_obsolete:
                date_opened = account.date_opened
                obsolete_date = _add_years(date_opened, 7)

                if obsolete_date < today:
                    # Calculate days/months past the 7-year limit
                    days_past_limit = (today - obsolete_date).days
                    months_past_limit = days_past_limit // 30

                    # Calculate TOTAL age of account (from date_opened to today)
                    total_days_old = (today - date_opened).days
                    total_years_old = round(total_days_old / 365, 1)

                    # Only flag if significantly past (at least 6 months past 7 years)
                    if days_past_limit >= 180:  # 6+ months past the 7-year mark
                        violations.append(Violation(
                            violation_type=ViolationType.OBSOLETE_ACCOUNT,
                            severity=Severity.HIGH,
                            account_id=account.account_id,
                            creditor_name=account.creditor_name,
                            account_number_masked=account.account_number_masked,
                            furnisher_type=account.furnisher_type,
                            bureau=bureau,
                            description=(
                                f"This account was opened on {date_opened.strftime('%B %d, %Y')} "
                                f"({total_days_old:,} days ago / {total_years_old} years). Under FCRA Section 605(a), "
                                f"adverse information cannot be reported beyond 7 years. This account has exceeded "
                                f"the statutory reporting limit by {months_past_limit} months and must be deleted immediately."
                            ),
                            expected_value=f"Deletion required by {obsolete_date.strftime('%B %d, %Y')} (7 years after account opened)",
                            actual_value=f"Still reporting {total_years_old} years after account opened",
                            fcra_section="605(a)",
                            metro2_field=None,
                            evidence={
                                "date_opened": str(date_opened),
                                "obsolete_date": str(obsolete_date),
                                "days_past_7_years": days_past_limit,
                                "months_past_7_years": months_past_limit,
                                "total_days_old": total_days_old,
                                "years_old": total_years_old,
                                "missing_dofd": True
                            }
                        ))

        return violations

    @staticmethod
    def check_stale_reporting(account: Account, bureau: Bureau) -> List[Violation]:
        """
        Check if account hasn't been updated in over 90 days.

        Furnishers should update accounts regularly.
        Note: Skips accounts that are likely obsolete (>7 years old) - those
        should be flagged for deletion instead, not just stale reporting.
        """
        violations = []

        if not account.date_reported:
            return violations

        today = date.today()
        days_since_update = (today - account.date_reported).days

        # Skip if account is likely obsolete (>7 years old)
        # Obsolete accounts need DELETION, not just stale reporting
        if account.date_opened:
            account_age_days = (today - account.date_opened).days
            if account_age_days > 2555 + 180:  # 7 years + 6 months buffer
                # This account should be caught by check_obsolete_account instead
                return violations

        if account.date_of_first_delinquency:
            dofd_age_days = (today - account.date_of_first_delinquency).days
            if dofd_age_days > 2555:  # 7 years from DOFD
                # This account should be caught by check_obsolete_account instead
                return violations

        if days_since_update > 90:
            violations.append(Violation(
                violation_type=ViolationType.STALE_REPORTING,
                severity=Severity.LOW,
                account_id=account.account_id,
                creditor_name=account.creditor_name,
                account_number_masked=account.account_number_masked,
                furnisher_type=account.furnisher_type,
                bureau=bureau,
                description=(
                    f"This account was last reported on {account.date_reported.strftime('%B %d, %Y')} "
                    f"({days_since_update} days ago). Under Metro 2 standards, furnishers must update "
                    f"accounts regularly. Failure to do so renders the data unverifiable under "
                    f"FCRA § 611(a)(5)(A)."
                ),
                expected_value="Recent update within 90 days",
                actual_value=f"{days_since_update} days since last update",
                fcra_section="611(a)",
                metro2_field="8",
                evidence={
                    "date_reported": str(account.date_reported),
                    "days_since_update": days_since_update
                }
            ))

        return violations

    @staticmethod
    def check_impossible_timeline(account: Account, bureau: Bureau) -> List[Violation]:
        """
        Check for impossible date sequences.

        E.g., date closed before date opened, last payment before account opened, etc.
        """
        violations = []

        # Date closed before date opened
        if account.date_opened and account.date_closed:
            if account.date_closed < account.date_opened:
                violations.append(Violation(
                    violation_type=ViolationType.IMPOSSIBLE_TIMELINE,
                    severity=Severity.HIGH,
                    account_id=account.account_id,
                    creditor_name=account.creditor_name,
                    account_number_masked=account.account_number_masked,
                    furnisher_type=account.furnisher_type,
                    bureau=bureau,
                    description=(
                        f"Date Closed ({account.date_closed}) is before Date Opened "
                        f"({account.date_opened}). An account cannot close before it opens."
                    ),
                    expected_value=f"Date Closed ≥ {account.date_opened}",
                    actual_value=str(account.date_closed),
                    fcra_section="611(a)",
                    metro2_field=None,
                    evidence={
                        "date_opened": str(account.date_opened),
                        "date_closed": str(account.date_closed)
                    }
                ))

        return violations


# =============================================================================
# INQUIRY RULES (FCRA §604 - Permissible Purposes)
# =============================================================================

class InquiryRules:
    """
    Rules that analyze credit inquiries for permissible purpose violations.

    Under FCRA §604, a credit report can only be pulled for specific permissible purposes:
    - Credit transaction (applying for credit)
    - Employment purposes (with consumer consent)
    - Insurance underwriting
    - Account review by existing creditor
    - Court order / subpoena
    - Legitimate business need

    Hard vs Soft Inquiries:
    - HARD: Counts against credit score, requires consumer-initiated action
    - SOFT: Does not affect score, can be done without consumer initiation
    """

    # Industries that should typically do SOFT pulls (not hard)
    SOFT_PULL_INDUSTRIES = {
        "insurance", "assurance", "mutual", "underwriter",
        "staffing", "screening", "background", "employ", "hiring", "recruit",
        "rental", "leasing", "property management", "apartment",
        "utility", "utilities", "electric", "gas", "water", "power",
        "telecom", "wireless", "phone", "mobile", "cellular"
    }

    # Collection agency indicators (for fishing expedition detection)
    COLLECTOR_KEYWORDS = {
        "recovery", "collection", "receivables", "asset", "portfolio",
        "financial", "credit management", "debt", "mdg", "lvnv", "midland",
        "cavalry", "portfolio recovery", "convergent", "enhanced recovery"
    }

    @staticmethod
    def _normalize_creditor_name(name: str) -> str:
        """
        Normalizes creditor aliases to a single root entity.

        Solves the "Alias Problem" where the same lender appears with different
        names across bureaus (e.g., 'COAF', 'CAP ONE AF', 'CAPITAL ONE AUTO FIN'
        are all Capital One Auto Finance).

        Example: 'COAF' -> 'CAPITAL ONE', 'JPMCB' -> 'JPMORGAN CHASE'
        """
        if not name:
            return ""

        n = name.upper().replace(".", "").replace(",", "").strip()

        # 1. Capital One Variations (auto, bank, etc.)
        if any(x in n for x in ["CAP ONE", "COAF", "CAPITAL ONE", "CAPITAL 1", "CAPONE"]):
            return "CAPITAL ONE"

        # 2. JPMorgan Chase Variations
        if any(x in n for x in ["JPM", "CHASE", "JP MORGAN", "JPMCB"]):
            return "JPMORGAN CHASE"

        # 3. Synchrony Variations (store cards)
        if any(x in n for x in ["SYNCB", "SYNCHRONY", "AMAZON/SYNC"]):
            return "SYNCHRONY BANK"

        # 4. Ally Financial / Americredit (same company)
        if any(x in n for x in ["ALLY", "AMERICREDIT", "AMCR"]):
            return "ALLY FINANCIAL"

        # 5. Department of Education / Student Loan Servicers
        if any(x in n for x in ["DEPT OF ED", "DEPT ED", "NELNET", "NAVIENT", "MOHELA", "FEDLOAN", "GREAT LAKES", "EDFINANCIAL"]):
            return "DEPT OF EDUCATION"

        # 6. Discover Variations
        if any(x in n for x in ["DISCOVER", "DFS", "DISCOVERBANK"]):
            return "DISCOVER"

        # 7. Bank of America
        if any(x in n for x in ["BANK OF AMERICA", "BOA", "BOFA", "B OF A"]):
            return "BANK OF AMERICA"

        # 8. Wells Fargo
        if any(x in n for x in ["WELLS FARGO", "WELLSFARGO", "WF"]):
            return "WELLS FARGO"

        # 9. Citibank
        if any(x in n for x in ["CITI", "CITIBANK", "CITICORP"]):
            return "CITIBANK"

        # 10. American Express
        if any(x in n for x in ["AMEX", "AMERICAN EXPRESS", "AMERICANEXP"]):
            return "AMERICAN EXPRESS"

        # 11. Toyota Financial
        if any(x in n for x in ["TOYOTA", "TFS", "LEXUS"]):
            return "TOYOTA FINANCIAL"

        # 12. Honda Financial
        if any(x in n for x in ["HONDA", "AHFC", "ACURA"]):
            return "HONDA FINANCIAL"

        # 13. Ford Credit
        if any(x in n for x in ["FORD", "FMC", "LINCOLN"]):
            return "FORD CREDIT"

        # 14. GM Financial
        if any(x in n for x in ["GM FINANCIAL", "GMAC", "GENERAL MOTORS"]):
            return "GM FINANCIAL"

        # 15. Santander
        if any(x in n for x in ["SANTANDER", "SCUSA"]):
            return "SANTANDER"

        # Default: clean up common suffixes
        for suffix in [" BANK", " CREDIT", " FINANCIAL", " CORP", " INC", " LLC", " NA", " FSB", " AUTO"]:
            n = n.replace(suffix, "")

        return n.strip()

    @staticmethod
    def check_inquiry_misclassification(inquiries: List[Inquiry]) -> List[Violation]:
        """
        Detect hard inquiries from industries that typically should do soft pulls.

        Insurance, employment screening, and utilities generally should NOT
        do hard pulls unless specifically applying for credit.

        Args:
            inquiries: List of parsed credit inquiries

        Returns:
            List of INQUIRY_MISCLASSIFICATION violations
        """
        violations = []

        for inq in inquiries:
            # Only check hard inquiries
            if inq.inquiry_type != "hard":
                continue

            creditor_lower = (inq.creditor_name or "").lower()
            business_lower = (inq.type_of_business or "").lower()

            # Check against soft-pull industries
            matched_industry = None
            for keyword in InquiryRules.SOFT_PULL_INDUSTRIES:
                if keyword in creditor_lower or keyword in business_lower:
                    matched_industry = keyword
                    break

            if matched_industry:
                # Determine the industry type for the description
                if matched_industry in {"insurance", "assurance", "mutual", "underwriter"}:
                    industry_type = "Insurance"
                    expected_purpose = "insurance underwriting (soft inquiry)"
                elif matched_industry in {"staffing", "screening", "background", "employ", "hiring", "recruit"}:
                    industry_type = "Employment/Background Check"
                    expected_purpose = "employment verification (soft inquiry)"
                elif matched_industry in {"rental", "leasing", "property management", "apartment"}:
                    industry_type = "Rental/Leasing"
                    expected_purpose = "rental application (soft or hard with consent)"
                elif matched_industry in {"utility", "utilities", "electric", "gas", "water", "power"}:
                    industry_type = "Utilities"
                    expected_purpose = "service application (soft inquiry)"
                elif matched_industry in {"telecom", "wireless", "phone", "mobile", "cellular"}:
                    industry_type = "Telecommunications"
                    expected_purpose = "service application (soft inquiry)"
                else:
                    industry_type = "Non-Credit"
                    expected_purpose = "soft inquiry"

                violations.append(Violation(
                    violation_type=ViolationType.INQUIRY_MISCLASSIFICATION,
                    severity=Severity.MEDIUM,
                    account_id=inq.inquiry_id,
                    creditor_name=inq.creditor_name,
                    bureau=inq.bureau,
                    description=(
                        f"Hard Inquiry by {industry_type} company '{inq.creditor_name}' "
                        f"(Date: {inq.inquiry_date}). Industry standards for {industry_type.lower()} "
                        f"typically require Soft Inquiries unless a specific application for credit "
                        f"was submitted. This may be a coding error or lack of permissible purpose "
                        f"under FCRA §604(a)(3)."
                    ),
                    expected_value=f"Soft Inquiry ({expected_purpose})",
                    actual_value="Hard Inquiry",
                    fcra_section="604(a)(3)",
                    metro2_field="Inquiry Section",
                    evidence={
                        "inquiry_date": str(inq.inquiry_date) if inq.inquiry_date else None,
                        "type_of_business": inq.type_of_business,
                        "matched_industry": matched_industry,
                        "industry_type": industry_type,
                        "bureau": inq.bureau.value if inq.bureau else None
                    }
                ))

        return violations

    @staticmethod
    def check_collection_fishing_inquiry(
        inquiries: List[Inquiry],
        accounts: List[Account]
    ) -> List[Violation]:
        """
        Detect collection agencies that pulled credit but have no tradeline.

        This is known as a "fishing expedition" - collectors pulling credit
        to look for assets without owning a debt from the consumer.

        Under FCRA §604(a)(3)(A), a permissible purpose requires a legitimate
        business transaction initiated by the consumer.

        Args:
            inquiries: List of parsed credit inquiries
            accounts: List of parsed accounts (to check for matching tradelines)

        Returns:
            List of COLLECTION_FISHING_INQUIRY violations
        """
        violations = []

        # Build list of active collector names from tradelines
        active_collectors = set()
        for account in accounts:
            if account.furnisher_type == FurnisherType.COLLECTOR:
                active_collectors.add((account.creditor_name or "").lower().strip())

        for inq in inquiries:
            # Only check hard inquiries
            if inq.inquiry_type != "hard":
                continue

            creditor_lower = (inq.creditor_name or "").lower()

            # Check if this looks like a collection agency
            is_collector = any(
                keyword in creditor_lower
                for keyword in InquiryRules.COLLECTOR_KEYWORDS
            )

            if not is_collector:
                continue

            # Check if this collector is reporting a tradeline
            has_tradeline = any(
                creditor_lower in ac or ac in creditor_lower
                for ac in active_collectors
            )

            if not has_tradeline:
                violations.append(Violation(
                    violation_type=ViolationType.COLLECTION_FISHING_INQUIRY,
                    severity=Severity.HIGH,
                    account_id=inq.inquiry_id,
                    creditor_name=inq.creditor_name,
                    bureau=inq.bureau,
                    description=(
                        f"Collection Agency '{inq.creditor_name}' performed a Hard Inquiry "
                        f"(Date: {inq.inquiry_date}) but is NOT reporting any associated debt "
                        f"on this credit file. Without an active account, judgment, or legitimate "
                        f"business transaction, they may lack Permissible Purpose to access "
                        f"your consumer report. This appears to be a 'fishing expedition' for assets."
                    ),
                    expected_value="No Inquiry (or Soft Inquiry)",
                    actual_value="Hard Inquiry without tradeline",
                    fcra_section="604(a)(3)(A)",
                    metro2_field="Inquiry Section",
                    evidence={
                        "inquiry_date": str(inq.inquiry_date) if inq.inquiry_date else None,
                        "type_of_business": inq.type_of_business,
                        "has_matching_tradeline": False,
                        "bureau": inq.bureau.value if inq.bureau else None
                    }
                ))

        return violations

    @staticmethod
    def check_duplicate_inquiries(
        inquiries: List[Inquiry],
        window_days: int = 14
    ) -> List[Violation]:
        """
        Detect duplicate inquiries from the same creditor.

        Two types of duplicates:
        1. "Double Tap" - Same creditor, same bureau, same DAY (technical glitch)
        2. Rate-shopping window - Same creditor within 14 days (should be merged)

        Uses _normalize_creditor_name to handle alias variations like:
        - COAF, CAP ONE AF, CAPITAL ONE AUTO FIN -> CAPITAL ONE

        Args:
            inquiries: List of parsed credit inquiries
            window_days: Days within which duplicates are flagged (default 14)

        Returns:
            List of DUPLICATE_INQUIRY violations
        """
        violations = []

        # ========================================
        # PHASE 1: Same-Day "Double Tap" Detection
        # ========================================
        # Key = (Bureau, Normalized_Name, Date) -> catches true duplicates
        same_day_seen: Dict[tuple, Inquiry] = {}

        for inq in inquiries:
            if inq.inquiry_type != "hard":
                continue
            if not inq.creditor_name or not inq.inquiry_date:
                continue

            # Use robust normalizer for alias matching
            norm_name = InquiryRules._normalize_creditor_name(inq.creditor_name)
            bureau_val = inq.bureau.value if inq.bureau else "unknown"

            # Create signature: same bureau + same normalized name + same date
            sig = (bureau_val, norm_name, inq.inquiry_date)

            if sig in same_day_seen:
                prev_inq = same_day_seen[sig]
                violations.append(Violation(
                    violation_type=ViolationType.DUPLICATE_INQUIRY,
                    severity=Severity.MEDIUM,  # Higher severity for same-day
                    account_id=inq.inquiry_id,
                    creditor_name=inq.creditor_name,
                    bureau=inq.bureau,
                    description=(
                        f"DOUBLE TAP: '{inq.creditor_name}' pulled your {bureau_val} report "
                        f"multiple times on {inq.inquiry_date}. Even for rate shopping, a single "
                        f"lender should only access your file once per application per bureau. "
                        f"Multiple same-day pulls indicate a technical error or duplicate submission "
                        f"by the dealer/creditor."
                    ),
                    expected_value="Single Inquiry per Application per Bureau",
                    actual_value=f"Multiple Inquiries on {inq.inquiry_date}",
                    fcra_section="604(a)(3)",
                    metro2_field="Inquiry Section",
                    evidence={
                        "inquiry_date": str(inq.inquiry_date),
                        "normalized_creditor": norm_name,
                        "duplicate_type": "same_day_double_tap",
                        "bureau": bureau_val
                    }
                ))
            else:
                same_day_seen[sig] = inq

        # ========================================
        # PHASE 2: Within-Window Duplicate Detection
        # ========================================
        # Group by (Normalized_Name, Bureau) to find close-together pulls
        creditor_bureau_inquiries: Dict[tuple, List[Inquiry]] = {}

        for inq in inquiries:
            if inq.inquiry_type != "hard":
                continue
            if not inq.creditor_name or not inq.inquiry_date:
                continue

            norm_name = InquiryRules._normalize_creditor_name(inq.creditor_name)
            bureau_val = inq.bureau.value if inq.bureau else "unknown"
            key = (norm_name, bureau_val)

            if key not in creditor_bureau_inquiries:
                creditor_bureau_inquiries[key] = []
            creditor_bureau_inquiries[key].append(inq)

        seen_pairs = set()  # Avoid double-reporting

        for (norm_name, bureau_val), inq_list in creditor_bureau_inquiries.items():
            if len(inq_list) < 2:
                continue

            # Sort by date
            inq_list.sort(key=lambda x: x.inquiry_date)

            # Check for within-window duplicates (but not same-day, already caught)
            for i, inq1 in enumerate(inq_list):
                for inq2 in inq_list[i+1:]:
                    days_apart = (inq2.inquiry_date - inq1.inquiry_date).days

                    # Skip same-day (already caught in Phase 1)
                    if days_apart == 0:
                        continue

                    if days_apart <= window_days:
                        pair_key = f"{inq1.inquiry_id}-{inq2.inquiry_id}"
                        if pair_key in seen_pairs:
                            continue
                        seen_pairs.add(pair_key)

                        violations.append(Violation(
                            violation_type=ViolationType.DUPLICATE_INQUIRY,
                            severity=Severity.LOW,
                            account_id=inq2.inquiry_id,
                            creditor_name=inq2.creditor_name,
                            bureau=inq2.bureau,
                            description=(
                                f"Duplicate Hard Inquiry: '{inq2.creditor_name}' (normalized: {norm_name}) "
                                f"pulled {bureau_val} on {inq2.inquiry_date}, only {days_apart} days after "
                                f"a previous pull on {inq1.inquiry_date}. Under most credit scoring models, "
                                f"rate-shopping inquiries within 14-45 days should be merged into one."
                            ),
                            expected_value="Single inquiry (or merged for scoring)",
                            actual_value=f"2 inquiries {days_apart} days apart",
                            fcra_section="604(a)(3)",
                            metro2_field="Inquiry Section",
                            evidence={
                                "first_inquiry_date": str(inq1.inquiry_date),
                                "second_inquiry_date": str(inq2.inquiry_date),
                                "days_apart": days_apart,
                                "normalized_creditor": norm_name,
                                "duplicate_type": "within_window",
                                "bureau": bureau_val
                            }
                        ))

        return violations

    @staticmethod
    def audit_inquiries(
        inquiries: List[Inquiry],
        accounts: List[Account]
    ) -> List[Violation]:
        """
        Run all inquiry audits and return combined violations.

        Args:
            inquiries: List of parsed credit inquiries
            accounts: List of parsed accounts (for fishing expedition check)

        Returns:
            Combined list of all inquiry-related violations
        """
        violations = []

        # Check for soft-pull industries doing hard pulls
        violations.extend(InquiryRules.check_inquiry_misclassification(inquiries))

        # Check for collection fishing expeditions
        violations.extend(InquiryRules.check_collection_fishing_inquiry(inquiries, accounts))

        # Check for duplicate inquiries
        violations.extend(InquiryRules.check_duplicate_inquiries(inquiries))

        return violations


# =============================================================================
# IDENTITY INTEGRITY RULES
# =============================================================================

class IdentityRules:
    """
    Compares parsed Credit Report Header data against the User Profile (Source of Truth).
    Detects Mixed Files, Identity Theft indicators, and Formatting errors.

    This is the "optic nerve" connecting the Frontend profile to the Audit engine.
    """

    @staticmethod
    def check_identity_integrity(
        report: 'NormalizedReport',
        user_profile: Dict[str, Any]
    ) -> List[Violation]:
        """
        Run all identity integrity checks comparing report header vs user profile.

        Args:
            report: NormalizedReport with consumer/personal info
            user_profile: Dict with user's profile data (first_name, last_name, suffix,
                         ssn_last_4, state, street_address, etc.)

        Returns:
            List of identity-related violations
        """
        violations = []

        if not user_profile:
            return violations

        # Get consumer data from report
        consumer = report.consumer
        report_name = consumer.full_name if consumer else ""
        report_state = consumer.state if consumer else ""
        report_address = consumer.address if consumer else ""
        report_ssn = consumer.ssn_last4 if consumer else ""

        # Run all identity checks
        violations.extend(IdentityRules.check_suffix_mismatch(report_name, user_profile))
        violations.extend(IdentityRules.check_ssn_mismatch(report_ssn, user_profile))
        violations.extend(IdentityRules.check_state_mismatch(report_state, report_address, user_profile))
        violations.extend(IdentityRules.check_name_mismatch(report_name, user_profile))

        return violations

    @staticmethod
    def check_suffix_mismatch(report_name: str, user_profile: Dict[str, Any]) -> List[Violation]:
        """
        Check for Jr/Sr suffix conflicts - the classic "Mixed File" trap.

        If the user is "Junior" but the report shows "Senior", this is a CRITICAL
        indicator that the credit file has been merged with a relative (usually parent).
        """
        violations = []

        profile_suffix = (user_profile.get("suffix") or "").lower().replace(".", "").strip()
        report_name_lower = (report_name or "").lower()

        if not profile_suffix:
            return violations

        # Define conflict pairs - these suffixes CANNOT coexist
        conflicts = {
            "jr": ["sr", "senior", " ii", " iii", " iv", " v"],
            "junior": ["sr", "senior", " ii", " iii", " iv", " v"],
            "sr": ["jr", "junior", " ii", " iii", " iv"],
            "senior": ["jr", "junior", " ii", " iii", " iv"],
            "ii": ["jr", "junior", "sr", "senior", " iii", " iv", " v"],
            "iii": ["jr", "junior", "sr", "senior", " ii", " iv", " v"],
            "iv": ["jr", "junior", "sr", "senior", " ii", " iii", " v"],
            "v": ["jr", "junior", "sr", "senior", " ii", " iii", " iv"]
        }

        conflicting = conflicts.get(profile_suffix, [])

        for bad_suffix in conflicting:
            # Check if conflicting suffix appears in report name
            # Using word boundary check to avoid false positives
            if bad_suffix in report_name_lower:
                violations.append(Violation(
                    violation_type=ViolationType.IDENTITY_SUFFIX_MISMATCH,
                    severity=Severity.CRITICAL,
                    description=(
                        f"CRITICAL MIXED FILE INDICATOR: Your profile identifies you as "
                        f"'{profile_suffix.upper()}', but the Credit Report lists your name as "
                        f"'{report_name}' (containing '{bad_suffix.strip().upper()}'). "
                        f"It is factually impossible to be both. This strongly suggests your credit file "
                        f"has been merged with a relative who shares your name."
                    ),
                    expected_value=f"Name with suffix: {profile_suffix.upper()}",
                    actual_value=report_name,
                    fcra_section="607(b) Maximum Possible Accuracy",
                    metro2_field="Consumer Name",
                    evidence={
                        "profile_suffix": profile_suffix,
                        "report_name": report_name,
                        "conflicting_suffix_found": bad_suffix.strip()
                    }
                ))
                break  # One violation is enough

        # Also check if user has suffix but report doesn't show ANY suffix
        # This is a MEDIUM severity issue - missing suffix can lead to mixed file confusion
        if not violations and profile_suffix:
            suffix_indicators = [' jr', ' sr', 'junior', 'senior', ' ii', ' iii', ' iv', ' v']
            has_any_suffix = any(ind in report_name_lower for ind in suffix_indicators)

            if not has_any_suffix:
                violations.append(Violation(
                    violation_type=ViolationType.IDENTITY_SUFFIX_MISMATCH,
                    severity=Severity.MEDIUM,
                    description=(
                        f"MISSING SUFFIX: You are '{profile_suffix.upper()}', but the Credit Report shows "
                        f"'{report_name}' with NO suffix. This omission makes it impossible to distinguish "
                        f"your credit file from a relative with the same name. Without your suffix, accounts "
                        f"could be mixed between you and a parent, child, or other family member."
                    ),
                    expected_value=f"Name with suffix: {profile_suffix.upper()}",
                    actual_value=report_name,
                    fcra_section="607(b) Maximum Possible Accuracy",
                    metro2_field="Consumer Name",
                    evidence={
                        "profile_suffix": profile_suffix,
                        "report_name": report_name,
                        "issue": "suffix_missing"
                    }
                ))

        return violations

    @staticmethod
    def check_ssn_mismatch(report_ssn: str, user_profile: Dict[str, Any]) -> List[Violation]:
        """
        Check if SSN last 4 digits match between profile and report.

        This is the "fatal" error - if SSNs don't match, either:
        1. The report belongs to someone else (Mixed File)
        2. There's a potential identity theft situation
        3. The bureau has merged files incorrectly
        """
        violations = []

        profile_ssn = str(user_profile.get("ssn_last_4") or "").strip()
        report_ssn_clean = str(report_ssn or "")[-4:].strip()  # Extract last 4

        # Only check if both have valid 4-digit values
        if len(profile_ssn) != 4 or len(report_ssn_clean) != 4:
            return violations

        if profile_ssn != report_ssn_clean:
            violations.append(Violation(
                violation_type=ViolationType.IDENTITY_SSN_MISMATCH,
                severity=Severity.CRITICAL,
                description=(
                    f"SSN MISMATCH: Your profile SSN ends in '{profile_ssn}', but the Credit Report "
                    f"shows SSN ending in '{report_ssn_clean}'. This is a severe indicator of either "
                    f"a Mixed File (your report merged with someone else's) or potential Identity Theft. "
                    f"This file may not belong to you."
                ),
                expected_value=f"xxx-xx-{profile_ssn}",
                actual_value=f"xxx-xx-{report_ssn_clean}",
                fcra_section="607(b) Maximum Possible Accuracy",
                metro2_field="Social Security Number",
                evidence={
                    "profile_ssn_last4": profile_ssn,
                    "report_ssn_last4": report_ssn_clean
                }
            ))

        return violations

    @staticmethod
    def check_state_mismatch(
        report_state: str,
        report_address: str,
        user_profile: Dict[str, Any]
    ) -> List[Violation]:
        """
        Check if user's state of residence matches the report.

        This affects:
        1. Statute of Limitations calculations (wrong SOL applied)
        2. May indicate a Mixed File with a stranger from another state
        """
        violations = []

        profile_state = (user_profile.get("state") or "").upper().strip()
        report_state_clean = (report_state or "").upper().strip()
        report_address_upper = (report_address or "").upper()

        if not profile_state or len(profile_state) != 2:
            return violations

        # Check if profile state matches report state
        state_matches = False

        if report_state_clean and len(report_state_clean) == 2:
            state_matches = (profile_state == report_state_clean)
        else:
            # Fallback: check if state code appears in the address
            state_matches = (f" {profile_state} " in report_address_upper or
                           f", {profile_state} " in report_address_upper or
                           report_address_upper.endswith(f" {profile_state}"))

        if not state_matches and report_state_clean:
            violations.append(Violation(
                violation_type=ViolationType.IDENTITY_ADDRESS_MISMATCH,
                severity=Severity.MEDIUM,
                description=(
                    f"Residency Mismatch: Your profile shows you reside in '{profile_state}', "
                    f"but the Credit Report lists current address in '{report_state_clean}'. "
                    f"If you have not lived at this address, this may indicate a Mixed File "
                    f"with a stranger who has a similar name. Additionally, this affects which "
                    f"state's Statute of Limitations applies to your debts."
                ),
                expected_value=f"State: {profile_state}",
                actual_value=f"State: {report_state_clean}",
                fcra_section="607(b) Maximum Possible Accuracy",
                metro2_field="Address Indicator",
                evidence={
                    "profile_state": profile_state,
                    "report_state": report_state_clean,
                    "report_address": report_address
                }
            ))

        return violations

    @staticmethod
    def check_name_mismatch(report_name: str, user_profile: Dict[str, Any]) -> List[Violation]:
        """
        Check if the consumer's first/last name matches the profile.

        Catches cases like "Robert" vs "Richard" or completely different last names
        that might indicate a mixed file or identity issue.
        """
        violations = []

        profile_first = (user_profile.get("first_name") or "").lower().strip()
        profile_last = (user_profile.get("last_name") or "").lower().strip()
        report_name_lower = (report_name or "").lower()

        # Skip if profile doesn't have name
        if not profile_first and not profile_last:
            return violations

        # Check if first name appears in report name
        first_name_matches = True
        if profile_first and len(profile_first) >= 2:
            # Allow for common nickname variations
            first_name_matches = profile_first in report_name_lower

        # Check if last name appears in report name
        last_name_matches = True
        if profile_last and len(profile_last) >= 2:
            last_name_matches = profile_last in report_name_lower

        # Only flag if BOTH don't match (to avoid false positives)
        if profile_first and profile_last and not first_name_matches and not last_name_matches:
            violations.append(Violation(
                violation_type=ViolationType.IDENTITY_NAME_MISMATCH,
                severity=Severity.HIGH,
                description=(
                    f"Name Mismatch: Your profile shows '{profile_first.title()} {profile_last.title()}', "
                    f"but the Credit Report shows '{report_name}'. Neither your first nor last name "
                    f"appears in the report. This may indicate a Mixed File or that this report "
                    f"belongs to someone else entirely."
                ),
                expected_value=f"{profile_first.title()} {profile_last.title()}",
                actual_value=report_name,
                fcra_section="607(b) Maximum Possible Accuracy",
                metro2_field="Consumer Name",
                evidence={
                    "profile_first_name": profile_first,
                    "profile_last_name": profile_last,
                    "report_name": report_name
                }
            ))

        return violations

    @staticmethod
    def check_deceased_indicator_consumer(report: 'NormalizedReport') -> List[Violation]:
        """
        Check for Deceased Indicator at the consumer/report level.

        Metro 2 Field 38 (Consumer Information Indicator) can have values:
        - 'X' = Consumer deceased
        - 'Y' = Consumer's spouse deceased (may affect joint accounts)
        - 'Z' = Consumer and spouse deceased

        This check scans for ANY deceased indicators across the entire report
        and creates a single CRITICAL-level violation at the consumer level.
        This is different from the account-level check in SingleBureauRules,
        which flags individual tradelines.

        A living consumer with a deceased indicator has effectively a 0 credit score.
        """
        violations = []

        # Deceased indicator keywords
        deceased_keywords = ["deceased", "death", "died", "decedent"]

        # Track all sources where deceased was detected
        deceased_sources = []
        bureaus_affected = set()

        # Check across all accounts for deceased indicators
        for account in report.accounts:
            for bureau, bureau_data in account.bureaus.items():
                # Check bureau_code
                bureau_code = (bureau_data.bureau_code or "").lower().strip()
                if bureau_code == "x" or "deceased" in bureau_code:
                    deceased_sources.append(f"{account.creditor_name} ({bureau.value}): Bureau Code '{bureau_data.bureau_code}'")
                    bureaus_affected.add(bureau.value)

                # Check remarks
                remarks = (bureau_data.remarks or "").lower()
                if any(kw in remarks for kw in deceased_keywords):
                    deceased_sources.append(f"{account.creditor_name} ({bureau.value}): Remarks contain deceased indicator")
                    bureaus_affected.add(bureau.value)

                # Check payment_status
                payment_status = (bureau_data.payment_status or "").lower()
                if any(kw in payment_status for kw in deceased_keywords):
                    deceased_sources.append(f"{account.creditor_name} ({bureau.value}): Payment Status '{bureau_data.payment_status}'")
                    bureaus_affected.add(bureau.value)

            # Check raw_data for Consumer Information Indicator
            raw_data = account.raw_data or {}
            consumer_info = str(raw_data.get("consumer_information_indicator", "")).lower().strip()
            if consumer_info in ["x", "y", "z"] or "deceased" in consumer_info:
                deceased_sources.append(f"{account.creditor_name}: Consumer Information Indicator '{consumer_info}'")
                bureaus_affected.add(account.bureau.value if account.bureau else "unknown")

        # If deceased indicator found anywhere, create a single CRITICAL violation
        if deceased_sources:
            violations.append(Violation(
                violation_type=ViolationType.DECEASED_INDICATOR_ERROR,
                severity=Severity.CRITICAL,
                description=(
                    f"CRITICAL: Your credit report contains a 'Deceased' indicator even though you are alive. "
                    f"This is a 'Death on Credit' error that effectively reduces your credit score to 0 "
                    f"and prevents ALL credit access. Found in {len(deceased_sources)} location(s) across "
                    f"{len(bureaus_affected)} bureau(s). Under FCRA §611, you have the right to dispute "
                    f"this inaccurate information. Under §623(a)(2), furnishers have a duty to correct errors. "
                    f"This is among the most damaging errors possible on a credit report."
                ),
                expected_value="No Deceased Indicator (Consumer is alive)",
                actual_value=f"Deceased indicator found in {len(deceased_sources)} location(s)",
                fcra_section="611(a), 623(a)(2)",
                metro2_field="Field 38 (Consumer Information Indicator)",
                evidence={
                    "deceased_sources": deceased_sources[:10],  # Limit to first 10
                    "total_sources": len(deceased_sources),
                    "bureaus_affected": list(bureaus_affected),
                    "consumer_name": report.consumer.full_name if report.consumer else None
                }
            ))

        return violations


# =============================================================================
# PUBLIC RECORD RULES
# =============================================================================

class PublicRecordRules:
    """
    Audits the 'Public Records' section (Bankruptcies, Judgments, Liens).
    Enforces NCAP 2017 standards and FCRA obsolescence periods.
    """

    @staticmethod
    def check_ncap_compliance(record: PublicRecord) -> List[Violation]:
        """
        NCAP (National Consumer Assistance Plan) Compliance Check.

        In 2017, the three major bureaus agreed to remove Civil Judgments and Tax Liens
        from credit reports due to lack of PII (SSN/DOB) matching requirements.
        If a Civil Judgment or Tax Lien appears, it is a likely violation of this agreement.
        """
        violations = []

        record_type_lower = (record.record_type or "").lower()

        # NCAP banned "Civil Judgments" and "Tax Liens"
        # Exception: Divorce decrees or Child Support may still appear
        if "judgment" in record_type_lower or "lien" in record_type_lower:
            # Skip child support and divorce-related records
            if "child support" in record_type_lower or "divorce" in record_type_lower:
                return violations

            violations.append(Violation(
                violation_type=ViolationType.NCAP_VIOLATION_JUDGMENT,
                severity=Severity.HIGH,
                account_id=record.record_id,
                creditor_name=record.court_name or "Public Record",
                description=(
                    f"NCAP VIOLATION: A '{record.record_type}' is reported on your credit file. "
                    f"Under the National Consumer Assistance Plan (NCAP) of 2017, the three major "
                    f"credit bureaus agreed to remove Civil Judgments and Tax Liens due to high "
                    f"error rates in matching consumer PII (Name, Address, SSN, DOB). Public court "
                    f"records typically lack SSN/DOB data required for accurate matching. "
                    f"This record likely cannot be verified to the standard required by NCAP and FCRA §607(b)."
                ),
                expected_value="No Civil Judgments or Tax Liens Reporting (per NCAP)",
                actual_value=f"Public Record: {record.record_type}",
                fcra_section="NCAP Settlement / FCRA 607(b)",
                metro2_field="Public Record Segment",
                evidence={
                    "record_type": record.record_type,
                    "court_name": record.court_name,
                    "filed_date": str(record.filed_date) if record.filed_date else None,
                    "amount": record.amount
                }
            ))

        return violations

    @staticmethod
    def check_judgment_status(record: PublicRecord) -> List[Violation]:
        """
        Check for Satisfied/Paid Judgments still reporting a balance.

        If a Judgment is marked "Satisfied", "Paid", or "Released",
        the reported balance/amount must be $0.
        """
        violations = []

        record_type_lower = (record.record_type or "").lower()
        status_lower = (record.status or "").lower()
        balance = record.amount or 0.0

        # Only check judgments/liens
        if "judgment" not in record_type_lower and "lien" not in record_type_lower:
            return violations

        # Check for paid/satisfied status keywords
        paid_keywords = ["satisfied", "paid", "released", "discharged", "vacated", "dismissed"]
        is_satisfied = any(kw in status_lower for kw in paid_keywords)

        if is_satisfied and balance > 0:
            violations.append(Violation(
                violation_type=ViolationType.JUDGMENT_NOT_UPDATED,
                severity=Severity.HIGH,
                account_id=record.record_id,
                creditor_name=record.court_name or "Public Record",
                description=(
                    f"This {record.record_type} is marked '{record.status}' but still reports an "
                    f"outstanding amount of ${balance:,.2f}. Once a judgment or lien is satisfied, "
                    f"the reported balance must be updated to $0.00 immediately. Continuing to report "
                    f"a balance on a satisfied record is inaccurate and misleading to creditors."
                ),
                expected_value="Balance: $0.00 (Satisfied/Paid)",
                actual_value=f"Balance: ${balance:,.2f}",
                fcra_section="611(a) / 607(b)",
                metro2_field="Public Record Amount Field",
                evidence={
                    "record_type": record.record_type,
                    "status": record.status,
                    "amount": balance,
                    "court_name": record.court_name
                }
            ))

        return violations

    @staticmethod
    def check_bankruptcy_dates(record: PublicRecord) -> List[Violation]:
        """
        Check for Bankruptcy Date Errors and Obsolescence.

        Detects:
        1. Future filing dates (data integrity error)
        2. Obsolete bankruptcies (FCRA §605(a)(1)):
           - Chapter 7: 10 years from filing date
           - Chapter 13: 7 years from filing date (or discharge)
        """
        violations = []
        record_type_lower = (record.record_type or "").lower()

        # Only check Bankruptcies
        if "bankruptcy" not in record_type_lower:
            return violations

        filing_date = record.filed_date
        today = date.today()

        if not filing_date:
            return violations  # Cannot check without date

        # Convert string date if needed
        if isinstance(filing_date, str):
            try:
                filing_date = datetime.strptime(filing_date, "%Y-%m-%d").date()
            except ValueError:
                return violations

        # 1. LOGIC CHECK: Future Filing Date
        if filing_date > today:
            violations.append(Violation(
                violation_type=ViolationType.BANKRUPTCY_DATE_ERROR,
                severity=Severity.MEDIUM,
                account_id=record.record_id,
                creditor_name=record.court_name or "Public Record",
                description=(
                    f"Bankruptcy Filing Date is in the future ({filing_date}). "
                    f"This is a clear data integrity error - a bankruptcy cannot be filed "
                    f"in the future. This record contains inaccurate information."
                ),
                expected_value="Past or Present Date",
                actual_value=str(filing_date),
                fcra_section="611(a) - Accuracy",
                metro2_field="Public Record Date Field",
                evidence={
                    "record_type": record.record_type,
                    "filed_date": str(filing_date),
                    "court_name": record.court_name
                }
            ))
            return violations  # Don't check obsolescence if date is invalid

        # 2. OBSOLESCENCE CHECK (Time-Barred Reporting)
        # Chapter 7/11: 10 Years from Filing
        # Chapter 13: 7 Years from Filing (standard removal)

        age_years = (today - filing_date).days / 365.25

        # Determine chapter type and limit
        is_chapter_7_or_11 = "7" in record_type_lower or "11" in record_type_lower
        is_chapter_13 = "13" in record_type_lower

        # Default to 10 years if chapter unclear (most protective for consumer)
        if is_chapter_13:
            limit = 7
            chapter_name = "Chapter 13"
        else:
            limit = 10
            chapter_name = "Chapter 7/11" if is_chapter_7_or_11 else "Bankruptcy"

        if age_years > limit:
            violations.append(Violation(
                violation_type=ViolationType.BANKRUPTCY_OBSOLETE,
                severity=Severity.CRITICAL,
                account_id=record.record_id,
                creditor_name=record.court_name or "Public Record",
                description=(
                    f"OBSOLETE PUBLIC RECORD: This {chapter_name} Bankruptcy "
                    f"was filed on {filing_date} ({age_years:.1f} years ago). "
                    f"Under FCRA §605(a)(1), bankruptcies must be removed after {limit} years "
                    f"from the date of filing. This record is {age_years - limit:.1f} years "
                    f"past its legal reporting period and should have been deleted."
                ),
                expected_value=f"Deleted / Obsolete (>{limit} years)",
                actual_value=f"Still Reporting ({age_years:.1f} years old)",
                fcra_section="605(a)(1)",
                metro2_field="Public Record Segment",
                evidence={
                    "record_type": record.record_type,
                    "chapter": chapter_name,
                    "filed_date": str(filing_date),
                    "age_years": round(age_years, 1),
                    "limit_years": limit,
                    "years_past_limit": round(age_years - limit, 1)
                }
            ))

        return violations

    @staticmethod
    def audit_public_records(records: List[PublicRecord]) -> List[Violation]:
        """
        Main entry point for auditing all public records.
        Runs all public record checks and returns combined violations.
        """
        all_violations = []

        for record in records:
            all_violations.extend(PublicRecordRules.check_ncap_compliance(record))
            all_violations.extend(PublicRecordRules.check_judgment_status(record))
            all_violations.extend(PublicRecordRules.check_bankruptcy_dates(record))

        return all_violations
