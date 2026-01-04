"""
Demand Resolution Engine

Determines the appropriate demand (DELETION vs CORRECTION) based on violation severity.

Demand Resolution Rules:
- ≥1 CRITICAL → DELETION required
- ≥2 HIGH → DELETION required
- Any MEDIUM (no deletion triggers) → CORRECTION + documentation
- LOW only → PROCEDURAL compliance request
- No violations → PROCEDURAL compliance request

Demand Block Templates are HARD-LOCKED - no deviation allowed.
"""

from typing import List, Optional

from app.models.ssot import Violation, Severity
from app.models.letter_object import DemandType, LetterBlock, LetterSection


# =============================================================================
# HARD-LOCKED DEMAND TEMPLATES - NO MODIFICATION ALLOWED
# =============================================================================

DELETION_DEMAND_TEMPLATE = """Because the above information cannot be verified as accurate, this account must be DELETED from all credit reporting.

Documentation of the deletion must be provided in writing."""

CORRECTION_DEMAND_TEMPLATE = """Because the above information contains inaccuracies, this account must be CORRECTED to reflect accurate data.

If corrected, complete documentation substantiating the accuracy of the corrected data must be provided.

If the information cannot be verified as accurate, it must be DELETED pursuant to FCRA § 611(a)(5)(A)."""

PROCEDURAL_DEMAND_TEMPLATE = """This request is submitted to ensure compliance with reporting obligations under the Fair Credit Reporting Act.

Please provide written confirmation of your verification procedures and the source documentation used to substantiate the accuracy of this account.

A response is required within 30 days pursuant to FCRA § 611(a)(1)."""


class DemandResolver:
    """
    Resolves the appropriate demand type based on violation severity.

    Rules are deterministic and non-negotiable:
    - ≥1 CRITICAL → DELETION
    - ≥2 HIGH → DELETION
    - Any MEDIUM (no deletion triggers) → CORRECTION
    - LOW only → PROCEDURAL
    - No violations → PROCEDURAL
    """

    def resolve(self, violations: List[Violation]) -> DemandType:
        """
        Determine demand type from violations.

        Args:
            violations: List of Violation objects

        Returns:
            DemandType indicating required action
        """
        if not violations:
            return DemandType.PROCEDURAL

        # Deterministic enum counting
        critical_count = sum(1 for v in violations if v.severity == Severity.CRITICAL)
        high_count = sum(1 for v in violations if v.severity == Severity.HIGH)
        medium_count = sum(1 for v in violations if v.severity == Severity.MEDIUM)

        # Deletion triggers
        if critical_count >= 1:
            return DemandType.DELETION
        if high_count >= 2:
            return DemandType.DELETION

        # MEDIUM or single HIGH triggers CORRECTION
        if medium_count > 0 or high_count > 0:
            return DemandType.CORRECTION

        # LOW only → PROCEDURAL
        return DemandType.PROCEDURAL

    def get_demand_text(self, demand_type: DemandType) -> str:
        """
        Get the hard-locked demand text for a demand type.

        Args:
            demand_type: The resolved demand type

        Returns:
            Deterministic demand paragraph text
        """
        if demand_type == DemandType.DELETION:
            return DELETION_DEMAND_TEMPLATE
        elif demand_type == DemandType.CORRECTION:
            return CORRECTION_DEMAND_TEMPLATE
        else:
            return PROCEDURAL_DEMAND_TEMPLATE

    def create_demand_block(
        self,
        violations: List[Violation],
        demand_type: Optional[DemandType] = None,
    ) -> LetterBlock:
        """
        Create a demand block for the letter.

        Args:
            violations: List of Violation objects
            demand_type: Optional override; if not provided, resolved from violations

        Returns:
            LetterBlock for the DEMAND section
        """
        if demand_type is None:
            demand_type = self.resolve(violations)

        demand_text = self.get_demand_text(demand_type)

        # Get highest severity from violations for the demand block
        highest_severity = Severity.LOW
        if violations:
            for v in violations:
                if v.severity == Severity.CRITICAL:
                    highest_severity = Severity.CRITICAL
                    break
                elif v.severity == Severity.HIGH and highest_severity != Severity.CRITICAL:
                    highest_severity = Severity.HIGH
                elif v.severity == Severity.MEDIUM and highest_severity not in [Severity.CRITICAL, Severity.HIGH]:
                    highest_severity = Severity.MEDIUM

        # Collect all statutes from violations
        statutes = set()
        for v in violations:
            if v.primary_statute:
                statutes.add(v.primary_statute)
            if v.secondary_statutes:
                statutes.update(v.secondary_statutes)

        # Add FCRA §611 which governs dispute procedures
        statutes.add("15 U.S.C. § 1681i(a)")

        # Deterministic block_id based on demand type
        block_id = f"demand_{demand_type.value.lower()}"

        return LetterBlock(
            block_id=block_id,
            violation_id="demand",  # Demand blocks are not tied to specific violations
            severity=highest_severity,
            section=LetterSection.DEMAND,
            text=demand_text,
            anchors=[],  # Demand blocks don't have CRRG anchors
            statutes=sorted(statutes),
            metro2_field=None,
        )


# =============================================================================
# MODULE-LEVEL SINGLETON
# =============================================================================

_resolver: Optional[DemandResolver] = None


def get_resolver() -> DemandResolver:
    """Get or create the default demand resolver singleton."""
    global _resolver
    if _resolver is None:
        _resolver = DemandResolver()
    return _resolver


def resolve_demand(violations: List[Violation]) -> DemandType:
    """
    Convenience function to resolve demand type.

    Args:
        violations: List of Violation objects

    Returns:
        DemandType indicating required action
    """
    return get_resolver().resolve(violations)


def create_demand_block(violations: List[Violation]) -> LetterBlock:
    """
    Convenience function to create a demand block.

    Args:
        violations: List of Violation objects

    Returns:
        LetterBlock for the DEMAND section
    """
    return get_resolver().create_demand_block(violations)
