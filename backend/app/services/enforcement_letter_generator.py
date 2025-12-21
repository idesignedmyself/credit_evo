"""
FCRA Enforcement Letter Generator
==================================
Production-grade generator for outbound enforcement correspondence.

PERMITTED OUTCOMES: NO_RESPONSE, VERIFIED, REJECTED, REINSERTION
PROHIBITED OUTCOMES: INVESTIGATING, UPDATED (not enforcement-ready)

Output: PDF-ready enforcement letters for certified mail delivery.
"""

from typing import List, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum


# =============================================================================
# ENFORCEMENT POSTURES (ONLY)
# =============================================================================

class EnforcementOutcome(str, Enum):
    """
    Permitted enforcement outcomes only.
    INVESTIGATING and UPDATED are explicitly excluded.
    """
    NO_RESPONSE = "NO_RESPONSE"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    REINSERTION = "REINSERTION"


# Outcomes that are NOT enforcement-ready
PROHIBITED_OUTCOMES = {"INVESTIGATING", "UPDATED"}


# =============================================================================
# ENTITY REGISTRY (CANONICAL NAMES ONLY)
# =============================================================================

ENTITY_REGISTRY = {
    "transunion": {
        "legal_name": "TransUnion LLC",
        "address_line_1": "Consumer Dispute Center",
        "address_line_2": "P.O. Box 2000",
        "city_state_zip": "Chester, PA 19016-2000",
    },
    "equifax": {
        "legal_name": "Equifax Information Services LLC",
        "address_line_1": "Consumer Dispute Center",
        "address_line_2": "P.O. Box 740256",
        "city_state_zip": "Atlanta, GA 30374-0256",
    },
    "experian": {
        "legal_name": "Experian Information Solutions, Inc.",
        "address_line_1": "National Consumer Assistance Center",
        "address_line_2": "P.O. Box 4500",
        "city_state_zip": "Allen, TX 75013",
    },
}

# Canonical entity name aliases for validation
CANONICAL_ENTITY_ALIASES = {
    "transunion": ["transunion", "trans union", "tu"],
    "equifax": ["equifax", "efx"],
    "experian": ["experian", "exp"],
}


def _normalize_entity_name(entity: str) -> Optional[str]:
    """
    Normalize entity name to canonical form.
    Returns None if entity is not recognized.
    """
    entity_lower = entity.lower().strip()
    for canonical, aliases in CANONICAL_ENTITY_ALIASES.items():
        if entity_lower in aliases or entity_lower.startswith(canonical):
            return canonical
    return None


def _is_canonical_entity(entity: str) -> bool:
    """Check if entity name resolves to a canonical CRA."""
    return _normalize_entity_name(entity) is not None


# =============================================================================
# STATUTORY FRAMEWORK TEMPLATES
# =============================================================================

