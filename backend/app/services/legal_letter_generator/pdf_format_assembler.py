"""
Legal Letter Generator - PDF Format Assembler
Generates dispute letters matching the exact PDF template structure.

Structure (from PDF template):
1. Title: "Credit Report Dispute Letter"
2. Header: Date, Bureau Address, RE: Formal Dispute
3. Introduction: FCRA 611 reference
4. Roman numeral sections grouped by VIOLATION TYPE (not by creditor)
5. Reinvestigation Requirements section
6. Case law at the very end
7. Signature block with enclosures
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum


class ViolationCategory(str, Enum):
    """Categories for grouping violations by error type."""
    MISSING_DOFD = "missing_dofd"
    OBSOLETE_ACCOUNT = "obsolete_account"
    STALE_REPORTING = "stale_reporting"
    AMOUNT_PAST_DUE_ERROR = "amount_past_due_error"
    BALANCE_ERROR = "balance_error"
    PAYMENT_STATUS_ERROR = "payment_status_error"
    MISSING_PAYMENT_HISTORY = "missing_payment_history"
    STUDENT_LOAN_VERIFICATION = "student_loan_verification"
    COLLECTION_VERIFICATION = "collection_verification"
    IDENTITY_ERROR = "identity_error"
    OTHER = "other"


@dataclass
class CategoryConfig:
    """Configuration for a violation category section."""
    title: str
    metro2_fields: str
    explanation: str
    resolution: str
    fcra_section: str


# Category configurations matching PDF template style
CATEGORY_CONFIGS: Dict[ViolationCategory, CategoryConfig] = {
    ViolationCategory.MISSING_DOFD: CategoryConfig(
        title="Accounts Missing Date of First Delinquency",
        metro2_fields="Metro 2 Field 25",
        explanation=(
            "The Date of First Delinquency (DOFD) is a mandatory field under Metro 2 reporting standards "
            "for any account that has experienced delinquency. Under FCRA Section 605(c), this date determines "
            "when the seven-year reporting period begins. The following accounts are reporting derogatory "
            "information without the required DOFD field:"
        ),
        resolution=(
            "These accounts must either provide the correct DOFD or be deleted from my credit file, as the "
            "absence of this required field makes the obsolescence calculation impossible and violates Metro 2 "
            "compliance standards."
        ),
        fcra_section="605(c)"
    ),
    ViolationCategory.OBSOLETE_ACCOUNT: CategoryConfig(
        title="Obsolete Accounts Exceeding Seven-Year Reporting Period",
        metro2_fields="Metro 2 Field 25 (DOFD) / FCRA § 605(a)",
        explanation=(
            "Under FCRA Section 605(a), adverse account information cannot be reported beyond seven years "
            "from the date of first delinquency. The following accounts have exceeded this statutory limit "
            "and must be immediately deleted:"
        ),
        resolution=(
            "These accounts are obsolete under federal law and must be deleted immediately. Continued "
            "reporting of obsolete information constitutes a willful violation of FCRA Section 605(a) "
            "(15 U.S.C. § 1681c(a))."
        ),
        fcra_section="605(a)"
    ),
    ViolationCategory.STALE_REPORTING: CategoryConfig(
        title="Accounts with Stale Reporting Data",
        metro2_fields="Metro 2 Field 8 (Date Reported)",
        explanation=(
            "Under Metro 2 reporting standards, furnishers are required to update account information "
            "at regular intervals. The following accounts have not been updated in an extended period, "
            "raising questions about the accuracy and currency of the reported information:"
        ),
        resolution=(
            "These accounts require verification and update. If current information cannot be obtained "
            "and verified, the stale data must be deleted pursuant to FCRA Section 611(a)(5)(A)."
        ),
        fcra_section="611(a)"
    ),
    ViolationCategory.AMOUNT_PAST_DUE_ERROR: CategoryConfig(
        title="Accounts with Amount Past Due Reporting Errors",
        metro2_fields="Metro 2 Fields 17A, 17B, and 21",
        explanation=(
            "The Amount Past Due and Current Balance fields (Metro 2 Fields 17A, 17B, and 21) must "
            "accurately reflect the account status. Accounts showing a past due amount on accounts that "
            "are current, closed, or paid violate Metro 2 accuracy requirements. The following accounts "
            "have discrepancies in these fields:"
        ),
        resolution=(
            "These reporting errors must be corrected. If the account is current or paid, the past due "
            "amount must be zeroed. If the account is closed, the balance fields must accurately reflect "
            "the final status."
        ),
        fcra_section="623(a)(1)"
    ),
    ViolationCategory.BALANCE_ERROR: CategoryConfig(
        title="Accounts with Balance Reporting Discrepancies",
        metro2_fields="Metro 2 Fields 15, 16, and 21",
        explanation=(
            "The balance-related fields (High Credit, Credit Limit, and Current Balance) must accurately "
            "reflect the account's financial status. The following accounts show balance discrepancies "
            "that materially affect credit scoring:"
        ),
        resolution=(
            "These balance discrepancies must be investigated and corrected. Inaccurate balance reporting "
            "directly impacts credit utilization calculations and scoring models."
        ),
        fcra_section="623(a)(2)"
    ),
    ViolationCategory.PAYMENT_STATUS_ERROR: CategoryConfig(
        title="Accounts with Payment Status Errors",
        metro2_fields="Metro 2 Fields 17A and 17B",
        explanation=(
            "The Account Status (Field 17A) and Payment Rating (Field 17B) must accurately reflect "
            "the current payment status of the account. The following accounts have payment status "
            "reporting that does not align with actual payment history:"
        ),
        resolution=(
            "Payment status errors must be corrected immediately. Under FCRA Section 623(a)(1), "
            "furnishers are prohibited from reporting information they know or should know is inaccurate."
        ),
        fcra_section="623(a)(1)"
    ),
    ViolationCategory.MISSING_PAYMENT_HISTORY: CategoryConfig(
        title="Accounts with Missing or Incomplete Payment History",
        metro2_fields="Metro 2 Field 25 (K2 Segment)",
        explanation=(
            "The Payment History Profile provides a month-by-month record of payment performance. "
            "The following accounts are missing required payment history data or have gaps that "
            "prevent accurate assessment:"
        ),
        resolution=(
            "Complete payment history must be provided or the account deleted. Incomplete payment "
            "history prevents proper dispute investigation under FCRA Section 611."
        ),
        fcra_section="611(a)"
    ),
    ViolationCategory.STUDENT_LOAN_VERIFICATION: CategoryConfig(
        title="Student Loan Accounts Requiring Verification",
        metro2_fields="Multiple Fields",
        explanation=(
            "Student loan accounts require accurate reporting of payment status, balance, and "
            "servicer information. The following student loan accounts have reporting discrepancies "
            "that require investigation:"
        ),
        resolution=(
            "These accounts must be verified with the current servicer and original loan documentation. "
            "Student loans frequently have servicer changes that can result in reporting errors."
        ),
        fcra_section="611(a)"
    ),
    ViolationCategory.COLLECTION_VERIFICATION: CategoryConfig(
        title="Collection Accounts Requiring Validation",
        metro2_fields="J2 Segment / Multiple Fields",
        explanation=(
            "Collection accounts must report the original creditor name and accurate balance information. "
            "Under FCRA Section 623(a)(6), debt buyers must report the original creditor. The following "
            "collection accounts have validation issues:"
        ),
        resolution=(
            "These collection accounts require complete chain of assignment documentation and original "
            "creditor verification. If proper documentation cannot be provided, the accounts must be deleted."
        ),
        fcra_section="623(a)(6)"
    ),
    ViolationCategory.IDENTITY_ERROR: CategoryConfig(
        title="Accounts with Identity Verification Issues",
        metro2_fields="Multiple Fields",
        explanation=(
            "Under FCRA Section 607(b), credit reporting agencies must maintain reasonable procedures "
            "to assure maximum possible accuracy. The following accounts may not belong to me or contain "
            "identity-related errors:"
        ),
        resolution=(
            "These accounts must be verified as belonging to me using original documentation including "
            "signed applications and identity verification records. If ownership cannot be verified, "
            "the accounts must be deleted."
        ),
        fcra_section="607(b)"
    ),
    ViolationCategory.OTHER: CategoryConfig(
        title="Additional Accounts Requiring Investigation",
        metro2_fields="Various Fields",
        explanation=(
            "The following accounts have reporting issues that require investigation under FCRA "
            "Section 611:"
        ),
        resolution=(
            "These items must be verified with original documentation. Any information that cannot "
            "be verified must be deleted pursuant to FCRA Section 611(a)(5)(A)."
        ),
        fcra_section="611"
    ),
}


# Bureau addresses
BUREAU_ADDRESSES = {
    "transunion": {
        "name": "TransUnion Consumer Solutions",
        "dept": "Dispute Department",
        "address": "P.O. Box 2000",
        "city_state_zip": "Chester, PA 19016-2000",
    },
    "experian": {
        "name": "Experian",
        "dept": "National Consumer Assistance Center",
        "address": "P.O. Box 4500",
        "city_state_zip": "Allen, TX 75013",
    },
    "equifax": {
        "name": "Equifax Information Services LLC",
        "dept": "Consumer Dispute Department",
        "address": "P.O. Box 740256",
        "city_state_zip": "Atlanta, GA 30374-0256",
    },
}


def _classify_violation(violation: Dict[str, Any]) -> ViolationCategory:
    """Classify a violation into a category for grouping."""
    v_type = violation.get("violation_type", "").lower()
    evidence = violation.get("evidence", "").lower()
    creditor = violation.get("creditor_name", "").lower()

    # Check for obsolete accounts (>7 years / 2555 days)
    days = violation.get("days_since_update")
    if days and days > 2555:
        return ViolationCategory.OBSOLETE_ACCOUNT
    if v_type in ["obsolete_account", "outdated_information"]:
        return ViolationCategory.OBSOLETE_ACCOUNT
    if "obsolete" in evidence or "2555" in evidence or "7 year" in evidence or "seven year" in evidence:
        return ViolationCategory.OBSOLETE_ACCOUNT

    # Check for stale reporting
    if days and 308 < days <= 2555:
        return ViolationCategory.STALE_REPORTING
    if v_type == "stale_reporting":
        return ViolationCategory.STALE_REPORTING
    if "stale" in evidence or "308 days" in evidence:
        return ViolationCategory.STALE_REPORTING

    # Check for missing DOFD
    if v_type in ["missing_dofd", "dofd_replaced_with_date_opened"]:
        return ViolationCategory.MISSING_DOFD
    if "dofd" in evidence or "date of first delinquency" in evidence:
        return ViolationCategory.MISSING_DOFD

    # Check for amount past due / balance errors
    if v_type in ["amount_past_due_error", "inaccurate_balance", "balance_discrepancy"]:
        return ViolationCategory.AMOUNT_PAST_DUE_ERROR
    if "past due" in evidence or "balance" in evidence:
        return ViolationCategory.BALANCE_ERROR

    # Check for payment status errors
    if v_type in ["incorrect_payment_status", "payment_history_error", "wrong_account_status"]:
        return ViolationCategory.PAYMENT_STATUS_ERROR

    # Check for missing payment history
    if v_type in ["missing_payment_history", "missing_payment_field"]:
        return ViolationCategory.MISSING_PAYMENT_HISTORY
    if "payment history" in evidence or "missing payment" in evidence:
        return ViolationCategory.MISSING_PAYMENT_HISTORY

    # Check for student loans
    if "student" in creditor or "loan" in creditor.split():
        if "navient" in creditor or "nelnet" in creditor or "mohela" in creditor or "fedloan" in creditor:
            return ViolationCategory.STUDENT_LOAN_VERIFICATION

    # Check for collections
    if v_type in ["collection_dispute"]:
        return ViolationCategory.COLLECTION_VERIFICATION
    if "collection" in creditor or "recovery" in creditor:
        return ViolationCategory.COLLECTION_VERIFICATION

    # Check for identity errors
    if v_type in ["not_mine", "identity_error", "mixed_file"]:
        return ViolationCategory.IDENTITY_ERROR

    return ViolationCategory.OTHER


def _group_violations_by_category(violations: List[Dict[str, Any]]) -> Dict[ViolationCategory, List[Dict[str, Any]]]:
    """Group violations by their category for Roman numeral sections."""
    groups: Dict[ViolationCategory, List[Dict[str, Any]]] = {}

    for violation in violations:
        category = _classify_violation(violation)
        if category not in groups:
            groups[category] = []
        groups[category].append(violation)

    return groups


def _to_roman(num: int) -> str:
    """Convert integer to Roman numeral."""
    val = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1]
    syms = ['M', 'CM', 'D', 'CD', 'C', 'XC', 'L', 'XL', 'X', 'IX', 'V', 'IV', 'I']
    roman_num = ''
    for i in range(len(val)):
        count = int(num / val[i])
        if count:
            roman_num += syms[i] * count
            num -= val[i] * count
    return roman_num


def _format_account_bullet(violation: Dict[str, Any]) -> str:
    """Format a single account as a bullet point."""
    creditor = violation.get("creditor_name", "Unknown")
    account = violation.get("account_number_masked", "")
    evidence = violation.get("evidence", "")
    days = violation.get("days_since_update")

    # Build account identifier
    if account:
        account_id = f"{creditor} (Account #{account})"
    else:
        account_id = creditor

    # Add specific issue details
    details = []
    if days:
        if days > 2555:
            years = round(days / 365, 1)
            details.append(f"{days:,} days since last update ({years} years - exceeds 7-year limit)")
        elif days > 308:
            details.append(f"{days:,} days since last update (stale reporting)")

    if evidence and evidence not in str(details):
        # Clean up evidence text
        evidence_clean = evidence.strip()
        if evidence_clean:
            details.append(evidence_clean)

    if details:
        return f"• {account_id}: {'; '.join(details)}"
    return f"• {account_id}"


def _build_reinvestigation_section() -> str:
    """Build the Reinvestigation Requirements section."""
    return """Reinvestigation Requirements

