"""
FCRA Statute Mapping - Single Source of Truth (SSOT)
Authoritative mapping of FCRA sections to correct U.S. Code citations.

This module provides litigation-grade citation accuracy for legal letters.
All FCRA statute references should use resolve_statute() for correct USC formatting.
"""

# FCRA Section → USC Mapping (authoritative source)
# Key insight: FCRA sections map to 15 U.S.C. § 1681 + letter suffix
# Section 611(a) → 15 U.S.C. § 1681i(a)  (i = reinvestigation)
# Section 623(b) → 15 U.S.C. § 1681s-2(b) (s-2 = furnisher duties)
# Section 605(a) → 15 U.S.C. § 1681c(a)  (c = obsolescence)
# Section 607(b) → 15 U.S.C. § 1681e(b)  (e = accuracy procedures)

FCRA_STATUTE_MAP = {
    # Section 611 - Reinvestigation (15 U.S.C. § 1681i)
    "611": {
        "usc": "15 U.S.C. § 1681i",
        "title": "Procedure in case of disputed accuracy",
        "subsections": ["(a)", "(a)(1)", "(a)(2)", "(a)(3)", "(a)(4)", "(a)(5)", "(a)(6)", "(b)", "(c)", "(d)"],
    },
    "611(a)": {
        "usc": "15 U.S.C. § 1681i(a)",
        "title": "Reinvestigation of disputed information",
        "description": "Requires CRAs to reinvestigate disputed information within 30 days",
    },
    "611(a)(1)": {
        "usc": "15 U.S.C. § 1681i(a)(1)",
        "title": "Reinvestigation required",
        "description": "CRA must conduct reasonable reinvestigation",
    },
    "611(a)(1)(A)": {
        "usc": "15 U.S.C. § 1681i(a)(1)(A)",
        "title": "Reinvestigation requirement",
        "description": "Must reinvestigate free of charge",
    },
    "611(a)(2)": {
        "usc": "15 U.S.C. § 1681i(a)(2)",
        "title": "Prompt notice to furnisher",
        "description": "CRA must notify furnisher of dispute",
    },
    "611(a)(3)": {
        "usc": "15 U.S.C. § 1681i(a)(3)",
        "title": "Determination that dispute is frivolous",
        "description": "Standards for frivolous dispute determination",
    },
    "611(a)(4)": {
        "usc": "15 U.S.C. § 1681i(a)(4)",
        "title": "Consideration of consumer information",
        "description": "CRA must consider all relevant information from consumer",
    },
    "611(a)(5)": {
        "usc": "15 U.S.C. § 1681i(a)(5)",
        "title": "Treatment of inaccurate or unverifiable information",
        "description": "Delete or modify information that cannot be verified",
    },
    "611(a)(5)(A)": {
        "usc": "15 U.S.C. § 1681i(a)(5)(A)",
        "title": "Deletion requirement",
        "description": "Promptly delete inaccurate or unverifiable information",
    },
    "611(a)(6)": {
        "usc": "15 U.S.C. § 1681i(a)(6)",
        "title": "Notice of results of reinvestigation",
        "description": "Written notice of reinvestigation results within 5 days",
    },
    "611(a)(6)(A)": {
        "usc": "15 U.S.C. § 1681i(a)(6)(A)",
        "title": "Statement of results",
        "description": "Prompt written notice of investigation results",
    },
    "611(a)(7)": {
        "usc": "15 U.S.C. § 1681i(a)(7)",
        "title": "Description of reinvestigation procedure",
        "description": "Consumer may request description of procedure",
    },

    # Section 623 - Furnisher Responsibilities (15 U.S.C. § 1681s-2)
    "623": {
        "usc": "15 U.S.C. § 1681s-2",
        "title": "Responsibilities of furnishers of information",
        "subsections": ["(a)", "(a)(1)", "(a)(2)", "(a)(3)", "(b)", "(b)(1)", "(b)(2)", "(c)", "(d)", "(e)"],
    },
    "623(a)": {
        "usc": "15 U.S.C. § 1681s-2(a)",
        "title": "Duty of furnishers to provide accurate information",
        "description": "Furnishers must not report known inaccurate information",
    },
    "623(a)(1)": {
        "usc": "15 U.S.C. § 1681s-2(a)(1)",
        "title": "Prohibition on reporting inaccurate information",
        "description": "May not furnish information known or believed to be inaccurate",
    },
    "623(a)(1)(A)": {
        "usc": "15 U.S.C. § 1681s-2(a)(1)(A)",
        "title": "Prohibition - known inaccurate",
        "description": "May not furnish information the person knows is inaccurate",
    },
    "623(a)(1)(B)": {
        "usc": "15 U.S.C. § 1681s-2(a)(1)(B)",
        "title": "Prohibition - reasonable cause to believe",
        "description": "May not furnish information with reasonable cause to believe inaccurate",
    },
    "623(a)(2)": {
        "usc": "15 U.S.C. § 1681s-2(a)(2)",
        "title": "Duty to correct and update information",
        "description": "Must promptly notify CRA of corrections/updates",
    },
    "623(a)(3)": {
        "usc": "15 U.S.C. § 1681s-2(a)(3)",
        "title": "Duty to provide notice of dispute",
        "description": "Must note disputed status when reporting",
    },
    "623(b)": {
        "usc": "15 U.S.C. § 1681s-2(b)",
        "title": "Duties of furnishers upon notice of dispute",
        "description": "Investigation duties when CRA forwards dispute",
    },
    "623(b)(1)": {
        "usc": "15 U.S.C. § 1681s-2(b)(1)",
        "title": "In general",
        "description": "Conduct investigation with respect to disputed information",
    },
    "623(b)(1)(A)": {
        "usc": "15 U.S.C. § 1681s-2(b)(1)(A)",
        "title": "Conduct investigation",
        "description": "Must conduct investigation of disputed information",
    },
    "623(b)(1)(B)": {
        "usc": "15 U.S.C. § 1681s-2(b)(1)(B)",
        "title": "Review relevant information",
        "description": "Review all relevant information provided by CRA",
    },
    "623(b)(1)(C)": {
        "usc": "15 U.S.C. § 1681s-2(b)(1)(C)",
        "title": "Report results",
        "description": "Report results of investigation to CRA",
    },
    "623(b)(1)(D)": {
        "usc": "15 U.S.C. § 1681s-2(b)(1)(D)",
        "title": "Modify, delete, or block",
        "description": "Modify, delete, or permanently block reporting if inaccurate",
    },
    "623(b)(1)(E)": {
        "usc": "15 U.S.C. § 1681s-2(b)(1)(E)",
        "title": "Report investigation results to all CRAs",
        "description": "Report results to all CRAs if information modified/deleted",
    },

    # Section 605 - Requirements Relating to Information (15 U.S.C. § 1681c)
    "605": {
        "usc": "15 U.S.C. § 1681c",
        "title": "Requirements relating to information contained in consumer reports",
        "subsections": ["(a)", "(b)", "(c)", "(d)", "(e)", "(f)", "(g)", "(h)"],
    },
    "605(a)": {
        "usc": "15 U.S.C. § 1681c(a)",
        "title": "Information excluded from consumer reports (obsolete information)",
        "description": "Time limits for reporting adverse information (7 years, 10 for bankruptcy)",
    },
    "605(a)(1)": {
        "usc": "15 U.S.C. § 1681c(a)(1)",
        "title": "Bankruptcy 10-year limit",
        "description": "Bankruptcy cases more than 10 years before report",
    },
    "605(a)(2)": {
        "usc": "15 U.S.C. § 1681c(a)(2)",
        "title": "Civil suits and judgments 7-year limit",
        "description": "Civil suits, civil judgments, and records of arrest",
    },
    "605(a)(3)": {
        "usc": "15 U.S.C. § 1681c(a)(3)",
        "title": "Paid tax liens 7-year limit",
        "description": "Paid tax liens from date of payment",
    },
    "605(a)(4)": {
        "usc": "15 U.S.C. § 1681c(a)(4)",
        "title": "Collections and charged-off accounts 7-year limit",
        "description": "Accounts placed for collection or charged to profit/loss",
    },
    "605(a)(5)": {
        "usc": "15 U.S.C. § 1681c(a)(5)",
        "title": "Other adverse items 7-year limit",
        "description": "Any other adverse item of information",
    },
    "605(b)": {
        "usc": "15 U.S.C. § 1681c(b)",
        "title": "Exempted cases",
        "description": "Exceptions for credit > $150k, employment > $75k, insurance > $150k",
    },

    # Section 605A - Identity Theft Provisions (15 U.S.C. § 1681c-1)
    "605A": {
        "usc": "15 U.S.C. § 1681c-1",
        "title": "Identity theft prevention; fraud alerts and active duty alerts",
        "description": "Fraud alert and active duty alert requirements",
    },
    "605A(a)": {
        "usc": "15 U.S.C. § 1681c-1(a)",
        "title": "Initial fraud alerts",
        "description": "One-call initial fraud alert for 1 year",
    },
    "605A(b)": {
        "usc": "15 U.S.C. § 1681c-1(b)",
        "title": "Extended fraud alerts",
        "description": "Extended fraud alert for 7 years",
    },
    "605A(c)": {
        "usc": "15 U.S.C. § 1681c-1(c)",
        "title": "Active duty military alerts",
        "description": "Active duty alerts for military personnel",
    },

    # Section 605B - Block of Information from Identity Theft (15 U.S.C. § 1681c-2)
    "605B": {
        "usc": "15 U.S.C. § 1681c-2",
        "title": "Block of information resulting from identity theft",
        "description": "Requirements to block information from identity theft",
    },
    "605B(a)": {
        "usc": "15 U.S.C. § 1681c-2(a)",
        "title": "Block requirement",
        "description": "CRA must block reporting of information from identity theft",
    },
    "605B(b)": {
        "usc": "15 U.S.C. § 1681c-2(b)",
        "title": "Notification",
        "description": "CRA must notify furnisher of block",
    },

    # Section 607 - Compliance Procedures (15 U.S.C. § 1681e)
    "607": {
        "usc": "15 U.S.C. § 1681e",
        "title": "Compliance procedures",
        "subsections": ["(a)", "(b)", "(c)", "(d)", "(e)"],
    },
    "607(a)": {
        "usc": "15 U.S.C. § 1681e(a)",
        "title": "Identity and purposes of credit users",
        "description": "CRA must require identification of users and permissible purposes",
    },
    "607(b)": {
        "usc": "15 U.S.C. § 1681e(b)",
        "title": "Accuracy of report (Maximum Possible Accuracy)",
        "description": "CRA must follow reasonable procedures to assure maximum possible accuracy",
    },
    "607(c)": {
        "usc": "15 U.S.C. § 1681e(c)",
        "title": "Disclosure of consumer reports",
        "description": "CRA must disclose to consumer upon request",
    },
    "607(d)": {
        "usc": "15 U.S.C. § 1681e(d)",
        "title": "Notice to users and furnishers",
        "description": "CRA must notify users and furnishers of responsibilities",
    },
    "607(e)": {
        "usc": "15 U.S.C. § 1681e(e)",
        "title": "Procurement of consumer report",
        "description": "Requirements for procuring consumer reports",
    },

    # Section 609 - Disclosures to Consumers (15 U.S.C. § 1681g)
    "609": {
        "usc": "15 U.S.C. § 1681g",
        "title": "Disclosures to consumers",
        "subsections": ["(a)", "(a)(1)", "(a)(2)", "(a)(3)", "(b)", "(c)", "(d)", "(e)", "(f)", "(g)"],
    },
    "609(a)": {
        "usc": "15 U.S.C. § 1681g(a)",
        "title": "Information on file",
        "description": "CRA must disclose all information in consumer's file",
    },
    "609(a)(1)": {
        "usc": "15 U.S.C. § 1681g(a)(1)",
        "title": "File contents disclosure",
        "description": "All information in consumer's file at time of request",
    },
    "609(a)(2)": {
        "usc": "15 U.S.C. § 1681g(a)(2)",
        "title": "Sources of information",
        "description": "Sources of information in consumer's file",
    },
    "609(a)(3)": {
        "usc": "15 U.S.C. § 1681g(a)(3)",
        "title": "Recipients of consumer reports",
        "description": "Identity of each person who procured consumer report",
    },
    "609(c)": {
        "usc": "15 U.S.C. § 1681g(c)",
        "title": "Summary of rights",
        "description": "CRA must provide summary of rights with each disclosure",
    },

    # Section 610 - Conditions and Form of Disclosure (15 U.S.C. § 1681h)
    "610": {
        "usc": "15 U.S.C. § 1681h",
        "title": "Conditions and form of disclosure to consumers",
        "description": "Requirements for how disclosures are made",
    },
    "610(a)": {
        "usc": "15 U.S.C. § 1681h(a)",
        "title": "In general",
        "description": "Proper identification required before disclosure",
    },

    # Section 612 - Charges for Disclosures (15 U.S.C. § 1681j)
    "612": {
        "usc": "15 U.S.C. § 1681j",
        "title": "Charges for certain disclosures",
        "description": "Free annual disclosure; free disclosure after adverse action",
    },
    "612(a)": {
        "usc": "15 U.S.C. § 1681j(a)",
        "title": "Free annual disclosure",
        "description": "Consumer entitled to free annual file disclosure",
    },
    "612(b)": {
        "usc": "15 U.S.C. § 1681j(b)",
        "title": "Free disclosure after adverse action",
        "description": "Free disclosure within 60 days of adverse action notice",
    },

    # Section 615 - Requirements on Users (15 U.S.C. § 1681m)
    "615": {
        "usc": "15 U.S.C. § 1681m",
        "title": "Requirements on users of consumer reports",
        "description": "Adverse action notice requirements",
    },
    "615(a)": {
        "usc": "15 U.S.C. § 1681m(a)",
        "title": "Adverse action duties",
        "description": "Notice of adverse action based on consumer report",
    },
    "615(a)(1)": {
        "usc": "15 U.S.C. § 1681m(a)(1)",
        "title": "Notice of adverse action",
        "description": "User must provide notice of adverse action",
    },

    # Section 616 - Civil Liability for Willful Noncompliance (15 U.S.C. § 1681n)
    "616": {
        "usc": "15 U.S.C. § 1681n",
        "title": "Civil liability for willful noncompliance",
        "description": "Actual damages, punitive damages, and attorney's fees",
    },
    "616(a)": {
        "usc": "15 U.S.C. § 1681n(a)",
        "title": "In general",
        "description": "Liability for willful violations",
    },
    "616(a)(1)": {
        "usc": "15 U.S.C. § 1681n(a)(1)",
        "title": "Actual damages or statutory damages",
        "description": "Greater of actual damages or $100-$1,000 per violation",
    },
    "616(a)(2)": {
        "usc": "15 U.S.C. § 1681n(a)(2)",
        "title": "Punitive damages",
        "description": "Punitive damages as court may allow",
    },
    "616(a)(3)": {
        "usc": "15 U.S.C. § 1681n(a)(3)",
        "title": "Attorney's fees",
        "description": "Costs of action and reasonable attorney's fees",
    },

    # Section 617 - Civil Liability for Negligent Noncompliance (15 U.S.C. § 1681o)
    "617": {
        "usc": "15 U.S.C. § 1681o",
        "title": "Civil liability for negligent noncompliance",
        "description": "Actual damages and attorney's fees for negligent violations",
    },
    "617(a)": {
        "usc": "15 U.S.C. § 1681o(a)",
        "title": "In general",
        "description": "Liability for negligent violations",
    },

    # Section 618 - Jurisdiction of Courts (15 U.S.C. § 1681p)
    "618": {
        "usc": "15 U.S.C. § 1681p",
        "title": "Jurisdiction of courts; limitation of actions",
        "description": "Federal court jurisdiction; 2-year statute of limitations",
    },

    # Section 619 - Obtaining Information Under False Pretenses (15 U.S.C. § 1681q)
    "619": {
        "usc": "15 U.S.C. § 1681q",
        "title": "Obtaining information under false pretenses",
        "description": "Criminal penalties for obtaining consumer reports under false pretenses",
    },

    # Section 620 - Unauthorized Disclosures (15 U.S.C. § 1681r)
    "620": {
        "usc": "15 U.S.C. § 1681r",
        "title": "Unauthorized disclosures by officers or employees",
        "description": "Criminal penalties for unauthorized disclosure",
    },
}


