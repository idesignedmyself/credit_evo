"""
Civil Letter Generator - Assertive Tone
Direct and demanding, but without legal terminology.
NO legal citations, case law, or formal legal terminology.
"""
from typing import Dict, List, Any
from dataclasses import dataclass


@dataclass
class ToneConfig:
    """Configuration for the assertive civil tone."""
    name: str = "assertive"
    description: str = "Direct and demanding tone emphasizing compliance obligations"
    letter_type: str = "civil"
    citation_density: str = "none"
    use_legal_terms: bool = False
    include_case_law: bool = False
    include_statutes: bool = False
    formality_level: int = 6  # 1-10 scale


class CivilAssertiveTone:
    """Assertive civil tone engine with direct, demanding language."""

    config = ToneConfig()
    description = "Direct and demanding tone emphasizing compliance obligations."
    formality_level = 6

    # Assertive openings
    OPENINGS = [
        "RE: URGENT - Credit Report Errors Requiring Immediate Correction",
        "RE: Demand for Correction of Credit Report Inaccuracies",
        "RE: IMPORTANT - Errors Found on Credit Report",
        "RE: Credit Report Dispute - Action Required",
    ]

    # Assertive section headers
    SECTION_HEADERS = {
        "introduction": "Notice of Dispute",
        "legal_basis": "Your Obligations",
        "violations": "Errors Requiring Correction",
        "metro2": "Data Problems",
        "mov": "Required Documentation",
        "demands": "What Must Be Done",
        "conclusion": "Deadline and Expectations",
    }

    # Assertive expressions
    EXPRESSIONS = {
        "dispute_intro": [
            "I am demanding immediate correction of false information on my credit report",
            "This is a formal notice that you are reporting incorrect information about me",
            "I am disputing the following errors and expect prompt action",
            "Your records about me contain serious errors that must be fixed now",
        ],
        "demand_verification": [
            "You need to verify this information with actual proof, not just by asking the creditor",
            "I expect you to check this against real documentation, not just take someone's word for it",
            "This must be verified with original records - a simple phone call isn't enough",
            "Real proof is required - not just confirmation from whoever reported this",
        ],
        "deletion_demand": [
            "If you can't prove this is accurate, remove it immediately",
            "Delete anything that cannot be backed up with real documentation",
            "I expect unproven information to be taken off my report right away",
            "Remove items that fail verification - no exceptions",
        ],
        "closure": [
            "I expect a response within 30 days as required",
            "Handle this matter promptly",
            "Do not delay in addressing this dispute",
            "I am counting on your timely response",
        ],
    }

    @classmethod
    def get_opening(cls, seed: int = 0) -> str:
        """Get an assertive opening."""
        return cls.OPENINGS[seed % len(cls.OPENINGS)]

    @classmethod
    def get_section_header(cls, section: str) -> str:
        """Get an assertive section header."""
        return cls.SECTION_HEADERS.get(section, section.replace("_", " ").upper())

    @classmethod
    def get_expression(cls, category: str, seed: int = 0) -> str:
        """Get an assertive expression by category."""
        expressions = cls.EXPRESSIONS.get(category, [])
        if expressions:
            return expressions[seed % len(expressions)]
        return ""

    @classmethod
    def format_violation(cls, violation: Dict[str, Any], index: int) -> str:
        """Format a violation in assertive style."""
        creditor = violation.get("creditor_name", "UNKNOWN")
        account = violation.get("account_number_masked", "")
        evidence = violation.get("evidence", "")
        v_type = violation.get("violation_type", "error").replace("_", " ")

        lines = [
            f"**ERROR {index}: {creditor.upper()}**",
        ]

        if account:
            lines.append(f"Account: {account}")

        lines.extend([
            f"Problem: {v_type.upper()}",
        ])

        if evidence:
            lines.append(f"Details: {evidence}")

        lines.extend([
            "",
            "This information is WRONG. I am disputing it and expect you to",
            "verify it with actual proof - not just ask the creditor if it's right.",
            ""
        ])

        return "\n".join(lines)

    @classmethod
    def format_legal_basis_section(cls, violations: List[Dict], fcra_sections: List[str]) -> str:
        """Format obligations section in assertive but plain language."""
        return f"""
**{cls.get_section_header("legal_basis")}**

You have responsibilities when I dispute information:

- You MUST investigate my dispute within 30 days
- You MUST verify information with actual documentation
- You MUST remove anything that cannot be proven accurate
- You MUST send me written results of your investigation

These are not optional. I expect full compliance.
"""

    @classmethod
    def format_conclusion(cls, seed: int = 0) -> str:
        """Format an assertive conclusion."""
        return f"""
**{cls.get_section_header("conclusion")}**

You have 30 days to:

1. INVESTIGATE every item I've disputed
2. VERIFY the accuracy with real documentation
3. CORRECT or DELETE any unverified information
4. NOTIFY me in writing of your findings

{cls.get_expression("closure", seed)}

I am keeping records of this dispute and will follow up if these issues are not resolved.
"""

    @classmethod
    def format_signature_block(cls, consumer_name: str) -> str:
        """Format an assertive signature block."""
        return f"""
Expecting prompt action,

{consumer_name}

I am documenting this dispute and all responses.

Enclosures:
- Credit report with errors highlighted
- Any supporting documentation
"""
