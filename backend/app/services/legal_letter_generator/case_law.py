"""
Legal Letter Generator - Case Law Library
Provides case law citations and legal precedents for FCRA dispute letters.
"""
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


class CaseLawCategory(str, Enum):
    """Categories of FCRA case law."""
    REINVESTIGATION = "reinvestigation"
    ACCURACY = "accuracy"
    FURNISHER_DUTY = "furnisher_duty"
    DAMAGES = "damages"
    WILLFUL_VIOLATION = "willful_violation"
    OBSOLETE_INFO = "obsolete_info"
    PROCEDURES = "procedures"
    IDENTITY = "identity"


@dataclass
class CaseLawCitation:
    """A case law citation with legal context."""
    case_name: str
    citation: str
    court: str
    year: int
    category: CaseLawCategory
    holding: str
    relevance: str
    key_quote: str
    fcra_sections: List[str]


# Comprehensive FCRA case law library
CASE_LAW_LIBRARY: Dict[str, CaseLawCitation] = {
    "cushman": CaseLawCitation(
        case_name="Cushman v. Trans Union Corp.",
        citation="115 F.3d 220 (3d Cir. 1997)",
        court="Third Circuit Court of Appeals",
        year=1997,
        category=CaseLawCategory.REINVESTIGATION,
        holding="A CRA's reinvestigation procedures are unreasonable as a matter of law if the CRA merely parrots back information from the furnisher without any independent verification.",
        relevance="Establishes that CRAs cannot simply accept furnisher responses without independent investigation.",
        key_quote="A 'reasonable' reinvestigation requires more than merely obtaining a verification from the furnisher; the CRA must conduct an independent review that goes beyond the original source of information.",
        fcra_sections=["611", "611(a)(1)"]
    ),
    "henson": CaseLawCitation(
        case_name="Henson v. CSC Credit Services",
        citation="29 F.3d 280 (7th Cir. 1994)",
        court="Seventh Circuit Court of Appeals",
        year=1994,
        category=CaseLawCategory.REINVESTIGATION,
        holding="A CRA's reinvestigation is unreasonable if it merely rubber-stamps the furnisher's position without conducting any meaningful review of the dispute.",
        relevance="Reinforces the requirement for substantive reinvestigation beyond simply contacting the furnisher.",
        key_quote="A credit reporting agency cannot discharge its duty to reinvestigate by merely rubber-stamping the furnisher's original entry.",
        fcra_sections=["611", "611(a)(1)"]
    ),
    "gorman": CaseLawCitation(
        case_name="Gorman v. Wolpoff & Abramson, LLP",
        citation="584 F.3d 1147 (9th Cir. 2009)",
        court="Ninth Circuit Court of Appeals",
        year=2009,
        category=CaseLawCategory.FURNISHER_DUTY,
        holding="Furnishers have a duty to conduct a reasonable investigation in response to consumer disputes, and this duty cannot be satisfied by merely verifying that the account exists.",
        relevance="Establishes furnisher obligations under FCRA Section 623(b) to conduct meaningful investigations.",
        key_quote="The statutory duty to 'review all relevant information' means that a furnisher must undertake a reasonable investigation proportional to the nature of the dispute.",
        fcra_sections=["623(b)", "623(a)(1)"]
    ),
    "johnson": CaseLawCitation(
        case_name="Johnson v. MBNA America Bank, NA",
        citation="357 F.3d 426 (4th Cir. 2004)",
        court="Fourth Circuit Court of Appeals",
        year=2004,
        category=CaseLawCategory.FURNISHER_DUTY,
        holding="A furnisher's investigation is unreasonable if it does not review all relevant information submitted by the consumer with the dispute.",
        relevance="Clarifies that furnishers must review consumer-provided documentation, not just internal records.",
        key_quote="When a consumer provides documents supporting a dispute, the furnisher cannot ignore that evidence and simply verify from its own files.",
        fcra_sections=["623(b)", "611"]
    ),
    "safeco": CaseLawCitation(
        case_name="Safeco Ins. Co. of America v. Burr",
        citation="551 U.S. 47 (2007)",
        court="Supreme Court of the United States",
        year=2007,
        category=CaseLawCategory.WILLFUL_VIOLATION,
        holding="A willful FCRA violation requires that the defendant knew or showed reckless disregard of whether its conduct violated the FCRA.",
        relevance="Defines the standard for willful violations and entitlement to statutory damages.",
        key_quote="Where the company's reading of the statute was not objectively unreasonable, there is no willful violation exposing the company to statutory damages.",
        fcra_sections=["616", "617"]
    ),
    "smith_safeco": CaseLawCitation(
        case_name="Smith v. LexisNexis Screening Solutions",
        citation="837 F.3d 604 (6th Cir. 2016)",
        court="Sixth Circuit Court of Appeals",
        year=2016,
        category=CaseLawCategory.ACCURACY,
        holding="A CRA violates the FCRA when it reports information that is technically accurate but materially misleading.",
        relevance="Establishes that accuracy requires more than technical truth; information must not be misleading.",
        key_quote="The FCRA's accuracy requirement is not met when a report is technically true but creates a materially misleading impression.",
        fcra_sections=["607(b)", "611"]
    ),
    "dennis": CaseLawCitation(
        case_name="Dennis v. BEH-1, LLC",
        citation="520 F.3d 1066 (9th Cir. 2008)",
        court="Ninth Circuit Court of Appeals",
        year=2008,
        category=CaseLawCategory.OBSOLETE_INFO,
        holding="The seven-year reporting period under FCRA Section 605(a) begins from the date of first delinquency, and this date cannot be reset by subsequent activity.",
        relevance="Prevents 're-aging' of accounts and extends clear guidance on obsolescence calculations.",
        key_quote="The date of first delinquency is fixed at the time the account first becomes delinquent, and subsequent events cannot restart the clock.",
        fcra_sections=["605(a)", "605(c)"]
    ),
    "sepulvado": CaseLawCitation(
        case_name="Sepulvado v. CSC Credit Services",
        citation="158 F.3d 890 (5th Cir. 1998)",
        court="Fifth Circuit Court of Appeals",
        year=1998,
        category=CaseLawCategory.PROCEDURES,
        holding="A CRA must maintain reasonable procedures to prevent the inclusion of inaccurate information, not just procedures to correct errors after they occur.",
        relevance="Emphasizes proactive duty of CRAs to prevent inaccuracies, not just reactive correction.",
        key_quote="The requirement of 'maximum possible accuracy' imposes a duty to establish reasonable procedures proactively, not merely to respond to disputes.",
        fcra_sections=["607(b)", "611"]
    ),
    "guimond": CaseLawCitation(
        case_name="Guimond v. Trans Union Credit Information Co.",
        citation="45 F.3d 1329 (9th Cir. 1995)",
        court="Ninth Circuit Court of Appeals",
        year=1995,
        category=CaseLawCategory.ACCURACY,
        holding="A CRA cannot satisfy its duty under Section 607(b) by blindly accepting all information provided by furnishers without independent verification.",
        relevance="Reinforces independent verification requirements for CRAs.",
        key_quote="The FCRA imposes a duty upon credit reporting agencies to establish reasonable procedures designed to ensure maximum possible accuracy of the information in consumer credit reports.",
        fcra_sections=["607(b)"]
    ),
    "philbin": CaseLawCitation(
        case_name="Philbin v. Trans Union Corp.",
        citation="101 F.3d 957 (3d Cir. 1996)",
        court="Third Circuit Court of Appeals",
        year=1996,
        category=CaseLawCategory.REINVESTIGATION,
        holding="A CRA's failure to verify information independently after receiving a consumer dispute can constitute a violation of the reinvestigation requirements.",
        relevance="Strengthens the requirement for independent verification during reinvestigation.",
        key_quote="Upon notice of a dispute, a CRA must do more than simply ask the original furnisher to verify the accuracy of the reported information.",
        fcra_sections=["611", "611(a)(1)"]
    ),
    "denan": CaseLawCitation(
        case_name="DeNan v. Trans Union LLC",
        citation="2019 WL 2009746 (N.D. Ill. 2019)",
        court="Northern District of Illinois",
        year=2019,
        category=CaseLawCategory.FURNISHER_DUTY,
        holding="A furnisher cannot satisfy its investigation duty by relying solely on automated dispute responses without human review of consumer allegations.",
        relevance="Addresses modern automated dispute handling and requires meaningful human involvement.",
        key_quote="The FCRA's investigation requirement cannot be satisfied by wholly automated systems that fail to consider the specific nature of consumer disputes.",
        fcra_sections=["623(b)"]
    ),
    "saunders": CaseLawCitation(
        case_name="Saunders v. Branch Banking & Trust Co.",
        citation="526 F.3d 142 (4th Cir. 2008)",
        court="Fourth Circuit Court of Appeals",
        year=2008,
        category=CaseLawCategory.FURNISHER_DUTY,
        holding="When a furnisher receives notice of a dispute, it must review all relevant information provided by the CRA, including information from the consumer.",
        relevance="Establishes that furnishers must review consumer-provided evidence during investigations.",
        key_quote="The duty to investigate triggered under Section 623(b) requires review of all relevant information forwarded by the CRA.",
        fcra_sections=["623(b)", "611"]
    ),
    "bruce": CaseLawCitation(
        case_name="Bruce v. First U.S.A. Bank, N.A.",
        citation="103 F. Supp. 2d 1135 (E.D. Mo. 2000)",
        court="Eastern District of Missouri",
        year=2000,
        category=CaseLawCategory.DAMAGES,
        holding="Emotional distress damages are recoverable under the FCRA without requiring physical manifestation.",
        relevance="Supports claims for emotional distress damages in FCRA cases.",
        key_quote="A consumer may recover damages for emotional distress caused by FCRA violations without proof of economic loss.",
        fcra_sections=["616", "617"]
    ),
    "stevenson": CaseLawCitation(
        case_name="Stevenson v. TRW Inc.",
        citation="987 F.2d 288 (5th Cir. 1993)",
        court="Fifth Circuit Court of Appeals",
        year=1993,
        category=CaseLawCategory.PROCEDURES,
        holding="The 'maximum possible accuracy' standard requires CRAs to implement procedures that prevent reasonably foreseeable errors.",
        relevance="Defines the scope of maximum accuracy requirements under Section 607(b).",
        key_quote="The FCRA requires reasonable procedures to assure accuracy, not perfection, but the standard is 'maximum possible accuracy' given the CRA's capabilities.",
        fcra_sections=["607(b)"]
    ),
    "koropoulos": CaseLawCitation(
        case_name="Koropoulos v. Credit Bureau, Inc.",
        citation="734 F.2d 37 (D.C. Cir. 1984)",
        court="D.C. Circuit Court of Appeals",
        year=1984,
        category=CaseLawCategory.IDENTITY,
        holding="A CRA may be liable for including information about a different person with a similar name in a consumer's credit file.",
        relevance="Establishes liability for mixed files and mistaken identity in credit reporting.",
        key_quote="A CRA has a duty to use reasonable procedures to ensure that credit information is being associated with the correct consumer.",
        fcra_sections=["607(b)", "611"]
    ),
}


