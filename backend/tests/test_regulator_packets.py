"""
Phase 4 Regulator Packets - Determinism Tests

Tests verify:
1. Same inputs → same outputs (hash stability)
2. Evidence ledger construction
3. CFPB formatter narrative assembly
4. Attachment renderer determinism
5. Packet builder validation
6. State machine eligibility rules
"""

import json
import pytest
from datetime import datetime, timezone, timedelta
from hashlib import sha256

from app.models.cfpb_packet import (
    RegulatorPacket,
    PacketType,
    RegulatorChannel,
    EvidenceLedger,
    EvidenceEvent,
    EventType,
    Actor,
    CFPBComplaintPayload,
    PacketAttachment,
    AttachmentType,
)
from app.models.letter_object import (
    LetterObject,
    LetterBlock,
    LetterChannel,
    LetterSection,
    DemandType,
)
from app.models.ssot import Severity

from app.services.regulator_packets.evidence_ledger import (
    EventFactory,
    build_ledger,
    EVENT_SUMMARIES,
)
from app.services.regulator_packets.cfpb_formatter import (
    format_cfpb_payload,
    assemble_narrative,
    resolve_category,
    resolve_desired_resolution,
    extract_metro2_anchors,
    CFPB_ISSUE_MAP,
)
from app.services.regulator_packets.attachment_renderer import (
    render_letter_attachment,
    render_violation_appendix,
    render_anchor_appendix,
    render_ledger_attachment,
    render_all_attachments,
    encode_content,
)
from app.services.regulator_packets.packet_builder import (
    PacketBuilder,
    build_initial_packet,
)
from app.services.regulator_packets.state_machine import (
    DisputeStateMachine,
    DisputeState,
    is_failure_eligible,
    days_until_failure_eligible,
    STATUTORY_RESPONSE_DAYS,
)


# =============================================================================
# TEST FIXTURES
# =============================================================================

