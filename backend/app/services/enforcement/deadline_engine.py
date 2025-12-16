"""
Deadline Engine

AUTHORITY: SYSTEM
Calculates and tracks response deadlines.
Automatically detects breaches and triggers state transitions WITHOUT user confirmation.

Key behaviors:
- Calculate initial deadlines based on dispute source (30/45 days)
- Auto-detect deadline breaches via daily scheduler
- Auto-create NO_RESPONSE violations on deadline breach
- Auto-convert INVESTIGATING responses to NO_RESPONSE after stall timeout
- Track REINSERTION_WATCH_PERIOD (90 days) after DELETED responses

All deadline breaches are SYSTEM-DETECTED violations.
User cannot extend or override deadlines.
"""
from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from uuid import uuid4

from sqlalchemy.orm import Session

from ...models.db_models import (
    DisputeDB, DisputeResponseDB, PaperTrailDB, SchedulerTaskDB,
    EscalationState, DisputeSource, EntityType, ActorType, ResponseType
)


# =============================================================================
# DEADLINE CONFIGURATION
# =============================================================================

DEADLINE_CONFIG = {
    # Source-aware deadlines per FCRA
    DisputeSource.DIRECT: {
        "days": 30,
        "statute": "FCRA § 611(a)(1)(A)",
        "description": "Standard 30-day investigation period",
    },
    DisputeSource.ANNUAL_CREDIT_REPORT: {
        "days": 45,
        "statute": "FCRA § 612(a)",
        "description": "Extended 45-day period for AnnualCreditReport.com disputes",
    },
}

# Additional deadline types
INVESTIGATING_STALL_LIMIT = 15  # Days after INVESTIGATING response before auto-NO_RESPONSE
MOV_RESPONSE_DEADLINE = 15      # Days to respond to Method of Verification demand
PROCEDURAL_CURE_DEADLINE = 30   # Days to cure after procedural enforcement
REINSERTION_WATCH_PERIOD = 90   # Days to monitor for reinsertion after deletion


# =============================================================================
# DEADLINE ENGINE
# =============================================================================

