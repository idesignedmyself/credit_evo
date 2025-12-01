"""
Legal Letter Generator - Tone Mask System
Provides strict tone isolation between legal and civil letter domains.
Prevents cross-contamination of phrasing, structure, and legal references.
"""
import re
from enum import Enum
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime


class LetterDomain(str, Enum):
    """Letter domain classification."""
    LEGAL = "legal"
    CIVIL = "civil"


class MaskViolationType(str, Enum):
    """Types of mask violations detected."""
    FORBIDDEN_PHRASE = "forbidden_phrase"
    MISSING_REQUIRED = "missing_required"
    DOMAIN_CONTAMINATION = "domain_contamination"
    STRUCTURAL_VIOLATION = "structural_violation"


@dataclass
class MaskViolation:
    """Record of a mask violation."""
    violation_type: MaskViolationType
    description: str
    original_text: str = ""
    replacement_text: str = ""
    line_number: int = 0


@dataclass
class MaskMetadata:
    """Metadata about mask application."""
    domain: LetterDomain
    tone: str
    applied_at: str
    violations_found: int
    violations_fixed: int
    forbidden_phrases_removed: int
    required_blocks_verified: int
    mask_version: str = "2.0"


# =============================================================================
# LEGAL MASK CONFIGURATION
# =============================================================================

# Phrases forbidden in LEGAL letters (too soft/civil)
LEGAL_FORBIDDEN_PHRASES = {
    # Soft/apologetic language
    "thank you for your time",
    "thanks for your help",
    "i would appreciate",
    "i would be grateful",
    "if you could please",
    "if you wouldn't mind",
    "i hope you can",
    "i hope this",
    "sorry for any confusion",
    "sorry to bother",
    "i understand you're busy",
    "when you get a chance",
    "at your convenience",
    "no rush",
    "just wanted to",
    "i was wondering if",
    "would it be possible",
    "could you maybe",
    # Uncertain language
    "i think there might be",
    "it seems like maybe",
    "possibly incorrect",
    "might be wrong",
    "could be an error",
    "seems a bit off",
    # Overly casual
    "hey there",
    "hi there",
    "just checking in",
    "quick question",
    "fyi",
    "btw",
    "asap",
}

# Required structural blocks for LEGAL letters
LEGAL_REQUIRED_BLOCKS = {
    "legal_basis": [
        r"fcra\s+section\s+\d+",
        r"15\s+u\.?s\.?c\.?\s+§?\s*1681",
        r"fair\s+credit\s+reporting\s+act",
        r"pursuant\s+to",
        r"under\s+the\s+provisions",
    ],
    "statutory_category": [
        r"section\s+\d+\([a-z]\)",
        r"statutory\s+(?:violation|requirement|category)",
    ],
    "mov_block": [
        r"method\s+of\s+verification",
        r"mov\s+",
        r"verification\s+(?:method|procedure|documentation)",
        r"original\s+source\s+documentation",
    ],
}

# Phrases that indicate legal tone (should be present)
LEGAL_MARKERS = {
    "pursuant to",
    "under the provisions of",
    "in accordance with",
    "as required by",
    "you are obligated",
    "you must",
    "you shall",
    "legally required",
    "statutory",
    "reinvestigation",
    "willful noncompliance",
    "reasonable procedures",
}


# =============================================================================
# CIVIL MASK CONFIGURATION
# =============================================================================

# Phrases/patterns FORBIDDEN in CIVIL letters (too legal)
CIVIL_FORBIDDEN_PATTERNS = [
    # Case law citations
    r"\b[A-Z][a-z]+\s+v\.?\s+[A-Z][a-z]+.*?\d{4}\b",  # Cushman v. Trans Union
    r"\b\d+\s+F\.\s*(?:2d|3d|Supp)\s+\d+\b",  # 115 F.3d 1097
    r"\b\d+\s+S\.?\s*Ct\.?\s+\d+\b",  # Supreme Court citations
    # USC citations
    r"15\s+u\.?s\.?c\.?\s+§?\s*\d+",  # 15 U.S.C.
    r"§\s*1681[a-z]?(?:\([a-z0-9]+\))?",  # Section symbols
    # Legal jargon
    r"\bpursuant\s+to\b",
    r"\bunder\s+the\s+provisions\s+of\b",
    r"\bwillful\s+(?:non)?compliance\b",
    r"\bstatutory\s+(?:damages?|violation|category|requirement)\b",
    r"\breinvestigation\b",
    r"\bmethod\s+of\s+verification\b",
    r"\bmov\s+(?:requirement|demand)\b",
    r"\bfurnisher\s+(?:duties?|obligations?)\b",
    r"\breasonable\s+(?:reinvestigation|procedures?)\b",
    r"\bfcra\s+section\b",
    r"\bsection\s+\d{3}\([a-z]\)",  # Section 611(a)
]

