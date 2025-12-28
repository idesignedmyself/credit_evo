# Tier 2 — Supervisory Enforcement

**Status:** SHIPPED
**Tests:** 21/21 passing
**Scope:** Locked

Tier 2 adds examiner-standard enforcement to the system.

## Overview

Tier 2 evaluates whether entity responses (VERIFIED, NO_RESPONSE) meet supervisory examination standards. When standards are not met, the system creates **response-layer violations** that compound the original data-layer violations.

This is distinct from Tier 1 (contradiction detection) which identifies data errors. Tier 2 evaluates the **quality of the entity's response** to those contradictions.

## Capabilities Delivered

- Response-layer violations created for VERIFIED / NO_RESPONSE failures
- Deterministic examiner checks (no NLP, no heuristics)
- Severity promotion based on examiner failure
- Examiner-driven escalation (replacing attempt-count logic)
- Automatic letter posture upgrade
- Immutable ledger capture of examiner failures
- **Tier-2 Canonical Letter Templates** for all response types

## Examiner Triggers Implemented

### 1. PERFUNCTORY_INVESTIGATION
```
IF response == VERIFIED
AND contradiction_previously_detected == TRUE
AND contradiction_still_present == TRUE
AND evidence_was_sent == TRUE
THEN FAIL
```
**Statute:** FCRA § 611(a)(1)(A), § 1681n

### 2. NOTICE_OF_RESULTS_FAILURE
```
IF response == NO_RESPONSE
AND statutory_deadline_passed == TRUE
THEN FAIL
```
**Statute:** FCRA § 611(a)(6)(A)

### 3. SYSTEMIC_ACCURACY_FAILURE
```
IF same contradiction exists on same tradeline
AND appears across ≥2 bureaus
AND within same dispute cycle
THEN FAIL
```
**Statute:** FCRA § 607(b)

*Note: No time-window analytics. No cross-user aggregation. Same dispute cycle only.*

### 4. UDAAP_MISLEADING_VERIFICATION
```
IF response == VERIFIED
AND contradiction.severity == CRITICAL
AND contradiction.is_logical_impossibility == TRUE
AND evidence_was_sent == TRUE
THEN FAIL
```
**Statute:** FCRA § 611(a)(1)(A)

**Logical Impossibility Rules:** T1, T2, T3, T4, M1, M2 (temporal/mathematical impossibilities)

## Architecture

```
Entity Response (VERIFIED / NO_RESPONSE)
         ↓
┌─────────────────────────────────────────┐
│         EXAMINER CHECK SERVICE          │
│                                         │
│  1. Check perfunctory investigation     │
│  2. Check notice of results failure     │
│  3. Check systemic accuracy failure     │
│  4. Check misleading verification       │
│                                         │
│  Output: ExaminerCheckResult            │
│    - passed: bool                       │
│    - standard_result: enum              │
│    - response_layer_violation: dict     │
│    - escalation_eligible: bool          │
└─────────────────────────────────────────┘
         ↓
Response Evaluator → Execution Ledger → State Machine
```

## Files Modified

| File | Change |
|------|--------|
| `models/ssot.py` | Added 4 ViolationType enum values |
| `services/enforcement/examiner_check.py` | **NEW** - Core Tier 2 module |
| `services/legal_letter_generator/violation_statutes.py` | Added statute mappings |
| `models/db_models.py` | Extended ExecutionResponseDB with examiner fields |
| `services/enforcement/execution_ledger.py` | Updated emit_execution_response() |
| `services/enforcement/response_evaluator.py` | Integrated ExaminerCheckService |
| `services/enforcement/dispute_service.py` | Passes contradictions to evaluator |
| `services/enforcement/state_machine.py` | Added examiner_failure_escalation() |
| `services/enforcement/response_letter_generator.py` | Tier-2 canonical templates for all 4 response types |
| `migrations/add_tier2_examiner_fields.py` | Database migration |
| `tests/test_examiner_enforcement.py` | 21 regression tests |

## Escalation Mapping

| Examiner Result | Target State |
|-----------------|--------------|
| FAIL_SYSTEMIC | SUBSTANTIVE_ENFORCEMENT |
| FAIL_MISLEADING | SUBSTANTIVE_ENFORCEMENT |
| FAIL_PERFUNCTORY | NON_COMPLIANT |
| FAIL_NO_RESULTS | NON_COMPLIANT |

## Letter Selection Upgrades

| Examiner Result | Primary Remedy |
|-----------------|----------------|
| FAIL_SYSTEMIC | IMMEDIATE_DELETION |
| FAIL_MISLEADING | IMMEDIATE_DELETION |
| FAIL_PERFUNCTORY | CORRECTION_WITH_DOCUMENTATION |
| FAIL_NO_RESULTS | CORRECTION_WITH_DOCUMENTATION |

