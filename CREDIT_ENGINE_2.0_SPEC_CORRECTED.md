# Credit Engine 2.0 — Corrected Unified Specification

**Version:** 2.0.1 (Post-Sweep Correction)
**Status:** Implementation-Ready

---

## Overview

Credit Engine 2.0 is a deterministic, Metro-2-aware credit auditing engine that:
- Parses credit reports from multiple formats
- Normalizes bureau-specific data into a unified schema
- Detects single-bureau and cross-bureau reporting violations
- Classifies furnisher types for correct rule application
- Generates template-resistant, human-sounding dispute letters

**Zero LLMs** are used in auditing. LLMs may *only* be used for optional stylistic enhancement during rendering.

---

## Single Source of Truth (SSOT) Architecture

### Core Principle
Each SSOT is **immutable** once created. Downstream modules MUST NOT mutate, recompute, or reinterpret upstream SSOTs.

### SSOT Chain

```
RawReport
    ↓ [Parsing Layer]
NormalizedReport (SSOT #1)
    ↓ [Audit Engine]
AuditResult (SSOT #2)
    ↓ [Strategy Selector]
LetterPlan (SSOT #3)
    ↓ [Renderer]
DisputeLetter (SSOT #4)
```

### SSOT Definitions

| SSOT | Name | Source | Consumers | Immutability |
|------|------|--------|-----------|--------------|
| #1 | NormalizedReport | Parsing Layer | Audit Engine | After parse completion |
| #2 | AuditResult | Audit Engine | Strategy Selector, Client UI | After audit completion |
| #3 | LetterPlan | Strategy Selector | Renderer | After plan creation |
| #4 | DisputeLetter | Renderer | Client/Output | Final output |

### SSOT #5: VariationSeed
- **Source:** Client request OR deterministic derivation from report_id
- **Usage:** Controls ALL stylistic randomness in rendering
- **Requirement:** MUST be provided or deterministically derived. Never use `random.randint()` without seed.

### SSOT #6: Phrasebanks
- `VariantPool` - Violation-specific phrasing
- `StructureTemplates` - Letter skeletons
- `TransitionBank` - Connective phrases
- `FCRAReferences` - Legal citation variants

---

## 1. Parsing Layer

### Supported Formats (Required Implementation)

| Format | Parser | Priority |
|--------|--------|----------|
| IdentityIQ HTML | `IdentityIQHTMLParser` | ✅ Implemented |
| Annual Credit Report HTML | `ACRHTMLParser` | P1 |
| Bureau PDF (TU/EX/EQ) | `PDFParser` | P2 |
| MISMO XML | `MISMOXMLParser` | P3 |
| JSON Export | `JSONParser` | P3 |

### NormalizedReport Schema (CORRECTED)

```python
@dataclass
class NormalizedReport:
    report_id: str
    consumer: Consumer
    report_date: date
    source_format: str  # NEW: Track source format

    # Per-Bureau Data (CORRECTED)
    bureau_reports: Dict[Bureau, BureauReport]  # NEW: Separate by bureau

    # OR single bureau if single-bureau source
    bureau: Optional[Bureau]  # Only set for single-bureau reports
    accounts: List[Account]   # Only used for single-bureau reports

    inquiries: List[Inquiry]
    public_records: List[PublicRecord]

    parse_timestamp: datetime
    source_file: str
```

### Account Schema (CORRECTED)

```python
@dataclass
class Account:
    account_id: str
    bureau: Bureau  # NEW: Required - which bureau reported this

    # Identification
    creditor_name: str
    original_creditor: Optional[str]
    account_number: str
    account_number_masked: str

    # Classification (SSOT - Final once set)
    furnisher_type: FurnisherType
    account_status: AccountStatus

    # Key Dates (ALL must be extracted)
    date_opened: Optional[date]
    date_closed: Optional[date]
    date_of_first_delinquency: Optional[date]  # CRITICAL: Must extract
    date_last_activity: Optional[date]
    date_last_payment: Optional[date]
    date_reported: Optional[date]

    # Metro-2 Balance Fields
    current_balance: Optional[float]      # Field 17A
    past_due_amount: Optional[float]      # Field 17B
    credit_limit: Optional[float]
    high_credit: Optional[float]
    scheduled_payment: Optional[float]
    monthly_payment: Optional[float]

    # Status Codes
    payment_status: Optional[str]         # Metro-2 payment rating
    account_status_code: Optional[str]    # Metro-2 account status code
    payment_pattern: Optional[str]        # 24-month history
    account_type: Optional[str]

    # Do not use downstream
    raw_data: Dict[str, Any]
```

