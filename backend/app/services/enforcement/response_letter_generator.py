"""
Credit Engine 2.0 - Response Letter Generator
Generates formal FCRA enforcement correspondence based on dispute responses.

ROLE: U.S. consumer credit compliance enforcement engine.
- Does NOT provide advice
- Generates formal regulatory correspondence asserting violations
- Cites statutes in canonical USC format only
- Treats all violations as assertions unless explicitly marked "resolved"
- Assumes recipient is legally sophisticated

Phase 2 Integration:
- VERIFIED and REJECTED letters support contradiction-first narratives
- Contradictions appear in "PROVABLE FACTUAL INACCURACIES" section after header
- NO_RESPONSE, REINSERTION, DELETED remain unchanged
"""

from datetime import datetime
from typing import Dict, List, Optional, Any, TYPE_CHECKING
from uuid import UUID
import textwrap

# Type hint for Contradiction without creating import dependency
if TYPE_CHECKING:
    from ..audit.contradiction_engine import Contradiction


# Canonical entity names (legal names for correspondence)
CANONICAL_ENTITY_NAMES = {
    # CRAs
    "transunion": "TransUnion LLC",
    "trans union": "TransUnion LLC",
    "tu": "TransUnion LLC",
    "equifax": "Equifax Inc.",
    "eq": "Equifax Inc.",
    "experian": "Experian LLC",
    "ex": "Experian LLC",
    "exp": "Experian LLC",
}


def canonicalize_entity_name(name: str) -> str:
    """
    Convert entity name to canonical legal name.

    Examples:
        "TransUnion" -> "TransUnion LLC"
        "transunion" -> "TransUnion LLC"
        "EQUIFAX" -> "Equifax Inc."
    """
    if not name:
        return name
    lookup = name.lower().strip()
    return CANONICAL_ENTITY_NAMES.get(lookup, name)


# Violation type to statute auto-assignment
# Maps violation types to their primary FCRA statute when not explicitly set
VIOLATION_STATUTE_DEFAULTS = {
    # Missing field violations -> §1681e(b) accuracy requirement
    "missing_dofd": "15 U.S.C. § 1681e(b)",
    "missing_date_opened": "15 U.S.C. § 1681e(b)",
    "missing_dla": "15 U.S.C. § 1681e(b)",
    "missing_payment_status": "15 U.S.C. § 1681e(b)",
    "missing_original_creditor": "15 U.S.C. § 1681e(b)",
    "missing_scheduled_payment": "15 U.S.C. § 1681e(b)",
    # Balance/amount violations -> §1681e(b)
    "negative_balance": "15 U.S.C. § 1681e(b)",
    "past_due_exceeds_balance": "15 U.S.C. § 1681e(b)",
    "balance_exceeds_high_credit": "15 U.S.C. § 1681e(b)",
    "balance_exceeds_credit_limit": "15 U.S.C. § 1681e(b)",
    # Date violations -> §1681e(b)
    "future_date": "15 U.S.C. § 1681e(b)",
    "dofd_after_date_opened": "15 U.S.C. § 1681e(b)",
    # Cross-bureau mismatches -> §1681e(b)
    "dofd_mismatch": "15 U.S.C. § 1681e(b)",
    "balance_mismatch": "15 U.S.C. § 1681e(b)",
    "status_mismatch": "15 U.S.C. § 1681e(b)",
    # Temporal violations -> §1681c(a) obsolescence
    "stale_reporting": "15 U.S.C. § 1681c(a)",
    "re_aging": "15 U.S.C. § 1681c(a)",
    "obsolete_account": "15 U.S.C. § 1681c(a)",
    # Default fallback
    "default": "15 U.S.C. § 1681e(b)",
}


def get_statute_for_violation(violation_type: str, explicit_statute: str = None) -> str:
    """
    Get the appropriate statute for a violation type.

    Uses explicit statute if provided and non-empty, otherwise auto-assigns
    based on violation type.
    """
    if explicit_statute and explicit_statute.strip():
        return explicit_statute

    v_type = violation_type.lower().replace(" ", "_") if violation_type else ""
    return VIOLATION_STATUTE_DEFAULTS.get(v_type, VIOLATION_STATUTE_DEFAULTS["default"])


# Canonical statute citations
STATUTE_CITATIONS = {
    # FCRA - Credit Reporting Agency (CRA) obligations
    "fcra_611_a_1_A": "15 U.S.C. § 1681i(a)(1)(A)",
    "fcra_611_a_5_B": "15 U.S.C. § 1681i(a)(5)(B)",
    "fcra_611_a_3": "15 U.S.C. § 1681i(a)(3)",
    "fcra_611_a_3_A": "15 U.S.C. § 1681i(a)(3)(A)",
    "fcra_611_a_3_B": "15 U.S.C. § 1681i(a)(3)(B)",
    "fcra_605_a": "15 U.S.C. § 1681c(a)",
    "fcra_616": "15 U.S.C. § 1681n",
    "fcra_617": "15 U.S.C. § 1681o",
    "fcra_623_b_1": "15 U.S.C. § 1681s-2(b)(1)",
    "fcra_623_b_1_A": "15 U.S.C. § 1681s-2(b)(1)(A)",

    # FDCPA - Debt Collector obligations
    "fdcpa_1692g_b": "15 U.S.C. § 1692g(b)",
    "fdcpa_1692e": "15 U.S.C. § 1692e",
    "fdcpa_1692e_2_A": "15 U.S.C. § 1692e(2)(A)",
    "fdcpa_1692e_5": "15 U.S.C. § 1692e(5)",
    "fdcpa_1692e_8": "15 U.S.C. § 1692e(8)",
    "fdcpa_1692f": "15 U.S.C. § 1692f",
    "fdcpa_1692k": "15 U.S.C. § 1692k",
}

