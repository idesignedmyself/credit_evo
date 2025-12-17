"""
Legal Letter Generator - Metro-2 Technical Explanations
Provides technical explanations of Metro-2 fields and compliance requirements.
"""
from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class Metro2FieldExplanation:
    """Detailed explanation of a Metro-2 field for legal letters."""
    field_name: str
    field_number: str
    segment: str
    description: str
    compliance_requirement: str
    legal_language: str
    fcra_section: str
    common_errors: list


# Complete Metro-2 field explanations for legal letters
METRO2_FIELDS: Dict[str, Metro2FieldExplanation] = {
    "account_status": Metro2FieldExplanation(
        field_name="Account Status",
        field_number="Field 17A",
        segment="Base Segment",
        description="Indicates the current status of the account as of the date reported.",
        compliance_requirement="Must accurately reflect the true status of the account. Values must conform to Metro-2 code definitions.",
        legal_language="The Account Status field (Field 17A) is required to accurately represent the current state of the consumer's obligation. Per CDIA Metro-2 Format guidelines, this field must be updated to reflect any changes in account status within the reporting cycle.",
        fcra_section="623(a)(1)",
        common_errors=[
            "Reporting closed accounts as open",
            "Failure to update status after payment",
            "Incorrect delinquency status codes",
            "Status inconsistent with payment pattern"
        ]
    ),
    "payment_rating": Metro2FieldExplanation(
        field_name="Payment Rating",
        field_number="Field 17B",
        segment="Base Segment",
        description="Indicates the payment performance on the account.",
        compliance_requirement="Must accurately reflect payment history. Cannot report late payments without documented proof of the delinquency date.",
        legal_language="The Payment Rating field (Field 17B) is governed by strict accuracy standards. Under the Metro-2 Format, furnishers must report only verified payment performance data and update ratings promptly when account status changes.",
        fcra_section="623(a)(1)",
        common_errors=[
            "Rating inconsistent with payment history",
            "Failure to update after dispute resolution",
            "Reporting delinquency without valid date",
            "Incorrect severity of delinquency"
        ]
    ),
    "current_balance": Metro2FieldExplanation(
        field_name="Current Balance",
        field_number="Field 21",
        segment="Base Segment",
        description="The balance owed on the account as of the date reported.",
        compliance_requirement="Must reflect the actual balance. Zero balances must be reported accurately for paid accounts.",
        legal_language="Field 21 (Current Balance) requires accurate reporting of the outstanding obligation. The FCRA mandates that this figure must reconcile with the creditor's internal records and be updated promptly to reflect payments received.",
        fcra_section="623(a)(2)",
        common_errors=[
            "Balance not reflecting recent payments",
            "Reporting balance on paid-off accounts",
            "Incorrect balance after settlement",
            "Failure to update after charge-off sale"
        ]
    ),
    "high_credit": Metro2FieldExplanation(
        field_name="High Credit/Original Loan Amount",
        field_number="Field 12",
        segment="Base Segment",
        description="The highest balance or original loan amount on the account.",
        compliance_requirement="Must accurately reflect the original credit extended or highest balance achieved.",
        legal_language="Field 12 (High Credit/Original Loan Amount) establishes the maximum credit exposure. Inaccurate reporting of this field can materially impact credit scoring models and debt-to-income calculations, requiring correction under FCRA Section 623(a)(1).",
        fcra_section="623(a)(1)",
        common_errors=[
            "Inflated high credit amounts",
            "Confusion between credit limit and high balance",
            "Incorrect original loan principal",
            "Failure to distinguish revolving from installment"
        ]
    ),
    "credit_limit": Metro2FieldExplanation(
        field_name="Credit Limit",
        field_number="Field 16",
        segment="Base Segment",
        description="The credit limit on revolving accounts.",
        compliance_requirement="Required for revolving accounts. Must accurately reflect the approved credit limit.",
        legal_language="Field 16 (Credit Limit) directly affects credit utilization calculations, a key factor in credit scoring. The Metro-2 Format requires this field be populated for all revolving accounts with the actual credit limit extended to the consumer.",
        fcra_section="623(a)(1)",
        common_errors=[
            "Missing credit limit on revolving accounts",
            "Outdated limit after increases/decreases",
            "Zero credit limit on open accounts",
            "Limit reported as high credit"
        ]
    ),
    "date_opened": Metro2FieldExplanation(
        field_name="Date Opened",
        field_number="Field 8",
        segment="Base Segment",
        description="The date the account was opened or the contractual obligation began.",
        compliance_requirement="Must accurately reflect when the credit obligation commenced. Critical for determining reporting periods.",
        legal_language="Field 8 (Date Opened) establishes the timeline for the account and affects the seven-year reporting limitation under FCRA Section 605(a). Inaccurate date reporting can result in the unlawful extension of adverse information beyond statutory limits.",
        fcra_section="605(a)",
        common_errors=[
            "Date changed after account sale",
            "Incorrect date restarting obsolescence clock",
            "Date inconsistent with account history",
            "Re-aged accounts with new open dates"
        ]
    ),
    "date_closed": Metro2FieldExplanation(
        field_name="Date Closed",
        field_number="Field 25",
        segment="Base Segment",
        description="The date the account was closed by consumer or creditor.",
        compliance_requirement="Must be populated when account is closed. Affects credit history length calculations.",
        legal_language="Field 25 (Date Closed) is required when an account is no longer active. The Metro-2 Format mandates reporting the actual closure date, and failure to do so or reporting an incorrect date materially impacts the consumer's credit profile.",
        fcra_section="623(a)(2)",
        common_errors=[
            "Missing date on closed accounts",
            "Incorrect closure date",
            "Open status on closed accounts",
            "Failure to report closure"
        ]
    ),
    "date_of_first_delinquency": Metro2FieldExplanation(
        field_name="Date of First Delinquency",
        field_number="Field 24",
        segment="Base Segment",
        description="The date the account first became delinquent leading to the current status.",
        compliance_requirement="Critical for determining the seven-year reporting period. Must be the original delinquency date, not reset by subsequent activity.",
        legal_language="Field 24 (Date of First Delinquency) is the cornerstone of FCRA Section 605(a) compliance. This date establishes when the seven-year reporting period begins and cannot be altered or 're-aged' by account sales, settlements, or other activities. Misreporting this date constitutes a willful violation of the FCRA.",
        fcra_section="605(a)",
        common_errors=[
            "Re-aging through date manipulation",
            "Missing DOFD on charged-off accounts",
            "DOFD changed after collection sale",
            "Incorrect calculation of DOFD"
        ]
    ),
    "payment_history_profile": Metro2FieldExplanation(
        field_name="Payment History Profile",
        field_number="Field 25 (K2 Segment)",
        segment="K2 Segment",
        description="Historical record of payment performance over up to 84 months.",
        compliance_requirement="Must accurately reflect actual payment history. Each month's status must be supported by verifiable records.",
        legal_language="The Payment History Profile provides a granular record of payment performance. Under FCRA Section 611, consumers have the right to dispute any month's reported status, and furnishers must verify each historical entry with supporting documentation.",
        fcra_section="611",
        common_errors=[
            "Unverified historical delinquencies",
            "Missing payment history data",
            "History inconsistent with current status",
            "Duplicate negative entries"
        ]
    ),
    "account_type": Metro2FieldExplanation(
        field_name="Account Type",
        field_number="Field 9",
        segment="Base Segment",
        description="Classification of the account type (installment, revolving, mortgage, etc.).",
        compliance_requirement="Must accurately identify the type of credit extended. Affects credit mix scoring factors.",
        legal_language="Field 9 (Account Type) classification impacts credit scoring algorithms that evaluate credit mix. Incorrect account type reporting can materially affect the consumer's credit profile under multiple scoring models.",
        fcra_section="607(b)",
        common_errors=[
            "Installment reported as revolving",
            "Incorrect mortgage classification",
            "Auto loan type miscoding",
            "Collection account type errors"
        ]
    ),
    "terms_duration": Metro2FieldExplanation(
        field_name="Terms Duration",
        field_number="Field 13",
        segment="Base Segment",
        description="The number of months in the payment term for installment accounts.",
        compliance_requirement="Required for installment accounts. Must reflect original contractual terms.",
        legal_language="Field 13 (Terms Duration) establishes the contractual repayment period. For installment loans, this field must accurately reflect the original agreement terms, as modifications to reported terms can affect the account's impact on credit utilization and mix calculations.",
        fcra_section="623(a)(1)",
        common_errors=[
            "Missing terms on installment accounts",
            "Terms inconsistent with payment amount",
            "Incorrect modification of terms",
            "Terms not updated for modifications"
        ]
    ),
    "original_creditor": Metro2FieldExplanation(
        field_name="Original Creditor Name",
        field_number="Field 6 (J2 Segment)",
        segment="J2 Segment",
        description="Name of the original creditor when account is sold or transferred.",
        compliance_requirement="Required when account has been sold or transferred. Must accurately identify the original creditor.",
        legal_language="The Original Creditor Name (J2 Segment Field 6) is required for sold or transferred accounts under the Metro-2 Format. FCRA Section 623(a)(6) mandates that debt buyers report the name of the original creditor, and failure to do so or reporting incorrectly violates accuracy requirements.",
        fcra_section="623(a)(6)",
        common_errors=[
            "Missing original creditor name",
            "Incorrect original creditor",
            "Failure to update after purchase",
            "Original creditor confusion with servicer"
        ]
    ),
    "consumer_information_indicator": Metro2FieldExplanation(
        field_name="Consumer Information Indicator",
        field_number="Field 38",
        segment="Base Segment",
        description="Special status codes for consumer accounts (bankruptcy, dispute, etc.).",
        compliance_requirement="Must accurately reflect current account conditions. Dispute flag (XB) required during active disputes.",
        legal_language="Field 38 (Consumer Information Indicator) is critical for compliance. When a consumer disputes an account, furnishers must report code 'XB' (Account Information Disputed by Consumer) until the dispute is resolved. Failure to do so violates FCRA Section 623(a)(3).",
        fcra_section="623(a)(3)",
        common_errors=[
            "Missing dispute flag during investigation",
            "Incorrect bankruptcy indicator",
            "Failure to remove dispute flag after resolution",
            "Wrong consumer statement indicator"
        ]
    ),
    "ecoa_code": Metro2FieldExplanation(
        field_name="ECOA Code",
        field_number="Field 4",
        segment="Base Segment",
        description="Equal Credit Opportunity Act designation for account relationship.",
        compliance_requirement="Must accurately identify the consumer's relationship to the account (individual, joint, authorized user, etc.).",
        legal_language="Field 4 (ECOA Code) determines responsibility attribution. Incorrect ECOA coding can result in accounts being reported to consumers who have no legal obligation on the debt, constituting a violation of FCRA accuracy requirements and potentially the ECOA.",
        fcra_section="607(b)",
        common_errors=[
            "Joint account reported as individual",
            "Authorized user shown as responsible party",
            "Incorrect co-signer designation",
            "Terminated authorized user still reporting"
        ]
    ),
    "portfolio_type": Metro2FieldExplanation(
        field_name="Portfolio Type",
        field_number="Field 10",
        segment="Base Segment",
        description="Classification of the portfolio category.",
        compliance_requirement="Must accurately classify the account's portfolio type.",
        legal_language="Field 10 (Portfolio Type) provides additional classification data for credit analysis. Accurate portfolio type reporting ensures proper evaluation by credit scoring models and lenders reviewing the consumer's credit profile.",
        fcra_section="607(b)",
        common_errors=[
            "Incorrect line of credit classification",
            "Mortgage portfolio type errors",
            "Auto loan classification issues",
            "Collection portfolio misclassification"
        ]
    ),
}


