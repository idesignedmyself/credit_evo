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
    TIME_BARRED_DEBT = "time_barred_debt"  # Collections past statute of limitations
    STALE_REPORTING = "stale_reporting"
    AMOUNT_PAST_DUE_ERROR = "amount_past_due_error"
    BALANCE_ERROR = "balance_error"
    PAYMENT_STATUS_ERROR = "payment_status_error"
    PHANTOM_LATE_PAYMENT = "phantom_late_payment"  # Late markers during $0 due or forbearance
    PAID_COLLECTION_CONTRADICTION = "paid_collection_contradiction"  # Paid status vs balance contradictions
    ILLOGICAL_DELINQUENCY = "illogical_delinquency"  # Impossible delinquency progression (0->60) or stagnant lates
    DOUBLE_JEOPARDY = "double_jeopardy"  # OC and Collector BOTH report balance for same debt
    MISSING_PAYMENT_HISTORY = "missing_payment_history"
    STUDENT_LOAN_VERIFICATION = "student_loan_verification"
    COLLECTION_VERIFICATION = "collection_verification"
    IDENTITY_ERROR = "identity_error"
    DECEASED_INDICATOR = "deceased_indicator"  # Living consumer marked as deceased - CRITICAL
    CHILD_IDENTITY_THEFT = "child_identity_theft"  # Account opened while consumer was a minor - CRITICAL
    # Public Record violations
    PUBLIC_RECORD_NCAP = "public_record_ncap"  # Civil Judgment/Tax Lien appearing post-NCAP 2017
    PUBLIC_RECORD_JUDGMENT_BALANCE = "public_record_judgment_balance"  # Satisfied judgment with balance
    PUBLIC_RECORD_BANKRUPTCY_OBSOLETE = "public_record_bankruptcy_obsolete"  # Obsolete bankruptcy > 7/10 years
    # Medical Debt violations (NCAP 2022/2023)
    MEDICAL_UNDER_500 = "medical_under_500"  # Unpaid medical collection < $500 (banned April 2023)
    MEDICAL_PAID_REPORTING = "medical_paid_reporting"  # Paid medical collection still reporting (banned July 2022)
    # Post-Settlement & Cross-Bureau Gaps
    POST_SETTLEMENT_NEGATIVE = "post_settlement_negative"  # Late markers reported AFTER account closed/settled
    MISSING_TRADELINE_INFO = "missing_tradeline_info"  # Account missing from some bureaus (explains score gaps)
    # FDCPA Collection violations (collectors/debt buyers only)
    COLLECTION_BALANCE_INFLATION = "collection_balance_inflation"  # 15 U.S.C. § 1692f(1)
    FALSE_DEBT_STATUS = "false_debt_status"  # 15 U.S.C. § 1692e(2)(A)
    UNVERIFIED_DEBT_REPORTING = "unverified_debt_reporting"  # 15 U.S.C. § 1692e(8)
    DUPLICATE_COLLECTION = "duplicate_collection"  # 15 U.S.C. § 1692e(2)(A)
    # Inquiry violations (FCRA §604)
    UNAUTHORIZED_INQUIRY = "unauthorized_inquiry"  # Fishing expedition / no permissible purpose
    DUPLICATE_INQUIRY = "duplicate_inquiry"  # Same creditor multiple pulls
    INQUIRY_MISCLASSIFICATION = "inquiry_misclassification"  # Soft pull coded as hard
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
    ViolationCategory.TIME_BARRED_DEBT: CategoryConfig(
        title="Time-Barred Debt - Statute of Limitations Expired",
        metro2_fields="State SOL Statutes / 15 U.S.C. § 1692e(5)",
        explanation=(
            "The following collection accounts have exceeded the applicable Statute of Limitations (SOL) "
            "for the consumer's state of residence. When the SOL expires, the creditor loses the legal "
            "right to sue for collection. Under the Fair Debt Collection Practices Act, 15 U.S.C. § 1692e(5), "
            "threatening to take any action that cannot legally be taken—including suing on "
            "time-barred debt—is a per se violation. The following accounts are time-barred:"
        ),
        resolution=(
            "While time-barred debt may still be reported on a credit file (separate from the 7-year "
            "FCRA reporting period), the collector has lost all legal recourse to sue for collection. "
            "Any communication threatening legal action, lawsuit, garnishment, or judgment on these "
            "debts would constitute an FDCPA violation. I demand that any legal threat language be "
            "removed from the account remarks and that the collector cease any implication of legal "
            "recourse on these time-barred debts."
        ),
        fcra_section="15 U.S.C. § 1692e(5)"  # Canonical format
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
        title="Accounts with Payment Status / Payment History Contradictions",
        metro2_fields="Metro 2 Fields 17A, 17B, and 25 (Payment History Profile)",
        explanation=(
            "The Account Status (Field 17A), Payment Rating (Field 17B), Comments/Special Comments, and "
            "Payment History Profile (Field 25) must be internally consistent. An account cannot show "
            "a charge-off status while simultaneously reporting 24 months of on-time payments - a charge-off "
            "requires prior delinquency (typically 120-180 days past due). The following accounts have "
            "payment status or comment fields that contradict the payment history profile:"
        ),
        resolution=(
            "These internal contradictions must be investigated and corrected immediately. Either the payment "
            "status/comments are incorrect, or the payment history is incorrect - both cannot be accurate. "
            "Under FCRA Section 623(a)(1), furnishers are prohibited from reporting information they know or "
            "should know is inaccurate. Reporting contradictory data fields constitutes a willful violation."
        ),
        fcra_section="623(a)(1)"
    ),
    ViolationCategory.PHANTOM_LATE_PAYMENT: CategoryConfig(
        title="Accounts Reporting Late Payments During $0 Due or Forbearance Periods",
        metro2_fields="Metro 2 Fields 15 (Scheduled Payment) and 25 (Payment History Profile)",
        explanation=(
            "Under FCRA Section 623(a)(1), furnishers cannot report a consumer as delinquent for failing "
            "to make a payment that was not due. When an account has a $0 scheduled payment (such as during "
            "forbearance, deferment, COVID-related payment pause, or hardship programs), reporting late "
            "payment markers (30, 60, 90+ days) is legally impermissible. The following accounts show "
            "'phantom' late payments during periods when no payment was required:"
        ),
        resolution=(
            "These phantom late payment markers must be immediately removed. A consumer cannot be reported "
            "as delinquent for failing to pay $0. Under the CARES Act and FCRA Section 623(c), if a consumer "
            "was in forbearance or had no payment due, any delinquency markers during that period are inaccurate "
            "by definition and must be deleted."
        ),
        fcra_section="623(a)(1)"
    ),
    ViolationCategory.PAID_COLLECTION_CONTRADICTION: CategoryConfig(
        title="Collection Accounts with Status/Balance Contradictions",
        metro2_fields="Metro 2 Fields 17A (Account Status), 10 (Current Balance), and 17B (Payment Rating)",
        explanation=(
            "Under FCRA Section 623(a)(1), furnishers must report accurate, internally consistent information. "
            "The Account Status (Field 17A) and Current Balance (Field 10) must logically align. An account "
            "cannot simultaneously show 'Paid' status while reporting a balance owed, nor can a collection "
            "with zero balance remain in 'Open' or 'Collection' status without being marked as Paid or Settled. "
            "The following accounts have contradictions between their status and balance fields:"
        ),
        resolution=(
            "These internal contradictions must be investigated and corrected. If the account is truly paid, "
            "the balance must be $0 and the status must reflect 'Paid' or 'Settled'. If a balance remains, "
            "the status cannot claim payment. Under FCRA Section 623(a)(1), furnishers are prohibited from "
            "reporting contradictory information - one of these fields is necessarily inaccurate and must be corrected."
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
        title="Identity Mismatch / Potential Mixed File Errors",
        metro2_fields="Consumer Identification Fields / Metro 2 Header Segment",
        explanation=(
            "Under FCRA Section 607(b), credit reporting agencies must maintain reasonable procedures "
            "to assure MAXIMUM POSSIBLE ACCURACY of consumer information. The following discrepancies "
            "between my personal identity information (as provided in my profile) and the credit report "
            "header indicate a potential MIXED FILE situation - where accounts belonging to another "
            "consumer (typically a family member with a similar name) have been incorrectly merged into "
            "my credit file:"
        ),
        resolution=(
            "Mixed file errors are among the most damaging FCRA violations. These identity discrepancies "
            "MUST be investigated immediately. You are required to compare the identifying information on "
            "disputed accounts (name, SSN, DOB, address) against my verified identity. Any accounts that "
            "cannot be positively verified as belonging to ME - not a relative or person with a similar "
            "name - must be immediately removed from my credit file. Under Cortez v. Trans Union, LLC, "
            "617 F.3d 688 (3d Cir. 2010), mixed file errors constitute willful violations of FCRA when "
            "the CRA fails to implement reasonable procedures to prevent them."
        ),
        fcra_section="607(b)"
    ),
    # FDCPA Collection Violations (Collectors/Debt Buyers Only)
    ViolationCategory.COLLECTION_BALANCE_INFLATION: CategoryConfig(
        title="Collection Balance Exceeds Original Debt Amount",
        metro2_fields="Metro 2 Fields 17A (Current Balance) vs 15A (High Credit) / 15 U.S.C. § 1692f(1)",
        explanation=(
            "Under the Fair Debt Collection Practices Act, 15 U.S.C. § 1692f(1), debt collectors are "
            "prohibited from collecting any amount not expressly authorized by the debt agreement or "
            "permitted by law. The following collection accounts report a current balance that exceeds "
            "the original debt amount (high credit), indicating unauthorized fees, interest, or charges "
            "may have been added:"
        ),
        resolution=(
            "Request itemized accounting of all fees and charges added to the original debt amount. "
            "Any amounts not authorized by the original contract or state law must be removed. If the "
            "collector cannot provide documentation authorizing the increased balance, the account must "
            "be corrected to reflect only the original debt amount."
        ),
        fcra_section="15 U.S.C. § 1692f(1)"
    ),
    ViolationCategory.FALSE_DEBT_STATUS: CategoryConfig(
        title="False Representation of Debt Status",
        metro2_fields="Metro 2 Field 05 (Account Status) / 15 U.S.C. § 1692e(2)(A)",
        explanation=(
            "Under the Fair Debt Collection Practices Act, 15 U.S.C. § 1692e(2)(A), debt collectors are "
            "prohibited from falsely representing the character, amount, or legal status of any debt. "
            "The following collection accounts have a $0 balance but are reported as 'Open' rather than "
            "'Paid' or 'Closed', which misrepresents the current status of the debt:"
        ),
        resolution=(
            "These accounts must be updated to accurately reflect the debt status. A $0 balance "
            "indicates the debt has been satisfied, and the account status must be updated to 'Paid' "
            "or 'Closed' accordingly. Continued reporting of an inaccurate status violates both FDCPA "
            "and FCRA accuracy requirements."
        ),
        fcra_section="15 U.S.C. § 1692e(2)(A)"
    ),
    ViolationCategory.UNVERIFIED_DEBT_REPORTING: CategoryConfig(
        title="Unverified Debt Reporting",
        metro2_fields="K1 Segment, Metro 2 Fields 17B (DOFD), 06 (Date Opened) / 15 U.S.C. § 1692e(8)",
        explanation=(
            "Under the Fair Debt Collection Practices Act, 15 U.S.C. § 1692e(8), debt collectors are "
            "prohibited from communicating or threatening to communicate credit information which is "
            "known or should be known to be false. The following collection accounts are missing critical "
            "verification data, indicating the debt may not have been properly validated before reporting:"
        ),
        resolution=(
            "These accounts lack the documentation required to verify the debt. Without the original "
            "creditor name, date of first delinquency, or original account opening date, the debt cannot "
            "be properly validated. Request complete verification documentation or deletion of these "
            "unverified entries."
        ),
        fcra_section="15 U.S.C. § 1692e(8)"
    ),
    ViolationCategory.DUPLICATE_COLLECTION: CategoryConfig(
        title="Duplicate Collection Reporting",
        metro2_fields="K1 Segment (Original Creditor) / 15 U.S.C. § 1692e(2)(A)",
        explanation=(
            "Under the Fair Debt Collection Practices Act, 15 U.S.C. § 1692e(2)(A), falsely representing "
            "the character or amount of a debt includes reporting the same underlying debt through "
            "multiple collection accounts. The following accounts appear to represent the same original "
            "debt being reported by multiple collectors, artificially inflating the consumer's apparent "
            "liability:"
        ),
        resolution=(
            "Only ONE collection account should report each original debt. Multiple collectors reporting "
            "the same debt violates fair representation requirements and creates the false impression "
            "of multiple separate debts. All duplicate entries must be removed, leaving only the current "
            "debt holder's account."
        ),
        fcra_section="15 U.S.C. § 1692e(2)(A)"
    ),
    # Inquiry Violations
    ViolationCategory.UNAUTHORIZED_INQUIRY: CategoryConfig(
        title="Unauthorized Hard Inquiries - No Permissible Purpose",
        metro2_fields="Inquiry Section / FCRA § 604(a)(3)(A)",
        explanation=(
            "Under FCRA Section 604(a)(3)(A), a creditor may only access your consumer report if they "
            "have a 'permissible purpose' - typically a credit transaction initiated by you, or an "
            "existing account relationship. The following inquiries appear to lack permissible purpose, "
            "as the creditor has no associated tradeline, account, or legitimate business transaction "
            "with you:"
        ),
        resolution=(
            "These inquiries must be investigated and removed if permissible purpose cannot be verified. "
            "Under FCRA Section 604(a), accessing a consumer report without permissible purpose is a "
            "violation that may result in statutory damages. I demand that you verify the permissible "
            "purpose for each inquiry listed below and delete any inquiry for which valid purpose "
            "cannot be documented."
        ),
        fcra_section="604(a)(3)(A)"
    ),
    ViolationCategory.DUPLICATE_INQUIRY: CategoryConfig(
        title="Duplicate Inquiries - Multiple Pulls by Same Creditor",
        metro2_fields="Inquiry Section / FCRA § 604(a)(3)",
        explanation=(
            "The following creditors accessed my credit report multiple times within a short period. "
            "While rate-shopping provisions allow multiple auto or mortgage inquiries to count as one "
            "within a 14-45 day window for scoring purposes, the underlying duplicates should still "
            "be consolidated or removed from the report itself to accurately reflect my credit-seeking "
            "behavior:"
        ),
        resolution=(
            "Duplicate inquiries from the same creditor for the same transaction should be consolidated "
            "into a single inquiry. Multiple same-day pulls indicate a technical error or duplicate "
            "submission. I request that you verify with the creditor and remove any duplicate entries."
        ),
        fcra_section="604(a)(3)"
    ),
    ViolationCategory.INQUIRY_MISCLASSIFICATION: CategoryConfig(
        title="Misclassified Inquiries - Soft Pulls Recorded as Hard",
        metro2_fields="Inquiry Section / FCRA § 604(a)(3)",
        explanation=(
            "The following inquiries appear to be from industries that typically perform soft inquiries "
            "(insurance, employment screening, account reviews) but have been incorrectly recorded as "
            "hard inquiries that negatively impact credit scores:"
        ),
        resolution=(
            "These inquiries should be reclassified as soft inquiries or removed entirely. Insurance "
            "quotes, employment background checks, and account reviews do not require hard inquiry "
            "authorization and should not appear as hard pulls on my credit report."
        ),
        fcra_section="604(a)(3)"
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
    ViolationCategory.ILLOGICAL_DELINQUENCY: CategoryConfig(
        title="Accounts with Illogical Delinquency Progression",
        metro2_fields="Metro 2 Field 18 (Payment History Profile)",
        explanation=(
            "Under Metro 2 reporting standards, delinquency must progress sequentially. A consumer "
            "cannot be 60 days late without first being 30 days late, and the status cannot jump "
            "from Current to 60 Days directly. The following accounts contain payment history "
            "patterns that are mathematically impossible or indicate data corruption:"
        ),
        resolution=(
            "These payment history errors must be corrected to reflect accurate, sequential "
            "delinquency progression. Under FCRA Section 623(a)(1), furnishers must report "
            "accurate information. Payment history data that defies basic logic cannot be considered "
            "accurate and must be verified with source documentation or deleted."
        ),
        fcra_section="623(a)(1)"
    ),
    ViolationCategory.DOUBLE_JEOPARDY: CategoryConfig(
        title="Accounts with Duplicate Debt Reporting (Double Jeopardy)",
        metro2_fields="Metro 2 Field 21 (Current Balance)",
        explanation=(
            "Under Metro 2 transfer logic, when a debt is sold or transferred to a collection agency, "
            "the Original Creditor must update their balance to $0 and mark the account as "
            "'Transferred/Sold'. The accounts below show both the Original Creditor AND the "
            "Collection Agency reporting an active balance for the same debt, artificially doubling "
            "the consumer's debt load and destroying Debt-to-Income ratios."
        ),
        resolution=(
            "The Original Creditor entry must be updated to reflect a $0 balance or deleted entirely. "
            "An account cannot be simultaneously 'owed' to two different entities. This duplicate "
            "reporting violates FCRA Section 607(b) which requires maximum possible accuracy. "
            "The Original Creditor no longer holds the debt and cannot report a balance."
        ),
        fcra_section="607(b)"
    ),
    ViolationCategory.DECEASED_INDICATOR: CategoryConfig(
        title="CRITICAL: Erroneous Deceased Indicator - Living Consumer Marked as Deceased",
        metro2_fields="Metro 2 Field 37 (ECOA Code) / Field 38 (Consumer Information Indicator)",
        explanation=(
            "This is among the most damaging errors possible on a credit report. Under Metro 2 "
            "reporting standards, ECOA Code 'X' or Consumer Information Indicator codes 'X', 'Y', or 'Z' "
            "designate a consumer as DECEASED. When a living consumer is erroneously marked as deceased, "
            "their credit score effectively drops to ZERO, and NO creditor will extend credit. "
            "This is commonly known as a 'Death on Credit' error. I AM ALIVE and this indicator "
            "is factually incorrect:"
        ),
        resolution=(
            "The deceased indicator must be IMMEDIATELY removed from my credit file. Under FCRA "
            "Section 611(a), you are required to conduct a reasonable investigation and correct "
            "this error. Under Section 623(a)(2), furnishers have a duty to correct inaccurate "
            "information. Continued reporting of a deceased indicator on a living consumer's file "
            "constitutes a willful violation of FCRA, causing catastrophic damage to my creditworthiness. "
            "See Sloane v. Equifax Info. Servs., LLC, where the court recognized the severe harm caused "
            "by deceased indicator errors. I demand immediate correction and will pursue statutory damages "
            "if this error is not resolved within the 30-day investigation period."
        ),
        fcra_section="611(a), 623(a)(2)"
    ),
    ViolationCategory.CHILD_IDENTITY_THEFT: CategoryConfig(
        title="CRITICAL: Account Opened When Consumer Was a Minor - Potential Identity Theft",
        metro2_fields="Metro 2 Field 10 (Date Opened) / Field 5 (ECOA Code)",
        explanation=(
            "Under contract law, minors (persons under 18 years of age) generally lack the legal capacity "
            "to enter into binding contractual agreements. The following account(s) show a Date Opened "
            "when I was under 18 years old, yet I am listed as a liable party (Individual or Joint), "
            "NOT as an Authorized User. This is a strong indicator of identity theft, synthetic fraud, "
            "or a significant data error. I was a MINOR and could not have legally entered into this contract:"
        ),
        resolution=(
            "Please verify the consumer's age at the time of application by comparing the Date Opened "
            "against my Date of Birth. Since I was a minor when this account was allegedly opened AND "
            "I am listed as liable (not an Authorized User), this account is either: (1) the result of "
            "identity theft where someone fraudulently opened the account in my name as a child, "
            "(2) a data error where the Date Opened or ECOA code is incorrect, or (3) synthetic identity fraud. "
            "Under FCRA Section 611(a), you must conduct a reasonable investigation. If the furnisher cannot "
            "produce a signed application from me as an adult, this tradeline must be DELETED as unverifiable. "
            "I demand immediate investigation and deletion of this invalid tradeline."
        ),
        fcra_section="611(a), Contract Law - Capacity to Contract"
    ),
    # PUBLIC RECORD VIOLATIONS
    ViolationCategory.PUBLIC_RECORD_NCAP: CategoryConfig(
        title="Civil Judgment/Tax Lien Reported in Violation of NCAP Agreement",
        metro2_fields="Public Record Segment",
        explanation=(
            "In 2017, the three major credit bureaus (Equifax, Experian, and TransUnion) entered into the "
            "National Consumer Assistance Plan (NCAP) settlement agreement. Under this agreement, the bureaus "
            "committed to removing all Civil Judgments and Tax Liens from credit reports because public court "
            "records do NOT contain sufficient Personally Identifiable Information (PII) - specifically SSN "
            "and Date of Birth - to accurately match records to consumers. This led to high error rates and "
            "mixed file issues. The following public record is reported in violation of this agreement:"
        ),
        resolution=(
            "You are reporting a Civil Judgment/Tax Lien in violation of the NCAP settlement agreement that "
            "your bureau entered into in 2017. Public court records lack the SSN and DOB data required to "
            "accurately match this record to me under FCRA Section 607(b) maximum possible accuracy standards. "
            "Please DELETE this public record immediately as it cannot be verified to the required standard "
            "and its continued presence violates your own NCAP commitments."
        ),
        fcra_section="NCAP Settlement / FCRA 607(b)"
    ),
    ViolationCategory.PUBLIC_RECORD_JUDGMENT_BALANCE: CategoryConfig(
        title="Satisfied Judgment/Lien Still Reporting Balance",
        metro2_fields="Public Record Amount Field",
        explanation=(
            "When a judgment or lien is satisfied, paid, released, or discharged, the reported balance/amount "
            "must be immediately updated to $0.00. Continuing to report an outstanding balance on a satisfied "
            "public record is inaccurate and misleading to creditors who may believe the debt remains unpaid. "
            "The following public record shows a paid/satisfied status but continues to report a balance:"
        ),
        resolution=(
            "This public record is marked as satisfied/paid/released but continues to report an outstanding "
            "balance. This is factually inaccurate - once satisfied, there is NO remaining balance. Under "
            "FCRA Section 611(a), you must correct this inaccuracy. Please update the balance to $0.00 or "
            "DELETE this record if the status cannot be accurately reconciled with the amount."
        ),
        fcra_section="611(a) / 607(b)"
    ),
    ViolationCategory.PUBLIC_RECORD_BANKRUPTCY_OBSOLETE: CategoryConfig(
        title="Obsolete Bankruptcy Exceeding FCRA Reporting Period",
        metro2_fields="Public Record Segment / FCRA 605(a)(1)",
        explanation=(
            "Under FCRA Section 605(a)(1), bankruptcies have specific maximum reporting periods: Chapter 7 and "
            "Chapter 11 bankruptcies may be reported for 10 years from the filing date, while Chapter 13 "
            "bankruptcies may be reported for 7 years from the filing date. The following bankruptcy has "
            "exceeded its legal reporting period and must be deleted:"
        ),
        resolution=(
            "This bankruptcy has exceeded the maximum reporting period allowed under FCRA Section 605(a)(1). "
            "Continued reporting of obsolete bankruptcy information constitutes a willful violation of federal "
            "law. Please DELETE this obsolete public record IMMEDIATELY. Failure to remove this time-barred "
            "information may result in liability under FCRA Section 616 (willful noncompliance) and Section 617 "
            "(negligent noncompliance)."
        ),
        fcra_section="605(a)(1)"
    ),
    # MEDICAL DEBT VIOLATIONS (NCAP 2022/2023 Bureau Policy)
    ViolationCategory.MEDICAL_UNDER_500: CategoryConfig(
        title="Medical Collection Under $500 Threshold (Bureau Policy Violation)",
        metro2_fields="Balance / Industry Code",
        explanation=(
            "As of April 2023, all three major credit bureaus (Equifax, Experian, and TransUnion) agreed "
            "to remove ALL unpaid medical collections under $500 from consumer credit reports. This was "
            "part of the National Consumer Assistance Plan (NCAP) updates to reduce the impact of medical "
            "debt on consumer credit scores. The following medical collection falls below the $500 threshold "
            "and should NOT appear on this report:"
        ),
        resolution=(
            "This medical collection is under $500 and should have been removed under the bureau's own "
            "data acceptance policy effective April 2023. You are reporting this item in violation of your "
            "own accuracy standards. Please DELETE this trade line immediately as it falls below the "
            "current medical debt reporting threshold."
        ),
        fcra_section="Bureau Policy / NCAP 2023"
    ),
    ViolationCategory.MEDICAL_PAID_REPORTING: CategoryConfig(
        title="Paid Medical Debt Still Reporting (Bureau Policy Violation)",
        metro2_fields="Account Status / Payment Status",
        explanation=(
            "Effective July 1, 2022, all three major credit bureaus (Equifax, Experian, and TransUnion) "
            "agreed to remove ALL paid medical collections from consumer credit reports. This was a "
            "significant policy change under the National Consumer Assistance Plan (NCAP) that recognizes "
            "the unfair impact of keeping paid medical debts on credit reports. The following paid medical "
            "collection should NOT appear on this report:"
        ),
        resolution=(
            "This medical collection has been marked as PAID or SETTLED but is still appearing on my "
            "credit report. Under the bureau's policy effective July 1, 2022, paid medical collections must "
            "be removed IMMEDIATELY upon payment. The continued presence of this item violates your own "
            "data acceptance standards and serves no permissible purpose. Please DELETE this item immediately."
        ),
        fcra_section="Bureau Policy / NCAP 2022"
    ),
    # POST-SETTLEMENT & CROSS-BUREAU GAPS
    ViolationCategory.POST_SETTLEMENT_NEGATIVE: CategoryConfig(
        title="Post-Settlement Negative Reporting (Zombie History)",
        metro2_fields="Metro 2 Field 18 (Payment History Profile) / Field 24 (Date Closed)",
        explanation=(
            "Under FCRA Section 623(a)(1), furnishers must report accurate information. When an account is "
            "closed, paid, or settled, the furnisher cannot continue to report new derogatory payment markers "
            "(30/60/90 days late) for periods AFTER the account was closed. This practice, known as 'zombie history' "
            "or 'ghost delinquency,' artificially refreshes the Date of Last Activity (DLA) and prevents the "
            "consumer's score from recovering. The following accounts show late payment markers reported for dates "
            "AFTER the account was closed or settled:"
        ),
        resolution=(
            "These post-settlement derogatory markers must be immediately removed. Once an account is closed "
            "or settled, no new delinquency can accrue - the debt no longer exists to become past due on. "
            "These phantom late markers are mathematically impossible and constitute inaccurate reporting under "
            "FCRA Section 623(a)(1). I demand immediate deletion of all payment history entries dated after the "
            "account closure/settlement date."
        ),
        fcra_section="623(a)(1)"
    ),
    ViolationCategory.MISSING_TRADELINE_INFO: CategoryConfig(
        title="Cross-Bureau Tradeline Gap (Missing Account)",
        metro2_fields="Furnisher Reporting Practices",
        explanation=(
            "The following account appears on some credit bureaus but is MISSING from this bureau's report. "
            "While furnishers are not legally required to report to all three bureaus, significant tradeline "
            "gaps between bureaus can materially affect credit scores and create unexplained score discrepancies "
            "between bureaus. This informational finding explains why scores may differ across bureaus:"
        ),
        resolution=(
            "This is an informational notice regarding a tradeline gap. While not a legal violation, the absence "
            "of this account from this bureau's report may be contributing to score discrepancies. I request that "
            "you note this gap for your records. If this account SHOULD be reporting to all bureaus and was "
            "inadvertently omitted, please contact the furnisher to ensure complete reporting."
        ),
        fcra_section="Informational"
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
    # Evidence can be a string or a dict - handle both cases
    evidence_raw = violation.get("evidence") or ""
    evidence = evidence_raw.lower() if isinstance(evidence_raw, str) else ""
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

    # Check for time-barred debt (SOL expired)
    if v_type == "time_barred_debt_risk":
        return ViolationCategory.TIME_BARRED_DEBT
    if "statute of limitations" in evidence or "time-barred" in evidence or "sol expired" in evidence:
        return ViolationCategory.TIME_BARRED_DEBT

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
    if v_type in ["incorrect_payment_status", "payment_history_error", "wrong_account_status", "status_payment_history_mismatch"]:
        return ViolationCategory.PAYMENT_STATUS_ERROR

    # Check for phantom late payments (late markers during $0 due or forbearance)
    if v_type == "phantom_late_payment":
        return ViolationCategory.PHANTOM_LATE_PAYMENT

    # Check for paid collection contradictions (status/balance mismatch)
    if v_type in ["paid_status_with_balance", "zero_balance_not_paid"]:
        return ViolationCategory.PAID_COLLECTION_CONTRADICTION

    # Check for illogical delinquency progression (skipped rungs, stagnant lates)
    if v_type in ["delinquency_jump", "stagnant_delinquency"]:
        return ViolationCategory.ILLOGICAL_DELINQUENCY

    # Check for double jeopardy (OC and Collector BOTH report balance for same debt)
    if v_type == "double_jeopardy":
        return ViolationCategory.DOUBLE_JEOPARDY

    # Check for deceased indicator error (CRITICAL - "Death on Credit" error)
    if v_type == "deceased_indicator_error":
        return ViolationCategory.DECEASED_INDICATOR
    if "deceased" in evidence or "death on credit" in evidence:
        return ViolationCategory.DECEASED_INDICATOR

    # Check for child identity theft (CRITICAL - account opened when consumer was a minor)
    if v_type == "child_identity_theft":
        return ViolationCategory.CHILD_IDENTITY_THEFT

    # Check for PUBLIC RECORD violations (Bankruptcies, Judgments, Liens)
    # NCAP violations - Civil Judgments and Tax Liens banned post-2017
    if v_type == "ncap_violation_judgment":
        return ViolationCategory.PUBLIC_RECORD_NCAP
    # Satisfied judgments still reporting a balance (should be $0)
    if v_type == "judgment_not_updated":
        return ViolationCategory.PUBLIC_RECORD_JUDGMENT_BALANCE
    # Obsolete bankruptcies (Ch7 > 10 years, Ch13 > 7 years) and impossible dates
    if v_type in ["bankruptcy_obsolete", "bankruptcy_date_error"]:
        return ViolationCategory.PUBLIC_RECORD_BANKRUPTCY_OBSOLETE

    # Check for MEDICAL DEBT violations (NCAP 2022/2023 Bureau Policy)
    # Unpaid medical < $500 (banned April 2023)
    if v_type == "medical_under_500":
        return ViolationCategory.MEDICAL_UNDER_500
    # Paid medical still reporting (banned July 2022)
    if v_type == "medical_paid_reporting":
        return ViolationCategory.MEDICAL_PAID_REPORTING

    # Check for POST-SETTLEMENT NEGATIVE REPORTING (Zombie History)
    # Late markers reported AFTER account was closed/settled
    if v_type == "post_settlement_negative":
        return ViolationCategory.POST_SETTLEMENT_NEGATIVE
    if "zombie" in evidence or "post-settlement" in evidence or "ghost delinquency" in evidence:
        return ViolationCategory.POST_SETTLEMENT_NEGATIVE

    # Check for MISSING TRADELINE (Cross-Bureau Gap)
    # Account appears on some bureaus but is missing from others
    if v_type == "missing_tradeline_inconsistency":
        return ViolationCategory.MISSING_TRADELINE_INFO

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

    # Check for identity errors (including new identity integrity violations)
    if v_type in [
        "not_mine", "identity_error", "mixed_file",
        "identity_suffix_mismatch", "identity_name_mismatch",
        "identity_ssn_mismatch", "identity_address_mismatch",
        "mixed_file_indicator"
    ]:
        return ViolationCategory.IDENTITY_ERROR
    # Also check evidence for identity-related keywords
    if "suffix" in evidence or "jr" in evidence or "sr" in evidence or "mixed file" in evidence:
        return ViolationCategory.IDENTITY_ERROR
    if "ssn" in evidence and "mismatch" in evidence:
        return ViolationCategory.IDENTITY_ERROR

    # Check for INQUIRY violations
    # Collection fishing / unauthorized inquiry - no permissible purpose
    if v_type in ["collection_fishing_inquiry", "unauthorized_hard_inquiry", "unauthorized_inquiry"]:
        return ViolationCategory.UNAUTHORIZED_INQUIRY
    if "fishing" in evidence or "no tradeline" in evidence or "permissible purpose" in evidence:
        return ViolationCategory.UNAUTHORIZED_INQUIRY
    # Duplicate inquiry from same creditor
    if v_type == "duplicate_inquiry":
        return ViolationCategory.DUPLICATE_INQUIRY
    if "double tap" in evidence or "duplicate inquiry" in evidence:
        return ViolationCategory.DUPLICATE_INQUIRY
    # Misclassified inquiry (soft as hard)
    if v_type == "inquiry_misclassification":
        return ViolationCategory.INQUIRY_MISCLASSIFICATION
    if "insurance" in evidence or "soft pull" in evidence:
        return ViolationCategory.INQUIRY_MISCLASSIFICATION

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
    Fixes issues like:
    - "10026-," -> "10026"
    - "NY10026-" -> "NY 10026"
    - "NY10026" -> "NY 10026"
    """
    if not city_state_zip:
        return ""

    # Remove trailing punctuation like ",-" or "-,"
    city_state_zip = re.sub(r'[,\-]+\s*$', '', city_state_zip)

    # Remove dangling comma before zip
    city_state_zip = re.sub(r',\s*,', ',', city_state_zip)

    # Fix state/zip concatenation: "NY10026" -> "NY 10026"
    # Match 2-letter state code immediately followed by zip code (no space)
    city_state_zip = re.sub(r'([A-Z]{2})(\d{5})', r'\1 \2', city_state_zip)

    return city_state_zip.strip()


def _format_account_bullet(violation: Dict[str, Any]) -> str:
    """Format a single account as a bullet point with specific factual details."""
    creditor = violation.get("creditor_name", "Unknown")
    account = violation.get("account_number_masked", "")
    evidence = violation.get("evidence", "")
    days = violation.get("days_since_update")
    last_reported_date_raw = violation.get("last_reported_date", "")
    dofd_raw = violation.get("dofd", "") or violation.get("date_of_first_delinquency", "")
    dofd_source = violation.get("dofd_source", "")  # "explicit", "inferred", or ""
    missing_field = violation.get("missing_field", "")
    violation_type = violation.get("violation_type", "")
    description = violation.get("description", "")

    # Convert dates to readable format (January 26, 2025 instead of 2025-01-26)
    last_reported_date = _format_readable_date(last_reported_date_raw)
    dofd_date = _format_readable_date(dofd_raw)

    # Build account identifier - for inquiries, creditor only (no account number)
    if account and violation_type not in ["collection_fishing_inquiry", "duplicate_inquiry", "inquiry_misclassification"]:
        account_id = f"{creditor} (Account #{account})"
    else:
        account_id = creditor

    # Add specific issue details
    details = []

    # Extract key field values from evidence dict for display
    evidence_dict = evidence if isinstance(evidence, dict) else {}
    payment_status = evidence_dict.get("payment_status", "") or violation.get("payment_status", "")
    balance = evidence_dict.get("balance") or evidence_dict.get("current_balance") or violation.get("balance")
    account_status = evidence_dict.get("account_status", "") or violation.get("account_status", "")

    # =========================================================================
    # INQUIRY VIOLATIONS - FCRA § 604 (Permissible Purpose)
    # =========================================================================

    # Handle Collection Fishing Inquiry (unauthorized access / no permissible purpose)
    if violation_type == "collection_fishing_inquiry" and isinstance(evidence, dict):
        inquiry_date = evidence.get("inquiry_date", "")
        bureau = evidence.get("bureau", "")
        has_tradeline = evidence.get("has_matching_tradeline", False)
        is_stacked = evidence.get("stacked_violation", False)
        violation_count = evidence.get("violation_count", 1)
        secondary_violations = evidence.get("secondary_violations", [])

        inquiry_parts = []

        # Primary violation: unauthorized inquiry
        if inquiry_date:
            inquiry_parts.append(f"Hard Inquiry Date: {_format_readable_date(inquiry_date)}")
        if bureau:
            inquiry_parts.append(f"Bureau: {bureau.upper()}")
        inquiry_parts.append("No associated tradeline, account, or loan found on credit file")
        inquiry_parts.append("Without a legitimate business transaction, creditor lacks permissible purpose under 15 U.S.C. § 1681b(a)(3)(A)")

        # =================================================================
        # EXPLICIT NUMEROSITY LANGUAGE (for duplicate inquiry evidence)
        # Inject only when: stacked violation includes DUPLICATE_INQUIRY
        # =================================================================
        has_duplicate_evidence = any(
            sv.get("type") == "duplicate_inquiry" for sv in secondary_violations
        ) if secondary_violations else False

        if is_stacked and has_duplicate_evidence and inquiry_date and bureau:
            # Count actual inquiry pulls (fishing violations + 1 for the duplicate trigger)
            # The stacking groups: N fishing inquiries + duplicate detection = N pulls
            fishing_count = sum(
                1 for sv in secondary_violations
                if sv.get("type") == "collection_fishing_inquiry"
            )
            # Total pulls = primary (1) + secondary fishing violations + implies at least 2 for duplicate
            inquiry_pull_count = max(2, fishing_count + 1)  # At minimum 2 if duplicate detected

            # Format count: "two (2)" for 2, "three (3)" for 3, etc.
            count_words = {
                2: "two (2)", 3: "three (3)", 4: "four (4)", 5: "five (5)",
                6: "six (6)", 7: "seven (7)", 8: "eight (8)", 9: "nine (9)", 10: "ten (10)"
            }
            count_text = count_words.get(inquiry_pull_count, f"{inquiry_pull_count} ({inquiry_pull_count})")

            # Canonical numerosity sentence
            numerosity_sentence = (
                f"On {_format_readable_date(inquiry_date)}, {creditor} accessed my "
                f"{bureau.upper()} consumer report {count_text} separate times in connection "
                f"with a single credit application, without any resulting account or tradeline."
            )
            inquiry_parts.append(f"\n{numerosity_sentence}")

        # If stacked, show secondary violations as supporting evidence
        if is_stacked and secondary_violations:
            inquiry_parts.append(f"\nSUPPORTING EVIDENCE ({violation_count} total violations grouped):")
            for sv in secondary_violations:
                sv_type = sv.get("type", "").replace("_", " ").title()
                sv_section = sv.get("fcra_section", "")
                inquiry_parts.append(f"  • {sv_type} (FCRA § {sv_section})")

        if inquiry_parts:
            return f"• {account_id}: {'; '.join(inquiry_parts[:4])}" + ("\n  " + "\n  ".join(inquiry_parts[4:]) if len(inquiry_parts) > 4 else "")

    # Handle Duplicate Inquiry (same-day double tap or within-window)
    if violation_type == "duplicate_inquiry" and isinstance(evidence, dict):
        inquiry_date = evidence.get("inquiry_date", "")
        first_inquiry_date = evidence.get("first_inquiry_date", "")
        second_inquiry_date = evidence.get("second_inquiry_date", "")
        days_apart = evidence.get("days_apart", 0)
        duplicate_type = evidence.get("duplicate_type", "")
        bureau = evidence.get("bureau", "")
        normalized_creditor = evidence.get("normalized_creditor", "")

        duplicate_parts = []

        if duplicate_type == "same_day_double_tap":
            duplicate_parts.append(f"DOUBLE TAP DETECTED: Multiple hard inquiries on same day ({_format_readable_date(inquiry_date)})")
            duplicate_parts.append(f"Bureau: {bureau.upper()}" if bureau else "")
            duplicate_parts.append("Single lender should only access credit file once per application per bureau")
            duplicate_parts.append("Multiple same-day pulls indicate technical error or duplicate submission")
        elif duplicate_type == "within_window":
            duplicate_parts.append(f"Duplicate pulls detected: {_format_readable_date(first_inquiry_date)} and {_format_readable_date(second_inquiry_date)}")
            duplicate_parts.append(f"Days apart: {days_apart}")
            duplicate_parts.append("Under rate-shopping provisions, multiple inquiries within 14-45 days should be merged")

        duplicate_parts = [p for p in duplicate_parts if p]  # Remove empty strings
        if duplicate_parts:
            return f"• {account_id}: {'; '.join(duplicate_parts)}"

    # Handle Inquiry Misclassification (soft pull coded as hard)
    if violation_type == "inquiry_misclassification" and isinstance(evidence, dict):
        inquiry_date = evidence.get("inquiry_date", "")
        industry_type = evidence.get("industry_type", "")
        matched_industry = evidence.get("matched_industry", "")
        bureau = evidence.get("bureau", "")

        misclass_parts = []
        misclass_parts.append(f"Hard Inquiry Date: {_format_readable_date(inquiry_date)}")
        if bureau:
            misclass_parts.append(f"Bureau: {bureau.upper()}")
        if industry_type:
            misclass_parts.append(f"Industry: {industry_type}")
        misclass_parts.append(f"{industry_type or 'This industry'} typically performs soft inquiries for {matched_industry or 'non-credit purposes'}")
        misclass_parts.append("Hard inquiry should be reclassified as soft inquiry or removed")

        if misclass_parts:
            return f"• {account_id}: {'; '.join(misclass_parts)}"

    # Handle Status/Payment History Mismatch violations with structured evidence
    if violation_type == "status_payment_history_mismatch" and isinstance(evidence, dict):
        payment_status = evidence.get("payment_status", "")
        comments = evidence.get("comments", "")
        ok_months = evidence.get("ok_months", 0)
        total_months = evidence.get("total_months", 0)

        # Build the contradiction description
        contradiction_parts = []
        if payment_status:
            contradiction_parts.append(f'Payment Status shows "{payment_status}"')
        if comments:
            # Truncate long comments
            comments_short = comments[:80] + "..." if len(comments) > 80 else comments
            contradiction_parts.append(f'Comments state "{comments_short}"')

        if contradiction_parts:
            details.append(f"{' and '.join(contradiction_parts)}, indicating charge-off/collection status")

        if ok_months and total_months:
            details.append(
                f"However, Payment History Profile shows {ok_months} out of {total_months} months as "
                f"current/OK — a charge-off requires prior delinquency (120-180 days), which is absent"
            )

        if details:
            return f"• {account_id}: {'; '.join(details)}"

    # Handle Phantom Late Payment violations with structured evidence
    if violation_type == "phantom_late_payment" and isinstance(evidence, dict):
        scheduled_payment = evidence.get("scheduled_payment")
        has_forbearance = evidence.get("has_forbearance", False)
        forbearance_remarks = evidence.get("forbearance_remarks", "")
        late_markers = evidence.get("late_markers", [])
        trigger_reason = evidence.get("trigger_reason", [])

        # Build the phantom late payment description
        phantom_parts = []

        # Show why no payment was due
        if scheduled_payment is not None and scheduled_payment == 0:
            phantom_parts.append("Scheduled Payment: $0 (no payment was due)")
        if has_forbearance and forbearance_remarks:
            # Truncate long remarks
            remarks_short = forbearance_remarks[:60] + "..." if len(forbearance_remarks) > 60 else forbearance_remarks
            phantom_parts.append(f'Account remarks indicate forbearance/deferment: "{remarks_short}"')

        if phantom_parts:
            details.append(" and ".join(phantom_parts))

        # Show the phantom late markers found
        if late_markers:
            late_text = ", ".join([
                f"{m.get('month', '')} {m.get('year', '')}: {m.get('status', '')}"
                for m in late_markers[:4]
            ])
            if len(late_markers) > 4:
                late_text += f" (+{len(late_markers) - 4} more)"
            details.append(f"Yet Payment History shows late markers: {late_text}")

        details.append("Cannot be late on a $0 payment or during forbearance")

        if details:
            return f"• {account_id}: {'; '.join(details)}"

    # Handle Paid Collection Contradiction violations with structured evidence
    if violation_type in ["paid_status_with_balance", "zero_balance_not_paid"] and isinstance(evidence, dict):
        payment_status = evidence.get("payment_status", "")
        balance = evidence.get("balance", 0)
        past_due = evidence.get("past_due", 0)
        account_type = evidence.get("account_type", "")
        scenario = evidence.get("scenario", "")

        # Build the contradiction description
        contradiction_parts = []

        if scenario == "paid_but_balance":
            # Scenario 1: Marked paid but still has balance
            if payment_status:
                contradiction_parts.append(f'Payment Status shows "{payment_status}" indicating account is paid')
            if balance > 0:
                contradiction_parts.append(f"Yet Current Balance reports ${balance:,.2f}")
            if past_due > 0:
                contradiction_parts.append(f"Past Due Amount shows ${past_due:,.2f}")
            contradiction_parts.append("An account cannot be 'Paid' while reporting a balance owed")
        elif scenario == "zero_balance_not_paid":
            # Scenario 2: Collection with $0 but not marked paid
            if account_type:
                contradiction_parts.append(f"Account Type: {account_type}")
            contradiction_parts.append("Balance: $0.00 and Past Due: $0.00")
            if payment_status:
                contradiction_parts.append(f'Yet Payment Status shows "{payment_status}" instead of "Paid"')
            contradiction_parts.append("A collection with $0 owed must be marked as Paid/Settled")

        if contradiction_parts:
            details.extend(contradiction_parts)
            return f"• {account_id}: {'; '.join(details)}"

    # Handle obsolete accounts (>2555 days / 7 years from DOFD per FCRA 605(a))
    if days and days > 2555:
        years = round(days / 365, 1)
        # FCRA 605(a)(4) + 605(c)(1): 7-year period runs from DOFD (Date of First Delinquency)
        # DOFD = date of commencement of delinquency + 180 days per 605(c)(1)
        if dofd_date and dofd_source == "explicit":
            # Explicit DOFD from Metro 2 Field 25
            details.append(f"DOFD: {dofd_date} (Metro 2 Field 25) — {days:,} days / {years} years exceeds FCRA § 605(a) 7-year limit")
        elif dofd_date and dofd_source == "inferred":
            # DOFD inferred from payment history analysis
            details.append(f"DOFD: {dofd_date} (inferred from payment history per § 605(c)(1)) — {days:,} days / {years} years exceeds FCRA § 605(a) 7-year limit. Note: Metro 2 Field 25 not explicitly reported.")
        elif dofd_date:
            # DOFD available but source unknown
            details.append(f"DOFD: {dofd_date} — {days:,} days / {years} years exceeds FCRA § 605(a) 7-year limit")
        else:
            # No DOFD available - dual violation (missing DOFD + obsolete)
            details.append(f"Metro 2 Field 25 (DOFD) NOT REPORTED — per FCRA § 605(c)(1), the 7-year period begins 180 days after commencement of delinquency. Based on account age of {days:,} days / {years} years, this account exceeds the § 605(a) 7-year limit regardless of actual DOFD.")

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

    # Add evidence if not already covered (handle string evidence)
    if evidence and isinstance(evidence, str) and evidence not in str(details):
        # Clean up evidence text
        evidence_clean = evidence.strip()
        if evidence_clean:
            details.append(evidence_clean)

    # FALLBACK: If no details were added but we have field values, show them
    # This ensures violations always show factual data like "Payment Status: X | Balance: Y"
    if not details:
        field_values = []
        if payment_status:
            field_values.append(f"Payment Status: {payment_status}")
        if balance is not None:
            try:
                balance_formatted = f"${float(balance):,.2f}" if balance else "$0.00"
            except (ValueError, TypeError):
                balance_formatted = str(balance)
            field_values.append(f"Balance: {balance_formatted}")
        if account_status and account_status != payment_status:
            field_values.append(f"Account Status: {account_status}")

        if field_values:
            # Build a summary line with the field values
            field_summary = " | ".join(field_values)
            # Add the description to explain what's wrong
            if description:
                # Use full description - no truncation for legal letters
                # Descriptions contain critical factual evidence
                details.append(f"{field_summary} — {description}")
            else:
                details.append(f"{field_summary} — These fields require investigation")

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
    account_num = discrepancy.get("account_number_masked", "")
    field_name = discrepancy.get("field_name", "Data")
    values_by_bureau = discrepancy.get("values_by_bureau", {})
    violation_type = discrepancy.get("violation_type", "")
    description = discrepancy.get("description", "")

    # Build account identifier
    if account_num:
        account_id = f"{creditor} (Account #{account_num})"
    else:
        account_id = creditor

    # Build the bureau comparison string
    bureau_values = []
    for bureau, value in values_by_bureau.items():
        bureau_name = bureau.upper() if len(bureau) <= 3 else bureau.title()
        bureau_values.append(f"{bureau_name}: {value}")

    comparison_str = ", ".join(bureau_values)

    # Special handling for dispute flag mismatch
    if violation_type == "dispute_flag_mismatch":
        # Parse values to build a more descriptive message
        bureaus_with_dispute = [b for b, v in values_by_bureau.items() if v == "DISPUTED"]
        bureaus_without = [b for b, v in values_by_bureau.items() if v == "NO FLAG"]

        if bureaus_with_dispute and bureaus_without:
            dispute_bureaus = ", ".join([b.upper() if len(b) <= 3 else b.title() for b in bureaus_with_dispute])
            no_flag_bureaus = ", ".join([b.upper() if len(b) <= 3 else b.title() for b in bureaus_without])
            return (
                f"• {account_id}: Dispute flag shows on {dispute_bureaus} but NOT on {no_flag_bureaus}. "
                f"Under FCRA §623(a)(3), when a consumer disputes an account, the furnisher must report "
                f"the dispute status to ALL bureaus - not selectively"
            )

    # Special handling for ECOA code mismatch
    if violation_type == "ecoa_code_mismatch":
        # Show what each bureau reports
        code_details = [f"{b.upper() if len(b) <= 3 else b.title()}: {v}" for b, v in values_by_bureau.items()]
        unique_codes = list(set(values_by_bureau.values()))
        return (
            f"• {account_id}: Inconsistent liability designation ({', '.join(code_details)}). "
            f"The same consumer cannot be both '{unique_codes[0]}' and '{unique_codes[1] if len(unique_codes) > 1 else 'different'}' "
            f"liable for the same account. Under FCRA §623(a)(1), furnishers must report accurate "
            f"information - one bureau's ECOA code is necessarily wrong"
        )

    # Special handling for Authorized User with derogatory marks
    if violation_type == "authorized_user_derogatory":
        # The description already contains the derogatory details
        return (
            f"• {account_id}: As an Authorized User (ECOA Code 3), I am NOT contractually liable for "
            f"this debt. Reporting negative marks on a non-liable party's credit file violates both "
            f"FCRA §623(a)(1) accuracy requirements and the Equal Credit Opportunity Act (ECOA). "
            f"These derogatory marks must be removed or the account removed from my file entirely"
        )

    # Format the bullet
    return f"• {account_id}: {field_name} differs across bureaus ({comparison_str})"


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
        # CRITICAL: All ViolationCategory values MUST be listed here to be rendered
        category_order = [
            # Critical/High severity - account should be deleted
            ViolationCategory.OBSOLETE_ACCOUNT,  # >7 years from DOFD per FCRA 605(a)
            ViolationCategory.TIME_BARRED_DEBT,  # SOL expired (different from 7-year FCRA rule)
            ViolationCategory.DECEASED_INDICATOR,  # "Death on Credit" error
            ViolationCategory.CHILD_IDENTITY_THEFT,  # Account opened when minor
            # Public records violations (NCAP, bankruptcy)
            ViolationCategory.PUBLIC_RECORD_NCAP,  # Civil judgments/tax liens banned post-2017
            ViolationCategory.PUBLIC_RECORD_JUDGMENT_BALANCE,  # Satisfied judgment still showing balance
            ViolationCategory.PUBLIC_RECORD_BANKRUPTCY_OBSOLETE,  # Bankruptcy >10/7 years
            # Medical debt violations (NCAP 2022/2023)
            ViolationCategory.MEDICAL_UNDER_500,  # <$500 medical banned April 2023
            ViolationCategory.MEDICAL_PAID_REPORTING,  # Paid medical banned July 2022
            # Data accuracy violations
            ViolationCategory.MISSING_DOFD,
            ViolationCategory.STALE_REPORTING,
            ViolationCategory.ILLOGICAL_DELINQUENCY,  # Impossible payment history progression
            ViolationCategory.DOUBLE_JEOPARDY,  # Same debt reported twice
            ViolationCategory.PHANTOM_LATE_PAYMENT,  # Late on $0 payment / during forbearance
            ViolationCategory.POST_SETTLEMENT_NEGATIVE,  # Zombie history - late markers after closed
            ViolationCategory.PAID_COLLECTION_CONTRADICTION,
            ViolationCategory.AMOUNT_PAST_DUE_ERROR,
            ViolationCategory.BALANCE_ERROR,
            ViolationCategory.PAYMENT_STATUS_ERROR,
            ViolationCategory.MISSING_PAYMENT_HISTORY,
            # FDCPA Collection violations (collectors/debt buyers only)
            ViolationCategory.COLLECTION_BALANCE_INFLATION,  # 15 U.S.C. § 1692f(1)
            ViolationCategory.FALSE_DEBT_STATUS,  # 15 U.S.C. § 1692e(2)(A)
            ViolationCategory.UNVERIFIED_DEBT_REPORTING,  # 15 U.S.C. § 1692e(8)
            ViolationCategory.DUPLICATE_COLLECTION,  # Same debt multiple collectors
            ViolationCategory.STUDENT_LOAN_VERIFICATION,
            ViolationCategory.COLLECTION_VERIFICATION,
            # Inquiry violations (FCRA § 604)
            ViolationCategory.UNAUTHORIZED_INQUIRY,  # Fishing expedition / no permissible purpose
            ViolationCategory.DUPLICATE_INQUIRY,  # Same creditor multiple pulls
            ViolationCategory.INQUIRY_MISCLASSIFICATION,  # Soft pull coded as hard
            # Identity / Mixed file
            ViolationCategory.IDENTITY_ERROR,
            ViolationCategory.MISSING_TRADELINE_INFO,  # Cross-bureau gaps (informational)
            # Fallback - MUST be last
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
