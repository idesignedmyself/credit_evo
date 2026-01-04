"""
Regulator Packets - Phase 4

Examiner-ready CFPB complaint packet generation.
Deterministic. No narrative variance. Hash everything.
"""

from .evidence_ledger import (
    EventFactory,
    event_factory,
    build_ledger,
    EVENT_SUMMARIES,
)

from .cfpb_formatter import (
    format_cfpb_payload,
    assemble_narrative,
    resolve_category,
    resolve_desired_resolution,
    extract_metro2_anchors,
    extract_disputed_accounts,
    extract_statutes,
    CFPB_ISSUE_MAP,
)

from .attachment_renderer import (
    render_letter_attachment,
    render_violation_appendix,
    render_anchor_appendix,
    render_ledger_attachment,
    render_all_attachments,
)

from .packet_builder import (
    PacketBuilder,
    build_initial_packet,
    build_failure_packet,
    build_response_packet,
)

from .state_machine import (
    DisputeStateMachine,
    DisputeState,
    PacketEligibility,
    is_failure_eligible,
    is_response_eligible,
    days_until_failure_eligible,
    STATUTORY_RESPONSE_DAYS,
    EXTENDED_RESPONSE_DAYS,
)


__all__ = [
    # Evidence Ledger
    "EventFactory",
    "event_factory",
    "build_ledger",
    "EVENT_SUMMARIES",
    # CFPB Formatter
    "format_cfpb_payload",
    "assemble_narrative",
    "resolve_category",
    "resolve_desired_resolution",
    "extract_metro2_anchors",
    "extract_disputed_accounts",
    "extract_statutes",
    "CFPB_ISSUE_MAP",
    # Attachment Renderer
    "render_letter_attachment",
    "render_violation_appendix",
    "render_anchor_appendix",
    "render_ledger_attachment",
    "render_all_attachments",
    # Packet Builder
    "PacketBuilder",
    "build_initial_packet",
    "build_failure_packet",
    "build_response_packet",
    # State Machine
    "DisputeStateMachine",
    "DisputeState",
    "PacketEligibility",
    "is_failure_eligible",
    "is_response_eligible",
    "days_until_failure_eligible",
    "STATUTORY_RESPONSE_DAYS",
    "EXTENDED_RESPONSE_DAYS",
]
