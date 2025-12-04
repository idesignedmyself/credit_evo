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
