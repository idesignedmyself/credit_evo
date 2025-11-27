"""
Credit Engine 2.0 - Letters API Router

Handles dispute letter generation.
"""
from __future__ import annotations
import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..services.strategy import create_letter_plan
from ..services.renderer import render_letter
from ..models import Tone

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/letters", tags=["letters"])

# Import storage from reports router
from .reports import REPORTS_STORAGE, AUDIT_RESULTS_STORAGE


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
# API ENDPOINTS
# =============================================================================

@router.post("/generate", response_model=LetterResponse)
async def generate_letter(request: LetterRequest):
    """
    Generate a dispute letter for a report.

    Pipeline:
    1. Get AuditResult (SSOT #2)
    2. Create LetterPlan (SSOT #3)
    3. Render DisputeLetter (SSOT #4)
    4. Return letter content
    """
    report_id = request.report_id

    if report_id not in REPORTS_STORAGE:
        raise HTTPException(status_code=404, detail="Report not found")

    if report_id not in AUDIT_RESULTS_STORAGE:
        raise HTTPException(status_code=404, detail="Audit result not found")

    report = REPORTS_STORAGE[report_id]
    original_audit = AUDIT_RESULTS_STORAGE[report_id]

    # Filter violations if specific ones are selected (SSOT-safe: create copy, never mutate)
    if request.selected_violations:
        filtered_violations = [
            v for v in original_audit.violations
            if v.violation_id in request.selected_violations
        ]
    else:
        filtered_violations = original_audit.violations.copy()

    # Create new AuditResult with filtered violations (preserves original SSOT)
    from ..models.ssot import AuditResult
    audit_result = AuditResult(
        audit_id=original_audit.audit_id,
        report_id=original_audit.report_id,
        bureau=original_audit.bureau,
        violations=filtered_violations,
        discrepancies=original_audit.discrepancies,
        clean_accounts=original_audit.clean_accounts,
        audit_timestamp=original_audit.audit_timestamp,
        total_accounts_audited=original_audit.total_accounts_audited,
        total_violations_found=len(filtered_violations)
    )

    # Map tone string to enum
    try:
        tone = Tone(request.tone)
    except ValueError:
        tone = Tone.FORMAL

    try:
        # Create LetterPlan (SSOT #3)
        plan = create_letter_plan(
            audit_result=audit_result,
            consumer=report.consumer,
            grouping_strategy=request.grouping_strategy,
            tone=tone,
            variation_seed=request.variation_seed
        )

        # Render DisputeLetter (SSOT #4)
        letter = render_letter(plan)

        return LetterResponse(
            letter_id=letter.letter_id,
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
async def preview_letter(request: LetterRequest):
    """
    Preview a dispute letter (first 500 characters).
    """
    report_id = request.report_id

    if report_id not in REPORTS_STORAGE:
        raise HTTPException(status_code=404, detail="Report not found")

    if report_id not in AUDIT_RESULTS_STORAGE:
        raise HTTPException(status_code=404, detail="Audit result not found")

    report = REPORTS_STORAGE[report_id]
    audit_result = AUDIT_RESULTS_STORAGE[report_id]

    # Map tone string to enum
    try:
        tone = Tone(request.tone)
    except ValueError:
        tone = Tone.FORMAL

    try:
        plan = create_letter_plan(
            audit_result=audit_result,
            consumer=report.consumer,
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
