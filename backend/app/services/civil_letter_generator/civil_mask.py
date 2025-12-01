"""
Civil Letter Generator - Civil Mask

Domain isolation system that ensures civil letters never contain legal terminology.
Applies filtering to remove any legal-only terms that might leak into civil output.
"""
import re
from typing import List, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum


class LetterDomain(Enum):
    """Letter domain types."""
    CIVIL = "civil"
    LEGAL = "legal"


@dataclass
class MaskResult:
    """Result of applying a mask to content."""
    content: str
    terms_removed: List[str] = field(default_factory=list)
    replacements_made: int = 0
    is_clean: bool = True


class CivilMask:
    """
    Civil domain mask that filters out legal terminology.

    Ensures civil letters remain human-friendly and accessible,
    without legal jargon that could confuse consumers.
    """

    # Legal terms that must NEVER appear in civil letters
    FORBIDDEN_TERMS: Set[str] = {
        # FCRA references
        "FCRA",
        "Fair Credit Reporting Act",
        "15 U.S.C.",
        "U.S.C.",
        "Section 611",
        "Section 623",
        "Section 605",
        "Section 607",
        "§ 1681",
        "1681i",
        "1681s-2",
        "1681c",
        "1681e",
        # Legal procedural terms
        "pursuant to",
        "under the provisions of",
        "statutory",
        "reinvestigation",
        "willful noncompliance",
        "negligent noncompliance",
        "actual damages",
        "punitive damages",
        "reasonable reinvestigation",
        # Metro-2 and technical terms
        "Metro-2",
        "Metro 2",
        "method of verification",
        "MOV",
        "furnisher",
        "data furnisher",
        # Case law markers
        "v.",
        "F.3d",
        "F.2d",
        "Cir.",
        "Circuit",
        "Supp.",
        # Formal legal phrases
        "hereby",
        "herein",
        "thereof",
        "wherefore",
        "notwithstanding",
        "reservation of rights",
        "formal demand",
        "legal basis",
        "statutory category",
    }

    # Patterns that indicate legal content (regex)
    FORBIDDEN_PATTERNS: List[str] = [
        r"\b\d+\s+U\.S\.C\.\s*§?\s*\d+",  # USC citations
        r"\b\d+\s+F\.\d+d\s+\d+",  # Federal reporter citations
        r"\bSection\s+\d+\([a-z]\)",  # Section references like 611(a)
        r"\b[A-Z][a-z]+\s+v\.\s+[A-Z][a-z]+",  # Case names (Smith v. Jones)
        r"\b§\s*\d+",  # Section symbols with numbers
    ]

    # Civil-friendly replacements for accidentally included terms
    REPLACEMENTS: dict = {
        "pursuant to": "based on",
        "reinvestigation": "review",
        "furnisher": "creditor",
        "data furnisher": "creditor",
        "method of verification": "documentation",
        "MOV": "documentation",
        "hereby": "",
        "herein": "in this letter",
        "thereof": "of this",
        "notwithstanding": "despite",
        "formal demand": "request",
    }

    @classmethod
    def apply(cls, content: str) -> MaskResult:
        """
        Apply civil mask to content, removing legal terminology.

        Args:
            content: Raw letter content

        Returns:
            MaskResult with cleaned content and metadata
        """
        result = MaskResult(content=content)

        # Apply replacements first (these are softer)
        for legal_term, civil_term in cls.REPLACEMENTS.items():
            if legal_term.lower() in content.lower():
                # Case-insensitive replacement
                pattern = re.compile(re.escape(legal_term), re.IGNORECASE)
                content = pattern.sub(civil_term, content)
                result.terms_removed.append(legal_term)
                result.replacements_made += 1

        # Check for and remove forbidden terms
        for term in cls.FORBIDDEN_TERMS:
            if term.lower() in content.lower():
                # Remove the term (or sentence containing it if appropriate)
                pattern = re.compile(re.escape(term), re.IGNORECASE)
                content = pattern.sub("", content)
                result.terms_removed.append(term)
                result.replacements_made += 1

        # Check for and remove forbidden patterns
        for pattern_str in cls.FORBIDDEN_PATTERNS:
            pattern = re.compile(pattern_str, re.IGNORECASE)
            matches = pattern.findall(content)
            if matches:
                content = pattern.sub("", content)
                result.terms_removed.extend(matches)
                result.replacements_made += len(matches)

        # Clean up any double spaces or empty lines created
        content = re.sub(r'  +', ' ', content)
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)

        result.content = content.strip()
        result.is_clean = len(result.terms_removed) == 0

        return result

    @classmethod
    def validate(cls, content: str) -> Tuple[bool, List[str]]:
        """
        Validate that content is free of legal terminology.

        Args:
            content: Content to validate

        Returns:
            Tuple of (is_valid, list of violations found)
        """
        violations = []
        content_lower = content.lower()

        # Check forbidden terms
        for term in cls.FORBIDDEN_TERMS:
            if term.lower() in content_lower:
                violations.append(f"Forbidden term: {term}")

        # Check forbidden patterns
        for pattern_str in cls.FORBIDDEN_PATTERNS:
            pattern = re.compile(pattern_str, re.IGNORECASE)
            matches = pattern.findall(content)
            for match in matches:
                violations.append(f"Forbidden pattern: {match}")

        return len(violations) == 0, violations

    @classmethod
    def get_metadata(cls) -> dict:
        """Get mask metadata for letter output."""
        return {
            "domain": "civil",
            "mask_applied": True,
            "mask_version": "2.0",
            "forbidden_term_count": len(cls.FORBIDDEN_TERMS),
            "forbidden_pattern_count": len(cls.FORBIDDEN_PATTERNS),
        }


# Convenience function
def apply_civil_mask(content: str) -> str:
    """Apply civil mask and return cleaned content."""
    result = CivilMask.apply(content)
    return result.content


def validate_civil_content(content: str) -> Tuple[bool, List[str]]:
    """Validate content is civil-safe."""
    return CivilMask.validate(content)
