"""
Letter Object Models - Phase 3 Deterministic Letter Generation

These models define the canonical structure for dispute letters.
Letters are ASSEMBLED from blocks, not WRITTEN.

Core Principle: Zero narrative variance - same inputs produce identical outputs.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from hashlib import sha256
from typing import Any, Dict, List, Optional
import json

from .ssot import Severity


class LetterChannel(str, Enum):
    """Letter delivery channel - determines framing wrapper."""
    CRA = "CRA"  # Credit Reporting Agency (§611 framing)
    FURNISHER = "FURNISHER"  # Data furnisher (§623 framing)
    MOV = "MOV"  # Method of Verification request


class LetterSection(str, Enum):
    """Canonical letter sections - order is fixed by renderer."""
    HEADER = "HEADER"
    PARTIES = "PARTIES"
    ACCOUNT_IDENTIFICATION = "ACCOUNT_IDENTIFICATION"
    FACTUAL_INACCURACIES = "FACTUAL_INACCURACIES"
    STATUTORY_AUTHORITY = "STATUTORY_AUTHORITY"
    DEMAND = "DEMAND"
    CLOSING = "CLOSING"


class DemandType(str, Enum):
    """Demand resolution - determined by violation severity."""
    DELETION = "DELETION"  # >=1 CRITICAL or >=2 HIGH
    CORRECTION = "CORRECTION"  # MEDIUM only
    PROCEDURAL = "PROCEDURAL"  # No violations / compliance request


@dataclass
class LetterBlock:
    """
    Atomic unit of letter content.

    Each violation produces exactly ONE block.
    Blocks are immutable and hashable.
    """
    block_id: str
    violation_id: str
    severity: Severity
    section: LetterSection
    text: str

    # CRRG anchor references
    # REQUIRED KEYS: anchor_id, rule_id, section_title, page_start, page_end
    # OPTIONAL KEYS: exhibit_id, fields, anchor_summary, fcra_cite
    anchors: List[Dict[str, Any]] = field(default_factory=list)

    # FCRA/ECOA statute citations (USC format)
    statutes: List[str] = field(default_factory=list)

    # Metro 2 field reference (e.g., "Field 24", "Field 17A")
    metro2_field: Optional[str] = None

    def content_hash(self) -> str:
        """
        Generate deterministic hash of block content.

        Used to verify letter stability - same inputs = same hash.
        """
        content = {
            "block_id": self.block_id,
            "violation_id": self.violation_id,
            "severity": self.severity.value,
            "section": self.section.value,
            "text": self.text,
            "anchors": self.anchors,
            "statutes": sorted(self.statutes),
            "metro2_field": self.metro2_field,
        }
        return sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "block_id": self.block_id,
            "violation_id": self.violation_id,
            "severity": self.severity.value,
            "section": self.section.value,
            "text": self.text,
            "anchors": self.anchors,
            "statutes": self.statutes,
            "metro2_field": self.metro2_field,
            "content_hash": self.content_hash(),
        }


@dataclass
class LetterObject:
    """
    Complete letter assembled from blocks.

    - channel: Determines wrapper (CRA/FURNISHER/MOV)
    - sections: Dict mapping section names to block lists
    - metadata: Dispute context (session_id, report_hash, timestamps)

    Letters are assembled by the renderer - this object provides the blocks.
    """
    channel: LetterChannel
    sections: Dict[LetterSection, List[LetterBlock]] = field(default_factory=dict)
    demand_type: DemandType = DemandType.PROCEDURAL

    # Metadata for traceability
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Generation timestamp
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self):
        """Initialize empty sections."""
        for section in LetterSection:
            if section not in self.sections:
                self.sections[section] = []

    def add_block(self, block: LetterBlock) -> None:
        """Add a block to its designated section."""
        if block.section not in self.sections:
            self.sections[block.section] = []
        self.sections[block.section].append(block)

    def get_all_blocks(self) -> List[LetterBlock]:
        """Get all blocks in section order."""
        blocks = []
        for section in LetterSection:
            blocks.extend(self.sections.get(section, []))
        return blocks

    def get_all_statutes(self) -> List[str]:
        """Extract deduplicated statute list from all blocks."""
        statutes = set()
        for block in self.get_all_blocks():
            statutes.update(block.statutes)
        return sorted(statutes)

    def get_all_anchors(self) -> List[Dict[str, Any]]:
        """
        Extract all CRRG anchors from blocks.

        Deduplicates by anchor_id (REQUIRED key in anchor dicts).
        """
        anchors = []
        seen = set()
        for block in self.get_all_blocks():
            for anchor in block.anchors:
                # anchor_id is REQUIRED - see LetterBlock.anchors docstring
                anchor_id = anchor.get("anchor_id", "")
                if anchor_id and anchor_id not in seen:
                    anchors.append(anchor)
                    seen.add(anchor_id)
        return anchors

    def content_hash(self) -> str:
        """
        Generate deterministic hash of entire letter.

        Proves letter stability - same violations = same letter hash.
        """
        content = {
            "channel": self.channel.value,
            "demand_type": self.demand_type.value,
            "blocks": [b.content_hash() for b in self.get_all_blocks()],
            "metadata": {k: v for k, v in self.metadata.items()
                        if k not in ["generated_at", "letter_hash"]},
        }
        return sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "channel": self.channel.value,
            "demand_type": self.demand_type.value,
            "sections": {
                section.value: [b.to_dict() for b in blocks]
                for section, blocks in self.sections.items()
            },
            "statutes": self.get_all_statutes(),
            "anchors": self.get_all_anchors(),
            "metadata": self.metadata,
            "generated_at": self.generated_at.isoformat(),
            "content_hash": self.content_hash(),
        }


# =============================================================================
# LETTER SECTION CONTENT TYPES
# =============================================================================

@dataclass
class HeaderContent:
    """Header section content."""
    date: str
    reference_number: Optional[str] = None
    dispute_session_id: Optional[str] = None


@dataclass
class PartiesContent:
    """Parties section content."""
    consumer_name: str
    consumer_address: str
    recipient_name: str
    recipient_address: str


@dataclass
class AccountContent:
    """Account identification section content."""
    creditor_name: str
    account_number_masked: str
    account_type: Optional[str] = None
    date_opened: Optional[str] = None
    current_balance: Optional[str] = None


@dataclass
class DemandContent:
    """Demand section content."""
    demand_type: DemandType
    demand_text: str
    response_deadline_days: int = 30
