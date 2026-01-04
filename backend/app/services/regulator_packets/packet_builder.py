"""
Packet Builder - Phase 4

Assembles complete RegulatorPacket from violations, letters, and evidence.
No runtime randomness. No mutation after construction.
Timestamp must be injected. All fields required.
"""

from datetime import datetime
from typing import Any, Dict, List

from app.models.cfpb_packet import (
    RegulatorPacket,
    PacketType,
    RegulatorChannel,
    EvidenceLedger,
    EvidenceEvent,
    EventType,
    Actor,
)
from app.models.letter_object import LetterObject, DemandType

from .cfpb_formatter import (
    format_cfpb_payload,
    extract_metro2_anchors,
)
from .attachment_renderer import render_all_attachments
from .evidence_ledger import EventFactory, build_ledger


# =============================================================================
# PACKET ID GENERATION (DETERMINISTIC)
# =============================================================================

def packet_id(
    packet_type: PacketType,
    dispute_session_id: str,
) -> str:
    """Generate deterministic packet ID."""
    return f"packet:{dispute_session_id}:{packet_type.value}"


# =============================================================================
# VIOLATIONS TO DICT CONVERSION
# =============================================================================

def violations_to_dicts(violations: List[Any]) -> List[Dict[str, Any]]:
    """
    Convert Violation objects to dicts for serialization.

    Handles both Violation objects (with to_dict) and raw dicts.
    """
    result = []
    for v in violations:
        if hasattr(v, "to_dict"):
            result.append(v.to_dict())
        elif isinstance(v, dict):
            result.append(v)
        else:
            raise ValueError(f"Cannot convert violation: {type(v)}")
    return result


# =============================================================================
# VALIDATION
# =============================================================================

def validate_violations_have_anchors(violations: List[Dict[str, Any]]) -> None:
    """
    Validate all violations have CRRG anchors.

    Phase 2 invariant: no violation can exist without authority mapping.
    """
    for i, v in enumerate(violations):
        citations = v.get("citations", [])
        if not citations:
            vtype = v.get("violation_type", "UNKNOWN")
            raise ValueError(
                f"Violation {i} ({vtype}) has no citations. "
                "Phase 2 invariant violated: all violations must have CRRG anchors."
            )


# =============================================================================
# LETTER HASH EXTRACTION
# =============================================================================

def extract_letter_hashes(letters: Dict[str, LetterObject]) -> List[str]:
    """
    Extract content hashes from letters.

    Sorted by channel key for determinism.
    """
    hashes = []
    for channel_key in sorted(letters.keys()):
        letter = letters[channel_key]
        hashes.append(letter.content_hash())
    return hashes


# =============================================================================
# PACKET BUILDER
# =============================================================================