### Furnisher Classification Logic (SSOT)

```python
def classify_furnisher_type(account_data) -> FurnisherType:
    """
    Classification hierarchy (in order):
    1. Has original_creditor field → COLLECTOR
    2. Account type contains "collection" keywords → COLLECTOR
    3. Status contains "charge off" keywords → OC_CHARGEOFF
    4. Default → OC_NON_CHARGEOFF
    """
```

**This classification is FINAL. No downstream module may reclassify.**

---

## 2. Audit Engine

### Rule Categories

#### 2.1 Single-Bureau Rules

| Rule ID | Rule Name | ViolationType | Severity | Implementation |
|---------|-----------|---------------|----------|----------------|
| SB-001 | Missing DOFD | `MISSING_DOFD` | HIGH | Derogatory accounts without DOFD |
| SB-002 | Missing Date Opened | `MISSING_DATE_OPENED` | MEDIUM | Any account without date_opened |
| SB-003 | Missing Date Last Payment | `MISSING_DLA` | MEDIUM | **NEW: Must implement** |
| SB-004 | Missing Payment Status | `MISSING_PAYMENT_STATUS` | LOW | **NEW: Must implement** |
| SB-005 | Missing Scheduled Payment | `MISSING_SCHEDULED_PAYMENT` | LOW | OC non-charge-off only |
| SB-006 | Negative Balance | `NEGATIVE_BALANCE` | HIGH | balance < 0 |
| SB-007 | Past Due > Balance | `PAST_DUE_EXCEEDS_BALANCE` | MEDIUM | 17B > 17A |
| SB-008 | Future Date | `FUTURE_DATE` | HIGH | Any date > today |
| SB-009 | DOFD Before Date Opened | `DOFD_AFTER_DATE_OPENED` | HIGH | DOFD < date_opened |
| SB-010 | Invalid Metro-2 Code | `INVALID_METRO2_CODE` | MEDIUM | **NEW: Must implement** |

#### 2.2 Furnisher-Type Rules

| Rule ID | Furnisher Type | Condition | Action | ViolationType |
|---------|---------------|-----------|--------|---------------|
| FT-001 | COLLECTOR | 17A = full balance, 17B = 0 | DO NOT FLAG | (Correct behavior) |
| FT-002 | COLLECTOR | 17A ≠ balance OR 17B > 0 | FLAG | `COLLECTOR_BALANCE_ERROR` (NEW) |
| FT-003 | COLLECTOR | Missing original_creditor | FLAG | `MISSING_ORIGINAL_CREDITOR` (NEW) |
| FT-004 | OC_CHARGEOFF | 17A = full balance, 17B = 0 | DO NOT FLAG | (Follows collector rules) |
| FT-005 | OC_CHARGEOFF | Missing DOFD | FLAG | `MISSING_DOFD` |
| FT-006 | OC_NON_CHARGEOFF (Closed) | 17A > 0 | FLAG | `CLOSED_OC_REPORTING_BALANCE` |
| FT-007 | OC_NON_CHARGEOFF (Closed) | 17B > 0 | FLAG | `CLOSED_OC_REPORTING_PAST_DUE` (NEW) |

**Critical Rule Matrix:**

| Furnisher Type | 17A Expected | 17B Expected | Flag If Violated |
|---------------|--------------|--------------|------------------|
| Collector | Full balance | $0 | No (unless wrong) |
| OC Charge-off | Full balance | $0 | No (unless wrong) |
| OC Non-Charge-off (Closed) | $0 | $0 | YES |
| OC Non-Charge-off (Open) | Current balance | Past due | Context-dependent |

#### 2.3 Cross-Bureau Rules (MUST IMPLEMENT)

| Rule ID | Rule Name | ViolationType | Detection Logic |
|---------|-----------|---------------|-----------------|
| CB-001 | DOFD Mismatch | `DOFD_MISMATCH` | Same account, different DOFD across bureaus |
| CB-002 | Date Opened Mismatch | `DATE_OPENED_MISMATCH` | >30 day variance |
| CB-003 | Balance Mismatch | `BALANCE_MISMATCH` | >10% variance (same reporting period) |
| CB-004 | Status Mismatch | `STATUS_MISMATCH` | Open vs Closed conflict |
| CB-005 | Payment History Mismatch | `PAYMENT_HISTORY_MISMATCH` | Different payment patterns |
| CB-006 | Past Due Mismatch | `PAST_DUE_MISMATCH` | Significant variance |
| CB-007 | Closed vs Open Conflict | `CLOSED_VS_OPEN_CONFLICT` | One bureau shows closed, another open |
| CB-008 | Creditor Name Mismatch | `CREDITOR_NAME_MISMATCH` | Material name differences |
| CB-009 | Account Number Mismatch | `ACCOUNT_NUMBER_MISMATCH` | Different account numbers |