STATUTORY_FRAMEWORKS = {
    EnforcementOutcome.NO_RESPONSE: {
        "title": "Failure to Complete Reinvestigation Within Statutory Period",
        "body": """Under 15 U.S.C. § 1681i(a)(1)(A), a consumer reporting agency that receives notice of a dispute from a consumer regarding the completeness or accuracy of any item of information contained in the consumer's file must, not later than thirty (30) days after the date on which the agency receives the notice of the dispute, conduct a reasonable reinvestigation to determine whether the disputed information is inaccurate and record the current status of the disputed information, or delete the item from the file in accordance with 15 U.S.C. § 1681i(a)(5)(A).

{entity} received the consumer's dispute on {dispute_date}. The statutory deadline for completion of the reinvestigation was {deadline_date}.

As of the date of this letter, {entity} has failed to provide any response to the consumer's dispute. This silence constitutes a per se violation of the mandatory reinvestigation requirement under 15 U.S.C. § 1681i(a)(1)(A). The failure to respond within the statutory period is not a matter of discretion—it mandates deletion of the disputed information under 15 U.S.C. § 1681i(a)(5)(A), which provides that if the completeness or accuracy of any item of information contained in a consumer's file cannot be verified, the consumer reporting agency shall promptly delete that item of information from the file.""",
    },

    EnforcementOutcome.VERIFIED: {
        "title": "Verification Without Reasonable Investigation",
        "body": """Under 15 U.S.C. § 1681i(a)(1)(A), a consumer reporting agency that receives notice of a dispute from a consumer regarding the completeness or accuracy of any item of information contained in the consumer's file must conduct a "reasonable reinvestigation" to determine whether the disputed information is inaccurate. The statutory requirement imposes substantive obligations—a consumer reporting agency may not merely transmit the dispute to a furnisher and uncritically accept the furnisher's response.

{entity} responded to the consumer's dispute by verifying the disputed information as accurate. However, verification without substantiation does not satisfy the reasonable reinvestigation standard established by Congress. See Cushman v. Trans Union Corp., 115 F.3d 220, 224 (3d Cir. 1997) (holding that a CRA's reinvestigation must be "reasonable" in light of the information provided by the consumer).

The consumer is entitled, under 15 U.S.C. § 1681i(a)(6)(B)(iii), to a written description of the procedure used to determine the accuracy or completeness of the disputed information, including the business name and address of any furnisher contacted in connection with such information. Under 15 U.S.C. § 1681i(a)(6)(B)(ii), the consumer is further entitled to a statement that the reinvestigation is completed together with identification of the furnisher of the information.

{entity}'s verification, absent production of documentation evidencing the nature and scope of its investigation, fails to satisfy the reasonable reinvestigation standard mandated by 15 U.S.C. § 1681i(a)(1)(A).""",
    },

    EnforcementOutcome.REJECTED: {
        "title": "Improper Determination of Frivolous Dispute",
        "body": """Under 15 U.S.C. § 1681i(a)(3)(A), a consumer reporting agency may terminate a reinvestigation of information disputed by a consumer only if the agency "reasonably determines" that the dispute is frivolous or irrelevant, including by reason of a failure by a consumer to provide sufficient information to investigate the disputed information.

{entity} has declined to investigate the consumer's dispute, characterizing it as frivolous or otherwise refusing to conduct a reinvestigation. However, 15 U.S.C. § 1681i(a)(3)(B) requires that before making any such determination, the agency must provide notice to the consumer within five (5) business days of making the determination, by mail or, if authorized by the consumer for that purpose, by any other means available to the agency, including the specific reasons for the determination and identification of any information required to investigate the disputed information.

The consumer's dispute was specific, identified particular data fields, and provided sufficient information to conduct a reinvestigation. {entity}'s refusal to investigate without satisfying the procedural requirements of 15 U.S.C. § 1681i(a)(3)(B) constitutes an independent violation of the FCRA.""",
    },

    EnforcementOutcome.REINSERTION: {
        "title": "Reinsertion of Previously Deleted Information Without Notice",
        "body": """Under 15 U.S.C. § 1681i(a)(5)(B)(ii), if an item of information is deleted from a consumer's file pursuant to subparagraph (A), and is subsequently reinserted in the file, the consumer reporting agency shall notify the consumer of the reinsertion in writing not later than five (5) business days after the reinsertion, or if authorized by the consumer for that purpose, by any other means available to the agency.

{entity} previously deleted the disputed information from the consumer's file pursuant to the consumer's dispute. The disputed information has subsequently been reinserted into the consumer's file. {entity} has failed to provide the mandatory written notice of reinsertion within five (5) business days as required by 15 U.S.C. § 1681i(a)(5)(B)(ii).

The notice requirement under 15 U.S.C. § 1681i(a)(5)(B)(ii) is not discretionary. Failure to provide timely notice of reinsertion constitutes a per se violation of the FCRA and may constitute willful noncompliance subject to statutory damages under 15 U.S.C. § 1681n.""",
    },
}


# =============================================================================
# DEFAULT STATUTES BY VIOLATION TYPE
# =============================================================================