class PacketBuilder:
    """
    Builds RegulatorPacket instances.

    Builder pattern - collects inputs, validates, assembles packet.
    No mutation after build. Timestamp injected externally.
    """

    def __init__(
        self,
        *,
        dispute_session_id: str,
        report_hash: str,
        packet_type: PacketType,
        channel: RegulatorChannel = RegulatorChannel.CFPB,
    ):
        """
        Initialize PacketBuilder.

        Args:
            dispute_session_id: Unique session identifier
            report_hash: SHA-256 of source credit report
            packet_type: INITIAL, RESPONSE, or FAILURE
            channel: Target regulator (default CFPB)
        """
        self._dispute_session_id = dispute_session_id
        self._report_hash = report_hash
        self._packet_type = packet_type
        self._channel = channel

        # Inputs to collect
        self._violations: List[Dict[str, Any]] = []
        self._letters: Dict[str, LetterObject] = {}
        self._events: List[EvidenceEvent] = []
        self._consumer_name: str = ""
        self._consumer_contact: Dict[str, str] = {}
        self._company_name: str = ""
        self._demand_type: DemandType = DemandType.PROCEDURAL

    def with_violations(self, violations: List[Any]) -> "PacketBuilder":
        """Add violations (Violation objects or dicts)."""
        self._violations = violations_to_dicts(violations)
        return self

    def with_letters(self, letters: Dict[str, LetterObject]) -> "PacketBuilder":
        """
        Add letters for each channel.

        Args:
            letters: Dict mapping channel suffix (cra, furnisher, mov) to LetterObject
        """
        self._letters = letters
        return self

    def with_consumer(
        self,
        name: str,
        contact: Dict[str, str],
    ) -> "PacketBuilder":
        """Add consumer information."""
        self._consumer_name = name
        self._consumer_contact = contact
        return self

    def with_company(self, name: str) -> "PacketBuilder":
        """Add target company (furnisher or CRA) name."""
        self._company_name = name
        return self

    def with_demand_type(self, demand_type: DemandType) -> "PacketBuilder":
        """Set demand type (from letter generation)."""
        self._demand_type = demand_type
        return self

    def with_events(self, events: List[EvidenceEvent]) -> "PacketBuilder":
        """Add evidence ledger events."""
        self._events = list(events)
        return self

    def add_event(self, event: EvidenceEvent) -> "PacketBuilder":
        """Add a single evidence event."""
        self._events.append(event)
        return self

    def build(self, generated_at: datetime) -> RegulatorPacket:
        """
        Build the RegulatorPacket.

        Args:
            generated_at: Timestamp for packet generation (MUST be injected)

        Returns:
            Complete RegulatorPacket

        Raises:
            ValueError: If required inputs are missing or invalid
        """
        # Phase 4 invariant: ledger cannot be empty
        if not self._events:
            raise ValueError(
                "Evidence ledger cannot be empty. "
                "Phase 4 forbids packet generation without ledger events."
            )

        # Validate timezone awareness
        if generated_at.tzinfo is None:
            raise ValueError("generated_at must be timezone-aware (UTC)")

        # Validate violations have anchors
        validate_violations_have_anchors(self._violations)

        # Validate required fields
        if not self._consumer_name:
            raise ValueError("Consumer name is required")
        if not self._company_name:
            raise ValueError("Company name is required")
        if not self._letters:
            raise ValueError("At least one letter is required")

        # Extract CRRG anchors from violations
        anchors = extract_metro2_anchors(self._violations)

        # Build evidence ledger
        ledger = build_ledger(
            dispute_session_id=self._dispute_session_id,
            report_hash=self._report_hash,
            events=self._events,
        )

        # Render attachments
        attachments = render_all_attachments(
            dispute_session_id=self._dispute_session_id,
            letters=self._letters,
            violations=self._violations,
            anchors=anchors,
            ledger=ledger,
        )

        # Build attachments index for CFPB payload
        attachments_index = [
            {"filename": a.filename, "sha256": a.sha256}
            for a in attachments
        ]

        # Format CFPB complaint payload
        complaint_payload = format_cfpb_payload(
            violations=self._violations,
            company_name=self._company_name,
            consumer_name=self._consumer_name,
            consumer_contact=self._consumer_contact,
            demand_type=self._demand_type,
            attachments_index=attachments_index,
        )

        # Extract letter hashes
        letter_hashes = extract_letter_hashes(self._letters)

        # Prepare packet ID
        pid = packet_id(self._packet_type, self._dispute_session_id)

        # Compute packet hash before construction (Phase 4 determinism)
        packet_hash = RegulatorPacket.compute_packet_hash(
            packet_id=pid,
            packet_type=self._packet_type,
            channel=self._channel,
            dispute_session_id=self._dispute_session_id,
            report_hash=self._report_hash,
            letter_hashes=letter_hashes,
            violations=self._violations,
            complaint_payload=complaint_payload,
            attachments=attachments,
            ledger=ledger,
        )

        # Build packet with pre-computed hash
        packet = RegulatorPacket(
            packet_id=pid,
            packet_type=self._packet_type,
            channel=self._channel,
            dispute_session_id=self._dispute_session_id,
            report_hash=self._report_hash,
            complaint_payload=complaint_payload,
            ledger=ledger,
            generated_at=generated_at,
            letter_hashes=letter_hashes,
            violations=self._violations,
            attachments=attachments,
            packet_hash=packet_hash,
        )

        return packet


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def build_initial_packet(
    *,
    dispute_session_id: str,
    report_hash: str,
    violations: List[Any],
    letters: Dict[str, LetterObject],
    consumer_name: str,
    consumer_contact: Dict[str, str],
    company_name: str,
    demand_type: DemandType,
    events: List[EvidenceEvent],
    generated_at: datetime,
) -> RegulatorPacket:
    """
    Build an INITIAL packet (first submission to CFPB).

    Convenience wrapper around PacketBuilder.
    """
    return (
        PacketBuilder(
            dispute_session_id=dispute_session_id,
            report_hash=report_hash,
            packet_type=PacketType.INITIAL,
        )
        .with_violations(violations)
        .with_letters(letters)
        .with_consumer(consumer_name, consumer_contact)
        .with_company(company_name)
        .with_demand_type(demand_type)
        .with_events(events)
        .build(generated_at)
    )


def build_failure_packet(
    *,
    dispute_session_id: str,
    report_hash: str,
    violations: List[Any],
    letters: Dict[str, LetterObject],
    consumer_name: str,
    consumer_contact: Dict[str, str],
    company_name: str,
    demand_type: DemandType,
    events: List[EvidenceEvent],
    generated_at: datetime,
) -> RegulatorPacket:
    """
    Build a FAILURE packet (no response / inadequate response).

    Convenience wrapper around PacketBuilder.
    """
    return (
        PacketBuilder(
            dispute_session_id=dispute_session_id,
            report_hash=report_hash,
            packet_type=PacketType.FAILURE,
        )
        .with_violations(violations)
        .with_letters(letters)
        .with_consumer(consumer_name, consumer_contact)
        .with_company(company_name)
        .with_demand_type(demand_type)
        .with_events(events)
        .build(generated_at)
    )


def build_response_packet(
    *,
    dispute_session_id: str,
    report_hash: str,
    violations: List[Any],
    letters: Dict[str, LetterObject],
    consumer_name: str,
    consumer_contact: Dict[str, str],
    company_name: str,
    demand_type: DemandType,
    events: List[EvidenceEvent],
    generated_at: datetime,
) -> RegulatorPacket:
    """
    Build a RESPONSE packet (bureau/furnisher response analyzed).

    Convenience wrapper around PacketBuilder.
    """
    return (
        PacketBuilder(
            dispute_session_id=dispute_session_id,
            report_hash=report_hash,
            packet_type=PacketType.RESPONSE,
        )
        .with_violations(violations)
        .with_letters(letters)
        .with_consumer(consumer_name, consumer_contact)
        .with_company(company_name)
        .with_demand_type(demand_type)
        .with_events(events)
        .build(generated_at)
    )
