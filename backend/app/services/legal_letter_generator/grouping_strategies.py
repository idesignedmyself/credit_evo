"""
Legal Letter Generator - Grouping Strategies
Groups violations by legal/technical criteria for structured dispute letters.
"""
from typing import List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum


class GroupingStrategy(str, Enum):
    """Available grouping strategies for legal letters."""
    BY_FCRA_SECTION = "by_fcra_section"
    BY_METRO2_FIELD = "by_metro2_field"
    BY_CREDITOR = "by_creditor"
    BY_SEVERITY = "by_severity"


@dataclass
class ViolationGroup:
    """A group of related violations with legal context."""
    group_key: str
    group_label: str
    fcra_section: str
    legal_requirement: str
    violations: List[Dict[str, Any]] = field(default_factory=list)
    metro2_fields: List[str] = field(default_factory=list)
    creditors: List[str] = field(default_factory=list)
    account_numbers: List[str] = field(default_factory=list)


# FCRA section descriptions for legal citations
FCRA_SECTIONS = {
    "611": {
        "title": "Procedure in Case of Disputed Accuracy",
        "requirement": "Consumer reporting agencies must conduct a reasonable reinvestigation of disputed information within 30 days.",
        "citation": "15 U.S.C. § 1681i"
    },
    "611(a)": {
        "title": "Reinvestigation Required",
        "requirement": "Upon receiving a dispute, the CRA must reinvestigate free of charge and record the current status of the disputed information.",
        "citation": "15 U.S.C. § 1681i(a)"
    },
    "611(a)(1)": {
        "title": "Reinvestigation Procedures",
        "requirement": "The CRA must conduct a reasonable reinvestigation to determine whether the disputed information is inaccurate.",
        "citation": "15 U.S.C. § 1681i(a)(1)"
    },
    "611(a)(5)": {
        "title": "Deletion of Information",
        "requirement": "If information cannot be verified within the reinvestigation period, it must be promptly deleted.",
        "citation": "15 U.S.C. § 1681i(a)(5)"
    },
    "623": {
        "title": "Responsibilities of Furnishers",
        "requirement": "Furnishers must provide accurate information and investigate consumer disputes.",
        "citation": "15 U.S.C. § 1681s-2"
    },
    "623(a)(1)": {
        "title": "Duty to Provide Accurate Information",
        "requirement": "A person shall not furnish information relating to a consumer to a CRA if the person knows or has reasonable cause to believe that the information is inaccurate.",
        "citation": "15 U.S.C. § 1681s-2(a)(1)"
    },
    "623(a)(2)": {
        "title": "Duty to Correct and Update",
        "requirement": "Furnishers must promptly notify CRAs of any corrections or updates to previously reported information.",
        "citation": "15 U.S.C. § 1681s-2(a)(2)"
    },
    "623(b)": {
        "title": "Duties Upon Notice of Dispute",
        "requirement": "After receiving notice of a dispute, furnishers must investigate and report results to the CRA.",
        "citation": "15 U.S.C. § 1681s-2(b)"
    },
    "605": {
        "title": "Requirements for Reporting",
        "requirement": "Information must meet accuracy standards and cannot be reported beyond applicable time limits.",
        "citation": "15 U.S.C. § 1681c"
    },
    "605(a)": {
        "title": "Obsolete Information",
        "requirement": "Certain adverse information cannot be reported after 7 years (10 years for bankruptcies).",
        "citation": "15 U.S.C. § 1681c(a)"
    },
    "607": {
        "title": "Compliance Procedures",
        "requirement": "CRAs must maintain reasonable procedures to assure maximum possible accuracy.",
        "citation": "15 U.S.C. § 1681e"
    },
    "607(b)": {
        "title": "Maximum Possible Accuracy",
        "requirement": "CRAs must follow reasonable procedures to assure maximum possible accuracy of information in consumer reports.",
        "citation": "15 U.S.C. § 1681e(b)"
    },
    "609": {
        "title": "Disclosures to Consumers",
        "requirement": "Upon request, CRAs must clearly and accurately disclose all information in the consumer's file.",
        "citation": "15 U.S.C. § 1681g"
    },
    "609(a)(1)": {
        "title": "Disclosure of Information",
        "requirement": "CRAs must disclose all information in consumer's file at time of request, including sources.",
        "citation": "15 U.S.C. § 1681g(a)(1)"
    },
    "612": {
        "title": "Charges for Disclosures",
        "requirement": "Consumers are entitled to free annual file disclosures and free disclosures after adverse actions.",
        "citation": "15 U.S.C. § 1681j"
    },
}

