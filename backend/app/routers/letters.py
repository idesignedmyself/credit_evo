"""
Credit Engine 2.0 - Letters API Router

Handles dispute letter generation with PostgreSQL persistence.
Uses the Credit Copilot human-language letter generator.
All endpoints require authentication.
"""
from __future__ import annotations
import logging
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.db_models import ReportDB, AuditResultDB, UserDB, LetterDB, ExecutionEventDB, DisputeDB
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
    use_legal: bool = False  # Use Mailed Dispute structured letter generator
    # Mailed Dispute generator options (only used when use_legal=True)
    include_case_law: bool = True
    include_metro2: bool = True
    include_mov: bool = True
    # Document channel: MAILED (default), CFPB, LITIGATION
    channel: str = "MAILED"
    # Route detection flags for CFPB channel (determines wording)
    has_prior_cra_dispute: bool = False  # True if user filed CRA dispute before CFPB
    has_prior_cra_response: bool = False  # True if CRA responded before CFPB filing


class LetterResponse(BaseModel):
    letter_id: str
    content: str
    bureau: str
    word_count: int
    accounts_disputed_count: int
    violations_cited_count: int
    discrepancies_cited: Optional[List[dict]] = None  # Cross-bureau discrepancies included
    discrepancy_count: int = 0
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


