# Rule Logic Location Guide

This document maps where all error detection, violation rules, and related logic lives in the codebase.

---

## Overview

The error detection logic is **spread across multiple directories**:

```
app/
├── services/
│   ├── audit/                    # PRIMARY: Violation detection
│   │   ├── rules.py              # Single-account violation rules
│   │   ├── engine.py             # Audit orchestration
│   │   ├── cross_bureau_rules.py # Multi-bureau discrepancy detection
│   │   └── __init__.py           # Exports
│   │
│   ├── parsing/                  # Data extraction
│   │   └── html_parser.py        # DOFD inference, field extraction
│   │
│   └── legal_letter_generator/   # Letter output
│       └── pdf_format_assembler.py # Violation classification for sections
│
└── routers/
    └── letters.py                # Field name mapping helpers
```

---

## File-by-File Breakdown

### 1. `app/services/audit/rules.py` - Main Violation Rules

**Purpose:** Defines all single-account audit rules that detect FCRA/Metro 2 violations.

**What lives here:**
- `AuditRule` class definitions
- Metro 2 field references (Field 8, 10, 15, 25, etc.)
- FCRA section citations (§605, §611, §623, etc.)
- Violation descriptions and severity levels

**Key Rules:**
| Rule | Violation Type | Metro 2 Field |
|------|---------------|---------------|
| Obsolete accounts | `obsolete_account` | Field 25 (DOFD) |
| Stale reporting | `stale_reporting` | Field 8 (Date Reported) |
| Missing DOFD | `missing_dofd` | Field 25 |
| Missing Scheduled Payment | `missing_scheduled_payment` | Field 15 |
| Missing Date Opened | `missing_date_opened` | Field 10 |
| Re-aged DOFD | `reaged_dofd` | Field 25 |
| Charge-off contradictions | Various | Status codes |
| Balance > High Credit | `balance_exceeds_high_credit` | Field 17A |
| Balance > Credit Limit (open accts only) | `balance_exceeds_credit_limit` | Field 17A/21 |
| Negative Credit Limit | `negative_credit_limit` | Field 21 |
| Status/Payment History Mismatch | `status_payment_history_mismatch` | Field 17A/25 (requires explicit derogatory status) |
| Phantom Late Payment | `phantom_late_payment` | Field 15/25 (late markers during $0 due or forbearance) |
| Paid Status with Balance | `paid_status_with_balance` | Field 17A/10 (status=Paid but balance>$0) |
| Zero Balance Not Paid | `zero_balance_not_paid` | Field 17A/10 (collection with $0 but not marked Paid) |

**To add a new rule:** Create a new function in this file following the existing pattern.

---

### 2. `app/services/audit/engine.py` - Audit Engine

**Purpose:** Orchestrates running rules against accounts and collecting violations.

**What lives here:**
- `audit_report()` function - main entry point
- Rule execution loop
- Violation aggregation
- Clean account tracking

**Flow:**
```
NormalizedReport → audit_report() → runs rules.py → AuditResult
```

---

### 3. `app/services/audit/cross_bureau_rules.py` - Cross-Bureau Analysis

**Purpose:** Detects discrepancies when the same account is reported differently across TU/EX/EQ.

**Status:** ✅ **INTEGRATED** - Runs automatically during audit on accounts with 2+ bureaus.

**What lives here:**
- Account fingerprinting/matching logic
- `CrossBureauRules` class with comparison methods
- `audit_cross_bureau()` function (legacy, for separate reports)

**Cross-Bureau Checks:**
| Check | Description | Legal Basis |
|-------|-------------|-------------|
| DOFD mismatch | Different DOFD dates across bureaus | FCRA §623(a)(1) |
| Date Opened mismatch | >30 day difference | FCRA §623(a)(1) |
| Balance mismatch | >10% variance | FCRA §623(a)(1) |
| Status mismatch | Open vs Closed conflicts | FCRA §623(a)(1) |
| Payment history mismatch | Different payment patterns | FCRA §623(a)(1) |
| Past due mismatch | Different amounts | FCRA §623(a)(1) |
| Closed vs Open conflict | One bureau shows closed, another open | FCRA §623(a)(1) |
| Dispute flag mismatch | One bureau shows dispute (XB/XC/XH), another doesn't | FCRA §623(a)(3) |

**How it works:**
- IdentityIQ reports contain all 3 bureaus in one file
- Parser merges bureau data into `Account.bureaus` dict
- During audit, `engine.py` runs cross-bureau checks on accounts with 2+ bureaus
- Discrepancies are stored in `AuditResult.discrepancies`

---

### 4. `app/services/parsing/html_parser.py` - Data Extraction

**Purpose:** Parses IdentityIQ HTML reports and extracts account data.

**What lives here:**
- HTML parsing logic
- **DOFD determination/inference logic**
- Payment history extraction
- Account field normalization

**DOFD Inference Priority:**
1. Explicit DOFD field from report
2. Inferred from payment history (first delinquency marker)
3. Fallback to date_opened (for derogatory accounts)

---

### 5. `app/services/legal_letter_generator/pdf_format_assembler.py` - Letter Assembly

**Purpose:** Assembles violations into formatted dispute letters.

**What lives here:**
- `_classify_violation()` - Routes violations to correct letter sections
- Section grouping (I=Obsolete, II=DOFD, III=Stale, IV=Other)
- PDF formatting logic

**Classification Priority:**
1. Specific field violations (Scheduled Payment, Date Opened) → Section IV
2. Obsolete accounts (>7 years) → Section I
3. Stale reporting (308-2555 days) → Section III
4. Missing DOFD → Section II
5. Everything else → Section IV

---

### 6. `app/routers/letters.py` - Letter API

**Purpose:** API endpoints for letter generation.

**What lives here:**
- `get_missing_field_name()` - Maps violation types to field names
- Letter generation endpoints
- Violation selection handling

**Field Name Mapping:**
| Violation Type | Returns |
|---------------|---------|
| `missing_dofd` | "DOFD" |
| `missing_date_opened` | "Date Opened" |
| `missing_scheduled_payment` | "Scheduled Payment" |

---

## Adding New Violations

### Step 1: Define the rule in `rules.py`
```python
def check_new_violation(account: Account, report_date: date) -> Optional[Violation]:
    # Detection logic here
    if violation_condition:
        return Violation(
            violation_type=ViolationType.NEW_TYPE,
            severity=Severity.HIGH,
            description="...",
            fcra_section="§XXX",
            metro2_field="XX"
        )
    return None
```

### Step 2: Add ViolationType enum (if new)
File: `app/models/__init__.py` or `app/models/ssot.py`

### Step 3: Update classification (if needed)
File: `app/services/legal_letter_generator/pdf_format_assembler.py`
- Add to `_classify_violation()` if special routing needed

### Step 4: Update field mapping (if missing field type)
File: `app/routers/letters.py`
- Add to `get_missing_field_name()` if applicable

---

## Quick Reference

| Task | File |
|------|------|
| Add new violation rule | `app/services/audit/rules.py` |
| Change DOFD inference | `app/services/parsing/html_parser.py` |
| Add cross-bureau check | `app/services/audit/cross_bureau_rules.py` |
| Change letter sections | `app/services/legal_letter_generator/pdf_format_assembler.py` |
| Update field name display | `app/routers/letters.py` |
| Add new ViolationType | `app/models/ssot.py` or `app/models/__init__.py` |

---

## Related Documentation

- `letter_fixes.md` - Recent fixes and Metro 2 field reference
- `system_checklist.md` - Full violation coverage checklist
- `violation_comparison.xlsx` - Comparison with industry standards