# Response type to violation mapping for letter context
RESPONSE_VIOLATION_MAP = {
    "NO_RESPONSE": {
        "CRA": {
            "violation": "failure_to_investigate_within_30_days",
            "statute": "fcra_611_a_1_A",
            "description": "Failed to conduct investigation and provide results within 30 days"
        },
        "FURNISHER": {
            "violation": "failure_to_investigate_notice_of_dispute",
            "statute": "fcra_623_b_1_A",
            "description": "Failed to investigate notice of dispute from CRA"
        },
        "COLLECTOR": {
            "violation": "failure_to_provide_validation",
            "statute": "fdcpa_1692g_b",
            "description": "Failed to provide validation of debt"
        }
    },
    "VERIFIED": {
        "CRA": {
            "violation": "failure_to_conduct_reasonable_investigation",
            "statute": "fcra_611_a_1_A",
            "description": "Verified disputed information without conducting reasonable investigation"
        },
        "FURNISHER": {
            "violation": "failure_to_investigate",
            "statute": "fcra_623_b_1",
            "description": "Failed to conduct proper investigation upon notice of dispute"
        },
        "COLLECTOR": {
            "violation": "continued_collection_during_dispute",
            "statute": "fdcpa_1692g_b",
            "description": "Continued collection activity during dispute period"
        }
    },
    "REJECTED": {
        "CRA": {
            "violation": "invalid_frivolous_determination",
            "statute": "fcra_611_a_3",
            "description": "Improperly determined dispute to be frivolous or irrelevant"
        }
    },
    "REINSERTION_NO_NOTICE": {
        "CRA": {
            "violation": "reinsertion_without_notice",
            "statute": "fcra_611_a_5_B",
            "description": "Reinserted previously deleted information without required 5-day advance notice"
        }
    }
}


TEST_FOOTER = """
════════════════════════════════════════════════════════════════════════════════
                         TEST DOCUMENT – NOT MAILED
════════════════════════════════════════════════════════════════════════════════
This letter was generated in test mode for preview purposes only.
Do not mail, save to production records, or use for escalation.
════════════════════════════════════════════════════════════════════════════════
"""


# =============================================================================
# PHASE 2: CONTRADICTION NARRATIVE FORMATTER
# =============================================================================

# Severity display order (CRITICAL first)
SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def format_contradiction_section(contradictions: List[Any]) -> Optional[str]:
    """
    Format contradictions into "PROVABLE FACTUAL INACCURACIES" section.

    Args:
        contradictions: List of Contradiction objects or dicts with fields:
            - type, severity, description, impact, proof_hint (optional)

    Returns:
        Formatted section string, or None if no contradictions
    """
    if not contradictions:
        return None

    # Sort by severity (CRITICAL → HIGH → MEDIUM → LOW)
    def get_severity_key(c):
        if hasattr(c, 'severity'):
            sev = c.severity.value if hasattr(c.severity, 'value') else str(c.severity)
        elif isinstance(c, dict):
            sev = c.get('severity', 'low')
            sev = sev.value if hasattr(sev, 'value') else str(sev)
        else:
            sev = 'low'
        return SEVERITY_ORDER.get(sev.lower(), 99)

    sorted_contradictions = sorted(contradictions, key=get_severity_key)

    section = f"""PROVABLE FACTUAL INACCURACIES
{'=' * 50}

The following data elements reported by the furnisher are factually impossible and cannot be verified because they are demonstrably false:
"""

    for i, c in enumerate(sorted_contradictions, 1):
        # Extract fields (support both Contradiction objects and dicts)
        if hasattr(c, 'description'):
            # Contradiction dataclass
            severity = c.severity.value if hasattr(c.severity, 'value') else str(c.severity)
            description = c.description
            impact = c.impact
            proof_hint = getattr(c, 'proof_hint', None)
            rule_code = getattr(c, 'rule_code', None)
            bureau_claim = getattr(c, 'bureau_claim', None)
            contradiction = getattr(c, 'contradiction', None)
        else:
            # Dict format
            severity = c.get('severity', 'MEDIUM')
            severity = severity.value if hasattr(severity, 'value') else str(severity)
            description = c.get('description', '')
            impact = c.get('impact', '')
            proof_hint = c.get('proof_hint')
            rule_code = c.get('rule_code')
            bureau_claim = c.get('bureau_claim')
            contradiction = c.get('contradiction')

        severity_upper = severity.upper()

        section += f"\n{i}. [{severity_upper}] {description}"

        # Add bureau claim vs contradiction if available (facts first)
        if bureau_claim and contradiction:
            section += f"\n   • Reported: {bureau_claim}"
            section += f"\n   • Actual: {contradiction}"

        # Add impact
        if impact:
            section += f"\n   • Impact: {impact}"

        # Add proof hint if present (optional)
        if proof_hint:
            section += f"\n   • Evidence: {proof_hint}"

    section += f"""

These inaccuracies are not matters of interpretation or opinion. They represent mathematical or temporal impossibilities that cannot be verified through any reasonable investigation because they are objectively false."""

    return section


# =============================================================================
# PHASE 3: DETERMINISTIC DEMAND PRIORITIZATION
# =============================================================================

class PrimaryRemedy:
    """Primary remedy types determined by contradiction severity."""
    IMMEDIATE_DELETION = "IMMEDIATE_DELETION"
    CORRECTION_WITH_DOCUMENTATION = "CORRECTION_WITH_DOCUMENTATION"
    STANDARD_PROCEDURAL = "STANDARD_PROCEDURAL"


def determine_primary_remedy(contradictions: Optional[List[Any]]) -> str:
    """
    Determine primary remedy based on contradiction severity.

    Rules (deterministic):
    1. If any contradiction has severity = CRITICAL → IMMEDIATE DELETION
    2. Else if 2+ contradictions have severity = HIGH → IMMEDIATE DELETION
    3. Else if 1 HIGH or any MEDIUM contradictions exist → CORRECTION WITH DOCUMENTATION
    4. Else → Fall back to standard procedural/statutory demands

    Args:
        contradictions: List of Contradiction objects or dicts

    Returns:
        PrimaryRemedy constant string
    """
    if not contradictions:
        return PrimaryRemedy.STANDARD_PROCEDURAL

    # Count by severity
    critical_count = 0
    high_count = 0
    medium_count = 0

    for c in contradictions:
        # Extract severity (support both Contradiction objects and dicts)
        if hasattr(c, 'severity'):
            sev = c.severity.value if hasattr(c.severity, 'value') else str(c.severity)
        elif isinstance(c, dict):
            sev = c.get('severity', 'low')
            sev = sev.value if hasattr(sev, 'value') else str(sev)
        else:
            sev = 'low'

        sev_lower = sev.lower()

        if sev_lower == 'critical':
            critical_count += 1
        elif sev_lower == 'high':
            high_count += 1
        elif sev_lower == 'medium':
            medium_count += 1

    # Apply deterministic rules
    # Rule 1: Any CRITICAL → IMMEDIATE DELETION
    if critical_count > 0:
        return PrimaryRemedy.IMMEDIATE_DELETION

    # Rule 2: 2+ HIGH → IMMEDIATE DELETION
    if high_count >= 2:
        return PrimaryRemedy.IMMEDIATE_DELETION

    # Rule 3: 1 HIGH or any MEDIUM → CORRECTION WITH DOCUMENTATION
    if high_count >= 1 or medium_count >= 1:
        return PrimaryRemedy.CORRECTION_WITH_DOCUMENTATION

    # Rule 4: Fallback
    return PrimaryRemedy.STANDARD_PROCEDURAL


