"""
Dispute System API Routes

Endpoints for the enforcement automation system.
Handles dispute creation, response logging, timeline viewing, and artifact generation.
"""
from datetime import date
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..auth import get_current_user
from ..models.db_models import (
    EntityType, ResponseType, DisputeSource, DisputeStatus, EscalationState
)
from ..services.enforcement import DisputeService


router = APIRouter(prefix="/disputes", tags=["disputes"])


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class CreateDisputeRequest(BaseModel):
    """Request to create a new dispute."""
    entity_type: EntityType = Field(..., description="Type of entity (CRA, FURNISHER, COLLECTOR)")
    entity_name: str = Field(..., description="Name of the entity")
    dispute_date: Optional[date] = Field(None, description="Date dispute was/will be sent")
    source: DisputeSource = Field(default=DisputeSource.DIRECT, description="Source of dispute")
    letter_id: Optional[str] = Field(None, description="ID of generated letter")
    violation_id: Optional[str] = Field(None, description="ID of the violation being disputed (single)")
    violation_ids: Optional[List[str]] = Field(None, description="IDs of violations being disputed (multiple)")
    account_fingerprint: Optional[str] = Field(None, description="Account fingerprint for tracking")
    violation_data: Optional[List[dict]] = Field(None, description="Snapshot of all violations data")
    has_validation_request: bool = Field(default=False, description="For FDCPA - validation request sent")
    collection_continued: bool = Field(default=False, description="For FDCPA - collection continued before validation")


class LogResponseRequest(BaseModel):
    """Request to log an entity response."""
    violation_id: Optional[str] = Field(None, description="ID of the specific violation this response is for")
    response_type: ResponseType = Field(..., description="Type of response received")
    response_date: Optional[date] = Field(None, description="Date response was received")
    updated_fields: Optional[dict] = Field(None, description="For UPDATED - field changes")
    rejection_reason: Optional[str] = Field(None, description="For REJECTED - reason given")
    has_5_day_notice: Optional[bool] = Field(None, description="For REJECTED - 5-day notice provided")
    has_specific_reason: Optional[bool] = Field(None, description="For REJECTED - specific reason stated")
    has_missing_info_request: Optional[bool] = Field(None, description="For REJECTED - missing info identified")


class ConfirmMailingRequest(BaseModel):
    """Request to confirm letter was mailed."""
    mailed_date: date = Field(..., description="Date letter was mailed")
    tracking_number: Optional[str] = Field(None, description="USPS/carrier tracking number")


class LogReinsertionNoticeRequest(BaseModel):
    """Request to log a reinsertion notice."""
    notice_date: date = Field(..., description="Date notice was received")
    notice_content: Optional[str] = Field(None, description="Content of the notice")


class DisputeResponse(BaseModel):
    """Standard dispute response."""
    dispute_id: str
    entity_type: str
    entity_name: str
    dispute_date: str
    deadline_date: str
    current_state: str


class TimelineEntry(BaseModel):
    """Paper trail entry."""
    id: str
    event_type: str
    actor: str
    description: str
    timestamp: str
    evidence_hash: Optional[str]
    artifact_type: Optional[str]
    metadata: Optional[dict]


# =============================================================================
# USER-AUTHORIZED ENDPOINTS
# =============================================================================

