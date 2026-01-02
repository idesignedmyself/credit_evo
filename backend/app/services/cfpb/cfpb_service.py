"""
CFPB Service

Main orchestrator for CFPB channel adapter.
Coordinates state machine, letter generation, and ledger integration.

Key responsibilities:
- Check CRA exhaustion and contradiction gating
- Generate CFPB letters (no state change)
- Submit complaints (state change)
- Log responses (state change)
- Evaluate responses (read-only)
"""
from datetime import datetime, date
from typing import Dict, Any, List, Optional, Tuple
from uuid import uuid4
from sqlalchemy.orm import Session

from app.models.ssot import (
    CFPBState, CFPBEventType, CFPBResponseClassification,
    Violation, Consumer,
)
from app.models.db_models import (
    CFPBCaseDB, CFPBEventDB, CFPBState as DBCFPBState,
    CFPBEventType as DBCFPBEventType,
    DisputeDB, DisputeResponseDB, ResponseType,
    AuditResultDB, ReportDB, UserDB,
)
from .cfpb_state_machine import CFPBStateMachine, CFPBStateMachineError
from .cfpb_letter_generator import CFPBLetterGenerator, TimelineEvent, CFPBLetter


class CFPBServiceError(Exception):
    """Raised when CFPB service operation fails."""
    pass


