"""
Tier 2 Examiner Standard Check

Evaluates entity responses against supervisory examination standards.
Creates response-layer violations when entities fail to meet minimum
investigative quality thresholds.

AUTHORITY: SYSTEM
All examiner checks execute automatically without user confirmation.
Results feed into escalation decisions and letter posture selection.

Tier 2 Scope (Strictly Enforced):
- No cross-user aggregation
- No time-window analytics
- No probability modeling
- All logic is deterministic
- Within same dispute cycle only
"""
from datetime import date
from typing import Dict, List, Optional, Any
from uuid import uuid4
from dataclasses import dataclass, field
from enum import Enum

from sqlalchemy.orm import Session

from ...models.ssot import ViolationType, Severity
from ...models.db_models import (
    DisputeDB, DisputeResponseDB, ExecutionEventDB,
    ResponseType, EntityType
)


# =============================================================================
# LOGICAL IMPOSSIBILITY RULE CODES
# =============================================================================
# These are rule codes from the contradiction engine that indicate
# provable mathematical/temporal impossibilities (not just data errors)
LOGICAL_IMPOSSIBILITY_RULES = frozenset({
    "T1",  # Open Date vs DOFD - DOFD before account opened
    "T2",  # Payment history exceeds account age
    "T3",  # Chargeoff before last payment
    "T4",  # Delinquency ladder inversion
    "M1",  # Balance exceeds legal maximum
    "M2",  # Balance increases after chargeoff
})


# =============================================================================
# EXAMINER STANDARD RESULT
# =============================================================================

class ExaminerStandardResult(str, Enum):
    """Result of examiner standard check."""
    PASS = "PASS"
    FAIL_PERFUNCTORY = "FAIL_PERFUNCTORY"
    FAIL_NO_RESULTS = "FAIL_NO_RESULTS"
    FAIL_SYSTEMIC = "FAIL_SYSTEMIC"
    FAIL_MISLEADING = "FAIL_MISLEADING"


# =============================================================================
# EXAMINER CHECK RESULT
# =============================================================================

@dataclass
class ExaminerCheckResult:
    """Result of an examiner standard check."""
    passed: bool
    standard_result: ExaminerStandardResult
    failure_reason: Optional[str] = None
    response_layer_violation: Optional[Dict[str, Any]] = None
    severity_promotion: Optional[Severity] = None
    escalation_eligible: bool = False
    evidence: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# EXAMINER CHECK SERVICE
# =============================================================================

