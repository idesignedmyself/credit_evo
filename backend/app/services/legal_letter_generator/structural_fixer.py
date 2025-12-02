"""
Structural Fixer - Enforces stable section ordering and structural integrity.
Guarantees that diversity engine mutations never break letter structure.
"""
import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum


class LetterDomainType(str, Enum):
    """Letter domain types."""
    LEGAL = "legal"
    CIVIL = "civil"


@dataclass
class SectionSpec:
    """Specification for a letter section."""
    name: str
    position: int
    required: bool = False
    header_patterns: List[str] = field(default_factory=list)
    forbidden_in_domains: List[LetterDomainType] = field(default_factory=list)


@dataclass
class StructuralMetadata:
    """Metadata about structural fixes applied."""
    sections_found: List[str] = field(default_factory=list)
    sections_reordered: List[str] = field(default_factory=list)
    sections_inserted: List[str] = field(default_factory=list)
    duplicates_removed: List[str] = field(default_factory=list)
    cross_domain_removed: List[str] = field(default_factory=list)
    order_violations_fixed: int = 0
    structure_valid: bool = True
    domain: str = "legal"


# LEGAL LETTER SECTION SEQUENCE (IMMUTABLE ORDER)
# Enforces: Header → Intro → Disputed Items → Legal Basis → MOV → Case Law → Demands → Signature
LEGAL_SECTION_SPECS: List[SectionSpec] = [
    SectionSpec(
        name="header",
        position=0,
        required=True,
        header_patterns=[
            r"^[A-Z][a-z]+ [A-Z][a-z]+\n",  # Consumer name pattern
            r"^(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}",
            r"^(RE:|Re:|Subject:|SUBJECT:)",
        ],
    ),
    SectionSpec(
        name="intro",
        position=1,
        required=True,
        header_patterns=[
            r"^(I\.?\s+)?PRELIMINARY STATEMENT",
            r"^(I\.?\s+)?NOTICE AND DEMAND",
            r"^Introduction",
            r"^INTRODUCTION",
            r"^About This Dispute",
            r"^I am writing",
            r"^I'm writing",
            r"^This letter serves",
            r"^Your records require",
        ],
    ),
    SectionSpec(
        name="disputed_items",
        position=2,
        required=True,
        header_patterns=[
            r"^(II\.?\s+)?SPECIFIC VIOLATIONS",
            r"^(II\.?\s+)?DISPUTED ITEMS",
            r"^(III\.?\s+)?SPECIFIC DEFICIENCIES",
            r"^Violations",
            r"^VIOLATIONS",
            r"^Disputed Items",
            r"^Items I'm Disputing",
            r"^FCRA VIOLATIONS IDENTIFIED",
        ],
    ),
    SectionSpec(
        name="legal_basis",
        position=3,
        required=False,
        header_patterns=[
            r"^(III\.?\s+)?LEGAL BASIS",
            r"^(II\.?\s+)?LEGAL BASIS",
            r"^Legal Basis",
            r"^LEGAL FRAMEWORK",
            r"^Legal Framework",
            r"^My Rights Under the Law",
        ],
    ),
    SectionSpec(
        name="mov_section",
        position=4,
        required=False,
        header_patterns=[
            r"^(IV\.?\s+)?METHOD OF VERIFICATION",
            r"^(V\.?\s+)?MANDATORY VERIFICATION",
            r"^(V\.?\s+)?MOV",
            r"^Verification Requirements",
            r"^VERIFICATION REQUIREMENTS",
            r"^What I Need to See",
        ],
        forbidden_in_domains=[LetterDomainType.CIVIL],
    ),
    SectionSpec(
        name="case_law",
        position=5,
        required=False,
        header_patterns=[
            r"^(V\.?\s+)?CASE LAW",
            r"^(V\.?\s+)?APPLICABLE CASE LAW",  # Matches strict_legal's "V. APPLICABLE CASE LAW"
            r"^(VI\.?\s+)?APPLICABLE CASE LAW",
            r"^(VI\.?\s+)?LEGAL PRECEDENT",
            r"^Case Law",
            r"^Legal Precedent",
            r"^Legal Standards",
        ],
        forbidden_in_domains=[LetterDomainType.CIVIL],
    ),
    SectionSpec(
        name="demands",
        position=6,
        required=True,
        header_patterns=[
            r"^(VI\.?\s+)?FORMAL DEMANDS",
            r"^(VII\.?\s+)?NON-NEGOTIABLE DEMANDS",
            r"^(VII\.?\s+)?DEMANDS",
            r"^Demands",
            r"^DEMANDS",
            r"^Requested Actions",
            r"^What I'm Asking For",
        ],
    ),
    SectionSpec(
        name="signature",
        position=7,
        required=True,
        header_patterns=[
            r"^(Respectfully|Sincerely|Thank you|WITHOUT PREJUDICE)",
            r"^_+",  # Signature line
            r"^GOVERN YOURSELF",
        ],
    ),
]


