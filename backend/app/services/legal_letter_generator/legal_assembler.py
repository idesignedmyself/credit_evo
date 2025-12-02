"""
Legal Letter Generator - Main Assembler
Combines all components to generate structured legal dispute letters.
"""
import json
import random
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set

from .grouping_strategies import LegalGrouper, GroupingStrategy


# =============================================================================
# SECTION DEDUPLICATION GUARD
# =============================================================================
# RULE: Each section header may appear only ONCE in the final letter.
# This prevents:
#   - Double MOV blocks
#   - Double case-law blocks
#   - Extra accuracy paragraphs
#   - Repeated section headers
# =============================================================================

@dataclass
class DeduplicationResult:
    """Result of deduplication operation."""
    original_section_count: int = 0
    deduplicated_section_count: int = 0
    duplicates_removed: List[str] = field(default_factory=list)
    duplicate_headers_found: List[str] = field(default_factory=list)
    repeated_paragraphs_removed: int = 0
    is_clean: bool = True


class SectionDeduplicator:
    """
    Deduplication guard for legal letter sections.

    Enforces the rule that each section header may appear only ONCE.
    Tracks inserted sections and prevents duplicates at assembly time.
    """

    # Canonical section identifiers (used for tracking)
    SECTION_IDS = {
        "header", "introduction", "violations", "legal_basis",
        "mov", "case_law", "demands", "signature", "metro2"
    }

    # Patterns that indicate duplicate content (case-insensitive)
    DUPLICATE_PATTERNS = [
        # MOV-related duplicates
        r"method\s+of\s+verification",
        r"verification\s+requirements",
        r"mandatory\s+verification",
        # Case law duplicates
        r"applicable\s+case\s+law",
        r"legal\s+standards",
        r"case\s+law\s+and\s+precedent",
        # Accuracy paragraph duplicates
        r"maximum\s+possible\s+accuracy",
        r"assure\s+maximum\s+possible\s+accuracy",
        # Legal basis duplicates
        r"legal\s+basis\s+for\s+dispute",
        r"fcra\s+violations\s+identified",
    ]

    def __init__(self):
        """Initialize the deduplicator with empty tracking state."""
        self._inserted_sections: Set[str] = set()
        self._section_content_hashes: Dict[str, int] = {}
        self._duplicate_log: List[str] = []

    def reset(self):
        """Reset tracking state for a new letter generation."""
        self._inserted_sections.clear()
        self._section_content_hashes.clear()
        self._duplicate_log.clear()

    def can_insert(self, section_id: str) -> bool:
        """
        Check if a section can be inserted (hasn't been inserted yet).

        Args:
            section_id: The canonical section identifier

        Returns:
            True if section can be inserted, False if already present
        """
        return section_id.lower() not in self._inserted_sections

    def mark_inserted(self, section_id: str, content: str = None):
        """
        Mark a section as inserted and optionally track its content hash.

        Args:
            section_id: The canonical section identifier
            content: Optional content to hash for duplicate detection
        """
        section_key = section_id.lower()
        self._inserted_sections.add(section_key)

        if content:
            self._section_content_hashes[section_key] = hash(content.strip())

    def try_insert(self, section_id: str, content: str) -> Optional[str]:
        """
        Attempt to insert a section. Returns content if allowed, None if duplicate.

        This is the primary guard function. Use this instead of directly appending.

        Args:
            section_id: The canonical section identifier
            content: The section content to insert

        Returns:
            The content if section can be inserted, None if it's a duplicate
        """
        if not content or not content.strip():
            return None

        if not self.can_insert(section_id):
            self._duplicate_log.append(f"BLOCKED duplicate section: {section_id}")
            return None

        self.mark_inserted(section_id, content)
        return content

    def deduplicate_final(self, letter_content: str) -> Tuple[str, DeduplicationResult]:
        """
        Final pass deduplication on assembled letter content.

        Removes any duplicate section headers that slipped through,
        and eliminates repeated paragraphs.

        Args:
            letter_content: The assembled letter content

        Returns:
            Tuple of (cleaned_content, DeduplicationResult)
        """
        result = DeduplicationResult()
        result.original_section_count = len(letter_content.split('\n\n'))

        lines = letter_content.split('\n')
        cleaned_lines = []
        seen_headers: Set[str] = set()
        seen_paragraphs: Set[int] = set()

        current_paragraph = []

        for line in lines:
            # Check for section headers (lines that look like headers)
            is_header = self._is_section_header(line)

            if is_header:
                header_key = self._normalize_header(line)
                if header_key in seen_headers:
                    # Skip this duplicate header
                    result.duplicate_headers_found.append(line.strip())
                    result.is_clean = False
                    continue
                seen_headers.add(header_key)

            # Track paragraphs for duplicate detection
            if line.strip() == '' and current_paragraph:
                para_text = '\n'.join(current_paragraph)
                para_hash = hash(para_text.strip().lower())

                if para_hash in seen_paragraphs and len(para_text) > 100:
                    # Skip duplicate paragraph (only if substantial)
                    result.repeated_paragraphs_removed += 1
                    result.is_clean = False
                    current_paragraph = []
                    continue

                seen_paragraphs.add(para_hash)
                cleaned_lines.extend(current_paragraph)
                cleaned_lines.append('')
                current_paragraph = []
            elif line.strip():
                current_paragraph.append(line)

        # Don't forget last paragraph
        if current_paragraph:
            cleaned_lines.extend(current_paragraph)

        # Remove duplicate MOV/Case Law blocks using pattern matching
        cleaned_content = '\n'.join(cleaned_lines)
        cleaned_content, pattern_removals = self._remove_duplicate_blocks(cleaned_content)
        result.duplicates_removed.extend(pattern_removals)

        result.deduplicated_section_count = len(cleaned_content.split('\n\n'))
        result.is_clean = result.is_clean and len(result.duplicates_removed) == 0

        return cleaned_content, result

    def _is_section_header(self, line: str) -> bool:
        """Check if a line appears to be a section header."""
        line = line.strip()
        if not line:
            return False

        # Roman numeral headers (I., II., III., etc.)
        if re.match(r'^[IVX]+\.\s+[A-Z]', line):
            return True

        # Markdown headers
        if line.startswith('**') and line.endswith('**'):
            return True
        if line.startswith('###') or line.startswith('##'):
            return True

        # All caps headers
        if line.isupper() and len(line) > 10:
            return True

        return False

    def _normalize_header(self, header: str) -> str:
        """Normalize a header for comparison."""
        # Remove markdown formatting
        normalized = re.sub(r'[*#]+', '', header)
        # Remove roman numerals
        normalized = re.sub(r'^[IVX]+\.\s*', '', normalized)
        # Lowercase and strip
        return normalized.strip().lower()

    def _remove_duplicate_blocks(self, content: str) -> Tuple[str, List[str]]:
        """Remove duplicate content blocks based on patterns."""
        removals = []

        for pattern in self.DUPLICATE_PATTERNS:
            # Find all matches
            matches = list(re.finditer(pattern, content, re.IGNORECASE))

            if len(matches) > 1:
                # Keep first occurrence, remove subsequent ones
                # Find the paragraph containing each match and remove duplicates
                for match in matches[1:]:
                    # Find paragraph boundaries around this match
                    start = content.rfind('\n\n', 0, match.start())
                    end = content.find('\n\n', match.end())

                    if start == -1:
                        start = 0
                    if end == -1:
                        end = len(content)

                    # Extract and remove the duplicate paragraph
                    duplicate_block = content[start:end]
                    if len(duplicate_block.strip()) < 500:  # Only remove smaller blocks
                        content = content[:start] + content[end:]
                        removals.append(f"Removed duplicate: {pattern}")

        return content, removals

    def get_insertion_log(self) -> List[str]:
        """Get the log of insertion attempts."""
        return list(self._duplicate_log)

    def get_inserted_sections(self) -> Set[str]:
        """Get the set of sections that have been inserted."""
        return set(self._inserted_sections)


