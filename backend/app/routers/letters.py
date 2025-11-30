"""
Credit Engine 2.0 - Letters API Router

Handles dispute letter generation with PostgreSQL persistence.
All endpoints require authentication.
"""
from __future__ import annotations
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.db_models import ReportDB, AuditResultDB, UserDB, LetterDB
from ..services.strategy import create_letter_plan
from ..services.renderer import render_letter
from ..models import Tone, Consumer
from ..models.ssot import AuditResult, Violation, Bureau, ViolationType, Severity, FurnisherType
from ..auth import get_current_user
import uuid

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/letters", tags=["letters"])


# =============================================================================
# PYDANTIC MODELS FOR API
# =============================================================================

class LetterRequest(BaseModel):
    report_id: str
    grouping_strategy: str = "by_violation_type"
    tone: str = "formal"
    variation_seed: Optional[int] = None
    selected_violations: Optional[List[str]] = None  # List of violation IDs to include


class LetterResponse(BaseModel):
    letter_id: str
    content: str
    bureau: str
    word_count: int
    accounts_disputed_count: int
    violations_cited_count: int
    variation_seed_used: int


class LetterPreviewResponse(BaseModel):
    preview: str  # First 500 characters
    word_count: int
    accounts_disputed_count: int
    violations_cited_count: int


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def reconstruct_violations(violations_data: list) -> List[Violation]:
    """Reconstruct Violation objects from stored JSON data."""
    violations = []
    for v in violations_data:
        try:
            violation = Violation(
                violation_id=v.get('violation_id', ''),
                violation_type=ViolationType(v.get('violation_type', 'missing_dofd')),
                severity=Severity(v.get('severity', 'medium')),
                account_id=v.get('account_id', ''),
                creditor_name=v.get('creditor_name', ''),
                account_number_masked=v.get('account_number_masked', ''),
                furnisher_type=FurnisherType(v.get('furnisher_type', 'unknown')),
                bureau=Bureau(v.get('bureau', 'transunion')),
                description=v.get('description', ''),
                expected_value=v.get('expected_value'),
                actual_value=v.get('actual_value'),
                fcra_section=v.get('fcra_section'),
                metro2_field=v.get('metro2_field'),
                evidence=v.get('evidence', {}),
                selected_for_dispute=v.get('selected_for_dispute', True)
            )
            violations.append(violation)
        except Exception as e:
            logger.warning(f"Could not reconstruct violation: {e}")
    return violations


def reconstruct_consumer(report: ReportDB) -> Consumer:
    """Reconstruct Consumer object from database record."""
    return Consumer(
        full_name=report.consumer_name or "",
        address=report.consumer_address or "",
        city=report.consumer_city or "",
        state=report.consumer_state or "",
        zip_code=report.consumer_zip or ""
    )


# =============================================================================
# API ENDPOINTS
# =============================================================================

