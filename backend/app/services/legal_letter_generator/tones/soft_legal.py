"""
Legal Letter Generator - Soft Legal Tone
FCRA compliant but accessible and friendly.
"""
from typing import Dict, List, Any
from dataclasses import dataclass


@dataclass
class ToneConfig:
    """Configuration for the soft legal tone."""
    name: str = "soft_legal"
    description: str = "FCRA compliant but accessible and friendly"
    citation_density: str = "low"
    use_legal_terms: bool = True
    include_case_law: bool = False
    include_statutes: bool = True
    formality_level: int = 5  # 1-10 scale


class SoftLegalTone:
    """Soft legal tone engine with accessible language."""

    config = ToneConfig()

    # Friendly openings
    OPENINGS = [
        "RE: Request to Review and Correct My Credit Report",
        "RE: Credit Report Dispute Request",
        "RE: Please Investigate Errors on My Credit Report",
        "RE: Help Needed to Correct Credit Report Errors",
    ]

    # Accessible section headers - STRICT ORDER enforced
    # Order: Header → Intro → Disputed Items → Legal Basis → MOV → Case Law → Demands → Signature
    SECTION_HEADERS = {
        "introduction": "About This Dispute",
        "violations": "Items I'm Disputing",
        "legal_basis": "My Rights Under the Law",
        "mov": "What I Need to See",
        "case_law": "Legal Support",
        "demands": "What I'm Asking For",
    }

    # Accessible expressions
    EXPRESSIONS = {
        "dispute_intro": [
            "I'm writing to request your assistance reviewing some items on my credit file",
            "I'm writing because I found some errors on my credit report that need to be fixed",
            "I recently reviewed my credit report and found some information that isn't correct",
            "I need your help correcting some mistakes on my credit file",
        ],
        "demand_verification": [
            "I'd appreciate it if you could look into these items and make sure they're accurate",
            "Please check these items carefully and verify that the information is correct",
            "I'm asking that you investigate these entries and confirm their accuracy",
        ],
        "deletion_demand": [
            "If you can't verify this information, the law requires that it be removed",
            "Any information that can't be confirmed should be taken off my report",
            "Please remove any items that can't be properly verified",
        ],
        "furnisher_duty": [
            "The companies reporting this information are required to make sure it's accurate",
            "Credit reporting rules require that all information be verified and correct",
            "The creditor has a responsibility to report only accurate information",
        ],
        "reservation": [
            "I understand I have rights under the Fair Credit Reporting Act",
            "I know the law protects consumers like me in these situations",
            "I'm aware of my rights under consumer protection laws",
        ],
    }

    @classmethod
    def get_opening(cls, seed: int = 0) -> str:
        """Get a friendly opening."""
        return cls.OPENINGS[seed % len(cls.OPENINGS)]

    @classmethod
    def get_section_header(cls, section: str) -> str:
        """Get the accessible section header."""
        return cls.SECTION_HEADERS.get(section, section.replace("_", " ").title())

    @classmethod
    def get_expression(cls, category: str, seed: int = 0) -> str:
        """Get an accessible expression by category."""
        expressions = cls.EXPRESSIONS.get(category, [])
        if expressions:
            return expressions[seed % len(expressions)]
        return ""

    @classmethod
    def format_violation(cls, violation: Dict[str, Any], index: int) -> str:
        """Format a violation in accessible style."""
        v_type = violation.get("violation_type", "error")
        creditor = violation.get("creditor_name", "Unknown Creditor")
        account = violation.get("account_number_masked", "")
        evidence = violation.get("evidence", "")

        lines = [
            f"**{index}. {creditor}**",
        ]

        if account:
            lines.append(f"   Account ending in: {account}")

        lines.append(f"   Problem: {v_type.replace('_', ' ').title()}")

        if evidence:
            lines.append(f"   Details: {evidence}")

        lines.extend([
            "",
            "   This information doesn't look right to me. Could you please verify it",
            "   with the original documents?",
            ""
        ])

        return "\n".join(lines)

    @classmethod
    def format_legal_basis_section(cls, violations: List[Dict], fcra_sections: List[str]) -> str:
        """Format the legal basis section in accessible language."""
        return f"""
**{cls.get_section_header("legal_basis")}**

The Fair Credit Reporting Act (FCRA) is a federal law that protects consumers like me.
Under this law, I have the right to:

- Dispute information I believe is wrong
- Have my disputes investigated within 30 days
- Have unverified information removed from my report
- Receive written results of the investigation

I'm using these rights to ask you to look into the items below.
"""

    @classmethod
    def format_conclusion(cls, seed: int = 0) -> str:
        """Format the accessible conclusion."""
        return f"""
**{cls.get_section_header("conclusion")}**

Thank you for taking the time to review my dispute. I know you handle many requests,
and I appreciate your help in getting my credit report corrected.

Under the FCRA, you have 30 days to complete your investigation. Please let me know
the results in writing.

If you have any questions or need more information from me, please don't hesitate
to reach out. I want to work with you to get this resolved.

{cls.get_expression("reservation", seed)}
"""

    @classmethod
    def format_signature_block(cls, consumer_name: str) -> str:
        """Format the friendly signature block."""
        return f"""
Thank you again,

{consumer_name}

P.S. I've included copies of the relevant parts of my credit report with the
errors marked. Please let me know if you need anything else.
"""
