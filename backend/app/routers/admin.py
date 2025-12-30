"""
Credit Engine 2.0 - Admin Router
Read-only intelligence console built on Execution Ledger truth.
Admin observes, correlates, diagnoses - never mutates.
"""
from datetime import datetime, timedelta, timezone
from typing import List, Optional
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, desc, and_
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.db_models import (
    UserDB, ReportDB, LetterDB, DisputeDB,
    ExecutionEventDB, ExecutionResponseDB, ExecutionOutcomeDB,
    ExecutionSuppressionEventDB, SuppressionReason, FinalOutcome,
    PaperTrailDB, EscalationLogDB
)
from ..auth import require_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class DashboardStats(BaseModel):
    """Dashboard statistics response."""
    total_users: int
    active_users_30d: int
    total_letters_sent: int
    letters_sent_30d: int
    total_executions: int
    deletion_rate: float  # Percentage of executions resulting in DELETED
    verification_rate: float  # Percentage of executions resulting in VERIFIED
    override_rate: float  # Percentage of USER_OVERRIDE suppressions
    pending_responses: int


class UserListItem(BaseModel):
    """User item for admin list view."""
    id: str
    email: str
    username: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    credit_goal: Optional[str] = None
    created_at: str
    last_activity: Optional[str] = None
    execution_count: int
    letter_count: int


class UserListResponse(BaseModel):
    """Paginated user list response."""
    users: List[UserListItem]
    total: int
    page: int
    page_size: int


class TimelineEvent(BaseModel):
    """Timeline event for user drilldown."""
    id: str
    event_type: str
    timestamp: str
    description: str
    metadata: Optional[dict] = None


class UserDetailResponse(BaseModel):
    """Detailed user view with timeline."""
    id: str
    email: str
    username: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    credit_goal: Optional[str] = None
    state: Optional[str] = None
    created_at: str
    profile_complete: int
    total_reports: int
    total_letters: int
    total_executions: int
    deletion_rate: float
    override_count: int
    timeline: List[TimelineEvent]


class BureauOutcome(BaseModel):
    """Outcome statistics by bureau."""
    bureau: str
    total_executions: int
    deleted: int
    verified: int
    updated: int
    ignored: int
    deletion_rate: float


class FurnisherOutcome(BaseModel):
    """Outcome statistics by furnisher."""
    furnisher_name: str
    total_executions: int
    deleted: int
    verified: int
    deletion_rate: float


class DisputeIntelResponse(BaseModel):
    """Dispute intelligence analytics response."""
    total_executions: int
    overall_deletion_rate: float
    overall_verification_rate: float
    by_bureau: List[BureauOutcome]
    top_furnishers: List[FurnisherOutcome]


class CopilotMetrics(BaseModel):
    """Copilot performance metrics."""
    total_recommendations: int
    follow_rate: float  # % of recommendations followed
    override_rate: float  # % of recommendations overridden
    followed_deletion_rate: float  # Deletion rate when user followed advice
    overridden_deletion_rate: float  # Deletion rate when user overrode advice
    by_goal: dict  # Metrics broken down by credit goal


# =============================================================================
# API ENDPOINTS
# =============================================================================

@router.get("/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    db: Session = Depends(get_db),
    admin: UserDB = Depends(require_admin)
):
    """
    Get dashboard statistics from Execution Ledger.
    All metrics are derived from immutable ledger data.
    """
    now = datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)

    # User counts
    total_users = db.query(func.count(UserDB.id)).scalar() or 0
    active_users_30d = db.query(func.count(func.distinct(ExecutionEventDB.user_id))).filter(
        ExecutionEventDB.executed_at >= thirty_days_ago
    ).scalar() or 0

    # Letter counts
    total_letters = db.query(func.count(LetterDB.id)).scalar() or 0
    letters_30d = db.query(func.count(LetterDB.id)).filter(
        LetterDB.created_at >= thirty_days_ago
    ).scalar() or 0

    # Execution stats
    total_executions = db.query(func.count(ExecutionEventDB.id)).scalar() or 0

    # Outcome rates
    outcomes = db.query(
        ExecutionOutcomeDB.final_outcome,
        func.count(ExecutionOutcomeDB.id)
    ).group_by(ExecutionOutcomeDB.final_outcome).all()

    outcome_counts = {str(o.value) if o else "UNKNOWN": c for o, c in outcomes}
    total_outcomes = sum(outcome_counts.values()) or 1

    deletion_rate = (outcome_counts.get("DELETED", 0) / total_outcomes) * 100
    verification_rate = (outcome_counts.get("VERIFIED", 0) / total_outcomes) * 100

    # Override rate (USER_OVERRIDE suppressions)
    total_suppressions = db.query(func.count(ExecutionSuppressionEventDB.id)).scalar() or 1
    override_count = db.query(func.count(ExecutionSuppressionEventDB.id)).filter(
        ExecutionSuppressionEventDB.suppression_reason == SuppressionReason.USER_OVERRIDE
    ).scalar() or 0
    override_rate = (override_count / total_suppressions) * 100 if total_suppressions > 0 else 0

    # Pending responses
    pending_responses = db.query(func.count(ExecutionEventDB.id)).filter(
        ExecutionEventDB.execution_status == "PENDING"
    ).scalar() or 0

    return DashboardStats(
        total_users=total_users,
        active_users_30d=active_users_30d,
        total_letters_sent=total_letters,
        letters_sent_30d=letters_30d,
        total_executions=total_executions,
        deletion_rate=round(deletion_rate, 1),
        verification_rate=round(verification_rate, 1),
        override_rate=round(override_rate, 1),
        pending_responses=pending_responses
    )