def resolve_statute(section: str) -> str:
    """
    Convert an FCRA section identifier to correct U.S. Code citation.

    Args:
        section: FCRA section identifier (e.g., "611(a)", "623(b)", "605(a)")

    Returns:
        Correct USC citation (e.g., "15 U.S.C. § 1681i(a)")

    Examples:
        >>> resolve_statute("611(a)")
        '15 U.S.C. § 1681i(a)'
        >>> resolve_statute("623(b)")
        '15 U.S.C. § 1681s-2(b)'
        >>> resolve_statute("605(a)")
        '15 U.S.C. § 1681c(a)'
        >>> resolve_statute("607(b)")
        '15 U.S.C. § 1681e(b)'
    """
    # Normalize section format
    section_clean = section.strip()

    # Try exact match
    if section_clean in FCRA_STATUTE_MAP:
        return FCRA_STATUTE_MAP[section_clean]["usc"]

    # Try without parentheses formatting variations
    section_normalized = section_clean.replace(" ", "")

    if section_normalized in FCRA_STATUTE_MAP:
        return FCRA_STATUTE_MAP[section_normalized]["usc"]

    # Try to find parent section
    # e.g., "611(a)(1)(A)" -> try "611(a)(1)" -> "611(a)" -> "611"
    parts = section_clean
    while "(" in parts:
        parent = parts.rsplit("(", 1)[0]
        if parent in FCRA_STATUTE_MAP:
            # Build the subsection part
            subsection = section_clean[len(parent):]
            return f"{FCRA_STATUTE_MAP[parent]['usc']}{subsection}"
        parts = parent

    # Base section lookup for unrecognized subsections
    # e.g., "611(z)" should still resolve to "15 U.S.C. § 1681i(z)"
    base_section_map = {
        "611": "15 U.S.C. § 1681i",
        "623": "15 U.S.C. § 1681s-2",
        "605": "15 U.S.C. § 1681c",
        "605A": "15 U.S.C. § 1681c-1",
        "605B": "15 U.S.C. § 1681c-2",
        "607": "15 U.S.C. § 1681e",
        "609": "15 U.S.C. § 1681g",
        "610": "15 U.S.C. § 1681h",
        "612": "15 U.S.C. § 1681j",
        "615": "15 U.S.C. § 1681m",
        "616": "15 U.S.C. § 1681n",
        "617": "15 U.S.C. § 1681o",
        "618": "15 U.S.C. § 1681p",
        "619": "15 U.S.C. § 1681q",
        "620": "15 U.S.C. § 1681r",
    }

    # Extract base section number
    import re
    match = re.match(r"(\d+[A-B]?)", section_clean)
    if match:
        base = match.group(1)
        subsection = section_clean[len(base):]
        if base in base_section_map:
            return f"{base_section_map[base]}{subsection}"

    # Final fallback - return with FCRA prefix
    return f"FCRA Section {section_clean}"