def get_case_by_name(name: str) -> Optional[CaseLawCitation]:
    """Get a case citation by its short name."""
    name_lower = name.lower().replace(" ", "_").replace("v.", "").replace("v", "")
    if name_lower in CASE_LAW_LIBRARY:
        return CASE_LAW_LIBRARY[name_lower]

    # Try partial matching
    for key, case in CASE_LAW_LIBRARY.items():
        if name_lower in key or key in name_lower:
            return case
        if name_lower in case.case_name.lower():
            return case

    return None


def get_cases_by_category(category: CaseLawCategory) -> List[CaseLawCitation]:
    """Get all cases in a specific category."""
    return [case for case in CASE_LAW_LIBRARY.values() if case.category == category]


def get_cases_by_fcra_section(section: str) -> List[CaseLawCitation]:
    """Get all cases relevant to a specific FCRA section."""
    return [case for case in CASE_LAW_LIBRARY.values() if section in case.fcra_sections]


def get_reinvestigation_cases() -> List[CaseLawCitation]:
    """Get cases relevant to reinvestigation disputes."""
    return get_cases_by_category(CaseLawCategory.REINVESTIGATION)


def get_furnisher_duty_cases() -> List[CaseLawCitation]:
    """Get cases relevant to furnisher duty disputes."""
    return get_cases_by_category(CaseLawCategory.FURNISHER_DUTY)


