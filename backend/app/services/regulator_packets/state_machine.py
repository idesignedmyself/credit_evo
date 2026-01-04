"""
State Machine - Phase 4

Determines packet eligibility based on dispute timeline.
All rules are hard-locked. No interpretation.
Timestamps must be timezone-aware UTC.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

from app.models.cfpb_packet import PacketType


# =============================================================================
# CONSTANTS (HARD-LOCKED)
# =============================================================================

# FCRA requires CRAs to respond within 30 days (15 U.S.C. § 1681i(a)(1))
STATUTORY_RESPONSE_DAYS = 30

# Extended period for complex investigations (15 U.S.C. § 1681i(a)(1))
EXTENDED_RESPONSE_DAYS = 45


# =============================================================================
# DISPUTE STATE
# =============================================================================

class DisputeState(str, Enum):
    """Current state of a dispute."""
    PENDING = "PENDING"  # Dispute sent, awaiting response
    RESPONDED = "RESPONDED"  # Response received
    NON_RESPONSE = "NON_RESPONSE"  # No response within statutory period
    VERIFIED_WITHOUT_CHANGE = "VERIFIED_WITHOUT_CHANGE"  # Verified but no correction
    REINSERTED = "REINSERTED"  # Account reinserted after deletion


# =============================================================================
# ELIGIBILITY RESULT
# =============================================================================

@dataclass
class PacketEligibility:
    """
    Result of packet eligibility check.

    eligible_types: List of packet types that can be generated
    current_state: Current dispute state
    days_since_dispute: Days elapsed since dispute was sent
    reason: Human-readable eligibility reason
    """
    eligible_types: list[PacketType]
    current_state: DisputeState
    days_since_dispute: int
    reason: str

    def is_eligible_for(self, packet_type: PacketType) -> bool:
        """Check if eligible for a specific packet type."""
        return packet_type in self.eligible_types


# =============================================================================
# STATE MACHINE
# =============================================================================

class DisputeStateMachine:
    """
    Determines packet eligibility based on dispute timeline.

    All rules are hard-locked and derived from FCRA statutory requirements.
    No heuristics. No interpretation.
    """

    @staticmethod
    def compute_state(
        *,
        dispute_sent_at: datetime,
        current_time: datetime,
        response_received_at: Optional[datetime] = None,
        verified_without_change: bool = False,
        account_reinserted: bool = False,
    ) -> DisputeState:
        """
        Compute current dispute state.

        Args:
            dispute_sent_at: When dispute was sent (UTC)
            current_time: Current time for evaluation (UTC)
            response_received_at: When response was received (UTC), if any
            verified_without_change: True if account was verified without correction
            account_reinserted: True if account was reinserted after deletion

        Returns:
            Current DisputeState
        """
        # Validate timezone awareness
        if dispute_sent_at.tzinfo is None:
            raise ValueError("dispute_sent_at must be timezone-aware (UTC)")
        if current_time.tzinfo is None:
            raise ValueError("current_time must be timezone-aware (UTC)")
        if response_received_at is not None and response_received_at.tzinfo is None:
            raise ValueError("response_received_at must be timezone-aware (UTC)")

        # State priority (highest first)
        if account_reinserted:
            return DisputeState.REINSERTED

        if verified_without_change:
            return DisputeState.VERIFIED_WITHOUT_CHANGE

        if response_received_at is not None:
            return DisputeState.RESPONDED

        # Check if statutory period has elapsed
        days_elapsed = (current_time - dispute_sent_at).days
        if days_elapsed >= STATUTORY_RESPONSE_DAYS:
            return DisputeState.NON_RESPONSE

        return DisputeState.PENDING

    @staticmethod
    def check_eligibility(
        *,
        dispute_sent_at: datetime,
        current_time: datetime,
        response_received_at: Optional[datetime] = None,
        verified_without_change: bool = False,
        account_reinserted: bool = False,
        initial_packet_sent: bool = False,
    ) -> PacketEligibility:
        """
        Check packet eligibility based on dispute state.

        Args:
            dispute_sent_at: When dispute was sent (UTC)
            current_time: Current time for evaluation (UTC)
            response_received_at: When response was received (UTC), if any
            verified_without_change: True if account was verified without correction
            account_reinserted: True if account was reinserted after deletion
            initial_packet_sent: True if INITIAL packet has already been sent

        Returns:
            PacketEligibility with eligible packet types
        """
        # Validate timezone awareness
        if dispute_sent_at.tzinfo is None:
            raise ValueError("dispute_sent_at must be timezone-aware (UTC)")
        if current_time.tzinfo is None:
            raise ValueError("current_time must be timezone-aware (UTC)")

        # Compute state
        state = DisputeStateMachine.compute_state(
            dispute_sent_at=dispute_sent_at,
            current_time=current_time,
            response_received_at=response_received_at,
            verified_without_change=verified_without_change,
            account_reinserted=account_reinserted,
        )

        days_elapsed = (current_time - dispute_sent_at).days
        eligible_types = []
        reason = ""

        # Determine eligibility based on state
        if state == DisputeState.PENDING:
            # No escalation yet - can only send INITIAL if not already sent
            if not initial_packet_sent:
                eligible_types = [PacketType.INITIAL]
                reason = f"Dispute pending ({days_elapsed} days). INITIAL packet eligible."
            else:
                eligible_types = []
                reason = f"Dispute pending ({days_elapsed} days). Awaiting response."

        elif state == DisputeState.RESPONDED:
            # Response received - RESPONSE packet eligible
            eligible_types = [PacketType.RESPONSE]
            reason = "Response received. RESPONSE packet eligible for analysis."

        elif state == DisputeState.NON_RESPONSE:
            # No response within statutory period - FAILURE packet eligible
            eligible_types = [PacketType.FAILURE]
            reason = (
                f"No response within {STATUTORY_RESPONSE_DAYS}-day statutory period "
                f"({days_elapsed} days elapsed). FAILURE packet eligible."
            )

        elif state == DisputeState.VERIFIED_WITHOUT_CHANGE:
            # Verified without change - FAILURE packet eligible
            eligible_types = [PacketType.FAILURE]
            reason = (
                "Account verified without correction despite documented inaccuracies. "
                "FAILURE packet eligible."
            )

        elif state == DisputeState.REINSERTED:
            # Account reinserted - FAILURE packet eligible
            eligible_types = [PacketType.FAILURE]
            reason = (
                "Account reinserted after deletion without proper notification. "
                "FAILURE packet eligible."
            )

        return PacketEligibility(
            eligible_types=eligible_types,
            current_state=state,
            days_since_dispute=days_elapsed,
            reason=reason,
        )


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def is_failure_eligible(
    *,
    dispute_sent_at: datetime,
    current_time: datetime,
    response_received_at: Optional[datetime] = None,
    verified_without_change: bool = False,
    account_reinserted: bool = False,
) -> bool:
    """
    Quick check if FAILURE packet is eligible.

    Returns True if any failure condition is met:
    - No response within 30 days
    - Verified without change
    - Account reinserted
    """
    eligibility = DisputeStateMachine.check_eligibility(
        dispute_sent_at=dispute_sent_at,
        current_time=current_time,
        response_received_at=response_received_at,
        verified_without_change=verified_without_change,
        account_reinserted=account_reinserted,
        initial_packet_sent=True,  # Assume initial was sent for failure check
    )
    return eligibility.is_eligible_for(PacketType.FAILURE)


def is_response_eligible(
    *,
    response_received_at: Optional[datetime],
) -> bool:
    """
    Quick check if RESPONSE packet is eligible.

    Returns True if response has been received.
    """
    return response_received_at is not None


def days_until_failure_eligible(
    *,
    dispute_sent_at: datetime,
    current_time: datetime,
) -> int:
    """
    Calculate days until FAILURE packet becomes eligible.

    Returns:
        Days remaining (0 if already eligible, negative if past deadline)
    """
    if dispute_sent_at.tzinfo is None:
        raise ValueError("dispute_sent_at must be timezone-aware (UTC)")
    if current_time.tzinfo is None:
        raise ValueError("current_time must be timezone-aware (UTC)")

    days_elapsed = (current_time - dispute_sent_at).days
    return STATUTORY_RESPONSE_DAYS - days_elapsed
