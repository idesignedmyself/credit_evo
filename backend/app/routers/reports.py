"""
Credit Engine 2.0 - Reports API Router

Handles report upload, parsing, and auditing.
"""
from __future__ import annotations
import logging
import os
import shutil
from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from ..services.parsing import parse_identityiq_html
from ..services.audit import audit_report
from ..models import NormalizedReport, AuditResult, Violation, ViolationType, Severity

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["reports"])

# In-memory storage for demo (would be database in production)
REPORTS_STORAGE = {}
AUDIT_RESULTS_STORAGE = {}


# =============================================================================
# PYDANTIC MODELS FOR API
# =============================================================================

class ViolationResponse(BaseModel):
    violation_id: str
    violation_type: str
    severity: str
    creditor_name: str
    account_number_masked: str
    description: str
    expected_value: Optional[str]
    actual_value: Optional[str]
    fcra_section: Optional[str]
    metro2_field: Optional[str]


class AuditResultResponse(BaseModel):
    audit_id: str
    report_id: str
    total_accounts_audited: int
    total_violations_found: int
    violations: List[ViolationResponse]
    clean_account_count: int


class ReportSummaryResponse(BaseModel):
    report_id: str
    source_file: str
    report_date: str
    consumer_name: str
    total_accounts: int
    parse_timestamp: str


class UploadResponse(BaseModel):
    report_id: str
    message: str
    total_accounts: int
    total_violations: int


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
# API ENDPOINTS
# =============================================================================

@router.get("", response_model=List[ReportListItem])
async def list_reports():
    """
    List all uploaded reports.

    Returns summary of each report including:
    - report_id
    - filename
    - upload timestamp
    - account count
    - violation count
    """
    reports_list = []
    for report_id, report in REPORTS_STORAGE.items():
        audit = AUDIT_RESULTS_STORAGE.get(report_id)
        violations_count = audit.total_violations_found if audit else 0

        # Get just the filename, not the full path
        filename = report.source_file or "Unknown"
        if "/" in filename:
            filename = filename.split("/")[-1]

        reports_list.append(ReportListItem(
            report_id=report_id,
            filename=filename,
            uploaded=str(report.parse_timestamp),
            accounts=len(report.accounts),
            violations=violations_count
        ))

    # Sort by upload time (newest first)
    reports_list.sort(key=lambda x: x.uploaded, reverse=True)
    return reports_list


@router.post("/upload", response_model=UploadResponse)
async def upload_report(file: UploadFile = File(...)):
    """
    Upload and process a credit report HTML file.

    Pipeline:
    1. Auto-purge old reports (single active report mode)
    2. Save uploaded file
    3. Parse HTML → NormalizedReport (SSOT #1)
    4. Audit → AuditResult (SSOT #2)
    5. Return summary
    """
    # Validate file type
    if not file.filename.endswith(('.html', '.htm')):
        raise HTTPException(status_code=400, detail="Only HTML files are supported")

    # Auto-purge: Clear all old reports before saving new one (single active report mode)
    upload_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data", "uploads")
    if os.path.exists(upload_dir):
        for old_file in os.listdir(upload_dir):
            if old_file.endswith('.html'):
                try:
                    os.remove(os.path.join(upload_dir, old_file))
                except Exception:
                    pass  # Best effort cleanup
    REPORTS_STORAGE.clear()
    AUDIT_RESULTS_STORAGE.clear()
    logger.info("Auto-purged old reports for new upload")

    # Create upload directory
    upload_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data", "uploads")
    os.makedirs(upload_dir, exist_ok=True)

    # Save file
    file_id = str(uuid4())
    file_path = os.path.join(upload_dir, f"{file_id}.html")

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    try:
        # Parse HTML → NormalizedReport
        report = parse_identityiq_html(file_path)

        # Store report
        REPORTS_STORAGE[report.report_id] = report

        # Audit → AuditResult
        audit_result = audit_report(report)

        # Store audit result
        AUDIT_RESULTS_STORAGE[report.report_id] = audit_result

        return UploadResponse(
            report_id=report.report_id,
            message="Report uploaded and processed successfully",
            total_accounts=len(report.accounts),
            total_violations=audit_result.total_violations_found
        )

    except Exception as e:
        logger.error(f"Error processing report: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing report: {e}")