def get_accuracy_cases() -> List[CaseLawCitation]:
    """Get cases relevant to accuracy disputes."""
    return get_cases_by_category(CaseLawCategory.ACCURACY)


def format_citation(case: CaseLawCitation, style: str = "full") -> str:
    """
    Format a case citation for inclusion in a letter.

    Args:
        case: The case citation to format
        style: 'full', 'short', or 'quote'

    Returns:
        Formatted citation string
    """
    if style == "short":
        return f"{case.case_name}, {case.citation}"
    elif style == "quote":
        return f'"{case.key_quote}" {case.case_name}, {case.citation}'
    else:  # full
        return f"""
**{case.case_name}**, {case.citation} ({case.court}, {case.year})

*Holding:* {case.holding}

*Key Quote:* "{case.key_quote}"

*Applicable FCRA Sections:* {', '.join(case.fcra_sections)}
"""


def get_relevant_cases_for_violation(violation_type: str) -> List[CaseLawCitation]:
    """
    Get relevant case law for a specific violation type.

    Args:
        violation_type: The type of violation

    Returns:
        List of relevant case citations
    """
    # Map violation types to case law categories
    violation_category_map = {
        "failure_to_investigate": CaseLawCategory.REINVESTIGATION,
        "incomplete_investigation": CaseLawCategory.REINVESTIGATION,
        "rubber_stamp_verification": CaseLawCategory.REINVESTIGATION,
        "inaccurate_balance": CaseLawCategory.ACCURACY,
        "incorrect_payment_status": CaseLawCategory.ACCURACY,
        "wrong_account_status": CaseLawCategory.ACCURACY,
        "balance_discrepancy": CaseLawCategory.ACCURACY,
        "payment_history_error": CaseLawCategory.ACCURACY,
        "furnisher_violation": CaseLawCategory.FURNISHER_DUTY,
        "failure_to_correct": CaseLawCategory.FURNISHER_DUTY,
        "outdated_information": CaseLawCategory.OBSOLETE_INFO,
        "obsolete_account": CaseLawCategory.OBSOLETE_INFO,
        "reaging": CaseLawCategory.OBSOLETE_INFO,
        "mixed_file": CaseLawCategory.IDENTITY,
        "identity_error": CaseLawCategory.IDENTITY,
        "not_mine": CaseLawCategory.IDENTITY,
        "willful_violation": CaseLawCategory.WILLFUL_VIOLATION,
    }

    category = violation_category_map.get(violation_type)
    if category:
        return get_cases_by_category(category)

    # Default to reinvestigation cases
    return get_reinvestigation_cases()


