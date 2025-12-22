"""
Credit Engine 2.0 - Goal-Oriented Copilot Engine Data Models

MANDATORY CONSTRAINTS:
1. NO SOL LOGIC - Zero statute-of-limitations reasoning. Copilot never reasons about SOL.
2. FCRA-native skip codes only
3. Impact = goal-relative (not severity-relative)
4. Two dependency gates before scoring
5. Employment = zero public records required
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Literal
from uuid import uuid4


# =============================================================================
# ENUMS
# =============================================================================

class CreditGoal(str, Enum):
    """User's financial goal that determines enforcement strategy."""
    MORTGAGE = "mortgage"
    AUTO_LOAN = "auto_loan"
    PRIME_CREDIT_CARD = "prime_credit_card"
    APARTMENT_RENTAL = "apartment_rental"
    EMPLOYMENT = "employment"
    CREDIT_HYGIENE = "credit_hygiene"  # Default - general cleanup


class SkipCode(str, Enum):
    """
    FCRA-native skip codes ONLY.

    NO SOL LOGIC. Copilot never reasons about statute of limitations.
    These codes explain why an item should NOT be attacked.
    """
    DOFD_UNSTABLE = "DOFD_UNSTABLE"
    REINSERTION_LIKELY = "REINSERTION_LIKELY"
    POSITIVE_LINE_LOSS = "POSITIVE_LINE_LOSS"
    UTILIZATION_SHOCK = "UTILIZATION_SHOCK"
    TACTICAL_VERIFICATION_RISK = "TACTICAL_VERIFICATION_RISK"


class ActionType(str, Enum):
    """Types of enforcement actions the Copilot can recommend."""
    DELETE_DEMAND = "DELETE_DEMAND"
    CORRECT_DEMAND = "CORRECT_DEMAND"
    MOV_DEMAND = "MOV_DEMAND"  # Method of Verification demand
    OWNERSHIP_CHAIN_DEMAND = "OWNERSHIP_CHAIN_DEMAND"
    DOFD_DEMAND = "DOFD_DEMAND"
    INQUIRY_DISPUTE = "INQUIRY_DISPUTE"
    DEFER = "DEFER"


class DeletabilityLevel(str, Enum):
    """Likelihood that attacking this item results in deletion."""
    LOW = "LOW"      # 0.2 weight
    MEDIUM = "MEDIUM"  # 0.6 weight
    HIGH = "HIGH"    # 1.0 weight


# Numeric weights for deletability scoring
DELETABILITY_WEIGHTS: Dict[str, float] = {
    "LOW": 0.2,
    "MEDIUM": 0.6,
    "HIGH": 1.0,
}


# =============================================================================
# GOAL DESCRIPTIONS (for UI)
# =============================================================================

GOAL_DESCRIPTIONS: Dict[CreditGoal, Dict[str, str]] = {
    CreditGoal.MORTGAGE: {
        "name": "Mortgage Pre-qualification",
        "description": "Prepare for home purchase or refinance. Strictest requirements.",
    },
    CreditGoal.AUTO_LOAN: {
        "name": "Auto Loan Approval",
        "description": "Prepare for vehicle financing. Moderate requirements.",
    },
    CreditGoal.PRIME_CREDIT_CARD: {
        "name": "Prime Credit Card",
        "description": "Qualify for rewards cards and low APR offers.",
    },
    CreditGoal.APARTMENT_RENTAL: {
        "name": "Apartment Rental",
        "description": "Pass rental application screening.",
    },
    CreditGoal.EMPLOYMENT: {
        "name": "Employment Screening",
        "description": "Prepare for employer background checks. Zero public records required.",
    },
    CreditGoal.CREDIT_HYGIENE: {
        "name": "General Credit Hygiene",
        "description": "Clean up and optimize your credit profile. Default mode.",
    },
}


# =============================================================================
# TARGET CREDIT STATE
# =============================================================================

@dataclass(frozen=True)
class TargetCreditState:
    """
    Target credit profile requirements for a given goal.

    Each goal maps to specific requirements. The Copilot uses these
    to determine what "blocks" the goal and what doesn't matter.
    """
    goal: CreditGoal

    # Composition requirements
    open_tradelines_min: int = 0
    revolving_min: int = 0
    installment_min: int = 0

    # Age requirements
    oldest_trade_min_months: int = 0
    avg_trade_min_months: int = 0

    # Utilization bands (informational - we don't control balances)
    overall_util_max: float = 1.0      # 1.0 = 100%
    per_card_util_max: float = 1.0     # 1.0 = 100%

    # Negative tolerance
    collections_allowed: int = 999
    chargeoffs_allowed: int = 999
    lates_24mo_allowed: int = 999

    # Public records (EMPLOYMENT CRITICAL)
    public_records_allowed: int = 999  # Employment = 0

    # Inquiry sensitivity
    hard_inquiries_12mo_max: int = 999
    hard_inquiries_6mo_max: int = 999

    # Hard blockers (deterministic switches)
    zero_collection_required: bool = False
    zero_chargeoff_required: bool = False
    zero_public_records_required: bool = False  # EMPLOYMENT = True
    zero_recent_lates_required: bool = False


