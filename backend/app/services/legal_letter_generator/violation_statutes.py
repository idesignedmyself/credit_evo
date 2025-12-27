"""
Unified Statute Routing - Multi-Statute Violation Support

This module provides a unified interface for mapping violations to their
applicable statutes, supporting primary and secondary citations with
actor-aware routing.

Scope:
- FCRA: Always applicable to all violations
- FDCPA: Applicable only to collectors and sold debt
- ECOA: Limited to Metro 2 ECOA Code errors
- Others: Flag-only, no automated assertions
"""
from enum import Enum
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
import warnings


class StatuteType(str, Enum):
    """Supported statute types."""
    FCRA = "fcra"
    FDCPA = "fdcpa"
    ECOA = "ecoa"      # Limited support
    STATE = "state"    # Flag-only
    TILA = "tila"      # Flag-only
    FCBA = "fcba"      # Flag-only
    SCRA = "scra"      # Flag-only


class ActorType(str, Enum):
    """Actor types for statute applicability routing."""
    BUREAU = "bureau"
    FURNISHER = "furnisher"
    COLLECTOR = "collector"
    ORIGINAL_CREDITOR = "original_creditor"
    DEBT_BUYER = "debt_buyer"


@dataclass
class StatuteCitation:
    """A single statute citation with applicability metadata."""
    statute_type: StatuteType
    section: str
    usc: str
    applies_to: List[str]
    title: Optional[str] = None
    description: Optional[str] = None
    consumer_facing: bool = True  # Whether to include in consumer letters

    def applies_to_actor(self, actor: str) -> bool:
        """Check if this citation applies to the given actor type."""
        return actor.lower() in [a.lower() for a in self.applies_to]


@dataclass
class ViolationStatutes:
    """
    Multi-statute support for a single violation type.

    Supports primary citation plus optional secondary citations
    for statute stacking when conduct violates multiple laws.
    """
    primary: StatuteCitation
    secondary: Optional[List[StatuteCitation]] = None
    flag_only: Optional[List[StatuteCitation]] = None  # Potential violations, not asserted

    def get_applicable_citations(self, actor: str) -> List[StatuteCitation]:
        """Get all citations applicable to the given actor."""
        citations = []

        if self.primary.applies_to_actor(actor):
            citations.append(self.primary)

        if self.secondary:
            for cite in self.secondary:
                if cite.applies_to_actor(actor):
                    citations.append(cite)

        return citations

    def get_primary_for_actor(self, actor: str) -> Optional[StatuteCitation]:
        """Get the primary applicable citation for an actor."""
        if self.primary.applies_to_actor(actor):
            return self.primary

        # Demote: find first applicable secondary
        if self.secondary:
            for cite in self.secondary:
                if cite.applies_to_actor(actor):
                    return cite

        return None


# =============================================================================
# VIOLATION STATUTE MAP - Single Source of Truth
# =============================================================================
# Migrated from VIOLATION_FCRA_MAP with multi-statute support

