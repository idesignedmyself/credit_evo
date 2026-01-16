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

EXECUTION LEDGER INTEGRATION (B7):
- Executions born at confirm_mailing() (AUTHORITY MOMENT)
- Responses emitted at log_response()
- Suppression events emitted when action is intentionally blocked
- All events linked by dispute_session_id
"""
from datetime import date, datetime, timedelta, timezone
from typing import Optional, List, Dict, Any, Tuple
from uuid import uuid4
import hashlib

from sqlalchemy.orm import Session

from ...models.db_models import (
    DisputeDB, DisputeResponseDB, PaperTrailDB, ReinsertionWatchDB,
    Tier2ResponseDB, Tier2ResponseType,
    EscalationState, ResponseType, EntityType, ActorType, DisputeSource,
    DisputeStatus, SuppressionReason, LetterDB, UserDB
)
from .state_machine import EscalationStateMachine, AutomaticTransitionTriggers
from .deadline_engine import DeadlineEngine
from .response_evaluator import ResponseEvaluator, FDCPA1692gGuardrail
from .reinsertion_detector import ReinsertionDetector
from .cross_entity_intelligence import CrossEntityIntelligence
from .execution_ledger import ExecutionLedgerService
from .dispute_session import DisputeSessionService
from .tier3_promotion import Tier3PromotionService


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
        # Execution Ledger services (B7)
        self.ledger = ExecutionLedgerService(db_session)
        self.session_service = DisputeSessionService(db_session)

    # =========================================================================
    # DISPUTE CREATION
    # =========================================================================

    def create_dispute(
        self,
        user_id: str,
        entity_type: EntityType,
        entity_name: str,
        dispute_date: date = None,
        source: DisputeSource = DisputeSource.DIRECT,
        violation_id: str = None,
        letter_id: str = None,
        account_fingerprint: str = None,
        violation_data: Dict[str, Any] = None,
        has_validation_request: bool = False,
        collection_continued: bool = False,
    ) -> Dict[str, Any]:
        """
        Create a new dispute.

        User-authorized action - user initiates dispute.

        If dispute_date is None, creates dispute in "pending tracking" state.
        The deadline clock doesn't start until user calls start_tracking/confirm_mailing.
        """
        # If dispute_date provided, calculate deadline and start tracking immediately
        deadline_date = None
        deadline_meta = {}
        tracking_started = False

        if dispute_date:
            deadline_date, deadline_meta = self.deadline_engine.calculate_deadline(
                dispute_date=dispute_date,
                source=source,
                entity_type=entity_type,
            )
            tracking_started = True

        # Fetch discrepancies from letter if letter_id provided
        discrepancies_data = None
        if letter_id:
            from app.models.db_models import LetterDB
            letter = self.db.query(LetterDB).filter(LetterDB.id == letter_id).first()
            if letter and letter.discrepancies_cited:
                discrepancies_data = letter.discrepancies_cited

        # Create dispute
        dispute = DisputeDB(
            id=str(uuid4()),
            user_id=user_id,
            violation_id=violation_id,
            entity_type=entity_type,
            entity_name=entity_name,
            dispute_date=dispute_date,
            deadline_date=deadline_date,
            tracking_started=tracking_started,
            source=source,
            status=DisputeStatus.OPEN,
            current_state=EscalationState.DETECTED if not tracking_started else EscalationState.DISPUTED,
            letter_id=letter_id,
            account_fingerprint=account_fingerprint,
            original_violation_data=violation_data,
            discrepancies_data=discrepancies_data,  # Cross-bureau discrepancies from letter
            has_validation_request=has_validation_request,
            collection_continued=collection_continued,
        )
        self.db.add(dispute)

        # Create initial paper trail entry
        if tracking_started:
            description = f"Dispute created against {entity_name} ({entity_type.value}). Deadline: {deadline_date.isoformat()}"
        else:
            description = f"Dispute tracking initiated against {entity_name} ({entity_type.value}). Awaiting send date to start clock."

        paper_trail = PaperTrailDB(
            id=str(uuid4()),
            dispute_id=dispute.id,
            event_type="dispute_created",
            actor=ActorType.USER,
            description=description,
            event_metadata={
                "entity_type": entity_type.value,
                "entity_name": entity_name,
                "source": source.value,
                "tracking_started": tracking_started,
                "deadline_date": deadline_date.isoformat() if deadline_date else None,
                **deadline_meta,
            }
        )
        self.db.add(paper_trail)

        # Only schedule deadline check if tracking has started
        if tracking_started:
            self.deadline_engine.schedule_deadline_check(dispute)

        self.db.commit()

        return {
            "dispute_id": dispute.id,
            "entity_type": entity_type.value,
            "entity_name": entity_name,
            "dispute_date": dispute_date.isoformat() if dispute_date else None,
            "deadline_date": deadline_date.isoformat() if deadline_date else None,
            "tracking_started": tracking_started,
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
        violation_id: str = None,
        response_date: date = None,
        updated_fields: Dict[str, Any] = None,
        rejection_reason: str = None,
        has_5_day_notice: bool = None,
        has_specific_reason: bool = None,
        has_missing_info_request: bool = None,
        evidence_path: str = None,
        dispute_session_id: str = None,
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

        EXECUTION LEDGER: Emits execution response event.
        """
        dispute = self.db.query(DisputeDB).get(dispute_id)
        if not dispute:
            return {"error": "Dispute not found"}

        evidence_hash = self._hash_file(evidence_path) if evidence_path else None

        # Create response record
        response = DisputeResponseDB(
            id=str(uuid4()),
            dispute_id=dispute_id,
            violation_id=violation_id,
            response_type=response_type,
            response_date=response_date or date.today(),
            reported_by=ActorType.USER,
            updated_fields=updated_fields,
            rejection_reason=rejection_reason,
            has_5_day_notice=has_5_day_notice,
            has_specific_reason=has_specific_reason,
            has_missing_info_request=has_missing_info_request,
            evidence_path=evidence_path,
            evidence_hash=evidence_hash,
        )
        self.db.add(response)

        # Create paper trail
        paper_trail = PaperTrailDB(
            id=str(uuid4()),
            dispute_id=dispute_id,
            event_type="response_logged",
            actor=ActorType.USER,
            description=f"Response logged: {response_type.value}",
            evidence_hash=evidence_hash,
            event_metadata={
                "response_type": response_type.value,
                "response_date": (response_date or date.today()).isoformat(),
                "dispute_session_id": dispute_session_id,
            }
        )
        self.db.add(paper_trail)

        # Update dispute status
        dispute.status = DisputeStatus.RESPONDED

        # =====================================================================
        # TIER 2: Extract contradictions for examiner check
        # =====================================================================
        original_contradictions = []
        cross_bureau_contradictions = []

        if dispute.original_violation_data:
            # Handle both dict format (from audit) and list format (from letter generation)
            if isinstance(dispute.original_violation_data, dict):
                # Extract Tier 1 contradictions that were detected during audit
                original_contradictions = dispute.original_violation_data.get("contradictions", [])
                # Extract cross-bureau contradictions (same tradeline across bureaus)
                cross_bureau_contradictions = dispute.original_violation_data.get("cross_bureau_contradictions", [])
            # If it's a list, there are no nested contradictions to extract

        # Evaluate response (system action) - now with Tier 2 examiner check
        evaluation = self.response_evaluator.evaluate_response(
            dispute=dispute,
            response=response,
            original_contradictions=original_contradictions,
            cross_bureau_contradictions=cross_bureau_contradictions,
        )

        # =================================================================
        # EXECUTION LEDGER: Emit response event
        # =================================================================
        # Find the execution event for this dispute
        execution = self.ledger.get_execution_for_dispute(dispute_id)

        if execution:
            # Detect field changes for ledger tracking
            balance_changed = "balance" in (updated_fields or {})
            dofd_changed = "dofd" in (updated_fields or {}) or "date_of_first_delinquency" in (updated_fields or {})
            status_changed = "status" in (updated_fields or {}) or "account_status" in (updated_fields or {})

            # Use the execution's session ID if not provided
            session_id = dispute_session_id or execution.dispute_session_id

            # Extract Tier 2 examiner results from evaluation
            examiner_check = evaluation.get("examiner_check", {})

            self.ledger.emit_execution_response(
                execution_id=execution.id,
                dispute_session_id=session_id,
                response_type=response_type.value,
                response_received_at=datetime.combine(response_date or date.today(), datetime.min.time()),
                bureau=dispute.entity_name if dispute.entity_type == EntityType.CRA else None,
                response_reason=rejection_reason,
                document_hash=evidence_hash,
                artifact_pointer=evidence_path,
                balance_changed=balance_changed,
                dofd_changed=dofd_changed,
                status_changed=status_changed,
                reinsertion_flag=response_type == ResponseType.REINSERTION,
                # Tier 2: Examiner Standard fields
                examiner_standard_result=examiner_check.get("standard_result"),
                examiner_failure_reason=examiner_check.get("failure_reason"),
                response_layer_violation_id=evaluation.get("response_layer_violation_id"),
                escalation_basis=evaluation.get("escalation_basis"),
            )

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
            "execution_response_logged": execution is not None,
        }

    # =========================================================================
    # CONFIRM MAILING
    # =========================================================================

    def confirm_mailing(
        self,
        dispute_id: str,
        mailed_date: date,
        tracking_number: str = None,
        dispute_session_id: str = None,
    ) -> Dict[str, Any]:
        """
        Confirm that dispute letter was mailed.

        User-authorized action - starts the deadline clock.
        This is also the "Start Tracking" action for disputes created without a date.

        EXECUTION LEDGER: This is the AUTHORITY MOMENT.
        Executions are born here, not at plan-time.
        """
        dispute = self.db.query(DisputeDB).get(dispute_id)
        if not dispute:
            return {"error": "Dispute not found"}

        # Get user for credit goal context
        user = self.db.query(UserDB).filter(UserDB.id == dispute.user_id).first()
        credit_goal = user.credit_goal if user else "credit_hygiene"

        # Generate dispute_session_id if not provided
        if not dispute_session_id:
            # Handle both dict and list formats for original_violation_data
            report_id = None
            if dispute.original_violation_data and isinstance(dispute.original_violation_data, dict):
                report_id = dispute.original_violation_data.get("report_id")
            dispute_session_id = self.session_service.create_session(
                user_id=dispute.user_id,
                report_id=report_id,
                credit_goal=credit_goal,
            )

        # Check suppression conditions before emitting execution event
        suppression = self._check_suppression_conditions(
            dispute_session_id=dispute_session_id,
            user_id=dispute.user_id,
            account_fingerprint=dispute.account_fingerprint,
            credit_goal=credit_goal,
        )

        if suppression:
            return {
                "error": "Action suppressed",
                "reason": suppression["reason"],
                "suppression_code": suppression["code"],
            }

        # Check if this is starting tracking for the first time
        is_first_tracking = not dispute.tracking_started

        if is_first_tracking:
            # First time tracking - calculate deadline from scratch
            deadline_date, deadline_meta = self.deadline_engine.calculate_deadline(
                dispute_date=mailed_date,
                source=dispute.source,
                entity_type=dispute.entity_type,
            )
            dispute.dispute_date = mailed_date
            dispute.deadline_date = deadline_date
            dispute.tracking_started = True
            dispute.current_state = EscalationState.DISPUTED

            # Schedule deadline check now that tracking has started
            self.deadline_engine.schedule_deadline_check(dispute)

            event_type = "tracking_started"
            description = f"Tracking started. Letter mailed on {mailed_date.isoformat()}. Deadline: {deadline_date.isoformat()}"
        else:
            # Already tracking - update if mailed date is different
            if mailed_date != dispute.dispute_date:
                self.deadline_engine.recalculate_deadline(
                    dispute=dispute,
                    reason="Mailing date confirmed",
                    new_base_date=mailed_date,
                    days=30 if dispute.source == DisputeSource.DIRECT else 45,
                )
            deadline_date = dispute.deadline_date
            event_type = "mailing_confirmed"
            description = f"Dispute letter mailed on {mailed_date.isoformat()}"

        # Create paper trail
        paper_trail = PaperTrailDB(
            id=str(uuid4()),
            dispute_id=dispute_id,
            event_type=event_type,
            actor=ActorType.USER,
            description=description,
            event_metadata={
                "mailed_date": mailed_date.isoformat(),
                "tracking_number": tracking_number,
                "deadline_date": dispute.deadline_date.isoformat() if dispute.deadline_date else None,
                "is_first_tracking": is_first_tracking,
                "dispute_session_id": dispute_session_id,
            }
        )
        self.db.add(paper_trail)

        # =================================================================
        # EXECUTION LEDGER: Emit execution event (AUTHORITY MOMENT)
        # =================================================================
        letter = self.db.query(LetterDB).filter(LetterDB.id == dispute.letter_id).first() if dispute.letter_id else None

        # Handle violation_data which may be a list or a dict
        raw_violation_data = dispute.original_violation_data
        if isinstance(raw_violation_data, list):
            # If it's a list, use the first violation's data
            violation_data = raw_violation_data[0] if raw_violation_data else {}
        else:
            violation_data = raw_violation_data or {}

        execution_event = self.ledger.emit_execution_event(
            dispute_session_id=dispute_session_id,
            user_id=dispute.user_id,
            executed_at=datetime.combine(mailed_date, datetime.min.time()),
            action_type=self._infer_action_type(violation_data),
            credit_goal=credit_goal,
            report_id=violation_data.get("report_id"),
            account_id=violation_data.get("account_id"),
            dispute_id=dispute.id,
            letter_id=dispute.letter_id,
            violation_type=violation_data.get("violation_type"),
            contradiction_rule=violation_data.get("rule_code"),
            bureau=violation_data.get("bureau") or (dispute.entity_name if dispute.entity_type == EntityType.CRA else None),
            furnisher_type=violation_data.get("furnisher_type"),
            creditor_name=violation_data.get("creditor_name") or dispute.entity_name,
            account_fingerprint=dispute.account_fingerprint,
            gate_applied=violation_data.get("gate_applied"),
            risk_flags=violation_data.get("risk_flags"),
            document_hash=self._hash_content(letter.content if letter else None),
            due_by=datetime.combine(dispute.deadline_date, datetime.min.time()) if dispute.deadline_date else None,
        )

        self.db.commit()

        return {
            "dispute_id": dispute_id,
            "mailed_date": mailed_date.isoformat(),
            "deadline_date": dispute.deadline_date.isoformat() if dispute.deadline_date else None,
            "tracking_number": tracking_number,
            "tracking_started": dispute.tracking_started,
            "dispute_session_id": dispute_session_id,
            "execution_id": execution_event.id,
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
        letter_id: str = None,
    ) -> List[Dict[str, Any]]:
        """Get all disputes for a user."""
        query = self.db.query(DisputeDB).filter(DisputeDB.user_id == user_id)

        if status:
            query = query.filter(DisputeDB.status == status)
        if state:
            query = query.filter(DisputeDB.current_state == state)
        if letter_id:
            query = query.filter(DisputeDB.letter_id == letter_id)

        disputes = query.order_by(DisputeDB.created_at.desc()).all()

        today = date.today()
        results = []

        for d in disputes:
            # Build response lookup by violation_id
            response_lookup = {}
            # Also track responses without violation_id (legacy) by index
            responses_without_vid = []
            for resp in d.responses:
                if resp.violation_id:
                    response_lookup[resp.violation_id] = resp.response_type.value
                else:
                    # Response logged before violation_id was added - track separately
                    responses_without_vid.append(resp.response_type.value)

            # Enrich violation_data with logged responses
            # Handle both list format (from letter generation) and dict format (legacy)
            raw_violation_data = d.original_violation_data or []

            # Normalize: if dict format, extract the list from common keys
            if isinstance(raw_violation_data, dict):
                # Legacy dict format might have violations under various keys
                violation_data = (
                    raw_violation_data.get("violations") or
                    raw_violation_data.get("contradictions") or
                    raw_violation_data.get("items") or
                    []
                )
            else:
                # Already a list
                violation_data = raw_violation_data

            enriched_violations = []
            responses_without_vid_idx = 0  # Track which legacy response to assign next

            for idx, v in enumerate(violation_data):
                # Skip non-dict items (shouldn't happen but be defensive)
                if not isinstance(v, dict):
                    continue
                v_copy = dict(v)

                # Generate violation_id if not present (for contradictions which use account_id)
                # This ensures consistent ID across frontend and backend
                if not v_copy.get("violation_id"):
                    # Use account_id if available, otherwise generate from index
                    v_copy["violation_id"] = v.get("account_id") or f"{d.id}-v{idx}"

                v_id = v_copy.get("violation_id")

                # Try to match by violation_id first
                if v_id and v_id in response_lookup:
                    v_copy["logged_response"] = response_lookup[v_id]
                # Fallback: assign legacy responses (without violation_id) in order
                elif responses_without_vid_idx < len(responses_without_vid):
                    v_copy["logged_response"] = responses_without_vid[responses_without_vid_idx]
                    responses_without_vid_idx += 1

                enriched_violations.append(v_copy)

            results.append({
                "id": d.id,
                "entity_type": d.entity_type.value,
                "entity_name": d.entity_name,
                "status": d.status.value,
                "current_state": d.current_state.value,
                "tracking_started": d.tracking_started,
                "dispute_date": d.dispute_date.isoformat() if d.dispute_date else None,
                "deadline_date": d.deadline_date.isoformat() if d.deadline_date else None,
                "days_to_deadline": (d.deadline_date - today).days if d.deadline_date else None,
                "created_at": d.created_at.isoformat(),
                "violation_data": enriched_violations,
                "discrepancies_data": d.discrepancies_data or [],  # Cross-bureau discrepancies
                # Tier-2/Tier-3 tracking fields
                "tier_reached": d.tier_reached,
                "locked": d.locked,
                "tier2_notice_sent": d.tier2_notice_sent,
                "tier2_notice_sent_at": (d.tier2_notice_sent_at.isoformat() + "Z") if d.tier2_notice_sent_at else None,
                # UI State Persistence
                "ui_state": d.ui_state,
            })

        return results

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

    def _hash_content(self, content: str) -> Optional[str]:
        """Generate SHA-256 hash of content string."""
        if not content:
            return None
        return hashlib.sha256(content.encode()).hexdigest()

    def _infer_action_type(self, violation_data: Dict[str, Any]) -> str:
        """
        Infer action type from violation data.

        Maps violation characteristics to action types:
        - DELETE_DEMAND: For contradictions, FCRA obsolete items
        - CORRECT_DEMAND: For inaccuracies that can be corrected
        - MOV_DEMAND: For verification challenges
        - DOFD_DEMAND: For DOFD-related issues
        - OWNERSHIP_CHAIN_DEMAND: For collection/debt buyer chain issues
        """
        if not violation_data:
            return "DELETE_DEMAND"

        rule_code = violation_data.get("rule_code", "")
        violation_type = str(violation_data.get("violation_type", "")).lower()
        furnisher_type = str(violation_data.get("furnisher_type", "")).upper()

        # DOFD issues
        if rule_code in {"D1", "D2", "D3"} or "dofd" in violation_type:
            return "DOFD_DEMAND"

        # Ownership chain issues
        if furnisher_type in {"COLLECTION", "DEBT_BUYER", "COLLECTOR"}:
            if not violation_data.get("has_original_creditor"):
                return "OWNERSHIP_CHAIN_DEMAND"

        # Contradictions = DELETE_DEMAND
        if violation_data.get("source_type") == "CONTRADICTION":
            return "DELETE_DEMAND"

        # High severity = DELETE_DEMAND
        severity = str(violation_data.get("severity", "")).upper()
        if severity in {"CRITICAL", "HIGH"}:
            return "DELETE_DEMAND"

        # Medium severity = CORRECT_DEMAND
        if severity == "MEDIUM":
            return "CORRECT_DEMAND"

        # Default
        return "DELETE_DEMAND"

    def _check_suppression_conditions(
        self,
        dispute_session_id: str,
        user_id: str,
        account_fingerprint: Optional[str],
        credit_goal: str,
    ) -> Optional[Dict[str, str]]:
        """
        Check if action should be suppressed.

        Suppression reasons:
        - DUPLICATE_IN_FLIGHT: Already have a pending execution for this account
        - COOLDOWN_ACTIVE: Too soon since last execution for this account

        Returns None if no suppression, otherwise dict with reason and code.
        Emits suppression event to ledger for admin/audit tracking.
        """
        if not account_fingerprint:
            return None

        # Check for duplicate in-flight
        if self.session_service.has_pending_execution(account_fingerprint, user_id):
            self.ledger.emit_suppression_event(
                dispute_session_id=dispute_session_id,
                user_id=user_id,
                suppression_reason=SuppressionReason.DUPLICATE_IN_FLIGHT,
                credit_goal=credit_goal,
            )
            return {
                "reason": "A dispute is already in progress for this account",
                "code": SuppressionReason.DUPLICATE_IN_FLIGHT.value,
            }

        # Check cooldown (30 days between executions on same account)
        last_execution = self.session_service.get_last_execution_date(
            account_fingerprint, user_id
        )
        if last_execution:
            days_since = (datetime.now(timezone.utc) - last_execution).days
            if days_since < 30:
                self.ledger.emit_suppression_event(
                    dispute_session_id=dispute_session_id,
                    user_id=user_id,
                    suppression_reason=SuppressionReason.COOLDOWN_ACTIVE,
                    credit_goal=credit_goal,
                )
                return {
                    "reason": f"Cooldown active. Last dispute sent {days_since} days ago. Wait {30 - days_since} more days.",
                    "code": SuppressionReason.COOLDOWN_ACTIVE.value,
                }

        return None

    # =========================================================================
    # TIER-2 NOTICE SENT TRACKING
    # =========================================================================

    def mark_tier2_notice_sent(self, dispute_id: str) -> Dict[str, Any]:
        """
        Mark a Tier-2 supervisory notice as sent.

        This is the authoritative event that transitions the dispute to Tier-2.
        After this, the Tier-2 adjudication UI becomes visible.

        GUARDRAILS:
        - Cannot unmark once sent
        - Cannot mark sent multiple times
        - Must be called before logging Tier-2 response

        Args:
            dispute_id: The dispute to mark as sent

        Returns:
            Dict with tier2_notice_sent status and timestamp

        Raises:
            ValueError: If dispute not found or already marked sent
        """
        dispute = self.db.query(DisputeDB).filter(DisputeDB.id == dispute_id).first()
        if not dispute:
            raise ValueError(f"Dispute not found: {dispute_id}")

        # Prevent double-marking
        if dispute.tier2_notice_sent:
            raise ValueError("Tier-2 notice already marked as sent. Cannot send multiple times.")

        # Prevent marking if already at Tier-3
        if dispute.locked:
            raise ValueError("Dispute is locked at Tier-3. Cannot modify Tier-2 notice status.")

        # Mark as sent
        now = datetime.now(timezone.utc)
        dispute.tier2_notice_sent = True
        dispute.tier2_notice_sent_at = now

        # Transition to Tier-2 if not already
        if dispute.tier_reached < 2:
            dispute.tier_reached = 2

        # Create paper trail entry
        paper_trail = PaperTrailDB(
            id=str(uuid4()),
            dispute_id=dispute_id,
            event_type="tier2_notice_sent",
            actor=ActorType.USER,
            description="Tier-2 supervisory notice marked as sent",
            event_metadata={
                "sent_at": now.isoformat(),
                "tier_reached": dispute.tier_reached,
            }
        )
        self.db.add(paper_trail)

        return {
            "status": "TIER2_NOTICE_SENT",
            "tier2_notice_sent": True,
            "tier2_notice_sent_at": now.isoformat() + "Z",  # Add Z to indicate UTC
            "tier_reached": dispute.tier_reached,
        }

    # =========================================================================
    # TIER-2 RESPONSE LOGGING
    # =========================================================================

    def log_tier2_response(
        self,
        dispute_id: str,
        response_type: Tier2ResponseType,
        response_date: date,
    ) -> Dict[str, Any]:
        """
        Log final Tier-2 supervisory response and handle promotion.

        TIER-2 EXHAUSTION RULE:
        - Only ONE Tier-2 response allowed per dispute
        - No looping, no additional letters

        OUTCOMES:
        - CURED → Close as CURED_AT_TIER_2 (tier_reached=2, state=RESOLVED_CURED)
        - Other → Auto-promote to Tier-3 (lock + classify + ledger)

        Args:
            dispute_id: The dispute to log response for
            response_type: One of CURED, REPEAT_VERIFIED, DEFLECTION_FRIVOLOUS, NO_RESPONSE_AFTER_CURE_WINDOW
            response_date: Date the response was received

        Returns:
            Dict with status and tier_reached, plus ledger_entry if promoted to Tier-3

        Raises:
            ValueError: If dispute not found or Tier-2 already exhausted
        """
        # Get dispute
        dispute = self.db.query(DisputeDB).filter(DisputeDB.id == dispute_id).first()
        if not dispute:
            raise ValueError(f"Dispute not found: {dispute_id}")

        # Check if dispute is locked (already at Tier-3)
        if dispute.locked:
            raise ValueError("Dispute is locked at Tier-3. No further responses allowed.")

        # Require Tier-2 notice to be sent before logging response
        if not dispute.tier2_notice_sent:
            raise ValueError("Tier-2 notice has not been marked as sent. Mark Tier-2 notice as sent first.")

        # Enforce Tier-2 exhaustion rule - only ONE response allowed
        existing = self.db.query(Tier2ResponseDB).filter(
            Tier2ResponseDB.dispute_id == dispute_id
        ).first()
        if existing:
            raise ValueError("Tier-2 response already logged. Tier-2 is exhausted after one supervisory response.")

        # Create Tier-2 response record
        tier2_response = Tier2ResponseDB(
            id=str(uuid4()),
            dispute_id=dispute_id,
            response_type=response_type,
            response_date=response_date,
        )
        self.db.add(tier2_response)

        # Handle outcome based on response type
        if response_type == Tier2ResponseType.CURED:
            # Close as CURED_AT_TIER_2
            dispute.tier_reached = 2
            dispute.current_state = EscalationState.RESOLVED_CURED

            # Create paper trail entry
            paper_trail = PaperTrailDB(
                id=str(uuid4()),
                dispute_id=dispute_id,
                event_type="tier2_cured",
                actor=ActorType.USER,
                description="Violation cured at Tier-2 after supervisory notice",
                event_metadata={
                    "response_type": response_type.value,
                    "response_date": response_date.isoformat(),
                    "tier_reached": 2,
                    "outcome": "CURED_AT_TIER_2",
                }
            )
            self.db.add(paper_trail)

            return {
                "status": "CURED_AT_TIER_2",
                "tier_reached": 2,
                "locked": False,
            }
        else:
            # Auto-promote to Tier-3
            promotion_service = Tier3PromotionService(self.db)
            ledger_entry = promotion_service.promote_to_tier3(dispute, tier2_response)

            return {
                "status": "PROMOTED_TO_TIER_3",
                "tier_reached": 3,
                "locked": True,
                "classification": tier2_response.tier3_classification,
                "ledger_entry": ledger_entry,
            }
