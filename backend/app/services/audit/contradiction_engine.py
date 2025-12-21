"""
Credit Engine 2.0 - Phase-1 Deterministic Contradiction Engine

Detects PROVABLE FACTUAL IMPOSSIBILITIES in tradeline data.
No probabilistic models. No machine learning. Only hard logic.

This engine runs BEFORE statute selection or letter generation.
Output feeds dispute letters, verification rebuttals, and enforcement escalation.

The goal is to FORCE DELETION by proving data CANNOT BE TRUE, not merely noncompliant.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Dict, List, Optional, Any
from enum import Enum

from ...models.ssot import (
    ViolationType,
    Severity,
    Bureau,
    FurnisherType,
    AccountStatus,
)


# =============================================================================
# CONTRADICTION OBJECT SCHEMA
# =============================================================================

@dataclass
class Contradiction:
    """
    Represents a mathematically or temporally impossible reporting condition.

    Each contradiction answers:
    - What is wrong? (type, description)
    - Why it cannot be true? (contradiction field)
    - Why it matters? (impact field)
    """
    # Classification
    type: str  # e.g., "temporal_impossibility", "mathematical_impossibility"
    rule_code: str  # e.g., "T1", "D2", "M1"
    violation_type: ViolationType
    severity: Severity

    # What the bureau claims
    bureau_claim: str  # e.g., "Opened 01/2023"

    # Why it's impossible
    contradiction: str  # e.g., "First delinquency 08/2019"
    description: str  # Human-readable explanation

    # Why it matters
    impact: str  # e.g., "Account appears artificially younger"
    supports_deletion: bool = True

    # Evidence for downstream processing
    evidence: Dict[str, Any] = field(default_factory=dict)

    # Account reference (for integration with existing violation system)
    account_id: Optional[str] = None
    creditor_name: Optional[str] = None
    account_number_masked: Optional[str] = None
    bureau: Optional[Bureau] = None


# =============================================================================
# CONTRADICTION DETECTION ENGINE
# =============================================================================

class ContradictionEngine:
    """
    Phase-1 Deterministic Contradiction Detection Engine.

    Detects:
    1. Temporal impossibilities (CRITICAL)
    2. DOFD/Aging violations (HIGH)
    3. Mathematical impossibilities (HIGH)
    4. Status/Field contradictions (MEDIUM)
    """

    # Default interest cap for balance calculations (conservative 8% APR)
    DEFAULT_INTEREST_CAP = 0.08

    # Negative status values that require DOFD
    NEGATIVE_STATUSES = {'collection', 'chargeoff', 'late', 'derogatory', '120+', '90', '60', '30'}

    def detect_contradictions(self, account: Dict[str, Any]) -> List[Contradiction]:
        """
        Analyze an account and return all detected contradictions.

        Args:
            account: Dict containing account data with fields like:
                - account_id, creditor_name, account_number_masked
                - open_date, dofd, chargeoff_date, last_payment_date
                - payment_history_months, payment_history (list of status codes)
                - status, reported_balance, original_balance
                - interest_cap, credit_limit, report_date
                - date_closed, date_last_activity

        Returns:
            List of Contradiction objects sorted by severity (critical → high → medium)
        """
        contradictions = []

        # Run all rule categories
        contradictions.extend(self._check_temporal_impossibilities(account))
        contradictions.extend(self._check_dofd_aging_violations(account))
        contradictions.extend(self._check_mathematical_impossibilities(account))
        contradictions.extend(self._check_status_field_contradictions(account))
        contradictions.extend(self._check_phase21_contradictions(account))

        # Sort by severity: CRITICAL > HIGH > MEDIUM > LOW
        severity_order = {
            Severity.CRITICAL: 0,
            Severity.HIGH: 1,
            Severity.MEDIUM: 2,
            Severity.LOW: 3,
        }
        contradictions.sort(key=lambda c: severity_order.get(c.severity, 99))

        return contradictions

    # =========================================================================
    # TEMPORAL IMPOSSIBILITIES (CRITICAL)
    # =========================================================================

    def _check_temporal_impossibilities(self, account: Dict[str, Any]) -> List[Contradiction]:
        """Check for timeline violations that cannot be true."""
        contradictions = []

        # T1: Open Date vs DOFD
        contradictions.extend(self._check_t1_open_date_vs_dofd(account))

        # T2: Payment History vs Account Age
        contradictions.extend(self._check_t2_payment_history_vs_age(account))

        # T3: Charge-Off Before Last Payment
        contradictions.extend(self._check_t3_chargeoff_before_last_payment(account))

        # T4: Delinquency Ladder Inversion
        contradictions.extend(self._check_t4_delinquency_ladder_inversion(account))

        return contradictions

    def _check_t1_open_date_vs_dofd(self, account: Dict[str, Any]) -> List[Contradiction]:
        """
        T1: Date of First Delinquency cannot be before the account was opened.

        Rule: if open_date > dofd → IMPOSSIBLE
        """
        open_date = self._parse_date(account.get('open_date') or account.get('date_opened'))
        dofd = self._parse_date(account.get('dofd') or account.get('date_of_first_delinquency'))

        if open_date and dofd and open_date > dofd:
            return [Contradiction(
                type="temporal_impossibility",
                rule_code="T1",
                violation_type=ViolationType.DOFD_AFTER_DATE_OPENED,
                severity=Severity.CRITICAL,
                bureau_claim=f"Account opened {open_date.strftime('%m/%Y')}",
                contradiction=f"First delinquency reported as {dofd.strftime('%m/%Y')}",
                description="Account opened AFTER the reported date of first delinquency. "
                           "An account cannot become delinquent before it exists.",
                impact="Account appears artificially younger, potentially extending the "
                       "7-year negative reporting window and misrepresenting account history.",
                supports_deletion=True,
                evidence={
                    "open_date": open_date.isoformat(),
                    "dofd": dofd.isoformat(),
                    "days_impossible": (open_date - dofd).days,
                },
                account_id=account.get('account_id'),
                creditor_name=account.get('creditor_name'),
                account_number_masked=account.get('account_number_masked'),
            )]
        return []

    def _check_t2_payment_history_vs_age(self, account: Dict[str, Any]) -> List[Contradiction]:
        """
        T2: Payment history cannot span more months than the account has existed.

        Rule: if payment_history_months > months_since(open_date) → IMPOSSIBLE
        """
        open_date = self._parse_date(account.get('open_date') or account.get('date_opened'))
        report_date = self._parse_date(account.get('report_date')) or date.today()

        # Get payment history months - either explicit count or from history array
        payment_history = account.get('payment_history', [])
        payment_history_months = account.get('payment_history_months')

        if payment_history_months is None and payment_history:
            payment_history_months = len(payment_history)

        if open_date and payment_history_months:
            # Calculate actual months since account opened
            months_since_open = self._months_between(open_date, report_date)

            if payment_history_months > months_since_open:
                return [Contradiction(
                    type="temporal_impossibility",
                    rule_code="T2",
                    violation_type=ViolationType.PAYMENT_HISTORY_EXCEEDS_ACCOUNT_AGE,
                    severity=Severity.CRITICAL,
                    bureau_claim=f"Payment history spans {payment_history_months} months",
                    contradiction=f"Account only {months_since_open} months old (opened {open_date.strftime('%m/%Y')})",
                    description="Payment history covers more months than the account has existed. "
                               "Cannot have payment records before the account was opened.",
                    impact="Fabricated payment history or incorrect account age, either of which "
                           "undermines the accuracy and reliability of the reported information.",
                    supports_deletion=True,
                    evidence={
                        "open_date": open_date.isoformat(),
                        "report_date": report_date.isoformat(),
                        "payment_history_months": payment_history_months,
                        "actual_account_age_months": months_since_open,
                        "excess_months": payment_history_months - months_since_open,
                    },
                    account_id=account.get('account_id'),
                    creditor_name=account.get('creditor_name'),
                    account_number_masked=account.get('account_number_masked'),
                )]
        return []

    def _check_t3_chargeoff_before_last_payment(self, account: Dict[str, Any]) -> List[Contradiction]:
        """
        T3: Cannot charge off an account before the last payment was received.

        Rule: if chargeoff_date < last_payment_date → IMPOSSIBLE
        """
        chargeoff_date = self._parse_date(account.get('chargeoff_date'))
        last_payment_date = self._parse_date(
            account.get('last_payment_date') or account.get('date_last_payment')
        )

        if chargeoff_date and last_payment_date and chargeoff_date < last_payment_date:
            return [Contradiction(
                type="temporal_impossibility",
                rule_code="T3",
                violation_type=ViolationType.CHARGEOFF_BEFORE_LAST_PAYMENT,
                severity=Severity.CRITICAL,
                bureau_claim=f"Charged off {chargeoff_date.strftime('%m/%d/%Y')}",
                contradiction=f"Last payment received {last_payment_date.strftime('%m/%d/%Y')}",
                description="Account was charged off BEFORE the last payment was made. "
                           "A chargeoff cannot precede ongoing payment activity.",
                impact="Impossible timeline suggests data fabrication or severe record-keeping "
                       "errors that fundamentally undermine account accuracy.",
                supports_deletion=True,
                evidence={
                    "chargeoff_date": chargeoff_date.isoformat(),
                    "last_payment_date": last_payment_date.isoformat(),
                    "days_impossible": (last_payment_date - chargeoff_date).days,
                },
                account_id=account.get('account_id'),
                creditor_name=account.get('creditor_name'),
                account_number_masked=account.get('account_number_masked'),
            )]
        return []

    def _check_t4_delinquency_ladder_inversion(self, account: Dict[str, Any]) -> List[Contradiction]:
        """
        T4: Delinquency must progress in order (30 → 60 → 90 → 120+).

        Rule: if 90_day_date < 30_day_date → IMPOSSIBLE

        Also checks for impossible jumps in payment history (0 → 60, skipping 30).
        """
        contradictions = []
        payment_history = account.get('payment_history', [])

        if not payment_history:
            return []

        # Check for ladder inversions in payment history
        prev_delinquency_level = 0
        prev_month_info = None

        for entry in payment_history:
            status = entry.get('status', '') if isinstance(entry, dict) else str(entry)
            month_info = entry.get('month', '') if isinstance(entry, dict) else ''

            # Parse delinquency level from status
            current_level = self._parse_delinquency_level(status)

            if current_level is not None and prev_delinquency_level is not None:
                # Check for impossible jumps: can't go from current to 60+ without hitting 30 first
                if prev_delinquency_level == 0 and current_level >= 60:
                    contradictions.append(Contradiction(
                        type="temporal_impossibility",
                        rule_code="T4",
                        violation_type=ViolationType.DELINQUENCY_LADDER_INVERSION,
                        severity=Severity.CRITICAL,
                        bureau_claim=f"Jumped from current to {current_level} days late",
                        contradiction="Must pass through 30-day delinquency first",
                        description=f"Payment history shows impossible delinquency progression: "
                                   f"jumped from current/0 days to {current_level} days late. "
                                   f"Delinquency must progress through each 30-day stage.",
                        impact="Fabricated or corrupted payment history that artificially "
                               "inflates derogatory reporting.",
                        supports_deletion=True,
                        evidence={
                            "previous_level": prev_delinquency_level,
                            "current_level": current_level,
                            "month": month_info,
                            "skipped_levels": list(range(30, current_level, 30)),
                        },
                        account_id=account.get('account_id'),
                        creditor_name=account.get('creditor_name'),
                        account_number_masked=account.get('account_number_masked'),
                    ))
                    break  # One violation is enough

            prev_delinquency_level = current_level
            prev_month_info = month_info

        return contradictions

    # =========================================================================
    # DOFD / AGING VIOLATIONS (HIGH)
    # =========================================================================

    def _check_dofd_aging_violations(self, account: Dict[str, Any]) -> List[Contradiction]:
        """Check for DOFD-related contradictions."""
        contradictions = []

        # D1: Missing DOFD with Negative Status
        contradictions.extend(self._check_d1_missing_dofd_negative_status(account))

        # D2: DOFD vs Inferred First Late
        contradictions.extend(self._check_d2_dofd_vs_inferred(account))

        # D3: Over-Reporting Beyond 7 Years
        contradictions.extend(self._check_d3_over_seven_years(account))

        return contradictions

    def _check_d1_missing_dofd_negative_status(self, account: Dict[str, Any]) -> List[Contradiction]:
        """
        D1: Accounts with negative status MUST have a Date of First Delinquency.

        Rule: if status in ['collection','chargeoff','late'] AND dofd is None → VIOLATION
        """
        status = str(account.get('status', '')).lower()
        dofd = account.get('dofd') or account.get('date_of_first_delinquency')

        # Check if status is negative
        is_negative_status = any(neg in status for neg in self.NEGATIVE_STATUSES)

        # Also check account_status if present
        account_status = account.get('account_status')
        if account_status:
            if isinstance(account_status, AccountStatus):
                is_negative_status = is_negative_status or account_status in [
                    AccountStatus.COLLECTION, AccountStatus.CHARGEOFF, AccountStatus.DEROGATORY
                ]
            else:
                is_negative_status = is_negative_status or str(account_status).lower() in self.NEGATIVE_STATUSES

        if is_negative_status and not dofd:
            return [Contradiction(
                type="dofd_aging_violation",
                rule_code="D1",
                violation_type=ViolationType.CHARGEOFF_MISSING_DOFD,
                severity=Severity.HIGH,
                bureau_claim=f"Account status: {status}",
                contradiction="No Date of First Delinquency reported",
                description="Account shows negative status (collection, chargeoff, or late) "
                           "but has no Date of First Delinquency. DOFD is required for all "
                           "derogatory accounts to establish the 7-year reporting window.",
                impact="Without DOFD, the account may be reported indefinitely, violating "
                       "FCRA §605(a) reporting time limits. Also prevents consumer from "
                       "knowing when negative information will age off.",
                supports_deletion=True,
                evidence={
                    "status": status,
                    "dofd": None,
                    "account_status": str(account_status) if account_status else None,
                },
                account_id=account.get('account_id'),
                creditor_name=account.get('creditor_name'),
                account_number_masked=account.get('account_number_masked'),
            )]
        return []

    def _check_d2_dofd_vs_inferred(self, account: Dict[str, Any]) -> List[Contradiction]:
        """
        D2: Reported DOFD must match the first late payment in payment history.

        Rule: if dofd != inferred_first_late_payment → CONTRADICTION
        """
        dofd = self._parse_date(account.get('dofd') or account.get('date_of_first_delinquency'))
        payment_history = account.get('payment_history', [])

        if not dofd or not payment_history:
            return []

        # Find first late payment in history
        inferred_first_late = None
        for entry in payment_history:
            if isinstance(entry, dict):
                status = entry.get('status', '')
                month = entry.get('month')
                year = entry.get('year')

                # Check if this is a late status
                if self._is_late_status(status):
                    if month and year:
                        try:
                            inferred_first_late = date(int(year), int(month), 1)
                            break
                        except (ValueError, TypeError):
                            pass

        if inferred_first_late:
            # Allow 1 month tolerance for reporting lag
            months_diff = abs(self._months_between(dofd, inferred_first_late))

            if months_diff > 1:
                return [Contradiction(
                    type="dofd_aging_violation",
                    rule_code="D2",
                    violation_type=ViolationType.DOFD_INFERRED_MISMATCH,
                    severity=Severity.HIGH,
                    bureau_claim=f"DOFD reported as {dofd.strftime('%m/%Y')}",
                    contradiction=f"First late payment in history: {inferred_first_late.strftime('%m/%Y')}",
                    description="Reported Date of First Delinquency does not match the first "
                               "late payment shown in payment history. This is a fundamental "
                               "data integrity issue.",
                    impact="Incorrect DOFD can extend the 7-year reporting window or create "
                           "an artificially severe derogatory pattern.",
                    supports_deletion=True,
                    evidence={
                        "reported_dofd": dofd.isoformat(),
                        "inferred_dofd": inferred_first_late.isoformat(),
                        "months_difference": months_diff,
                    },
                    account_id=account.get('account_id'),
                    creditor_name=account.get('creditor_name'),
                    account_number_masked=account.get('account_number_masked'),
                )]
        return []

    def _check_d3_over_seven_years(self, account: Dict[str, Any]) -> List[Contradiction]:
        """
        D3: Negative accounts cannot be reported beyond 7 years from DOFD.

        Rule: if report_date - dofd > 7 years → OBSOLETE
        """
        dofd = self._parse_date(account.get('dofd') or account.get('date_of_first_delinquency'))
        report_date = self._parse_date(account.get('report_date')) or date.today()

        if not dofd:
            return []

        # Calculate years since DOFD
        years_since_dofd = (report_date - dofd).days / 365.25

        if years_since_dofd > 7:
            return [Contradiction(
                type="dofd_aging_violation",
                rule_code="D3",
                violation_type=ViolationType.OBSOLETE_ACCOUNT,
                severity=Severity.HIGH,
                bureau_claim=f"Still reporting as of {report_date.strftime('%m/%Y')}",
                contradiction=f"DOFD was {dofd.strftime('%m/%Y')} ({years_since_dofd:.1f} years ago)",
                description="Account is being reported beyond the 7-year FCRA limit. "
                           "Negative information must be removed 7 years from DOFD.",
                impact="Continued reporting of obsolete information violates FCRA §605(a) "
                       "and artificially suppresses consumer's credit score.",
                supports_deletion=True,
                evidence={
                    "dofd": dofd.isoformat(),
                    "report_date": report_date.isoformat(),
                    "years_since_dofd": round(years_since_dofd, 2),
                    "years_over_limit": round(years_since_dofd - 7, 2),
                },
                account_id=account.get('account_id'),
                creditor_name=account.get('creditor_name'),
                account_number_masked=account.get('account_number_masked'),
            )]
        return []

    # =========================================================================
    # MATHEMATICAL IMPOSSIBILITIES (HIGH)
    # =========================================================================

    def _check_mathematical_impossibilities(self, account: Dict[str, Any]) -> List[Contradiction]:
        """Check for math-based contradictions."""
        contradictions = []

        # M1: Balance Exceeds Legal Maximum
        contradictions.extend(self._check_m1_balance_exceeds_legal_max(account))

        # M2: Balance Increases After Charge-Off
        contradictions.extend(self._check_m2_balance_increase_after_chargeoff(account))

        return contradictions

    def _check_m1_balance_exceeds_legal_max(self, account: Dict[str, Any]) -> List[Contradiction]:
        """
        M1: Reported balance cannot exceed mathematical maximum with interest.

        Rule: reported_balance > max_legal_balance(original, interest_cap, years) → IMPOSSIBLE
        """
        reported_balance = account.get('reported_balance') or account.get('balance')
        original_balance = account.get('original_balance') or account.get('high_credit')
        interest_cap = account.get('interest_cap', self.DEFAULT_INTEREST_CAP)

        # Get date information for time calculation
        open_date = self._parse_date(account.get('open_date') or account.get('date_opened'))
        report_date = self._parse_date(account.get('report_date')) or date.today()

        if not all([reported_balance, original_balance, open_date]):
            return []

        # Skip if reported balance is less than original (paid down)
        if reported_balance <= original_balance:
            return []

        # Calculate maximum possible balance with compound interest
        years_elapsed = (report_date - open_date).days / 365.25
        max_legal_balance = original_balance * ((1 + interest_cap) ** years_elapsed)

        # Add 20% buffer for fees and penalties (conservative)
        max_legal_balance *= 1.20

        if reported_balance > max_legal_balance:
            return [Contradiction(
                type="mathematical_impossibility",
                rule_code="M1",
                violation_type=ViolationType.BALANCE_EXCEEDS_LEGAL_MAX,
                severity=Severity.HIGH,
                bureau_claim=f"Current balance: ${reported_balance:,.2f}",
                contradiction=f"Maximum possible with {interest_cap*100:.0f}% APR over "
                             f"{years_elapsed:.1f} years: ${max_legal_balance:,.2f}",
                description="Reported balance exceeds the mathematical maximum possible "
                           "even with maximum allowable interest compounding.",
                impact="Balance inflation beyond legal limits indicates fabricated debt "
                       "amounts or unauthorized charges.",
                supports_deletion=True,
                evidence={
                    "reported_balance": reported_balance,
                    "original_balance": original_balance,
                    "interest_cap": interest_cap,
                    "years_elapsed": round(years_elapsed, 2),
                    "max_legal_balance": round(max_legal_balance, 2),
                    "excess_amount": round(reported_balance - max_legal_balance, 2),
                },
                account_id=account.get('account_id'),
                creditor_name=account.get('creditor_name'),
                account_number_masked=account.get('account_number_masked'),
            )]
        return []

    def _check_m2_balance_increase_after_chargeoff(self, account: Dict[str, Any]) -> List[Contradiction]:
        """
        M2: Balance cannot increase after charge-off without new activity.

        Rule: if balance(t2) > balance(t1) after chargeoff without activity → IMPOSSIBLE

        Note: This requires historical balance data which may not always be available.
        For single-point-in-time data, we check if current balance > chargeoff balance.
        """
        status = str(account.get('status', '')).lower()
        account_status = account.get('account_status')

        # Check if account is charged off
        is_chargeoff = 'chargeoff' in status or 'charge-off' in status
        if account_status and isinstance(account_status, AccountStatus):
            is_chargeoff = is_chargeoff or account_status == AccountStatus.CHARGEOFF

        if not is_chargeoff:
            return []

        reported_balance = account.get('reported_balance') or account.get('balance')
        chargeoff_balance = account.get('chargeoff_balance') or account.get('high_credit')

        # If we have both and current > chargeoff, that's suspicious
        if reported_balance and chargeoff_balance and reported_balance > chargeoff_balance:
            # Check for legitimate reasons (payments reduced it, then increased - unlikely)
            # For now, flag if balance is significantly higher (10%+ increase)
            increase_pct = (reported_balance - chargeoff_balance) / chargeoff_balance * 100

            if increase_pct > 10:
                return [Contradiction(
                    type="mathematical_impossibility",
                    rule_code="M2",
                    violation_type=ViolationType.BALANCE_INCREASE_AFTER_CHARGEOFF,
                    severity=Severity.HIGH,
                    bureau_claim=f"Current balance: ${reported_balance:,.2f}",
                    contradiction=f"Original/chargeoff balance: ${chargeoff_balance:,.2f}",
                    description="Balance has increased after charge-off. Once an account is "
                               "charged off, the balance should not grow without new credit "
                               "activity (which is prohibited on a charged-off account).",
                    impact="Post-chargeoff balance inflation indicates unauthorized fees "
                           "or fabricated debt amounts.",
                    supports_deletion=True,
                    evidence={
                        "reported_balance": reported_balance,
                        "chargeoff_balance": chargeoff_balance,
                        "increase_amount": round(reported_balance - chargeoff_balance, 2),
                        "increase_percentage": round(increase_pct, 1),
                    },
                    account_id=account.get('account_id'),
                    creditor_name=account.get('creditor_name'),
                    account_number_masked=account.get('account_number_masked'),
                )]
        return []

    # =========================================================================
    # STATUS / FIELD CONTRADICTIONS (MEDIUM)
    # =========================================================================

    def _check_status_field_contradictions(self, account: Dict[str, Any]) -> List[Contradiction]:
        """Check for contradictory status/field combinations."""
        contradictions = []

        # S1: Paid Status with Delinquencies
        contradictions.extend(self._check_s1_paid_status_with_delinquencies(account))

        # S2: Closed Account with Activity
        contradictions.extend(self._check_s2_closed_account_with_activity(account))

        return contradictions

    def _check_s1_paid_status_with_delinquencies(self, account: Dict[str, Any]) -> List[Contradiction]:
        """
        S1: An account marked as "Paid" should not have late payment markers.

        Rule: if status == 'paid' AND late_payments_exist → CONTRADICTION
        """
        status = str(account.get('status', '')).lower()
        account_status = account.get('account_status')
        payment_history = account.get('payment_history', [])

        # Check if status is "paid"
        is_paid = 'paid' in status or status == 'paid'
        if account_status:
            if isinstance(account_status, AccountStatus):
                is_paid = is_paid or account_status == AccountStatus.PAID
            else:
                is_paid = is_paid or str(account_status).lower() == 'paid'

        if not is_paid or not payment_history:
            return []

        # Check for late payments in history
        late_count = 0
        late_months = []
        for entry in payment_history:
            if isinstance(entry, dict):
                entry_status = entry.get('status', '')
                if self._is_late_status(entry_status):
                    late_count += 1
                    month_info = f"{entry.get('month', '?')}/{entry.get('year', '?')}"
                    late_months.append(month_info)

        if late_count > 0:
            return [Contradiction(
                type="status_field_contradiction",
                rule_code="S1",
                violation_type=ViolationType.PAID_STATUS_WITH_DELINQUENCIES,
                severity=Severity.MEDIUM,
                bureau_claim=f"Account status: PAID",
                contradiction=f"{late_count} late payment(s) in history",
                description="Account is marked as 'Paid' but payment history shows late "
                           "payments. A fully paid account in good standing should not "
                           "have derogatory payment markers.",
                impact="Contradictory information creates confusion about account standing "
                       "and may be suppressing credit score unnecessarily.",
                supports_deletion=True,
                evidence={
                    "status": "paid",
                    "late_payment_count": late_count,
                    "late_months": late_months[:5],  # First 5 for evidence
                },
                account_id=account.get('account_id'),
                creditor_name=account.get('creditor_name'),
                account_number_masked=account.get('account_number_masked'),
            )]
        return []

    def _check_s2_closed_account_with_activity(self, account: Dict[str, Any]) -> List[Contradiction]:
        """
        S2: Activity cannot occur after an account is closed.

        Rule: if activity_date > closed_date → CONTRADICTION
        """
        closed_date = self._parse_date(account.get('date_closed') or account.get('closed_date'))
        last_activity_date = self._parse_date(
            account.get('date_last_activity') or account.get('last_activity_date')
        )
        last_payment_date = self._parse_date(
            account.get('last_payment_date') or account.get('date_last_payment')
        )

        if not closed_date:
            return []

        contradictions = []

        # Check if last activity is after close date
        if last_activity_date and last_activity_date > closed_date:
            contradictions.append(Contradiction(
                type="status_field_contradiction",
                rule_code="S2",
                violation_type=ViolationType.CLOSED_ACCOUNT_POST_ACTIVITY,
                severity=Severity.MEDIUM,
                bureau_claim=f"Account closed {closed_date.strftime('%m/%d/%Y')}",
                contradiction=f"Activity reported {last_activity_date.strftime('%m/%d/%Y')}",
                description="Account shows activity after the reported close date. "
                           "No activity should occur on a closed account.",
                impact="Post-closure activity indicates data integrity issues or "
                       "improper account handling.",
                supports_deletion=True,
                evidence={
                    "closed_date": closed_date.isoformat(),
                    "last_activity_date": last_activity_date.isoformat(),
                    "days_after_close": (last_activity_date - closed_date).days,
                },
                account_id=account.get('account_id'),
                creditor_name=account.get('creditor_name'),
                account_number_masked=account.get('account_number_masked'),
            ))

        # Check if last payment is after close date
        if last_payment_date and last_payment_date > closed_date:
            contradictions.append(Contradiction(
                type="status_field_contradiction",
                rule_code="S2",
                violation_type=ViolationType.CLOSED_ACCOUNT_POST_ACTIVITY,
                severity=Severity.MEDIUM,
                bureau_claim=f"Account closed {closed_date.strftime('%m/%d/%Y')}",
                contradiction=f"Payment recorded {last_payment_date.strftime('%m/%d/%Y')}",
                description="Payment recorded after the account close date. "
                           "Payments should not be processed on closed accounts.",
                impact="Post-closure payments indicate data integrity issues or "
                       "the account was improperly reopened without updating status.",
                supports_deletion=True,
                evidence={
                    "closed_date": closed_date.isoformat(),
                    "last_payment_date": last_payment_date.isoformat(),
                    "days_after_close": (last_payment_date - closed_date).days,
                },
                account_id=account.get('account_id'),
                creditor_name=account.get('creditor_name'),
                account_number_masked=account.get('account_number_masked'),
            ))

        return contradictions

    # =========================================================================
    # PHASE-2.1 ADDITIONAL CONTRADICTIONS (MEDIUM)
    # =========================================================================

    def _check_phase21_contradictions(self, account: Dict[str, Any]) -> List[Contradiction]:
        """Check for Phase-2.1 additional contradictions."""
        contradictions = []

        # X1: Stale/Outdated Data
        contradictions.extend(self._check_x1_stale_data(account))

        # K1: Missing Original Creditor Elevated
        contradictions.extend(self._check_k1_missing_original_creditor_elevated(account))

        # P1: Missing Scheduled Payment Contradiction
        contradictions.extend(self._check_p1_missing_scheduled_payment(account))

        return contradictions

    def _check_x1_stale_data(self, account: Dict[str, Any]) -> List[Contradiction]:
        """
        X1: Stale/Outdated Data - Activity date older than status updates.

        Triggers when:
        - last_activity_date is older than the most recent reported status update, OR
        - Account shows recent updates with no corresponding activity signals
        """
        last_activity_date = self._parse_date(
            account.get('date_last_activity') or account.get('last_activity_date')
        )
        status_date = self._parse_date(
            account.get('status_date') or account.get('date_reported') or account.get('report_date')
        )
        last_payment_date = self._parse_date(
            account.get('last_payment_date') or account.get('date_last_payment')
        )

        # Check if last_activity_date is significantly older than status updates
        if last_activity_date and status_date:
            # If status was updated more than 60 days after last activity, that's stale
            days_stale = (status_date - last_activity_date).days

            if days_stale > 60:
                return [Contradiction(
                    type="stale_data",
                    rule_code="X1",
                    violation_type=ViolationType.STALE_DATA,
                    severity=Severity.MEDIUM,
                    bureau_claim=f"Account status updated {status_date.strftime('%m/%Y')}",
                    contradiction=f"Last activity was {last_activity_date.strftime('%m/%Y')} ({days_stale} days prior)",
                    description="Account status was updated without corresponding account activity. "
                               "The reported status does not reflect current account conditions.",
                    impact="Continued reporting of stale data perpetuates inaccurate information "
                           "and may misrepresent the consumer's current credit standing.",
                    supports_deletion=True,
                    evidence={
                        "last_activity_date": last_activity_date.isoformat(),
                        "status_date": status_date.isoformat(),
                        "days_stale": days_stale,
                    },
                    account_id=account.get('account_id'),
                    creditor_name=account.get('creditor_name'),
                    account_number_masked=account.get('account_number_masked'),
                )]

        # Check if account has recent payment but no activity update
        if last_payment_date and last_activity_date:
            if last_payment_date > last_activity_date:
                days_gap = (last_payment_date - last_activity_date).days
                if days_gap > 30:
                    return [Contradiction(
                        type="stale_data",
                        rule_code="X1",
                        violation_type=ViolationType.STALE_DATA,
                        severity=Severity.MEDIUM,
                        bureau_claim=f"Last activity: {last_activity_date.strftime('%m/%d/%Y')}",
                        contradiction=f"Payment received {last_payment_date.strftime('%m/%d/%Y')} ({days_gap} days later)",
                        description="Payment activity occurred after the reported last activity date. "
                                   "Account activity tracking is not current.",
                        impact="Failure to update activity dates creates stale data that does not "
                               "reflect the consumer's actual payment behavior.",
                        supports_deletion=True,
                        evidence={
                            "last_activity_date": last_activity_date.isoformat(),
                            "last_payment_date": last_payment_date.isoformat(),
                            "days_gap": days_gap,
                        },
                        account_id=account.get('account_id'),
                        creditor_name=account.get('creditor_name'),
                        account_number_masked=account.get('account_number_masked'),
                    )]

        return []

    def _check_k1_missing_original_creditor_elevated(self, account: Dict[str, Any]) -> List[Contradiction]:
        """
        K1: Missing Original Creditor Elevated to Contradiction.

        Promotes missing original creditor from "required field" violation to contradiction when:
        - Account is collection / debt buyer, OR
        - Chain-of-title ambiguity exists

        Impact: Furnisher authority unclear, consumer cannot verify ownership or accuracy.
        """
        original_creditor = account.get('original_creditor') or account.get('k1_original_creditor')
        creditor_name = account.get('creditor_name', '').lower()
        status = str(account.get('status', '')).lower()
        account_type = str(account.get('account_type', '')).lower()

        # Collection agency keywords
        collection_keywords = [
            'collection', 'coll', 'recovery', 'midland', 'lvnv', 'cavalry',
            'encore', 'portfolio', 'convergent', 'transworld', 'asset',
            'jefferson capital', 'unifin', 'enhanced', 'debt buyer',
            'purchased', 'assigned'
        ]

        # Check if this is a collection/debt buyer account
        is_collection = (
            'collection' in status or
            'collection' in account_type or
            any(kw in creditor_name for kw in collection_keywords)
        )

        # Check for chain-of-title indicators
        has_chain_of_title_issue = (
            account.get('sold_to') is not None or
            account.get('transferred_to') is not None or
            account.get('purchased_from') is not None or
            'sold' in creditor_name or
            'transferred' in creditor_name
        )

        # Only elevate to contradiction if collection/debt buyer AND missing OC
        if (is_collection or has_chain_of_title_issue) and not original_creditor:
            return [Contradiction(
                type="missing_original_creditor_elevated",
                rule_code="K1",
                violation_type=ViolationType.MISSING_ORIGINAL_CREDITOR_ELEVATED,
                severity=Severity.MEDIUM,
                bureau_claim=f"Account reported by: {account.get('creditor_name', 'Unknown')}",
                contradiction="No original creditor identified for collection/purchased debt",
                description="Collection or debt buyer account is reported without identifying the "
                           "original creditor. This creates a break in the chain of title and "
                           "prevents verification of legitimate ownership.",
                impact="Consumer cannot verify the debt's origin, ownership chain, or the "
                       "reporting party's authority to furnish this information. "
                       "Chain-of-title ambiguity undermines data accuracy.",
                supports_deletion=True,
                evidence={
                    "creditor_name": account.get('creditor_name'),
                    "is_collection": is_collection,
                    "has_chain_of_title_issue": has_chain_of_title_issue,
                    "original_creditor": None,
                    "status": status,
                },
                account_id=account.get('account_id'),
                creditor_name=account.get('creditor_name'),
                account_number_masked=account.get('account_number_masked'),
            )]

        return []

    def _check_p1_missing_scheduled_payment(self, account: Dict[str, Any]) -> List[Contradiction]:
        """
        P1: Missing Scheduled Payment Contradiction.

        Triggers when:
        - Scheduled payment exists but payment history is blank or skipped
        """
        scheduled_payment = account.get('scheduled_payment') or account.get('scheduled_monthly_payment')
        payment_history = account.get('payment_history', [])
        status = str(account.get('status', '')).lower()

        # Check if scheduled payment exists and is non-zero
        has_scheduled_payment = False
        if scheduled_payment:
            try:
                scheduled_amount = float(scheduled_payment)
                has_scheduled_payment = scheduled_amount > 0
            except (ValueError, TypeError):
                has_scheduled_payment = False

        if not has_scheduled_payment:
            return []

        # Check if payment history is blank, empty, or all unknown
        history_is_blank = False

        if not payment_history:
            history_is_blank = True
        elif isinstance(payment_history, list):
            # Check if all entries are blank/unknown
            non_blank_count = 0
            for entry in payment_history:
                if isinstance(entry, dict):
                    status_val = entry.get('status', '')
                else:
                    status_val = str(entry)

                # Unknown/blank indicators
                if status_val and status_val.upper().strip() not in ['', 'U', 'UNKNOWN', '-', 'X', '*']:
                    non_blank_count += 1

            # If less than 3 months of actual history, consider it effectively blank
            history_is_blank = non_blank_count < 3

        # Only flag if account is NOT closed/paid (active account should have history)
        is_active = not any(x in status for x in ['closed', 'paid', 'settled', 'transferred'])

        if has_scheduled_payment and history_is_blank and is_active:
            return [Contradiction(
                type="missing_scheduled_payment",
                rule_code="P1",
                violation_type=ViolationType.MISSING_SCHEDULED_PAYMENT_CONTRADICTION,
                severity=Severity.MEDIUM,
                bureau_claim=f"Scheduled payment: ${scheduled_payment}",
                contradiction="Payment history is blank or insufficient",
                description="Account reports a scheduled payment amount but has no meaningful "
                           "payment history. An account with scheduled payments must have "
                           "corresponding payment tracking.",
                impact="Missing payment history prevents verification of payment patterns "
                       "and creates incomplete data that cannot be confirmed accurate.",
                supports_deletion=True,
                evidence={
                    "scheduled_payment": scheduled_payment,
                    "payment_history_length": len(payment_history) if payment_history else 0,
                    "status": status,
                    "is_active": is_active,
                },
                account_id=account.get('account_id'),
                creditor_name=account.get('creditor_name'),
                account_number_masked=account.get('account_number_masked'),
            )]

        return []

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _parse_date(self, value: Any) -> Optional[date]:
        """Parse a date value from various formats."""
        if value is None:
            return None
        if isinstance(value, date):
            return value
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, str):
            # Try common formats
            for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%m-%d-%Y', '%Y/%m/%d']:
                try:
                    return datetime.strptime(value, fmt).date()
                except ValueError:
                    continue
        return None

    def _months_between(self, d1: date, d2: date) -> int:
        """Calculate the number of months between two dates."""
        if d1 > d2:
            d1, d2 = d2, d1
        return (d2.year - d1.year) * 12 + (d2.month - d1.month)

    def _parse_delinquency_level(self, status: str) -> Optional[int]:
        """
        Parse delinquency level from status code.
        Returns 0 for current, 30/60/90/120/150/180 for late, None for unknown.
        """
        if not status:
            return None

        status = str(status).upper().strip()

        # Current/OK statuses
        if status in ['C', 'OK', '0', 'CURRENT', '*', 'X', '-']:
            return 0

        # Numeric delinquency levels
        if status in ['1', '30']:
            return 30
        if status in ['2', '60']:
            return 60
        if status in ['3', '90']:
            return 90
        if status in ['4', '120']:
            return 120
        if status in ['5', '150']:
            return 150
        if status in ['6', '180', 'CO', 'CHARGEOFF']:
            return 180

        # Check for numeric values
        try:
            level = int(status)
            if level in [0, 30, 60, 90, 120, 150, 180]:
                return level
        except (ValueError, TypeError):
            pass

        return None

    def _is_late_status(self, status: str) -> bool:
        """Check if a payment history status indicates late payment."""
        if not status:
            return False

        status = str(status).upper().strip()

        # Late indicators
        late_indicators = ['1', '2', '3', '4', '5', '6', '30', '60', '90', '120', '150', '180',
                          'L', 'LATE', 'CO', 'CHARGEOFF', 'COLLECTION']

        return status in late_indicators or any(ind in status for ind in ['LATE', 'DELINQ'])


# =============================================================================
# CONVENIENCE FUNCTION
# =============================================================================

def detect_contradictions(account: Dict[str, Any]) -> List[Contradiction]:
    """
    Convenience function to detect contradictions in an account.

    Returns a list of Contradiction objects sorted by severity.
    """
    engine = ContradictionEngine()
    return engine.detect_contradictions(account)