DEFAULT_STATUTES = {
    "missing_dofd": "15 U.S.C. § 1681e(b)",
    "missing_original_creditor": "15 U.S.C. § 1681e(b)",
    "balance_discrepancy": "15 U.S.C. § 1681e(b)",
    "date_discrepancy": "15 U.S.C. § 1681e(b)",
    "status_discrepancy": "15 U.S.C. § 1681e(b)",
    "obsolete_debt": "15 U.S.C. § 1681c(a)",
    "re_aging": "15 U.S.C. § 1681c(a)",
    "failure_to_investigate": "15 U.S.C. § 1681i(a)(1)(A)",
    "verification_without_investigation": "15 U.S.C. § 1681i(a)(1)(A)",
    "frivolous_rejection": "15 U.S.C. § 1681i(a)(3)(A)",
    "reinsertion_without_notice": "15 U.S.C. § 1681i(a)(5)(B)(ii)",
}


# =============================================================================
# INPUT STRUCTURES
# =============================================================================

@dataclass
class ViolationRecord:
    """Single violation for inclusion in letter."""
    account: str
    violation_type: str
    facts: List[str]
    statute: str = ""  # If empty, will be auto-assigned or violation removed


@dataclass
class EnforcementLetterRequest:
    """Complete request for enforcement letter generation."""
    consumer_name: str
    consumer_address: str
    entity: str
    response_outcome: str
    statutory_theory: str
    statutes: List[str]
    violations: List[ViolationRecord]
    demands: List[str]
    delivery_method: str = "Certified Mail, Return Receipt Requested"
    dispute_date: Optional[str] = None
    deadline_date: Optional[str] = None  # Required for NO_RESPONSE
    response_date: Optional[str] = None
    test_context: bool = False  # Test mode - bypasses deadline validation


# =============================================================================
# TEST MODE CONSTANTS
# =============================================================================

TEST_FOOTER = """
════════════════════════════════════════════════════════════════════════════════
                         TEST DOCUMENT – NOT MAILED
════════════════════════════════════════════════════════════════════════════════
This letter was generated in test mode for preview purposes only.
Do not mail, save to production records, or use for escalation.
════════════════════════════════════════════════════════════════════════════════
"""


# =============================================================================
# ENFORCEMENT LETTER GENERATOR
# =============================================================================

def _normalize_violation_type(vtype: str) -> str:
    """Normalize violation type for statute lookup."""
    return vtype.lower().replace(" ", "_").replace("-", "_")


def _assign_statute(violation: ViolationRecord, outcome: str) -> Optional[str]:
    """Assign statute to violation based on type and outcome."""
    if violation.statute:
        return violation.statute

    # Try to match by violation type
    normalized = _normalize_violation_type(violation.violation_type)
    if normalized in DEFAULT_STATUTES:
        return DEFAULT_STATUTES[normalized]

    # Partial matching
    for key, statute in DEFAULT_STATUTES.items():
        if key in normalized or normalized in key:
            return statute

    # Fallback based on outcome
    if outcome == "NO_RESPONSE":
        return "15 U.S.C. § 1681i(a)(1)(A)"
    elif outcome == "VERIFIED":
        return "15 U.S.C. § 1681i(a)(1)(A)"
    elif outcome == "REJECTED":
        return "15 U.S.C. § 1681i(a)(3)(A)"
    elif outcome == "REINSERTION":
        return "15 U.S.C. § 1681i(a)(5)(B)(ii)"

    return None  # No statute found - violation will be removed


