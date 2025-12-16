"""
Cross-Entity Intelligence

Detects patterns across multiple entities (CRAs, furnishers, collectors).
Creates violations based on inconsistent or contradictory responses.
"""
from datetime import date, datetime
from typing import Optional, List, Dict, Any, Tuple
from uuid import uuid4

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from ...models.db_models import (
    DisputeDB, DisputeResponseDB, PaperTrailDB,
    EscalationState, ResponseType, EntityType, ActorType
)


# =============================================================================
# CROSS-ENTITY PATTERNS
# =============================================================================

CROSS_ENTITY_PATTERNS = {
    "bureau_deletes_furnisher_rereports": {
        "description": "Bureau deletes item but furnisher re-reports it",
        "detection": "CRA DELETED + same account reappears + no reinsertion notice",
        "violations": [
            {"type": "reinsertion_without_notice", "statute": "FCRA § 611(a)(5)(B)", "entity": "CRA"},
            {"type": "reporting_deleted_information", "statute": "FCRA § 623(a)(6)", "entity": "FURNISHER"},
        ],
        "escalation": EscalationState.REGULATORY_ESCALATION,
        "severity": "CRITICAL",
    },
    "bureau_verify_delete_conflict": {
        "description": "One bureau verifies while another deletes same account",
        "detection": "Bureau_A VERIFIED + Bureau_B DELETED + same account fingerprint",
        "violations": [
            {"type": "failure_to_conduct_reasonable_investigation", "statute": "FCRA § 611(a)(1)(A)", "entity": "verifying_bureau"},
        ],
        "escalation": EscalationState.NON_COMPLIANT,
        "severity": "HIGH",
    },
    "bureau_verifies_without_furnisher": {
        "description": "Bureau verifies but furnisher did not respond or deleted",
        "detection": "CRA VERIFIED + Furnisher (NO_RESPONSE or DELETED)",
        "violations": [
            {"type": "verification_without_source_confirmation", "statute": "FCRA § 611(a)(1)(A)", "entity": "CRA"},
        ],
        "escalation": EscalationState.NON_COMPLIANT,
        "severity": "HIGH",
    },
    "cross_bureau_dofd_inconsistency": {
        "description": "Date of First Delinquency varies by more than 30 days across bureaus",
        "detection": "Account on multiple bureaus + DOFD variance > 30 days",
        "violations": [
            {"type": "failure_to_report_accurate_information", "statute": "FCRA § 623(a)(2)", "entity": "FURNISHER"},
            {"type": "failure_to_maintain_accuracy", "statute": "FCRA § 607(b)", "entity": "CRA"},
        ],
        "escalation": EscalationState.SUBSTANTIVE_ENFORCEMENT,
        "severity": "HIGH",
    },
    "cross_bureau_status_conflict": {
        "description": "Account status conflicts across bureaus (e.g., Paid vs Collection)",
        "detection": "Account on multiple bureaus + conflicting status codes",
        "violations": [
            {"type": "failure_to_report_accurate_information", "statute": "FCRA § 623(a)(2)", "entity": "FURNISHER"},
            {"type": "failure_to_maintain_accuracy", "statute": "FCRA § 607(b)", "entity": "CRA"},
        ],
        "escalation": EscalationState.SUBSTANTIVE_ENFORCEMENT,
        "severity": "HIGH",
    },
}


# =============================================================================
# CROSS-ENTITY INTELLIGENCE
# =============================================================================