@pytest.fixture
def fixed_timestamp():
    """Fixed UTC timestamp for determinism tests."""
    return datetime(2026, 1, 3, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def dispute_session_id():
    """Fixed dispute session ID."""
    return "session_001"


@pytest.fixture
def report_hash():
    """Fixed report hash."""
    return "abc123def456"


@pytest.fixture
def sample_violation():
    """Sample violation dict with citations."""
    return {
        "violation_type": "balance_mismatch",
        "creditor_name": "Test Bank",
        "account_number_masked": "****1234",
        "account_type": "revolving",
        "severity": "HIGH",
        "statutes": ["15 U.S.C. § 1681e(b)", "15 U.S.C. § 1681i"],
        "citations": [
            {
                "anchor_id": "crrg_balance_001",
                "rule_id": "RULE_BALANCE_01",
                "section_title": "Balance Reporting",
                "page_start": 45,
                "page_end": 47,
            }
        ],
    }


@pytest.fixture
def sample_letter(fixed_timestamp):
    """Sample LetterObject."""
    letter = LetterObject(
        channel=LetterChannel.CRA,
        demand_type=DemandType.DELETION,
        metadata={"dispute_session_id": "session_001"},
        generated_at=fixed_timestamp,
    )
    letter.add_block(LetterBlock(
        block_id="test_block_001",
        violation_id="viol_001",
        severity=Severity.HIGH,
        section=LetterSection.FACTUAL_INACCURACIES,
        text="Test violation text.",
        anchors=[{"anchor_id": "crrg_001", "section_title": "Test", "page_start": 1, "page_end": 2}],
        statutes=["15 U.S.C. § 1681e(b)"],
    ))
    return letter


@pytest.fixture
def sample_events(fixed_timestamp, dispute_session_id):
    """Sample evidence events."""
    return [
        EventFactory.create(
            event_type=EventType.REPORT_UPLOADED,
            dispute_session_id=dispute_session_id,
            occurred_at=fixed_timestamp,
            actor=Actor.CONSUMER,
            refs={"report_hash": "abc123"},
        ),
        EventFactory.create(
            event_type=EventType.VIOLATIONS_DETECTED,
            dispute_session_id=dispute_session_id,
            occurred_at=fixed_timestamp + timedelta(minutes=1),
            actor=Actor.SYSTEM,
            refs={"count": "3"},
        ),
    ]


# =============================================================================
# EVIDENCE LEDGER TESTS
# =============================================================================

class TestEvidenceLedger:
    """Tests for evidence ledger construction."""

    def test_event_factory_creates_deterministic_id(self, dispute_session_id):
        """Event IDs are deterministic."""
        event_id_1 = EventFactory.event_id(EventType.REPORT_UPLOADED, dispute_session_id)
        event_id_2 = EventFactory.event_id(EventType.REPORT_UPLOADED, dispute_session_id)
        assert event_id_1 == event_id_2
        assert event_id_1 == f"{dispute_session_id}:REPORT_UPLOADED"

    def test_event_factory_hard_locked_summaries(self, fixed_timestamp, dispute_session_id):
        """Event summaries are hard-locked from EVENT_SUMMARIES."""
        event = EventFactory.create(
            event_type=EventType.REPORT_UPLOADED,
            dispute_session_id=dispute_session_id,
            occurred_at=fixed_timestamp,
            actor=Actor.CONSUMER,
            refs={},
        )
        assert event.summary == EVENT_SUMMARIES[EventType.REPORT_UPLOADED]

    def test_ledger_hash_is_deterministic(self, sample_events, dispute_session_id, report_hash):
        """Same events → same ledger hash."""
        ledger_1 = build_ledger(
            dispute_session_id=dispute_session_id,
            report_hash=report_hash,
            events=sample_events,
        )
        ledger_2 = build_ledger(
            dispute_session_id=dispute_session_id,
            report_hash=report_hash,
            events=sample_events,
        )
        assert ledger_1.sha256 == ledger_2.sha256

    def test_ledger_hash_changes_with_events(self, sample_events, fixed_timestamp, dispute_session_id, report_hash):
        """Different events → different ledger hash."""
        ledger_1 = build_ledger(
            dispute_session_id=dispute_session_id,
            report_hash=report_hash,
            events=sample_events,
        )

        extra_event = EventFactory.create(
            event_type=EventType.DISPUTE_SENT,
            dispute_session_id=dispute_session_id,
            occurred_at=fixed_timestamp + timedelta(hours=1),
            actor=Actor.CONSUMER,
            refs={"channel": "CRA"},
        )
        ledger_2 = build_ledger(
            dispute_session_id=dispute_session_id,
            report_hash=report_hash,
            events=sample_events + [extra_event],
        )
        assert ledger_1.sha256 != ledger_2.sha256

    def test_event_requires_timezone_aware_timestamp(self, dispute_session_id):
        """Events reject naive timestamps."""
        naive_dt = datetime(2026, 1, 3, 12, 0, 0)  # No timezone
        with pytest.raises(ValueError, match="timezone-aware"):
            EventFactory.create(
                event_type=EventType.REPORT_UPLOADED,
                dispute_session_id=dispute_session_id,
                occurred_at=naive_dt,
                actor=Actor.CONSUMER,
                refs={},
            )


# =============================================================================
# CFPB FORMATTER TESTS
# =============================================================================

class TestCFPBFormatter:
    """Tests for CFPB payload formatting."""

    def test_narrative_is_deterministic(self, sample_violation):
        """Same violations → same narrative."""
        violations = [sample_violation]
        narrative_1 = assemble_narrative(violations)
        narrative_2 = assemble_narrative(violations)
        assert narrative_1 == narrative_2

    def test_narrative_contains_no_free_text(self, sample_violation):
        """Narrative only contains templated content."""
        violations = [sample_violation]
        narrative = assemble_narrative(violations)

        # Should contain header and footer
        assert "I am disputing inaccurate information" in narrative
        assert "Consumer Financial Protection Bureau" in narrative

        # Should contain violation line
        assert sample_violation["violation_type"] in narrative

    def test_category_resolution_sorts_violations(self):
        """Category selection is deterministic via sorting."""
        violations = [
            {"violation_type": "z_violation", "citations": []},
            {"violation_type": "a_violation", "citations": []},
        ]
        # Should select 'a_violation' (lexicographically first)
        category = resolve_category(violations)
        # Both should map to default since not in config
        assert category == CFPB_ISSUE_MAP["default"]

    def test_desired_resolution_mapping(self):
        """Demand types map to config resolutions."""
        deletion_text = resolve_desired_resolution(DemandType.DELETION)
        correction_text = resolve_desired_resolution(DemandType.CORRECTION)

        assert deletion_text == CFPB_ISSUE_MAP["desired_resolutions"]["DELETION"]
        assert correction_text == CFPB_ISSUE_MAP["desired_resolutions"]["CORRECTION"]

    def test_payload_hash_is_deterministic(self, sample_violation):
        """Same inputs → same payload hash."""
        violations = [sample_violation]
        payload_1 = format_cfpb_payload(
            violations=violations,
            company_name="Test Bank",
            consumer_name="John Doe",
            consumer_contact={"email": "john@example.com"},
            demand_type=DemandType.DELETION,
        )
        payload_2 = format_cfpb_payload(
            violations=violations,
            company_name="Test Bank",
            consumer_name="John Doe",
            consumer_contact={"email": "john@example.com"},
            demand_type=DemandType.DELETION,
        )
        assert payload_1.content_hash() == payload_2.content_hash()


# =============================================================================
# ATTACHMENT RENDERER TESTS
# =============================================================================

class TestAttachmentRenderer:
    """Tests for attachment rendering."""

    def test_encode_content_is_deterministic(self):
        """Same content → same base64 and hash."""
        content = "Test content for encoding"
        b64_1, hash_1 = encode_content(content)
        b64_2, hash_2 = encode_content(content)
        assert b64_1 == b64_2
        assert hash_1 == hash_2

    def test_letter_attachment_hash_is_deterministic(self, sample_letter, dispute_session_id):
        """Same letter → same attachment hash."""
        att_1 = render_letter_attachment(sample_letter, dispute_session_id, suffix="cra")
        att_2 = render_letter_attachment(sample_letter, dispute_session_id, suffix="cra")
        assert att_1.sha256 == att_2.sha256

    def test_violation_appendix_is_deterministic(self, sample_violation, dispute_session_id):
        """Same violations → same appendix hash."""
        violations = [sample_violation]
        att_1 = render_violation_appendix(violations, dispute_session_id)
        att_2 = render_violation_appendix(violations, dispute_session_id)
        assert att_1.sha256 == att_2.sha256

    def test_violation_appendix_sorts_violations(self, dispute_session_id):
        """Violations are sorted in appendix."""
        violations = [
            {"violation_type": "z_type", "creditor_name": "Z Bank", "account_number_masked": "****9999", "severity": "HIGH", "citations": []},
            {"violation_type": "a_type", "creditor_name": "A Bank", "account_number_masked": "****1111", "severity": "LOW", "citations": []},
        ]
        att = render_violation_appendix(violations, dispute_session_id)
        import base64
        content = base64.b64decode(att.content_bytes_b64).decode("utf-8")
        # a_type should appear before z_type
        a_pos = content.find("a_type")
        z_pos = content.find("z_type")
        assert a_pos < z_pos

    def test_ledger_attachment_is_deterministic(self, sample_events, dispute_session_id, report_hash):
        """Same ledger → same attachment hash."""
        ledger = build_ledger(
            dispute_session_id=dispute_session_id,
            report_hash=report_hash,
            events=sample_events,
        )
        att_1 = render_ledger_attachment(ledger, dispute_session_id)
        att_2 = render_ledger_attachment(ledger, dispute_session_id)
        assert att_1.sha256 == att_2.sha256


# =============================================================================
# PACKET BUILDER TESTS
# =============================================================================

class TestPacketBuilder:
    """Tests for packet building."""

    def test_packet_requires_non_empty_ledger(
        self, dispute_session_id, report_hash, sample_violation, sample_letter, fixed_timestamp
    ):
        """Packet builder rejects empty events list."""
        builder = PacketBuilder(
            dispute_session_id=dispute_session_id,
            report_hash=report_hash,
            packet_type=PacketType.INITIAL,
        )
        builder.with_violations([sample_violation])
        builder.with_letters({"cra": sample_letter})
        builder.with_consumer("John Doe", {"email": "john@example.com"})
        builder.with_company("Test Bank")
        builder.with_demand_type(DemandType.DELETION)
        # No events added

        with pytest.raises(ValueError, match="Evidence ledger cannot be empty"):
            builder.build(fixed_timestamp)

    def test_packet_requires_violations_with_anchors(
        self, dispute_session_id, report_hash, sample_letter, sample_events, fixed_timestamp
    ):
        """Packet builder rejects violations without citations."""
        violation_no_anchor = {
            "violation_type": "test_violation",
            "creditor_name": "Test",
            "citations": [],  # Empty!
        }

        builder = PacketBuilder(
            dispute_session_id=dispute_session_id,
            report_hash=report_hash,
            packet_type=PacketType.INITIAL,
        )
        builder.with_violations([violation_no_anchor])
        builder.with_letters({"cra": sample_letter})
        builder.with_consumer("John Doe", {"email": "john@example.com"})
        builder.with_company("Test Bank")
        builder.with_demand_type(DemandType.DELETION)
        builder.with_events(sample_events)

        with pytest.raises(ValueError, match="no citations"):
            builder.build(fixed_timestamp)

    def test_packet_hash_is_deterministic(
        self, dispute_session_id, report_hash, sample_violation, sample_letter, sample_events, fixed_timestamp
    ):
        """Same inputs → same packet hash."""
        def build_packet():
            builder = PacketBuilder(
                dispute_session_id=dispute_session_id,
                report_hash=report_hash,
                packet_type=PacketType.INITIAL,
            )
            builder.with_violations([sample_violation])
            builder.with_letters({"cra": sample_letter})
            builder.with_consumer("John Doe", {"email": "john@example.com"})
            builder.with_company("Test Bank")
            builder.with_demand_type(DemandType.DELETION)
            builder.with_events(sample_events)
            return builder.build(fixed_timestamp)

        packet_1 = build_packet()
        packet_2 = build_packet()

        assert packet_1.packet_hash == packet_2.packet_hash

    def test_packet_requires_timezone_aware_timestamp(
        self, dispute_session_id, report_hash, sample_violation, sample_letter, sample_events
    ):
        """Packet builder rejects naive timestamps."""
        builder = PacketBuilder(
            dispute_session_id=dispute_session_id,
            report_hash=report_hash,
            packet_type=PacketType.INITIAL,
        )
        builder.with_violations([sample_violation])
        builder.with_letters({"cra": sample_letter})
        builder.with_consumer("John Doe", {"email": "john@example.com"})
        builder.with_company("Test Bank")
        builder.with_demand_type(DemandType.DELETION)
        builder.with_events(sample_events)

        naive_dt = datetime(2026, 1, 3, 12, 0, 0)  # No timezone
        with pytest.raises(ValueError, match="timezone-aware"):
            builder.build(naive_dt)


# =============================================================================
# STATE MACHINE TESTS
# =============================================================================

class TestStateMachine:
    """Tests for dispute state machine."""

    def test_pending_state_within_30_days(self, fixed_timestamp):
        """Dispute is PENDING within 30 days."""
        dispute_sent = fixed_timestamp
        current_time = fixed_timestamp + timedelta(days=15)

        state = DisputeStateMachine.compute_state(
            dispute_sent_at=dispute_sent,
            current_time=current_time,
        )
        assert state == DisputeState.PENDING

    def test_non_response_after_30_days(self, fixed_timestamp):
        """Dispute is NON_RESPONSE after 30 days with no response."""
        dispute_sent = fixed_timestamp
        current_time = fixed_timestamp + timedelta(days=31)

        state = DisputeStateMachine.compute_state(
            dispute_sent_at=dispute_sent,
            current_time=current_time,
        )
        assert state == DisputeState.NON_RESPONSE

    def test_responded_state_with_response(self, fixed_timestamp):
        """Dispute is RESPONDED when response received."""
        dispute_sent = fixed_timestamp
        response_received = fixed_timestamp + timedelta(days=20)
        current_time = fixed_timestamp + timedelta(days=25)

        state = DisputeStateMachine.compute_state(
            dispute_sent_at=dispute_sent,
            current_time=current_time,
            response_received_at=response_received,
        )
        assert state == DisputeState.RESPONDED

    def test_verified_without_change_state(self, fixed_timestamp):
        """Dispute is VERIFIED_WITHOUT_CHANGE when flagged."""
        dispute_sent = fixed_timestamp
        current_time = fixed_timestamp + timedelta(days=25)

        state = DisputeStateMachine.compute_state(
            dispute_sent_at=dispute_sent,
            current_time=current_time,
            verified_without_change=True,
        )
        assert state == DisputeState.VERIFIED_WITHOUT_CHANGE

    def test_reinserted_state_takes_priority(self, fixed_timestamp):
        """REINSERTED state takes priority over other states."""
        dispute_sent = fixed_timestamp
        response_received = fixed_timestamp + timedelta(days=20)
        current_time = fixed_timestamp + timedelta(days=25)

        state = DisputeStateMachine.compute_state(
            dispute_sent_at=dispute_sent,
            current_time=current_time,
            response_received_at=response_received,
            account_reinserted=True,
        )
        assert state == DisputeState.REINSERTED

    def test_failure_eligible_after_30_days(self, fixed_timestamp):
        """FAILURE packet eligible after 30 days non-response."""
        dispute_sent = fixed_timestamp
        current_time = fixed_timestamp + timedelta(days=31)

        eligible = is_failure_eligible(
            dispute_sent_at=dispute_sent,
            current_time=current_time,
        )
        assert eligible is True

    def test_failure_not_eligible_within_30_days(self, fixed_timestamp):
        """FAILURE packet not eligible within 30 days."""
        dispute_sent = fixed_timestamp
        current_time = fixed_timestamp + timedelta(days=20)

        eligible = is_failure_eligible(
            dispute_sent_at=dispute_sent,
            current_time=current_time,
        )
        assert eligible is False

    def test_days_until_failure_calculation(self, fixed_timestamp):
        """Days until failure is calculated correctly."""
        dispute_sent = fixed_timestamp
        current_time = fixed_timestamp + timedelta(days=20)

        days_remaining = days_until_failure_eligible(
            dispute_sent_at=dispute_sent,
            current_time=current_time,
        )
        assert days_remaining == 10  # 30 - 20 = 10

    def test_state_machine_requires_timezone_aware_timestamps(self, fixed_timestamp):
        """State machine rejects naive timestamps."""
        naive_dt = datetime(2026, 1, 3, 12, 0, 0)  # No timezone

        with pytest.raises(ValueError, match="timezone-aware"):
            DisputeStateMachine.compute_state(
                dispute_sent_at=naive_dt,
                current_time=fixed_timestamp,
            )


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestPacketIntegration:
    """Integration tests for full packet generation."""

    def test_full_packet_generation(
        self, dispute_session_id, report_hash, sample_violation, sample_letter, sample_events, fixed_timestamp
    ):
        """Full packet generation produces valid output."""
        packet = build_initial_packet(
            dispute_session_id=dispute_session_id,
            report_hash=report_hash,
            violations=[sample_violation],
            letters={"cra": sample_letter},
            consumer_name="John Doe",
            consumer_contact={"email": "john@example.com"},
            company_name="Test Bank",
            demand_type=DemandType.DELETION,
            events=sample_events,
            generated_at=fixed_timestamp,
        )

        # Verify packet structure
        assert packet.packet_id == f"packet:{dispute_session_id}:INITIAL"
        assert packet.packet_type == PacketType.INITIAL
        assert packet.channel == RegulatorChannel.CFPB
        assert packet.dispute_session_id == dispute_session_id
        assert packet.report_hash == report_hash

        # Verify complaint payload
        assert packet.complaint_payload.consumer_name == "John Doe"
        assert packet.complaint_payload.company_name == "Test Bank"
        assert "Delete" in packet.complaint_payload.desired_resolution

        # Verify ledger
        assert len(packet.ledger.events) == 2
        assert packet.ledger.sha256  # Hash computed

        # Verify attachments
        assert len(packet.attachments) >= 4  # letters + violation + anchor + ledger

        # Verify packet hash
        assert packet.packet_hash  # Hash computed and stored

    def test_packet_to_dict_is_serializable(
        self, dispute_session_id, report_hash, sample_violation, sample_letter, sample_events, fixed_timestamp
    ):
        """Packet to_dict produces valid JSON."""
        packet = build_initial_packet(
            dispute_session_id=dispute_session_id,
            report_hash=report_hash,
            violations=[sample_violation],
            letters={"cra": sample_letter},
            consumer_name="John Doe",
            consumer_contact={"email": "john@example.com"},
            company_name="Test Bank",
            demand_type=DemandType.DELETION,
            events=sample_events,
            generated_at=fixed_timestamp,
        )

        # Should serialize without error
        packet_dict = packet.to_dict()
        json_str = json.dumps(packet_dict, sort_keys=True)
        assert json_str  # Non-empty

        # Should deserialize
        parsed = json.loads(json_str)
        assert parsed["packet_id"] == packet.packet_id
        assert parsed["packet_hash"] == packet.packet_hash