def generate_demanded_actions(
    primary_remedy: str,
    entity_name: str,
    response_type: str = "VERIFIED",
) -> List[str]:
    """
    Generate demanded actions ordered by primary remedy.

    Args:
        primary_remedy: PrimaryRemedy constant
        entity_name: Canonical entity name for letter
        response_type: VERIFIED or REJECTED

    Returns:
        List of demanded action strings, ordered by priority
    """
    actions = []

    if primary_remedy == PrimaryRemedy.IMMEDIATE_DELETION:
        # Lead with deletion demand - no ambiguity
        actions.append(
            f"IMMEDIATE DELETION of the disputed tradeline(s) from {entity_name}'s consumer file. "
            f"The factual impossibilities documented herein cannot be corrected because they are "
            f"demonstrably false. Under 15 U.S.C. § 1681e(b), information that cannot be verified "
            f"as accurate must be deleted."
        )
        actions.append(
            "Written confirmation of deletion sent to consumer within five (5) business days"
        )
        actions.append(
            "Notification to all parties who received consumer reports containing the disputed "
            "information within the preceding six (6) months"
        )
        # Secondary demands
        if response_type == "VERIFIED":
            actions.append(
                "Disclosure of the purported verification method, if any was actually conducted"
            )
        elif response_type == "REJECTED":
            actions.append(
                "Withdrawal of the frivolous/irrelevant determination"
            )

    elif primary_remedy == PrimaryRemedy.CORRECTION_WITH_DOCUMENTATION:
        # Lead with correction demand + documentation requirement
        actions.append(
            "Immediate correction of the inaccurate data elements identified herein, with "
            "supporting documentation demonstrating the corrected information is complete and accurate"
        )
        actions.append(
            f"Production of all documents relied upon by {entity_name} in reporting the disputed information"
        )
        actions.append(
            "Identification of the furnisher(s) contacted and date(s) of contact during any investigation"
        )
        if response_type == "VERIFIED":
            actions.append(
                "Disclosure of the method of verification used for each disputed item"
            )
            actions.append(
                "Written results of reinvestigation within fifteen (15) days"
            )
        elif response_type == "REJECTED":
            actions.append(
                "Withdrawal of the frivolous/irrelevant determination and immediate investigation "
                "of the disputed items in compliance with 15 U.S.C. § 1681i(a)(1)(A)"
            )
            actions.append(
                "Written results of investigation within thirty (30) days of original dispute submission"
            )

    else:
        # Standard procedural demands (fallback - no contradictions)
        if response_type == "VERIFIED":
            actions = [
                "Disclosure of the method of verification used for each disputed item",
                "Production of all documents relied upon in the purported verification",
                "Identification of the furnisher(s) contacted and date(s) of contact",
                "Immediate reinvestigation using procedures that constitute a reasonable investigation",
                "Written results of reinvestigation within fifteen (15) days",
            ]
        elif response_type == "REJECTED":
            actions = [
                "Withdrawal of the frivolous/irrelevant determination",
                "Immediate investigation of the disputed items in compliance with 15 U.S.C. § 1681i(a)(1)(A)",
                "Written results of investigation within thirty (30) days of original dispute submission",
                "If maintaining frivolous determination: Written notice identifying SPECIFIC information "
                "required to investigate, as mandated by § 1681i(a)(3)(B)(ii)",
            ]

    return actions


def format_demanded_actions_section(actions: List[str]) -> str:
    """
    Format demanded actions into letter section.

    Args:
        actions: List of action strings

    Returns:
        Formatted section string
    """
    section = f"""DEMANDED ACTIONS
{'-' * 50}

The following actions are demanded within fifteen (15) days of receipt of this notice:
"""

    for i, action in enumerate(actions, 1):
        section += f"\n\n{i}. {action}"

    return section


