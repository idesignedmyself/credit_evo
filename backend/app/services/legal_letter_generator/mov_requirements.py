"""
Legal Letter Generator - Method of Verification (MOV) Requirements
Defines MOV requirements for FCRA compliance and dispute letters.
"""
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


class MOVCategory(str, Enum):
    """Categories of Method of Verification requirements."""
    ACCOUNT_OWNERSHIP = "account_ownership"
    PAYMENT_HISTORY = "payment_history"
    BALANCE_VERIFICATION = "balance_verification"
    DATE_VERIFICATION = "date_verification"
    STATUS_VERIFICATION = "status_verification"
    IDENTITY_VERIFICATION = "identity_verification"
    CONTRACT_VERIFICATION = "contract_verification"
    COLLECTION_VERIFICATION = "collection_verification"


@dataclass
class MOVRequirement:
    """A specific MOV requirement with legal basis."""
    name: str
    category: MOVCategory
    description: str
    required_documents: List[str]
    legal_basis: str
    fcra_section: str
    demand_language: str


# Comprehensive MOV requirements library
MOV_REQUIREMENTS: Dict[str, MOVRequirement] = {
    "original_contract": MOVRequirement(
        name="Original Signed Contract",
        category=MOVCategory.CONTRACT_VERIFICATION,
        description="The original signed contract or agreement establishing the debt obligation.",
        required_documents=[
            "Original signed credit agreement",
            "Signed promissory note",
            "Copy of credit application with signature",
            "Terms and conditions accepted at account opening"
        ],
        legal_basis="Under FCRA Section 611(a)(1), furnishers must maintain and produce documentation supporting the existence and terms of the alleged obligation.",
        fcra_section="611(a)(1)",
        demand_language="I demand production of the original signed contract or credit agreement establishing this alleged debt. A computer-generated statement is not sufficient verification."
    ),
    "account_statements": MOVRequirement(
        name="Complete Account Statements",
        category=MOVCategory.BALANCE_VERIFICATION,
        description="Complete account statements showing the transaction history and balance calculations.",
        required_documents=[
            "Monthly or periodic account statements",
            "Transaction history from account opening",
            "Payment application records",
            "Interest and fee calculations"
        ],
        legal_basis="FCRA Section 623(b)(1) requires furnishers to review all relevant information when investigating disputes, including statements proving balance accuracy.",
        fcra_section="623(b)(1)",
        demand_language="I require complete account statements from the date of account opening through the present date, demonstrating how the reported balance was calculated."
    ),
    "payment_records": MOVRequirement(
        name="Payment History Documentation",
        category=MOVCategory.PAYMENT_HISTORY,
        description="Documentation of all payments received and their application to the account.",
        required_documents=[
            "Payment receipt records",
            "Cleared check images",
            "Electronic payment confirmations",
            "Payment posting history"
        ],
        legal_basis="Per Cushman v. Trans Union, payment history must be independently verified, not simply accepted from the furnisher without documentation.",
        fcra_section="611",
        demand_language="Provide documentation of all payments received on this account, including dates received, amounts, and how each payment was applied."
    ),
    "date_verification": MOVRequirement(
        name="Account Date Verification",
        category=MOVCategory.DATE_VERIFICATION,
        description="Documentation verifying reported dates including date opened, date of last activity, and date of first delinquency.",
        required_documents=[
            "Account opening documentation with date",
            "Date of first delinquency calculation worksheet",
            "Last payment date verification",
            "Account closure documentation"
        ],
        legal_basis="FCRA Section 605(a) requires accurate reporting of dates, particularly the date of first delinquency which determines the seven-year reporting period.",
        fcra_section="605(a)",
        demand_language="Verify and provide documentation for all reported dates, including date opened, date of last activity, and specifically the date of first delinquency used for obsolescence calculation."
    ),
    "assignment_chain": MOVRequirement(
        name="Complete Assignment Chain",
        category=MOVCategory.ACCOUNT_OWNERSHIP,
        description="Documentation showing the chain of ownership from original creditor through all subsequent purchasers.",
        required_documents=[
            "Original creditor account records",
            "Bill of sale or assignment documents",
            "Chain of title documentation",
            "Transfer notification letters"
        ],
        legal_basis="Under FCRA Section 623(a)(6), debt buyers must report the original creditor name. The assignment chain establishes legal standing to collect and report.",
        fcra_section="623(a)(6)",
        demand_language="Provide complete chain of assignment documentation showing legal transfer of this account from the original creditor to the current reporter."
    ),
    "identity_proof": MOVRequirement(
        name="Consumer Identity Verification",
        category=MOVCategory.IDENTITY_VERIFICATION,
        description="Documentation proving the account belongs to the consumer identified in the report.",
        required_documents=[
            "Signed application or contract",
            "Identification used at account opening",
            "Social Security Number verification",
            "Address verification at time of application"
        ],
        legal_basis="FCRA Section 607(b) requires maximum possible accuracy, including verifying the account belongs to the correct consumer.",
        fcra_section="607(b)",
        demand_language="Verify and provide documentation proving this account belongs to me and was opened with my authorization. Include copies of any identification or application used."
    ),
    "collection_validation": MOVRequirement(
        name="Collection Account Validation",
        category=MOVCategory.COLLECTION_VERIFICATION,
        description="Documentation validating a collection account including original debt documentation.",
        required_documents=[
            "Original creditor account documentation",
            "Itemized statement of debt",
            "Collection agency authorization",
            "Judgment documentation (if applicable)"
        ],
        legal_basis="While FDCPA Section 809 governs debt validation, FCRA requires collectors to verify accuracy before reporting. See Gorman v. Wolpoff & Abramson.",
        fcra_section="623(b)",
        demand_language="As a collection account, provide complete validation including original creditor documentation, itemized statement of the alleged debt, and authorization to collect."
    ),
    "charge_off_documentation": MOVRequirement(
        name="Charge-Off Documentation",
        category=MOVCategory.STATUS_VERIFICATION,
        description="Documentation supporting the charge-off status and date.",
        required_documents=[
            "Internal charge-off memo or decision",
            "Account status at time of charge-off",
            "Balance at charge-off",
            "1099-C if debt was cancelled"
        ],
        legal_basis="Charge-off status significantly impacts credit scores. FCRA accuracy requirements demand documentation supporting this adverse status.",
        fcra_section="623(a)(1)",
        demand_language="Provide documentation supporting the charge-off status, including the charge-off date, balance at charge-off, and any 1099-C issued for cancelled debt."
    ),
    "late_payment_proof": MOVRequirement(
        name="Late Payment Documentation",
        category=MOVCategory.PAYMENT_HISTORY,
        description="Documentation proving specific late payments were actually late.",
        required_documents=[
            "Payment due date documentation",
            "Actual payment receipt date",
            "Grace period terms",
            "Late fee assessment records"
        ],
        legal_basis="Late payment entries must be accurate per FCRA Section 623(a)(1). Furnishers must prove the payment was received after the due date plus any grace period.",
        fcra_section="623(a)(1)",
        demand_language="For each reported late payment, provide documentation showing: (1) the contractual due date, (2) any applicable grace period, and (3) the actual date payment was received."
    ),
    "metro2_compliance": MOVRequirement(
        name="Metro-2 Format Compliance",
        category=MOVCategory.STATUS_VERIFICATION,
        description="Documentation that reported data complies with Metro-2 Format requirements.",
        required_documents=[
            "Metro-2 data submission records",
            "Field-by-field verification",
            "Compliance audit documentation",
            "Error correction history"
        ],
        legal_basis="Industry standard Metro-2 Format defines data quality requirements. Non-compliance indicates procedural failures under FCRA Section 607(b).",
        fcra_section="607(b)",
        demand_language="Verify that all data reported for this account complies with CDIA Metro-2 Format requirements and provide documentation of compliance review."
    ),
}