class DeadlineEngine:
    """
    Manages deadlines for the enforcement system.

    Core Responsibilities:
    - Calculate initial deadlines based on dispute source
    - Track deadline status
    - Detect breaches automatically
    - Recalculate deadlines on response
    """

    def __init__(self, db_session: Session):
        """Initialize with database session."""
        self.db = db_session

    def calculate_deadline(
        self,
        dispute_date: date,
        source: DisputeSource,
        entity_type: EntityType,
    ) -> Tuple[date, Dict[str, Any]]:
        """
        Calculate the deadline for a dispute response.

        Returns (deadline_date, metadata)
        """
        config = DEADLINE_CONFIG.get(source, DEADLINE_CONFIG[DisputeSource.DIRECT])

        deadline_date = dispute_date + timedelta(days=config["days"])

        metadata = {
            "source": source.value,
            "days": config["days"],
            "statute": config["statute"],
            "description": config["description"],
            "entity_type": entity_type.value,
        }

        return deadline_date, metadata

    def check_deadline_breach(self, dispute: DisputeDB) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Check if a dispute deadline has been breached.

        AUTHORITY: SYSTEM - Called by daily scheduler.
        Detection is automatic. User cannot suppress breach detection.

        Returns (is_breached, breach_info)
        """
        # Only check disputes in DISPUTED state
        if dispute.current_state != EscalationState.DISPUTED:
            return False, None

        # Check if deadline has passed
        today = date.today()
        if today > dispute.deadline_date:
            # Check if any response has been logged
            response_count = self.db.query(DisputeResponseDB).filter(
                DisputeResponseDB.dispute_id == dispute.id
            ).count()

            if response_count == 0:
                # DEADLINE BREACH DETECTED
                breach_info = {
                    "dispute_id": dispute.id,
                    "deadline_date": dispute.deadline_date.isoformat(),
                    "days_overdue": (today - dispute.deadline_date).days,
                    "entity_type": dispute.entity_type.value,
                    "entity_name": dispute.entity_name,
                }
                return True, breach_info

        return False, None

    def process_deadline_breach(
        self,
        dispute: DisputeDB,
        breach_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process a deadline breach - create violations and transition state.

        AUTHORITY: SYSTEM - Executes automatically without user confirmation.
        Creates NO_RESPONSE response record, violations, and state transition.
        User cannot cancel or delay breach processing.
        """
        from .state_machine import EscalationStateMachine, AutomaticTransitionTriggers
        from .response_evaluator import ResponseEvaluator

        # Create NO_RESPONSE record
        response = DisputeResponseDB(
            id=str(uuid4()),
            dispute_id=dispute.id,
            response_type=ResponseType.NO_RESPONSE,
            response_date=date.today(),
            reported_by=ActorType.SYSTEM,
        )
        self.db.add(response)

        # Create paper trail entry
        paper_trail = PaperTrailDB(
            id=str(uuid4()),
            dispute_id=dispute.id,
            event_type="deadline_breach",
            actor=ActorType.SYSTEM,
            description=f"Deadline breach detected. Entity {dispute.entity_name} failed to respond within {breach_info['days_overdue']} days of deadline.",
            metadata=breach_info,
        )
        self.db.add(paper_trail)

        # Trigger state transition
        state_machine = EscalationStateMachine(self.db)
        success, message = AutomaticTransitionTriggers.deadline_breach(
            state_machine, dispute
        )

        # Create violation based on entity type
        evaluator = ResponseEvaluator(self.db)
        violations = evaluator.create_no_response_violations(dispute)

        # Update response with created violations
        response.new_violations = violations

        return {
            "breach_processed": True,
            "state_transition": success,
            "message": message,
            "violations_created": violations,
        }

    def get_upcoming_deadlines(
        self,
        days_ahead: int = 7
    ) -> List[Dict[str, Any]]:
        """Get disputes with deadlines in the next N days."""
        today = date.today()
        future_date = today + timedelta(days=days_ahead)

        disputes = self.db.query(DisputeDB).filter(
            DisputeDB.current_state == EscalationState.DISPUTED,
            DisputeDB.deadline_date >= today,
            DisputeDB.deadline_date <= future_date,
        ).all()

        return [
            {
                "dispute_id": d.id,
                "entity_name": d.entity_name,
                "entity_type": d.entity_type.value,
                "deadline_date": d.deadline_date.isoformat(),
                "days_remaining": (d.deadline_date - today).days,
            }
            for d in disputes
        ]

    def get_breached_deadlines(self) -> List[DisputeDB]:
        """Get all disputes with breached deadlines."""
        today = date.today()

        return self.db.query(DisputeDB).filter(
            DisputeDB.current_state == EscalationState.DISPUTED,
            DisputeDB.deadline_date < today,
        ).all()

    def recalculate_deadline(
        self,
        dispute: DisputeDB,
        reason: str,
        new_base_date: date,
        days: int,
    ) -> date:
        """
        Recalculate deadline (e.g., after additional info request).

        Creates paper trail entry for the change.
        """
        old_deadline = dispute.deadline_date
        new_deadline = new_base_date + timedelta(days=days)

        # Update dispute
        dispute.deadline_date = new_deadline
        dispute.updated_at = datetime.utcnow()

        # Create paper trail entry
        paper_trail = PaperTrailDB(
            id=str(uuid4()),
            dispute_id=dispute.id,
            event_type="deadline_recalculated",
            actor=ActorType.SYSTEM,
            description=f"Deadline recalculated: {reason}",
            metadata={
                "old_deadline": old_deadline.isoformat(),
                "new_deadline": new_deadline.isoformat(),
                "reason": reason,
                "days": days,
            }
        )
        self.db.add(paper_trail)

        return new_deadline

    def schedule_deadline_check(self, dispute: DisputeDB) -> SchedulerTaskDB:
        """Schedule a deadline check task for a dispute."""
        # Schedule check for day after deadline
        check_date = datetime.combine(
            dispute.deadline_date + timedelta(days=1),
            datetime.min.time()
        )

        task = SchedulerTaskDB(
            id=str(uuid4()),
            task_type="deadline_check",
            dispute_id=dispute.id,
            scheduled_for=check_date,
            status="pending",
        )
        self.db.add(task)

        return task