@router.get("/{report_id}", response_model=ReportSummaryResponse)
async def get_report(report_id: str):
    """Get report summary by ID."""
    if report_id not in REPORTS_STORAGE:
        raise HTTPException(status_code=404, detail="Report not found")

    report = REPORTS_STORAGE[report_id]

    return ReportSummaryResponse(
        report_id=report.report_id,
        source_file=report.source_file or "",
        report_date=str(report.report_date),
        consumer_name=report.consumer.full_name,
        total_accounts=len(report.accounts),
        parse_timestamp=str(report.parse_timestamp)
    )


@router.get("/{report_id}/audit", response_model=AuditResultResponse)
async def get_audit_result(report_id: str):
    """Get audit results for a report."""
    if report_id not in AUDIT_RESULTS_STORAGE:
        raise HTTPException(status_code=404, detail="Audit result not found")

    audit = AUDIT_RESULTS_STORAGE[report_id]

    violations_response = [
        ViolationResponse(
            violation_id=v.violation_id,
            violation_type=v.violation_type.value,
            severity=v.severity.value,
            creditor_name=v.creditor_name,
            account_number_masked=v.account_number_masked,
            description=v.description,
            expected_value=v.expected_value,
            actual_value=v.actual_value,
            fcra_section=v.fcra_section,
            metro2_field=v.metro2_field
        )
        for v in audit.violations
    ]

    return AuditResultResponse(
        audit_id=audit.audit_id,
        report_id=audit.report_id,
        total_accounts_audited=audit.total_accounts_audited,
        total_violations_found=audit.total_violations_found,
        violations=violations_response,
        clean_account_count=len(audit.clean_accounts)
    )


@router.get("/{report_id}/violations", response_model=List[ViolationResponse])
async def get_violations(report_id: str, severity: Optional[str] = None, violation_type: Optional[str] = None):
    """Get violations for a report with optional filtering."""
    if report_id not in AUDIT_RESULTS_STORAGE:
        raise HTTPException(status_code=404, detail="Audit result not found")

    audit = AUDIT_RESULTS_STORAGE[report_id]
    violations = audit.violations

    # Filter by severity
    if severity:
        violations = [v for v in violations if v.severity.value == severity]

    # Filter by type
    if violation_type:
        violations = [v for v in violations if v.violation_type.value == violation_type]

    return [
        ViolationResponse(
            violation_id=v.violation_id,
            violation_type=v.violation_type.value,
            severity=v.severity.value,
            creditor_name=v.creditor_name,
            account_number_masked=v.account_number_masked,
            description=v.description,
            expected_value=v.expected_value,
            actual_value=v.actual_value,
            fcra_section=v.fcra_section,
            metro2_field=v.metro2_field
        )
        for v in violations
    ]


@router.delete("/{report_id}", response_model=DeleteResponse)
async def delete_report(report_id: str):
    """
    Delete a specific report and its audit results.

    Removes:
    - Report from REPORTS_STORAGE
    - Audit result from AUDIT_RESULTS_STORAGE
    - Uploaded file from disk
    """
    if report_id not in REPORTS_STORAGE:
        raise HTTPException(status_code=404, detail="Report not found")

    # Remove from storage
    del REPORTS_STORAGE[report_id]

    # Remove audit result if exists
    if report_id in AUDIT_RESULTS_STORAGE:
        del AUDIT_RESULTS_STORAGE[report_id]

    # Try to delete uploaded file
    upload_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data", "uploads")
    file_path = os.path.join(upload_dir, f"{report_id}.html")
    if os.path.exists(file_path):
        os.remove(file_path)

    return DeleteResponse(status="deleted", report_id=report_id)


@router.delete("", response_model=DeleteResponse)
async def delete_all_reports():
    """
    Delete ALL reports and audit results.

    Use with caution - this clears all data.
    """
    count = len(REPORTS_STORAGE)

    # Clear all storage
    REPORTS_STORAGE.clear()
    AUDIT_RESULTS_STORAGE.clear()

    # Clear upload directory
    upload_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data", "uploads")
    if os.path.exists(upload_dir):
        for f in os.listdir(upload_dir):
            if f.endswith('.html'):
                os.remove(os.path.join(upload_dir, f))

    return DeleteResponse(status="all_deleted", deleted_count=count)