@router.get("/users", response_model=UserListResponse)
async def get_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    admin: UserDB = Depends(require_admin)
):
    """
    Get paginated list of users with execution metrics.
    """
    query = db.query(UserDB)

    # Search filter
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (UserDB.email.ilike(search_term)) |
            (UserDB.username.ilike(search_term)) |
            (UserDB.first_name.ilike(search_term)) |
            (UserDB.last_name.ilike(search_term))
        )

    # Get total count
    total = query.count()

    # Paginate
    offset = (page - 1) * page_size
    users = query.order_by(desc(UserDB.created_at)).offset(offset).limit(page_size).all()

    # Build response with execution counts
    user_items = []
    for user in users:
        # Get execution count
        exec_count = db.query(func.count(ExecutionEventDB.id)).filter(
            ExecutionEventDB.user_id == user.id
        ).scalar() or 0

        # Get letter count
        letter_count = db.query(func.count(LetterDB.id)).filter(
            LetterDB.user_id == user.id
        ).scalar() or 0

        # Get last activity (most recent execution)
        last_exec = db.query(ExecutionEventDB.executed_at).filter(
            ExecutionEventDB.user_id == user.id
        ).order_by(desc(ExecutionEventDB.executed_at)).first()

        user_items.append(UserListItem(
            id=user.id,
            email=user.email,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            credit_goal=user.credit_goal,
            created_at=user.created_at.isoformat() if user.created_at else "",
            last_activity=last_exec[0].isoformat() if last_exec else None,
            execution_count=exec_count,
            letter_count=letter_count
        ))

    return UserListResponse(
        users=user_items,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/users/{user_id}", response_model=UserDetailResponse)
async def get_user_detail(
    user_id: str,
    db: Session = Depends(get_db),
    admin: UserDB = Depends(require_admin)
):
    """
    Get detailed user view with timeline of all ledger events.
    """
    user = db.query(UserDB).filter(UserDB.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get counts
    total_reports = db.query(func.count(ReportDB.id)).filter(
        ReportDB.user_id == user_id
    ).scalar() or 0

    total_letters = db.query(func.count(LetterDB.id)).filter(
        LetterDB.user_id == user_id
    ).scalar() or 0

    total_executions = db.query(func.count(ExecutionEventDB.id)).filter(
        ExecutionEventDB.user_id == user_id
    ).scalar() or 0

    # Calculate deletion rate for this user
    user_outcomes = db.query(ExecutionOutcomeDB).join(ExecutionEventDB).filter(
        ExecutionEventDB.user_id == user_id
    ).all()

    deleted_count = sum(1 for o in user_outcomes if o.final_outcome == FinalOutcome.DELETED)
    deletion_rate = (deleted_count / len(user_outcomes) * 100) if user_outcomes else 0

    # Override count
    override_count = db.query(func.count(ExecutionSuppressionEventDB.id)).filter(
        ExecutionSuppressionEventDB.user_id == user_id,
        ExecutionSuppressionEventDB.suppression_reason == SuppressionReason.USER_OVERRIDE
    ).scalar() or 0

    # Build timeline from ledger events
    timeline = []

    # Add execution events
    executions = db.query(ExecutionEventDB).filter(
        ExecutionEventDB.user_id == user_id
    ).order_by(desc(ExecutionEventDB.executed_at)).limit(50).all()

    for ex in executions:
        timeline.append(TimelineEvent(
            id=ex.id,
            event_type="EXECUTION",
            timestamp=ex.executed_at.isoformat(),
            description=f"{ex.action_type} sent to {ex.bureau or 'unknown'} for {ex.creditor_name or 'unknown'}",
            metadata={
                "action_type": ex.action_type,
                "bureau": ex.bureau,
                "creditor_name": ex.creditor_name,
                "status": str(ex.execution_status.value) if ex.execution_status else None
            }
        ))

    # Add response events
    responses = db.query(ExecutionResponseDB).join(ExecutionEventDB).filter(
        ExecutionEventDB.user_id == user_id
    ).order_by(desc(ExecutionResponseDB.response_received_at)).limit(50).all()

    for resp in responses:
        timeline.append(TimelineEvent(
            id=resp.id,
            event_type="RESPONSE",
            timestamp=resp.response_received_at.isoformat(),
            description=f"Response received: {resp.response_type}",
            metadata={
                "response_type": resp.response_type,
                "bureau": resp.bureau
            }
        ))

    # Add outcome events
    outcomes = db.query(ExecutionOutcomeDB).join(ExecutionEventDB).filter(
        ExecutionEventDB.user_id == user_id
    ).order_by(desc(ExecutionOutcomeDB.resolved_at)).limit(50).all()

    for outcome in outcomes:
        timeline.append(TimelineEvent(
            id=outcome.id,
            event_type="OUTCOME",
            timestamp=outcome.resolved_at.isoformat(),
            description=f"Final outcome: {outcome.final_outcome.value}",
            metadata={
                "final_outcome": outcome.final_outcome.value,
                "account_removed": outcome.account_removed,
                "durability_score": outcome.durability_score
            }
        ))

    # Add suppression events
    suppressions = db.query(ExecutionSuppressionEventDB).filter(
        ExecutionSuppressionEventDB.user_id == user_id
    ).order_by(desc(ExecutionSuppressionEventDB.suppressed_at)).limit(20).all()

    for sup in suppressions:
        timeline.append(TimelineEvent(
            id=sup.id,
            event_type="SUPPRESSION",
            timestamp=sup.suppressed_at.isoformat(),
            description=f"Action suppressed: {sup.suppression_reason.value}",
            metadata={
                "reason": sup.suppression_reason.value,
                "credit_goal": sup.credit_goal
            }
        ))

    # Sort timeline by timestamp descending
    timeline.sort(key=lambda x: x.timestamp, reverse=True)

    return UserDetailResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        credit_goal=user.credit_goal,
        state=user.state,
        created_at=user.created_at.isoformat() if user.created_at else "",
        profile_complete=user.profile_complete or 0,
        total_reports=total_reports,
        total_letters=total_letters,
        total_executions=total_executions,
        deletion_rate=round(deletion_rate, 1),
        override_count=override_count,
        timeline=timeline[:100]  # Limit to 100 most recent events
    )


@router.get("/intelligence/disputes", response_model=DisputeIntelResponse)
async def get_dispute_intelligence(
    days: int = Query(90, ge=1, le=365),
    db: Session = Depends(get_db),
    admin: UserDB = Depends(require_admin)
):
    """
    Get population-level dispute analytics from Execution Ledger.
    Aggregates outcomes by bureau and furnisher.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    # Get all outcomes in time window
    outcomes = db.query(
        ExecutionEventDB.bureau,
        ExecutionEventDB.creditor_name,
        ExecutionOutcomeDB.final_outcome
    ).join(ExecutionOutcomeDB).filter(
        ExecutionOutcomeDB.resolved_at >= cutoff
    ).all()

    total_executions = len(outcomes)
    if total_executions == 0:
        return DisputeIntelResponse(
            total_executions=0,
            overall_deletion_rate=0,
            overall_verification_rate=0,
            by_bureau=[],
            top_furnishers=[]
        )

    # Overall rates
    deleted_total = sum(1 for o in outcomes if o.final_outcome == FinalOutcome.DELETED)
    verified_total = sum(1 for o in outcomes if o.final_outcome == FinalOutcome.VERIFIED)

    overall_deletion_rate = (deleted_total / total_executions) * 100
    overall_verification_rate = (verified_total / total_executions) * 100

    # By bureau
    bureau_stats = {}
    for o in outcomes:
        bureau = o.bureau or "UNKNOWN"
        if bureau not in bureau_stats:
            bureau_stats[bureau] = {"total": 0, "deleted": 0, "verified": 0, "updated": 0, "ignored": 0}
        bureau_stats[bureau]["total"] += 1
        if o.final_outcome == FinalOutcome.DELETED:
            bureau_stats[bureau]["deleted"] += 1
        elif o.final_outcome == FinalOutcome.VERIFIED:
            bureau_stats[bureau]["verified"] += 1
        elif o.final_outcome == FinalOutcome.UPDATED:
            bureau_stats[bureau]["updated"] += 1
        elif o.final_outcome == FinalOutcome.IGNORED:
            bureau_stats[bureau]["ignored"] += 1

    by_bureau = [
        BureauOutcome(
            bureau=bureau,
            total_executions=stats["total"],
            deleted=stats["deleted"],
            verified=stats["verified"],
            updated=stats["updated"],
            ignored=stats["ignored"],
            deletion_rate=round((stats["deleted"] / stats["total"]) * 100, 1) if stats["total"] > 0 else 0
        )
        for bureau, stats in bureau_stats.items()
    ]

    # By furnisher (top 20)
    furnisher_stats = {}
    for o in outcomes:
        furnisher = o.creditor_name or "UNKNOWN"
        if furnisher not in furnisher_stats:
            furnisher_stats[furnisher] = {"total": 0, "deleted": 0, "verified": 0}
        furnisher_stats[furnisher]["total"] += 1
        if o.final_outcome == FinalOutcome.DELETED:
            furnisher_stats[furnisher]["deleted"] += 1
        elif o.final_outcome == FinalOutcome.VERIFIED:
            furnisher_stats[furnisher]["verified"] += 1

    top_furnishers = sorted(
        [
            FurnisherOutcome(
                furnisher_name=name,
                total_executions=stats["total"],
                deleted=stats["deleted"],
                verified=stats["verified"],
                deletion_rate=round((stats["deleted"] / stats["total"]) * 100, 1) if stats["total"] > 0 else 0
            )
            for name, stats in furnisher_stats.items()
        ],
        key=lambda x: x.total_executions,
        reverse=True
    )[:20]

    return DisputeIntelResponse(
        total_executions=total_executions,
        overall_deletion_rate=round(overall_deletion_rate, 1),
        overall_verification_rate=round(overall_verification_rate, 1),
        by_bureau=by_bureau,
        top_furnishers=top_furnishers
    )


@router.get("/copilot/performance", response_model=CopilotMetrics)
async def get_copilot_performance(
    days: int = Query(90, ge=1, le=365),
    db: Session = Depends(get_db),
    admin: UserDB = Depends(require_admin)
):
    """
    Get Copilot performance metrics from Execution Ledger.
    Compares outcomes when user followed vs overrode Copilot advice.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    # Get all suppressions (to find overrides)
    suppressions = db.query(ExecutionSuppressionEventDB).filter(
        ExecutionSuppressionEventDB.suppressed_at >= cutoff
    ).all()

    total_suppressions = len(suppressions)
    override_count = sum(1 for s in suppressions if s.suppression_reason == SuppressionReason.USER_OVERRIDE)

    # Get all executions in time window
    executions = db.query(ExecutionEventDB).filter(
        ExecutionEventDB.executed_at >= cutoff
    ).all()

    total_executions = len(executions)

    # For simplicity, we'll treat all executions as "followed" unless there's an override suppression
    # In a real implementation, you'd correlate by dispute_session_id
    followed_count = total_executions  # Users who followed Copilot and sent letters

    # Calculate rates
    total_recommendations = total_executions + override_count  # Simplified approximation
    follow_rate = (followed_count / total_recommendations * 100) if total_recommendations > 0 else 0
    override_rate = (override_count / total_recommendations * 100) if total_recommendations > 0 else 0

    # Get outcomes for followed recommendations
    followed_outcomes = db.query(ExecutionOutcomeDB).join(ExecutionEventDB).filter(
        ExecutionEventDB.executed_at >= cutoff
    ).all()

    followed_deleted = sum(1 for o in followed_outcomes if o.final_outcome == FinalOutcome.DELETED)
    followed_deletion_rate = (followed_deleted / len(followed_outcomes) * 100) if followed_outcomes else 0

    # Override deletion rate would require tracking what happened after overrides
    # For MVP, we'll show 0 since overrides don't generate executions
    overridden_deletion_rate = 0.0

    # By goal breakdown
    by_goal = {}
    for ex in executions:
        goal = ex.credit_goal or "credit_hygiene"
        if goal not in by_goal:
            by_goal[goal] = {"total": 0, "deleted": 0}
        by_goal[goal]["total"] += 1

    for outcome in followed_outcomes:
        goal = outcome.execution.credit_goal or "credit_hygiene"
        if goal in by_goal and outcome.final_outcome == FinalOutcome.DELETED:
            by_goal[goal]["deleted"] += 1

    # Calculate deletion rate per goal
    goal_metrics = {
        goal: {
            "total": stats["total"],
            "deletion_rate": round((stats["deleted"] / stats["total"]) * 100, 1) if stats["total"] > 0 else 0
        }
        for goal, stats in by_goal.items()
    }

    return CopilotMetrics(
        total_recommendations=total_recommendations,
        follow_rate=round(follow_rate, 1),
        override_rate=round(override_rate, 1),
        followed_deletion_rate=round(followed_deletion_rate, 1),
        overridden_deletion_rate=round(overridden_deletion_rate, 1),
        by_goal=goal_metrics
    )
