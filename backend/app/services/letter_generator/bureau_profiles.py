"""
Credit Copilot - Bureau-Specific Profiles

Each credit bureau has different characteristics that influence
how letters should be written for maximum effectiveness.
"""
from typing import Dict, Any


# =============================================================================
# BUREAU PROFILES
# =============================================================================

BUREAU_PROFILES: Dict[str, Dict[str, Any]] = {
    "transunion": {
        "name": "TransUnion",
        "full_name": "TransUnion Consumer Solutions",
        "address": """TransUnion Consumer Solutions
P.O. Box 2000
Chester, PA 19016-2000""",
        "formality_level": "moderate",
        "preferred_tone": "straightforward",
        "word_count_range": (250, 400),
        "preferred_structure": "narrative",
        "bureau_specific_notes": [
            "TransUnion uses a highly automated dispute system",
            "Clear, concise language works best",
            "They respond well to specific data point references",
        ],
    },

    "experian": {
        "name": "Experian",
        "full_name": "Experian",
        "address": """Experian
P.O. Box 4500
Allen, TX 75013""",
        "formality_level": "slightly_formal",
        "preferred_tone": "collaborative",
        "word_count_range": (300, 450),
        "preferred_structure": "observation",
        "bureau_specific_notes": [
            "Experian has strict processing guidelines",
            "Detailed explanations can help",
            "Reference specific fields when possible",
        ],
    },

    "equifax": {
        "name": "Equifax",
        "full_name": "Equifax Information Services LLC",
        "address": """Equifax Information Services LLC
P.O. Box 740256
Atlanta, GA 30374-0256""",
        "formality_level": "moderate",
        "preferred_tone": "concerned",
        "word_count_range": (250, 400),
        "preferred_structure": "narrative",
        "bureau_specific_notes": [
            "Equifax processes disputes systematically",
            "Consumer-focused language is effective",
            "Express genuine concern about impact",
        ],
    },
}


# =============================================================================
# TONE MAPPINGS BASED ON BUREAU
# =============================================================================

BUREAU_TONE_PREFERENCES = {
    "transunion": {
        "formal": "formal",
        "assertive": "assertive",
        "conversational": "conversational",
        "narrative": "narrative",
    },
    "experian": {
        "formal": "formal",
        "assertive": "formal",  # Tone down assertive for Experian
        "conversational": "conversational",
        "narrative": "conversational",
    },
    "equifax": {
        "formal": "formal",
        "assertive": "assertive",
        "conversational": "narrative",  # Equifax responds to narrative
        "narrative": "narrative",
    },
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_bureau_profile(bureau: str) -> Dict[str, Any]:
    """Get the profile for a specific bureau."""
    bureau_key = bureau.lower()
    return BUREAU_PROFILES.get(bureau_key, BUREAU_PROFILES["transunion"])


def get_bureau_address(bureau: str) -> str:
    """Get the mailing address for a bureau."""
    profile = get_bureau_profile(bureau)
    return profile.get("address", "")


def get_bureau_name(bureau: str) -> str:
    """Get the display name for a bureau."""
    profile = get_bureau_profile(bureau)
    return profile.get("name", bureau.title())


def get_adjusted_tone(bureau: str, requested_tone: str) -> str:
    """
    Adjust the tone based on bureau preferences.
    Some bureaus respond better to certain tones.
    """
    bureau_key = bureau.lower()
    tone_map = BUREAU_TONE_PREFERENCES.get(bureau_key, {})
    return tone_map.get(requested_tone, requested_tone)


def get_word_count_range(bureau: str) -> tuple:
    """Get the preferred word count range for a bureau."""
    profile = get_bureau_profile(bureau)
    return profile.get("word_count_range", (250, 400))


def get_preferred_structure(bureau: str) -> str:
    """Get the preferred letter structure for a bureau."""
    profile = get_bureau_profile(bureau)
    return profile.get("preferred_structure", "narrative")