class EnforcementLetterGenerator:
    """
    Production enforcement letter generator.

    Generates formal correspondence for certified mail delivery.
    Does NOT generate letters for non-enforcement outcomes.

    HARD GUARDS (raise errors, no silent fallback):
    - NO_RESPONSE requires deadline_date AND deadline must have passed
    - All violations must have valid statutes
    - Entity must resolve to canonical CRA name
    - Exactly ONE enforcement theory per letter
    - Mixed response outcomes prohibited
    """

    def __init__(self, request: EnforcementLetterRequest):
        # Store test mode flag
        self.test_context = request.test_context

        # Run all validation guards BEFORE any processing
        self._validate_outcome(request.response_outcome)
        self._validate_entity(request.entity)

        # Skip deadline validation in test mode
        if not self.test_context:
            self._validate_deadline_for_no_response(request)

        self._validate_single_enforcement_theory(request)

        self.request = request
        self.outcome = EnforcementOutcome(request.response_outcome)
        self.letter_date = datetime.now().strftime("%B %d, %Y")
        self.entity_info = self._get_entity_info()

        # Validate violations (raises on empty statutes)
        self._validate_violations()

    def _validate_entity(self, entity: str) -> None:
        """
        HARD GUARD: Entity must resolve to a canonical CRA name.
        No silent fallback to unknown entities.
        """
        if not entity or not entity.strip():
            raise ValueError(
                "Entity name is required. Cannot generate letter without target entity."
            )

        if not _is_canonical_entity(entity):
            canonical_names = list(ENTITY_REGISTRY.keys())
            raise ValueError(
                f"Non-canonical entity name: '{entity}'. "
                f"Must be one of: {', '.join(n.title() for n in canonical_names)}"
            )

    def _validate_single_enforcement_theory(self, request: EnforcementLetterRequest) -> None:
        """
        HARD GUARD: Exactly ONE enforcement theory per letter.
        Mixed response outcomes are prohibited.
        """
        if not request.statutory_theory or not request.statutory_theory.strip():
            raise ValueError(
                "Statutory theory is required. Each letter must assert exactly ONE enforcement theory."
            )

        # Validate statutes list is not empty
        if not request.statutes:
            raise ValueError(
                "At least one statute citation is required for enforcement letter."
            )

        # All statutes should belong to the same statutory family for coherent legal theory
        statute_families = set()
        for statute in request.statutes:
            if "1681i(a)(1)" in statute:
                statute_families.add("reinvestigation")
            elif "1681i(a)(3)" in statute:
                statute_families.add("frivolous")
            elif "1681i(a)(5)" in statute:
                statute_families.add("reinsertion")
            elif "1681e(b)" in statute:
                statute_families.add("accuracy")
            elif "1681c(a)" in statute:
                statute_families.add("obsolescence")
            else:
                statute_families.add("other")

        if len(statute_families) > 2:  # Allow some overlap (e.g., accuracy + reinvestigation)
            raise ValueError(
                f"Mixed enforcement theories detected. Letter contains statutes from {len(statute_families)} "
                f"different statutory families: {statute_families}. Use separate letters for each theory."
            )

    def _validate_deadline_for_no_response(self, request: EnforcementLetterRequest) -> None:
        """
        HARD GUARD: NO_RESPONSE requires dispute_date AND deadline_date AND deadline must have passed.
        """
        if request.response_outcome != "NO_RESPONSE":
            return

        if not request.dispute_date:
            raise ValueError(
                "Cannot generate NO_RESPONSE letter - dispute_date (mailed_date) is required"
            )

        if not request.deadline_date:
            raise ValueError(
                "Cannot generate NO_RESPONSE letter - deadline_date is required"
            )

        # Parse deadline and check if passed
        try:
            deadline_dt = datetime.strptime(request.deadline_date, "%Y-%m-%d").date()
            today = datetime.now().date()
            if today <= deadline_dt:
                raise ValueError(
                    f"Cannot generate NO_RESPONSE letter - deadline ({request.deadline_date}) has not passed"
                )
        except ValueError as e:
            if "has not passed" in str(e):
                raise
            raise ValueError(
                f"Invalid deadline_date format: {request.deadline_date}. Expected YYYY-MM-DD"
            )

    def _validate_violations(self) -> None:
        """
        HARD GUARD: All violations must have valid statutes.
        No silent dropping - raises explicit error for each invalid violation.
        """
        if not self.request.violations:
            raise ValueError(
                "At least one violation is required. Cannot generate empty enforcement letter."
            )

        violations_without_statutes = []
        violations_with_empty_accounts = []

        for i, v in enumerate(self.request.violations):
            # Try to assign statute if missing
            if not v.statute:
                assigned = _assign_statute(v, self.request.response_outcome)
                if assigned:
                    v.statute = assigned
                else:
                    violations_without_statutes.append(
                        f"Violation {i+1}: {v.violation_type} (no matching statute)"
                    )

            # Validate account is not empty
            if not v.account or not v.account.strip():
                violations_with_empty_accounts.append(
                    f"Violation {i+1}: {v.violation_type} (missing account identifier)"
                )

        # Raise aggregated errors
        errors = []
        if violations_without_statutes:
            errors.append(
                f"Violations without valid statutes (cannot be silently dropped):\n  - " +
                "\n  - ".join(violations_without_statutes)
            )
        if violations_with_empty_accounts:
            errors.append(
                f"Violations with missing account identifiers:\n  - " +
                "\n  - ".join(violations_with_empty_accounts)
            )

        if errors:
            raise ValueError(
                "Validation failed - cannot generate letter:\n\n" + "\n\n".join(errors)
            )

    def _validate_outcome(self, outcome: str) -> None:
        """Reject non-enforcement outcomes."""
        if outcome in PROHIBITED_OUTCOMES:
            raise ValueError(
                f"Outcome '{outcome}' is not enforcement-ready. "
                f"Permitted outcomes: {[e.value for e in EnforcementOutcome]}"
            )
        if outcome not in [e.value for e in EnforcementOutcome]:
            raise ValueError(
                f"Unknown outcome '{outcome}'. "
                f"Permitted outcomes: {[e.value for e in EnforcementOutcome]}"
            )

    def _get_entity_info(self) -> Dict:
        """Resolve entity to registry entry."""
        entity_key = self.request.entity.lower().split()[0]
        return ENTITY_REGISTRY.get(entity_key, {
            "legal_name": self.request.entity,
            "address_line_1": "",
            "address_line_2": "[Address Required]",
            "city_state_zip": "",
        })

    def generate(self) -> str:
        """Generate complete enforcement letter."""
        sections = [
            self._letterhead(),
            self._addresses(),
            self._reference_block(),
            self._salutation(),
            self._introduction(),
            self._statutory_framework(),
            self._violations_section(),
            self._demands_section(),
            self._preservation_clause(),
            self._closing(),
        ]

        letter = "\n".join(sections)

        # Append test footer in test mode
        if self.test_context:
            letter += TEST_FOOTER

        return letter

    def _letterhead(self) -> str:
        """Date and delivery method."""
        return f"""{self.letter_date}

{self.request.delivery_method}
"""

    def _addresses(self) -> str:
        """Entity and consumer address blocks."""
        entity = self.entity_info
        entity_block = f"""{entity['legal_name']}
{entity['address_line_1']}
{entity['address_line_2']}
{entity['city_state_zip']}"""

        return f"""{entity_block}

        {self.request.consumer_name}
        {self.request.consumer_address}
"""

    def _reference_block(self) -> str:
        """Subject line identifying the matter."""
        return f"""
RE:     Notice of Violation of Fair Credit Reporting Act
        Consumer: {self.request.consumer_name}
        Enforcement Posture: {self._format_outcome()}
"""

    def _format_outcome(self) -> str:
        """Format outcome for display."""
        mapping = {
            EnforcementOutcome.NO_RESPONSE: "Failure to Respond to Dispute",
            EnforcementOutcome.VERIFIED: "Verification Without Substantiation",
            EnforcementOutcome.REJECTED: "Improper Frivolous Determination",
            EnforcementOutcome.REINSERTION: "Reinsertion Without Notice",
        }
        return mapping.get(self.outcome, self.outcome.value)

    def _salutation(self) -> str:
        """Formal salutation."""
        return """
To Whom It May Concern:
"""

    def _introduction(self) -> str:
        """Opening paragraph establishing purpose with statutory citations."""
        accounts = " and ".join(v.account for v in self.request.violations)
        statutes = " and ".join(self.request.statutes)

        return f"""This letter constitutes formal notice of violation of the Fair Credit Reporting Act ("FCRA"), 15 U.S.C. § 1681 et seq., specifically {statutes}, arising from {self.entity_info['legal_name']}'s handling of the undersigned consumer's dispute regarding the following accounts: {accounts}.

The consumer demands immediate corrective action and preserves all remedies available under federal law, including those provided by 15 U.S.C. § 1681n and 15 U.S.C. § 1681o.
"""

    def _statutory_framework(self) -> str:
        """Single unified statutory theory section."""
        framework = STATUTORY_FRAMEWORKS.get(self.outcome)
        if not framework:
            return ""

        # Calculate deadline if dispute date provided
        deadline_date = "[thirty days from dispute receipt]"
        dispute_date_display = self.request.dispute_date or "[date of dispute]"

        if self.request.dispute_date:
            try:
                dispute_dt = datetime.strptime(self.request.dispute_date, "%Y-%m-%d")
                deadline_dt = dispute_dt + timedelta(days=30)
                deadline_date = deadline_dt.strftime("%B %d, %Y")
                dispute_date_display = dispute_dt.strftime("%B %d, %Y")
            except ValueError:
                pass

        body = framework["body"].format(
            entity=self.entity_info["legal_name"],
            dispute_date=dispute_date_display,
            deadline_date=deadline_date,
        )

        return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

                              STATUTORY FRAMEWORK

                   {self.request.statutory_theory}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{body}
