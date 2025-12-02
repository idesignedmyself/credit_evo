"""
Civil Letter Generator - Narrative Tone
Storytelling approach that explains the situation in detail.
NO legal citations, case law, or formal legal terminology.
"""
from typing import Dict, List, Any
from dataclasses import dataclass


@dataclass
class ToneConfig:
    """Configuration for the narrative civil tone."""
    name: str = "narrative"
    description: str = "Storytelling approach that explains the situation in detail"
    letter_type: str = "civil"
    citation_density: str = "none"
    use_legal_terms: bool = False
    include_case_law: bool = False
    include_statutes: bool = False
    formality_level: int = 4  # 1-10 scale


class CivilNarrativeTone:
    """Narrative civil tone engine with storytelling, detailed explanations."""

    config = ToneConfig()
    description = "Storytelling approach that explains the situation in detail."
    formality_level = 4

    # Narrative openings
    OPENINGS = [
        "RE: My Story - Credit Report Errors That Need Your Attention",
        "RE: Let Me Explain - Problems Found on My Credit Report",
        "RE: Credit Report Issues - Here's What Happened",
        "RE: Something's Not Right - My Credit Report Concerns",
    ]

    # Narrative section headers
    SECTION_HEADERS = {
        "introduction": "Here's What's Going On",
        "legal_basis": "What I Know About My Rights",
        "violations": "The Problems I've Found",
        "metro2": "Technical Details",
        "mov": "What I Need From You",
        "demands": "How We Can Fix This",
        "conclusion": "Looking Forward",
    }

    # Narrative expressions
    EXPRESSIONS = {
        "dispute_intro": [
            "Let me tell you what's been happening with my credit report",
            "I want to share with you some problems I've discovered on my credit file",
            "Here's the situation - I've been reviewing my credit report and found some concerning issues",
            "I need to walk you through what I've found on my credit report",
        ],
        "demand_verification": [
            "What I really need is for someone to actually look into this and confirm what's true",
            "I'm hoping you can dig into this and find out what really happened",
            "It would mean a lot if you could verify this with the actual records",
            "I need someone to check the real paperwork on this, not just take someone's word for it",
        ],
        "deletion_demand": [
            "If this turns out to be incorrect, I'd like it removed so my credit can be accurate",
            "Anything that's not actually true should come off my report",
            "I'm asking that false information be taken out of my credit file",
            "Please remove whatever can't be proven - my credit score depends on accuracy",
        ],
        "closure": [
            "I really appreciate you taking the time to read my story and help me out",
            "Thank you for listening and for whatever help you can provide",
            "I'm grateful for your attention to my situation",
            "Thanks for being willing to look into this for me",
        ],
    }

    @classmethod
    def get_opening(cls, seed: int = 0) -> str:
        """Get a narrative opening."""
        return cls.OPENINGS[seed % len(cls.OPENINGS)]

    @classmethod
    def get_section_header(cls, section: str) -> str:
        """Get a narrative section header."""
        return cls.SECTION_HEADERS.get(section, section.replace("_", " ").title())

    @classmethod
    def get_expression(cls, category: str, seed: int = 0) -> str:
        """Get a narrative expression by category."""
        expressions = cls.EXPRESSIONS.get(category, [])
        if expressions:
            return expressions[seed % len(expressions)]
        return ""

    @classmethod
    def format_violation(cls, violation: Dict[str, Any], index: int) -> str:
        """Format a violation in narrative style, telling the story with factual evidence."""
        creditor = violation.get("creditor_name", "a creditor")
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
            f"**Problem {index}: About {creditor}**",
            "",
        ]

        # Tell the story of this issue
        story = f"When I looked at my report, I noticed something wrong with {creditor}"
        if account:
            story += f" (account ending in {account})"
        story += "."

        lines.append(story)
        lines.append("")

        lines.append(f"The issue is: {v_type.title()}")
        lines.append("")

        # Add the factual evidence as part of the narrative
        lines.append("Let me give you some specifics about what I'm seeing:")
        lines.append("")

        if date_reported:
            lines.append(f"- The report shows this was reported on {date_reported}")
        if last_reported:
            lines.append(f"- The last activity date shows as {last_reported}")
        if date_of_status:
            lines.append(f"- The current status is dated {date_of_status}")
        if days_since_update is not None:
            if days_since_update > 60:
                lines.append(f"- This hasn't been updated in {days_since_update} days - that seems like a long time")
            else:
                lines.append(f"- The last update was {days_since_update} days ago")
        if balance_reported:
            lines.append(f"- The balance is showing as ${balance_reported}")

        # Missing fields as part of the story
        if missing_fields:
            lines.append("")
            lines.append("I also noticed some information is missing:")
            for field in missing_fields:
                lines.append(f"- {field}")

        if evidence:
            lines.append("")
            lines.append(f"The main problem I see: {evidence}")

        lines.extend([
            "",
            "This doesn't match what I know to be true, and I'm worried it's affecting",
            "my credit score. I'd really like someone to look into this and see what's",
            "actually accurate.",
            ""
        ])

        return "\n".join(lines)

    @classmethod
    def format_legal_basis_section(cls, violations: List[Dict], fcra_sections: List[str]) -> str:
        """Format rights section as a narrative explanation."""
        return f"""
**{cls.get_section_header("legal_basis")}**

From what I understand, when I find something wrong on my credit report, I have
certain rights as a consumer:

- I can point out things I believe are incorrect
- The credit bureau has to look into what I've reported within 30 days
- If they can't prove something is true, they have to remove it
- They have to tell me what they found out

That's why I'm writing to you today - to exercise these rights and hopefully
get my credit report corrected.
"""

    @classmethod
    def format_conclusion(cls, seed: int = 0) -> str:
        """Format a narrative conclusion."""
        return f"""
**{cls.get_section_header("conclusion")}**

So here's where we are: I've found these problems on my credit report, and I'm
asking for your help to get them fixed. I know you probably deal with thousands
of these requests, but each one represents someone like me who's trying to make
sure their financial record is accurate.

Over the next 30 days, I'm hoping you'll:

1. Take a close look at each item I've mentioned
2. Check with the actual records to see what's true
3. Fix anything that turns out to be wrong
4. Let me know what you discovered

{cls.get_expression("closure", seed)}

I'm looking forward to getting this resolved and moving on with an accurate
credit report.
"""

    @classmethod
    def format_signature_block(cls, consumer_name: str) -> str:
        """Format a warm, narrative signature block."""
        return f"""
With hope for a good resolution,

{consumer_name}

P.S. I've included a copy of my credit report with the problem areas marked so
you can see exactly what I'm talking about. If there's anything else you need
from me, just let me know - I want to make this as easy as possible to resolve.
"""