class ResponseLetterGenerator:
    """
    Generates formal FCRA enforcement letters based on dispute responses.
    """

    def __init__(self, test_context: bool = False):
        self.generated_at = datetime.now()
        self.test_context = test_context

    def generate_enforcement_letter(
        self,
        consumer: Dict[str, str],
        entity_type: str,
        entity_name: str,
        violations: List[Dict[str, Any]],
        demanded_actions: List[str],
        dispute_date: Optional[datetime] = None,
        response_date: Optional[datetime] = None,
        response_type: Optional[str] = None,
        deadline_date: Optional[datetime] = None,
        include_willful_notice: bool = False
    ) -> str:
        """
        Generate a formal enforcement letter.

        Args:
            consumer: Dict with 'name' and 'address' keys
            entity_type: CRA, FURNISHER, or COLLECTOR
            entity_name: Name of the entity (e.g., "TransUnion")
            violations: List of violation dicts with type, statute, facts
            demanded_actions: List of demanded remedial actions
            dispute_date: Date original dispute was sent
            response_date: Date response was received (if any)
            response_type: Type of response (NO_RESPONSE, VERIFIED, etc.)
            deadline_date: Statutory deadline date
            include_willful_notice: Include willful noncompliance notice (§616)

        Returns:
            Formatted letter as string
        """
        letter_parts = []

        # Header
        letter_parts.append(self._generate_header(consumer, entity_name))

        # Subject line
        letter_parts.append(self._generate_subject_line(entity_type, response_type))

        # Opening paragraph
        letter_parts.append(self._generate_opening(
            consumer, entity_type, entity_name, dispute_date, response_type
        ))

        # Violation assertions
        letter_parts.append(self._generate_violation_section(violations, entity_type))

        # Timeline facts (if applicable)
        if dispute_date or response_date or deadline_date:
            letter_parts.append(self._generate_timeline_section(
                dispute_date, response_date, deadline_date, response_type
            ))

        # Demands section
        letter_parts.append(self._generate_demands_section(demanded_actions))

        # Willful noncompliance notice (if applicable)
        if include_willful_notice:
            letter_parts.append(self._generate_willful_notice(entity_type))

        # Closing
        letter_parts.append(self._generate_closing(consumer))

        letter = "\n\n".join(filter(None, letter_parts))

        # Append test footer if in test mode
        if self.test_context:
            letter += TEST_FOOTER

        return letter

    def _generate_header(self, consumer: Dict[str, str], entity_name: str) -> str:
        """Generate letter header with date and addresses."""
        today = datetime.now().strftime("%B %d, %Y")

        consumer_block = f"""{consumer.get('name', '[CONSUMER NAME]')}
{consumer.get('address', '[CONSUMER ADDRESS]')}"""

        return f"""{consumer_block}

{today}

{entity_name}
Consumer Dispute Department
[ADDRESS ON FILE]

Via Certified Mail, Return Receipt Requested"""

    def _generate_subject_line(self, entity_type: str, response_type: Optional[str]) -> str:
        """Generate subject line based on entity and response type."""
        if response_type == "NO_RESPONSE":
            return "RE: FORMAL NOTICE OF STATUTORY VIOLATION - Failure to Respond Within Statutory Deadline"
        elif response_type == "VERIFIED":
            return "RE: FORMAL NOTICE OF STATUTORY VIOLATION - Verification Without Reasonable Investigation"
        elif response_type == "REJECTED":
            return "RE: FORMAL NOTICE OF STATUTORY VIOLATION - Improper Frivolous/Irrelevant Determination"
        elif response_type == "REINSERTION_NO_NOTICE":
            return "RE: FORMAL NOTICE OF STATUTORY VIOLATION - Reinsertion Without Required Notice"
        else:
            return "RE: FORMAL NOTICE OF STATUTORY VIOLATIONS"

    def _generate_opening(
        self,
        consumer: Dict[str, str],
        entity_type: str,
        entity_name: str,
        dispute_date: Optional[datetime],
        response_type: Optional[str]
    ) -> str:
        """Generate opening paragraph asserting the dispute context."""
        consumer_name = consumer.get('name', 'the undersigned consumer')

        if dispute_date:
            date_str = dispute_date.strftime("%B %d, %Y")
            dispute_context = f"On {date_str}, {consumer_name} submitted a written dispute"
        else:
            dispute_context = f"{consumer_name} previously submitted a written dispute"

        entity_role = {
            "CRA": "credit reporting agency",
            "FURNISHER": "furnisher of information",
            "COLLECTOR": "debt collector"
        }.get(entity_type, "entity")

        opening = f"""{dispute_context} to {entity_name} regarding inaccurate information appearing in {consumer_name}'s consumer file.

{entity_name}, as a {entity_role} subject to the Fair Credit Reporting Act (FCRA), 15 U.S.C. § 1681 et seq."""

        if entity_type == "COLLECTOR":
            opening += " and the Fair Debt Collection Practices Act (FDCPA), 15 U.S.C. § 1692 et seq."

        opening += ", bears specific statutory obligations upon receipt of a consumer dispute."

        if response_type == "NO_RESPONSE":
            opening += f"\n\n{entity_name} has failed to satisfy these obligations."
        elif response_type == "VERIFIED":
            opening += f"\n\n{entity_name}'s verification response fails to satisfy its statutory obligations and compounds its liability."
        elif response_type == "REJECTED":
            opening += f"\n\n{entity_name}'s determination that this dispute is frivolous or irrelevant fails to comply with statutory requirements."

        return opening

    def _generate_violation_section(
        self,
        violations: List[Dict[str, Any]],
        entity_type: str
    ) -> str:
        """Generate the violations assertion section."""
        if not violations:
            return ""

        section = "STATUTORY VIOLATIONS\n" + "=" * 50

        for i, violation in enumerate(violations, 1):
            v_type = violation.get("type", "UNKNOWN")
            statute_key = violation.get("statute", "")
            statute_citation = STATUTE_CITATIONS.get(statute_key, statute_key)
            facts = violation.get("facts", [])
            account = violation.get("account", {})

            creditor = account.get("creditor", "")
            account_mask = account.get("account_mask", "")
            account_str = f" ({creditor} {account_mask})" if creditor else ""

            section += f"\n\nViolation {i}: {self._format_violation_type(v_type)}{account_str}"
            section += f"\nStatute: {statute_citation}"

            if facts:
                section += "\n\nEstablished Facts:"
                for fact in facts:
                    section += f"\n    - {fact}"

        return section

    def _format_violation_type(self, v_type: str) -> str:
        """Format violation type for display."""
        return v_type.replace("_", " ").title()

    def _generate_timeline_section(
        self,
        dispute_date: Optional[datetime],
        response_date: Optional[datetime],
        deadline_date: Optional[datetime],
        response_type: Optional[str]
    ) -> str:
        """Generate timeline section showing statutory breach."""
        section = "TIMELINE OF EVENTS\n" + "-" * 50

        if dispute_date:
            section += f"\n\nDispute Submitted: {dispute_date.strftime('%B %d, %Y')}"

        if deadline_date:
            section += f"\nStatutory Deadline: {deadline_date.strftime('%B %d, %Y')}"

        if response_type == "NO_RESPONSE":
            section += f"\nResponse Received: NONE"
            if deadline_date and datetime.now() > deadline_date:
                days_overdue = (datetime.now() - deadline_date).days
                section += f"\nDays Past Deadline: {days_overdue}"
        elif response_date:
            section += f"\nResponse Received: {response_date.strftime('%B %d, %Y')}"
            if deadline_date and response_date > deadline_date:
                days_late = (response_date - deadline_date).days
                section += f"\nDays Past Deadline: {days_late}"

        return section

    def _generate_demands_section(self, demanded_actions: List[str]) -> str:
        """Generate the demands section."""
        if not demanded_actions:
            return ""

        section = "DEMANDED ACTIONS\n" + "-" * 50
        section += "\n\nThe following actions are demanded within fifteen (15) days of receipt of this notice:"

        for i, action in enumerate(demanded_actions, 1):
            section += f"\n\n{i}. {action}"

        return section

    def _generate_willful_notice(self, entity_type: str) -> str:
        """Generate rights-preservation notice (single sentence, no damages lecture)."""
        return f"""RIGHTS PRESERVATION
{'-' * 50}

Nothing in this correspondence shall be construed as a waiver of any rights or remedies available under 15 U.S.C. §§ 1681n or 1681o for negligent or willful noncompliance."""

    def _generate_closing(self, consumer: Dict[str, str]) -> str:
        """Generate the closing and signature block (no regulatory cc at this stage)."""
        consumer_name = consumer.get('name', '[CONSUMER NAME]')

        return f"""RESPONSE REQUIRED
{'-' * 50}

A written response addressing each demanded action is required within fifteen (15) days of receipt of this notice. Failure to respond or inadequate response will be documented and may be submitted as evidence in subsequent proceedings.

All future correspondence regarding this matter should be directed to the undersigned at the address provided above.



Respectfully submitted,



____________________________________
{consumer_name}

Enclosures:
- Copy of original dispute letter
- Certified mail receipt
- Supporting documentation"""