# Words/phrases that must be replaced in CIVIL letters
CIVIL_REPLACEMENTS = {
    "reinvestigation": "review",
    "reinvestigate": "review",
    "furnisher": "creditor",
    "furnishers": "creditors",
    "data furnisher": "reporting company",
    "consumer reporting agency": "credit bureau",
    "cra": "credit bureau",
    "pursuant to": "according to",
    "under the provisions of": "under",
    "statutory requirement": "legal requirement",
    "statutory damages": "compensation",
    "willful noncompliance": "deliberate failure",
    "negligent noncompliance": "careless mistakes",
    "method of verification": "proof",
    "mov": "proof",
    "maximum possible accuracy": "accuracy",
}

# Required elements for CIVIL letters
CIVIL_REQUIRED_ELEMENTS = {
    "plain_language": True,
    "personal_voice": True,
    "clear_action_requests": True,
}


# =============================================================================
# LEGAL REPLACEMENTS (soft phrases -> formal alternatives)
# =============================================================================

LEGAL_SOFT_TO_FORMAL = {
    "thank you for your time": "I await your timely response",
    "thanks for your help": "Compliance with this request is required",
    "i would appreciate": "I demand",
    "if you could please": "You are required to",
    "i hope you can": "You must",
    "sorry for any confusion": "For clarification",
    "i understand you're busy": "Notwithstanding your workload",
    "at your convenience": "within the statutory timeframe",
    "when you get a chance": "immediately",
    "just wanted to": "I hereby",
    "i was wondering if": "I demand to know whether",
    "would it be possible": "You are obligated to",
    "i think there might be": "There exists",
    "it seems like maybe": "The evidence demonstrates",
    "could be an error": "constitutes a violation",
}


# =============================================================================
# TONE MASK CLASS
# =============================================================================

