"""
FDCPA Statute Mapping - Single Source of Truth (SSOT)
Authoritative mapping of FDCPA sections to correct U.S. Code citations.

This module provides litigation-grade citation accuracy for legal letters.
All FDCPA statute references should use resolve_fdcpa_statute() for correct USC formatting.

Actor Scope:
- Primary: Third-party debt collectors
- Secondary: Debt buyers, collection attorneys
- Excluded: Original creditors (unless collecting under different name)
"""

# FDCPA Section → USC Mapping (authoritative source)
# All sections are under 15 U.S.C. § 1692x
FDCPA_STATUTE_MAP = {
    # Section 1692 - Congressional findings and purpose
    "1692": {
        "usc": "15 U.S.C. § 1692",
        "title": "Congressional findings and declaration of purpose",
        "description": "Establishes purpose of eliminating abusive debt collection practices",
    },

    # Section 1692a - Definitions
    "1692a": {
        "usc": "15 U.S.C. § 1692a",
        "title": "Definitions",
        "description": "Defines debt, debt collector, consumer, creditor, and other key terms",
    },
    "1692a(3)": {
        "usc": "15 U.S.C. § 1692a(3)",
        "title": "Definition of consumer",
        "description": "Natural person obligated or allegedly obligated to pay debt",
    },
    "1692a(5)": {
        "usc": "15 U.S.C. § 1692a(5)",
        "title": "Definition of debt",
        "description": "Obligation arising from consumer transaction for personal, family, or household purposes",
    },
    "1692a(6)": {
        "usc": "15 U.S.C. § 1692a(6)",
        "title": "Definition of debt collector",
        "description": "Person who regularly collects debts owed to another or uses another name",
    },

    # Section 1692b - Acquisition of location information
    "1692b": {
        "usc": "15 U.S.C. § 1692b",
        "title": "Acquisition of location information",
        "description": "Restrictions on contacting third parties to locate consumer",
    },

    # Section 1692c - Communication in connection with debt collection
    "1692c": {
        "usc": "15 U.S.C. § 1692c",
        "title": "Communication in connection with debt collection",
        "subsections": ["(a)", "(a)(1)", "(a)(2)", "(a)(3)", "(b)", "(c)"],
    },
    "1692c(a)": {
        "usc": "15 U.S.C. § 1692c(a)",
        "title": "Communication with the consumer generally",
        "description": "Time, place, and manner restrictions on communications",
    },
    "1692c(b)": {
        "usc": "15 U.S.C. § 1692c(b)",
        "title": "Communication with third parties",
        "description": "Prohibition on communicating with third parties about debt",
    },
    "1692c(c)": {
        "usc": "15 U.S.C. § 1692c(c)",
        "title": "Ceasing communication",
        "description": "Consumer's right to demand cessation of communication",
    },

    # Section 1692d - Harassment or abuse
    "1692d": {
        "usc": "15 U.S.C. § 1692d",
        "title": "Harassment or abuse",
        "description": "Prohibition on conduct intended to harass, oppress, or abuse",
    },
    "1692d(1)": {
        "usc": "15 U.S.C. § 1692d(1)",
        "title": "Threats of violence",
        "description": "Prohibition on threats of violence or criminal means",
    },
    "1692d(2)": {
        "usc": "15 U.S.C. § 1692d(2)",
        "title": "Obscene language",
        "description": "Prohibition on obscene or profane language",
    },
    "1692d(5)": {
        "usc": "15 U.S.C. § 1692d(5)",
        "title": "Repeated telephone calls",
        "description": "Prohibition on repeated calls intended to annoy or harass",
    },

    # Section 1692e - False or misleading representations (PRIMARY ENFORCEMENT SECTION)
    "1692e": {
        "usc": "15 U.S.C. § 1692e",
        "title": "False or misleading representations",
        "description": "Prohibition on false, deceptive, or misleading representations",
        "subsections": ["(2)", "(2)(A)", "(2)(B)", "(3)", "(4)", "(5)", "(7)", "(8)", "(9)", "(10)", "(11)"],
    },
    "1692e(2)": {
        "usc": "15 U.S.C. § 1692e(2)",
        "title": "False representation of debt characteristics",
        "description": "False representation of character, amount, or legal status of debt",
    },
    "1692e(2)(A)": {
        "usc": "15 U.S.C. § 1692e(2)(A)",
        "title": "False representation of legal status",
        "description": "Falsely representing the character, amount, or legal status of any debt",
    },
    "1692e(2)(B)": {
        "usc": "15 U.S.C. § 1692e(2)(B)",
        "title": "False representation of services",
        "description": "Falsely representing compensation or services rendered",
    },
    "1692e(3)": {
        "usc": "15 U.S.C. § 1692e(3)",
        "title": "False representation of affiliation",
        "description": "False representation of affiliation with government",
    },
    "1692e(4)": {
        "usc": "15 U.S.C. § 1692e(4)",
        "title": "False representation of consequences",
        "description": "False representation of consequences of nonpayment",
    },
    "1692e(5)": {
        "usc": "15 U.S.C. § 1692e(5)",
        "title": "Threat to take action that cannot legally be taken",
        "description": "Threatening to take any action that cannot legally be taken or that is not intended",
    },
    "1692e(7)": {
        "usc": "15 U.S.C. § 1692e(7)",
        "title": "False representation of consumer's conduct",
        "description": "Falsely representing that consumer committed crime or other conduct",
    },
    "1692e(8)": {
        "usc": "15 U.S.C. § 1692e(8)",
        "title": "Communicating false credit information",
        "description": "Communicating credit information known or which should be known to be false",
    },
    "1692e(9)": {
        "usc": "15 U.S.C. § 1692e(9)",
        "title": "Deceptive document simulation",
        "description": "Using documents that simulate legal process or government authorization",
    },
    "1692e(10)": {
        "usc": "15 U.S.C. § 1692e(10)",
        "title": "Deceptive means",
        "description": "Use of any false representation or deceptive means to collect or attempt to collect debt",
    },
    "1692e(11)": {
        "usc": "15 U.S.C. § 1692e(11)",
        "title": "Failure to disclose collector identity",
        "description": "Failure to disclose in initial communication that debt collector is attempting to collect a debt",
    },

    # Section 1692f - Unfair practices
    "1692f": {
        "usc": "15 U.S.C. § 1692f",
        "title": "Unfair practices",
        "description": "Prohibition on unfair or unconscionable means to collect debt",
        "subsections": ["(1)", "(2)", "(3)", "(4)", "(5)", "(6)", "(7)", "(8)"],
    },
    "1692f(1)": {
        "usc": "15 U.S.C. § 1692f(1)",
        "title": "Collection of unauthorized amounts",
        "description": "Collection of any amount not expressly authorized by agreement or permitted by law",
    },
    "1692f(2)": {
        "usc": "15 U.S.C. § 1692f(2)",
        "title": "Acceptance of postdated checks",
        "description": "Soliciting postdated check for threatening or instituting criminal prosecution",
    },
    "1692f(6)": {
        "usc": "15 U.S.C. § 1692f(6)",
        "title": "Nonjudicial action on exempt property",
        "description": "Taking or threatening nonjudicial action to dispossess exempt property",
    },
    "1692f(8)": {
        "usc": "15 U.S.C. § 1692f(8)",
        "title": "Deceptive envelope language",
        "description": "Using language or symbols on envelope indicating debt collection",
    },

    # Section 1692g - Validation of debts
    "1692g": {
        "usc": "15 U.S.C. § 1692g",
        "title": "Validation of debts",
        "description": "Requirements for debt validation notices and consumer dispute rights",
        "subsections": ["(a)", "(a)(1)", "(a)(2)", "(a)(3)", "(a)(4)", "(a)(5)", "(b)", "(c)"],
    },
    "1692g(a)": {
        "usc": "15 U.S.C. § 1692g(a)",
        "title": "Notice of debt",
        "description": "Required disclosure within 5 days of initial communication",
    },
    "1692g(a)(1)": {
        "usc": "15 U.S.C. § 1692g(a)(1)",
        "title": "Amount of debt",
        "description": "Statement of amount of debt",
    },
    "1692g(a)(2)": {
        "usc": "15 U.S.C. § 1692g(a)(2)",
        "title": "Name of creditor",
        "description": "Name of creditor to whom debt is owed",
    },
    "1692g(a)(3)": {
        "usc": "15 U.S.C. § 1692g(a)(3)",
        "title": "Right to dispute",
        "description": "Statement that debt will be assumed valid unless disputed within 30 days",
    },
    "1692g(a)(4)": {
        "usc": "15 U.S.C. § 1692g(a)(4)",
        "title": "Verification statement",
        "description": "Statement that verification will be mailed if disputed",
    },
    "1692g(a)(5)": {
        "usc": "15 U.S.C. § 1692g(a)(5)",
        "title": "Original creditor identification",
        "description": "Statement that name of original creditor will be provided if requested",
    },
    "1692g(b)": {
        "usc": "15 U.S.C. § 1692g(b)",
        "title": "Disputed debts",
        "description": "Collector must cease until verification is mailed if timely disputed",
    },

    # Section 1692h - Multiple debts
    "1692h": {
        "usc": "15 U.S.C. § 1692h",
        "title": "Multiple debts",
        "description": "Payment application rules when consumer owes multiple debts",
    },

    # Section 1692i - Legal actions by debt collectors
    "1692i": {
        "usc": "15 U.S.C. § 1692i",
        "title": "Legal actions by debt collectors",
        "description": "Venue requirements for legal actions",
    },
    "1692i(a)": {
        "usc": "15 U.S.C. § 1692i(a)",
        "title": "Venue for legal action",
        "description": "Actions must be brought in judicial district where consumer signed contract or resides",
    },

    # Section 1692j - Furnishing deceptive forms
    "1692j": {
        "usc": "15 U.S.C. § 1692j",
        "title": "Furnishing certain deceptive forms",
        "description": "Prohibition on designing or providing deceptive collection forms",
    },

    # Section 1692k - Civil liability (DAMAGES SECTION - INTERNAL USE ONLY)
    "1692k": {
        "usc": "15 U.S.C. § 1692k",
        "title": "Civil liability",
        "description": "Damages available for FDCPA violations",
        "subsections": ["(a)", "(a)(1)", "(a)(2)(A)", "(a)(2)(B)", "(a)(3)", "(b)", "(c)", "(d)"],
    },
    "1692k(a)": {
        "usc": "15 U.S.C. § 1692k(a)",
        "title": "Amount of damages",
        "description": "Actual damages, statutory damages, costs and fees",
    },
    "1692k(a)(1)": {
        "usc": "15 U.S.C. § 1692k(a)(1)",
        "title": "Actual damages",
        "description": "Any actual damages sustained by person",
    },
    "1692k(a)(2)(A)": {
        "usc": "15 U.S.C. § 1692k(a)(2)(A)",
        "title": "Individual statutory damages",
        "description": "Additional damages up to $1,000 for individual actions",
    },
    "1692k(a)(2)(B)": {
        "usc": "15 U.S.C. § 1692k(a)(2)(B)",
        "title": "Class action damages",
        "description": "Class action damages up to lesser of $500,000 or 1% of net worth",
    },
    "1692k(a)(3)": {
        "usc": "15 U.S.C. § 1692k(a)(3)",
        "title": "Costs and attorney's fees",
        "description": "Costs of action plus reasonable attorney's fees",
    },
    "1692k(b)": {
        "usc": "15 U.S.C. § 1692k(b)",
        "title": "Factors for additional damages",
        "description": "Court considers frequency, persistence, nature of noncompliance, intent",
    },
    "1692k(c)": {
        "usc": "15 U.S.C. § 1692k(c)",
        "title": "Bona fide error defense",
        "description": "No liability if violation unintentional and resulted from bona fide error",
    },
    "1692k(d)": {
        "usc": "15 U.S.C. § 1692k(d)",
        "title": "Statute of limitations",
        "description": "Action must be brought within one year from date of violation",
    },

    # Section 1692l - Administrative enforcement
    "1692l": {
        "usc": "15 U.S.C. § 1692l",
        "title": "Administrative enforcement",
        "description": "FTC and CFPB enforcement authority",
    },

    # Section 1692m - Reports to Congress
    "1692m": {
        "usc": "15 U.S.C. § 1692m",
        "title": "Reports to Congress by the Bureau",
        "description": "Annual reporting requirements",
    },

    # Section 1692n - Relation to State laws
    "1692n": {
        "usc": "15 U.S.C. § 1692n",
        "title": "Relation to State laws",
        "description": "FDCPA does not preempt stronger state laws",
    },

    # Section 1692o - Exemption for State regulation
    "1692o": {
        "usc": "15 U.S.C. § 1692o",
        "title": "Exemption for State regulation",
        "description": "CFPB may exempt state-regulated collectors",
    },

    # Section 1692p - Exception for certain bad check enforcement
    "1692p": {
        "usc": "15 U.S.C. § 1692p",
        "title": "Exception for certain bad check enforcement programs",
        "description": "Limited exception for district attorney bad check programs",
    },
}


