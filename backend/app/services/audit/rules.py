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
from datetime import date, timedelta
from typing import List

from ...models.ssot import (
    Account, NormalizedReport, Violation,
    ViolationType, Severity, FurnisherType, AccountStatus, Bureau
)

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
                        f"This open original creditor account is missing the Scheduled Payment field."
                    ),
                    expected_value="Valid scheduled payment amount",
                    actual_value="Not Reported",
                    fcra_section="611(a)",
                    metro2_field=None,
                    evidence={}
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
        Check if a collection account is missing original creditor info.

        Collectors MUST report who the original creditor was.
        """
        violations = []

        if account.furnisher_type != FurnisherType.COLLECTOR:
            return violations

        if not account.original_creditor:
            violations.append(Violation(
                violation_type=ViolationType.MISSING_ORIGINAL_CREDITOR,  # FIXED: correct type
                severity=Severity.MEDIUM,
                account_id=account.account_id,
                creditor_name=account.creditor_name,
                account_number_masked=account.account_number_masked,
                furnisher_type=account.furnisher_type,
                bureau=bureau,
                description=(
                    f"This collection account does not identify the original creditor. "
                    f"Without this information, the debt cannot be properly verified."
                ),
                expected_value="Original creditor name",
                actual_value="Not Reported",
                fcra_section="611(a)",
                metro2_field=None,
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


# =============================================================================
# TEMPORAL RULES
# =============================================================================

class TemporalRules:
    """
    Rules that check time-based violations.
    """

    @staticmethod
    def check_obsolete_account(account: Account, bureau: Bureau) -> List[Violation]:
        """
        Check if account has exceeded 7-year reporting limit.

        FCRA §605(a) limits reporting to 7 years from DOFD.
        """
        violations = []

        # Must have DOFD to check
        if not account.date_of_first_delinquency:
            return violations

        # Only applies to derogatory accounts
        if account.account_status not in [AccountStatus.CHARGEOFF, AccountStatus.COLLECTION, AccountStatus.DEROGATORY]:
            return violations

        dofd = account.date_of_first_delinquency
        obsolete_date = _add_years(dofd, 7)
        today = date.today()

        if obsolete_date < today:
            days_past = (today - obsolete_date).days
            months_past = days_past // 30

            violations.append(Violation(
                violation_type=ViolationType.OBSOLETE_ACCOUNT,
                severity=Severity.HIGH,
                account_id=account.account_id,
                creditor_name=account.creditor_name,
                account_number_masked=account.account_number_masked,
                furnisher_type=account.furnisher_type,
                bureau=bureau,
                description=(
                    f"This account has a DOFD of {dofd.strftime('%B %d, %Y')}, meaning the "
                    f"7-year reporting period expired on {obsolete_date.strftime('%B %d, %Y')}. "
                    f"This account is approximately {months_past} months past the legal limit."
                ),
                expected_value=f"Removal by {obsolete_date}",
                actual_value=f"Still reporting as of {today}",
                fcra_section="605(a)",
                metro2_field="25",
                evidence={
                    "dofd": str(dofd),
                    "obsolete_date": str(obsolete_date),
                    "days_past": days_past,
                    "months_past": months_past
                }
            ))

        return violations

    @staticmethod
    def check_stale_reporting(account: Account, bureau: Bureau) -> List[Violation]:
        """
        Check if account hasn't been updated in over 90 days.

        Furnishers should update accounts regularly.
        """
        violations = []

        if not account.date_reported:
            return violations

        today = date.today()
        days_since_update = (today - account.date_reported).days

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
                    f"This account was last reported on {account.date_reported.strftime('%B %d, %Y')}, "
                    f"which is {days_since_update} days ago. Data may be stale and inaccurate."
                ),
                expected_value="Recent update within 90 days",
                actual_value=f"{days_since_update} days since last update",
                fcra_section="611(a)",
                metro2_field=None,
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
