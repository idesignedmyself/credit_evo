"""
Response Evaluator

Maps entity responses to legal interpretations and violations.
Implements the Response → Violation Mapping logic.
"""
from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from uuid import uuid4

from sqlalchemy.orm import Session

from ...models.db_models import (
    DisputeDB, DisputeResponseDB, PaperTrailDB, ReinsertionWatchDB,
    EscalationState, ResponseType, EntityType, ActorType,
    ReinsertionWatchStatus
)


# =============================================================================
# RESPONSE → VIOLATION MAPPING
# =============================================================================

RESPONSE_VIOLATION_MAP = {
    ResponseType.DELETED: {
        "legal_interpretation": "Dispute successful. Item removed from consumer file.",
        "violations_created": [],  # Favorable outcome
        "validation_required": True,
        "validation_type": "reinsertion_watch",
        "deadline_recalc": False,
        "escalation_queued": False,
        "next_state": EscalationState.RESOLVED_DELETED,
    },
    ResponseType.VERIFIED: {
        "legal_interpretation": "Entity claims disputed information is accurate. Compounds liability if underlying violation exists.",
        "violations_by_entity": {
            EntityType.CRA: [
                {
                    "type": "failure_to_conduct_reasonable_investigation",
                    "statute": "FCRA § 611(a)(1)(A)",
                    "condition": "verified_without_furnisher_contact",
                },
            ],
            EntityType.FURNISHER: [
                {
                    "type": "failure_to_investigate",
                    "statute": "FCRA § 623(b)(1)",
                    "condition": "verified_without_substantiation",
                },
            ],
            EntityType.COLLECTOR: [
                {
                    "type": "continued_collection_during_dispute",
                    "statute": "FDCPA § 1692g(b)",
                    "condition": "validation_request_exists",
                    "guardrail": "1692g_b_preconditions",
                },
            ],
        },
        "validation_required": True,
        "validation_type": "ground_truth_comparison",
        "deadline_recalc": True,
        "new_deadlines": {
            "mov_demand": 15,
            "escalation": 30,
        },
        "escalation_queued": True,
        "next_state": EscalationState.NON_COMPLIANT,
    },
    ResponseType.UPDATED: {
        "legal_interpretation": "Entity modified data. Modification may be partial, cosmetic, or substantive.",
        "violations_by_condition": [
            {
                "condition": "update_does_not_cure",
                "type": "continued_inaccuracy",
                "statute": "FCRA § 623(a)(2)",
            },
            {
                "condition": "update_creates_inconsistency",
                "type": "new_data_integrity_violation",
                "statute": "FCRA § 607(b)",
            },
            {
                "condition": "partial_update",
                "type": "incomplete_investigation",
                "statute": "FCRA § 611(a)(1)(A)",
            },
        ],
        "validation_required": True,
        "validation_type": "re_ingestion",
        "deadline_recalc": True,
        "deadline_conditional": True,  # Only if violation persists
        "escalation_queued": "conditional",
        "next_state": EscalationState.EVALUATED,
    },
    ResponseType.INVESTIGATING: {
        "legal_interpretation": "Entity claims ongoing investigation. Stall tactic if received after statutory deadline.",
        "violations_by_condition": [
            {
                "condition": "received_after_30_day_deadline",
                "type": "failure_to_complete_investigation",
                "statute": "FCRA § 611(a)(1)",
            },
            {
                "condition": "received_after_45_day_deadline",
                "type": "failure_to_complete_extended_investigation",
                "statute": "FCRA § 612(a)",
            },
        ],
        "validation_required": False,
        "deadline_recalc": True,
        "new_deadlines": {
            "stall_limit": 15,  # Auto-convert to NO_RESPONSE after 15 days
        },
        "escalation_queued": True,
        "next_state": EscalationState.RESPONDED,
    },
    ResponseType.NO_RESPONSE: {
        "legal_interpretation": "Entity failed to respond within statutory period. Automatic violation.",
        "violations_by_entity": {
            EntityType.CRA: [
                {
                    "type": "failure_to_investigate_within_30_days",
                    "statute": "FCRA § 611(a)(1)(A)",
                },
            ],
            EntityType.FURNISHER: [
                {
                    "type": "failure_to_investigate_notice_of_dispute",
                    "statute": "FCRA § 623(b)(1)(A)",
                },
            ],
            EntityType.COLLECTOR: [
                {
                    "type": "failure_to_provide_validation",
                    "statute": "FDCPA § 1692g(b)",
                    "guardrail": "1692g_b_preconditions",
                },
            ],
        },
        "validation_required": False,
        "deadline_recalc": False,
        "escalation_queued": True,
        "next_state": EscalationState.NON_COMPLIANT,
    },
    ResponseType.REJECTED: {
        "legal_interpretation": "Entity refuses to investigate, claiming dispute is frivolous. Heavily regulated under FCRA § 611(a)(3).",
        "procedural_requirements": {
            "5_day_notice": {
                "statute": "FCRA § 611(a)(3)(A)",
                "description": "Must notify consumer within 5 business days",
            },
            "specific_reason": {
                "statute": "FCRA § 611(a)(3)(B)",
                "description": "Must state specific reason for determination",
            },
            "missing_info": {
                "statute": "FCRA § 611(a)(3)(B)",
                "description": "Must identify what information is needed",
            },
        },
        "violations_by_condition": [
            {
                "condition": "no_5_day_notice",
                "type": "procedural_rejection_violation",
                "statute": "FCRA § 611(a)(3)(A)",
            },
            {
                "condition": "no_specific_reason",
                "type": "invalid_frivolous_determination",
                "statute": "FCRA § 611(a)(3)(B)",
            },
            {
                "condition": "no_cure_opportunity",
                "type": "denial_of_procedural_rights",
                "statute": "FCRA § 611(a)(3)(B)",
            },
            {
                "condition": "rejection_of_valid_dispute",
                "type": "willful_failure_to_investigate",
                "statute": "FCRA § 616",
            },
        ],
        "validation_required": True,
        "validation_type": "procedural_compliance",
        "deadline_recalc": True,
        "deadline_conditional": True,
        "escalation_queued": True,
        "next_state": "conditional",  # REJECTED_PENDING_CURE or NON_COMPLIANT
    },
}


