"""
Metro 2 V2.0 Schema Kill-Switch Validators

Kill-switch pattern:
- Each validator can be enabled/disabled via ValidationMode
- Returns ValidationResult with error details
- COERCE mode (default) maps text values to valid Metro 2 codes
- STRICT mode rejects anything that isn't a valid Metro 2 code

Usage:
    validator = Metro2SchemaValidator(mode=ValidationMode.COERCE)
    result = validator.validate_account_status("84")
    if not result.is_valid:
        # Handle schema violation
        print(f"Error: {result.error_message}")
"""
import json
from pathlib import Path
from typing import Tuple, Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum


# Path to Metro 2 enums config
_ENUMS_PATH = Path(__file__).parent.parent.parent.parent / "configs" / "enums_metro2.json"


class ValidationMode(str, Enum):
    """Validation strictness levels (kill-switch modes)."""
    STRICT = "strict"      # Reject invalid values - no coercion
    COERCE = "coerce"      # Map text to valid codes (DEFAULT)
    WARN = "warn"          # Log warning but allow
    DISABLED = "disabled"  # Skip validation entirely


@dataclass
class ValidationResult:
    """Result of a schema validation check."""
    is_valid: bool
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    corrected_value: Optional[Any] = None
    original_value: Optional[Any] = None
    field_name: Optional[str] = None
    crrg_reference: Optional[str] = None  # For linking to CRRG anchors

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON serialization."""
        return {
            "is_valid": self.is_valid,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "corrected_value": self.corrected_value,
            "original_value": self.original_value,
            "field_name": self.field_name,
            "crrg_reference": self.crrg_reference,
        }


@dataclass
class SchemaViolation:
    """
    A schema violation for integration with the audit engine.

    Created when a Metro 2 field fails validation.
    """
    rule_id: str
    field: str
    bad_value: Any
    expected: str
    anchor_id: Optional[str] = None
    severity: str = "MEDIUM"
    description: Optional[str] = None


class Metro2SchemaValidator:
    """
    Kill-switch enabled Metro 2 schema validator.

    Validates Metro 2 field values against the official CRRG enums.
    Default mode is COERCE for gradual migration.

    Usage:
        validator = Metro2SchemaValidator(mode=ValidationMode.COERCE)
        result = validator.validate_account_status("84")

        # Or validate multiple fields at once
        violations = validator.validate_account(account_data)
    """

    # Text-to-code coercion mappings
    ACCOUNT_STATUS_COERCE_MAP = {
        # Current/Open statuses
        "current": "11",
        "open": "11",
        "active": "11",

        # Paid/Closed statuses
        "paid": "13",
        "paid in full": "13",
        "closed": "13",
        "closed paid": "13",
        "zero balance": "13",

        # Delinquent statuses
        "30": "71",
        "30 days": "71",
        "30 days late": "71",
        "30-59": "71",
        "60": "78",
        "60 days": "78",
        "60 days late": "78",
        "60-89": "78",
        "90": "79",
        "90 days": "79",
        "90 days late": "79",
        "90-119": "79",
        "120": "80",
        "120 days": "80",
        "120-149": "80",
        "150": "82",
        "150 days": "82",
        "150-179": "82",
        "180": "83",
        "180 days": "83",
        "180+": "83",

        # Chargeoff
        "charge off": "84",
        "chargeoff": "84",
        "charged off": "84",
        "charge-off": "84",
        "co": "84",
        "loss": "97",

        # Collection
        "collection": "93",
        "collections": "93",
        "in collection": "93",
        "assigned": "93",

        # Foreclosure/Repo
        "foreclosure": "94",
        "repo": "96",
        "repossession": "96",
        "repossessed": "96",
        "voluntary surrender": "95",
        "surrendered": "95",
    }

    PAYMENT_HISTORY_COERCE_MAP = {
        # Current
        "ok": "0",
        "current": "0",
        "c": "0",
        "*": "0",
        "-": "D",
        "": "D",
        "nd": "D",
        "no data": "D",

        # Delinquent
        "30": "1",
        "60": "2",
        "90": "3",
        "120": "4",
        "150": "5",
        "180": "6",
        "180+": "6",

        # Special statuses
        "co": "L",
        "chargeoff": "L",
        "collection": "G",
        "coll": "G",
        "foreclosure": "H",
        "repo": "K",
        "repossession": "K",
        "surrender": "J",
    }

    ECOA_COERCE_MAP = {
        "individual": "1",
        "joint": "2",
        "joint contractual": "2",
        "authorized user": "3",  # Will flag as obsolete
        "au": "3",  # Will flag as obsolete
        "cosigner": "5",
        "comaker": "5",
        "maker": "7",
        "terminated": "T",
        "deceased": "X",
        "delete": "Z",
    }

    def __init__(self, mode: ValidationMode = ValidationMode.COERCE):
        """
        Initialize the validator.

        Args:
            mode: Validation strictness (default: COERCE for gradual migration)
        """
        self.mode = mode
        self._enums: Dict = {}
        self._load_enums()

    def _load_enums(self) -> None:
        """Load Metro 2 enums from config file."""
        if _ENUMS_PATH.exists():
            try:
                with open(_ENUMS_PATH, 'r') as f:
                    data = json.load(f)
                    self._enums = data.get("enums", {})
            except (json.JSONDecodeError, IOError):
                self._enums = {}
        else:
            # Fallback to hardcoded critical enums if config not found
            self._enums = self._get_fallback_enums()

    def _get_fallback_enums(self) -> Dict:
        """Fallback enum definitions if config file is missing."""
        return {
            "account_status_17a": {
                "11": {}, "13": {}, "71": {}, "78": {}, "79": {},
                "80": {}, "82": {}, "83": {}, "84": {}, "93": {},
                "97": {}, "DA": {}
            },
            "payment_history_profile": {
                "0": {}, "1": {}, "2": {}, "3": {}, "4": {},
                "5": {}, "6": {}, "B": {}, "D": {}, "E": {},
                "G": {}, "H": {}, "J": {}, "K": {}, "L": {}
            },
            "ecoa_code": {
                "1": {}, "2": {}, "5": {}, "7": {},
                "T": {}, "W": {}, "X": {}, "Z": {}
            },
            "ecoa_obsolete": ["3", "4", "6"],
            "portfolio_type": {
                "C": {}, "I": {}, "M": {}, "O": {}, "R": {}
            },
        }

    # =========================================================================
    # ACCOUNT STATUS (FIELD 17A) VALIDATION
    # =========================================================================

    def validate_account_status(self, code: str) -> ValidationResult:
        """
        Validate Account Status (Field 17A) code.

        Args:
            code: The account status code or text to validate

        Returns:
            ValidationResult with validity and any corrections
        """
        if self.mode == ValidationMode.DISABLED:
            return ValidationResult(is_valid=True, field_name="17A")

        valid_codes = self._enums.get("account_status_17a", {})
        original_code = code

        # Normalize input
        code_normalized = str(code).strip().upper() if code else ""

        # Direct match check
        if code_normalized in valid_codes:
            return ValidationResult(
                is_valid=True,
                original_value=original_code,
                field_name="17A",
            )

        # Attempt coercion in COERCE mode
        if self.mode == ValidationMode.COERCE:
            coerced = self._coerce_account_status(code)
            if coerced:
                return ValidationResult(
                    is_valid=True,
                    corrected_value=coerced,
                    original_value=original_code,
                    field_name="17A",
                )

        # Validation failed
        error_result = ValidationResult(
            is_valid=False,
            error_code="INVALID_ACCOUNT_STATUS",
            error_message=f"Account Status '{original_code}' is not a valid Metro 2 code. Valid codes: 11, 13, 61-65, 71, 78-84, 88-89, 93-97, DA",
            original_value=original_code,
            field_name="17A",
            crrg_reference="FIELD_17A",
        )

        if self.mode == ValidationMode.WARN:
            error_result.is_valid = True  # Allow but flag

        return error_result

    def _coerce_account_status(self, text: str) -> Optional[str]:
        """Attempt to coerce text status to Metro 2 code."""
        if not text:
            return None
        text_lower = text.lower().strip()
        return self.ACCOUNT_STATUS_COERCE_MAP.get(text_lower)

    # =========================================================================
    # PAYMENT HISTORY PROFILE (K2 SEGMENT) VALIDATION
    # =========================================================================

    def validate_payment_history_code(self, code: str) -> ValidationResult:
        """
        Validate Payment History Profile code.

        Args:
            code: Single character payment history code

        Returns:
            ValidationResult with validity status
        """
        if self.mode == ValidationMode.DISABLED:
            return ValidationResult(is_valid=True, field_name="K2-25")

        valid_codes = self._enums.get("payment_history_profile", {})
        original_code = code

        # Normalize input
        code_normalized = str(code).strip().upper() if code else ""

        # Direct match check
        if code_normalized in valid_codes:
            return ValidationResult(
                is_valid=True,
                original_value=original_code,
                field_name="K2-25",
            )

        # Attempt coercion
        if self.mode == ValidationMode.COERCE:
            coerced = self._coerce_payment_history(code)
            if coerced:
                return ValidationResult(
                    is_valid=True,
                    corrected_value=coerced,
                    original_value=original_code,
                    field_name="K2-25",
                )

        error_result = ValidationResult(
            is_valid=False,
            error_code="INVALID_PAYMENT_HISTORY",
            error_message=f"Payment History code '{original_code}' is not valid Metro 2. Valid codes: 0-6, B, D, E, G, H, J, K, L",
            original_value=original_code,
            field_name="K2-25",
            crrg_reference="FIELD_25_K2",
        )

        if self.mode == ValidationMode.WARN:
            error_result.is_valid = True

        return error_result

    def _coerce_payment_history(self, text: str) -> Optional[str]:
        """Attempt to coerce text to payment history code."""
        if not text:
            return "D"  # No data
        text_lower = text.lower().strip()
        return self.PAYMENT_HISTORY_COERCE_MAP.get(text_lower)

    # =========================================================================
    # ECOA CODE (FIELD 4) VALIDATION
    # =========================================================================

    def validate_ecoa_code(self, code: str) -> ValidationResult:
        """
        Validate ECOA Code (Field 4) with obsolete code detection.

        Args:
            code: ECOA code to validate

        Returns:
            ValidationResult - invalid if obsolete (3, 4, 6)
        """
        if self.mode == ValidationMode.DISABLED:
            return ValidationResult(is_valid=True, field_name="4")

        valid_codes = self._enums.get("ecoa_code", {})
        obsolete_codes = self._enums.get("ecoa_obsolete", ["3", "4", "6"])
        original_code = code

        # Normalize
        code_normalized = str(code).strip().upper() if code else ""

        # Check for obsolete codes first (this is a violation even if technically valid)
        if code_normalized in obsolete_codes:
            return ValidationResult(
                is_valid=False,
                error_code="OBSOLETE_ECOA_CODE",
                error_message=f"ECOA Code '{original_code}' is obsolete per CRRG. Codes 3, 4, 6 are no longer valid.",
                original_value=original_code,
                field_name="4",
                crrg_reference="FIELD_4",
            )

        # Check if valid
        if code_normalized in valid_codes:
            return ValidationResult(
                is_valid=True,
                original_value=original_code,
                field_name="4",
            )

        # Attempt coercion
        if self.mode == ValidationMode.COERCE:
            coerced = self._coerce_ecoa_code(code)
            if coerced:
                # Check if coerced value is obsolete
                if coerced in obsolete_codes:
                    return ValidationResult(
                        is_valid=False,
                        error_code="OBSOLETE_ECOA_CODE",
                        error_message=f"ECOA Code '{original_code}' maps to obsolete code {coerced}",
                        original_value=original_code,
                        corrected_value=coerced,
                        field_name="4",
                        crrg_reference="FIELD_4",
                    )
                return ValidationResult(
                    is_valid=True,
                    corrected_value=coerced,
                    original_value=original_code,
                    field_name="4",
                )

        error_result = ValidationResult(
            is_valid=False,
            error_code="INVALID_ECOA_CODE",
            error_message=f"ECOA Code '{original_code}' is not valid. Valid codes: 1, 2, 5, 7, T, W, X, Z",
            original_value=original_code,
            field_name="4",
            crrg_reference="FIELD_4",
        )

        if self.mode == ValidationMode.WARN:
            error_result.is_valid = True

        return error_result

    def _coerce_ecoa_code(self, text: str) -> Optional[str]:
        """Attempt to coerce text to ECOA code."""
        if not text:
            return None
        text_lower = text.lower().strip()
        return self.ECOA_COERCE_MAP.get(text_lower)

    # =========================================================================
    # PORTFOLIO TYPE (FIELD 10) VALIDATION
    # =========================================================================

    def validate_portfolio_type(self, code: str) -> ValidationResult:
        """
        Validate Portfolio Type (Field 10) code.

        Args:
            code: Portfolio type code (C, I, M, O, R)

        Returns:
            ValidationResult with validity status
        """
        if self.mode == ValidationMode.DISABLED:
            return ValidationResult(is_valid=True, field_name="10")

        valid_codes = self._enums.get("portfolio_type", {})
        original_code = code

        # Normalize
        code_normalized = str(code).strip().upper() if code else ""

        if code_normalized in valid_codes:
            return ValidationResult(
                is_valid=True,
                original_value=original_code,
                field_name="10",
            )

        # Attempt text coercion
        if self.mode == ValidationMode.COERCE:
            coerce_map = {
                "installment": "I",
                "revolving": "R",
                "mortgage": "M",
                "open": "O",
                "line of credit": "C",
                "credit line": "C",
            }
            text_lower = str(code).lower().strip() if code else ""
            if text_lower in coerce_map:
                return ValidationResult(
                    is_valid=True,
                    corrected_value=coerce_map[text_lower],
                    original_value=original_code,
                    field_name="10",
                )

        error_result = ValidationResult(
            is_valid=False,
            error_code="INVALID_PORTFOLIO_TYPE",
            error_message=f"Portfolio Type '{original_code}' is not valid. Valid codes: C, I, M, O, R",
            original_value=original_code,
            field_name="10",
            crrg_reference="FIELD_10",
        )

        if self.mode == ValidationMode.WARN:
            error_result.is_valid = True

        return error_result

    # =========================================================================
    # ACCOUNT TYPE VALIDATION
    # =========================================================================

    def validate_account_type(self, code: str) -> ValidationResult:
        """
        Validate Account Type (Field 9) code.

        Args:
            code: Account type code (00, 01, 02, etc.)

        Returns:
            ValidationResult with validity status
        """
        if self.mode == ValidationMode.DISABLED:
            return ValidationResult(is_valid=True, field_name="9")

        valid_codes = self._enums.get("account_type", {})
        original_code = code

        # Normalize
        code_normalized = str(code).strip().upper() if code else ""

        if code_normalized in valid_codes:
            return ValidationResult(
                is_valid=True,
                original_value=original_code,
                field_name="9",
            )

        error_result = ValidationResult(
            is_valid=False,
            error_code="INVALID_ACCOUNT_TYPE",
            error_message=f"Account Type '{original_code}' is not a valid Metro 2 code",
            original_value=original_code,
            field_name="9",
            crrg_reference="FIELD_9",
        )

        if self.mode == ValidationMode.WARN:
            error_result.is_valid = True

        return error_result

    # =========================================================================
    # COMPLIANCE CONDITION CODE VALIDATION
    # =========================================================================

    def validate_compliance_condition_code(self, code: str) -> ValidationResult:
        """
        Validate Compliance Condition Code (Field 38).

        Args:
            code: Compliance condition code (XB, XC, XD, XF, XH, XR)

        Returns:
            ValidationResult with validity status
        """
        if self.mode == ValidationMode.DISABLED:
            return ValidationResult(is_valid=True, field_name="38")

        valid_codes = self._enums.get("compliance_condition_code", {})
        original_code = code

        # Normalize
        code_normalized = str(code).strip().upper() if code else ""

        if code_normalized in valid_codes or code_normalized == "":
            return ValidationResult(
                is_valid=True,
                original_value=original_code,
                field_name="38",
            )

        error_result = ValidationResult(
            is_valid=False,
            error_code="INVALID_COMPLIANCE_CODE",
            error_message=f"Compliance Condition Code '{original_code}' is not valid. Valid codes: XB, XC, XD, XF, XH, XR",
            original_value=original_code,
            field_name="38",
            crrg_reference="FIELD_38",
        )

        if self.mode == ValidationMode.WARN:
            error_result.is_valid = True

        return error_result

    # =========================================================================
    # BATCH VALIDATION
    # =========================================================================

    def validate_account(self, account_data: Dict[str, Any]) -> List[SchemaViolation]:
        """
        Validate all Metro 2 fields on an account.

        Args:
            account_data: Dict containing account fields

        Returns:
            List of SchemaViolation objects for any failed validations
        """
        violations = []

        # Account Status (17A)
        status = account_data.get("account_status_raw") or account_data.get("status")
        if status:
            result = self.validate_account_status(status)
            if not result.is_valid:
                violations.append(SchemaViolation(
                    rule_id=result.error_code or "INVALID_ACCOUNT_STATUS",
                    field="17A",
                    bad_value=result.original_value,
                    expected="Valid Metro 2 Account Status code",
                    anchor_id=result.crrg_reference,
                    description=result.error_message,
                ))

        # ECOA Code (Field 4)
        ecoa = account_data.get("ecoa_code") or account_data.get("bureau_code")
        if ecoa:
            result = self.validate_ecoa_code(ecoa)
            if not result.is_valid:
                severity = "HIGH" if result.error_code == "OBSOLETE_ECOA_CODE" else "MEDIUM"
                violations.append(SchemaViolation(
                    rule_id=result.error_code or "INVALID_ECOA_CODE",
                    field="4",
                    bad_value=result.original_value,
                    expected="Valid ECOA code (1, 2, 5, 7, T, W, X, Z)",
                    anchor_id=result.crrg_reference,
                    severity=severity,
                    description=result.error_message,
                ))

        # Portfolio Type (Field 10)
        portfolio = account_data.get("portfolio_type")
        if portfolio:
            result = self.validate_portfolio_type(portfolio)
            if not result.is_valid:
                violations.append(SchemaViolation(
                    rule_id=result.error_code or "INVALID_PORTFOLIO_TYPE",
                    field="10",
                    bad_value=result.original_value,
                    expected="C, I, M, O, or R",
                    anchor_id=result.crrg_reference,
                    description=result.error_message,
                ))

        # Account Type (Field 9)
        account_type = account_data.get("account_type_code") or account_data.get("account_type")
        if account_type:
            result = self.validate_account_type(account_type)
            if not result.is_valid:
                violations.append(SchemaViolation(
                    rule_id=result.error_code or "INVALID_ACCOUNT_TYPE",
                    field="9",
                    bad_value=result.original_value,
                    expected="Valid Metro 2 Account Type code",
                    anchor_id=result.crrg_reference,
                    description=result.error_message,
                ))

        return violations

    def validate_payment_history(
        self,
        payment_history: List[Dict[str, Any]]
    ) -> List[SchemaViolation]:
        """
        Validate all payment history codes.

        Args:
            payment_history: List of {"month": str, "year": int, "status": str}

        Returns:
            List of SchemaViolation objects
        """
        violations = []

        for entry in payment_history:
            code = entry.get("status")
            if code:
                result = self.validate_payment_history_code(code)
                if not result.is_valid:
                    month = entry.get("month", "?")
                    year = entry.get("year", "?")
                    violations.append(SchemaViolation(
                        rule_id=result.error_code or "INVALID_PAYMENT_HISTORY",
                        field=f"K2-25 ({month}/{year})",
                        bad_value=result.original_value,
                        expected="Valid payment history code (0-6, B, D, E, G, H, J, K, L)",
                        anchor_id=result.crrg_reference,
                        description=f"{result.error_message} for {month}/{year}",
                    ))

        return violations

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def get_status_metadata(self, code: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for an account status code.

        Args:
            code: Account status code

        Returns:
            Dict with label, category, negative flag, requires_dofd
        """
        statuses = self._enums.get("account_status_17a", {})
        return statuses.get(str(code).upper())

    def requires_dofd(self, status_code: str) -> bool:
        """
        Check if a status code requires DOFD.

        Args:
            status_code: Account status code

        Returns:
            True if DOFD is required for this status
        """
        metadata = self.get_status_metadata(status_code)
        if metadata:
            return metadata.get("requires_dofd", False)
        return False

    def is_negative_status(self, status_code: str) -> bool:
        """
        Check if a status code is considered negative/derogatory.

        Args:
            status_code: Account status code

        Returns:
            True if this is a negative status
        """
        metadata = self.get_status_metadata(status_code)
        if metadata:
            return metadata.get("negative", False)
        return False

    def is_collector_account_type(self, account_type_code: str) -> bool:
        """
        Check if account type indicates a collection agency.

        Args:
            account_type_code: Account type code

        Returns:
            True if this is a collector account type (43, 47, 95)
        """
        validation_rules = {}
        if _ENUMS_PATH.exists():
            try:
                with open(_ENUMS_PATH, 'r') as f:
                    data = json.load(f)
                    validation_rules = data.get("validation_rules", {})
            except (json.JSONDecodeError, IOError):
                pass

        collector_types = validation_rules.get("collector_account_types", ["43", "47", "95"])
        return str(account_type_code).upper() in collector_types

    def is_debt_buyer_account_type(self, account_type_code: str) -> bool:
        """
        Check if account type indicates a debt buyer.

        Args:
            account_type_code: Account type code

        Returns:
            True if this is a debt buyer account type (43)
        """
        validation_rules = {}
        if _ENUMS_PATH.exists():
            try:
                with open(_ENUMS_PATH, 'r') as f:
                    data = json.load(f)
                    validation_rules = data.get("validation_rules", {})
            except (json.JSONDecodeError, IOError):
                pass

        debt_buyer_types = validation_rules.get("debt_buyer_account_types", ["43"])
        return str(account_type_code).upper() in debt_buyer_types
