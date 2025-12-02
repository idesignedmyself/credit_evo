"""
Legal Letter Generator - Professional Tone
Clear, businesslike, legally sound without being intimidating.
"""
from typing import Dict, List, Any
from dataclasses import dataclass


@dataclass
class ToneConfig:
    """Configuration for the professional tone."""
    name: str = "professional"
    description: str = "Clear, businesslike, legally sound without being intimidating"
    citation_density: str = "moderate"
    use_legal_terms: bool = True
    include_case_law: bool = True
    include_statutes: bool = True
    formality_level: int = 7  # 1-10 scale


class ProfessionalTone:
    """Professional tone engine with businesslike language."""

    config = ToneConfig()

    # Professional openings
    OPENINGS = [
        "RE: Credit Report Dispute - Request for Investigation",
        "RE: Formal Dispute of Inaccurate Credit Information",
        "RE: Request for Reinvestigation Under FCRA Section 611",
        "RE: Consumer Dispute and Verification Request",
    ]

    # Section headers - STRICT ORDER enforced
    # Order: Header → Intro → Disputed Items → Legal Basis → MOV → Case Law → Demands → Signature
    SECTION_HEADERS = {
        "introduction": "Introduction",
        "violations": "Disputed Items",
        "legal_basis": "Legal Framework",
        "mov": "Verification Requirements",
        "case_law": "Legal Standards",
        "demands": "Requested Actions",
    }

    # Professional expressions
    EXPRESSIONS = {
        "dispute_intro": [
            "This letter is a formal dispute submitted pursuant to FCRA § 611",
            "I am writing to formally dispute inaccurate information appearing on my credit report",
            "This letter serves as my formal dispute of the following credit reporting errors",
            "Please accept this letter as my dispute of certain information on my credit file",
        ],
        "demand_verification": [
            "I request that you conduct a thorough investigation as required by the FCRA",
            "Please verify this information through proper documentation, not merely furnisher confirmation",
            "I ask that you investigate this matter and correct any inaccuracies found",
        ],
        "deletion_demand": [
            "If the information cannot be properly verified, please delete it from my credit file",
            "Any unverifiable information should be removed pursuant to FCRA requirements",
            "Please delete any disputed items that cannot be verified through documentation",
        ],
        "furnisher_duty": [
            "The creditor is obligated under FCRA Section 623 to report only accurate information",
            "Data furnishers have a legal duty to ensure the accuracy of reported information",
            "The reporting entity must verify and correct any inaccurate data they have furnished",
        ],
        "reservation": [
            "I reserve my rights under the Fair Credit Reporting Act",
            "This dispute is submitted with full reservation of my legal rights and remedies",
            "I retain all rights available to me under applicable consumer protection laws",
        ],
    }

    @classmethod
    def get_opening(cls, seed: int = 0) -> str:
        """Get a professional opening."""
        return cls.OPENINGS[seed % len(cls.OPENINGS)]

    @classmethod
    def get_section_header(cls, section: str) -> str:
        """Get the section header."""
        return cls.SECTION_HEADERS.get(section, section.replace("_", " ").title())

    @classmethod
    def get_expression(cls, category: str, seed: int = 0) -> str:
        """Get a professional expression by category."""
        expressions = cls.EXPRESSIONS.get(category, [])
        if expressions:
            return expressions[seed % len(expressions)]
        return ""

    @classmethod
    def format_violation(cls, violation: Dict[str, Any], index: int) -> str:
        """Format a violation in professional style."""
        v_type = violation.get("violation_type", "inaccuracy")
        creditor = violation.get("creditor_name", "Unknown Creditor")
        account = violation.get("account_number_masked", "")
        fcra_section = violation.get("fcra_section", "611")
        metro2_field = violation.get("metro2_field", "")
        evidence = violation.get("evidence", "")

        lines = [
            f"**Item {index}: {creditor}**",
        ]

        if account:
            lines.append(f"Account Number: {account}")

        lines.extend([
            f"Issue: {v_type.replace('_', ' ').title()}",
            f"Applicable FCRA Section: {fcra_section}",
        ])

        if metro2_field:
            lines.append(f"Data Field Affected: {metro2_field}")

        if evidence:
            lines.append(f"Details: {evidence}")

        lines.extend([
            "",
            "I dispute this information as inaccurate and request verification through",
            "original source documentation.",
            ""
        ])

        return "\n".join(lines)

    @classmethod
    def format_legal_basis_section(cls, violations: List[Dict], fcra_sections: List[str]) -> str:
        """Format the legal basis section."""
        lines = [
            f"**{cls.get_section_header('legal_basis')}**",
            "",
            "This dispute is submitted under the Fair Credit Reporting Act, which provides:",
            "",
        ]

        section_summaries = {
            "611": "The right to dispute inaccurate information and receive a reinvestigation",
            "611(a)(1)": "The requirement for a reasonable reinvestigation within 30 days",
            "611(a)(5)": "The obligation to delete information that cannot be verified",
            "623": "Furnisher duties to report accurate information",
            "623(a)(1)": "The prohibition against reporting known inaccurate data",
            "623(b)": "Furnisher investigation duties upon notice of dispute",
            "607(b)": "The requirement for maximum possible accuracy",
            "605(a)": "Time limits on reporting adverse information",
        }

        for section in sorted(set(fcra_sections)):
            summary = section_summaries.get(section, f"Requirements under Section {section}")
            lines.append(f"- Section {section}: {summary}")

        lines.append("")
        return "\n".join(lines)

    @classmethod
    def format_conclusion(cls, seed: int = 0) -> str:
        """Format the professional conclusion."""
        return f"""
**{cls.get_section_header("conclusion")}**

Please complete your investigation within 30 days as required by the FCRA. I request that you:

1. Conduct a thorough reinvestigation of the disputed items
2. Contact the data furnishers to verify the accuracy of the information
3. Review any documentation I have provided with this dispute
4. Delete or correct any information that cannot be properly verified
5. Provide me with written notice of the results

{cls.get_expression("reservation", seed)}

Thank you for your prompt attention to this matter.
"""

    @classmethod
    def format_signature_block(cls, consumer_name: str) -> str:
        """Format the professional signature block."""
        return f"""
Sincerely,

{consumer_name}

Enclosures (if applicable):
- Copy of credit report with disputed items marked
- Supporting documentation
"""
