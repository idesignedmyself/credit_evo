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

        For CFPB letters, uses ONLY the selected violations and discrepancies
        from the letter (violations_cited + discrepancies_cited).
        CRITICAL: Must preserve BOTH violation types - never omit discrepancies.
        """
        from app.models.db_models import LetterDB, AuditResultDB

        violations = []
        discrepancies = []

        # PRIORITY 1: Try to find letter by ID - use its selected violations/discrepancies
        letter = self.db.query(LetterDB).filter(LetterDB.id == dispute_session_id).first()

        if letter:
            # Get violations from letter
            if letter.violations_cited:
                for v_data in letter.violations_cited:
                    if isinstance(v_data, dict):
                        # Full violation object stored
                        v = self._reconstruct_violation(v_data)
                        if v:
                            violations.append(v)
                    elif isinstance(v_data, str):
                        # Just violation type string - need to look up full data from audit
                        pass  # Will be handled below

            # If violations_cited contained just strings, look up from audit
            if not violations and letter.violations_cited and letter.report_id:
                from collections import Counter
                audit_result = self.db.query(AuditResultDB).filter(
                    AuditResultDB.report_id == letter.report_id
                ).first()
                if audit_result and audit_result.violations_data:
                    # Count violation types needed from letter
                    cited_counts = Counter(
                        v if isinstance(v, str) else v.get('violation_type')
                        for v in letter.violations_cited
                    )
                    # Match violations from audit by type (respect counts for duplicates)
                    for v_data in audit_result.violations_data:
                        if isinstance(v_data, dict):
                            vtype = v_data.get('violation_type')
                            if cited_counts.get(vtype, 0) > 0:
                                v = self._reconstruct_violation(v_data)
                                if v:
                                    violations.append(v)
                                    cited_counts[vtype] -= 1
                                if sum(cited_counts.values()) <= 0:
                                    break

            # Use ONLY the discrepancies selected for this letter
            if letter.discrepancies_cited:
                for d_data in letter.discrepancies_cited:
                    if isinstance(d_data, dict):
                        v = self._reconstruct_discrepancy_as_violation(d_data)
                        if v:
                            discrepancies.append(v)

            # Letter found - return its selected items only
            return violations + discrepancies

        # PRIORITY 2: Try to find by dispute ID
        dispute = self.db.query(DisputeDB).filter(DisputeDB.id == dispute_session_id).first()

        if dispute:
            # Get violations from original_violation_data
            if dispute.original_violation_data:
                v_data = dispute.original_violation_data
                if isinstance(v_data, dict):
                    v = self._reconstruct_violation(v_data)
                    if v:
                        violations.append(v)
                elif isinstance(v_data, list):
                    for item in v_data:
                        if isinstance(item, dict):
                            v = self._reconstruct_violation(item)
                            if v:
                                violations.append(v)

            # Get cross-bureau discrepancies from dispute
            if dispute.discrepancies_data:
                for d_data in dispute.discrepancies_data:
                    if isinstance(d_data, dict):
                        v = self._reconstruct_discrepancy_as_violation(d_data)
                        if v:
                            discrepancies.append(v)

            # If dispute has a linked letter, get discrepancies from there
            if not discrepancies and dispute.letter_id:
                linked_letter = self.db.query(LetterDB).filter(LetterDB.id == dispute.letter_id).first()
                if linked_letter and linked_letter.discrepancies_cited:
                    for d_data in linked_letter.discrepancies_cited:
                        if isinstance(d_data, dict):
                            v = self._reconstruct_discrepancy_as_violation(d_data)
                            if v:
                                discrepancies.append(v)

            if violations or discrepancies:
                return violations + discrepancies

        # PRIORITY 3: Fallback - try to find by violation_id prefix pattern
        disputes = self.db.query(DisputeDB).filter(
            DisputeDB.violation_id.like(f"{dispute_session_id}%")
        ).all()

        for d in disputes:
            if d.original_violation_data:
                v_data = d.original_violation_data
                if isinstance(v_data, dict):
                    v = self._reconstruct_violation(v_data)
                    if v:
                        violations.append(v)

        # Combine violations and discrepancies - BOTH must be present
        return violations + discrepancies

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

        # Get entity info from dispute or letter
        from app.models.db_models import LetterDB

        dispute = self.db.query(DisputeDB).filter(DisputeDB.id == dispute_session_id).first()
        entity_name = "Credit Bureau"
        account_info = "Account"

        if dispute:
            entity_name = dispute.entity_name or "Credit Bureau"
            account_info = dispute.account_fingerprint or "Account"
        else:
            # Try letter lookup
            letter = self.db.query(LetterDB).filter(LetterDB.id == dispute_session_id).first()
            if letter:
                entity_name = letter.bureau.title() if letter.bureau else "Credit Bureau"
                accounts = letter.accounts_disputed or []
                account_info = ", ".join(accounts[:3]) if accounts else "Account"
            else:
                # Fallback to prefix pattern
                dispute = self.db.query(DisputeDB).filter(
                    DisputeDB.violation_id.like(f"{dispute_session_id}%")
                ).first()
                if dispute:
                    entity_name = dispute.entity_name or "Credit Bureau"
                    account_info = dispute.account_fingerprint or "Account"

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

        # First try to find by dispute ID directly
        dispute = self.db.query(DisputeDB).filter(DisputeDB.id == dispute_session_id).first()
        disputes = [dispute] if dispute else []

        # Fallback to prefix pattern
        if not disputes:
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

    def _reconstruct_discrepancy_as_violation(self, d_data: Dict[str, Any]) -> Optional[Violation]:
        """Convert a cross-bureau discrepancy to a Violation object for CFPB letter."""
        try:
            from app.models.ssot import ViolationType, Severity

            field_name = d_data.get("field_name", "unknown")
            values_by_bureau = d_data.get("values_by_bureau", {})

            # Build description from the discrepancy data
            values_str = ", ".join([f"{b}: {v}" for b, v in values_by_bureau.items() if v])
            description = f"Cross-bureau discrepancy in {field_name}: {values_str}"

            # Normalize field_name for lookup (handle "Date Opened" -> "date_opened")
            normalized_field = field_name.lower().replace(" ", "_")

            # Map field_name to a violation type (using _mismatch suffix from ViolationType enum)
            vtype_map = {
                "date_opened": "date_opened_mismatch",
                "balance": "balance_mismatch",
                "high_credit": "balance_mismatch",  # Use balance_mismatch as fallback
                "payment_status": "status_mismatch",
                "status": "status_mismatch",
                "dofd": "dofd_mismatch",
                "past_due": "past_due_mismatch",
                "payment_history": "payment_history_mismatch",
            }
            violation_type_str = vtype_map.get(normalized_field, f"{normalized_field}_mismatch")

            # Try to use the mapped type, fallback to a generic one
            try:
                violation_type = ViolationType(violation_type_str)
            except ValueError:
                # If not a valid enum, use a generic cross-bureau type
                violation_type = ViolationType("missing_dofd")  # Fallback

            return Violation(
                violation_id=d_data.get("discrepancy_id", str(uuid4())),
                violation_type=violation_type,
                severity=Severity(d_data.get("severity", "medium")),
                account_id=d_data.get("account_id", ""),
                creditor_name=d_data.get("creditor_name", ""),
                account_number_masked=d_data.get("account_number_masked", ""),
                description=description,
                expected_value=None,
                actual_value=values_str,
                evidence={"values_by_bureau": values_by_bureau, "field_name": field_name},
            )
        except Exception as e:
            print(f"Error reconstructing discrepancy: {e}")
            return None