# =============================================================================
# DEADLINE SCHEDULER (SYSTEM-AUTHORITATIVE)
# =============================================================================
#
# This scheduler runs AUTOMATICALLY via cron/scheduled job.
# User cannot disable or override scheduled deadline checks.
# All breach detections trigger automatic violation creation.
#
# =============================================================================

class DeadlineScheduler:
    """
    Daily scheduler for deadline-related tasks.

    AUTHORITY: SYSTEM - Runs automatically, no user intervention required.
    All detected breaches result in automatic violation creation and state transitions.
    User is notified via Paper Trail only.
    """

    def __init__(self, db_session: Session):
        """Initialize with database session."""
        self.db = db_session
        self.engine = DeadlineEngine(db_session)

    def run_daily_deadline_check(self) -> Dict[str, Any]:
        """
        Run daily deadline check.

        AUTHORITY: SYSTEM - Called automatically via scheduler endpoint.
        No user confirmation required for breach processing.

        Actions:
        - Scans all open disputes
        - Detects deadline breaches
        - Creates NO_RESPONSE violations automatically
        - Triggers state transitions to NO_RESPONSE
        """
        breaches_found = []
        breaches_processed = []
        errors = []

        # Get all disputes that might have breached
        breached_disputes = self.engine.get_breached_deadlines()

        for dispute in breached_disputes:
            try:
                is_breached, breach_info = self.engine.check_deadline_breach(dispute)

                if is_breached and breach_info:
                    breaches_found.append(breach_info)

                    # Process the breach
                    result = self.engine.process_deadline_breach(dispute, breach_info)
                    breaches_processed.append({
                        "dispute_id": dispute.id,
                        "result": result,
                    })

            except Exception as e:
                errors.append({
                    "dispute_id": dispute.id,
                    "error": str(e),
                })

        # Commit all changes
        self.db.commit()

        return {
            "run_date": datetime.utcnow().isoformat(),
            "breaches_found": len(breaches_found),
            "breaches_processed": len(breaches_processed),
            "errors": len(errors),
            "details": {
                "found": breaches_found,
                "processed": breaches_processed,
                "errors": errors,
            }
        }

    def run_stall_detection(self) -> Dict[str, Any]:
        """
        Detect INVESTIGATING responses that have exceeded the 15-day limit.
        Converts them to NO_RESPONSE automatically.
        """
        from .state_machine import EscalationStateMachine, AutomaticTransitionTriggers

        stalls_found = []
        stalls_processed = []
        errors = []

        today = date.today()
        stall_threshold = today - timedelta(days=INVESTIGATING_STALL_LIMIT)

        # Find INVESTIGATING responses older than threshold
        investigating_responses = self.db.query(DisputeResponseDB).filter(
            DisputeResponseDB.response_type == ResponseType.INVESTIGATING,
            DisputeResponseDB.response_date <= stall_threshold,
        ).all()

        for response in investigating_responses:
            try:
                dispute = self.db.query(DisputeDB).get(response.dispute_id)

                # Only process if dispute is still waiting
                if dispute and dispute.current_state in [
                    EscalationState.DISPUTED,
                    EscalationState.RESPONDED,
                ]:
                    stalls_found.append({
                        "dispute_id": dispute.id,
                        "investigating_date": response.response_date.isoformat(),
                        "days_stalled": (today - response.response_date).days,
                    })

                    # Trigger stall timeout
                    state_machine = EscalationStateMachine(self.db)
                    success, message = AutomaticTransitionTriggers.stall_timeout(
                        state_machine, dispute
                    )

                    stalls_processed.append({
                        "dispute_id": dispute.id,
                        "success": success,
                        "message": message,
                    })

            except Exception as e:
                errors.append({
                    "response_id": response.id,
                    "error": str(e),
                })

        self.db.commit()

        return {
            "run_date": datetime.utcnow().isoformat(),
            "stalls_found": len(stalls_found),
            "stalls_processed": len(stalls_processed),
            "errors": len(errors),
            "details": {
                "found": stalls_found,
                "processed": stalls_processed,
                "errors": errors,
            }
        }
