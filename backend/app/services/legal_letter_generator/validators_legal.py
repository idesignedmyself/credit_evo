"""
Legal Letter Generator - Validators
Ensures legal letter structure is complete and valid.
Includes structural validation for section ordering and domain isolation.
"""
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import re

from .structural_fixer import (
    StructuralFixer,
    LetterDomainType,
    LEGAL_SECTION_SPECS,
    CIVIL_SECTION_SPECS,
    LEGAL_ONLY_TERMS,
    CIVIL_ONLY_TERMS,
)


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


class StructuralValidator:
    """Validates structural integrity of generated letters."""

    def __init__(self):
        self.fixer = StructuralFixer()

    @classmethod
    def validate_legal_order(cls, content: str) -> List[ValidationIssue]:
        """Validate that legal letter sections are in correct order."""
        issues = []
        last_position = -1
        last_section = None

        for spec in LEGAL_SECTION_SPECS:
            for pattern in spec.header_patterns:
                match = re.search(pattern, content, re.IGNORECASE | re.MULTILINE)
                if match:
                    position = match.start()
                    if position < last_position and spec.position > 0:
                        issues.append(ValidationIssue(
                            level=ValidationLevel.ERROR,
                            code="SECTION_ORDER_VIOLATION",
                            message=f"Section '{spec.name}' appears before '{last_section}' but should come after",
                            field=spec.name,
                            suggestion=f"Move '{spec.name}' section to correct position"
                        ))
                    last_position = position
                    last_section = spec.name
                    break

        return issues

    @classmethod
    def validate_civil_order(cls, content: str) -> List[ValidationIssue]:
        """Validate that civil letter sections are in correct order."""
        issues = []
        last_position = -1
        last_section = None

        for spec in CIVIL_SECTION_SPECS:
            for pattern in spec.header_patterns:
                match = re.search(pattern, content, re.IGNORECASE | re.MULTILINE)
                if match:
                    position = match.start()
                    if position < last_position and spec.position > 0:
                        issues.append(ValidationIssue(
                            level=ValidationLevel.ERROR,
                            code="SECTION_ORDER_VIOLATION",
                            message=f"Section '{spec.name}' appears before '{last_section}' but should come after",
                            field=spec.name,
                            suggestion=f"Move '{spec.name}' section to correct position"
                        ))
                    last_position = position
                    last_section = spec.name
                    break

        return issues

    @classmethod
    def validate_required_sections(
        cls,
        content: str,
        domain: str
    ) -> List[ValidationIssue]:
        """Validate that all required sections are present."""
        issues = []
        specs = LEGAL_SECTION_SPECS if domain == "legal" else CIVIL_SECTION_SPECS
        domain_type = LetterDomainType(domain)

        for spec in specs:
            if not spec.required:
                continue
            if domain_type in spec.forbidden_in_domains:
                continue

            found = False
            for pattern in spec.header_patterns:
                if re.search(pattern, content, re.IGNORECASE | re.MULTILINE):
                    found = True
                    break

            if not found:
                issues.append(ValidationIssue(
                    level=ValidationLevel.ERROR,
                    code="MISSING_REQUIRED_SECTION",
                    message=f"Required section '{spec.name}' is missing",
                    field=spec.name,
                    suggestion=f"Add '{spec.name}' section to the letter"
                ))

        return issues

    @classmethod
    def validate_no_cross_domain_bleed(
        cls,
        content: str,
        domain: str
    ) -> List[ValidationIssue]:
        """Validate that no cross-domain content exists."""
        issues = []
        domain_type = LetterDomainType(domain)

        if domain_type == LetterDomainType.CIVIL:
            # Check for legal-only terms
            for pattern in LEGAL_ONLY_TERMS:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    issues.append(ValidationIssue(
                        level=ValidationLevel.ERROR,
                        code="CROSS_DOMAIN_TERM",
                        message=f"Legal term '{match.group()}' found in civil letter",
                        suggestion="Remove legal terminology from civil letter"
                    ))

            # Check for forbidden sections
            for spec in LEGAL_SECTION_SPECS:
                if LetterDomainType.CIVIL in spec.forbidden_in_domains:
                    for pattern in spec.header_patterns:
                        if re.search(pattern, content, re.IGNORECASE | re.MULTILINE):
                            issues.append(ValidationIssue(
                                level=ValidationLevel.ERROR,
                                code="FORBIDDEN_SECTION",
                                message=f"Legal-only section '{spec.name}' found in civil letter",
                                field=spec.name,
                                suggestion=f"Remove '{spec.name}' section from civil letter"
                            ))

        elif domain_type == LetterDomainType.LEGAL:
            # Check for civil-only terms
            for pattern in CIVIL_ONLY_TERMS:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    issues.append(ValidationIssue(
                        level=ValidationLevel.WARNING,
                        code="CROSS_DOMAIN_TERM",
                        message=f"Civil term '{match.group()}' found in legal letter",
                        suggestion="Consider using more formal legal language"
                    ))

        return issues

    @classmethod
    def validate_mov_position(cls, content: str) -> List[ValidationIssue]:
        """Validate that MOV section is in correct position (after Metro2, before Case Law)."""
        issues = []
        mov_match = re.search(r"METHOD OF VERIFICATION|MOV\b", content, re.IGNORECASE)

        if not mov_match:
            return issues

        mov_pos = mov_match.start()

        # Check Metro2 is before MOV
        metro2_match = re.search(r"METRO-?2", content, re.IGNORECASE)
        if metro2_match and metro2_match.start() > mov_pos:
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                code="MOV_POSITION_VIOLATION",
                message="Metro-2 section should appear before MOV section",
                field="mov_section",
                suggestion="Reorder sections: Metro-2 -> MOV -> Case Law"
            ))

        # Check Case Law is after MOV
        case_law_match = re.search(r"CASE LAW|LEGAL PRECEDENT", content, re.IGNORECASE)
        if case_law_match and case_law_match.start() < mov_pos:
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                code="MOV_POSITION_VIOLATION",
                message="Case Law section should appear after MOV section",
                field="mov_section",
                suggestion="Reorder sections: Metro-2 -> MOV -> Case Law"
            ))

        return issues

    @classmethod
    def validate_case_law_position(cls, content: str) -> List[ValidationIssue]:
        """Validate that Case Law section is in correct position (after MOV, before Demands)."""
        issues = []
        case_law_match = re.search(r"CASE LAW|LEGAL PRECEDENT", content, re.IGNORECASE)

        if not case_law_match:
            return issues

        case_pos = case_law_match.start()

        # Check MOV is before Case Law
        mov_match = re.search(r"METHOD OF VERIFICATION|MOV\b", content, re.IGNORECASE)
        if mov_match and mov_match.start() > case_pos:
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                code="CASE_LAW_POSITION_VIOLATION",
                message="MOV section should appear before Case Law section",
                field="case_law",
                suggestion="Reorder sections: MOV -> Case Law -> Demands"
            ))

        # Check Demands is after Case Law
        demands_match = re.search(r"FORMAL DEMANDS|DEMANDS\b", content, re.IGNORECASE)
        if demands_match and demands_match.start() < case_pos:
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                code="CASE_LAW_POSITION_VIOLATION",
                message="Demands section should appear after Case Law section",
                field="case_law",
                suggestion="Reorder sections: MOV -> Case Law -> Demands"
            ))

        return issues

    @classmethod
    def validate_metro2_position(cls, content: str) -> List[ValidationIssue]:
        """Validate that Metro-2 section is in correct position (after Violations, before MOV)."""
        issues = []
        metro2_match = re.search(r"METRO-?2", content, re.IGNORECASE)

        if not metro2_match:
            return issues

        metro2_pos = metro2_match.start()

        # Check Violations is before Metro-2
        violations_match = re.search(r"SPECIFIC VIOLATIONS|VIOLATIONS\b|DISPUTED ITEMS", content, re.IGNORECASE)
        if violations_match and violations_match.start() > metro2_pos:
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                code="METRO2_POSITION_VIOLATION",
                message="Violations section should appear before Metro-2 section",
                field="metro2_compliance",
                suggestion="Reorder sections: Violations -> Metro-2 -> MOV"
            ))

        # Check MOV is after Metro-2
        mov_match = re.search(r"METHOD OF VERIFICATION|MOV\b", content, re.IGNORECASE)
        if mov_match and mov_match.start() < metro2_pos:
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                code="METRO2_POSITION_VIOLATION",
                message="MOV section should appear after Metro-2 section",
                field="metro2_compliance",
                suggestion="Reorder sections: Violations -> Metro-2 -> MOV"
            ))

        return issues

    @classmethod
    def validate_section_count(
        cls,
        content: str,
        domain: str
    ) -> List[ValidationIssue]:
        """Validate the number of sections matches expectations."""
        issues = []
        specs = LEGAL_SECTION_SPECS if domain == "legal" else CIVIL_SECTION_SPECS
        domain_type = LetterDomainType(domain)

        found_count = 0
        expected_required = 0

        for spec in specs:
            if domain_type in spec.forbidden_in_domains:
                continue

            if spec.required:
                expected_required += 1

            for pattern in spec.header_patterns:
                if re.search(pattern, content, re.IGNORECASE | re.MULTILINE):
                    found_count += 1
                    break

        if found_count < expected_required:
            issues.append(ValidationIssue(
                level=ValidationLevel.WARNING,
                code="INSUFFICIENT_SECTIONS",
                message=f"Only {found_count} sections found, expected at least {expected_required}",
                suggestion="Ensure all required sections are present"
            ))

        return issues

    @classmethod
    def validate_structure(
        cls,
        content: str,
        domain: str
    ) -> Tuple[bool, List[ValidationIssue]]:
        """
        Run all structural validations.

        Args:
            content: Letter content to validate
            domain: "legal" or "civil"

        Returns:
            Tuple of (is_valid, issues)
        """
        all_issues = []

        # Run order validation
        if domain == "legal":
            all_issues.extend(cls.validate_legal_order(content))
            all_issues.extend(cls.validate_mov_position(content))
            all_issues.extend(cls.validate_case_law_position(content))
            all_issues.extend(cls.validate_metro2_position(content))
        else:
            all_issues.extend(cls.validate_civil_order(content))

        # Run required sections validation
        all_issues.extend(cls.validate_required_sections(content, domain))

        # Run cross-domain validation
        all_issues.extend(cls.validate_no_cross_domain_bleed(content, domain))

        # Run section count validation
        all_issues.extend(cls.validate_section_count(content, domain))

        # Check if any errors exist
        has_errors = any(issue.level == ValidationLevel.ERROR for issue in all_issues)

        return (not has_errors, all_issues)

    @classmethod
    def format_issues(cls, issues: List[ValidationIssue]) -> str:
        """Format structural validation issues as a readable string."""
        if not issues:
            return "No structural issues found."

        lines = []

        errors = [i for i in issues if i.level == ValidationLevel.ERROR]
        warnings = [i for i in issues if i.level == ValidationLevel.WARNING]

        if errors:
            lines.append("STRUCTURAL ERRORS:")
            for issue in errors:
                lines.append(f"  - [{issue.code}] {issue.message}")
                if issue.suggestion:
                    lines.append(f"    Fix: {issue.suggestion}")

        if warnings:
            lines.append("\nSTRUCTURAL WARNINGS:")
            for issue in warnings:
                lines.append(f"  - [{issue.code}] {issue.message}")
                if issue.suggestion:
                    lines.append(f"    Suggestion: {issue.suggestion}")

        return "\n".join(lines)