# CIVIL LETTER SECTION SEQUENCE (IMMUTABLE ORDER)
CIVIL_SECTION_SPECS: List[SectionSpec] = [
    SectionSpec(
        name="header",
        position=0,
        required=True,
        header_patterns=[r"^[A-Z][a-z]+ [A-Z][a-z]+\n"],
    ),
    SectionSpec(
        name="date_line",
        position=1,
        required=True,
        header_patterns=[r"^(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}"],
    ),
    SectionSpec(
        name="subject_line",
        position=2,
        required=False,
        header_patterns=[r"^(RE:|Re:|Subject:|SUBJECT:)", r"^Credit Report Dispute"],
    ),
    SectionSpec(
        name="narrative_intro",
        position=3,
        required=True,
        header_patterns=[
            r"^(Dear|To Whom|Hello)",
            r"^I am writing",
            r"^I'm writing",
            r"^This letter",
        ],
    ),
    SectionSpec(
        name="disputed_items",
        position=4,
        required=True,
        header_patterns=[
            r"^(The following|These items|I am disputing|I dispute)",
            r"^Items I'm Disputing",
            r"^Disputed Items",
            r"^Problems I Found",
        ],
    ),
    SectionSpec(
        name="evidence_block",
        position=5,
        required=False,
        header_patterns=[
            r"^(Here's what|The details|Specifically|My evidence)",
            r"^Details",
            r"^Evidence",
        ],
    ),
    SectionSpec(
        name="requested_actions",
        position=6,
        required=True,
        header_patterns=[
            r"^(I would like|Please|I am asking|I request|I'm asking)",
            r"^What I Need",
            r"^My Requests",
            r"^Actions Needed",
        ],
    ),
    SectionSpec(
        name="closing_paragraph",
        position=7,
        required=True,
        header_patterns=[
            r"^(Thank you|I appreciate|I look forward)",
            r"^Thanks for",
        ],
    ),
    SectionSpec(
        name="signature",
        position=8,
        required=True,
        header_patterns=[
            r"^(Sincerely|Best|Thanks|Thank you)",
            r"^_+",
        ],
    ),
]


# Legal-only terms that must not appear in civil letters
LEGAL_ONLY_TERMS = [
    r"\bpursuant to\b",
    r"\bhereby\b",
    r"\bwherein\b",
    r"\bwherefore\b",
    r"\bnotwithstanding\b",
    r"\baforesaid\b",
    r"\bhereunder\b",
    r"\bhereinafter\b",
    r"\binter alia\b",
    r"\bab initio\b",
    r"\bMethod of Verification\b",
    r"\bMOV\b",
    r"\bMetro-?2\b",
    r"\bwillful\b.*\bviolation\b",
    r"\bstatutory damages\b",
    r"\bpunitive damages\b",
    r"\b\d+ U\.S\.C\.",
    r"\bcase law\b",
    r"\blegal precedent\b",
]

# Civil-only terms that must not appear in legal letters
CIVIL_ONLY_TERMS = [
    r"\bkindly\b",
    r"\bplease help\b",
    r"\bI would appreciate\b",
    r"\bif you could\b",
    r"\bwould you mind\b",
    r"\bI'm confused\b",
    r"\bI don't understand\b",
]


