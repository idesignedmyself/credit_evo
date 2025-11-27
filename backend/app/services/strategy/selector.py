"""
Credit Engine 2.0 - Strategy Selector

Takes AuditResult (SSOT #2) and creates LetterPlan (SSOT #3).
Determines:
- How to group violations (by type, by creditor, by severity)
- Which tone to use
- The variation seed for stylistic randomness
"""
from __future__ import annotations
import hashlib
import logging
from collections import defaultdict
from typing import Dict, List, Optional

from ...models.ssot import (
    AuditResult, LetterPlan, Violation, Consumer,
    Bureau, Tone, ViolationType
)

logger = logging.getLogger(__name__)


# Bureau addresses for dispute letters
BUREAU_ADDRESSES = {
    Bureau.TRANSUNION: """TransUnion Consumer Solutions
P.O. Box 2000
Chester, PA 19016-2000""",

    Bureau.EXPERIAN: """Experian
P.O. Box 4500
Allen, TX 75013""",

    Bureau.EQUIFAX: """Equifax Information Services LLC
P.O. Box 740256
Atlanta, GA 30374-0256"""
}


class StrategySelector:
    """
    Select the optimal strategy for letter generation.

    Input: AuditResult (SSOT #2)
    Output: LetterPlan (SSOT #3)

    Strategy decisions are made here and ONLY here.
    Renderer cannot override or recompute strategy.
    """

    def __init__(self, grouping_strategy: str = "by_violation_type", tone: Tone = Tone.FORMAL):
        """
        Initialize strategy selector.

        Args:
            grouping_strategy: How to group violations ("by_violation_type", "by_creditor", "by_severity")
            tone: Letter tone to use
        """
        self.grouping_strategy = grouping_strategy
        self.tone = tone

    def create_plan(
        self,
        audit_result: AuditResult,
        consumer: Consumer,
        variation_seed: Optional[int] = None
    ) -> LetterPlan:
        """
        Create a LetterPlan from an AuditResult.

        Args:
            audit_result: AuditResult (SSOT #2) from audit engine
            consumer: Consumer information for the letter
            variation_seed: Seed for stylistic variation (deterministically derived if None)

        Returns:
            LetterPlan (SSOT #3) - immutable plan for rendering
        """
        logger.info(f"Creating letter plan for {len(audit_result.violations)} violations")

        # Generate variation seed DETERMINISTICALLY if not provided
        if variation_seed is None:
            # Derive from report_id hash - ALWAYS deterministic
            variation_seed = int(
                hashlib.sha256(audit_result.report_id.encode("utf-8")).hexdigest(), 16
            ) % (2**32)

        # Group violations based on strategy
        grouped = self._group_violations(audit_result.violations)

        # Build LetterPlan
        plan = LetterPlan(
            bureau=audit_result.bureau,
            consumer=consumer,
            grouped_violations=grouped,
            grouping_strategy=self.grouping_strategy,
            variation_seed=variation_seed,
            tone=self.tone,
            bureau_address=BUREAU_ADDRESSES.get(audit_result.bureau, "")
        )

        logger.info(f"Created plan with {len(grouped)} violation groups, seed={variation_seed}")
        return plan

    def _group_violations(self, violations: List[Violation]) -> Dict[str, List[Violation]]:
        """Group violations based on the selected strategy."""
        if self.grouping_strategy == "by_violation_type":
            return self._group_by_type(violations)
        elif self.grouping_strategy == "by_creditor":
            return self._group_by_creditor(violations)
        elif self.grouping_strategy == "by_severity":
            return self._group_by_severity(violations)
        else:
            return self._group_by_type(violations)

    def _group_by_type(self, violations: List[Violation]) -> Dict[str, List[Violation]]:
        """Group violations by violation type."""
        groups: Dict[str, List[Violation]] = defaultdict(list)

        for v in violations:
            key = v.violation_type.value
            groups[key].append(v)

        return dict(groups)

    def _group_by_creditor(self, violations: List[Violation]) -> Dict[str, List[Violation]]:
        """Group violations by creditor name."""
        groups: Dict[str, List[Violation]] = defaultdict(list)

        for v in violations:
            key = v.creditor_name or "Unknown"
            groups[key].append(v)

        return dict(groups)

    def _group_by_severity(self, violations: List[Violation]) -> Dict[str, List[Violation]]:
        """Group violations by severity (HIGH first, then MEDIUM, then LOW)."""
        groups: Dict[str, List[Violation]] = defaultdict(list)

        for v in violations:
            key = v.severity.value
            groups[key].append(v)

        return dict(groups)


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

def create_letter_plan(
    audit_result: AuditResult,
    consumer: Consumer,
    grouping_strategy: str = "by_violation_type",
    tone: Tone = Tone.FORMAL,
    variation_seed: int = None
) -> LetterPlan:
    """
    Factory function to create a LetterPlan.

    Args:
        audit_result: AuditResult (SSOT #2)
        consumer: Consumer information
        grouping_strategy: How to group violations
        tone: Letter tone
        variation_seed: Seed for variation (auto-generated if None)

    Returns:
        LetterPlan (SSOT #3)
    """
    selector = StrategySelector(grouping_strategy=grouping_strategy, tone=tone)
    return selector.create_plan(audit_result, consumer, variation_seed)
