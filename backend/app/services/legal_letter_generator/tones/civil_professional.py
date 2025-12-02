"""
Civil Letter Generator - Professional Tone
Businesslike and clear, without legal jargon.
NO legal citations, case law, or formal legal terminology.
"""
from typing import Dict, List, Any
from dataclasses import dataclass


@dataclass
class ToneConfig:
    """Configuration for the professional civil tone."""
    name: str = "civil_professional"
    description: str = "Businesslike and clear, without legal jargon"
    letter_type: str = "civil"
    citation_density: str = "none"
    use_legal_terms: bool = False
    include_case_law: bool = False
    include_statutes: bool = False
    formality_level: int = 5  # 1-10 scale


class CivilProfessionalTone:
    """Professional civil tone engine with businesslike, clear language."""

    config = ToneConfig()
    description = "Professional language citing specific FCRA sections and legal requirements."
    formality_level = 5

    # Professional openings
    OPENINGS = [
        "RE: Credit Report Dispute - Formal Request for Correction",
        "RE: Request for Investigation of Credit Report Errors",
        "RE: Credit File Review and Correction Request",
        "RE: Dispute of Inaccurate Credit Information",
    ]

    # Professional section headers
    SECTION_HEADERS = {
        "introduction": "Purpose of This Letter",
        "legal_basis": "Consumer Rights",
        "violations": "Items Requiring Correction",
        "metro2": "Reporting Discrepancies",
        "mov": "Documentation Request",
        "demands": "Requested Actions",
        "conclusion": "Next Steps",
    }

    # Professional expressions
    EXPRESSIONS = {
        "dispute_intro": [
            "I am writing to formally dispute inaccurate information on my credit report",
            "This letter serves as my formal request to investigate and correct errors in my credit file",
            "I have identified several discrepancies on my credit report that require your attention",
            "Please accept this letter as my formal dispute of the items detailed below",
        ],
        "demand_verification": [
            "I request that you investigate these items and verify their accuracy",
            "Please review the disputed information and confirm it with original records",
            "I ask that you thoroughly examine these entries for accuracy",
            "These items should be verified against original documentation",
        ],
        "deletion_demand": [
            "Any information that cannot be verified should be removed from my credit file",
            "Please delete items that cannot be confirmed through proper documentation",
            "Unverifiable information should be promptly removed",
            "I request deletion of any items that fail verification",
        ],
        "closure": [
            "Thank you for your prompt attention to this matter",
            "I appreciate your cooperation in resolving these issues",
            "Your timely response to this request is appreciated",
            "Thank you for addressing these concerns",
        ],
    }

    @classmethod
    def get_opening(cls, seed: int = 0) -> str:
        """Get a professional opening."""
        return cls.OPENINGS[seed % len(cls.OPENINGS)]

    @classmethod
    def get_section_header(cls, section: str) -> str:
        """Get a professional section header."""
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
        """Format a violation in professional style with factual evidence."""
        creditor = violation.get("creditor_name", "Unknown Creditor")
        account = violation.get("account_number_masked", "")
        evidence = violation.get("evidence", "")
        v_type = violation.get("violation_type", "error").replace("_", " ")

        # Factual evidence fields
        date_reported = violation.get("date_reported", "")
        last_reported = violation.get("last_reported", "")
        date_of_status = violation.get("date_of_status", "")
        days_since_update = violation.get("days_since_update")
        missing_fields = violation.get("missing_fields", [])
        balance_reported = violation.get("balance", "")
        high_credit = violation.get("high_credit", "")

        lines = [
            f"**Item {index}: {creditor}**",
            "",
        ]

        if account:
            lines.append(f"Account Number: {account}")

        lines.append(f"Issue Type: {v_type.title()}")

        # Add factual evidence section
        lines.append("")
        lines.append("**Factual Details:**")

        if date_reported:
            lines.append(f"- Date Reported: {date_reported}")
        if last_reported:
            lines.append(f"- Last Activity: {last_reported}")
        if date_of_status:
            lines.append(f"- Status Date: {date_of_status}")
        if days_since_update is not None:
            lines.append(f"- Days Since Last Update: {days_since_update} days")
        if balance_reported:
            lines.append(f"- Balance Reported: ${balance_reported}")
        if high_credit:
            lines.append(f"- High Credit/Original Amount: ${high_credit}")

        # Missing fields
        if missing_fields:
            lines.append("")
            lines.append("**Missing Information:**")
            for field in missing_fields:
                lines.append(f"- {field}")

        if evidence:
            lines.append("")
            lines.append(f"**Specific Issue:** {evidence}")

        lines.extend([
            "",
            "This information is disputed and requires verification. Please confirm",
            "its accuracy using original records and documentation.",
            ""
        ])

        return "\n".join(lines)

    @classmethod
    def format_legal_basis_section(cls, violations: List[Dict], fcra_sections: List[str]) -> str:
        """Format consumer rights section in professional but plain language."""
        return f"""
**{cls.get_section_header("legal_basis")}**

As a consumer, I have certain rights regarding my credit information:

- The right to dispute information I believe to be inaccurate
- The right to have disputes investigated within 30 days
- The right to have unverifiable information removed
- The right to receive written notification of investigation results

This dispute is submitted in exercise of these consumer rights.
"""

    @classmethod
    def format_conclusion(cls, seed: int = 0) -> str:
        """Format a professional conclusion."""
        return f"""
**{cls.get_section_header("conclusion")}**

Please complete your investigation within 30 days and provide written notification
of the results. I expect the following:

1. A thorough review of each disputed item
2. Verification of information with original records
3. Correction or deletion of inaccurate entries
4. Written notification of the investigation outcome

{cls.get_expression("closure", seed)}
"""

    @classmethod
    def format_signature_block(cls, consumer_name: str) -> str:
        """Format a professional signature block."""
        return f"""
Sincerely,

{consumer_name}

Enclosures:
- Copy of credit report with disputed items marked
- Supporting documentation (if applicable)
"""