"""

    def _violations_section(self) -> str:
        """Individual violation subsections."""
        header = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

                              SPECIFIC VIOLATIONS

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The following violations arise from {self.entity_info['legal_name']}'s response to the consumer's dispute. Each violation shares the statutory framework set forth above and constitutes a separate and independent basis for liability under 15 U.S.C. § 1681i.
"""
        violations_text = "\n".join(
            self._format_violation(i, v)
            for i, v in enumerate(self.request.violations, 1)
        )

        return header + violations_text

    def _format_violation(self, index: int, violation: ViolationRecord) -> str:
        """Format single violation subsection with complete enforcement language."""
        # Build factual narrative
        facts_narrative = []
        for fact in violation.facts:
            # Ensure proper sentence ending
            fact_clean = fact.rstrip('.')
            facts_narrative.append(f"{fact_clean}.")

        facts_formatted = " ".join(facts_narrative)

        # Outcome-specific conclusion
        if self.outcome == EnforcementOutcome.NO_RESPONSE:
            conclusion = f"""{self.entity_info['legal_name']} failed to respond to the consumer's dispute within the statutory period, constituting a violation of {violation.statute}."""
        elif self.outcome == EnforcementOutcome.VERIFIED:
            conclusion = f"""{self.entity_info['legal_name']} verified the information as accurate without correcting the deficiency and without disclosing the method of verification employed, constituting a violation of {violation.statute}."""
        elif self.outcome == EnforcementOutcome.REJECTED:
            conclusion = f"""{self.entity_info['legal_name']} improperly rejected the dispute as frivolous without satisfying the procedural requirements of {violation.statute}."""
        elif self.outcome == EnforcementOutcome.REINSERTION:
            conclusion = f"""{self.entity_info['legal_name']} reinserted previously deleted information without providing the required five-day written notice, constituting a violation of {violation.statute}."""
        else:
            conclusion = f"""This constitutes a violation of {violation.statute}."""

        return f"""

────────────────────────────────────────────────────────────────────────────────
VIOLATION {index}
────────────────────────────────────────────────────────────────────────────────

Account:                {violation.account}
Reporting Deficiency:   {violation.violation_type}
Statute:                {violation.statute}

{facts_formatted}

{conclusion}
"""

    def _demands_section(self) -> str:
        """Unified demands section with statutory authority."""
        demands_formatted = "\n".join(
            f"        {i}.  {demand}."
            for i, demand in enumerate(self.request.demands, 1)
        )

        # List all accounts for the demands section
        accounts_list = " and ".join(v.account for v in self.request.violations)

        return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

                              DEMANDED ACTIONS

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Pursuant to 15 U.S.C. § 1681i(a)(6) and § 1681i(a)(7), the consumer demands that {self.entity_info['legal_name']} take the following actions within fifteen (15) days of receipt of this letter:

