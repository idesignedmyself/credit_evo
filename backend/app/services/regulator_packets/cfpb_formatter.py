"""
CFPB Payload Formatter - Phase 4

Converts violations + letter data into structured CFPB complaint payload.
No free-text. Narrative assembled from deterministic blocks only.
"""

import json
from pathlib import Path
from typing import Any, Dict, List

from app.models.cfpb_packet import CFPBComplaintPayload
from app.models.letter_object import DemandType


# =============================================================================
# LOAD CFPB ISSUE MAPPING CONFIG
# =============================================================================

_CONFIG_PATH = Path(__file__).parent.parent.parent.parent / "configs" / "cfpb_issue_map.json"

with open(_CONFIG_PATH, "r") as f:
    CFPB_ISSUE_MAP = json.load(f)


# =============================================================================
# HARD-LOCKED NARRATIVE TEMPLATES
# =============================================================================

NARRATIVE_HEADER = (
    "I am disputing inaccurate information on my credit report. "
    "The following factual inaccuracies have been identified through analysis "
    "of my credit file against Metro 2 Format reporting standards and the "
    "Credit Reporting Resource Guide (CRRG)."
)

NARRATIVE_FOOTER = (
    "I request that the Consumer Financial Protection Bureau investigate "
    "these violations and take appropriate enforcement action. "
    "All cited violations are substantiated by the attached evidence, "
    "including the original dispute letter, violation analysis, "
    "and CRRG authority references."
)


# =============================================================================
# VIOLATION LINE TEMPLATE
# =============================================================================

def format_violation_line(violation: Dict[str, Any]) -> str:
    """
    Format a single violation as a deterministic narrative line.

    Template: "Violation: {rule_id} | {creditor} | {acct_mask} | {field/page} | {statute}"
    """
    rule_id = violation.get("violation_type", "UNKNOWN")
    creditor = violation.get("creditor_name", "Unknown Creditor")
    acct_mask = violation.get("account_number_masked", "****")

    # Get CRRG citation - sort by anchor_id for determinism
    citations = sorted(
        violation.get("citations", []),
        key=lambda c: c.get("anchor_id", "")
    )
    citation = citations[0] if citations else None

    if citation:
        field_ref = citation.get("section_title", "")
        page_ref = f"pp. {citation.get('page_start', '')}-{citation.get('page_end', '')}"
        crrg_ref = f"{field_ref} ({page_ref})"
    else:
        crrg_ref = "N/A"

    # Get statute - sort for determinism
    statutes = sorted(violation.get("statutes", []))
    statute = statutes[0] if statutes else "15 U.S.C. § 1681"

    return f"- Violation: {rule_id} | {creditor} | {acct_mask} | {crrg_ref} | {statute}"


# =============================================================================
# CATEGORY RESOLUTION
# =============================================================================

def resolve_category(violations: List[Dict[str, Any]]) -> Dict[str, str]:
    """
    Resolve CFPB product/issue/sub_issue from violation types.

    CFPB complaint schema permits only a single product/issue/sub_issue triplet.
    When multiple violation categories exist, the lexicographically-first
    violation type is used solely to satisfy CFPB schema constraints.
    This does NOT imply prioritization or weighting of violations.

    Returns the category mapping for the primary violation type.
    Violations are sorted by type for deterministic selection.
    """
    if not violations:
        return CFPB_ISSUE_MAP["default"]

    # Sort violations by type for deterministic primary selection
    violations_sorted = sorted(
        violations,
        key=lambda v: v.get("violation_type", "")
    )
    primary_vtype = violations_sorted[0].get("violation_type", "")

    # Find matching category
    for category_name, category_data in CFPB_ISSUE_MAP["categories"].items():
        if primary_vtype in category_data.get("violation_types", []):
            return {
                "product": category_data["product"],
                "issue": category_data["issue"],
                "sub_issue": category_data["sub_issue"],
            }

    # Default fallback
    return CFPB_ISSUE_MAP["default"]


# =============================================================================
# DESIRED RESOLUTION
# =============================================================================

def resolve_desired_resolution(demand_type: DemandType) -> str:
    """
    Map demand type to CFPB desired resolution text.

    Hard-locked from config - no free-text.
    """
    resolution_key = demand_type.value  # "DELETION", "CORRECTION", "PROCEDURAL"
    return CFPB_ISSUE_MAP["desired_resolutions"].get(
        resolution_key,
        CFPB_ISSUE_MAP["desired_resolutions"]["CORRECTION"]
    )


# =============================================================================
# NARRATIVE ASSEMBLY
# =============================================================================