def generate_no_response_letter(
    consumer: Dict[str, str],
    entity_type: str,
    entity_name: str,
    original_violations: List[Dict[str, Any]],
    dispute_date: datetime,
    deadline_date: datetime,
    test_context: bool = False,
) -> str:
    """
    Generate enforcement letter for NO_RESPONSE scenario.

    This is a convenience function for the most common enforcement scenario.

    Args:
        test_context: If True, appends test footer and bypasses deadline validation.
    """
    generator = ResponseLetterGenerator(test_context=test_context)

    # Build violation based on entity type
    response_violation = RESPONSE_VIOLATION_MAP.get("NO_RESPONSE", {}).get(entity_type, {})

    violations = [{
        "type": response_violation.get("violation", "failure_to_respond"),
        "statute": response_violation.get("statute", ""),
        "facts": [
            f"Written dispute submitted on {dispute_date.strftime('%B %d, %Y')}",
            f"Statutory deadline was {deadline_date.strftime('%B %d, %Y')}",
            "No response received as of the date of this letter",
            response_violation.get("description", "Failed to respond within statutory period")
        ]
    }]

    # Add original violations as context
    for v in original_violations:
        violations.append({
            "type": v.get("violation_type", v.get("type", "UNKNOWN")),
            "statute": v.get("primary_statute", v.get("statute", "")),
            "facts": [v.get("description", "Original disputed violation")],
            "account": {
                "creditor": v.get("creditor_name", ""),
                "account_mask": v.get("account_number_masked", "")
            }
        })

    demanded_actions = [
        "Immediate deletion of all disputed tradeline(s) from consumer's credit file",
        "Written confirmation of deletion sent to consumer within five (5) business days",
        "Notification to all parties who received consumer reports containing the disputed information within the preceding six (6) months"
    ]

    return generator.generate_enforcement_letter(
        consumer=consumer,
        entity_type=entity_type,
        entity_name=entity_name,
        violations=violations,
        demanded_actions=demanded_actions,
        dispute_date=dispute_date,
        deadline_date=deadline_date,
        response_type="NO_RESPONSE",
        include_willful_notice=True
    )


def generate_verified_response_letter(
    consumer: Dict[str, str],
    entity_type: str,
    entity_name: str,
    original_violations: List[Dict[str, Any]],
    dispute_date: datetime,
    response_date: datetime,
    contradictions: Optional[List[Any]] = None,
) -> str:
    """
    Generate enforcement letter for VERIFIED response scenario.

    Production-ready implementation:
    - Single statutory theory: Verification Without Reasonable Investigation (§611(a)(1)(A))
    - Canonical entity names (TransUnion LLC, Equifax Inc., Experian LLC)
    - Original violations referenced as facts, not separate violation entries
    - No damages lecture, single rights-preservation sentence
    - No regulatory cc at this stage

    Phase 2 Integration:
    - If contradictions provided, inserts PROVABLE FACTUAL INACCURACIES section after header
    - Facts first, statutes second
    - Contradictions sorted by severity (CRITICAL → HIGH → MEDIUM)
    """
    # Canonicalize entity name
    canonical_entity = canonicalize_entity_name(entity_name)

    # Build disputed items with auto-assigned statutes
    disputed_items_facts = []
    for v in original_violations:
        v_type = v.get("violation_type", v.get("type", ""))
        creditor = v.get("creditor_name", "")
        account_mask = v.get("account_number_masked", "")
        description = v.get("description", "")

        # Auto-assign statute if empty
        explicit_statute = v.get("primary_statute", v.get("statute", ""))
        statute = get_statute_for_violation(v_type, explicit_statute)

        item_desc = f"{creditor}" if creditor else "Disputed tradeline"
        if account_mask:
            item_desc += f" ({account_mask})"
        if v_type:
            item_desc += f" - {v_type.replace('_', ' ').title()}"
        if statute:
            item_desc += f" [{statute}]"

        disputed_items_facts.append(item_desc)

    # Build the letter content directly (custom structure for VERIFIED with contradictions)
    letter_parts = []

    # Header
    today = datetime.now().strftime("%B %d, %Y")
    consumer_name = consumer.get('name', '[CONSUMER NAME]')
    consumer_address = consumer.get('address', '[CONSUMER ADDRESS]')

    header = f"""{consumer_name}
{consumer_address}

{today}

{canonical_entity}
Consumer Dispute Department
[ADDRESS ON FILE]

Via Certified Mail, Return Receipt Requested"""
    letter_parts.append(header)

    # Subject line
    subject = "RE: FORMAL NOTICE OF STATUTORY VIOLATION - Verification Without Reasonable Investigation"
    letter_parts.append(subject)

    # PHASE 2: Insert PROVABLE FACTUAL INACCURACIES section if contradictions exist
    contradiction_section = format_contradiction_section(contradictions)
    if contradiction_section:
        letter_parts.append(contradiction_section)

    # Opening paragraph
    opening = f"""On {dispute_date.strftime('%B %d, %Y')}, {consumer_name} submitted a written dispute to {canonical_entity} regarding inaccurate information appearing in {consumer_name}'s consumer file.

{canonical_entity}, as a credit reporting agency subject to the Fair Credit Reporting Act (FCRA), 15 U.S.C. § 1681 et seq., bears specific statutory obligations upon receipt of a consumer dispute.

{canonical_entity}'s verification response fails to satisfy its statutory obligations and compounds its liability."""
    letter_parts.append(opening)

    # STATUTORY FRAMEWORK - lead with contradictions context if present
    if contradiction_section:
        statutory_framework = f"""STATUTORY FRAMEWORK
{'=' * 50}

Under 15 U.S.C. § 1681i(a)(1)(A), upon receiving notice of a dispute, a consumer reporting agency shall conduct a reasonable reinvestigation to determine whether the disputed information is inaccurate.

The provable factual inaccuracies documented above demonstrate that no reasonable investigation was conducted. Information that is mathematically or temporally impossible cannot be "verified" through any legitimate investigative process. {canonical_entity}'s claim of verification is therefore facially deficient."""
    else:
        statutory_framework = f"""STATUTORY FRAMEWORK
{'=' * 50}

Under 15 U.S.C. § 1681i(a)(1)(A), upon receiving notice of a dispute, a consumer reporting agency shall conduct a reasonable reinvestigation to determine whether the disputed information is inaccurate.

{canonical_entity}'s claim of verification fails to satisfy this statutory standard."""
    letter_parts.append(statutory_framework)

    # VIOLATION SECTION
    violation_section = f"""STATUTORY VIOLATION
{'=' * 50}

Violation: Verification Without Reasonable Investigation
Statute: 15 U.S.C. § 1681i(a)(1)(A)

Established Facts:
    - Written dispute submitted on {dispute_date.strftime('%B %d, %Y')}
    - Response received on {response_date.strftime('%B %d, %Y')} claiming verification of disputed information
    - {canonical_entity} failed to conduct a reasonable reinvestigation as required by statute

Disputed Items:"""

    for item in disputed_items_facts:
        violation_section += f"\n    • {item}"

    letter_parts.append(violation_section)

    # TIMELINE SECTION
    timeline = f"""TIMELINE OF EVENTS
{'-' * 50}

Dispute Submitted: {dispute_date.strftime('%B %d, %Y')}
Response Received: {response_date.strftime('%B %d, %Y')}
Response Type: VERIFIED (Claimed)"""
    letter_parts.append(timeline)

    # PHASE 3: DEMANDED ACTIONS - Dynamic based on contradiction severity
    primary_remedy = determine_primary_remedy(contradictions)
    actions = generate_demanded_actions(primary_remedy, canonical_entity, "VERIFIED")
    demands = format_demanded_actions_section(actions)
    letter_parts.append(demands)

    # RIGHTS PRESERVATION
    rights = f"""RIGHTS PRESERVATION
{'-' * 50}

Nothing in this correspondence shall be construed as a waiver of any rights or remedies available under 15 U.S.C. §§ 1681n or 1681o for negligent or willful noncompliance."""
    letter_parts.append(rights)

    # CLOSING
    closing = f"""RESPONSE REQUIRED
{'-' * 50}

A written response addressing each demanded action is required within fifteen (15) days of receipt of this notice. Failure to respond or inadequate response will be documented and may be submitted as evidence in subsequent proceedings.

All future correspondence regarding this matter should be directed to the undersigned at the address provided above.



Respectfully submitted,



____________________________________
{consumer_name}

Enclosures:
- Copy of original dispute letter
- Certified mail receipt
- Supporting documentation"""
    letter_parts.append(closing)

    return "\n\n".join(letter_parts)


