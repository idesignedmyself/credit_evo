"""
Credit Copilot - Letter Assembler

Main orchestration for generating human-sounding dispute letters.
Implements three narrative structures:
- Type A: Narrative Flow (storytelling approach)
- Type B: Observation Style (analytical, fact-based)
- Type C: Question-Based (consumer asking questions)

Key features:
- No template markers (bullet points, numbered lists)
- Natural prose flow
- Bureau-specific customization
- Phrase rotation to prevent repetition
"""
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import date
import random
import hashlib

from .expressions import (
    get_violation_expression,
    get_account_reference,
    get_confidence_phrase,
    get_action_request,
    get_evidence_mention,
    VIOLATION_EXPRESSIONS,
)
from .templates import (
    get_opening,
    get_context,
    get_transition,
    get_closing,
    get_signature,
    get_subject_line,
    get_consumer_id_intro,
    OPENINGS,
    CLOSINGS,
)
from .bureau_profiles import (
    get_bureau_profile,
    get_bureau_address,
    get_bureau_name,
    get_adjusted_tone,
    get_word_count_range,
    get_preferred_structure,
)
from .validators import (
    UsageTracker,
    LetterValidator,
    get_unique_phrase,
    calculate_quality_score,
)


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class ViolationItem:
    """Represents a single violation to include in the letter."""
    violation_id: str
    violation_type: str
    creditor_name: str
    account_number: Optional[str] = None
    bureau: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LetterConfig:
    """Configuration for letter generation."""
    bureau: str
    tone: str = "conversational"
    consumer_name: Optional[str] = None
    consumer_address: Optional[str] = None
    consumer_ssn_last4: Optional[str] = None
    consumer_dob: Optional[str] = None
    report_id: Optional[str] = None
    consumer_id: Optional[str] = None
    include_fcra: bool = False  # Minimal FCRA citations


@dataclass
class GeneratedLetter:
    """Output of letter generation."""
    content: str
    bureau: str
    bureau_address: str
    violations_included: List[str]
    structure_type: str
    word_count: int
    quality_score: float
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# NARRATIVE STRUCTURE A: FLOWING NARRATIVE
# =============================================================================

class NarrativeStructure:
    """
    Type A: Narrative Flow

    Tells a story about discovering issues. Natural, conversational.
    Good for: TransUnion, Equifax

    Structure:
    - Opening with context about why reviewing
    - Weave violations into a story
    - Natural transitions between accounts
    - Concerned but hopeful closing
    """

    def __init__(self, rng: random.Random, tracker: UsageTracker):
        self.rng = rng
        self.tracker = tracker

    def generate_body(
        self,
        violations: List[ViolationItem],
        tone: str,
        config: LetterConfig
    ) -> str:
        """Generate the letter body using narrative structure."""
        paragraphs = []

        # Opening with optional context
        opening = get_unique_phrase(
            OPENINGS.get(tone, OPENINGS["conversational"]),
            self.tracker,
            self.rng,
            config.consumer_id
        )

        context = get_context(self.rng)
        if context:
            opening_para = f"{context}, {opening.lower()}"
        else:
            opening_para = opening

        paragraphs.append(opening_para)

        # Group violations by creditor for natural flow
        by_creditor = {}
        for v in violations:
            creditor = v.creditor_name or "Unknown"
            if creditor not in by_creditor:
                by_creditor[creditor] = []
            by_creditor[creditor].append(v)

        # Shuffle creditor order for variety
        creditors = list(by_creditor.keys())
        self.rng.shuffle(creditors)

        # Build narrative for each creditor's violations
        first_creditor = True
        for creditor in creditors:
            creditor_violations = by_creditor[creditor]

            para_sentences = []

            if not first_creditor:
                # Add transition
                transition = get_transition("to_next", self.rng)
                para_sentences.append(transition)
            first_creditor = False

            # Reference the account
            first_violation = creditor_violations[0]
            account_ref = get_account_reference(
                first_violation.creditor_name,
                first_violation.account_number,
                self.rng
            )

            # Describe first violation
            expression = get_violation_expression(first_violation.violation_type, self.rng)
            self.tracker.mark_used(expression)

            if len(creditor_violations) == 1:
                para_sentences.append(f"When looking at {account_ref}, {expression.lower()}.")
            else:
                para_sentences.append(f"Looking at {account_ref}, I found several concerns.")
                para_sentences.append(f"First, {expression.lower()}.")

                # Add remaining violations with continuation transitions
                for v in creditor_violations[1:]:
                    continuation = get_transition("continuation", self.rng)
                    expr = get_violation_expression(v.violation_type, self.rng)
                    self.tracker.mark_used(expr)
                    para_sentences.append(f"{continuation} {expr.lower()}.")

            paragraphs.append(" ".join(para_sentences))

        # Add optional FCRA reference (max 1)
        if config.include_fcra and self.rng.random() > 0.7:
            fcra_note = "I understand my rights under the Fair Credit Reporting Act include having accurate information reported."
            paragraphs.append(fcra_note)

        # Closing
        closing = get_unique_phrase(
            CLOSINGS.get(tone, CLOSINGS["conversational"]),
            self.tracker,
            self.rng,
            config.consumer_id
        )
        paragraphs.append(closing)

        return "\n\n".join(paragraphs)