# =============================================================================
# GOAL REQUIREMENTS MAPPING
# =============================================================================

GOAL_REQUIREMENTS: Dict[CreditGoal, TargetCreditState] = {
    CreditGoal.MORTGAGE: TargetCreditState(
        goal=CreditGoal.MORTGAGE,
        open_tradelines_min=4,
        revolving_min=2,
        installment_min=1,
        oldest_trade_min_months=24,
        avg_trade_min_months=18,
        overall_util_max=0.25,
        per_card_util_max=0.30,
        collections_allowed=0,
        chargeoffs_allowed=0,
        lates_24mo_allowed=0,
        public_records_allowed=0,
        hard_inquiries_12mo_max=2,
        hard_inquiries_6mo_max=1,
        zero_collection_required=True,
        zero_chargeoff_required=True,
        zero_public_records_required=True,
        zero_recent_lates_required=True,
    ),
    CreditGoal.AUTO_LOAN: TargetCreditState(
        goal=CreditGoal.AUTO_LOAN,
        open_tradelines_min=3,
        revolving_min=1,
        installment_min=1,
        oldest_trade_min_months=12,
        avg_trade_min_months=9,
        overall_util_max=0.35,
        per_card_util_max=0.50,
        collections_allowed=1,
        chargeoffs_allowed=0,
        lates_24mo_allowed=2,
        public_records_allowed=0,
        hard_inquiries_12mo_max=4,
        hard_inquiries_6mo_max=2,
        zero_chargeoff_required=True,
        zero_public_records_required=True,
    ),
    CreditGoal.PRIME_CREDIT_CARD: TargetCreditState(
        goal=CreditGoal.PRIME_CREDIT_CARD,
        open_tradelines_min=3,
        revolving_min=2,
        installment_min=0,
        oldest_trade_min_months=12,
        avg_trade_min_months=9,
        overall_util_max=0.20,
        per_card_util_max=0.30,
        collections_allowed=0,
        chargeoffs_allowed=0,
        lates_24mo_allowed=1,
        public_records_allowed=0,
        hard_inquiries_12mo_max=3,
        hard_inquiries_6mo_max=2,
        zero_collection_required=True,
        zero_chargeoff_required=True,
        zero_public_records_required=True,
    ),
    CreditGoal.APARTMENT_RENTAL: TargetCreditState(
        goal=CreditGoal.APARTMENT_RENTAL,
        open_tradelines_min=2,
        revolving_min=1,
        installment_min=0,
        oldest_trade_min_months=6,
        avg_trade_min_months=6,
        overall_util_max=0.50,
        per_card_util_max=0.70,
        collections_allowed=1,
        chargeoffs_allowed=1,
        lates_24mo_allowed=3,
        public_records_allowed=1,
        hard_inquiries_12mo_max=5,
        hard_inquiries_6mo_max=3,
    ),
    CreditGoal.EMPLOYMENT: TargetCreditState(
        goal=CreditGoal.EMPLOYMENT,
        # Employment checks are name-based + public record-sensitive
        open_tradelines_min=0,
        revolving_min=0,
        installment_min=0,
        oldest_trade_min_months=0,
        avg_trade_min_months=0,
        overall_util_max=1.0,
        per_card_util_max=1.0,
        collections_allowed=0,
        chargeoffs_allowed=1,
        lates_24mo_allowed=999,  # Lates don't typically block employment
        # CRITICAL: Zero public records (judgments, liens, bankruptcies)
        public_records_allowed=0,
        hard_inquiries_12mo_max=999,  # Inquiries don't matter
        hard_inquiries_6mo_max=999,
        zero_collection_required=True,
        zero_public_records_required=True,  # CRITICAL
    ),
    CreditGoal.CREDIT_HYGIENE: TargetCreditState(
        goal=CreditGoal.CREDIT_HYGIENE,
        # Default mode - optimize everything, no hard blockers
        open_tradelines_min=0,
        revolving_min=0,
        installment_min=0,
        oldest_trade_min_months=0,
        avg_trade_min_months=0,
        overall_util_max=1.0,
        per_card_util_max=1.0,
        collections_allowed=999,
        chargeoffs_allowed=999,
        lates_24mo_allowed=999,
        public_records_allowed=999,
        hard_inquiries_12mo_max=999,
        hard_inquiries_6mo_max=999,
    ),
}


# =============================================================================
# BLOCKER
# =============================================================================