class ExaminerCheckService:
    """
    Examiner-like quality check for entity responses.

    Implements CFPB examiner standards for evaluating whether
    bureau/furnisher responses meet minimum investigative quality.

    Core Logic (Tier 2 Only):
    1. PERFUNCTORY_INVESTIGATION:
       IF VERIFIED + contradiction_detected + evidence_sent → FAIL
    2. NOTICE_OF_RESULTS_FAILURE:
       IF NO_RESPONSE + deadline_passed → FAIL
    3. SYSTEMIC_ACCURACY_FAILURE:
       IF same contradiction on same tradeline across ≥2 bureaus in same cycle → FAIL
    4. UDAAP_MISLEADING_VERIFICATION:
       IF VERIFIED + CRITICAL severity + is_logical_impossibility + evidence_sent → FAIL

    Constraints:
    - No cross-user aggregation
    - No time-window analytics
    - All logic deterministic
    - Within same dispute cycle only
    """

    def __init__(self, db_session: Session):
        self.db = db_session

    def check_response(
        self,
        dispute: DisputeDB,
        response: DisputeResponseDB,
        original_contradictions: Optional[List[Dict[str, Any]]] = None,
        cross_bureau_contradictions: Optional[List[Dict[str, Any]]] = None,
    ) -> ExaminerCheckResult:
        """
        Run examiner standard check on an entity response.

        Args:
            dispute: The dispute record
            response: The entity response
            original_contradictions: Contradictions from the original dispute
            cross_bureau_contradictions: Same tradeline contradictions across bureaus

        Returns:
            ExaminerCheckResult with pass/fail status and any violations
        """
        # Default to empty lists if None
        original_contradictions = original_contradictions or []
        cross_bureau_contradictions = cross_bureau_contradictions or []

        # Check 1: PERFUNCTORY_INVESTIGATION (VERIFIED responses only)
        if response.response_type == ResponseType.VERIFIED:
            result = self._check_perfunctory_investigation(
                dispute, response, original_contradictions
            )
            if not result.passed:
                return result

        # Check 2: NOTICE_OF_RESULTS_FAILURE (NO_RESPONSE only)
        if response.response_type == ResponseType.NO_RESPONSE:
            result = self._check_notice_of_results_failure(dispute, response)
            if not result.passed:
                return result

        # Check 3: SYSTEMIC_ACCURACY_FAILURE (cross-bureau pattern in same cycle)
        if response.response_type == ResponseType.VERIFIED:
            result = self._check_systemic_failure(
                dispute, response, cross_bureau_contradictions
            )
            if result and not result.passed:
                return result

        # Check 4: UDAAP_MISLEADING_VERIFICATION (VERIFIED on CRITICAL impossibilities)
        if response.response_type == ResponseType.VERIFIED:
            result = self._check_misleading_verification(
                dispute, response, original_contradictions
            )
            if not result.passed:
                return result

        # All checks passed
        return ExaminerCheckResult(
            passed=True,
            standard_result=ExaminerStandardResult.PASS,
            evidence={"checks_performed": ["perfunctory", "notice_of_results", "systemic", "misleading"]}
        )

    # =========================================================================
    # CHECK 1: PERFUNCTORY INVESTIGATION
    # =========================================================================

    def _check_perfunctory_investigation(
        self,
        dispute: DisputeDB,
        response: DisputeResponseDB,
        original_contradictions: List[Dict[str, Any]],
    ) -> ExaminerCheckResult:
        """
        Check for perfunctory investigation.

        Triggers when:
        - Response is VERIFIED
        - Original dispute contained contradictions (Tier 1 violations)
        - Evidence was sent with original dispute

        This check evaluates whether the entity conducted a reasonable
        investigation before verifying disputed information.
        """
        # Must have original contradictions
        if not original_contradictions or len(original_contradictions) == 0:
            return ExaminerCheckResult(
                passed=True,
                standard_result=ExaminerStandardResult.PASS
            )

        # Check if evidence was sent
        evidence_sent = self._check_evidence_sent(dispute)

        if evidence_sent and len(original_contradictions) > 0:
            # FAIL: Perfunctory investigation
            severity = self._calculate_severity_promotion(original_contradictions)

            return ExaminerCheckResult(
                passed=False,
                standard_result=ExaminerStandardResult.FAIL_PERFUNCTORY,
                failure_reason=(
                    f"Entity verified disputed information despite {len(original_contradictions)} "
                    f"provable factual impossibilities. Evidence was provided with dispute. "
                    f"No reasonable investigation could have verified mathematically impossible data."
                ),
                response_layer_violation={
                    "id": str(uuid4()),
                    "type": ViolationType.PERFUNCTORY_INVESTIGATION.value,
                    "statute": "15 U.S.C. § 1681i(a)(1)(A)",
                    "severity": severity.value,
                    "description": "Perfunctory investigation - verified despite provable impossibilities",
                    "contradiction_count": len(original_contradictions),
                    "evidence_sent": evidence_sent,
                    "authority": "SYSTEM",
                },
                severity_promotion=severity,
                escalation_eligible=True,
                evidence={
                    "original_contradictions": len(original_contradictions),
                    "evidence_sent": evidence_sent,
                }
            )

        return ExaminerCheckResult(
            passed=True,
            standard_result=ExaminerStandardResult.PASS
        )

    # =========================================================================
    # CHECK 2: NOTICE OF RESULTS FAILURE
    # =========================================================================

    def _check_notice_of_results_failure(
        self,
        dispute: DisputeDB,
        response: DisputeResponseDB,
    ) -> ExaminerCheckResult:
        """
        Check for notice of results failure.

        Triggers when:
        - Response is NO_RESPONSE
        - Statutory deadline has passed

        This is a strict liability check - if the deadline passed
        and no response was received, the entity failed.
        """
        today = date.today()

        if dispute.deadline_date and today > dispute.deadline_date:
            days_overdue = (today - dispute.deadline_date).days

            return ExaminerCheckResult(
                passed=False,
                standard_result=ExaminerStandardResult.FAIL_NO_RESULTS,
                failure_reason=(
                    f"Entity failed to provide notice of investigation results within "
                    f"statutory deadline. {days_overdue} days past deadline."
                ),
                response_layer_violation={
                    "id": str(uuid4()),
                    "type": ViolationType.NOTICE_OF_RESULTS_FAILURE.value,
                    "statute": "15 U.S.C. § 1681i(a)(6)(A)",
                    "severity": Severity.HIGH.value,
                    "description": f"Failed to provide investigation results. {days_overdue} days overdue.",
                    "days_overdue": days_overdue,
                    "deadline_date": dispute.deadline_date.isoformat() if dispute.deadline_date else None,
                    "authority": "SYSTEM",
                },
                severity_promotion=Severity.HIGH,
                escalation_eligible=True,
                evidence={
                    "deadline_date": dispute.deadline_date.isoformat() if dispute.deadline_date else None,
                    "days_overdue": days_overdue,
                }
            )

        return ExaminerCheckResult(
            passed=True,
            standard_result=ExaminerStandardResult.PASS
        )

    # =========================================================================
    # CHECK 3: SYSTEMIC ACCURACY FAILURE
    # =========================================================================

    def _check_systemic_failure(
        self,
        dispute: DisputeDB,
        response: DisputeResponseDB,
        cross_bureau_contradictions: List[Dict[str, Any]],
    ) -> Optional[ExaminerCheckResult]:
        """
        Check for systemic accuracy failure.

        Triggers when:
        - Same contradiction exists on same tradeline
        - Appears across ≥2 bureaus
        - Within the same dispute cycle

        This is NOT a time-window check. It only looks at the current
        dispute cycle's cross-bureau data that was already detected
        during the audit phase.

        No cross-user aggregation. No time-series analysis.
        """
        if not cross_bureau_contradictions:
            return None

        # Group by account fingerprint and contradiction type
        # to find same contradiction across multiple bureaus
        contradiction_bureau_map: Dict[str, set] = {}

        for contradiction in cross_bureau_contradictions:
            # Create a key for this specific contradiction type on this tradeline
            account_id = contradiction.get("account_id", "unknown")
            rule_code = contradiction.get("rule_code", "unknown")
            key = f"{account_id}:{rule_code}"

            bureau = contradiction.get("bureau", "unknown")

            if key not in contradiction_bureau_map:
                contradiction_bureau_map[key] = set()
            contradiction_bureau_map[key].add(bureau)

        # Check if any contradiction appears across ≥2 bureaus
        multi_bureau_contradictions = [
            (key, bureaus) for key, bureaus in contradiction_bureau_map.items()
            if len(bureaus) >= 2
        ]

        if multi_bureau_contradictions:
            # Found systemic failure pattern
            example_key, bureaus = multi_bureau_contradictions[0]
            account_id, rule_code = example_key.split(":", 1)

            return ExaminerCheckResult(
                passed=False,
                standard_result=ExaminerStandardResult.FAIL_SYSTEMIC,
                failure_reason=(
                    f"Same contradiction ({rule_code}) verified on same tradeline across "
                    f"{len(bureaus)} bureaus ({', '.join(bureaus)}) in single dispute cycle. "
                    f"Demonstrates systemic failure to assure accuracy."
                ),
                response_layer_violation={
                    "id": str(uuid4()),
                    "type": ViolationType.SYSTEMIC_ACCURACY_FAILURE.value,
                    "statute": "15 U.S.C. § 1681e(b)",
                    "severity": Severity.CRITICAL.value,
                    "description": f"Systemic failure: {rule_code} verified across {len(bureaus)} bureaus",
                    "bureaus_affected": list(bureaus),
                    "contradiction_count": len(multi_bureau_contradictions),
                    "authority": "SYSTEM",
                },
                severity_promotion=Severity.CRITICAL,
                escalation_eligible=True,
                evidence={
                    "multi_bureau_contradictions": len(multi_bureau_contradictions),
                    "bureaus_affected": list(bureaus),
                    "example_rule_code": rule_code,
                }
            )

        return None

    # =========================================================================
    # CHECK 4: UDAAP MISLEADING VERIFICATION
    # =========================================================================

    def _check_misleading_verification(
        self,
        dispute: DisputeDB,
        response: DisputeResponseDB,
        original_contradictions: List[Dict[str, Any]],
    ) -> ExaminerCheckResult:
        """
        Check for misleading verification.

        Triggers when:
        - Response is VERIFIED
        - Contradiction has CRITICAL severity
        - Contradiction is a logical impossibility (T1-T4, M1-M2)
        - Evidence was sent with dispute

        Verification of mathematically impossible data creates a misleading
        impression that investigation was conducted.
        """
        if not original_contradictions:
            return ExaminerCheckResult(
                passed=True,
                standard_result=ExaminerStandardResult.PASS
            )

        # Check for CRITICAL logical impossibilities
        critical_impossibilities = []
        for contradiction in original_contradictions:
            severity = str(contradiction.get("severity", "")).lower()
            rule_code = contradiction.get("rule_code", "")

            is_critical = severity == "critical"
            is_impossibility = rule_code in LOGICAL_IMPOSSIBILITY_RULES

            if is_critical and is_impossibility:
                critical_impossibilities.append(contradiction)

        # Check if evidence was sent
        evidence_sent = self._check_evidence_sent(dispute)

        if critical_impossibilities and evidence_sent:
            return ExaminerCheckResult(
                passed=False,
                standard_result=ExaminerStandardResult.FAIL_MISLEADING,
                failure_reason=(
                    f"Verification response is misleading: {len(critical_impossibilities)} "
                    f"CRITICAL logical impossibilities were verified as accurate. "
                    f"Verification creates false impression of thorough investigation."
                ),
                response_layer_violation={
                    "id": str(uuid4()),
                    "type": ViolationType.UDAAP_MISLEADING_VERIFICATION.value,
                    "statute": "15 U.S.C. § 1681i(a)(1)(A)",
                    "severity": Severity.CRITICAL.value,
                    "description": "Misleading verification - verified CRITICAL impossibilities",
                    "critical_impossibility_count": len(critical_impossibilities),
                    "rule_codes": [c.get("rule_code") for c in critical_impossibilities],
                    "evidence_sent": evidence_sent,
                    "authority": "SYSTEM",
                },
                severity_promotion=Severity.CRITICAL,
                escalation_eligible=True,
                evidence={
                    "critical_impossibilities": len(critical_impossibilities),
                    "rule_codes": [c.get("rule_code") for c in critical_impossibilities],
                    "evidence_sent": evidence_sent,
                }
            )

        return ExaminerCheckResult(
            passed=True,
            standard_result=ExaminerStandardResult.PASS
        )

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _check_evidence_sent(self, dispute: DisputeDB) -> bool:
        """
        Check if evidence was sent with the original dispute.

        Evidence indicators:
        - document_hash exists in ExecutionEventDB
        - artifact_pointer exists in ExecutionEventDB

        Returns True if evidence was attached to the dispute letter.
        """
        execution = self.db.query(ExecutionEventDB).filter(
            ExecutionEventDB.dispute_id == dispute.id
        ).first()

        if execution:
            return bool(execution.document_hash or execution.artifact_pointer)

        return False

    def _calculate_severity_promotion(
        self,
        contradictions: List[Dict[str, Any]],
    ) -> Severity:
        """
        Calculate severity promotion based on contradiction severity.

        Rules:
        - Any CRITICAL contradiction → CRITICAL severity
        - 2+ HIGH contradictions → CRITICAL severity
        - 1 HIGH → HIGH severity
        - Otherwise → HIGH (minimum for Tier 2 violations)
        """
        critical_count = sum(
            1 for c in contradictions
            if str(c.get("severity", "")).lower() == "critical"
        )
        high_count = sum(
            1 for c in contradictions
            if str(c.get("severity", "")).lower() == "high"
        )

        if critical_count > 0:
            return Severity.CRITICAL
        if high_count >= 2:
            return Severity.CRITICAL
        if high_count >= 1:
            return Severity.HIGH

        # Minimum severity for Tier 2 response-layer violations
        return Severity.HIGH