Under FCRA Section 611(a), you are required to conduct a reinvestigation of the disputed items within 30 days of receiving this dispute. This reinvestigation must be reasonable and cannot consist of simply verifying the information with the furnisher.

Pursuant to FCRA Section 611(a)(6)(B)(iii), upon completion of your reinvestigation, you must provide me with:

1. Written notice of the results of the reinvestigation
2. A description of the procedure used to determine the accuracy of the disputed information
3. A copy of my credit file reflecting any changes made as a result of the reinvestigation
4. A notice that I may request a description of the method of verification

If any disputed item cannot be verified through original documentation, it must be deleted from my credit file pursuant to FCRA Section 611(a)(5)(A).

Method of Verification Requirements

I specifically request that you provide the method of verification for each disputed item as required by FCRA Section 611(a)(7). This must include:

• The business name, address, and telephone number of each furnisher contacted
• The specific documents or records reviewed during verification
• The date of verification and the name of the individual who performed it

A simple automated verification response from the furnisher is insufficient. Per Cushman v. Trans Union Corp., 115 F.3d 220 (3d Cir. 1997), your reinvestigation must involve independent verification using original source documentation."""


def _build_case_law_section() -> str:
    """Build the case law section at the bottom of the letter."""
    return """Legal Standards and Applicable Case Law

