"""
Explanation Renderer (Tier 6)

Copilot as Regulator Translator — explains outcomes clearly to humans.

Renders explanations in three dialects:
1. Consumer view (plain English)
2. Examiner view (procedural failure framing)
3. Attorney view (elements + evidence)

Maps each Tier-3 classification to explanation templates.
Read-only — trust layer for human understanding.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from enum import Enum

from sqlalchemy.orm import Session

from ...models.db_models import (
    DisputeDB,
    Tier2ResponseDB,
    PaperTrailDB,
)


class ExplanationDialect(str, Enum):
    """Target audience for explanation."""
    CONSUMER = "consumer"    # Plain English, empowering
    EXAMINER = "examiner"    # Procedural, regulatory lens
    ATTORNEY = "attorney"    # Legal elements, evidence-focused


@dataclass
class Explanation:
    """Rendered explanation for a specific audience."""
    dialect: ExplanationDialect
    headline: str
    summary: str
    key_points: List[str] = field(default_factory=list)
    evidence_summary: List[str] = field(default_factory=list)
    next_steps: List[str] = field(default_factory=list)
    legal_basis: Optional[str] = None
    rendered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "dialect": self.dialect.value,
            "headline": self.headline,
            "summary": self.summary,
            "key_points": self.key_points,
            "evidence_summary": self.evidence_summary,
            "next_steps": self.next_steps,
            "legal_basis": self.legal_basis,
            "rendered_at": self.rendered_at.isoformat(),
        }


# =============================================================================
# EXPLANATION TEMPLATES BY TIER-3 CLASSIFICATION
# =============================================================================

CONSUMER_TEMPLATES = {
    "REPEATED_VERIFICATION_FAILURE": {
        "headline": "The credit bureau refused to fix proven errors",
        "summary": (
            "You disputed inaccurate information with evidence proving it was wrong. "
            "The bureau claimed they \"verified\" the data twice, but never explained "
            "how impossible data could be accurate. This is a serious violation of your rights."
        ),
        "key_points": [
            "You sent clear evidence showing the data was wrong",
            "The bureau said they verified it — but didn't address your evidence",
            "They did this twice, showing a pattern of ignoring disputes",
            "Federal law requires them to actually investigate, not rubber-stamp",
        ],
        "next_steps": [
            "Your case has been documented and is ready for escalation",
            "You may be entitled to damages under the Fair Credit Reporting Act",
            "An attorney can help you recover compensation for this violation",
        ],
    },
    "FRIVOLOUS_DEFLECTION": {
        "headline": "The credit bureau refused to investigate your dispute",
        "summary": (
            "Instead of investigating your dispute, the bureau rejected it as \"frivolous.\" "
            "However, you provided specific evidence of errors. Bureaus cannot dismiss "
            "well-documented disputes just because they don't want to investigate."
        ),
        "key_points": [
            "You filed a legitimate dispute with specific evidence",
            "The bureau called it 'frivolous' and refused to investigate",
            "Your dispute was not frivolous — it identified real errors",
            "This rejection violates federal law",
        ],
        "next_steps": [
            "Your case documents their improper rejection",
            "This type of deflection often indicates willful noncompliance",
            "Legal action may be appropriate to recover damages",
        ],
    },
    "CURE_WINDOW_EXPIRED": {
        "headline": "The credit bureau failed to respond within the legal deadline",
        "summary": (
            "After you disputed inaccurate information, the bureau was required to respond "
            "within 30 days. They didn't. We gave them an additional cure opportunity, "
            "and they still failed to respond. This is a clear violation of federal law."
        ),
        "key_points": [
            "You disputed the error and the bureau missed their 30-day deadline",
            "We sent a formal notice giving them another chance to comply",
            "They failed to respond within the cure window",
            "Their silence is a violation of the Fair Credit Reporting Act",
        ],
        "next_steps": [
            "Their failure to respond is documented in your case file",
            "No-response cases are often strong for legal action",
            "The bureau's silence speaks volumes about their procedures",
        ],
    },
}

EXAMINER_TEMPLATES = {
    "REPEATED_VERIFICATION_FAILURE": {
        "headline": "Perfunctory Investigation — FCRA § 1681i(a)(1)(A) Violation",
        "summary": (
            "The CRA verified disputed information twice despite consumer providing evidence "
            "of data impossibility. No meaningful investigation was conducted. The CRA's "
            "verification procedure failed to address specific factual contradictions."
        ),
        "key_points": [
            "Consumer dispute contained specific, verifiable evidence",
            "CRA response was generic verification without addressing evidence",
            "Pattern repeated on second-round dispute",
            "Indicates systemic failure in reasonable investigation procedures",
        ],
        "evidence_summary": [
            "Initial dispute with evidence: documented in ledger",
            "First verification response: generic, no evidence addressed",
            "Second dispute (Tier-2): repeated evidence submission",
            "Second verification: continued failure to investigate",
        ],
        "legal_basis": (
            "15 U.S.C. § 1681i(a)(1)(A) requires CRAs to conduct 'reasonable investigation' "
            "of disputed information. Verification without addressing consumer evidence "
            "does not satisfy this standard. See Cushman v. Trans Union Corp."
        ),
    },
    "FRIVOLOUS_DEFLECTION": {
        "headline": "Improper Frivolous Determination — FCRA § 1681i(a)(3) Violation",
        "summary": (
            "The CRA determined the consumer's dispute was frivolous despite receiving "
            "specific information identifying the disputed item and basis for dispute. "
            "This determination was improper under § 1681i(a)(3)(A)."
        ),
        "key_points": [
            "Consumer dispute identified specific inaccuracy",
            "Dispute included supporting documentation",
            "CRA determination of frivolousness was not supported",
            "Notice requirements under § 1681i(a)(3)(B) may also be violated",
        ],
        "evidence_summary": [
            "Dispute content: specific account identified, error described",
            "Evidence submitted: contradiction documentation provided",
            "CRA response: frivolous determination without adequate basis",
        ],
        "legal_basis": (
            "15 U.S.C. § 1681i(a)(3)(A) only permits frivolous determination when consumer "
            "fails to provide 'sufficient information to investigate.' Consumer provided "
            "specific, verifiable evidence of inaccuracy."
        ),
    },
    "CURE_WINDOW_EXPIRED": {
        "headline": "Failure to Provide Notice of Results — FCRA § 1681i(a)(6)(A) Violation",
        "summary": (
            "The CRA failed to respond to consumer dispute within 30-day statutory period. "
            "After Tier-2 cure notice, CRA continued to fail to respond. This constitutes "
            "failure to investigate and failure to provide notice of results."
        ),
        "key_points": [
            "Initial dispute: no response within 30 days",
            "Tier-2 cure notice sent: documented with tracking",
            "Cure window (15 days): no response received",
            "Total days without response exceeds statutory maximum",
        ],
        "evidence_summary": [
            "Dispute sent: date and method documented",
            "30-day deadline: passed without response",
            "Cure notice sent: date and delivery confirmation",
            "Cure window expiration: documented",
        ],
        "legal_basis": (
            "15 U.S.C. § 1681i(a)(6)(A) requires CRA to provide written notice of results "
            "within 5 days of completing investigation. Investigation must be completed "
            "within 30 days per § 1681i(a)(1). CRA failed both requirements."
        ),
    },
}

ATTORNEY_TEMPLATES = {
    "REPEATED_VERIFICATION_FAILURE": {
        "headline": "FCRA § 1681i(a)(1)(A) — Failure to Conduct Reasonable Investigation",
        "summary": (
            "CRA verified disputed information twice without addressing consumer's evidence "
            "of logical impossibility. Pattern suggests either (1) no investigation occurred, "
            "or (2) CRA's verification procedure is systemically deficient."
        ),
        "key_points": [
            "ELEMENT 1: Consumer disputed accuracy of information",
            "ELEMENT 2: Consumer provided relevant information with dispute",
            "ELEMENT 3: CRA failed to conduct reasonable investigation",
            "ELEMENT 4: Inaccurate information remained on report",
        ],
        "evidence_summary": [
            "Dispute letters with evidence (hash verified in ledger)",
            "CRA response letters (generic verification language)",
            "Tier-2 notice and second dispute documentation",
            "Continued reporting of disputed information",
        ],
        "next_steps": [
            "Statutory damages: $100-$1,000 per violation",
            "Actual damages: provable with credit denial evidence",
            "Punitive damages: available if willful (pattern suggests willfulness)",
            "Attorney fees: recoverable under 15 U.S.C. § 1681n/o",
        ],
        "legal_basis": (
            "15 U.S.C. § 1681i(a)(1)(A); Cushman v. Trans Union Corp., 115 F.3d 220 "
            "(3d Cir. 1997) — investigation must address specific dispute, not just "
            "parrot furnisher. See also Gorman v. Wolpoff & Abramson, 584 F.3d 1147 "
            "(9th Cir. 2009) — verification is not investigation."
        ),
    },
    "FRIVOLOUS_DEFLECTION": {
        "headline": "FCRA § 1681i(a)(3) — Improper Frivolous Determination",
        "summary": (
            "CRA rejected dispute as frivolous despite consumer providing specific "
            "identification of disputed item and supporting evidence. Frivolous "
            "determination not supported by statutory requirements."
        ),
        "key_points": [
            "ELEMENT 1: Consumer filed dispute with CRA",
            "ELEMENT 2: Consumer provided sufficient information to investigate",
            "ELEMENT 3: CRA determined dispute was frivolous",
            "ELEMENT 4: Determination was improper under § 1681i(a)(3)(A)",
        ],
        "evidence_summary": [
            "Dispute letter identifying specific account and error",
            "Supporting documentation (evidence of data impossibility)",
            "CRA frivolous determination notice",
            "Tier-2 follow-up demonstrating legitimacy of dispute",
        ],
        "next_steps": [
            "Strong willfulness argument: deflection to avoid investigation",
            "Pattern evidence if CRA has history of improper frivolous determinations",
            "Punitive damages appropriate for bad-faith deflection",
        ],
        "legal_basis": (
            "15 U.S.C. § 1681i(a)(3)(A) — frivolous only if consumer fails to provide "
            "'sufficient information to investigate the disputed information.' "
            "Consumer provided specific, documented evidence. See Dennis v. BEH-1, LLC, "
            "520 F.3d 1066 (9th Cir. 2008)."
        ),
    },
    "CURE_WINDOW_EXPIRED": {
        "headline": "FCRA § 1681i(a)(1) & (a)(6)(A) — Failure to Investigate and Notify",
        "summary": (
            "CRA failed to investigate within 30-day statutory period and failed to "
            "provide notice of results. After cure opportunity, CRA continued pattern "
            "of non-response. Clear statutory violation."
        ),
        "key_points": [
            "ELEMENT 1: Consumer filed valid dispute",
            "ELEMENT 2: 30-day investigation period expired",
            "ELEMENT 3: No investigation results provided",
            "ELEMENT 4: Cure opportunity given and expired",
        ],
        "evidence_summary": [
            "Dispute letter with certified mail tracking",
            "30-day deadline calculation",
            "Tier-2 cure notice with delivery confirmation",
            "Cure window expiration without response",
        ],
        "next_steps": [
            "Per se violation: no investigation within statutory period",
            "Strong case: timeline is clear and documented",
            "Attorney fees recoverable regardless of other damages",
        ],
        "legal_basis": (
            "15 U.S.C. § 1681i(a)(1)(A) — 30-day investigation deadline. "
            "15 U.S.C. § 1681i(a)(6)(A) — 5-day notice requirement after investigation. "
            "CRA violated both. No investigation = no notice of results."
        ),
    },
}


class ExplanationRenderer:
    """
    Renders human-readable explanations for Tier-3 outcomes.

    Tier-6 component. Trust layer for human understanding.
    Read-only — does not modify enforcement state.

    Usage:
        renderer = ExplanationRenderer(db)
        consumer_explanation = renderer.render(dispute_id, ExplanationDialect.CONSUMER)
        all_explanations = renderer.render_all_dialects(dispute_id)
    """

    def __init__(self, db: Session):
        self.db = db

    def render(
        self,
        dispute_id: str,
        dialect: ExplanationDialect,
    ) -> Optional[Explanation]:
        """
        Render explanation for a Tier-3 dispute in specified dialect.

        Args:
            dispute_id: The dispute UUID
            dialect: Target audience dialect

        Returns:
            Explanation or None if not eligible
        """
        # Fetch dispute and Tier-3 data
        dispute = self.db.query(DisputeDB).filter(
            DisputeDB.id == dispute_id
        ).first()

        if not dispute or dispute.tier_reached < 3:
            return None

        tier2_response = self.db.query(Tier2ResponseDB).filter(
            Tier2ResponseDB.dispute_id == dispute_id,
            Tier2ResponseDB.tier3_promoted == True,
        ).first()

        if not tier2_response:
            return None

        classification = tier2_response.tier3_classification or "UNKNOWN"

        # Select template based on dialect
        if dialect == ExplanationDialect.CONSUMER:
            template = CONSUMER_TEMPLATES.get(classification, {})
        elif dialect == ExplanationDialect.EXAMINER:
            template = EXAMINER_TEMPLATES.get(classification, {})
        elif dialect == ExplanationDialect.ATTORNEY:
            template = ATTORNEY_TEMPLATES.get(classification, {})
        else:
            return None

        if not template:
            return self._render_generic(dispute, tier2_response, dialect)

        # Build explanation from template
        explanation = Explanation(
            dialect=dialect,
            headline=template.get("headline", "Case Summary"),
            summary=template.get("summary", ""),
            key_points=template.get("key_points", []),
            evidence_summary=template.get("evidence_summary", []),
            next_steps=template.get("next_steps", []),
            legal_basis=template.get("legal_basis"),
        )

        # Enrich with case-specific details
        self._enrich_explanation(explanation, dispute, tier2_response)

        return explanation

    def render_all_dialects(
        self,
        dispute_id: str,
    ) -> Dict[str, Explanation]:
        """
        Render explanations in all three dialects.

        Args:
            dispute_id: The dispute UUID

        Returns:
            Dict mapping dialect name to Explanation
        """
        result = {}
        for dialect in ExplanationDialect:
            explanation = self.render(dispute_id, dialect)
            if explanation:
                result[dialect.value] = explanation
        return result

    def _render_generic(
        self,
        dispute: DisputeDB,
        tier2_response: Tier2ResponseDB,
        dialect: ExplanationDialect,
    ) -> Explanation:
        """Render a generic explanation for unknown classifications."""
        if dialect == ExplanationDialect.CONSUMER:
            return Explanation(
                dialect=dialect,
                headline="Your dispute has been fully documented",
                summary=(
                    "Your credit dispute went through all available administrative remedies. "
                    "The credit bureau or furnisher failed to properly resolve your concerns."
                ),
                key_points=[
                    "Your dispute was sent and documented",
                    "The response did not adequately address your concerns",
                    "All evidence has been preserved",
                ],
                next_steps=[
                    "Your case file is available for review",
                    "Consider consulting with a consumer rights attorney",
                ],
            )
        elif dialect == ExplanationDialect.EXAMINER:
            return Explanation(
                dialect=dialect,
                headline="Dispute Resolution Failure — Administrative Record Complete",
                summary="Consumer dispute exhausted administrative remedies without satisfactory resolution.",
                key_points=[
                    "Dispute filed and documented",
                    "Entity response inadequate",
                    "Tier-2 cure opportunity provided",
                    "Resolution failure documented",
                ],
            )
        else:  # ATTORNEY
            return Explanation(
                dialect=dialect,
                headline="FCRA Violation — Administrative Exhaustion Complete",
                summary="Consumer dispute proceeded through full administrative process. Case file contains complete evidence chain.",
                key_points=[
                    "Full dispute documentation available",
                    "Entity response(s) documented",
                    "Cure opportunity record complete",
                ],
                next_steps=[
                    "Review full case packet for specific violations",
                    "Assess statutory and actual damages",
                ],
            )

    def _enrich_explanation(
        self,
        explanation: Explanation,
        dispute: DisputeDB,
        tier2_response: Tier2ResponseDB,
    ) -> None:
        """Enrich explanation with case-specific details."""
        # Add entity name to summary if not present
        entity_name = dispute.entity_name or "The credit bureau"
        if entity_name not in explanation.summary:
            explanation.summary = explanation.summary.replace(
                "The credit bureau",
                entity_name
            ).replace(
                "the bureau",
                entity_name
            )

        # Add timeline info to evidence summary
        if dispute.dispute_date:
            explanation.evidence_summary.insert(
                0,
                f"Initial dispute filed: {dispute.dispute_date.isoformat()}"
            )

        if tier2_response.tier3_promotion_date:
            explanation.evidence_summary.append(
                f"Case elevated to Tier-3: {tier2_response.tier3_promotion_date.strftime('%Y-%m-%d')}"
            )

    def get_violation_explanation(
        self,
        violation_type: str,
        dialect: ExplanationDialect = ExplanationDialect.CONSUMER,
    ) -> Dict[str, str]:
        """
        Get explanation for a specific violation type.

        Args:
            violation_type: e.g., "T1", "D2", "PERFUNCTORY_INVESTIGATION"
            dialect: Target audience

        Returns:
            Dict with headline and description
        """
        # Violation type explanations
        violation_explanations = {
            "T1": {
                ExplanationDialect.CONSUMER: {
                    "headline": "Impossible Timeline",
                    "description": "The account shows a first late payment BEFORE the account was even opened. This is logically impossible.",
                },
                ExplanationDialect.EXAMINER: {
                    "headline": "DOFD Precedes Account Opening — Temporal Impossibility",
                    "description": "Date of First Delinquency reported before Date Opened. Metro 2 field contradiction.",
                },
                ExplanationDialect.ATTORNEY: {
                    "headline": "Logical Impossibility — DOFD < Date Opened",
                    "description": "Reported DOFD precedes account opening date. Data is logically impossible and cannot be accurate.",
                },
            },
            "T2": {
                ExplanationDialect.CONSUMER: {
                    "headline": "Payment History Longer Than Account Age",
                    "description": "The payment history shows more months than the account has existed. The data doesn't add up.",
                },
                ExplanationDialect.EXAMINER: {
                    "headline": "Payment History Exceeds Account Age — Data Integrity Failure",
                    "description": "Payment history months exceed months since account opening. Metro 2 compliance failure.",
                },
                ExplanationDialect.ATTORNEY: {
                    "headline": "Mathematical Impossibility — Payment History > Account Age",
                    "description": "Reported payment history duration exceeds account age. Data is facially inaccurate.",
                },
            },
            "M1": {
                ExplanationDialect.CONSUMER: {
                    "headline": "Balance Exceeds Legal Maximum",
                    "description": "The reported balance is higher than legally possible given interest rate limits.",
                },
                ExplanationDialect.EXAMINER: {
                    "headline": "Balance Exceeds Legal Accumulation Maximum",
                    "description": "Reported balance exceeds maximum possible with legal interest rates. Mathematical impossibility.",
                },
                ExplanationDialect.ATTORNEY: {
                    "headline": "Mathematical Impossibility — Balance Exceeds Legal Cap",
                    "description": "Balance exceeds maximum possible accumulation under applicable usury limits.",
                },
            },
            "PERFUNCTORY_INVESTIGATION": {
                ExplanationDialect.CONSUMER: {
                    "headline": "Rubber-Stamp Verification",
                    "description": "The bureau said they 'verified' the information but didn't actually investigate your evidence.",
                },
                ExplanationDialect.EXAMINER: {
                    "headline": "Perfunctory Investigation — § 1681i(a)(1)(A) Violation",
                    "description": "CRA verified without addressing specific consumer evidence. Investigation procedure inadequate.",
                },
                ExplanationDialect.ATTORNEY: {
                    "headline": "§ 1681i(a)(1)(A) — Failure to Reasonably Investigate",
                    "description": "Verification without investigation. See Cushman v. Trans Union Corp.",
                },
            },
        }

        if violation_type in violation_explanations:
            if dialect in violation_explanations[violation_type]:
                return violation_explanations[violation_type][dialect]

        # Default
        return {
            "headline": f"Violation: {violation_type}",
            "description": "A data accuracy violation was detected.",
        }