# Metro-2 field categories for technical grouping
METRO2_FIELD_CATEGORIES = {
    "payment_status": {
        "fields": ["Current Status", "Payment Status", "Account Status", "Payment Rating"],
        "description": "Payment history and current account standing",
        "fcra_relevance": "611, 623(a)(1)"
    },
    "balance_amount": {
        "fields": ["Current Balance", "Balance Amount", "High Credit", "Credit Limit", "Original Amount"],
        "description": "Balance and credit limit information",
        "fcra_relevance": "623(a)(2)"
    },
    "date_fields": {
        "fields": ["Date Opened", "Date Reported", "Date of Last Activity", "Date of First Delinquency", "Date Closed"],
        "description": "Account timeline and activity dates",
        "fcra_relevance": "605(a), 623(a)(1)"
    },
    "account_info": {
        "fields": ["Account Number", "Account Type", "Portfolio Type", "Terms Duration", "Terms Frequency"],
        "description": "Core account identification and terms",
        "fcra_relevance": "607(b)"
    },
    "payment_history": {
        "fields": ["Payment History", "Payment Pattern", "Historical Status", "Months Reviewed"],
        "description": "Historical payment performance pattern",
        "fcra_relevance": "611, 623(a)(1)"
    },
    "creditor_info": {
        "fields": ["Creditor Name", "Original Creditor", "Subscriber Code", "Creditor Classification"],
        "description": "Furnisher identification information",
        "fcra_relevance": "609(a)(1), 623"
    },
    "remarks": {
        "fields": ["Consumer Statement", "Special Comment", "Compliance Condition", "ECOA Code"],
        "description": "Special conditions and consumer remarks",
        "fcra_relevance": "611(a), 609"
    },
}

# Violation type to FCRA section mapping
VIOLATION_FCRA_MAP = {
    "inaccurate_balance": "623(a)(1)",
    "incorrect_payment_status": "623(a)(1)",
    "wrong_account_status": "623(a)(1)",
    "outdated_information": "605(a)",
    "obsolete_account": "605(a)",
    "incorrect_dates": "623(a)(2)",
    "missing_payment_history": "611",
    "duplicate_account": "607(b)",
    "wrong_creditor_name": "609(a)(1)",
    "incorrect_high_credit": "623(a)(1)",
    "wrong_credit_limit": "623(a)(1)",
    "payment_history_error": "623(a)(1)",
    "incorrect_account_type": "607(b)",
    "mixed_file": "607(b)",
    "identity_error": "607(b)",
    "balance_discrepancy": "623(a)(1)",
    "late_payment_dispute": "611",
    "charge_off_dispute": "623(a)(1)",
    "collection_dispute": "623(b)",
    "not_mine": "607(b)",
    "fraud_alert": "605",
    "reinsertion": "611(a)(5)",
    "failure_to_investigate": "611(a)(1)",
    "incomplete_investigation": "611(a)(1)",
    "unverifiable_information": "611(a)(5)",
}


def get_fcra_section_details(section: str) -> Dict[str, str]:
    """Get full FCRA section details including title and requirement."""
    from .fcra_statutes import resolve_statute
    return FCRA_SECTIONS.get(section, {
        "title": "FCRA Compliance",
        "requirement": "Information must be accurate and verifiable per FCRA standards.",
        "citation": resolve_statute(section)
    })


def get_metro2_category(field_name: str) -> str:
    """Determine the Metro-2 category for a given field name."""
    field_lower = field_name.lower()
    for category, data in METRO2_FIELD_CATEGORIES.items():
        for field in data["fields"]:
            if field.lower() in field_lower or field_lower in field.lower():
                return category
    return "other"


def get_violation_fcra_section(violation_type: str) -> str:
    """Map a violation type to its primary FCRA section."""
    return VIOLATION_FCRA_MAP.get(violation_type, "611")