def resolve_fdcpa_statute(section: str) -> str:
    """
    Convert an FDCPA section identifier to correct U.S. Code citation.

    Args:
        section: FDCPA section identifier (e.g., "1692e(5)", "1692f(1)")

    Returns:
        Correct USC citation (e.g., "15 U.S.C. § 1692e(5)")

    Examples:
        >>> resolve_fdcpa_statute("1692e(5)")
        '15 U.S.C. § 1692e(5)'
        >>> resolve_fdcpa_statute("1692f(1)")
        '15 U.S.C. § 1692f(1)'
        >>> resolve_fdcpa_statute("FDCPA 1692e(5)")
        '15 U.S.C. § 1692e(5)'
    """
    # Normalize section format
    section_clean = section.strip()

    # Strip common prefixes
    for prefix in ["FDCPA ", "FDCPA§", "§", "Section "]:
        if section_clean.upper().startswith(prefix.upper()):
            section_clean = section_clean[len(prefix):].strip()
            break

    # Try exact match
    if section_clean in FDCPA_STATUTE_MAP:
        return FDCPA_STATUTE_MAP[section_clean]["usc"]

    # Try without parentheses formatting variations
    section_normalized = section_clean.replace(" ", "")

    if section_normalized in FDCPA_STATUTE_MAP:
        return FDCPA_STATUTE_MAP[section_normalized]["usc"]

    # Try to find parent section and build full citation
    # e.g., "1692e(2)(A)(i)" -> try "1692e(2)(A)" -> "1692e(2)" -> "1692e"
    parts = section_clean
    while "(" in parts:
        parent = parts.rsplit("(", 1)[0]
        if parent in FDCPA_STATUTE_MAP:
            subsection = section_clean[len(parent):]
            return f"{FDCPA_STATUTE_MAP[parent]['usc']}{subsection}"
        parts = parent

    # Base section lookup for unrecognized subsections
    # e.g., "1692e(99)" should still resolve to "15 U.S.C. § 1692e(99)"
    import re
    match = re.match(r"(1692[a-p]?)", section_clean)
    if match:
        base = match.group(1)
        subsection = section_clean[len(base):]
        return f"15 U.S.C. § {base}{subsection}"

    # Final fallback - return with FDCPA prefix
    return f"15 U.S.C. § {section_clean}"