def generate_rejected_response_letter(
    consumer: Dict[str, str],
    entity_type: str,
    entity_name: str,
    original_violations: List[Dict[str, Any]],
    dispute_date: datetime,
    rejection_date: datetime,
    rejection_reason: str = None,
    has_5_day_notice: bool = False,
    has_specific_reason: bool = False,
    contradictions: Optional[List[Any]] = None,
) -> str:
    """
    Generate enforcement letter for REJECTED (Frivolous/Irrelevant) response scenario.

    Production-ready implementation:
    - Single statutory theory: Improper Frivolous Determination under §1681i(a)(3)(B)
    - Canonical entity names (TransUnion LLC, Equifax Inc., Experian LLC)
    - Statutory Framework section explaining legal requirements
    - Timeline noting failure to provide written notice with specific deficiencies
    - All violations assigned statutes (no empty statutes)
    - No damages lecture, single rights-preservation sentence
    - No regulatory cc at this stage

    Phase 2 Integration:
    - If contradictions provided, inserts PROVABLE FACTUAL INACCURACIES section after header
    - Facts first, statutes second
    - Contradictions sorted by severity (CRITICAL → HIGH → MEDIUM)
    """
    # Canonicalize entity name
    canonical_entity = canonicalize_entity_name(entity_name)

    # Build disputed items with auto-assigned statutes
    disputed_items = []
    for v in original_violations:
        v_type = v.get("violation_type", v.get("type", ""))
        creditor = v.get("creditor_name", "")
        account_mask = v.get("account_number_masked", "")

        # Auto-assign statute if empty
        explicit_statute = v.get("primary_statute", v.get("statute", ""))
        statute = get_statute_for_violation(v_type, explicit_statute)

        item_desc = f"{creditor}" if creditor else "Disputed tradeline"
        if account_mask:
            item_desc += f" ({account_mask})"
        if v_type:
            item_desc += f" - {v_type.replace('_', ' ').title()}"

        disputed_items.append({
            "description": item_desc,
            "statute": statute,
            "type": v_type,
        })

    # Build the letter content directly (custom structure for REJECTED)
    letter_parts = []

    # Header
    today = datetime.now().strftime("%B %d, %Y")
    consumer_name = consumer.get('name', '[CONSUMER NAME]')
    consumer_address = consumer.get('address', '[CONSUMER ADDRESS]')

    header = f"""{consumer_name}
{consumer_address}

{today}

{canonical_entity}
Consumer Dispute Department
[ADDRESS ON FILE]

Via Certified Mail, Return Receipt Requested"""
    letter_parts.append(header)

    # Subject line
    subject = "RE: FORMAL NOTICE OF STATUTORY VIOLATION - Improper Frivolous/Irrelevant Determination"
    letter_parts.append(subject)

    # PHASE 2: Insert PROVABLE FACTUAL INACCURACIES section if contradictions exist
    contradiction_section = format_contradiction_section(contradictions)
    if contradiction_section:
        letter_parts.append(contradiction_section)

    # Opening paragraph
    opening = f"""On {dispute_date.strftime('%B %d, %Y')}, {consumer_name} submitted a written dispute to {canonical_entity} regarding inaccurate information appearing in {consumer_name}'s consumer file.

{canonical_entity}'s determination that this dispute is frivolous or irrelevant fails to comply with statutory requirements."""
    letter_parts.append(opening)

    # STATUTORY FRAMEWORK SECTION - lead with contradictions context if present
    if contradiction_section:
        statutory_framework = f"""STATUTORY FRAMEWORK
{'=' * 50}

Under 15 U.S.C. § 1681i(a)(3)(B), a consumer reporting agency may treat a dispute as frivolous or irrelevant ONLY if:

(i) The consumer fails to provide sufficient information to investigate the disputed information; AND

(ii) The agency provides written notice to the consumer within five (5) business days that:
    (A) Informs the consumer of the determination and reasons for it; AND
    (B) Identifies any information required to investigate the disputed item.

The provable factual inaccuracies documented above demonstrate that the disputed information is objectively false. A dispute identifying mathematically or temporally impossible data cannot be deemed "frivolous" - such data must be deleted regardless of furnisher confirmation.

{canonical_entity} has failed to satisfy these statutory prerequisites for a valid frivolous determination."""
    else:
        statutory_framework = f"""STATUTORY FRAMEWORK
{'=' * 50}

Under 15 U.S.C. § 1681i(a)(3)(B), a consumer reporting agency may treat a dispute as frivolous or irrelevant ONLY if:

(i) The consumer fails to provide sufficient information to investigate the disputed information; AND

(ii) The agency provides written notice to the consumer within five (5) business days that:
    (A) Informs the consumer of the determination and reasons for it; AND
    (B) Identifies any information required to investigate the disputed item.

{canonical_entity} has failed to satisfy these statutory prerequisites for a valid frivolous determination."""
    letter_parts.append(statutory_framework)

    # VIOLATION SECTION - Primary violation is the improper frivolous determination
    violation_section = f"""STATUTORY VIOLATION
{'=' * 50}

Violation: Improper Frivolous/Irrelevant Determination
Statute: 15 U.S.C. § 1681i(a)(3)(B)

Established Facts:
    - Written dispute submitted on {dispute_date.strftime('%B %d, %Y')}
    - {canonical_entity} rejected the dispute as frivolous/irrelevant on {rejection_date.strftime('%B %d, %Y')}
    - {canonical_entity} failed to provide written notice identifying specific information required to investigate
    - {canonical_entity} failed to identify which element(s) of the dispute were allegedly deficient

Disputed Items:"""

    for item in disputed_items:
        violation_section += f"\n    • {item['description']} [{item['statute']}]"

    letter_parts.append(violation_section)

    # TIMELINE SECTION
    timeline = f"""TIMELINE OF EVENTS
{'-' * 50}

Dispute Submitted: {dispute_date.strftime('%B %d, %Y')}
Rejection Received: {rejection_date.strftime('%B %d, %Y')}
5-Day Written Notice with Specific Deficiencies: NOT PROVIDED
Identification of Required Information: NOT PROVIDED"""
    letter_parts.append(timeline)

    # PHASE 3: DEMANDED ACTIONS - Dynamic based on contradiction severity
    primary_remedy = determine_primary_remedy(contradictions)
    actions = generate_demanded_actions(primary_remedy, canonical_entity, "REJECTED")
    demands = format_demanded_actions_section(actions)
    letter_parts.append(demands)

    # RIGHTS PRESERVATION (single sentence, no damages lecture)
    rights = f"""RIGHTS PRESERVATION
{'-' * 50}

Nothing in this correspondence shall be construed as a waiver of any rights or remedies available under 15 U.S.C. §§ 1681n or 1681o for negligent or willful noncompliance."""
    letter_parts.append(rights)

    # CLOSING (no regulatory cc)
    closing = f"""RESPONSE REQUIRED
{'-' * 50}

A written response addressing each demanded action is required within fifteen (15) days of receipt of this notice. Failure to respond or inadequate response will be documented and may be submitted as evidence in subsequent proceedings.

All future correspondence regarding this matter should be directed to the undersigned at the address provided above.



Respectfully submitted,



____________________________________
{consumer_name}

Enclosures:
- Copy of original dispute letter
- Certified mail receipt
- Supporting documentation"""
    letter_parts.append(closing)

    return "\n\n".join(letter_parts)


