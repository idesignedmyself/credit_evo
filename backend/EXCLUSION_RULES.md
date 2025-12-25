# Copilot Exclusion Rules

This document defines which violation types are **NOT disputable** under FCRA and should be automatically excluded from Copilot recommendations.

## Purpose

The Copilot engine filters out certain violation types that:
1. Are informational observations, not FCRA violations
2. Represent expected financial behavior (e.g., interest accruing on loans)
3. Cannot be disputed because they are factually accurate

These exclusions prevent users from wasting time on non-actionable items and keep dispute letters focused on legitimate FCRA violations.

---

## Excluded Violation Types

### 1. `student_loan_capitalized_interest`

**Reason:** Interest and fees on student loans are expected and legally permissible. The FCRA does not require creditors to remove accurate interest/fee reporting.

**When Added:** Originally flagged as `Severity.LOW` (informational) in `backend/app/services/audit/rules.py`.

**Exception:** Only dispute if the balance amount is **factually incorrect** (e.g., wrong total balance), not merely because interest was capitalized.

**Rule Location:** Lines 414-444 in `backend/app/services/audit/rules.py`

---

### 2. `mortgage_balance_review`

**Reason:** Informational balance observations for mortgage accounts are not FCRA violations. Mortgage balances fluctuate with amortization and are expected to change.

**Exception:** Only dispute if the balance is mathematically impossible or contradicts other verified data.

---

## Implementation Details

### Where Exclusions Are Applied

**File:** `backend/app/services/copilot/copilot_engine.py`

```python
# Informational violation types that are NOT FCRA-disputable
INFORMATIONAL_VIOLATION_TYPES = {
    "student_loan_capitalized_interest",
    "mortgage_balance_review",
}
```

The check happens in `_violation_to_blocker()`:
```python
if violation_type in self.INFORMATIONAL_VIOLATION_TYPES:
    return None  # Skip - never becomes a Blocker
```

### Adding New Exclusions

To add a new exclusion:

1. Add the violation type to `INFORMATIONAL_VIOLATION_TYPES` in `copilot_engine.py`
2. Document the reason in this file
3. Ensure the violation is created with `Severity.LOW` in the audit rules

---

## Skip Codes vs. Exclusions

| Type | When Used | Appears in UI |
|------|-----------|---------------|
| **Skip Codes** | FCRA-native tactical skips (e.g., DOFD unstable, reinsertion risk) | Yes - shown in Skip list |
| **Exclusions** | Non-disputable informational items | No - filtered before processing |

Skip codes are for items that *could* be disputed but *shouldn't* be for tactical reasons.
Exclusions are for items that *cannot* be disputed because they're not FCRA violations.

---

## Related Files

- `backend/app/models/copilot_models.py` - SkipCode enum and descriptions
- `backend/app/services/copilot/copilot_engine.py` - INFORMATIONAL_VIOLATION_TYPES
- `backend/app/services/audit/rules.py` - Where violations are created with severity

---

## Change Log

| Date | Change | Author |
|------|--------|--------|
| 2024-12-24 | Initial documentation | Claude |