class LegalGrouper:
    """Groups violations using legal/technical criteria for dispute letters."""

    def __init__(self, violations: List[Dict[str, Any]]):
        self.violations = violations

    def group_by_fcra_section(self) -> Dict[str, ViolationGroup]:
        """Group violations by their applicable FCRA section."""
        groups: Dict[str, ViolationGroup] = {}

        for violation in self.violations:
            v_type = violation.get("violation_type", "")
            fcra_section = violation.get("fcra_section") or get_violation_fcra_section(v_type)

            if fcra_section not in groups:
                section_details = get_fcra_section_details(fcra_section)
                groups[fcra_section] = ViolationGroup(
                    group_key=fcra_section,
                    group_label=f"FCRA Section {fcra_section} - {section_details['title']}",
                    fcra_section=fcra_section,
                    legal_requirement=section_details["requirement"],
                )

            group = groups[fcra_section]
            group.violations.append(violation)

            # Track Metro-2 fields
            metro2_field = violation.get("metro2_field")
            if metro2_field and metro2_field not in group.metro2_fields:
                group.metro2_fields.append(metro2_field)

            # Track creditors
            creditor = violation.get("creditor_name", "Unknown")
            if creditor not in group.creditors:
                group.creditors.append(creditor)

            # Track account numbers
            acct_num = violation.get("account_number_masked", "")
            if acct_num and acct_num not in group.account_numbers:
                group.account_numbers.append(acct_num)

        return groups

    def group_by_metro2_field(self) -> Dict[str, ViolationGroup]:
        """Group violations by Metro-2 field category."""
        groups: Dict[str, ViolationGroup] = {}

        for violation in self.violations:
            metro2_field = violation.get("metro2_field", "")
            category = get_metro2_category(metro2_field) if metro2_field else "other"

            category_data = METRO2_FIELD_CATEGORIES.get(category, {
                "description": "Other data fields",
                "fcra_relevance": "611"
            })

            if category not in groups:
                groups[category] = ViolationGroup(
                    group_key=category,
                    group_label=f"Metro-2 {category.replace('_', ' ').title()} Fields",
                    fcra_section=category_data.get("fcra_relevance", "611").split(",")[0].strip(),
                    legal_requirement=category_data["description"],
                )

            group = groups[category]
            group.violations.append(violation)

            if metro2_field and metro2_field not in group.metro2_fields:
                group.metro2_fields.append(metro2_field)

            creditor = violation.get("creditor_name", "Unknown")
            if creditor not in group.creditors:
                group.creditors.append(creditor)

            acct_num = violation.get("account_number_masked", "")
            if acct_num and acct_num not in group.account_numbers:
                group.account_numbers.append(acct_num)

        return groups

    def group_by_creditor(self) -> Dict[str, ViolationGroup]:
        """Group violations by creditor/furnisher."""
        groups: Dict[str, ViolationGroup] = {}

        for violation in self.violations:
            creditor = violation.get("creditor_name", "Unknown Creditor")
            creditor_key = creditor.lower().replace(" ", "_")

            if creditor_key not in groups:
                groups[creditor_key] = ViolationGroup(
                    group_key=creditor_key,
                    group_label=f"Furnisher: {creditor}",
                    fcra_section="623",
                    legal_requirement="Furnishers have a duty to report accurate information per FCRA Section 623.",
                )
                groups[creditor_key].creditors.append(creditor)

            group = groups[creditor_key]
            group.violations.append(violation)

            metro2_field = violation.get("metro2_field")
            if metro2_field and metro2_field not in group.metro2_fields:
                group.metro2_fields.append(metro2_field)

            fcra_section = violation.get("fcra_section") or get_violation_fcra_section(violation.get("violation_type", ""))
            if fcra_section != "623" and fcra_section not in str(group.fcra_section):
                group.fcra_section = f"{group.fcra_section}, {fcra_section}"

            acct_num = violation.get("account_number_masked", "")
            if acct_num and acct_num not in group.account_numbers:
                group.account_numbers.append(acct_num)

        return groups

    def group_by_severity(self) -> Dict[str, ViolationGroup]:
        """Group violations by severity level."""
        severity_labels = {
            "critical": "Critical Violations Requiring Immediate Action",
            "high": "High Priority Accuracy Violations",
            "medium": "Material Inaccuracies",
            "low": "Minor Discrepancies"
        }

        severity_requirements = {
            "critical": "These violations represent severe inaccuracies that significantly impact creditworthiness and require immediate correction under FCRA Section 611.",
            "high": "These violations constitute material inaccuracies that furnishers are obligated to correct under FCRA Section 623(a)(1).",
            "medium": "These discrepancies require verification and potential correction under FCRA Section 611(a).",
            "low": "These items require review for accuracy under FCRA maximum accuracy standards (Section 607(b))."
        }

        groups: Dict[str, ViolationGroup] = {}

        for violation in self.violations:
            severity = violation.get("severity", "medium").lower()
            if severity not in severity_labels:
                severity = "medium"

            if severity not in groups:
                groups[severity] = ViolationGroup(
                    group_key=severity,
                    group_label=severity_labels[severity],
                    fcra_section="611" if severity in ["critical", "high"] else "607(b)",
                    legal_requirement=severity_requirements[severity],
                )

            group = groups[severity]
            group.violations.append(violation)

            metro2_field = violation.get("metro2_field")
            if metro2_field and metro2_field not in group.metro2_fields:
                group.metro2_fields.append(metro2_field)

            creditor = violation.get("creditor_name", "Unknown")
            if creditor not in group.creditors:
                group.creditors.append(creditor)

            acct_num = violation.get("account_number_masked", "")
            if acct_num and acct_num not in group.account_numbers:
                group.account_numbers.append(acct_num)

        return groups

    def group(self, strategy: GroupingStrategy = GroupingStrategy.BY_FCRA_SECTION) -> Dict[str, ViolationGroup]:
        """Group violations using the specified strategy."""
        strategies = {
            GroupingStrategy.BY_FCRA_SECTION: self.group_by_fcra_section,
            GroupingStrategy.BY_METRO2_FIELD: self.group_by_metro2_field,
            GroupingStrategy.BY_CREDITOR: self.group_by_creditor,
            GroupingStrategy.BY_SEVERITY: self.group_by_severity,
        }

        return strategies.get(strategy, self.group_by_fcra_section)()


def group_violations(
    violations: List[Dict[str, Any]],
    strategy: str = "by_fcra_section"
) -> Dict[str, ViolationGroup]:
    """
    Convenience function to group violations.

    Args:
        violations: List of violation dictionaries
        strategy: Grouping strategy name

    Returns:
        Dictionary mapping group keys to ViolationGroup objects
    """
    try:
        strategy_enum = GroupingStrategy(strategy)
    except ValueError:
        strategy_enum = GroupingStrategy.BY_FCRA_SECTION

    grouper = LegalGrouper(violations)
    return grouper.group(strategy_enum)
