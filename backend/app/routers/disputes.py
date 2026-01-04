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
    EntityType, ResponseType, DisputeSource, DisputeStatus, EscalationState,
    Tier2ResponseType, ExecutionEventDB
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

    # Pass dispute_date as-is - if None, dispute will be created in "pending tracking" state
    # The clock won't start until user calls confirm-sent with the actual send date

    # Get violation_id - prefer single, fall back to first of array
    violation_id = request.violation_id
    if not violation_id and request.violation_ids:
        violation_id = request.violation_ids[0] if request.violation_ids else None

    result = service.create_dispute(
        user_id=current_user.id,
        entity_type=request.entity_type,
        entity_name=request.entity_name,
        dispute_date=request.dispute_date,  # Pass as-is - None means pending tracking
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
    from ..models.db_models import DisputeDB
    from datetime import datetime

    service = DisputeService(db)

    # Get dispute and verify ownership
    dispute = db.query(DisputeDB).filter(
        DisputeDB.id == dispute_id,
        DisputeDB.user_id == current_user.id
    ).first()

    if not dispute:
        raise HTTPException(status_code=404, detail="Dispute not found")

    # HARD GUARD: NO_RESPONSE requires tracking_started AND deadline must have passed
    if request.response_type == ResponseType.NO_RESPONSE:
        if not dispute.tracking_started or not dispute.dispute_date:
            raise HTTPException(
                status_code=400,
                detail="Cannot log NO_RESPONSE - clock not started (mailed_date is required)"
            )
        if not dispute.deadline_date:
            raise HTTPException(
                status_code=400,
                detail="Cannot log NO_RESPONSE - deadline not set"
            )
        if datetime.now().date() <= dispute.deadline_date:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot log NO_RESPONSE - deadline ({dispute.deadline_date.isoformat()}) has not passed"
            )

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
# RESPONSE LETTER GENERATION
# =============================================================================

class GenerateResponseLetterRequest(BaseModel):
    """Request to generate an enforcement response letter."""
    letter_type: str = Field(
        default="enforcement",
        description="Type of letter: enforcement, follow_up, mov_demand, reinsertion"
    )
    response_type: Optional[str] = Field(
        None,
        description="Response type to generate letter for (NO_RESPONSE, VERIFIED, etc.)"
    )
    violation_id: Optional[str] = Field(
        None,
        description="Specific violation ID to generate letter for (for per-violation letters)"
    )
    include_willful_notice: bool = Field(
        default=True,
        description="Include willful noncompliance notice under §616"
    )
    test_context: bool = Field(
        default=False,
        description="Test mode - bypasses deadline validation, appends test footer, blocks save/mail/escalation"
    )


