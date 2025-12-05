"""
Credit Engine 2.0 - Reports API Router

Handles report upload, parsing, and auditing with PostgreSQL persistence.
All endpoints require authentication.
"""
from __future__ import annotations
import json
import logging
import os
import shutil
from dataclasses import asdict
from datetime import datetime, date
from enum import Enum
from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.db_models import ReportDB, AuditResultDB, UserDB
from ..services.parsing import parse_identityiq_html
from ..services.audit import audit_report
from ..models import NormalizedReport, AuditResult, Violation, ViolationType, Severity
from ..auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["reports"])


# =============================================================================
# PYDANTIC MODELS FOR API
# =============================================================================

class ViolationResponse(BaseModel):
    violation_id: str
    violation_type: str
    severity: str
    bureau: str
    creditor_name: str
    account_number_masked: str
    description: str
    expected_value: Optional[str]
    actual_value: Optional[str]
    fcra_section: Optional[str]
    metro2_field: Optional[str]


class DiscrepancyResponse(BaseModel):
    """Cross-bureau discrepancy response model."""
    discrepancy_id: str
    violation_type: str
    creditor_name: str
    account_number_masked: str = ""  # Masked account number for display
    account_fingerprint: str
    field_name: str
    values_by_bureau: dict  # e.g., {"transunion": "$5,000", "experian": "$5,200"}
    description: str
    severity: str


class AuditResultResponse(BaseModel):
    audit_id: str
    report_id: str
    total_accounts_audited: int
    total_violations_found: int
    violations: List[ViolationResponse]
    discrepancies: List[DiscrepancyResponse] = []
    total_discrepancies_found: int = 0
    clean_account_count: int


class CreditScoreResponse(BaseModel):
    transunion: Optional[int] = None
    experian: Optional[int] = None
    equifax: Optional[int] = None
    transunion_rank: Optional[str] = None
    experian_rank: Optional[str] = None
    equifax_rank: Optional[str] = None
    score_scale: str = "300-850"


class ReportSummaryResponse(BaseModel):
    report_id: str
    source_file: str
    report_date: str
    consumer_name: str
    bureau: str
    total_accounts: int
    accounts: List[dict]
    parse_timestamp: str
    credit_scores: Optional[CreditScoreResponse] = None


class UploadResponse(BaseModel):
    report_id: str
    message: str
    total_accounts: int
    total_violations: int
    accounts: List[dict]
    credit_scores: Optional[CreditScoreResponse] = None


class ReportListItem(BaseModel):
    report_id: str
    filename: str
    uploaded: str
    accounts: int
    violations: int


