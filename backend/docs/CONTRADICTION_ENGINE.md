# Phase-1 Deterministic Contradiction Engine

## Overview

The Contradiction Engine detects **PROVABLE FACTUAL IMPOSSIBILITIES** in tradeline data. Unlike compliance violations that argue "you should have done X," contradictions prove "this data CANNOT BE TRUE."

This engine runs **BEFORE** statute selection or letter generation. Output feeds dispute letters, verification rebuttals, and enforcement escalation.

**Goal:** Force deletion by proving data cannot be true, not merely noncompliant.

---

## How It Works

### Location
`backend/app/services/audit/contradiction_engine.py`

### Core Components

```python
from app.services.audit.contradiction_engine import detect_contradictions

# Analyze an account
contradictions = detect_contradictions(account_data)

# Returns List[Contradiction] sorted by severity (CRITICAL → HIGH → MEDIUM)
```

### Contradiction Object Schema

```python
@dataclass
class Contradiction:
    type: str              # e.g., "temporal_impossibility"
    rule_code: str         # e.g., "T1", "D2", "M1"
    violation_type: ViolationType
    severity: Severity     # CRITICAL, HIGH, MEDIUM

    bureau_claim: str      # What the bureau reports
    contradiction: str     # Why it's impossible
    description: str       # Human-readable explanation
    impact: str            # Why it matters

    supports_deletion: bool = True
    evidence: Dict[str, Any] = {}  # Data for downstream processing

    # Account reference
    account_id: Optional[str]
    creditor_name: Optional[str]
    account_number_masked: Optional[str]
```

---

## Detection Rules

### Temporal Impossibilities (CRITICAL) — T-Series

| Rule | Name | Condition | Example |
|------|------|-----------|---------|
| **T1** | Open Date vs DOFD | `open_date > dofd` | Opened 01/2023, DOFD 06/2022 |
| **T2** | Payment History vs Age | `payment_history_months > account_age` | 24 months history, account 6 months old |
| **T3** | Chargeoff Before Payment | `chargeoff_date < last_payment_date` | Charged off 03/2023, paid 06/2023 |
| **T4** | Delinquency Ladder | Jumped stages (0→60, skipping 30) | Current → 90 days late in one month |

**Why CRITICAL:** These are mathematically impossible timelines. An account cannot become delinquent before it exists.

---

### DOFD / Aging Violations (HIGH) — D-Series

| Rule | Name | Condition | Example |
|------|------|-----------|---------|
| **D1** | Missing DOFD | Negative status + no DOFD | Collection account, DOFD blank |
| **D2** | DOFD vs Inferred | Reported DOFD ≠ first late payment | DOFD 06/2023, first late 02/2023 |
| **D3** | Over 7 Years | `report_date - dofd > 7 years` | DOFD 2016, still reporting 2024 |

**Why HIGH:** DOFD controls the 7-year reporting window. Incorrect DOFD = extended damage.

---

### Mathematical Impossibilities (HIGH) — M-Series

| Rule | Name | Condition | Example |
|------|------|-----------|---------|
| **M1** | Balance Exceeds Max | `balance > principal × (1 + APR)^years × 1.20` | $1K original → $50K in 2 years |
| **M2** | Balance After Chargeoff | Balance increased post-chargeoff by >10% | Chargeoff $5K, now $8K |

**Why HIGH:** Balances cannot grow faster than compound interest allows. Post-chargeoff increases suggest fabricated amounts.

---

### Status/Field Contradictions (MEDIUM) — S-Series

| Rule | Name | Condition | Example |
|------|------|-----------|---------|
| **S1** | Paid with Delinquencies | Status "Paid" + late payments in history | Paid account shows 30/60 day lates |
| **S2** | Closed with Activity | Activity date > close date | Closed 01/2023, activity 06/2023 |

**Why MEDIUM:** Contradictory but potentially explainable. Still strong deletion arguments.

---

### Phase-2.1 Additional Contradictions (MEDIUM)

| Rule | Name | Condition | Example |
|------|------|-----------|---------|
| **X1** | Stale Data | `status_date - last_activity > 60 days` | Activity 01/2023, status updated 06/2023 |
| **K1** | Missing OC Elevated | Collection/debt buyer + no original creditor | Midland Credit reports without OC |
| **P1** | Missing Scheduled Payment | `scheduled_payment > 0` + blank history | $250/mo scheduled, no payment history |

**X1 Stale Data:**
- Triggers when status updates occur without corresponding activity
- Indicates data not reflecting current account conditions
- Impact: Perpetuates inaccurate information