def get_mov_requirement(name: str) -> Optional[MOVRequirement]:
    """Get MOV requirement by name."""
    name_key = name.lower().replace(" ", "_").replace("-", "_")
    if name_key in MOV_REQUIREMENTS:
        return MOV_REQUIREMENTS[name_key]

    # Partial match
    for key, req in MOV_REQUIREMENTS.items():
        if name_key in key or key in name_key:
            return req

    return None


def get_mov_by_category(category: MOVCategory) -> List[MOVRequirement]:
    """Get all MOV requirements in a category."""
    return [req for req in MOV_REQUIREMENTS.values() if req.category == category]


def get_mov_for_violation_type(violation_type: str) -> List[MOVRequirement]:
    """Get relevant MOV requirements for a violation type."""
    violation_mov_map = {
        "inaccurate_balance": ["account_statements", "payment_records"],
        "incorrect_payment_status": ["payment_records", "late_payment_proof"],
        "wrong_account_status": ["charge_off_documentation", "metro2_compliance"],
        "balance_discrepancy": ["account_statements", "payment_records"],
        "payment_history_error": ["payment_records", "late_payment_proof"],
        "incorrect_dates": ["date_verification"],
        "outdated_information": ["date_verification"],
        "obsolete_account": ["date_verification"],
        "not_mine": ["identity_proof", "original_contract"],
        "identity_error": ["identity_proof"],
        "mixed_file": ["identity_proof"],
        "collection_dispute": ["collection_validation", "assignment_chain"],
        "charge_off_dispute": ["charge_off_documentation", "account_statements"],
        "duplicate_account": ["original_contract", "identity_proof"],
        "wrong_creditor_name": ["assignment_chain", "original_contract"],
    }

    mov_keys = violation_mov_map.get(violation_type, ["original_contract", "account_statements"])
    return [MOV_REQUIREMENTS[key] for key in mov_keys if key in MOV_REQUIREMENTS]


