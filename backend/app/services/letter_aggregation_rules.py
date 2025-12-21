"""
FCRA Enforcement Letter Aggregation Rules Engine
=================================================
Deterministic logic for grouping violations into coherent enforcement letters.

Design Principle: Legal coherence over convenience.
Each output letter must be defensible as a standalone enforcement action.
"""

from enum import Enum
from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict


# =============================================================================
# RESPONSE OUTCOME TAXONOMY
# =============================================================================

class ResponseOutcome(str, Enum):
    """
    Response outcomes are legally distinct enforcement postures.
    They MUST NOT be mixed in a single letter.
    """
    NO_RESPONSE = "NO_RESPONSE"        # §611(a)(1) deadline breach - procedural
    VERIFIED = "VERIFIED"              # §611(a)(5)(A) substantive challenge
    REJECTED = "REJECTED"              # §611(a)(3) frivolous determination attack
    REINSERTION = "REINSERTION"        # §611(a)(5)(B)(ii) notice violation
    INVESTIGATING = "INVESTIGATING"    # Stall tactic - procedural pressure
    UPDATED = "UPDATED"                # Partial cure - residual violations only


# =============================================================================
# STATUTE COMPATIBILITY MATRIX
# =============================================================================

class StatuteFamily(str, Enum):
    """Statute families that may coexist in one letter."""
    FCRA_PROCEDURAL = "FCRA_PROCEDURAL"      # §611(a)(1), §611(a)(3)
    FCRA_SUBSTANTIVE = "FCRA_SUBSTANTIVE"    # §611(a)(5), §611(a)(6), §611(a)(7)
    FCRA_REINSERTION = "FCRA_REINSERTION"    # §611(a)(5)(B)
    FCRA_ACCURACY = "FCRA_ACCURACY"          # §623(a)(1), §623(b)
    FDCPA = "FDCPA"                          # §1692 et seq.
    STATE = "STATE"                          # State-specific statutes


# Statutes that CAN appear together in one letter
COMPATIBLE_STATUTE_FAMILIES: Dict[StatuteFamily, Set[StatuteFamily]] = {
    StatuteFamily.FCRA_PROCEDURAL: {
        StatuteFamily.FCRA_PROCEDURAL,
    },
    StatuteFamily.FCRA_SUBSTANTIVE: {
        StatuteFamily.FCRA_SUBSTANTIVE,
        StatuteFamily.FCRA_ACCURACY,  # Furnisher accuracy ties to CRA verification
    },
    StatuteFamily.FCRA_REINSERTION: {
        StatuteFamily.FCRA_REINSERTION,
        # Reinsertion is standalone - requires its own notice
    },
    StatuteFamily.FCRA_ACCURACY: {
        StatuteFamily.FCRA_ACCURACY,
        StatuteFamily.FCRA_SUBSTANTIVE,
    },
    StatuteFamily.FDCPA: {
        StatuteFamily.FDCPA,
        # FDCPA violations should NOT mix with FCRA in same letter
    },
    StatuteFamily.STATE: {
        StatuteFamily.STATE,
        # State claims can supplement federal but get separate treatment
    },
}