class CFPBService:
    """
    CFPB Channel Adapter service.

    Reuses existing contradiction/severity/remedy from CRA dispute system.
    Only transforms rendering for CFPB audience.
    """

    def __init__(self, db: Session):
        self.db = db
        self.state_machine = CFPBStateMachine()
        self.generator = CFPBLetterGenerator()

    # =========================================================================
    # GATING CHECKS
    # =========================================================================

    def check_cra_exhaustion(self, dispute_session_id: str) -> Tuple[bool, Optional[ResponseType]]:
        """
        Check if CRA exhaustion criteria is met.

        CRA exhaustion = VERIFIED | NO_RESPONSE | REJECTED (DEFECTIVE)

        Returns:
            Tuple of (is_exhausted, response_type)
        """
        # Find disputes for this session
        disputes = self.db.query(DisputeDB).filter(
            DisputeDB.violation_id.like(f"{dispute_session_id}%")
        ).all()

        if not disputes:
            # Try to find by looking at paper trail or other linkage
            # For now, return False if no disputes found
            return False, None

        # Check responses
        exhaustion_types = {ResponseType.VERIFIED, ResponseType.NO_RESPONSE, ResponseType.REJECTED}

        for dispute in disputes:
            responses = self.db.query(DisputeResponseDB).filter(
                DisputeResponseDB.dispute_id == dispute.id
            ).order_by(DisputeResponseDB.created_at.desc()).first()

            if responses and responses.response_type in exhaustion_types:
                return True, responses.response_type

        return False, None

    def get_unresolved_contradictions(
        self,
        dispute_session_id: str,
    ) -> List[Violation]:
        """
        Get unresolved contradictions for a dispute session.

        Pulls from existing audit results and filters by resolution status.
        """
        # For now, return violations from the audit result
        # In production, this would track which violations have been resolved
        violations = []

        # Find associated report
        disputes = self.db.query(DisputeDB).filter(
            DisputeDB.violation_id.like(f"{dispute_session_id}%")
        ).all()

        for dispute in disputes:
            if dispute.original_violation_data:
                # Reconstruct violation from stored data
                v_data = dispute.original_violation_data
                if isinstance(v_data, dict):
                    v = self._reconstruct_violation(v_data)
                    if v:
                        violations.append(v)

        return violations

    def can_escalate(self, dispute_session_id: str) -> Tuple[bool, Optional[str]]:
        """
        Check if CFPB escalation is allowed.

        Requires:
        1. CRA exhaustion (VERIFIED | NO_RESPONSE | DEFECTIVE)
        2. unresolved_contradictions_count > 0

        Returns:
            Tuple of (is_allowed, error_message)
        """
        # Check CRA exhaustion
        is_exhausted, response_type = self.check_cra_exhaustion(dispute_session_id)
        if not is_exhausted:
            return False, "CRA exhaustion not met - must have VERIFIED, NO_RESPONSE, or DEFECTIVE response"

        # Check unresolved contradictions
        contradictions = self.get_unresolved_contradictions(dispute_session_id)
        if len(contradictions) == 0:
            return False, "No unresolved contradictions - cannot escalate"

        return True, None

    # =========================================================================
    # LETTER GENERATION (NO STATE CHANGE)
    # =========================================================================

    def generate_letter(
        self,
        dispute_session_id: str,
        cfpb_stage: str,
        user_id: str,
    ) -> Dict[str, Any]:
        """
        Generate CFPB letter draft (no state change).

        Args:
            dispute_session_id: Links to existing dispute lifecycle
            cfpb_stage: "initial", "escalation", or "final"
            user_id: User ID for consumer info

        Returns:
            Dict with content, contradictions_included, timeline
        """
        # Get user/consumer info
        user = self.db.query(UserDB).filter(UserDB.id == user_id).first()
        if not user:
            raise CFPBServiceError(f"User not found: {user_id}")

        consumer = Consumer(
            full_name=f"{user.first_name or ''} {user.last_name or ''}".strip() or user.email,
            address=user.street_address or "",
            city=user.city or "",
            state=user.state or "",
            zip_code=user.zip_code or "",
        )

        # Get contradictions
        contradictions = self.get_unresolved_contradictions(dispute_session_id)

        # Get timeline events
        timeline_events = self._build_timeline(dispute_session_id)

        # Get entity info from disputes
        disputes = self.db.query(DisputeDB).filter(
            DisputeDB.violation_id.like(f"{dispute_session_id}%")
        ).first()

        entity_name = disputes.entity_name if disputes else "Credit Bureau"
        account_info = disputes.account_fingerprint if disputes else "Account"

        # Get CFPB case number for escalation/final
        cfpb_case = self._get_or_create_case(dispute_session_id, user_id, create=False)
        cfpb_case_number = cfpb_case.cfpb_case_number if cfpb_case else None

        # Generate letter
        letter = self.generator.generate(
            cfpb_stage=cfpb_stage,
            consumer=consumer,
            contradictions=contradictions,
            timeline_events=timeline_events,
            entity_name=entity_name,
            account_info=account_info,
            cfpb_case_number=cfpb_case_number,
        )

        return {
            "content": letter.content,
            "contradictions_included": letter.contradictions_included,
            "timeline": letter.timeline,
        }

    # =========================================================================
    # SUBMIT COMPLAINT (STATE CHANGE)
    # =========================================================================

    def submit_complaint(
        self,
        dispute_session_id: str,
        user_id: str,
        cfpb_stage: str,
        submission_payload: Dict[str, Any],
        cfpb_case_number: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Submit CFPB complaint and advance state.

        Args:
            dispute_session_id: Links to existing dispute lifecycle
            user_id: User ID
            cfpb_stage: "initial", "escalation", or "final"
            submission_payload: {complaint_text, attachments}
            cfpb_case_number: CFPB portal case number (optional for initial)

        Returns:
            Dict with cfpb_case_id, cfpb_state, submitted_at
        """
        # Get or create case
        cfpb_case = self._get_or_create_case(dispute_session_id, user_id, create=True)

        # Map stage to action
        action_map = {
            "initial": "submit_initial",
            "escalation": "submit_escalation",
            "final": "submit_final",
        }
        action = action_map.get(cfpb_stage)
        if not action:
            raise CFPBServiceError(f"Invalid CFPB stage: {cfpb_stage}")

        # Get gating info for escalation/final
        cra_response_type = None
        unresolved_count = 0

        if cfpb_stage in ("escalation", "final"):
            # Check gating
            is_allowed, error = self.can_escalate(dispute_session_id)
            if not is_allowed:
                raise CFPBServiceError(error)

            _, cra_response_type = self.check_cra_exhaustion(dispute_session_id)
            unresolved_count = len(self.get_unresolved_contradictions(dispute_session_id))

            # Require case number for escalation/final
            if not cfpb_case.cfpb_case_number and not cfpb_case_number:
                raise CFPBServiceError("CFPB case number required for escalation/final")

        # Perform state transition
        current_state = CFPBState(cfpb_case.cfpb_state.value)
        try:
            new_state = self.state_machine.transition(
                current_state,
                action,
                cra_response_type,
                unresolved_count,
            )
        except CFPBStateMachineError as e:
            raise CFPBServiceError(str(e))

        # Update case
        cfpb_case.cfpb_state = DBCFPBState(new_state.value)
        if cfpb_case_number:
            cfpb_case.cfpb_case_number = cfpb_case_number
        cfpb_case.updated_at = datetime.utcnow()

        # Log event
        event = CFPBEventDB(
            id=str(uuid4()),
            cfpb_case_id=cfpb_case.id,
            event_type=DBCFPBEventType.SUBMISSION,
            payload={
                "stage": cfpb_stage,
                "complaint_text": submission_payload.get("complaint_text", "")[:1000],  # Truncate
                "attachments": submission_payload.get("attachments", []),
            },
            timestamp=datetime.utcnow(),
        )
        self.db.add(event)
        self.db.commit()

        return {
            "cfpb_case_id": cfpb_case.id,
            "cfpb_state": new_state.value,
            "submitted_at": datetime.utcnow().isoformat(),
        }

    # =========================================================================
    # LOG RESPONSE (STATE CHANGE)
    # =========================================================================

    def log_response(
        self,
        cfpb_case_id: str,
        response_text: str,
        responding_entity: str,
        response_date: date,
    ) -> Dict[str, Any]:
        """
        Log CFPB response and advance state.

        Args:
            cfpb_case_id: CFPB case ID
            response_text: Response text from entity
            responding_entity: "CRA" or "Furnisher"
            response_date: Date response was received

        Returns:
            Dict with response_id, classification, new_state
        """
        # Get case
        cfpb_case = self.db.query(CFPBCaseDB).filter(CFPBCaseDB.id == cfpb_case_id).first()
        if not cfpb_case:
            raise CFPBServiceError(f"CFPB case not found: {cfpb_case_id}")

        # Perform state transition
        current_state = CFPBState(cfpb_case.cfpb_state.value)
        try:
            new_state = self.state_machine.transition(current_state, "log_response")
        except CFPBStateMachineError as e:
            raise CFPBServiceError(str(e))

        # Classify response (informational, does not gate state)
        classification = self._classify_response(response_text)

        # Update case
        cfpb_case.cfpb_state = DBCFPBState(new_state.value)
        cfpb_case.updated_at = datetime.utcnow()

        # Log event
        event = CFPBEventDB(
            id=str(uuid4()),
            cfpb_case_id=cfpb_case.id,
            event_type=DBCFPBEventType.RESPONSE,
            payload={
                "response_text": response_text[:2000],  # Truncate
                "responding_entity": responding_entity,
                "response_date": response_date.isoformat(),
                "classification": classification.value,
            },
            timestamp=datetime.utcnow(),
        )
        self.db.add(event)
        self.db.commit()

        return {
            "response_id": event.id,
            "classification": classification.value,
            "new_state": new_state.value,
        }

    # =========================================================================
    # EVALUATE RESPONSE (READ-ONLY)
    # =========================================================================

    def evaluate(self, cfpb_case_id: str) -> Dict[str, Any]:
        """
        Evaluate CFPB response (read-only, no state change).

        Returns recommendations based on state and unresolved contradictions.
        """
        # Get case
        cfpb_case = self.db.query(CFPBCaseDB).filter(CFPBCaseDB.id == cfpb_case_id).first()
        if not cfpb_case:
            raise CFPBServiceError(f"CFPB case not found: {cfpb_case_id}")

        # Get unresolved contradictions
        contradictions = self.get_unresolved_contradictions(cfpb_case.dispute_session_id)

        # Get recommendation from state machine
        current_state = CFPBState(cfpb_case.cfpb_state.value)
        recommended_action = self.state_machine.get_recommended_action(
            current_state,
            len(contradictions),
        )

        # Map action to stage
        stage_map = {
            "escalate": "escalation",
            "finalize": "final",
            "close": "none",
        }
        recommended_stage = stage_map.get(recommended_action, "none")

        return {
            "unresolved_contradictions": [
                {
                    "violation_id": v.violation_id,
                    "type": v.violation_type.value,
                    "severity": v.severity.value,
                    "description": v.description,
                }
                for v in contradictions
            ],
            "recommended_next_action": recommended_action or "none",
            "recommended_next_stage": recommended_stage,
        }

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _get_or_create_case(
        self,
        dispute_session_id: str,
        user_id: str,
        create: bool = True,
    ) -> Optional[CFPBCaseDB]:
        """Get existing CFPB case or create new one."""
        cfpb_case = self.db.query(CFPBCaseDB).filter(
            CFPBCaseDB.dispute_session_id == dispute_session_id
        ).first()

        if not cfpb_case and create:
            cfpb_case = CFPBCaseDB(
                id=str(uuid4()),
                dispute_session_id=dispute_session_id,
                user_id=user_id,
                cfpb_state=DBCFPBState.NONE,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            self.db.add(cfpb_case)
            self.db.flush()

        return cfpb_case

    def _classify_response(self, response_text: str) -> CFPBResponseClassification:
        """
        Classify CFPB response (informational, does not gate state).

        Simple heuristic classification.
        """
        text_lower = response_text.lower()

        # Check for generic responses
        generic_phrases = [
            "verified",
            "accurate",
            "confirmed",
            "reviewed and verified",
            "information is correct",
        ]
        if any(phrase in text_lower for phrase in generic_phrases):
            return CFPBResponseClassification.GENERIC_RESPONSE

        # Check for addressed facts
        addressed_phrases = [
            "corrected",
            "updated",
            "deleted",
            "removed",
            "modified",
            "explanation",
        ]
        if any(phrase in text_lower for phrase in addressed_phrases):
            return CFPBResponseClassification.ADDRESSED_FACTS

        # Default to ignored
        return CFPBResponseClassification.IGNORED_FACTS

    def _build_timeline(self, dispute_session_id: str) -> List[TimelineEvent]:
        """Build timeline of dispute events."""
        events = []

        # Get disputes for this session
        disputes = self.db.query(DisputeDB).filter(
            DisputeDB.violation_id.like(f"{dispute_session_id}%")
        ).all()

        for dispute in disputes:
            # Dispute creation
            if dispute.dispute_date:
                events.append(TimelineEvent(
                    event_date=dispute.dispute_date,
                    event_description=f"Dispute submitted to {dispute.entity_name}",
                    outcome="Via certified mail",
                ))

            # Deadline
            if dispute.deadline_date:
                events.append(TimelineEvent(
                    event_date=dispute.deadline_date,
                    event_description="30-day statutory deadline",
                    outcome="Passed" if date.today() > dispute.deadline_date else "Pending",
                ))

            # Responses
            for response in dispute.responses:
                if response.response_date:
                    events.append(TimelineEvent(
                        event_date=response.response_date,
                        event_description=f"{dispute.entity_name} response received",
                        outcome=response.response_type.value,
                    ))

        # Sort by date
        events.sort(key=lambda e: e.event_date)
        return events

    def _reconstruct_violation(self, v_data: Dict[str, Any]) -> Optional[Violation]:
        """Reconstruct Violation object from stored JSON."""
        try:
            from app.models.ssot import ViolationType, Severity, FurnisherType, Bureau

            return Violation(
                violation_id=v_data.get("violation_id", str(uuid4())),
                violation_type=ViolationType(v_data.get("violation_type", "missing_dofd")),
                severity=Severity(v_data.get("severity", "medium")),
                account_id=v_data.get("account_id", ""),
                creditor_name=v_data.get("creditor_name", ""),
                account_number_masked=v_data.get("account_number_masked", ""),
                description=v_data.get("description", ""),
                expected_value=v_data.get("expected_value"),
                actual_value=v_data.get("actual_value"),
                evidence=v_data.get("evidence", {}),
            )
        except Exception:
            return None