class CrossEntityIntelligence:
    """
    Detects patterns across multiple entities.

    System-automatic detection during response evaluation
    and report ingestion.
    """

    def __init__(self, db_session: Session):
        """Initialize with database session."""
        self.db = db_session

    def analyze_responses(
        self,
        user_id: str,
        account_fingerprint: str,
    ) -> Dict[str, Any]:
        """
        Analyze all responses for an account across entities.

        Detects contradictions and inconsistencies.
        """
        # Get all disputes for this account
        disputes = self.db.query(DisputeDB).filter(
            DisputeDB.user_id == user_id,
            DisputeDB.account_fingerprint == account_fingerprint,
        ).all()

        if len(disputes) < 2:
            return {"patterns_detected": [], "violations_created": []}

        # Collect responses by entity
        responses_by_entity = {}
        for dispute in disputes:
            entity_key = f"{dispute.entity_type.value}_{dispute.entity_name}"
            responses = self.db.query(DisputeResponseDB).filter(
                DisputeResponseDB.dispute_id == dispute.id
            ).all()

            responses_by_entity[entity_key] = {
                "dispute": dispute,
                "responses": responses,
                "latest_response": responses[-1] if responses else None,
            }

        # Run pattern detection
        patterns_detected = []
        violations_created = []

        # Pattern 1: Bureau Verifies, Another Deletes
        verify_delete = self._detect_verify_delete_conflict(responses_by_entity)
        if verify_delete:
            patterns_detected.append(verify_delete)
            violations_created.extend(verify_delete.get("violations", []))

        # Pattern 2: Bureau Verifies Without Furnisher Substantiation
        verify_without_furnisher = self._detect_verify_without_furnisher(responses_by_entity)
        if verify_without_furnisher:
            patterns_detected.append(verify_without_furnisher)
            violations_created.extend(verify_without_furnisher.get("violations", []))

        return {
            "account_fingerprint": account_fingerprint,
            "entities_analyzed": len(responses_by_entity),
            "patterns_detected": patterns_detected,
            "violations_created": violations_created,
        }

    def _detect_verify_delete_conflict(
        self,
        responses_by_entity: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Detect Pattern 2: One bureau verifies, another deletes.

        If Bureau A verifies and Bureau B deletes the same account,
        Bureau A failed to conduct a reasonable investigation.
        """
        cra_responses = {}

        for entity_key, data in responses_by_entity.items():
            if data["dispute"].entity_type == EntityType.CRA:
                latest = data.get("latest_response")
                if latest:
                    cra_responses[entity_key] = {
                        "dispute": data["dispute"],
                        "response_type": latest.response_type,
                    }

        # Check for verify/delete conflict
        verified_bureaus = [k for k, v in cra_responses.items() if v["response_type"] == ResponseType.VERIFIED]
        deleted_bureaus = [k for k, v in cra_responses.items() if v["response_type"] == ResponseType.DELETED]

        if verified_bureaus and deleted_bureaus:
            violations = []
            pattern_config = CROSS_ENTITY_PATTERNS["bureau_verify_delete_conflict"]

            for verified_key in verified_bureaus:
                verified_data = cra_responses[verified_key]
                violation = {
                    "id": str(uuid4()),
                    "type": pattern_config["violations"][0]["type"],
                    "statute": pattern_config["violations"][0]["statute"],
                    "description": f"{verified_data['dispute'].entity_name} verified while another bureau deleted same account",
                    "severity": pattern_config["severity"],
                    "evidence": {
                        "verifying_bureau": verified_data["dispute"].entity_name,
                        "deleting_bureaus": [cra_responses[k]["dispute"].entity_name for k in deleted_bureaus],
                    },
                }
                violations.append(violation)

                # Create paper trail
                self._create_pattern_paper_trail(
                    dispute=verified_data["dispute"],
                    pattern_name="bureau_verify_delete_conflict",
                    violations=violations,
                )

            return {
                "pattern": "bureau_verify_delete_conflict",
                "description": pattern_config["description"],
                "violations": violations,
                "escalation": pattern_config["escalation"].value,
            }

        return None

    def _detect_verify_without_furnisher(
        self,
        responses_by_entity: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Detect Pattern 3: Bureau verifies without furnisher substantiation.

        If CRA verifies but furnisher didn't respond or deleted,
        CRA verification was unreasonable.
        """
        cra_verified = []
        furnisher_responses = {}

        for entity_key, data in responses_by_entity.items():
            latest = data.get("latest_response")
            if not latest:
                continue

            if data["dispute"].entity_type == EntityType.CRA:
                if latest.response_type == ResponseType.VERIFIED:
                    cra_verified.append(data)
            elif data["dispute"].entity_type == EntityType.FURNISHER:
                furnisher_responses[entity_key] = {
                    "dispute": data["dispute"],
                    "response_type": latest.response_type,
                }

        if not cra_verified or not furnisher_responses:
            return None

        # Check if any furnisher didn't respond or deleted
        furnisher_issues = [
            k for k, v in furnisher_responses.items()
            if v["response_type"] in [ResponseType.NO_RESPONSE, ResponseType.DELETED]
        ]

        if cra_verified and furnisher_issues:
            violations = []
            pattern_config = CROSS_ENTITY_PATTERNS["bureau_verifies_without_furnisher"]

            for cra_data in cra_verified:
                violation = {
                    "id": str(uuid4()),
                    "type": pattern_config["violations"][0]["type"],
                    "statute": pattern_config["violations"][0]["statute"],
                    "description": f"{cra_data['dispute'].entity_name} verified but furnisher silence/deletion contradicts verification",
                    "severity": pattern_config["severity"],
                    "evidence": {
                        "verifying_cra": cra_data["dispute"].entity_name,
                        "furnisher_issues": [
                            {
                                "furnisher": furnisher_responses[k]["dispute"].entity_name,
                                "response": furnisher_responses[k]["response_type"].value,
                            }
                            for k in furnisher_issues
                        ],
                    },
                }
                violations.append(violation)

                # Create paper trail
                self._create_pattern_paper_trail(
                    dispute=cra_data["dispute"],
                    pattern_name="bureau_verifies_without_furnisher",
                    violations=violations,
                )

            return {
                "pattern": "bureau_verifies_without_furnisher",
                "description": pattern_config["description"],
                "violations": violations,
                "escalation": pattern_config["escalation"].value,
            }

        return None

    def detect_dofd_inconsistency(
        self,
        account_data: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """
        Detect Pattern 4: DOFD varies by more than 30 days across bureaus.

        Args:
            account_data: List of account data from different bureaus
                          Each should have 'bureau' and 'dofd' keys
        """
        if len(account_data) < 2:
            return None

        dofds = []
        for data in account_data:
            dofd = data.get("dofd")
            if dofd:
                if isinstance(dofd, str):
                    dofd = datetime.fromisoformat(dofd).date()
                dofds.append({"bureau": data["bureau"], "dofd": dofd})

        if len(dofds) < 2:
            return None

        # Calculate variance
        dates = [d["dofd"] for d in dofds]
        min_date = min(dates)
        max_date = max(dates)
        variance_days = (max_date - min_date).days

        if variance_days > 30:
            pattern_config = CROSS_ENTITY_PATTERNS["cross_bureau_dofd_inconsistency"]

            violations = []
            for v_config in pattern_config["violations"]:
                violation = {
                    "id": str(uuid4()),
                    "type": v_config["type"],
                    "statute": v_config["statute"],
                    "description": f"DOFD varies by {variance_days} days across bureaus (max allowed: 30)",
                    "severity": pattern_config["severity"],
                    "evidence": {
                        "dofd_by_bureau": {d["bureau"]: d["dofd"].isoformat() for d in dofds},
                        "variance_days": variance_days,
                    },
                }
                violations.append(violation)

            return {
                "pattern": "cross_bureau_dofd_inconsistency",
                "description": pattern_config["description"],
                "violations": violations,
                "escalation": pattern_config["escalation"].value,
            }

        return None

    def detect_status_conflict(
        self,
        account_data: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """
        Detect Pattern 5: Status codes conflict across bureaus.

        Args:
            account_data: List of account data from different bureaus
                          Each should have 'bureau' and 'status' keys
        """
        if len(account_data) < 2:
            return None

        statuses = {}
        for data in account_data:
            bureau = data.get("bureau")
            status = data.get("status", "").upper()
            if bureau and status:
                statuses[bureau] = status

        if len(statuses) < 2:
            return None

        # Check for conflicts
        unique_statuses = set(statuses.values())

        # Define conflicting status pairs
        conflicts = [
            ("PAID", "COLLECTION"),
            ("CURRENT", "CHARGED OFF"),
            ("CLOSED", "OPEN"),
            ("PAID", "DELINQUENT"),
        ]

        has_conflict = False
        conflict_details = []

        for status1, status2 in conflicts:
            if status1 in unique_statuses and status2 in unique_statuses:
                has_conflict = True
                conflict_details.append(f"{status1} vs {status2}")

        if has_conflict:
            pattern_config = CROSS_ENTITY_PATTERNS["cross_bureau_status_conflict"]

            violations = []
            for v_config in pattern_config["violations"]:
                violation = {
                    "id": str(uuid4()),
                    "type": v_config["type"],
                    "statute": v_config["statute"],
                    "description": f"Status conflicts across bureaus: {', '.join(conflict_details)}",
                    "severity": pattern_config["severity"],
                    "evidence": {
                        "status_by_bureau": statuses,
                        "conflicts": conflict_details,
                    },
                }
                violations.append(violation)

            return {
                "pattern": "cross_bureau_status_conflict",
                "description": pattern_config["description"],
                "violations": violations,
                "escalation": pattern_config["escalation"].value,
            }

        return None

    def _create_pattern_paper_trail(
        self,
        dispute: DisputeDB,
        pattern_name: str,
        violations: List[Dict[str, Any]],
    ):
        """Create paper trail entry for pattern detection."""
        paper_trail = PaperTrailDB(
            id=str(uuid4()),
            dispute_id=dispute.id,
            event_type="cross_entity_pattern_detected",
            actor=ActorType.SYSTEM,
            description=f"Cross-entity pattern detected: {pattern_name}. {len(violations)} violations created.",
            metadata={
                "pattern": pattern_name,
                "violations_count": len(violations),
                "violation_ids": [v["id"] for v in violations],
            }
        )
        self.db.add(paper_trail)

    def run_full_analysis(
        self,
        user_id: str,
    ) -> Dict[str, Any]:
        """
        Run full cross-entity analysis for a user.

        Analyzes all disputes and detects patterns.
        """
        # Get all unique account fingerprints for user
        disputes = self.db.query(DisputeDB).filter(
            DisputeDB.user_id == user_id,
            DisputeDB.account_fingerprint.isnot(None),
        ).all()

        fingerprints = set(d.account_fingerprint for d in disputes if d.account_fingerprint)

        all_patterns = []
        all_violations = []

        for fingerprint in fingerprints:
            result = self.analyze_responses(user_id, fingerprint)
            all_patterns.extend(result.get("patterns_detected", []))
            all_violations.extend(result.get("violations_created", []))

        return {
            "user_id": user_id,
            "accounts_analyzed": len(fingerprints),
            "patterns_detected": len(all_patterns),
            "violations_created": len(all_violations),
            "details": {
                "patterns": all_patterns,
                "violations": all_violations,
            }
        }
