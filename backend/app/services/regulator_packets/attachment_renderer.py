"""
Attachment Renderer - Phase 4

Renders deterministic attachments from letters, violations, and ledgers.
All output is base64 encoded with SHA-256 hashes.
No runtime randomness. Same inputs → same attachment hashes.
"""

import base64
import json
from hashlib import sha256
from typing import Any, Dict, List

from app.models.cfpb_packet import (
    PacketAttachment,
    AttachmentType,
    EvidenceLedger,
)
from app.models.letter_object import LetterObject, LetterSection


# =============================================================================
# ATTACHMENT ID GENERATION (DETERMINISTIC)
# =============================================================================

def attachment_id(
    attachment_type: AttachmentType,
    dispute_session_id: str,
    suffix: str = "",
) -> str:
    """Generate deterministic attachment ID."""
    base = f"{dispute_session_id}:{attachment_type.value}"
    return f"{base}:{suffix}" if suffix else base


# =============================================================================
# CONTENT ENCODING
# =============================================================================

def encode_content(content: str) -> tuple[str, str]:
    """
    Encode content to base64 and compute SHA-256 hash.

    Args:
        content: Plain text content

    Returns:
        Tuple of (base64_encoded_content, sha256_hash_of_raw_bytes)
    """
    raw_bytes = content.encode("utf-8")
    content_b64 = base64.b64encode(raw_bytes).decode("ascii")
    content_hash = sha256(raw_bytes).hexdigest()
    return content_b64, content_hash


# =============================================================================
# LETTER RENDERER
# =============================================================================

def render_letter_text(letter: LetterObject) -> str:
    """
    Render LetterObject to plain text format.

    Renders blocks in canonical section order.
    No free-text additions.
    """
    lines = []

    # Section order is fixed by LetterSection enum
    for section in LetterSection:
        blocks = letter.sections.get(section, [])
        if not blocks:
            continue

        # Section header
        lines.append(f"=== {section.value} ===")
        lines.append("")

        for block in blocks:
            lines.append(block.text)
            lines.append("")

            # Add citations if present
            if block.anchors:
                for anchor in block.anchors:
                    anchor_id = anchor.get("anchor_id", "")
                    section_title = anchor.get("section_title", "")
                    page_start = anchor.get("page_start", "")
                    page_end = anchor.get("page_end", "")
                    lines.append(f"  [CRRG: {anchor_id} - {section_title}, pp. {page_start}-{page_end}]")

            if block.statutes:
                statutes_str = ", ".join(sorted(block.statutes))
                lines.append(f"  [Statutes: {statutes_str}]")

            lines.append("")

    return "\n".join(lines)


def render_letter_attachment(
    letter: LetterObject,
    dispute_session_id: str,
    suffix: str,
) -> PacketAttachment:
    """
    Render LetterObject to PacketAttachment.

    Args:
        letter: LetterObject to render
        dispute_session_id: Session ID for attachment ID
        suffix: Channel suffix (cra, furnisher, mov) - REQUIRED

    Returns:
        PacketAttachment with plain text letter
    """
    content = render_letter_text(letter)
    content_b64, content_hash = encode_content(content)

    # Filename is strictly suffix-driven (builder decides naming)
    filename = f"dispute_letter_{suffix}.txt"

    return PacketAttachment(
        attachment_id=attachment_id(AttachmentType.DISPUTE_LETTER, dispute_session_id, suffix),
        attachment_type=AttachmentType.DISPUTE_LETTER,
        filename=filename,
        mime_type="text/plain",
        content_bytes_b64=content_b64,
        sha256=content_hash,
    )


# =============================================================================
# VIOLATION APPENDIX RENDERER
# =============================================================================

def render_violation_table(violations: List[Dict[str, Any]]) -> str:
    """
    Render violations as human-readable table.

    Format:
    | # | Violation Type | Creditor | Account | Severity |
    |---|----------------|----------|---------|----------|
    """
    lines = [
        "VIOLATION APPENDIX",
        "=" * 80,
        "",
        "| # | Violation Type | Creditor | Account | Severity |",
        "|---|----------------|----------|---------|----------|",
    ]

    # Sort violations by type for determinism
    violations_sorted = sorted(
        violations,
        key=lambda v: v.get("violation_type", "")
    )

    for i, v in enumerate(violations_sorted, 1):
        vtype = v.get("violation_type", "UNKNOWN")
        creditor = v.get("creditor_name", "Unknown")
        acct = v.get("account_number_masked", "****")
        severity = v.get("severity", "UNKNOWN")
        lines.append(f"| {i} | {vtype} | {creditor} | {acct} | {severity} |")

    lines.append("")
    lines.append("=" * 80)
    lines.append("")
    lines.append("CANONICAL JSON:")
    lines.append("")

    # Canonical JSON with sorted keys
    canonical_json = json.dumps(violations_sorted, sort_keys=True, indent=2)
    lines.append(canonical_json)

    return "\n".join(lines)


def render_violation_appendix(
    violations: List[Dict[str, Any]],
    dispute_session_id: str,
) -> PacketAttachment:
    """
    Render violations to PacketAttachment.

    Args:
        violations: List of violation dicts
        dispute_session_id: Session ID for attachment ID

    Returns:
        PacketAttachment with violation table + JSON
    """
    content = render_violation_table(violations)
    content_b64, content_hash = encode_content(content)

    return PacketAttachment(
        attachment_id=attachment_id(AttachmentType.EVIDENCE, dispute_session_id, "violations"),
        attachment_type=AttachmentType.EVIDENCE,
        filename="violation_appendix.txt",
        mime_type="text/plain",
        content_bytes_b64=content_b64,
        sha256=content_hash,
    )