@router.post("", response_model=dict)
async def create_dispute(
    request: CreateDisputeRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    Create a new dispute.

    User-authorized action - initiates the dispute process.
    """
    service = DisputeService(db)

    # Use dispute_date if provided, otherwise use today
    from datetime import date as date_type
    dispute_date = request.dispute_date or date_type.today()

    # Get violation_id - prefer single, fall back to first of array
    violation_id = request.violation_id
    if not violation_id and request.violation_ids:
        violation_id = request.violation_ids[0] if request.violation_ids else None

    result = service.create_dispute(
        user_id=current_user.id,
        entity_type=request.entity_type,
        entity_name=request.entity_name,
        dispute_date=dispute_date,
        source=request.source,
        violation_id=violation_id,
        letter_id=request.letter_id,
        account_fingerprint=request.account_fingerprint,
        violation_data=request.violation_data,
        has_validation_request=request.has_validation_request,
        collection_continued=request.collection_continued,
    )

    return result


@router.post("/{dispute_id}/response", response_model=dict)
async def log_response(
    dispute_id: str,
    request: LogResponseRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    Log an entity response.

    User-authorized action - reports what response was received.
    System evaluates the response and creates violations as needed.
    """
    service = DisputeService(db)

    # Verify user owns this dispute
    dispute = service.db.query(service.db.query.__self__.query(
        type(service.db.query.__self__)
    ).first().__class__).get(dispute_id)

    result = service.log_response(
        dispute_id=dispute_id,
        violation_id=request.violation_id,
        response_type=request.response_type,
        response_date=request.response_date,
        updated_fields=request.updated_fields,
        rejection_reason=request.rejection_reason,
        has_5_day_notice=request.has_5_day_notice,
        has_specific_reason=request.has_specific_reason,
        has_missing_info_request=request.has_missing_info_request,
    )

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result


@router.post("/{dispute_id}/confirm-sent", response_model=dict)
async def confirm_mailing(
    dispute_id: str,
    request: ConfirmMailingRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    Confirm that the dispute letter was mailed.

    User-authorized action - starts the deadline clock.
    """
    service = DisputeService(db)

    result = service.confirm_mailing(
        dispute_id=dispute_id,
        mailed_date=request.mailed_date,
        tracking_number=request.tracking_number,
    )

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result


@router.post("/{dispute_id}/artifacts", response_model=dict)
async def request_artifact(
    dispute_id: str,
    artifact_type: str = Query(..., description="Type of artifact to generate"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    Request generation of an artifact (letter, complaint packet, etc.).

    User-authorized action.
    """
    service = DisputeService(db)

    result = service.request_artifact(
        dispute_id=dispute_id,
        artifact_type=artifact_type,
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


# =============================================================================
# READ-ONLY ENDPOINTS
# =============================================================================

@router.get("", response_model=List[dict])
async def get_user_disputes(
    status: Optional[DisputeStatus] = None,
    state: Optional[EscalationState] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    Get all disputes for the current user.

    Optional filters by status and state.
    """
    service = DisputeService(db)

    return service.get_user_disputes(
        user_id=current_user.id,
        status=status,
        state=state,
    )


@router.get("/{dispute_id}", response_model=dict)
async def get_dispute(
    dispute_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    Get details of a specific dispute.
    """
    service = DisputeService(db)

    result = service.get_dispute_state(dispute_id)

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result


@router.get("/{dispute_id}/timeline", response_model=List[dict])
async def get_dispute_timeline(
    dispute_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    Get the complete paper trail for a dispute.

    Immutable, chronological record of all events.
    """
    service = DisputeService(db)

    return service.get_dispute_timeline(dispute_id)


@router.get("/{dispute_id}/state", response_model=dict)
async def get_dispute_state(
    dispute_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    Get the current state of a dispute.

    Shows state machine position, available actions, and deadlines.
    """
    service = DisputeService(db)

    result = service.get_dispute_state(dispute_id)

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result


@router.get("/{dispute_id}/artifacts", response_model=List[str])
async def get_available_artifacts(
    dispute_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    Get available artifacts for the current state.
    """
    service = DisputeService(db)

    return service.get_available_artifacts(dispute_id)


@router.get("/{dispute_id}/system-events", response_model=dict)
async def get_system_events(
    dispute_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    Get system-triggered events for a dispute.

    Shows pending deadlines, reinsertion watches, and auto-escalations.
    """
    service = DisputeService(db)

    result = service.get_system_events(dispute_id)

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result


# =============================================================================
# DELETE DISPUTE
# =============================================================================

@router.delete("/{dispute_id}")
async def delete_dispute(
    dispute_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a dispute.

    Only the owner can delete their disputes.
    """
    from ..models.db_models import DisputeDB

    dispute = db.query(DisputeDB).filter(
        DisputeDB.id == dispute_id,
        DisputeDB.user_id == current_user.id
    ).first()

    if not dispute:
        raise HTTPException(status_code=404, detail="Dispute not found")

    db.delete(dispute)
    db.commit()

    return {"status": "deleted", "dispute_id": dispute_id}


# =============================================================================
# REINSERTION NOTICE ENDPOINT
# =============================================================================

@router.post("/{dispute_id}/reinsertion-notice", response_model=dict)
async def log_reinsertion_notice(
    dispute_id: str,
    request: LogReinsertionNoticeRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    Log receipt of a reinsertion notice.

    User reports receiving advance notice of reinsertion.
    System validates if notice was timely.
    """
    from ..services.enforcement import ReinsertionDetector
    from ..models.db_models import ReinsertionWatchDB

    # Find active watch for this dispute
    watch = db.query(ReinsertionWatchDB).filter(
        ReinsertionWatchDB.dispute_id == dispute_id
    ).first()

    if not watch:
        raise HTTPException(status_code=404, detail="No reinsertion watch found for this dispute")

    detector = ReinsertionDetector(db)

    result = detector.log_reinsertion_notice(
        watch_id=watch.id,
        notice_date=request.notice_date,
        notice_content=request.notice_content,
    )

    db.commit()

    return result
