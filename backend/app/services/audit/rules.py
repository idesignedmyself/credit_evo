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
    Account, NormalizedReport, Violation, BureauAccountData,
    ViolationType, Severity, FurnisherType, AccountStatus, Bureau
)
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
