"""
Citation Normalization Utilities

Provides unified citation formatting across all supported statutes.
All citations are normalized to canonical USC format: "15 U.S.C. § {section}"
"""
import re
from typing import Optional, Tuple

from .fcra_statutes import resolve_statute as resolve_fcra
from .fdcpa_statutes import resolve_fdcpa_statute as resolve_fdcpa


def normalize_citation(raw: str) -> str:
    """
    Convert any citation format to canonical USC format.

    Canonical Format: "15 U.S.C. § {section}"

    Args:
        raw: Raw citation string in any format

    Returns:
        Normalized USC citation

    Examples:
        >>> normalize_citation("FDCPA 1692e(5)")
        '15 U.S.C. § 1692e(5)'
        >>> normalize_citation("FCRA 611(a)")
        '15 U.S.C. § 1681i(a)'
        >>> normalize_citation("605(a)")
        '15 U.S.C. § 1681c(a)'
        >>> normalize_citation("15 U.S.C. § 1692e(5)")
        '15 U.S.C. § 1692e(5)'
    """
    if not raw:
        return raw

    raw = raw.strip()

    # Already in canonical format
    if raw.startswith("15 U.S.C."):
        return raw

    # Detect statute type and route to appropriate resolver
    statute_type, section = _detect_statute_type(raw)

    if statute_type == "fdcpa":
        return resolve_fdcpa(section)
    elif statute_type == "fcra":
        return resolve_fcra(section)
    else:
        # Unknown statute - return as-is with basic formatting
        return f"15 U.S.C. § {section}"


def _detect_statute_type(raw: str) -> Tuple[str, str]:
    """
    Detect the statute type from a raw citation.

    Returns:
        Tuple of (statute_type, section)
    """
    raw_upper = raw.upper()
    section = raw

    # Explicit FDCPA prefix
    if raw_upper.startswith("FDCPA"):
        section = raw[5:].strip()
        if section.startswith("§"):
            section = section[1:].strip()
        return ("fdcpa", section)

    # Explicit FCRA prefix
    if raw_upper.startswith("FCRA"):
        section = raw[4:].strip()
        if section.startswith("§"):
            section = section[1:].strip()
        return ("fcra", section)

    # Section prefix
    if raw_upper.startswith("SECTION "):
        section = raw[8:].strip()

    # § prefix
    if section.startswith("§"):
        section = section[1:].strip()

    # Detect by section number pattern
    # FDCPA sections: 1692, 1692a-p
    # FCRA sections: 6xx (e.g., 605, 611, 623)
    if re.match(r"^1692[a-p]?", section):
        return ("fdcpa", section)
    elif re.match(r"^6\d{2}", section):
        return ("fcra", section)
    elif re.match(r"^1681", section):
        # Already USC format for FCRA
        return ("fcra", section)

    # Default to FCRA for ambiguous cases
    return ("fcra", section)


def format_citation_for_letter(
    citation: str,
    include_statute_name: bool = False,
    formal: bool = True
) -> str:
    """
    Format a citation for inclusion in a consumer letter.

    Args:
        citation: The citation to format
        include_statute_name: Whether to include the statute name
        formal: Whether to use formal formatting

    Returns:
        Formatted citation string

    Examples:
        >>> format_citation_for_letter("15 U.S.C. § 1692e(5)")
        '15 U.S.C. § 1692e(5)'
        >>> format_citation_for_letter("15 U.S.C. § 1692e(5)", include_statute_name=True)
        'Fair Debt Collection Practices Act (15 U.S.C. § 1692e(5))'
    """
    normalized = normalize_citation(citation)

    if include_statute_name:
        statute_name = get_statute_name(normalized)
        if statute_name:
            return f"{statute_name} ({normalized})"

    return normalized


def get_statute_name(citation: str) -> Optional[str]:
    """
    Get the full statute name from a citation.

    Args:
        citation: The USC citation

    Returns:
        Statute name or None
    """
    if "1692" in citation:
        return "Fair Debt Collection Practices Act"
    elif "1681" in citation:
        return "Fair Credit Reporting Act"
    elif "1691" in citation:
        return "Equal Credit Opportunity Act"
    elif "1601" in citation:
        return "Truth in Lending Act"
    elif "1666" in citation:
        return "Fair Credit Billing Act"
    return None


def get_statute_abbreviation(citation: str) -> Optional[str]:
    """
    Get the statute abbreviation from a citation.

    Args:
        citation: The USC citation

    Returns:
        Abbreviation (FDCPA, FCRA, etc.) or None
    """
    if "1692" in citation:
        return "FDCPA"
    elif "1681" in citation:
        return "FCRA"
    elif "1691" in citation:
        return "ECOA"
    elif "1601" in citation:
        return "TILA"
    elif "1666" in citation:
        return "FCBA"
    return None


def is_fdcpa_citation(citation: str) -> bool:
    """Check if a citation is an FDCPA citation."""
    return "1692" in citation


def is_fcra_citation(citation: str) -> bool:
    """Check if a citation is an FCRA citation."""
    return "1681" in citation


def validate_citation_format(citation: str) -> bool:
    """
    Validate that a citation is in canonical format.

    Args:
        citation: The citation to validate

    Returns:
        True if valid, False otherwise
    """
    if not citation:
        return False

    # Must start with "15 U.S.C. §"
    pattern = r"^15 U\.S\.C\. § \d{4}"
    return bool(re.match(pattern, citation))


def extract_section_number(citation: str) -> Optional[str]:
    """
    Extract the section number from a citation.

    Args:
        citation: The citation (any format)

    Returns:
        Section number (e.g., "1692e(5)", "1681i(a)")
    """
    normalized = normalize_citation(citation)

    # Extract section after "§ "
    match = re.search(r"§ (\d{4}[a-z]?(?:\([^)]+\))*)", normalized)
    if match:
        return match.group(1)

    return None


# Batch normalization for violation processing
def normalize_violation_citations(violation: dict) -> dict:
    """
    Normalize all citation fields in a violation dictionary.

    Args:
        violation: Violation dictionary with citation fields

    Returns:
        Violation with normalized citations
    """
    # Normalize fcra_section (legacy field)
    if "fcra_section" in violation and violation["fcra_section"]:
        violation["fcra_section"] = normalize_citation(violation["fcra_section"])

    # Normalize primary_statute (new field)
    if "primary_statute" in violation and violation["primary_statute"]:
        violation["primary_statute"] = normalize_citation(violation["primary_statute"])

    # Normalize secondary_statutes (new field)
    if "secondary_statutes" in violation and violation["secondary_statutes"]:
        violation["secondary_statutes"] = [
            normalize_citation(s) for s in violation["secondary_statutes"]
        ]

    return violation