**Account Matching for Cross-Bureau:**
```python
def create_account_fingerprint(account: Account) -> str:
    """
    Create fingerprint for matching accounts across bureaus.
    Uses: creditor_name (normalized) + last 4 of account number + date_opened (month/year)
    """
```

#### 2.4 Temporal Rules

| Rule ID | Rule Name | ViolationType | Detection Logic |
|---------|-----------|---------------|-----------------|
| TR-001 | Obsolete Account | `OBSOLETE_ACCOUNT` | DOFD + 7 years < today |
| TR-002 | Stale Reporting | `STALE_REPORTING` | date_reported + 90 days < today |
| TR-003 | Re-aging Detected | `RE_AGING` | **NEW:** DOFD moved forward without new delinquency |
| TR-004 | DOFD Replaced | `DOFD_REPLACED_WITH_DATE_OPENED` | **NEW:** DOFD = date_opened (common violation) |
| TR-005 | Impossible Timeline | `IMPOSSIBLE_TIMELINE` | date_closed < date_opened, etc. |

### AuditResult Schema

```python
@dataclass
class AuditResult:
    audit_id: str
    report_id: str
    bureau: Bureau

    violations: List[Violation]
    discrepancies: List[CrossBureauDiscrepancy]
    clean_accounts: List[str]

    audit_timestamp: datetime
    total_accounts_audited: int
    total_violations_found: int

    # NEW: Audit metadata
    rules_executed: List[str]
    audit_duration_ms: int
```

### Violation Schema (CORRECTED)

```python
@dataclass
class Violation:
    violation_id: str
    violation_type: ViolationType
    severity: Severity

    # Account reference
    account_id: str
    creditor_name: str
    account_number_masked: str
    furnisher_type: FurnisherType
    bureau: Bureau

    # Violation details
    description: str
    expected_value: Optional[str]
    actual_value: Optional[str]

    # Legal basis
    fcra_section: Optional[str]
    metro2_field: Optional[str]

    # Evidence (for letter generation)
    evidence: Dict[str, Any]

    # User selection
    selected_for_dispute: bool = True

    # NEW: Dispute validity
    disputable: bool = True  # False if violation shouldn't be disputed
    dispute_rationale: str   # Plain English explanation
```

---

## 3. Strategy Selector

