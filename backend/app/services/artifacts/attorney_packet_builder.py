"""
Attorney Packet Builder (Tier 5)

Packages Tier-3 ledger entries into attorney-ready case packets.

Inputs:
- Tier-3 ledger entry
- Evidence chain (Tier 1-2 violations + responses)
- Timeline of events

Output:
- Single immutable "case packet" (JSON structure)
- Can be rendered to PDF via external service

No auto-sending — generation only.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from uuid import uuid4
from collections import defaultdict
import hashlib
import json

from sqlalchemy.orm import Session

from ...models.db_models import (
    DisputeDB,
    Tier2ResponseDB,
    PaperTrailDB,
    ExecutionEventDB,
    ExecutionResponseDB,
    ExecutionOutcomeDB,
)


@dataclass
class AttorneyPacketViolation:
    """Single violation entry in the packet."""
    violation_id: str
    violation_type: str
    severity: str
    description: str
    evidence: Dict[str, Any]
    creditor_name: Optional[str] = None
    account_number_masked: Optional[str] = None
    statute: Optional[str] = None
    metro2_field: Optional[str] = None


@dataclass
class AttorneyPacketTimeline:
    """Timeline event in the packet."""
    date: datetime
    event_type: str
    description: str
    actor: str  # USER, SYSTEM, ENTITY
    evidence_hash: Optional[str] = None


@dataclass
class AttorneyPacket:
    """
    Immutable attorney-ready case packet.

    Contains all evidence needed for FCRA/FDCPA litigation referral.
    """
    # Identity
    packet_id: str
    dispute_id: str
    user_id: str

    # Parties
    consumer_name: Optional[str] = None
    cra_name: str = ""
    furnisher_name: str = ""

    # Classification
    tier3_classification: str = ""
    readiness_status: str = "ATTORNEY_READY"  # ATTORNEY_READY, REGULATORY_READY

    # Violations (Tier 1)
    primary_violations: List[AttorneyPacketViolation] = field(default_factory=list)
    total_violation_count: int = 0

    # Examiner Failures (Tier 2-3)
    examiner_failures: List[Dict[str, Any]] = field(default_factory=list)
    cure_opportunity_given: bool = True
    cure_outcome: str = ""

    # Evidence Chain
    timeline: List[AttorneyPacketTimeline] = field(default_factory=list)
    document_hashes: List[str] = field(default_factory=list)
    artifact_pointers: List[str] = field(default_factory=list)

    # Legal Elements
    statutes_violated: List[str] = field(default_factory=list)
    potential_damages: Dict[str, Any] = field(default_factory=dict)

    # Cross-Bureau Discrepancies
    discrepancies: List[Dict[str, Any]] = field(default_factory=list)

    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    packet_hash: str = ""  # SHA256 of packet contents for integrity

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "packet_id": self.packet_id,
            "dispute_id": self.dispute_id,
            "user_id": self.user_id,
            "consumer_name": self.consumer_name,
            "cra_name": self.cra_name,
            "furnisher_name": self.furnisher_name,
            "tier3_classification": self.tier3_classification,
            "readiness_status": self.readiness_status,
            "primary_violations": [
                {
                    "violation_id": v.violation_id,
                    "violation_type": v.violation_type,
                    "severity": v.severity,
                    "description": v.description,
                    "evidence": v.evidence,
                    "creditor_name": v.creditor_name,
                    "account_number_masked": v.account_number_masked,
                    "statute": v.statute,
                    "metro2_field": v.metro2_field,
                }
                for v in self.primary_violations
            ],
            "total_violation_count": self.total_violation_count,
            "examiner_failures": self.examiner_failures,
            "cure_opportunity_given": self.cure_opportunity_given,
            "cure_outcome": self.cure_outcome,
            "timeline": [
                {
                    "date": t.date.isoformat(),
                    "event_type": t.event_type,
                    "description": t.description,
                    "actor": t.actor,
                    "evidence_hash": t.evidence_hash,
                }
                for t in self.timeline
            ],
            "document_hashes": self.document_hashes,
            "artifact_pointers": self.artifact_pointers,
            "statutes_violated": self.statutes_violated,
            "potential_damages": self.potential_damages,
            "discrepancies": self.discrepancies,
            "created_at": self.created_at.isoformat(),
            "packet_hash": self.packet_hash,
        }

    def compute_hash(self) -> str:
        """Compute SHA256 hash of packet contents for integrity verification."""
        # Create deterministic JSON string
        content = {
            "dispute_id": self.dispute_id,
            "violations": [v.violation_id for v in self.primary_violations],
            "classification": self.tier3_classification,
            "cure_outcome": self.cure_outcome,
            "timeline_count": len(self.timeline),
            "document_hashes": sorted(self.document_hashes),
        }
        json_str = json.dumps(content, sort_keys=True)
        return hashlib.sha256(json_str.encode()).hexdigest()

    @classmethod
    def from_packet_data(cls, packet_data: Dict[str, Any]) -> "AttorneyPacket":
        """
        Create an AttorneyPacket from the packet_data dict used by letters.py legal-packet endpoint.

        This normalizes the dict format from the API into the structured AttorneyPacket class.
        """
        # Convert violations list to AttorneyPacketViolation objects
        violations = []
        for v in packet_data.get('violations', []):
            if isinstance(v, dict):
                violations.append(AttorneyPacketViolation(
                    violation_id=v.get('violation_id', str(uuid4())),
                    violation_type=v.get('violation_type', 'unknown'),
                    severity=v.get('severity', 'medium'),
                    description=v.get('description', ''),
                    evidence=v.get('evidence', {}),
                    creditor_name=v.get('creditor_name'),
                    account_number_masked=v.get('account_number_masked'),
                    statute=v.get('statute'),
                    metro2_field=v.get('metro2_field'),
                ))

        # Convert timeline list to AttorneyPacketTimeline objects
        timeline = []
        for t in packet_data.get('timeline', []):
            if isinstance(t, dict):
                # Parse date string to datetime
                date_str = t.get('date', '')
                try:
                    if date_str:
                        event_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    else:
                        event_date = datetime.now(timezone.utc)
                except (ValueError, TypeError):
                    event_date = datetime.now(timezone.utc)

                timeline.append(AttorneyPacketTimeline(
                    date=event_date,
                    event_type=t.get('event', 'unknown'),
                    description=t.get('event', ''),
                    actor=t.get('actor', 'CONSUMER'),
                    evidence_hash=t.get('evidence_hash'),
                ))

        # Parse created_at from generated_at
        generated_at = packet_data.get('generated_at', '')
        try:
            if generated_at:
                created_at = datetime.fromisoformat(generated_at.replace('Z', '+00:00'))
            else:
                created_at = datetime.now(timezone.utc)
        except (ValueError, TypeError):
            created_at = datetime.now(timezone.utc)

        return cls(
            packet_id=packet_data.get('packet_id', f"PKT-{str(uuid4())[:8]}"),
            dispute_id=packet_data.get('letter_id', str(uuid4())),
            user_id=packet_data.get('user_id', ''),
            consumer_name=packet_data.get('consumer_name'),
            cra_name=packet_data.get('entity_name', ''),
            furnisher_name='',  # Not in packet_data
            tier3_classification=packet_data.get('channel', 'CFPB'),
            readiness_status='ATTORNEY_READY',
            primary_violations=violations,
            total_violation_count=packet_data.get('violation_count', len(violations)),
            examiner_failures=[],  # Not in packet_data
            cure_opportunity_given=True,
            cure_outcome='',
            timeline=timeline,
            document_hashes=[],
            artifact_pointers=[],
            statutes_violated=packet_data.get('statutes_violated', []),
            potential_damages=packet_data.get('potential_damages', {}),
            discrepancies=packet_data.get('discrepancies', []),
            created_at=created_at,
            packet_hash='',
        )

    def render_document(self) -> str:
        """
        Render the packet as a litigation-ready document for attorney consultation.

        This document ALLEGES violations, establishes notice timeline, and frames
        the case for willful/negligent noncompliance under FCRA §§1681n/1681o.

        Returns a formatted text document suitable for filing.
        """
        lines = []
        w = 80  # Document width

        def header(text: str) -> str:
            return "=" * w + "\n" + text.center(w) + "\n" + "=" * w

        def section(text: str) -> str:
            return "\n" + "=" * w + "\n" + text.center(w) + "\n" + "=" * w + "\n"

        def subsection(text: str) -> str:
            return "\n" + text + "\n" + "━" * w + "\n"

        # ==================================================================
        # TITLE — Litigation-Grade Framing
        # ==================================================================
        lines.append(header("FCRA LITIGATION PACKET\nCase for Willful/Negligent Noncompliance"))
        lines.append("")
        lines.append(f"CASE REFERENCE: {self.packet_id}")
        lines.append(f"GENERATED:      {self.created_at.strftime('%B %d, %Y')}")
        lines.append(f"STATUS:         {self.readiness_status.replace('_', '-')} — Remedies Exhausted")
        lines.append("")
        lines.append("This packet establishes: (1) notice was given, (2) violations persisted,")
        lines.append("and (3) defendant failed to comply despite opportunity to cure.")
        lines.append("")

        # ==================================================================
        # PARTIES INVOLVED
        # ==================================================================
        lines.append(section("PARTIES INVOLVED"))
        lines.append(f"PLAINTIFF:          {self.consumer_name or '[Consumer Name]'}")
        lines.append("")
        lines.append(f"DEFENDANT CRA:      {self.cra_name or '[Credit Bureau]'}")
        lines.append("")
        if self.furnisher_name:
            lines.append(f"DEFENDANT FURNISHER: {self.furnisher_name}")
            lines.append("")

        # ==================================================================
        # NOTICE TIMELINE — Legal, Not UI
        # ==================================================================
        lines.append(section("NOTICE TIMELINE — BASIS FOR WILLFUL/NEGLIGENT LIABILITY"))
        lines.append("")
        lines.append("The following timeline establishes that Defendant received formal notice")
        lines.append("of inaccurate reporting and failed to cure despite opportunity to do so:")
        lines.append("")

        # Count dispute events
        dispute_count = len([t for t in self.timeline if 'dispute' in t.event_type.lower()])
        response_count = len([t for t in self.timeline if 'response' in t.event_type.lower()])

        # Detect if this is CFPB-first route (notice via regulatory complaint, not CRA dispute)
        is_cfpb_route = (
            self.tier3_classification == "CFPB" or
            any("cfpb" in t.event_type.lower() for t in self.timeline)
        )
        cfpb_notice_count = len([t for t in self.timeline if 'cfpb' in t.event_type.lower()])

        lines.append("PHASE 1: PRE-DISPUTE VIOLATIONS")
        lines.append("━" * w)
        lines.append(f"    • {self.total_violation_count} FCRA violations detected in credit file")
        lines.append("    • Violations existed BEFORE any dispute was filed")
        lines.append("    • Defendant had duty to assure maximum possible accuracy (§1681e(b))")
        lines.append("")

        # Phase 2: Route-aware language (CFPB vs CRA dispute)
        if is_cfpb_route:
            lines.append("PHASE 2: POST-NOTICE PERSISTENCE (CFPB)")
            lines.append("━" * w)
            lines.append("    • Consumer filed CFPB regulatory complaint identifying violations")
            lines.append("    • Defendant received formal notice via CFPB complaint process")
            lines.append("    • Defendant had full opportunity to cure after regulatory notice")
            lines.append("    • Violations PERSISTED after notice — Defendant failed to cure")
        else:
            lines.append("PHASE 2: POST-DISPUTE PERSISTENCE")
            lines.append("━" * w)
            lines.append(f"    • Consumer filed {dispute_count} formal dispute(s)")
            lines.append("    • Defendant received written notice identifying specific inaccuracies")
            lines.append("    • Defendant had statutory obligation to investigate (§1681i(a))")
            lines.append("    • Violations PERSISTED after dispute — Defendant failed to cure")
        lines.append("")

        if response_count > 0:
            lines.append("PHASE 3: POST-RESPONSE CONTINUATION")
            lines.append("━" * w)
            lines.append(f"    • Defendant provided {response_count} response(s)")
            lines.append("    • Responses failed to address documented inaccuracies")
            lines.append("    • Defendant continued reporting unchanged inaccurate information")
            lines.append("    • This constitutes continued noncompliance AFTER notice")
            lines.append("")

        lines.append("LEGAL SIGNIFICANCE:")
        lines.append("━" * w)
        lines.append("    Continued reporting of inaccurate information AFTER formal notice")
        lines.append("    transforms simple negligence into potential WILLFUL noncompliance")
        lines.append("    under 15 U.S.C. § 1681n, supporting enhanced damages.")
        lines.append("")

        # ==================================================================
        # VIOLATIONS ALLEGED
        # ==================================================================
        lines.append(section("VIOLATIONS ALLEGED"))
        lines.append("")
        lines.append("Plaintiff alleges the following FCRA violations, each supported by")
        lines.append("documentary evidence and Metro-2 field analysis:")
        lines.append("")

        # Check for DOFD and cross-bureau issues
        def _get_vtype(v) -> str:
            if isinstance(v, dict):
                return (v.get("violation_type", "") or "").lower()
            return (getattr(v, "violation_type", "") or "").lower()

        has_dofd = any("dofd" in _get_vtype(v) for v in self.primary_violations)
        cross_bureau_types = {"date_opened_mismatch", "dofd_mismatch", "balance_mismatch",
                             "status_mismatch", "payment_history_mismatch", "past_due_mismatch"}
        has_cross_bureau = any(_get_vtype(v) in cross_bureau_types for v in self.primary_violations)

        # ------------------------------
        # Bug #1 Fix: Group violations by type
        # ------------------------------
        violations_by_type: Dict[str, List[Any]] = defaultdict(list)
        for v in (self.primary_violations or []):
            # Handle both Violation objects and dicts
            if isinstance(v, dict):
                vtype = (v.get("violation_type", "") or "unknown").strip()
            else:
                vtype = (getattr(v, "violation_type", "") or "unknown").strip()
            violations_by_type[vtype].append(v)

        # Helper: collect unique affected accounts from a list of violations
        def _collect_accounts_from_violations(v_list: List[Any]) -> List[str]:
            seen = set()
            out: List[str] = []
            for vv in v_list:
                # Handle both Violation objects and dicts
                if isinstance(vv, dict):
                    # Dict format (from serialized violations)
                    ev = vv.get("evidence", {}) or {}
                    creditor = (
                        vv.get("creditor_name")         # Check TOP-LEVEL first for dicts
                        or ev.get("creditor_name")
                        or ev.get("furnisher_name")
                        or "Unknown"
                    )
                    acct = (
                        vv.get("account_number_masked") # Check TOP-LEVEL first for dicts
                        or ev.get("account_number_masked")
                        or ev.get("account")
                        or "****"
                    )
                else:
                    # Violation object format
                    ev = getattr(vv, "evidence", None) or {}
                    creditor = (
                        getattr(vv, "creditor_name", None)
                        or ev.get("creditor_name")
                        or ev.get("furnisher_name")
                        or "Unknown"
                    )
                    acct = (
                        getattr(vv, "account_number_masked", None)
                        or ev.get("account_number_masked")
                        or ev.get("account")
                        or "****"
                    )

                key = (str(creditor), str(acct))
                if key in seen:
                    continue
                seen.add(key)
                out.append(f"{creditor} — Account: {acct}")
            return out

        issue_num = 1
        for vtype, v_list in violations_by_type.items():
            title = vtype.replace("_", " ").upper()
            lines.append(subsection(f"VIOLATION #{issue_num}: {title}"))

            lines.append("")
            lines.append("    Affected accounts:")
            accounts = _collect_accounts_from_violations(v_list)
            if accounts:
                for a in accounts:
                    lines.append(f"      • {a}")
            else:
                lines.append("      • (Accounts not specified in evidence)")
            lines.append("")
            # Handle both Violation objects and dicts for severity
            if v_list:
                first_v = v_list[0]
                if isinstance(first_v, dict):
                    sev = first_v.get("severity", "medium")
                else:
                    sev = getattr(first_v, "severity", "medium")
            else:
                sev = "medium"
            lines.append(f"    Severity:         {sev}")
            lines.append("    Status:           PERSISTED AFTER NOTICE")
            lines.append("")
            issue_num += 1

        # ------------------------------
        # Bug #2 Fix: Discrepancies become violations (e.g., Date Opened Mismatch)
        # Render ONE violation per field mismatch, listing all affected accounts
        # ------------------------------
        discrepancy_groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for d in (self.discrepancies or []):
            if not isinstance(d, dict):
                continue
            field_name = (d.get("field_name") or "unknown_field").strip()
            discrepancy_groups[field_name].append(d)

        for field_name, d_list in discrepancy_groups.items():
            # Title normalization: "date_opened" -> "DATE OPENED MISMATCH"
            base = field_name.replace("_", " ").upper()
            lines.append(subsection(f"VIOLATION #{issue_num}: {base} MISMATCH (CROSS-BUREAU)"))
            lines.append("")
            lines.append("    Affected accounts:")

            seen = set()
            for d in d_list:
                creditor = d.get("creditor_name", "Unknown")
                acct = d.get("account_number_masked", "****")
                key = (creditor, acct)
                if key in seen:
                    continue
                seen.add(key)
                lines.append(f"      • {creditor} — Account: {acct}")
            lines.append("")
            lines.append("    Severity:         high")
            lines.append("    Status:           PERSISTED AFTER NOTICE")
            lines.append("")
            issue_num += 1

        # ==================================================================
        # DOFD ALLEGATIONS (if applicable)
        # ==================================================================
        if has_dofd:
            lines.append(section("DOFD ALLEGATIONS — MANDATORY FIELD OMISSION"))
            lines.append("")
            lines.append("Plaintiff specifically alleges that Defendant failed to report the")
            lines.append("Date of First Delinquency (DOFD), a MANDATORY Metro-2 field:")
            lines.append("")
            lines.append("1. DOFD OMISSION PREVENTS STATUTORY COMPLIANCE")
            lines.append("━" * w)
            lines.append("    Without DOFD, the 7-year obsolescence calculation required by")
            lines.append("    15 U.S.C. § 1681c(a) cannot be performed. The consumer cannot")
            lines.append("    verify when negative information should be purged.")
            lines.append("")
            lines.append("2. CONTINUED REPORTING WITHOUT DOFD IS UNLAWFUL")
            lines.append("━" * w)
            lines.append("    Reporting derogatory information without the mandatory DOFD field")
            lines.append("    is incompatible with Metro-2 required reporting standards and")
            lines.append("    defeats § 1681c(a) obsolescence verification.")
            lines.append("")
            lines.append("3. POST-NOTICE CONTINUATION SHOWS RECKLESS DISREGARD")
            lines.append("━" * w)
            lines.append("    Defendant continued reporting without DOFD AFTER receiving formal")
            lines.append("    notice of this deficiency. This demonstrates reckless disregard")
            lines.append("    for accuracy obligations, supporting willful noncompliance.")
            lines.append("")

        # ==================================================================
        # CROSS-BUREAU CONTRADICTIONS (if applicable)
        # ==================================================================
        if has_cross_bureau or self.discrepancies:
            lines.append(section("CROSS-BUREAU CONTRADICTIONS — INCONSISTENT REPORTING"))
            lines.append("")
            lines.append("The following data fields are reported DIFFERENTLY across credit bureaus,")
            lines.append("proving that at least one bureau is reporting inaccurate information:")
            lines.append("")

            # Show actual discrepancy data with values by bureau
            if self.discrepancies:
                for d in self.discrepancies:
                    if isinstance(d, dict):
                        field = d.get('field_name', 'Unknown field')
                        creditor = d.get('creditor_name', 'Unknown')
                        acct = d.get('account_number_masked', '****')
                        values = d.get('values_by_bureau', {})

                        lines.append(f"Account: {creditor} — {acct}")
                        lines.append(f"  Field: {field.replace('_', ' ').title()}")
                        if values:
                            for bureau, value in values.items():
                                lines.append(f"    • {bureau.title()}: {value}")
                        lines.append("")
            else:
                # Fallback to listing violation types
                for v in self.primary_violations:
                    vtype = _get_vtype(v)
                    if vtype in cross_bureau_types:
                        lines.append(f"    • {vtype.replace('_', ' ').title()}")
                lines.append("")

            lines.append("LEGAL SIGNIFICANCE:")
            lines.append("━" * w)
            lines.append("    These contradictions CANNOT simultaneously be accurate. At minimum,")
            lines.append("    one bureau is reporting false information. Continued contradictory")
            lines.append("    reporting after notice demonstrates reckless disregard for the")
            lines.append("    maximum possible accuracy standard of 15 U.S.C. § 1681e(b).")
            lines.append("")

        # ==================================================================
        # PATTERN OF CONDUCT
        # ==================================================================
        lines.append(section("PATTERN OF CONDUCT — NOT ISOLATED INCIDENT"))
        lines.append("")
        lines.append("This case demonstrates a PATTERN of noncompliance, not an isolated error:")
        lines.append("")
        lines.append(f"    • {self.total_violation_count} distinct violations detected")
        # Route-aware notice language
        if is_cfpb_route:
            lines.append("    • Notice provided via CFPB regulatory complaint")
        else:
            lines.append(f"    • {dispute_count} formal disputes filed by consumer")
        if self.discrepancies:
            lines.append(f"    • {len(self.discrepancies)} cross-bureau contradictions documented")
        if self.examiner_failures:
            lines.append(f"    • {len(self.examiner_failures)} examiner standard failures recorded")
        lines.append("    • Violations persisted through MULTIPLE notice events")
        lines.append("    • Generic verification responses provided without factual review")
        lines.append("")
        lines.append("This pattern supports enhanced liability under FCRA §§ 1681n/1681o:")
        lines.append("")
        lines.append("    § 1681n (WILLFUL): Pattern shows knowing/reckless disregard")
        lines.append("    § 1681o (NEGLIGENT): At minimum, failure to maintain reasonable procedures")
        lines.append("")

        # ==================================================================
        # EXAMINER FAILURE ANALYSIS
        # ==================================================================
        if self.examiner_failures:
            lines.append(section("REGULATORY EXAMINATION FAILURES"))
            lines.append("")
            lines.append("The following CFPB examiner standards were applied to Defendant's")
            lines.append("dispute handling. Each failure supports the pattern-of-conduct theory:")
            lines.append("")

            for i, failure in enumerate(self.examiner_failures, 1):
                result = failure.get("result", "UNKNOWN")
                reason = failure.get("reason", "No reason provided")
                check_name = result.replace("FAIL_", "").replace("_", " ").title()
                lines.append(f"EXAMINER CHECK #{i}: {check_name}")
                lines.append("━" * w)
                lines.append(f"    Result:     FAILED")
                lines.append(f"    Finding:    {reason}")
                lines.append(f"    Liability:  Supports willful/negligent noncompliance theory")
                lines.append("")

        # ==================================================================
        # ELEMENTS OF FCRA CLAIM — Litigation Checklist
        # ==================================================================
        lines.append(section("ELEMENTS OF FCRA CLAIM — ALL SATISFIED"))
        lines.append("")

        # Route-aware elements (CFPB vs CRA dispute notice)
        if is_cfpb_route:
            notice_element = ("2. CONSUMER PROVIDED NOTICE VIA CFPB COMPLAINT", bool(self.timeline),
                            "CFPB complaint and company response attached")
        else:
            notice_element = ("2. CONSUMER PROVIDED NOTICE VIA DISPUTE", bool(self.timeline),
                            "Dispute letters with certified mail receipts attached")

        elements = [
            ("1. INACCURATE INFORMATION REPORTED", bool(self.primary_violations),
             "Documentary evidence of Metro-2 violations attached"),
            notice_element,
            ("3. DEFENDANT FAILED REASONABLE INVESTIGATION", bool(self.examiner_failures),
             "Generic verification without factual review documented"),
            ("4. VIOLATIONS PERSISTED AFTER NOTICE", True,
             "Current credit report shows unchanged inaccurate data"),
        ]

        for element, satisfied, evidence in elements:
            status = "✓ ESTABLISHED" if satisfied else "○ PENDING"
            lines.append(f"{element}")
            lines.append("━" * w)
            lines.append(f"    Status:   {status}")
            lines.append(f"    Evidence: {evidence}")
            lines.append("")

        # ==================================================================
        # WILLFULNESS ANALYSIS
        # ==================================================================
        damages = self.potential_damages
        lines.append(section("WILLFULNESS ANALYSIS — §1681n vs §1681o"))
        lines.append("")

        willful_factors = []
        if self.tier3_classification == "REPEATED_VERIFICATION_FAILURE":
            willful_factors.append("Verified disputed information multiple times without review")
        if len(self.examiner_failures) >= 2:
            willful_factors.append(f"{len(self.examiner_failures)} examiner standard failures")
        for v in self.primary_violations:
            v_sev = v.get("severity", "") if isinstance(v, dict) else getattr(v, "severity", "")
            v_type = _get_vtype(v)
            if v_sev == "CRITICAL":
                willful_factors.append(f"Critical violation: {v_type}")
        if dispute_count >= 2:
            willful_factors.append(f"Ignored {dispute_count} formal disputes")
        willful_factors.append("Pattern consistent with automated verification without human review")

        if willful_factors:
            lines.append("FACTORS SUPPORTING WILLFUL NONCOMPLIANCE (§1681n):")
            lines.append("━" * w)
            for factor in willful_factors:
                lines.append(f"    ☒ {factor}")
            lines.append("")

        lines.append("WILLFULNESS DETERMINATION:")
        lines.append("━" * w)
        lines.append("    RECKLESS DISREGARD — Continued violations after formal notice")
        lines.append("    Evidence supports §1681n willful claim; discovery may establish knowing misconduct")
        lines.append("")

        # ==================================================================
        # DAMAGES AVAILABLE
        # ==================================================================
        lines.append(section("DAMAGES AVAILABLE"))
        lines.append("")
        lines.append("STATUTORY DAMAGES (15 U.S.C. § 1681n(a)(1)(A))")
        lines.append("━" * w)
        lines.append(f"    Per-violation range: $100 – $1,000")
        # Calculate statutory count from grouped violations + discrepancies
        statutory_count = len(violations_by_type) + len(discrepancy_groups)
        statutory_min = 100 * statutory_count
        statutory_max = 1000 * statutory_count
        lines.append(f"    Violations alleged:  {statutory_count}")
        lines.append(f"    Statutory range:     ${statutory_min:,} – ${statutory_max:,}")
        lines.append("")

        if damages.get("punitive_eligible"):
            lines.append("PUNITIVE DAMAGES (15 U.S.C. § 1681n(a)(2))")
            lines.append("━" * w)
            lines.append("    Status:    AVAILABLE — Willfulness indicators present")
            lines.append("    Cap:       No statutory maximum")
            lines.append("    Standard:  Punish and deter willful noncompliance")
            lines.append("")

        lines.append("ACTUAL DAMAGES")
        lines.append("━" * w)
        lines.append("    Recoverable with documentation of:")
        lines.append("    • Credit denials or adverse terms")
        lines.append("    • Increased interest rates paid")
        lines.append("    • Emotional distress")
        lines.append("    • Time and expense of dispute process")
        lines.append("")

        lines.append("ATTORNEY'S FEES (15 U.S.C. § 1681n(a)(3) / §1681o(a)(2))")
        lines.append("━" * w)
        lines.append("    Status:    Recoverable by prevailing plaintiff")
        lines.append("    Standard:  Fee-shifting provision encourages FCRA enforcement")
        lines.append("")

        # ==================================================================
        # STATUTES VIOLATED
        # ==================================================================
        lines.append(section("STATUTES VIOLATED"))
        lines.append("")
        for statute in self.statutes_violated:
            lines.append(f"    • {statute}")
        lines.append("")

        # ==================================================================
        # EVIDENCE EXHIBITS
        # ==================================================================
        lines.append(section("EVIDENCE EXHIBITS"))
        lines.append("")
        lines.append("    Exhibit A:  Credit report with violations highlighted")
        lines.append("    Exhibit B:  Dispute letters with certified mail receipts")
        lines.append("    Exhibit C:  Defendant response letters (generic verification)")
        lines.append("    Exhibit D:  Current credit report showing UNCHANGED violations")
        lines.append("    Exhibit E:  Timeline of notice events and Defendant failures")
        if self.document_hashes:
            lines.append(f"    Exhibit F:  Evidence integrity hashes ({len(self.document_hashes)} documents)")
        lines.append("")

        # ==================================================================
        # FOOTER — Integrity Verification
        # ==================================================================
        lines.append("=" * w)
        lines.append("")
        lines.append("    This litigation packet was generated by an automated FCRA")
        lines.append("    enforcement system. All violations were detected using")
        lines.append("    deterministic rules applied to Metro-2 credit data fields.")
        lines.append("")
        lines.append("    PACKET ALLEGATION: Notice was given, violations persisted,")
        lines.append("    and Defendant failed to comply despite opportunity to cure.")
        lines.append("")
        lines.append(f"    Case Packet ID:   {self.packet_id}")
        lines.append(f"    Generated:        {self.created_at.strftime('%Y-%m-%d %H:%M:%S')} UTC")
        lines.append(f"    Integrity Hash:   {self.packet_hash[:16]}...")
        lines.append("")
        lines.append("=" * w)

        return "\n".join(lines)

    def _wrap_text(self, text: str, width: int) -> List[str]:
        """Wrap text to specified width."""
        words = text.split()
        lines = []
        current_line = []
        current_length = 0

        for word in words:
            if current_length + len(word) + 1 <= width:
                current_line.append(word)
                current_length += len(word) + 1
            else:
                if current_line:
                    lines.append(" ".join(current_line))
                current_line = [word]
                current_length = len(word)

        if current_line:
            lines.append(" ".join(current_line))

        return lines


class AttorneyPacketBuilder:
    """
    Builds attorney-ready case packets from Tier-3 disputes.

    Tier-5 component. Consumes ledger outputs only.
    No auto-sending — generation only.

    Usage:
        builder = AttorneyPacketBuilder(db)
        packet = builder.build_packet(dispute_id)
    """

    # FCRA statutory damages
    FCRA_STATUTORY_MIN = 100
    FCRA_STATUTORY_MAX = 1000
    FCRA_WILLFUL_PUNITIVE_CAP = None  # No cap for willful

    # FDCPA damages
    FDCPA_STATUTORY_MAX = 1000

    def __init__(self, db: Session):
        self.db = db

    def build_packet(
        self,
        dispute_id: str,
        include_consumer_name: bool = False,
    ) -> Optional[AttorneyPacket]:
        """
        Build attorney packet for a Tier-3 dispute.

        Args:
            dispute_id: The dispute UUID
            include_consumer_name: Whether to include PII

        Returns:
            AttorneyPacket or None if dispute not eligible
        """
        # Fetch dispute
        dispute = self.db.query(DisputeDB).filter(
            DisputeDB.id == dispute_id
        ).first()

        if not dispute:
            return None

        # Must be Tier-3 promoted
        if dispute.tier_reached < 3:
            return None

        # Get Tier-2 response
        tier2_response = self.db.query(Tier2ResponseDB).filter(
            Tier2ResponseDB.dispute_id == dispute_id,
            Tier2ResponseDB.tier3_promoted == True,
        ).first()

        # Build packet
        packet = AttorneyPacket(
            packet_id=str(uuid4()),
            dispute_id=dispute_id,
            user_id=dispute.user_id,
            cra_name=dispute.entity_name or "",
        )

        # 1. Extract violations from original dispute data
        self._extract_violations(packet, dispute)

        # 2. Extract Tier-3 classification
        if tier2_response:
            packet.tier3_classification = tier2_response.tier3_classification or ""
            packet.cure_outcome = tier2_response.response_type.value if tier2_response.response_type else ""

        # 3. Build timeline from paper trail
        self._build_timeline(packet, dispute_id)

        # 4. Collect document hashes from execution ledger
        self._collect_evidence(packet, dispute_id)

        # 5. Determine statutes violated
        self._determine_statutes(packet)

        # 6. Calculate potential damages
        self._calculate_damages(packet)

        # 7. Set readiness status
        packet.readiness_status = self._determine_readiness(packet)

        # 8. Compute integrity hash
        packet.packet_hash = packet.compute_hash()

        return packet

    def build_all_ready_packets(
        self,
        limit: int = 100,
    ) -> List[AttorneyPacket]:
        """
        Build packets for all Tier-3 disputes without packets.

        For batch processing.

        Args:
            limit: Maximum packets to build

        Returns:
            List of built packets
        """
        # Find Tier-3 disputes without packets
        disputes = (
            self.db.query(DisputeDB)
            .filter(
                DisputeDB.tier_reached >= 3,
                DisputeDB.locked == True,
            )
            .limit(limit)
            .all()
        )

        packets = []
        for dispute in disputes:
            packet = self.build_packet(dispute.id)
            if packet:
                packets.append(packet)

        return packets

    def _extract_violations(
        self,
        packet: AttorneyPacket,
        dispute: DisputeDB,
    ) -> None:
        """Extract violations from dispute's original violation data."""
        # Handle both list and dict formats
        raw_data = dispute.original_violation_data
        if isinstance(raw_data, list):
            # List format - each item is a violation
            contradictions = raw_data
        elif isinstance(raw_data, dict):
            contradictions = raw_data.get("contradictions", [])
        else:
            contradictions = []

        for contra in contradictions:
            violation = AttorneyPacketViolation(
                violation_id=contra.get("id", str(uuid4())),
                violation_type=contra.get("rule_code", "UNKNOWN"),
                severity=contra.get("severity", "MEDIUM"),
                description=contra.get("description", ""),
                evidence=contra.get("evidence", {}),
                statute=contra.get("primary_statute"),
                metro2_field=contra.get("metro2_field"),
            )
            packet.primary_violations.append(violation)

            # Extract furnisher name from first violation
            if not packet.furnisher_name:
                packet.furnisher_name = contra.get("creditor_name", "")

        packet.total_violation_count = len(packet.primary_violations)

    def _build_timeline(
        self,
        packet: AttorneyPacket,
        dispute_id: str,
    ) -> None:
        """Build timeline from paper trail entries."""
        entries = (
            self.db.query(PaperTrailDB)
            .filter(PaperTrailDB.dispute_id == dispute_id)
            .order_by(PaperTrailDB.created_at.asc())
            .all()
        )

        for entry in entries:
            timeline_event = AttorneyPacketTimeline(
                date=entry.created_at,
                event_type=entry.event_type,
                description=entry.description or "",
                actor=entry.actor.value if entry.actor else "SYSTEM",
                evidence_hash=entry.evidence_hash,
            )
            packet.timeline.append(timeline_event)

            if entry.evidence_hash:
                packet.document_hashes.append(entry.evidence_hash)

    def _collect_evidence(
        self,
        packet: AttorneyPacket,
        dispute_id: str,
    ) -> None:
        """Collect evidence from execution ledger."""
        # Get execution events for this dispute
        events = (
            self.db.query(ExecutionEventDB)
            .filter(ExecutionEventDB.dispute_session_id == dispute_id)
            .all()
        )

        for event in events:
            if event.document_hash:
                packet.document_hashes.append(event.document_hash)
            if event.artifact_pointer:
                packet.artifact_pointers.append(event.artifact_pointer)

        # Get responses
        responses = (
            self.db.query(ExecutionResponseDB)
            .join(ExecutionEventDB)
            .filter(ExecutionEventDB.dispute_session_id == dispute_id)
            .all()
        )

        for response in responses:
            if response.examiner_standard_result:
                packet.examiner_failures.append({
                    "result": response.examiner_standard_result,
                    "reason": response.examiner_failure_reason,
                    "response_type": response.response_type.value if response.response_type else None,
                })

    def _determine_statutes(self, packet: AttorneyPacket) -> None:
        """Determine all statutes violated based on violations and failures."""
        statutes = set()

        # From violations
        for v in packet.primary_violations:
            if v.statute:
                statutes.add(v.statute)

        # Common FCRA violations based on classification
        classification_statutes = {
            "REPEATED_VERIFICATION_FAILURE": [
                "15 U.S.C. § 1681i(a)(1)(A)",  # Failure to investigate
                "15 U.S.C. § 1681e(b)",        # Reasonable procedures
            ],
            "FRIVOLOUS_DEFLECTION": [
                "15 U.S.C. § 1681i(a)(3)",     # Frivolous determination
            ],
            "CURE_WINDOW_EXPIRED": [
                "15 U.S.C. § 1681i(a)(1)(A)",  # Failure to investigate
                "15 U.S.C. § 1681i(a)(6)(A)",  # Notice of results
            ],
        }

        if packet.tier3_classification in classification_statutes:
            statutes.update(classification_statutes[packet.tier3_classification])

        # Always include core accuracy statute for data violations
        if packet.primary_violations:
            statutes.add("15 U.S.C. § 1681e(b)")

        packet.statutes_violated = sorted(list(statutes))

    def _calculate_damages(self, packet: AttorneyPacket) -> None:
        """Calculate potential damages range."""
        # FCRA statutory damages
        fcra_min = self.FCRA_STATUTORY_MIN * packet.total_violation_count
        fcra_max = self.FCRA_STATUTORY_MAX * packet.total_violation_count

        # Check for willful violation indicators
        willful_indicators = 0
        if packet.tier3_classification == "REPEATED_VERIFICATION_FAILURE":
            willful_indicators += 1
        if len(packet.examiner_failures) >= 2:
            willful_indicators += 1
        for v in packet.primary_violations:
            if v.severity == "CRITICAL":
                willful_indicators += 1

        packet.potential_damages = {
            "fcra_statutory_min": fcra_min,
            "fcra_statutory_max": fcra_max,
            "willful_indicators": willful_indicators,
            "willful_likely": willful_indicators >= 2,
            "punitive_eligible": willful_indicators >= 2,
            "notes": [
                "Statutory damages: $100-$1,000 per violation",
                "Actual damages recoverable with proof",
                "Attorney fees recoverable under FCRA",
            ],
        }

        if willful_indicators >= 2:
            packet.potential_damages["notes"].append(
                "Punitive damages available for willful noncompliance"
            )

    def _determine_readiness(self, packet: AttorneyPacket) -> str:
        """Determine packet readiness status."""
        # Check for regulatory escalation criteria
        regulatory_indicators = 0

        if packet.tier3_classification == "REPEATED_VERIFICATION_FAILURE":
            regulatory_indicators += 1
        if len(packet.examiner_failures) >= 2:
            regulatory_indicators += 1
        if packet.total_violation_count >= 3:
            regulatory_indicators += 1

        if regulatory_indicators >= 2:
            return "REGULATORY_READY"

        return "ATTORNEY_READY"

    def tag_dispute_readiness(
        self,
        dispute_id: str,
        readiness_status: str,
    ) -> bool:
        """
        Tag a dispute with readiness status.

        Args:
            dispute_id: The dispute UUID
            readiness_status: ATTORNEY_READY or REGULATORY_READY

        Returns:
            Success status
        """
        dispute = self.db.query(DisputeDB).filter(
            DisputeDB.id == dispute_id
        ).first()

        if not dispute:
            return False

        # Store in metadata (don't modify dispute state)
        if not dispute.metadata:
            dispute.metadata = {}

        dispute.metadata["readiness_status"] = readiness_status
        dispute.metadata["readiness_tagged_at"] = datetime.now(timezone.utc).isoformat()

        self.db.commit()
        return True