class DeleteResponse(BaseModel):
    status: str
    report_id: Optional[str] = None
    deleted_count: Optional[int] = None


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def serialize_report(report: NormalizedReport) -> dict:
    """Convert NormalizedReport dataclass to JSON-serializable dict."""
    def convert(obj):
        if isinstance(obj, dict):
            return {k: convert(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert(i) for i in obj]
        elif isinstance(obj, Enum):
            return obj.value
        elif isinstance(obj, (date, datetime)):
            return obj.isoformat()
        return obj
    return convert(asdict(report))


def serialize_audit(audit: AuditResult) -> dict:
    """Convert AuditResult dataclass to JSON-serializable dict."""
    def convert(obj):
        if isinstance(obj, dict):
            return {k: convert(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert(i) for i in obj]
        elif isinstance(obj, Enum):
            return obj.value
        elif isinstance(obj, (date, datetime)):
            return obj.isoformat()
        return obj
    return convert(asdict(audit))


def get_user_storage_dir(user_id: str) -> str:
    """Get storage directory for a user."""
    base_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data", "storage")
    user_dir = os.path.join(base_dir, user_id)
    os.makedirs(user_dir, exist_ok=True)
    return user_dir


# =============================================================================
# API ENDPOINTS
# =============================================================================

@router.get("", response_model=List[ReportListItem])
async def list_reports(
    current_user: UserDB = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all reports for the authenticated user.
    """
    reports = db.query(ReportDB).filter(
        ReportDB.user_id == current_user.id
    ).order_by(ReportDB.created_at.desc()).all()

    reports_list = []
    for report in reports:
        # Get audit result for violation count
        audit = db.query(AuditResultDB).filter(AuditResultDB.report_id == report.id).first()
        violations_count = audit.total_violations_found if audit else 0

        # Get account count from accounts_json, fallback to report_data for old reports
        accounts = report.accounts_json or (report.report_data.get('accounts', []) if report.report_data else [])

        # Get just the filename
        filename = report.source_file or "Unknown"
        if "/" in filename:
            filename = filename.split("/")[-1]

        reports_list.append(ReportListItem(
            report_id=report.id,
            filename=filename,
            uploaded=str(report.created_at),
            accounts=len(accounts),
            violations=violations_count
        ))

    return reports_list


@router.post("/upload", response_model=UploadResponse)
async def upload_report(
    file: UploadFile = File(...),
    current_user: UserDB = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload and process a credit report HTML file.
    Associates report with authenticated user.
    """
    # Validate file type
    if not file.filename.endswith(('.html', '.htm')):
        raise HTTPException(status_code=400, detail="Only HTML files are supported")

    # Get user's storage directory
    user_storage = get_user_storage_dir(current_user.id)

    # Save file
    file_id = str(uuid4())
    file_path = os.path.join(user_storage, f"{file_id}.html")

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    try:
        # Parse HTML → NormalizedReport
        report = parse_identityiq_html(file_path)

        # Serialize report once for reuse
        serialized_report = serialize_report(report)

        # Save report to database with user_id
        db_report = ReportDB(
            id=report.report_id,
            user_id=current_user.id,
            consumer_name=report.consumer.full_name,
            consumer_address=report.consumer.address,
            consumer_city=report.consumer.city,
            consumer_state=report.consumer.state,
            consumer_zip=report.consumer.zip_code,
            bureau=report.bureau.value,
            report_date=report.report_date,
            source_file=file.filename,
            report_data=serialized_report,
            accounts_json=serialized_report.get('accounts', [])
        )
        db.add(db_report)

        # Audit → AuditResult
        audit_result = audit_report(report)

        # Serialize discrepancies for storage
        serialized_audit = serialize_audit(audit_result)
        discrepancies_data = serialized_audit.get('discrepancies', [])

        # Save audit result to database
        db_audit = AuditResultDB(
            id=audit_result.audit_id,
            report_id=report.report_id,
            bureau=audit_result.bureau.value,
            total_accounts_audited=audit_result.total_accounts_audited,
            total_violations_found=audit_result.total_violations_found,
            violations_data=serialized_audit.get('violations', []),
            discrepancies_data=discrepancies_data,
            clean_accounts=audit_result.clean_accounts
        )
        db.add(db_audit)
        db.commit()

        logger.info(f"Audit saved: {audit_result.total_violations_found} violations, {len(discrepancies_data)} cross-bureau discrepancies")

        # Extract credit scores for response
        credit_scores_data = serialized_report.get('credit_scores')
        credit_scores_response = None
        if credit_scores_data:
            credit_scores_response = CreditScoreResponse(
                transunion=credit_scores_data.get('transunion'),
                experian=credit_scores_data.get('experian'),
                equifax=credit_scores_data.get('equifax'),
                transunion_rank=credit_scores_data.get('transunion_rank'),
                experian_rank=credit_scores_data.get('experian_rank'),
                equifax_rank=credit_scores_data.get('equifax_rank'),
                score_scale=credit_scores_data.get('score_scale', '300-850')
            )

        return UploadResponse(
            report_id=report.report_id,
            message="Report uploaded and processed successfully",
            total_accounts=len(report.accounts),
            total_violations=audit_result.total_violations_found,
            accounts=serialized_report.get('accounts', []),
            credit_scores=credit_scores_response
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Error processing report: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing report: {e}")


@router.get("/{report_id}", response_model=ReportSummaryResponse)
async def get_report(
    report_id: str,
    current_user: UserDB = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get report summary by ID. Only returns if owned by current user."""
    report = db.query(ReportDB).filter(
        ReportDB.id == report_id,
        ReportDB.user_id == current_user.id
    ).first()

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    # Use accounts_json for reliable retrieval, fallback to report_data for old reports
    accounts = report.accounts_json or (report.report_data.get('accounts', []) if report.report_data else [])

    # Extract credit scores from report_data
    credit_scores_response = None
    if report.report_data:
        credit_scores_data = report.report_data.get('credit_scores')
        if credit_scores_data:
            credit_scores_response = CreditScoreResponse(
                transunion=credit_scores_data.get('transunion'),
                experian=credit_scores_data.get('experian'),
                equifax=credit_scores_data.get('equifax'),
                transunion_rank=credit_scores_data.get('transunion_rank'),
                experian_rank=credit_scores_data.get('experian_rank'),
                equifax_rank=credit_scores_data.get('equifax_rank'),
                score_scale=credit_scores_data.get('score_scale', '300-850')
            )

    return ReportSummaryResponse(
        report_id=report.id,
        source_file=report.source_file or "",
        report_date=str(report.report_date) if report.report_date else "",
        consumer_name=report.consumer_name,
        bureau=report.bureau or "transunion",
        total_accounts=len(accounts),
        accounts=accounts,
        parse_timestamp=str(report.created_at),
        credit_scores=credit_scores_response
    )


@router.get("/{report_id}/audit", response_model=AuditResultResponse)
async def get_audit_result(
    report_id: str,
    current_user: UserDB = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get audit results for a report. Only returns if owned by current user."""
    # First verify ownership
    report = db.query(ReportDB).filter(
        ReportDB.id == report_id,
        ReportDB.user_id == current_user.id
    ).first()

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    audit = db.query(AuditResultDB).filter(AuditResultDB.report_id == report_id).first()

    if not audit:
        raise HTTPException(status_code=404, detail="Audit result not found")

    # Convert stored violations back to response format
    violations_data = audit.violations_data or []
    violations_response = [
        ViolationResponse(
            violation_id=v.get('violation_id', ''),
            violation_type=v.get('violation_type', ''),
            severity=v.get('severity', ''),
            bureau=v.get('bureau', 'transunion'),
            creditor_name=v.get('creditor_name', ''),
            account_number_masked=v.get('account_number_masked', ''),
            description=v.get('description', ''),
            expected_value=v.get('expected_value'),
            actual_value=v.get('actual_value'),
            fcra_section=v.get('fcra_section'),
            metro2_field=v.get('metro2_field')
        )
        for v in violations_data
    ]

    # Convert stored discrepancies back to response format
    discrepancies_data = audit.discrepancies_data or []
    discrepancies_response = [
        DiscrepancyResponse(
            discrepancy_id=d.get('discrepancy_id', ''),
            violation_type=d.get('violation_type', ''),
            creditor_name=d.get('creditor_name', ''),
            account_number_masked=d.get('account_number_masked', ''),
            account_fingerprint=d.get('account_fingerprint', ''),
            field_name=d.get('field_name', ''),
            values_by_bureau=d.get('values_by_bureau', {}),
            description=d.get('description', ''),
            severity=d.get('severity', 'medium')
        )
        for d in discrepancies_data
    ]

    return AuditResultResponse(
        audit_id=audit.id,
        report_id=audit.report_id,
        total_accounts_audited=audit.total_accounts_audited,
        total_violations_found=audit.total_violations_found,
        violations=violations_response,
        discrepancies=discrepancies_response,
        total_discrepancies_found=len(discrepancies_response),
        clean_account_count=len(audit.clean_accounts or [])
    )


@router.get("/{report_id}/violations", response_model=List[ViolationResponse])
async def get_violations(
    report_id: str,
    severity: Optional[str] = None,
    violation_type: Optional[str] = None,
    current_user: UserDB = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get violations for a report with optional filtering. Only for owned reports."""
    # First verify ownership
    report = db.query(ReportDB).filter(
        ReportDB.id == report_id,
        ReportDB.user_id == current_user.id
    ).first()

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    audit = db.query(AuditResultDB).filter(AuditResultDB.report_id == report_id).first()

    if not audit:
        raise HTTPException(status_code=404, detail="Audit result not found")

    violations_data = audit.violations_data or []

    # Filter by severity
    if severity:
        violations_data = [v for v in violations_data if v.get('severity') == severity]

    # Filter by type
    if violation_type:
        violations_data = [v for v in violations_data if v.get('violation_type') == violation_type]

    return [
        ViolationResponse(
            violation_id=v.get('violation_id', ''),
            violation_type=v.get('violation_type', ''),
            severity=v.get('severity', ''),
            bureau=v.get('bureau', 'transunion'),
            creditor_name=v.get('creditor_name', ''),
            account_number_masked=v.get('account_number_masked', ''),
            description=v.get('description', ''),
            expected_value=v.get('expected_value'),
            actual_value=v.get('actual_value'),
            fcra_section=v.get('fcra_section'),
            metro2_field=v.get('metro2_field')
        )
        for v in violations_data
    ]


@router.delete("/{report_id}", response_model=DeleteResponse)
async def delete_report(
    report_id: str,
    current_user: UserDB = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a specific report. Only if owned by current user."""
    report = db.query(ReportDB).filter(
        ReportDB.id == report_id,
        ReportDB.user_id == current_user.id
    ).first()

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    # Delete from database (cascade will handle audit_results)
    db.delete(report)
    db.commit()

    # Try to delete uploaded file
    user_storage = get_user_storage_dir(current_user.id)
    file_path = os.path.join(user_storage, f"{report_id}.html")
    if os.path.exists(file_path):
        os.remove(file_path)

    return DeleteResponse(status="deleted", report_id=report_id)


@router.delete("", response_model=DeleteResponse)
async def delete_all_reports(
    current_user: UserDB = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete ALL reports for the current user only."""
    # Get count of user's reports
    count = db.query(ReportDB).filter(ReportDB.user_id == current_user.id).count()

    # Delete user's audit results
    user_reports = db.query(ReportDB).filter(ReportDB.user_id == current_user.id).all()
    for report in user_reports:
        db.query(AuditResultDB).filter(AuditResultDB.report_id == report.id).delete()

    # Delete user's reports
    db.query(ReportDB).filter(ReportDB.user_id == current_user.id).delete()
    db.commit()

    # Clear user's storage directory
    user_storage = get_user_storage_dir(current_user.id)
    if os.path.exists(user_storage):
        for f in os.listdir(user_storage):
            if f.endswith('.html'):
                os.remove(os.path.join(user_storage, f))

    return DeleteResponse(status="all_deleted", deleted_count=count)