class StructuralFixer:
    """
    Enforces stable section ordering and structural integrity.
    Guarantees that diversity engine mutations never break letter structure.
    """

    def __init__(self):
        self.legal_specs = {s.name: s for s in LEGAL_SECTION_SPECS}
        self.civil_specs = {s.name: s for s in CIVIL_SECTION_SPECS}

    def fix_structure(
        self,
        letter_content: str,
        domain: str,
        tone: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, StructuralMetadata]:
        """
        Fix structural issues in a letter.

        Args:
            letter_content: The raw letter content
            domain: "legal" or "civil"
            tone: The tone used (e.g., "professional", "strict_legal")
            metadata: Optional additional metadata

        Returns:
            Tuple of (fixed_content, structural_metadata)
        """
        domain_type = LetterDomainType(domain.lower())
        struct_meta = StructuralMetadata(domain=domain)

        if not letter_content:
            struct_meta.structure_valid = False
            return letter_content, struct_meta

        # Step 1: Parse sections
        sections = self._parse_sections(letter_content, domain_type)
        struct_meta.sections_found = list(sections.keys())

        # Step 2: Remove cross-domain content
        sections, removed = self._remove_cross_domain_content(sections, domain_type)
        struct_meta.cross_domain_removed = removed

        # Step 3: Remove duplicate sections
        sections, duplicates = self._remove_duplicate_sections(sections)
        struct_meta.duplicates_removed = duplicates

        # Step 4: Insert missing required sections
        sections, inserted = self._insert_missing_sections(sections, domain_type, tone, metadata)
        struct_meta.sections_inserted = inserted

        # Step 5: Enforce correct ordering
        sections, reordered, order_fixes = self._enforce_ordering(sections, domain_type)
        struct_meta.sections_reordered = reordered
        struct_meta.order_violations_fixed = order_fixes

        # Step 6: Reassemble letter
        fixed_content = self._reassemble_letter(sections, domain_type)

        # Step 7: Apply domain-specific term filtering
        fixed_content = self._filter_domain_terms(fixed_content, domain_type)

        # Validate final structure
        struct_meta.structure_valid = self._validate_structure(fixed_content, domain_type)

        return fixed_content, struct_meta

    def _parse_sections(
        self,
        content: str,
        domain: LetterDomainType
    ) -> Dict[str, str]:
        """Parse letter content into sections."""
        specs = LEGAL_SECTION_SPECS if domain == LetterDomainType.LEGAL else CIVIL_SECTION_SPECS
        sections: Dict[str, str] = {}

        # Split content by double newlines (paragraph breaks)
        paragraphs = re.split(r'\n\n+', content)

        current_section = "header"
        current_content = []

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # Check if this paragraph starts a new section
            matched_section = None
            for spec in specs:
                for pattern in spec.header_patterns:
                    if re.search(pattern, para, re.IGNORECASE | re.MULTILINE):
                        matched_section = spec.name
                        break
                if matched_section:
                    break

            if matched_section and matched_section != current_section:
                # Save current section
                if current_content:
                    sections[current_section] = "\n\n".join(current_content)
                current_section = matched_section
                current_content = [para]
            else:
                current_content.append(para)

        # Save final section
        if current_content:
            sections[current_section] = "\n\n".join(current_content)

        return sections

    def _remove_cross_domain_content(
        self,
        sections: Dict[str, str],
        domain: LetterDomainType
    ) -> Tuple[Dict[str, str], List[str]]:
        """Remove sections that are forbidden in the current domain."""
        removed = []
        specs = LEGAL_SECTION_SPECS if domain == LetterDomainType.LEGAL else CIVIL_SECTION_SPECS

        for spec in specs:
            if domain in spec.forbidden_in_domains and spec.name in sections:
                del sections[spec.name]
                removed.append(spec.name)

        return sections, removed

    def _remove_duplicate_sections(
        self,
        sections: Dict[str, str]
    ) -> Tuple[Dict[str, str], List[str]]:
        """Remove duplicate section content."""
        duplicates = []
        seen_content = {}

        for name, content in list(sections.items()):
            # Normalize content for comparison
            normalized = re.sub(r'\s+', ' ', content.lower().strip())
            content_hash = hash(normalized[:500])  # Hash first 500 chars

            if content_hash in seen_content:
                # This is a duplicate
                duplicates.append(f"{name} (duplicate of {seen_content[content_hash]})")
                del sections[name]
            else:
                seen_content[content_hash] = name

        return sections, duplicates

    def _insert_missing_sections(
        self,
        sections: Dict[str, str],
        domain: LetterDomainType,
        tone: str,
        metadata: Optional[Dict[str, Any]]
    ) -> Tuple[Dict[str, str], List[str]]:
        """Insert placeholder content for missing required sections."""
        inserted = []
        specs = LEGAL_SECTION_SPECS if domain == LetterDomainType.LEGAL else CIVIL_SECTION_SPECS

        for spec in specs:
            if spec.required and spec.name not in sections:
                # Skip if forbidden in this domain
                if domain in spec.forbidden_in_domains:
                    continue

                # Generate placeholder content
                placeholder = self._generate_placeholder(spec.name, domain, tone, metadata)
                if placeholder:
                    sections[spec.name] = placeholder
                    inserted.append(spec.name)

        return sections, inserted

    def _generate_placeholder(
        self,
        section_name: str,
        domain: LetterDomainType,
        tone: str,
        metadata: Optional[Dict[str, Any]]
    ) -> Optional[str]:
        """Generate placeholder content for a missing section."""
        placeholders = {
            "header": "[CONSUMER NAME]\n[ADDRESS]\n[CITY, STATE ZIP]",
            "date_line": "[DATE]",
            "subject_line": "RE: Credit Report Dispute",
            "preliminary_statement": "This letter constitutes a formal dispute of information contained in my credit report.",
            "narrative_intro": "I am writing to dispute inaccurate information on my credit report.",
            "specific_violations": "The following items are disputed as inaccurate.",
            "disputed_items": "I am disputing the following items on my credit report.",
            "formal_demands": "I demand that you investigate these items and correct any inaccuracies.",
            "requested_actions": "Please investigate these items and correct any errors found.",
            "closing_paragraph": "Thank you for your attention to this matter.",
            "signature": "Respectfully,\n\n\n[SIGNATURE]\n[PRINTED NAME]",
        }

        return placeholders.get(section_name)

    def _enforce_ordering(
        self,
        sections: Dict[str, str],
        domain: LetterDomainType
    ) -> Tuple[Dict[str, str], List[str], int]:
        """Enforce correct section ordering based on domain."""
        specs = LEGAL_SECTION_SPECS if domain == LetterDomainType.LEGAL else CIVIL_SECTION_SPECS
        spec_order = {s.name: s.position for s in specs}

        # Get current order
        current_order = list(sections.keys())

        # Sort by correct position
        sorted_order = sorted(
            current_order,
            key=lambda x: spec_order.get(x, 999)
        )

        # Track what was reordered
        reordered = []
        order_fixes = 0

        for i, (curr, sorted_name) in enumerate(zip(current_order, sorted_order)):
            if curr != sorted_name:
                reordered.append(f"{curr} -> position {i}")
                order_fixes += 1

        # Create new ordered dict
        ordered_sections = {}
        for name in sorted_order:
            if name in sections:
                ordered_sections[name] = sections[name]

        return ordered_sections, reordered, order_fixes

    def _reassemble_letter(
        self,
        sections: Dict[str, str],
        domain: LetterDomainType
    ) -> str:
        """Reassemble sections into a complete letter."""
        parts = []
        for name, content in sections.items():
            if content:
                parts.append(content)
        return "\n\n".join(parts)

    def _filter_domain_terms(
        self,
        content: str,
        domain: LetterDomainType
    ) -> str:
        """Filter out terms that don't belong in the domain."""
        if domain == LetterDomainType.CIVIL:
            # Remove legal-only terms from civil letters
            for pattern in LEGAL_ONLY_TERMS:
                content = re.sub(pattern, "", content, flags=re.IGNORECASE)
        elif domain == LetterDomainType.LEGAL:
            # Remove civil-only terms from legal letters
            for pattern in CIVIL_ONLY_TERMS:
                content = re.sub(pattern, "", content, flags=re.IGNORECASE)

        # Clean up any double spaces or extra newlines
        content = re.sub(r'  +', ' ', content)
        content = re.sub(r'\n{3,}', '\n\n', content)

        return content.strip()

    def _validate_structure(
        self,
        content: str,
        domain: LetterDomainType
    ) -> bool:
        """Validate that the final structure is correct."""
        specs = LEGAL_SECTION_SPECS if domain == LetterDomainType.LEGAL else CIVIL_SECTION_SPECS

        # Check for required sections
        for spec in specs:
            if not spec.required:
                continue
            if domain in spec.forbidden_in_domains:
                continue

            # Check if at least one pattern matches
            found = False
            for pattern in spec.header_patterns:
                if re.search(pattern, content, re.IGNORECASE | re.MULTILINE):
                    found = True
                    break

            if not found:
                return False

        return True

    def validate_legal_order(self, content: str) -> Tuple[bool, List[str]]:
        """Validate that legal letter sections are in correct order."""
        issues = []
        last_position = -1

        for spec in LEGAL_SECTION_SPECS:
            for pattern in spec.header_patterns:
                match = re.search(pattern, content, re.IGNORECASE | re.MULTILINE)
                if match:
                    position = match.start()
                    if position < last_position and spec.position > 0:
                        issues.append(f"Section '{spec.name}' appears out of order")
                    last_position = position
                    break

        return len(issues) == 0, issues

    def validate_civil_order(self, content: str) -> Tuple[bool, List[str]]:
        """Validate that civil letter sections are in correct order."""
        issues = []
        last_position = -1

        for spec in CIVIL_SECTION_SPECS:
            for pattern in spec.header_patterns:
                match = re.search(pattern, content, re.IGNORECASE | re.MULTILINE)
                if match:
                    position = match.start()
                    if position < last_position and spec.position > 0:
                        issues.append(f"Section '{spec.name}' appears out of order")
                    last_position = position
                    break

        return len(issues) == 0, issues

    def validate_no_cross_domain_bleed(
        self,
        content: str,
        domain: LetterDomainType
    ) -> Tuple[bool, List[str]]:
        """Validate that no cross-domain content exists."""
        issues = []

        if domain == LetterDomainType.CIVIL:
            # Check for legal-only terms
            for pattern in LEGAL_ONLY_TERMS:
                if re.search(pattern, content, re.IGNORECASE):
                    issues.append(f"Legal term found in civil letter: {pattern}")

            # Check for forbidden sections
            for spec in LEGAL_SECTION_SPECS:
                if LetterDomainType.CIVIL in spec.forbidden_in_domains:
                    for pattern in spec.header_patterns:
                        if re.search(pattern, content, re.IGNORECASE | re.MULTILINE):
                            issues.append(f"Legal-only section '{spec.name}' found in civil letter")

        return len(issues) == 0, issues

    def validate_mov_position(self, content: str) -> Tuple[bool, str]:
        """Validate that MOV section is in correct position (after Metro2, before Case Law)."""
        mov_match = re.search(r"METHOD OF VERIFICATION|MOV", content, re.IGNORECASE)
        if not mov_match:
            return True, "MOV section not present"

        mov_pos = mov_match.start()

        # Check Metro2 is before MOV
        metro2_match = re.search(r"METRO-?2", content, re.IGNORECASE)
        if metro2_match and metro2_match.start() > mov_pos:
            return False, "Metro2 section should appear before MOV"

        # Check Case Law is after MOV
        case_law_match = re.search(r"CASE LAW|LEGAL PRECEDENT", content, re.IGNORECASE)
        if case_law_match and case_law_match.start() < mov_pos:
            return False, "Case Law section should appear after MOV"

        return True, "MOV position is correct"

    def validate_case_law_position(self, content: str) -> Tuple[bool, str]:
        """Validate that Case Law section is in correct position (after MOV, before Demands)."""
        case_law_match = re.search(r"CASE LAW|LEGAL PRECEDENT", content, re.IGNORECASE)
        if not case_law_match:
            return True, "Case Law section not present"

        case_pos = case_law_match.start()

        # Check MOV is before Case Law
        mov_match = re.search(r"METHOD OF VERIFICATION|MOV", content, re.IGNORECASE)
        if mov_match and mov_match.start() > case_pos:
            return False, "MOV section should appear before Case Law"

        # Check Demands is after Case Law
        demands_match = re.search(r"FORMAL DEMANDS|DEMANDS", content, re.IGNORECASE)
        if demands_match and demands_match.start() < case_pos:
            return False, "Demands section should appear after Case Law"

        return True, "Case Law position is correct"


def create_structural_fixer() -> StructuralFixer:
    """Factory function to create a structural fixer."""
    return StructuralFixer()
