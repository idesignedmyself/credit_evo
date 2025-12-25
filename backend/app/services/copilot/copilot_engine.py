"""
Credit Engine 2.0 - Goal-Oriented Copilot Engine

MANDATORY CONSTRAINTS:
1. NO SOL LOGIC - Zero statute-of-limitations reasoning. Copilot never reasons about SOL.
2. FCRA-native skip codes only
3. Impact = goal-relative (not severity-relative)
4. Two dependency gates before scoring
5. Employment = zero public records required

This engine is:
- Deterministic: Same input = same output, no ML
- Read-only: Does not modify credit data
- Explainable: Every recommendation has explicit rationale
- Conservative: Errs on side of caution with risk warnings

Execution Ledger Integration (B7):
- Generates dispute_session_id at decision time
- Reads aggregated signals from CopilotSignalCacheDB
- Never writes to the ledger (Copilot is read-only)
"""

from __future__ import annotations

from dataclasses import asdict, replace
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING
from uuid import uuid4

from app.models.copilot_models import (
    ActionType,
    Blocker,
    CopilotRecommendation,
    CreditGoal,
    DeletabilityLevel,
    DELETABILITY_WEIGHTS,
    EnforcementAction,
    GOAL_REQUIREMENTS,
    SkipCode,
    SKIP_CODE_DESCRIPTIONS,
    SkipRationale,
    TargetCreditState,
)

