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
        has_prior_cra_dispute: bool = False,
        has_prior_cra_response: bool = False,
        discrepancies: Optional[List[Dict[str, Any]]] = None,
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
            has_prior_cra_dispute: Whether user filed CRA dispute before CFPB
            has_prior_cra_response: Whether CRA responded before CFPB filing
            discrepancies: List of cross-bureau discrepancy dicts (optional)

        Returns:
            CFPBLetter with generated content

        Route-Dependent Wording:
            Mail-First Route (has_prior_cra_response=True):
                - References prior CRA dispute and response
                - Uses "REINVESTIGATION DEFICIENCY" section

            CFPB-First Route (has_prior_cra_response=False):
                - NO claims about prior CRA dispute/response
                - Uses "FAILURE TO ASSURE MAXIMUM POSSIBLE ACCURACY" section
        """
        if cfpb_stage == "initial":
            content = self._generate_initial(
                consumer, contradictions, timeline_events,
                entity_name, account_info,
                has_prior_cra_dispute, has_prior_cra_response,
                discrepancies or []
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

    def _format_entity_name(self, entity_name: str) -> str:
        """Format entity name properly (e.g., 'transunion' -> 'TransUnion LLC')."""
        entity_map = {
            "transunion": "TransUnion LLC",
            "equifax": "Equifax Inc.",
            "experian": "Experian Information Solutions, Inc.",
        }
        lower_name = entity_name.lower().strip()
        return entity_map.get(lower_name, entity_name.title())

    def _generate_initial(
        self,
        consumer: Consumer,
        contradictions: List[Violation],
        timeline_events: List[TimelineEvent],
        entity_name: str,
        account_info: str,
        has_prior_cra_dispute: bool = False,
        has_prior_cra_response: bool = False,
        discrepancies: List[Dict[str, Any]] = None,
    ) -> str:
        """Generate CFPB Initial letter - examiner-grade, litigation-ready format.

        Route-dependent wording:
        - Mail-First (has_prior_cra_response=True): References CRA dispute/response
        - CFPB-First (has_prior_cra_response=False): No claims about prior CRA actions
        """
        discrepancies = discrepancies or []
        today = date.today().strftime("%B %d, %Y")
        formatted_entity = self._format_entity_name(entity_name)

        # Group violations by type
        violations_by_type = self._group_violations_by_type(contradictions)
        all_violation_types = list(violations_by_type.keys())

        lines = [
            "CONSUMER FINANCIAL PROTECTION BUREAU COMPLAINT",
            "",
            "Complaint Type: Credit Reporting Dispute",
            f"Date: {today}",
            f"Consumer: {consumer.full_name}",
            f"Entity Complained Against: {formatted_entity}",
            "",
            "=" * 60,
            "",
            "FACTUAL SUMMARY",
            "",
        ]

        # Route-dependent FACTUAL SUMMARY
        if has_prior_cra_response:
            # Mail-First Route: CRA dispute + response occurred
            lines.extend([
                f"I am filing this complaint against {formatted_entity} for reporting inaccurate",
                "information on my consumer credit file. I previously disputed these matters",
                f"directly with the credit reporting agency. {formatted_entity}'s reinvestigation",
                "response failed to address the specific factual inaccuracies identified and",
                "consisted only of a generic verification statement.",
            ])
        elif has_prior_cra_dispute:
            # CRA dispute filed but no response yet
            lines.extend([
                f"I am filing this complaint against {formatted_entity} for reporting inaccurate",
                "information on my consumer credit file. I previously submitted a dispute",
                f"directly to {formatted_entity} identifying specific factual inaccuracies.",
                f"{formatted_entity} has not yet provided a substantive response addressing",
                "the documented defects in my credit file.",
            ])
        else:
            # CFPB-First Route: No prior CRA dispute
            lines.extend([
                f"I am filing this complaint against {formatted_entity} for reporting inaccurate",
                "information on my consumer credit file. My credit report contains specific,",
                "verifiable inaccuracies that violate the Fair Credit Reporting Act's requirement",
                "for maximum possible accuracy under 15 U.S.C. § 1681e(b).",
            ])

        lines.extend([
            "",
            "=" * 60,
            "",
            "STATUTORY BASIS",
            "",
            "This complaint concerns violations of the Fair Credit Reporting Act (FCRA),",
            "including but not limited to:",
            "",
        ])

        # Determine which statutes apply based on violation types
        statutes = self._get_applicable_statutes(contradictions)
        for statute in statutes:
            lines.append(f"• {statute}")
        lines.append("")

        # Issues Presented - grouped by type with --- separators
        lines.append("=" * 60)
        lines.append("")
        lines.append("ISSUES PRESENTED")
        lines.append("")

        issue_num = 1
        violation_items = list(violations_by_type.items())
        for idx, (violation_type, violations) in enumerate(violation_items):
            lines.append(f"{issue_num}. {self._format_issue_title(violation_type)}")
            lines.append("")

            # Get the statutory context for this violation type
            statutory_context = self._get_violation_statutory_context(violation_type)
            if statutory_context:
                lines.append(statutory_context)
                lines.append("")

            # List affected accounts - deduplicate by creditor+account
            lines.append("Affected accounts:")
            seen_accounts = set()
            for v in violations:
                acct = getattr(v, "account_number_masked", None) or "(masked)"
                key = (v.creditor_name, acct)
                if key not in seen_accounts:
                    seen_accounts.add(key)
                    lines.append(f"• {v.creditor_name} — Account: {acct}")
            lines.append("")

            # Add separator between issues (but not after the last one)
            if idx < len(violation_items) - 1:
                lines.append("---")
                lines.append("")

            issue_num += 1

        # CROSS-BUREAU CONTRADICTIONS section (if discrepancies exist)
        if discrepancies:
            lines.append("=" * 60)
            lines.append("")
            lines.append("CROSS-BUREAU CONTRADICTIONS")
            lines.append("")
            lines.append("The following data fields are reported inconsistently across credit bureaus,")
            lines.append("demonstrating that at least one bureau is reporting inaccurate information:")
            lines.append("")

            # Group discrepancies by account
            discrepancies_by_account = {}
            for d in discrepancies:
                creditor = d.get("creditor_name", "Unknown")
                acct = d.get("account_number_masked", "(masked)")
                key = (creditor, acct)
                if key not in discrepancies_by_account:
                    discrepancies_by_account[key] = []
                discrepancies_by_account[key].append(d)

            for (creditor, acct), account_discrepancies in discrepancies_by_account.items():
                lines.append(f"Account: {creditor} — {acct}")
                lines.append("")

                for d in account_discrepancies:
                    field_name = d.get("field_name", "Unknown Field")
                    values_by_bureau = d.get("values_by_bureau", {})

                    # Format the field name nicely
                    field_display = field_name.replace("_", " ").title()
                    lines.append(f"  • {field_display}:")

                    # Show each bureau's value
                    for bureau, value in values_by_bureau.items():
                        bureau_display = bureau.title()
                        lines.append(f"    - {bureau_display}: {value}")
                    lines.append("")

            lines.append("Under 15 U.S.C. § 1681e(b), credit bureaus must maintain reasonable procedures")
            lines.append("to assure maximum possible accuracy. Conflicting data across bureaus proves")
            lines.append("that at least one agency is not meeting this standard.")
            lines.append("")

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
            # Default timeline if none provided - route-dependent
            if has_prior_cra_response:
                # Mail-First Route: include dispute and response
                lines.append(f"• [DATE] — Dispute submitted to {formatted_entity}")
                lines.append("• [DATE] — 30-day statutory reinvestigation deadline")
                lines.append(f"• [DATE] — {formatted_entity} response received")
            elif has_prior_cra_dispute:
                # Dispute filed but no response yet
                lines.append(f"• [DATE] — Dispute submitted to {formatted_entity}")
                lines.append("• [DATE] — 30-day statutory reinvestigation deadline (pending)")
            else:
                # CFPB-First Route: no prior CRA activity
                lines.append("• [DATE] — Credit report reviewed, inaccuracies identified")
                lines.append("• [DATE] — CFPB complaint filed")
        lines.append("")

        # Route-dependent section: REINVESTIGATION DEFICIENCY vs FAILURE TO ASSURE MAXIMUM POSSIBLE ACCURACY
        lines.append("=" * 60)
        lines.append("")

        if has_prior_cra_response:
            # Mail-First Route: CRA responded - can claim reinvestigation deficiency
            lines.append("REINVESTIGATION DEFICIENCY")
            lines.append("")
            lines.append("Despite my dispute identifying specific, verifiable inaccuracies,")
            lines.append(f"{formatted_entity} responded that the accounts were \"verified as accurate\"")
            lines.append("without addressing the documented defects.")
            lines.append("")
            lines.append("The reinvestigation failed to:")
            lines.append("")

            # List specific failures based on ALL violation types
            for vtype in all_violation_types:
                failure = self._get_reinvestigation_failure(vtype)
                lines.append(f"• {failure}")
            lines.append("• Demonstrate any independent verification beyond furnisher confirmation")
            lines.append("")
            lines.append("Reliance on furnisher affirmation alone does not constitute a reasonable")
            lines.append("reinvestigation under **15 U.S.C. § 1681i(a)**.")
        else:
            # CFPB-First Route: No prior response - cannot claim reinvestigation deficiency
            lines.append("FAILURE TO ASSURE MAXIMUM POSSIBLE ACCURACY")
            lines.append("")
            lines.append(f"The information reported by {formatted_entity} contains specific,")
            lines.append("verifiable inaccuracies that violate the FCRA's accuracy requirements.")
            lines.append("")
            lines.append(f"{formatted_entity} has failed to:")
            lines.append("")

            # List specific accuracy failures based on ALL violation types
            for vtype in all_violation_types:
                failure = self._get_accuracy_failure(vtype)
                lines.append(f"• {failure}")
            lines.append("• Verify the accuracy of reported data against original source documents")
            lines.append("")
            lines.append("Under 15 U.S.C. § 1681e(b), consumer reporting agencies must follow")
            lines.append("reasonable procedures to assure maximum possible accuracy of consumer reports.")
        lines.append("")

        # Consumer Impact and Prejudice section
        lines.append("=" * 60)
        lines.append("")
        lines.append("CONSUMER IMPACT AND PREJUDICE")
        lines.append("")
        lines.append("These inaccuracies cause material harm to my creditworthiness and financial")
        lines.append("standing:")
        lines.append("")
        impact_statements = self._get_consumer_impact_statements(all_violation_types)
        for statement in impact_statements:
            # Skip header lines we already added
            if statement and not statement.startswith("These inaccuracies"):
                lines.append(statement)
        lines.append("")

        # Requested Resolution - dynamic based on violation types
        lines.append("=" * 60)
        lines.append("")
        lines.append("REQUESTED RESOLUTION")
        lines.append("")
        lines.append(f"I request that the CFPB compel {formatted_entity} to fulfill its statutory")
        lines.append("obligations by performing the following:")
        lines.append("")

        resolution_num = 1
        resolutions = self._get_dynamic_resolutions(all_violation_types, violations_by_type)
        for title, details in resolutions:
            lines.append(f"{resolution_num}. {title}")
            for detail in details:
                lines.append(f"   {detail}")
            lines.append("")
            resolution_num += 1

        # Attachments - route-dependent
        lines.append("=" * 60)
        lines.append("")
        lines.append("ATTACHMENTS PROVIDED")
        lines.append("")
        if has_prior_cra_response:
            # Mail-First Route: include dispute and response letters
            lines.append(f"• Copy of dispute letter sent to {formatted_entity}")
            lines.append("• Certified mail receipt (if applicable)")
            lines.append(f"• {formatted_entity} response letter")
            lines.append("• Credit report excerpts showing disputed information")
        elif has_prior_cra_dispute:
            # Dispute filed but no response yet
            lines.append(f"• Copy of dispute letter sent to {formatted_entity}")
            lines.append("• Certified mail receipt (if applicable)")
            lines.append("• Credit report excerpts showing disputed information")
        else:
            # CFPB-First Route: no prior CRA dispute
            lines.append("• Credit report excerpts showing inaccurate information")
            lines.append("• Documentation of identified Metro-2 discrepancies")
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
            # Single-bureau violations
            "missing_dofd": "Missing Date of First Delinquency (Metro-2 Field 25)",
            "chargeoff_missing_dofd": "Charge-Off Account Missing Required DOFD",
            "obsolete_account": "Account Exceeds 7-Year Reporting Period",
            "stale_reporting": "Stale/Outdated Reporting",
            "balance_increase_after_chargeoff": "Balance Increased After Charge-Off",
            "missing_date_opened": "Missing Date Opened Field",
            "missing_scheduled_payment": "Missing Scheduled Payment Amount",
            "dofd_after_date_opened": "DOFD Precedes Account Open Date (Temporal Impossibility)",
            "payment_history_exceeds_account_age": "Payment History Exceeds Account Age",
            # Cross-bureau discrepancies
            "date_opened_mismatch": "Cross-Bureau Date Opened Mismatch",
            "dofd_mismatch": "Cross-Bureau DOFD Mismatch",
            "balance_mismatch": "Cross-Bureau Balance Mismatch",
            "status_mismatch": "Cross-Bureau Account Status Mismatch",
            "payment_history_mismatch": "Cross-Bureau Payment History Mismatch",
            "past_due_mismatch": "Cross-Bureau Past Due Amount Mismatch",
            "closed_vs_open_conflict": "Cross-Bureau Open/Closed Status Conflict",
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
            # Cross-bureau discrepancies
            "date_opened_mismatch": (
                "Different credit bureaus are reporting different account open dates for the same account. "
                "Under § 1681e(b), CRAs must assure maximum possible accuracy. Conflicting dates across "
                "bureaus prove at least one (and possibly all) are inaccurate."
            ),
            "dofd_mismatch": (
                "Different credit bureaus report different Dates of First Delinquency for the same account. "
                "Since DOFD determines the 7-year reporting period under § 1681c(a), conflicting dates "
                "create legal uncertainty about when the account should be purged."
            ),
            "balance_mismatch": (
                "Different credit bureaus report different balance amounts for the same account. "
                "This discrepancy violates the accuracy requirements of § 1681e(b) and may be "
                "artificially inflating or deflating the consumer's apparent debt load."
            ),
            "status_mismatch": (
                "Different credit bureaus report conflicting account statuses. This inconsistency "
                "proves the information cannot be accurate across all bureaus and violates § 1681e(b)."
            ),
        }
        return context_map.get(violation_type, "")

    def _get_reinvestigation_failure(self, violation_type: str) -> str:
        """Get specific reinvestigation failure for a violation type."""
        failure_map = {
            # Single-bureau violations
            "missing_dofd": "Provide or verify the Date of First Delinquency",
            "chargeoff_missing_dofd": "Explain why DOFD is missing from charge-off account",
            "obsolete_account": "Verify the account has not exceeded the 7-year reporting period",
            "stale_reporting": "Confirm the reported data reflects current account status",
            "balance_increase_after_chargeoff": "Explain the basis for post-charge-off balance increase",
            "missing_date_opened": "Verify the account open date from original records",
            "missing_scheduled_payment": "Provide the scheduled payment amount",
            # Cross-bureau discrepancies
            "date_opened_mismatch": "Reconcile conflicting Date Opened values reported across bureaus",
            "dofd_mismatch": "Reconcile conflicting Date of First Delinquency values across bureaus",
            "balance_mismatch": "Reconcile conflicting balance amounts reported across bureaus",
            "status_mismatch": "Reconcile conflicting account status values across bureaus",
            "payment_history_mismatch": "Reconcile conflicting payment history data across bureaus",
            "past_due_mismatch": "Reconcile conflicting past due amounts across bureaus",
        }
        return failure_map.get(violation_type, f"Address the {violation_type.replace('_', ' ')} issue")

    def _get_accuracy_failure(self, violation_type: str) -> str:
        """Get specific accuracy failure for a violation type (CFPB-First route - no reinvestigation claim)."""
        failure_map = {
            # Single-bureau violations - focus on accuracy, not reinvestigation
            "missing_dofd": "Report a Date of First Delinquency as required by Metro-2 standards",
            "chargeoff_missing_dofd": "Include DOFD on charge-off accounts as required by Metro-2 Field 25",
            "obsolete_account": "Remove accounts that exceed the 7-year reporting period",
            "stale_reporting": "Ensure reported data reflects current account status",
            "balance_increase_after_chargeoff": "Report accurate balance without unexplained post-charge-off increases",
            "missing_date_opened": "Report the account open date as required by Metro-2 standards",
            "missing_scheduled_payment": "Report the scheduled payment amount as required",
            # Cross-bureau discrepancies - focus on consistency
            "date_opened_mismatch": "Report consistent Date Opened values across all bureaus",
            "dofd_mismatch": "Report consistent Date of First Delinquency values across all bureaus",
            "balance_mismatch": "Report consistent balance amounts across all bureaus",
            "status_mismatch": "Report consistent account status values across all bureaus",
            "payment_history_mismatch": "Report consistent payment history data across all bureaus",
            "past_due_mismatch": "Report consistent past due amounts across all bureaus",
        }
        return failure_map.get(violation_type, f"Assure accuracy of {violation_type.replace('_', ' ')} data")

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

    def _get_consumer_impact_statements(self, violation_types: List[str]) -> List[str]:
        """Generate consumer impact statements based on violation types."""
        statements = []

        # Build impact based on violation categories
        has_dofd = any("dofd" in vt.lower() for vt in violation_types)
        has_balance = any("balance" in vt.lower() for vt in violation_types)
        has_obsolete = any("obsolete" in vt.lower() for vt in violation_types)
        has_missing = any("missing" in vt.lower() and "dofd" not in vt.lower() for vt in violation_types)
        has_temporal = any("temporal" in vt.lower() or "exceeds" in vt.lower() or "after" in vt.lower() for vt in violation_types)
        has_mismatch = any("mismatch" in vt.lower() for vt in violation_types)

        statements.append("These inaccuracies cause material harm to my creditworthiness and financial standing:")
        statements.append("")

        if has_dofd:
            statements.append("• Missing DOFD prevents verification of 7-year obsolescence compliance,")
            statements.append("  effectively granting unlimited reporting in violation of 15 U.S.C. § 1681c(a).")

        if has_balance:
            statements.append("• Inflated or incorrect balance reporting distorts my debt-to-income ratio,")
            statements.append("  directly impacting credit decisions and loan eligibility.")

        if has_obsolete:
            statements.append("• Reporting beyond the statutory 7-year limit violates 15 U.S.C. § 1681c(a),")
            statements.append("  causing continued damage from information that should have been purged.")

        if has_missing:
            statements.append("• Missing required Metro-2 fields render the account data incomplete,")
            statements.append("  violating the maximum accuracy standard of 15 U.S.C. § 1681e(b).")

        if has_temporal:
            statements.append("• Temporal impossibilities in the reported data (dates that contradict each other)")
            statements.append("  prove the information cannot be accurate as reported.")

        if has_mismatch:
            statements.append("• Cross-bureau discrepancies prove that at least one bureau is reporting")
            statements.append("  inaccurate information, violating the maximum accuracy standard of § 1681e(b).")
            statements.append("  These inconsistencies create confusion for creditors evaluating my file.")

        # Generic catch-all if no specific matches
        if not (has_dofd or has_balance or has_obsolete or has_missing or has_temporal or has_mismatch):
            statements.append("• The documented inaccuracies suppress my creditworthiness")
            statements.append("  and access to credit on fair and equal terms.")

        return statements

    def _get_dynamic_resolutions(
        self, violation_types: List[str], violations_by_type: Dict[str, List[Violation]]
    ) -> List[tuple]:
        """Generate dynamic resolution requests based on violation types."""
        resolutions = []

        has_dofd = any("dofd" in vt.lower() for vt in violation_types)
        has_balance = any("balance" in vt.lower() for vt in violation_types)
        has_obsolete = any("obsolete" in vt.lower() for vt in violation_types)
        has_missing = any("missing" in vt.lower() for vt in violation_types)
        has_mismatch = any("mismatch" in vt.lower() for vt in violation_types)

        # Violation-specific resolutions
        if has_dofd or has_missing:
            resolutions.append((
                "Mandatory Correction or Deletion",
                [
                    "Provide original source documentation for the disputed data fields.",
                    "If documentation cannot be produced, delete the accounts pursuant",
                    "to 15 U.S.C. § 1681i(a)(5)(A)."
                ]
            ))

        if has_balance:
            resolutions.append((
                "Balance Verification",
                [
                    "Provide documentation supporting the reported balance amount.",
                    "Explain any balance changes after charge-off date.",
                    "Correct any balance reporting errors identified."
                ]
            ))

        if has_obsolete:
            resolutions.append((
                "Obsolete Account Deletion",
                [
                    "Delete any accounts exceeding the 7-year reporting period",
                    "under 15 U.S.C. § 1681c(a)."
                ]
            ))

        if has_mismatch:
            resolutions.append((
                "Cross-Bureau Discrepancy Resolution",
                [
                    "Identify the correct value for each field where cross-bureau",
                    "discrepancies exist by obtaining original source documentation.",
                    "Correct the inaccurate reporting to match verified records.",
                    "Notify all credit bureaus of the corrections made."
                ]
            ))

        # Always include procedural disclosure
        resolutions.append((
            "Procedural Disclosure",
            [
                "Provide a full description of reinvestigation procedures conducted,",
                "including:",
                "• the records reviewed,",
                "• whether an ACDV/e-OSCAR system was used,",
                "• the identity of individual(s) who certified data accuracy."
            ]
        ))

        # Add certification of accuracy for specific types
        if has_dofd or has_missing or has_balance or has_mismatch:
            cert_details = ["Provide a written explanation of how accounts were deemed"]
            cert_details.append("\"verified as accurate\" despite the documented issues:")
            for vtype in list(violation_types)[:3]:
                cert_details.append(f"  • {self._format_issue_title(vtype)}")
            resolutions.append((
                "Certification of Accuracy",
                cert_details
            ))

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
        """Generate CFPB Escalation letter - regulatory noncompliance after notice."""
        today = date.today().strftime("%B %d, %Y")
        case_ref = cfpb_case_number or "[CASE NUMBER]"
        formatted_entity = self._format_entity_name(entity_name)

        # Group violations by type
        violations_by_type = self._group_violations_by_type(contradictions)
        all_violation_types = list(violations_by_type.keys())

        # Cross-bureau detection: explicit types list
        cross_bureau_types = {
            "date_opened_mismatch", "dofd_mismatch", "balance_mismatch",
            "status_mismatch", "payment_history_mismatch", "past_due_mismatch",
            "closed_vs_open_conflict"
        }
        has_cross_bureau = any(vt.lower() in cross_bureau_types for vt in all_violation_types)
        has_dofd = any("dofd" in vt.lower() for vt in all_violation_types)

        # Collect unique accounts from ALL violations (not just contradictions subset)
        unique_accounts = []
        seen_accounts = set()
        for v in contradictions:
            acct = getattr(v, "account_number_masked", None) or "(masked)"
            key = (v.creditor_name, acct)
            if key not in seen_accounts:
                seen_accounts.add(key)
                unique_accounts.append((v.creditor_name, acct))

        lines = [
            "CONSUMER FINANCIAL PROTECTION BUREAU COMPLAINT — ESCALATION",
            "",
            "Complaint Type: Continued Regulatory Noncompliance After Notice",
            f"CFPB Case Number: {case_ref}",
            f"Date: {today}",
            f"Consumer: {consumer.full_name}",
            "",
            "Accounts at Issue:",
        ]

        for creditor, acct in unique_accounts:
            lines.append(f"• {creditor} — Account: {acct}")

        # =====================================================================
        # ESCALATION BASIS — Failure to Comply After Regulatory Notice
        # =====================================================================
        lines.append("")
        lines.append("=" * 60)
        lines.append("")
        lines.append("ESCALATION BASIS — FAILURE TO COMPLY AFTER REGULATORY NOTICE")
        lines.append("")
        lines.append(f"This escalation is submitted because {formatted_entity} was placed on")
        lines.append(f"formal notice through CFPB Case #{case_ref} and **failed to cure** the")
        lines.append("identified violations despite having a full opportunity to do so.")
        lines.append("")
        lines.append("The company's response to the initial CFPB complaint did not:")
        lines.append("")
        lines.append("• Address the specific factual inaccuracies identified")
        lines.append("• Provide documentation supporting the disputed data fields")
        lines.append("• Correct the inaccurate information on my credit file")
        lines.append("• Demonstrate any genuine investigation beyond furnisher confirmation")
        lines.append("")
        lines.append("**The inaccurate information remains unchanged after CFPB intervention.**")
        lines.append("")
        lines.append("This transforms the matter from an initial accuracy dispute into a case of")
        lines.append("**continued regulatory noncompliance after notice** — a materially different")
        lines.append("liability posture under the FCRA.")
        lines.append("")

        # =====================================================================
        # POST-CFPB PERSISTENCE OF VIOLATIONS
        # =====================================================================
        lines.append("=" * 60)
        lines.append("")
        lines.append("POST-CFPB PERSISTENCE OF VIOLATIONS")
        lines.append("")
        lines.append("Despite receiving formal notice through the CFPB complaint process,")
        lines.append(f"{formatted_entity} continues to report the following violations:")
        lines.append("")

        issue_num = 1
        for violation_type, violations in violations_by_type.items():
            lines.append(f"{issue_num}. **{self._format_issue_title(violation_type)}**")
            lines.append("")
            lines.append("   Status: UNCHANGED after CFPB notice")
            lines.append(f"   Affected accounts: {len(violations)}")
            lines.append("")
            issue_num += 1

        if has_dofd:
            lines.append("**DOFD Allegation:**")
            lines.append("The Date of First Delinquency (DOFD) remains missing or inaccurate")
            lines.append("after CFPB review. Without DOFD, the 7-year obsolescence calculation")
            lines.append("required by 15 U.S.C. § 1681c(a) cannot be performed. Continued")
            lines.append("reporting without this mandatory field is incompatible with Metro-2")
            lines.append("required reporting standards and defeats § 1681c(a) obsolescence verification.")
            lines.append("")

        # =====================================================================
        # CROSS-BUREAU CONTRADICTIONS (if applicable)
        # =====================================================================
        if has_cross_bureau:
            lines.append("=" * 60)
            lines.append("")
            lines.append("CROSS-BUREAU CONTRADICTIONS")
            lines.append("")
            lines.append("The same accounts are reported with **contradictory data** across")
            lines.append("consumer reporting agencies:")
            lines.append("")
            for vtype in all_violation_types:
                if vtype.lower() in cross_bureau_types:
                    lines.append(f"• {self._format_issue_title(vtype)}")
            lines.append("")
            lines.append("These contradictions **cannot simultaneously be accurate**. At minimum,")
            lines.append("one bureau is reporting false information. This independently violates")
            lines.append("15 U.S.C. § 1681e(b)'s requirement for maximum possible accuracy.")
            lines.append("")
            lines.append("The company was notified of these cross-bureau contradictions in the")
            lines.append("initial CFPB complaint. Continued contradictory reporting after notice")
            lines.append("demonstrates **reckless disregard** for accuracy obligations.")
            lines.append("")

        # =====================================================================
        # LIABILITY SHIFT — From Accuracy Failure to Noncompliance After Notice
        # =====================================================================
        lines.append("=" * 60)
        lines.append("")
        lines.append("LIABILITY POSTURE SHIFT")
        lines.append("")
        lines.append("The initial CFPB complaint alleged **accuracy failure** under")
        lines.append("15 U.S.C. § 1681e(b) — a correctable deficiency.")
        lines.append("")
        lines.append("This escalation now alleges **continued noncompliance after regulatory")
        lines.append("notice** — a materially elevated liability theory:")
        lines.append("")
        lines.append(f"• The company received formal notice through CFPB Case #{case_ref}")
        lines.append("• The company had opportunity and obligation to cure")
        lines.append("• The company failed to correct the identified violations")
        lines.append("• The violations persist unchanged after notice")
        lines.append("")
        lines.append("This pattern supports findings of **negligent or willful noncompliance**")
        lines.append("under 15 U.S.C. §§ 1681n (willful) and 1681o (negligent), rather than")
        lines.append("mere procedural deficiency.")
        lines.append("")

        # =====================================================================
        # COMPANY RESPONSE ANALYSIS
        # =====================================================================
        lines.append("=" * 60)
        lines.append("")
        lines.append("COMPANY RESPONSE ANALYSIS")
        lines.append("")
        if cra_response_summary:
            lines.append(cra_response_summary)
        else:
            lines.append("The company's response to the initial complaint stated, in substance:")
            lines.append("\"We have reviewed the consumer's dispute and verified the information.\"")
        lines.append("")
        lines.append("This response constitutes **continued noncompliance** because it:")
        lines.append("")
        for vtype in violations_by_type.keys():
            deficiency = self._get_response_deficiency(vtype)
            lines.append(f"• {deficiency}")
        lines.append("• Provides no documentation or factual explanation")
        lines.append("• Relies on conclusory verification language rather than evidence")
        lines.append("• Demonstrates no genuine investigation was conducted")
        lines.append("")
        lines.append("A generic assertion of accuracy after formal CFPB notice does not satisfy")
        lines.append("the reasonable reinvestigation standard under 15 U.S.C. § 1681i(a).")
        lines.append("")

        # =====================================================================
        # TIMELINE OF ACTIONS
        # =====================================================================
        lines.append("=" * 60)
        lines.append("")
        lines.append("TIMELINE OF ACTIONS")
        lines.append("")

        if timeline_events:
            lines.append("| Date | Event | Outcome |")
            lines.append("|------|-------|---------|")
            # Deduplicate timeline events
            seen_events = set()
            unique_events = []
            for event in timeline_events:
                key = (event.event_date, event.event_description)
                if key not in seen_events:
                    seen_events.add(key)
                    unique_events.append(event)

            for event in sorted(unique_events, key=lambda e: e.event_date):
                date_str = event.event_date.strftime("%b %d, %Y")
                desc = event.event_description
                for raw_name in ["transunion", "equifax", "experian"]:
                    if raw_name in desc.lower():
                        desc = desc.replace(raw_name, self._format_entity_name(raw_name))
                        desc = desc.replace(raw_name.title(), self._format_entity_name(raw_name))
                lines.append(f"| {date_str} | {desc} | {event.outcome} |")
        else:
            lines.append(f"• [DATE] — CFPB complaint filed (Case #{case_ref})")
            lines.append("• [DATE] — Company response received; violations remain unchanged")
        lines.append("")

        # =====================================================================
        # REQUESTED CFPB ACTION — Escalated Enforcement
        # =====================================================================
        lines.append("=" * 60)
        lines.append("")
        lines.append("REQUESTED CFPB ACTION — ESCALATED ENFORCEMENT")
        lines.append("")
        lines.append("Given the company's failure to comply after formal notice, I request")
        lines.append("the CFPB take escalated enforcement action:")
        lines.append("")
        lines.append("1. **Require Documented Proof, Not Assertions**")
        lines.append("   The company must produce original source documentation for each")
        lines.append("   disputed data field. Generic verification statements should be")
        lines.append("   rejected as non-responsive.")
        lines.append("")
        lines.append("2. **Treat Continued Reporting as Noncompliance**")
        lines.append("   Continued reporting of unchanged inaccurate information after")
        lines.append("   CFPB notice should be treated as regulatory noncompliance,")
        lines.append("   not mere procedural delay.")
        lines.append("")
        lines.append("3. **Escalate Supervisory Action**")
        lines.append("   If the company fails to substantively respond to this escalation,")
        lines.append("   I request referral for supervisory examination of the company's")
        lines.append("   dispute handling procedures under 12 U.S.C. § 5514.")
        lines.append("")
        lines.append("4. **Preserve Record for Potential Enforcement**")
        lines.append("   This escalation should be preserved as part of any pattern-or-")
        lines.append("   practice analysis of the company's FCRA compliance.")
        lines.append("")

        # Attachments
        lines.append("=" * 60)
        lines.append("")
        lines.append("ATTACHMENTS")
        lines.append("")
        lines.append(f"• Original CFPB complaint (Case #{case_ref})")
        lines.append("• Company response")
        lines.append("• Updated credit report showing unchanged inaccuracies")

        return "\n".join(lines)

    def _get_escalation_explanation(self, violation_type: str) -> List[str]:
        """Get escalation-specific explanation for a violation type."""
        explanations = {
            "missing_dofd": [
                "The company failed to explain or correct the absence of the Date of First",
                "Delinquency for the accounts listed above.",
                "",
                "Without a DOFD, compliance with the 7-year obsolescence requirement under",
                "15 U.S.C. § 1681c(a) cannot be verified. The company's response did not",
                "address this impossibility.",
            ],
            "chargeoff_missing_dofd": [
                "The company failed to explain why charge-off accounts are missing the",
                "required Date of First Delinquency field.",
                "",
                "This omission violates Metro-2 reporting standards and prevents verification",
                "of § 1681c(a) obsolescence compliance.",
            ],
            "date_opened_mismatch": [
                "The same accounts continue to be reported with conflicting \"Date Opened\"",
                "values across consumer reporting agencies.",
                "",
                "The company did not explain how internally inconsistent reporting can",
                "satisfy the \"maximum possible accuracy\" requirement of 15 U.S.C. § 1681e(b),",
                "nor did it identify which value is correct.",
            ],
            "dofd_mismatch": [
                "The same accounts are reported with conflicting Dates of First Delinquency",
                "across consumer reporting agencies.",
                "",
                "The company did not reconcile these inconsistencies or identify the correct",
                "DOFD for § 1681c(a) obsolescence calculation.",
            ],
            "balance_mismatch": [
                "The same accounts are reported with conflicting balance amounts across",
                "consumer reporting agencies.",
                "",
                "The company did not explain these discrepancies or identify the correct",
                "balance amount.",
            ],
            "status_mismatch": [
                "The same accounts are reported with conflicting status values across",
                "consumer reporting agencies.",
                "",
                "The company did not reconcile these inconsistencies.",
            ],
            "obsolete_account": [
                "The account appears to exceed the 7-year reporting period under",
                "15 U.S.C. § 1681c(a).",
                "",
                "The company did not provide documentation demonstrating the account",
                "is still within the permissible reporting period.",
            ],
        }

        default = [
            f"The company failed to address the {violation_type.replace('_', ' ')} issue",
            "identified in the original complaint.",
            "",
            "The response did not explain or correct this inaccuracy.",
        ]

        return explanations.get(violation_type, default)

    def _get_response_deficiency(self, violation_type: str) -> str:
        """Get specific response deficiency statement for a violation type."""
        deficiencies = {
            "missing_dofd": "Fails to address the missing Date of First Delinquency",
            "chargeoff_missing_dofd": "Fails to explain missing DOFD on charge-off accounts",
            "date_opened_mismatch": "Fails to address cross-bureau Date Opened inconsistencies",
            "dofd_mismatch": "Fails to reconcile cross-bureau DOFD discrepancies",
            "balance_mismatch": "Fails to address cross-bureau balance inconsistencies",
            "status_mismatch": "Fails to reconcile cross-bureau status conflicts",
            "obsolete_account": "Fails to demonstrate the account is within reporting period",
            "stale_reporting": "Fails to confirm data reflects current account status",
        }
        return deficiencies.get(violation_type, f"Fails to address the {violation_type.replace('_', ' ')} issue")

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