{demands_formatted}

These demands apply to all accounts identified in this letter: {accounts_list}.

Failure to comply with any of the foregoing demands within the time specified will be documented and may form the basis for additional claims. The consumer will treat silence or partial compliance as refusal.
"""

    def _preservation_clause(self) -> str:
        """Minimal preservation clause - no damages lecture."""
        return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

                           PRESERVATION OF RIGHTS

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Nothing in this correspondence shall be construed as a waiver of any rights or remedies available under 15 U.S.C. §§ 1681n or 1681o for willful or negligent noncompliance.
"""

    def _closing(self) -> str:
        """Formal closing with signature block."""
        return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

All responses must be in writing and directed to the consumer at the address stated above. Telephone responses will not be accepted and will not be treated as compliance with this demand.

Time is of the essence.

Respectfully submitted,




__________________________________________
{self.request.consumer_name}
{self.letter_date}
"""


# =============================================================================
# PUBLIC API
# =============================================================================

def generate_enforcement_letter(request_data: Dict) -> str:
    """
    Generate enforcement letter from request dictionary.

    HARD GUARDS (all raise ValueError, no silent fallback):
    - NO_RESPONSE blocked unless deadline_date exists AND today > deadline_date
    - All violations must have valid statutes (no silent dropping)
    - Entity must resolve to canonical CRA name (TransUnion, Equifax, Experian)
    - Exactly ONE enforcement theory per letter
    - Mixed response outcomes prohibited

    Args:
        request_data: Dictionary containing:
            - consumer: {name, address}
            - entity: str (must be canonical: TransUnion, Equifax, Experian)
            - response_outcome: str (NO_RESPONSE, VERIFIED, REJECTED, REINSERTION)
            - statutory_theory: str (required - single theory per letter)
            - statutes: List[str] (required - must be from same statutory family)
            - violations: List[{account, violation_type, facts, statute}]
              - account: required
              - violation_type: required
              - facts: List[str]
              - statute: auto-assigned if missing, error if unassignable
            - demands: List[str]
            - delivery: str (optional)
            - dispute_date: str YYYY-MM-DD (required for NO_RESPONSE)
            - deadline_date: str YYYY-MM-DD (required for NO_RESPONSE, must be in past)
            - response_date: str YYYY-MM-DD (optional)

    Returns:
        Complete letter text ready for PDF generation.

    Raises:
        ValueError: If response_outcome is INVESTIGATING or UPDATED
        ValueError: If response_outcome is NO_RESPONSE and deadline hasn't passed (unless test_context=True)
        ValueError: If entity is not a canonical CRA name
        ValueError: If any violation has empty statute that cannot be auto-assigned
        ValueError: If statutory_theory is missing
        ValueError: If statutes span multiple incompatible statutory families

    Test Mode (test_context=True):
        - Bypasses deadline validation for same-day testing
        - Appends "TEST DOCUMENT – NOT MAILED" footer
        - Do NOT save, mail, or escalate test letters
    """
    # Parse violations with optional statute
    violations = [
        ViolationRecord(
            account=v.get("account", ""),
            violation_type=v.get("violation_type", ""),
            facts=v.get("facts", []),
            statute=v.get("statute", ""),  # May be empty - will be auto-assigned
        )
        for v in request_data.get("violations", [])
    ]

    # Build request object
    consumer = request_data.get("consumer", {})
    test_context = request_data.get("test_context", False)

    request = EnforcementLetterRequest(
        consumer_name=consumer.get("name", ""),
        consumer_address=consumer.get("address", ""),
        entity=request_data.get("entity", ""),
        response_outcome=request_data.get("response_outcome", ""),
        statutory_theory=request_data.get("statutory_theory", ""),
        statutes=request_data.get("statutes", []),
        violations=violations,
        demands=request_data.get("demands", []),
        delivery_method=request_data.get("delivery", "Certified Mail, Return Receipt Requested"),
        dispute_date=request_data.get("dispute_date"),
        deadline_date=request_data.get("deadline_date"),
        response_date=request_data.get("response_date"),
        test_context=test_context,
    )

    generator = EnforcementLetterGenerator(request)
    return generator.generate()


def validate_enforcement_outcome(outcome: str) -> bool:
    """Check if outcome is enforcement-ready."""
    return outcome in [e.value for e in EnforcementOutcome]


# =============================================================================
# NO_RESPONSE LETTER GENERATOR (FINAL TEMPLATE)
# =============================================================================

def generate_no_response_letter(
    consumer_name: str,
    consumer_address: str,
    entity: str,
    accounts: List[str],
    dispute_date: str,
    deadline_date: str,
    test_context: bool = False,
) -> str:
    """
    Generate NO_RESPONSE enforcement letter with exact required structure.

    Structure:
    1. Header (Certified Mail)
    2. Reference Line (Consumer + Entity + Outcome)
    3. Statutory Framework - 15 U.S.C. § 1681i(a)(1)(A)
    4. Timeline - Dispute sent, Deadline date, No response received
    5. Demanded Actions - Deletion, Written confirmation
    6. Rights Preservation (ONE sentence)
    7. Signature

    Prohibited: Damages lecture, CFPB/AG references, advisory language, mixed outcomes.

    Test Mode (test_context=True):
        - Bypasses deadline validation for same-day testing
        - Appends "TEST DOCUMENT – NOT MAILED" footer
        - Do NOT save, mail, or escalate test letters

    Raises:
        ValueError: If deadline_date has not passed (unless test_context=True)
        ValueError: If entity is not canonical
    """
    # Validate deadline has passed (skip in test mode)
    deadline_dt = datetime.strptime(deadline_date, "%Y-%m-%d").date()
    today = datetime.now().date()
    if not test_context and today <= deadline_dt:
        raise ValueError(
            f"Cannot generate NO_RESPONSE letter - deadline ({deadline_date}) has not passed"
        )

    # Validate entity
    if not _is_canonical_entity(entity):
        raise ValueError(
            f"Non-canonical entity: '{entity}'. Must be TransUnion, Equifax, or Experian."
        )

    # Get entity info
    entity_key = _normalize_entity_name(entity)
    entity_info = ENTITY_REGISTRY[entity_key]
    legal_name = entity_info["legal_name"]

    # Format dates
    dispute_dt = datetime.strptime(dispute_date, "%Y-%m-%d")
    dispute_date_formatted = dispute_dt.strftime("%B %d, %Y")
    deadline_date_formatted = deadline_dt.strftime("%B %d, %Y")
    letter_date = datetime.now().strftime("%B %d, %Y")

    # Format accounts
    accounts_formatted = ", ".join(accounts) if len(accounts) > 1 else accounts[0] if accounts else "[Account]"

    letter = f"""{letter_date}

