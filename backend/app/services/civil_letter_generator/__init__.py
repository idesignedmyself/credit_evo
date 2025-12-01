"""
Civil Letter Generator Package

Domain-isolated civil letter generation system.
All civil letters are generated through CivilAssembler v2 which:
- Wraps the existing Credit Copilot LetterAssembler
- Applies civil mask for domain isolation
- Provides structured output with metadata
- Supports grouping strategies matching the legal generator
- Includes SWEEP-D compliance metadata
"""

from .civil_mask import (
    CivilMask,
    MaskResult,
    LetterDomain,
    apply_civil_mask,
    validate_civil_content,
)

from .structure import (
    CivilSection,
    SectionSpec,
    StructuredSection,
    CivilLetterStructure,
    CivilStructureBuilder,
    StructureValidator,
    create_civil_structure,
    get_structure_metadata,
    CIVIL_SECTION_SPECS,
)

from .tone_engine import (
    CivilTone,
    ToneConfig,
    CivilToneEngine,
    resolve_tone,
    is_civil_tone,
    get_civil_tones,
    create_tone_engine,
    TONE_CONFIGS,
    CIVIL_TONE_ALIASES,
)

from .civil_assembler import (
    CivilViolation,
    CivilLetterConfig,
    CivilLetterResult,
    CivilAssembler,
    generate_civil_letter,
    create_civil_assembler,
    get_available_civil_tones,
    get_civil_grouping_strategies,
)


__all__ = [
    # Civil Mask
    "CivilMask",
    "MaskResult",
    "LetterDomain",
    "apply_civil_mask",
    "validate_civil_content",
    # Structure
    "CivilSection",
    "SectionSpec",
    "StructuredSection",
    "CivilLetterStructure",
    "CivilStructureBuilder",
    "StructureValidator",
    "create_civil_structure",
    "get_structure_metadata",
    "CIVIL_SECTION_SPECS",
    # Tone Engine
    "CivilTone",
    "ToneConfig",
    "CivilToneEngine",
    "resolve_tone",
    "is_civil_tone",
    "get_civil_tones",
    "create_tone_engine",
    "TONE_CONFIGS",
    "CIVIL_TONE_ALIASES",
    # Civil Assembler
    "CivilViolation",
    "CivilLetterConfig",
    "CivilLetterResult",
    "CivilAssembler",
    "generate_civil_letter",
    "create_civil_assembler",
    "get_available_civil_tones",
    "get_civil_grouping_strategies",
]
