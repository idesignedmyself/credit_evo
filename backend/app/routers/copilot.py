"""
Credit Engine 2.0 - Copilot API Router

Goal-Oriented Credit Copilot Engine endpoints.
Translates user financial goals into prioritized enforcement strategies.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..database import get_db
from ..models.db_models import UserDB, ReportDB, AuditResultDB
from ..models.copilot_models import (
    CreditGoal,
    GOAL_DESCRIPTIONS,
    GOAL_REQUIREMENTS,
    CopilotRecommendation,
    TargetCreditState,
    Blocker,
    EnforcementAction,
    SkipRationale,
)
from ..services.copilot.copilot_engine import CopilotEngine
from .auth import get_current_user

import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/copilot", tags=["copilot"])


# =============================================================================
# RESPONSE MODELS
# =============================================================================

class GoalInfo(BaseModel):
    """Information about a credit goal."""
    code: str
    name: str
    description: str


class GoalsListResponse(BaseModel):
    """List of available credit goals."""
    goals: List[GoalInfo]


class TargetStateResponse(BaseModel):
    """Target credit state requirements for a goal."""
    goal: str
    open_tradelines_min: int
    revolving_min: int
    installment_min: int
    oldest_trade_min_months: int
    avg_trade_min_months: int
    overall_util_max: float
    per_card_util_max: float
    collections_allowed: int
    chargeoffs_allowed: int
    lates_24mo_allowed: int
    public_records_allowed: int
    hard_inquiries_12mo_max: int
    hard_inquiries_6mo_max: int
    zero_collection_required: bool
    zero_chargeoff_required: bool
    zero_public_records_required: bool
    zero_recent_lates_required: bool


class BlockerResponse(BaseModel):
    """Blocker information for API response."""
    source_type: str
    source_id: str
    account_id: Optional[str] = None
    creditor_name: Optional[str] = None
    bureau: Optional[str] = None
    title: str
    description: str
    category: str
    blocks_goal: bool
    impact_score: int
    deletability: str
    risk_score: int
    dofd_unstable: bool
    requires_ownership_first: bool
    risk_factors: List[str]


class ActionResponse(BaseModel):
    """Enforcement action for API response."""
    action_id: str
    blocker_source_id: str
    account_id: Optional[str] = None
    creditor_name: Optional[str] = None
    action_type: str
    response_posture: Optional[str] = None
    priority_score: float
    sequence_order: int
    rationale: str


class SkipResponse(BaseModel):
    """Skip rationale for API response."""
    source_id: str
    account_id: Optional[str] = None
    creditor_name: Optional[str] = None
    code: str
    rationale: str


class RecommendationResponse(BaseModel):
    """Full copilot recommendation response."""
    recommendation_id: str
    user_id: Optional[str] = None
    report_id: Optional[str] = None
    goal: str
    target_state: TargetStateResponse
    current_gap_summary: str
    goal_achievability: str
    hard_blocker_count: int
    soft_blocker_count: int
    blockers: List[BlockerResponse]
    actions: List[ActionResponse]
    skips: List[SkipResponse]
    sequencing_rationale: str
    dofd_gate_active: bool
    ownership_gate_active: bool
    notes: List[str]


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/goals", response_model=GoalsListResponse)
async def get_available_goals():
    """
    Get all available credit goals with descriptions.
    """
    goals = []
    for goal in CreditGoal:
        info = GOAL_DESCRIPTIONS.get(goal, {"name": goal.value, "description": ""})
        goals.append(GoalInfo(
            code=goal.value,
            name=info["name"],
            description=info["description"]
        ))
    return GoalsListResponse(goals=goals)


@router.get("/goals/{goal_code}/requirements", response_model=TargetStateResponse)
async def get_goal_requirements(goal_code: str):
    """
    Get target credit state requirements for a specific goal.
    """
    try:
        goal = CreditGoal(goal_code.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid goal code. Must be one of: {', '.join(g.value for g in CreditGoal)}"
        )

    target = GOAL_REQUIREMENTS.get(goal)
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No requirements found for goal: {goal_code}"
        )

    return TargetStateResponse(
        goal=target.goal.value,
        open_tradelines_min=target.open_tradelines_min,
        revolving_min=target.revolving_min,
        installment_min=target.installment_min,
        oldest_trade_min_months=target.oldest_trade_min_months,
        avg_trade_min_months=target.avg_trade_min_months,
        overall_util_max=target.overall_util_max,
        per_card_util_max=target.per_card_util_max,
        collections_allowed=target.collections_allowed,
        chargeoffs_allowed=target.chargeoffs_allowed,
        lates_24mo_allowed=target.lates_24mo_allowed,
        public_records_allowed=target.public_records_allowed,
        hard_inquiries_12mo_max=target.hard_inquiries_12mo_max,
        hard_inquiries_6mo_max=target.hard_inquiries_6mo_max,
        zero_collection_required=target.zero_collection_required,
        zero_chargeoff_required=target.zero_chargeoff_required,
        zero_public_records_required=target.zero_public_records_required,
        zero_recent_lates_required=target.zero_recent_lates_required,
    )


@router.get("/recommendation/{report_id}", response_model=RecommendationResponse)
async def get_recommendation(
    report_id: str,
    goal: Optional[str] = None,
    current_user: UserDB = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate copilot recommendation for a report.

    Uses user's saved credit_goal if not overridden via query param.
    """
    # Verify report belongs to user
    report = db.query(ReportDB).filter(
        ReportDB.id == report_id,
        ReportDB.user_id == current_user.id
    ).first()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found or access denied"
        )

    # Determine goal - use query param, or user's saved goal, or default
    goal_str = goal or current_user.credit_goal or "credit_hygiene"
    try:
        credit_goal = CreditGoal(goal_str.lower())
    except ValueError:
        credit_goal = CreditGoal.CREDIT_HYGIENE

    # Get violations from AuditResultDB (where they're actually stored)
    audit_result = db.query(AuditResultDB).filter(
        AuditResultDB.report_id == report_id
    ).first()

    violations = []
    contradictions = []

    if audit_result:
        # Violations are stored in violations_data JSON column
        violations = audit_result.violations_data or []
        # Discrepancies/contradictions stored in discrepancies_data
        contradictions = audit_result.discrepancies_data or []
    else:
        logger.warning(f"No audit result found for report {report_id}")

    logger.info(f"Copilot analyzing {len(violations)} violations, {len(contradictions)} contradictions for goal {credit_goal.value}")

    # Run copilot analysis
    engine = CopilotEngine()
    recommendation = engine.analyze(
        goal=credit_goal,
        violations=violations,
        contradictions=contradictions,
        user_id=current_user.id,
        report_id=report_id,
    )

    # Convert to response format
    return _recommendation_to_response(recommendation)