def generate_reinsertion_letter(
    consumer: Dict[str, str],
    entity_name: str,
    account: Dict[str, str],
    deletion_date: datetime,
    reinsertion_date: datetime,
    notice_received: bool = False
) -> str:
    """
    DEPRECATED: Use generate_reinsertion_response_letter() for production letters.

    Generate enforcement letter for reinsertion without notice.
    Under FCRA §611(a)(5)(B), CRAs must provide 5-day advance written notice
    before reinserting previously deleted information.
    """
    generator = ResponseLetterGenerator()

    facts = [
        f"Disputed tradeline was deleted on or about {deletion_date.strftime('%B %d, %Y')}",
        f"Same tradeline was reinserted on or about {reinsertion_date.strftime('%B %d, %Y')}",
    ]

    if not notice_received:
        facts.append("No written notice of reinsertion was received by consumer")
        facts.append("No notice was received within five (5) business days prior to reinsertion as required by statute")
    else:
        facts.append("Notice received was not provided within the required five (5) business day advance period")

    violations = [{
        "type": "REINSERTION_NO_NOTICE",
        "statute": "fcra_611_a_5_B",
        "facts": facts,
        "account": account
    }]

    demanded_actions = [
        "Immediate deletion of the reinserted tradeline",
        "Written confirmation of deletion within five (5) business days",
        "Disclosure of the furnisher certification relied upon for reinsertion, if any",
        "Identification of the individual(s) responsible for reinsertion decision"
    ]

    return generator.generate_enforcement_letter(
        consumer=consumer,
        entity_type="CRA",
        entity_name=entity_name,
        violations=violations,
        demanded_actions=demanded_actions,
        response_type="REINSERTION_NO_NOTICE",
        include_willful_notice=True
    )