class ToneMask:
    """
    Two-mask system for tone isolation between legal and civil letter domains.

    LEGAL_MASK:
        - Requires: legal basis block, statutory category, MOV block
        - Forbids: soft/civil phrasing, apologies, uncertain language
        - Filters: conversational markers, softeners

    CIVIL_MASK:
        - Forbids: case law, USC citations, FCRA sections, MOV, reinvestigation
        - Replaces: legal jargon with plain language equivalents
        - Requires: plain language, personal voice, clear requests
    """

    def __init__(
        self,
        domain: LetterDomain,
        tone: str,
        strict_mode: bool = True,
        include_case_law: bool = False,
    ):
        """
        Initialize the tone mask.

        Args:
            domain: Letter domain (LEGAL or CIVIL)
            tone: Specific tone within the domain
            strict_mode: If True, enforce all rules strictly
            include_case_law: If True, MOV block is required for legal
        """
        self.domain = domain
        self.tone = tone
        self.strict_mode = strict_mode
        self.include_case_law = include_case_law
        self.violations: List[MaskViolation] = []
        self._stats = {
            "forbidden_removed": 0,
            "required_verified": 0,
            "replacements_made": 0,
        }

    def apply(self, content: str) -> str:
        """
        Apply the appropriate mask to content.

        Args:
            content: Raw letter content

        Returns:
            Filtered content with mask applied
        """
        self.violations.clear()
        self._stats = {"forbidden_removed": 0, "required_verified": 0, "replacements_made": 0}

        if self.domain == LetterDomain.LEGAL:
            return self._apply_legal_mask(content)
        else:
            return self._apply_civil_mask(content)

    def _apply_legal_mask(self, content: str) -> str:
        """Apply LEGAL mask: remove soft phrases, verify required blocks."""
        filtered = content

        # 1. Remove forbidden soft phrases
        for phrase in LEGAL_FORBIDDEN_PHRASES:
            pattern = re.compile(re.escape(phrase), re.IGNORECASE)
            if pattern.search(filtered):
                # Get replacement if available
                replacement = LEGAL_SOFT_TO_FORMAL.get(phrase.lower(), "")
                if replacement:
                    filtered = pattern.sub(replacement, filtered)
                    self._stats["replacements_made"] += 1
                else:
                    # Remove the phrase entirely
                    filtered = pattern.sub("", filtered)

                self._stats["forbidden_removed"] += 1
                self.violations.append(MaskViolation(
                    violation_type=MaskViolationType.FORBIDDEN_PHRASE,
                    description=f"Soft/civil phrase removed: '{phrase}'",
                    original_text=phrase,
                    replacement_text=replacement,
                ))

        # 2. Verify required blocks are present (warning only in non-strict mode)
        if self.strict_mode:
            for block_name, patterns in LEGAL_REQUIRED_BLOCKS.items():
                # Skip MOV check if case law not included
                if block_name == "mov_block" and not self.include_case_law:
                    continue

                block_found = False
                for pattern in patterns:
                    if re.search(pattern, filtered, re.IGNORECASE):
                        block_found = True
                        break

                if block_found:
                    self._stats["required_verified"] += 1
                else:
                    self.violations.append(MaskViolation(
                        violation_type=MaskViolationType.MISSING_REQUIRED,
                        description=f"Required block missing: {block_name}",
                    ))

        # 3. Ensure legal markers are present
        markers_found = 0
        for marker in LEGAL_MARKERS:
            if marker.lower() in filtered.lower():
                markers_found += 1

        if markers_found < 2 and self.strict_mode:
            self.violations.append(MaskViolation(
                violation_type=MaskViolationType.DOMAIN_CONTAMINATION,
                description="Insufficient legal markers - letter may appear too civil",
            ))

        # 4. Clean up any double spaces from removals
        filtered = re.sub(r' +', ' ', filtered)
        filtered = re.sub(r'\n +', '\n', filtered)

        return filtered.strip()

    def _apply_civil_mask(self, content: str) -> str:
        """Apply CIVIL mask: remove legal terms, replace with plain language."""
        filtered = content

        # 1. Remove forbidden legal patterns
        for pattern in CIVIL_FORBIDDEN_PATTERNS:
            regex = re.compile(pattern, re.IGNORECASE)
            matches = regex.findall(filtered)
            if matches:
                for match in matches:
                    self.violations.append(MaskViolation(
                        violation_type=MaskViolationType.FORBIDDEN_PHRASE,
                        description=f"Legal terminology removed: '{match}'",
                        original_text=match if isinstance(match, str) else str(match),
                    ))
                filtered = regex.sub("", filtered)
                self._stats["forbidden_removed"] += len(matches)

        # 2. Apply replacements for legal jargon
        for legal_term, plain_term in CIVIL_REPLACEMENTS.items():
            pattern = re.compile(re.escape(legal_term), re.IGNORECASE)
            if pattern.search(filtered):
                filtered = pattern.sub(plain_term, filtered)
                self._stats["replacements_made"] += 1
                self.violations.append(MaskViolation(
                    violation_type=MaskViolationType.DOMAIN_CONTAMINATION,
                    description=f"Legal term replaced: '{legal_term}' -> '{plain_term}'",
                    original_text=legal_term,
                    replacement_text=plain_term,
                ))

        # 3. Check for remaining legal contamination
        remaining_legal = []
        for marker in LEGAL_MARKERS:
            if marker.lower() in filtered.lower():
                remaining_legal.append(marker)

        if remaining_legal and self.strict_mode:
            for marker in remaining_legal:
                self.violations.append(MaskViolation(
                    violation_type=MaskViolationType.DOMAIN_CONTAMINATION,
                    description=f"Legal marker still present: '{marker}'",
                    original_text=marker,
                ))

        # 4. Clean up formatting
        filtered = re.sub(r' +', ' ', filtered)
        filtered = re.sub(r'\n +', '\n', filtered)
        filtered = re.sub(r'\n{3,}', '\n\n', filtered)

        return filtered.strip()

    def get_metadata(self) -> MaskMetadata:
        """Get metadata about mask application."""
        return MaskMetadata(
            domain=self.domain,
            tone=self.tone,
            applied_at=datetime.now().isoformat(),
            violations_found=len(self.violations),
            violations_fixed=self._stats["forbidden_removed"] + self._stats["replacements_made"],
            forbidden_phrases_removed=self._stats["forbidden_removed"],
            required_blocks_verified=self._stats["required_verified"],
        )

    def get_violations(self) -> List[MaskViolation]:
        """Get list of violations found during mask application."""
        return self.violations.copy()

    def is_clean(self) -> bool:
        """Check if content passed mask with no violations."""
        return len(self.violations) == 0

    def to_dict(self) -> Dict:
        """Convert metadata to dictionary for JSON serialization."""
        meta = self.get_metadata()
        return {
            "domain": meta.domain.value,
            "tone": meta.tone,
            "applied_at": meta.applied_at,
            "violations_found": meta.violations_found,
            "violations_fixed": meta.violations_fixed,
            "forbidden_phrases_removed": meta.forbidden_phrases_removed,
            "required_blocks_verified": meta.required_blocks_verified,
            "mask_version": meta.mask_version,
            "is_clean": self.is_clean(),
        }


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_domain_for_tone(tone: str) -> LetterDomain:
    """Determine the domain for a given tone."""
    legal_tones = {"strict_legal", "professional", "soft_legal", "aggressive"}
    civil_tones = {"conversational", "civil_professional", "assertive", "narrative", "formal"}

    if tone in legal_tones:
        return LetterDomain.LEGAL
    elif tone in civil_tones:
        return LetterDomain.CIVIL
    else:
        # Default to legal for unknown tones
        return LetterDomain.LEGAL


