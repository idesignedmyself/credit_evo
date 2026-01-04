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

    def render_document(self) -> str:
        """
        Render the packet as a printable document for attorney consultation.

        Returns a formatted text document suitable for printing.
        """
        lines = []
        w = 80  # Document width

        def header(text: str) -> str:
            return "=" * w + "\n" + text.center(w) + "\n" + "=" * w

        def section(text: str) -> str:
            return "\n" + "=" * w + "\n" + text.center(w) + "\n" + "=" * w + "\n"

        def subsection(text: str) -> str:
            return "\n" + text + "\n" + "━" * w + "\n"

        # Title
        lines.append(header("FCRA VIOLATION CASE PACKET\nPrepared for Attorney Consultation"))
        lines.append("")
        lines.append(f"CASE REFERENCE: {self.packet_id}")
        lines.append(f"GENERATED:      {self.created_at.strftime('%B %d, %Y')}")
        lines.append(f"STATUS:         {self.readiness_status.replace('_', '-')} (Tier-3 Exhausted)")

        # Parties
        lines.append(section("PARTIES INVOLVED"))
        lines.append(f"CONSUMER:           [Name Redacted]")
        if self.consumer_name:
            lines.append(f"                    {self.consumer_name}")
        lines.append("")
        lines.append(f"CREDIT BUREAU:      {self.cra_name or 'Unknown CRA'}")
        lines.append("")
        if self.furnisher_name:
            lines.append(f"FURNISHER:          {self.furnisher_name}")
            lines.append("")

        # Violations
        lines.append(section("VIOLATIONS DETECTED"))

        for i, v in enumerate(self.primary_violations, 1):
            violation_title = f"VIOLATION #{i}: {v.violation_type.replace('_', ' ')} (Rule {v.violation_type[:2] if len(v.violation_type) >= 2 else v.violation_type})"
            lines.append(subsection(violation_title))

            # Description
            if v.description:
                # Word wrap description
                desc_lines = self._wrap_text(v.description, w - 4)
                for dl in desc_lines:
                    lines.append(dl)
                lines.append("")

            lines.append(f"    Severity:    {v.severity}")
            if v.statute:
                lines.append(f"    Statute:     {v.statute}")
            if v.metro2_field:
                lines.append(f"    Field:       {v.metro2_field}")
            lines.append("")

        # Dispute History / Timeline
        lines.append(section("DISPUTE HISTORY"))
        lines.append("")
        lines.append("DATE           ACTION                                              OUTCOME")
        lines.append("─" * w)

        for event in self.timeline:
            date_str = event.date.strftime("%b %d, %Y") if event.date else "Unknown"
            desc = event.description[:50] if event.description else event.event_type
            lines.append(f"{date_str:<14} {desc:<55}")

        lines.append("")

        # Examiner Failures
        if self.examiner_failures:
            lines.append(section("EXAMINER FAILURE ANALYSIS"))
            lines.append("")
            lines.append("The following regulatory examination standards were applied.")
            lines.append("")

            for i, failure in enumerate(self.examiner_failures, 1):
                result = failure.get("result", "UNKNOWN")
                reason = failure.get("reason", "No reason provided")

                check_name = result.replace("FAIL_", "").replace("_", " ").title()
                lines.append(f"CHECK #{i}: {check_name}")
                lines.append("━" * w)
                lines.append(f"    Result:    FAILED")
                lines.append(f"    Finding:   {reason}")
                lines.append("")

        # Tier-3 Classification
        lines.append(section("BASIS FOR LEGAL ACTION"))
        lines.append("")

        classification_text = {
            "REPEATED_VERIFICATION_FAILURE": (
                "REPEATED VERIFICATION FAILURE:\n\n"
                "    The credit reporting agency verified disputed information multiple times\n"
                "    despite receiving documentary evidence proving the information is inaccurate.\n"
                "    This pattern indicates willful noncompliance with FCRA investigation\n"
                "    requirements."
            ),
            "FRIVOLOUS_DEFLECTION": (
                "FRIVOLOUS DEFLECTION:\n\n"
                "    The credit reporting agency improperly rejected the dispute as frivolous\n"
                "    without meeting the statutory requirements for such a determination.\n"
                "    The required written notice with specific reasons was not provided."
            ),
            "CURE_WINDOW_EXPIRED": (
                "CURE WINDOW EXPIRED:\n\n"
                "    The credit reporting agency failed to complete its investigation within\n"
                "    the 30-day statutory window (or 45 days if extended). The consumer's\n"
                "    right to timely investigation was violated."
            ),
        }

        lines.append(classification_text.get(
            self.tier3_classification,
            f"Classification: {self.tier3_classification}"
        ))
        lines.append("")
        lines.append("CURE ATTEMPT EXHAUSTED:")
        lines.append("")
        lines.append(f"    • Dispute rounds completed: {len([t for t in self.timeline if 'dispute' in t.event_type.lower()])}")
        lines.append(f"    • Examiner failures recorded: {len(self.examiner_failures)}")
        lines.append(f"    • Consumer remedies through dispute process: EXHAUSTED")

        # Elements of Claim
        lines.append(section("ELEMENTS OF FCRA CLAIM"))
        lines.append("")

        elements = [
            ("1. INACCURATE INFORMATION REPORTED", bool(self.primary_violations)),
            ("2. CONSUMER DISPUTED THE INACCURACY", bool(self.timeline)),
            ("3. FAILURE TO CONDUCT REASONABLE INVESTIGATION", bool(self.examiner_failures)),
            ("4. CONTINUED REPORTING OF INACCURATE INFORMATION", self.tier3_classification == "REPEATED_VERIFICATION_FAILURE"),
        ]

        for element, satisfied in elements:
            status = "✓ SATISFIED" if satisfied else "○ PENDING"
            lines.append(f"{element:<55} {status}")
            lines.append("─" * w)
            lines.append("")

        # Willfulness Indicators
        damages = self.potential_damages
        if damages.get("willful_likely"):
            lines.append(section("WILLFULNESS INDICATORS"))
            lines.append("")
            lines.append("The following factors suggest WILLFUL rather than negligent noncompliance:")
            lines.append("")

            if self.tier3_classification == "REPEATED_VERIFICATION_FAILURE":
                lines.append("    ☒ Verified disputed information multiple times")
            if len(self.examiner_failures) >= 2:
                lines.append("    ☒ Multiple examiner check failures")
            for v in self.primary_violations:
                if v.severity == "CRITICAL":
                    lines.append(f"    ☒ Critical violation: {v.violation_type}")
            lines.append("    ☒ Pattern consistent with automated verification without human review")
            lines.append("")

        # Damages
        lines.append(section("DAMAGES AVAILABLE"))
        lines.append("")
        lines.append("STATUTORY DAMAGES (15 U.S.C. § 1681n(a)(1)(A))")
        lines.append(f"    Range: ${damages.get('fcra_statutory_min', 100):,} – ${damages.get('fcra_statutory_max', 1000):,} per willful violation")
        lines.append("")

        if damages.get("punitive_eligible"):
            lines.append("PUNITIVE DAMAGES (15 U.S.C. § 1681n(a)(2))")
            lines.append("    Available where willfulness is established")
            lines.append("    No statutory cap")
            lines.append("")

        lines.append("ACTUAL DAMAGES")
        lines.append("    • Credit denials or adverse terms")
        lines.append("    • Increased interest rates paid")
        lines.append("    • Emotional distress")
        lines.append("    • Time spent disputing")
        lines.append("")
        lines.append("ATTORNEY'S FEES (15 U.S.C. § 1681n(a)(3))")
        lines.append("    Recoverable by prevailing plaintiff")

        # Statutes
        lines.append(section("STATUTES VIOLATED"))
        lines.append("")
        for statute in self.statutes_violated:
            lines.append(f"    • {statute}")
        lines.append("")

        # Evidence
        lines.append(section("ATTACHED EXHIBITS"))
        lines.append("")
        lines.append("    Exhibit A:  Credit report with violations highlighted")
        lines.append("    Exhibit B:  Dispute letters with certified mail receipts")
        lines.append("    Exhibit C:  Entity response letters")
        lines.append("    Exhibit D:  Current credit report showing unchanged data")
        if self.document_hashes:
            lines.append(f"    Exhibit E:  Evidence integrity hashes ({len(self.document_hashes)} documents)")
        lines.append("")

        # Footer
        lines.append("=" * w)
        lines.append("")
        lines.append("    This packet was generated by an automated FCRA enforcement system.")
        lines.append("    All violations were detected using deterministic rules applied to")
        lines.append("    Metro 2 credit data schema fields. No AI interpretation was used")
        lines.append("    in violation detection.")
        lines.append("")
        lines.append(f"    Case Packet ID: {self.packet_id}")
        lines.append(f"    Generated: {self.created_at.strftime('%Y-%m-%d %H:%M:%S')} UTC")
        lines.append(f"    Integrity Hash: {self.packet_hash[:16]}...")
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
