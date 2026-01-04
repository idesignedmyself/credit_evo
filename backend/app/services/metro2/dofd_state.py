"""
DOFD (Date of First Delinquency) State Machine

Tracks DOFD state transitions and detects re-aging violations per Metro 2 V2.0 spec.
The DOFD is a protected field that establishes the 7-year reporting window under FCRA §605(a).

Key Rules:
- DOFD_CURRENT_MUST_ZERO_FILL: Current accounts (status 11) must have zero-filled DOFD
- STATUS_REGRESSION_REAGING: Changing from negative to current and back without cure is re-aging
- DEBT_BUYER_DOFD_INVARIANT: Debt buyers (account type 43) cannot modify DOFD once set
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import json
from pathlib import Path


class DOFDState(Enum):
    """DOFD lifecycle states."""
    CURRENT = "current"           # Account is current, DOFD should be zero-filled
    DELINQUENT = "delinquent"     # Account is delinquent, DOFD should be set
    DOFD_SET = "dofd_set"         # DOFD has been established
    CHARGEOFF = "chargeoff"       # Account charged off, DOFD locked
    COLLECTION = "collection"     # Account in collection, DOFD locked
    PAID_DEROG = "paid_derog"     # Paid but was derogatory, DOFD locked


class DOFDEventType(Enum):
    """Events that can trigger DOFD state transitions."""
    ACCOUNT_OPENED = "account_opened"
    PAYMENT_CURRENT = "payment_current"
    PAYMENT_LATE = "payment_late"
    STATUS_CHANGE = "status_change"
    CHARGEOFF = "chargeoff"
    COLLECTION_ASSIGNED = "collection_assigned"
    ACCOUNT_SOLD = "account_sold"
    CURE_COMPLETE = "cure_complete"        # Full cure - returned to current
    DOFD_MODIFICATION = "dofd_modification"
    ACCOUNT_PAID = "account_paid"


@dataclass
class DOFDViolation:
    """Represents a DOFD-related violation."""
    rule_code: str
    severity: str
    description: str
    expected_dofd: Optional[date]
    actual_dofd: Optional[date]
    account_status: str
    event_date: Optional[date]
    evidence: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "rule_code": self.rule_code,
            "severity": self.severity,
            "description": self.description,
            "expected_dofd": self.expected_dofd.isoformat() if self.expected_dofd else None,
            "actual_dofd": self.actual_dofd.isoformat() if self.actual_dofd else None,
            "account_status": self.account_status,
            "event_date": self.event_date.isoformat() if self.event_date else None,
            "evidence": self.evidence,
        }


@dataclass
class DOFDStateSnapshot:
    """Snapshot of DOFD state at a point in time."""
    state: DOFDState
    dofd_value: Optional[date]
    dofd_locked: bool
    locked_date: Optional[date]
    account_status: str
    snapshot_date: date

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "state": self.state.value,
            "dofd_value": self.dofd_value.isoformat() if self.dofd_value else None,
            "dofd_locked": self.dofd_locked,
            "locked_date": self.locked_date.isoformat() if self.locked_date else None,
            "account_status": self.account_status,
            "snapshot_date": self.snapshot_date.isoformat(),
        }


class DOFDStateMachine:
    """
    Tracks DOFD state transitions and detects violations.

    The state machine enforces Metro 2 DOFD rules:
    1. Current accounts must zero-fill DOFD field
    2. DOFD cannot be changed after chargeoff or collection assignment
    3. Debt buyers inherit DOFD and cannot modify it
    4. Re-aging (manipulating DOFD to extend reporting window) is prohibited
    """

    # Account statuses that require DOFD
    DOFD_REQUIRED_STATUSES = {
        "61", "62", "63", "64", "65",  # Paid derogatory
        "71", "78", "79", "80", "82", "83",  # Delinquent
        "84", "88", "89",  # Chargeoff, claim filed, deed in lieu
        "93", "94", "95", "96", "97",  # Collection, foreclosure, repo, chargeoff
    }

    # Account statuses where DOFD should be zero-filled
    DOFD_ZERO_FILL_STATUSES = {"11", "13"}

    # Chargeoff statuses - DOFD becomes locked
    CHARGEOFF_STATUSES = {"84", "97"}

    # Collection statuses - DOFD becomes locked
    COLLECTION_STATUSES = {"93"}

    # Paid derogatory statuses - DOFD remains locked
    PAID_DEROG_STATUSES = {"61", "62", "63", "64", "65"}

    # Debt buyer account types
    DEBT_BUYER_ACCOUNT_TYPES = {"43"}

    def __init__(
        self,
        account_type: Optional[str] = None,
        date_opened: Optional[date] = None,
    ):
        """
        Initialize the DOFD state machine.

        Args:
            account_type: Metro 2 account type code (e.g., "43" for debt buyer)
            date_opened: Account open date for validation
        """
        self.account_type = account_type
        self.date_opened = date_opened
        self.state = DOFDState.CURRENT
        self.dofd_value: Optional[date] = None
        self.dofd_locked = False
        self.dofd_lock_date: Optional[date] = None
        self.original_dofd: Optional[date] = None  # For debt buyer validation
        self.history: List[DOFDStateSnapshot] = []
        self.violations: List[DOFDViolation] = []
        self._is_debt_buyer = account_type in self.DEBT_BUYER_ACCOUNT_TYPES

    def _record_snapshot(self, account_status: str, snapshot_date: date) -> None:
        """Record current state as a snapshot."""
        self.history.append(DOFDStateSnapshot(
            state=self.state,
            dofd_value=self.dofd_value,
            dofd_locked=self.dofd_locked,
            locked_date=self.dofd_lock_date,
            account_status=account_status,
            snapshot_date=snapshot_date,
        ))

    def _parse_dofd(self, dofd: Any) -> Optional[date]:
        """Parse DOFD from various formats."""
        if dofd is None:
            return None
        if isinstance(dofd, date):
            return dofd
        if isinstance(dofd, datetime):
            return dofd.date()
        if isinstance(dofd, str):
            # Handle zero-filled DOFD
            if dofd in ("", "00000000", "0", "00/00/0000"):
                return None
            # Try common date formats
            for fmt in ("%Y%m%d", "%Y-%m-%d", "%m/%d/%Y"):
                try:
                    return datetime.strptime(dofd, fmt).date()
                except ValueError:
                    continue
        return None

    def _is_zero_filled(self, dofd: Any) -> bool:
        """Check if DOFD is zero-filled (indicating no DOFD set)."""
        if dofd is None:
            return True
        if isinstance(dofd, str):
            return dofd in ("", "00000000", "0", "00/00/0000")
        return False

    def process_event(
        self,
        event_type: DOFDEventType,
        event_date: date,
        account_status: str,
        dofd: Any = None,
    ) -> List[DOFDViolation]:
        """
        Process a DOFD-related event and detect violations.

        Args:
            event_type: Type of event
            event_date: Date of the event
            account_status: Current account status code
            dofd: DOFD value (if provided/changed)

        Returns:
            List of violations detected
        """
        new_violations = []
        parsed_dofd = self._parse_dofd(dofd)
        is_zero_filled = self._is_zero_filled(dofd)

        # Check for DOFD_CURRENT_MUST_ZERO_FILL
        if account_status in self.DOFD_ZERO_FILL_STATUSES:
            if not is_zero_filled:
                new_violations.append(DOFDViolation(
                    rule_code="DOFD_CURRENT_MUST_ZERO_FILL",
                    severity="MEDIUM",
                    description=f"Current account (status {account_status}) has non-zero DOFD. "
                                f"DOFD should be zero-filled for current accounts.",
                    expected_dofd=None,
                    actual_dofd=parsed_dofd,
                    account_status=account_status,
                    event_date=event_date,
                    evidence={
                        "rule_type": "dofd_state_machine",
                        "current_state": self.state.value,
                        "account_status_category": "current",
                    }
                ))

        # Check for missing DOFD when required
        if account_status in self.DOFD_REQUIRED_STATUSES:
            if is_zero_filled:
                new_violations.append(DOFDViolation(
                    rule_code="MISSING_DOFD_DEROGATORY",
                    severity="HIGH",
                    description=f"Derogatory account (status {account_status}) is missing DOFD. "
                                f"DOFD is required for all negative statuses per FCRA §605(a).",
                    expected_dofd=None,  # Should have a DOFD
                    actual_dofd=None,
                    account_status=account_status,
                    event_date=event_date,
                    evidence={
                        "rule_type": "dofd_state_machine",
                        "current_state": self.state.value,
                        "account_status_category": "derogatory",
                    }
                ))

        # Handle state transitions and locking
        previous_state = self.state

        if account_status in self.CHARGEOFF_STATUSES:
            self.state = DOFDState.CHARGEOFF
            if not self.dofd_locked and parsed_dofd:
                self.dofd_locked = True
                self.dofd_lock_date = event_date
                if self.original_dofd is None:
                    self.original_dofd = parsed_dofd
                self.dofd_value = parsed_dofd

        elif account_status in self.COLLECTION_STATUSES:
            self.state = DOFDState.COLLECTION
            if not self.dofd_locked and parsed_dofd:
                self.dofd_locked = True
                self.dofd_lock_date = event_date
                if self.original_dofd is None:
                    self.original_dofd = parsed_dofd
                self.dofd_value = parsed_dofd

        elif account_status in self.PAID_DEROG_STATUSES:
            self.state = DOFDState.PAID_DEROG
            # DOFD remains locked for paid derogatory

        elif account_status in self.DOFD_ZERO_FILL_STATUSES:
            # Check for status regression re-aging
            if previous_state in (DOFDState.DELINQUENT, DOFDState.DOFD_SET,
                                  DOFDState.CHARGEOFF, DOFDState.COLLECTION):
                if event_type != DOFDEventType.CURE_COMPLETE:
                    # Potential re-aging - went from negative to current
                    new_violations.append(DOFDViolation(
                        rule_code="STATUS_REGRESSION_REAGING",
                        severity="CRITICAL",
                        description=f"Account status changed from derogatory to current "
                                    f"without documented cure. This may constitute re-aging.",
                        expected_dofd=self.dofd_value,
                        actual_dofd=parsed_dofd,
                        account_status=account_status,
                        event_date=event_date,
                        evidence={
                            "rule_type": "dofd_state_machine",
                            "previous_state": previous_state.value,
                            "current_state": DOFDState.CURRENT.value,
                            "dofd_was_locked": self.dofd_locked,
                            "cfpb_recommend": True,
                        }
                    ))
            self.state = DOFDState.CURRENT

        elif account_status in self.DOFD_REQUIRED_STATUSES:
            self.state = DOFDState.DELINQUENT
            if parsed_dofd and self.dofd_value is None:
                self.dofd_value = parsed_dofd
                if self.original_dofd is None:
                    self.original_dofd = parsed_dofd

        # Check for DOFD modification after lock
        if self.dofd_locked and parsed_dofd and self.dofd_value:
            if parsed_dofd != self.dofd_value:
                new_violations.append(DOFDViolation(
                    rule_code="DOFD_MODIFICATION_AFTER_LOCK",
                    severity="CRITICAL",
                    description=f"DOFD was modified after being locked. "
                                f"Original: {self.dofd_value}, New: {parsed_dofd}. "
                                f"This is a potential re-aging violation.",
                    expected_dofd=self.dofd_value,
                    actual_dofd=parsed_dofd,
                    account_status=account_status,
                    event_date=event_date,
                    evidence={
                        "rule_type": "dofd_state_machine",
                        "lock_date": self.dofd_lock_date.isoformat() if self.dofd_lock_date else None,
                        "dofd_change_days": (parsed_dofd - self.dofd_value).days if self.dofd_value else None,
                        "cfpb_recommend": True,
                    }
                ))

        # Check for debt buyer DOFD modification
        if self._is_debt_buyer and parsed_dofd:
            if self.original_dofd and parsed_dofd != self.original_dofd:
                new_violations.append(DOFDViolation(
                    rule_code="DEBT_BUYER_DOFD_INVARIANT",
                    severity="CRITICAL",
                    description=f"Debt buyer modified DOFD. Original: {self.original_dofd}, "
                                f"Current: {parsed_dofd}. Debt buyers must preserve the original DOFD.",
                    expected_dofd=self.original_dofd,
                    actual_dofd=parsed_dofd,
                    account_status=account_status,
                    event_date=event_date,
                    evidence={
                        "rule_type": "dofd_state_machine",
                        "account_type": self.account_type,
                        "is_debt_buyer": True,
                        "dofd_change_days": (parsed_dofd - self.original_dofd).days,
                        "cfpb_recommend": True,
                    }
                ))

        # Record history
        self._record_snapshot(account_status, event_date)

        # Store violations
        self.violations.extend(new_violations)

        return new_violations

    def validate_dofd_timeline(
        self,
        account_status: str,
        dofd: Any,
        date_opened: Optional[date] = None,
        date_of_last_activity: Optional[date] = None,
        report_date: Optional[date] = None,
    ) -> List[DOFDViolation]:
        """
        Validate DOFD against account timeline.

        Args:
            account_status: Current account status code
            dofd: DOFD value
            date_opened: Account open date
            date_of_last_activity: Date of last activity
            report_date: Report date for 7-year calculation

        Returns:
            List of violations detected
        """
        violations = []
        parsed_dofd = self._parse_dofd(dofd)
        opened = date_opened or self.date_opened

        # DOFD cannot be before account opened
        if parsed_dofd and opened:
            if parsed_dofd < opened:
                violations.append(DOFDViolation(
                    rule_code="DOFD_BEFORE_OPEN_DATE",
                    severity="CRITICAL",
                    description=f"DOFD ({parsed_dofd}) is before account open date ({opened}). "
                                f"This is a temporal impossibility.",
                    expected_dofd=None,
                    actual_dofd=parsed_dofd,
                    account_status=account_status,
                    event_date=report_date,
                    evidence={
                        "date_opened": opened.isoformat(),
                        "days_before_open": (opened - parsed_dofd).days,
                    }
                ))

        # Check 7-year reporting window
        if parsed_dofd and report_date:
            from dateutil.relativedelta import relativedelta
            seven_years_ago = report_date - relativedelta(years=7)
            if parsed_dofd < seven_years_ago:
                violations.append(DOFDViolation(
                    rule_code="OVER_7_YEAR_REPORTING",
                    severity="HIGH",
                    description=f"Account is being reported beyond 7-year window. "
                                f"DOFD: {parsed_dofd}, Report Date: {report_date}. "
                                f"Account should have fallen off credit reports.",
                    expected_dofd=None,
                    actual_dofd=parsed_dofd,
                    account_status=account_status,
                    event_date=report_date,
                    evidence={
                        "seven_year_window_start": seven_years_ago.isoformat(),
                        "days_over_limit": (seven_years_ago - parsed_dofd).days,
                        "fcra_cite": "15 U.S.C. § 1681c(a)",
                    }
                ))

        return violations

    def get_current_state(self) -> DOFDStateSnapshot:
        """Get current state as a snapshot."""
        return DOFDStateSnapshot(
            state=self.state,
            dofd_value=self.dofd_value,
            dofd_locked=self.dofd_locked,
            locked_date=self.dofd_lock_date,
            account_status="",  # Current status unknown
            snapshot_date=date.today(),
        )

    def reset(self) -> None:
        """Reset the state machine."""
        self.state = DOFDState.CURRENT
        self.dofd_value = None
        self.dofd_locked = False
        self.dofd_lock_date = None
        self.original_dofd = None
        self.history = []
        self.violations = []


def validate_dofd(
    account_status: str,
    dofd: Any,
    account_type: Optional[str] = None,
    date_opened: Optional[date] = None,
    report_date: Optional[date] = None,
) -> List[DOFDViolation]:
    """
    Convenience function to validate DOFD for a single account snapshot.

    Args:
        account_status: Current account status code
        dofd: DOFD value
        account_type: Metro 2 account type code
        date_opened: Account open date
        report_date: Report date for 7-year calculation

    Returns:
        List of violations detected
    """
    machine = DOFDStateMachine(account_type=account_type, date_opened=date_opened)
    event_date = report_date or date.today()

    # Process single event
    violations = machine.process_event(
        event_type=DOFDEventType.STATUS_CHANGE,
        event_date=event_date,
        account_status=account_status,
        dofd=dofd,
    )

    # Add timeline validations
    violations.extend(machine.validate_dofd_timeline(
        account_status=account_status,
        dofd=dofd,
        date_opened=date_opened,
        report_date=report_date,
    ))

    return violations