def assemble_narrative(violations: List[Dict[str, Any]]) -> str:
    """
    Assemble CFPB narrative from deterministic blocks.

    Structure:
    1. Header (hard-locked)
    2. Violation lines (templated)
    3. Footer (hard-locked)

    No free-text writing. Template only.
    """
    lines = [NARRATIVE_HEADER, ""]

    # Sort violations by type for deterministic ordering
    violations_sorted = sorted(
        violations,
        key=lambda v: v.get("violation_type", "")
    )

    for violation in violations_sorted:
        lines.append(format_violation_line(violation))

    lines.append("")
    lines.append(NARRATIVE_FOOTER)

    return "\n".join(lines)


# =============================================================================
# METRO 2 ANCHORS EXTRACTION
# =============================================================================

def extract_metro2_anchors(violations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Extract and deduplicate CRRG anchors from violations.

    Sorted by anchor_id for determinism.
    """
    anchors = []
    seen_ids = set()

    for violation in violations:
        for citation in violation.get("citations", []):
            anchor_id = citation.get("anchor_id", "")
            if anchor_id and anchor_id not in seen_ids:
                anchors.append({
                    "anchor_id": anchor_id,
                    "rule_id": citation.get("rule_id", ""),
                    "section_title": citation.get("section_title", ""),
                    "page_start": citation.get("page_start"),
                    "page_end": citation.get("page_end"),
                })
                seen_ids.add(anchor_id)

    # Sort by anchor_id for determinism
    return sorted(anchors, key=lambda a: a.get("anchor_id", ""))


# =============================================================================
# DISPUTED ACCOUNT REFS EXTRACTION
# =============================================================================

def extract_disputed_accounts(violations: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """
    Extract disputed account references from violations.

    Deduplicated by (creditor, account_mask) pair.
    Sorted for determinism.
    """
    accounts = []
    seen = set()

    for violation in violations:
        creditor = violation.get("creditor_name", "")
        acct_mask = violation.get("account_number_masked", "")
        key = (creditor, acct_mask)

        if key not in seen and creditor:
            accounts.append({
                "creditor_name": creditor,
                "account_number_masked": acct_mask,
                "account_type": violation.get("account_type", ""),
            })
            seen.add(key)

    # Sort by creditor name, then account mask for determinism
    return sorted(accounts, key=lambda a: (a["creditor_name"], a["account_number_masked"]))


# =============================================================================
# STATUTES EXTRACTION
# =============================================================================

def extract_statutes(violations: List[Dict[str, Any]]) -> List[str]:
    """
    Extract and deduplicate statutes from violations.

    Sorted for determinism.
    """
    statutes = set()

    for violation in violations:
        for statute in violation.get("statutes", []):
            statutes.add(statute)

    return sorted(statutes)


# =============================================================================
# MAIN FORMATTER
# =============================================================================

def format_cfpb_payload(
    *,
    violations: List[Dict[str, Any]],
    company_name: str,
    consumer_name: str,
    consumer_contact: Dict[str, str],
    demand_type: DemandType,
    attachments_index: List[Dict[str, str]] = None,
) -> CFPBComplaintPayload:
    """
    Format violations into a structured CFPB complaint payload.

    Args:
        violations: List of violation dicts with citations injected
        company_name: Furnisher or CRA name
        consumer_name: Consumer's full name
        consumer_contact: Dict with email, phone, address fields
        demand_type: DemandType enum (from letter generation)
        attachments_index: Optional list of {filename, sha256} dicts

    Returns:
        CFPBComplaintPayload with all fields populated deterministically
    """
    # Resolve category from violations
    category = resolve_category(violations)

    # Assemble narrative from blocks
    narrative = assemble_narrative(violations)

    # Resolve desired resolution
    desired_resolution = resolve_desired_resolution(demand_type)

    # Extract metro2 anchors
    metro2_anchors = extract_metro2_anchors(violations)

    # Extract disputed accounts
    disputed_accounts = extract_disputed_accounts(violations)

    # Extract statutes
    statutes = extract_statutes(violations)

    return CFPBComplaintPayload(
        product=category["product"],
        issue=category["issue"],
        sub_issue=category["sub_issue"],
        company_name=company_name,
        consumer_name=consumer_name,
        consumer_contact=consumer_contact,
        narrative=narrative,
        desired_resolution=desired_resolution,
        disputed_account_refs=disputed_accounts,
        statutes=statutes,
        metro2_anchors=metro2_anchors,
        attachments_index=attachments_index or [],
    )