# =============================================================================
# FDCPA §1692g(b) GUARDRAIL
# =============================================================================
#
# MANDATORY PRECONDITIONS FOR §1692g(b) CITATION:
#
# This guardrail MUST be applied before citing §1692g(b) in any context.
# The statute governs debt validation requirements and applies ONLY when
# ALL three preconditions are satisfied:
#
# 1. ENTITY TYPE: Must be a third-party debt collector (not original creditor)
#    - Original creditors are NOT subject to FDCPA
#    - Furnishers who are also collectors must be properly classified
#
# 2. VALIDATION REQUEST: Consumer must have sent written validation request
#    - Request must be within 30 days of initial collector communication
#    - Verbal requests do NOT trigger §1692g(b) protections
#
# 3. CONTINUED COLLECTION: Collector must have continued collection activity
#    - This includes credit reporting, phone calls, letters, or legal action
#    - Continuation must occur BEFORE providing validation
#
# If ANY precondition is NOT met, §1692g(b) MUST NOT be cited.
# System will automatically substitute appropriate alternative statutes.
#
# =============================================================================

class FDCPA1692gGuardrail:
    """
    EXPLICIT GUARDRAIL for FDCPA §1692g(b) application.

    THIS GUARDRAIL IS MANDATORY - the system MUST call can_cite_1692g_b()
    before creating any violation that references §1692g(b).

    If preconditions are not met, use get_alternative_statutes() instead.
    """

    @staticmethod
    def can_cite_1692g_b(dispute: DisputeDB) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Check if §1692g(b) can be cited for this dispute.

        Returns (can_cite, reason, precondition_status)

        MUST be called before ANY §1692g(b) citation.
        """
        preconditions = {
            "is_debt_collector": False,
            "has_validation_request": False,
            "collection_continued": False,
        }

        # Precondition 1: Must be debt collector (NOT original creditor)
        if dispute.entity_type == EntityType.COLLECTOR:
            preconditions["is_debt_collector"] = True
        else:
            return (
                False,
                f"GUARDRAIL BLOCK: Entity type is {dispute.entity_type.value}, not COLLECTOR. §1692g(b) does not apply.",
                preconditions
            )

        # Precondition 2: Must have written validation request within 30 days
        if dispute.has_validation_request:
            preconditions["has_validation_request"] = True
        else:
            return (
                False,
                "GUARDRAIL BLOCK: No validation request exists. §1692g(b) requires consumer to have sent written validation request.",
                preconditions
            )

        # Precondition 3: Collection must have continued before validation
        if dispute.collection_continued:
            preconditions["collection_continued"] = True
        else:
            return (
                False,
                "GUARDRAIL BLOCK: Collection did not continue before validation. §1692g(b) requires collector to have continued collection activities.",
                preconditions
            )

        # ALL PRECONDITIONS MET
        return (
            True,
            "All §1692g(b) preconditions satisfied. Statute may be cited.",
            preconditions
        )

    @staticmethod
    def get_alternative_statutes() -> List[Dict[str, str]]:
        """
        Get alternative FDCPA statutes when §1692g(b) preconditions are NOT met.

        These statutes may apply to debt collector misconduct even when
        §1692g(b) validation requirements are not triggered.
        """
        return [
            {
                "statute": "FDCPA § 1692e(8)",
                "description": "False representation of credit information",
                "use_when": "Collector reported inaccurate information to CRA",
            },
            {
                "statute": "FDCPA § 1692f",
                "description": "Unfair practices",
                "use_when": "Collector engaged in unfair collection methods",
            },
            {
                "statute": "FDCPA § 1692e",
                "description": "False or misleading representations",
                "use_when": "Collector made false statements about debt",
            },
            {
                "statute": "FDCPA § 1692d",
                "description": "Harassment or abuse",
                "use_when": "Collector engaged in harassing behavior",
            },
        ]

    @staticmethod
    def select_appropriate_statute(
        dispute: DisputeDB,
        violation_context: str
    ) -> Dict[str, Any]:
        """
        Select the appropriate FDCPA statute based on guardrail check.

        Returns the statute to cite and the reason for selection.
        """
        can_cite, reason, preconditions = FDCPA1692gGuardrail.can_cite_1692g_b(dispute)

        if can_cite:
            return {
                "statute": "FDCPA § 1692g(b)",
                "can_cite": True,
                "reason": reason,
                "preconditions": preconditions,
            }
        else:
            # Select best alternative based on context
            alternatives = FDCPA1692gGuardrail.get_alternative_statutes()
            # Default to §1692e(8) for reporting violations
            if "report" in violation_context.lower() or "credit" in violation_context.lower():
                selected = alternatives[0]  # §1692e(8)
            else:
                selected = alternatives[1]  # §1692f

            return {
                "statute": selected["statute"],
                "can_cite": False,
                "reason": reason,
                "preconditions": preconditions,
                "alternative_used": True,
                "alternative_reason": selected["use_when"],
            }


# =============================================================================
# RESPONSE EVALUATOR
# =============================================================================

class ResponseEvaluator:
    """
    Evaluates entity responses and creates appropriate violations.

    Core Responsibilities:
    - Map responses to legal interpretations
    - Create violations based on response type and conditions
    - Trigger validation requirements
    - Determine state transitions
    """

    def __init__(self, db_session: Session):
        """Initialize with database session."""
        self.db = db_session

    def evaluate_response(
        self,
        dispute: DisputeDB,
        response: DisputeResponseDB,
    ) -> Dict[str, Any]:
        """
        Evaluate a response and determine legal consequences.

        Returns evaluation result with violations and next actions.
        """
        response_config = RESPONSE_VIOLATION_MAP.get(response.response_type, {})

        result = {
            "response_type": response.response_type.value,
            "legal_interpretation": response_config.get("legal_interpretation", "Unknown response type"),
            "violations_created": [],
            "validation_required": response_config.get("validation_required", False),
            "validation_type": response_config.get("validation_type"),
            "deadline_recalc": response_config.get("deadline_recalc", False),
            "escalation_queued": response_config.get("escalation_queued", False),
            "next_state": response_config.get("next_state"),
            "actions": [],
        }

        # Create violations based on response type
        if response.response_type == ResponseType.DELETED:
            result = self._handle_deleted_response(dispute, response, result)

        elif response.response_type == ResponseType.VERIFIED:
            result = self._handle_verified_response(dispute, response, result)

        elif response.response_type == ResponseType.UPDATED:
            result = self._handle_updated_response(dispute, response, result)

        elif response.response_type == ResponseType.INVESTIGATING:
            result = self._handle_investigating_response(dispute, response, result)

        elif response.response_type == ResponseType.NO_RESPONSE:
            result = self._handle_no_response(dispute, response, result)

        elif response.response_type == ResponseType.REJECTED:
            result = self._handle_rejected_response(dispute, response, result)

        # Update response with violations
        response.new_violations = result["violations_created"]

        # Create paper trail
        self._create_evaluation_paper_trail(dispute, response, result)

        return result

    def _handle_deleted_response(
        self,
        dispute: DisputeDB,
        response: DisputeResponseDB,
        result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle DELETED response - favorable outcome, start reinsertion watch."""
        # Create reinsertion watch
        watch = ReinsertionWatchDB(
            id=str(uuid4()),
            dispute_id=dispute.id,
            account_fingerprint=dispute.account_fingerprint or f"{dispute.entity_name}_{dispute.violation_id}",
            furnisher_name=dispute.entity_name if dispute.entity_type == EntityType.FURNISHER else None,
            bureau=dispute.entity_name if dispute.entity_type == EntityType.CRA else None,
            monitoring_start=response.response_date or date.today(),
            monitoring_end=(response.response_date or date.today()) + timedelta(days=90),
            status=ReinsertionWatchStatus.ACTIVE,
        )
        self.db.add(watch)

        result["actions"].append({
            "type": "reinsertion_watch_created",
            "watch_id": watch.id,
            "monitoring_end": watch.monitoring_end.isoformat(),
        })

        return result

    def _handle_verified_response(
        self,
        dispute: DisputeDB,
        response: DisputeResponseDB,
        result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle VERIFIED response - compounds liability."""
        violations = []
        config = RESPONSE_VIOLATION_MAP[ResponseType.VERIFIED]

        # Get entity-specific violations
        entity_violations = config.get("violations_by_entity", {}).get(dispute.entity_type, [])

        for v in entity_violations:
            # Check guardrail for collector - MANDATORY for §1692g(b)
            if v.get("guardrail") == "1692g_b_preconditions":
                can_cite, reason, preconditions = FDCPA1692gGuardrail.can_cite_1692g_b(dispute)
                if not can_cite:
                    # GUARDRAIL ACTIVE: Use alternative statute
                    statute_selection = FDCPA1692gGuardrail.select_appropriate_statute(
                        dispute,
                        violation_context="credit reporting verification"
                    )
                    violations.append({
                        "id": str(uuid4()),
                        "type": "false_representation",
                        "statute": statute_selection["statute"],
                        "description": f"Collector verified disputed debt. {reason}",
                        "severity": "HIGH",
                        "guardrail_applied": True,
                        "guardrail_reason": reason,
                        "preconditions_checked": preconditions,
                        "authority": "SYSTEM",  # System determined statute selection
                    })
                    continue

            violations.append({
                "id": str(uuid4()),
                "type": v["type"],
                "statute": v["statute"],
                "description": f"Entity verified disputed information without proper investigation",
                "severity": "HIGH",
                "willful_indicator": True,  # Verification of known inaccuracy suggests willfulness
                "authority": "SYSTEM",  # System created violation
            })

        # Add willful noncompliance if original violation was provably false (SYSTEM determination)
        if dispute.original_violation_data:
            violations.append({
                "id": str(uuid4()),
                "type": "willful_noncompliance",
                "statute": "FCRA § 616",
                "description": "Verification of provably false data indicates willful noncompliance",
                "severity": "CRITICAL",
                "damages_range": "$100 - $1,000 per violation",
                "authority": "SYSTEM",  # System elevates to willful based on evidence
            })

        result["violations_created"] = violations
        result["actions"].append({
            "type": "mov_demand_available",
            "deadline": 15,
            "description": "Method of Verification demand can be sent",
        })

        return result

    def _handle_updated_response(
        self,
        dispute: DisputeDB,
        response: DisputeResponseDB,
        result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle UPDATED response - requires validation."""
        result["actions"].append({
            "type": "validation_required",
            "validation_type": "re_ingestion",
            "description": "User must confirm updated values or re-ingest report",
        })

        # Violations will be determined after validation
        result["pending_validation"] = True

        return result

    def _handle_investigating_response(
        self,
        dispute: DisputeDB,
        response: DisputeResponseDB,
        result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle INVESTIGATING response - start stall timer.

        AUTHORITY: USER reports "investigating" response.
        AUTHORITY: SYSTEM creates violation if received after deadline.
        AUTHORITY: SYSTEM starts stall timer automatically.
        """
        violations = []

        # Check if received after deadline (stall tactic) - SYSTEM evaluation
        if response.response_date and dispute.deadline_date:
            if response.response_date > dispute.deadline_date:
                violations.append({
                    "id": str(uuid4()),
                    "type": "failure_to_complete_investigation",
                    "statute": "FCRA § 611(a)(1)",
                    "description": "Investigation notice received after statutory deadline",
                    "severity": "HIGH",
                    "authority": "SYSTEM",  # System detected deadline breach
                })

        result["violations_created"] = violations
        result["actions"].append({
            "type": "stall_timer_started",
            "expires_in_days": 15,
            "description": "SYSTEM: Will auto-convert to NO_RESPONSE if no final response in 15 days",
            "authority": "SYSTEM",  # System schedules automatic conversion
        })

        return result

    def _handle_no_response(
        self,
        dispute: DisputeDB,
        response: DisputeResponseDB,
        result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle NO_RESPONSE - automatic violation."""
        violations = self.create_no_response_violations(dispute)
        result["violations_created"] = violations

        return result

    def _handle_rejected_response(
        self,
        dispute: DisputeDB,
        response: DisputeResponseDB,
        result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle REJECTED response - check procedural compliance.

        AUTHORITY: SYSTEM - Procedural violation detection is automatic.
        User reports rejection; system evaluates §611(a)(3) compliance.
        """
        violations = []

        # Check procedural requirements (SYSTEM evaluates user-reported data)
        if not response.has_5_day_notice:
            violations.append({
                "id": str(uuid4()),
                "type": "procedural_rejection_violation",
                "statute": "FCRA § 611(a)(3)(A)",
                "description": "No 5-day notice provided for frivolous determination",
                "severity": "HIGH",
                "authority": "SYSTEM",
            })

        if not response.has_specific_reason:
            violations.append({
                "id": str(uuid4()),
                "type": "invalid_frivolous_determination",
                "statute": "FCRA § 611(a)(3)(B)",
                "description": "No specific reason stated for rejection",
                "severity": "HIGH",
                "authority": "SYSTEM",
            })

        if not response.has_missing_info_request:
            violations.append({
                "id": str(uuid4()),
                "type": "denial_of_procedural_rights",
                "statute": "FCRA § 611(a)(3)(B)",
                "description": "No cure opportunity provided - missing information not identified",
                "severity": "HIGH",
                "authority": "SYSTEM",
            })

        # If all procedural requirements violated, likely willful (SYSTEM determination)
        if len(violations) >= 2:
            violations.append({
                "id": str(uuid4()),
                "type": "willful_failure_to_investigate",
                "statute": "FCRA § 616",
                "description": "Pattern of procedural violations indicates willful refusal to investigate",
                "severity": "CRITICAL",
                "authority": "SYSTEM",
            })

        result["violations_created"] = violations

        # Determine next state based on procedural compliance
        if violations:
            result["next_state"] = EscalationState.NON_COMPLIANT
        else:
            result["next_state"] = EscalationState.EVALUATED
            result["actions"].append({
                "type": "procedural_cure_available",
                "deadline": 30,
                "description": "Consumer can provide requested information to restart dispute",
            })

        return result

    def create_no_response_violations(self, dispute: DisputeDB) -> List[Dict[str, Any]]:
        """
        Create violations for NO_RESPONSE based on entity type.

        AUTHORITY: SYSTEM - Violations are created automatically by deadline engine.
        No user input required.
        """
        violations = []
        config = RESPONSE_VIOLATION_MAP[ResponseType.NO_RESPONSE]

        entity_violations = config.get("violations_by_entity", {}).get(dispute.entity_type, [])

        for v in entity_violations:
            # Check guardrail for collector - MANDATORY for §1692g(b)
            if v.get("guardrail") == "1692g_b_preconditions":
                can_cite, reason, preconditions = FDCPA1692gGuardrail.can_cite_1692g_b(dispute)
                if not can_cite:
                    # GUARDRAIL ACTIVE: Use alternative statute
                    statute_selection = FDCPA1692gGuardrail.select_appropriate_statute(
                        dispute,
                        violation_context="debt collection no response"
                    )
                    violations.append({
                        "id": str(uuid4()),
                        "type": "unfair_practices",
                        "statute": statute_selection["statute"],
                        "description": f"Collector failed to respond to dispute. {reason}",
                        "severity": "HIGH",
                        "guardrail_applied": True,
                        "guardrail_reason": reason,
                        "preconditions_checked": preconditions,
                        "authority": "SYSTEM",  # System created violation
                    })
                    continue

            violations.append({
                "id": str(uuid4()),
                "type": v["type"],
                "statute": v["statute"],
                "description": f"Entity failed to respond within statutory deadline",
                "severity": "HIGH",
                "authority": "SYSTEM",  # System created violation
            })

        return violations

    def _create_evaluation_paper_trail(
        self,
        dispute: DisputeDB,
        response: DisputeResponseDB,
        result: Dict[str, Any]
    ):
        """Create paper trail entry for response evaluation."""
        paper_trail = PaperTrailDB(
            id=str(uuid4()),
            dispute_id=dispute.id,
            event_type="response_evaluated",
            actor=ActorType.SYSTEM,
            description=f"Response type {response.response_type.value} evaluated. {len(result['violations_created'])} violations created.",
            metadata={
                "response_id": response.id,
                "response_type": response.response_type.value,
                "violations_created": len(result["violations_created"]),
                "escalation_queued": result["escalation_queued"],
                "next_state": result["next_state"].value if isinstance(result["next_state"], EscalationState) else result["next_state"],
            }
        )
        self.db.add(paper_trail)
