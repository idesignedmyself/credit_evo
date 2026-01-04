"""
Evidence Ledger - Phase 4

Deterministic, append-only evidence construction.
No randomness. No mutation after build.
All summaries hard-locked.
"""

from datetime import datetime
from typing import Dict, List

from app.models.cfpb_packet import (
    EvidenceEvent,
    EvidenceLedger,
    EventType,
    Actor,
)


# =============================================================================
# HARD-LOCKED EVENT SUMMARIES
# =============================================================================

EVENT_SUMMARIES: Dict[EventType, str] = {
    EventType.REPORT_UPLOADED: "Credit report uploaded for analysis",
    EventType.VIOLATIONS_DETECTED: "Metro 2 violations detected in credit report",
    EventType.DISPUTE_LETTER_GENERATED: "Dispute letter generated",
    EventType.DISPUTE_SENT: "Dispute letter sent",
    EventType.RESPONSE_RECEIVED: "Response received from dispute recipient",
    EventType.NO_RESPONSE_30_DAYS: "No response received within 30-day statutory period",
    EventType.VERIFIED_WITHOUT_CHANGE: "Account verified without change despite documented inaccuracies",
    EventType.ACCOUNT_REINSERTED: "Previously deleted account reinserted without proper notification",
    EventType.PACKET_GENERATED_INITIAL: "Initial CFPB complaint packet generated",
    EventType.PACKET_GENERATED_RESPONSE: "CFPB response analysis packet generated",
    EventType.PACKET_GENERATED_FAILURE: "CFPB non-compliance escalation packet generated",
}


# =============================================================================
# EVENT FACTORY (DETERMINISTIC)
# =============================================================================

class EventFactory:
    """
    Factory for creating evidence events with deterministic IDs.

    No randomness. No free-text. All summaries hard-locked.
    """

    @staticmethod
    def event_id(event_type: EventType, dispute_session_id: str, suffix: str = "") -> str:
        """Generate deterministic event ID."""
        base = f"{dispute_session_id}:{event_type.value}"
        return f"{base}:{suffix}" if suffix else base

    @staticmethod
    def create(
        *,
        event_type: EventType,
        dispute_session_id: str,
        occurred_at: datetime,
        actor: Actor,
        refs: Dict[str, str],
        suffix: str = "",
    ) -> EvidenceEvent:
        """
        Create an evidence event with hard-locked summary.

        Args:
            event_type: Type of event from EventType enum
            dispute_session_id: Session identifier
            occurred_at: Timestamp (must be timezone-aware UTC)
            actor: Actor who triggered the event
            refs: Reference dictionary (hashes, channels, etc.)
            suffix: Optional suffix for event ID disambiguation

        Returns:
            EvidenceEvent with deterministic ID and hard-locked summary
        """
        return EvidenceEvent(
            event_id=EventFactory.event_id(event_type, dispute_session_id, suffix),
            event_type=event_type,
            occurred_at=occurred_at,
            actor=actor,
            summary=EVENT_SUMMARIES[event_type],
            refs=refs,
        )


# =============================================================================
# LEDGER CONSTRUCTION (IMMUTABLE)
# =============================================================================

def build_ledger(
    *,
    dispute_session_id: str,
    report_hash: str,
    events: List[EvidenceEvent],
) -> EvidenceLedger:
    """
    Construct an immutable EvidenceLedger.

    Hash is computed at build time and frozen.
    Events list is copied to prevent external mutation.
    """
    ledger_id = f"ledger:{dispute_session_id}"
    events_copy = list(events)

    sha = EvidenceLedger.compute_hash(
        ledger_id=ledger_id,
        dispute_session_id=dispute_session_id,
        report_hash=report_hash,
        events=events_copy,
    )

    return EvidenceLedger(
        ledger_id=ledger_id,
        dispute_session_id=dispute_session_id,
        report_hash=report_hash,
        events=events_copy,
        sha256=sha,
    )


# =============================================================================
# MODULE-LEVEL FACTORY INSTANCE
# =============================================================================

event_factory = EventFactory()
