"""
Civil Letter Generator - Tone Engine

Handles civil tone variations: conversational, formal, assertive, narrative.
All tones produce human-friendly, accessible letters without legal jargon.
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import random


class CivilTone(Enum):
    """Available civil tone types."""
    CONVERSATIONAL = "conversational"
    FORMAL = "formal"
    ASSERTIVE = "assertive"
    NARRATIVE = "narrative"


# Aliases for backward compatibility
CIVIL_TONE_ALIASES = {
    "civil_professional": CivilTone.FORMAL,
    "civil_conversational": CivilTone.CONVERSATIONAL,
    "civil_assertive": CivilTone.ASSERTIVE,
    "civil_narrative": CivilTone.NARRATIVE,
}


@dataclass
class ToneConfig:
    """Configuration for a civil tone."""
    tone: CivilTone
    formality_level: int  # 1-10 scale
    warmth_level: int  # 1-10 scale
    directness_level: int  # 1-10 scale
    description: str


# Tone configurations
TONE_CONFIGS: Dict[CivilTone, ToneConfig] = {
    CivilTone.CONVERSATIONAL: ToneConfig(
        tone=CivilTone.CONVERSATIONAL,
        formality_level=3,
        warmth_level=9,
        directness_level=5,
        description="Friendly, approachable language for first-time disputes",
    ),
    CivilTone.FORMAL: ToneConfig(
        tone=CivilTone.FORMAL,
        formality_level=7,
        warmth_level=5,
        directness_level=6,
        description="Professional, businesslike tone for formal correspondence",
    ),
    CivilTone.ASSERTIVE: ToneConfig(
        tone=CivilTone.ASSERTIVE,
        formality_level=6,
        warmth_level=4,
        directness_level=9,
        description="Direct and firm tone that emphasizes your concerns",
    ),
    CivilTone.NARRATIVE: ToneConfig(
        tone=CivilTone.NARRATIVE,
        formality_level=4,
        warmth_level=7,
        directness_level=4,
        description="Story-telling approach that explains your situation",
    ),
}


class CivilToneEngine:
    """
    Engine for generating tone-appropriate civil letter content.

    Features:
    - Phrase pools specific to each tone
    - Greeting/closing variations
    - Seed-based deterministic selection
    """

    # Greetings by tone
    GREETINGS: Dict[CivilTone, List[str]] = {
        CivilTone.CONVERSATIONAL: [
            "Dear Credit Bureau Team,",
            "Hello,",
            "Hi there,",
            "Dear Sir or Madam,",
        ],
        CivilTone.FORMAL: [
            "Dear Sir or Madam,",
            "To Whom It May Concern,",
            "Dear Credit Bureau Representative,",
            "Dear Dispute Department,",
        ],
        CivilTone.ASSERTIVE: [
            "To Whom It May Concern,",
            "Attention: Dispute Department,",
            "Dear Credit Bureau,",
            "Dear Sir or Madam,",
        ],
        CivilTone.NARRATIVE: [
            "Dear Reader,",
            "Hello,",
            "Dear Credit Bureau Representative,",
            "Dear Sir or Madam,",
        ],
    }

    # Opening phrases by tone
    OPENINGS: Dict[CivilTone, List[str]] = {
        CivilTone.CONVERSATIONAL: [
            "I'm writing to you today because I found some things on my credit report that don't look right.",
            "I recently checked my credit report and noticed a few items that seem incorrect.",
            "I'm reaching out because I spotted some errors on my credit file that I'd like help with.",
            "I was reviewing my credit report and found some information that needs to be corrected.",
        ],
        CivilTone.FORMAL: [
            "I am writing to formally dispute certain information contained in my credit file.",
            "This letter serves as a formal request to review and correct errors in my credit report.",
            "I am contacting you to address inaccuracies that I have identified in my credit report.",
            "I wish to bring to your attention several errors that appear on my credit file.",
        ],
        CivilTone.ASSERTIVE: [
            "I am writing to dispute inaccurate information on my credit report that requires immediate attention.",
            "I have identified errors in my credit file that must be corrected without delay.",
            "This letter is to formally notify you of inaccurate information that needs to be removed from my credit report.",
            "I am demanding that you investigate and correct the following errors on my credit report.",
        ],
        CivilTone.NARRATIVE: [
            "Let me tell you about a problem I've been dealing with regarding my credit report.",
            "I want to share with you a situation that has been affecting my credit history.",
            "I'd like to explain what happened and why I believe there are errors on my credit report.",
            "Here's my story about the inaccurate information that has appeared on my credit file.",
        ],
    }

    # Closing phrases by tone
    CLOSINGS: Dict[CivilTone, List[str]] = {
        CivilTone.CONVERSATIONAL: [
            "Thanks so much for looking into this for me!",
            "I really appreciate your help with this matter.",
            "Thank you for taking the time to review my concerns.",
            "I'm grateful for your assistance in correcting these errors.",
        ],
        CivilTone.FORMAL: [
            "Thank you for your prompt attention to this matter.",
            "I appreciate your assistance in resolving these issues.",
            "I look forward to receiving confirmation of the corrections.",
            "Thank you for your cooperation in addressing these concerns.",
        ],
        CivilTone.ASSERTIVE: [
            "I expect these issues to be resolved within the required timeframe.",
            "Please ensure these errors are corrected promptly.",
            "I will follow up if I do not receive a response within 30 days.",
            "I trust you will take immediate action on this matter.",
        ],
        CivilTone.NARRATIVE: [
            "I hope this letter helps you understand my situation and why these corrections are important to me.",
            "Thank you for reading my story and for your help in setting things right.",
            "I appreciate you taking the time to understand what happened and correct these errors.",
            "I'm hopeful that sharing my experience will lead to the corrections I need.",
        ],
    }

    # Signatures by tone
    SIGNATURES: Dict[CivilTone, List[str]] = {
        CivilTone.CONVERSATIONAL: [
            "Best regards,",
            "Thanks again,",
            "Warmly,",
            "Take care,",
        ],
        CivilTone.FORMAL: [
            "Sincerely,",
            "Respectfully,",
            "Best regards,",
            "Yours truly,",
        ],
        CivilTone.ASSERTIVE: [
            "Respectfully,",
            "Sincerely,",
            "Regards,",
            "Cordially,",
        ],
        CivilTone.NARRATIVE: [
            "Sincerely,",
            "With appreciation,",
            "Best wishes,",
            "Warmly,",
        ],
    }

    # Subject lines by tone
    SUBJECTS: Dict[CivilTone, List[str]] = {
        CivilTone.CONVERSATIONAL: [
            "RE: Help Needed - Errors on My Credit Report",
            "RE: Requesting Your Help with Credit Report Corrections",
            "RE: Credit Report Review Request",
            "RE: Found Some Mistakes on My Credit Report",
        ],
        CivilTone.FORMAL: [
            "RE: Formal Dispute of Credit Report Information",
            "RE: Request for Credit Report Correction",
            "RE: Credit File Dispute Notice",
            "RE: Dispute of Inaccurate Credit Information",
        ],
        CivilTone.ASSERTIVE: [
            "RE: Immediate Action Required - Credit Report Errors",
            "RE: Dispute Notice - Inaccurate Credit Information",
            "RE: Correction Required - Credit Report Errors",
            "RE: Formal Dispute - Credit Report Inaccuracies",
        ],
        CivilTone.NARRATIVE: [
            "RE: My Story - Credit Report Errors That Need Fixing",
            "RE: Credit Report Issues - My Experience",
            "RE: What Happened to My Credit - A Request for Help",
            "RE: Credit Report Dispute - Understanding My Situation",
        ],
    }

    # Request phrases by tone
    REQUESTS: Dict[CivilTone, List[str]] = {
        CivilTone.CONVERSATIONAL: [
            "Could you please look into these items and let me know what you find?",
            "I'd really appreciate it if you could verify this information and make corrections.",
            "Would you mind checking on these entries and updating them if they're wrong?",
            "I'm hoping you can help me fix these problems on my credit report.",
        ],
        CivilTone.FORMAL: [
            "I request that you investigate these items and provide written verification of your findings.",
            "Please review the disputed items and correct any inaccurate information.",
            "I ask that you conduct a thorough investigation and notify me of the results.",
            "Kindly verify the accuracy of these items and remove any incorrect information.",
        ],
        CivilTone.ASSERTIVE: [
            "I demand that you investigate these items and remove any information that cannot be verified.",
            "You must review these disputed items and correct all inaccuracies immediately.",
            "I expect you to investigate and provide written confirmation of corrections within 30 days.",
            "These errors must be corrected and removed from my credit file without delay.",
        ],
        CivilTone.NARRATIVE: [
            "Now that you know my story, I hope you can help me correct these errors.",
            "Understanding what happened, I trust you'll agree these items need to be fixed.",
            "Given what I've explained, I'm asking for your help in making these corrections.",
            "With this context, I hope you can see why these items are inaccurate and need updating.",
        ],
    }

    def __init__(self, tone: CivilTone, seed: Optional[int] = None):
        """
        Initialize tone engine.

        Args:
            tone: The civil tone to use
            seed: Optional seed for deterministic selection
        """
        self.tone = tone
        self.config = TONE_CONFIGS[tone]
        self.seed = seed or random.randint(0, 2**32)
        self.rng = random.Random(self.seed)

    def get_greeting(self) -> str:
        """Get a tone-appropriate greeting."""
        options = self.GREETINGS[self.tone]
        return self.rng.choice(options)

    def get_opening(self) -> str:
        """Get a tone-appropriate opening paragraph."""
        options = self.OPENINGS[self.tone]
        return self.rng.choice(options)

    def get_closing(self) -> str:
        """Get a tone-appropriate closing paragraph."""
        options = self.CLOSINGS[self.tone]
        return self.rng.choice(options)

    def get_signature(self) -> str:
        """Get a tone-appropriate signature."""
        options = self.SIGNATURES[self.tone]
        return self.rng.choice(options)

    def get_subject(self) -> str:
        """Get a tone-appropriate subject line."""
        options = self.SUBJECTS[self.tone]
        return self.rng.choice(options)

    def get_request(self) -> str:
        """Get a tone-appropriate request phrase."""
        options = self.REQUESTS[self.tone]
        return self.rng.choice(options)

    def get_metadata(self) -> dict:
        """Get tone metadata for letter output."""
        return {
            "tone": self.tone.value,
            "formality_level": self.config.formality_level,
            "warmth_level": self.config.warmth_level,
            "directness_level": self.config.directness_level,
            "description": self.config.description,
            "seed": self.seed,
        }


def resolve_tone(tone_str: str) -> CivilTone:
    """
    Resolve a tone string to a CivilTone enum.

    Handles aliases and defaults to CONVERSATIONAL if unknown.
    """
    # Check direct enum values
    try:
        return CivilTone(tone_str.lower())
    except ValueError:
        pass

    # Check aliases
    if tone_str.lower() in CIVIL_TONE_ALIASES:
        return CIVIL_TONE_ALIASES[tone_str.lower()]

    # Default to conversational
    return CivilTone.CONVERSATIONAL


def is_civil_tone(tone_str: str) -> bool:
    """Check if a tone string represents a civil tone."""
    tone_lower = tone_str.lower()

    # Check direct matches
    civil_tone_values = {t.value for t in CivilTone}
    if tone_lower in civil_tone_values:
        return True

    # Check aliases
    if tone_lower in CIVIL_TONE_ALIASES:
        return True

    return False


def get_civil_tones() -> List[Dict[str, Any]]:
    """Get list of available civil tones with metadata."""
    return [
        {
            "id": tone.value,
            "name": tone.value.title(),
            "description": TONE_CONFIGS[tone].description,
            "formality_level": TONE_CONFIGS[tone].formality_level,
            "letter_type": "civil",
        }
        for tone in CivilTone
    ]


def create_tone_engine(tone: str, seed: Optional[int] = None) -> CivilToneEngine:
    """
    Create a tone engine for the specified tone.

    Args:
        tone: Tone name (string)
        seed: Optional seed for deterministic output

    Returns:
        CivilToneEngine instance
    """
    resolved_tone = resolve_tone(tone)
    return CivilToneEngine(resolved_tone, seed)