**K1 Missing Original Creditor Elevated:**
- Elevates from "required field" to contradiction for collection accounts
- Chain-of-title ambiguity undermines accuracy
- Impact: Consumer cannot verify debt origin or ownership

**P1 Missing Scheduled Payment:**
- Active account with scheduled payment must have payment history
- Incomplete data cannot be confirmed accurate
- Only triggers for active (not closed/paid) accounts

---

## Decision Flow

```
┌─────────────────────────────────────────────────────────────┐
│                     ACCOUNT DATA                            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              TEMPORAL CHECKS (T1-T4)                        │
│  • Open Date vs DOFD                                        │
│  • Payment History vs Age                                   │
│  • Chargeoff Before Payment                                 │
│  • Delinquency Ladder                                       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              DOFD/AGING CHECKS (D1-D3)                      │
│  • Missing DOFD with negative status                        │
│  • DOFD vs Inferred first late                              │
│  • Over 7-year reporting                                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              MATHEMATICAL CHECKS (M1-M2)                    │
│  • Balance exceeds legal maximum                            │
│  • Balance increase after chargeoff                         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              STATUS/FIELD CHECKS (S1-S2)                    │
│  • Paid status with delinquencies                           │
│  • Closed account with activity                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│         SORT BY SEVERITY (CRITICAL → HIGH → MEDIUM)         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  List[Contradiction]                        │
└─────────────────────────────────────────────────────────────┘
```

---

## Input Data Requirements

The engine accepts a dictionary with these fields:

### Required for Temporal Checks
| Field | Type | Example |
|-------|------|---------|
| `open_date` or `date_opened` | str/date | "2023-01-15" |
| `dofd` or `date_of_first_delinquency` | str/date | "2022-06-01" |
| `chargeoff_date` | str/date | "2023-03-01" |
| `last_payment_date` or `date_last_payment` | str/date | "2023-06-15" |
| `payment_history` | List[Dict] | `[{"status": "C", "month": 1, "year": 2023}]` |
| `payment_history_months` | int | 24 |

### Required for Balance Checks
| Field | Type | Example |
|-------|------|---------|
| `reported_balance` or `balance` | float | 5000.00 |
| `original_balance` or `high_credit` | float | 1000.00 |
| `chargeoff_balance` | float | 5000.00 |
| `interest_cap` | float | 0.08 (default 8% APR) |

### Required for Status Checks
| Field | Type | Example |
|-------|------|---------|
| `status` | str | "Collection", "Chargeoff", "Paid" |
| `account_status` | AccountStatus | AccountStatus.COLLECTION |
| `date_closed` or `closed_date` | str/date | "2023-01-15" |
| `date_last_activity` or `last_activity_date` | str/date | "2023-06-01" |

### Account Identifiers
| Field | Type | Example |
|-------|------|---------|
| `account_id` | str | "VERIZON-123" |
| `creditor_name` | str | "Verizon Wireless" |
| `account_number_masked` | str | "****5678" |
| `report_date` | str/date | "2025-12-21" (defaults to today) |

---

## Usage Examples

### Basic Detection

```python
from app.services.audit.contradiction_engine import detect_contradictions

account = {
    "account_id": "ACC-001",
    "creditor_name": "Example Bank",
    "open_date": "2023-01-15",
    "dofd": "2022-06-01",  # Before open date = T1 violation
    "status": "Collection",
}

contradictions = detect_contradictions(account)

for c in contradictions:
    print(f"[{c.severity}] {c.rule_code}: {c.description}")
    print(f"  Bureau claims: {c.bureau_claim}")
    print(f"  But: {c.contradiction}")
```

### Integration with Existing Audit

```python
from app.services.audit.contradiction_engine import ContradictionEngine

engine = ContradictionEngine()

# Run on all accounts in an audit
for account in audit_result.accounts:
    contradictions = engine.detect_contradictions(account.dict())

    if contradictions:
        # Add to violations list
        for c in contradictions:
            violations.append({
                "violation_type": c.violation_type,
                "severity": c.severity,
                "description": c.description,
                "evidence": c.evidence,
            })
```

### Filtering by Severity

```python
contradictions = detect_contradictions(account)

critical_only = [c for c in contradictions if c.severity == Severity.CRITICAL]
high_and_above = [c for c in contradictions if c.severity in [Severity.CRITICAL, Severity.HIGH]]
```

---

## ViolationType Enum Values

The following enum values were added to `ssot.py` for contradiction detection:

```python
# Phase-1 Deterministic Contradictions
# Temporal Impossibilities (CRITICAL) - T-series
PAYMENT_HISTORY_EXCEEDS_ACCOUNT_AGE = "payment_history_exceeds_account_age"
CHARGEOFF_BEFORE_LAST_PAYMENT = "chargeoff_before_last_payment"
DELINQUENCY_LADDER_INVERSION = "delinquency_ladder_inversion"

# DOFD/Aging Contradictions (HIGH) - D-series
DOFD_INFERRED_MISMATCH = "dofd_inferred_mismatch"

# Mathematical Impossibilities (HIGH) - M-series
BALANCE_EXCEEDS_LEGAL_MAX = "balance_exceeds_legal_max"
BALANCE_INCREASE_AFTER_CHARGEOFF = "balance_increase_after_chargeoff"

# Status/Field Contradictions (MEDIUM) - S-series
PAID_STATUS_WITH_DELINQUENCIES = "paid_status_with_delinquencies"
CLOSED_ACCOUNT_POST_ACTIVITY = "closed_account_post_activity"
```

**Note:** Some rules reuse existing ViolationType values:
- T1 uses `DOFD_AFTER_DATE_OPENED`
- D1 uses `CHARGEOFF_MISSING_DOFD`
- D3 uses `OBSOLETE_ACCOUNT`

### Phase-2.1 ViolationType Enum Values

```python
# Phase-2.1 Additional Contradictions
STALE_DATA = "stale_data"  # X1
MISSING_ORIGINAL_CREDITOR_ELEVATED = "missing_original_creditor_elevated"  # K1
MISSING_SCHEDULED_PAYMENT_CONTRADICTION = "missing_scheduled_payment_contradiction"  # P1
```

---

## Phase 2: Response Letter Integration

Phase 2 integrates contradiction findings into response letter generation. VERIFIED and REJECTED/FRIVOLOUS letters now lead with factual contradictions before statutory analysis.

### Affected Response Types

| Response Type | Contradiction Support | Behavior |
|--------------|----------------------|----------|
| **VERIFIED** | Yes | Inserts PROVABLE FACTUAL INACCURACIES section after header |
| **REJECTED** | Yes | Inserts PROVABLE FACTUAL INACCURACIES section after header |
| **NO_RESPONSE** | No | Unchanged (procedural letter) |
| **REINSERTION** | No | Unchanged (procedural letter) |
| **DELETED** | No | Unchanged |

### Letter Structure with Contradictions

When contradictions are present, letters follow this structure:

```
[HEADER]
[SUBJECT LINE]
[PROVABLE FACTUAL INACCURACIES]   ← New section
[OPENING PARAGRAPH]
[STATUTORY FRAMEWORK]              ← Updated to reference contradictions
[STATUTORY VIOLATION]
[TIMELINE]
[DEMANDED ACTIONS]
[RIGHTS PRESERVATION]
[CLOSING]
```

### Usage

```python
from app.services.enforcement.response_letter_generator import generate_verified_response_letter
from app.services.audit.contradiction_engine import detect_contradictions

# Detect contradictions for the account
account_data = {...}  # Account fields
contradictions = detect_contradictions(account_data)

# Generate letter with contradictions
letter = generate_verified_response_letter(
    consumer={"name": "John Doe", "address": "123 Main St"},
    entity_type="CRA",
    entity_name="TransUnion",
    original_violations=[...],
    dispute_date=dispute_date,
    response_date=response_date,
    contradictions=contradictions,  # Pass contradictions here
)
```

### Sample Output

When contradictions exist, the letter includes:

```
PROVABLE FACTUAL INACCURACIES
==================================================

The following data elements reported by the furnisher are factually
impossible and cannot be verified because they are demonstrably false:

1. [CRITICAL] Account opened AFTER the reported date of first delinquency.
   An account cannot become delinquent before it exists.
   • Reported: Account opened 01/2023
   • Actual: First delinquency reported as 06/2022
   • Impact: Account appears artificially younger, potentially extending the
     7-year negative reporting window and misrepresenting account history.

These inaccuracies are not matters of interpretation or opinion. They
represent mathematical or temporal impossibilities that cannot be verified
through any reasonable investigation because they are objectively false.
```

### Guards

- Contradictions never block letter generation
- Empty contradictions list = section omitted entirely
- Falls back to standard letter structure when no contradictions

---

## Phase 3: Deterministic Demand Prioritization

Phase 3 determines the **primary remedy** (DELETE vs CORRECT vs DOCUMENT) based on contradiction severity and orders the Demanded Actions section accordingly.