# Conditional import to avoid circular dependency at import time
if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class CopilotEngine:
    """
    Goal-Oriented Credit Copilot Engine.

    Analyzes violations, contradictions, and discrepancies against
    a user's stated financial goal. Generates prioritized enforcement
    strategy with clear attack/skip guidance.

    Design principles:
    - Deterministic: No ML, no probability, same input = same output
    - Explainable: Every recommendation has explicit rationale
    - Conservative: Errs on side of caution with risk warnings
    - Read-only: Does not modify credit data, only advises
    - NO SOL: Never reasons about statute of limitations
    """

    # DOFD-related contradiction codes that trigger the stability gate
    DOFD_GATE_CODES = {"D1", "D2", "D3"}

    # Collection-related furnisher types that trigger ownership gate
    OWNERSHIP_GATE_FURNISHERS = {"COLLECTION", "DEBT_BUYER", "COLLECTOR", "UNKNOWN"}

    # Category mappings for classification
    COLLECTION_CATEGORIES = {"collection", "collections", "debt_collection"}
    CHARGEOFF_CATEGORIES = {"chargeoff", "charge_off", "charge-off", "written_off"}
    LATE_CATEGORIES = {"late", "delinquency", "delinquent", "past_due"}
    PUBLIC_RECORD_CATEGORIES = {"public_record", "judgment", "lien", "bankruptcy", "tax_lien"}
    INQUIRY_CATEGORIES = {"inquiry", "hard_inquiry", "hard_pull"}

    # ==========================================================================
    # PUBLIC API
    # ==========================================================================

    def analyze(
        self,
        *,
        goal: Optional[CreditGoal] = None,
        violations: Optional[List[Dict[str, Any]]] = None,
        contradictions: Optional[List[Dict[str, Any]]] = None,
        user_id: Optional[str] = None,
        report_id: Optional[str] = None,
        db_session: Optional["Session"] = None,
    ) -> CopilotRecommendation:
        """
        Main analysis entry point.

        Args:
            goal: User's financial goal (defaults to CREDIT_HYGIENE)
            violations: List of violation dicts from audit engine
            contradictions: List of contradiction dicts from contradiction engine
            user_id: Optional user ID for tracking
            report_id: Optional report ID for tracking
            db_session: Optional database session for ledger integration

        Returns:
            CopilotRecommendation with prioritized attack plan and skip list
        """
        goal = goal or CreditGoal.CREDIT_HYGIENE
        target = GOAL_REQUIREMENTS.get(goal, GOAL_REQUIREMENTS[CreditGoal.CREDIT_HYGIENE])

        violations = violations or []
        contradictions = contradictions or []

        # Generate dispute_session_id for Execution Ledger correlation
        # This ID links the entire enforcement lifecycle
        dispute_session_id = None
        ledger_signals = {}
        if db_session and user_id and report_id:
            from ..enforcement.dispute_session import DisputeSessionService
            from ..enforcement.execution_ledger import ExecutionLedgerService

            session_service = DisputeSessionService(db_session)
            dispute_session_id = session_service.create_session(
                user_id=user_id,
                report_id=report_id,
                credit_goal=goal.value,
            )

            # Read aggregated signals from ledger (Copilot never writes)
            ledger_service = ExecutionLedgerService(db_session)
            ledger_signals = ledger_service.get_all_copilot_signals("GLOBAL")

        # Step 1: Convert inputs to Blockers
        blockers = self._identify_blockers(goal, target, violations, contradictions)

        # Step 2: Apply dependency gates BEFORE scoring
        blockers = self._apply_dofd_stability_gate(blockers)
        blockers = self._apply_ownership_gate(blockers)

        # Step 2.5: Apply ledger signals to adjust risk scores
        if ledger_signals:
            blockers = self._apply_ledger_signals(blockers, ledger_signals)

        # Step 3: Identify items to skip
        skips = self._identify_skips(blockers)
        skip_ids = {s.source_id for s in skips}

        # Step 4: Generate attack plan (excludes skips)
        actions = self._generate_attack_plan(goal, target, blockers, skip_ids)

        # Step 5: Determine sequencing rationale
        sequencing = self._build_sequencing_rationale(goal, blockers, actions, skips)

        # Step 6: Assess goal achievability
        achievability = self._assess_achievability(goal, target, blockers)
        gap_summary = self._build_gap_summary(goal, blockers)

        # Check which gates are active
        dofd_gate_active = any(
            b.dofd_unstable or b.rule_code in self.DOFD_GATE_CODES
            for b in blockers
        )
        ownership_gate_active = any(b.requires_ownership_first for b in blockers)

        return CopilotRecommendation(
            recommendation_id=str(uuid4()),
            user_id=user_id,
            report_id=report_id,
            generated_at=datetime.utcnow(),
            dispute_session_id=dispute_session_id,
            goal=goal,
            target_state=target,
            current_gap_summary=gap_summary,
            goal_achievability=achievability,
            blockers=blockers,
            hard_blocker_count=sum(1 for b in blockers if b.blocks_goal),
            soft_blocker_count=sum(1 for b in blockers if not b.blocks_goal),
            actions=actions,
            skips=skips,
            sequencing_rationale=sequencing,
            dofd_gate_active=dofd_gate_active,
            ownership_gate_active=ownership_gate_active,
        )

    # ==========================================================================
    # BLOCKER IDENTIFICATION
    # ==========================================================================

    def _identify_blockers(
        self,
        goal: CreditGoal,
        target: TargetCreditState,
        violations: List[Dict[str, Any]],
        contradictions: List[Dict[str, Any]],
    ) -> List[Blocker]:
        """
        Convert violations and contradictions into Blockers.

        Impact scoring is GOAL-RELATIVE, not severity-relative.
        """
        blockers: List[Blocker] = []

        # Process contradictions (typically high deletability)
        for c in contradictions:
            blocker = self._contradiction_to_blocker(goal, target, c)
            if blocker:
                blockers.append(blocker)

        # Process violations
        for v in violations:
            blocker = self._violation_to_blocker(goal, target, v)
            if blocker:
                blockers.append(blocker)

        # Sort by goal-relative impact (highest first)
        blockers.sort(
            key=lambda b: (
                -b.impact_score,
                -DELETABILITY_WEIGHTS.get(b.deletability, 0.5),
                b.risk_score,
                b.source_id,
            )
        )

        return blockers

    def _contradiction_to_blocker(
        self,
        goal: CreditGoal,
        target: TargetCreditState,
        c: Dict[str, Any],
    ) -> Optional[Blocker]:
        """Convert a contradiction dict to a Blocker."""
        severity = str(c.get("severity", "")).upper()
        rule_code = c.get("rule_code") or c.get("code") or ""
        category = self._infer_category(c)

        # Deletability based on contradiction severity
        if severity == "CRITICAL":
            deletability = "HIGH"
        elif severity == "HIGH":
            deletability = "HIGH"
        else:
            deletability = "MEDIUM"

        # Goal-relative impact
        impact = self._calculate_goal_relative_impact(goal, target, category)

        # Risk assessment (FCRA-native only, NO SOL)
        risk_score, risk_factors = self._assess_risk(c)

        # Check if this blocks the goal
        blocks_goal = self._blocks_goal(goal, target, category, c)

        # DOFD instability flag
        dofd_unstable = rule_code in self.DOFD_GATE_CODES or c.get("dofd_missing", False)

        # Ownership context
        furnisher_type = str(c.get("furnisher_type", "")).upper()
        has_oc = bool(c.get("original_creditor") or c.get("has_original_creditor", True))

        # For cross-bureau discrepancies, extract list of bureaus and their values
        bureaus = []
        values_by_bureau = {}
        if c.get("values_by_bureau"):
            # CrossBureauDiscrepancy format: values_by_bureau is a dict with bureau keys
            raw_values = c.get("values_by_bureau", {})
            bureaus = list(raw_values.keys())
            # Convert values to strings for display
            values_by_bureau = {k: str(v) if v is not None else "Not Reported" for k, v in raw_values.items()}
        elif c.get("bureaus"):
            # Direct bureaus list
            bureaus = list(c.get("bureaus", []))

        return Blocker(
            source_type="CONTRADICTION",
            source_id=str(c.get("id") or c.get("rule_code") or str(uuid4())),
            account_id=c.get("account_id"),
            creditor_name=c.get("creditor_name"),
            account_number_masked=c.get("account_number_masked"),
            bureau=c.get("bureau"),
            bureaus=bureaus,  # All bureaus for cross-bureau items
            values_by_bureau=values_by_bureau,  # Cross-bureau values for display
            title=c.get("description", "")[:100] or f"Contradiction {rule_code}",
            description=c.get("description") or c.get("impact") or "",
            category=category,
            rule_code=rule_code,
            blocks_goal=blocks_goal,
            impact_score=impact,
            deletability=deletability,
            risk_score=risk_score,
            dofd_unstable=dofd_unstable,
            furnisher_type=furnisher_type,
            has_original_creditor=has_oc,
            is_derogatory=True,  # Contradictions are always on derogatory items
            risk_factors=risk_factors,
            proof_hints=list(c.get("proof_hints") or []),
        )

    def _violation_to_blocker(
        self,
        goal: CreditGoal,
        target: TargetCreditState,
        v: Dict[str, Any],
    ) -> Optional[Blocker]:
        """Convert a violation dict to a Blocker."""
        severity = str(v.get("severity", "")).upper()
        violation_type = str(v.get("violation_type", "")).lower()
        category = self._infer_category(v)

        # Deletability based on violation characteristics
        if v.get("is_obsolete_7yr") or v.get("fcra_obsolete"):
            deletability = "HIGH"
        elif v.get("has_math_impossibility") or v.get("has_temporal_impossibility"):
            deletability = "HIGH"
        elif severity == "HIGH":
            deletability = "MEDIUM"
        else:
            deletability = "LOW"

        # Goal-relative impact
        impact = self._calculate_goal_relative_impact(goal, target, category)

        # Risk assessment
        risk_score, risk_factors = self._assess_risk(v)

        # Check if this blocks the goal
        blocks_goal = self._blocks_goal(goal, target, category, v)

        # DOFD instability
        dofd_unstable = v.get("dofd_missing", False) or "dofd" in violation_type

        # Positive tradeline check
        is_positive = v.get("is_positive", False)
        is_derogatory = v.get("is_derogatory", True) or category in (
            self.COLLECTION_CATEGORIES | self.CHARGEOFF_CATEGORIES | self.LATE_CATEGORIES
        )

        # Revolving account check for utilization shock
        is_revolving = v.get("is_revolving", False) or v.get("account_type", "").lower() in {
            "revolving", "credit_card", "heloc"
        }
        credit_limit = v.get("credit_limit")

        # Ownership context
        furnisher_type = str(v.get("furnisher_type", "")).upper()
        has_oc = bool(v.get("original_creditor") or v.get("has_original_creditor", True))

        return Blocker(
            source_type="VIOLATION",
            source_id=str(v.get("violation_id") or v.get("id") or str(uuid4())),
            account_id=v.get("account_id"),
            creditor_name=v.get("creditor_name"),
            account_number_masked=v.get("account_number_masked"),
            bureau=v.get("bureau"),
            title=v.get("description", "")[:100] or f"Violation: {violation_type}",
            description=v.get("description") or "",
            category=category,
            rule_code=None,
            blocks_goal=blocks_goal,
            impact_score=impact,
            deletability=deletability,
            risk_score=risk_score,
            dofd_unstable=dofd_unstable,
            furnisher_type=furnisher_type,
            has_original_creditor=has_oc,
            is_positive=is_positive,
            is_derogatory=is_derogatory,
            is_revolving=is_revolving,
            credit_limit=credit_limit,
            reinsertion_risk=v.get("reinsertion_risk", False),
            risk_factors=risk_factors,
            proof_hints=list(v.get("proof_hints") or []),
        )

    # ==========================================================================
    # DEPENDENCY GATES (Must apply BEFORE scoring)
    # ==========================================================================

    def _apply_dofd_stability_gate(self, blockers: List[Blocker]) -> List[Blocker]:
        """
        GATE A: DOFD Stability

        If ANY blocker has:
        - dofd_missing = True
        - OR rule_code in {"D1", "D2", "D3"}

        THEN:
        - Force DOFD/aging actions to priority 1
        - Suppress balance/status deletions until DOFD resolved

        This prevents attacking balance/status issues when the foundational
        DOFD data is unstable, which could cause re-aging.
        """
        has_dofd_instability = any(
            b.dofd_unstable or b.rule_code in self.DOFD_GATE_CODES
            for b in blockers
        )

        if not has_dofd_instability:
            return blockers

        # Modify gate priorities (using replace since Blocker is mutable)
        result = []
        for b in blockers:
            if b.rule_code in self.DOFD_GATE_CODES or b.dofd_unstable:
                # Promote DOFD blockers - must resolve first
                b.gate_priority = 1
            elif b.category in {"balance", "status", "payment_history"}:
                # Suppress balance/status blockers until DOFD gate clears
                b.gate_priority = 99
            result.append(b)

        return result

    def _apply_ownership_gate(self, blockers: List[Blocker]) -> List[Blocker]:
        """
        GATE B: Ownership / Authority

        If furnisher is:
        - Collection agency
        - Debt buyer
        - Unknown chain-of-title

        THEN:
        - Ownership/authority actions precede deletion posture
        - Cannot demand deletion without establishing who owns the debt

        This ensures we challenge chain-of-title before demanding deletion,
        which is legally stronger and prevents "verified by furnisher" deflection.
        """
        for b in blockers:
            if b.furnisher_type in self.OWNERSHIP_GATE_FURNISHERS:
                if not b.has_original_creditor:
                    b.requires_ownership_first = True
                    # Add to risk factors for transparency
                    if "ownership_unclear" not in b.risk_factors:
                        b.risk_factors.append("ownership_unclear")

        return blockers

    def _apply_ledger_signals(
        self,
        blockers: List[Blocker],
        signals: Dict[str, float],
    ) -> List[Blocker]:
        """
        Apply aggregated ledger signals to adjust blocker risk scores.

        Signals read from CopilotSignalCacheDB:
        - reinsertion_rate: Raise REINSERTION_LIKELY if high
        - dofd_change_rate: Enforce DOFD gate earlier if high
        - verification_spike_rate: Raise TACTICAL_VERIFICATION_RISK if high
        - deletion_durability: Increase deletability confidence if high

        Copilot NEVER writes to the ledger. Signals are inputs only.
        No permanent blocks. No self-modifying rules.
        Deterministic replay always possible.
        """
        # Thresholds for signal effects
        HIGH_REINSERTION_THRESHOLD = 0.3  # 30% reinsertion rate = high risk
        HIGH_VERIFICATION_THRESHOLD = 0.5  # 50% verification rate = spike
        HIGH_DOFD_CHANGE_THRESHOLD = 0.2  # 20% DOFD change rate = concern
        HIGH_DURABILITY_THRESHOLD = 70  # 70+ durability = reliable

        reinsertion_rate = signals.get("reinsertion_rate", 0.0)
        verification_rate = signals.get("verification_spike_rate", 0.0)
        dofd_change_rate = signals.get("dofd_change_rate", 0.0)
        durability = signals.get("deletion_durability", 0.0)

        for b in blockers:
            # High reinsertion rate → increase reinsertion risk
            if reinsertion_rate >= HIGH_REINSERTION_THRESHOLD:
                if not b.reinsertion_risk:
                    b.reinsertion_risk = True
                    b.risk_score = min(5, b.risk_score + 1)
                    if "ledger_reinsertion_signal" not in b.risk_factors:
                        b.risk_factors.append("ledger_reinsertion_signal")

            # High verification spike → increase tactical risk for low deletability
            if verification_rate >= HIGH_VERIFICATION_THRESHOLD:
                if b.deletability == "LOW":
                    b.risk_score = min(5, b.risk_score + 1)
                    if "ledger_verification_spike" not in b.risk_factors:
                        b.risk_factors.append("ledger_verification_spike")

            # High DOFD change rate → enforce DOFD gate more strictly
            if dofd_change_rate >= HIGH_DOFD_CHANGE_THRESHOLD:
                if b.category in {"balance", "status", "payment_history"}:
                    if not b.dofd_unstable:
                        # Don't mark as unstable, but add risk
                        b.risk_score = min(5, b.risk_score + 1)
                        if "ledger_dofd_signal" not in b.risk_factors:
                            b.risk_factors.append("ledger_dofd_signal")

            # High durability → increase confidence in deletability
            if durability >= HIGH_DURABILITY_THRESHOLD:
                if b.deletability == "MEDIUM":
                    # Consider upgrading, but don't directly change
                    # Just reduce risk slightly to favor this action
                    b.risk_score = max(0, b.risk_score - 1)

        return blockers

    # ==========================================================================
    # GOAL-RELATIVE IMPACT SCORING
    # ==========================================================================

    def _calculate_goal_relative_impact(
        self,
        goal: CreditGoal,
        target: TargetCreditState,
        category: str,
    ) -> int:
        """
        Calculate impact score based on how much this blocks the TARGET GOAL.

        Impact = how much this item blocks the target credit state.
        NOT severity-based. NOT dollar-amount based.

        A $200 collection blocks mortgage MORE than a $20k chargeoff blocks apartment.

        Returns: 1-10 impact score
        """
        category_lower = category.lower()

        # ==========================================================================
        # MORTGAGE - Strictest requirements
        # ==========================================================================
        if goal == CreditGoal.MORTGAGE:
            if category_lower in self.COLLECTION_CATEGORIES:
                return 10  # Absolute blocker - zero tolerance
            if category_lower in self.CHARGEOFF_CATEGORIES:
                return 10  # Absolute blocker - zero tolerance
            if category_lower in self.PUBLIC_RECORD_CATEGORIES:
                return 10  # Absolute blocker
            if category_lower in self.LATE_CATEGORIES:
                return 8  # Serious impact
            if category_lower in self.INQUIRY_CATEGORIES:
                return 4  # Moderate impact
            return 5

        # ==========================================================================
        # EMPLOYMENT - Public records are critical
        # ==========================================================================
        elif goal == CreditGoal.EMPLOYMENT:
            if category_lower in self.PUBLIC_RECORD_CATEGORIES:
                return 10  # CRITICAL: Employment cares most about public records
            if category_lower in self.COLLECTION_CATEGORIES:
                return 9  # Collections matter for employment
            if category_lower in self.CHARGEOFF_CATEGORIES:
                return 5  # Less critical for employment
            if category_lower in self.LATE_CATEGORIES:
                return 2  # Lates rarely block employment
            if category_lower in self.INQUIRY_CATEGORIES:
                return 1  # Inquiries don't matter for employment
            return 3

        # ==========================================================================
        # AUTO LOAN - Moderate requirements
        # ==========================================================================
        elif goal == CreditGoal.AUTO_LOAN:
            if category_lower in self.CHARGEOFF_CATEGORIES:
                return 9  # Zero chargeoff tolerance
            if category_lower in self.PUBLIC_RECORD_CATEGORIES:
                return 9  # Zero public records
            if category_lower in self.COLLECTION_CATEGORIES:
                return 6  # One collection allowed
            if category_lower in self.LATE_CATEGORIES:
                return 5  # Two lates allowed
            if category_lower in self.INQUIRY_CATEGORIES:
                return 3  # Multiple inquiries allowed
            return 5

        # ==========================================================================
        # PRIME CREDIT CARD
        # ==========================================================================
        elif goal == CreditGoal.PRIME_CREDIT_CARD:
            if category_lower in self.COLLECTION_CATEGORIES:
                return 10  # Zero tolerance
            if category_lower in self.CHARGEOFF_CATEGORIES:
                return 10  # Zero tolerance
            if category_lower in self.PUBLIC_RECORD_CATEGORIES:
                return 10  # Zero tolerance
            if category_lower in self.LATE_CATEGORIES:
                return 7  # One late allowed
            if category_lower in self.INQUIRY_CATEGORIES:
                return 5  # Some sensitivity
            return 5

        # ==========================================================================
        # APARTMENT RENTAL - More lenient
        # ==========================================================================
        elif goal == CreditGoal.APARTMENT_RENTAL:
            if category_lower in self.COLLECTION_CATEGORIES:
                return 6  # One collection allowed
            if category_lower in self.CHARGEOFF_CATEGORIES:
                return 6  # One chargeoff allowed
            if category_lower in self.PUBLIC_RECORD_CATEGORIES:
                return 7  # One public record allowed
            if category_lower in self.LATE_CATEGORIES:
                return 4  # Multiple lates allowed
            if category_lower in self.INQUIRY_CATEGORIES:
                return 2  # Inquiries rarely matter
            return 4

        # ==========================================================================
        # CREDIT HYGIENE - General cleanup (default)
        # ==========================================================================
        else:  # CREDIT_HYGIENE
            # No hard blockers, so impact is based on general severity
            if category_lower in self.COLLECTION_CATEGORIES:
                return 7
            if category_lower in self.CHARGEOFF_CATEGORIES:
                return 7
            if category_lower in self.PUBLIC_RECORD_CATEGORIES:
                return 8
            if category_lower in self.LATE_CATEGORIES:
                return 5
            if category_lower in self.INQUIRY_CATEGORIES:
                return 4
            return 5

    def _blocks_goal(
        self,
        goal: CreditGoal,
        target: TargetCreditState,
        category: str,
        item: Dict[str, Any],
    ) -> bool:
        """
        Determine if this item is a hard blocker for the goal.

        Hard blockers prevent goal achievement entirely.
        """
        category_lower = category.lower()

        # Collections
        if category_lower in self.COLLECTION_CATEGORIES:
            if target.zero_collection_required:
                return True

        # Chargeoffs
        if category_lower in self.CHARGEOFF_CATEGORIES:
            if target.zero_chargeoff_required:
                return True

        # Public records (CRITICAL for Employment)
        if category_lower in self.PUBLIC_RECORD_CATEGORIES:
            if target.zero_public_records_required:
                return True

        # Recent lates
        if category_lower in self.LATE_CATEGORIES:
            if target.zero_recent_lates_required:
                return True

        # For hygiene goal, only high-severity items are "blockers"
        if goal == CreditGoal.CREDIT_HYGIENE:
            severity = str(item.get("severity", "")).upper()
            return severity in {"CRITICAL", "HIGH"}

        return False

    # ==========================================================================
    # RISK ASSESSMENT (FCRA-NATIVE ONLY, NO SOL)
    # ==========================================================================

    def _assess_risk(self, item: Dict[str, Any]) -> Tuple[int, List[str]]:
        """
        Assess risk factors for attacking this item.

        ONLY FCRA-native risks. NO SOL LOGIC.

        Risk factors:
        - DOFD instability (re-aging risk)
        - Reinsertion likelihood
        - Positive tradeline loss
        - Utilization shock
        - Tactical verification risk

        Returns: (risk_score 0-5, list of risk factor codes)
        """
        risk = 0
        factors: List[str] = []

        # DOFD instability → re-aging risk
        if item.get("dofd_missing") or item.get("dofd_unstable"):
            risk += 2
            factors.append("dofd_instability")

        # Reinsertion risk
        if item.get("reinsertion_risk"):
            risk += 2
            factors.append("reinsertion_likely")

        # Positive tradeline risk
        if item.get("is_positive") and not item.get("is_derogatory"):
            risk += 2
            factors.append("positive_line_loss")

        # Utilization shock (revolving accounts with credit limits)
        if item.get("is_revolving") and item.get("credit_limit", 0) > 0:
            risk += 1
            factors.append("utilization_shock")

        # Ownership unclear (may get "verified by furnisher" deflection)
        furnisher_type = str(item.get("furnisher_type", "")).upper()
        if furnisher_type in self.OWNERSHIP_GATE_FURNISHERS:
            if not item.get("original_creditor") and not item.get("has_original_creditor"):
                risk += 1
                factors.append("ownership_unclear")

        return min(5, risk), factors

    # ==========================================================================
    # SKIP IDENTIFICATION (FCRA-NATIVE ONLY, NO SOL)
    # ==========================================================================

    def _identify_skips(self, blockers: List[Blocker]) -> List[SkipRationale]:
        """
        Identify items that should NOT be attacked.

        ONLY FCRA-native reasons. NO SOL LOGIC.

        Skip codes:
        - DOFD_UNSTABLE: DOFD is missing/unstable, attacking may re-age
        - REINSERTION_LIKELY: High probability item returns after deletion
        - POSITIVE_LINE_LOSS: Attacking removes positive tradeline age/limit
        - UTILIZATION_SHOCK: Deleting revolving line spikes utilization
        - TACTICAL_VERIFICATION_RISK: May force bad outcome, wait for better posture
        """
        skips: List[SkipRationale] = []

        for b in blockers:
            # DOFD instability → skip until stabilized
            # (unless it's the DOFD blocker itself, which should be attacked)
            if b.dofd_unstable and b.rule_code not in self.DOFD_GATE_CODES:
                if b.category in {"balance", "status", "payment_history"}:
                    skips.append(SkipRationale(
                        source_id=b.source_id,
                        account_id=b.account_id,
                        creditor_name=b.creditor_name,
                        code=SkipCode.DOFD_UNSTABLE,
                        rationale="DOFD missing or contradicted; resolve DOFD first to prevent re-aging risk",
                    ))

            # Positive tradeline protection
            if b.is_positive and not b.is_derogatory:
                skips.append(SkipRationale(
                    source_id=b.source_id,
                    account_id=b.account_id,
                    creditor_name=b.creditor_name,
                    code=SkipCode.POSITIVE_LINE_LOSS,
                    rationale="Positive tradeline contributes age/limit; deletion harms credit mix",
                ))

            # Utilization shock (revolving accounts)
            if b.is_revolving and b.credit_limit and b.credit_limit > 0 and not b.is_derogatory:
                skips.append(SkipRationale(
                    source_id=b.source_id,
                    account_id=b.account_id,
                    creditor_name=b.creditor_name,
                    code=SkipCode.UTILIZATION_SHOCK,
                    rationale="Deleting revolving line may spike utilization ratio",
                ))

            # Reinsertion risk
            if b.reinsertion_risk:
                skips.append(SkipRationale(
                    source_id=b.source_id,
                    account_id=b.account_id,
                    creditor_name=b.creditor_name,
                    code=SkipCode.REINSERTION_LIKELY,
                    rationale="High reinsertion probability; defer until stronger multi-bureau proof",
                ))

            # Tactical verification risk (low deletability + ownership unclear)
            if b.deletability == "LOW" and b.requires_ownership_first:
                skips.append(SkipRationale(
                    source_id=b.source_id,
                    account_id=b.account_id,
                    creditor_name=b.creditor_name,
                    code=SkipCode.TACTICAL_VERIFICATION_RISK,
                    rationale="Low deletability with unclear ownership; may force 'verified with updates' outcome",
                ))

        # Deduplicate by source_id (keep first occurrence)
        seen = set()
        unique_skips = []
        for s in skips:
            if s.source_id not in seen:
                seen.add(s.source_id)
                unique_skips.append(s)

        return unique_skips

    # ==========================================================================
    # ATTACK PLAN GENERATION
    # ==========================================================================

    def _generate_attack_plan(
        self,
        goal: CreditGoal,
        target: TargetCreditState,
        blockers: List[Blocker],
        skip_ids: set,
    ) -> List[EnforcementAction]:
        """
        Generate prioritized enforcement actions.

        Priority formula: impact × deletability ÷ (1 + risk)

        Scales:
        - impact: 1-10 (goal-relative)
        - deletability: 0.2/0.6/1.0 (LOW/MEDIUM/HIGH)
        - risk: 0-5

        Gate priorities override the formula:
        - Gate priority 1 = DOFD/ownership actions first
        - Gate priority 99 = suppressed until gate clears
        """
        actions: List[EnforcementAction] = []

        for b in blockers:
            # Skip items in the skip list
            if b.source_id in skip_ids:
                continue

            # Calculate priority score
            d = DELETABILITY_WEIGHTS.get(b.deletability, 0.5)
            risk = max(0, min(5, b.risk_score))
            impact = max(1, min(10, b.impact_score))
            priority = (impact * d) / (1.0 + risk)

            # Determine action type
            action_type, posture = self._determine_action_type(b)

            # Build dependencies
            depends_on = []
            if b.requires_ownership_first and action_type == ActionType.DELETE_DEMAND:
                # This action should depend on an ownership action
                depends_on.append(f"ownership_{b.account_id}")

            actions.append(EnforcementAction(
                action_id=str(uuid4()),
                blocker_source_id=b.source_id,
                account_id=b.account_id,
                creditor_name=b.creditor_name,
                account_number_masked=b.account_number_masked,
                bureau=b.bureau,  # Pass bureau for BatchEngine grouping
                bureaus=b.bureaus,  # For cross-bureau: all involved bureaus
                # Blocker context for rich display
                blocker_title=b.title,
                blocker_description=b.description,
                source_type=b.source_type,
                category=b.category,
                values_by_bureau=b.values_by_bureau,  # Cross-bureau values for display
                # Action specification
                action_type=action_type,
                response_posture=posture,
                priority_score=round(priority, 4),
                impact_score=b.impact_score,
                deletability=b.deletability,
                risk_score=b.risk_score,
                depends_on=depends_on,
                rationale=self._build_action_rationale(goal, b, action_type, posture),
            ))

        # Sort by gate priority first, then by priority score
        actions.sort(
            key=lambda a: (
                self._get_blocker_gate_priority(a.blocker_source_id, blockers),
                -a.priority_score,
                a.action_type.value,
            )
        )

        # Assign sequence order
        for i, action in enumerate(actions):
            action.sequence_order = i + 1

        return actions

    def _determine_action_type(self, b: Blocker) -> Tuple[ActionType, Optional[str]]:
        """
        Determine the appropriate action type for a blocker.

        Respects dependency gates:
        - If DOFD unstable and this is DOFD blocker → DOFD_DEMAND
        - If ownership required → OWNERSHIP_CHAIN_DEMAND first
        - If high deletability → DELETE_DEMAND
        - Otherwise → CORRECT_DEMAND or MOV_DEMAND
        """
        # DOFD-related blockers get DOFD_DEMAND
        if b.rule_code in self.DOFD_GATE_CODES:
            return ActionType.DOFD_DEMAND, "VERIFIED"

        # Ownership unclear → ownership demand first
        if b.requires_ownership_first:
            return ActionType.OWNERSHIP_CHAIN_DEMAND, "VERIFIED"

        # Inquiry blockers
        if b.category in self.INQUIRY_CATEGORIES:
            return ActionType.INQUIRY_DISPUTE, None

        # High deletability contradictions → DELETE_DEMAND
        if b.source_type == "CONTRADICTION" and b.deletability == "HIGH":
            return ActionType.DELETE_DEMAND, "VERIFIED"

        # High deletability violations → DELETE_DEMAND
        if b.deletability == "HIGH":
            return ActionType.DELETE_DEMAND, "VERIFIED"

        # Medium deletability → CORRECT_DEMAND
        if b.deletability == "MEDIUM":
            return ActionType.CORRECT_DEMAND, "VERIFIED"

        # Low deletability → MOV_DEMAND (Method of Verification)
        return ActionType.MOV_DEMAND, "VERIFIED"

    def _get_blocker_gate_priority(self, source_id: str, blockers: List[Blocker]) -> int:
        """Get the gate priority for a blocker by source_id."""
        for b in blockers:
            if b.source_id == source_id:
                return b.gate_priority
        return 50  # Default middle priority

    def _build_action_rationale(
        self,
        goal: CreditGoal,
        b: Blocker,
        action_type: ActionType,
        posture: Optional[str],
    ) -> str:
        """Build explainable rationale for an action."""
        return (
            f"Goal={goal.value}. "
            f"Blocker: {b.title[:50]}. "
            f"Impact={b.impact_score}/10 (goal-relative), "
            f"Deletability={b.deletability}, "
            f"Risk={b.risk_score}/5. "
            f"Action: {action_type.value}"
            + (f" with {posture} posture" if posture else "")
            + f" to resolve goal-blocking condition."
        )

    # ==========================================================================
    # SEQUENCING & SUMMARY
    # ==========================================================================

    def _build_sequencing_rationale(
        self,
        goal: CreditGoal,
        blockers: List[Blocker],
        actions: List[EnforcementAction],
        skips: List[SkipRationale],
    ) -> str:
        """Build explanation of action sequencing."""
        if not actions:
            return "No goal-blocking items met the enforcement threshold. Copilot recommends restraint."

        parts = []

        # Explain gates
        dofd_active = any(b.dofd_unstable or b.rule_code in self.DOFD_GATE_CODES for b in blockers)
        ownership_active = any(b.requires_ownership_first for b in blockers)

        if dofd_active:
            parts.append("DOFD stability gate ACTIVE: DOFD/aging actions prioritized first")
        if ownership_active:
            parts.append("Ownership gate ACTIVE: Chain-of-title actions precede deletions")

        # Explain priority formula
        parts.append("Priority formula: impact(1-10) x deletability(0.2-1.0) / (1 + risk(0-5))")

        # Top action
        if actions:
            top = actions[0]
            parts.append(f"Top action: {top.action_type.value} on {top.creditor_name or 'account'} (priority={top.priority_score:.2f})")

        # Skips
        if skips:
            parts.append(f"{len(skips)} item(s) skipped to protect age/utilization or avoid tactical risks")

        return ". ".join(parts) + "."

    def _build_gap_summary(self, goal: CreditGoal, blockers: List[Blocker]) -> str:
        """Build summary of what's blocking the goal."""
        if not blockers:
            return "No blockers detected. Goal appears achievable."

        hard_blockers = [b for b in blockers if b.blocks_goal]
        if not hard_blockers:
            return f"{len(blockers)} soft issues detected, but no hard blockers for {goal.value}."

        # Count by category
        collections = sum(1 for b in hard_blockers if b.category in self.COLLECTION_CATEGORIES)
        chargeoffs = sum(1 for b in hard_blockers if b.category in self.CHARGEOFF_CATEGORIES)
        public_records = sum(1 for b in hard_blockers if b.category in self.PUBLIC_RECORD_CATEGORIES)
        lates = sum(1 for b in hard_blockers if b.category in self.LATE_CATEGORIES)

        parts = []
        if collections:
            parts.append(f"{collections} collection(s)")
        if chargeoffs:
            parts.append(f"{chargeoffs} chargeoff(s)")
        if public_records:
            parts.append(f"{public_records} public record(s)")
        if lates:
            parts.append(f"{lates} late(s)")

        if parts:
            return f"{', '.join(parts)} blocking {goal.value}"
        return f"{len(hard_blockers)} blocker(s) detected for {goal.value}"

    def _assess_achievability(
        self,
        goal: CreditGoal,
        target: TargetCreditState,
        blockers: List[Blocker],
    ) -> str:
        """
        Assess how achievable the goal is given current blockers.

        Returns: ACHIEVABLE, CHALLENGING, or UNLIKELY
        """
        hard_blockers = [b for b in blockers if b.blocks_goal]

        if not hard_blockers:
            return "ACHIEVABLE"

        # Count high-deletability hard blockers
        deletable_blockers = sum(1 for b in hard_blockers if b.deletability == "HIGH")

        if len(hard_blockers) <= 2 and deletable_blockers == len(hard_blockers):
            return "ACHIEVABLE"
        elif len(hard_blockers) <= 5:
            return "CHALLENGING"
        else:
            return "UNLIKELY"

    # ==========================================================================
    # HELPERS
    # ==========================================================================

    def _infer_category(self, item: Dict[str, Any]) -> str:
        """Infer category from violation/contradiction data."""
        # Try explicit category
        cat = item.get("category") or item.get("type") or ""
        if cat:
            return cat.lower()

        # Infer from violation_type
        vtype = str(item.get("violation_type", "")).lower()
        if "collection" in vtype:
            return "collection"
        if "chargeoff" in vtype or "charge_off" in vtype:
            return "chargeoff"
        if "late" in vtype or "delinquen" in vtype:
            return "late"
        if "inquiry" in vtype:
            return "inquiry"
        if "judgment" in vtype or "lien" in vtype or "bankruptcy" in vtype:
            return "public_record"
        if "dofd" in vtype or "aging" in vtype:
            return "dofd"
        if "balance" in vtype:
            return "balance"
        if "status" in vtype:
            return "status"

        # Default
        return "other"
