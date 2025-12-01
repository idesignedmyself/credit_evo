"""
Legal Letter Generator - Validators
Ensures legal letter structure is complete and valid.
"""
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class ValidationLevel(str, Enum):
    """Severity level for validation issues."""
    ERROR = "error"      # Must be fixed before generation
    WARNING = "warning"  # Can proceed but may have issues
    INFO = "info"        # Informational only


@dataclass
class ValidationIssue:
    """A single validation issue."""
    level: ValidationLevel
    code: str
    message: str
    field: Optional[str] = None
    suggestion: Optional[str] = None


class LegalLetterValidator:
    """Validates legal letter components before assembly."""

    # Required sections for a complete legal letter
    REQUIRED_SECTIONS = [
        "introduction",
        "violations",
        "demands",
        "conclusion",
    ]

    # Optional but recommended sections
    RECOMMENDED_SECTIONS = [
        "legal_basis",
        "mov",
        "case_law",
        "metro2",
    ]

    # Valid tones
    VALID_TONES = ["strict_legal", "professional", "soft_legal", "aggressive"]

    # Valid grouping strategies
    VALID_STRATEGIES = ["by_fcra_section", "by_metro2_field", "by_creditor", "by_severity"]

    # FCRA sections that require specific documentation
    FCRA_SECTION_REQUIREMENTS = {
        "611": ["dispute_statement", "violation_details"],
        "611(a)(1)": ["reinvestigation_demand", "violation_details"],
        "611(a)(5)": ["deletion_demand"],
        "623": ["furnisher_identification", "account_details"],
        "623(a)(1)": ["furnisher_identification", "inaccuracy_description"],
        "623(b)": ["dispute_notice_reference"],
        "607(b)": ["accuracy_violation_description"],
        "605(a)": ["date_calculation", "obsolete_item_details"],
    }

    @classmethod
    def validate_violations(cls, violations: List[Dict[str, Any]]) -> List[ValidationIssue]:
        """Validate the violations list."""
        issues = []

        if not violations:
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                code="NO_VIOLATIONS",
                message="At least one violation is required to generate a legal letter",
                suggestion="Select accounts with disputes to include in the letter"
            ))
            return issues

        for i, violation in enumerate(violations):
            v_issues = cls._validate_single_violation(violation, i)
            issues.extend(v_issues)

        return issues

    @classmethod
    def _validate_single_violation(cls, violation: Dict[str, Any], index: int) -> List[ValidationIssue]:
        """Validate a single violation entry."""
        issues = []
        field_prefix = f"violations[{index}]"

        # Required fields
        if not violation.get("creditor_name"):
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                code="MISSING_CREDITOR",
                message=f"Violation {index + 1}: Missing creditor name",
                field=f"{field_prefix}.creditor_name",
                suggestion="Provide the name of the creditor or furnisher"
            ))

        if not violation.get("violation_type"):
            issues.append(ValidationIssue(
                level=ValidationLevel.WARNING,
                code="MISSING_VIOLATION_TYPE",
                message=f"Violation {index + 1}: No violation type specified",
                field=f"{field_prefix}.violation_type",
                suggestion="Specify the type of inaccuracy (e.g., 'balance_error', 'payment_history_error')"
            ))

        # Recommended fields
        if not violation.get("fcra_section"):
            issues.append(ValidationIssue(
                level=ValidationLevel.INFO,
                code="MISSING_FCRA_SECTION",
                message=f"Violation {index + 1}: No FCRA section specified",
                field=f"{field_prefix}.fcra_section",
                suggestion="Section will be auto-assigned based on violation type"
            ))

        if not violation.get("account_number_masked") and not violation.get("account_number"):
            issues.append(ValidationIssue(
                level=ValidationLevel.WARNING,
                code="MISSING_ACCOUNT_NUMBER",
                message=f"Violation {index + 1}: No account number provided",
                field=f"{field_prefix}.account_number_masked",
                suggestion="Include masked account number for identification"
            ))

        return issues

    @classmethod
    def validate_consumer_info(cls, consumer: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate consumer information."""
        issues = []

        if not consumer:
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                code="NO_CONSUMER_INFO",
                message="Consumer information is required",
                suggestion="Provide consumer name and address"
            ))
            return issues

        if not consumer.get("name"):
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                code="MISSING_CONSUMER_NAME",
                message="Consumer name is required for the letter",
                field="consumer.name",
                suggestion="Enter the consumer's full legal name"
            ))

        if not consumer.get("address"):
            issues.append(ValidationIssue(
                level=ValidationLevel.WARNING,
                code="MISSING_CONSUMER_ADDRESS",
                message="Consumer address is recommended",
                field="consumer.address",
                suggestion="Include address for proper identification"
            ))

        return issues

    @classmethod
    def validate_recipient(cls, recipient: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate recipient (bureau/furnisher) information."""
        issues = []

        if not recipient:
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                code="NO_RECIPIENT_INFO",
                message="Recipient information is required",
                suggestion="Specify the credit bureau or furnisher"
            ))
            return issues

        if not recipient.get("name"):
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                code="MISSING_RECIPIENT_NAME",
                message="Recipient name is required",
                field="recipient.name",
                suggestion="Specify TransUnion, Experian, Equifax, or furnisher name"
            ))

        if not recipient.get("address"):
            issues.append(ValidationIssue(
                level=ValidationLevel.INFO,
                code="MISSING_RECIPIENT_ADDRESS",
                message="Recipient address will use default bureau address",
                field="recipient.address"
            ))

        return issues

    @classmethod
    def validate_tone(cls, tone: str) -> List[ValidationIssue]:
        """Validate the selected tone."""
        issues = []

        if not tone:
            issues.append(ValidationIssue(
                level=ValidationLevel.WARNING,
                code="NO_TONE_SELECTED",
                message="No tone selected, defaulting to 'professional'",
                field="tone",
                suggestion="Choose a tone: strict_legal, professional, soft_legal, or aggressive"
            ))
        elif tone not in cls.VALID_TONES:
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                code="INVALID_TONE",
                message=f"Invalid tone '{tone}'",
                field="tone",
                suggestion=f"Valid tones: {', '.join(cls.VALID_TONES)}"
            ))

        return issues

    @classmethod
    def validate_grouping_strategy(cls, strategy: str) -> List[ValidationIssue]:
        """Validate the grouping strategy."""
        issues = []

        if not strategy:
            issues.append(ValidationIssue(
                level=ValidationLevel.INFO,
                code="NO_STRATEGY_SELECTED",
                message="No grouping strategy selected, defaulting to 'by_fcra_section'",
                field="grouping_strategy"
            ))
        elif strategy not in cls.VALID_STRATEGIES:
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                code="INVALID_STRATEGY",
                message=f"Invalid grouping strategy '{strategy}'",
                field="grouping_strategy",
                suggestion=f"Valid strategies: {', '.join(cls.VALID_STRATEGIES)}"
            ))

        return issues

    @classmethod
    def validate_sections(cls, sections: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate letter sections configuration."""
        issues = []

        if not sections:
            return issues  # Will use defaults

        # Check for unknown sections
        known_sections = set(cls.REQUIRED_SECTIONS + cls.RECOMMENDED_SECTIONS)
        for section in sections.keys():
            if section not in known_sections:
                issues.append(ValidationIssue(
                    level=ValidationLevel.WARNING,
                    code="UNKNOWN_SECTION",
                    message=f"Unknown section '{section}' will be ignored",
                    field=f"sections.{section}"
                ))

        return issues

    @classmethod
    def validate_fcra_compliance(cls, violations: List[Dict[str, Any]]) -> List[ValidationIssue]:
        """Validate FCRA compliance requirements."""
        issues = []

        # Check for sections that require specific documentation
        for violation in violations:
            fcra_section = violation.get("fcra_section", "")
            requirements = cls.FCRA_SECTION_REQUIREMENTS.get(fcra_section, [])

            for req in requirements:
                if req == "dispute_statement" and not violation.get("dispute_reason"):
                    issues.append(ValidationIssue(
                        level=ValidationLevel.WARNING,
                        code="MISSING_DISPUTE_REASON",
                        message=f"Section {fcra_section} dispute should include reason",
                        field="dispute_reason",
                        suggestion="Add specific reason why information is disputed"
                    ))

        return issues

    @classmethod
    def validate_all(
        cls,
        violations: List[Dict[str, Any]],
        consumer: Dict[str, Any],
        recipient: Dict[str, Any],
        tone: str,
        grouping_strategy: str = None,
        sections: Dict[str, Any] = None
    ) -> Tuple[bool, List[ValidationIssue]]:
        """
        Run all validations and return overall result.

        Returns:
            Tuple of (is_valid, issues)
            - is_valid: True if no ERROR level issues
            - issues: List of all validation issues
        """
        all_issues = []

        all_issues.extend(cls.validate_violations(violations))
        all_issues.extend(cls.validate_consumer_info(consumer))
        all_issues.extend(cls.validate_recipient(recipient))
        all_issues.extend(cls.validate_tone(tone))

        if grouping_strategy:
            all_issues.extend(cls.validate_grouping_strategy(grouping_strategy))

        if sections:
            all_issues.extend(cls.validate_sections(sections))

        all_issues.extend(cls.validate_fcra_compliance(violations))

        # Check if any errors exist
        has_errors = any(issue.level == ValidationLevel.ERROR for issue in all_issues)

        return (not has_errors, all_issues)

    @classmethod
    def format_issues(cls, issues: List[ValidationIssue]) -> str:
        """Format validation issues as a readable string."""
        if not issues:
            return "No validation issues found."

        lines = []

        # Group by level
        errors = [i for i in issues if i.level == ValidationLevel.ERROR]
        warnings = [i for i in issues if i.level == ValidationLevel.WARNING]
        infos = [i for i in issues if i.level == ValidationLevel.INFO]

        if errors:
            lines.append("ERRORS (must fix):")
            for issue in errors:
                lines.append(f"  - [{issue.code}] {issue.message}")
                if issue.suggestion:
                    lines.append(f"    Suggestion: {issue.suggestion}")

        if warnings:
            lines.append("\nWARNINGS (recommended to fix):")
            for issue in warnings:
                lines.append(f"  - [{issue.code}] {issue.message}")
                if issue.suggestion:
                    lines.append(f"    Suggestion: {issue.suggestion}")

        if infos:
            lines.append("\nINFO:")
            for issue in infos:
                lines.append(f"  - [{issue.code}] {issue.message}")

        return "\n".join(lines)


class LetterContentValidator:
    """Validates generated letter content."""

    # Minimum lengths for sections (in characters)
    MIN_SECTION_LENGTHS = {
        "introduction": 100,
        "violations": 50,
        "demands": 50,
        "conclusion": 50,
    }

    # Maximum letter length (characters)
    MAX_LETTER_LENGTH = 50000

    # Required phrases that should appear in legal letters
    REQUIRED_PHRASES = {
        "strict_legal": ["Fair Credit Reporting Act", "15 U.S.C."],
        "professional": ["Fair Credit Reporting Act", "dispute"],
        "soft_legal": ["credit report", "dispute"],
        "aggressive": ["FCRA", "violation", "demand"],
    }

    @classmethod
    def validate_letter_content(
        cls,
        content: str,
        tone: str
    ) -> List[ValidationIssue]:
        """Validate generated letter content."""
        issues = []

        if not content:
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                code="EMPTY_LETTER",
                message="Generated letter is empty"
            ))
            return issues

        # Check length
        if len(content) > cls.MAX_LETTER_LENGTH:
            issues.append(ValidationIssue(
                level=ValidationLevel.WARNING,
                code="LETTER_TOO_LONG",
                message=f"Letter exceeds {cls.MAX_LETTER_LENGTH} characters",
                suggestion="Consider splitting into multiple letters"
            ))

        if len(content) < 200:
            issues.append(ValidationIssue(
                level=ValidationLevel.WARNING,
                code="LETTER_TOO_SHORT",
                message="Letter seems unusually short",
                suggestion="Verify all sections were included"
            ))

        # Check for required phrases
        required = cls.REQUIRED_PHRASES.get(tone, [])
        for phrase in required:
            if phrase.lower() not in content.lower():
                issues.append(ValidationIssue(
                    level=ValidationLevel.WARNING,
                    code="MISSING_REQUIRED_PHRASE",
                    message=f"Expected phrase '{phrase}' not found in {tone} letter",
                    suggestion="Verify letter was generated with correct tone"
                ))

        return issues

    @classmethod
    def validate_section_content(
        cls,
        section_name: str,
        content: str
    ) -> List[ValidationIssue]:
        """Validate a specific section's content."""
        issues = []

        min_length = cls.MIN_SECTION_LENGTHS.get(section_name, 0)

        if not content:
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                code=f"EMPTY_{section_name.upper()}",
                message=f"Section '{section_name}' is empty"
            ))
        elif len(content) < min_length:
            issues.append(ValidationIssue(
                level=ValidationLevel.WARNING,
                code=f"SHORT_{section_name.upper()}",
                message=f"Section '{section_name}' is shorter than expected ({len(content)} < {min_length} chars)"
            ))

        return issues
