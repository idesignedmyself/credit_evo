"""
Credit Engine 2.0 - Single Source of Truth Models

These models are the ONLY data structures used throughout the pipeline.
No module may reference raw data after parsing.
No module may recompute logic from upstream SSOTs.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from uuid import uuid4


# =============================================================================
# ENUMS
# =============================================================================

class Bureau(str, Enum):
    TRANSUNION = "transunion"
    EXPERIAN = "experian"
    EQUIFAX = "equifax"


class FurnisherType(str, Enum):
    """SSOT for furnisher classification - once set, cannot be changed downstream."""
    COLLECTOR = "collector"
    OC_CHARGEOFF = "oc_chargeoff"
    OC_NON_CHARGEOFF = "oc_non_chargeoff"
    UNKNOWN = "unknown"


class AccountStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    PAID = "paid"
    CHARGEOFF = "chargeoff"
    COLLECTION = "collection"
    DEROGATORY = "derogatory"
    UNKNOWN = "unknown"


class ViolationType(str, Enum):
    # Single-bureau violations
    MISSING_DOFD = "missing_dofd"
    MISSING_DATE_OPENED = "missing_date_opened"
    MISSING_DLA = "missing_dla"
    MISSING_PAYMENT_STATUS = "missing_payment_status"
    MISSING_SCHEDULED_PAYMENT = "missing_scheduled_payment"
    MISSING_ORIGINAL_CREDITOR = "missing_original_creditor"  # NEW
    NEGATIVE_BALANCE = "negative_balance"
    NEGATIVE_CREDIT_LIMIT = "negative_credit_limit"  # NEW
    PAST_DUE_EXCEEDS_BALANCE = "past_due_exceeds_balance"
    BALANCE_EXCEEDS_HIGH_CREDIT = "balance_exceeds_high_credit"  # NEW
    FUTURE_DATE = "future_date"
    DOFD_AFTER_DATE_OPENED = "dofd_after_date_opened"
    INVALID_METRO2_CODE = "invalid_metro2_code"
    CLOSED_OC_REPORTING_BALANCE = "closed_oc_reporting_balance"
    CLOSED_OC_REPORTING_PAST_DUE = "closed_oc_reporting_past_due"  # NEW
    CHARGEOFF_MISSING_DOFD = "chargeoff_missing_dofd"  # NEW

    # Cross-bureau violations
    DOFD_MISMATCH = "dofd_mismatch"
    DATE_OPENED_MISMATCH = "date_opened_mismatch"
    BALANCE_MISMATCH = "balance_mismatch"
    STATUS_MISMATCH = "status_mismatch"
    PAYMENT_HISTORY_MISMATCH = "payment_history_mismatch"
    PAST_DUE_MISMATCH = "past_due_mismatch"
    CLOSED_VS_OPEN_CONFLICT = "closed_vs_open_conflict"
    CREDITOR_NAME_MISMATCH = "creditor_name_mismatch"
    ACCOUNT_NUMBER_MISMATCH = "account_number_mismatch"

    # Temporal violations
    STALE_REPORTING = "stale_reporting"
    RE_AGING = "re_aging"
    DOFD_REPLACED_WITH_DATE_OPENED = "dofd_replaced_with_date_opened"
    IMPOSSIBLE_TIMELINE = "impossible_timeline"
    OBSOLETE_ACCOUNT = "obsolete_account"


class Severity(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Tone(str, Enum):
    FORMAL = "formal"
    CONVERSATIONAL = "conversational"
    ASSERTIVE = "assertive"
    NARRATIVE = "narrative"


# =============================================================================
# SSOT #1: NORMALIZED REPORT (Output of Parsing Layer)
# =============================================================================

@dataclass
class Consumer:
    """Consumer personal information."""
    full_name: str
    address: str
    city: str
    state: str
    zip_code: str
    ssn_last4: Optional[str] = None
    date_of_birth: Optional[date] = None


@dataclass
class BureauAccountData:
    """Bureau-specific data for a single account."""
    bureau: Bureau = Bureau.TRANSUNION

    # Key dates
    date_opened: Optional[date] = None
    date_closed: Optional[date] = None
    date_of_first_delinquency: Optional[date] = None
    date_last_activity: Optional[date] = None
    date_last_payment: Optional[date] = None
    date_reported: Optional[date] = None

    # Balances
    balance: Optional[float] = None
    credit_limit: Optional[float] = None
    high_credit: Optional[float] = None
    past_due_amount: Optional[float] = None
    scheduled_payment: Optional[float] = None
    monthly_payment: Optional[float] = None

    # Status
    payment_status: Optional[str] = None
    payment_pattern: Optional[str] = None
    account_status_raw: Optional[str] = None
    remarks: Optional[str] = None

    # Raw HTML for debugging
    raw_html: Optional[str] = None


@dataclass
class Account:
    """
    Single tradeline account - fully normalized.

    NEW MODEL: Each Account represents ONE canonical tradeline.
    Bureau-specific data is stored in the `bureaus` dict.
    This gives us 31 accounts instead of 63 bureau-duplicated records.
    """
    account_id: str = field(default_factory=lambda: str(uuid4()))
    creditor_name: str = ""
    original_creditor: Optional[str] = None
    account_number: str = ""
    account_number_masked: str = ""

    # Classification (SSOT - once set, final)
    furnisher_type: FurnisherType = FurnisherType.UNKNOWN
    account_status: AccountStatus = AccountStatus.UNKNOWN
    account_type: Optional[str] = None

    # Bureau-specific data (TU/EX/EQ merged into one Account)
    # Key is Bureau enum, value is BureauAccountData
    bureaus: Dict[Bureau, BureauAccountData] = field(default_factory=dict)

    # LEGACY FIELDS - kept for backward compatibility with existing code
    # These are populated from the "primary" bureau (first one with data)
    bureau: Bureau = Bureau.TRANSUNION  # Primary bureau for this account

    # Key dates (legacy - use bureaus[bureau].date_* for bureau-specific)
    date_opened: Optional[date] = None
    date_closed: Optional[date] = None
    date_of_first_delinquency: Optional[date] = None
    date_last_activity: Optional[date] = None
    date_last_payment: Optional[date] = None
    date_reported: Optional[date] = None

    # Balances (legacy - use bureaus[bureau].* for bureau-specific)
    balance: Optional[float] = None
    credit_limit: Optional[float] = None
    high_credit: Optional[float] = None
    past_due_amount: Optional[float] = None
    current_balance: Optional[float] = None
    scheduled_payment: Optional[float] = None
    monthly_payment: Optional[float] = None

    # Status codes (legacy)
    payment_status: Optional[str] = None
    payment_pattern: Optional[str] = None

    # Raw data for reference
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def get_bureau_data(self, bureau: Bureau) -> Optional[BureauAccountData]:
        """Get data for a specific bureau."""
        return self.bureaus.get(bureau)

    def has_bureau(self, bureau: Bureau) -> bool:
        """Check if account has data for a specific bureau."""
        return bureau in self.bureaus

    @property
    def bureau_count(self) -> int:
        """Number of bureaus reporting this account."""
        return len(self.bureaus)


@dataclass
class Inquiry:
    """Credit inquiry."""
    inquiry_id: str = field(default_factory=lambda: str(uuid4()))
    creditor_name: str = ""
    inquiry_date: Optional[date] = None
    inquiry_type: str = ""  # hard/soft


@dataclass
class PublicRecord:
    """Public record entry."""
    record_id: str = field(default_factory=lambda: str(uuid4()))
    record_type: str = ""  # bankruptcy, judgment, lien
    filed_date: Optional[date] = None
    court_name: Optional[str] = None
    amount: Optional[float] = None
    status: Optional[str] = None


@dataclass
class NormalizedReport:
    """
    SSOT #1: The single source of truth for all parsed data.

    All downstream modules MUST use this and ONLY this.
    No module may reference raw PDFs/HTML after this is created.
    """
    report_id: str = field(default_factory=lambda: str(uuid4()))
    consumer: Consumer = field(default_factory=lambda: Consumer("", "", "", "", ""))
    bureau: Bureau = Bureau.TRANSUNION
    report_date: date = field(default_factory=date.today)

    accounts: List[Account] = field(default_factory=list)
    inquiries: List[Inquiry] = field(default_factory=list)
    public_records: List[PublicRecord] = field(default_factory=list)

    # Metadata
    parse_timestamp: datetime = field(default_factory=datetime.now)
    source_file: Optional[str] = None


# =============================================================================
# SSOT #2: AUDIT RESULT (Output of Audit Engine)
# =============================================================================

@dataclass
class Violation:
    """
    SSOT for a single detected violation.

    Letters MUST use this object directly - no recomputation allowed.
    """
    violation_id: str = field(default_factory=lambda: str(uuid4()))
    violation_type: ViolationType = ViolationType.MISSING_DOFD
    severity: Severity = Severity.MEDIUM

    # Account reference
    account_id: str = ""
    creditor_name: str = ""
    account_number_masked: str = ""
    furnisher_type: FurnisherType = FurnisherType.UNKNOWN

    # Bureau where violation was found
    bureau: Bureau = Bureau.TRANSUNION

    # Violation details
    description: str = ""
    expected_value: Optional[str] = None
    actual_value: Optional[str] = None

    # Legal basis
    fcra_section: Optional[str] = None
    metro2_field: Optional[str] = None

    # Evidence for letter generation
    evidence: Dict[str, Any] = field(default_factory=dict)

    # User selection (for consumer-directed disputes)
    selected_for_dispute: bool = True


@dataclass
class CrossBureauDiscrepancy:
    """
    SSOT for a cross-bureau mismatch.

    Letters cannot recompute or reinterpret these.
    """
    discrepancy_id: str = field(default_factory=lambda: str(uuid4()))
    violation_type: ViolationType = ViolationType.BALANCE_MISMATCH

    # Account matching info
    creditor_name: str = ""
    account_fingerprint: str = ""  # For matching across bureaus

    # What differs
    field_name: str = ""
    values_by_bureau: Dict[Bureau, Any] = field(default_factory=dict)

    description: str = ""
    severity: Severity = Severity.MEDIUM


@dataclass
class AuditResult:
    """
    SSOT #2: The single source of truth for all violations and discrepancies.

    Strategy Selector and Renderer MUST use this exclusively.
    No downstream module may re-run audit rules.
    """
    audit_id: str = field(default_factory=lambda: str(uuid4()))
    report_id: str = ""
    bureau: Bureau = Bureau.TRANSUNION

    violations: List[Violation] = field(default_factory=list)
    discrepancies: List[CrossBureauDiscrepancy] = field(default_factory=list)
    clean_accounts: List[str] = field(default_factory=list)  # Account IDs with no issues

    audit_timestamp: datetime = field(default_factory=datetime.now)

    # Summary stats
    total_accounts_audited: int = 0
    total_violations_found: int = 0


# =============================================================================
# SSOT #3: LETTER PLAN (Output of Strategy Selector)
# =============================================================================

@dataclass
class LetterPlan:
    """
    SSOT for letter generation planning.

    Renderer uses this to generate final letters.
    """
    plan_id: str = field(default_factory=lambda: str(uuid4()))
    bureau: Bureau = Bureau.TRANSUNION
    consumer: Consumer = field(default_factory=lambda: Consumer("", "", "", "", ""))

    # Grouped violations for the letter
    grouped_violations: Dict[str, List[Violation]] = field(default_factory=dict)

    # Strategy choices
    grouping_strategy: str = "by_violation_type"  # or "by_creditor", "by_severity"
    variation_seed: int = 0  # SSOT for all stylistic randomness
    tone: Tone = Tone.FORMAL

    # Bureau address
    bureau_address: str = ""


# =============================================================================
# SSOT #4: DISPUTE LETTER (Output of Renderer)
# =============================================================================

@dataclass
class LetterMetadata:
    """Metadata about the generated letter."""
    generated_at: datetime = field(default_factory=datetime.now)
    variation_seed_used: int = 0
    tone_used: Tone = Tone.FORMAL
    template_id: Optional[str] = None
    word_count: int = 0


@dataclass
class DisputeLetter:
    """
    Final output of the rendering pipeline.
    """
    letter_id: str = field(default_factory=lambda: str(uuid4()))
    content: str = ""
    bureau: Bureau = Bureau.TRANSUNION

    accounts_disputed: List[str] = field(default_factory=list)
    violations_cited: List[ViolationType] = field(default_factory=list)

    metadata: LetterMetadata = field(default_factory=LetterMetadata)
