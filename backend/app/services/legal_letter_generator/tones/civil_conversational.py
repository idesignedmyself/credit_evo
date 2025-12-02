"""
Civil Letter Generator - Conversational Tone
Friendly, approachable language for first-time disputes.
NO legal citations, case law, or formal legal terminology.
"""
from typing import Dict, List, Any
from dataclasses import dataclass


@dataclass
class ToneConfig:
    """Configuration for the conversational civil tone."""
    name: str = "conversational"
    description: str = "Friendly, approachable language for first-time disputes"
    letter_type: str = "civil"
    citation_density: str = "none"
    use_legal_terms: bool = False
    include_case_law: bool = False
    include_statutes: bool = False
    formality_level: int = 3  # 1-10 scale


class CivilConversationalTone:
    """Conversational civil tone engine with friendly, accessible language."""

    config = ToneConfig()
    description = "Friendly and approachable language that clearly explains the issues."
    formality_level = 3

    # Friendly openings
    OPENINGS = [
        "RE: Help Needed - Errors on My Credit Report",
        "RE: Requesting Your Help with Credit Report Corrections",
        "RE: Found Some Mistakes on My Credit Report",
        "RE: Credit Report Review Request",
    ]

    # Simple section headers
    SECTION_HEADERS = {
        "introduction": "Why I'm Writing",
        "legal_basis": "My Rights",
        "violations": "Problems I Found",
        "metro2": "Data Issues",
        "mov": "What I Need",
        "demands": "My Request",
        "conclusion": "Thank You",
    }

    # Friendly expressions
    EXPRESSIONS = {
        "dispute_intro": [
            "Hi there! I recently checked my credit report and found some information that doesn't look right",
            "I'm reaching out because I noticed some errors on my credit report that I'd like fixed",
            "I was going through my credit report and spotted a few things that seem wrong",
            "I'm hoping you can help me with some mistakes I found on my credit file",
        ],
        "demand_verification": [
            "Could you please take a look at these items and make sure they're correct?",
            "I'd really appreciate it if you could verify this information",
            "Would you mind checking on these entries to confirm they're accurate?",
            "I'm hoping you can look into these and let me know what you find",
        ],
        "deletion_demand": [
            "If this turns out to be wrong, I'd like it removed from my report",
            "Please take off anything that can't be confirmed",
            "It would be great if you could remove any information that's not accurate",
            "I'm asking that incorrect items be deleted from my file",
        ],
        "closure": [
            "Thanks so much for your help with this!",
            "I really appreciate you taking the time to look into this",
            "Thank you for helping me sort this out",
            "I'm grateful for your assistance",
        ],
    }

    @classmethod
    def get_opening(cls, seed: int = 0) -> str:
        """Get a friendly opening."""
        return cls.OPENINGS[seed % len(cls.OPENINGS)]

    @classmethod
    def get_section_header(cls, section: str) -> str:
        """Get a simple section header."""
        return cls.SECTION_HEADERS.get(section, section.replace("_", " ").title())

    @classmethod
    def get_expression(cls, category: str, seed: int = 0) -> str:
        """Get a friendly expression by category."""
        expressions = cls.EXPRESSIONS.get(category, [])
        if expressions:
            return expressions[seed % len(expressions)]
        return ""

    @classmethod
    def format_violation(cls, violation: Dict[str, Any], index: int) -> str:
        """Format a violation in friendly, conversational style with factual evidence."""
        creditor = violation.get("creditor_name", "A creditor")
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

        lines = [
            f"**{index}. {creditor}**",
            "",
        ]

        if account:
            lines.append(f"Account ending in: {account}")

        lines.append(f"What's wrong: {v_type.title()}")

        # Add factual details in a friendly way
        lines.append("")
        lines.append("Here's what I found:")

        if date_reported:
            lines.append(f"- This was reported on: {date_reported}")
        if last_reported:
            lines.append(f"- Last activity shown: {last_reported}")
        if date_of_status:
            lines.append(f"- The status is dated: {date_of_status}")
        if days_since_update is not None:
            lines.append(f"- It hasn't been updated in {days_since_update} days")
        if balance_reported:
            lines.append(f"- Balance showing: ${balance_reported}")

        # Missing fields in friendly language
        if missing_fields:
            lines.append("")
            lines.append("Some things seem to be missing from this record:")
            for field in missing_fields:
                lines.append(f"- {field}")

        if evidence:
            lines.append("")
            lines.append(f"The main problem: {evidence}")

        lines.extend([
            "",
            "This doesn't match what I know to be true. Could you please check on",
            "this and let me know what you find?",
            ""
        ])

        return "\n".join(lines)

    @classmethod
    def format_legal_basis_section(cls, violations: List[Dict], fcra_sections: List[str]) -> str:
        """Format rights section in plain language (NO legal citations)."""
        return f"""
**{cls.get_section_header("legal_basis")}**

I know that as a consumer, I have the right to:

- Question information on my credit report that I think is wrong
- Have my questions looked into within 30 days
- Get information removed if it can't be proven accurate
- Receive a written response about what was found

I'm using these rights to ask for your help with the items below.
"""

    @classmethod
    def format_conclusion(cls, seed: int = 0) -> str:
        """Format a friendly conclusion."""
        return f"""
**{cls.get_section_header("conclusion")}**

{cls.get_expression("closure", seed)}

I know you probably get a lot of these requests, so I really do appreciate you
taking the time to look into my concerns. If you need any more information from
me or have any questions, please don't hesitate to reach out.

I'm looking forward to hearing back from you within the next 30 days.
"""

    @classmethod
    def format_signature_block(cls, consumer_name: str) -> str:
        """Format a warm signature block."""
        return f"""
Best regards,

{consumer_name}

P.S. I've attached copies of my credit report with the problems highlighted.
Please let me know if you need anything else from me!
"""
