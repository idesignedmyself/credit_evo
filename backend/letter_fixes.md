# Letter Generation Fixes - December 2025

## Issue: Category Mismatch in Section II

### Problem
Section II header was "Missing DOFD (Field 25)" but contained a **Scheduled Payment violation (Field 15)** instead of an actual DOFD violation.

**Example of incorrect output:**
```
II. Accounts Missing Date of First Delinquency (Metro 2 Field 25)
...
• MIDLAND CRED (Account #30058****): Missing Scheduled Payment field (Metro 2 Field 15)
```

This caused confusion because the violation listed did not match the section category.

---

## Root Causes

### 1. Wrong Field Mapping in `letters.py`
**File:** `app/routers/letters.py` (lines 348-357)

The `get_missing_field_name()` function had a critical bug:
```python
# BEFORE (BUG):
if vtype == "missing_dofd":
    return "Scheduled Payment"  # WRONG! This mapped DOFD to Scheduled Payment
```

**Fix:**
```python
# AFTER (CORRECT):
if vtype == "missing_dofd" or vtype == "chargeoff_missing_dofd":
    return "DOFD"  # Metro 2 Field 25 (Date of First Delinquency)
elif vtype == "missing_date_opened":
    return "Date Opened"  # Metro 2 Field 10
elif vtype == "missing_scheduled_payment":
    return "Scheduled Payment"  # Metro 2 Field 15
```

### 2. Missing Early Classification in `pdf_format_assembler.py`
**File:** `app/services/legal_letter_generator/pdf_format_assembler.py` (lines 259-266)

The `_classify_violation()` function didn't have early checks for specific violation types, allowing them to fall through to wrong categories.

**Fix:** Added early classification rules:
```python
# FIRST: Check for specific missing field types - these should NOT be misclassified
# Missing Scheduled Payment goes to OTHER (not DOFD!)
if v_type == "missing_scheduled_payment" or missing_field == "scheduled_payment":
    return ViolationCategory.OTHER

# Missing Date Opened goes to OTHER
if v_type == "missing_date_opened" or missing_field == "date_opened":
    return ViolationCategory.OTHER
```

### 3. NoneType Error on `.lower()` Call
**File:** `app/services/legal_letter_generator/pdf_format_assembler.py` (lines 254-257)

When violation fields contained `None` (not missing, but explicitly `None`), calling `.lower()` caused a crash:
```
Error generating letter: 'NoneType' object has no attribute 'lower'
```

**Before (Bug):**
```python
evidence = violation.get("evidence", "").lower()  # Fails if evidence=None
```

**After (Fix):**
```python
evidence = (violation.get("evidence") or "").lower()  # Handles None correctly
```

---

## Result

After these fixes:
- **DOFD violations** → Section "Accounts Missing Date of First Delinquency"
- **Scheduled Payment violations** → Section "Additional Accounts Requiring Investigation"
- **Date Opened violations** → Section "Additional Accounts Requiring Investigation"
- No more `NoneType` crashes when fields are `None`

Each violation type now routes to its correct category section in the generated letter.

---

## Issue: Wrong Metro 2 Field Number for Scheduled Payment

### Problem
The system was citing **Field 13** for Missing Scheduled Payment violations. Field 13 is actually "Terms Duration" (number of months), not the payment amount.

### Metro 2 Base Segment Field Reference

| Field | Name | Description |
|-------|------|-------------|
| **Field 10** | Date Opened | Date the account was opened |
| **Field 13** | Terms Duration | Number of months the terms are in effect |
| **Field 15** | Scheduled Monthly Payment Amount | The whole dollar amount of the regular monthly payment due |
| **Field 17A** | Account Status | 2-character code indicating current status (e.g., "11" = current) |
| **Field 17B** | Payment Rating | 1-character code for payment status (e.g., '1' = 30 days past due) |
| **Field 25** | Date of First Delinquency (DOFD) | Date when account first became delinquent |
| **Field 8** | Date Reported | Date the information was reported to the bureau |

### Root Cause
**Files affected:**
- `app/services/audit/rules.py` (line 255, 261)
- `app/routers/letters.py` (line 356)
- `app/services/legal_letter_generator/pdf_format_assembler.py` (line 521)

All referenced "Metro 2 Field 13" instead of the correct "Metro 2 Field 15".

### Fix
Changed all instances from Field 13 to Field 15:

