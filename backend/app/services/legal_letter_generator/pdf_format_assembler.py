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
import re


def _format_readable_date(date_str: str) -> str:
    """
    Convert date string to readable format.
    Input: "2025-01-26" or "2015-04-20"
    Output: "January 26, 2025" or "April 20, 2015"
    """
    if not date_str:
        return ""
    try:
        # Try parsing YYYY-MM-DD format
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%B %d, %Y")
    except ValueError:
        # If it's already in a different format or invalid, return as-is
        return date_str


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
            "monthly. The following accounts have not been updated in over 308 days (approximately 10 months), "
            "indicating the furnisher has failed to maintain current, accurate reporting as required by "
            "FCRA Section 623(a)(2) and Metro 2 Format guidelines:"
        ),
        resolution=(
            "These accounts require immediate verification and update with current information. If the furnisher "
            "cannot provide current, verified data, the stale information must be deleted pursuant to "
            "FCRA Section 611(a)(5)(A) as it cannot be confirmed accurate."
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
    v_type = (violation.get("violation_type") or "").lower()
    evidence = (violation.get("evidence") or "").lower()
    creditor = (violation.get("creditor_name") or "").lower()
    missing_field = (violation.get("missing_field") or "").lower()

    # FIRST: Check for specific missing field types - these should NOT be misclassified
    # Missing Scheduled Payment goes to OTHER (not DOFD!)
    if v_type == "missing_scheduled_payment" or missing_field == "scheduled_payment":
        return ViolationCategory.OTHER

    # Missing Date Opened goes to OTHER
    if v_type == "missing_date_opened" or missing_field == "date_opened":
        return ViolationCategory.OTHER

    # Check for obsolete accounts (>7 years / 2555 days)
    days = violation.get("days_since_update")
    if days and days > 2555:
        return ViolationCategory.OBSOLETE_ACCOUNT
    if v_type in ["obsolete_account", "outdated_information"]:
        return ViolationCategory.OBSOLETE_ACCOUNT
    if "obsolete" in evidence or "2555" in evidence or "7 year" in evidence or "seven year" in evidence:
        return ViolationCategory.OBSOLETE_ACCOUNT

    # Check for stale reporting (>= 308 days)
    if days and 308 <= days <= 2555:
        return ViolationCategory.STALE_REPORTING
    if v_type == "stale_reporting":
        return ViolationCategory.STALE_REPORTING
    if "stale" in evidence or "308 days" in evidence:
        return ViolationCategory.STALE_REPORTING

    # Check for missing DOFD - ONLY actual DOFD violations, not other missing fields
    if v_type in ["missing_dofd", "dofd_replaced_with_date_opened", "chargeoff_missing_dofd"]:
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
    """
    Group violations by their category for Roman numeral sections.

    IMPORTANT: If an account is OBSOLETE (should be deleted), we exclude it from
    all other categories. It's contradictory to say "delete this account" AND
    "fix this field on this account" - pick one. Deletion takes priority.
    """
    groups: Dict[ViolationCategory, List[Dict[str, Any]]] = {}

    # First pass: identify all accounts that are obsolete (should be deleted)
    obsolete_accounts = set()
    for violation in violations:
        category = _classify_violation(violation)
        if category == ViolationCategory.OBSOLETE_ACCOUNT:
            # Track by creditor + account number to identify the account
            account_key = (
                violation.get("creditor_name", ""),
                violation.get("account_number_masked", "")
            )
            obsolete_accounts.add(account_key)

    # Second pass: group violations, excluding obsolete accounts from non-obsolete categories
    for violation in violations:
        category = _classify_violation(violation)
        account_key = (
            violation.get("creditor_name", ""),
            violation.get("account_number_masked", "")
        )

        # If this account is obsolete but this violation is NOT the obsolete violation,
        # skip it - we don't need to fix fields on accounts that should be deleted
        if account_key in obsolete_accounts and category != ViolationCategory.OBSOLETE_ACCOUNT:
            continue

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


def _format_consumer_name(name: str) -> str:
    """
    Format consumer name properly with spaces.
    Fixes issues like "TIFFANYCBROWN" -> "TIFFANY C BROWN"
    Also removes trailing hyphens/punctuation.
    """
    if not name:
        return "[CONSUMER NAME]"

    # Remove trailing punctuation like hyphens
    name = name.rstrip('-').strip()

    # If name already has spaces, just return it
    if ' ' in name:
        return name

    # If name is all uppercase without spaces, try to detect word boundaries
    if name.isupper():
        # Common first names to help detect boundaries
        common_first_names = [
            'TIFFANY', 'MICHAEL', 'CHRISTOPHER', 'JENNIFER', 'ELIZABETH',
            'WILLIAM', 'MATTHEW', 'ANTHONY', 'STEPHANIE', 'PATRICIA',
            'JESSICA', 'ASHLEY', 'AMANDA', 'MELISSA', 'MICHELLE',
            'DAVID', 'JAMES', 'ROBERT', 'JOHN', 'MARY', 'LINDA',
            'BARBARA', 'SUSAN', 'MARGARET', 'DOROTHY', 'RICHARD',
            'JOSEPH', 'THOMAS', 'CHARLES', 'DANIEL', 'SARAH', 'KAREN',
            'NANCY', 'BETTY', 'HELEN', 'SANDRA', 'DONNA', 'CAROL',
        ]

        # Common last names
        common_last_names = [
            'BROWN', 'SMITH', 'JOHNSON', 'WILLIAMS', 'JONES', 'MILLER',
            'DAVIS', 'GARCIA', 'RODRIGUEZ', 'WILSON', 'MARTINEZ',
            'ANDERSON', 'TAYLOR', 'THOMAS', 'HERNANDEZ', 'MOORE',
            'MARTIN', 'JACKSON', 'THOMPSON', 'WHITE', 'LOPEZ', 'LEE',
            'GONZALEZ', 'HARRIS', 'CLARK', 'LEWIS', 'ROBINSON', 'WALKER',
            'PEREZ', 'HALL', 'YOUNG', 'ALLEN', 'SANCHEZ', 'WRIGHT',
            'KING', 'SCOTT', 'GREEN', 'BAKER', 'ADAMS', 'NELSON',
        ]

        # Try to match known first name + middle initial + last name
        for first in common_first_names:
            if name.startswith(first) and len(name) > len(first):
                remainder = name[len(first):]
                # Check if next char is a single letter (middle initial)
                if len(remainder) >= 2:
                    middle_initial = remainder[0]
                    possible_last = remainder[1:]
                    # Verify the last name looks reasonable (3+ chars)
                    if len(possible_last) >= 3:
                        return f"{first} {middle_initial} {possible_last}"
                # No middle initial - check for direct first + last
                for last in common_last_names:
                    if remainder == last:
                        return f"{first} {last}"

        # Fallback: Try pattern matching for FirstMiddleLast
        # Look for pattern like FIRST (4+ chars) + MIDDLE (1 char) + LAST (4+ chars)
        match = re.match(r'^([A-Z]{4,})([A-Z])([A-Z]{4,})$', name)
        if match:
            return f"{match.group(1)} {match.group(2)} {match.group(3)}"

        # Try FirstLast without middle (both 4+ chars)
        match = re.match(r'^([A-Z]{4,})([A-Z]{4,})$', name)
        if match:
            return f"{match.group(1)} {match.group(2)}"

    return name


def _format_address(address: str) -> str:
    """
    Format address properly with spaces.
    Fixes issues like "6NEW YORK" -> "6 NEW YORK"
    """
    if not address:
        return ""

    # Fix street numbers followed directly by text (no space)
    # Pattern: digits immediately followed by letters
    address = re.sub(r'(\d)([A-Za-z])', r'\1 \2', address)

    return address


def _format_city_state_zip(city_state_zip: str) -> str:
    """
    Format city/state/zip properly.
    Fixes issues like "10026-," -> "10026"
    """
    if not city_state_zip:
        return ""

    # Remove trailing punctuation like ",-" or "-,"
    city_state_zip = re.sub(r'[,\-]+\s*$', '', city_state_zip)

    # Remove dangling comma before zip
    city_state_zip = re.sub(r',\s*,', ',', city_state_zip)

    return city_state_zip.strip()


def _format_account_bullet(violation: Dict[str, Any]) -> str:
    """Format a single account as a bullet point with specific factual details."""
    creditor = violation.get("creditor_name", "Unknown")
    account = violation.get("account_number_masked", "")
    evidence = violation.get("evidence", "")
    days = violation.get("days_since_update")
    last_reported_date_raw = violation.get("last_reported_date", "")
    missing_field = violation.get("missing_field", "")

    # Convert date to readable format (January 26, 2025 instead of 2025-01-26)
    last_reported_date = _format_readable_date(last_reported_date_raw)

    # Build account identifier
    if account:
        account_id = f"{creditor} (Account #{account})"
    else:
        account_id = creditor

    # Add specific issue details
    details = []

    # Handle obsolete accounts (>2555 days)
    if days and days > 2555:
        years = round(days / 365, 1)
        if last_reported_date:
            details.append(f"Last reported {last_reported_date} ({days:,} days ago / {years} years - exceeds 7-year limit)")
        else:
            details.append(f"{days:,} days since last reported ({years} years - exceeds 7-year limit)")

    # Handle stale reporting (>=308 days but <=2555)
    elif days and days >= 308:
        if last_reported_date:
            details.append(f"Last reported {last_reported_date} ({days:,} days ago - stale reporting)")
        else:
            details.append(f"{days:,} days since last reported (stale reporting)")

    # Handle missing field violations
    if missing_field:
        field_impacts = {
            "scheduled_payment": "Missing Scheduled Payment field (Metro 2 Field 15) prevents verification of payment terms for accuracy",
            "dofd": "Missing Date of First Delinquency (Metro 2 Field 25) prevents proper obsolescence calculation under FCRA § 605(a)",
            "payment_history": "Missing Payment History Profile prevents accurate assessment of payment performance",
            "original_creditor": "Missing Original Creditor name violates FCRA § 623(a)(6) debt buyer reporting requirements",
            "balance": "Missing or inconsistent balance information prevents accurate credit utilization calculation",
        }
        field_lower = missing_field.lower().replace(" ", "_")
        if field_lower in field_impacts:
            details.append(f"{field_impacts[field_lower]}, violating duty under 15 U.S.C. § 1681e(b) to maintain maximum possible accuracy")
        else:
            details.append(f"Missing {missing_field} field prevents proper verification, violating 15 U.S.C. § 1681e(b)")

    # Add evidence if not already covered
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

Pursuant to FCRA Section 611(a)(6), upon completion of your reinvestigation, you must provide me with:

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


def _build_case_law_section(has_obsolete_accounts: bool = False) -> str:
    """
    Build the case law section at the bottom of the letter.

    Args:
        has_obsolete_accounts: If True, includes 15 U.S.C. § 1681c(c)(1) citation
                               for the 7-year obsolescence rule. Only relevant when
                               the dispute contains accounts exceeding the 7-year limit.
    """
    base_section = """Legal Standards and Applicable Case Law

The following legal standards govern your reinvestigation obligations:

Cushman v. Trans Union Corp., 115 F.3d 220 (3d Cir. 1997)
Holding: A CRA's reinvestigation procedures are unreasonable as a matter of law if the CRA merely parrots back information from the furnisher without independent verification. The reinvestigation must go beyond simply accepting the furnisher's verification.

Henson v. CSC Credit Services, 29 F.3d 280 (7th Cir. 1994)
Holding: A credit reporting agency cannot discharge its duty to reinvestigate by merely "rubber-stamping" the furnisher's original entry. The FCRA requires meaningful review of disputed information."""

    # Add obsolescence citation ONLY if dispute contains accounts >7 years old
    if has_obsolete_accounts:
        obsolescence_citation = """

15 U.S.C. § 1681c(c)(1) (FCRA Section 605(c)(1))
Statutory Requirement: The seven-year reporting period for adverse accounts must begin no later than 180 days after the Date of First Delinquency (DOFD). This date is fixed by federal law and cannot be reset by subsequent payments, charge-offs, or transfers. Reporting a later date (such as Date of Last Activity) to extend this period constitutes illegal re-aging."""
        base_section += obsolescence_citation

    closing = """

These cases establish that your reinvestigation must include review of original source documentation, not merely acceptance of furnisher verification codes. Failure to conduct a reasonable reinvestigation constitutes a violation of FCRA Section 611 and may expose you to statutory and actual damages."""

    return base_section + closing


def _format_discrepancy_bullet(discrepancy: Dict[str, Any]) -> str:
    """Format a single cross-bureau discrepancy as a bullet point."""
    creditor = discrepancy.get("creditor_name", "Unknown")
    field_name = discrepancy.get("field_name", "Data")
    values_by_bureau = discrepancy.get("values_by_bureau", {})
    violation_type = discrepancy.get("violation_type", "").replace("_", " ").title()

    # Build the bureau comparison string
    bureau_values = []
    for bureau, value in values_by_bureau.items():
        bureau_name = bureau.upper() if len(bureau) <= 3 else bureau.title()
        bureau_values.append(f"{bureau_name}: {value}")

    comparison_str = ", ".join(bureau_values)

    # Format the bullet
    return f"• {creditor}: {field_name} differs across bureaus ({comparison_str})"


def _build_cross_bureau_section(section_num: int, discrepancies: List[Dict[str, Any]]) -> str:
    """Build a Roman numeral section for cross-bureau discrepancies."""
    roman = _to_roman(section_num)

    lines = [
        f"{roman}. Cross-Bureau Reporting Inconsistencies (FCRA § 623(a)(1) / Metro 2 Compliance)",
        "",
        "Under FCRA Section 623(a)(1), furnishers are required to report accurate information to all "
        "consumer reporting agencies. The Metro 2 format requires consistent reporting across all bureaus. "
        "The following accounts show discrepancies between bureau reports, indicating potential furnisher "
        "reporting errors:",
        "",
    ]

    # Group discrepancies by creditor for cleaner output
    by_creditor: Dict[str, List[Dict[str, Any]]] = {}
    for disc in discrepancies:
        creditor = disc.get("creditor_name", "Unknown")
        if creditor not in by_creditor:
            by_creditor[creditor] = []
        by_creditor[creditor].append(disc)

    # Format bullets
    for creditor, cred_discrepancies in by_creditor.items():
        for disc in cred_discrepancies:
            lines.append(_format_discrepancy_bullet(disc))

    lines.extend([
        "",
        "These cross-bureau inconsistencies demonstrate that the furnisher is not reporting consistent, "
        "accurate information to all bureaus as required by law. Under FCRA Section 623(a)(1)(B), furnishers "
        "must correct and update information they determine to be inaccurate. The differing values across "
        "bureaus prove at minimum one bureau's data is inaccurate and must be investigated and corrected.",
    ])

    return "\n".join(lines)


def _build_signature_block(consumer_name: str, ssn_last4: str = None) -> str:
    """Build the signature block with enclosures."""
    # Format consumer name properly (remove hyphens, add spaces)
    formatted_name = _format_consumer_name(consumer_name)

    lines = [
        "Sincerely,",
        "",
        "",
        "",
        "________________________________",
        formatted_name,
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
        discrepancies: List[Dict[str, Any]] = None,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Generate a letter matching the PDF template format.

        Args:
            violations: List of violation dictionaries
            consumer: Consumer info with name, address, ssn_last4
            bureau: Target bureau (transunion, experian, equifax)
            discrepancies: Optional list of cross-bureau discrepancy dictionaries

        Returns:
            Tuple of (letter_content, metadata)
        """
        discrepancies = discrepancies or []
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

        # 5b. Cross-Bureau Discrepancies section (if any discrepancies provided)
        if discrepancies:
            sections.append(_build_cross_bureau_section(section_num, discrepancies))
            sections.append("")
            categories_used.append("cross_bureau")
            section_num += 1

        # 6. Reinvestigation Requirements
        sections.append(_build_reinvestigation_section())
        sections.append("")

        # 7. Case Law (at the very end before signature)
        # Include 15 U.S.C. § 1681c(c)(1) citation ONLY if dispute has obsolete accounts
        has_obsolete = ViolationCategory.OBSOLETE_ACCOUNT in grouped and len(grouped[ViolationCategory.OBSOLETE_ACCOUNT]) > 0
        sections.append(_build_case_law_section(has_obsolete_accounts=has_obsolete))
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
            "total_discrepancies": len(discrepancies),
            "bureau": bureau,
            "generated_at": datetime.now().isoformat(),
        }

        return letter_content, metadata

    def _build_header(self, consumer: Dict[str, Any], bureau: str) -> str:
        """Build the header with date and addresses."""
        today = datetime.now().strftime("%B %d, %Y")
        bureau_info = BUREAU_ADDRESSES.get(bureau.lower(), BUREAU_ADDRESSES["transunion"])

        # Format consumer name properly
        consumer_name = _format_consumer_name(consumer.get("name", "[CONSUMER NAME]"))

        lines = [
            f"Date: {today}",
            "",
            # Consumer address (sender)
            consumer_name,
        ]
        if consumer.get("address"):
            lines.append(_format_address(consumer["address"]))
        if consumer.get("city_state_zip"):
            lines.append(_format_city_state_zip(consumer["city_state_zip"]))

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
    discrepancies: List[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Generate a letter in PDF template format.

    Args:
        violations: List of violation dictionaries
        consumer: Consumer info with name, address, ssn_last4
        bureau: Target bureau
        seed: Optional random seed
        discrepancies: Optional list of cross-bureau discrepancy dictionaries

    Returns:
        Dict with 'letter', 'metadata', 'is_valid'
    """
    assembler = PDFFormatAssembler(seed=seed)
    letter, metadata = assembler.generate(violations, consumer, bureau, discrepancies=discrepancies)

    return {
        "letter": letter,
        "metadata": metadata,
        "is_valid": True,
        "validation_issues": [],
    }