@router.post("/generate", response_model=LetterResponse)
async def generate_letter(
    request: LetterRequest,
    current_user: UserDB = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate a dispute letter for a report.
    Only works for reports owned by current user.

    Pipeline:
    1. Get AuditResult from database
    2. Create LetterPlan (SSOT #3)
    3. Render DisputeLetter (SSOT #4)
    4. Return letter content
    """
    report_id = request.report_id

    # Get report from database - verify ownership
    report = db.query(ReportDB).filter(
        ReportDB.id == report_id,
        ReportDB.user_id == current_user.id
    ).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    # Get audit result from database
    audit_db = db.query(AuditResultDB).filter(AuditResultDB.report_id == report_id).first()
    if not audit_db:
        raise HTTPException(status_code=404, detail="Audit result not found")

    # Reconstruct violations from stored JSON
    all_violations = reconstruct_violations(audit_db.violations_data or [])

    # Filter violations if specific ones are selected
    if request.selected_violations:
        filtered_violations = [
            v for v in all_violations
            if v.violation_id in request.selected_violations
        ]
    else:
        filtered_violations = all_violations

    # Create AuditResult object
    audit_result = AuditResult(
        audit_id=audit_db.id,
        report_id=audit_db.report_id,
        bureau=Bureau(audit_db.bureau or 'transunion'),
        violations=filtered_violations,
        discrepancies=[],
        clean_accounts=audit_db.clean_accounts or [],
        total_accounts_audited=audit_db.total_accounts_audited,
        total_violations_found=len(filtered_violations)
    )

    # Reconstruct consumer
    consumer = reconstruct_consumer(report)

    # Map tone string to enum
    try:
        tone = Tone(request.tone)
    except ValueError:
        tone = Tone.FORMAL

    try:
        # Create LetterPlan (SSOT #3)
        plan = create_letter_plan(
            audit_result=audit_result,
            consumer=consumer,
            grouping_strategy=request.grouping_strategy,
            tone=tone,
            variation_seed=request.variation_seed
        )

        # Render DisputeLetter (SSOT #4)
        letter = render_letter(plan)

        # Save letter to database
        letter_db = LetterDB(
            id=str(uuid.uuid4()),
            report_id=report_id,
            user_id=current_user.id,  # Store user_id for orphaned letter access
            content=letter.content,
            bureau=letter.bureau.value,
            tone=request.tone,
            accounts_disputed=[acc for acc in letter.accounts_disputed],
            violations_cited=[v for v in letter.violations_cited],
            word_count=letter.metadata.word_count,
        )
        db.add(letter_db)
        db.commit()

        return LetterResponse(
            letter_id=letter_db.id,
            content=letter.content,
            bureau=letter.bureau.value,
            word_count=letter.metadata.word_count,
            accounts_disputed_count=len(letter.accounts_disputed),
            violations_cited_count=len(letter.violations_cited),
            variation_seed_used=letter.metadata.variation_seed_used
        )

    except Exception as e:
        logger.error(f"Error generating letter: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating letter: {e}")


@router.post("/preview", response_model=LetterPreviewResponse)
async def preview_letter(
    request: LetterRequest,
    current_user: UserDB = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Preview a dispute letter (first 500 characters).
    Only works for reports owned by current user.
    """
    report_id = request.report_id

    # Get report from database - verify ownership
    report = db.query(ReportDB).filter(
        ReportDB.id == report_id,
        ReportDB.user_id == current_user.id
    ).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    # Get audit result from database
    audit_db = db.query(AuditResultDB).filter(AuditResultDB.report_id == report_id).first()
    if not audit_db:
        raise HTTPException(status_code=404, detail="Audit result not found")

    # Reconstruct violations and consumer
    all_violations = reconstruct_violations(audit_db.violations_data or [])
    consumer = reconstruct_consumer(report)

    # Create AuditResult object
    audit_result = AuditResult(
        audit_id=audit_db.id,
        report_id=audit_db.report_id,
        bureau=Bureau(audit_db.bureau or 'transunion'),
        violations=all_violations,
        discrepancies=[],
        clean_accounts=audit_db.clean_accounts or [],
        total_accounts_audited=audit_db.total_accounts_audited,
        total_violations_found=len(all_violations)
    )

    # Map tone string to enum
    try:
        tone = Tone(request.tone)
    except ValueError:
        tone = Tone.FORMAL

    try:
        plan = create_letter_plan(
            audit_result=audit_result,
            consumer=consumer,
            grouping_strategy=request.grouping_strategy,
            tone=tone,
            variation_seed=request.variation_seed
        )

        letter = render_letter(plan)

        return LetterPreviewResponse(
            preview=letter.content[:500] + "..." if len(letter.content) > 500 else letter.content,
            word_count=letter.metadata.word_count,
            accounts_disputed_count=len(letter.accounts_disputed),
            violations_cited_count=len(letter.violations_cited)
        )

    except Exception as e:
        logger.error(f"Error previewing letter: {e}")
        raise HTTPException(status_code=500, detail=f"Error previewing letter: {e}")


@router.get("/tones")
async def get_available_tones():
    """Get list of available letter tones."""
    return {
        "tones": [
            {"id": "formal", "name": "Formal", "description": "Professional, businesslike tone"},
            {"id": "assertive", "name": "Assertive", "description": "Direct, demanding tone"},
            {"id": "conversational", "name": "Conversational", "description": "Friendly, approachable tone"},
            {"id": "narrative", "name": "Narrative", "description": "Story-like, explanatory tone"},
        ]
    }


@router.get("/strategies")
async def get_available_strategies():
    """Get list of available grouping strategies."""
    return {
        "strategies": [
            {"id": "by_violation_type", "name": "By Violation Type", "description": "Group violations by type (e.g., Missing DOFD, Obsolete)"},
            {"id": "by_creditor", "name": "By Creditor", "description": "Group violations by creditor name"},
            {"id": "by_severity", "name": "By Severity", "description": "Group violations by severity (HIGH, MEDIUM, LOW)"},
        ]
    }


class SaveLetterRequest(BaseModel):
    edited_content: str


class SaveLetterResponse(BaseModel):
    status: str
    letter_id: str
    word_count: int


@router.put("/{letter_id}", response_model=SaveLetterResponse)
async def save_letter(
    letter_id: str,
    request: SaveLetterRequest,
    current_user: UserDB = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Save edited letter content.
    Only works for letters owned by current user.
    """
    # Get letter from database with ownership check
    letter = db.query(LetterDB).filter(
        LetterDB.id == letter_id,
        LetterDB.user_id == current_user.id
    ).first()
    if not letter:
        raise HTTPException(status_code=404, detail="Letter not found")

    # Update edited content
    letter.edited_content = request.edited_content
    letter.word_count = len(request.edited_content.split())
    db.commit()

    return SaveLetterResponse(
        status="saved",
        letter_id=letter_id,
        word_count=letter.word_count
    )


@router.get("/all")
async def list_all_letters(
    current_user: UserDB = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all letters for the current user.
    Letters are retrieved directly by user_id (includes orphaned letters).
    """
    # Query directly by user_id to include orphaned letters (report_id = NULL)
    letters = (
        db.query(LetterDB)
        .filter(LetterDB.user_id == current_user.id)
        .order_by(LetterDB.created_at.desc())
        .all()
    )

    return [
        {
            "id": letter.id,
            "report_id": letter.report_id,  # May be NULL if report was deleted
            "created_at": letter.created_at.isoformat() if letter.created_at else None,
            "bureau": letter.bureau,
            "tone": letter.tone,
            "word_count": letter.word_count,
            "violations": len(letter.violations_cited or []),
            "accounts": len(letter.accounts_disputed or []),
            "has_edits": letter.edited_content is not None,
        }
        for letter in letters
    ]


@router.get("/{letter_id}")
async def get_letter(
    letter_id: str,
    current_user: UserDB = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a letter by ID.
    Returns edited_content if it exists, otherwise original content.
    """
    # Get letter from database with ownership check
    letter = db.query(LetterDB).filter(
        LetterDB.id == letter_id,
        LetterDB.user_id == current_user.id
    ).first()
    if not letter:
        raise HTTPException(status_code=404, detail="Letter not found")

    return {
        "letter_id": letter.id,
        "content": letter.edited_content or letter.content,
        "original_content": letter.content,
        "has_edits": letter.edited_content is not None,
        "bureau": letter.bureau,
        "tone": letter.tone,
        "word_count": letter.word_count,
        "accounts_disputed": letter.accounts_disputed,
        "violations_cited": letter.violations_cited,
        "created_at": letter.created_at.isoformat() if letter.created_at else None,
        "updated_at": letter.updated_at.isoformat() if letter.updated_at else None,
        "report_id": letter.report_id,  # May be NULL if report was deleted
    }


@router.delete("/{letter_id}")
async def delete_letter(
    letter_id: str,
    current_user: UserDB = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a letter by ID.
    Only works for letters owned by current user.
    """
    # Get letter from database with ownership check
    letter = db.query(LetterDB).filter(
        LetterDB.id == letter_id,
        LetterDB.user_id == current_user.id
    ).first()
    if not letter:
        raise HTTPException(status_code=404, detail="Letter not found")

    # Delete the letter
    db.delete(letter)
    db.commit()

    return {"status": "deleted", "letter_id": letter_id}
