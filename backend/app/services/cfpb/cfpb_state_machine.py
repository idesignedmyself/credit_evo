"""
CFPB State Machine

Single CFPBState enum is the source of truth.
State transitions:
    NONE → INITIAL_SUBMITTED → RESPONSE_RECEIVED → ESCALATION_SUBMITTED
    → ESCALATION_RESPONSE_RECEIVED → FINAL_SUBMITTED → CLOSED

Escalation gating rules:
- CRA exhaustion required (VERIFIED | NO_RESPONSE | DEFECTIVE)
- unresolved_contradictions_count > 0 required for escalation/final
"""
from typing import Optional, Tuple
from app.models.ssot import CFPBState
from app.models.db_models import ResponseType


class CFPBStateMachineError(Exception):
    """Raised when a state transition is invalid."""
    pass


class CFPBStateMachine:
    """
    CFPB state machine with escalation gating.

    State transitions are deterministic based on current state and action.
    Escalation requires CRA exhaustion AND unresolved contradictions.
    """

    # Valid CRA exhaustion response types
    CRA_EXHAUSTION_RESPONSES = {
        ResponseType.VERIFIED,
        ResponseType.NO_RESPONSE,
        ResponseType.REJECTED,  # DEFECTIVE = REJECTED in our system
    }

    # State transition map: (current_state, action) -> new_state
    TRANSITIONS = {
        # Initial submission
        (CFPBState.NONE, "submit_initial"): CFPBState.INITIAL_SUBMITTED,

        # Response logging
        (CFPBState.INITIAL_SUBMITTED, "log_response"): CFPBState.RESPONSE_RECEIVED,
        (CFPBState.ESCALATION_SUBMITTED, "log_response"): CFPBState.ESCALATION_RESPONSE_RECEIVED,

        # Escalation submission (requires gating check)
        (CFPBState.RESPONSE_RECEIVED, "submit_escalation"): CFPBState.ESCALATION_SUBMITTED,

        # Final submission (requires gating check)
        (CFPBState.ESCALATION_RESPONSE_RECEIVED, "submit_final"): CFPBState.FINAL_SUBMITTED,

        # Close
        (CFPBState.FINAL_SUBMITTED, "close"): CFPBState.CLOSED,
        (CFPBState.RESPONSE_RECEIVED, "close"): CFPBState.CLOSED,
        (CFPBState.ESCALATION_RESPONSE_RECEIVED, "close"): CFPBState.CLOSED,
    }

    def can_transition(
        self,
        current_state: CFPBState,
        action: str,
        cra_response_type: Optional[ResponseType] = None,
        unresolved_contradictions_count: int = 0,
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if a state transition is allowed.

        Args:
            current_state: Current CFPB state
            action: Action to perform (submit_initial, log_response, submit_escalation, submit_final, close)
            cra_response_type: CRA response type for escalation gating
            unresolved_contradictions_count: Number of unresolved contradictions

        Returns:
            Tuple of (is_allowed, error_message)
        """
        # Check if transition exists
        if (current_state, action) not in self.TRANSITIONS:
            return False, f"Invalid transition: {current_state.value} + {action}"

        # Escalation gating for submit_escalation and submit_final
        if action in ("submit_escalation", "submit_final"):
            # Check CRA exhaustion
            if cra_response_type is None:
                return False, "CRA response required for escalation"

            if cra_response_type not in self.CRA_EXHAUSTION_RESPONSES:
                return False, f"CRA exhaustion not met: {cra_response_type.value} is not exhaustion response"

            # Check unresolved contradictions
            if unresolved_contradictions_count <= 0:
                return False, "No unresolved contradictions - cannot escalate"

        return True, None

    def transition(
        self,
        current_state: CFPBState,
        action: str,
        cra_response_type: Optional[ResponseType] = None,
        unresolved_contradictions_count: int = 0,
    ) -> CFPBState:
        """
        Perform a state transition.

        Args:
            current_state: Current CFPB state
            action: Action to perform
            cra_response_type: CRA response type for escalation gating
            unresolved_contradictions_count: Number of unresolved contradictions

        Returns:
            New CFPB state

        Raises:
            CFPBStateMachineError: If transition is not allowed
        """
        is_allowed, error = self.can_transition(
            current_state,
            action,
            cra_response_type,
            unresolved_contradictions_count,
        )

        if not is_allowed:
            raise CFPBStateMachineError(error)

        return self.TRANSITIONS[(current_state, action)]

    def get_available_actions(
        self,
        current_state: CFPBState,
    ) -> list[str]:
        """
        Get list of actions available from current state.

        Returns actions without checking gating rules.
        Use can_transition() to verify if action is actually allowed.
        """
        actions = []
        for (state, action), _ in self.TRANSITIONS.items():
            if state == current_state:
                actions.append(action)
        return actions

    def is_terminal(self, state: CFPBState) -> bool:
        """Check if state is terminal (no further transitions possible)."""
        return state == CFPBState.CLOSED

    def get_recommended_action(
        self,
        current_state: CFPBState,
        unresolved_contradictions_count: int,
    ) -> Optional[str]:
        """
        Get recommended next action based on state and contradictions.

        This is used by the /evaluate endpoint (read-only).
        """
        if current_state == CFPBState.RESPONSE_RECEIVED:
            if unresolved_contradictions_count > 0:
                return "escalate"
            else:
                return "close"

        elif current_state == CFPBState.ESCALATION_RESPONSE_RECEIVED:
            if unresolved_contradictions_count > 0:
                return "finalize"
            else:
                return "close"

        elif current_state == CFPBState.FINAL_SUBMITTED:
            return "close"

        return None