def get_fdcpa_statute_details(section: str) -> dict:
    """
    Get full details for an FDCPA section.

    Args:
        section: FDCPA section identifier

    Returns:
        Dictionary with 'usc', 'title', and optionally 'description'
    """
    # Strip common prefixes
    section_clean = section.strip()
    for prefix in ["FDCPA ", "FDCPA§", "§", "Section "]:
        if section_clean.upper().startswith(prefix.upper()):
            section_clean = section_clean[len(prefix):].strip()
            break

    if section_clean in FDCPA_STATUTE_MAP:
        return FDCPA_STATUTE_MAP[section_clean]

    # Try normalized version
    section_normalized = section_clean.replace(" ", "")
    if section_normalized in FDCPA_STATUTE_MAP:
        return FDCPA_STATUTE_MAP[section_normalized]

    # Return basic info with resolved USC
    return {
        "usc": resolve_fdcpa_statute(section),
        "title": f"FDCPA Section {section_clean}",
    }


def format_fdcpa_legal_citation(section: str, include_title: bool = False) -> str:
    """
    Format a complete legal citation for an FDCPA section.

    Args:
        section: FDCPA section identifier
        include_title: Whether to include the section title

    Returns:
        Formatted legal citation string

    Examples:
        >>> format_fdcpa_legal_citation("1692e(5)")
        '15 U.S.C. § 1692e(5)'
        >>> format_fdcpa_legal_citation("1692e(5)", include_title=True)
        '15 U.S.C. § 1692e(5) (Threat to take action that cannot legally be taken)'
    """
    usc = resolve_fdcpa_statute(section)

    if include_title:
        details = get_fdcpa_statute_details(section)
        title = details.get("title", "")
        if title:
            return f"{usc} ({title})"

    return usc


# Actor applicability flags
FDCPA_ACTOR_SCOPE = {
    "applies_to": ["collector", "debt_buyer", "collection_attorney"],
    "excludes": ["original_creditor", "bureau"],
    "conditional": {
        "oc_chargeoff": "Applies if collecting under different name or sold to debt buyer"
    }
}

# Sections detectable via credit report analysis
CREDIT_REPORT_DETECTABLE_SECTIONS = [
    "1692e(2)(A)",  # False representation of legal status
    "1692e(5)",     # Threat on time-barred debt
    "1692e(8)",     # False credit information
    "1692f(1)",     # Unauthorized amounts
]

# Sections NOT detectable via credit report (require communication records)
NON_DETECTABLE_SECTIONS = [
    "1692c",        # Communication violations
    "1692d",        # Harassment
    "1692g",        # Validation timing
]