from .metro2_explanations import Metro2ExplanationBuilder, get_metro2_explanation
from .case_law import CaseLawLibrary, STANDARD_REINVESTIGATION_CITE
from .mov_requirements import MOVBuilder
from .validators_legal import LegalLetterValidator, LetterContentValidator, ValidationIssue
from .tones import TONE_REGISTRY, get_tone_class, is_legal_tone, is_civil_tone
from .diversity import DiversityEngine, shuffle_section_order
from .fcra_statutes import resolve_statute
from .tone_mask import ToneMask, LetterDomain, get_domain_for_tone, create_mask_for_tone

# Import the new diversity engine components
from .diversity_engine import (
    DiversityEngine as NewDiversityEngine,
    DiversityConfig,
    MutationStrength,
    create_diversity_engine,
)
from .entropy import EntropyLevel, create_entropy_controller

# Import structural fixer for post-diversity structure enforcement
from .structural_fixer import StructuralFixer, StructuralMetadata, create_structural_fixer


# Load seed data
SEEDS_DIR = Path(__file__).parent / "seeds"


def load_seed_file(filename: str) -> Dict:
    """Load a seed JSON file."""
    filepath = SEEDS_DIR / filename
    if filepath.exists():
        with open(filepath, "r") as f:
            return json.load(f)
    return {}


OPENINGS = load_seed_file("openings.json")
CLOSINGS = load_seed_file("closings.json")
TRANSITIONS = load_seed_file("transitions.json")
SECTION_INTROS = load_seed_file("section_intros.json")


# Bureau addresses
BUREAU_ADDRESSES = {
    "transunion": {
        "name": "TransUnion LLC",
        "address": "P.O. Box 2000",
        "city_state_zip": "Chester, PA 19016-2000",
    },
    "experian": {
        "name": "Experian",
        "address": "P.O. Box 4500",
        "city_state_zip": "Allen, TX 75013",
    },
    "equifax": {
        "name": "Equifax Information Services LLC",
        "address": "P.O. Box 740256",
        "city_state_zip": "Atlanta, GA 30374-0256",
    },
}


