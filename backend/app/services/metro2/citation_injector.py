"""
CRRG Citation Injector

Injects Metro 2 CRRG (Credit Reporting Resource Guide) citations into violations,
providing page references, section titles, and FCRA statute links.
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional, List
from dataclasses import dataclass, field


@dataclass
class CRRGCitation:
    """Structured CRRG citation data."""
    anchor_id: str
    rule_id: str
    doc: str
    toc_title: str
    section_title: str
    page_start: int
    page_end: int
    exhibit_id: Optional[str]
    fields: List[str]
    anchor_summary: str
    fcra_cite: str
    fcra_section_name: Optional[str] = None
    ecoa_cite: Optional[str] = None
    effective_date: Optional[str] = None
    notes: Optional[str] = None

    def page_range(self) -> str:
        """Return formatted page range string."""
        if self.page_start == self.page_end:
            return f"p. {self.page_start}"
        return f"pp. {self.page_start}-{self.page_end}"

    def field_list(self) -> str:
        """Return comma-separated field list."""
        return ", ".join(self.fields)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "anchor_id": self.anchor_id,
            "rule_id": self.rule_id,
            "doc": self.doc,
            "toc_title": self.toc_title,
            "section_title": self.section_title,
            "page_range": self.page_range(),
            "page_start": self.page_start,
            "page_end": self.page_end,
            "exhibit_id": self.exhibit_id,
            "fields": self.fields,
            "field_list": self.field_list(),
            "anchor_summary": self.anchor_summary,
            "fcra_cite": self.fcra_cite,
            "fcra_section_name": self.fcra_section_name,
            "ecoa_cite": self.ecoa_cite,
            "effective_date": self.effective_date,
            "notes": self.notes,
        }


@dataclass
class InjectionResult:
    """Result of citation injection."""
    success: bool
    citation: Optional[CRRGCitation] = None
    error: Optional[str] = None
    rule_code: Optional[str] = None


class CitationInjector:
    """
    Injects CRRG citations into violations based on rule codes.

    Loads anchor mappings from crrg_anchors.json and provides methods
    to enrich violations with Metro 2 spec references.
    """

    def __init__(self, anchors_path: Optional[Path] = None):
        """
        Initialize the citation injector.

        Args:
            anchors_path: Path to crrg_anchors.json. Defaults to configs directory.
        """
        if anchors_path is None:
            # Default to configs directory relative to this file
            anchors_path = Path(__file__).parent.parent.parent.parent / "configs" / "crrg_anchors.json"

        self._anchors_path = anchors_path
        self._anchors: Dict[str, Any] = {}
        self._rule_to_anchor: Dict[str, str] = {}
        self._statute_map: Dict[str, Any] = {}
        self._loaded = False

    def _load_anchors(self) -> None:
        """Load anchor definitions from JSON file."""
        if self._loaded:
            return

        try:
            with open(self._anchors_path, "r") as f:
                data = json.load(f)

            self._anchors = data.get("anchors", {})
            # Normalize rule_to_anchor keys to lowercase for case-insensitive lookup
            raw_rule_to_anchor = data.get("rule_to_anchor", {})
            self._rule_to_anchor = {k.lower(): v for k, v in raw_rule_to_anchor.items()}
            self._statute_map = data.get("statute_map", {})
            self._loaded = True
        except FileNotFoundError:
            raise RuntimeError(f"CRRG anchors file not found: {self._anchors_path}")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid JSON in CRRG anchors file: {e}")

    def get_anchor_for_rule(self, rule_code: str) -> Optional[str]:
        """
        Get the anchor ID for a given rule code.

        Args:
            rule_code: The rule code (e.g., "T1", "D1", "INVALID_ACCOUNT_STATUS")

        Returns:
            Anchor ID if found, None otherwise.
        """
        self._load_anchors()
        return self._rule_to_anchor.get(rule_code)

    def get_citation(self, anchor_id: str) -> Optional[CRRGCitation]:
        """
        Get a structured citation for an anchor ID.

        Args:
            anchor_id: The anchor ID (e.g., "FIELD_17A", "FIELD_24")

        Returns:
            CRRGCitation if found, None otherwise.
        """
        self._load_anchors()

        anchor_data = self._anchors.get(anchor_id)
        if not anchor_data:
            return None

        # Get statute section name from statute_map if available
        statute_info = self._statute_map.get(anchor_id, {})

        return CRRGCitation(
            anchor_id=anchor_id,
            rule_id=anchor_data.get("rule_id", ""),
            doc=anchor_data.get("doc", "Metro 2 CRRG"),
            toc_title=anchor_data.get("toc_title", ""),
            section_title=anchor_data.get("section_title", ""),
            page_start=anchor_data.get("page_start", 0),
            page_end=anchor_data.get("page_end", 0),
            exhibit_id=anchor_data.get("exhibit_id"),
            fields=anchor_data.get("fields", []),
            anchor_summary=anchor_data.get("anchor_summary", ""),
            fcra_cite=anchor_data.get("fcra_cite", ""),
            fcra_section_name=statute_info.get("section_name"),
            ecoa_cite=anchor_data.get("ecoa_cite"),
            effective_date=anchor_data.get("effective_date"),
            notes=anchor_data.get("notes"),
        )

    def inject_into_violation(self, violation: Any, rule_code: Optional[str] = None) -> InjectionResult:
        """
        Inject CRRG citation directly into violation.citations list.

        This is the ONLY method that should be used to attach citations to violations.
        Citations are attached to the violation object itself, NOT to evidence dict.

        Args:
            violation: The Violation object to enrich (must have .citations attribute)
            rule_code: Optional rule code override. If not provided, extracted from violation.

        Returns:
            InjectionResult with success status and citation data
        """
        self._load_anchors()

        # Extract rule_code from violation if not provided
        if rule_code is None:
            if hasattr(violation, 'violation_type'):
                vtype = violation.violation_type
                rule_code = vtype.value if hasattr(vtype, 'value') else str(vtype)
            else:
                return InjectionResult(
                    success=False,
                    error="Cannot extract rule_code from violation",
                    rule_code=None
                )

        # Normalize to lowercase for lookup (all keys in _rule_to_anchor are lowercase)
        rule_code_normalized = rule_code.lower()

        # Get anchor ID for this rule
        anchor_id = self._rule_to_anchor.get(rule_code_normalized)
        if not anchor_id:
            return InjectionResult(
                success=False,
                error=f"No anchor mapping for rule: {rule_code}",
                rule_code=rule_code
            )

        # Get citation data
        citation = self.get_citation(anchor_id)
        if not citation:
            return InjectionResult(
                success=False,
                error=f"Anchor not found: {anchor_id}",
                rule_code=rule_code
            )

        # Attach citation to violation.citations (NOT evidence)
        if hasattr(violation, 'citations'):
            violation.citations.append(citation.to_dict())
        else:
            return InjectionResult(
                success=False,
                error="Violation object has no citations attribute",
                rule_code=rule_code
            )

        return InjectionResult(
            success=True,
            citation=citation,
            rule_code=rule_code
        )

    def get_all_citations_for_rules(self, rule_codes: List[str]) -> Dict[str, CRRGCitation]:
        """
        Get all citations for a list of rule codes.

        Args:
            rule_codes: List of rule codes

        Returns:
            Dict mapping rule codes to their citations (only for rules with citations)
        """
        self._load_anchors()

        result = {}
        for rule_code in rule_codes:
            anchor_id = self._rule_to_anchor.get(rule_code)
            if anchor_id:
                citation = self.get_citation(anchor_id)
                if citation:
                    result[rule_code] = citation
        return result

    def format_for_letter(self, citation: CRRGCitation) -> str:
        """
        Format a citation for inclusion in a dispute letter.

        Args:
            citation: The citation to format

        Returns:
            Formatted string suitable for letter inclusion
        """
        parts = [
            f"Per {citation.doc}, {citation.section_title} ({citation.page_range()}):",
            f'"{citation.anchor_summary}"',
        ]

        if citation.fcra_cite:
            fcra_parts = [citation.fcra_cite]
            if citation.fcra_section_name:
                fcra_parts.append(f"({citation.fcra_section_name})")
            parts.append(f"FCRA: {' '.join(fcra_parts)}")

        if citation.ecoa_cite:
            parts.append(f"ECOA: {citation.ecoa_cite}")

        return "\n".join(parts)

    def build_citation_table(self, citations: List[CRRGCitation]) -> str:
        """
        Build a markdown table of citations for CFPB packets.

        Args:
            citations: List of citations to include

        Returns:
            Markdown-formatted table
        """
        if not citations:
            return ""

        lines = [
            "| Field | Section | Page | FCRA Citation |",
            "|-------|---------|------|---------------|",
        ]

        for citation in citations:
            fcra = citation.fcra_cite
            if citation.fcra_section_name:
                fcra = f"{fcra} ({citation.fcra_section_name})"

            lines.append(
                f"| {citation.field_list()} | {citation.toc_title} | {citation.page_range()} | {fcra} |"
            )

        return "\n".join(lines)

    def get_statute_stack(self, citations: List[CRRGCitation]) -> List[str]:
        """
        Extract deduplicated statute citations from a list of citations.

        Args:
            citations: List of citations

        Returns:
            Deduplicated list of statute citations
        """
        statutes = set()
        for citation in citations:
            if citation.fcra_cite:
                statutes.add(citation.fcra_cite)
            if citation.ecoa_cite:
                statutes.add(citation.ecoa_cite)
        return sorted(statutes)


# Module-level singleton for convenience
_default_injector: Optional[CitationInjector] = None


def get_injector() -> CitationInjector:
    """Get or create the default citation injector singleton."""
    global _default_injector
    if _default_injector is None:
        _default_injector = CitationInjector()
    return _default_injector


def inject_citation_into_violation(violation: Any, rule_code: Optional[str] = None) -> InjectionResult:
    """
    Convenience function to inject a citation using the default injector.

    Args:
        violation: The Violation object to enrich (must have .citations attribute)
        rule_code: Optional rule code override. If not provided, extracted from violation.

    Returns:
        InjectionResult with success status and citation data
    """
    return get_injector().inject_into_violation(violation, rule_code)