@router.post("/{dispute_id}/generate-response-letter", response_model=dict)
async def generate_response_letter(
    dispute_id: str,
    request: GenerateResponseLetterRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    Generate a formal enforcement response letter.

    Based on the dispute state and response type, generates appropriate
    FCRA/FDCPA enforcement correspondence.
    """
    from ..models.db_models import DisputeDB, DisputeResponseDB, UserDB
    from ..services.enforcement.response_letter_generator import (
        ResponseLetterGenerator,
        generate_no_response_letter,
        generate_verified_response_letter,
        generate_rejected_response_letter,
        generate_reinsertion_response_letter,
    )
    from datetime import datetime

    # Get the dispute
    dispute = db.query(DisputeDB).filter(
        DisputeDB.id == dispute_id,
        DisputeDB.user_id == current_user.id
    ).first()

    if not dispute:
        raise HTTPException(status_code=404, detail="Dispute not found")

    # Get user info for consumer block
    user = db.query(UserDB).filter(UserDB.id == current_user.id).first()

    # Build consumer name from first/last name fields
    consumer_name = "[CONSUMER NAME]"
    if user:
        name_parts = [user.first_name, user.last_name]
        name_parts = [p for p in name_parts if p]
        if name_parts:
            consumer_name = " ".join(name_parts)

    # Build consumer address from individual fields
    consumer_address = "[CONSUMER ADDRESS]"
    if user and user.street_address:
        addr_parts = [user.street_address]
        if user.unit:
            addr_parts[0] += f" {user.unit}"
        if user.city or user.state or user.zip_code:
            city_state_zip = ", ".join(filter(None, [user.city, user.state]))
            if user.zip_code:
                city_state_zip += f" {user.zip_code}"
            addr_parts.append(city_state_zip)
        consumer_address = "\n".join(addr_parts)

    consumer = {
        "name": consumer_name,
        "address": consumer_address
    }

    # Get violations from dispute
    all_violations = dispute.original_violation_data or []

    # If a specific violation_id is provided, filter to just that violation
    if request.violation_id:
        # Check both 'violation_id' and 'id' fields, convert to string for comparison
        violations = [
            v for v in all_violations
            if str(v.get('violation_id', '')) == str(request.violation_id)
            or str(v.get('id', '')) == str(request.violation_id)
        ]
        if not violations:
            # Debug: log what we have vs what we're looking for
            available_ids = [v.get('violation_id') or v.get('id') for v in all_violations]
            raise HTTPException(
                status_code=404,
                detail=f"Violation not found. Looking for: {request.violation_id}. Available: {available_ids}"
            )
    else:
        violations = all_violations

    # Determine response type to generate letter for
    response_type = request.response_type

    # If not specified, check if there are responses logged
    if not response_type:
        responses = db.query(DisputeResponseDB).filter(
            DisputeResponseDB.dispute_id == dispute_id
        ).order_by(DisputeResponseDB.response_date.desc()).all()

        if responses:
            # Use the most recent response type
            response_type = responses[0].response_type.value if responses[0].response_type else "NO_RESPONSE"
        else:
            # Default to NO_RESPONSE if deadline has passed
            if dispute.deadline_date and datetime.now().date() > dispute.deadline_date:
                response_type = "NO_RESPONSE"
            else:
                response_type = "enforcement"

    # Generate appropriate letter based on response type
    entity_type = dispute.entity_type.value if dispute.entity_type else "CRA"
    entity_name = dispute.entity_name or "Credit Reporting Agency"

    dispute_date = dispute.dispute_date
    deadline_date = dispute.deadline_date

    if response_type == "NO_RESPONSE":
        # HARD GUARD: NO_RESPONSE requires mailed_date AND deadline must have passed
        # Skip validation in test mode for same-day testing
        if not request.test_context:
            if not dispute.tracking_started or not dispute.dispute_date:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot generate NO_RESPONSE letter - clock not started (mailed_date is required)"
                )
            if not dispute.deadline_date:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot generate NO_RESPONSE letter - deadline not set"
                )
            if datetime.now().date() <= dispute.deadline_date:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot generate NO_RESPONSE letter - deadline ({dispute.deadline_date.isoformat()}) has not passed"
                )

        # Use today's date for test mode if no dates set
        test_dispute_date = dispute_date or datetime.now().date()
        test_deadline_date = deadline_date or datetime.now().date()

        letter_content = generate_no_response_letter(
            consumer=consumer,
            entity_type=entity_type,
            entity_name=entity_name,
            original_violations=violations,
            dispute_date=datetime.combine(test_dispute_date, datetime.min.time()),
            deadline_date=datetime.combine(test_deadline_date, datetime.min.time()),
            test_context=request.test_context,
        )

    elif response_type == "VERIFIED":
        # Get response date
        response = db.query(DisputeResponseDB).filter(
            DisputeResponseDB.dispute_id == dispute_id,
            DisputeResponseDB.response_type == ResponseType.VERIFIED
        ).first()

        response_date = response.response_date if response else datetime.now().date()

        letter_content = generate_verified_response_letter(
            consumer=consumer,
            entity_type=entity_type,
            entity_name=entity_name,
            original_violations=violations,
            dispute_date=datetime.combine(dispute_date, datetime.min.time()) if dispute_date else datetime.now(),
            response_date=datetime.combine(response_date, datetime.min.time()) if response_date else datetime.now(),
        )

    elif response_type in ("REINSERTION_NO_NOTICE", "REINSERTION") or request.letter_type == "reinsertion":
        # Reinsertion is detected via ReinsertionWatch, not logged as a response type
        # Get reinsertion watch data for deletion and detection dates
        from ..models.db_models import ReinsertionWatchDB

        watch = db.query(ReinsertionWatchDB).filter(
            ReinsertionWatchDB.dispute_id == dispute_id
        ).first()

        # Determine dates from watch data
        # reinsertion_detected comes from watch, deletion date from monitoring_start
        reinsertion_date = watch.reinsertion_detected if watch and hasattr(watch, 'reinsertion_detected') and watch.reinsertion_detected else datetime.now().date()
        deletion_date = watch.monitoring_start if watch else None
        notice_received_date = None  # Will be set if notice was received

        if watch and hasattr(watch, 'notice_received') and watch.notice_received:
            # If notice was received, it would have a date (deficient notice case)
            notice_received_date = getattr(watch, 'notice_date', None)

        letter_content = generate_reinsertion_response_letter(
            consumer=consumer,
            entity_type=entity_type,
            entity_name=entity_name,
            original_violations=violations,
            reinsertion_date=datetime.combine(reinsertion_date, datetime.min.time()) if isinstance(reinsertion_date, date) else reinsertion_date,
            deletion_date=datetime.combine(deletion_date, datetime.min.time()) if deletion_date and isinstance(deletion_date, date) else deletion_date,
            notice_received_date=datetime.combine(notice_received_date, datetime.min.time()) if notice_received_date and isinstance(notice_received_date, date) else notice_received_date,
        )

    elif response_type == "REJECTED":
        # Get rejection response data
        response = db.query(DisputeResponseDB).filter(
            DisputeResponseDB.dispute_id == dispute_id,
            DisputeResponseDB.response_type == ResponseType.REJECTED
        ).first()

        rejection_date = response.response_date if response else datetime.now().date()
        rejection_reason = response.rejection_reason if response and hasattr(response, 'rejection_reason') else None
        has_5_day_notice = response.has_5_day_notice if response and hasattr(response, 'has_5_day_notice') else False
        has_specific_reason = response.has_specific_reason if response and hasattr(response, 'has_specific_reason') else False

        letter_content = generate_rejected_response_letter(
            consumer=consumer,
            entity_type=entity_type,
            entity_name=entity_name,
            original_violations=violations,
            dispute_date=datetime.combine(dispute_date, datetime.min.time()) if dispute_date else datetime.now(),
            rejection_date=datetime.combine(rejection_date, datetime.min.time()) if rejection_date else datetime.now(),
            rejection_reason=rejection_reason,
            has_5_day_notice=has_5_day_notice,
            has_specific_reason=has_specific_reason,
        )

    else:
        # Generic enforcement letter
        generator = ResponseLetterGenerator()

        demanded_actions = [
            "Immediate correction or deletion of all disputed information",
            "Written confirmation of actions taken within five (5) business days",
            "Disclosure of investigation procedures followed"
        ]

        letter_content = generator.generate_enforcement_letter(
            consumer=consumer,
            entity_type=entity_type,
            entity_name=entity_name,
            violations=[{
                "type": v.get("violation_type", "UNKNOWN"),
                "statute": v.get("primary_statute", ""),
                "facts": [v.get("description", "Disputed violation")],
                "account": {
                    "creditor": v.get("creditor_name", ""),
                    "account_mask": v.get("account_number_masked", "")
                }
            } for v in violations],
            demanded_actions=demanded_actions,
            dispute_date=datetime.combine(dispute_date, datetime.min.time()) if dispute_date else None,
            deadline_date=datetime.combine(deadline_date, datetime.min.time()) if deadline_date else None,
            response_type=response_type,
            include_willful_notice=request.include_willful_notice,
        )

    # Calculate word count
    word_count = len(letter_content.split()) if letter_content else 0

    return {
        "dispute_id": dispute_id,
        "letter_type": request.letter_type,
        "response_type": response_type,
        "content": letter_content,
        "generated_at": datetime.now().isoformat(),
        "entity_name": entity_name,
        "entity_type": entity_type,
        "word_count": word_count,
        "violations": violations,
        "test_context": request.test_context,
    }


# =============================================================================
# SAVE RESPONSE LETTER
# =============================================================================

class SaveResponseLetterRequest(BaseModel):
    """Request to save a response letter."""
    content: str = Field(..., description="Letter content to save")
    response_type: str = Field(..., description="Response type (NO_RESPONSE, VERIFIED, etc.)")
    violation_id: Optional[str] = Field(None, description="Specific violation this letter addresses")
    test_context: bool = Field(default=False, description="If true, block save - test letters cannot be saved")


@router.post("/{dispute_id}/save-response-letter", response_model=dict)
async def save_response_letter(
    dispute_id: str,
    request: SaveResponseLetterRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    Save a response/enforcement letter to the letters table.

    This persists the letter so it appears on the My Letters page.
    Test letters (test_context=True) cannot be saved.
    """
    from ..models.db_models import DisputeDB, LetterDB
    import uuid

    # HARD BLOCK: Test letters cannot be saved to production
    if request.test_context:
        raise HTTPException(
            status_code=400,
            detail="Test letters cannot be saved. Disable test mode to save this letter."
        )

    # Verify dispute exists and user owns it
    dispute = db.query(DisputeDB).filter(
        DisputeDB.id == dispute_id,
        DisputeDB.user_id == current_user.id
    ).first()

    if not dispute:
        raise HTTPException(status_code=404, detail="Dispute not found")

    # Get violations for metadata
    all_violations = dispute.original_violation_data or []

    # Filter to specific violation if provided
    if request.violation_id:
        violations = [
            v for v in all_violations
            if str(v.get('violation_id', '')) == str(request.violation_id)
            or str(v.get('id', '')) == str(request.violation_id)
        ]
    else:
        violations = all_violations

    # Build metadata arrays
    accounts_disputed = list(set(v.get('creditor_name', '') for v in violations if v.get('creditor_name')))
    violations_cited = [v.get('violation_type', '') for v in violations if v.get('violation_type')]
    account_numbers = [v.get('account_number_masked', '') for v in violations if v.get('account_number_masked')]

    # Calculate word count
    word_count = len(request.content.split()) if request.content else 0

    # Create letter record
    letter_id = str(uuid.uuid4())
    letter_db = LetterDB(
        id=letter_id,
        user_id=current_user.id,
        dispute_id=dispute_id,
        content=request.content,
        bureau=dispute.entity_name or "Unknown",
        tone="enforcement",
        letter_category="response",
        response_type=request.response_type,
        accounts_disputed=accounts_disputed,
        violations_cited=violations_cited,
        account_numbers=account_numbers,
        word_count=word_count,
    )
    db.add(letter_db)
    db.commit()

    return {
        "status": "saved",
        "letter_id": letter_id,
        "word_count": word_count,
        "dispute_id": dispute_id,
    }


# =============================================================================
# LETTER AUDITOR
# =============================================================================

class AuditLetterRequest(BaseModel):
    """Request to audit an enforcement letter."""
    letter_content: str = Field(..., description="Full letter text to audit")
    strict_mode: bool = Field(
        default=True,
        description="If True, removes speculative language; if False, only flags it"
    )


@router.post("/{dispute_id}/audit-letter", response_model=dict)
async def audit_letter(
    dispute_id: str,
    request: AuditLetterRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    Audit and harden an enforcement letter.

    Reviews the letter for regulatory compliance and returns a corrected version
    with a change log of improvements made.
    """
    from ..models.db_models import DisputeDB
    from ..services.enforcement.letter_auditor import audit_enforcement_letter

    # Verify dispute exists and user owns it
    dispute = db.query(DisputeDB).filter(
        DisputeDB.id == dispute_id,
        DisputeDB.user_id == current_user.id
    ).first()

    if not dispute:
        raise HTTPException(status_code=404, detail="Dispute not found")

    # Audit the letter
    result = audit_enforcement_letter(
        letter_content=request.letter_content,
        strict_mode=request.strict_mode,
    )

    return {
        "dispute_id": dispute_id,
        "audited_letter": result["audited_letter"],
        "change_log": result["change_log"],
        "issues_found": result["issues_found"],
        "issues_corrected": result["issues_corrected"],
        "audit_score": result["audit_score"],
    }


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
    Hard delete a dispute and all dependent records.
    """
    from ..services.hard_delete_service import HardDeleteService

    service = HardDeleteService(db)
    cascade = service.delete_dispute(dispute_id, current_user.id)

    if cascade is None:
        raise HTTPException(status_code=404, detail="Dispute not found")

    return {"status": "deleted", "dispute_id": dispute_id, "cascade": cascade}


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


# =============================================================================
# TIER-2 NOTICE SENT ENDPOINT
# =============================================================================

@router.post("/{dispute_id}/mark-tier2-sent", response_model=dict)
async def mark_tier2_notice_sent(
    dispute_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    Mark Tier-2 supervisory notice as sent.

    This is the authoritative event that transitions the dispute to Tier-2.
    After this, the Tier-2 adjudication UI becomes visible.

    GUARDRAILS:
    - Cannot unmark once sent
    - Cannot mark sent multiple times
    - Must be called before logging Tier-2 response
    """
    from ..models.db_models import DisputeDB

    service = DisputeService(db)

    # Verify dispute exists and user owns it
    dispute = db.query(DisputeDB).filter(
        DisputeDB.id == dispute_id,
        DisputeDB.user_id == current_user.id
    ).first()

    if not dispute:
        raise HTTPException(status_code=404, detail="Dispute not found")

    try:
        result = service.mark_tier2_notice_sent(dispute_id=dispute_id)
        db.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# TIER-2 RESPONSE ENDPOINT
# =============================================================================

class LogTier2ResponseRequest(BaseModel):
    """Request to log final Tier-2 supervisory response."""
    response_type: Tier2ResponseType = Field(..., description="Final Tier-2 response type")
    response_date: date = Field(..., description="Date response was received")


@router.post("/{dispute_id}/tier2-response", response_model=dict)
async def log_tier2_response(
    dispute_id: str,
    request: LogTier2ResponseRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    Log final Tier-2 supervisory response.

    Tier-2 is exhausted after exactly ONE response evaluation.
    - CURED → Close as CURED_AT_TIER_2
    - Others → Auto-promote to Tier-3 (lock + classify + ledger write)

    Tier-3 does NOT generate letters, contact regulators, or trigger litigation.
    """
    from ..models.db_models import DisputeDB

    service = DisputeService(db)

    # Verify dispute exists and user owns it
    dispute = db.query(DisputeDB).filter(
        DisputeDB.id == dispute_id,
        DisputeDB.user_id == current_user.id
    ).first()

    if not dispute:
        raise HTTPException(status_code=404, detail="Dispute not found")

    try:
        result = service.log_tier2_response(
            dispute_id=dispute_id,
            response_type=request.response_type,
            response_date=request.response_date,
        )
        db.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# TIER 5: ATTORNEY PACKETS & REFERRAL ARTIFACTS
# =============================================================================

@router.get("/{dispute_id}/attorney-packet")
async def get_attorney_packet(
    dispute_id: str,
    format: str = Query(
        default="document",
        description="Output format: 'document' (printable text) or 'json' (structured data)"
    ),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    Generate attorney-ready case packet for a Tier-3 dispute.

    Use format=document (default) for a printable text document to give to your attorney.
    Use format=json for structured data.

    Returns a complete litigation packet containing:
    - Primary violations with evidence
    - Examiner failure classifications
    - Complete timeline with document hashes
    - Statutes violated
    - Potential damages calculation

    Requires: Dispute must be at Tier-3 (locked).
    """
    from fastapi.responses import PlainTextResponse
    from ..models.db_models import DisputeDB
    from ..services.artifacts import AttorneyPacketBuilder

    # Verify dispute exists and user owns it
    dispute = db.query(DisputeDB).filter(
        DisputeDB.id == dispute_id,
        DisputeDB.user_id == current_user.id
    ).first()

    if not dispute:
        raise HTTPException(status_code=404, detail="Dispute not found")

    if dispute.tier_reached < 3:
        raise HTTPException(
            status_code=400,
            detail=f"Attorney packets require Tier-3 disputes. Current tier: {dispute.tier_reached}"
        )

    builder = AttorneyPacketBuilder(db)
    packet = builder.build_packet(dispute_id)

    if not packet:
        raise HTTPException(status_code=500, detail="Failed to generate attorney packet")

    # Return printable document or JSON based on format parameter
    if format.lower() == "document":
        return PlainTextResponse(
            content=packet.render_document(),
            media_type="text/plain; charset=utf-8"
        )
    else:
        return {
            "status": "generated",
            "packet": packet.to_dict(),
        }


@router.get("/{dispute_id}/referral-artifact", response_model=dict)
async def get_referral_artifact(
    dispute_id: str,
    referral_type: str = Query(
        default="attorney",
        description="Referral type: attorney, cfpb, state_ag, ftc"
    ),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    Generate minimal referral artifact for attorney/regulatory intake.

    Returns a compact, machine-readable artifact containing:
    - Violations summary
    - Cure attempt record
    - Failure mode classification

    Requires: Dispute must be at Tier-3 (locked).
    """
    from ..models.db_models import DisputeDB
    from ..services.artifacts import ReferralArtifactBuilder, ReferralType

    # Verify dispute exists and user owns it
    dispute = db.query(DisputeDB).filter(
        DisputeDB.id == dispute_id,
        DisputeDB.user_id == current_user.id
    ).first()

    if not dispute:
        raise HTTPException(status_code=404, detail="Dispute not found")

    if dispute.tier_reached < 3:
        raise HTTPException(
            status_code=400,
            detail=f"Referral artifacts require Tier-3 disputes. Current tier: {dispute.tier_reached}"
        )

    # Map referral type string to enum
    type_map = {
        "attorney": ReferralType.ATTORNEY,
        "cfpb": ReferralType.CFPB,
        "state_ag": ReferralType.STATE_AG,
        "ftc": ReferralType.FTC,
    }
    ref_type = type_map.get(referral_type.lower())
    if not ref_type:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid referral type: {referral_type}. Must be: attorney, cfpb, state_ag, ftc"
        )

    builder = ReferralArtifactBuilder(db)
    artifact = builder.build_artifact(dispute_id, ref_type)

    if not artifact:
        raise HTTPException(status_code=500, detail="Failed to generate referral artifact")

    return {
        "status": "generated",
        "referral_type": referral_type,
        "artifact": artifact.to_dict(),
    }


# =============================================================================
# TIER 6: HUMAN-READABLE EXPLANATIONS
# =============================================================================

@router.get("/{dispute_id}/explanation", response_model=dict)
async def get_explanation(
    dispute_id: str,
    dialect: str = Query(
        default="consumer",
        description="Explanation dialect: consumer, examiner, attorney"
    ),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    Get human-readable explanation for a Tier-3 dispute outcome.

    Renders the dispute outcome in plain language for the specified audience:
    - consumer: Plain English, empowering language
    - examiner: Procedural compliance, regulatory lens
    - attorney: Legal elements, evidence, case law

    Requires: Dispute must be at Tier-3 (locked).
    """
    from ..models.db_models import DisputeDB
    from ..services.copilot import ExplanationRenderer, ExplanationDialect

    # Verify dispute exists and user owns it
    dispute = db.query(DisputeDB).filter(
        DisputeDB.id == dispute_id,
        DisputeDB.user_id == current_user.id
    ).first()

    if not dispute:
        raise HTTPException(status_code=404, detail="Dispute not found")

    if dispute.tier_reached < 3:
        raise HTTPException(
            status_code=400,
            detail=f"Explanations require Tier-3 disputes. Current tier: {dispute.tier_reached}"
        )

    # Map dialect string to enum
    dialect_map = {
        "consumer": ExplanationDialect.CONSUMER,
        "examiner": ExplanationDialect.EXAMINER,
        "attorney": ExplanationDialect.ATTORNEY,
    }
    exp_dialect = dialect_map.get(dialect.lower())
    if not exp_dialect:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid dialect: {dialect}. Must be: consumer, examiner, attorney"
        )

    renderer = ExplanationRenderer(db)
    explanation = renderer.render(dispute_id, exp_dialect)

    if not explanation:
        raise HTTPException(status_code=500, detail="Failed to generate explanation")

    return {
        "status": "generated",
        "dialect": dialect,
        "explanation": explanation.to_dict(),
    }


@router.get("/{dispute_id}/explanations", response_model=dict)
async def get_all_explanations(
    dispute_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    Get explanations in all three dialects for a Tier-3 dispute.

    Returns consumer, examiner, and attorney views simultaneously.
    Useful for displaying toggle views in the UI.

    Requires: Dispute must be at Tier-3 (locked).
    """
    from ..models.db_models import DisputeDB
    from ..services.copilot import ExplanationRenderer

    # Verify dispute exists and user owns it
    dispute = db.query(DisputeDB).filter(
        DisputeDB.id == dispute_id,
        DisputeDB.user_id == current_user.id
    ).first()

    if not dispute:
        raise HTTPException(status_code=404, detail="Dispute not found")

    if dispute.tier_reached < 3:
        raise HTTPException(
            status_code=400,
            detail=f"Explanations require Tier-3 disputes. Current tier: {dispute.tier_reached}"
        )

    renderer = ExplanationRenderer(db)
    explanations = renderer.render_all_dialects(dispute_id)

    if not explanations:
        raise HTTPException(status_code=500, detail="Failed to generate explanations")

    return {
        "status": "generated",
        "dispute_id": dispute_id,
        "explanations": {k: v.to_dict() for k, v in explanations.items()},
    }