**Before (Wrong):**
```python
description=(
    f"This open original creditor account is missing the Scheduled Payment field "
    f"(Metro 2 Field 13)..."
),
metro2_field="13",
```

**After (Correct):**
```python
description=(
    f"This open original creditor account is missing the Scheduled Payment field "
    f"(Metro 2 Field 15)..."
),
metro2_field="15",
```

---

## Letter Section Structure

The legal dispute letter is organized into Roman numeral sections by violation category:

| Section | Category | Metro 2 Field | Description |
|---------|----------|---------------|-------------|
| **I** | Obsolete Accounts | Field 25 (DOFD) | Accounts exceeding 7-year reporting limit per FCRA § 605(a) |
| **II** | Missing DOFD | Field 25 | Derogatory accounts without Date of First Delinquency |
| **III** | Stale Reporting | Field 8 | Accounts not updated in >308 days |
| **IV** | Other Violations | Various | Missing Scheduled Payment (Field 15), Date Opened (Field 10), etc. |

### Classification Logic

Violations are classified in `_classify_violation()` with the following priority:

1. **Specific field violations first** (Scheduled Payment, Date Opened) → Section IV
2. **Obsolete accounts** (>2555 days / 7 years) → Section I
3. **Stale reporting** (308-2555 days) → Section III
4. **Missing DOFD** → Section II
5. **Everything else** → Section IV

This prevents field-specific violations from being misclassified into DOFD or other categories.

---

## Validation Checklist

After re-uploading a report, verify:

- [ ] Section I contains only obsolete accounts (>7 years old)
- [ ] Section II contains only Missing DOFD violations (Field 25)
- [ ] Section III contains only Stale Reporting violations (Field 8)
- [ ] Section IV contains Scheduled Payment (Field 15), Date Opened (Field 10), and other miscellaneous violations
- [ ] No duplicate Field numbers in the same bullet (e.g., "Field 15...Field 13")
- [ ] All Metro 2 field references are correct per the table above

---

## B6 Update: Balance Rule Field Citations & Severity Gating (December 2025)

### Problem
Balance-related violation rules were citing incorrect Metro 2 fields:
- **Field 17A** (Account Status Code) was incorrectly cited for monetary discrepancies
- **Field 15** was incorrectly referenced (doesn't exist for balance)
- Installment loan overages had flat severity regardless of materiality

### Correct Metro 2 Field Reference (CRRG 2024-2025)

| Field # | Name | Purpose |
|---------|------|---------|
| **Field 12** | High Credit / Original Loan Amount | Installment/Student Loans/Mortgages |
| **Field 16** | Credit Limit | Revolving accounts ONLY |
| **Field 17A** | Account Status Code | Status indicator (NEVER monetary) |
| **Field 21** | Current Balance | Current balance owed |

### Field Citation Corrections Made

| Rule | Old Citation | Correct Citation |
|------|--------------|------------------|
| `check_negative_balance` | Field 17A | Field 21 |
| `check_negative_credit_limit` | None | Field 16 |
| `check_balance_exceeds_credit_limit` | Field 17A/21 | Field 21 & Field 16 |
| `check_balance_exceeds_high_credit` | Field 17A | Field 21 & Field 12 |
| `check_status_payment_history_mismatch` | 17A/25 | Field 17A & Field 18 |
| `check_paid_collection_contradiction` | 17A/10 | Field 17A & Field 21 |
| `check_collection_balance_inflation` | 17A vs 15A | Field 21 & Field 12 |

### Installment Loan Threshold-Based Severity Gating

Small overages on installment loans may result from late fees or administrative noise. Material deviations are inconsistent with amortization.

| Overage Condition | Severity | Auto-Dispute |
|-------------------|----------|--------------|
| < 3% OR < $100 | LOW | NO (review only) |
| ≥ 3% AND ≥ $100 | MEDIUM | YES |

**Conservative gating:** MEDIUM requires BOTH thresholds exceeded.

### Account Type Scoping

| Account Type | Balance Comparison | Severity |
|--------------|-------------------|----------|
| Revolving | Balance > Credit Limit | MEDIUM |
| Installment | Balance > High Credit | *Threshold-gated* |
| Student Loan | Balance > High Credit | LOW (capitalized interest) |
| Mortgage | Balance > High Credit | LOW (escrow/neg-am) |
| Collection | Balance > Original Debt | HIGH (FDCPA §1692f) |

### Key Rule: Field 17A (Account Status) is NEVER cited for monetary discrepancies
