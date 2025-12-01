"""
Legal Letter Generator - Strict Legal Tone
Maximum legal citations, formal structure, attorney-style language.
"""
from typing import Dict, List, Any
from dataclasses import dataclass


@dataclass
class ToneConfig:
    """Configuration for the strict legal tone."""
    name: str = "strict_legal"
    description: str = "Maximum legal citations, formal structure, attorney-style language"
    citation_density: str = "high"
    use_legal_terms: bool = True
    include_case_law: bool = True
    include_statutes: bool = True
    formality_level: int = 10  # 1-10 scale


class StrictLegalTone:
    """Strict legal tone engine with attorney-style language."""

    config = ToneConfig()

    # Formal legal openings
    OPENINGS = [
        "RE: Formal Dispute and Demand for Reinvestigation Pursuant to 15 U.S.C. § 1681i",
        "RE: Notice of Dispute and Demand for Verification Under the Fair Credit Reporting Act",
        "RE: Formal Consumer Dispute Pursuant to FCRA Sections 611 and 623",
        "RE: Demand for Reinvestigation and Correction of Inaccurate Credit Information",
    ]

    # Legal section headers
    SECTION_HEADERS = {
        "introduction": "I. PRELIMINARY STATEMENT",
        "legal_basis": "II. LEGAL BASIS FOR DISPUTE",
        "violations": "III. SPECIFIC VIOLATIONS AND INACCURACIES",
        "metro2": "IV. METRO-2 COMPLIANCE DEFICIENCIES",
        "mov": "V. METHOD OF VERIFICATION REQUIREMENTS",
        "case_law": "VI. APPLICABLE CASE LAW",
        "demands": "VII. FORMAL DEMANDS",
        "conclusion": "VIII. RESERVATION OF RIGHTS",
    }

    # Legal phrases and expressions
    EXPRESSIONS = {
        "dispute_intro": [
            "Pursuant to the Fair Credit Reporting Act, 15 U.S.C. § 1681 et seq., I hereby formally dispute",
            "Under the provisions of FCRA Section 611, I am exercising my statutory right to dispute",
            "This letter constitutes formal notice of dispute as provided under 15 U.S.C. § 1681i",
        ],
        "demand_verification": [
            "I demand that you conduct a reasonable reinvestigation as required by FCRA Section 611(a)(1)",
            "You are legally obligated to verify this information pursuant to 15 U.S.C. § 1681i(a)(1)(A)",
            "Under the FCRA, you must reinvestigate and record the current status of this disputed information",
        ],
        "deletion_demand": [
            "If the disputed information cannot be verified within 30 days, you must delete it pursuant to FCRA Section 611(a)(5)(A)",
            "Failure to verify must result in prompt deletion as mandated by 15 U.S.C. § 1681i(a)(5)(A)",
            "Unverifiable information must be promptly deleted in accordance with FCRA requirements",
        ],
        "furnisher_duty": [
            "The furnisher has a duty under FCRA Section 623(a)(1) to report only accurate information",
            "Pursuant to 15 U.S.C. § 1681s-2(a)(1), furnishers may not report information known to be inaccurate",
            "The furnisher's obligation under Section 623 includes the duty to correct inaccurate information",
        ],
        "reservation": [
            "I reserve all rights and remedies available under the FCRA, including but not limited to statutory damages under 15 U.S.C. § 1681n for willful violations",
            "This dispute is made without prejudice to any other rights or remedies available at law or equity",
            "I expressly reserve the right to pursue all available legal remedies should this dispute not be properly resolved",
        ],
    }

    @classmethod
    def get_opening(cls, seed: int = 0) -> str:
        """Get a formal legal opening."""
        return cls.OPENINGS[seed % len(cls.OPENINGS)]

    @classmethod
    def get_section_header(cls, section: str) -> str:
        """Get the formal section header."""
        return cls.SECTION_HEADERS.get(section, section.upper())

    @classmethod
    def get_expression(cls, category: str, seed: int = 0) -> str:
        """Get a legal expression by category."""
        expressions = cls.EXPRESSIONS.get(category, [])
        if expressions:
            return expressions[seed % len(expressions)]
        return ""

    @classmethod
    def format_violation(cls, violation: Dict[str, Any], index: int) -> str:
        """Format a violation in strict legal style."""
        v_type = violation.get("violation_type", "inaccuracy")
        creditor = violation.get("creditor_name", "Unknown Creditor")
        account = violation.get("account_number_masked", "")
        fcra_section = violation.get("fcra_section", "611")
        metro2_field = violation.get("metro2_field", "")
        evidence = violation.get("evidence", "")

        lines = [
            f"    {index}. **{creditor}**{f' (Account: {account})' if account else ''}",
            "",
            f"       Violation Type: {v_type.replace('_', ' ').title()}",
            f"       FCRA Section Violated: Section {fcra_section}",
        ]

        if metro2_field:
            lines.append(f"       Metro-2 Field: {metro2_field}")

        if evidence:
            lines.append(f"       Specific Issue: {evidence}")

        lines.extend([
            "",
            f"       This information is disputed as inaccurate, incomplete, or unverifiable",
            f"       pursuant to 15 U.S.C. § 1681i. I demand verification of this data through",
            f"       production of original source documentation, not merely furnisher confirmation.",
            ""
        ])

        return "\n".join(lines)

    @classmethod
    def format_legal_basis_section(cls, violations: List[Dict], fcra_sections: List[str]) -> str:
        """Format the legal basis section."""
        lines = [
            cls.get_section_header("legal_basis"),
            "",
            "This dispute is brought pursuant to the following provisions of the Fair Credit Reporting Act:",
            "",
        ]

        section_descriptions = {
            "611": "Section 611 (15 U.S.C. § 1681i) - Procedure in Case of Disputed Accuracy",
            "611(a)(1)": "Section 611(a)(1) - Reinvestigation Required Within 30 Days",
            "611(a)(5)": "Section 611(a)(5) - Deletion of Unverifiable Information",
            "623": "Section 623 (15 U.S.C. § 1681s-2) - Responsibilities of Furnishers",
            "623(a)(1)": "Section 623(a)(1) - Duty to Provide Accurate Information",
            "623(b)": "Section 623(b) - Duties Upon Notice of Dispute",
            "607(b)": "Section 607(b) (15 U.S.C. § 1681e(b)) - Maximum Possible Accuracy",
            "605(a)": "Section 605(a) (15 U.S.C. § 1681c(a)) - Obsolete Information",
        }

        for section in sorted(set(fcra_sections)):
            desc = section_descriptions.get(section, f"Section {section}")
            lines.append(f"    - {desc}")

        lines.append("")
        return "\n".join(lines)

    @classmethod
    def format_conclusion(cls, seed: int = 0) -> str:
        """Format the formal conclusion."""
        return f"""
{cls.get_section_header("conclusion")}

{cls.get_expression("reservation", seed)}

You have thirty (30) days from receipt of this dispute to complete your reinvestigation
and provide me with written notice of the results, as required by FCRA Section 611(a)(6)(A).

Failure to comply with FCRA requirements may result in civil liability under 15 U.S.C. § 1681n
(willful noncompliance) or 15 U.S.C. § 1681o (negligent noncompliance), including actual damages,
statutory damages of $100 to $1,000 per violation, punitive damages, and attorney's fees.

This communication shall serve as formal notice of dispute for purposes of triggering your
obligations under the Fair Credit Reporting Act.
"""

    @classmethod
    def format_signature_block(cls, consumer_name: str) -> str:
        """Format the formal signature block."""
        return f"""
Respectfully submitted,



_________________________________
{consumer_name}
Consumer/Disputant

Date: _____________________

Sent via Certified Mail, Return Receipt Requested
"""
