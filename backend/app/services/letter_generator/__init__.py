"""
Credit Copilot - Human-Language Dispute Letter Generator

A sophisticated letter generation system designed to:
- Produce natural, human-sounding dispute letters
- Avoid template detection markers (eOscar filtering)
- Provide 8-10 variations per violation type
- Support multiple narrative structures
- Customize for each bureau's preferences
- Track phrase usage to prevent repetition

Usage:
    from app.services.letter_generator import generate_letter, LetterConfig

    letter = generate_letter(
        violations=[
            {"violation_type": "missing_dofd", "creditor_name": "Bank ABC"},
            {"violation_type": "stale_reporting", "creditor_name": "Credit Co"},
        ],
        bureau="transunion",
        tone="conversational",
    )

    print(letter.content)
"""

# Main assembler and generation
from .assembler import (
    LetterAssembler,
    LetterConfig,
    ViolationItem,
    GeneratedLetter,
    generate_letter,
    get_available_tones,
    get_available_structures,
)

# Narrative structures
from .assembler import (
    NarrativeStructure,
    ObservationStructure,
    QuestionStructure,
)

# Validation and tracking
from .validators import (
    UsageTracker,
    LetterValidator,
    calculate_quality_score,
    calculate_variation_score,
    get_unique_phrase,
    ensure_minimum_variation,
)

# Template seeds
from .templates import (
    OPENINGS,
    CLOSINGS,
    TRANSITIONS,
    CONTEXT_SEEDS,
    SIGNATURES,
    SUBJECT_LINES,
    get_opening,
    get_closing,
    get_transition,
    get_context,
    get_signature,
    get_subject_line,
)

# Violation expressions
from .expressions import (
    VIOLATION_EXPRESSIONS,
    ACCOUNT_REFERENCES,
    CONFIDENCE_PHRASES,
    ACTION_REQUESTS,
    get_violation_expression,
    get_account_reference,
    get_confidence_phrase,
    get_action_request,
    get_evidence_mention,
)

# Bureau profiles
from .bureau_profiles import (
    BUREAU_PROFILES,
    BUREAU_TONE_PREFERENCES,
    get_bureau_profile,
    get_bureau_address,
    get_bureau_name,
    get_adjusted_tone,
    get_word_count_range,
    get_preferred_structure,
)

__all__ = [
    # Main generation
    "LetterAssembler",
    "LetterConfig",
    "ViolationItem",
    "GeneratedLetter",
    "generate_letter",
    "get_available_tones",
    "get_available_structures",
    # Structures
    "NarrativeStructure",
    "ObservationStructure",
    "QuestionStructure",
    # Validation
    "UsageTracker",
    "LetterValidator",
    "calculate_quality_score",
    "calculate_variation_score",
    "get_unique_phrase",
    "ensure_minimum_variation",
    # Templates
    "OPENINGS",
    "CLOSINGS",
    "TRANSITIONS",
    "CONTEXT_SEEDS",
    "SIGNATURES",
    "SUBJECT_LINES",
    "get_opening",
    "get_closing",
    "get_transition",
    "get_context",
    "get_signature",
    "get_subject_line",
    # Expressions
    "VIOLATION_EXPRESSIONS",
    "ACCOUNT_REFERENCES",
    "CONFIDENCE_PHRASES",
    "ACTION_REQUESTS",
    "get_violation_expression",
    "get_account_reference",
    "get_confidence_phrase",
    "get_action_request",
    "get_evidence_mention",
    # Bureau profiles
    "BUREAU_PROFILES",
    "BUREAU_TONE_PREFERENCES",
    "get_bureau_profile",
    "get_bureau_address",
    "get_bureau_name",
    "get_adjusted_tone",
    "get_word_count_range",
    "get_preferred_structure",
]