def reconstruct_consumer(report: ReportDB, user: UserDB = None) -> Consumer:
    """
    Reconstruct Consumer object, preferring user profile data over parsed report data.

    Priority:
    1. User profile data (if user has filled out their profile)
    2. Parsed report data (fallback)

    Also fixes formatting issues like "NY10026-" -> "NY 10026"
    """
    # Build full name from user profile if available
    if user and user.first_name and user.last_name:
        name_parts = [user.first_name]
        if user.middle_name:
            name_parts.append(user.middle_name)
        name_parts.append(user.last_name)
        if user.suffix:
            name_parts.append(user.suffix)
        full_name = " ".join(name_parts).upper()
    else:
        full_name = report.consumer_name or ""

    # Use user profile address if available
    if user and user.street_address and user.city and user.state and user.zip_code:
        address = user.street_address
        if user.unit:
            address += f" {user.unit}"
        city = user.city
        state = user.state
        zip_code = user.zip_code
    else:
        address = report.consumer_address or ""
        city = report.consumer_city or ""
        state = report.consumer_state or ""
        zip_code = report.consumer_zip or ""

    # Clean up zip code - remove trailing dash and ensure proper formatting
    zip_code = zip_code.rstrip('-').strip()

    return Consumer(
        full_name=full_name,
        address=address,
        city=city,
        state=state,
        zip_code=zip_code
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
                "account_number_masked": d.get("account_number_masked", ""),  # For letter output
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

    # DEBUG: Log available discrepancy IDs
    stored_ids = [d.get("discrepancy_id") for d in all_discrepancies]
    logger.info(f"[CROSS-BUREAU DEBUG] Total discrepancies in DB: {len(all_discrepancies)}")
    logger.info(f"[CROSS-BUREAU DEBUG] Stored discrepancy IDs: {stored_ids}")
    logger.info(f"[CROSS-BUREAU DEBUG] Requested discrepancy IDs: {request.selected_discrepancies}")

    # Filter discrepancies if specific ones are selected
    if request.selected_discrepancies:
        filtered_discrepancies = [
            d for d in all_discrepancies
            if d.get("discrepancy_id") in request.selected_discrepancies
        ]
        logger.info(f"[CROSS-BUREAU DEBUG] Filtered discrepancies count: {len(filtered_discrepancies)}")
    else:
        filtered_discrepancies = []  # Don't include discrepancies by default
        logger.info(f"[CROSS-BUREAU DEBUG] No discrepancies requested, filtered count: 0")

    # Reconstruct consumer - prefer user profile data over parsed report data
    consumer = reconstruct_consumer(report, current_user)

    try:
        # =================================================================
        # CHANNEL ROUTING: CFPB and LITIGATION have separate generators
        # =================================================================
        logger.info(f"[CHANNEL DEBUG] Received channel: '{request.channel}' (type: {type(request.channel).__name__})")

        if request.channel == "CFPB":
            # Generate CFPB complaint using CFPB letter generator
            from ..services.cfpb.cfpb_letter_generator import CFPBLetterGenerator, TimelineEvent

            cfpb_generator = CFPBLetterGenerator()

            # Build timeline from violations
            timeline_events = []
            for v in filtered_violations:
                # Use evidence date if available, otherwise leave as dispute creation
                event_date_val = date.today()
                if v.evidence and v.evidence.get("date_reported"):
                    try:
                        event_date_val = date.fromisoformat(v.evidence["date_reported"])
                    except (ValueError, TypeError):
                        pass

                timeline_events.append(
                    TimelineEvent(
                        event_date=event_date_val,
                        event_description=f"Disputed {v.violation_type.value}: {v.creditor_name}",
                        outcome="Pending"
                    )
                )

            cfpb_letter = cfpb_generator.generate(
                cfpb_stage="initial",
                consumer=consumer,
                contradictions=filtered_violations,
                timeline_events=timeline_events,
                entity_name=request.bureau.title(),
                account_info=filtered_violations[0].account_number_masked if filtered_violations else "N/A",
                has_prior_cra_dispute=request.has_prior_cra_dispute,
                has_prior_cra_response=request.has_prior_cra_response,
                discrepancies=filtered_discrepancies,
            )

            # Build full violation data for CFPB letter (matches LITIGATION format)
            # This enables the litigation packet to use the same violation bundle
            violation_data = [
                {
                    "violation_id": v.violation_id,
                    "violation_type": v.violation_type.value,
                    "creditor_name": v.creditor_name,
                    "account_number_masked": v.account_number_masked,
                    "severity": v.severity.value,
                    "description": v.description,
                    "evidence": v.evidence,
                }
                for v in filtered_violations
            ]

            # Save to database with CFPB channel
            letter_db = LetterDB(
                id=str(uuid.uuid4()),
                user_id=current_user.id,
                report_id=report_id,
                content=cfpb_letter.content,
                bureau=request.bureau,
                tone="regulatory",
                channel="CFPB",
                tier=0,
                accounts_disputed=[v.creditor_name for v in filtered_violations],
                violations_cited=violation_data,  # Full violation objects, not just types
                discrepancies_cited=filtered_discrepancies,  # Cross-bureau discrepancy objects
                account_numbers=[v.account_number_masked or '' for v in filtered_violations],
                word_count=len(cfpb_letter.content.split()),
            )
            db.add(letter_db)
            db.commit()

            return LetterResponse(
                letter_id=letter_db.id,
                content=cfpb_letter.content,
                bureau=request.bureau,
                word_count=len(cfpb_letter.content.split()),
                accounts_disputed_count=len(set(v.creditor_name for v in filtered_violations)),
                violations_cited_count=len(filtered_violations),
                discrepancies_cited=filtered_discrepancies,  # Actual discrepancy data
                discrepancy_count=len(filtered_discrepancies),
                variation_seed_used=0,
                quality_score=0.9,
                structure_type="cfpb_complaint",
                is_legal_format=True,
                grouping_strategy=request.grouping_strategy,
            )

        elif request.channel == "LITIGATION":
            # Generate litigation packet using attorney packet builder
            from ..services.artifacts.attorney_packet_builder import AttorneyPacketBuilder

            packet_builder = AttorneyPacketBuilder()

            # Build violation data for packet
            violation_data = [
                {
                    "violation_id": v.violation_id,
                    "violation_type": v.violation_type.value,
                    "creditor_name": v.creditor_name,
                    "account_number_masked": v.account_number_masked,
                    "severity": v.severity.value,
                    "description": v.description,
                }
                for v in filtered_violations
            ]

            packet = packet_builder.build(
                consumer=consumer,
                violations=violation_data,
                entity_name=request.bureau.title(),
                dispute_timeline=[],
            )

            # Save to database with LITIGATION channel
            letter_db = LetterDB(
                id=str(uuid.uuid4()),
                user_id=current_user.id,
                report_id=report_id,
                content=packet.get("demand_letter", ""),
                bureau=request.bureau,
                tone="demand",
                channel="LITIGATION",
                tier=0,
                accounts_disputed=[v.creditor_name for v in filtered_violations],
                violations_cited=violation_data,  # Full violation objects (matches CFPB)
                account_numbers=[v.account_number_masked or '' for v in filtered_violations],
                word_count=len(packet.get("demand_letter", "").split()),
            )
            db.add(letter_db)
            db.commit()

            return LetterResponse(
                letter_id=letter_db.id,
                content=packet.get("demand_letter", ""),
                bureau=request.bureau,
                word_count=len(packet.get("demand_letter", "").split()),
                accounts_disputed_count=len(set(v.creditor_name for v in filtered_violations)),
                violations_cited_count=len(filtered_violations),
                discrepancies_cited=[],
                discrepancy_count=0,
                variation_seed_used=0,
                quality_score=0.95,
                structure_type="litigation_packet",
                is_legal_format=True,
                grouping_strategy=request.grouping_strategy,
            )

        # =================================================================
        # MAILED CHANNEL: Standard dispute letter (default fallthrough)
        # =================================================================

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
                accounts_disputed=[v.creditor_name for v in filtered_violations],
                violations_cited=[v.violation_type.value for v in filtered_violations],
                discrepancies_cited=[{
                    "discrepancy_id": d.get("discrepancy_id"),
                    "field_name": d.get("field_name"),
                    "creditor_name": d.get("creditor_name"),
                    "account_number_masked": d.get("account_number_masked"),
                } for d in filtered_discrepancies],
                account_numbers=[v.account_number_masked or '' for v in filtered_violations],
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
                discrepancies_cited=[{
                    "discrepancy_id": d.get("discrepancy_id"),
                    "field_name": d.get("field_name"),
                    "creditor_name": d.get("creditor_name"),
                    "account_number_masked": d.get("account_number_masked"),
                } for d in filtered_discrepancies],
                discrepancy_count=len(filtered_discrepancies),
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
                """Extract last reported date (Metro 2 Field 8 - Date Reported)."""
                if not v.evidence:
                    return None
                # Stale reporting uses "date_reported" (Metro 2 Field 8)
                if "date_reported" in v.evidence:
                    return v.evidence["date_reported"]
                return None

            def get_dofd(v):
                """Extract Date of First Delinquency (Metro 2 Field 25) for obsolete accounts."""
                if not v.evidence:
                    return None
                # DOFD is the key field for FCRA 605(a) 7-year calculation
                if "dofd" in v.evidence:
                    return v.evidence["dofd"]
                # Fall back to date_opened for accounts where DOFD calculation was based on that
                if "date_opened" in v.evidence:
                    return v.evidence["date_opened"]
                return None

            def get_dofd_source(v):
                """
                Determine the source of DOFD: 'explicit', 'inferred', or '' (missing).

                - 'explicit': DOFD was directly reported in Metro 2 Field 25
                - 'inferred': DOFD was calculated from payment history per FCRA 605(c)(1)
                - '': No DOFD available (itself a violation for derogatory accounts)
                """
                if not v.evidence:
                    return ""
                # Check if evidence indicates DOFD source
                if "dofd_source" in v.evidence:
                    return v.evidence["dofd_source"]
                # Infer source: if we have "dofd" in evidence, it was either explicit or inferred
                # If we have total_days_since_dofd, we calculated from actual DOFD
                if "dofd" in v.evidence:
                    # If evidence also mentions "inferred" or payment history, it's inferred
                    reason = v.evidence.get("reason", "").lower()
                    if "inferred" in reason or "payment history" in reason:
                        return "inferred"
                    # Otherwise assume explicit from Metro 2 Field 25
                    return "explicit"
                # If using date_opened as fallback, it's because DOFD is missing
                if "date_opened" in v.evidence and "dofd" not in v.evidence:
                    return ""  # No DOFD - using date_opened as fallback
                return ""

            pdf_violations = [
                {
                    "creditor_name": v.creditor_name,
                    "account_number_masked": v.account_number_masked,
                    "violation_type": v.violation_type.value,
                    "fcra_section": v.fcra_section or get_violation_fcra_section(v.violation_type.value),
                    "metro2_field": v.metro2_field,
                    # Pass full evidence dict for structured data, with text "reason" fallback
                    "evidence": v.evidence if isinstance(v.evidence, dict) else (v.evidence or v.description),
                    "days_since_update": get_days_since_update(v),
                    "missing_field": get_missing_field_name(v),
                    "last_reported_date": get_last_reported_date(v),
                    "dofd": get_dofd(v),  # FCRA 605(a) uses DOFD for 7-year calculation
                    "dofd_source": get_dofd_source(v),  # 'explicit', 'inferred', or ''
                    "severity": v.severity.value,
                    # Pass description for fallback display text
                    "description": v.description,
                    # Extract commonly needed fields from evidence for display
                    "payment_status": v.evidence.get("payment_status", "") if v.evidence else "",
                    "balance": v.evidence.get("balance") if v.evidence else None,
                    "account_status": v.evidence.get("account_status", "") if v.evidence else "",
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
                accounts_disputed=[v.creditor_name for v in filtered_violations],
                violations_cited=[v.violation_type.value for v in filtered_violations],
                discrepancies_cited=[{
                    "discrepancy_id": d.get("discrepancy_id"),
                    "field_name": d.get("field_name"),
                    "creditor_name": d.get("creditor_name"),
                    "account_number_masked": d.get("account_number_masked"),
                } for d in filtered_discrepancies],
                account_numbers=[v.account_number_masked or '' for v in filtered_violations],
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
                discrepancies_cited=[{
                    "discrepancy_id": d.get("discrepancy_id"),
                    "field_name": d.get("field_name"),
                    "creditor_name": d.get("creditor_name"),
                    "account_number_masked": d.get("account_number_masked"),
                } for d in filtered_discrepancies],
                discrepancy_count=len(filtered_discrepancies),
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
                accounts_disputed=[v.creditor_name for v in filtered_violations],
                violations_cited=[v.violation_type.value for v in filtered_violations],
                discrepancies_cited=[{
                    "discrepancy_id": d.get("discrepancy_id"),
                    "field_name": d.get("field_name"),
                    "creditor_name": d.get("creditor_name"),
                    "account_number_masked": d.get("account_number_masked"),
                } for d in filtered_discrepancies],
                account_numbers=[v.account_number_masked or '' for v in filtered_violations],
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
                discrepancies_cited=[{
                    "discrepancy_id": d.get("discrepancy_id"),
                    "field_name": d.get("field_name"),
                    "creditor_name": d.get("creditor_name"),
                    "account_number_masked": d.get("account_number_masked"),
                } for d in filtered_discrepancies],
                discrepancy_count=len(filtered_discrepancies),
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
                violations_cited=[v.value if hasattr(v, 'value') else str(v) for v in letter.violations_cited],  # Convert enums to strings
                discrepancies_cited=[{
                    "discrepancy_id": d.get("discrepancy_id"),
                    "field_name": d.get("field_name"),
                    "creditor_name": d.get("creditor_name"),
                    "account_number_masked": d.get("account_number_masked"),
                } for d in filtered_discrepancies],
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
                discrepancies_cited=[{
                    "discrepancy_id": d.get("discrepancy_id"),
                    "field_name": d.get("field_name"),
                    "creditor_name": d.get("creditor_name"),
                    "account_number_masked": d.get("account_number_masked"),
                } for d in filtered_discrepancies],
                discrepancy_count=len(filtered_discrepancies),
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

    # Reconstruct violations and consumer - prefer user profile data
    all_violations = reconstruct_violations(audit_db.violations_data or [])
    consumer = reconstruct_consumer(report, current_user)

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
    channel: Optional[str] = Query(None, description="Filter by channel: CRA, CFPB, LAWYER"),
    tier: Optional[int] = Query(None, description="Filter by tier: 0=initial, 1=tier-1, 2=tier-2"),
    current_user: UserDB = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all letters for the current user.
    Letters are retrieved directly by user_id (includes orphaned letters).
    Optional filtering by channel and/or tier.
    """
    # Query directly by user_id to include orphaned letters (report_id = NULL)
    query = db.query(LetterDB).filter(LetterDB.user_id == current_user.id)

    # Apply optional filters
    if channel:
        query = query.filter(LetterDB.channel == channel)
    if tier is not None:
        query = query.filter(LetterDB.tier == tier)

    letters = query.order_by(LetterDB.created_at.desc()).all()

    def get_letter_type(tone: str) -> str:
        """Infer letter type from tone."""
        if tone and is_legal_tone(tone):
            return "legal"
        return "civilian"

    return [
        {
            "letter_id": letter.id,
            "report_id": letter.report_id,  # May be NULL if report was deleted
            "dispute_id": letter.dispute_id,  # For response letters
            "created_at": letter.created_at.isoformat() if letter.created_at else None,
            "bureau": letter.bureau,
            "tone": letter.tone,
            "letter_type": get_letter_type(letter.tone),
            "letter_category": getattr(letter, 'letter_category', 'dispute') or 'dispute',  # "dispute" or "response"
            "response_type": getattr(letter, 'response_type', None),  # For response letters: NO_RESPONSE, VERIFIED, etc.
            "word_count": letter.word_count,
            "violation_count": len(letter.violations_cited or []),
            "violations_cited": letter.violations_cited or [],  # Array of violation type strings
            "discrepancies_cited": letter.discrepancies_cited or [],  # Array of cross-bureau discrepancies
            "discrepancy_count": len(letter.discrepancies_cited or []),
            "accounts_disputed": letter.accounts_disputed or [],  # Array of creditor names
            "account_numbers": letter.account_numbers or [],  # Array of masked account numbers
            "accounts": len(letter.accounts_disputed or []),
            "has_edits": letter.edited_content is not None,
            "content": letter.edited_content or letter.content,  # For previews - returns edited version if exists
            "tier": getattr(letter, 'tier', 0) or 0,  # 0=initial, 1=tier-1, 2=tier-2
            "channel": getattr(letter, 'channel', 'CRA') or 'CRA',  # CRA, CFPB, LAWYER
        }
        for letter in letters
    ]


@router.get("/counts")
async def get_letter_counts(
    current_user: UserDB = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get letter counts by channel and tier for tab display.
    Returns counts for each channel (CRA, CFPB, LAWYER) and tier (0, 1, 2).
    """
    from sqlalchemy import func

    # Query counts grouped by channel and tier
    counts = db.query(
        LetterDB.channel,
        LetterDB.tier,
        func.count(LetterDB.id).label('count')
    ).filter(
        LetterDB.user_id == current_user.id
    ).group_by(
        LetterDB.channel,
        LetterDB.tier
    ).all()

    # Initialize result structure
    result = {
        "CRA": {"total": 0, "tier_0": 0, "tier_1": 0, "tier_2": 0},
        "CFPB": {"total": 0, "tier_0": 0, "tier_1": 0, "tier_2": 0},
        "LAWYER": {"total": 0, "tier_0": 0, "tier_1": 0, "tier_2": 0},
    }

    # Populate counts
    for channel, tier, count in counts:
        channel_key = channel or "CRA"
        tier_key = tier if tier is not None else 0
        if channel_key in result:
            result[channel_key][f"tier_{tier_key}"] = count
            result[channel_key]["total"] += count

    return result


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
        "discrepancies_cited": letter.discrepancies_cited or [],  # Cross-bureau discrepancies
        "discrepancy_count": len(letter.discrepancies_cited or []),
        "account_numbers": letter.account_numbers,  # Masked account numbers parallel to violations_cited
        "violation_count": len(letter.violations_cited or []),
        "created_at": letter.created_at.isoformat() if letter.created_at else None,
        "updated_at": letter.updated_at.isoformat() if letter.updated_at else None,
        "report_id": letter.report_id,  # May be NULL if report was deleted
    }


@router.get("/{letter_id}/legal-packet")
async def get_legal_packet(
    letter_id: str,
    format: str = Query(
        default="document",
        description="Output format: 'document' (printable text) or 'json' (structured data)"
    ),
    current_user: UserDB = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate attorney-ready legal packet for a letter.

    This endpoint generates a comprehensive litigation packet containing:
    - All violations and discrepancies from the letter
    - Complete dispute timeline
    - CFPB complaint history (if any)
    - Bureau responses
    - Statutory analysis
    - Potential damages calculation

    Use format=document (default) for a printable text document.
    Use format=json for structured data.
    """
    from fastapi.responses import PlainTextResponse
    from datetime import datetime, timezone
    from ..models.db_models import DisputeDB, DisputeResponseDB, CFPBCaseDB, CFPBEventDB

    # Verify letter exists and user owns it
    letter = db.query(LetterDB).filter(
        LetterDB.id == letter_id,
        LetterDB.user_id == current_user.id
    ).first()

    if not letter:
        raise HTTPException(status_code=404, detail="Letter not found")

    # Get user info for consumer name
    consumer_name = f"{current_user.first_name or ''} {current_user.last_name or ''}".strip()
    if not consumer_name:
        consumer_name = current_user.email

    # Format entity name
    entity_map = {
        "transunion": "TransUnion LLC",
        "equifax": "Equifax Inc.",
        "experian": "Experian Information Solutions, Inc.",
    }
    entity_name = entity_map.get(letter.bureau.lower() if letter.bureau else "", letter.bureau or "Credit Bureau")

    # CRITICAL: Use ONLY the violations and discrepancies from this letter
    # Do NOT pull from audit - must match CFPB Stage 1/2 exactly
    discrepancies = letter.discrepancies_cited or []

    # Build violations directly from letter's violations_cited
    # Now stores full violation objects (not just type strings) for CFPB letters
    violations = []
    if letter.violations_cited:
        for i, v in enumerate(letter.violations_cited):
            if isinstance(v, dict):
                # Full violation object - use directly
                violations.append(v)
            elif isinstance(v, str):
                # Legacy: just a type string - create minimal violation entry
                # Use index i to access parallel arrays (accounts_disputed, account_numbers)
                violations.append({
                    "violation_type": v,
                    "creditor_name": letter.accounts_disputed[i] if i < len(letter.accounts_disputed or []) else "Unknown",
                    "account_number_masked": letter.account_numbers[i] if i < len(letter.account_numbers or []) else "N/A",
                    "severity": "high",
                    "description": v.replace("_", " ").title(),
                })

    # Fallback: derive from discrepancies if no violations
    if not violations and discrepancies:
        for d in discrepancies:
            if isinstance(d, dict):
                # Create violation entries from discrepancy accounts
                violations.append({
                    "violation_type": d.get("violation_type", "missing_dofd"),
                    "creditor_name": d.get("creditor_name"),
                    "account_number_masked": d.get("account_number_masked"),
                    "severity": "high",
                    "description": d.get("description", "Cross-bureau data discrepancy"),
                })

    # Build timeline from disputes (with deduplication)
    timeline = []
    seen_timeline = set()
    disputes = db.query(DisputeDB).filter(DisputeDB.letter_id == letter_id).all()
    for dispute in disputes:
        if dispute.dispute_date:
            key = (dispute.dispute_date.isoformat(), "dispute_submitted")
            if key not in seen_timeline:
                seen_timeline.add(key)
                timeline.append({
                    "date": dispute.dispute_date.isoformat(),
                    "event": f"Dispute submitted to {entity_name}",
                    "outcome": "Sent via certified mail",
                    "actor": "CONSUMER"
                })
        if dispute.deadline_date:
            key = (dispute.deadline_date.isoformat(), "deadline")
            if key not in seen_timeline:
                seen_timeline.add(key)
                timeline.append({
                    "date": dispute.deadline_date.isoformat(),
                    "event": "30-day statutory deadline",
                    "outcome": "Passed" if date.today() > dispute.deadline_date else "Pending",
                    "actor": "SYSTEM"
                })
        # Get responses (deduplicated)
        responses = db.query(DisputeResponseDB).filter(DisputeResponseDB.dispute_id == dispute.id).all()
        for resp in responses:
            if resp.response_date:
                key = (resp.response_date.isoformat(), "response", resp.response_type.value if resp.response_type else "")
                if key not in seen_timeline:
                    seen_timeline.add(key)
                    timeline.append({
                        "date": resp.response_date.isoformat(),
                        "event": f"{entity_name} response received",
                        "outcome": resp.response_type.value if resp.response_type else "Unknown",
                        "actor": "ENTITY"
                    })

    # Check for CFPB case (deduplicated)
    cfpb_case = db.query(CFPBCaseDB).filter(CFPBCaseDB.dispute_session_id == letter_id).first()
    cfpb_events = []
    if cfpb_case:
        events = db.query(CFPBEventDB).filter(CFPBEventDB.cfpb_case_id == cfpb_case.id).order_by(CFPBEventDB.timestamp).all()
        for event in events:
            event_date = event.timestamp.isoformat() if event.timestamp else None
            event_type = event.event_type.value if event.event_type else "Unknown"
            cfpb_events.append({
                "date": event_date,
                "event_type": event_type,
                "payload": event.payload or {}
            })
            key = (event_date, "cfpb", event_type)
            if key not in seen_timeline:
                seen_timeline.add(key)
                timeline.append({
                    "date": event_date,
                    "event": f"CFPB {event_type}",
                    "outcome": event.payload.get("stage", "") if event.payload else "",
                    "actor": "REGULATORY"
                })

    # Sort timeline by date
    timeline.sort(key=lambda x: x.get("date") or "")

    # Determine statutes violated (no duplicates)
    statutes = set()
    statutes.add("15 U.S.C. § 1681e(b) — Maximum possible accuracy")
    statutes.add("15 U.S.C. § 1681i(a) — Reasonable reinvestigation")

    for v in violations:
        v_type = v.get("violation_type", "") if isinstance(v, dict) else str(v)
        if "dofd" in v_type.lower() or "missing" in v_type.lower():
            statutes.add("15 U.S.C. § 1681s-2(a)(1)(A) — Furnishing information known to be inaccurate")
            statutes.add("15 U.S.C. § 1681c(a) — Obsolescence period / 7-year reporting limit")

    # Note: Cross-bureau discrepancies fall under § 1681e(b) already added above
    # No separate "cross-bureau accuracy requirement" needed

    # Count violation TYPES (categories), not individual instances
    violation_types = set()
    for v in violations:
        v_type = v.get("violation_type", "") if isinstance(v, dict) else str(v)
        violation_types.add(v_type)
    if discrepancies:
        violation_types.add("date_opened_mismatch")  # Cross-bureau discrepancy type

    # Use type count for legal framing, instance count for damages
    type_count = len(violation_types)
    instance_count = len(violations) + len(discrepancies)

    # Calculate potential damages (based on affected accounts)
    # Get unique accounts
    unique_accounts = set()
    for v in violations:
        if isinstance(v, dict):
            acct = (v.get("creditor_name"), v.get("account_number_masked"))
            unique_accounts.add(acct)
    for d in discrepancies:
        if isinstance(d, dict):
            acct = (d.get("creditor_name"), d.get("account_number_masked"))
            unique_accounts.add(acct)

    account_count = len(unique_accounts)

    # FCRA Statutory damages: $100-$1,000 per willful violation (15 U.S.C. §1681n(a)(1)(A))
    # Do NOT pre-aggregate - show the per-violation statutory range
    damages = {
        "fcra_statutory_min": 100,  # Per willful violation
        "fcra_statutory_max": 1000,  # Per willful violation
        "statutory_citation": "15 U.S.C. §1681n(a)(1)(A)",
        "punitive_eligible": len(timeline) >= 3,  # Multiple dispute rounds
        "willful_indicators": [],
        "violation_types": type_count,
        "affected_accounts": account_count,
    }

    # Check for willfulness indicators
    verified_count = sum(1 for t in timeline if "VERIFIED" in str(t.get("outcome", "")))
    if verified_count >= 1:
        damages["willful_indicators"].append("Verified disputed information despite documented inaccuracies")
    if type_count >= 2:
        damages["willful_indicators"].append(f"Multiple violation categories ({type_count} types)")
    if discrepancies:
        damages["willful_indicators"].append("Cross-bureau inconsistencies prove at least one bureau is inaccurate")

    # Group violations by category (legal theory), not per-account instances
    violations_grouped = {}
    for v in violations:
        if isinstance(v, dict):
            v_type = v.get("violation_type", "unknown")
            if v_type not in violations_grouped:
                violations_grouped[v_type] = {
                    "category": v_type.replace("_", " ").title(),
                    "accounts": []
                }
            acct_info = {
                "creditor_name": v.get("creditor_name"),
                "account_number_masked": v.get("account_number_masked")
            }
            # Avoid duplicate accounts in same category
            if acct_info not in violations_grouped[v_type]["accounts"]:
                violations_grouped[v_type]["accounts"].append(acct_info)

    # Add cross-bureau discrepancies as a separate violation category
    if discrepancies:
        # Group discrepancies by field_name
        discrepancy_fields = {}
        for d in discrepancies:
            if isinstance(d, dict):
                field = d.get("field_name", "Cross-Bureau Mismatch")
                if field not in discrepancy_fields:
                    discrepancy_fields[field] = {
                        "category": f"{field} Mismatch",
                        "accounts": []
                    }
                acct_info = {
                    "creditor_name": d.get("creditor_name"),
                    "account_number_masked": d.get("account_number_masked")
                }
                if acct_info not in discrepancy_fields[field]["accounts"]:
                    discrepancy_fields[field]["accounts"].append(acct_info)
        violations_grouped.update(discrepancy_fields)

    # Build the packet data
    packet_data = {
        "packet_id": f"PKT-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{letter_id[:8].upper()}",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "consumer_name": consumer_name,
        "entity_name": entity_name,
        "letter_id": letter_id,
        "channel": letter.channel or "CRA",
        "tier": letter.tier or 0,
        "violations": violations,  # Raw violations (for backward compat)
        "discrepancies": discrepancies,  # Raw discrepancies (for backward compat)
        "violations_grouped": violations_grouped,  # Grouped by category for UI
        "violation_count": type_count,  # Number of legal violation categories
        "violation_type_count": type_count,  # Categories for legal framing
        "affected_account_count": account_count,  # Accounts for damages
        "timeline": timeline,
        "cfpb_case": {
            "case_number": cfpb_case.cfpb_case_number if cfpb_case else None,
            "state": cfpb_case.cfpb_state.value if cfpb_case and cfpb_case.cfpb_state else None,
            "events": cfpb_events
        } if cfpb_case else None,
        "statutes_violated": sorted(list(statutes)),
        "potential_damages": damages,
    }

    if format.lower() == "json":
        return packet_data

    # Generate printable document using the authoritative AttorneyPacket renderer
    from ..services.artifacts.attorney_packet_builder import AttorneyPacket
    packet_obj = AttorneyPacket.from_packet_data(packet_data)
    document = packet_obj.render_document()
    return PlainTextResponse(content=document, media_type="text/plain; charset=utf-8")


@router.delete("/{letter_id}")
async def delete_letter(
    letter_id: str,
    current_user: UserDB = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Hard delete a letter and all dependent records.
    """
    from ..services.hard_delete_service import HardDeleteService

    service = HardDeleteService(db)
    cascade = service.delete_letter(letter_id, current_user.id)

    if cascade is None:
        raise HTTPException(status_code=404, detail="Letter not found")

    return {"status": "deleted", "letter_id": letter_id, "cascade": cascade}