Certified Mail, Return Receipt Requested

{legal_name}
{entity_info["address_line_1"]}
{entity_info["address_line_2"]}
{entity_info["city_state_zip"]}

        {consumer_name}
        {consumer_address}

RE:     Notice of Violation of Fair Credit Reporting Act
        Consumer: {consumer_name}
        Entity: {legal_name}
        Enforcement Posture: Failure to Respond Within Statutory Period

To Whom It May Concern:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

                              STATUTORY FRAMEWORK

                   15 U.S.C. § 1681i(a)(1)(A) - Duty to Reinvestigate

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Under 15 U.S.C. § 1681i(a)(1)(A), a consumer reporting agency that receives notice of a dispute from a consumer must, not later than 30 days after receiving the dispute, conduct a reasonable reinvestigation to determine whether the disputed information is inaccurate, and record the current status of the disputed information or delete the item from the file.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

                                   TIMELINE

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Dispute Sent:           {dispute_date_formatted}
Statutory Deadline:     {deadline_date_formatted}
Response Received:      NONE

The undersigned consumer submitted a written dispute to {legal_name} regarding the following account(s): {accounts_formatted}.

As of the date of this letter, {legal_name} has failed to provide any response. This failure to complete the reinvestigation within the statutory period constitutes a violation of 15 U.S.C. § 1681i(a)(1)(A).

Under 15 U.S.C. § 1681i(a)(5)(A), information that cannot be verified must be promptly deleted from the consumer's file.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

                              DEMANDED ACTIONS

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The consumer demands that {legal_name} immediately:

        1.  Delete all disputed information from the consumer's file pursuant to 15 U.S.C. § 1681i(a)(5)(A).

        2.  Provide written confirmation of deletion within five (5) business days.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

                           PRESERVATION OF RIGHTS

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Nothing in this correspondence shall be construed as a waiver of any rights or remedies available under 15 U.S.C. §§ 1681n or 1681o.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Respectfully submitted,




__________________________________________
{consumer_name}
{letter_date}
"""

    # Append test footer in test mode
    if test_context:
        letter += TEST_FOOTER

    return letter
