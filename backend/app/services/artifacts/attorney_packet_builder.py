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
        violation_data = dispute.original_violation_data or {}
        contradictions = violation_data.get("contradictions", [])

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