VIOLATION_STATUTE_MAP: Dict[str, ViolationStatutes] = {
    # =========================================================================
    # TIME-BARRED / SOL VIOLATIONS (FDCPA Primary)
    # =========================================================================
    "time_barred_debt_risk": ViolationStatutes(
        primary=StatuteCitation(
            statute_type=StatuteType.FDCPA,
            section="1692e(5)",
            usc="15 U.S.C. § 1692e(5)",
            applies_to=["collector", "debt_buyer"],
            title="Threat to take action that cannot legally be taken",
            description="Threatening to sue on time-barred debt",
        ),
        secondary=[
            StatuteCitation(
                statute_type=StatuteType.FCRA,
                section="623(a)(1)",
                usc="15 U.S.C. § 1681s-2(a)(1)",
                applies_to=["collector", "debt_buyer", "furnisher", "original_creditor"],
                title="Duty to provide accurate information",
            ),
        ],
    ),

    # =========================================================================
    # COLLECTION-SPECIFIC VIOLATIONS (FDCPA Primary)
    # =========================================================================
    "collection_balance_inflation": ViolationStatutes(
        primary=StatuteCitation(
            statute_type=StatuteType.FDCPA,
            section="1692f(1)",
            usc="15 U.S.C. § 1692f(1)",
            applies_to=["collector", "debt_buyer"],
            title="Collection of unauthorized amounts",
            description="Collecting amounts not authorized by agreement or law",
        ),
        secondary=[
            StatuteCitation(
                statute_type=StatuteType.FCRA,
                section="623(a)(1)",
                usc="15 U.S.C. § 1681s-2(a)(1)",
                applies_to=["collector", "debt_buyer", "furnisher"],
                title="Duty to provide accurate information",
            ),
        ],
    ),

    "false_debt_status": ViolationStatutes(
        primary=StatuteCitation(
            statute_type=StatuteType.FDCPA,
            section="1692e(2)(A)",
            usc="15 U.S.C. § 1692e(2)(A)",
            applies_to=["collector", "debt_buyer"],
            title="False representation of legal status",
            description="Falsely representing the character, amount, or legal status of debt",
        ),
        secondary=[
            StatuteCitation(
                statute_type=StatuteType.FCRA,
                section="623(a)(1)",
                usc="15 U.S.C. § 1681s-2(a)(1)",
                applies_to=["collector", "debt_buyer", "furnisher"],
                title="Duty to provide accurate information",
            ),
        ],
    ),

    "unverified_debt_reporting": ViolationStatutes(
        primary=StatuteCitation(
            statute_type=StatuteType.FDCPA,
            section="1692e(8)",
            usc="15 U.S.C. § 1692e(8)",
            applies_to=["collector", "debt_buyer"],
            title="Communicating false credit information",
            description="Reporting credit information known or should be known to be false",
        ),
        secondary=[
            StatuteCitation(
                statute_type=StatuteType.FCRA,
                section="623(a)(1)",
                usc="15 U.S.C. § 1681s-2(a)(1)",
                applies_to=["collector", "debt_buyer", "furnisher"],
                title="Duty to provide accurate information",
            ),
        ],
    ),

    "duplicate_collection": ViolationStatutes(
        primary=StatuteCitation(
            statute_type=StatuteType.FDCPA,
            section="1692e(2)(A)",
            usc="15 U.S.C. § 1692e(2)(A)",
            applies_to=["collector", "debt_buyer"],
            title="False representation of debt character",
            description="Same debt reported by multiple collectors",
        ),
        secondary=[
            StatuteCitation(
                statute_type=StatuteType.FCRA,
                section="607(b)",
                usc="15 U.S.C. § 1681e(b)",
                applies_to=["bureau"],
                title="Maximum possible accuracy",
            ),
        ],
    ),

    # =========================================================================
    # TEMPORAL VIOLATIONS (FCRA Primary)
    # =========================================================================
    "obsolete_account": ViolationStatutes(
        primary=StatuteCitation(
            statute_type=StatuteType.FCRA,
            section="605(a)",
            usc="15 U.S.C. § 1681c(a)",
            applies_to=["bureau", "furnisher", "collector", "original_creditor"],
            title="Obsolete information",
            description="Information cannot be reported beyond 7 years (10 for bankruptcy)",
        ),
    ),

    "outdated_information": ViolationStatutes(
        primary=StatuteCitation(
            statute_type=StatuteType.FCRA,
            section="605(a)",
            usc="15 U.S.C. § 1681c(a)",
            applies_to=["bureau", "furnisher", "collector", "original_creditor"],
            title="Obsolete information",
        ),
    ),

    "stale_reporting": ViolationStatutes(
        primary=StatuteCitation(
            statute_type=StatuteType.FCRA,
            section="611(a)",
            usc="15 U.S.C. § 1681i(a)",
            applies_to=["bureau", "furnisher", "collector", "original_creditor"],
            title="Reinvestigation required",
            description="Account not updated in over 308 days",
        ),
    ),

    "re_aging": ViolationStatutes(
        primary=StatuteCitation(
            statute_type=StatuteType.FCRA,
            section="623(a)(1)",
            usc="15 U.S.C. § 1681s-2(a)(1)",
            applies_to=["furnisher", "collector", "original_creditor"],
            title="Prohibition on reporting inaccurate information",
            description="Manipulating dates to extend reporting period",
        ),
        secondary=[
            StatuteCitation(
                statute_type=StatuteType.FDCPA,
                section="1692e(2)(A)",
                usc="15 U.S.C. § 1692e(2)(A)",
                applies_to=["collector", "debt_buyer"],
                title="False representation of legal status",
            ),
        ],
    ),

    "dofd_replaced_with_date_opened": ViolationStatutes(
        primary=StatuteCitation(
            statute_type=StatuteType.FCRA,
            section="623(a)(1)",
            usc="15 U.S.C. § 1681s-2(a)(1)",
            applies_to=["furnisher", "collector", "original_creditor"],
            title="Prohibition on reporting inaccurate information",
        ),
    ),

    "impossible_timeline": ViolationStatutes(
        primary=StatuteCitation(
            statute_type=StatuteType.FCRA,
            section="623(a)(1)",
            usc="15 U.S.C. § 1681s-2(a)(1)",
            applies_to=["furnisher", "collector", "original_creditor"],
            title="Prohibition on reporting inaccurate information",
        ),
    ),

    # =========================================================================
    # ACCURACY VIOLATIONS (FCRA Primary)
    # =========================================================================
    "inaccurate_balance": ViolationStatutes(
        primary=StatuteCitation(
            statute_type=StatuteType.FCRA,
            section="623(a)(1)",
            usc="15 U.S.C. § 1681s-2(a)(1)",
            applies_to=["furnisher", "collector", "original_creditor"],
            title="Prohibition on reporting inaccurate information",
        ),
        secondary=[
            StatuteCitation(
                statute_type=StatuteType.FDCPA,
                section="1692f(1)",
                usc="15 U.S.C. § 1692f(1)",
                applies_to=["collector", "debt_buyer"],
                title="Collection of unauthorized amounts",
            ),
        ],
    ),

    "incorrect_payment_status": ViolationStatutes(
        primary=StatuteCitation(
            statute_type=StatuteType.FCRA,
            section="623(a)(1)",
            usc="15 U.S.C. § 1681s-2(a)(1)",
            applies_to=["furnisher", "collector", "original_creditor"],
            title="Prohibition on reporting inaccurate information",
        ),
    ),

    "wrong_account_status": ViolationStatutes(
        primary=StatuteCitation(
            statute_type=StatuteType.FCRA,
            section="623(a)(1)",
            usc="15 U.S.C. § 1681s-2(a)(1)",
            applies_to=["furnisher", "collector", "original_creditor"],
            title="Prohibition on reporting inaccurate information",
        ),
    ),

    "incorrect_dates": ViolationStatutes(
        primary=StatuteCitation(
            statute_type=StatuteType.FCRA,
            section="623(a)(2)",
            usc="15 U.S.C. § 1681s-2(a)(2)",
            applies_to=["furnisher", "collector", "original_creditor"],
            title="Duty to correct and update information",
        ),
    ),

    "missing_payment_history": ViolationStatutes(
        primary=StatuteCitation(
            statute_type=StatuteType.FCRA,
            section="611(a)",
            usc="15 U.S.C. § 1681i(a)",
            applies_to=["bureau", "furnisher"],
            title="Reinvestigation required",
        ),
    ),

    "duplicate_account": ViolationStatutes(
        primary=StatuteCitation(
            statute_type=StatuteType.FCRA,
            section="607(b)",
            usc="15 U.S.C. § 1681e(b)",
            applies_to=["bureau"],
            title="Maximum possible accuracy",
        ),
    ),

    "wrong_creditor_name": ViolationStatutes(
        primary=StatuteCitation(
            statute_type=StatuteType.FCRA,
            section="609(a)(1)",
            usc="15 U.S.C. § 1681g(a)(1)",
            applies_to=["bureau"],
            title="File contents disclosure",
        ),
    ),

    "incorrect_high_credit": ViolationStatutes(
        primary=StatuteCitation(
            statute_type=StatuteType.FCRA,
            section="623(a)(1)",
            usc="15 U.S.C. § 1681s-2(a)(1)",
            applies_to=["furnisher", "collector", "original_creditor"],
            title="Prohibition on reporting inaccurate information",
        ),
    ),

    "wrong_credit_limit": ViolationStatutes(
        primary=StatuteCitation(
            statute_type=StatuteType.FCRA,
            section="623(a)(1)",
            usc="15 U.S.C. § 1681s-2(a)(1)",
            applies_to=["furnisher", "collector", "original_creditor"],
            title="Prohibition on reporting inaccurate information",
        ),
    ),

    "payment_history_error": ViolationStatutes(
        primary=StatuteCitation(
            statute_type=StatuteType.FCRA,
            section="623(a)(1)",
            usc="15 U.S.C. § 1681s-2(a)(1)",
            applies_to=["furnisher", "collector", "original_creditor"],
            title="Prohibition on reporting inaccurate information",
        ),
    ),

    "incorrect_account_type": ViolationStatutes(
        primary=StatuteCitation(
            statute_type=StatuteType.FCRA,
            section="607(b)",
            usc="15 U.S.C. § 1681e(b)",
            applies_to=["bureau"],
            title="Maximum possible accuracy",
        ),
    ),

    "mixed_file": ViolationStatutes(
        primary=StatuteCitation(
            statute_type=StatuteType.FCRA,
            section="607(b)",
            usc="15 U.S.C. § 1681e(b)",
            applies_to=["bureau"],
            title="Maximum possible accuracy",
        ),
    ),

    "identity_error": ViolationStatutes(
        primary=StatuteCitation(
            statute_type=StatuteType.FCRA,
            section="607(b)",
            usc="15 U.S.C. § 1681e(b)",
            applies_to=["bureau"],
            title="Maximum possible accuracy",
        ),
    ),

    "balance_discrepancy": ViolationStatutes(
        primary=StatuteCitation(
            statute_type=StatuteType.FCRA,
            section="623(a)(1)",
            usc="15 U.S.C. § 1681s-2(a)(1)",
            applies_to=["furnisher", "collector", "original_creditor"],
            title="Prohibition on reporting inaccurate information",
        ),
    ),

    "late_payment_dispute": ViolationStatutes(
        primary=StatuteCitation(
            statute_type=StatuteType.FCRA,
            section="611(a)",
            usc="15 U.S.C. § 1681i(a)",
            applies_to=["bureau", "furnisher"],
            title="Reinvestigation required",
        ),
    ),

    "charge_off_dispute": ViolationStatutes(
        primary=StatuteCitation(
            statute_type=StatuteType.FCRA,
            section="623(a)(1)",
            usc="15 U.S.C. § 1681s-2(a)(1)",
            applies_to=["furnisher", "collector", "original_creditor"],
            title="Prohibition on reporting inaccurate information",
        ),
    ),

    "collection_dispute": ViolationStatutes(
        primary=StatuteCitation(
            statute_type=StatuteType.FCRA,
            section="623(b)",
            usc="15 U.S.C. § 1681s-2(b)",
            applies_to=["furnisher", "collector"],
            title="Duties upon notice of dispute",
        ),
        secondary=[
            StatuteCitation(
                statute_type=StatuteType.FDCPA,
                section="1692e(8)",
                usc="15 U.S.C. § 1692e(8)",
                applies_to=["collector", "debt_buyer"],
                title="False credit reporting",
            ),
        ],
    ),

    "not_mine": ViolationStatutes(
        primary=StatuteCitation(
            statute_type=StatuteType.FCRA,
            section="607(b)",
            usc="15 U.S.C. § 1681e(b)",
            applies_to=["bureau"],
            title="Maximum possible accuracy",
        ),
    ),

    "fraud_alert": ViolationStatutes(
        primary=StatuteCitation(
            statute_type=StatuteType.FCRA,
            section="605",
            usc="15 U.S.C. § 1681c",
            applies_to=["bureau"],
            title="Requirements relating to information in consumer reports",
        ),
    ),

    # =========================================================================
    # METRO-2 FIELD VIOLATIONS (FCRA Primary)
    # =========================================================================
    "missing_dofd": ViolationStatutes(
        primary=StatuteCitation(
            statute_type=StatuteType.FCRA,
            section="623(a)(1)",
            usc="15 U.S.C. § 1681s-2(a)(1)",
            applies_to=["furnisher", "collector", "original_creditor"],
            title="Prohibition on reporting inaccurate information",
        ),
    ),

    "missing_date_opened": ViolationStatutes(
        primary=StatuteCitation(
            statute_type=StatuteType.FCRA,
            section="623(a)(1)",
            usc="15 U.S.C. § 1681s-2(a)(1)",
            applies_to=["furnisher", "collector", "original_creditor"],
            title="Prohibition on reporting inaccurate information",
        ),
    ),

    "missing_date_reported": ViolationStatutes(
        primary=StatuteCitation(
            statute_type=StatuteType.FCRA,
            section="623(a)(2)",
            usc="15 U.S.C. § 1681s-2(a)(2)",
            applies_to=["furnisher", "collector", "original_creditor"],
            title="Duty to correct and update information",
        ),
    ),

    "missing_high_credit": ViolationStatutes(
        primary=StatuteCitation(
            statute_type=StatuteType.FCRA,
            section="623(a)(1)",
            usc="15 U.S.C. § 1681s-2(a)(1)",
            applies_to=["furnisher", "collector", "original_creditor"],
            title="Prohibition on reporting inaccurate information",
        ),
    ),

    "missing_credit_limit": ViolationStatutes(
        primary=StatuteCitation(
            statute_type=StatuteType.FCRA,
            section="623(a)(1)",
            usc="15 U.S.C. § 1681s-2(a)(1)",
            applies_to=["furnisher", "collector", "original_creditor"],
            title="Prohibition on reporting inaccurate information",
        ),
    ),

    "missing_terms": ViolationStatutes(
        primary=StatuteCitation(
            statute_type=StatuteType.FCRA,
            section="607(b)",
            usc="15 U.S.C. § 1681e(b)",
            applies_to=["bureau"],
            title="Maximum possible accuracy",
        ),
    ),

    "missing_account_type": ViolationStatutes(
        primary=StatuteCitation(
            statute_type=StatuteType.FCRA,
            section="607(b)",
            usc="15 U.S.C. § 1681e(b)",
            applies_to=["bureau"],
            title="Maximum possible accuracy",
        ),
    ),

    "missing_payment_status": ViolationStatutes(
        primary=StatuteCitation(
            statute_type=StatuteType.FCRA,
            section="623(a)(1)",
            usc="15 U.S.C. § 1681s-2(a)(1)",
            applies_to=["furnisher", "collector", "original_creditor"],
            title="Prohibition on reporting inaccurate information",
        ),
    ),

    "missing_current_balance": ViolationStatutes(
        primary=StatuteCitation(
            statute_type=StatuteType.FCRA,
            section="623(a)(1)",
            usc="15 U.S.C. § 1681s-2(a)(1)",
            applies_to=["furnisher", "collector", "original_creditor"],
            title="Prohibition on reporting inaccurate information",
        ),
    ),

    "missing_scheduled_payment": ViolationStatutes(
        primary=StatuteCitation(
            statute_type=StatuteType.FCRA,
            section="623(a)(1)",
            usc="15 U.S.C. § 1681s-2(a)(1)",
            applies_to=["furnisher", "collector", "original_creditor"],
            title="Prohibition on reporting inaccurate information",
        ),
    ),

    # =========================================================================
    # REINVESTIGATION VIOLATIONS (FCRA Primary)
    # =========================================================================
    "reinsertion": ViolationStatutes(
        primary=StatuteCitation(
            statute_type=StatuteType.FCRA,
            section="611(a)(5)",
            usc="15 U.S.C. § 1681i(a)(5)",
            applies_to=["bureau"],
            title="Deletion of information",
        ),
    ),

    "failure_to_investigate": ViolationStatutes(
        primary=StatuteCitation(
            statute_type=StatuteType.FCRA,
            section="611(a)(1)",
            usc="15 U.S.C. § 1681i(a)(1)",
            applies_to=["bureau"],
            title="Reinvestigation required",
        ),
    ),

    "incomplete_investigation": ViolationStatutes(
        primary=StatuteCitation(
            statute_type=StatuteType.FCRA,
            section="611(a)(1)",
            usc="15 U.S.C. § 1681i(a)(1)",
            applies_to=["bureau"],
            title="Reinvestigation required",
        ),
    ),

    "unverifiable_information": ViolationStatutes(
        primary=StatuteCitation(
            statute_type=StatuteType.FCRA,
            section="611(a)(5)",
            usc="15 U.S.C. § 1681i(a)(5)",
            applies_to=["bureau"],
            title="Deletion of information",
        ),
    ),

    # =========================================================================
    # ECOA VIOLATIONS (Limited Support)
    # =========================================================================
    "ecoa_code_error": ViolationStatutes(
        primary=StatuteCitation(
            statute_type=StatuteType.ECOA,
            section="1691",
            usc="15 U.S.C. § 1691",
            applies_to=["furnisher", "original_creditor"],
            title="Equal Credit Opportunity",
            description="Metro 2 Field 37 (ECOA Code) error",
        ),
        secondary=[
            StatuteCitation(
                statute_type=StatuteType.FCRA,
                section="623(a)(1)",
                usc="15 U.S.C. § 1681s-2(a)(1)",
                applies_to=["furnisher", "original_creditor"],
                title="Prohibition on reporting inaccurate information",
            ),
        ],
    ),

    # =========================================================================
    # TIER 2: RESPONSE-LAYER VIOLATIONS
    # Created when entity responses fail examiner standards
    # =========================================================================
    "perfunctory_investigation": ViolationStatutes(
        primary=StatuteCitation(
            statute_type=StatuteType.FCRA,
            section="611(a)(1)(A)",
            usc="15 U.S.C. § 1681i(a)(1)(A)",
            applies_to=["bureau", "furnisher"],
            title="Failure to conduct reasonable investigation",
            description="Entity verified disputed information despite provable factual impossibilities",
        ),
        secondary=[
            StatuteCitation(
                statute_type=StatuteType.FCRA,
                section="616",
                usc="15 U.S.C. § 1681n",
                applies_to=["bureau", "furnisher"],
                title="Willful noncompliance",
                description="Willful failure to conduct reasonable reinvestigation",
            ),
        ],
    ),

    "notice_of_results_failure": ViolationStatutes(
        primary=StatuteCitation(
            statute_type=StatuteType.FCRA,
            section="611(a)(6)(A)",
            usc="15 U.S.C. § 1681i(a)(6)(A)",
            applies_to=["bureau"],
            title="Failure to provide notice of results",
            description="Entity failed to provide investigation results within statutory deadline",
        ),
        secondary=[
            StatuteCitation(
                statute_type=StatuteType.FCRA,
                section="623(b)(1)",
                usc="15 U.S.C. § 1681s-2(b)(1)",
                applies_to=["furnisher"],
                title="Duties upon notice of dispute",
                description="Furnisher failed to investigate within 30 days of notice",
            ),
        ],
    ),

    "systemic_accuracy_failure": ViolationStatutes(
        primary=StatuteCitation(
            statute_type=StatuteType.FCRA,
            section="607(b)",
            usc="15 U.S.C. § 1681e(b)",
            applies_to=["bureau"],
            title="Maximum possible accuracy",
            description="Same contradiction verified across multiple bureaus in single dispute cycle",
        ),
        secondary=[
            StatuteCitation(
                statute_type=StatuteType.FCRA,
                section="623(a)(1)",
                usc="15 U.S.C. § 1681s-2(a)(1)",
                applies_to=["furnisher"],
                title="Prohibition on reporting inaccurate information",
            ),
        ],
    ),

    "udaap_misleading_verification": ViolationStatutes(
        primary=StatuteCitation(
            statute_type=StatuteType.FCRA,
            section="611(a)(1)(A)",
            usc="15 U.S.C. § 1681i(a)(1)(A)",
            applies_to=["bureau", "furnisher"],
            title="Misleading verification response",
            description="Verification of CRITICAL logical impossibilities creates misleading impression",
        ),
        flag_only=[
            StatuteCitation(
                statute_type=StatuteType.STATE,
                section="UDAAP",
                usc="12 U.S.C. § 5536",
                applies_to=["bureau", "furnisher"],
                title="Unfair, Deceptive, or Abusive Acts or Practices",
                description="Verification may constitute deceptive practice under CFPB authority",
                consumer_facing=False,
            ),
        ],
    ),
}


