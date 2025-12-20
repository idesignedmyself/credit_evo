"""
Credit Engine 2.0 - Response Letter Generator
Generates formal FCRA enforcement correspondence based on dispute responses.

ROLE: U.S. consumer credit compliance enforcement engine.
- Does NOT provide advice
- Generates formal regulatory correspondence asserting violations
- Cites statutes in canonical USC format only
- Treats all violations as assertions unless explicitly marked "resolved"
- Assumes recipient is legally sophisticated
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import UUID
import textwrap


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


class ResponseLetterGenerator:
    """
    Generates formal FCRA enforcement letters based on dispute responses.
    """

    def __init__(self):
        self.generated_at = datetime.now()

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

        return "\n\n".join(filter(None, letter_parts))

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
        """Generate willful noncompliance notice under §616."""
        return f"""NOTICE OF POTENTIAL WILLFUL NONCOMPLIANCE
{'-' * 50}

This letter serves as formal notice that continued noncompliance may constitute willful failure to comply with the requirements of the Fair Credit Reporting Act. Under {STATUTE_CITATIONS['fcra_616']}, any person who willfully fails to comply with any requirement imposed under this title with respect to any consumer is liable to that consumer in an amount equal to the sum of:

(1) Any actual damages sustained by the consumer as a result of the failure or damages of not less than $100 and not more than $1,000;

(2) Such amount of punitive damages as the court may allow; and

(3) In the case of any successful action to enforce any liability under this section, the costs of the action together with reasonable attorney's fees as determined by the court.

This notice is provided to establish knowledge of the violations asserted herein for purposes of any subsequent determination of willfulness."""

    def _generate_closing(self, consumer: Dict[str, str]) -> str:
        """Generate the closing and signature block."""
        consumer_name = consumer.get('name', '[CONSUMER NAME]')

        return f"""RESPONSE REQUIRED
{'-' * 50}

A written response addressing each demanded action is required within fifteen (15) days of receipt of this notice. Failure to respond or inadequate response will be documented and may be submitted as evidence in subsequent regulatory complaints or civil proceedings.

All future correspondence regarding this matter should be directed to the undersigned at the address provided above.



Respectfully submitted,



____________________________________
{consumer_name}

Enclosures:
- Copy of original dispute letter
- Certified mail receipt
- Supporting documentation

cc: Consumer Financial Protection Bureau
    [State Attorney General Consumer Protection Division]"""


def generate_no_response_letter(
    consumer: Dict[str, str],
    entity_type: str,
    entity_name: str,
    original_violations: List[Dict[str, Any]],
    dispute_date: datetime,
    deadline_date: datetime
) -> str:
    """
    Generate enforcement letter for NO_RESPONSE scenario.

    This is a convenience function for the most common enforcement scenario.
    """
    generator = ResponseLetterGenerator()

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
    response_date: datetime
) -> str:
    """
    Generate enforcement letter for VERIFIED response scenario.

    When entity verifies disputed information without proper investigation.
    """
    generator = ResponseLetterGenerator()

    response_violation = RESPONSE_VIOLATION_MAP.get("VERIFIED", {}).get(entity_type, {})

    violations = [{
        "type": response_violation.get("violation", "failure_to_investigate"),
        "statute": response_violation.get("statute", ""),
        "facts": [
            f"Written dispute submitted on {dispute_date.strftime('%B %d, %Y')}",
            f"Response received on {response_date.strftime('%B %d, %Y')} verifying disputed information",
            "Verification performed without reasonable investigation into accuracy",
            response_violation.get("description", "Verified without proper investigation")
        ]
    }]

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
        "Disclosure of the method of verification used for each disputed item",
        "Production of all documents relied upon in verification",
        "Identification of the furnisher(s) contacted and date(s) of contact",
        "Immediate reinvestigation using procedures that constitute a reasonable investigation",
        "Written results of reinvestigation within fifteen (15) days"
    ]

    return generator.generate_enforcement_letter(
        consumer=consumer,
        entity_type=entity_type,
        entity_name=entity_name,
        violations=violations,
        demanded_actions=demanded_actions,
        dispute_date=dispute_date,
        response_date=response_date,
        response_type="VERIFIED",
        include_willful_notice=True
    )


def generate_reinsertion_letter(
    consumer: Dict[str, str],
    entity_name: str,
    account: Dict[str, str],
    deletion_date: datetime,
    reinsertion_date: datetime,
    notice_received: bool = False
) -> str:
    """
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