# =============================================================================
# NARRATIVE STRUCTURE B: OBSERVATION STYLE
# =============================================================================

class ObservationStructure:
    """
    Type B: Observation Style

    More analytical, fact-based approach. Points out discrepancies objectively.
    Good for: Experian (more formal), detailed disputes

    Structure:
    - Professional opening
    - State observations clearly
    - Logical flow between issues
    - Request action professionally
    """

    def __init__(self, rng: random.Random, tracker: UsageTracker):
        self.rng = rng
        self.tracker = tracker

    def generate_body(
        self,
        violations: List[ViolationItem],
        tone: str,
        config: LetterConfig
    ) -> str:
        """Generate the letter body using observation structure."""
        paragraphs = []

        # Professional opening
        opening = get_unique_phrase(
            OPENINGS.get(tone, OPENINGS["formal"]),
            self.tracker,
            self.rng,
            config.consumer_id
        )
        paragraphs.append(opening)

        # Group by violation type for logical organization
        by_type = {}
        for v in violations:
            vtype = v.violation_type
            if vtype not in by_type:
                by_type[vtype] = []
            by_type[vtype].append(v)

        # Shuffle types for variety
        types = list(by_type.keys())
        self.rng.shuffle(types)

        # Build observations
        observation_intro = self.rng.choice([
            "Upon reviewing my credit report, I observed the following:",
            "My review revealed these specific concerns:",
            "I have identified the following issues requiring attention:",
            "The following observations require your investigation:",
        ])
        paragraphs.append(observation_intro)

        observations = []
        for vtype in types:
            type_violations = by_type[vtype]

            for v in type_violations:
                # Get expression
                expression = get_violation_expression(v.violation_type, self.rng)
                self.tracker.mark_used(expression)

                # Create observation sentence
                account_ref = get_account_reference(
                    v.creditor_name,
                    v.account_number,
                    self.rng
                )

                observation = f"Regarding {account_ref}: {expression}."

                # Sometimes add confidence phrase
                if self.rng.random() > 0.6:
                    confidence = get_confidence_phrase(self.rng)
                    observation = f"Regarding {account_ref}: {expression}. {confidence}."

                observations.append(observation)

        # Join observations as flowing prose (not bullets!)
        if len(observations) <= 3:
            # Short list - one paragraph
            paragraphs.append(" ".join(observations))
        else:
            # Longer list - split into two paragraphs
            mid = len(observations) // 2
            paragraphs.append(" ".join(observations[:mid]))

            transition = self.rng.choice([
                "Furthermore, I also noted",
                "In addition to the above",
                "I also observed",
                "My review also revealed",
            ])
            paragraphs.append(f"{transition}: {' '.join(observations[mid:])}")

        # Action request
        action = get_action_request(self.rng)
        paragraphs.append(action)

        # Closing
        closing = get_unique_phrase(
            CLOSINGS.get(tone, CLOSINGS["formal"]),
            self.tracker,
            self.rng,
            config.consumer_id
        )
        paragraphs.append(closing)

        return "\n\n".join(paragraphs)