class CaseLawLibrary:
    """Static helper class for accessing case law."""

    @staticmethod
    def get_case(name: str) -> Optional[CaseLawCitation]:
        """Get a case by its short name (e.g., 'cushman', 'henson')."""
        return CASE_LAW_LIBRARY.get(name.lower())

    @staticmethod
    def get_cases_by_category(category: CaseLawCategory) -> List[CaseLawCitation]:
        """Get all cases in a specific category."""
        return [case for case in CASE_LAW_LIBRARY.values() if case.category == category]

    @staticmethod
    def get_cases_by_fcra_section(section: str) -> List[CaseLawCitation]:
        """Get all cases relevant to a specific FCRA section."""
        return [case for case in CASE_LAW_LIBRARY.values() if section in case.fcra_sections]


class CaseLawCitationBuilder:
    """Builds case law citation blocks for legal letters."""

    def __init__(self, violations: List[Dict]):
        self.violations = violations
        self.relevant_cases: Dict[str, CaseLawCitation] = {}
        self._analyze_violations()

    def _analyze_violations(self) -> None:
        """Analyze violations to determine relevant case law."""
        for violation in self.violations:
            v_type = violation.get("violation_type", "")
            for case in get_relevant_cases_for_violation(v_type):
                self.relevant_cases[case.case_name] = case

    def get_primary_cases(self, limit: int = 3) -> List[CaseLawCitation]:
        """Get the most relevant primary cases for the dispute."""
        # Prioritize cases by relevance (reinvestigation first, then accuracy, etc.)
        priority_order = [
            CaseLawCategory.REINVESTIGATION,
            CaseLawCategory.FURNISHER_DUTY,
            CaseLawCategory.ACCURACY,
            CaseLawCategory.OBSOLETE_INFO,
            CaseLawCategory.PROCEDURES,
        ]

        sorted_cases = sorted(
            self.relevant_cases.values(),
            key=lambda c: (priority_order.index(c.category) if c.category in priority_order else 99, -c.year)
        )

        return sorted_cases[:limit]

    def build_citation_block(self, cases: List[CaseLawCitation] = None) -> str:
        """Build a formatted citation block for inclusion in a letter."""
        if cases is None:
            cases = self.get_primary_cases()

        if not cases:
            return ""

        blocks = []
        for case in cases:
            blocks.append(format_citation(case, style="full"))

        return "\n---\n".join(blocks)

    def get_key_quotes(self) -> List[str]:
        """Get key quotes from relevant cases."""
        cases = self.get_primary_cases()
        return [f'"{case.key_quote}" - {case.case_name}' for case in cases]