def get_violation_statutes(violation_type: str) -> Optional[ViolationStatutes]:
    """
    Get the statute mapping for a violation type.

    Args:
        violation_type: The violation type identifier

    Returns:
        ViolationStatutes object or None if not found
    """
    return VIOLATION_STATUTE_MAP.get(violation_type)


def get_primary_statute(violation_type: str, actor: str) -> Optional[str]:
    """
    Get the primary USC citation for a violation and actor.

    Args:
        violation_type: The violation type identifier
        actor: The actor type (collector, furnisher, bureau, etc.)

    Returns:
        USC citation string or None
    """
    statutes = get_violation_statutes(violation_type)
    if not statutes:
        return None

    citation = statutes.get_primary_for_actor(actor)
    return citation.usc if citation else None


def get_all_applicable_statutes(
    violation_type: str,
    actor: str
) -> Dict[str, Any]:
    """
    Get all applicable statutes for a violation and actor.

    Args:
        violation_type: The violation type identifier
        actor: The actor type

    Returns:
        Dictionary with primary and secondary citations
    """
    statutes = get_violation_statutes(violation_type)
    if not statutes:
        return {"primary": None, "secondary": []}

    citations = statutes.get_applicable_citations(actor)

    if not citations:
        return {"primary": None, "secondary": []}

    primary = citations[0]
    secondary = [c.usc for c in citations[1:]] if len(citations) > 1 else []

    return {
        "primary": primary.usc,
        "primary_type": primary.statute_type.value,
        "primary_section": primary.section,
        "secondary": secondary,
    }


def map_furnisher_type_to_actor(furnisher_type: str) -> str:
    """
    Map FurnisherType enum values to actor strings.

    Args:
        furnisher_type: FurnisherType value (collector, oc_chargeoff, etc.)

    Returns:
        Actor string for statute routing
    """
    mapping = {
        "collector": "collector",
        "debt_buyer": "debt_buyer",
        "oc_chargeoff": "furnisher",  # Treated as furnisher unless sold
        "oc_non_chargeoff": "original_creditor",
        "unknown": "furnisher",
    }
    return mapping.get(furnisher_type.lower(), "furnisher")


# Legacy compatibility - deprecated
def get_violation_fcra_section(violation_type: str) -> str:
    """
    DEPRECATED: Use get_primary_statute() instead.

    Get the FCRA section for a violation type (legacy compatibility).
    """
    warnings.warn(
        "get_violation_fcra_section() is deprecated. Use get_primary_statute() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    statutes = get_violation_statutes(violation_type)
    if statutes and statutes.primary:
        # Return just the section number for legacy compatibility
        return statutes.primary.section
    return "611"  # Default fallback