def get_statute_details(section: str) -> dict:
    """
    Get full details for an FCRA section.

    Args:
        section: FCRA section identifier

    Returns:
        Dictionary with 'usc', 'title', and optionally 'description'
    """
    if section in FCRA_STATUTE_MAP:
        return FCRA_STATUTE_MAP[section]

    # Try normalized version
    section_normalized = section.strip().replace(" ", "")
    if section_normalized in FCRA_STATUTE_MAP:
        return FCRA_STATUTE_MAP[section_normalized]

    # Return basic info with resolved USC
    return {
        "usc": resolve_statute(section),
        "title": f"FCRA Section {section}",
    }


def format_legal_citation(section: str, include_title: bool = False) -> str:
    """
    Format a complete legal citation for an FCRA section.

    Args:
        section: FCRA section identifier
        include_title: Whether to include the section title

    Returns:
        Formatted legal citation string

    Examples:
        >>> format_legal_citation("611(a)")
        '15 U.S.C. § 1681i(a)'
        >>> format_legal_citation("611(a)", include_title=True)
        '15 U.S.C. § 1681i(a) (Reinvestigation of disputed information)'
    """
    usc = resolve_statute(section)

    if include_title:
        details = get_statute_details(section)
        title = details.get("title", "")
        if title:
            return f"{usc} ({title})"

    return usc
