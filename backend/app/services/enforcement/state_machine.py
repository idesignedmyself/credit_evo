"""
Escalation State Machine

Deterministic state machine for dispute escalation.
States are non-reversible once advanced past certain points.
All transitions are logged immutably.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from uuid import uuid4

from ...models.db_models import (
    EscalationState, ActorType, ResponseType, EntityType,
    DisputeDB, EscalationLogDB, PaperTrailDB
)


# =============================================================================
# STATE CONFIGURATION
# =============================================================================

STATE_CONFIG = {
    EscalationState.DETECTED: {
        "description": "Violation identified by audit engine",
        "allowed_transitions": [EscalationState.DISPUTED],
        "tone_posture": "informational",
        "outputs": ["initial_dispute_letter"],
        "statutes": [],  # Underlying violation statute
        "reversible": True,
    },
    EscalationState.DISPUTED: {
        "description": "Dispute sent, awaiting response",
        "allowed_transitions": [
            EscalationState.RESPONDED,
            EscalationState.NO_RESPONSE,
        ],
        "tone_posture": "informational",
        "outputs": [],
        "statutes": ["FCRA § 611(a)(1)", "FCRA § 623(b)(1)"],
        "reversible": False,
    },
    EscalationState.RESPONDED: {
        "description": "Response received from entity",
        "allowed_transitions": [
            EscalationState.EVALUATED,
            EscalationState.RESOLVED_DELETED,
            EscalationState.RESOLVED_CURED,
        ],
        "tone_posture": "informational",
        "outputs": ["validation_prompts"],
        "statutes": [],
        "reversible": False,
    },
    EscalationState.NO_RESPONSE: {
        "description": "Entity failed to respond within deadline",
        "allowed_transitions": [EscalationState.NON_COMPLIANT],
        "tone_posture": "assertive",
        "outputs": ["escalation_notice"],
        "statutes": ["FCRA § 611(a)(1)(A)", "FCRA § 623(b)(1)(A)"],
        "reversible": False,
    },
    EscalationState.EVALUATED: {
        "description": "Response evaluated, determination made",
        "allowed_transitions": [
            EscalationState.NON_COMPLIANT,
            EscalationState.RESOLVED_CURED,
        ],
        "tone_posture": "informational",
        "outputs": ["evaluation_summary"],
        "statutes": [],
        "reversible": False,
    },
    EscalationState.NON_COMPLIANT: {
        "description": "Entity failed statutory duty",
        "allowed_transitions": [
            EscalationState.PROCEDURAL_ENFORCEMENT,
            EscalationState.SUBSTANTIVE_ENFORCEMENT,
        ],
        "tone_posture": "assertive",
        "outputs": ["escalation_notice", "procedural_cure_letter"],
        "statutes": ["FCRA § 611(a)", "FCRA § 623(b)"],
        "reversible": False,
    },
    EscalationState.PROCEDURAL_ENFORCEMENT: {
        "description": "Procedural remedies in progress",
        "allowed_transitions": [
            EscalationState.SUBSTANTIVE_ENFORCEMENT,
            EscalationState.RESOLVED_CURED,
        ],
        "tone_posture": "enforcement",
        "outputs": ["mov_demand", "procedural_cure_letter"],
        "statutes": ["FCRA § 611(a)(6)(B)(iii)", "FCRA § 623(b)(1)(B)"],
        "reversible": False,
    },
    EscalationState.SUBSTANTIVE_ENFORCEMENT: {
        "description": "Substantive enforcement in progress",
        "allowed_transitions": [
            EscalationState.REGULATORY_ESCALATION,
            EscalationState.RESOLVED_CURED,
        ],
        "tone_posture": "enforcement",
        "outputs": ["failure_to_investigate_letter", "formal_demand"],
        "statutes": ["FCRA § 616", "FCRA § 617", "FDCPA § 1692k"],
        "reversible": False,
    },
    EscalationState.REGULATORY_ESCALATION: {
        "description": "Regulatory complaint preparation",
        "allowed_transitions": [EscalationState.LITIGATION_READY],
        "tone_posture": "regulatory",
        "outputs": ["cfpb_complaint_packet", "ag_referral_letter"],
        "statutes": ["FCRA § 621"],
        "reversible": False,
    },
    EscalationState.LITIGATION_READY: {
        "description": "All remedies exhausted, litigation ready",
        "allowed_transitions": [],  # Terminal state
        "tone_posture": "litigation",
        "outputs": ["attorney_evidence_bundle"],
        "statutes": ["FCRA § 616", "FCRA § 617", "FDCPA § 1692k"],
        "reversible": False,
    },
    EscalationState.RESOLVED_DELETED: {
        "description": "Dispute resolved - item deleted",
        "allowed_transitions": [EscalationState.REGULATORY_ESCALATION],  # If reinsertion
        "tone_posture": "informational",
        "outputs": [],
        "statutes": [],
        "reversible": False,
    },
    EscalationState.RESOLVED_CURED: {
        "description": "Dispute resolved - entity cured violation",
        "allowed_transitions": [],  # Terminal state
        "tone_posture": "informational",
        "outputs": [],
        "statutes": [],
        "reversible": False,
    },
}


# =============================================================================
# STATE MACHINE
# =============================================================================

class EscalationStateMachine:
    """
    Deterministic state machine for dispute escalation.

    Core Principles:
    - User provides facts, system makes legal determinations
    - States are non-reversible past DISPUTED
    - All transitions are logged immutably
    - Silence is treated as NO_RESPONSE
    - Verification compounds liability
    """

    def __init__(self, db_session):
        """Initialize with database session."""
        self.db = db_session

    def get_state_config(self, state: EscalationState) -> Dict[str, Any]:
        """Get configuration for a state."""
        return STATE_CONFIG.get(state, {})

    def can_transition(
        self,
        from_state: EscalationState,
        to_state: EscalationState
    ) -> Tuple[bool, str]:
        """
        Check if a state transition is allowed.

        Returns (allowed, reason)
        """
        config = self.get_state_config(from_state)
        allowed_transitions = config.get("allowed_transitions", [])

        if to_state in allowed_transitions:
            return True, "Transition allowed"

        return False, f"Cannot transition from {from_state.value} to {to_state.value}"

    def transition(
        self,
        dispute: DisputeDB,
        to_state: EscalationState,
        trigger: str,
        actor: ActorType,
        statutes_activated: Optional[List[str]] = None,
        violations_created: Optional[List[str]] = None,
    ) -> Tuple[bool, str]:
        """
        Execute a state transition.

        Returns (success, message)
        """
        from_state = dispute.current_state

        # Check if transition is allowed
        allowed, reason = self.can_transition(from_state, to_state)
        if not allowed:
            return False, reason

        # Create escalation log entry (immutable)
        log_entry = EscalationLogDB(
            id=str(uuid4()),
            dispute_id=dispute.id,
            from_state=from_state,
            to_state=to_state,
            trigger=trigger,
            actor=actor,
            statutes_activated=statutes_activated or [],
            violations_created=violations_created or [],
        )
        self.db.add(log_entry)

        # Create paper trail entry
        paper_trail = PaperTrailDB(
            id=str(uuid4()),
            dispute_id=dispute.id,
            event_type="state_transition",
            actor=actor,
            description=f"State changed from {from_state.value} to {to_state.value}. Trigger: {trigger}",
            metadata={
                "from_state": from_state.value,
                "to_state": to_state.value,
                "trigger": trigger,
                "statutes_activated": statutes_activated or [],
            }
        )
        self.db.add(paper_trail)

        # Update dispute state
        dispute.current_state = to_state
        dispute.updated_at = datetime.utcnow()

        return True, f"Transitioned to {to_state.value}"

    def get_available_outputs(self, state: EscalationState) -> List[str]:
        """Get available output artifacts for a state."""
        config = self.get_state_config(state)
        return config.get("outputs", [])

    def get_tone_posture(self, state: EscalationState) -> str:
        """Get the tone posture for a state."""
        config = self.get_state_config(state)
        return config.get("tone_posture", "informational")

    def is_terminal_state(self, state: EscalationState) -> bool:
        """Check if a state is terminal (no further transitions)."""
        config = self.get_state_config(state)
        return len(config.get("allowed_transitions", [])) == 0

    def get_next_states(self, state: EscalationState) -> List[EscalationState]:
        """Get possible next states from current state."""
        config = self.get_state_config(state)
        return config.get("allowed_transitions", [])


# =============================================================================
# AUTOMATIC TRANSITION TRIGGERS
# =============================================================================

class AutomaticTransitionTriggers:
    """
    System-authoritative actions that trigger state transitions
    without user confirmation.
    """

    @staticmethod
    def deadline_breach(
        state_machine: EscalationStateMachine,
        dispute: DisputeDB
    ) -> Tuple[bool, str]:
        """
        Triggered when deadline passes with no response.
        System-automatic, no user confirmation required.
        """
        if dispute.current_state != EscalationState.DISPUTED:
            return False, "Dispute not in DISPUTED state"

        return state_machine.transition(
            dispute=dispute,
            to_state=EscalationState.NO_RESPONSE,
            trigger="deadline_breach",
            actor=ActorType.SYSTEM,
            statutes_activated=["FCRA § 611(a)(1)(A)"],
        )

    @staticmethod
    def reinsertion_detected(
        state_machine: EscalationStateMachine,
        dispute: DisputeDB
    ) -> Tuple[bool, str]:
        """
        Triggered when a deleted item reappears.
        Bypasses intermediate states, goes directly to REGULATORY_ESCALATION.
        System-automatic, no user confirmation required.
        """
        if dispute.current_state != EscalationState.RESOLVED_DELETED:
            return False, "Dispute not in RESOLVED_DELETED state"

        return state_machine.transition(
            dispute=dispute,
            to_state=EscalationState.REGULATORY_ESCALATION,
            trigger="reinsertion_detected",
            actor=ActorType.SYSTEM,
            statutes_activated=["FCRA § 611(a)(5)(B)", "FCRA § 623(a)(6)"],
        )

    @staticmethod
    def stall_timeout(
        state_machine: EscalationStateMachine,
        dispute: DisputeDB
    ) -> Tuple[bool, str]:
        """
        Triggered when INVESTIGATING response exceeds 15-day limit.
        Converts to NO_RESPONSE.
        System-automatic, no user confirmation required.
        """
        # This would be called when an INVESTIGATING response
        # has been pending for more than 15 days
        return state_machine.transition(
            dispute=dispute,
            to_state=EscalationState.NO_RESPONSE,
            trigger="investigating_stall_timeout",
            actor=ActorType.SYSTEM,
            statutes_activated=["FCRA § 611(a)(1)"],
        )

    @staticmethod
    def non_compliance_confirmed(
        state_machine: EscalationStateMachine,
        dispute: DisputeDB,
        statutes: List[str]
    ) -> Tuple[bool, str]:
        """
        Triggered after response evaluation determines non-compliance.
        System-automatic based on response analysis.
        """
        allowed_from = [
            EscalationState.NO_RESPONSE,
            EscalationState.EVALUATED,
        ]

        if dispute.current_state not in allowed_from:
            return False, f"Cannot transition to NON_COMPLIANT from {dispute.current_state.value}"

        return state_machine.transition(
            dispute=dispute,
            to_state=EscalationState.NON_COMPLIANT,
            trigger="non_compliance_confirmed",
            actor=ActorType.SYSTEM,
            statutes_activated=statutes,
        )
