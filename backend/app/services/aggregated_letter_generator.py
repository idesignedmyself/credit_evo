"""
FCRA Aggregated Enforcement Letter Generator
=============================================
Generates single enforcement letters from precomputed aggregation groups.

Input: Aggregation group with shared entity, outcome, statutes, and demands.
Output: Single coherent enforcement letter with unified statutory theory.

This generator does NOT decide grouping - it receives pre-validated groups.
"""

from typing import List, Dict, Optional, Set
from dataclasses import dataclass
from datetime import datetime, date
from enum import Enum


# =============================================================================
# RESPONSE OUTCOME DEFINITIONS
# =============================================================================

class ResponseOutcome(str, Enum):
    NO_RESPONSE = "NO_RESPONSE"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    REINSERTION = "REINSERTION"
    INVESTIGATING = "INVESTIGATING"
    UPDATED = "UPDATED"


class StatuteFamily(str, Enum):
    FCRA_PROCEDURAL = "FCRA_PROCEDURAL"
    FCRA_SUBSTANTIVE = "FCRA_SUBSTANTIVE"
    FCRA_REINSERTION = "FCRA_REINSERTION"
    FCRA_ACCURACY = "FCRA_ACCURACY"
    FDCPA = "FDCPA"
    STATE = "STATE"


# =============================================================================
# INPUT DATA STRUCTURES
# =============================================================================

@dataclass
class ViolationInput:
    """Single violation within an aggregation group."""
    violation_id: str
    account: str                    # e.g., "Verizon ****8579"
    violation_type: str             # e.g., "Missing DOFD"
    statutes: List[str]             # e.g., ["15 USC §1681i(a)(1)(A)"]
    facts: List[str]                # Factual assertions


@dataclass
class AggregationGroupInput:
    """Precomputed aggregation group - input to letter generator."""
    entity: str                     # e.g., "TransUnion LLC"
    response_outcome: str           # e.g., "VERIFIED"
    statute_family: str             # e.g., "FCRA_PROCEDURAL"
    violations: List[ViolationInput]
    demands: List[str]              # Shared demands for all violations
    consumer_name: str = ""
    consumer_address: str = ""
    dispute_date: Optional[str] = None
    response_date: Optional[str] = None


# =============================================================================
# STATUTORY THEORY TEMPLATES BY RESPONSE OUTCOME
# =============================================================================