# =============================================================================
# NARRATIVE STRUCTURE C: QUESTION-BASED
# =============================================================================

class QuestionStructure:
    """
    Type C: Question-Based

    Frames issues as genuine questions. Very human, non-confrontational.
    Great for: Any bureau, good variation option

    Structure:
    - Confused/concerned opening
    - Ask questions about each issue
    - Show genuine desire to understand
    - Politely request resolution
    """

    QUESTION_TEMPLATES = [
        "I'm confused about {account} - {issue}?",
        "Can you help me understand why {account} shows {issue}?",
        "I noticed {account} has something that doesn't seem right: {issue}. Is this correct?",
        "Looking at {account}, I see {issue}. Could this be an error?",
        "I'm wondering about {account}. {issue} - is this supposed to be this way?",
        "Why does {account} show {issue}? This doesn't match my records.",
        "Could you please check {account}? {issue} and I'm not sure why.",
        "I don't understand something about {account}. {issue} - can you explain?",
    ]

    def __init__(self, rng: random.Random, tracker: UsageTracker):
        self.rng = rng
        self.tracker = tracker

    def generate_body(
        self,
        violations: List[ViolationItem],
        tone: str,
        config: LetterConfig
    ) -> str:
        """Generate the letter body using question structure."""
        paragraphs = []

        # Confused/concerned opening
        question_openings = [
            "I've been looking at my credit report and have some questions about what I'm seeing.",
            "I'm writing because I found some things on my credit report that I don't understand.",
            "After reviewing my credit report, I have several questions I hope you can help me with.",
            "I recently checked my credit and found some things that are confusing to me.",
            "I'm a bit confused about some items on my credit report and hoping you can help.",
        ]

        opening = self.rng.choice(question_openings)
        paragraphs.append(opening)

        # Shuffle violations for variety
        shuffled_violations = violations.copy()
        self.rng.shuffle(shuffled_violations)

        # Generate questions for each violation
        questions = []
        for v in shuffled_violations:
            account_ref = get_account_reference(
                v.creditor_name,
                v.account_number,
                self.rng
            )

            # Get violation expression and convert to question issue
            expression = get_violation_expression(v.violation_type, self.rng)
            self.tracker.mark_used(expression)

            # Simplify expression for question format
            issue = expression.lower()
            if issue.startswith("i "):
                issue = issue[2:]  # Remove "I " prefix
            if issue.startswith("this account "):
                issue = issue[13:]  # Remove "This account" prefix

            # Choose question template
            template = self.rng.choice(self.QUESTION_TEMPLATES)
            question = template.format(account=account_ref, issue=issue)
            questions.append(question)

        # Group questions into paragraphs (2-3 per paragraph)
        for i in range(0, len(questions), 2):
            chunk = questions[i:i+2]
            paragraphs.append(" ".join(chunk))

        # Polite request
        request_phrases = [
            "I would really appreciate it if you could look into these questions for me.",
            "Could you please investigate these items and let me know what you find?",
            "I'm hoping you can help me understand these issues and correct any errors.",
            "I'd be grateful if you could check on these things and get back to me.",
            "Would it be possible to have someone review these items?",
        ]
        paragraphs.append(self.rng.choice(request_phrases))

        # Closing
        closing = get_unique_phrase(
            CLOSINGS.get(tone, CLOSINGS["conversational"]),
            self.tracker,
            self.rng,
            config.consumer_id
        )
        paragraphs.append(closing)

        return "\n\n".join(paragraphs)


# =============================================================================
# MAIN ASSEMBLER
# =============================================================================