# Map USC citations to statute families
STATUTE_TO_FAMILY: Dict[str, StatuteFamily] = {
    # FCRA Procedural
    "15 USC 1681i(a)(1)": StatuteFamily.FCRA_PROCEDURAL,
    "15 USC 1681i(a)(1)(A)": StatuteFamily.FCRA_PROCEDURAL,
    "15 USC 1681i(a)(3)": StatuteFamily.FCRA_PROCEDURAL,
    "15 USC 1681i(a)(3)(A)": StatuteFamily.FCRA_PROCEDURAL,

    # FCRA Substantive
    "15 USC 1681i(a)(5)": StatuteFamily.FCRA_SUBSTANTIVE,
    "15 USC 1681i(a)(5)(A)": StatuteFamily.FCRA_SUBSTANTIVE,
    "15 USC 1681i(a)(6)": StatuteFamily.FCRA_SUBSTANTIVE,
    "15 USC 1681i(a)(6)(B)(iii)": StatuteFamily.FCRA_SUBSTANTIVE,
    "15 USC 1681i(a)(7)": StatuteFamily.FCRA_SUBSTANTIVE,
    "15 USC 1681e(b)": StatuteFamily.FCRA_SUBSTANTIVE,

    # FCRA Reinsertion
    "15 USC 1681i(a)(5)(B)": StatuteFamily.FCRA_REINSERTION,
    "15 USC 1681i(a)(5)(B)(ii)": StatuteFamily.FCRA_REINSERTION,

    # FCRA Accuracy (Furnisher)
    "15 USC 1681s-2(a)(1)": StatuteFamily.FCRA_ACCURACY,
    "15 USC 1681s-2(a)(1)(A)": StatuteFamily.FCRA_ACCURACY,
    "15 USC 1681s-2(b)": StatuteFamily.FCRA_ACCURACY,
    "15 USC 1681s-2(b)(1)": StatuteFamily.FCRA_ACCURACY,

    # FDCPA
    "15 USC 1692e": StatuteFamily.FDCPA,
    "15 USC 1692e(2)": StatuteFamily.FDCPA,
    "15 USC 1692e(8)": StatuteFamily.FDCPA,
    "15 USC 1692f": StatuteFamily.FDCPA,
    "15 USC 1692g": StatuteFamily.FDCPA,
    "15 USC 1692g(b)": StatuteFamily.FDCPA,
}


# =============================================================================
# VIOLATION DATA STRUCTURE
# =============================================================================

@dataclass
class Violation:
    """Input violation ready for aggregation analysis."""
    violation_id: str
    entity: str                              # e.g., "TransUnion LLC"
    response_outcome: ResponseOutcome
    statute_set: Set[str]                    # USC citations
    demanded_actions: Set[str]               # e.g., {"DELETE", "PROVIDE_MOV"}
    timeline_context: str                    # e.g., "2024-Q4-DISPUTE-001"
    account_identifier: Optional[str] = None # For grouping related accounts
    severity: str = "MEDIUM"                 # HIGH, MEDIUM, LOW


@dataclass
class AggregationGroup:
    """Output: A coherent group of violations for one letter."""
    group_id: str
    entity: str
    response_outcome: ResponseOutcome
    statute_family: StatuteFamily
    violations: List[Violation] = field(default_factory=list)

    @property
    def violation_ids(self) -> List[str]:
        return [v.violation_id for v in self.violations]

    @property
    def combined_statutes(self) -> Set[str]:
        result = set()
        for v in self.violations:
            result.update(v.statute_set)
        return result

    @property
    def combined_demands(self) -> Set[str]:
        result = set()
        for v in self.violations:
            result.update(v.demanded_actions)
        return result


# =============================================================================
# AGGREGATION RULES - CONDITIONS WHERE AGGREGATION IS ALLOWED
# =============================================================================

AGGREGATION_ALLOWED_CONDITIONS = """
AGGREGATION IS PERMITTED when ALL of the following are TRUE:

1. SAME ENTITY
   - All violations target the identical legal entity
   - Entity name must match exactly (case-insensitive)
   - Example: "TransUnion LLC" != "Trans Union" (no aggregation)

2. SAME RESPONSE OUTCOME
   - All violations share identical response_outcome value
   - NO_RESPONSE violations group together
   - VERIFIED violations group together
   - Never mix outcomes in same letter

3. COMPATIBLE STATUTE FAMILIES
   - All statutes must belong to compatible families per COMPATIBLE_STATUTE_FAMILIES
   - FCRA procedural violations may aggregate
   - FCRA substantive violations may aggregate
   - FCRA + FDCPA MUST NOT aggregate (different regulatory frameworks)

4. SAME TIMELINE CONTEXT
   - Violations must arise from the same dispute cycle
   - Reinsertion violations are ALWAYS separate (different timeline)
   - Stale violations (>90 days) should not aggregate with fresh violations

5. NON-CONFLICTING DEMANDED ACTIONS
   - Demanded actions must not contradict
   - DELETE + VERIFY = conflict (cannot demand both)
   - DELETE + PROVIDE_MOV = allowed (both apply pressure)
"""


# =============================================================================
# AGGREGATION RULES - CONDITIONS WHERE AGGREGATION IS PROHIBITED
# =============================================================================