The following legal standards govern your reinvestigation obligations:

Cushman v. Trans Union Corp., 115 F.3d 220 (3d Cir. 1997)
Holding: A CRA's reinvestigation procedures are unreasonable as a matter of law if the CRA merely parrots back information from the furnisher without independent verification. The reinvestigation must go beyond simply accepting the furnisher's verification.

Henson v. CSC Credit Services, 29 F.3d 280 (7th Cir. 1994)
Holding: A credit reporting agency cannot discharge its duty to reinvestigate by merely "rubber-stamping" the furnisher's original entry. The FCRA requires meaningful review of disputed information.

These cases establish that your reinvestigation must include review of original source documentation, not merely acceptance of furnisher verification codes. Failure to conduct a reasonable reinvestigation constitutes a violation of FCRA Section 611 and may expose you to statutory and actual damages."""


def _build_signature_block(consumer_name: str, ssn_last4: str = None) -> str:
    """Build the signature block with enclosures."""
    lines = [
        "Sincerely,",
        "",
        "",
        "",
        "________________________________",
        consumer_name,
        "",
        "Date: ________________________",
    ]

    if ssn_last4:
        lines.extend([
            "",
            f"SSN (Last 4 Digits): XXX-XX-{ssn_last4}",
        ])

    lines.extend([
        "",
        "",
        "Enclosures:",
        "• Copy of credit report with disputed items highlighted",
        "• Copy of government-issued photo identification",
        "• Proof of current address (utility bill or bank statement)",
        "",
        "THIS LETTER SENT VIA CERTIFIED MAIL, RETURN RECEIPT REQUESTED",
    ])

    return "\n".join(lines)


class PDFFormatAssembler:
    """
    Assembler that generates letters matching the PDF template format exactly.

    Key features:
    - Roman numeral sections grouped by violation TYPE (not by creditor)
    - Each section has: explanation paragraph, account bullets, resolution paragraph
    - Reinvestigation Requirements section after disputed items
    - Case law at the very end
    - Professional signature block with enclosures
    """

    def __init__(self, seed: int = None):
        """Initialize the assembler."""
        self.seed = seed or 0

    def generate(
        self,
        violations: List[Dict[str, Any]],
        consumer: Dict[str, Any],
        bureau: str,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Generate a letter matching the PDF template format.

        Args:
            violations: List of violation dictionaries
            consumer: Consumer info with name, address, ssn_last4
            bureau: Target bureau (transunion, experian, equifax)

        Returns:
            Tuple of (letter_content, metadata)
        """
        sections = []

        # 1. Title
        sections.append("Credit Report Dispute Letter")
        sections.append("")

        # 2. Header with date and bureau address
        sections.append(self._build_header(consumer, bureau))
        sections.append("")

        # 3. RE: line
        sections.append("RE: Formal Dispute - Inaccurate Account Information Requiring Investigation")
        sections.append("")

        # 4. Salutation and Introduction
        sections.append("To Whom It May Concern:")
        sections.append("")
        sections.append(self._build_introduction())
        sections.append("")

        # 5. Roman numeral sections grouped by violation type
        grouped = _group_violations_by_category(violations)
        section_num = 1
        categories_used = []

        # Define category order for consistent output
        category_order = [
            ViolationCategory.OBSOLETE_ACCOUNT,
            ViolationCategory.MISSING_DOFD,
            ViolationCategory.STALE_REPORTING,
            ViolationCategory.AMOUNT_PAST_DUE_ERROR,
            ViolationCategory.BALANCE_ERROR,
            ViolationCategory.PAYMENT_STATUS_ERROR,
            ViolationCategory.MISSING_PAYMENT_HISTORY,
            ViolationCategory.STUDENT_LOAN_VERIFICATION,
            ViolationCategory.COLLECTION_VERIFICATION,
            ViolationCategory.IDENTITY_ERROR,
            ViolationCategory.OTHER,
        ]

        for category in category_order:
            if category in grouped and grouped[category]:
                section_content = self._build_category_section(
                    section_num, category, grouped[category]
                )
                sections.append(section_content)
                sections.append("")
                categories_used.append(category.value)
                section_num += 1

        # 6. Reinvestigation Requirements
        sections.append(_build_reinvestigation_section())
        sections.append("")

        # 7. Case Law (at the very end before signature)
        sections.append(_build_case_law_section())
        sections.append("")

        # 8. Signature Block
        sections.append(_build_signature_block(
            consumer.get("name", "[CONSUMER NAME]"),
            consumer.get("ssn_last4")
        ))

        # Combine all sections
        letter_content = "\n".join(sections)

        # Build metadata
        metadata = {
            "format": "pdf_template",
            "sections_generated": section_num - 1,
            "categories_used": categories_used,
            "total_violations": len(violations),
            "bureau": bureau,
            "generated_at": datetime.now().isoformat(),
        }

        return letter_content, metadata

    def _build_header(self, consumer: Dict[str, Any], bureau: str) -> str:
        """Build the header with date and addresses."""
        today = datetime.now().strftime("%B %d, %Y")
        bureau_info = BUREAU_ADDRESSES.get(bureau.lower(), BUREAU_ADDRESSES["transunion"])

        lines = [
            f"Date: {today}",
            "",
            # Consumer address (sender)
            consumer.get("name", "[CONSUMER NAME]"),
        ]
        if consumer.get("address"):
            lines.append(consumer["address"])
        if consumer.get("city_state_zip"):
            lines.append(consumer["city_state_zip"])

        lines.extend([
            "",
            # Bureau address (recipient)
            bureau_info["name"],
            bureau_info["dept"],
            bureau_info["address"],
            bureau_info["city_state_zip"],
        ])

        return "\n".join(lines)

    def _build_introduction(self) -> str:
        """Build the introduction paragraph referencing FCRA 611."""
        return (
            "I am writing to formally dispute inaccurate information appearing on my credit report "
            "maintained by your agency. Pursuant to the Fair Credit Reporting Act (FCRA), Section 611 "
            "(15 U.S.C. § 1681i), I am exercising my right to dispute the accuracy of the items "
            "identified below and request that you conduct a reinvestigation of each disputed item.\n\n"
            "After careful review of my credit report, I have identified the following accounts that "
            "contain inaccurate, incomplete, or unverifiable information that must be investigated and "
            "corrected or deleted:"
        )

    def _build_category_section(
        self,
        section_num: int,
        category: ViolationCategory,
        violations: List[Dict[str, Any]]
    ) -> str:
        """Build a Roman numeral section for a violation category."""
        config = CATEGORY_CONFIGS[category]
        roman = _to_roman(section_num)

        lines = [
            f"{roman}. {config.title} ({config.metro2_fields})",
            "",
            config.explanation,
            "",
        ]

        # Add account bullets
        for violation in violations:
            lines.append(_format_account_bullet(violation))

        lines.extend([
            "",
            config.resolution,
        ])

        return "\n".join(lines)


# Convenience function
def generate_pdf_format_letter(
    violations: List[Dict[str, Any]],
    consumer: Dict[str, Any],
    bureau: str,
    seed: int = None,
) -> Dict[str, Any]:
    """
    Generate a letter in PDF template format.

    Args:
        violations: List of violation dictionaries
        consumer: Consumer info with name, address, ssn_last4
        bureau: Target bureau
        seed: Optional random seed

    Returns:
        Dict with 'letter', 'metadata', 'is_valid'
    """
    assembler = PDFFormatAssembler(seed=seed)
    letter, metadata = assembler.generate(violations, consumer, bureau)

    return {
        "letter": letter,
        "metadata": metadata,
        "is_valid": True,
        "validation_issues": [],
    }