class LegalLetterAssembler:
    """
    Main assembler for legal dispute letters.

    Combines grouping strategies, Metro-2 explanations, case law,
    MOV requirements, and tone engines to generate complete letters.
    """

    def __init__(
        self,
        tone: str = "professional",
        grouping_strategy: str = "by_fcra_section",
        seed: int = None,
        include_case_law: bool = True,
        include_metro2: bool = True,
        include_mov: bool = True,
        entropy_level: str = "medium",
        mutation_strength: str = "medium",
    ):
        """
        Initialize the assembler.

        Args:
            tone: Letter tone (strict_legal, professional, soft_legal, aggressive)
            grouping_strategy: How to group violations
            seed: Random seed for deterministic phrase selection
            include_case_law: Whether to include case law citations
            include_metro2: Whether to include Metro-2 explanations
            include_mov: Whether to include MOV requirements
            entropy_level: Variation intensity (low, medium, high, maximum)
            mutation_strength: Sentence mutation intensity (none, low, medium, high, maximum)
        """
        self.tone = tone
        self.grouping_strategy = GroupingStrategy(grouping_strategy)
        self.seed = seed if seed is not None else random.randint(0, 999999)
        self.include_case_law = include_case_law
        self.include_metro2 = include_metro2
        self.include_mov = include_mov
        self.entropy_level = entropy_level
        self.mutation_strength = mutation_strength

        # Determine letter domain (legal vs civil) from tone
        self.letter_domain = get_domain_for_tone(tone)
        self.is_legal_letter = self.letter_domain == LetterDomain.LEGAL
        self.is_civil_letter = self.letter_domain == LetterDomain.CIVIL

        # Get tone engine
        self.tone_engine = get_tone_class(tone)
        if not self.tone_engine:
            self.tone_engine = get_tone_class("professional")

        # Initialize builders
        self.metro2_builder = Metro2ExplanationBuilder()
        self.mov_builder = MOVBuilder()

        # Initialize legacy diversity engine for backward compatibility
        self.diversity_engine = DiversityEngine(seed=self.seed, tone=tone)

        # Initialize new diversity engine with entropy and mutation controls
        domain = "legal" if self.is_legal_letter else "civil"
        self.new_diversity_engine = create_diversity_engine(
            entropy_level=entropy_level,
            mutation_strength=mutation_strength,
            domain=domain,
            seed=self.seed,
        )

        # Initialize tone mask for domain isolation
        self.tone_mask = create_mask_for_tone(tone, include_case_law=include_case_law)

        # Initialize structural fixer for post-diversity integrity enforcement
        self.structural_fixer = create_structural_fixer()

        # Initialize section deduplicator for duplicate prevention
        # RULE: Each section header may appear only ONCE in the final letter
        self.deduplicator = SectionDeduplicator()

    def generate(
        self,
        violations: List[Dict[str, Any]],
        consumer: Dict[str, Any],
        bureau: str,
        recipient: Dict[str, Any] = None,
    ) -> Tuple[str, List[ValidationIssue]]:
        """
        Generate a complete legal dispute letter.

        Args:
            violations: List of violation dictionaries
            consumer: Consumer information dict with name, address, ssn_last4
            bureau: Target bureau (transunion, experian, equifax)
            recipient: Optional custom recipient info

        Returns:
            Tuple of (letter_content, validation_issues)
        """
        # Build recipient info
        if not recipient:
            recipient = self._build_bureau_recipient(bureau)

        # Validate inputs
        is_valid, issues = LegalLetterValidator.validate_all(
            violations=violations,
            consumer=consumer,
            recipient=recipient,
            tone=self.tone,
            grouping_strategy=self.grouping_strategy.value,
        )

        if not is_valid:
            # Return validation errors without generating
            return "", issues

        # Group violations
        grouper = LegalGrouper(violations)
        grouped = grouper.group(self.grouping_strategy)

        # Extract FCRA sections for legal basis
        fcra_sections = list(set(
            v.get("fcra_section", "611") for v in violations
        ))

        # =================================================================
        # DEDUPLICATION GUARD: Reset and prepare for new letter generation
        # RULE: Each section header may appear only ONCE in the final letter
        # =================================================================
        self.deduplicator.reset()

        # Build letter sections in STRICT ORDER with deduplication guards
        # Enforces: Header → Intro → Disputed Items → Legal Basis → MOV → Case Law → Demands → Signature
        # This order is immutable and prevents section duplication/orphaning
        sections = []

        # 1. HEADER (consumer info + date + subject line)
        header_content = self.deduplicator.try_insert("header", self._build_header(consumer, recipient))
        if header_content:
            sections.append(header_content)

        # 2. INTRO (tone-specific introduction paragraph)
        intro_content = self.deduplicator.try_insert("introduction", self._build_introduction(bureau))
        if intro_content:
            sections.append(intro_content)

        # 3. DISPUTED ITEMS (violations section with Metro-2 inline if applicable)
        violations_section = self._build_violations_section(grouped, violations)
        # Inline Metro-2 explanations within violations to prevent duplication
        if self.include_metro2 and self.is_legal_letter:
            metro2_section = self._build_metro2_section(violations)
            if metro2_section:
                violations_section = f"{violations_section}\n\n{metro2_section}"
        violations_content = self.deduplicator.try_insert("violations", violations_section)
        if violations_content:
            sections.append(violations_content)

        # 4. LEGAL BASIS
        legal_basis_content = self.deduplicator.try_insert("legal_basis", self._build_legal_basis(fcra_sections))
        if legal_basis_content:
            sections.append(legal_basis_content)

        # 5. METHOD OF VERIFICATION (legal letters only) - DEDUP GUARDED
        if self.include_mov and self.is_legal_letter:
            mov_content = self.deduplicator.try_insert("mov", self._build_mov_section(violations))
            if mov_content:
                sections.append(mov_content)

        # 6. CASE LAW (legal letters only, if tone requires it) - DEDUP GUARDED
        if self.include_case_law and self.is_legal_letter:
            case_law_content = self.deduplicator.try_insert("case_law", self._build_case_law_section(violations))
            if case_law_content:
                sections.append(case_law_content)

        # 7. DEMANDS
        demands_content = self.deduplicator.try_insert("demands", self._build_demands_section())
        if demands_content:
            sections.append(demands_content)

        # 8. SIGNATURE BLOCK (includes closing statement)
        signature_content = self.deduplicator.try_insert("signature", self._build_signature(consumer))
        if signature_content:
            sections.append(signature_content)

        # Combine sections
        letter_content = "\n\n".join(filter(None, sections))

        # =================================================================
        # FINAL DEDUPLICATION PASS: Catch any duplicates that slipped through
        # This handles edge cases like duplicate paragraphs or repeated headers
        # =================================================================
        letter_content, dedup_result = self.deduplicator.deduplicate_final(letter_content)

        # Store deduplication metadata for return
        self._deduplication_result = dedup_result

        # Apply tone mask for domain isolation
        # This filters forbidden phrases and applies domain-specific rules
        letter_content = self.tone_mask.apply(letter_content)

        # Apply structural fixer to enforce section ordering and integrity
        # This runs AFTER diversity/mutation and BEFORE final validation
        domain = "legal" if self.is_legal_letter else "civil"
        letter_content, structural_metadata = self.structural_fixer.fix_structure(
            letter_content,
            domain=domain,
            tone=self.tone,
            metadata={
                "bureau": bureau,
                "violation_count": len(violations),
                "include_case_law": self.include_case_law,
                "include_metro2": self.include_metro2,
                "include_mov": self.include_mov,
            }
        )

        # Store structural metadata for return
        self._structural_metadata = structural_metadata

        # Validate generated content
        content_issues = LetterContentValidator.validate_letter_content(
            letter_content, self.tone
        )
        issues.extend(content_issues)

        return letter_content, issues

    def _build_bureau_recipient(self, bureau: str) -> Dict[str, Any]:
        """Build recipient info for a bureau."""
        bureau_lower = bureau.lower()
        bureau_info = BUREAU_ADDRESSES.get(bureau_lower, BUREAU_ADDRESSES["transunion"])
        return {
            "name": bureau_info["name"],
            "address": bureau_info["address"],
            "city_state_zip": bureau_info["city_state_zip"],
        }

    def _build_header(self, consumer: Dict, recipient: Dict) -> str:
        """Build the letter header with addresses."""
        today = datetime.now().strftime("%B %d, %Y")

        lines = [
            consumer.get("name", "[CONSUMER NAME]"),
        ]

        if consumer.get("address"):
            lines.append(consumer["address"])
        if consumer.get("city_state_zip"):
            lines.append(consumer["city_state_zip"])

        lines.extend([
            "",
            today,
            "",
            recipient.get("name", "[RECIPIENT]"),
            recipient.get("address", ""),
            recipient.get("city_state_zip", ""),
        ])

        return "\n".join(lines)

    def _build_opening(self) -> str:
        """Build the opening/subject line."""
        openings = OPENINGS.get(self.tone, OPENINGS.get("professional", []))
        if openings:
            return openings[self.seed % len(openings)]
        return self.tone_engine.get_opening(self.seed)

    def _build_introduction(self, bureau: str = None) -> str:
        """Build the introduction section with bureau-specific content."""
        header = self.tone_engine.get_section_header("introduction")
        intro = SECTION_INTROS.get(self.tone, {}).get("introduction", "")

        if not intro:
            intro = self.tone_engine.get_expression("dispute_intro", self.seed)

        # Add bureau-specific intro sentence for differentiation
        if bureau:
            bureau_intro = self.diversity_engine.get_bureau_intro(bureau)
            intro = f"{bureau_intro}\n\n{intro}"

        return f"{header}\n\n{intro}"

    def _build_legal_basis(self, fcra_sections: List[str]) -> str:
        """Build the legal basis section."""
        header = self.tone_engine.get_section_header("legal_basis")
        transition = TRANSITIONS.get(self.tone, {}).get("to_legal_basis", "")
        intro = SECTION_INTROS.get(self.tone, {}).get("legal_basis", "")

        lines = [header, ""]

        if transition:
            lines.append(transition)
            lines.append("")

        if intro:
            lines.append(intro)
            lines.append("")

        # Add section descriptions based on tone
        if hasattr(self.tone_engine, "format_legal_basis_section"):
            return self.tone_engine.format_legal_basis_section([], fcra_sections)

        # Default formatting
        for section in sorted(set(fcra_sections)):
            from .grouping_strategies import FCRA_SECTIONS
            section_info = FCRA_SECTIONS.get(section, {})
            desc = section_info.get("description", f"Section {section}")
            lines.append(f"  - FCRA Section {section}: {desc}")

        return "\n".join(lines)

    def _build_violations_section(
        self,
        grouped: Dict[str, List[Dict]],
        all_violations: List[Dict]
    ) -> str:
        """Build the violations section with grouped items."""
        header = self.tone_engine.get_section_header("violations")
        transition = TRANSITIONS.get(self.tone, {}).get("to_violations", "")
        intro = SECTION_INTROS.get(self.tone, {}).get("violations", "")

        lines = [header, ""]

        if transition:
            lines.append(transition)
            lines.append("")

        if intro:
            lines.append(intro)
            lines.append("")

        # Add preamble - different for civil vs legal
        if self.is_civil_letter:
            # Civil letters use simple, non-legal preamble
            lines.append("I've identified the following issues on my credit report:")
        else:
            # Legal letters use strategy-specific preamble
            strategy_preamble = self.diversity_engine.get_strategy_preamble(self.grouping_strategy.value)
            lines.append(strategy_preamble)
        lines.append("")

        # Get strategy-specific formatting configuration (legal only)
        strategy_fmt = self.diversity_engine.get_strategy_format(self.grouping_strategy.value) if not self.is_civil_letter else {}

        # Format each group with appropriate headers
        violation_index = 1
        between_transition = TRANSITIONS.get(self.tone, {}).get("between_violations", "") if not self.is_civil_letter else ""

        for group_key, group_violations in grouped.items():
            # Civil letters don't show legal-style group headers
            if self.is_civil_letter:
                # Simple creditor grouping for civil letters
                if self.grouping_strategy == GroupingStrategy.BY_CREDITOR:
                    lines.append(f"**{group_key}**")
                    lines.append("")
            else:
                # Legal letters use strategy-specific headers
                if self.grouping_strategy == GroupingStrategy.BY_FCRA_SECTION:
                    from .grouping_strategies import FCRA_SECTIONS
                    section_info = FCRA_SECTIONS.get(group_key, {})
                    group_title = section_info.get("title", f"Section {group_key} Violations")
                    lines.append(f"### STATUTORY CATEGORY: {group_title}")
                    lines.append(f"Legal Reference: {resolve_statute(group_key)}")
                elif self.grouping_strategy == GroupingStrategy.BY_CREDITOR:
                    lines.append(f"### FURNISHER: {group_key}")
                    lines.append(f"Reporting entity requiring investigation")
                elif self.grouping_strategy == GroupingStrategy.BY_METRO2_FIELD:
                    lines.append(f"### DATA ELEMENT: {group_key.replace('_', ' ').title()}")
                    lines.append(f"Metro-2 field with reporting discrepancies")
                elif self.grouping_strategy == GroupingStrategy.BY_SEVERITY:
                    severity_labels = {"high": "CRITICAL", "medium": "MODERATE", "low": "MINOR"}
                    label = severity_labels.get(group_key.lower(), group_key.upper())
                    lines.append(f"### PRIORITY LEVEL: {label}")
                    lines.append(f"Impact severity: {group_key.replace('_', ' ').title()}")
                lines.append("")

            # Format each violation - use tone engine's format_violation for civil letters
            for violation in group_violations.violations:
                if self.is_civil_letter and hasattr(self.tone_engine, 'format_violation'):
                    # Civil letters use tone engine's native format with factual evidence
                    formatted = self.tone_engine.format_violation(violation, violation_index)
                else:
                    # Legal letters use strategy-specific formatting
                    formatted = self._format_violation_with_strategy(
                        violation, violation_index, self.grouping_strategy.value, strategy_fmt
                    )
                lines.append(formatted)
                violation_index += 1

                if between_transition and violation != group_violations.violations[-1]:
                    lines.append(between_transition)
                    lines.append("")

            lines.append("")

        # Add summary at end - different for civil vs legal
        if self.is_civil_letter:
            # Civil letters don't need legal-style summaries
            pass
        else:
            # Legal letters use strategy-specific summary
            strategy_summary = self.diversity_engine.get_strategy_summary(self.grouping_strategy.value)
            lines.append(strategy_summary)
            lines.append("")

        return "\n".join(lines)

    def _build_metro2_section(self, violations: List[Dict]) -> Optional[str]:
        """Build the Metro-2 explanations section."""
        # Gather unique Metro-2 fields from violations
        metro2_fields = set()
        for v in violations:
            if v.get("metro2_field"):
                metro2_fields.add(v["metro2_field"])

        if not metro2_fields:
            return None

        header = self.tone_engine.get_section_header("metro2")
        intro = SECTION_INTROS.get(self.tone, {}).get("metro2", "")

        lines = [header, ""]

        if intro:
            lines.append(intro)
            lines.append("")

        # Add explanations for each field
        for field in sorted(metro2_fields):
            explanation = get_metro2_explanation(field)
            if explanation:
                lines.append(f"**{field.upper()} (Metro-2 Field {explanation.field_number})**")
                lines.append("")
                lines.append(f"  Segment: {explanation.segment}")
                lines.append(f"  Purpose: {explanation.description}")
                lines.append("")
                lines.append(f"  Legal Requirement: {explanation.legal_language}")
                lines.append("")
                if explanation.common_errors:
                    lines.append("  Common Errors:")
                    for error in explanation.common_errors[:3]:
                        lines.append(f"    - {error}")
                lines.append("")

        return "\n".join(lines)

    def _build_mov_section(self, violations: List[Dict]) -> str:
        """Build the Method of Verification section."""
        header = self.tone_engine.get_section_header("mov")
        transition = TRANSITIONS.get(self.tone, {}).get("to_mov", "")
        intro = SECTION_INTROS.get(self.tone, {}).get("mov", "")

        lines = [header, ""]

        if transition:
            lines.append(transition)
            lines.append("")

        if intro:
            lines.append(intro)
            lines.append("")

        # Build MOV requirements based on violations
        mov_builder = MOVBuilder(violations, self.tone, self.include_case_law)
        mov_section = mov_builder.build_section()

        lines.append(mov_section)

        # Add Cushman citation if aggressive/strict (only if case law is enabled)
        if self.include_case_law and self.tone in ["aggressive", "strict_legal"]:
            lines.append("")
            lines.append(STANDARD_REINVESTIGATION_CITE)

        return "\n".join(lines)

    def _build_case_law_section(self, violations: List[Dict]) -> str:
        """Build the case law section."""
        header = self.tone_engine.get_section_header("case_law")
        transition = TRANSITIONS.get(self.tone, {}).get("to_case_law", "")
        intro = SECTION_INTROS.get(self.tone, {}).get("case_law", "")

        lines = [header, ""]

        if transition:
            lines.append(transition)
            lines.append("")

        if intro:
            lines.append(intro)
            lines.append("")

        # Select relevant cases based on violation types
        has_reinvestigation = any(
            (v.get("fcra_section") or "").startswith("611")
            for v in violations
        )
        has_furnisher = any(
            (v.get("fcra_section") or "").startswith("623")
            for v in violations
        )
        has_willful = any(
            v.get("severity") == "high" or v.get("willful")
            for v in violations
        )

        cases = []

        if has_reinvestigation:
            cases.append(CaseLawLibrary.get_case("cushman"))
            cases.append(CaseLawLibrary.get_case("henson"))

        if has_furnisher:
            cases.append(CaseLawLibrary.get_case("gorman"))

        if has_willful:
            cases.append(CaseLawLibrary.get_case("safeco"))

        # Always include Dennis for general accuracy
        cases.append(CaseLawLibrary.get_case("dennis"))

        # Remove duplicates while preserving order
        seen = set()
        unique_cases = []
        for case in cases:
            if case and case.case_name not in seen:
                seen.add(case.case_name)
                unique_cases.append(case)

        # Format cases
        for case in unique_cases[:5]:  # Limit to 5 cases
            lines.append(f"**{case.case_name}**, {case.citation}")
            lines.append("")
            lines.append(f"  Holding: {case.holding}")
            lines.append("")
            if case.key_quote and self.tone in ["strict_legal", "aggressive"]:
                lines.append(f'  Key Quote: "{case.key_quote}"')
                lines.append("")
            lines.append(f"  Relevance: {case.relevance}")
            lines.append("")

        return "\n".join(lines)

    def _build_demands_section(self) -> str:
        """Build the demands section."""
        header = self.tone_engine.get_section_header("demands")
        transition = TRANSITIONS.get(self.tone, {}).get("to_demands", "")
        intro = SECTION_INTROS.get(self.tone, {}).get("demands", "")

        lines = [header, ""]

        if transition:
            lines.append(transition)
            lines.append("")

        if intro:
            lines.append(intro)
            lines.append("")

        # Standard demands based on tone
        if self.tone == "aggressive":
            demands = [
                "CONDUCT a reasonable reinvestigation using ORIGINAL SOURCE DOCUMENTATION within 30 days",
                "DELETE any information that cannot be INDEPENDENTLY VERIFIED through original documents",
                "CEASE reporting disputed items during the investigation period",
                "PROVIDE written results of your investigation including the method of verification used",
                "FORWARD this dispute to all furnishers as required by FCRA Section 611(a)(2)",
            ]
        elif self.tone == "strict_legal":
            demands = [
                "Conduct a reasonable reinvestigation pursuant to FCRA Section 611(a)(1)",
                "Delete or modify any information that cannot be verified through original source documentation",
                "Provide written notice of the results within 30 days as required by Section 611(a)(6)(A)",
                "Include a description of the reinvestigation procedure used",
                "Forward this dispute to all relevant furnishers per Section 611(a)(2)",
            ]
        elif self.tone == "soft_legal":
            demands = [
                "Please investigate these items within 30 days as the law requires",
                "Remove any information that can't be properly verified",
                "Send me written results of your investigation",
                "Let me know what steps you took to verify the information",
            ]
        else:  # professional
            demands = [
                "Conduct a thorough reinvestigation of the disputed items within 30 days",
                "Delete any information that cannot be independently verified",
                "Provide written notice of the investigation results",
                "Include the method of verification used for each item",
                "Forward this dispute to the relevant furnishers",
            ]

        for i, demand in enumerate(demands, 1):
            lines.append(f"{i}. {demand}")

        return "\n".join(lines)

    def _build_conclusion(self, bureau: str = None) -> str:
        """Build the conclusion section with bureau-specific content."""
        header = self.tone_engine.get_section_header("conclusion")
        intro = SECTION_INTROS.get(self.tone, {}).get("conclusion", "")

        lines = [header, ""]

        if intro:
            lines.append(intro)
            lines.append("")

        # Get closing from seeds or tone engine
        closings = CLOSINGS.get(self.tone, [])
        if closings:
            closing = closings[self.seed % len(closings)]
        elif hasattr(self.tone_engine, "format_conclusion"):
            closing = self.tone_engine.format_conclusion(self.seed)
        else:
            closing = "Thank you for your attention to this matter."

        lines.append(closing)

        # Add bureau-specific closing if bureau is provided
        if bureau:
            bureau_closing = self.diversity_engine.get_bureau_closing(bureau)
            lines.append("")
            lines.append(bureau_closing)

        return "\n".join(lines)

    def _format_violation_with_strategy(
        self, violation: Dict[str, Any], index: int, strategy: str, strategy_fmt: Dict
    ) -> str:
        """Format a violation based on grouping strategy for structural differentiation."""
        v_type = violation.get("violation_type", "inaccuracy")
        creditor = violation.get("creditor_name", "Unknown Creditor")
        account = violation.get("account_number_masked", "")
        fcra_section = violation.get("fcra_section", "611")
        metro2_field = violation.get("metro2_field", "")
        evidence = violation.get("evidence", "")
        severity = violation.get("severity", "medium")

        lines = []
        fields_order = strategy_fmt.get("fields_order", ["violation_type", "fcra_section", "metro2_field", "evidence"])

        # Strategy-specific header using diversity engine
        header = self.diversity_engine.format_violation_header(strategy, index, violation)
        lines.append(f"**{header}**")
        lines.append("")

        # Add fields in strategy-specific order
        for field in fields_order:
            if field == "violation_type":
                lines.append(f"Type: {v_type.replace('_', ' ').title()}")
            elif field == "fcra_section":
                fcra_citation = self.diversity_engine.get_fcra_citation(fcra_section)
                lines.append(f"Legal Reference: {fcra_citation}")
            elif field == "metro2_field" and metro2_field:
                lines.append(f"Data Element: {metro2_field}")
            elif field == "evidence" and evidence:
                lines.append(f"Description: {evidence}")

        lines.append("")

        # Get diverse intro and demand
        intro = self.diversity_engine.get_unique_violation_intro()
        demand = self.diversity_engine.get_unique_verification_demand()
        intro = self.diversity_engine.diversify(intro, intensity=0.2)
        demand = self.diversity_engine.diversify(demand, intensity=0.2)

        lines.append(intro)
        lines.append(demand)

        if self.tone == "aggressive":
            legal_basis = self.diversity_engine.get_unique_legal_basis()
            lines.append("")
            lines.append(legal_basis)

        lines.append("")
        return "\n".join(lines)

    def _format_violation_with_diversity(self, violation: Dict[str, Any], index: int) -> str:
        """Format a violation with diversity measures to avoid template-like output."""
        v_type = violation.get("violation_type", "inaccuracy")
        creditor = violation.get("creditor_name", "Unknown Creditor")
        account = violation.get("account_number_masked", "")
        fcra_section = violation.get("fcra_section", "611")
        metro2_field = violation.get("metro2_field", "")
        evidence = violation.get("evidence", "")

        lines = []

        # Format header based on tone
        if self.tone == "aggressive":
            lines.append(f"    **VIOLATION {index}: {creditor.upper()}**")
        elif self.tone == "strict_legal":
            lines.append(f"    {index}. **{creditor}**{f' (Account: {account})' if account else ''}")
        elif self.tone == "soft_legal":
            lines.append(f"**{index}. {creditor}**")
        else:  # professional
            lines.append(f"**Item {index}: {creditor}**")

        lines.append("")

        if account and self.tone not in ["strict_legal"]:
            if self.tone == "soft_legal":
                lines.append(f"   Account ending in: {account}")
            elif self.tone == "aggressive":
                lines.append(f"    Account: {account}")
            else:
                lines.append(f"Account Number: {account}")

        # Get varied FCRA citation using diversity engine
        fcra_citation = self.diversity_engine.get_fcra_citation(fcra_section)

        # Format type based on tone with varied FCRA citations
        if self.tone == "aggressive":
            lines.append(f"    VIOLATION TYPE: {v_type.replace('_', ' ').upper()}")
            lines.append(f"    STATUTORY VIOLATION: {fcra_citation}")
        elif self.tone == "strict_legal":
            lines.append(f"       Violation Type: {v_type.replace('_', ' ').title()}")
            lines.append(f"       Applicable Law: {fcra_citation}")
        elif self.tone == "soft_legal":
            lines.append(f"   Problem: {v_type.replace('_', ' ').title()}")
        else:
            lines.append(f"Issue: {v_type.replace('_', ' ').title()}")
            lines.append(f"Legal Reference: {fcra_citation}")

        if metro2_field:
            # Vary the metro2 field label to prevent n-gram repetition
            metro2_labels = {
                "aggressive": ["METRO-2 FIELD AFFECTED", "REPORTING CODE VIOLATION", "DATA ELEMENT IMPACTED"],
                "strict_legal": ["Metro-2 Field", "Reporting Element", "Credit Data Field"],
                "soft_legal": ["Reporting field", "Data element", "Credit field"],
                "professional": ["Data Field Affected", "Reporting Field", "Credit Element"],
            }
            label_choices = metro2_labels.get(self.tone, metro2_labels["professional"])
            metro2_label = self.diversity_engine.rng.choice(label_choices)

            if self.tone == "aggressive":
                lines.append(f"    {metro2_label}: {metro2_field}")
            elif self.tone == "strict_legal":
                lines.append(f"       {metro2_label}: {metro2_field}")
            else:
                lines.append(f"{metro2_label}: {metro2_field}")

        if evidence:
            if self.tone == "aggressive":
                lines.append(f"    SPECIFIC DEFICIENCY: {evidence}")
            elif self.tone == "strict_legal":
                lines.append(f"       Specific Issue: {evidence}")
            elif self.tone == "soft_legal":
                lines.append(f"   Details: {evidence}")
            else:
                lines.append(f"Details: {evidence}")

        lines.append("")

        # Use diversity engine for unique intro and verification demand
        intro = self.diversity_engine.get_unique_violation_intro()
        demand = self.diversity_engine.get_unique_verification_demand()

        # Apply synonym diversification
        intro = self.diversity_engine.diversify(intro, intensity=0.2)
        demand = self.diversity_engine.diversify(demand, intensity=0.2)

        if self.tone == "aggressive":
            legal_basis = self.diversity_engine.get_unique_legal_basis()
            lines.extend([
                f"    {intro}",
                f"    {demand}",
                "",
                f"    {legal_basis}",
                ""
            ])
        elif self.tone == "strict_legal":
            lines.extend([
                f"       {intro}",
                f"       {demand}",
                ""
            ])
        elif self.tone == "soft_legal":
            lines.extend([
                f"   {intro}",
                f"   {demand}",
                ""
            ])
        else:
            lines.extend([
                intro,
                demand,
                ""
            ])

        return "\n".join(lines)

    def _build_signature(self, consumer: Dict) -> str:
        """Build the signature block."""
        if hasattr(self.tone_engine, "format_signature_block"):
            return self.tone_engine.format_signature_block(
                consumer.get("name", "[CONSUMER NAME]")
            )

        # Default signature
        name = consumer.get("name", "[CONSUMER NAME]")

        lines = [
            "Respectfully submitted,",
            "",
            "",
            "",
            "_________________________________",
            name,
            "",
            "Date: _____________________",
            "",
        ]

        if consumer.get("ssn_last4"):
            lines.append(f"SSN (last 4): XXX-XX-{consumer['ssn_last4']}")

        lines.extend([
            "",
            "Enclosures:",
            "  - Copy of credit report with disputed items highlighted",
            "  - Copy of government-issued identification",
            "",
            "SENT VIA CERTIFIED MAIL, RETURN RECEIPT REQUESTED",
        ])

        return "\n".join(lines)