def create_mask_for_tone(tone: str, include_case_law: bool = False) -> ToneMask:
    """Create appropriate mask for the given tone."""
    domain = get_domain_for_tone(tone)
    return ToneMask(
        domain=domain,
        tone=tone,
        strict_mode=True,
        include_case_law=include_case_law,
    )


def validate_content_domain(content: str, expected_domain: LetterDomain) -> Tuple[bool, List[str]]:
    """
    Validate that content matches expected domain.

    Returns:
        Tuple of (is_valid, list of issues found)
    """
    issues = []

    if expected_domain == LetterDomain.CIVIL:
        # Check for legal contamination
        for pattern in CIVIL_FORBIDDEN_PATTERNS[:5]:  # Check key patterns
            if re.search(pattern, content, re.IGNORECASE):
                issues.append(f"Legal pattern found in civil letter: {pattern}")
    else:
        # Check for missing legal requirements
        legal_found = False
        for pattern in LEGAL_REQUIRED_BLOCKS["legal_basis"]:
            if re.search(pattern, content, re.IGNORECASE):
                legal_found = True
                break
        if not legal_found:
            issues.append("Legal basis section missing from legal letter")

    return len(issues) == 0, issues


# =============================================================================
# SWEEP C COMPLIANCE HELPERS
# =============================================================================

def get_domain_phrase_pool(domain: LetterDomain) -> Set[str]:
    """Get the phrase pool for a domain (for anti-template measures)."""
    if domain == LetterDomain.LEGAL:
        return LEGAL_MARKERS.copy()
    else:
        return set(CIVIL_REPLACEMENTS.values())


def check_cross_contamination(content: str, domain: LetterDomain) -> List[str]:
    """Check for cross-domain contamination."""
    contaminations = []

    if domain == LetterDomain.LEGAL:
        # Check for civil phrases in legal content
        for phrase in LEGAL_FORBIDDEN_PHRASES:
            if phrase.lower() in content.lower():
                contaminations.append(f"Civil phrase in legal: {phrase}")
    else:
        # Check for legal markers in civil content
        for marker in LEGAL_MARKERS:
            if marker.lower() in content.lower():
                contaminations.append(f"Legal marker in civil: {marker}")

    return contaminations
