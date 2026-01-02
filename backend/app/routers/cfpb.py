"""
CFPB Channel Adapter - API Endpoints

Provides CFPB-specific escalation track that mirrors CRA lifecycle.
Same facts, same contradictions, same severity, same remedies - different audience rendering.

Endpoints:
A) POST /api/cfpb/letters/generate - Generate CFPB draft (no state change)
B) POST /api/cfpb/complaints/submit - Submit CFPB complaint (state change)
C) POST /api/cfpb/complaints/response - Log CFPB response (state change)
D) POST /api/cfpb/evaluate - Evaluate CFPB response (read-only)
"""
from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..auth import get_current_user
from ..services.cfpb import CFPBService, CFPBServiceError


router = APIRouter(prefix="/cfpb", tags=["CFPB Channel Adapter"])


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class GenerateLetterRequest(BaseModel):
    """Request to generate CFPB letter draft."""
    dispute_session_id: str = Field(..., description="Links to existing dispute lifecycle")
    cfpb_stage: str = Field(..., description="initial | escalation | final")


class GenerateLetterResponse(BaseModel):
    """Response with generated CFPB letter."""
    content: str
    contradictions_included: List[dict]
    timeline: List[dict]


class SubmissionPayload(BaseModel):
    """Submission payload for CFPB complaint."""
    complaint_text: str = Field(..., description="Complaint text submitted to CFPB")
    attachments: List[str] = Field(default=[], description="List of attachment references")


class SubmitComplaintRequest(BaseModel):
    """Request to submit CFPB complaint."""
    dispute_session_id: str = Field(..., description="Links to existing dispute lifecycle")
    cfpb_stage: str = Field(..., description="initial | escalation | final")
    submission_payload: SubmissionPayload
    cfpb_case_number: Optional[str] = Field(None, description="CFPB portal case number")


class SubmitComplaintResponse(BaseModel):
    """Response after submitting CFPB complaint."""
    cfpb_case_id: str
    cfpb_state: str
    submitted_at: str


class LogResponseRequest(BaseModel):
    """Request to log CFPB response."""
    cfpb_case_id: str = Field(..., description="CFPB case ID")
    response_text: str = Field(..., description="Response text from entity")
    responding_entity: str = Field(..., description="CRA | Furnisher")
    response_date: str = Field(..., description="ISO8601 date")


class LogResponseResponse(BaseModel):
    """Response after logging CFPB response."""
    response_id: str
    classification: str
    new_state: str


class EvaluateRequest(BaseModel):
    """Request to evaluate CFPB response."""
    cfpb_case_id: str = Field(..., description="CFPB case ID")