# =============================================================================
# CRRG ANCHOR APPENDIX RENDERER
# =============================================================================

def render_anchor_table(anchors: List[Dict[str, Any]]) -> str:
    """
    Render CRRG anchors as human-readable appendix.

    Lists all cited CRRG sections with page references.
    """
    lines = [
        "CRRG ANCHOR APPENDIX",
        "=" * 80,
        "",
        "The following Credit Reporting Resource Guide (CRRG) sections are cited",
        "as authority for the violations documented in this complaint.",
        "",
        "| Anchor ID | Rule ID | Section Title | Pages |",
        "|-----------|---------|---------------|-------|",
    ]

    # Sort by anchor_id for determinism
    anchors_sorted = sorted(anchors, key=lambda a: a.get("anchor_id", ""))

    for anchor in anchors_sorted:
        anchor_id = anchor.get("anchor_id", "")
        rule_id = anchor.get("rule_id", "")
        section = anchor.get("section_title", "")
        page_start = anchor.get("page_start", "")
        page_end = anchor.get("page_end", "")
        pages = f"{page_start}-{page_end}"
        lines.append(f"| {anchor_id} | {rule_id} | {section} | {pages} |")

    lines.append("")
    lines.append("=" * 80)

    return "\n".join(lines)


def render_anchor_appendix(
    anchors: List[Dict[str, Any]],
    dispute_session_id: str,
) -> PacketAttachment:
    """
    Render CRRG anchors to PacketAttachment.

    Args:
        anchors: List of anchor dicts (from violations)
        dispute_session_id: Session ID for attachment ID

    Returns:
        PacketAttachment with anchor table
    """
    content = render_anchor_table(anchors)
    content_b64, content_hash = encode_content(content)

    return PacketAttachment(
        attachment_id=attachment_id(AttachmentType.EXHIBITS, dispute_session_id, "crrg_anchors"),
        attachment_type=AttachmentType.EXHIBITS,
        filename="crrg_anchor_appendix.txt",
        mime_type="text/plain",
        content_bytes_b64=content_b64,
        sha256=content_hash,
    )


# =============================================================================
# EVIDENCE LEDGER RENDERER
# =============================================================================

def render_ledger_text(ledger: EvidenceLedger) -> str:
    """
    Render EvidenceLedger as human-readable export.

    Lists all events with timestamps.
    Ledger sha256 is authoritative; no per-event hashes.
    """
    lines = [
        "EVIDENCE LEDGER",
        "=" * 80,
        "",
        f"Ledger ID: {ledger.ledger_id}",
        f"Dispute Session: {ledger.dispute_session_id}",
        f"Report Hash: {ledger.report_hash}",
        f"Ledger SHA-256: {ledger.sha256}",
        "",
        "EVENTS:",
        "-" * 80,
        "",
    ]

    for event in ledger.events:
        lines.append(f"Event: {event.event_id}")
        lines.append(f"  Type: {event.event_type.value}")
        lines.append(f"  Occurred: {event.occurred_at.isoformat()}")
        lines.append(f"  Actor: {event.actor.value}")
        lines.append(f"  Summary: {event.summary}")
        if event.refs:
            refs_str = json.dumps(event.refs, sort_keys=True)
            lines.append(f"  Refs: {refs_str}")
        # No per-event hash; ledger sha256 is authoritative
        lines.append("")

    lines.append("=" * 80)
    lines.append("")
    lines.append("CANONICAL JSON:")
    lines.append("")
    lines.append(json.dumps(ledger.to_dict(), sort_keys=True, indent=2))

    return "\n".join(lines)


def render_ledger_attachment(
    ledger: EvidenceLedger,
    dispute_session_id: str,
) -> PacketAttachment:
    """
    Render EvidenceLedger to PacketAttachment.

    Args:
        ledger: EvidenceLedger to render
        dispute_session_id: Session ID for attachment ID

    Returns:
        PacketAttachment with ledger export
    """
    content = render_ledger_text(ledger)
    content_b64, content_hash = encode_content(content)

    return PacketAttachment(
        attachment_id=attachment_id(AttachmentType.LEDGER, dispute_session_id, "evidence"),
        attachment_type=AttachmentType.LEDGER,
        filename="evidence_ledger.txt",
        mime_type="text/plain",
        content_bytes_b64=content_b64,
        sha256=content_hash,
    )


# =============================================================================
# BATCH RENDERER
# =============================================================================

def render_all_attachments(
    *,
    dispute_session_id: str,
    letters: Dict[str, LetterObject],
    violations: List[Dict[str, Any]],
    anchors: List[Dict[str, Any]],
    ledger: EvidenceLedger,
) -> List[PacketAttachment]:
    """
    Render all packet attachments.

    Args:
        dispute_session_id: Session ID for attachment IDs
        letters: Dict mapping channel suffix to LetterObject
        violations: List of violation dicts
        anchors: List of CRRG anchor dicts
        ledger: EvidenceLedger instance

    Returns:
        List of PacketAttachment in deterministic order
    """
    attachments = []

    # 1. Letters (sorted by channel key for determinism)
    for channel_key in sorted(letters.keys()):
        letter = letters[channel_key]
        attachments.append(
            render_letter_attachment(letter, dispute_session_id, suffix=channel_key)
        )

    # 2. Violation appendix
    attachments.append(
        render_violation_appendix(violations, dispute_session_id)
    )

    # 3. CRRG anchor appendix
    attachments.append(
        render_anchor_appendix(anchors, dispute_session_id)
    )

    # 4. Evidence ledger
    attachments.append(
        render_ledger_attachment(ledger, dispute_session_id)
    )

    return attachments