def build_mov_demand(violations: List[Dict], include_case_law: bool = True) -> str:
    """
    Build a comprehensive MOV demand section for a dispute letter.

    Args:
        violations: List of violation dictionaries
        include_case_law: Whether to include case law citations

    Returns:
        Formatted MOV demand text for inclusion in letter
    """
    # Collect unique MOV requirements based on violations
    required_movs: Dict[str, MOVRequirement] = {}

    for violation in violations:
        v_type = violation.get("violation_type", "")
        for mov in get_mov_for_violation_type(v_type):
            required_movs[mov.name] = mov

    if not required_movs:
        # Default MOV requirements
        required_movs = {
            "Original Signed Contract": MOV_REQUIREMENTS["original_contract"],
            "Complete Account Statements": MOV_REQUIREMENTS["account_statements"],
            "Payment History Documentation": MOV_REQUIREMENTS["payment_records"],
        }

    # Build the demand text
    if include_case_law:
        lines = [
            "METHOD OF VERIFICATION REQUIRED",
            "",
            "Pursuant to FCRA Sections 611 and 623, I demand that you verify the disputed information",
            "using the following methods of verification. A simple verification response from the",
            "furnisher is insufficient under Cushman v. Trans Union Corp., 115 F.3d 220 (3d Cir. 1997).",
            "",
            "I require production of the following documentation:",
            ""
        ]
    else:
        lines = [
            "METHOD OF VERIFICATION REQUIRED",
            "",
            "Pursuant to FCRA Sections 611 and 623, I demand that you verify the disputed information",
            "using the following methods of verification. A simple verification response from the",
            "furnisher is not sufficient to satisfy the reasonable reinvestigation requirement.",
            "",
            "I require production of the following documentation:",
            ""
        ]

    for idx, (name, mov) in enumerate(required_movs.items(), 1):
        lines.append(f"{idx}. **{mov.name}**")
        lines.append(f"   {mov.description}")
        lines.append("")
        lines.append("   Required documents:")
        for doc in mov.required_documents:
            lines.append(f"   - {doc}")
        lines.append("")
        if include_case_law:
            lines.append(f"   Legal Basis: {mov.legal_basis}")
            lines.append("")

    lines.extend([
        "",
        "If you are unable to provide the above documentation, you must delete the disputed",
        "information from my credit file pursuant to FCRA Section 611(a)(5)(A), which requires",
        "deletion of information that cannot be verified.",
        ""
    ])

    return "\n".join(lines)


