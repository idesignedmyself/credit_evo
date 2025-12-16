"""
Dispute Service

Main orchestration service for the enforcement system.
Coordinates state machine, deadline engine, response evaluation,
reinsertion detection, and cross-entity intelligence.

AUTHORITY MODEL:
- USER-AUTHORIZED: create_dispute, log_response, confirm_mailing
- SYSTEM-AUTHORITATIVE: deadline breaches, reinsertion detection, escalation, violation creation

The user is a FACTUAL REPORTER only. The user:
- Initiates disputes (provides facts about what was sent)
- Logs entity responses (reports what was received)
- Uploads reports (provides data for reinsertion detection)

The system is the LEGAL DECISION-MAKER. The system:
- Creates violations based on statutory requirements
- Escalates disputes based on entity conduct
- Detects reinsertions and creates automatic violations
- Applies FDCPA guardrails to ensure correct statute citation
"""
from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from uuid import uuid4
import hashlib

from sqlalchemy.orm import Session

from ...models.db_models import (
    DisputeDB, DisputeResponseDB, PaperTrailDB, ReinsertionWatchDB,
    EscalationState, ResponseType, EntityType, ActorType, DisputeSource,
    DisputeStatus
)
from .state_machine import EscalationStateMachine, AutomaticTransitionTriggers
from .deadline_engine import DeadlineEngine
from .response_evaluator import ResponseEvaluator, FDCPA1692gGuardrail
from .reinsertion_detector import ReinsertionDetector
from .cross_entity_intelligence import CrossEntityIntelligence


# =============================================================================
# DISPUTE SERVICE
# =============================================================================

