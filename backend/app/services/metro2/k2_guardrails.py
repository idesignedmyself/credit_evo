"""
K2 Guardrails

Validates Metro 2 K2 segment (Payment History Profile) compliance per CRRG 2024-2025.
The K2 segment contains 24 months of payment history using standardized codes.

Key Rules:
- K2_PROHIBITED_REPORTER_HAS_K2: Collection agencies (47) and summary accounts (95) should NOT have K2
- DEBT_BUYER_CHAIN_GAP_K2_REQUIRED: Debt buyers (43) with chain gaps need K2 for transparency
- Payment history codes must be valid Metro 2 values
- Payment history length cannot exceed account age
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class K2ValidationLevel(Enum):
    """Validation result levels."""
    VALID = "valid"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class K2Violation:
    """Represents a K2-related violation."""
    rule_code: str
    severity: str
    description: str
    invalid_codes: List[str] = field(default_factory=list)
    position_issues: List[int] = field(default_factory=list)
    evidence: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "rule_code": self.rule_code,
            "severity": self.severity,
            "description": self.description,
            "invalid_codes": self.invalid_codes,
            "position_issues": self.position_issues,
            "evidence": self.evidence,
        }


@dataclass
class K2ValidationResult:
    """Result of K2 validation."""
    level: K2ValidationLevel
    violations: List[K2Violation] = field(default_factory=list)
    valid_codes: List[str] = field(default_factory=list)
    invalid_codes: List[str] = field(default_factory=list)
    payment_history_length: int = 0
    expected_max_length: int = 24

    @property
    def is_valid(self) -> bool:
        """Check if validation passed without errors."""
        return self.level in (K2ValidationLevel.VALID, K2ValidationLevel.WARNING)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "level": self.level.value,
            "is_valid": self.is_valid,
            "violations": [v.to_dict() for v in self.violations],
            "valid_codes_count": len(self.valid_codes),
            "invalid_codes": self.invalid_codes,
            "payment_history_length": self.payment_history_length,
            "expected_max_length": self.expected_max_length,
        }


class K2Guardrails:
    """
    Validates K2 segment (Payment History Profile) compliance.

    The K2 segment contains 24 positions representing the last 24 months of payment history.
    Each position uses a standardized code indicating payment status for that month.
    """

    # Valid payment history codes per Metro 2 CRRG
    VALID_CODES: Set[str] = {
        "0",  # Current (0 days past due)
        "1",  # 30-59 days past due
        "2",  # 60-89 days past due
        "3",  # 90-119 days past due
        "4",  # 120-149 days past due
        "5",  # 150-179 days past due
        "6",  # 180+ days past due
        "B",  # No payment history prior to this month
        "D",  # No payment history required this month
        "E",  # Zero balance/current
        "G",  # Collection
        "H",  # Foreclosure completed
        "J",  # Voluntary surrender
        "K",  # Repossession
        "L",  # Charge-off
    }

    # Codes indicating delinquency
    DELINQUENT_CODES: Set[str] = {"1", "2", "3", "4", "5", "6", "G", "H", "J", "K", "L"}

    # Account types that should NOT have K2 segment
    K2_PROHIBITED_ACCOUNT_TYPES: Set[str] = {
        "47",  # Collection Agency/Attorney
        "95",  # Summary of Accounts (Collection)
    }

    # Debt buyer account type
    DEBT_BUYER_ACCOUNT_TYPE: str = "43"

    # Maximum payment history length
    MAX_PAYMENT_HISTORY_LENGTH: int = 24

    def __init__(self):
        """Initialize K2 guardrails."""
        pass

    def _parse_payment_history(self, payment_history: Any) -> List[str]:
        """
        Parse payment history from various formats.

        Args:
            payment_history: Payment history as string or list

        Returns:
            List of individual payment codes
        """
        if payment_history is None:
            return []

        if isinstance(payment_history, list):
            return [str(code) for code in payment_history]

        if isinstance(payment_history, str):
            # Handle 24-character string format
            return list(payment_history.strip())

        return []

    def _calculate_max_history_months(
        self,
        date_opened: Optional[date],
        report_date: Optional[date] = None,
    ) -> int:
        """
        Calculate maximum allowed payment history months based on account age.

        Args:
            date_opened: Account open date
            report_date: Report date (defaults to today)

        Returns:
            Maximum number of months of payment history allowed
        """
        if date_opened is None:
            return self.MAX_PAYMENT_HISTORY_LENGTH

        effective_report_date = report_date or date.today()

        # Calculate months between dates
        delta = relativedelta(effective_report_date, date_opened)
        months = delta.years * 12 + delta.months

        # Cap at 24 months
        return min(months, self.MAX_PAYMENT_HISTORY_LENGTH)

    def validate(
        self,
        payment_history: Any,
        date_opened: Optional[date] = None,
        report_date: Optional[date] = None,
        account_type: Optional[str] = None,
        has_chain_gap: bool = False,
    ) -> K2ValidationResult:
        """
        Validate K2 payment history segment.

        Args:
            payment_history: Payment history string or list
            date_opened: Account open date
            report_date: Report date for validation
            account_type: Metro 2 account type code
            has_chain_gap: Whether there's a chain-of-title gap (for debt buyers)

        Returns:
            K2ValidationResult with validation details
        """
        violations = []
        parsed_history = self._parse_payment_history(payment_history)
        history_length = len(parsed_history)

        # Determine if K2 is present
        has_k2 = history_length > 0

        # Check if prohibited reporter has K2
        if account_type in self.K2_PROHIBITED_ACCOUNT_TYPES and has_k2:
            violations.append(K2Violation(
                rule_code="K2_PROHIBITED_REPORTER_HAS_K2",
                severity="MEDIUM",
                description=f"Account type {account_type} should not have K2 payment history segment. "
                            f"Collection agencies and summary accounts do not report payment history.",
                evidence={
                    "account_type": account_type,
                    "has_k2": True,
                    "payment_history_length": history_length,
                }
            ))

        # Check if debt buyer with chain gap needs K2
        if account_type == self.DEBT_BUYER_ACCOUNT_TYPE and has_chain_gap and not has_k2:
            violations.append(K2Violation(
                rule_code="DEBT_BUYER_CHAIN_GAP_K2_REQUIRED",
                severity="MEDIUM",
                description="Debt buyer with chain-of-title gap should include K2 segment "
                            "to document payment history continuity.",
                evidence={
                    "account_type": account_type,
                    "has_chain_gap": True,
                    "has_k2": False,
                }
            ))

        # Validate individual codes
        valid_codes = []
        invalid_codes = []
        position_issues = []

        for i, code in enumerate(parsed_history):
            if code in self.VALID_CODES:
                valid_codes.append(code)
            else:
                invalid_codes.append(code)
                position_issues.append(i)

        if invalid_codes:
            violations.append(K2Violation(
                rule_code="INVALID_PAYMENT_HISTORY",
                severity="HIGH",
                description=f"Invalid payment history codes found: {', '.join(set(invalid_codes))}. "
                            f"Valid codes are: 0-6, B, D, E, G, H, J, K, L.",
                invalid_codes=invalid_codes,
                position_issues=position_issues,
                evidence={
                    "invalid_count": len(invalid_codes),
                    "positions": position_issues,
                }
            ))

        # Check if payment history exceeds account age
        max_months = self._calculate_max_history_months(date_opened, report_date)
        if history_length > max_months:
            violations.append(K2Violation(
                rule_code="PAYMENT_HISTORY_EXCEEDS_ACCOUNT_AGE",
                severity="CRITICAL",
                description=f"Payment history has {history_length} months but account is only "
                            f"{max_months} months old. Payment history cannot exceed account age.",
                evidence={
                    "payment_history_length": history_length,
                    "account_age_months": max_months,
                    "date_opened": date_opened.isoformat() if date_opened else None,
                    "excess_months": history_length - max_months,
                }
            ))

        # Check for delinquency ladder inversion (e.g., 4-3-2-6 pattern)
        ladder_violations = self._check_delinquency_ladder(parsed_history)
        violations.extend(ladder_violations)

        # Determine overall validation level
        if any(v.severity == "CRITICAL" for v in violations):
            level = K2ValidationLevel.CRITICAL
        elif any(v.severity == "HIGH" for v in violations):
            level = K2ValidationLevel.ERROR
        elif any(v.severity == "MEDIUM" for v in violations):
            level = K2ValidationLevel.WARNING
        else:
            level = K2ValidationLevel.VALID

        return K2ValidationResult(
            level=level,
            violations=violations,
            valid_codes=valid_codes,
            invalid_codes=invalid_codes,
            payment_history_length=history_length,
            expected_max_length=max_months,
        )

    def _check_delinquency_ladder(self, payment_history: List[str]) -> List[K2Violation]:
        """
        Check for delinquency ladder inversions in payment history.

        A ladder inversion occurs when delinquency levels decrease then jump
        without returning to current (0), which is temporally impossible.

        Example violation: "4-3-2-6" - Cannot go from 2 to 6 without 3,4,5

        Args:
            payment_history: Parsed payment history codes

        Returns:
            List of ladder inversion violations
        """
        violations = []

        # Only check numeric delinquency codes
        numeric_codes = {"0", "1", "2", "3", "4", "5", "6"}

        # Track state for ladder analysis
        prev_level: Optional[int] = None
        ladder_violations_found = []

        for i, code in enumerate(payment_history):
            if code not in numeric_codes:
                # Non-numeric code resets ladder tracking
                prev_level = None
                continue

            current_level = int(code)

            if prev_level is not None:
                # Check for impossible jumps
                # Going from lower to higher by more than 1 is suspicious
                # but going from higher to 0 (cure) is valid
                if current_level > prev_level + 1 and prev_level > 0:
                    # Jumped multiple delinquency levels - possible data error
                    ladder_violations_found.append({
                        "position": i,
                        "prev_code": str(prev_level),
                        "current_code": code,
                        "jump": current_level - prev_level,
                    })

            prev_level = current_level

        if ladder_violations_found:
            violations.append(K2Violation(
                rule_code="DELINQUENCY_LADDER_INVERSION",
                severity="HIGH",
                description="Payment history shows impossible delinquency progression. "
                            "Delinquency cannot skip levels without returning to current first.",
                position_issues=[v["position"] for v in ladder_violations_found],
                evidence={
                    "inversions": ladder_violations_found,
                    "pattern": "".join(payment_history[:12]) + "...",
                }
            ))

        return violations

    def extract_delinquency_pattern(self, payment_history: Any) -> Dict[str, Any]:
        """
        Extract delinquency statistics from payment history.

        Args:
            payment_history: Payment history string or list

        Returns:
            Dictionary with delinquency analysis
        """
        parsed = self._parse_payment_history(payment_history)

        if not parsed:
            return {
                "has_payment_history": False,
                "months_count": 0,
            }

        # Count delinquencies by level
        delinquency_counts = {}
        for code in self.DELINQUENT_CODES:
            count = parsed.count(code)
            if count > 0:
                delinquency_counts[code] = count

        # Find first delinquency (most recent is position 0)
        first_delinquent_pos = None
        for i, code in enumerate(parsed):
            if code in self.DELINQUENT_CODES:
                if first_delinquent_pos is None:
                    first_delinquent_pos = i

        # Find worst delinquency level
        worst_level = "0"
        for code in parsed:
            if code in {"1", "2", "3", "4", "5", "6"}:
                if code > worst_level:
                    worst_level = code
            elif code in {"G", "H", "J", "K", "L"}:
                worst_level = code
                break  # Terminal status

        return {
            "has_payment_history": True,
            "months_count": len(parsed),
            "delinquency_counts": delinquency_counts,
            "total_delinquent_months": sum(delinquency_counts.values()),
            "first_delinquent_position": first_delinquent_pos,
            "worst_delinquency": worst_level,
            "current_months": parsed.count("0") + parsed.count("E"),
            "pattern_summary": "".join(parsed[:6]) if len(parsed) >= 6 else "".join(parsed),
        }

    def infer_dofd_from_k2(
        self,
        payment_history: Any,
        report_date: Optional[date] = None,
    ) -> Optional[date]:
        """
        Infer DOFD from payment history by finding first delinquency.

        Args:
            payment_history: Payment history string or list
            report_date: Report date (defaults to today)

        Returns:
            Inferred DOFD date or None if no delinquency found
        """
        parsed = self._parse_payment_history(payment_history)
        effective_date = report_date or date.today()

        if not parsed:
            return None

        # Find first delinquency position (most recent = position 0)
        # We need to find the FIRST occurrence when scanning from oldest to newest
        first_delinquent_pos = None
        for i in range(len(parsed) - 1, -1, -1):  # Scan from oldest to newest
            if parsed[i] in self.DELINQUENT_CODES:
                first_delinquent_pos = i
                break

        if first_delinquent_pos is None:
            return None

        # Calculate date: position 0 = current month, position 1 = last month, etc.
        months_ago = first_delinquent_pos
        inferred_dofd = effective_date - relativedelta(months=months_ago)

        # Return first day of that month
        return date(inferred_dofd.year, inferred_dofd.month, 1)


def validate_k2(
    payment_history: Any,
    date_opened: Optional[date] = None,
    account_type: Optional[str] = None,
) -> K2ValidationResult:
    """
    Convenience function to validate K2 payment history.

    Args:
        payment_history: Payment history string or list
        date_opened: Account open date
        account_type: Metro 2 account type code

    Returns:
        K2ValidationResult with validation details
    """
    guardrails = K2Guardrails()
    return guardrails.validate(
        payment_history=payment_history,
        date_opened=date_opened,
        account_type=account_type,
    )