@router.post("/analyze")
async def analyze_with_data(
    goal: str,
    violations: Optional[List[dict]] = None,
    contradictions: Optional[List[dict]] = None,
    current_user: UserDB = Depends(get_current_user),
):
    """
    Run copilot analysis with provided data.

    This endpoint allows direct analysis without requiring a stored report.
    Useful for testing or real-time analysis.
    """
    try:
        credit_goal = CreditGoal(goal.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid goal. Must be one of: {', '.join(g.value for g in CreditGoal)}"
        )

    engine = CopilotEngine()
    recommendation = engine.analyze(
        goal=credit_goal,
        violations=violations or [],
        contradictions=contradictions or [],
        user_id=current_user.id,
    )

    return _recommendation_to_response(recommendation)


# =============================================================================
# OVERRIDE LOGGING
# =============================================================================

class OverrideRequest(BaseModel):
    """Request to log a user override of Copilot advice."""
    dispute_session_id: str
    copilot_version_id: str  # REQUIRED - version hash of the recommendation
    report_id: str
    violation_id: Optional[str] = None
    copilot_advice: str  # 'skip' | 'defer' | 'advised_against'
    user_action: str  # 'proceed' | 'include'


@router.post("/override")
async def log_copilot_override(
    request: OverrideRequest,
    current_user: UserDB = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Log when user proceeds against Copilot advice.

    This creates a suppression event in the Execution Ledger with
    reason USER_OVERRIDE. This allows tracking of user decisions
    against Copilot recommendations for:
    - Analytics and model improvement
    - Audit trail for compliance
    - User decision history

    Note: This endpoint never blocks the user - it only logs.
    """
    from ..models.db_models import SuppressionReason
    from ..services.enforcement import ExecutionLedgerService

    ledger = ExecutionLedgerService(db)

    # Log the override as a suppression event
    # Note: Using suppression event since user is suppressing Copilot's advice
    ledger.emit_suppression_event(
        dispute_session_id=request.dispute_session_id,
        user_id=current_user.id,
        suppression_reason=SuppressionReason.USER_OVERRIDE,
        credit_goal=current_user.credit_goal or "credit_hygiene",
        report_id=request.report_id,
        account_id=request.violation_id,  # Store violation_id in account_id field
    )

    db.commit()

    logger.info(
        f"User {current_user.id} overrode Copilot advice for "
        f"violation {request.violation_id} (advice: {request.copilot_advice})"
    )

    return {"status": "logged", "override_id": request.dispute_session_id}


# =============================================================================
# HELPERS
# =============================================================================

def _recommendation_to_response(rec: CopilotRecommendation) -> RecommendationResponse:
    """Convert CopilotRecommendation to API response format."""
    # Convert target state
    target = rec.target_state
    target_response = TargetStateResponse(
        goal=target.goal.value if target else "credit_hygiene",
        open_tradelines_min=target.open_tradelines_min if target else 0,
        revolving_min=target.revolving_min if target else 0,
        installment_min=target.installment_min if target else 0,
        oldest_trade_min_months=target.oldest_trade_min_months if target else 0,
        avg_trade_min_months=target.avg_trade_min_months if target else 0,
        overall_util_max=target.overall_util_max if target else 1.0,
        per_card_util_max=target.per_card_util_max if target else 1.0,
        collections_allowed=target.collections_allowed if target else 999,
        chargeoffs_allowed=target.chargeoffs_allowed if target else 999,
        lates_24mo_allowed=target.lates_24mo_allowed if target else 999,
        public_records_allowed=target.public_records_allowed if target else 999,
        hard_inquiries_12mo_max=target.hard_inquiries_12mo_max if target else 999,
        hard_inquiries_6mo_max=target.hard_inquiries_6mo_max if target else 999,
        zero_collection_required=target.zero_collection_required if target else False,
        zero_chargeoff_required=target.zero_chargeoff_required if target else False,
        zero_public_records_required=target.zero_public_records_required if target else False,
        zero_recent_lates_required=target.zero_recent_lates_required if target else False,
    )

    # Convert blockers
    blockers = [
        BlockerResponse(
            source_type=b.source_type,
            source_id=b.source_id,
            account_id=b.account_id,
            creditor_name=b.creditor_name,
            bureau=b.bureau,
            title=b.title,
            description=b.description,
            category=b.category,
            blocks_goal=b.blocks_goal,
            impact_score=b.impact_score,
            deletability=b.deletability,
            risk_score=b.risk_score,
            dofd_unstable=b.dofd_unstable,
            requires_ownership_first=b.requires_ownership_first,
            risk_factors=b.risk_factors,
        )
        for b in rec.blockers
    ]

    # Convert actions
    actions = [
        ActionResponse(
            action_id=a.action_id,
            blocker_source_id=a.blocker_source_id,
            account_id=a.account_id,
            creditor_name=a.creditor_name,
            action_type=a.action_type.value,
            response_posture=a.response_posture,
            priority_score=a.priority_score,
            sequence_order=a.sequence_order,
            rationale=a.rationale,
        )
        for a in rec.actions
    ]

    # Convert skips
    skips = [
        SkipResponse(
            source_id=s.source_id,
            account_id=s.account_id,
            creditor_name=s.creditor_name,
            code=s.code.value,
            rationale=s.rationale,
        )
        for s in rec.skips
    ]

    return RecommendationResponse(
        recommendation_id=rec.recommendation_id,
        user_id=rec.user_id,
        report_id=rec.report_id,
        goal=rec.goal.value,
        target_state=target_response,
        current_gap_summary=rec.current_gap_summary,
        goal_achievability=rec.goal_achievability,
        hard_blocker_count=rec.hard_blocker_count,
        soft_blocker_count=rec.soft_blocker_count,
        blockers=blockers,
        actions=actions,
        skips=skips,
        sequencing_rationale=rec.sequencing_rationale,
        dofd_gate_active=rec.dofd_gate_active,
        ownership_gate_active=rec.ownership_gate_active,
        notes=rec.notes,
    )