## Tier-2 Canonical Letter Templates

All response letters have been upgraded to Tier-2 canonical structure.

### Core Principle: Fact-First, Not Statute-First

Tier-2 letters prove that compliance was **procedurally impossible**, not just inadequate. This frames issues as examiner failures rather than consumer disagreements.

### Subject Line Change

| Before (Pre-Tier-2) | After (Tier-2) |
|---------------------|----------------|
| STATUTORY VIOLATION | STATUTORY NON-COMPLIANCE |

### Key Section: BASIS FOR NON-COMPLIANCE

Every Tier-2 letter includes a `BASIS FOR NON-COMPLIANCE` section that proves **why** compliance was impossible:

| Response Type | Procedural Impossibility |
|---------------|-------------------------|
| VERIFIED | "Verification was impossible" (missing data, logical impossibility) |
| REJECTED | "Frivolous determination could not legally exist" (missing required disclosures) |
| NO_RESPONSE | "Compliance became procedurally impossible" (deadline elapsed) |
| REINSERTION | "Lawful reinsertion could not have occurred" (missing certification/notice) |

### Canonical Section Order

All Tier-2 letters follow this structure:

1. Header
2. Subject: "STATUTORY NON-COMPLIANCE" + specific type
3. Opening (fact-focused)
4. **ESTABLISHED FACTS** (bullet points)
5. **DISPUTED ITEM** or **REINSERTED ITEM** (clean format)
6. **BASIS FOR NON-COMPLIANCE** (procedural impossibility)
7. STATUTORY FRAMEWORK
8. STATUTORY NON-COMPLIANCE (summary)
9. DEMANDED ACTIONS (no redundant timeframes)
10. RIGHTS PRESERVATION
11. RESPONSE REQUIRED + signature

### Letter Types Implemented

| Letter Type | Function | Statute |
|-------------|----------|---------|
| VERIFIED | `generate_verified_response_letter()` | § 1681i(a)(1)(A) |
| REJECTED (Frivolous) | `generate_rejected_response_letter()` | § 1681i(a)(3)(B) |
| NO_RESPONSE | `generate_no_response_letter()` | § 1681i(a)(1)(A), § 1681i(a)(6)(A) |
| REINSERTION | `generate_reinsertion_response_letter()` | § 1681i(a)(5)(B) |

### Helper Functions

| Function | Purpose |
|----------|---------|
| `format_violation_display()` | Preserves acronyms (DOFD, DLA, FCRA, etc.) |
| `get_basis_for_non_compliance()` | Returns violation-specific basis text |
| `canonicalize_entity_name()` | Converts to legal names (TransUnion LLC, etc.) |

### Acronyms Preserved

```python
PRESERVE_ACRONYMS = {"dofd", "dla", "fcra", "fdcpa", "ecoa", "ssn", "oc", "au", "ncap", "udaap"}
```

### Example Output (VERIFIED)

```
RE: FORMAL NOTICE OF STATUTORY NON-COMPLIANCE

Verification Without Reasonable Investigation

...

BASIS FOR NON-COMPLIANCE
==================================================

The disputed account is missing the Date of First Delinquency (DOFD),
a mandatory compliance field required for the lawful reporting of
delinquent accounts.

An account missing a required compliance field cannot be verified as
accurate, as the absence of DOFD prevents confirmation of:
- Lawful aging of the account
- Compliance with reporting period limitations
- Accuracy and integrity controls required under the FCRA

Verification of an account lacking mandatory compliance data is
logically and procedurally impossible.
```

## Constraints

- **No UI changes** - Backend only
- **No NLP** - No response text parsing
- **No cross-user aggregation** - Single user scope only
- **No time-window analytics** - Same dispute cycle only
- **No probability modeling** - Deterministic logic only
- **Tier 1 unchanged** - All existing violation detection preserved
- **Tier 3+ deferred** - No advanced behavioral patterns

## Database Schema

Added to `execution_responses` table:

```sql
examiner_standard_result VARCHAR(50)    -- PASS, FAIL_PERFUNCTORY, etc.
examiner_failure_reason TEXT            -- Human-readable explanation
response_layer_violation_id VARCHAR(36) -- UUID of created violation
escalation_basis VARCHAR(100)           -- What triggered escalation
```

## Testing

```bash
source venv/bin/activate && python -m pytest tests/test_examiner_enforcement.py -v
```

All 21 tests cover:
- 4 examiner trigger conditions
- 4 statute mappings
- Letter selection upgrades
- Tier 1 behavior unchanged
- Escalation trigger methods

---

**This tier is sufficient for monetization.**

Tier 1 behavior unchanged.
Tier 3+ explicitly deferred.