def format_mov_for_letter(mov: MOVRequirement, tone: str = "formal") -> str:
    """
    Format an MOV requirement for inclusion in a letter.

    Args:
        mov: The MOV requirement
        tone: Letter tone (formal, aggressive, etc.)

    Returns:
        Formatted text
    """
    if tone == "aggressive":
        return f"""
**{mov.name.upper()}**

I DEMAND immediate production of the following:
{chr(10).join('- ' + doc for doc in mov.required_documents)}

{mov.demand_language}

Legal Authority: {mov.legal_basis}
Applicable FCRA Section: {mov.fcra_section}
"""
    else:  # formal
        return f"""
**{mov.name}**

Pursuant to FCRA Section {mov.fcra_section}, I request verification through the following documentation:

{chr(10).join('- ' + doc for doc in mov.required_documents)}

{mov.demand_language}

Legal Basis: {mov.legal_basis}
"""


class MOVBuilder:
    """Builds MOV requirement sections for legal letters."""

    def __init__(self, violations: List[Dict] = None, tone: str = "formal", include_case_law: bool = True):
        self.violations = violations or []
        self.tone = tone
        self.include_case_law = include_case_law
        self.required_movs: Dict[str, MOVRequirement] = {}
        if self.violations:
            self._analyze_violations()

    def _analyze_violations(self) -> None:
        """Analyze violations to determine required MOVs."""
        for violation in self.violations:
            v_type = violation.get("violation_type", "")
            for mov in get_mov_for_violation_type(v_type):
                self.required_movs[mov.name] = mov

        # Always include basic MOV requirements
        self.required_movs["Original Signed Contract"] = MOV_REQUIREMENTS["original_contract"]
        self.required_movs["Complete Account Statements"] = MOV_REQUIREMENTS["account_statements"]

    def get_mov_list(self) -> List[MOVRequirement]:
        """Get list of required MOVs."""
        return list(self.required_movs.values())

    def build_section(self) -> str:
        """Build the complete MOV section for the letter."""
        return build_mov_demand(self.violations, self.include_case_law)

    def get_summary(self) -> str:
        """Get a summary of MOV requirements."""
        categories = set(mov.category for mov in self.required_movs.values())
        return f"This dispute requires verification in {len(categories)} categories with {len(self.required_movs)} specific documentation requirements."


# Standard MOV demand language for common scenarios
STANDARD_MOV_DEMAND = """
METHOD OF VERIFICATION (MOV) REQUIREMENTS

Under the Fair Credit Reporting Act, you are required to conduct a reasonable reinvestigation
of disputed information. Per Cushman v. Trans Union Corp., 115 F.3d 220 (3d Cir. 1997), simply
relaying the furnisher's verification is insufficient. I demand that you obtain and review
the following documentation:

1. ORIGINAL CONTRACT/AGREEMENT
   - Signed credit application or agreement
   - Terms and conditions accepted
   - Proof of my authorization

2. COMPLETE ACCOUNT HISTORY
   - All account statements from opening to present
   - Complete payment history with dates
   - All fees and interest calculations

3. VERIFICATION OF REPORTED DATA
   - Source documentation for each disputed data element
   - Proof that Metro-2 Format requirements are met
   - Documentation supporting the account status

If the above documentation cannot be produced, the disputed information must be deleted
pursuant to FCRA Section 611(a)(5)(A).
"""

COLLECTION_MOV_DEMAND = """
COLLECTION ACCOUNT VERIFICATION REQUIREMENTS

As this is a collection account, I require enhanced verification including:

1. ORIGINAL CREDITOR DOCUMENTATION
   - Original signed contract with original creditor
   - Final account statement from original creditor
   - Original creditor's internal account records

2. CHAIN OF ASSIGNMENT
   - Complete chain of title from original creditor
   - Bill of sale or assignment agreement
   - Notification of assignment sent to consumer

3. VALIDATION OF DEBT
   - Itemized statement of the alleged debt
   - Explanation of all fees and interest added
   - License to collect in my state of residence

Per FCRA Section 623(a)(6), the original creditor name must be reported. If the assignment
chain or original debt cannot be verified, this account must be deleted.
"""