def get_metro2_explanation(field_name: str) -> Optional[Metro2FieldExplanation]:
    """Get the Metro-2 explanation for a given field name."""
    field_key = field_name.lower().replace(" ", "_").replace("-", "_")
    if field_key in METRO2_FIELDS:
        return METRO2_FIELDS[field_key]

    # Try partial matching
    for key, explanation in METRO2_FIELDS.items():
        if field_key in key or key in field_key:
            return explanation
        if field_name.lower() in explanation.field_name.lower():
            return explanation

    return None


def get_legal_explanation_for_field(field_name: str) -> str:
    """Get the legal language explanation for a Metro-2 field."""
    explanation = get_metro2_explanation(field_name)
    if explanation:
        return explanation.legal_language
    return f"The {field_name} field must be accurately reported per Metro-2 Format guidelines and FCRA requirements."


def get_compliance_requirement(field_name: str) -> str:
    """Get the compliance requirement for a Metro-2 field."""
    explanation = get_metro2_explanation(field_name)
    if explanation:
        return explanation.compliance_requirement
    return "Information must be accurate and verifiable per FCRA standards."


def get_fcra_section_for_field(field_name: str) -> str:
    """Get the applicable FCRA section for a Metro-2 field."""
    explanation = get_metro2_explanation(field_name)
    if explanation:
        return explanation.fcra_section
    return "611"