class LetterAssembler:
    """
    Main orchestrator for generating dispute letters.

    Features:
    - Selects narrative structure based on bureau/preferences
    - Manages phrase rotation
    - Validates output quality
    - Ensures variety across letters
    """

    STRUCTURES = {
        "narrative": NarrativeStructure,
        "observation": ObservationStructure,
        "question": QuestionStructure,
    }

    def __init__(self, seed: Optional[int] = None):
        """Initialize assembler with optional seed for determinism."""
        self.seed = seed or random.randint(0, 2**32)
        self.rng = random.Random(self.seed)
        self.tracker = UsageTracker()
        self.validator = LetterValidator()

    def _create_seed_from_report(self, report_id: str) -> int:
        """Create deterministic seed from report ID."""
        hash_bytes = hashlib.md5(report_id.encode()).digest()
        return int.from_bytes(hash_bytes[:4], byteorder='big')

    def _select_structure(self, config: LetterConfig) -> str:
        """Select narrative structure based on bureau and preferences."""
        bureau = config.bureau.lower()

        # Get bureau's preferred structure
        preferred = get_preferred_structure(bureau)

        # Add some randomness (30% chance of different structure)
        if self.rng.random() > 0.7:
            all_structures = list(self.STRUCTURES.keys())
            return self.rng.choice(all_structures)

        return preferred

    def _build_header(self, config: LetterConfig) -> str:
        """Build letter header with consumer info and bureau address."""
        lines = []

        # Date
        today = date.today()
        lines.append(today.strftime("%B %d, %Y"))
        lines.append("")

        # Bureau address
        bureau_address = get_bureau_address(config.bureau)
        lines.append(bureau_address)
        lines.append("")

        # Subject line
        subject = get_subject_line(self.rng)
        lines.append(subject)
        lines.append("")

        # Consumer identification (if provided)
        if config.consumer_name:
            id_intro = get_consumer_id_intro(self.rng)
            lines.append(id_intro)
            lines.append(f"Name: {config.consumer_name}")

            if config.consumer_address:
                lines.append(f"Address: {config.consumer_address}")

            if config.consumer_ssn_last4:
                lines.append(f"SSN (last 4): XXX-XX-{config.consumer_ssn_last4}")

            if config.consumer_dob:
                lines.append(f"Date of Birth: {config.consumer_dob}")

            lines.append("")

        return "\n".join(lines)

    def _build_signature(self, config: LetterConfig) -> str:
        """Build letter signature block."""
        lines = []

        signature = get_signature(self.rng)
        lines.append(signature)
        lines.append("")

        if config.consumer_name:
            lines.append(config.consumer_name)

        return "\n".join(lines)

    def generate(
        self,
        violations: List[ViolationItem],
        config: LetterConfig,
        force_structure: Optional[str] = None
    ) -> GeneratedLetter:
        """
        Generate a complete dispute letter.

        Args:
            violations: List of violations to include
            config: Letter configuration
            force_structure: Optional override for structure type

        Returns:
            GeneratedLetter with content and metadata
        """
        # Set up deterministic seed if report_id provided
        if config.report_id:
            self.seed = self._create_seed_from_report(config.report_id)
            self.rng = random.Random(self.seed)

        # Adjust tone for bureau
        adjusted_tone = get_adjusted_tone(config.bureau, config.tone)

        # Select structure
        structure_type = force_structure or self._select_structure(config)

        # Create structure instance
        structure_class = self.STRUCTURES.get(structure_type, NarrativeStructure)
        structure = structure_class(self.rng, self.tracker)

        # Generate body
        body = structure.generate_body(violations, adjusted_tone, config)

        # Build complete letter
        header = self._build_header(config)
        signature = self._build_signature(config)

        full_content = f"{header}\n{body}\n\n{signature}"

        # Validate
        word_min, word_max = get_word_count_range(config.bureau)
        validation = self.validator.validate(
            body,
            min_words=word_min,
            max_words=word_max
        )

        quality_score = calculate_quality_score(validation)

        # Finalize tracking for this letter
        self.tracker.finalize_letter(config.consumer_id)

        return GeneratedLetter(
            content=full_content,
            bureau=config.bureau,
            bureau_address=get_bureau_address(config.bureau),
            violations_included=[v.violation_id for v in violations],
            structure_type=structure_type,
            word_count=validation["word_count"],
            quality_score=quality_score,
            metadata={
                "seed": self.seed,
                "tone": adjusted_tone,
                "validation": validation,
            }
        )

    def generate_multi_bureau(
        self,
        violations: List[ViolationItem],
        bureaus: List[str],
        base_config: LetterConfig
    ) -> Dict[str, GeneratedLetter]:
        """
        Generate letters for multiple bureaus.

        Creates varied letters for each bureau with different structures.
        """
        letters = {}

        # Ensure different structures for each bureau
        used_structures = []

        for bureau in bureaus:
            config = LetterConfig(
                bureau=bureau,
                tone=base_config.tone,
                consumer_name=base_config.consumer_name,
                consumer_address=base_config.consumer_address,
                consumer_ssn_last4=base_config.consumer_ssn_last4,
                consumer_dob=base_config.consumer_dob,
                report_id=base_config.report_id,
                consumer_id=base_config.consumer_id,
                include_fcra=base_config.include_fcra,
            )

            # Try to use different structure than previous bureaus
            available_structures = [s for s in self.STRUCTURES.keys()
                                    if s not in used_structures]

            if not available_structures:
                available_structures = list(self.STRUCTURES.keys())

            force_structure = self.rng.choice(available_structures)
            used_structures.append(force_structure)

            letters[bureau] = self.generate(
                violations,
                config,
                force_structure=force_structure
            )

        return letters


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def generate_letter(
    violations: List[Dict[str, Any]],
    bureau: str,
    tone: str = "conversational",
    consumer_name: Optional[str] = None,
    consumer_address: Optional[str] = None,
    report_id: Optional[str] = None,
    consumer_id: Optional[str] = None,
) -> GeneratedLetter:
    """
    Convenience function to generate a single letter.

    Args:
        violations: List of violation dictionaries
        bureau: Target bureau (transunion, experian, equifax)
        tone: Letter tone (formal, assertive, conversational, narrative)
        consumer_name: Optional consumer name for header
        consumer_address: Optional address for header
        report_id: Optional report ID for seed
        consumer_id: Optional consumer ID for phrase tracking

    Returns:
        GeneratedLetter object
    """
    # Convert dictionaries to ViolationItem objects
    violation_items = [
        ViolationItem(
            violation_id=v.get("violation_id", str(i)),
            violation_type=v.get("violation_type", "unknown"),
            creditor_name=v.get("creditor_name", "Unknown"),
            account_number=v.get("account_number"),
            bureau=v.get("bureau"),
            details=v.get("details", {}),
        )
        for i, v in enumerate(violations)
    ]

    config = LetterConfig(
        bureau=bureau,
        tone=tone,
        consumer_name=consumer_name,
        consumer_address=consumer_address,
        report_id=report_id,
        consumer_id=consumer_id,
    )

    assembler = LetterAssembler()
    return assembler.generate(violation_items, config)


def get_available_tones() -> List[Dict[str, str]]:
    """Get list of available tones with descriptions."""
    return [
        {
            "id": "conversational",
            "name": "Conversational",
            "description": "Friendly, approachable tone like talking to a neighbor"
        },
        {
            "id": "formal",
            "name": "Professional",
            "description": "Business-like tone suitable for official correspondence"
        },
        {
            "id": "assertive",
            "name": "Assertive",
            "description": "Direct and firm tone that emphasizes your rights"
        },
        {
            "id": "narrative",
            "name": "Narrative",
            "description": "Story-telling approach that explains your situation"
        },
    ]


def get_available_structures() -> List[Dict[str, str]]:
    """Get list of available narrative structures."""
    return [
        {
            "id": "narrative",
            "name": "Narrative Flow",
            "description": "Story-telling approach that weaves issues together"
        },
        {
            "id": "observation",
            "name": "Observation Style",
            "description": "Analytical approach that presents findings objectively"
        },
        {
            "id": "question",
            "name": "Question-Based",
            "description": "Curious approach that asks questions about discrepancies"
        },
    ]