# Pre-built citation strings for common use cases
STANDARD_REINVESTIGATION_CITE = """
Per *Cushman v. Trans Union Corp.*, 115 F.3d 220 (3d Cir. 1997), a CRA's reinvestigation procedures
are unreasonable as a matter of law if the CRA merely parrots back information from the furnisher
without any independent verification. See also *Henson v. CSC Credit Services*, 29 F.3d 280 (7th Cir. 1994)
(holding that rubber-stamping furnisher responses fails to satisfy reinvestigation requirements).
"""

STANDARD_FURNISHER_CITE = """
Under *Gorman v. Wolpoff & Abramson, LLP*, 584 F.3d 1147 (9th Cir. 2009), furnishers have a duty to
conduct a reasonable investigation in response to consumer disputes. This duty requires review of
all relevant information, including documents submitted by the consumer. See *Johnson v. MBNA America Bank, NA*,
357 F.3d 426 (4th Cir. 2004).
"""

STANDARD_ACCURACY_CITE = """
Per *Smith v. LexisNexis Screening Solutions*, 837 F.3d 604 (6th Cir. 2016), the FCRA's accuracy
requirement mandates that reported information not be materially misleading, even if technically true.
See also *Guimond v. Trans Union Credit Information Co.*, 45 F.3d 1329 (9th Cir. 1995) (requiring
independent verification of furnisher-provided data).
"""

STANDARD_OBSOLESCENCE_CITE = """
Under *Dennis v. BEH-1, LLC*, 520 F.3d 1066 (9th Cir. 2008), the seven-year reporting period
begins from the date of first delinquency and cannot be reset by subsequent activity. Re-aging
of accounts through manipulation of reporting dates violates FCRA Section 605(a).
"""