@dataclass
class Blocker:
    """
    Represents a violation/contradiction blocking the user's goal.

    Impact scoring is GOAL-RELATIVE, not severity-relative.
    A $200 collection blocks mortgage more than a $20k chargeoff blocks apartment.
    """
    # Source identification
    source_type: Literal["VIOLATION", "CONTRADICTION"]
    source_id: str  # Stable identifier from audit system

    # Account reference
    account_id: Optional[str] = None
    creditor_name: Optional[str] = None
    account_number_masked: Optional[str] = None
    bureau: Optional[str] = None  # EXP/EQ/TU

    # Classification
    title: str = ""
    description: str = ""
    category: str = ""  # collection, chargeoff, late, inquiry, public_record
    rule_code: Optional[str] = None  # T1, D1, M2, etc.

    # Goal-blocking assessment
    blocks_goal: bool = True

    # Scoring inputs (1-10 impact, 0-5 risk)
    impact_score: int = 5  # GOAL-RELATIVE, not severity
    deletability: str = "MEDIUM"  # LOW, MEDIUM, HIGH
    risk_score: int = 0  # 0-5

    # Dependency gate flags
    dofd_unstable: bool = False
    requires_ownership_first: bool = False
    gate_priority: int = 50  # 1 = must resolve first, 99 = suppressed

    # Context flags
    furnisher_type: Optional[str] = None  # ORIGINAL_CREDITOR, COLLECTION, DEBT_BUYER
    has_original_creditor: bool = True
    is_positive: bool = False
    is_derogatory: bool = True
    is_revolving: bool = False
    credit_limit: Optional[float] = None
    reinsertion_risk: bool = False

    # Explainability
    risk_factors: List[str] = field(default_factory=list)
    proof_hints: List[str] = field(default_factory=list)


# =============================================================================
# ENFORCEMENT ACTION
# =============================================================================

@dataclass
class EnforcementAction:
    """
    A prioritized action in the attack plan.

    Priority formula: impact × deletability ÷ (1 + risk)

    Scales:
    - impact: 1-10 (goal-relative)
    - deletability: 0.2/0.6/1.0 (LOW/MEDIUM/HIGH)
    - risk: 0-5
    """
    action_id: str = field(default_factory=lambda: str(uuid4()))

    # Links to blocker
    blocker_source_id: str = ""
    account_id: Optional[str] = None
    creditor_name: Optional[str] = None

    # Action specification
    action_type: ActionType = ActionType.DEFER
    response_posture: Optional[str] = None  # VERIFIED, REJECTED, NO_RESPONSE, REINSERTION

    # Priority scoring
    priority_score: float = 0.0
    impact_score: int = 5
    deletability: str = "MEDIUM"
    risk_score: int = 0

    # Sequencing
    sequence_order: int = 0
    depends_on: List[str] = field(default_factory=list)  # Action IDs that must complete first

    # Explainability
    rationale: str = ""


# =============================================================================
# SKIP RATIONALE
# =============================================================================

@dataclass
class SkipRationale:
    """
    Explanation for why a blocker should NOT be attacked.

    ONLY FCRA-native reasons. NO SOL LOGIC.
    """
    source_id: str
    account_id: Optional[str] = None
    creditor_name: Optional[str] = None
    code: SkipCode = SkipCode.DOFD_UNSTABLE
    rationale: str = ""


# Skip code descriptions for UI/letters
SKIP_CODE_DESCRIPTIONS: Dict[SkipCode, str] = {
    SkipCode.DOFD_UNSTABLE: "DOFD is missing or unstable; attacking may refresh/re-age the account",
    SkipCode.REINSERTION_LIKELY: "High probability item returns after deletion; strengthen proof first",
    SkipCode.POSITIVE_LINE_LOSS: "Attacking removes positive tradeline age/limit; utilization impact",
    SkipCode.UTILIZATION_SHOCK: "Deleting this revolving line spikes overall utilization",
    SkipCode.TACTICAL_VERIFICATION_RISK: "May force 'verified with updated fields' outcome; wait for stronger posture",
}


# =============================================================================
# COPILOT RECOMMENDATION (Main Output)
# =============================================================================

@dataclass
class CopilotRecommendation:
    """
    Complete copilot analysis and prioritized enforcement plan.

    This is the main output of the Copilot Engine.
    """
    recommendation_id: str = field(default_factory=lambda: str(uuid4()))
    user_id: Optional[str] = None
    report_id: Optional[str] = None
    generated_at: datetime = field(default_factory=datetime.utcnow)

    # Execution Ledger correlation ID
    # Generated at Copilot decision time, passed to Response Engine, Ledger,
    # Bureau intake, and Re-audit diffing. Survives suppressions, retries,
    # silent updates, and delayed responses.
    dispute_session_id: Optional[str] = None

    # Goal and target state
    goal: CreditGoal = CreditGoal.CREDIT_HYGIENE
    target_state: Optional[TargetCreditState] = None

    # Analysis summary
    current_gap_summary: str = ""  # "3 collections, 2 chargeoffs blocking mortgage"
    goal_achievability: str = "UNKNOWN"  # ACHIEVABLE, CHALLENGING, UNLIKELY

    # Blockers
    blockers: List[Blocker] = field(default_factory=list)
    hard_blocker_count: int = 0
    soft_blocker_count: int = 0

    # Attack plan (ordered by priority)
    actions: List[EnforcementAction] = field(default_factory=list)

    # Skip list (with rationale)
    skips: List[SkipRationale] = field(default_factory=list)

    # Sequencing
    sequencing_rationale: str = ""
    dofd_gate_active: bool = False
    ownership_gate_active: bool = False

    # Notes/warnings
    notes: List[str] = field(default_factory=list)
