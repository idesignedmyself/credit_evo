"""
Scheduler API Routes

Internal endpoints for system-automatic tasks.
Deadline checks, reinsertion scans, stall detection.
"""
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..services.enforcement import (
    DisputeService,
    ReinsertionDetector,
)
from ..services.enforcement.deadline_engine import DeadlineScheduler


router = APIRouter(prefix="/internal", tags=["scheduler"])


# =============================================================================
# INTERNAL API KEY VALIDATION
# =============================================================================

INTERNAL_API_KEY = "scheduler-internal-key-change-in-production"


async def verify_internal_key(x_internal_key: str = Header(...)):
    """Verify internal API key for scheduler endpoints."""
    if x_internal_key != INTERNAL_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid internal API key")
    return True


# =============================================================================
# SCHEDULER ENDPOINTS (SYSTEM-ONLY)
# =============================================================================

@router.post("/deadline-check", response_model=dict)
async def run_deadline_check(
    db: Session = Depends(get_db),
    _: bool = Depends(verify_internal_key),
):
    """
    Run daily deadline breach scan.

    System-automatic - no user confirmation required.
    Scans all open disputes and processes breaches.
    """
    scheduler = DeadlineScheduler(db)

    result = scheduler.run_daily_deadline_check()

    return result


@router.post("/reinsertion-scan", response_model=dict)
async def run_reinsertion_scan(
    db: Session = Depends(get_db),
    _: bool = Depends(verify_internal_key),
):
    """
    Run daily reinsertion watch expiration.

    System-automatic - expires old watches.
    Actual reinsertion detection happens during report ingestion.
    """
    detector = ReinsertionDetector(db)

    result = detector.expire_old_watches()

    db.commit()

    return {
        "task": "reinsertion_scan",
        "run_date": datetime.utcnow().isoformat(),
        **result,
    }


@router.post("/stall-detection", response_model=dict)
async def run_stall_detection(
    db: Session = Depends(get_db),
    _: bool = Depends(verify_internal_key),
):
    """
    Run stall detection for INVESTIGATING responses.

    System-automatic - converts stale INVESTIGATING to NO_RESPONSE.
    """
    scheduler = DeadlineScheduler(db)

    result = scheduler.run_stall_detection()

    return result


# =============================================================================
# SCHEDULER STATUS ENDPOINTS (READ-ONLY)
# =============================================================================

@router.get("/deadlines", response_model=dict)
async def get_upcoming_deadlines(
    days_ahead: int = 7,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_internal_key),
):
    """
    Get upcoming deadlines for monitoring.
    """
    from ..services.enforcement.deadline_engine import DeadlineEngine

    engine = DeadlineEngine(db)
    deadlines = engine.get_upcoming_deadlines(days_ahead)

    return {
        "days_ahead": days_ahead,
        "count": len(deadlines),
        "deadlines": deadlines,
    }


@router.get("/reinsertion-watches", response_model=dict)
async def get_active_reinsertion_watches(
    db: Session = Depends(get_db),
    _: bool = Depends(verify_internal_key),
):
    """
    Get all active reinsertion watches.
    """
    detector = ReinsertionDetector(db)
    watches = detector.get_active_watches()

    return {
        "count": len(watches),
        "watches": [
            {
                "id": w.id,
                "dispute_id": w.dispute_id,
                "account_fingerprint": w.account_fingerprint,
                "monitoring_end": w.monitoring_end.isoformat(),
                "status": w.status.value,
            }
            for w in watches
        ],
    }


# =============================================================================
# MANUAL TRIGGER ENDPOINTS (FOR TESTING)
# =============================================================================

@router.post("/trigger-all", response_model=dict)
async def trigger_all_tasks(
    db: Session = Depends(get_db),
    _: bool = Depends(verify_internal_key),
):
    """
    Trigger all scheduler tasks.

    For testing/manual intervention only.
    """
    scheduler = DeadlineScheduler(db)
    detector = ReinsertionDetector(db)

    results = {
        "deadline_check": scheduler.run_daily_deadline_check(),
        "stall_detection": scheduler.run_stall_detection(),
        "reinsertion_expiration": detector.expire_old_watches(),
    }

    db.commit()

    return {
        "run_date": datetime.utcnow().isoformat(),
        "results": results,
    }
