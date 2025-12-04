"""
Credit Engine 2.0 - Letters API Router

Handles dispute letter generation with PostgreSQL persistence.
Uses the Credit Copilot human-language letter generator.
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
from ..services.letter_generator import (
    LetterAssembler,
    LetterConfig,
    ViolationItem,
    get_available_tones as get_copilot_tones,
    get_available_structures,
)
from ..services.legal_letter_generator import (
    generate_legal_letter,
    list_tones as get_legal_tones,
    GroupingStrategy,
)
from ..services.legal_letter_generator.grouping_strategies import get_violation_fcra_section
from ..services.legal_letter_generator.pdf_format_assembler import generate_pdf_format_letter
from ..services.civil_letter_generator import (
    generate_civil_letter,
    is_civil_tone,
    get_civil_tones,
    get_civil_grouping_strategies,
)
import uuid

# Define tone sets for routing (normalized form: lowercase with underscores)
LEGAL_TONES = {"strict_legal", "professional", "soft_legal", "aggressive"}
CIVIL_TONES = {"conversational", "formal", "assertive", "narrative"}


def normalize_tone(tone: str) -> str:
    """
    Normalize tone name to canonical form (lowercase, underscores).
    Handles variants like: soft-legal, soft legal, SoftLegal, Soft_Legal, softlegal
    """
    return tone.lower().replace("-", "_").replace(" ", "_")


def is_legal_tone(tone: str) -> bool:
    """
    Check if a tone is a legal tone.
    Catches all variants and any tone containing 'legal' in the name.
    """
    normalized = normalize_tone(tone)
    # Check if it's in LEGAL_TONES set
    if normalized in LEGAL_TONES:
        return True
    # Check if it contains 'legal' anywhere in the name
    if "legal" in normalized:
        return True
    return False

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/letters", tags=["letters"])


# =============================================================================
# PYDANTIC MODELS FOR API
# =============================================================================

class LetterRequest(BaseModel):
    report_id: str
    grouping_strategy: str = "by_violation_type"
    tone: str = "conversational"  # Default to conversational for Credit Copilot
    variation_seed: Optional[int] = None
    selected_violations: Optional[List[str]] = None  # List of violation IDs to include
    selected_discrepancies: Optional[List[str]] = None  # List of discrepancy IDs to include
    bureau: str = "transunion"  # Target bureau for the letter
    use_copilot: bool = True  # Use Credit Copilot human-language generator
    use_legal: bool = False  # Use Legal/Metro-2 structured letter generator
    # Legal generator options (only used when use_legal=True)
    include_case_law: bool = True
    include_metro2: bool = True
    include_mov: bool = True


class LetterResponse(BaseModel):
    letter_id: str
    content: str
    bureau: str
    word_count: int
    accounts_disputed_count: int
    violations_cited_count: int
    variation_seed_used: int
    quality_score: Optional[float] = None  # Credit Copilot quality score (0-100)
    structure_type: Optional[str] = None  # narrative, observation, or question
    is_legal_format: bool = False  # Whether this is a Legal/Metro-2 structured letter
    grouping_strategy: Optional[str] = None  # Grouping strategy used (legal letters only)


class LetterPreviewResponse(BaseModel):
    preview: str  # First 500 characters
    word_count: int
    accounts_disputed_count: int
    violations_cited_count: int


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def reclassify_obsolete_violations(violations: List[Violation]) -> List[Violation]:
    """
    Re-classify stale_reporting violations as obsolete_account if >7 years old.

    FCRA 605(a) mandates DELETION for accounts >7 years (2555 days).
    This ensures civil letters correctly demand deletion instead of verification.
    """
    SEVEN_YEARS_DAYS = 2555

    for v in violations:
        # Check if this is a stale_reporting that should be obsolete_account
        if v.violation_type == ViolationType.STALE_REPORTING:
            evidence = v.evidence or {}
            days_since = evidence.get('days_since_update', 0)

            # If >7 years, reclassify as obsolete_account
            if days_since > SEVEN_YEARS_DAYS:
                years_old = days_since / 365.25
                v.violation_type = ViolationType.OBSOLETE_ACCOUNT
                v.severity = Severity.HIGH
                v.fcra_section = "605(a)"
                v.description = (
                    f"This account has exceeded the 7-year reporting limit under FCRA 605(a). "
                    f"The account is {years_old:.1f} years old ({days_since} days since last update). "
                    f"This information is LEGALLY OBSOLETE and must be DELETED immediately."
                )
                v.expected_value = "Account deleted (>7 years)"
                v.actual_value = f"{days_since} days since last update"
                logger.info(f"Reclassified {v.creditor_name} from stale_reporting to obsolete_account ({days_since} days)")

    return violations


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


def reconstruct_discrepancies(discrepancies_data: list) -> list:
    """Reconstruct discrepancy dictionaries from stored JSON data."""
    discrepancies = []
    for d in discrepancies_data or []:
        try:
            discrepancy = {
                "discrepancy_id": d.get("discrepancy_id", ""),
                "violation_type": d.get("violation_type", ""),
                "creditor_name": d.get("creditor_name", ""),
                "account_fingerprint": d.get("account_fingerprint", ""),
                "field_name": d.get("field_name", ""),
                "values_by_bureau": d.get("values_by_bureau", {}),
                "description": d.get("description", ""),
                "severity": d.get("severity", "MEDIUM"),
            }
            discrepancies.append(discrepancy)
        except Exception as e:
            logger.warning(f"Could not reconstruct discrepancy: {e}")
    return discrepancies


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

    Pipeline (Credit Copilot - default):
    1. Get violations from database
    2. Use Credit Copilot human-language assembler
    3. Return natural, template-free letter

    Pipeline (Legacy):
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

    # Re-classify stale_reporting violations that are actually obsolete (>7 years)
    # This fixes cached violations that were classified before the audit rules were updated
    filtered_violations = reclassify_obsolete_violations(filtered_violations)

    # Reconstruct discrepancies from stored JSON
    all_discrepancies = reconstruct_discrepancies(audit_db.discrepancies_data or [])

    # Filter discrepancies if specific ones are selected
    if request.selected_discrepancies:
        filtered_discrepancies = [
            d for d in all_discrepancies
            if d.get("discrepancy_id") in request.selected_discrepancies
        ]
    else:
        filtered_discrepancies = []  # Don't include discrepancies by default

    # Reconstruct consumer
    consumer = reconstruct_consumer(report)

    try:
        # Normalize tone for routing
        tone_normalized = normalize_tone(request.tone)

        # AUTO-DETECT LEGAL TONES: If tone is legal, force use_legal=True
        # This ensures legal tones ALWAYS route to LegalLetterAssembler
        # regardless of what the frontend sends
        # Catches: soft_legal, soft-legal, soft legal, SoftLegal, Soft_Legal, softlegal
        # Also catches ANY tone containing "legal" in the name
        if is_legal_tone(request.tone):
            request.use_legal = True
            logger.info(f"Auto-detected legal tone '{request.tone}' (normalized: '{tone_normalized}'), forcing use_legal=True")

        # Route civil tones to CivilAssembler v2
        # Civil tones: conversational, formal, assertive, narrative
        # Only route to civil if it's NOT a legal tone
        if not is_legal_tone(request.tone) and (tone_normalized in CIVIL_TONES or is_civil_tone(request.tone)):
            # Convert violations to dictionary format for civil generator
            civil_violations = [
                {
                    "violation_id": v.violation_id,
                    "creditor_name": v.creditor_name,
                    "account_number_masked": v.account_number_masked,
                    "violation_type": v.violation_type.value,
                    "description": v.description,
                    "severity": v.severity.value,
                    "bureau": v.bureau.value if v.bureau else None,
                }
                for v in filtered_violations
            ]

            # Map grouping strategy
            civil_grouping_map = {
                "by_violation_type": "by_violation_type",
                "by_creditor": "by_creditor",
                "by_severity": "by_severity",
            }
            grouping_strategy = civil_grouping_map.get(
                request.grouping_strategy, "by_creditor"
            )

            # Generate civil letter using CivilAssembler v2
            civil_result = generate_civil_letter(
                violations=civil_violations,
                bureau=request.bureau,
                tone=request.tone,
                consumer_name=consumer.full_name,
                consumer_address=f"{consumer.address}, {consumer.city}, {consumer.state} {consumer.zip_code}",
                report_id=report_id,
                consumer_id=str(current_user.id),
                grouping_strategy=grouping_strategy,
                seed=request.variation_seed,
            )

            if not civil_result.is_valid:
                raise HTTPException(
                    status_code=400,
                    detail=f"Validation errors: {'; '.join(civil_result.validation_issues)}"
                )

            # Save letter to database
            letter_db = LetterDB(
                id=str(uuid.uuid4()),
                report_id=report_id,
                user_id=current_user.id,
                content=civil_result.content,
                bureau=civil_result.bureau,
                tone=request.tone,
                accounts_disputed=list(set(v.creditor_name for v in filtered_violations)),
                violations_cited=civil_result.violations_included,
                word_count=civil_result.word_count,
            )
            db.add(letter_db)
            db.commit()

            return LetterResponse(
                letter_id=letter_db.id,
                content=civil_result.content,
                bureau=civil_result.bureau,
                word_count=civil_result.word_count,
                accounts_disputed_count=len(set(v.creditor_name for v in filtered_violations)),
                violations_cited_count=len(civil_result.violations_included),
                variation_seed_used=civil_result.metadata.get("seed", 0),
                quality_score=civil_result.quality_score,
                structure_type="civil_v2",
                is_legal_format=False,
                grouping_strategy=grouping_strategy,
            )

        # Use Legal/Metro-2 Structured Letter Generator (PDF Format)
        elif request.use_legal:
            # Convert violations to PDF format assembler format
            # Map audit evidence fields to PDF assembler expected names:
            # - audit stores "date_reported" -> PDF expects "last_reported_date"
            # - audit stores "days_since_update" -> PDF expects "days_since_update" (same)
            # - for missing field violations, extract field name from description or use violation_type
            def get_missing_field_name(v):
                """Extract missing field name for missing field violations."""
                vtype = v.violation_type.value if v.violation_type else ""
                if vtype == "missing_dofd" or vtype == "chargeoff_missing_dofd":
                    return "DOFD"  # Metro 2 Field 25 (Date of First Delinquency)
                elif vtype == "missing_date_opened":
                    return "Date Opened"  # Metro 2 Field 10
                elif vtype == "missing_scheduled_payment":
                    return "Scheduled Payment"  # Metro 2 Field 15
                return None

            def get_days_since_update(v):
                """Extract days since update, handling different evidence field names."""
                if not v.evidence:
                    return None
                # Stale reporting uses "days_since_update"
                if "days_since_update" in v.evidence:
                    return v.evidence["days_since_update"]
                # Obsolete accounts with DOFD: use total_days_since_dofd
                if "total_days_since_dofd" in v.evidence:
                    return v.evidence["total_days_since_dofd"]
                # Obsolete accounts without DOFD: use total_days_old
                if "total_days_old" in v.evidence:
                    return v.evidence["total_days_old"]
                # Fallback for old data: calculate from days_past + 2555
                if "days_past" in v.evidence:
                    return v.evidence["days_past"] + 2555
                if "days_past_7_years" in v.evidence:
                    return v.evidence["days_past_7_years"] + 2555
                return None

            def get_last_reported_date(v):
                """Extract last reported date, handling different evidence field names."""
                if not v.evidence:
                    return None
                # Stale reporting uses "date_reported"
                if "date_reported" in v.evidence:
                    return v.evidence["date_reported"]
                # Obsolete accounts use "dofd" (Date of First Delinquency) or "date_opened"
                if "dofd" in v.evidence:
                    return v.evidence["dofd"]
                if "date_opened" in v.evidence:
                    return v.evidence["date_opened"]
                return None

            pdf_violations = [
                {
                    "creditor_name": v.creditor_name,
                    "account_number_masked": v.account_number_masked,
                    "violation_type": v.violation_type.value,
                    "fcra_section": v.fcra_section or get_violation_fcra_section(v.violation_type.value),
                    "metro2_field": v.metro2_field,
                    "evidence": v.evidence.get("reason", "") if v.evidence else v.description,
                    "days_since_update": get_days_since_update(v),
                    "missing_field": get_missing_field_name(v),
                    "last_reported_date": get_last_reported_date(v),
                    "severity": v.severity.value,
                }
                for v in filtered_violations
            ]

            # Build consumer info for PDF format
            pdf_consumer = {
                "name": consumer.full_name,
                "address": consumer.address,
                "city_state_zip": f"{consumer.city}, {consumer.state} {consumer.zip_code}",
            }

            # Generate legal letter using PDF format assembler
            # Groups violations by TYPE with Roman numerals, matching PDF template
            pdf_result = generate_pdf_format_letter(
                violations=pdf_violations,
                consumer=pdf_consumer,
                bureau=request.bureau,
                seed=request.variation_seed,
                discrepancies=filtered_discrepancies,
            )

            if not pdf_result["is_valid"]:
                validation_errors = [str(issue) for issue in pdf_result.get("validation_issues", [])]
                raise HTTPException(
                    status_code=400,
                    detail=f"Validation errors: {'; '.join(validation_errors)}"
                )

            letter_content = pdf_result["letter"]
            word_count = len(letter_content.split())

            # Save letter to database
            letter_db = LetterDB(
                id=str(uuid.uuid4()),
                report_id=report_id,
                user_id=current_user.id,
                content=letter_content,
                bureau=request.bureau,
                tone=request.tone,
                accounts_disputed=list(set(v.creditor_name for v in filtered_violations)),
                violations_cited=[v.violation_id for v in filtered_violations],
                word_count=word_count,
            )
            db.add(letter_db)
            db.commit()

            return LetterResponse(
                letter_id=letter_db.id,
                content=letter_content,
                bureau=request.bureau,
                word_count=word_count,
                accounts_disputed_count=len(set(v.creditor_name for v in filtered_violations)),
                violations_cited_count=len(filtered_violations),
                variation_seed_used=pdf_result["metadata"].get("seed", request.variation_seed or 0),
                is_legal_format=True,
                grouping_strategy="by_violation_type",  # PDF format always groups by violation type
            )

        # Use Credit Copilot human-language generator (default)
        elif request.use_copilot:
            # Convert violations to ViolationItem format
            violation_items = [
                ViolationItem(
                    violation_id=v.violation_id,
                    violation_type=v.violation_type.value,
                    creditor_name=v.creditor_name,
                    account_number=v.account_number_masked,
                    bureau=v.bureau.value if v.bureau else None,
                    details={
                        "severity": v.severity.value,
                        "description": v.description,
                    }
                )
                for v in filtered_violations
            ]

            # Configure letter
            config = LetterConfig(
                bureau=request.bureau,
                tone=request.tone,
                consumer_name=consumer.full_name,
                consumer_address=f"{consumer.address}, {consumer.city}, {consumer.state} {consumer.zip_code}",
                report_id=report_id,
                consumer_id=str(current_user.id),
            )

            # Generate using Credit Copilot
            assembler = LetterAssembler(seed=request.variation_seed)
            copilot_letter = assembler.generate(violation_items, config)

            # Save letter to database
            letter_db = LetterDB(
                id=str(uuid.uuid4()),
                report_id=report_id,
                user_id=current_user.id,
                content=copilot_letter.content,
                bureau=copilot_letter.bureau,
                tone=request.tone,
                accounts_disputed=list(set(v.creditor_name for v in filtered_violations)),
                violations_cited=copilot_letter.violations_included,
                word_count=copilot_letter.word_count,
            )
            db.add(letter_db)
            db.commit()

            return LetterResponse(
                letter_id=letter_db.id,
                content=copilot_letter.content,
                bureau=copilot_letter.bureau,
                word_count=copilot_letter.word_count,
                accounts_disputed_count=len(set(v.creditor_name for v in filtered_violations)),
                violations_cited_count=len(copilot_letter.violations_included),
                variation_seed_used=copilot_letter.metadata.get("seed", 0),
                quality_score=copilot_letter.quality_score,
                structure_type=copilot_letter.structure_type,
            )

        # Legacy pipeline (use_copilot=False)
        else:
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

            # Map tone string to enum
            try:
                tone = Tone(request.tone)
            except ValueError:
                tone = Tone.FORMAL

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
                user_id=current_user.id,
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
    """Get list of available letter tones from Credit Copilot."""
    return {
        "tones": get_copilot_tones()
    }


@router.get("/structures")
async def get_letter_structures():
    """Get list of available narrative structures from Credit Copilot."""
    return {
        "structures": get_available_structures()
    }


@router.get("/bureaus")
async def get_supported_bureaus():
    """Get list of supported credit bureaus."""
    return {
        "bureaus": [
            {"id": "transunion", "name": "TransUnion", "description": "TransUnion Consumer Solutions"},
            {"id": "experian", "name": "Experian", "description": "Experian"},
            {"id": "equifax", "name": "Equifax", "description": "Equifax Information Services LLC"},
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


@router.get("/civil/tones")
async def get_civil_letter_tones():
    """Get list of available tones for Civil Letter Generator v2."""
    tones = get_civil_tones()
    return {
        "tones": [
            {
                "id": tone["id"],
                "name": tone["name"],
                "description": tone["description"],
                "formality_level": tone.get("formality_level", 5),
                "letter_type": "civil",
            }
            for tone in tones
        ]
    }


@router.get("/civil/strategies")
async def get_civil_grouping_strategies_endpoint():
    """Get list of available grouping strategies for Civil Letter Generator v2."""
    return {
        "strategies": get_civil_grouping_strategies()
    }


@router.get("/legal/tones")
async def get_legal_letter_tones():
    """Get list of available tones for Legal/Metro-2 letter generator."""
    tones = get_legal_tones()
    return {
        "tones": [
            {
                "id": tone["id"],
                "name": tone["name"],
                "description": tone["description"],
                "formality_level": tone.get("formality_level", 5),
            }
            for tone in tones
        ]
    }


@router.get("/legal/strategies")
async def get_legal_grouping_strategies():
    """Get list of available grouping strategies for Legal/Metro-2 letter generator."""
    return {
        "strategies": [
            {
                "id": "by_fcra_section",
                "name": "By FCRA Section",
                "description": "Group violations by FCRA section (611, 623, 607(b), etc.)"
            },
            {
                "id": "by_metro2_field",
                "name": "By Metro-2 Field",
                "description": "Group violations by affected Metro-2 data field"
            },
            {
                "id": "by_creditor",
                "name": "By Creditor",
                "description": "Group violations by creditor/furnisher name"
            },
            {
                "id": "by_severity",
                "name": "By Severity",
                "description": "Group violations by legal severity (high, medium, low)"
            },
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