### Input/Output
- **Input:** AuditResult (SSOT #2)
- **Output:** LetterPlan (SSOT #3)

### Responsibilities
1. Filter invalid/weak violations
2. Filter based on client selection (WITHOUT mutating AuditResult)
3. Group violations by strategy
4. Assign variation_seed
5. Select tone

### Grouping Strategies

| Strategy | Groups By | Use Case |
|----------|-----------|----------|
| `by_violation_type` | ViolationType | Default, logical grouping |
| `by_creditor` | Creditor name | Multiple issues with one creditor |
| `by_severity` | HIGH/MEDIUM/LOW | Prioritize serious issues |

### VariationSeed Generation (CORRECTED)

```python
def generate_variation_seed(report_id: str, seed: Optional[int] = None) -> int:
    """
    MUST be deterministic.

    If seed provided: use it
    If seed is None: derive from report_id hash

    NEVER use random.randint() without deterministic source.
    """
    if seed is not None:
        return seed
    # Deterministic derivation
    return hash(report_id) % 1000000
```

### Client Selection Handling (CORRECTED)

```python
def filter_violations(
    audit_result: AuditResult,
    selected_violation_ids: Optional[List[str]]
) -> List[Violation]:
    """
    Filter violations WITHOUT mutating AuditResult.

    Returns a NEW list, never modifies original.
    """
    if selected_violation_ids is None:
        return audit_result.violations.copy()

    return [
        v for v in audit_result.violations
        if v.violation_id in selected_violation_ids
    ]
```

---

## 4. Rendering Engine

### Core Principles (Template Resistance)

1. **No fixed structure markers** - No "Account 1:", "Item A:", "---" dividers
2. **Randomized element order** - Vary which fields appear and in what order
3. **Natural prose flow** - Paragraph-style, not bulleted lists
4. **Phrase variation** - Every sentence pulls from phrasebanks
5. **Human pacing** - Use transitions, vary sentence length

### Required Phrasebanks

#### VariantPool (by ViolationType)
Every ViolationType MUST have 4+ phrase variants:

```python
VIOLATION_PHRASES = {
    "missing_dofd": [
        "This account is missing the required Date of First Delinquency...",
        "The Date of First Delinquency is not reported...",
        "No DOFD is shown for this derogatory account...",
        "This account lacks the mandatory DOFD field...",
    ],
    "obsolete_account": [...],
    "negative_balance": [...],
    "past_due_exceeds_balance": [...],
    "future_date": [...],
    "closed_oc_reporting_balance": [...],
    "missing_date_opened": [...],  # NEW
    "missing_dla": [...],  # NEW
    "impossible_timeline": [...],  # NEW
    "stale_reporting": [...],  # NEW
    # ... ALL violation types
}
```

#### Tone-Specific Phrasebanks (CORRECTED)
ALL tones must have entries:

```python
OPENINGS = {
    "formal": [...],
    "assertive": [...],
    "conversational": [...],
    "narrative": [  # NEW - Must add
        "I want to share my experience with what I found on my credit report.",
        "After reviewing my credit report, I need to bring some concerns to your attention.",
        "Let me explain the issues I've discovered with my credit report.",
        "I'm writing to you today about problems I found when checking my credit.",
    ],
}
```

### Deterministic Randomness (CORRECTED)

```python
class RenderingEngine:
    def render(self, plan: LetterPlan) -> DisputeLetter:
        # Use instance-based random, not global
        rng = random.Random(plan.variation_seed)

        # Use rng.choice() instead of random.choice()
        opening = rng.choice(self.phrasebanks["openings"][tone])
```

### Anti-Template Rendering (CORRECTED)

```python
def _render_violation_naturally(self, violation: Violation, rng: random.Random) -> str:
    """
    Render a violation in natural prose, not structured format.

    WRONG:
    Creditor: ACME
    Account #: ****1234
    Issue: Missing DOFD

    RIGHT:
    "The account with ACME (ending in 1234) appears to be missing
    the Date of First Delinquency, which is required for any
    derogatory tradeline under Metro 2 reporting standards."
    """
    # Randomly decide which elements to include
    include_account_number = rng.random() > 0.3
    include_metro_field = rng.random() > 0.5

    # Build natural sentence
    parts = []
    parts.append(rng.choice(ACCOUNT_REFERENCES).format(
        creditor=violation.creditor_name,
        account=violation.account_number_masked if include_account_number else ""
    ))

    parts.append(rng.choice(VIOLATION_PHRASES[violation.violation_type.value]))

    if include_metro_field and violation.metro2_field:
        parts.append(rng.choice(METRO_REFERENCES).format(field=violation.metro2_field))

    return " ".join(parts)
```

---

## 5. Client Control Module

### Required Features

1. **Plain English Explanations**
   - Every violation must have a `dispute_rationale` in plain English
   - No legal jargon without explanation

2. **Severity Indicators**
   - HIGH: "This is a serious violation that may significantly impact your credit"
   - MEDIUM: "This is a moderate issue that should be corrected"
   - LOW: "This is a minor issue but still worth disputing"

3. **Furnisher-Type Indicator**
   - Show whether account is: Collection, Charge-off, or Original Creditor
   - Explain why this matters for the violation

4. **Selection Validation**
   - Prevent selection of non-disputable violations
   - Warn on weak violations
   - Confirm selections before generation

5. **No Re-computation**
   - UI receives AuditResult (SSOT #2)
   - Cannot trigger re-audit
   - Cannot modify violation classifications

### API Contract

```python
class ViolationDisplay(BaseModel):
    violation_id: str
    creditor_name: str
    account_number_masked: str

    # Plain English
    issue_summary: str  # "Missing required date field"
    issue_explanation: str  # Full paragraph explanation

    # Indicators
    severity: str
    severity_description: str
    furnisher_type: str
    furnisher_type_description: str

    # Selection
    is_disputable: bool
    selection_warning: Optional[str]  # "This may be a weak dispute because..."

    # Legal reference (optional display)
    fcra_section: Optional[str]
    metro2_field: Optional[str]
```

---

## 6. Determinism Requirements

### Guaranteed Determinism
Given:
- Same input file
- Same variation_seed

The system MUST produce:
- Identical NormalizedReport
- Identical AuditResult
- Identical LetterPlan
- Identical DisputeLetter content

### Acceptable Non-Determinism
- Timestamps (parse_timestamp, audit_timestamp, generated_at)
- UUIDs (report_id, violation_id, etc.) - different but consistent within run

### Time-Dependent Behavior (Documented)
The following rules depend on `date.today()`:
- `check_obsolete_account` - 7-year calculation
- `check_stale_reporting` - 90-day calculation
- `check_future_dates` - future date detection

This is **expected and correct** - the same report audited on different days SHOULD produce different results if time-based violations change.

---

## 7. Metro-2 Compliance Requirements

### Required Field Validations

| Field | Name | Valid Values | Validation |
|-------|------|--------------|------------|
| 11 | DOFD | Valid date | Required for derogatory |
| 10 | Date Opened | Valid date | Always required |
| 17A | Current Balance | Non-negative | Context-dependent |
| 17B | Amount Past Due | Non-negative | ≤ 17A |
| 18 | Payment Rating | 0-9, A-Z | Valid code check |
| 05 | Account Status | Valid codes | See below |

### Account Status Codes (Metro-2)
```
05 - Account transferred
11 - Current account
13 - Paid or closed/zero balance
61 - Paid, was 30-59 days past due
62 - Paid, was 60-89 days past due
63 - Paid, was 90-119 days past due
64 - Paid, was 120-149 days past due
65 - Paid, was 150-179 days past due
71 - Paid, was 180+ days past due
78 - Foreclosure
80 - Collection account
82 - Collection account, zero balance
83 - Paid collection, zero balance
84 - Charge-off
88 - Claim filed
89 - Deceased
93 - Account assigned to Government
94 - Paid charge-off, zero balance
95 - Account paid, was collection
96 - Account paid, was charge-off
97 - Unpaid charge-off
```

---

## 8. FCRA Compliance Requirements

### Required Section References

| Section | Requirement | System Coverage |
|---------|-------------|-----------------|
| §605(a) | 7-year reporting limit | `check_obsolete_account` |
| §605(c)(1) | DOFD determines 7-year period | `check_missing_dofd` |
| §611(a) | Accuracy requirement | Most violation rules |
| §611(a)(1)(A) | Completeness requirement | Missing field rules |
| §611(a)(5)(A) | Reinvestigation duties | Referenced in letters |
| §623(a)(1)(A) | Furnisher accuracy | Should be added to letters |

### Letter Legal Language
Every dispute letter MUST include:
1. Reference to consumer's rights under FCRA
2. Specific section citation for each violation type
3. 30-day investigation requirement reminder

---

## Appendix A: Implementation Checklist

### Critical (Block Release)
- [ ] Fix AuditResult mutation in letters.py
- [ ] Implement deterministic seed generation
- [ ] Add DOFD extraction to HTML parser
- [ ] Fix bureau assignment for multi-bureau reports
- [ ] Add `MISSING_ORIGINAL_CREDITOR` violation type
- [ ] Add narrative tone to phrasebanks

### High Priority
- [ ] Implement all missing single-bureau rules (6)
- [ ] Implement cross-bureau rules (9)
- [ ] Complete furnisher 17A/17B rules
- [ ] Remove template markers from renderer
- [ ] Use `random.Random(seed)` instance

### Medium Priority
- [ ] Add violation ID validation in API
- [ ] Add furnisher-aware selection validation
- [ ] Add violation phrases for all types
- [ ] Extract date_closed from HTML
- [ ] Add frivolous violation filtering

### Low Priority
- [ ] PDF parser implementation
- [ ] XML parser implementation
- [ ] Public records parser
- [ ] Additional FCRA section references

---

## Appendix B: Test Scenarios

### Scenario 1: Same Seed Determinism
```
Input: report_a.html, seed=12345
Run 1 → Letter A
Run 2 → Letter B
Assert: Letter A == Letter B (character-for-character)
```

### Scenario 2: Different Seed Variation
```
Input: report_a.html, seed=12345
Run → Letter A

Input: report_a.html, seed=67890
Run → Letter B

Assert: Letter A ≠ Letter B (different wording)
Assert: Letter A violations == Letter B violations (same content)
```

### Scenario 3: Cross-Bureau Detection
```
Input: multi_bureau_report.html
Expected:
- Accounts matched across TU, EX, EQ
- DOFD_MISMATCH detected if DOFDs differ
- BALANCE_MISMATCH detected if balances differ significantly
```

### Scenario 4: Furnisher Rule Application
```
Input: Account with furnisher_type=COLLECTOR, 17A=$5000, 17B=$0
Expected: No violation (correct collector reporting)

Input: Account with furnisher_type=OC_NON_CHARGEOFF, status=CLOSED, 17A=$5000
Expected: CLOSED_OC_REPORTING_BALANCE violation
```

---

*Specification Version 2.0.1 - Corrected based on System Sweep findings*