def get_common_errors_for_field(field_name: str) -> list:
    """Get common reporting errors for a Metro-2 field."""
    explanation = get_metro2_explanation(field_name)
    if explanation:
        return explanation.common_errors
    return ["Inaccurate reporting", "Failure to update information"]


def format_metro2_citation(field_name: str, violation_details: str = "") -> str:
    """
    Format a complete Metro-2 field citation for use in legal letters.

    Args:
        field_name: The Metro-2 field being cited
        violation_details: Optional specific details about the violation

    Returns:
        Formatted citation text for inclusion in dispute letter
    """
    explanation = get_metro2_explanation(field_name)

    if not explanation:
        return f"The {field_name} data element contains inaccurate information requiring correction under FCRA accuracy standards."

    citation_parts = [
        f"**{explanation.field_name} ({explanation.field_number})**",
        "",
        f"*Technical Requirement:* {explanation.compliance_requirement}",
        "",
        explanation.legal_language,
    ]

    if violation_details:
        citation_parts.extend([
            "",
            f"*Specific Issue:* {violation_details}"
        ])

    citation_parts.extend([
        "",
        f"*Applicable Law:* FCRA Section {explanation.fcra_section} ({FCRA_CITATIONS.get(explanation.fcra_section, '')})"
    ])

    return "\n".join(citation_parts)


