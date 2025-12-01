"""
Legal Letter Generator - Tone Modules

Contains 4 legal tones for formal dispute letters.

NOTE: Civil tones are DEPRECATED in this module. Use the new
civil_letter_generator package instead, which provides:
- CivilAssembler v2 with domain isolation
- CivilMask to prevent legal term contamination
- Structured output with SWEEP-D compliance metadata

Migration path:
  OLD: from ..legal_letter_generator.tones import CivilConversationalTone
  NEW: from ..civil_letter_generator import generate_civil_letter

Civil tones are still exported for backward compatibility but will
be removed in a future version.
"""
import warnings

# Legal tones (ACTIVE)
from .strict_legal import StrictLegalTone
from .professional import ProfessionalTone
from .soft_legal import SoftLegalTone
from .aggressive import AggressiveTone

# Civil tones (DEPRECATED - use civil_letter_generator instead)
from .civil_conversational import CivilConversationalTone
from .civil_professional import CivilProfessionalTone
from .civil_assertive import CivilAssertiveTone
from .civil_narrative import CivilNarrativeTone

# Issue deprecation warning when civil tones are used
def _deprecated_civil_tone_warning(tone_name: str):
    warnings.warn(
        f"{tone_name} is deprecated in legal_letter_generator. "
        "Use civil_letter_generator.generate_civil_letter() instead. "
        "This tone will be removed in a future version.",
        DeprecationWarning,
        stacklevel=3
    )

__all__ = [
    # Legal tones
    "StrictLegalTone",
    "ProfessionalTone",
    "SoftLegalTone",
    "AggressiveTone",
    # Civil tones
    "CivilConversationalTone",
    "CivilProfessionalTone",
    "CivilAssertiveTone",
    "CivilNarrativeTone",
    # Registry and helpers
    "TONE_REGISTRY",
    "LEGAL_TONES",
    "CIVIL_TONES",
    "get_tone_class",
    "get_tone_engine",
    "list_tones",
    "list_legal_tones",
    "list_civil_tones",
    "is_legal_tone",
    "is_civil_tone",
]

# Legal tone registry (require FCRA citations, case law, MOV)
LEGAL_TONES = {
    "strict_legal": StrictLegalTone,
    "professional": ProfessionalTone,
    "soft_legal": SoftLegalTone,
    "aggressive": AggressiveTone,
}

# Civil tone registry (forbidden: legal terms, case law, MOV)
CIVIL_TONES = {
    "conversational": CivilConversationalTone,
    "civil_professional": CivilProfessionalTone,
    "assertive": CivilAssertiveTone,
    "narrative": CivilNarrativeTone,
    # Aliases for backward compatibility
    "formal": CivilProfessionalTone,
}

# Combined registry
TONE_REGISTRY = {**LEGAL_TONES, **CIVIL_TONES}


def get_tone_engine(tone: str):
    """Get the appropriate tone engine class."""
    return TONE_REGISTRY.get(tone, ProfessionalTone)


# Alias for backward compatibility
get_tone_class = get_tone_engine


def is_legal_tone(tone: str) -> bool:
    """Check if a tone is a legal tone."""
    return tone in LEGAL_TONES


def is_civil_tone(tone: str) -> bool:
    """Check if a tone is a civil tone."""
    return tone in CIVIL_TONES


def list_tones():
    """List all available tones with metadata."""
    tones = []
    for name, tone_class in TONE_REGISTRY.items():
        # Skip aliases
        if name == "formal":
            continue
        tones.append({
            "name": name,
            "description": getattr(tone_class, "description", name.replace("_", " ").title()),
            "formality_level": getattr(tone_class, "formality_level", 5),
            "letter_type": "legal" if name in LEGAL_TONES else "civil",
        })
    return tones


def list_legal_tones():
    """List legal tones with metadata."""
    tones = []
    for name, tone_class in LEGAL_TONES.items():
        tones.append({
            "name": name,
            "description": getattr(tone_class, "description", name.replace("_", " ").title()),
            "formality_level": getattr(tone_class, "formality_level", 5),
            "letter_type": "legal",
            "includes_case_law": getattr(tone_class.config, "include_case_law", True),
            "citation_density": getattr(tone_class.config, "citation_density", "moderate"),
        })
    return tones


def list_civil_tones():
    """
    List civil tones with metadata.

    DEPRECATED: Use civil_letter_generator.get_civil_tones() instead.
    This function is maintained for backward compatibility only.
    """
    warnings.warn(
        "list_civil_tones() is deprecated. Use civil_letter_generator.get_civil_tones() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    tones = []
    for name, tone_class in CIVIL_TONES.items():
        # Skip aliases
        if name == "formal":
            continue
        tones.append({
            "name": name,
            "description": getattr(tone_class, "description", name.replace("_", " ").title()),
            "formality_level": getattr(tone_class, "formality_level", 5),
            "letter_type": "civil",
            "includes_case_law": False,
            "citation_density": "none",
            "deprecated": True,
            "migration_path": "Use civil_letter_generator.generate_civil_letter()",
        })
    return tones