AGGREGATION_PROHIBITED_CONDITIONS = """
AGGREGATION IS PROHIBITED when ANY of the following are TRUE:

1. DIFFERENT ENTITIES
   - Each entity receives its own letter(s)
   - Never address multiple entities in one letter
   - ABSOLUTE RULE - no exceptions

2. DIFFERENT RESPONSE OUTCOMES
   - NO_RESPONSE = procedural breach (deadline violation)
   - VERIFIED = substantive challenge (accuracy dispute)
   - REJECTED = procedural attack (frivolous determination)
   - REINSERTION = statutory notice violation
   - Each requires distinct legal framing
   - ABSOLUTE RULE - no exceptions

3. INCOMPATIBLE STATUTES
   - FCRA violations cannot mix with FDCPA violations
   - Reinsertion violations (§611(a)(5)(B)) are always standalone
   - State law claims get separate treatment

4. CONFLICTING DEMANDS
   - Cannot demand DELETE and VERIFY in same letter
   - Cannot demand CEASE_COLLECTION and VALIDATE_DEBT simultaneously
   - Conflicting demands weaken enforcement posture

5. TIMELINE DISCONTINUITY
   - Original dispute violations vs. reinsertion violations
   - Fresh violations (<30 days) vs. stale violations (>90 days)
   - Each dispute cycle is a separate enforcement action

6. SEVERITY MISMATCH (OPTIONAL SEPARATION)
   - HIGH severity violations MAY be separated for emphasis
   - Willful noncompliance should not be diluted by negligent violations
"""


# =============================================================================
# AGGREGATION ALGORITHM
# =============================================================================

def get_statute_family(statute: str) -> StatuteFamily:
    """Map a statute citation to its family."""
    # Exact match first
    if statute in STATUTE_TO_FAMILY:
        return STATUTE_TO_FAMILY[statute]

    # Partial match (e.g., "15 USC 1681i(a)(1)(A)" matches "15 USC 1681i(a)(1)")
    for known_statute, family in STATUTE_TO_FAMILY.items():
        if statute.startswith(known_statute.rsplit("(", 1)[0]):
            return family

    # Default to substantive for unknown FCRA
    if "1681" in statute:
        return StatuteFamily.FCRA_SUBSTANTIVE
    if "1692" in statute:
        return StatuteFamily.FDCPA

    return StatuteFamily.STATE


def get_primary_statute_family(statutes: Set[str]) -> StatuteFamily:
    """Determine primary statute family from a set of statutes."""
    families = {get_statute_family(s) for s in statutes}

    # Priority order for primary family
    priority = [
        StatuteFamily.FCRA_REINSERTION,  # Always standalone
        StatuteFamily.FDCPA,              # Separate from FCRA
        StatuteFamily.FCRA_PROCEDURAL,
        StatuteFamily.FCRA_SUBSTANTIVE,
        StatuteFamily.FCRA_ACCURACY,
        StatuteFamily.STATE,
    ]

    for family in priority:
        if family in families:
            return family

    return StatuteFamily.FCRA_SUBSTANTIVE


def are_statutes_compatible(statutes_a: Set[str], statutes_b: Set[str]) -> bool:
    """Check if two statute sets can coexist in one letter."""
    family_a = get_primary_statute_family(statutes_a)
    family_b = get_primary_statute_family(statutes_b)

    if family_a == family_b:
        return True

    compatible_with_a = COMPATIBLE_STATUTE_FAMILIES.get(family_a, set())
    return family_b in compatible_with_a


def are_demands_compatible(demands_a: Set[str], demands_b: Set[str]) -> bool:
    """Check if demanded actions are non-conflicting."""
    # Define conflicting demand pairs
    conflicts = [
        ({"DELETE"}, {"VERIFY", "REVERIFY"}),
        ({"CEASE_COLLECTION"}, {"VALIDATE_DEBT"}),
        ({"REMOVE_FROM_REPORT"}, {"UPDATE_BALANCE"}),
    ]

    combined = demands_a | demands_b

    for conflict_a, conflict_b in conflicts:
        if (combined & conflict_a) and (combined & conflict_b):
            return False

    return True