def generate_reinsertion_response_letter(
    consumer: Dict[str, str],
    entity_type: str,
    entity_name: str,
    original_violations: List[Dict[str, Any]],
    reinsertion_date: datetime,
    deletion_date: datetime = None,
    notice_received_date: datetime = None,
) -> str:
    """
    Generate enforcement letter for REINSERTION response scenario.

    Production-ready implementation:
    - Single statutory theory: Reinsertion Without Required Notice under §1681i(a)(5)(B)
    - Canonical entity names (TransUnion LLC, Equifax Inc., Experian LLC)
    - Reinsertion-specific statutory elements
    - Timeline with deletion date, reinsertion detected date, notice received date
    - Reinsertion-specific demands
    - No mention of "reasonable investigation" or 30-day dispute deadline
    - No damages lecture, single rights-preservation sentence
    - No regulatory cc at this stage
    """
    # Canonicalize entity name
    canonical_entity = canonicalize_entity_name(entity_name)

    # Build reinserted items with auto-assigned statutes
    reinserted_items = []
    for v in original_violations:
        v_type = v.get("violation_type", v.get("type", ""))
        creditor = v.get("creditor_name", "")
        account_mask = v.get("account_number_masked", "")

        item_desc = f"{creditor}" if creditor else "Disputed tradeline"
        if account_mask:
            item_desc += f" ({account_mask})"

        reinserted_items.append(item_desc)

    # Build the letter content directly (custom structure for REINSERTION)
    letter_parts = []

    # Header
    today = datetime.now().strftime("%B %d, %Y")
    consumer_name = consumer.get('name', '[CONSUMER NAME]')
    consumer_address = consumer.get('address', '[CONSUMER ADDRESS]')

    header = f"""{consumer_name}
{consumer_address}

{today}

{canonical_entity}
Consumer Dispute Department
[ADDRESS ON FILE]

Via Certified Mail, Return Receipt Requested"""
    letter_parts.append(header)

    # Subject line
    subject = "RE: FORMAL NOTICE OF STATUTORY VIOLATION - Reinsertion Without Required Notice"
    letter_parts.append(subject)

    # Opening paragraph - NO mention of dispute deadline or reasonable investigation
    opening = f"""{consumer_name} previously disputed inaccurate information appearing in {consumer_name}'s consumer file maintained by {canonical_entity}.

Following {canonical_entity}'s prior deletion of the disputed information, {canonical_entity} has reinserted the same information without providing the written notice required by federal law."""
    letter_parts.append(opening)

    # STATUTORY FRAMEWORK SECTION
    statutory_framework = f"""STATUTORY FRAMEWORK
{'=' * 50}

Under 15 U.S.C. § 1681i(a)(5)(B), if information that has been deleted from a consumer's file is reinserted, the consumer reporting agency shall:

(i) Certify that the information is complete and accurate; AND

(ii) Provide written notice to the consumer within five (5) business days of the reinsertion that includes:
    (A) A statement that the disputed information has been reinserted;
    (B) The business name and address of any furnisher that provided information that was the basis for reinsertion; AND
    (C) A notice that the consumer has the right to add a statement to the file disputing the accuracy or completeness of the information.

{canonical_entity} has failed to satisfy these statutory prerequisites for valid reinsertion."""
    letter_parts.append(statutory_framework)

    # VIOLATION SECTION
    violation_section = f"""STATUTORY VIOLATION
{'=' * 50}

Violation: Reinsertion Without Required Notice
Statute: 15 U.S.C. § 1681i(a)(5)(B)

Established Facts:"""

    # Deletion date fact
    if deletion_date:
        violation_section += f"\n    - Disputed information was deleted on or about {deletion_date.strftime('%B %d, %Y')}"
    else:
        violation_section += f"\n    - Disputed information was previously deleted per {canonical_entity} dispute results"

    violation_section += f"""
    - Same information was reinserted into consumer file on or about {reinsertion_date.strftime('%B %d, %Y')}
    - {canonical_entity} failed to provide written notice of reinsertion within five (5) business days
    - {canonical_entity} failed to identify the furnisher and furnisher address as required by § 1681i(a)(5)(B)(ii)
    - {canonical_entity} failed to notify consumer of right to add dispute statement

Reinserted Item(s):"""

    for item in reinserted_items:
        violation_section += f"\n    • {item}"

    letter_parts.append(violation_section)

    # TIMELINE SECTION - reinsertion-specific
    timeline = f"""TIMELINE OF EVENTS
{'-' * 50}

"""
    if deletion_date:
        timeline += f"Prior Deletion Date: {deletion_date.strftime('%B %d, %Y')}\n"
    else:
        timeline += f"Prior Deletion: Previously deleted per {canonical_entity} dispute results\n"

    timeline += f"Reinsertion Detected: {reinsertion_date.strftime('%B %d, %Y')}\n"

    if notice_received_date:
        timeline += f"Written Notice Received: {notice_received_date.strftime('%B %d, %Y')} (DEFICIENT)"
    else:
        timeline += "Written Notice Received: NONE"

    letter_parts.append(timeline)

    # DEMANDED ACTIONS - reinsertion-specific
    demands = f"""DEMANDED ACTIONS
{'-' * 50}

The following actions are demanded within fifteen (15) days of receipt of this notice:

1. Immediate deletion or re-blocking of the reinserted item unless {canonical_entity} can demonstrate statutory compliance with 15 U.S.C. § 1681i(a)(5)(B)

2. Written certification of the reinsertion source and furnisher verification, including the specific steps taken to certify that the information is complete and accurate

3. If {canonical_entity} claims written notice was provided: Production of the reinsertion notice allegedly sent, including date of mailing and method of delivery

4. Identification of the furnisher whose information was the basis for reinsertion, including furnisher name, address, and date furnisher was notified

5. Updated consumer disclosure reflecting removal of the reinserted information"""
    letter_parts.append(demands)

    # RIGHTS PRESERVATION (single sentence, no damages lecture)
    rights = f"""RIGHTS PRESERVATION
{'-' * 50}

Nothing in this correspondence shall be construed as a waiver of any rights or remedies available under 15 U.S.C. §§ 1681n or 1681o for negligent or willful noncompliance."""
    letter_parts.append(rights)

    # CLOSING (no regulatory cc)
    closing = f"""RESPONSE REQUIRED
{'-' * 50}

A written response addressing each demanded action is required within fifteen (15) days of receipt of this notice. Failure to respond or inadequate response will be documented and may be submitted as evidence in subsequent proceedings.

All future correspondence regarding this matter should be directed to the undersigned at the address provided above.



Respectfully submitted,



____________________________________
{consumer_name}

Enclosures:
- Copy of prior dispute results showing deletion
- Evidence of reinsertion (current credit report)
- Certified mail receipt"""
    letter_parts.append(closing)

    return "\n\n".join(letter_parts)