### Remedy Determination Rules

| Condition | Primary Remedy |
|-----------|---------------|
| Any CRITICAL contradiction | IMMEDIATE_DELETION |
| 2+ HIGH contradictions | IMMEDIATE_DELETION |
| 1 HIGH or any MEDIUM | CORRECTION_WITH_DOCUMENTATION |
| No contradictions | STANDARD_PROCEDURAL |

### Usage

```python
from app.services.enforcement.response_letter_generator import (
    determine_primary_remedy,
    generate_demanded_actions,
    PrimaryRemedy,
)

# Determine remedy from contradictions
remedy = determine_primary_remedy(contradictions)

# Generate ordered demands
actions = generate_demanded_actions(remedy, "TransUnion LLC", "VERIFIED")
```

### Demanded Actions by Remedy

**IMMEDIATE_DELETION:**
1. IMMEDIATE DELETION of disputed tradeline(s)
2. Written confirmation of deletion within 5 business days
3. Notification to parties who received reports in preceding 6 months
4. Disclosure of verification method (VERIFIED) / Withdrawal of frivolous determination (REJECTED)

**CORRECTION_WITH_DOCUMENTATION:**
1. Immediate correction with supporting documentation
2. Production of all documents relied upon
3. Identification of furnisher(s) contacted
4. Method disclosure / Investigation results

**STANDARD_PROCEDURAL:**
- Falls back to standard statutory demands (no contradiction-based prioritization)

### Integration

- Only affects VERIFIED and REJECTED letters
- NO_RESPONSE and REINSERTION remain unchanged
- Remedy determination is deterministic and auditable

---

## Testing

Run the test suite:

```bash
cd backend
python3 test_contradiction_engine.py
```

Expected output:
```
============================================================
PHASE-1 CONTRADICTION ENGINE TEST SUITE
============================================================
  TOTAL: 13/13 tests passed
============================================================

============================================================
PHASE-2.1 ADDITIONAL CONTRADICTION RULES
============================================================
  TOTAL: 5/5 tests passed
============================================================

============================================================
PHASE-3: DETERMINISTIC DEMAND PRIORITIZATION
============================================================
  [PASS] CRITICAL → IMMEDIATE_DELETION
  [PASS] 2+ HIGH → IMMEDIATE_DELETION
  [PASS] 1 HIGH → CORRECTION
  [PASS] MEDIUM → CORRECTION
  [PASS] No contradictions → STANDARD
  [PASS] VERIFIED letter deletion demand
  [PASS] REJECTED letter correction demand
  TOTAL: 7/7 tests passed
============================================================

============================================================
PHASE 2: CONTRADICTION-FIRST LETTER INTEGRATION TESTS
============================================================
  TOTAL: 4/4 tests passed
============================================================

GRAND TOTAL: 29/29 tests passed
```

---

## Troubleshooting

### False Positive (Contradiction detected on valid data)
**Symptom:** Engine flags a contradiction that's actually valid
**Common Causes:**
- Date parsing issue (check format: YYYY-MM-DD, MM/DD/YYYY)
- Missing field causing fallback to defaults
- Legitimate exception not accounted for

**Fix:** Check `evidence` dict on the contradiction for actual parsed values.

### False Negative (Contradiction not detected)
**Symptom:** Known impossible data not flagged
**Common Causes:**
- Field name mismatch (e.g., `date_opened` vs `open_date`)
- Data type issue (string vs date)
- Value is None/missing

**Fix:** Ensure account dict uses supported field names.

### Severity Order Wrong
**Symptom:** MEDIUM contradictions appearing before CRITICAL
**Cause:** Custom sorting applied after `detect_contradictions()`
**Fix:** Don't re-sort the returned list; it's pre-sorted.

---

## Future Improvements (Phase-2+)

### Cross-Account Detection
- Same DOFD across multiple collectors
- Duplicate accounts with conflicting data
- Balance discrepancies across bureaus

### Advanced Temporal Analysis
- Payment history gap detection
- Impossible date sequences
- Retroactive status changes

### Integration Points
- Automatic letter generation for CRITICAL contradictions
- Escalation to attorney review for multiple contradictions
- Batch processing for multi-bureau analysis

---

## Related Documentation

- `ssot.py` — ViolationType enum definitions
- `rules.py` — Compliance rule detection (separate from contradictions)
- `RESPONSE_LETTER_GENERATOR.md` — How letters use contradiction data
- `LETTER_AUDITOR.md` — Letter quality validation
