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
        """Generate CFPB Initial letter with proper regulatory framing."""
        today = date.today().strftime("%B %d, %Y")

        # Group violations by type
        violations_by_type = self._group_violations_by_type(contradictions)

        lines = [
            "CONSUMER FINANCIAL PROTECTION BUREAU COMPLAINT",
            "",
            "Complaint Type: Credit Reporting Dispute",
            f"Date: {today}",
            f"Consumer: {consumer.full_name}",
            f"Entity Complained Against: {entity_name}",
            "",
            "=" * 60,
            "",
            "FACTUAL SUMMARY",
            "",
            f"I am filing this complaint against {entity_name} for reporting inaccurate",
            "information on my consumer credit file. I previously disputed this matter",
            "directly with the credit reporting agency. Their reinvestigation response",
            "failed to address the specific factual inaccuracies I identified and consisted",
            "only of a generic verification statement.",
            "",
            "=" * 60,
            "",
            "STATUTORY BASIS",
            "",
            "This complaint concerns violations of the Fair Credit Reporting Act (FCRA),",
            "including but not limited to:",
            "",
        ]

        # Determine which statutes apply based on violation types
        statutes = self._get_applicable_statutes(contradictions)
        for statute in statutes:
            lines.append(f"• {statute}")
        lines.append("")

        # Issues Presented - grouped by type
        lines.append("=" * 60)
        lines.append("")
        lines.append("ISSUES PRESENTED")
        lines.append("")

        issue_num = 1
        for violation_type, violations in violations_by_type.items():
            lines.append(f"{issue_num}. {self._format_issue_title(violation_type)}")
            lines.append("")

            # Get the statutory context for this violation type
            statutory_context = self._get_violation_statutory_context(violation_type)
            if statutory_context:
                lines.append(statutory_context)
                lines.append("")

            lines.append("Affected accounts:")
            for v in violations:
                acct = getattr(v, "account_number_masked", None)
                if acct and acct.strip():
                    lines.append(f"  • {v.creditor_name} — Account: {acct}")
                else:
                    lines.append(f"  • {v.creditor_name} — Account: (masked)")
            lines.append("")
            issue_num += 1

        # Timeline - collapse duplicates and use meaningful descriptions
        lines.append("=" * 60)
        lines.append("")
        lines.append("TIMELINE OF ACTIONS")
        lines.append("")

        if timeline_events:
            # Deduplicate timeline events by (date, description)
            seen = set()
            unique_events = []
            for event in timeline_events:
                key = (event.event_date, event.event_description)
                if key not in seen:
                    seen.add(key)
                    unique_events.append(event)

            for event in sorted(unique_events, key=lambda e: e.event_date):
                date_str = event.event_date.strftime("%m/%d/%Y")
                lines.append(f"• {date_str} — {event.event_description}")
        else:
            # Default timeline if none provided - use realistic flow
            lines.append(f"• [DATE] — Consumer filed written dispute with {entity_name}")
            lines.append(f"• [DATE] — {entity_name} responded with generic verification")
            lines.append(f"• {today} — CFPB complaint filed due to inadequate reinvestigation")
        lines.append("")

        # CRA Response Deficiency - statute-anchored
        lines.append("=" * 60)
        lines.append("")
        lines.append("REINVESTIGATION DEFICIENCY")
        lines.append("")
        lines.append(f"Despite my formal dispute, {entity_name} responded that the accounts were")
        lines.append("\"verified as accurate\" without addressing the specific inaccuracies documented.")
        lines.append("")
        lines.append("The reinvestigation appears to have consisted solely of querying the furnisher,")
        lines.append("rather than independently verifying the data as required under 15 U.S.C. § 1681i(a).")
        lines.append("")
        lines.append("Specifically, the response failed to:")
        lines.append("")

        # List specific failures based on violation types
        for vtype in list(violations_by_type.keys())[:3]:
            failure = self._get_reinvestigation_failure(vtype)
            lines.append(f"• {failure}")
        # Factual impossibility argument
        lines.append("• Explain how the accounts could be \"verified as accurate\" when the")
        lines.append("  Date of First Delinquency — the sole trigger for the seven-year purge")
        lines.append("  under 15 U.S.C. § 1681c(c) — is absent, rendering any assertion of")
        lines.append("  reporting accuracy a factual impossibility.")
        lines.append("")
        lines.append("Therefore, the dispute was not reasonably investigated as required by law.")
        lines.append("")

        # Consumer Impact and Prejudice section
        lines.append("=" * 60)
        lines.append("")
        lines.append("CONSUMER IMPACT AND PREJUDICE")
        lines.append("")
        lines.append("Without the DOFD, I cannot determine whether these accounts are reporting")
        lines.append("beyond the seven-year statutory limit. This missing mandatory field effectively")
        lines.append("grants the furnisher an unlimited reporting period in violation of")
        lines.append("15 U.S.C. § 1681c(a), suppressing my creditworthiness and access to credit.")
        lines.append("")

        # Requested Resolution - precision legal language
        lines.append("=" * 60)
        lines.append("")
        lines.append("REQUESTED RESOLUTION")
        lines.append("")
        lines.append(f"I request that the CFPB compel {entity_name} to fulfill its statutory")
        lines.append("obligations by performing the following:")
        lines.append("")

        lines.append("1. Mandatory Correction or Deletion")
        lines.append("   Provide the original Date of First Delinquency (Metro-2 Field 25) used")
        lines.append("   for reporting purposes, obtained from original source records. If the")
        lines.append("   DOFD cannot be verified from the furnisher's records, the accounts must")
        lines.append("   be deleted pursuant to 15 U.S.C. § 1681i(a)(5)(A).")
        lines.append("")

        lines.append("2. Procedural Disclosure")
        lines.append("   Provide a full description of the reinvestigation procedures conducted")
        lines.append("   in response to my dispute, including:")
        lines.append("   • the records reviewed,")
        lines.append("   • whether an ACDV/e-OSCAR system was used,")
        lines.append("   • and the identity or department of the individual(s) at the furnishing")
        lines.append("     entity who certified the accuracy of the data.")
        lines.append("")

        lines.append("3. Certification of Accuracy")
        lines.append("   Provide a written explanation describing how the accounts were deemed")
        lines.append("   \"verified as accurate\" while the legally-determinative DOFD field")
        lines.append("   remains null or unreported, and identify the DOFD value relied upon")
        lines.append("   in making that determination.")
        lines.append("")

        # Attachments
        lines.append("=" * 60)
        lines.append("")
        lines.append("ATTACHMENTS PROVIDED")
        lines.append("")
        lines.append("• Copy of dispute letter sent to CRA")
        lines.append("• Certified mail receipt (if applicable)")
        lines.append(f"• {entity_name} response letter")
        lines.append("• Credit report excerpts showing disputed information")
        lines.append("")
        lines.append("=" * 60)
        lines.append("")
        lines.append(f"Submitted by: {consumer.full_name}")
        lines.append(f"Date: {today}")

        return "\n".join(lines)

    def _extract_account_suffix(self, v: Violation) -> str:
        """Extract last 4 visible digits from account number, handling masked format."""
        acct = getattr(v, "account_number_masked", None)
        if not acct:
            return "(masked)"

        # Remove asterisks and get last 4 visible digits
        visible_digits = acct.replace("*", "").replace("-", "").replace(" ", "")
        if len(visible_digits) >= 4:
            return visible_digits[-4:]
        elif visible_digits:
            return visible_digits
        else:
            return "(masked)"

    def _group_violations_by_type(self, contradictions: List[Violation]) -> Dict[str, List[Violation]]:
        """Group violations by their type for consolidated reporting."""
        grouped: Dict[str, List[Violation]] = {}
        for v in contradictions:
            vtype = v.violation_type.value
            if vtype not in grouped:
                grouped[vtype] = []
            grouped[vtype].append(v)
        return grouped

    def _get_applicable_statutes(self, contradictions: List[Violation]) -> List[str]:
        """Determine which FCRA statutes apply based on violation types."""
        statutes = set()
        statutes.add("15 U.S.C. § 1681e(b) — Duty to assure maximum possible accuracy")
        statutes.add("15 U.S.C. § 1681i(a) — Duty to conduct reasonable reinvestigation")

        for v in contradictions:
            vtype = v.violation_type.value.lower()
            if "dofd" in vtype or "missing" in vtype:
                statutes.add("15 U.S.C. § 1681s-2(a)(1)(A) — Furnishing information known to be inaccurate")
            if "obsolete" in vtype or "dofd" in vtype:
                statutes.add("15 U.S.C. § 1681c(a) — Obsolescence period / 7-year reporting limit")
            if "chargeoff" in vtype:
                statutes.add("15 U.S.C. § 1681s-2(b) — Furnisher investigation duties")

        return sorted(list(statutes))

    def _format_issue_title(self, violation_type: str) -> str:
        """Format violation type as a proper issue title."""
        title_map = {
            "missing_dofd": "Missing Date of First Delinquency (Metro-2 Field 25)",
            "chargeoff_missing_dofd": "Charge-Off Account Missing Required DOFD",
            "obsolete_account": "Account Exceeds 7-Year Reporting Period",
            "stale_reporting": "Stale/Outdated Reporting",
            "balance_increase_after_chargeoff": "Balance Increased After Charge-Off",
            "missing_date_opened": "Missing Date Opened Field",
            "missing_scheduled_payment": "Missing Scheduled Payment Amount",
            "dofd_after_date_opened": "DOFD Precedes Account Open Date (Temporal Impossibility)",
            "payment_history_exceeds_account_age": "Payment History Exceeds Account Age",
        }
        return title_map.get(violation_type, violation_type.replace("_", " ").title())

    def _get_violation_statutory_context(self, violation_type: str) -> str:
        """Get statutory context explanation for a violation type."""
        context_map = {
            "missing_dofd": (
                "The Date of First Delinquency (DOFD) is a mandatory field under Metro-2 reporting "
                "standards for any account that has experienced delinquency. Under FCRA § 1681c(a), "
                "this date determines when the 7-year reporting period begins. Without DOFD, the "
                "obsolescence calculation required by law cannot be performed."
            ),
            "chargeoff_missing_dofd": (
                "Charge-off accounts must include a Date of First Delinquency per Metro-2 Field 25. "
                "The absence of this required field on a derogatory account violates the CRA's duty "
                "under § 1681e(b) to maintain maximum possible accuracy."
            ),
            "obsolete_account": (
                "Under FCRA § 1681c(a), adverse information generally cannot be reported after 7 years "
                "from the date of first delinquency. This account has exceeded that statutory limit "
                "and must be deleted."
            ),
            "balance_increase_after_chargeoff": (
                "A charged-off account balance cannot increase absent documented post-charge-off "
                "activity. An unexplained balance increase suggests reporting error or data corruption."
            ),
        }
        return context_map.get(violation_type, "")

    def _get_reinvestigation_failure(self, violation_type: str) -> str:
        """Get specific reinvestigation failure for a violation type."""
        failure_map = {
            "missing_dofd": "Provide or verify the Date of First Delinquency",
            "chargeoff_missing_dofd": "Explain why DOFD is missing from charge-off account",
            "obsolete_account": "Verify the account has not exceeded the 7-year reporting period",
            "stale_reporting": "Confirm the reported data reflects current account status",
            "balance_increase_after_chargeoff": "Explain the basis for post-charge-off balance increase",
            "missing_date_opened": "Verify the account open date from original records",
            "missing_scheduled_payment": "Provide the scheduled payment amount",
        }
        return failure_map.get(violation_type, f"Address the {violation_type.replace('_', ' ')} issue")

    def _get_requested_resolutions(self, violations_by_type: Dict[str, List[Violation]]) -> List[str]:
        """Generate specific resolution requests based on violation types."""
        resolutions = []

        for vtype in violations_by_type.keys():
            if "dofd" in vtype.lower() or "missing" in vtype.lower():
                resolutions.append(
                    "Provide the original source documentation for disputed data fields, OR "
                    "delete the accounts if documentation cannot be produced"
                )
                break

        if any("obsolete" in vt.lower() for vt in violations_by_type.keys()):
            resolutions.append("Delete any accounts that have exceeded the 7-year reporting period under § 1681c(a)")

        resolutions.append("Provide a detailed description of the reinvestigation procedures used")
        resolutions.append("Identify the documents and records reviewed during verification")
        resolutions.append("Cease reporting inaccurate or unverifiable information")
        resolutions.append("Provide written confirmation of corrections made")

        return resolutions

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