class DisputeService:
    """
    Main service for dispute management.

    Orchestrates all enforcement subsystems:
    - State machine transitions
    - Deadline tracking
    - Response evaluation
    - Reinsertion detection
    - Cross-entity intelligence
    """

    def __init__(self, db_session: Session):
        """Initialize with database session."""
        self.db = db_session
        self.state_machine = EscalationStateMachine(db_session)
        self.deadline_engine = DeadlineEngine(db_session)
        self.response_evaluator = ResponseEvaluator(db_session)
        self.reinsertion_detector = ReinsertionDetector(db_session)
        self.cross_entity = CrossEntityIntelligence(db_session)

    # =========================================================================
    # DISPUTE CREATION
    # =========================================================================

    def create_dispute(
        self,
        user_id: str,
        violation_id: str,
        entity_type: EntityType,
        entity_name: str,
        dispute_date: date,
        source: DisputeSource = DisputeSource.DIRECT,
        letter_id: str = None,
        account_fingerprint: str = None,
        violation_data: Dict[str, Any] = None,
        has_validation_request: bool = False,
        collection_continued: bool = False,
    ) -> Dict[str, Any]:
        """
        Create a new dispute.

        User-authorized action - user initiates dispute.
        """
        # Calculate deadline
        deadline_date, deadline_meta = self.deadline_engine.calculate_deadline(
            dispute_date=dispute_date,
            source=source,
            entity_type=entity_type,
        )

        # Create dispute
        dispute = DisputeDB(
            id=str(uuid4()),
            user_id=user_id,
            violation_id=violation_id,
            entity_type=entity_type,
            entity_name=entity_name,
            dispute_date=dispute_date,
            deadline_date=deadline_date,
            source=source,
            status=DisputeStatus.OPEN,
            current_state=EscalationState.DISPUTED,
            letter_id=letter_id,
            account_fingerprint=account_fingerprint,
            original_violation_data=violation_data,
            has_validation_request=has_validation_request,
            collection_continued=collection_continued,
        )
        self.db.add(dispute)

        # Create initial paper trail entry
        paper_trail = PaperTrailDB(
            id=str(uuid4()),
            dispute_id=dispute.id,
            event_type="dispute_created",
            actor=ActorType.USER,
            description=f"Dispute created against {entity_name} ({entity_type.value}). Deadline: {deadline_date.isoformat()}",
            event_metadata={
                "entity_type": entity_type.value,
                "entity_name": entity_name,
                "source": source.value,
                "deadline_date": deadline_date.isoformat(),
                **deadline_meta,
            }
        )
        self.db.add(paper_trail)

        # Schedule deadline check
        self.deadline_engine.schedule_deadline_check(dispute)

        self.db.commit()

        return {
            "dispute_id": dispute.id,
            "entity_type": entity_type.value,
            "entity_name": entity_name,
            "dispute_date": dispute_date.isoformat(),
            "deadline_date": deadline_date.isoformat(),
            "current_state": dispute.current_state.value,
            "deadline_info": deadline_meta,
        }

    # =========================================================================
    # RESPONSE LOGGING
    # =========================================================================

    def log_response(
        self,
        dispute_id: str,
        response_type: ResponseType,
        response_date: date = None,
        updated_fields: Dict[str, Any] = None,
        rejection_reason: str = None,
        has_5_day_notice: bool = None,
        has_specific_reason: bool = None,
        has_missing_info_request: bool = None,
        evidence_path: str = None,
    ) -> Dict[str, Any]:
        """
        Log a response from an entity.

        AUTHORITY: USER - User reports factual information about response received.
        AUTHORITY: SYSTEM - After user logs response, system:
        - Evaluates response against statutory requirements
        - Creates violations automatically if warranted
        - Triggers state transitions based on evaluation
        - Starts REINSERTION WATCH if response is DELETED (90-day monitoring)
        - Runs cross-entity analysis for pattern detection
        """
        dispute = self.db.query(DisputeDB).get(dispute_id)
        if not dispute:
            return {"error": "Dispute not found"}

        # Create response record
        response = DisputeResponseDB(
            id=str(uuid4()),
            dispute_id=dispute_id,
            response_type=response_type,
            response_date=response_date or date.today(),
            reported_by=ActorType.USER,
            updated_fields=updated_fields,
            rejection_reason=rejection_reason,
            has_5_day_notice=has_5_day_notice,
            has_specific_reason=has_specific_reason,
            has_missing_info_request=has_missing_info_request,
            evidence_path=evidence_path,
            evidence_hash=self._hash_file(evidence_path) if evidence_path else None,
        )
        self.db.add(response)

        # Create paper trail
        paper_trail = PaperTrailDB(
            id=str(uuid4()),
            dispute_id=dispute_id,
            event_type="response_logged",
            actor=ActorType.USER,
            description=f"Response logged: {response_type.value}",
            evidence_hash=response.evidence_hash,
            event_metadata={
                "response_type": response_type.value,
                "response_date": (response_date or date.today()).isoformat(),
            }
        )
        self.db.add(paper_trail)

        # Update dispute status
        dispute.status = DisputeStatus.RESPONDED

        # Evaluate response (system action)
        evaluation = self.response_evaluator.evaluate_response(dispute, response)

        # Transition state based on evaluation
        if evaluation.get("next_state"):
            next_state = evaluation["next_state"]
            if isinstance(next_state, EscalationState):
                # Transition to RESPONDED first
                self.state_machine.transition(
                    dispute=dispute,
                    to_state=EscalationState.RESPONDED,
                    trigger=f"response_logged_{response_type.value}",
                    actor=ActorType.USER,
                )

                # Then transition to evaluated state if non-compliant
                if evaluation.get("escalation_queued") and next_state == EscalationState.NON_COMPLIANT:
                    statutes = [v.get("statute") for v in evaluation.get("violations_created", [])]
                    AutomaticTransitionTriggers.non_compliance_confirmed(
                        self.state_machine, dispute, statutes
                    )

        # Run cross-entity analysis if we have enough data
        if dispute.account_fingerprint:
            cross_entity_result = self.cross_entity.analyze_responses(
                dispute.user_id, dispute.account_fingerprint
            )
            if cross_entity_result.get("patterns_detected"):
                evaluation["cross_entity_patterns"] = cross_entity_result["patterns_detected"]

        self.db.commit()

        return {
            "response_id": response.id,
            "response_type": response_type.value,
            "evaluation": evaluation,
            "current_state": dispute.current_state.value,
        }

    # =========================================================================
    # CONFIRM MAILING
    # =========================================================================

    def confirm_mailing(
        self,
        dispute_id: str,
        mailed_date: date,
        tracking_number: str = None,
    ) -> Dict[str, Any]:
        """
        Confirm that dispute letter was mailed.

        User-authorized action - starts the deadline clock.
        """
        dispute = self.db.query(DisputeDB).get(dispute_id)
        if not dispute:
            return {"error": "Dispute not found"}

        # Update dispute date if different from creation
        if mailed_date != dispute.dispute_date:
            old_deadline = dispute.deadline_date
            new_deadline = self.deadline_engine.recalculate_deadline(
                dispute=dispute,
                reason="Mailing date confirmed",
                new_base_date=mailed_date,
                days=30 if dispute.source == DisputeSource.DIRECT else 45,
            )

        # Create paper trail
        paper_trail = PaperTrailDB(
            id=str(uuid4()),
            dispute_id=dispute_id,
            event_type="mailing_confirmed",
            actor=ActorType.USER,
            description=f"Dispute letter mailed on {mailed_date.isoformat()}",
            event_metadata={
                "mailed_date": mailed_date.isoformat(),
                "tracking_number": tracking_number,
                "deadline_date": dispute.deadline_date.isoformat(),
            }
        )
        self.db.add(paper_trail)

        self.db.commit()

        return {
            "dispute_id": dispute_id,
            "mailed_date": mailed_date.isoformat(),
            "deadline_date": dispute.deadline_date.isoformat(),
            "tracking_number": tracking_number,
        }

    # =========================================================================
    # TIMELINE & STATUS
    # =========================================================================

    def get_dispute_timeline(self, dispute_id: str) -> List[Dict[str, Any]]:
        """
        Get the complete paper trail for a dispute.

        Read-only, immutable record.
        """
        entries = self.db.query(PaperTrailDB).filter(
            PaperTrailDB.dispute_id == dispute_id
        ).order_by(PaperTrailDB.created_at).all()

        return [
            {
                "id": e.id,
                "event_type": e.event_type,
                "actor": e.actor.value,
                "description": e.description,
                "timestamp": e.created_at.isoformat(),
                "evidence_hash": e.evidence_hash,
                "artifact_type": e.artifact_type,
                "metadata": e.event_metadata,
            }
            for e in entries
        ]

    def get_dispute_state(self, dispute_id: str) -> Dict[str, Any]:
        """
        Get the current state of a dispute.

        Includes state machine position, available actions, and deadlines.
        """
        dispute = self.db.query(DisputeDB).get(dispute_id)
        if not dispute:
            return {"error": "Dispute not found"}

        state_config = self.state_machine.get_state_config(dispute.current_state)

        # Calculate days until deadline
        today = date.today()
        days_to_deadline = (dispute.deadline_date - today).days if dispute.deadline_date else None

        return {
            "dispute_id": dispute_id,
            "current_state": dispute.current_state.value,
            "state_description": state_config.get("description"),
            "tone_posture": state_config.get("tone_posture"),
            "available_outputs": state_config.get("outputs", []),
            "next_states": [s.value for s in state_config.get("allowed_transitions", [])],
            "is_terminal": self.state_machine.is_terminal_state(dispute.current_state),
            "deadline_date": dispute.deadline_date.isoformat() if dispute.deadline_date else None,
            "days_to_deadline": days_to_deadline,
            "status": dispute.status.value,
            "entity_type": dispute.entity_type.value,
            "entity_name": dispute.entity_name,
        }

    def get_system_events(self, dispute_id: str) -> Dict[str, Any]:
        """
        Get system-triggered events for a dispute.

        AUTHORITY: READ-ONLY - User can VIEW system events but cannot modify them.
        Shows:
        - Pending deadlines (SYSTEM will auto-create violations on breach)
        - Reinsertion watches (SYSTEM monitors for 90 days after DELETED)
        - Escalation history (SYSTEM-triggered state transitions)
        """
        dispute = self.db.query(DisputeDB).get(dispute_id)
        if not dispute:
            return {"error": "Dispute not found"}

        # Get reinsertion watches
        watches = self.db.query(ReinsertionWatchDB).filter(
            ReinsertionWatchDB.dispute_id == dispute_id
        ).all()

        # Get escalation log
        escalations = self.db.query(
            PaperTrailDB
        ).filter(
            PaperTrailDB.dispute_id == dispute_id,
            PaperTrailDB.actor == ActorType.SYSTEM,
        ).order_by(PaperTrailDB.created_at.desc()).limit(10).all()

        today = date.today()

        return {
            "dispute_id": dispute_id,
            "deadline": {
                "date": dispute.deadline_date.isoformat() if dispute.deadline_date else None,
                "days_remaining": (dispute.deadline_date - today).days if dispute.deadline_date else None,
                "is_breached": today > dispute.deadline_date if dispute.deadline_date else False,
            },
            "reinsertion_watches": [
                {
                    "id": w.id,
                    "account_fingerprint": w.account_fingerprint,
                    "status": w.status.value,
                    "monitoring_end": w.monitoring_end.isoformat(),
                    "days_remaining": (w.monitoring_end - today).days,
                }
                for w in watches
            ],
            "recent_system_events": [
                {
                    "event_type": e.event_type,
                    "description": e.description,
                    "timestamp": e.created_at.isoformat(),
                }
                for e in escalations
            ],
        }

    # =========================================================================
    # ARTIFACT GENERATION
    # =========================================================================

    def get_available_artifacts(self, dispute_id: str) -> List[str]:
        """Get available artifact types for the current state."""
        dispute = self.db.query(DisputeDB).get(dispute_id)
        if not dispute:
            return []

        return self.state_machine.get_available_outputs(dispute.current_state)

    def request_artifact(
        self,
        dispute_id: str,
        artifact_type: str,
    ) -> Dict[str, Any]:
        """
        Request generation of an artifact.

        User-authorized action.
        """
        dispute = self.db.query(DisputeDB).get(dispute_id)
        if not dispute:
            return {"error": "Dispute not found"}

        available = self.get_available_artifacts(dispute_id)
        if artifact_type not in available:
            return {
                "error": f"Artifact {artifact_type} not available in state {dispute.current_state.value}",
                "available": available,
            }

        # Create paper trail entry for artifact request
        paper_trail = PaperTrailDB(
            id=str(uuid4()),
            dispute_id=dispute_id,
            event_type="artifact_requested",
            actor=ActorType.USER,
            description=f"Artifact requested: {artifact_type}",
            artifact_type=artifact_type,
            event_metadata={
                "artifact_type": artifact_type,
                "state_at_request": dispute.current_state.value,
            }
        )
        self.db.add(paper_trail)
        self.db.commit()

        # TODO: Integrate with letter generation system
        return {
            "artifact_requested": artifact_type,
            "status": "queued",
            "message": f"Artifact {artifact_type} has been queued for generation",
        }

    # =========================================================================
    # USER DISPUTES LIST
    # =========================================================================

    def get_user_disputes(
        self,
        user_id: str,
        status: DisputeStatus = None,
        state: EscalationState = None,
    ) -> List[Dict[str, Any]]:
        """Get all disputes for a user."""
        query = self.db.query(DisputeDB).filter(DisputeDB.user_id == user_id)

        if status:
            query = query.filter(DisputeDB.status == status)
        if state:
            query = query.filter(DisputeDB.current_state == state)

        disputes = query.order_by(DisputeDB.created_at.desc()).all()

        today = date.today()

        return [
            {
                "id": d.id,
                "entity_type": d.entity_type.value,
                "entity_name": d.entity_name,
                "status": d.status.value,
                "current_state": d.current_state.value,
                "dispute_date": d.dispute_date.isoformat(),
                "deadline_date": d.deadline_date.isoformat() if d.deadline_date else None,
                "days_to_deadline": (d.deadline_date - today).days if d.deadline_date else None,
                "created_at": d.created_at.isoformat(),
            }
            for d in disputes
        ]

    # =========================================================================
    # UTILITIES
    # =========================================================================

    def _hash_file(self, file_path: str) -> Optional[str]:
        """Generate SHA-256 hash of a file."""
        if not file_path:
            return None
        try:
            with open(file_path, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception:
            return None