def compute_aggregation_key(violation: Violation) -> Tuple[str, str, str, str]:
    """
    Generate a grouping key for a violation.
    Violations with identical keys MAY be aggregated (pending compatibility checks).
    """
    entity_normalized = violation.entity.lower().strip()
    outcome = violation.response_outcome.value
    statute_family = get_primary_statute_family(violation.statute_set).value
    timeline = violation.timeline_context

    return (entity_normalized, outcome, statute_family, timeline)


def aggregate_violations(violations: List[Violation]) -> List[AggregationGroup]:
    """
    MAIN ALGORITHM: Group violations into coherent enforcement letter groups.

    Input: List of enforcement-ready violations
    Output: List of aggregation groups (each becomes one letter)

    Algorithm:
    1. Group by (entity, response_outcome, statute_family, timeline)
    2. Within each group, verify pairwise compatibility
    3. Split incompatible violations into separate groups
    4. Return final groups
    """
    if not violations:
        return []

    # Step 1: Initial grouping by key
    initial_groups: Dict[Tuple, List[Violation]] = defaultdict(list)

    for violation in violations:
        key = compute_aggregation_key(violation)
        initial_groups[key].append(violation)

    # Step 2: Validate and finalize groups
    final_groups: List[AggregationGroup] = []
    group_counter = 0

    for key, group_violations in initial_groups.items():
        entity_normalized, outcome, statute_family, timeline = key

        # For single-violation groups, no compatibility check needed
        if len(group_violations) == 1:
            v = group_violations[0]
            group_counter += 1
            final_groups.append(AggregationGroup(
                group_id=f"AG-{group_counter:04d}",
                entity=v.entity,
                response_outcome=v.response_outcome,
                statute_family=StatuteFamily(statute_family),
                violations=[v],
            ))
            continue

        # For multi-violation groups, verify pairwise compatibility
        compatible_subgroups = _split_incompatible(group_violations)

        for subgroup in compatible_subgroups:
            if subgroup:
                group_counter += 1
                final_groups.append(AggregationGroup(
                    group_id=f"AG-{group_counter:04d}",
                    entity=subgroup[0].entity,
                    response_outcome=subgroup[0].response_outcome,
                    statute_family=StatuteFamily(statute_family),
                    violations=subgroup,
                ))

    return final_groups


def _split_incompatible(violations: List[Violation]) -> List[List[Violation]]:
    """
    Split a list of violations into compatible subgroups.
    Uses greedy algorithm: add to first compatible group, else create new.
    """
    subgroups: List[List[Violation]] = []

    for violation in violations:
        placed = False

        for subgroup in subgroups:
            # Check compatibility with all existing members
            compatible = True
            for existing in subgroup:
                if not are_statutes_compatible(violation.statute_set, existing.statute_set):
                    compatible = False
                    break
                if not are_demands_compatible(violation.demanded_actions, existing.demanded_actions):
                    compatible = False
                    break

            if compatible:
                subgroup.append(violation)
                placed = True
                break

        if not placed:
            subgroups.append([violation])

    return subgroups


# =============================================================================
# VALIDATION AND EXAMPLES
# =============================================================================

def validate_aggregation_group(group: AggregationGroup) -> Tuple[bool, List[str]]:
    """
    Validate that an aggregation group is legally coherent.
    Returns (is_valid, list_of_issues).
    """
    issues = []

    # Rule 1: All violations must target same entity
    entities = {v.entity.lower().strip() for v in group.violations}
    if len(entities) > 1:
        issues.append(f"FATAL: Multiple entities in group: {entities}")

    # Rule 2: All violations must share response outcome
    outcomes = {v.response_outcome for v in group.violations}
    if len(outcomes) > 1:
        issues.append(f"FATAL: Mixed response outcomes: {outcomes}")

    # Rule 3: Statute compatibility
    for i, v1 in enumerate(group.violations):
        for v2 in group.violations[i+1:]:
            if not are_statutes_compatible(v1.statute_set, v2.statute_set):
                issues.append(
                    f"FATAL: Incompatible statutes between {v1.violation_id} and {v2.violation_id}"
                )

    # Rule 4: Demand compatibility
    for i, v1 in enumerate(group.violations):
        for v2 in group.violations[i+1:]:
            if not are_demands_compatible(v1.demanded_actions, v2.demanded_actions):
                issues.append(
                    f"FATAL: Conflicting demands between {v1.violation_id} and {v2.violation_id}"
                )

    return len(issues) == 0, issues