def generate_legal_letter(
    violations: List[Dict[str, Any]],
    consumer: Dict[str, Any],
    bureau: str,
    tone: str = "professional",
    grouping_strategy: str = "by_fcra_section",
    seed: int = None,
    include_case_law: bool = True,
    include_metro2: bool = True,
    include_mov: bool = True,
    entropy_level: str = "medium",
    mutation_strength: str = "medium",
) -> Dict[str, Any]:
    """
    Convenience function to generate a legal letter.

    Args:
        violations: List of violation dictionaries
        consumer: Consumer information dict
        bureau: Target bureau (transunion, experian, equifax)
        tone: Letter tone
        grouping_strategy: How to group violations
        seed: Random seed for deterministic output
        include_case_law: Whether to include case law citations
        include_metro2: Whether to include Metro-2 explanations
        include_mov: Whether to include MOV requirements
        entropy_level: Variation intensity (low, medium, high, maximum)
        mutation_strength: Sentence mutation intensity (none, low, medium, high, maximum)

    Returns:
        Dict with 'letter', 'validation_issues', 'is_valid', 'metadata'
    """
    assembler = LegalLetterAssembler(
        tone=tone,
        grouping_strategy=grouping_strategy,
        seed=seed,
        include_case_law=include_case_law,
        include_metro2=include_metro2,
        include_mov=include_mov,
        entropy_level=entropy_level,
        mutation_strength=mutation_strength,
    )

    letter, issues = assembler.generate(
        violations=violations,
        consumer=consumer,
        bureau=bureau,
    )

    is_valid = not any(i.level.value == "error" for i in issues)

    # Get mask metadata for tone isolation compliance
    mask_metadata = assembler.tone_mask.to_dict()

    # Get diversity engine statistics
    diversity_stats = assembler.new_diversity_engine.get_variation_stats()

    # Get structural metadata
    structural_metadata = getattr(assembler, '_structural_metadata', None)
    structural_meta_dict = None
    if structural_metadata:
        structural_meta_dict = {
            "sections_found": structural_metadata.sections_found,
            "sections_reordered": structural_metadata.sections_reordered,
            "sections_inserted": structural_metadata.sections_inserted,
            "duplicates_removed": structural_metadata.duplicates_removed,
            "cross_domain_removed": structural_metadata.cross_domain_removed,
            "order_violations_fixed": structural_metadata.order_violations_fixed,
            "structure_valid": structural_metadata.structure_valid,
            "domain": structural_metadata.domain,
        }

    # Get deduplication metadata
    dedup_result = getattr(assembler, '_deduplication_result', None)
    dedup_meta_dict = None
    if dedup_result:
        dedup_meta_dict = {
            "original_section_count": dedup_result.original_section_count,
            "deduplicated_section_count": dedup_result.deduplicated_section_count,
            "duplicates_removed": dedup_result.duplicates_removed,
            "duplicate_headers_found": dedup_result.duplicate_headers_found,
            "repeated_paragraphs_removed": dedup_result.repeated_paragraphs_removed,
            "is_clean": dedup_result.is_clean,
            "sections_inserted": list(assembler.deduplicator.get_inserted_sections()),
            "insertion_log": assembler.deduplicator.get_insertion_log(),
        }

    return {
        "letter": letter,
        "validation_issues": [
            {
                "level": i.level.value,
                "code": i.code,
                "message": i.message,
                "field": i.field,
                "suggestion": i.suggestion,
            }
            for i in issues
        ],
        "is_valid": is_valid,
        "metadata": {
            "tone": tone,
            "grouping_strategy": grouping_strategy,
            "seed": seed or assembler.seed,
            "violation_count": len(violations),
            "bureau": bureau,
            "generated_at": datetime.now().isoformat(),
            # Letter domain information (LEGAL vs CIVIL)
            "letter_domain": assembler.letter_domain.value,
            "is_legal_letter": assembler.is_legal_letter,
            "is_civil_letter": assembler.is_civil_letter,
            # Diversity engine settings
            "entropy_level": entropy_level,
            "mutation_strength": mutation_strength,
        },
        # Mask application metadata (SWEEP C compliance)
        "mask_metadata": mask_metadata,
        # Diversity engine statistics
        "diversity_stats": diversity_stats,
        # Structural integrity metadata
        "structural_metadata": structural_meta_dict,
        # Deduplication guard metadata
        "deduplication_metadata": dedup_meta_dict,
    }
