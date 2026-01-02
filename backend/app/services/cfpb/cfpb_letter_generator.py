"""
CFPB Letter Generator

Generates CFPB-specific narrative variants for regulatory submissions.
Reuses existing contradiction/severity/remedy objects - only transforms rendering.

Rendering rules:
- Tone: neutral_formal (not aggressive)
- Statute density: low (minimal citations)
- Contradiction visibility: high (explicit facts)
- Remedy language: request (not demand)
- Timeline: mandatory tables
- Rights language: Final only

Three variants:
1. CFPB Initial - Opens supervisory review
2. CFPB Escalation - Exposes perfunctory investigation
3. CFPB Final - Creates examiner-ready record
"""
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import List, Dict, Any, Optional
from app.models.ssot import Violation, Severity, Consumer


@dataclass
class TimelineEvent:
    """A single event in the dispute timeline."""
    event_date: date
    event_description: str
    outcome: str


@dataclass
class CFPBLetter:
    """Generated CFPB letter output."""
    content: str
    stage: str  # initial, escalation, final
    contradictions_included: List[Dict[str, Any]]
    timeline: List[Dict[str, str]]
    generated_at: datetime = field(default_factory=datetime.utcnow)


class CFPBLetterGenerator:
    """
    Generates CFPB complaint letters with neutral, examiner-safe tone.

    Key principle: Same facts, same contradictions - different rendering for CFPB audience.
    """

    def generate(
        self,
        cfpb_stage: str,
        consumer: Consumer,
        contradictions: List[Violation],
        timeline_events: List[TimelineEvent],
        entity_name: str,
        account_info: str,
        cfpb_case_number: Optional[str] = None,
        cra_response_summary: Optional[str] = None,
    ) -> CFPBLetter:
        """
        Generate a CFPB letter for the specified stage.

        Args:
            cfpb_stage: "initial", "escalation", or "final"
            consumer: Consumer information
            contradictions: List of Violation objects from existing engine
            timeline_events: List of dispute timeline events
            entity_name: Name of entity being complained about
            account_info: Account identifier (masked)
            cfpb_case_number: CFPB case number (required for escalation/final)
            cra_response_summary: Summary of CRA response (for escalation/final)

        Returns:
            CFPBLetter with generated content
        """
        if cfpb_stage == "initial":
            content = self._generate_initial(
                consumer, contradictions, timeline_events,
                entity_name, account_info
            )
        elif cfpb_stage == "escalation":
            content = self._generate_escalation(
                consumer, contradictions, timeline_events,
                entity_name, account_info, cfpb_case_number,
                cra_response_summary
            )
        elif cfpb_stage == "final":
            content = self._generate_final(
                consumer, contradictions, timeline_events,
                entity_name, account_info, cfpb_case_number,
                cra_response_summary
            )
        else:
            raise ValueError(f"Invalid CFPB stage: {cfpb_stage}")

        return CFPBLetter(
            content=content,
            stage=cfpb_stage,
            contradictions_included=self._serialize_contradictions(contradictions),
            timeline=self._serialize_timeline(timeline_events),
        )

    def _generate_initial(
        self,
        consumer: Consumer,
        contradictions: List[Violation],
        timeline_events: List[TimelineEvent],
        entity_name: str,
        account_info: str,
    ) -> str:
        """Generate CFPB Initial letter."""
        today = date.today().strftime("%B %d, %Y")

        lines = [
            "CONSUMER FINANCIAL PROTECTION BUREAU COMPLAINT",
            "",
            "Complaint Type: Credit Reporting Dispute",
            f"Date: {today}",
            f"Consumer: {consumer.full_name}",
            f"Account: {account_info}",
            "",
            "FACTUAL SUMMARY",
            "",
            f"I am submitting this complaint regarding inaccurate information being reported",
            f"by {entity_name} on my consumer credit file. I have previously disputed this matter",
            "directly with the credit reporting agency, and their response failed to address",
            "the factual contradictions I documented.",
            "",
            "DOCUMENTED CONTRADICTIONS",
            "",
        ]

        # Add contradictions
        for i, v in enumerate(contradictions, 1):
            severity_label = v.severity.value.title()
            lines.append(f"{i}. {self._format_contradiction_title(v)} ({severity_label})")
            lines.append(f"   - {v.description}")
            if v.expected_value and v.actual_value:
                lines.append(f"   - Expected: {v.expected_value}")
                lines.append(f"   - Actual: {v.actual_value}")
            lines.append("")

        # Add timeline
        lines.append("TIMELINE OF DISPUTE EFFORTS")
        lines.append("")
        lines.append("| Date | Event | Outcome |")
        lines.append("|------|-------|---------|")
        for event in timeline_events:
            date_str = event.event_date.strftime("%B %d, %Y")
            lines.append(f"| {date_str} | {event.event_description} | {event.outcome} |")
        lines.append("")

        # CRA response deficiency
        lines.append("CRA RESPONSE DEFICIENCY")
        lines.append("")
        lines.append(f"{entity_name}'s verification response stated only that the \"information was verified")
        lines.append("with the data furnisher\" without addressing the specific factual impossibilities")
        lines.append("I documented. The response did not explain:")
        lines.append("")
        for v in contradictions[:3]:  # Top 3
            lines.append(f"- {self._format_unanswered_question(v)}")
        lines.append("")

        # Requested action
        lines.append("REQUESTED ACTION")
        lines.append("")
        lines.append("I request that the CFPB review this matter and facilitate a response from")
        lines.append(f"{entity_name} that addresses the specific factual contradictions documented above,")
        lines.append("rather than a generic verification statement.")
        lines.append("")

        # Attachments (suggested)
        lines.append("ATTACHMENTS")
        lines.append("- Original dispute letter")
        lines.append("- Certified mail receipt")
        lines.append(f"- {entity_name} response letter")
        lines.append("- Credit report excerpt showing contradictory data")

        return "\n".join(lines)

    def _generate_escalation(
        self,
        consumer: Consumer,
        contradictions: List[Violation],
        timeline_events: List[TimelineEvent],
        entity_name: str,
        account_info: str,
        cfpb_case_number: Optional[str],
        cra_response_summary: Optional[str],
    ) -> str:
        """Generate CFPB Escalation letter."""
        today = date.today().strftime("%B %d, %Y")
        case_ref = cfpb_case_number or "[CASE NUMBER]"

        lines = [
            "CONSUMER FINANCIAL PROTECTION BUREAU COMPLAINT - ESCALATION",
            "",
            "Complaint Type: Credit Reporting Dispute - Unresolved",
            f"CFPB Case Number: {case_ref}",
            f"Date: {today}",
            f"Consumer: {consumer.full_name}",
            f"Account: {account_info}",
            "",
            "ESCALATION BASIS",
            "",
            f"This is an escalation of CFPB Case #{case_ref}. The company's response",
            "to my initial CFPB complaint failed to address the factual contradictions",
            "I documented. The contradictions remain on my credit file.",
            "",
            "UNANSWERED MATERIAL FACTS",
            "",
        ]

        # Add contradictions as unanswered facts
        for i, v in enumerate(contradictions, 1):
            lines.append(f"{i}. {self._format_contradiction_title(v)} - UNADDRESSED")
            lines.append(f"   - {v.description}")
            lines.append("   - Company response did not explain this impossibility")
            lines.append("")

        # Company response analysis
        lines.append("COMPANY RESPONSE ANALYSIS")
        lines.append("")
        if cra_response_summary:
            lines.append(cra_response_summary)
        else:
            lines.append("The company's response to my CFPB complaint stated:")
            lines.append("\"We have reviewed the consumer's dispute and verified the information")
            lines.append("with our records. The account information is accurate.\"")
        lines.append("")
        lines.append("This response is deficient because:")
        lines.append("")
        for i, v in enumerate(contradictions[:4], 1):
            lines.append(f"{i}. It does not explain {self._format_unanswered_question(v).lower()}")
        lines.append("")

        # Timeline
        lines.append("TIMELINE")
        lines.append("")
        lines.append("| Date | Event | Outcome |")
        lines.append("|------|-------|---------|")
        for event in timeline_events:
            date_str = event.event_date.strftime("%b %d, %Y")
            lines.append(f"| {date_str} | {event.event_description} | {event.outcome} |")
        lines.append("")

        # Requested action
        lines.append("REQUESTED ACTION")
        lines.append("")
        lines.append("I request that the CFPB:")
        lines.append("1. Require the company to specifically address each documented contradiction")
        for i, v in enumerate(contradictions[:2], 2):
            lines.append(f"{i}. Require documentation supporting {v.metro2_field or 'the reported data'}")
        lines.append("")

        # Attachments
        lines.append("ATTACHMENTS")
        lines.append(f"- Original CFPB complaint (Case #{case_ref})")
        lines.append("- Company response")
        lines.append("- Updated credit report showing unchanged contradictions")

        return "\n".join(lines)

    def _generate_final(
        self,
        consumer: Consumer,
        contradictions: List[Violation],
        timeline_events: List[TimelineEvent],
        entity_name: str,
        account_info: str,
        cfpb_case_number: Optional[str],
        cra_response_summary: Optional[str],
    ) -> str:
        """Generate CFPB Final letter with rights reservation."""
        today = date.today().strftime("%B %d, %Y")
        case_ref = cfpb_case_number or "[CASE NUMBER]"

        # Calculate days elapsed
        if timeline_events:
            first_date = min(e.event_date for e in timeline_events)
            days_elapsed = (date.today() - first_date).days
        else:
            days_elapsed = 0

        lines = [
            "CONSUMER FINANCIAL PROTECTION BUREAU COMPLAINT - FINAL SUBMISSION",
            "",
            "Complaint Type: Credit Reporting Dispute - Exhausted Remedies",
            f"CFPB Case Number: {case_ref}",
            f"Date: {today}",
            f"Consumer: {consumer.full_name}",
            f"Account: {account_info}",
            "",
            "FINAL SUBMISSION NOTICE",
            "",
            f"This is my final submission regarding CFPB Case #{case_ref}. Despite",
            "two rounds of CFPB-facilitated review, the documented factual contradictions",
            "remain unaddressed. I am creating this final record for regulatory purposes.",
            "",
            "COMPLETE ENFORCEMENT TIMELINE",
            "",
            "| Date | Event | Outcome |",
            "|------|-------|---------|",
        ]

        for event in timeline_events:
            date_str = event.event_date.strftime("%b %d, %Y")
            lines.append(f"| {date_str} | {event.event_description} | {event.outcome} |")
        lines.append("")

        # Contradictions summary table
        lines.append("CONTRADICTIONS SUMMARY (ALL UNRESOLVED)")
        lines.append("")
        lines.append("| ID | Type | Severity | Status |")
        lines.append("|----|------|----------|--------|")
        for i, v in enumerate(contradictions, 1):
            rule_code = v.evidence.get("rule_code", f"V{i}") if v.evidence else f"V{i}"
            lines.append(f"| {rule_code} | {self._format_contradiction_title(v)} | {v.severity.value.upper()} | Unresolved |")
        lines.append("")

        # Investigation failures
        lines.append("DOCUMENTED INVESTIGATION FAILURES")
        lines.append("")
        lines.append("Across three dispute cycles, the credit reporting agency has:")
        lines.append("")
        for i, v in enumerate(contradictions, 1):
            lines.append(f"{i}. Never explained {self._format_unanswered_question(v).lower()}")
        lines.append(f"{len(contradictions) + 1}. Used identical response language in all responses")
        lines.append("")

        # Examiner-ready summary
        lines.append("EXAMINER-READY SUMMARY")
        lines.append("")
        lines.append("For regulatory review purposes, this case demonstrates:")
        lines.append("")
        lines.append(f"- Factual contradictions: {len(contradictions)} documented impossibilities")
        lines.append(f"- Dispute attempts: 3 (direct + 2 CFPB rounds)")
        lines.append(f"- Days elapsed: {days_elapsed} days")
        lines.append("- Contradictions addressed: 0")
        lines.append("- Response pattern: Generic verification without factual review")
        lines.append("")

        # Evidence packet
        lines.append("EVIDENCE PACKET")
        lines.append("")
        lines.append("1. Credit report excerpt - showing contradictions")
        lines.append("2. Direct dispute letter")
        lines.append("3. Certified mail receipt - direct dispute")
        lines.append(f"4. {entity_name} response")
        lines.append("5. CFPB Initial complaint")
        lines.append("6. Company CFPB response #1")
        lines.append("7. CFPB Escalation complaint")
        lines.append("8. Company CFPB response #2")
        lines.append("9. Current credit report - contradictions unchanged")
        lines.append("")

        # Requested regulatory action
        lines.append("REQUESTED REGULATORY ACTION")
        lines.append("")
        lines.append("I request that this matter be referred for supervisory review. The pattern")
        lines.append("of generic responses without factual investigation, maintained across")
        lines.append("multiple dispute cycles, warrants examination of the company's dispute")
        lines.append("handling procedures.")
        lines.append("")

        # Rights reservation - FINAL ONLY
        lines.append("I reserve all rights under applicable consumer protection statutes.")
        lines.append("")
        lines.append("---")
        lines.append(f"Consumer Signature: {consumer.full_name}")
        lines.append(f"Date: {today}")

        return "\n".join(lines)

    def _format_contradiction_title(self, v: Violation) -> str:
        """Format contradiction type as human-readable title."""
        type_map = {
            "dofd_after_date_opened": "Temporal Impossibility",
            "payment_history_exceeds_account_age": "Temporal Impossibility",
            "chargeoff_before_last_payment": "Temporal Impossibility",
            "delinquency_ladder_inversion": "Temporal Impossibility",
            "balance_exceeds_legal_max": "Mathematical Impossibility",
            "balance_increase_after_chargeoff": "Mathematical Impossibility",
            "dofd_inferred_mismatch": "DOFD Contradiction",
            "chargeoff_missing_dofd": "Missing Required Field",
            "obsolete_account": "Reporting Period Violation",
        }
        return type_map.get(v.violation_type.value, v.violation_type.value.replace("_", " ").title())

    def _format_unanswered_question(self, v: Violation) -> str:
        """Format contradiction as an unanswered question."""
        if "dofd" in v.violation_type.value.lower():
            return "How the Date of First Delinquency can precede the account open date"
        elif "balance" in v.violation_type.value.lower() and "increase" in v.violation_type.value.lower():
            return "How a charged-off balance can increase without documented activity"
        elif "temporal" in v.violation_type.value.lower() or "timeline" in v.violation_type.value.lower():
            return "How the reported timeline is logically possible"
        elif "missing" in v.violation_type.value.lower():
            return "Why required regulatory fields are missing"
        else:
            return f"The {v.violation_type.value.replace('_', ' ')} contradiction"

    def _serialize_contradictions(self, contradictions: List[Violation]) -> List[Dict[str, Any]]:
        """Serialize contradictions for API response."""
        return [
            {
                "violation_id": v.violation_id,
                "type": v.violation_type.value,
                "severity": v.severity.value,
                "description": v.description,
                "creditor_name": v.creditor_name,
            }
            for v in contradictions
        ]

    def _serialize_timeline(self, events: List[TimelineEvent]) -> List[Dict[str, str]]:
        """Serialize timeline for API response."""
        return [
            {
                "date": e.event_date.isoformat(),
                "event": e.event_description,
                "outcome": e.outcome,
            }
            for e in events
        ]