class EvaluateResponse(BaseModel):
    """Response with evaluation results."""
    unresolved_contradictions: List[dict]
    recommended_next_action: str
    recommended_next_stage: str


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/letters/generate", response_model=GenerateLetterResponse)
async def generate_cfpb_letter(
    request: GenerateLetterRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    Generate CFPB letter draft (no state change).

    Pulls contradictions/severity/remedy from existing engine.
    Applies CFPB rendering rules.
    Returns draft only - no submission.
    """
    # Validate stage
    if request.cfpb_stage not in ("initial", "escalation", "final"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid cfpb_stage: {request.cfpb_stage}. Must be initial, escalation, or final."
        )

    service = CFPBService(db)

    try:
        result = service.generate_letter(
            dispute_session_id=request.dispute_session_id,
            cfpb_stage=request.cfpb_stage,
            user_id=current_user.id,
        )
        return GenerateLetterResponse(**result)
    except CFPBServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/complaints/submit", response_model=SubmitComplaintResponse)
async def submit_cfpb_complaint(
    request: SubmitComplaintRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    Submit CFPB complaint and advance state.

    State changes:
    - initial: NONE → INITIAL_SUBMITTED
    - escalation: RESPONSE_RECEIVED → ESCALATION_SUBMITTED (requires gating)
    - final: ESCALATION_RESPONSE_RECEIVED → FINAL_SUBMITTED (requires gating)

    Gating rules:
    - escalation/final require CRA exhaustion (VERIFIED | NO_RESPONSE | DEFECTIVE)
    - escalation/final require unresolved_contradictions_count > 0
    """
    # Validate stage
    if request.cfpb_stage not in ("initial", "escalation", "final"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid cfpb_stage: {request.cfpb_stage}. Must be initial, escalation, or final."
        )

    service = CFPBService(db)

    try:
        result = service.submit_complaint(
            dispute_session_id=request.dispute_session_id,
            user_id=current_user.id,
            cfpb_stage=request.cfpb_stage,
            submission_payload=request.submission_payload.dict(),
            cfpb_case_number=request.cfpb_case_number,
        )
        return SubmitComplaintResponse(**result)
    except CFPBServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/complaints/response", response_model=LogResponseResponse)
async def log_cfpb_response(
    request: LogResponseRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    Log CFPB response and advance state.

    State changes:
    - INITIAL_SUBMITTED → RESPONSE_RECEIVED
    - ESCALATION_SUBMITTED → ESCALATION_RESPONSE_RECEIVED

    Response classification (informational, does not gate state):
    - ADDRESSED_FACTS
    - IGNORED_FACTS
    - GENERIC_RESPONSE
    """
    # Validate responding entity
    if request.responding_entity not in ("CRA", "Furnisher"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid responding_entity: {request.responding_entity}. Must be CRA or Furnisher."
        )

    # Parse date
    try:
        response_date = date.fromisoformat(request.response_date)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid response_date format: {request.response_date}. Use ISO8601 (YYYY-MM-DD)."
        )

    service = CFPBService(db)

    try:
        result = service.log_response(
            cfpb_case_id=request.cfpb_case_id,
            response_text=request.response_text,
            responding_entity=request.responding_entity,
            response_date=response_date,
        )
        return LogResponseResponse(**result)
    except CFPBServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/evaluate", response_model=EvaluateResponse)
async def evaluate_cfpb_response(
    request: EvaluateRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    Evaluate CFPB response (read-only, no state change).

    Returns recommendations based on state and unresolved contradictions:
    - unresolved_contradictions == 0 → recommend close
    - State = RESPONSE_RECEIVED → recommend escalation
    - State = ESCALATION_RESPONSE_RECEIVED → recommend final
    """
    service = CFPBService(db)

    try:
        result = service.evaluate(cfpb_case_id=request.cfpb_case_id)
        return EvaluateResponse(**result)
    except CFPBServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# ADDITIONAL ENDPOINTS (Convenience)
# =============================================================================

@router.get("/cases/{cfpb_case_id}")
async def get_cfpb_case(
    cfpb_case_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Get CFPB case details."""
    from ..models.db_models import CFPBCaseDB

    cfpb_case = db.query(CFPBCaseDB).filter(
        CFPBCaseDB.id == cfpb_case_id,
        CFPBCaseDB.user_id == current_user.id,
    ).first()

    if not cfpb_case:
        raise HTTPException(status_code=404, detail="CFPB case not found")

    return {
        "id": cfpb_case.id,
        "dispute_session_id": cfpb_case.dispute_session_id,
        "cfpb_case_number": cfpb_case.cfpb_case_number,
        "cfpb_state": cfpb_case.cfpb_state.value,
        "created_at": cfpb_case.created_at.isoformat(),
        "updated_at": cfpb_case.updated_at.isoformat(),
    }


@router.get("/cases/{cfpb_case_id}/events")
async def get_cfpb_events(
    cfpb_case_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Get CFPB case event history."""
    from ..models.db_models import CFPBCaseDB, CFPBEventDB

    # Verify ownership
    cfpb_case = db.query(CFPBCaseDB).filter(
        CFPBCaseDB.id == cfpb_case_id,
        CFPBCaseDB.user_id == current_user.id,
    ).first()

    if not cfpb_case:
        raise HTTPException(status_code=404, detail="CFPB case not found")

    # Get events
    events = db.query(CFPBEventDB).filter(
        CFPBEventDB.cfpb_case_id == cfpb_case_id
    ).order_by(CFPBEventDB.timestamp.desc()).all()

    return {
        "events": [
            {
                "id": e.id,
                "event_type": e.event_type.value,
                "payload": e.payload,
                "timestamp": e.timestamp.isoformat(),
            }
            for e in events
        ]
    }


@router.get("/cases")
async def list_cfpb_cases(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """List all CFPB cases for current user."""
    from ..models.db_models import CFPBCaseDB

    cases = db.query(CFPBCaseDB).filter(
        CFPBCaseDB.user_id == current_user.id
    ).order_by(CFPBCaseDB.created_at.desc()).all()

    return {
        "cases": [
            {
                "id": c.id,
                "dispute_session_id": c.dispute_session_id,
                "cfpb_case_number": c.cfpb_case_number,
                "cfpb_state": c.cfpb_state.value,
                "created_at": c.created_at.isoformat(),
            }
            for c in cases
        ]
    }
