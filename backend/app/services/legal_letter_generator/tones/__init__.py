"""
Legal Letter Generator - Tone Modules
Four distinct tone engines for legal dispute letters.
"""
from .strict_legal import StrictLegalTone
from .professional import ProfessionalTone
from .soft_legal import SoftLegalTone
from .aggressive import AggressiveTone

__all__ = [
    "StrictLegalTone",
    "ProfessionalTone",
    "SoftLegalTone",
    "AggressiveTone",
    "TONE_REGISTRY",
    "get_tone_class",
    "get_tone_engine",
    "list_tones",
]

TONE_REGISTRY = {
    "strict_legal": StrictLegalTone,
    "professional": ProfessionalTone,
    "soft_legal": SoftLegalTone,
    "aggressive": AggressiveTone,
}


def get_tone_engine(tone: str):
    """Get the appropriate tone engine class."""
    return TONE_REGISTRY.get(tone, ProfessionalTone)


# Alias for backward compatibility
get_tone_class = get_tone_engine


def list_tones():
    """List available tones with metadata."""
    tones = []
    for name, tone_class in TONE_REGISTRY.items():
        tones.append({
            "name": name,
            "description": getattr(tone_class, "description", name.replace("_", " ").title()),
            "formality_level": getattr(tone_class, "formality_level", 5),
        })
    return tones
