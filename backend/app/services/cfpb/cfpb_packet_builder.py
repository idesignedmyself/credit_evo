"""
CFPB Packet Builder

Builds structured CFPB complaint packets with Metro 2 CRRG citations.
Integrates with CitationInjector to add spec references to each violation.

The packet includes:
- Contradiction table with CRRG column references
- Deduped statute stack (FCRA/ECOA citations)
- Timeline summary
- Escalation recommendations based on violation patterns
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Any, Dict, List, Optional, Set

from app.models.ssot import Consumer, Violation, Severity
from ..metro2 import (
    CitationInjector,
    CRRGCitation,
    get_injector,
)


@dataclass
class CFPBPacket:
    """Structured CFPB complaint packet with citations."""
    consumer_name: str
    entity_name: str
    account_info: str
    contradiction_table: str  # Markdown table
    crrg_citations: List[Dict[str, Any]]
    statute_stack: List[str]  # Deduplicated statutes
    violation_summary: Dict[str, Any]
    timeline_summary: Optional[str] = None
    escalation_recommended: bool = False
    escalation_reasons: List[str] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "consumer_name": self.consumer_name,
            "entity_name": self.entity_name,
            "account_info": self.account_info,
            "contradiction_table": self.contradiction_table,
            "crrg_citations": self.crrg_citations,
            "statute_stack": self.statute_stack,
            "violation_summary": self.violation_summary,
            "timeline_summary": self.timeline_summary,
            "escalation_recommended": self.escalation_recommended,
            "escalation_reasons": self.escalation_reasons,
            "generated_at": self.generated_at.isoformat(),
        }


@dataclass
class TimelineEvent:
    """A single event in the dispute timeline."""
    event_date: date
    event_description: str
    outcome: str


class CFPBPacketBuilder:
    """
    Builds CFPB complaint packets with Metro 2 CRRG citations.

    The packet builder:
    1. Injects CRRG anchor citations into each violation
    2. Builds a contradiction table with spec references
    3. Extracts and deduplicates statute citations
    4. Recommends CFPB escalation based on violation patterns
    """

    # Violation patterns that warrant CFPB escalation
    ESCALATION_TRIGGERS = {
        "STATUS_REGRESSION_REAGING": "Re-aging detected - DOFD manipulation",
        "DEBT_BUYER_DOFD_INVARIANT": "Debt buyer modified locked DOFD",
        "DOFD_MODIFICATION_AFTER_LOCK": "DOFD modified after chargeoff/collection",
        "OVER_7_YEAR_REPORTING": "Account reported beyond 7-year FCRA window",
        "DOUBLE_JEOPARDY": "Double jeopardy - same debt reported with duplicate balances",
        "INVALID_ACCOUNT_STATUS": "Invalid Metro 2 account status code",
        "OBSOLETE_ECOA_CODE": "Obsolete ECOA code still in use",
    }

    # Critical severity always escalates
    CRITICAL_ESCALATION = True

    def __init__(self, injector: Optional[CitationInjector] = None):
        """
        Initialize the packet builder.

        Args:
            injector: CitationInjector instance. Defaults to global singleton.
        """
        self.injector = injector or get_injector()

    def _get_rule_code(self, violation: Violation) -> Optional[str]:
        """Extract rule code from violation."""
        # Check evidence dict first
        if hasattr(violation, 'evidence') and isinstance(violation.evidence, dict):
            rule_code = violation.evidence.get('rule_code')
            if rule_code:
                return rule_code

        # Fall back to violation_type
        if hasattr(violation, 'violation_type'):
            vtype = violation.violation_type
            if hasattr(vtype, 'value'):
                return vtype.value
            return str(vtype)

        return None

    def _collect_citations(self, violations: List[Violation]) -> List[CRRGCitation]:
        """
        Collect CRRG citations from violations (already injected by AuditEngine).

        Citations are attached to violation.citations by the audit engine.
        This method converts citation dicts to CRRGCitation objects.

        Args:
            violations: List of Violation objects with citations already attached

        Returns:
            List of CRRGCitation objects from all violations
        """
        citations = []

        for violation in violations:
            # Read citations from violation.citations (injected by engine.py)
            if not hasattr(violation, 'citations') or not violation.citations:
                continue

            for citation_dict in violation.citations:
                # Convert dict back to CRRGCitation object
                citation = CRRGCitation(
                    anchor_id=citation_dict.get("anchor_id", ""),
                    rule_id=citation_dict.get("rule_id", ""),
                    doc=citation_dict.get("doc", "Metro 2 CRRG"),
                    toc_title=citation_dict.get("toc_title", ""),
                    section_title=citation_dict.get("section_title", ""),
                    page_start=citation_dict.get("page_start", 0),
                    page_end=citation_dict.get("page_end", 0),
                    exhibit_id=citation_dict.get("exhibit_id"),
                    fields=citation_dict.get("fields", []),
                    anchor_summary=citation_dict.get("anchor_summary", ""),
                    fcra_cite=citation_dict.get("fcra_cite", ""),
                    fcra_section_name=citation_dict.get("fcra_section_name"),
                    ecoa_cite=citation_dict.get("ecoa_cite"),
                    effective_date=citation_dict.get("effective_date"),
                    notes=citation_dict.get("notes"),
                )
                citations.append(citation)

        return citations

    def _build_contradiction_table(
        self,
        violations: List[Violation],
        citations: List[CRRGCitation],
    ) -> str:
        """
        Build markdown table of contradictions with CRRG references.

        Args:
            violations: List of violations
            citations: List of CRRG citations

        Returns:
            Markdown-formatted table
        """
        # Build citation lookup by rule code
        citation_lookup: Dict[str, CRRGCitation] = {}
        for citation in citations:
            citation_lookup[citation.rule_id] = citation

        lines = [
            "## Contradictions Found",
            "",
            "| # | Violation | Metro 2 Field | CRRG Reference | FCRA Citation |",
            "|---|-----------|---------------|----------------|---------------|",
        ]

        for i, violation in enumerate(violations, 1):
            rule_code = self._get_rule_code(violation)
            description = violation.description[:50] + "..." if len(violation.description) > 50 else violation.description

            # Get citation data
            citation = None
            if hasattr(violation, 'evidence') and isinstance(violation.evidence, dict):
                crrg_anchor = violation.evidence.get('crrg_anchor')
                if crrg_anchor:
                    field_list = crrg_anchor.get('field_list', '-')
                    section = crrg_anchor.get('toc_title', '-')
                    page_range = crrg_anchor.get('page_range', '-')
                    fcra_cite = crrg_anchor.get('fcra_cite', '-')

                    lines.append(
                        f"| {i} | {description} | {field_list} | {section} ({page_range}) | {fcra_cite} |"
                    )
                    continue

            # Fallback for violations without citation
            lines.append(f"| {i} | {description} | - | - | - |")

        lines.append("")
        return "\n".join(lines)

    def _extract_statute_stack(self, citations: List[CRRGCitation]) -> List[str]:
        """
        Extract and deduplicate statute citations.

        Args:
            citations: List of CRRG citations

        Returns:
            Sorted list of unique statute citations
        """
        statutes: Set[str] = set()

        for citation in citations:
            if citation.fcra_cite:
                statutes.add(citation.fcra_cite)
            if citation.ecoa_cite:
                statutes.add(citation.ecoa_cite)

        return sorted(statutes)

    def _check_escalation(self, violations: List[Violation]) -> tuple[bool, List[str]]:
        """
        Determine if CFPB escalation is recommended.

        Args:
            violations: List of violations

        Returns:
            Tuple of (escalation_recommended, list of reasons)
        """
        reasons = []

        for violation in violations:
            rule_code = self._get_rule_code(violation)

            # Check for escalation triggers
            if rule_code and rule_code in self.ESCALATION_TRIGGERS:
                reasons.append(self.ESCALATION_TRIGGERS[rule_code])

            # Check for critical severity
            if self.CRITICAL_ESCALATION:
                severity = getattr(violation, 'severity', None)
                if severity == Severity.CRITICAL or str(severity).upper() == "CRITICAL":
                    reason = f"Critical violation: {rule_code or violation.description[:30]}"
                    if reason not in reasons:
                        reasons.append(reason)

            # Check evidence for cfpb_recommend flag
            if hasattr(violation, 'evidence') and isinstance(violation.evidence, dict):
                if violation.evidence.get('cfpb_recommend'):
                    reason = f"Violation flagged for CFPB: {rule_code}"
                    if reason not in reasons:
                        reasons.append(reason)

        return len(reasons) > 0, list(set(reasons))

    def _build_violation_summary(self, violations: List[Violation]) -> Dict[str, Any]:
        """
        Build summary statistics of violations.

        Args:
            violations: List of violations

        Returns:
            Dictionary with violation statistics
        """
        by_severity: Dict[str, int] = {}
        by_type: Dict[str, int] = {}

        for violation in violations:
            # Count by severity
            severity = getattr(violation, 'severity', 'UNKNOWN')
            sev_str = severity.value if hasattr(severity, 'value') else str(severity)
            by_severity[sev_str] = by_severity.get(sev_str, 0) + 1

            # Count by type
            rule_code = self._get_rule_code(violation)
            if rule_code:
                by_type[rule_code] = by_type.get(rule_code, 0) + 1

        return {
            "total_violations": len(violations),
            "by_severity": by_severity,
            "by_type": by_type,
            "critical_count": by_severity.get("CRITICAL", 0),
            "high_count": by_severity.get("HIGH", 0),
        }

    def _build_timeline_summary(self, events: List[TimelineEvent]) -> str:
        """
        Build markdown timeline summary.

        Args:
            events: List of timeline events

        Returns:
            Markdown-formatted timeline
        """
        if not events:
            return ""

        lines = [
            "## Dispute Timeline",
            "",
            "| Date | Event | Outcome |",
            "|------|-------|---------|",
        ]

        for event in sorted(events, key=lambda e: e.event_date):
            lines.append(
                f"| {event.event_date.strftime('%Y-%m-%d')} | {event.event_description} | {event.outcome} |"
            )

        lines.append("")
        return "\n".join(lines)

    def build(
        self,
        consumer: Consumer,
        violations: List[Violation],
        entity_name: str,
        account_info: str,
        timeline_events: Optional[List[TimelineEvent]] = None,
    ) -> CFPBPacket:
        """
        Build a complete CFPB complaint packet.

        Args:
            consumer: Consumer information
            violations: List of Violation objects
            entity_name: Name of entity being complained about
            account_info: Account identifier (masked)
            timeline_events: Optional list of dispute timeline events

        Returns:
            CFPBPacket with all components
        """
        # Collect CRRG citations from violations (already injected by AuditEngine)
        citations = self._collect_citations(violations)

        # Build components
        contradiction_table = self._build_contradiction_table(violations, citations)
        statute_stack = self._extract_statute_stack(citations)
        violation_summary = self._build_violation_summary(violations)
        escalation_recommended, escalation_reasons = self._check_escalation(violations)

        # Build timeline if provided
        timeline_summary = None
        if timeline_events:
            timeline_summary = self._build_timeline_summary(timeline_events)

        # Format consumer name
        consumer_name = consumer.full_name

        return CFPBPacket(
            consumer_name=consumer_name,
            entity_name=entity_name,
            account_info=account_info,
            contradiction_table=contradiction_table,
            crrg_citations=[c.to_dict() for c in citations],
            statute_stack=statute_stack,
            violation_summary=violation_summary,
            timeline_summary=timeline_summary,
            escalation_recommended=escalation_recommended,
            escalation_reasons=escalation_reasons,
        )

    def build_escalation_packet(
        self,
        consumer: Consumer,
        violations: List[Violation],
        entity_name: str,
        account_info: str,
        original_case_number: str,
        cra_response_summary: str,
        timeline_events: Optional[List[TimelineEvent]] = None,
    ) -> CFPBPacket:
        """
        Build a CFPB escalation packet (for follow-up complaints).

        Args:
            consumer: Consumer information
            violations: List of Violation objects
            entity_name: Name of entity being complained about
            account_info: Account identifier (masked)
            original_case_number: CFPB case number from initial complaint
            cra_response_summary: Summary of CRA's response to initial complaint
            timeline_events: Optional list of dispute timeline events

        Returns:
            CFPBPacket configured for escalation
        """
        # Build base packet
        packet = self.build(
            consumer=consumer,
            violations=violations,
            entity_name=entity_name,
            account_info=account_info,
            timeline_events=timeline_events,
        )

        # Add escalation context to contradiction table
        escalation_header = f"""## CFPB Escalation - Case #{original_case_number}

**Prior Response Summary:** {cra_response_summary}

**Reason for Escalation:** The prior response failed to address the documented Metro 2 violations below.

"""
        packet.contradiction_table = escalation_header + packet.contradiction_table

        # Force escalation recommendation
        packet.escalation_recommended = True
        if "Prior complaint not adequately addressed" not in packet.escalation_reasons:
            packet.escalation_reasons.insert(0, "Prior complaint not adequately addressed")

        return packet
