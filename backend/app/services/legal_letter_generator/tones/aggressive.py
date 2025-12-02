"""
Legal Letter Generator - Aggressive Tone
Heavy case law, explicit damage warnings, demands for documentation.
"""
from typing import Dict, List, Any
from dataclasses import dataclass


@dataclass
class ToneConfig:
    """Configuration for the aggressive tone."""
    name: str = "aggressive"
    description: str = "Heavy case law, explicit damage warnings, demands for documentation"
    citation_density: str = "maximum"
    use_legal_terms: bool = True
    include_case_law: bool = True
    include_statutes: bool = True
    formality_level: int = 9  # 1-10 scale


class AggressiveTone:
    """Aggressive tone engine with strong legal language and warnings."""

    config = ToneConfig()

    # Assertive openings
    OPENINGS = [
        "RE: FORMAL DEMAND FOR CORRECTION AND NOTICE OF POTENTIAL FCRA VIOLATIONS",
        "RE: DEMAND FOR IMMEDIATE REINVESTIGATION - NOTICE OF WILLFUL NONCOMPLIANCE",
        "RE: FINAL NOTICE: FCRA VIOLATION AND DEMAND FOR CORRECTION",
        "RE: NOTICE OF DISPUTE AND DEMAND FOR COMPLIANCE UNDER 15 U.S.C. § 1681",
    ]

    # Assertive section headers - STRICT ORDER enforced
    # Order: Header → Intro → Disputed Items → Legal Basis → MOV → Case Law → Demands → Signature
    SECTION_HEADERS = {
        "introduction": "I. NOTICE AND DEMAND",
        "violations": "II. SPECIFIC DEFICIENCIES REQUIRING IMMEDIATE CORRECTION",
        "legal_basis": "III. FCRA VIOLATIONS IDENTIFIED",
        "mov": "IV. MANDATORY VERIFICATION DOCUMENTATION",
        "case_law": "V. APPLICABLE CASE LAW AND PRECEDENT",
        "demands": "VI. NON-NEGOTIABLE DEMANDS",
    }

    # Strong expressions
    EXPRESSIONS = {
        "dispute_intro": [
            "Your records require immediate attention due to multiple FCRA violations",
            "I DEMAND immediate correction of the following FCRA violations appearing on my credit report",
            "This constitutes FORMAL NOTICE that you are reporting information in violation of federal law",
            "You are hereby put on NOTICE that the following items violate the Fair Credit Reporting Act",
        ],
        "demand_verification": [
            "I DEMAND production of original source documentation - NOT mere electronic verification from the furnisher",
            "You MUST provide verifiable proof, not simply parrot back the furnisher's data",
            "Your obligation to conduct a REASONABLE reinvestigation cannot be satisfied by rubber-stamping furnisher responses",
        ],
        "deletion_demand": [
            "If you FAIL to produce the required documentation within 30 days, you MUST DELETE this information",
            "Your failure to verify REQUIRES deletion under FCRA Section 611(a)(5)(A) - no exceptions",
            "Any item not verified through ORIGINAL DOCUMENTATION must be IMMEDIATELY DELETED",
        ],
        "furnisher_duty": [
            "The furnisher has VIOLATED Section 623(a)(1) by reporting information it knew or should have known was inaccurate",
            "The furnisher's failure to conduct a reasonable investigation constitutes a WILLFUL VIOLATION under the FCRA",
            "The reporting entity is LIABLE for furnishing inaccurate information in violation of 15 U.S.C. § 1681s-2",
        ],
        "reservation": [
            "I FULLY RESERVE my right to pursue statutory and punitive damages under 15 U.S.C. § 1681n for your WILLFUL VIOLATIONS",
            "This notice preserves ALL remedies available to me including statutory damages of $100-$1,000 PER VIOLATION, actual damages, and attorney's fees",
            "Failure to comply will result in litigation seeking MAXIMUM DAMAGES permitted under federal law",
        ],
    }

    # Damage warnings
    DAMAGE_WARNINGS = [
        "WILLFUL noncompliance exposes you to statutory damages of $100-$1,000 per violation, actual damages, punitive damages, and attorney's fees under 15 U.S.C. § 1681n.",
        "Courts have awarded substantial damages in FCRA cases, including six-figure verdicts for willful FCRA violations.",
        "Each day these violations continue constitutes a SEPARATE and CONTINUING violation subject to independent damages.",
    ]

    @classmethod
    def get_opening(cls, seed: int = 0) -> str:
        """Get an assertive opening."""
        return cls.OPENINGS[seed % len(cls.OPENINGS)]

    @classmethod
    def get_section_header(cls, section: str) -> str:
        """Get the assertive section header."""
        return cls.SECTION_HEADERS.get(section, section.upper())

    @classmethod
    def get_expression(cls, category: str, seed: int = 0) -> str:
        """Get an assertive expression by category."""
        expressions = cls.EXPRESSIONS.get(category, [])
        if expressions:
            return expressions[seed % len(expressions)]
        return ""

    @classmethod
    def get_damage_warning(cls, seed: int = 0) -> str:
        """Get a damage warning."""
        return cls.DAMAGE_WARNINGS[seed % len(cls.DAMAGE_WARNINGS)]

    @classmethod
    def format_violation(cls, violation: Dict[str, Any], index: int) -> str:
        """Format a violation in aggressive style."""
        v_type = violation.get("violation_type", "violation")
        creditor = violation.get("creditor_name", "UNKNOWN CREDITOR")
        account = violation.get("account_number_masked", "")
        fcra_section = violation.get("fcra_section", "611")
        metro2_field = violation.get("metro2_field", "")
        evidence = violation.get("evidence", "")

        lines = [
            f"    **VIOLATION {index}: {creditor.upper()}**",
            "",
        ]

        if account:
            lines.append(f"    Account: {account}")

        lines.extend([
            f"    VIOLATION TYPE: {v_type.replace('_', ' ').upper()}",
            f"    FCRA SECTION VIOLATED: 15 U.S.C. § 1681 (Section {fcra_section})",
        ])

        if metro2_field:
            lines.append(f"    METRO-2 FIELD AFFECTED: {metro2_field}")

        if evidence:
            lines.append(f"    SPECIFIC DEFICIENCY: {evidence}")

        lines.extend([
            "",
            "    This information is DISPUTED as FALSE, INACCURATE, and UNVERIFIABLE.",
            "    You are REQUIRED to verify this through original source documentation -",
            "    NOT through the same furnisher that provided the erroneous data.",
            "",
            "    LEGAL BASIS: Your reinvestigation procedures are UNREASONABLE if you merely",
            "    parrot back furnisher confirmations without independent verification.",
            ""
        ])

        return "\n".join(lines)

    @classmethod
    def format_legal_basis_section(cls, violations: List[Dict], fcra_sections: List[str]) -> str:
        """Format the legal basis section with strong language."""
        lines = [
            cls.get_section_header("legal_basis"),
            "",
            "Your reporting of the disputed information VIOLATES the following provisions of federal law:",
            "",
        ]

        section_violations = {
            "611": "SECTION 611 VIOLATION - Failure to maintain reasonable procedures for reinvestigation",
            "611(a)(1)": "SECTION 611(a)(1) VIOLATION - Unreasonable reinvestigation procedures",
            "611(a)(5)": "SECTION 611(a)(5) VIOLATION - Failure to delete unverifiable information",
            "623": "SECTION 623 VIOLATION - Furnisher noncompliance with accuracy requirements",
            "623(a)(1)": "SECTION 623(a)(1) VIOLATION - Reporting information known to be inaccurate",
            "623(b)": "SECTION 623(b) VIOLATION - Failure to investigate upon notice of dispute",
            "607(b)": "SECTION 607(b) VIOLATION - Failure to assure maximum possible accuracy",
            "605(a)": "SECTION 605(a) VIOLATION - Reporting obsolete information",
        }

        for section in sorted(set(fcra_sections)):
            violation_desc = section_violations.get(section, f"SECTION {section} VIOLATION")
            lines.append(f"    - {violation_desc}")

        lines.extend([
            "",
            "Each violation subjects you to LIABILITY under 15 U.S.C. § 1681n (willful) or",
            "§ 1681o (negligent), including actual damages, statutory damages, punitive damages,",
            "and attorney's fees.",
            ""
        ])

        return "\n".join(lines)

    @classmethod
    def format_conclusion(cls, seed: int = 0) -> str:
        """Format the aggressive conclusion."""
        return f"""
{cls.get_section_header("conclusion")}

YOU HAVE EXACTLY THIRTY (30) DAYS from receipt of this notice to:

1. CONDUCT a reasonable reinvestigation using ORIGINAL SOURCE DOCUMENTATION
2. DELETE any information that cannot be INDEPENDENTLY VERIFIED
3. PROVIDE written results of your investigation to me

{cls.get_damage_warning(seed)}

THIS IS NOT A THREAT - IT IS A STATEMENT OF LEGAL FACT.

If you continue to report this unverified, inaccurate information after receiving this notice,
such conduct will be deemed WILLFUL under the FCRA, entitling me to pursue MAXIMUM DAMAGES
available under federal law, including statutory damages, punitive damages, and attorney's fees.

{cls.get_expression("reservation", seed)}

GOVERN YOURSELF ACCORDINGLY.
"""

    @classmethod
    def format_signature_block(cls, consumer_name: str) -> str:
        """Format the assertive signature block."""
        return f"""
WITHOUT PREJUDICE AND WITH FULL RESERVATION OF ALL RIGHTS,



_________________________________
{consumer_name}

Date: _____________________

CC: Consumer Financial Protection Bureau
CC: [State] Attorney General
CC: Federal Trade Commission

SENT VIA CERTIFIED MAIL, RETURN RECEIPT REQUESTED
RETAIN THIS LETTER AND ALL RESPONSES FOR POTENTIAL LITIGATION
"""
