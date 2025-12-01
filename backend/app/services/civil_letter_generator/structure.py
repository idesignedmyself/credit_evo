"""
Civil Letter Generator - Structure Module

Defines the civil letter structure: intro → dispute_items → body → summary
Ensures consistent organization across all civil letters.
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import re


class CivilSection(Enum):
    """Civil letter section types (in order)."""
    HEADER = "header"
    DATE = "date"
    RECIPIENT = "recipient"
    SUBJECT = "subject"
    GREETING = "greeting"
    INTRO = "intro"
    DISPUTE_ITEMS = "dispute_items"
    EVIDENCE = "evidence"
    REQUEST = "request"
    CLOSING = "closing"
    SIGNATURE = "signature"


@dataclass
class SectionSpec:
    """Specification for a civil letter section."""
    section: CivilSection
    position: int
    required: bool = True
    min_sentences: int = 1
    max_sentences: int = 5


# Civil letter section order (9 sections)
CIVIL_SECTION_SPECS: List[SectionSpec] = [
    SectionSpec(CivilSection.HEADER, 1, required=False),
    SectionSpec(CivilSection.DATE, 2, required=True),
    SectionSpec(CivilSection.RECIPIENT, 3, required=True),
    SectionSpec(CivilSection.SUBJECT, 4, required=True),
    SectionSpec(CivilSection.GREETING, 5, required=True),
    SectionSpec(CivilSection.INTRO, 6, required=True, min_sentences=2, max_sentences=4),
    SectionSpec(CivilSection.DISPUTE_ITEMS, 7, required=True, min_sentences=1, max_sentences=20),
    SectionSpec(CivilSection.EVIDENCE, 8, required=False, min_sentences=1, max_sentences=5),
    SectionSpec(CivilSection.REQUEST, 9, required=True, min_sentences=1, max_sentences=3),
    SectionSpec(CivilSection.CLOSING, 10, required=True, min_sentences=1, max_sentences=2),
    SectionSpec(CivilSection.SIGNATURE, 11, required=True),
]


@dataclass
class StructuredSection:
    """A structured section with content and metadata."""
    section_type: CivilSection
    content: str
    position: int
    sentence_count: int = 0
    word_count: int = 0


@dataclass
class CivilLetterStructure:
    """Complete civil letter structure with all sections."""
    sections: List[StructuredSection] = field(default_factory=list)
    total_word_count: int = 0
    total_sentence_count: int = 0
    is_valid: bool = True
    validation_errors: List[str] = field(default_factory=list)

    def get_section(self, section_type: CivilSection) -> Optional[StructuredSection]:
        """Get a specific section by type."""
        for section in self.sections:
            if section.section_type == section_type:
                return section
        return None

    def get_content(self) -> str:
        """Get the full letter content in order."""
        sorted_sections = sorted(self.sections, key=lambda s: s.position)
        return "\n\n".join(s.content for s in sorted_sections if s.content)


class CivilStructureBuilder:
    """
    Builder for creating properly structured civil letters.

    Ensures sections appear in correct order and validates structure.
    """

    def __init__(self):
        self.sections: Dict[CivilSection, str] = {}

    def set_header(self, content: str) -> 'CivilStructureBuilder':
        """Set the header section (consumer info)."""
        self.sections[CivilSection.HEADER] = content
        return self

    def set_date(self, content: str) -> 'CivilStructureBuilder':
        """Set the date section."""
        self.sections[CivilSection.DATE] = content
        return self

    def set_recipient(self, content: str) -> 'CivilStructureBuilder':
        """Set the recipient section (bureau address)."""
        self.sections[CivilSection.RECIPIENT] = content
        return self

    def set_subject(self, content: str) -> 'CivilStructureBuilder':
        """Set the subject line."""
        self.sections[CivilSection.SUBJECT] = content
        return self

    def set_greeting(self, content: str) -> 'CivilStructureBuilder':
        """Set the greeting (Dear ...)."""
        self.sections[CivilSection.GREETING] = content
        return self

    def set_intro(self, content: str) -> 'CivilStructureBuilder':
        """Set the introduction paragraph."""
        self.sections[CivilSection.INTRO] = content
        return self

    def set_dispute_items(self, content: str) -> 'CivilStructureBuilder':
        """Set the dispute items section."""
        self.sections[CivilSection.DISPUTE_ITEMS] = content
        return self

    def set_evidence(self, content: str) -> 'CivilStructureBuilder':
        """Set the evidence/documentation section."""
        self.sections[CivilSection.EVIDENCE] = content
        return self

    def set_request(self, content: str) -> 'CivilStructureBuilder':
        """Set the request/action section."""
        self.sections[CivilSection.REQUEST] = content
        return self

    def set_closing(self, content: str) -> 'CivilStructureBuilder':
        """Set the closing paragraph."""
        self.sections[CivilSection.CLOSING] = content
        return self

    def set_signature(self, content: str) -> 'CivilStructureBuilder':
        """Set the signature block."""
        self.sections[CivilSection.SIGNATURE] = content
        return self

    def build(self) -> CivilLetterStructure:
        """Build the structured letter."""
        structure = CivilLetterStructure()

        for spec in CIVIL_SECTION_SPECS:
            content = self.sections.get(spec.section, "")

            if spec.required and not content:
                structure.is_valid = False
                structure.validation_errors.append(
                    f"Missing required section: {spec.section.value}"
                )
                continue

            if content:
                # Count sentences and words
                sentences = len(re.findall(r'[.!?]+', content))
                words = len(content.split())

                section = StructuredSection(
                    section_type=spec.section,
                    content=content,
                    position=spec.position,
                    sentence_count=sentences,
                    word_count=words,
                )
                structure.sections.append(section)
                structure.total_word_count += words
                structure.total_sentence_count += sentences

        return structure


class StructureValidator:
    """Validates civil letter structure."""

    @staticmethod
    def validate_order(content: str) -> tuple:
        """
        Validate that sections appear in correct order.

        Returns:
            Tuple of (is_valid, list of errors)
        """
        errors = []

        # Section markers to look for (in order)
        markers = [
            ("RE:", "subject"),
            ("Dear", "greeting"),
            ("I am writing", "intro"),
            ("account", "dispute_items"),
            ("Thank you", "closing"),
            ("Sincerely", "signature"),
        ]

        last_position = -1
        for marker, section_name in markers:
            pos = content.lower().find(marker.lower())
            if pos != -1:
                if pos < last_position:
                    errors.append(f"Section '{section_name}' appears out of order")
                last_position = pos

        return len(errors) == 0, errors

    @staticmethod
    def validate_completeness(structure: CivilLetterStructure) -> tuple:
        """
        Validate that all required sections are present.

        Returns:
            Tuple of (is_valid, list of errors)
        """
        errors = []

        for spec in CIVIL_SECTION_SPECS:
            if spec.required:
                section = structure.get_section(spec.section)
                if not section or not section.content:
                    errors.append(f"Missing required section: {spec.section.value}")

        return len(errors) == 0, errors

    @staticmethod
    def validate_length(structure: CivilLetterStructure) -> tuple:
        """
        Validate that letter is within acceptable length.

        Returns:
            Tuple of (is_valid, list of warnings)
        """
        warnings = []

        if structure.total_word_count < 100:
            warnings.append("Letter is very short (< 100 words)")
        elif structure.total_word_count > 1000:
            warnings.append("Letter is very long (> 1000 words)")

        return len(warnings) == 0, warnings


def create_civil_structure(
    date: str,
    recipient: str,
    subject: str,
    greeting: str,
    intro: str,
    dispute_items: str,
    request: str,
    closing: str,
    signature: str,
    header: str = "",
    evidence: str = "",
) -> CivilLetterStructure:
    """
    Convenience function to create a civil letter structure.

    Args:
        date: Date string
        recipient: Bureau address
        subject: Subject line
        greeting: Greeting (Dear ...)
        intro: Introduction paragraph
        dispute_items: Dispute items section
        request: Request/action section
        closing: Closing paragraph
        signature: Signature block
        header: Optional consumer header
        evidence: Optional evidence section

    Returns:
        CivilLetterStructure with all sections
    """
    builder = CivilStructureBuilder()

    if header:
        builder.set_header(header)

    builder.set_date(date)
    builder.set_recipient(recipient)
    builder.set_subject(subject)
    builder.set_greeting(greeting)
    builder.set_intro(intro)
    builder.set_dispute_items(dispute_items)

    if evidence:
        builder.set_evidence(evidence)

    builder.set_request(request)
    builder.set_closing(closing)
    builder.set_signature(signature)

    return builder.build()


def get_structure_metadata(structure: CivilLetterStructure) -> dict:
    """Get metadata about the letter structure."""
    return {
        "section_count": len(structure.sections),
        "sections_present": [s.section_type.value for s in structure.sections],
        "total_word_count": structure.total_word_count,
        "total_sentence_count": structure.total_sentence_count,
        "is_valid": structure.is_valid,
        "validation_errors": structure.validation_errors,
        "structure_type": "civil_v2",
    }
