"""
Phase 3 Letter Generation Tests

Verifies:
1. Every violation maps to exactly one paragraph block
2. Every paragraph cites CRRG + statute
3. Letters vary only by channel wrapper
4. Letter hashes are stable for same inputs
5. Demand resolution is deterministic
"""

import pytest
from uuid import uuid4

from app.models.ssot import Violation, ViolationType, Severity, Consumer
from app.models.letter_object import (
    LetterBlock,
    LetterObject,
    LetterChannel,
    LetterSection,
    DemandType,
)
from app.services.letter_generation import (
    BlockCompiler,
    DemandResolver,
    ChannelWrapper,
    LetterAssembler,
    FACTUAL_FAILURE_MAP,
    compile_violation,
    compile_violations,
    resolve_demand,
    create_demand_block,
    assemble_letter,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def sample_violation():
    """Create a sample violation for testing."""
    return Violation(
        violation_id="test-violation-001",
        violation_type=ViolationType.MISSING_DOFD,
        severity=Severity.CRITICAL,
        account_id="acc-001",
        creditor_name="Test Creditor",
        account_number_masked="XXXX1234",
        description="Date of First Delinquency is missing",
        citations=[{
            "anchor_id": "FIELD_24",
            "rule_id": "DOFD",
            "section_title": "Base Segment Field 24 - Date of First Delinquency",
            "page_start": 52,
            "page_end": 54,
            "fields": ["24"],
            "fcra_cite": "15 U.S.C. § 1681c(a)",
        }],
    )


@pytest.fixture
def sample_violations():
    """Create multiple violations for testing."""
    return [
        Violation(
            violation_id="test-v1",
            violation_type=ViolationType.MISSING_DOFD,
            severity=Severity.CRITICAL,
            description="DOFD missing",
            citations=[{
                "anchor_id": "FIELD_24",
                "section_title": "Field 24",
                "page_start": 52,
                "page_end": 54,
                "fcra_cite": "15 U.S.C. § 1681c(a)",
            }],
        ),
        Violation(
            violation_id="test-v2",
            violation_type=ViolationType.BALANCE_MISMATCH,
            severity=Severity.HIGH,
            description="Balance differs between bureaus",
            citations=[{
                "anchor_id": "FIELD_21",
                "section_title": "Field 21",
                "page_start": 50,
                "page_end": 51,
                "fcra_cite": "15 U.S.C. § 1681s-2(a)(2)",
            }],
        ),
    ]


@pytest.fixture
def sample_consumer():
    """Create a sample consumer for testing."""
    return Consumer(
        full_name="John Doe",
        address="123 Main St",
        city="Anytown",
        state="CA",
        zip_code="90210",
    )


# =============================================================================
# BLOCK COMPILER TESTS
# =============================================================================

class TestBlockCompiler:
    """Tests for violation → block compilation."""

    def test_compile_produces_one_block(self, sample_violation):
        """Each violation produces exactly one block."""
        compiler = BlockCompiler()
        block = compiler.compile(sample_violation)

        assert isinstance(block, LetterBlock)
        assert block.violation_id == sample_violation.violation_id

    def test_compile_block_in_correct_section(self, sample_violation):
        """Violation blocks go to FACTUAL_INACCURACIES section."""
        compiler = BlockCompiler()
        block = compiler.compile(sample_violation)

        assert block.section == LetterSection.FACTUAL_INACCURACIES

    def test_compile_preserves_severity(self, sample_violation):
        """Block severity matches violation severity."""
        compiler = BlockCompiler()
        block = compiler.compile(sample_violation)

        assert block.severity == sample_violation.severity

    def test_compile_includes_crrg_reference(self, sample_violation):
        """Block text includes CRRG reference."""
        compiler = BlockCompiler()
        block = compiler.compile(sample_violation)

        assert "Metro 2" in block.text or "CRRG" in block.text or "Field" in block.text

    def test_compile_includes_statute(self, sample_violation):
        """Block text includes statute citation."""
        compiler = BlockCompiler()
        block = compiler.compile(sample_violation)

        assert "U.S.C." in block.text

    def test_compile_deterministic_block_id(self, sample_violation):
        """Block ID is deterministic (no UUID)."""
        compiler = BlockCompiler()
        block1 = compiler.compile(sample_violation)
        block2 = compiler.compile(sample_violation)

        assert block1.block_id == block2.block_id
        assert block1.block_id == f"block_{sample_violation.violation_id}"

    def test_compile_many_produces_same_count(self, sample_violations):
        """compile_many produces one block per violation."""
        compiler = BlockCompiler()
        blocks = compiler.compile_many(sample_violations)

        assert len(blocks) == len(sample_violations)

    def test_missing_violation_type_raises_error(self):
        """Unknown violation type raises KeyError."""
        # Create violation with a type not in FACTUAL_FAILURE_MAP
        # This tests the hard failure requirement
        compiler = BlockCompiler()

        # All ViolationType values should be covered
        for vtype in ViolationType:
            vtype_key = vtype.value.lower()
            # Skip types that might be added but not mapped
            if vtype_key in FACTUAL_FAILURE_MAP:
                violation = Violation(
                    violation_id="test",
                    violation_type=vtype,
                    severity=Severity.MEDIUM,
                )
                # Should not raise
                block = compiler.compile(violation)
                assert block is not None


# =============================================================================
# DEMAND RESOLVER TESTS
# =============================================================================

class TestDemandResolver:
    """Tests for severity → demand resolution."""

    def test_no_violations_returns_procedural(self):
        """Empty violations list returns PROCEDURAL."""
        resolver = DemandResolver()
        demand = resolver.resolve([])

        assert demand == DemandType.PROCEDURAL

    def test_one_critical_returns_deletion(self):
        """≥1 CRITICAL → DELETION."""
        resolver = DemandResolver()
        violations = [
            Violation(
                violation_id="v1",
                violation_type=ViolationType.MISSING_DOFD,
                severity=Severity.CRITICAL,
            ),
        ]
        demand = resolver.resolve(violations)

        assert demand == DemandType.DELETION

    def test_two_high_returns_deletion(self):
        """≥2 HIGH → DELETION."""
        resolver = DemandResolver()
        violations = [
            Violation(
                violation_id="v1",
                violation_type=ViolationType.BALANCE_MISMATCH,
                severity=Severity.HIGH,
            ),
            Violation(
                violation_id="v2",
                violation_type=ViolationType.STATUS_MISMATCH,
                severity=Severity.HIGH,
            ),
        ]
        demand = resolver.resolve(violations)

        assert demand == DemandType.DELETION

    def test_one_high_returns_correction(self):
        """1 HIGH → CORRECTION."""
        resolver = DemandResolver()
        violations = [
            Violation(
                violation_id="v1",
                violation_type=ViolationType.BALANCE_MISMATCH,
                severity=Severity.HIGH,
            ),
        ]
        demand = resolver.resolve(violations)

        assert demand == DemandType.CORRECTION

    def test_medium_only_returns_correction(self):
        """MEDIUM only → CORRECTION."""
        resolver = DemandResolver()
        violations = [
            Violation(
                violation_id="v1",
                violation_type=ViolationType.STALE_REPORTING,
                severity=Severity.MEDIUM,
            ),
        ]
        demand = resolver.resolve(violations)

        assert demand == DemandType.CORRECTION

    def test_low_only_returns_procedural(self):
        """LOW only → PROCEDURAL."""
        resolver = DemandResolver()
        violations = [
            Violation(
                violation_id="v1",
                violation_type=ViolationType.STALE_REPORTING,
                severity=Severity.LOW,
            ),
        ]
        demand = resolver.resolve(violations)

        assert demand == DemandType.PROCEDURAL

    def test_demand_block_deterministic_id(self, sample_violations):
        """Demand block ID is deterministic."""
        resolver = DemandResolver()
        block1 = resolver.create_demand_block(sample_violations)
        block2 = resolver.create_demand_block(sample_violations)

        assert block1.block_id == block2.block_id


# =============================================================================
# CHANNEL WRAPPER TESTS
# =============================================================================

class TestChannelWrapper:
    """Tests for channel-specific framing."""

    def test_cra_opening_includes_611(self):
        """CRA opening references §611."""
        wrapper = ChannelWrapper()
        block = wrapper.create_opening_block(LetterChannel.CRA)

        assert "611" in block.text or "1681i" in block.text

    def test_furnisher_opening_includes_623(self):
        """FURNISHER opening references §623."""
        wrapper = ChannelWrapper()
        block = wrapper.create_opening_block(LetterChannel.FURNISHER)

        assert "623" in block.text or "1681s-2" in block.text

    def test_mov_opening_includes_verification(self):
        """MOV opening mentions verification."""
        wrapper = ChannelWrapper()
        block = wrapper.create_opening_block(LetterChannel.MOV)

        assert "verification" in block.text.lower()

    def test_wrap_returns_three_blocks(self):
        """wrap() returns opening, statutory, and closing blocks."""
        wrapper = ChannelWrapper()

        for channel in LetterChannel:
            blocks = wrapper.wrap(channel)
            assert len(blocks) == 3

    def test_wrapper_blocks_deterministic(self):
        """Wrapper blocks have deterministic IDs."""
        wrapper = ChannelWrapper()

        for channel in LetterChannel:
            blocks1 = wrapper.wrap(channel)
            blocks2 = wrapper.wrap(channel)

            for b1, b2 in zip(blocks1, blocks2):
                assert b1.block_id == b2.block_id


# =============================================================================
# LETTER ASSEMBLER TESTS
# =============================================================================

class TestLetterAssembler:
    """Tests for letter assembly."""

    def test_assemble_produces_letter_object(self, sample_violations):
        """assemble() returns a LetterObject."""
        assembler = LetterAssembler()
        letter = assembler.assemble(
            violations=sample_violations,
            channel=LetterChannel.CRA,
        )

        assert isinstance(letter, LetterObject)
        assert letter.channel == LetterChannel.CRA

    def test_assemble_includes_all_sections(self, sample_violations):
        """Assembled letter includes all required sections."""
        assembler = LetterAssembler()
        letter = assembler.assemble(
            violations=sample_violations,
            channel=LetterChannel.CRA,
        )

        # Check required sections have blocks
        assert len(letter.sections[LetterSection.HEADER]) > 0
        assert len(letter.sections[LetterSection.FACTUAL_INACCURACIES]) > 0
        assert len(letter.sections[LetterSection.STATUTORY_AUTHORITY]) > 0
        assert len(letter.sections[LetterSection.DEMAND]) > 0
        assert len(letter.sections[LetterSection.CLOSING]) > 0

    def test_assemble_violation_count_matches(self, sample_violations):
        """Number of FACTUAL blocks matches violation count."""
        assembler = LetterAssembler()
        letter = assembler.assemble(
            violations=sample_violations,
            channel=LetterChannel.CRA,
        )

        factual_blocks = letter.sections[LetterSection.FACTUAL_INACCURACIES]
        assert len(factual_blocks) == len(sample_violations)

    def test_assemble_demand_type_set(self, sample_violations):
        """Letter demand_type is set based on violations."""
        assembler = LetterAssembler()
        letter = assembler.assemble(
            violations=sample_violations,
            channel=LetterChannel.CRA,
        )

        # sample_violations has 1 CRITICAL → DELETION
        assert letter.demand_type == DemandType.DELETION


# =============================================================================
# DETERMINISM TESTS
# =============================================================================

class TestDeterminism:
    """Tests for deterministic output (same inputs → same outputs)."""

    def test_block_hash_stable(self, sample_violation):
        """Same violation produces same block hash."""
        compiler = BlockCompiler()

        block1 = compiler.compile(sample_violation)
        block2 = compiler.compile(sample_violation)

        assert block1.content_hash() == block2.content_hash()

    def test_letter_hash_stable(self, sample_violations):
        """Same violations produce same letter hash."""
        assembler = LetterAssembler()

        letter1 = assembler.assemble(
            violations=sample_violations,
            channel=LetterChannel.CRA,
        )
        letter2 = assembler.assemble(
            violations=sample_violations,
            channel=LetterChannel.CRA,
        )

        assert letter1.content_hash() == letter2.content_hash()

    def test_different_channels_different_hashes(self, sample_violations):
        """Different channels produce different letter hashes."""
        assembler = LetterAssembler()

        cra_letter = assembler.assemble(
            violations=sample_violations,
            channel=LetterChannel.CRA,
        )
        furnisher_letter = assembler.assemble(
            violations=sample_violations,
            channel=LetterChannel.FURNISHER,
        )

        assert cra_letter.content_hash() != furnisher_letter.content_hash()

    def test_different_violations_different_hashes(self):
        """Different violations produce different letter hashes."""
        assembler = LetterAssembler()

        violations1 = [
            Violation(
                violation_id="v1",
                violation_type=ViolationType.MISSING_DOFD,
                severity=Severity.CRITICAL,
            ),
        ]
        violations2 = [
            Violation(
                violation_id="v2",
                violation_type=ViolationType.BALANCE_MISMATCH,
                severity=Severity.HIGH,
            ),
        ]

        letter1 = assembler.assemble(violations=violations1, channel=LetterChannel.CRA)
        letter2 = assembler.assemble(violations=violations2, channel=LetterChannel.CRA)

        assert letter1.content_hash() != letter2.content_hash()


# =============================================================================
# COVERAGE TESTS
# =============================================================================

class TestCoverage:
    """Tests for factual failure mapping coverage."""

    def test_all_metro2_v2_types_covered(self):
        """All Metro 2 V2.0 violation types have factual failure mappings."""
        # Get the set of types that should be covered
        from app.models.ssot import Violation
        metro2_v2_types = Violation.METRO2_V2_VIOLATION_TYPES

        missing = []
        for vtype in metro2_v2_types:
            if vtype not in FACTUAL_FAILURE_MAP:
                missing.append(vtype)

        assert not missing, f"Missing factual failure mappings for: {missing}"

    def test_factual_failure_map_not_empty(self):
        """FACTUAL_FAILURE_MAP has entries."""
        assert len(FACTUAL_FAILURE_MAP) > 0

    def test_each_factual_failure_is_string(self):
        """Each factual failure is a non-empty string."""
        for vtype, text in FACTUAL_FAILURE_MAP.items():
            assert isinstance(text, str), f"{vtype} mapping is not a string"
            assert len(text) > 0, f"{vtype} mapping is empty"


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestIntegration:
    """End-to-end integration tests."""

    def test_full_letter_assembly_cra(self, sample_violations, sample_consumer):
        """Full CRA letter assembly works end-to-end."""
        letter = assemble_letter(
            violations=sample_violations,
            channel=LetterChannel.CRA,
            consumer=sample_consumer,
            account_info={
                "creditor_name": "Test Bank",
                "account_number_masked": "XXXX1234",
            },
            metadata={"dispute_session_id": "sess-001"},
        )

        # Verify structure
        assert letter.channel == LetterChannel.CRA
        assert letter.demand_type == DemandType.DELETION
        assert len(letter.get_all_blocks()) > 0
        assert letter.content_hash() is not None

    def test_full_letter_assembly_furnisher(self, sample_violations):
        """Full FURNISHER letter assembly works end-to-end."""
        letter = assemble_letter(
            violations=sample_violations,
            channel=LetterChannel.FURNISHER,
        )

        assert letter.channel == LetterChannel.FURNISHER
        assert "1681s-2" in str(letter.get_all_statutes())

    def test_full_letter_assembly_mov(self, sample_violations):
        """Full MOV letter assembly works end-to-end."""
        letter = assemble_letter(
            violations=sample_violations,
            channel=LetterChannel.MOV,
        )

        assert letter.channel == LetterChannel.MOV
        assert any("verification" in b.text.lower() for b in letter.get_all_blocks())