# =============================================================================
# EXPLICIT EXAMPLES
# =============================================================================

VALID_AGGREGATION_EXAMPLE = """
VALID AGGREGATION EXAMPLE:
--------------------------
Violation A:
  - entity: "TransUnion LLC"
  - response_outcome: NO_RESPONSE
  - statute_set: {"15 USC 1681i(a)(1)(A)"}
  - demanded_actions: {"DELETE", "PROVIDE_MOV"}
  - timeline_context: "2024-Q4-DISPUTE-001"

Violation B:
  - entity: "TransUnion LLC"
  - response_outcome: NO_RESPONSE
  - statute_set: {"15 USC 1681i(a)(1)(A)", "15 USC 1681i(a)(3)"}
  - demanded_actions: {"DELETE"}
  - timeline_context: "2024-Q4-DISPUTE-001"

RESULT: AGGREGATE INTO ONE LETTER
Reason: Same entity, same outcome (NO_RESPONSE), compatible statutes (both FCRA procedural),
        non-conflicting demands, same dispute timeline.
"""

INVALID_AGGREGATION_EXAMPLE = """
INVALID AGGREGATION EXAMPLE:
----------------------------
Violation A:
  - entity: "TransUnion LLC"
  - response_outcome: NO_RESPONSE
  - statute_set: {"15 USC 1681i(a)(1)(A)"}
  - demanded_actions: {"DELETE"}
  - timeline_context: "2024-Q4-DISPUTE-001"

Violation B:
  - entity: "TransUnion LLC"
  - response_outcome: VERIFIED
  - statute_set: {"15 USC 1681i(a)(5)(A)"}
  - demanded_actions: {"PROVIDE_MOV", "DELETE"}
  - timeline_context: "2024-Q4-DISPUTE-001"

RESULT: SEPARATE LETTERS REQUIRED
Reason: Different response outcomes (NO_RESPONSE vs VERIFIED).
        NO_RESPONSE is a procedural deadline breach - entity failed to respond.
        VERIFIED is a substantive accuracy challenge - entity responded but verified inaccurate data.
        These require entirely different legal arguments and cannot be coherently combined.
"""

WHY_MIXED_OUTCOMES_PROHIBITED = """
Mixed response outcomes MUST NOT be aggregated because each outcome represents a
fundamentally different enforcement posture: NO_RESPONSE attacks procedural compliance
(the entity failed to act within statutory deadlines), while VERIFIED attacks
substantive accuracy (the entity acted but reached the wrong conclusion) — combining
them in one letter creates logical contradiction and weakens both arguments.
"""


# =============================================================================
# CONVENIENCE FUNCTION FOR ROUTER INTEGRATION
# =============================================================================

def compute_letter_groups(violations_data: List[Dict]) -> List[Dict]:
    """
    Convenience wrapper for API integration.

    Input: List of violation dictionaries from the disputes system
    Output: List of group dictionaries ready for letter generation
    """
    # Convert dicts to Violation objects
    violations = []
    for v in violations_data:
        violations.append(Violation(
            violation_id=v.get("violation_id", ""),
            entity=v.get("entity", ""),
            response_outcome=ResponseOutcome(v.get("response_outcome", "NO_RESPONSE")),
            statute_set=set(v.get("statute_set", [])),
            demanded_actions=set(v.get("demanded_actions", [])),
            timeline_context=v.get("timeline_context", ""),
            account_identifier=v.get("account_identifier"),
            severity=v.get("severity", "MEDIUM"),
        ))

    # Compute groups
    groups = aggregate_violations(violations)

    # Convert back to dicts
    result = []
    for group in groups:
        is_valid, issues = validate_aggregation_group(group)
        result.append({
            "group_id": group.group_id,
            "entity": group.entity,
            "response_outcome": group.response_outcome.value,
            "statute_family": group.statute_family.value,
            "violation_ids": group.violation_ids,
            "combined_statutes": list(group.combined_statutes),
            "combined_demands": list(group.combined_demands),
            "violation_count": len(group.violations),
            "is_valid": is_valid,
            "validation_issues": issues,
        })

    return result
