"""
Legal Letter Generator Module

A comprehensive legal dispute letter generator with:
- Multiple tone engines (strict_legal, professional, soft_legal, aggressive)
- Grouping strategies (by FCRA section, Metro-2 field, creditor, severity)
- Metro-2 format explanations
- Case law citations
- Method of Verification (MOV) requirements
- Seeded phrase variation for deterministic output

Usage:
    from app.services.legal_letter_generator import generate_legal_letter

    result = generate_legal_letter(
        violations=[
            {
                "creditor_name": "Example Bank",
                "account_number_masked": "XXXX1234",
                "violation_type": "balance_error",
                "fcra_section": "611",
                "evidence": "Balance reported incorrectly",
            }
        ],
        consumer={"name": "John Doe", "address": "123 Main St"},
        bureau="transunion",
        tone="professional",
        grouping_strategy="by_fcra_section",
    )

    letter_content = result["letter"]
    is_valid = result["is_valid"]
"""

# Main assembler and convenience function
from .legal_assembler import (
    LegalLetterAssembler,
    generate_legal_letter,
    BUREAU_ADDRESSES,
)

# Grouping strategies
from .grouping_strategies import (
    GroupingStrategy,
    LegalGrouper,
    FCRA_SECTIONS,
    METRO2_FIELD_CATEGORIES,
)

# Metro-2 explanations
from .metro2_explanations import (
    Metro2FieldExplanation,
    Metro2ExplanationBuilder,
    METRO2_FIELDS,
)

# Case law
from .case_law import (
    CaseLawCitation,
    CaseLawLibrary,
    CaseLawCitationBuilder,
    STANDARD_REINVESTIGATION_CITE,
    STANDARD_ACCURACY_CITE,
    STANDARD_OBSOLESCENCE_CITE,
)

# MOV requirements
from .mov_requirements import (
    MOVRequirement,
    MOVBuilder,
    MOV_REQUIREMENTS,
)

# Validators
from .validators_legal import (
    ValidationLevel,
    ValidationIssue,
    LegalLetterValidator,
    LetterContentValidator,
)

# Tone engines
from .tones import (
    TONE_REGISTRY,
    get_tone_class,
    list_tones,
)

__all__ = [
    # Main exports
    "LegalLetterAssembler",
    "generate_legal_letter",
    "BUREAU_ADDRESSES",
    # Grouping
    "GroupingStrategy",
    "LegalGrouper",
    "FCRA_SECTIONS",
    "METRO2_FIELD_CATEGORIES",
    # Metro-2
    "Metro2FieldExplanation",
    "Metro2ExplanationBuilder",
    "METRO2_FIELDS",
    # Case law
    "CaseLawCitation",
    "CaseLawLibrary",
    "CaseLawCitationBuilder",
    "STANDARD_REINVESTIGATION_CITE",
    "STANDARD_ACCURACY_CITE",
    "STANDARD_OBSOLESCENCE_CITE",
    # MOV
    "MOVRequirement",
    "MOVBuilder",
    "MOV_REQUIREMENTS",
    # Validators
    "ValidationLevel",
    "ValidationIssue",
    "LegalLetterValidator",
    "LetterContentValidator",
    # Tones
    "TONE_REGISTRY",
    "get_tone_class",
    "list_tones",
]