STATUTORY_THEORY_TEMPLATES = {
    ResponseOutcome.NO_RESPONSE: """
STATUTORY FRAMEWORK: FAILURE TO RESPOND

Under 15 U.S.C. § 1681i(a)(1)(A), a consumer reporting agency that receives a
dispute regarding the completeness or accuracy of any item of information must,
within thirty (30) days of receipt, conduct a reasonable reinvestigation to
determine whether the disputed information is inaccurate and record the current
status of the disputed information, or delete the item from the file.

{entity} received notice of the disputed information on {dispute_date}. The
statutory deadline expired on {deadline_date}. As of the date of this letter,
{entity} has failed to provide any response to the dispute, constituting a
per se violation of the reinvestigation mandate.

The failure to respond within the statutory period is not a discretionary matter.
Congress imposed this deadline to protect consumers from indefinite uncertainty
regarding disputed credit information. {entity}'s silence operates as a waiver
of any defense to the accuracy challenge and mandates deletion under
§ 1681i(a)(5)(A).
""",

    ResponseOutcome.VERIFIED: """
STATUTORY FRAMEWORK: VERIFICATION WITHOUT SUBSTANTIATION

Under 15 U.S.C. § 1681i(a)(1)(A), a consumer reporting agency must conduct a
"reasonable reinvestigation" of disputed information. The term "reasonable"
imposes substantive requirements—a CRA may not merely parrot the furnisher's
response without independent analysis of the consumer's specific dispute.

{entity} responded to the dispute with a verification of the disputed
information. However, verification without disclosure of the method employed
fails to satisfy the "reasonable reinvestigation" standard established in
Cushman v. Trans Union Corp., 115 F.3d 220 (3d Cir. 1997), and its progeny.

The consumer disputes the accuracy of specific data fields. {entity}'s bare
verification, absent production of documentation evidencing actual investigation,
does not constitute compliance with § 1681i(a)(1)(A). The consumer is entitled
to disclosure of the method of verification under § 1681i(a)(6)(B)(iii) and
identification of the furnisher contacted under § 1681i(a)(6)(B)(ii).
""",

    ResponseOutcome.REJECTED: """
STATUTORY FRAMEWORK: IMPROPER FRIVOLOUS DETERMINATION

Under 15 U.S.C. § 1681i(a)(3)(A), a consumer reporting agency may terminate a
reinvestigation only if it "reasonably determines" that the dispute is frivolous
or irrelevant, including by reason of a failure by a consumer to provide
sufficient information to investigate the disputed information.

{entity} rejected this dispute as frivolous or otherwise refused to investigate.
However, § 1681i(a)(3)(B) requires that any such determination be communicated
to the consumer within five (5) business days, with a statement of the specific
reasons for the determination and identification of any information required to
investigate the disputed information.

The dispute submitted was specific, identified particular data fields, and
provided sufficient information to conduct a reinvestigation. {entity}'s
rejection does not satisfy the procedural requirements of § 1681i(a)(3) and
constitutes an independent violation of the FCRA.
""",

    ResponseOutcome.REINSERTION: """
STATUTORY FRAMEWORK: REINSERTION WITHOUT NOTICE

Under 15 U.S.C. § 1681i(a)(5)(B)(ii), if deleted information is subsequently
reinserted into a consumer's file, the consumer reporting agency must provide
written notice to the consumer stating that the information has been reinserted,
not later than five (5) business days after the reinsertion.

{entity} previously deleted the disputed information from the consumer's file.
The information has subsequently reappeared. {entity} failed to provide the
mandatory five-day written notice of reinsertion as required by statute.

Reinsertion without notice is a per se violation of § 1681i(a)(5)(B)(ii). The
notice requirement is not optional—it exists to ensure consumers can promptly
respond to the reappearance of disputed information. {entity}'s failure to
provide notice constitutes willful noncompliance, exposing {entity} to
statutory damages under 15 U.S.C. § 1681n.
""",

    ResponseOutcome.INVESTIGATING: """
STATUTORY FRAMEWORK: UNREASONABLE DELAY

Under 15 U.S.C. § 1681i(a)(1)(A), a consumer reporting agency must complete its
reinvestigation within thirty (30) days of receiving the dispute. The statute
provides a limited extension to forty-five (45) days only when the consumer
submits additional information during the reinvestigation period.

{entity} has indicated the dispute remains under investigation beyond the
statutory deadline. Continued investigation without resolution constitutes a
failure to comply with the mandatory timeline. The "investigating" status is
not a permissible indefinite state.

The consumer disputes specific, verifiable data fields. The reinvestigation
should require only contact with the furnisher and review of source documents.
{entity}'s prolonged investigation suggests either procedural failure or
deliberate delay, neither of which excuses noncompliance with § 1681i(a)(1)(A).
""",

    ResponseOutcome.UPDATED: """
STATUTORY FRAMEWORK: PARTIAL CURE WITH RESIDUAL VIOLATIONS

Under 15 U.S.C. § 1681i(a)(5)(A), upon completion of a reinvestigation that
results in modification of a disputed item, the consumer reporting agency must
modify or delete the item in accordance with the determination and notify the
consumer of the results.

{entity} updated certain fields in response to the dispute. However, the
modifications do not fully address the inaccuracies identified by the consumer.
Partial correction does not constitute full compliance with the reinvestigation
mandate when residual inaccuracies remain.

The consumer continues to dispute the accuracy of the information as currently
reported. {entity}'s obligation to ensure maximum possible accuracy under
§ 1681e(b) is ongoing. The residual violations identified below require
additional corrective action.
""",
}


# =============================================================================
# ENTITY ADDRESS DATABASE
# =============================================================================

ENTITY_ADDRESSES = {
    "transunion": {
        "legal_name": "TransUnion LLC",
        "address": "P.O. Box 2000\nChester, PA 19016-2000",
        "department": "Consumer Dispute Center",
    },
    "equifax": {
        "legal_name": "Equifax Information Services LLC",
        "address": "P.O. Box 740256\nAtlanta, GA 30374-0256",
        "department": "Consumer Dispute Center",
    },
    "experian": {
        "legal_name": "Experian Information Solutions, Inc.",
        "address": "P.O. Box 4500\nAllen, TX 75013",
        "department": "National Consumer Assistance Center",
    },
}


# =============================================================================
# LETTER GENERATOR
# =============================================================================