# FCRA citation references
FCRA_CITATIONS = {
    "605(a)": "15 U.S.C. § 1681c(a) - Obsolete Information",
    "607(b)": "15 U.S.C. § 1681e(b) - Maximum Possible Accuracy",
    "611": "15 U.S.C. § 1681i - Procedure in Case of Disputed Accuracy",
    "611(a)(1)": "15 U.S.C. § 1681i(a)(1) - Reinvestigation Procedures",
    "611(a)(5)": "15 U.S.C. § 1681i(a)(5) - Deletion of Unverifiable Information",
    "623(a)(1)": "15 U.S.C. § 1681s-2(a)(1) - Duty to Provide Accurate Information",
    "623(a)(2)": "15 U.S.C. § 1681s-2(a)(2) - Duty to Correct and Update",
    "623(a)(3)": "15 U.S.C. § 1681s-2(a)(3) - Duty to Report Dispute Status",
    "623(a)(6)": "15 U.S.C. § 1681s-2(a)(6) - Duty to Report Original Creditor",
    "623(b)": "15 U.S.C. § 1681s-2(b) - Duties Upon Notice of Dispute",
}


def get_fcra_citation(section: str) -> str:
    """Get the full FCRA citation for a section number."""
    return FCRA_CITATIONS.get(section, f"15 U.S.C. § 1681 (Section {section})")


class Metro2ExplanationBuilder:
    """Builds comprehensive Metro-2 explanations for legal letters."""

    def __init__(self, violations: list = None):
        self.violations = violations or []
        self.field_explanations: Dict[str, Metro2FieldExplanation] = {}
        if self.violations:
            self._analyze_violations()

    def _analyze_violations(self) -> None:
        """Analyze violations to collect relevant Metro-2 fields."""
        for violation in self.violations:
            field = violation.get("metro2_field", "")
            if field:
                explanation = get_metro2_explanation(field)
                if explanation:
                    self.field_explanations[field] = explanation

    def get_unique_fields(self) -> list:
        """Get list of unique Metro-2 fields involved."""
        return list(self.field_explanations.keys())

    def get_technical_summary(self) -> str:
        """Generate a technical summary of Metro-2 issues."""
        if not self.field_explanations:
            return ""

        summaries = []
        for field, explanation in self.field_explanations.items():
            summaries.append(
                f"- **{explanation.field_name}** ({explanation.field_number}): "
                f"{explanation.compliance_requirement}"
            )

        return "\n".join(summaries)

    def get_fcra_sections_cited(self) -> list:
        """Get unique FCRA sections applicable to the Metro-2 issues."""
        sections = set()
        for explanation in self.field_explanations.values():
            sections.add(explanation.fcra_section)
        return sorted(list(sections))

    def build_detailed_explanation(self, field_name: str) -> str:
        """Build a detailed explanation for a specific field."""
        explanation = self.field_explanations.get(field_name) or get_metro2_explanation(field_name)

        if not explanation:
            return f"The {field_name} field requires accurate reporting under Metro-2 standards."

        return f"""
{explanation.field_name} ({explanation.field_number})
Segment: {explanation.segment}

Technical Description:
{explanation.description}

Compliance Standard:
{explanation.compliance_requirement}

Legal Basis:
{explanation.legal_language}

Applicable FCRA Section: {explanation.fcra_section}
({get_fcra_citation(explanation.fcra_section)})
"""
