"""
Credit Engine 2.0 - Downstream Outcomes API Router

Handles user-reported downstream outcomes (loan approvals, etc.)
Part of the B7 Execution Ledger system.

Note: Downstream outcomes are informational only and are NEVER used
directly for enforcement decisions. They do NOT feed Copilot.
"""
from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.db_models import (
    UserDB,
    DownstreamOutcomeDB,
    DownstreamEventType,
)
from ..auth import get_current_user
from ..services.enforcement import ExecutionLedgerService


router = APIRouter(prefix="/outcomes", tags=["outcomes"])


# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class DownstreamOutcomeRequest(BaseModel):
    """Request model for reporting a downstream outcome."""
    event_type: str  # LOAN_APPROVED, APARTMENT_APPROVED, EMPLOYMENT_CLEARED
    notes: Optional[str] = None
    dispute_session_id: Optional[str] = None


class DownstreamOutcomeResponse(BaseModel):
    """Response model for a downstream outcome."""
    id: str
    event_type: str
    credit_goal: str
    notes: Optional[str]
    reported_at: str
    created_at: str


class DownstreamOutcomesList(BaseModel):
    """List of downstream outcomes."""
    outcomes: List[DownstreamOutcomeResponse]
    total: int


# =============================================================================
# API ENDPOINTS
# =============================================================================

@router.post("", response_model=DownstreamOutcomeResponse)
async def report_downstream_outcome(
    request: DownstreamOutcomeRequest,
    current_user: UserDB = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Report a downstream outcome (loan approval, apartment approval, etc.)

    These outcomes are informational only and help track the real-world
    impact of credit repair efforts. They are NOT used for enforcement
    decisions and do NOT feed Copilot.
    """
    # Validate event type
    try:
        event_type = DownstreamEventType(request.event_type)
    except ValueError:
        valid_types = [e.value for e in DownstreamEventType]
        raise HTTPException(
            status_code=400,
            detail=f"Invalid event_type. Must be one of: {valid_types}",
        )

    # Get user's credit goal
    credit_goal = current_user.credit_goal or "credit_hygiene"

    # Emit downstream outcome to ledger
    ledger = ExecutionLedgerService(db)
    outcome = ledger.emit_downstream_outcome(
        user_id=current_user.id,
        credit_goal=credit_goal,
        event_type=event_type,
        reported_at=datetime.utcnow(),
        dispute_session_id=request.dispute_session_id,
        notes=request.notes,
    )

    db.commit()

    return DownstreamOutcomeResponse(
        id=outcome.id,
        event_type=outcome.event_type.value,
        credit_goal=outcome.credit_goal,
        notes=outcome.notes,
        reported_at=outcome.reported_at.isoformat(),
        created_at=outcome.created_at.isoformat(),
    )


@router.get("", response_model=DownstreamOutcomesList)
async def list_downstream_outcomes(
    current_user: UserDB = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all downstream outcomes reported by the current user.
    """
    outcomes = (
        db.query(DownstreamOutcomeDB)
        .filter(DownstreamOutcomeDB.user_id == current_user.id)
        .order_by(DownstreamOutcomeDB.reported_at.desc())
        .all()
    )

    return DownstreamOutcomesList(
        outcomes=[
            DownstreamOutcomeResponse(
                id=o.id,
                event_type=o.event_type.value,
                credit_goal=o.credit_goal,
                notes=o.notes,
                reported_at=o.reported_at.isoformat(),
                created_at=o.created_at.isoformat(),
            )
            for o in outcomes
        ],
        total=len(outcomes),
    )


@router.get("/types")
async def get_outcome_types():
    """
    Get available downstream outcome types.
    """
    return {
        "types": [
            {
                "code": DownstreamEventType.LOAN_APPROVED.value,
                "name": "Loan Approved",
                "description": "A loan application was approved (mortgage, auto, personal, etc.)",
            },
            {
                "code": DownstreamEventType.APARTMENT_APPROVED.value,
                "name": "Apartment Approved",
                "description": "An apartment rental application was approved",
            },
            {
                "code": DownstreamEventType.EMPLOYMENT_CLEARED.value,
                "name": "Employment Cleared",
                "description": "An employment background check was cleared",
            },
        ]
    }