class AggregatedLetterGenerator:
    """
    Generates enforcement letters from precomputed aggregation groups.

    Design principles:
    - One statutory theory per letter
    - Violations as subsections, not separate arguments
    - Shared demands (no repetition)
    - Liability preservation, not damages lecture
    """

    def __init__(self, group: AggregationGroupInput):
        self.group = group
        self.entity = group.entity
        self.outcome = ResponseOutcome(group.response_outcome)
        self.statute_family = StatuteFamily(group.statute_family)
        self.violations = group.violations
        self.demands = group.demands
        self.consumer_name = group.consumer_name
        self.consumer_address = group.consumer_address
        self.dispute_date = group.dispute_date
        self.response_date = group.response_date
        self.letter_date = datetime.now().strftime("%B %d, %Y")

    def generate(self) -> str:
        """Generate complete enforcement letter."""
        sections = [
            self._header(),
            self._reference_line(),
            self._opening(),
            self._statutory_theory(),
            self._violations_section(),
            self._demands_section(),
            self._liability_preservation(),
            self._closing(),
        ]
        return "\n".join(sections)

    def _header(self) -> str:
        """Letter header with date and addresses."""
        # Get entity address info
        entity_key = self.entity.lower().split()[0]  # "transunion", "equifax", etc.
        entity_info = ENTITY_ADDRESSES.get(entity_key, {
            "legal_name": self.entity,
            "address": "[Address Required]",
            "department": "Consumer Dispute Department",
        })

        consumer_block = f"{self.consumer_name}\n{self.consumer_address}" if self.consumer_name else "[CONSUMER NAME]\n[CONSUMER ADDRESS]"

        return f"""{self.letter_date}

VIA CERTIFIED MAIL, RETURN RECEIPT REQUESTED

{entity_info['legal_name']}
{entity_info['department']}
{entity_info['address']}

{consumer_block}
"""

    def _reference_line(self) -> str:
        """Reference line with dispute identification."""
        violation_ids = ", ".join(v.violation_id for v in self.violations)
        return f"""RE:     NOTICE OF CONTINUING VIOLATION — FCRA § 611
        Consumer: {self.consumer_name or '[CONSUMER NAME]'}
        Dispute Reference: {violation_ids}
        Response Outcome: {self.outcome.value.replace('_', ' ').title()}
"""

    def _opening(self) -> str:
        """Opening paragraph establishing the letter's purpose."""
        violation_count = len(self.violations)
        accounts = ", ".join(v.account for v in self.violations)

        return f"""To Whom It May Concern:

This letter constitutes formal notice of continuing violations of the Fair Credit
Reporting Act ("FCRA"), 15 U.S.C. § 1681 et seq., arising from {self.entity}'s
handling of disputes regarding {violation_count} account(s): {accounts}.

The violations documented herein share a common statutory basis and remedial
framework. This letter demands immediate corrective action and preserves all
rights under federal law.
"""

    def _statutory_theory(self) -> str:
        """Single unified statutory theory section."""
        template = STATUTORY_THEORY_TEMPLATES.get(self.outcome, "")

        # Calculate deadline (30 days from dispute date)
        deadline_date = "[DEADLINE DATE]"
        if self.dispute_date:
            try:
                dispute = datetime.strptime(self.dispute_date, "%Y-%m-%d")
                from datetime import timedelta
                deadline = dispute + timedelta(days=30)
                deadline_date = deadline.strftime("%B %d, %Y")
            except ValueError:
                pass

        # Format template with context
        theory = template.format(
            entity=self.entity,
            dispute_date=self.dispute_date or "[DISPUTE DATE]",
            deadline_date=deadline_date,
            response_date=self.response_date or "[RESPONSE DATE]",
        )

        return f"""
{"=" * 72}
I. STATUTORY FRAMEWORK
{"=" * 72}
{theory}
"""

    def _violations_section(self) -> str:
        """Individual violation subsections."""
        lines = [f"""
{"=" * 72}
II. SPECIFIC VIOLATIONS
{"=" * 72}

The following violations arise from {self.entity}'s response to the consumer's
dispute. Each violation shares the statutory framework set forth above.
"""]

        for i, violation in enumerate(self.violations, 1):
            lines.append(self._format_violation(i, violation))

        return "\n".join(lines)

    def _format_violation(self, index: int, violation: ViolationInput) -> str:
        """Format a single violation subsection."""
        statutes_str = ", ".join(violation.statutes)
        facts_str = "\n".join(f"   • {fact}" for fact in violation.facts) if violation.facts else "   • [Facts to be inserted]"

        return f"""
{"-" * 72}
VIOLATION {index}: {violation.violation_type}
{"-" * 72}

Account:        {violation.account}
Violation ID:   {violation.violation_id}
Statutes:       {statutes_str}

Factual Basis:
{facts_str}

Status: UNRESOLVED — Corrective action required.
"""

    def _demands_section(self) -> str:
        """Unified demands section (not repeated per violation)."""
        demands_list = "\n".join(f"   {i}. {demand}" for i, demand in enumerate(self.demands, 1))

        return f"""
{"=" * 72}
III. DEMANDS
{"=" * 72}

Pursuant to 15 U.S.C. § 1681i and applicable regulations, the consumer demands
that {self.entity} take the following actions within fifteen (15) days of
receipt of this letter:

{demands_list}

These demands apply to all violations identified in this letter. Failure to
comply with any demand will be documented and may form the basis for additional
claims.
"""

    def _liability_preservation(self) -> str:
        """Liability preservation language (not damages lecture)."""
        return f"""
{"=" * 72}
IV. PRESERVATION OF RIGHTS
{"=" * 72}

This letter is sent without prejudice to any rights, remedies, or defenses
available to the consumer under federal or state law.

Nothing in this letter constitutes a waiver of any claim, including but not
limited to claims for:

   • Statutory damages under 15 U.S.C. § 1681n (willful noncompliance)
   • Actual damages under 15 U.S.C. § 1681o (negligent noncompliance)
   • Reasonable attorney's fees and costs under 15 U.S.C. § 1681n(a)(3)

The consumer expressly reserves the right to pursue all available remedies
should {self.entity} fail to cure the violations identified herein.

Evidence of the violations documented in this letter, including this
correspondence and any response thereto, may be introduced in any subsequent
proceeding.
"""

    def _closing(self) -> str:
        """Letter closing with signature block."""
        return f"""
{"=" * 72}

Please direct all responses to the undersigned at the address provided above.
Responses must be in writing. Telephone responses are not acceptable and will
not be treated as compliance with this demand.

Time is of the essence.

Respectfully submitted,



__________________________________________
{self.consumer_name or '[CONSUMER NAME]'}
Date: {self.letter_date}


ENCLOSURES:
   • Copy of original dispute letter
   • Copy of {self.entity}'s response (if any)
   • Supporting documentation as applicable


                              CERTIFICATE OF SERVICE

I hereby certify that a copy of the foregoing was sent via Certified Mail,
Return Receipt Requested, to {self.entity} at the address listed above on
{self.letter_date}.



__________________________________________
{self.consumer_name or '[CONSUMER NAME]'}
"""


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def generate_aggregated_letter(group_data: Dict) -> str:
    """
    Generate enforcement letter from aggregation group dictionary.

    Input: Dictionary with keys:
        - entity: str
        - response_outcome: str
        - statute_family: str
        - violations: List[Dict] with keys: violation_id, account, violation_type, statutes, facts
        - demands: List[str]
        - consumer_name: str (optional)
        - consumer_address: str (optional)
        - dispute_date: str (optional, YYYY-MM-DD)
        - response_date: str (optional, YYYY-MM-DD)

    Output: Complete letter text (PDF-ready)
    """
    # Convert violation dicts to ViolationInput objects
    violations = [
        ViolationInput(
            violation_id=v.get("violation_id", ""),
            account=v.get("account", ""),
            violation_type=v.get("violation_type", ""),
            statutes=v.get("statutes", []),
            facts=v.get("facts", []),
        )
        for v in group_data.get("violations", [])
    ]

    group = AggregationGroupInput(
        entity=group_data.get("entity", ""),
        response_outcome=group_data.get("response_outcome", "NO_RESPONSE"),
        statute_family=group_data.get("statute_family", "FCRA_PROCEDURAL"),
        violations=violations,
        demands=group_data.get("demands", []),
        consumer_name=group_data.get("consumer_name", ""),
        consumer_address=group_data.get("consumer_address", ""),
        dispute_date=group_data.get("dispute_date"),
        response_date=group_data.get("response_date"),
    )

    generator = AggregatedLetterGenerator(group)
    return generator.generate()


def generate_letters_from_groups(groups: List[Dict], consumer_info: Dict = None) -> List[Dict]:
    """
    Generate letters from multiple aggregation groups.

    Input:
        - groups: List of aggregation group dictionaries
        - consumer_info: Optional dict with consumer_name, consumer_address

    Output: List of dicts with:
        - group_id: str
        - entity: str
        - response_outcome: str
        - violation_count: int
        - letter_content: str
    """
    results = []
    consumer_info = consumer_info or {}

    for group in groups:
        # Merge consumer info into group
        group_with_consumer = {
            **group,
            "consumer_name": group.get("consumer_name") or consumer_info.get("consumer_name", ""),
            "consumer_address": group.get("consumer_address") or consumer_info.get("consumer_address", ""),
        }

        letter_content = generate_aggregated_letter(group_with_consumer)

        results.append({
            "group_id": group.get("group_id", ""),
            "entity": group.get("entity", ""),
            "response_outcome": group.get("response_outcome", ""),
            "violation_count": len(group.get("violations", [])),
            "violation_ids": [v.get("violation_id") for v in group.get("violations", [])],
            "letter_content": letter_content,
            "word_count": len(letter_content.split()),
        })

    return results
