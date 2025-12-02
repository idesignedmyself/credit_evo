"""
Civil Letter Generator - Civil Assembler v2

Main orchestrator for generating civil dispute letters.
Wraps the existing Credit Copilot LetterAssembler with:
- Civil mask for domain isolation
- Structured output with metadata
- Grouping support
- Deterministic seeding
- SWEEP-D compliance metadata
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import date
import random
import hashlib
import re

from .civil_mask import CivilMask, apply_civil_mask, validate_civil_content
from .structure import (
    CivilLetterStructure,
    CivilStructureBuilder,
    CivilSection,
    get_structure_metadata,
)
from .tone_engine import (
    CivilTone,
    CivilToneEngine,
    create_tone_engine,
    resolve_tone,
    is_civil_tone,
    get_civil_tones,
)

# Import existing Credit Copilot components
from ..letter_generator.assembler import (
    LetterAssembler as CreditCopilotAssembler,
    ViolationItem,
    LetterConfig as CopilotConfig,
    GeneratedLetter as CopilotLetter,
)
from ..letter_generator.bureau_profiles import get_bureau_address


@dataclass
class CivilViolation:
    """A violation formatted for civil letters."""
    violation_id: str
    creditor_name: str
    account_number_masked: str
    violation_type: str
    description: str
    severity: str = "medium"
    bureau: Optional[str] = None


@dataclass
class CivilLetterConfig:
    """Configuration for civil letter generation."""
    bureau: str
    tone: str = "conversational"
    consumer_name: Optional[str] = None
    consumer_address: Optional[str] = None
    report_id: Optional[str] = None
    consumer_id: Optional[str] = None
    grouping_strategy: str = "by_creditor"
    entropy_level: str = "medium"  # low, medium, high, maximum
    mutation_strength: str = "low"  # low, medium, high


@dataclass
class CivilLetterResult:
    """Output of civil letter generation."""
    content: str
    bureau: str
    bureau_address: str
    violations_included: List[str]
    word_count: int
    sentence_count: int
    quality_score: float
    is_valid: bool
    validation_issues: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class CivilAssembler:
    """
    Civil Letter Assembler v2

    Main orchestrator that:
    1. Wraps Credit Copilot LetterAssembler
    2. Applies civil mask for domain isolation
    3. Provides structured output
    4. Supports grouping strategies
    5. Includes SWEEP-D compliance metadata
    """

    # Grouping strategies
    GROUPING_STRATEGIES = {
        "by_creditor": "Group violations by creditor name",
        "by_violation_type": "Group violations by type",
        "by_severity": "Group violations by severity level",
        "none": "No grouping - list all violations",
    }

    def __init__(self, seed: Optional[int] = None):
        """
        Initialize assembler with optional seed.

        Args:
            seed: Random seed for deterministic output
        """
        self.seed = seed or random.randint(0, 2**32)
        self.rng = random.Random(self.seed)

    def _create_seed_from_report(self, report_id: str) -> int:
        """Create deterministic seed from report ID."""
        hash_bytes = hashlib.md5(report_id.encode()).digest()
        return int.from_bytes(hash_bytes[:4], byteorder='big')

    def _mask_account_number(self, account_number: str) -> str:
        """Mask account number to show only last 4 digits."""
        if not account_number:
            return "XXXX"

        # Remove any existing masking
        clean = re.sub(r'[X*#]', '', account_number)

        if len(clean) <= 4:
            return f"XXXX{clean}"

        return f"XXXX{clean[-4:]}"

    def _group_violations(
        self,
        violations: List[CivilViolation],
        strategy: str
    ) -> Dict[str, List[CivilViolation]]:
        """Group violations by the specified strategy."""
        groups: Dict[str, List[CivilViolation]] = {}

        for v in violations:
            if strategy == "by_creditor":
                key = v.creditor_name or "Unknown Creditor"
            elif strategy == "by_violation_type":
                key = v.violation_type.replace("_", " ").title()
            elif strategy == "by_severity":
                key = v.severity.title()
            else:  # none
                key = "All Items"

            if key not in groups:
                groups[key] = []
            groups[key].append(v)

        return groups

    def _format_violation_prose(
        self,
        violation: CivilViolation,
        tone_engine: CivilToneEngine
    ) -> str:
        """Format a violation in prose style for civil letters."""
        creditor = violation.creditor_name or "the creditor"
        account = self._mask_account_number(violation.account_number_masked)
        v_type = violation.violation_type.replace("_", " ")

        # Tone-appropriate templates
        templates = [
            f"The account with {creditor} (ending in {account}) shows {v_type}.",
            f"I noticed that {creditor}'s account ({account}) has {v_type}.",
            f"For the {creditor} account ending in {account}, I found {v_type}.",
            f"My {creditor} account ({account}) has {v_type}.",
        ]

        return tone_engine.rng.choice(templates)

    def _format_dispute_items(
        self,
        violations: List[CivilViolation],
        config: CivilLetterConfig,
        tone_engine: CivilToneEngine
    ) -> str:
        """Format all dispute items in prose style."""
        lines = []

        # Group violations
        groups = self._group_violations(violations, config.grouping_strategy)

        # Format each group
        for group_name, group_violations in groups.items():
            if config.grouping_strategy != "none" and len(groups) > 1:
                lines.append(f"Regarding {group_name}:")

            for v in group_violations:
                prose = self._format_violation_prose(v, tone_engine)
                if v.description:
                    prose += f" {v.description}"
                lines.append(prose)

            lines.append("")  # Empty line between groups

        return "\n".join(lines).strip()

    def generate(
        self,
        violations: List[CivilViolation],
        config: CivilLetterConfig,
    ) -> CivilLetterResult:
        """
        Generate a civil dispute letter.

        Args:
            violations: List of violations to include
            config: Letter configuration

        Returns:
            CivilLetterResult with content and metadata
        """
        # Set up deterministic seed if report_id provided
        if config.report_id:
            self.seed = self._create_seed_from_report(config.report_id)
            self.rng = random.Random(self.seed)

        # Create tone engine
        tone_engine = create_tone_engine(config.tone, self.seed)

        # Build letter sections
        builder = CivilStructureBuilder()

        # Date
        today = date.today()
        builder.set_date(today.strftime("%B %d, %Y"))

        # Recipient (bureau address)
        bureau_address = get_bureau_address(config.bureau)
        builder.set_recipient(bureau_address)

        # Subject
        builder.set_subject(tone_engine.get_subject())

        # Greeting
        builder.set_greeting(tone_engine.get_greeting())

        # Header (consumer info)
        if config.consumer_name:
            header_lines = [config.consumer_name]
            if config.consumer_address:
                header_lines.append(config.consumer_address)
            builder.set_header("\n".join(header_lines))

        # Intro
        builder.set_intro(tone_engine.get_opening())

        # Dispute items
        dispute_content = self._format_dispute_items(violations, config, tone_engine)
        builder.set_dispute_items(dispute_content)

        # Request
        builder.set_request(tone_engine.get_request())

        # Closing
        builder.set_closing(tone_engine.get_closing())

        # Signature
        signature_lines = [tone_engine.get_signature()]
        if config.consumer_name:
            signature_lines.append("")
            signature_lines.append(config.consumer_name)
        builder.set_signature("\n".join(signature_lines))

        # Build structure
        structure = builder.build()

        # Get full content
        raw_content = structure.get_content()

        # Apply civil mask
        mask_result = CivilMask.apply(raw_content)
        content = mask_result.content

        # Validate civil content
        is_valid, validation_issues = validate_civil_content(content)

        # Calculate quality score
        quality_score = self._calculate_quality_score(
            content,
            structure,
            mask_result.is_clean,
            is_valid
        )

        # Build metadata
        metadata = {
            "domain": "civil",
            "tone": config.tone,
            "tone_metadata": tone_engine.get_metadata(),
            "structure": get_structure_metadata(structure),
            "mask": CivilMask.get_metadata(),
            "grouping_strategy": config.grouping_strategy,
            "entropy_level": config.entropy_level,
            "mutation_strength": config.mutation_strength,
            "seed": self.seed,
            "violations_count": len(violations),
            "mask_applied": True,
            "mask_terms_removed": mask_result.terms_removed,
            "account_masking": True,
            "routing_path": "civil",
            "generator_version": "civil_v2",
        }

        return CivilLetterResult(
            content=content,
            bureau=config.bureau,
            bureau_address=bureau_address,
            violations_included=[v.violation_id for v in violations],
            word_count=structure.total_word_count,
            sentence_count=structure.total_sentence_count,
            quality_score=quality_score,
            is_valid=is_valid and structure.is_valid,
            validation_issues=validation_issues + structure.validation_errors,
            metadata=metadata,
        )

    def _calculate_quality_score(
        self,
        content: str,
        structure: CivilLetterStructure,
        mask_clean: bool,
        content_valid: bool
    ) -> float:
        """Calculate quality score (0-100) for the letter."""
        score = 100.0

        # Deduct for structure issues
        if not structure.is_valid:
            score -= 20.0

        # Deduct for mask contamination
        if not mask_clean:
            score -= 15.0

        # Deduct for content validation issues
        if not content_valid:
            score -= 15.0

        # Deduct for length issues
        if structure.total_word_count < 100:
            score -= 10.0
        elif structure.total_word_count > 800:
            score -= 5.0

        # Deduct for missing sections
        score -= len(structure.validation_errors) * 5.0

        return max(0.0, min(100.0, score))


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def generate_civil_letter(
    violations: List[Dict[str, Any]],
    bureau: str,
    tone: str = "conversational",
    consumer_name: Optional[str] = None,
    consumer_address: Optional[str] = None,
    report_id: Optional[str] = None,
    consumer_id: Optional[str] = None,
    grouping_strategy: str = "by_creditor",
    seed: Optional[int] = None,
) -> CivilLetterResult:
    """
    Convenience function to generate a civil letter.

    Args:
        violations: List of violation dictionaries
        bureau: Target bureau
        tone: Civil tone (conversational, formal, assertive, narrative)
        consumer_name: Optional consumer name
        consumer_address: Optional address
        report_id: Optional report ID for seed
        consumer_id: Optional consumer ID
        grouping_strategy: How to group violations
        seed: Optional random seed

    Returns:
        CivilLetterResult with content and metadata
    """
    # Convert dictionaries to CivilViolation objects
    civil_violations = [
        CivilViolation(
            violation_id=v.get("violation_id", str(i)),
            creditor_name=v.get("creditor_name", "Unknown"),
            account_number_masked=v.get("account_number_masked", v.get("account_number", "")),
            violation_type=v.get("violation_type", "error"),
            description=v.get("description", v.get("evidence", "")),
            severity=v.get("severity", "medium"),
            bureau=v.get("bureau"),
        )
        for i, v in enumerate(violations)
    ]

    config = CivilLetterConfig(
        bureau=bureau,
        tone=tone,
        consumer_name=consumer_name,
        consumer_address=consumer_address,
        report_id=report_id,
        consumer_id=consumer_id,
        grouping_strategy=grouping_strategy,
    )

    assembler = CivilAssembler(seed=seed)
    return assembler.generate(civil_violations, config)


def create_civil_assembler(seed: Optional[int] = None) -> CivilAssembler:
    """Create a civil assembler instance."""
    return CivilAssembler(seed=seed)


def get_available_civil_tones() -> List[Dict[str, Any]]:
    """Get list of available civil tones."""
    return get_civil_tones()


def get_civil_grouping_strategies() -> List[Dict[str, str]]:
    """Get list of available grouping strategies."""
    return [
        {"id": k, "name": k.replace("_", " ").title(), "description": v}
        for k, v in CivilAssembler.GROUPING_STRATEGIES.items()
    ]
