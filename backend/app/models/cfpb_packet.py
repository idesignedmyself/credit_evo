"""
CFPB Packet Data Contracts - Phase 4

Canonical dataclasses for regulator packets.
All hashes computed from canonical JSON with sort_keys=True.
No runtime randomness. Datetimes always UTC aware.
Timestamps are injected, never generated in contracts.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from hashlib import sha256
from typing import Any, Dict, List
import json


# =============================================================================
# ENUMS
# =============================================================================

class PacketType(str, Enum):
    """Type of regulator packet."""
    INITIAL = "INITIAL"  # First submission to CFPB
    RESPONSE = "RESPONSE"  # Bureau/furnisher response analyzed
    FAILURE = "FAILURE"  # No response / inadequate response / verified-without-change


class RegulatorChannel(str, Enum):
    """Target regulator channel."""
    CFPB = "CFPB"
    STATE_AG = "STATE_AG"
    OTHER = "OTHER"


class AttachmentType(str, Enum):
    """Type of packet attachment."""
    DISPUTE_LETTER = "DISPUTE_LETTER"
    EVIDENCE = "EVIDENCE"
    LEDGER = "LEDGER"
    EXHIBITS = "EXHIBITS"
    RESPONSE_ANALYSIS = "RESPONSE_ANALYSIS"


class EventType(str, Enum):
    """
    Evidence ledger event types.

    DISPUTE_SENT is a single event type; the channel (CRA/FURNISHER/MOV)
    is specified in the event's refs["channel"] field.
    """
    REPORT_UPLOADED = "REPORT_UPLOADED"
    VIOLATIONS_DETECTED = "VIOLATIONS_DETECTED"
    DISPUTE_LETTER_GENERATED = "DISPUTE_LETTER_GENERATED"
    DISPUTE_SENT = "DISPUTE_SENT"  # refs["channel"] specifies CRA/FURNISHER/MOV
    RESPONSE_RECEIVED = "RESPONSE_RECEIVED"
    NO_RESPONSE_30_DAYS = "NO_RESPONSE_30_DAYS"
    VERIFIED_WITHOUT_CHANGE = "VERIFIED_WITHOUT_CHANGE"
    ACCOUNT_REINSERTED = "ACCOUNT_REINSERTED"
    PACKET_GENERATED_INITIAL = "PACKET_GENERATED_INITIAL"
    PACKET_GENERATED_RESPONSE = "PACKET_GENERATED_RESPONSE"
    PACKET_GENERATED_FAILURE = "PACKET_GENERATED_FAILURE"


class Actor(str, Enum):
    """Event actor types."""
    CONSUMER = "CONSUMER"
    CRA = "CRA"
    FURNISHER = "FURNISHER"
    CFPB = "CFPB"
    SYSTEM = "SYSTEM"


# =============================================================================
# ATTACHMENT
# =============================================================================

@dataclass
class PacketAttachment:
    """
    Single attachment in a regulator packet.

    Content is base64 encoded for deterministic serialization.
    SHA256 hash ensures integrity.
    """
    attachment_id: str
    attachment_type: AttachmentType
    filename: str
    mime_type: str
    content_bytes_b64: str  # deterministic base64 encoding
    sha256: str  # full SHA-256 hash of raw bytes before encoding

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "attachment_id": self.attachment_id,
            "attachment_type": self.attachment_type.value,
            "filename": self.filename,
            "mime_type": self.mime_type,
            "content_bytes_b64": self.content_bytes_b64,
            "sha256": self.sha256,
        }


# =============================================================================
# EVIDENCE LEDGER
# =============================================================================

@dataclass
class EvidenceEvent:
    """
    Single event in the evidence ledger.

    Events are immutable. Summary text is hard-locked - no free-text.
    """
    event_id: str
    event_type: EventType
    occurred_at: datetime  # MUST be timezone-aware UTC
    actor: Actor
    summary: str  # hard-locked short string, no free-text
    refs: Dict[str, str] = field(default_factory=dict)  # letter_hash, report_hash, channel, etc.

    def __post_init__(self):
        """Validate timezone awareness."""
        if self.occurred_at.tzinfo is None:
            raise ValueError("occurred_at must be timezone-aware (UTC)")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "occurred_at": self.occurred_at.isoformat(),
            "actor": self.actor.value,
            "summary": self.summary,
            "refs": self.refs,
        }

    def content_hash(self) -> str:
        """Compute deterministic full SHA-256 hash of event content."""
        content = json.dumps(self.to_dict(), sort_keys=True)
        return sha256(content.encode()).hexdigest()


@dataclass
class EvidenceLedger:
    """
    Immutable chain of evidence events.

    Ledger is constructed once with a finalized events list.
    Hash is computed at build time and stored as sha256 field.
    No mutation methods - ledger construction is external.
    """
    ledger_id: str
    dispute_session_id: str
    report_hash: str
    events: List[EvidenceEvent]
    sha256: str  # Computed at build time, stored immutably

    @staticmethod
    def compute_hash(
        *,
        ledger_id: str,
        dispute_session_id: str,
        report_hash: str,
        events: List[EvidenceEvent],
    ) -> str:
        """Compute deterministic full SHA-256 hash of ledger content."""
        content = {
            "ledger_id": ledger_id,
            "dispute_session_id": dispute_session_id,
            "report_hash": report_hash,
            "events": [e.to_dict() for e in events],
        }
        return sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "ledger_id": self.ledger_id,
            "dispute_session_id": self.dispute_session_id,
            "report_hash": self.report_hash,
            "events": [e.to_dict() for e in self.events],
            "sha256": self.sha256,
        }


# =============================================================================
# CFPB COMPLAINT PAYLOAD
# =============================================================================

@dataclass
class CFPBComplaintPayload:
    """
    Structured CFPB complaint payload.

    All fields are deterministic. Narrative is assembled from blocks.
    No free-text writing allowed.
    """
    product: str  # e.g., "Credit reporting, credit repair services, or other personal consumer reports"
    issue: str  # e.g., "Incorrect information on your report"
    sub_issue: str  # e.g., "Account status incorrect"
    company_name: str  # Furnisher or CRA name
    consumer_name: str
    consumer_contact: Dict[str, str]  # email, phone, address fields
    narrative: str  # assembled from deterministic blocks only
    desired_resolution: str  # hard-locked resolution text
    disputed_account_refs: List[Dict[str, str]] = field(default_factory=list)  # creditor, acct_mask, etc.
    statutes: List[str] = field(default_factory=list)  # FCRA sections cited
    metro2_anchors: List[Dict[str, Any]] = field(default_factory=list)  # CRRG anchors
    attachments_index: List[Dict[str, str]] = field(default_factory=list)  # filename, sha256

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "product": self.product,
            "issue": self.issue,
            "sub_issue": self.sub_issue,
            "company_name": self.company_name,
            "consumer_name": self.consumer_name,
            "consumer_contact": self.consumer_contact,
            "narrative": self.narrative,
            "desired_resolution": self.desired_resolution,
            "disputed_account_refs": self.disputed_account_refs,
            "statutes": self.statutes,
            "metro2_anchors": self.metro2_anchors,
            "attachments_index": self.attachments_index,
        }

    def content_hash(self) -> str:
        """Compute deterministic full SHA-256 hash of payload content."""
        content = json.dumps(self.to_dict(), sort_keys=True)
        return sha256(content.encode()).hexdigest()


# =============================================================================
# REGULATOR PACKET
# =============================================================================

@dataclass
class RegulatorPacket:
    """
    Complete regulator packet with all components.

    Contains:
    - CFPB complaint payload (required)
    - Attachment bundle
    - Evidence ledger (required)
    - Deterministic packet hash (computed at build time, stored immutably)

    Packets cannot exist without a ledger and complaint payload.
    Timestamp must be injected - no runtime generation.
    Hash must be computed at build time and passed to constructor.
    """
    packet_id: str
    packet_type: PacketType
    channel: RegulatorChannel
    dispute_session_id: str
    report_hash: str
    complaint_payload: CFPBComplaintPayload  # required, not optional
    ledger: EvidenceLedger  # required, not optional
    generated_at: datetime  # must be injected, not generated
    packet_hash: str  # computed at build time, stored immutably
    letter_hashes: List[str] = field(default_factory=list)
    violations: List[Dict[str, Any]] = field(default_factory=list)
    attachments: List[PacketAttachment] = field(default_factory=list)

    def __post_init__(self):
        """Validate timezone awareness."""
        if self.generated_at.tzinfo is None:
            raise ValueError("generated_at must be timezone-aware (UTC)")

    @staticmethod
    def compute_packet_hash(
        *,
        packet_id: str,
        packet_type: PacketType,
        channel: RegulatorChannel,
        dispute_session_id: str,
        report_hash: str,
        letter_hashes: List[str],
        violations: List[Dict[str, Any]],
        complaint_payload: CFPBComplaintPayload,
        attachments: List[PacketAttachment],
        ledger: EvidenceLedger,
    ) -> str:
        """
        Compute deterministic full SHA-256 hash of packet content.

        Hash excludes generated_at for stability when regenerating.
        Called at build time before construction.
        """
        content = {
            "packet_id": packet_id,
            "packet_type": packet_type.value,
            "channel": channel.value,
            "dispute_session_id": dispute_session_id,
            "report_hash": report_hash,
            "letter_hashes": sorted(letter_hashes),
            "violations": violations,
            "complaint_payload": complaint_payload.to_dict(),
            "attachments": [a.to_dict() for a in attachments],
            "ledger": ledger.to_dict(),
        }
        return sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "packet_id": self.packet_id,
            "packet_type": self.packet_type.value,
            "channel": self.channel.value,
            "dispute_session_id": self.dispute_session_id,
            "report_hash": self.report_hash,
            "letter_hashes": self.letter_hashes,
            "violations": self.violations,
            "complaint_payload": self.complaint_payload.to_dict(),
            "attachments": [a.to_dict() for a in self.attachments],
            "ledger": self.ledger.to_dict(),
            "generated_at": self.generated_at.isoformat(),
            "packet_hash": self.packet_hash,
        }
