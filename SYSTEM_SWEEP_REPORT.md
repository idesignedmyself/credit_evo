# Credit Engine 2.0 - System Sweep Report

**Date:** November 27, 2025
**Auditor Role:** Senior QA Engineer for Deterministic Rule-Based Systems, Metro-2 Compliance, and Template-Resistant Text Generation

---

## Executive Summary

The Credit Engine 2.0 codebase has been thoroughly analyzed across 10 phases. The architecture is sound and demonstrates good SSOT principles, but **23 issues** were identified ranging from critical violations to missing implementations.

### Issue Severity Summary
| Severity | Count |
|----------|-------|
| CRITICAL | 4 |
| HIGH | 8 |
| MEDIUM | 7 |
| LOW | 4 |

---

# PHASE 1 — SSOT Integrity Sweep

## Findings

### CRITICAL-001: AuditResult Mutated After Creation
**Location:** `app/routers/letters.py:81-85`
```python
if request.selected_violations:
    audit_result.violations = [
        v for v in audit_result.violations
        if v.violation_id in request.selected_violations
    ]
```
**Violation:** SSOT #2 (AuditResult) is directly mutated after creation. This violates the core SSOT principle that downstream modules cannot modify upstream SSOTs.

**Impact:** If the same AuditResult is used multiple times (e.g., generating multiple letters), the violations list is corrupted after the first call.

**Correction Required:** Create a filtered copy, never mutate original.

---

### HIGH-002: Non-Deterministic VariationSeed Generation
**Location:** `app/services/strategy/selector.py:82-83`
```python
if variation_seed is None:
    variation_seed = random.randint(0, 999999)
```
**Violation:** When variation_seed is not provided, it uses `random.randint()` which depends on global random state, making outputs non-deterministic.

**Correction Required:** Either require seed to be provided, or derive seed deterministically from report_id.

---

### MEDIUM-003: Missing "narrative" Tone in Phrasebanks
**Location:** `app/services/renderer/phrasebanks.py`
**Issue:** The `Tone` enum includes `NARRATIVE` but the phrasebanks only have entries for `formal`, `assertive`, and `conversational`.

**Impact:** Using `narrative` tone falls back to `formal`, which is undocumented behavior.

**Correction Required:** Add narrative tone entries or remove from enum.

---

### VERIFIED SSOT Compliance
- ✅ NormalizedReport is the only input to AuditEngine
- ✅ AuditResult is the only input to StrategySelector (aside from mutation bug)
- ✅ Violation objects contain necessary data for rendering
- ✅ Phrasebanks act as SSOT for phrasing
- ✅ No recursive data paths detected

---

# PHASE 2 — Parsing Layer Sweep

## Findings

### HIGH-004: Only IdentityIQ HTML Parser Implemented
**Location:** `app/services/parsing/`
**Issue:** The spec claims support for "HTML/PDF/XML/JSON" formats, but only IdentityIQ HTML is implemented.

**Missing:**
- PDF parser
- XML parser (MISMO format)
- JSON parser
- Direct bureau format parsers (TU/EX/EQ native)

---

### HIGH-005: Incorrect Bureau Assignment in Multi-Bureau Report
**Location:** `app/services/parsing/html_parser.py:233`
```python
bureau=Bureau.TRANSUNION,  # Default - IdentityIQ is multi-bureau
```
**Issue:** IdentityIQ reports contain data from ALL three bureaus, but the parser sets all accounts to TRANSUNION and creates separate Account objects per bureau with the bureau stored only in `raw_data["bureau"]`.

**Impact:** The NormalizedReport's `bureau` field is always TRANSUNION regardless of which bureau's data each account came from. Cross-bureau analysis becomes impossible.

**Correction Required:** Either:
1. Return three NormalizedReports (one per bureau), or
2. Store bureau on each Account object (add `bureau: Bureau` field to Account)

---

### HIGH-006: Missing DOFD Extraction
**Location:** `app/services/parsing/html_parser.py`
**Issue:** The parser extracts many date fields but does NOT extract `date_of_first_delinquency`. It's never populated from the HTML.

**Impact:** DOFD-based rules (missing DOFD, obsolete account) will never fire correctly.

**Correction Required:** Add DOFD field mapping in `_extract_account_data_for_header()`.

---

### MEDIUM-007: Missing date_closed Extraction
**Location:** `app/services/parsing/html_parser.py`
**Issue:** `date_closed` is defined in the Account model but never extracted by the parser.

---

### LOW-008: Public Records Parser Not Implemented
**Location:** `app/services/parsing/html_parser.py:517`
```python
# TODO: Parse actual public records when sample HTML is available
return records
```

---

# PHASE 3 — Audit Engine Rule Sweep

## Findings

### CRITICAL-009: Multiple Rules Not Implemented
**Location:** `app/services/audit/rules.py`

The ViolationType enum defines these violation types that have NO corresponding rules:

| Violation Type | Implementation Status |
|---------------|----------------------|
| `MISSING_DLA` | ❌ Not implemented |
| `MISSING_PAYMENT_STATUS` | ❌ Not implemented |
| `MISSING_SCHEDULED_PAYMENT` | ❌ Not implemented |
| `INVALID_METRO2_CODE` | ❌ Not implemented |
| `RE_AGING` | ❌ Not implemented |
| `DOFD_REPLACED_WITH_DATE_OPENED` | ❌ Not implemented |

---

### CRITICAL-010: Cross-Bureau Rules Not Implemented
**Location:** `app/services/audit/engine.py:62`
```python
discrepancies=[],  # Cross-bureau would be populated here
```

The following cross-bureau violation types exist in the enum but have NO rules:
- `DOFD_MISMATCH`
- `DATE_OPENED_MISMATCH`
- `BALANCE_MISMATCH`
- `STATUS_MISMATCH`
- `PAYMENT_HISTORY_MISMATCH`
- `PAST_DUE_MISMATCH`
- `CLOSED_VS_OPEN_CONFLICT`
- `CREDITOR_NAME_MISMATCH`
- `ACCOUNT_NUMBER_MISMATCH`

**Impact:** A major selling point of the system (cross-bureau discrepancy detection) is non-functional.

---

### HIGH-011: Wrong ViolationType Used for Missing Original Creditor
**Location:** `app/services/audit/rules.py:307`
```python
violations.append(Violation(
    violation_type=ViolationType.MISSING_DOFD,  # Reusing for now
```
**Issue:** `check_collector_missing_original_creditor` uses `MISSING_DOFD` instead of creating a proper violation type.

**Correction Required:** Add `MISSING_ORIGINAL_CREDITOR` to ViolationType enum and use it.

---

### HIGH-012: Incomplete 17A/17B Furnisher Rules
**Location:** `app/services/audit/rules.py`

Per the spec:
- **Collectors:** 17A = full balance, 17B = 0 → correct, do NOT flag
- **OC (charge-off):** follows collector rules
- **OC (non-charge-off, closed):** 17A = 0, 17B = 0 → flag if violated

**Current State:**
- Only `check_closed_oc_reporting_balance` exists (partial OC non-charge-off rule)
- No validation that collectors are reporting correctly
- No OC charge-off specific rules
- No 17B validation at all

---

### MEDIUM-013: Date of Last Payment Rule Missing
**Issue:** `MISSING_DLA` (Date Last Activity) exists in enum but the actual "Date of Last Payment" rule from the spec is not implemented.

---

## Verified Rules Working Correctly
- ✅ `check_missing_dofd` - Correct logic for derogatory accounts
- ✅ `check_missing_date_opened` - Correct
- ✅ `check_negative_balance` - Correct
- ✅ `check_past_due_exceeds_balance` - Correct
- ✅ `check_future_dates` - Correct
- ✅ `check_dofd_after_date_opened` - Correct (but name is confusing - checks DOFD *before* date opened)
- ✅ `check_obsolete_account` - Correct 7-year calculation
- ✅ `check_stale_reporting` - Correct 90-day threshold
- ✅ `check_impossible_timeline` - Correct

---

# PHASE 4 — Dispute Strategy Sweep

## Findings

### LOW-009: No Frivolous Violation Filtering
**Issue:** The Strategy Selector does not filter out weak or frivolous violations before grouping. The spec states it should "Filter invalid or weak violations."

**Current State:** All violations pass through to the LetterPlan regardless of merit.

---

### VERIFIED Working Correctly
- ✅ Strategy Selector does not re-evaluate violations
- ✅ All three grouping strategies (by_type, by_creditor, by_severity) are implemented
- ✅ LetterPlan always produced
- ✅ Bureau addresses are correct

---

# PHASE 5 — Rendering Engine Sweep

## Findings

### HIGH-014: Template Fingerprint Detected
**Location:** `app/services/renderer/engine.py:191`
```python
parts.append(f"\n--- DISPUTED ITEM GROUP {group_num} ---")
```
**Violation:** This creates an obvious, detectable template marker. The spec explicitly prohibits "robotic structure markers."

---

### HIGH-015: Rigid Structure in Violation Rendering
**Location:** `app/services/renderer/engine.py:201-246`
```python
parts.append(f"Creditor: {violation.creditor_name}")
parts.append(f"Account #: {violation.account_number_masked}")
parts.append(f"Issue: {violation.description}")
parts.append(f"Detail: {random.choice(phrases)}")
parts.append(f"Legal Basis: ...")
parts.append(f"Metro 2 Field: {violation.metro2_field}")
parts.append(f"Expected: {violation.expected_value}")
parts.append(f"Actual: {violation.actual_value}")
parts.append(f"Action Requested: ...")
```
**Violation:** Every violation is rendered with identical structure. This creates a detectable pattern.

**Correction Required:** Randomize order, vary which fields are included, use varied phrasings.

---

### MEDIUM-016: Limited Violation Phrasebanks
**Location:** `app/services/renderer/phrasebanks.py`

Only 6 violation types have custom phrases:
- `missing_dofd`
- `obsolete_account`
- `negative_balance`
- `past_due_exceeds_balance`
- `future_date`
- `closed_oc_reporting_balance`

**Missing phrases for:**
- `missing_date_opened`
- `missing_dla`
- `missing_payment_status`
- `impossible_timeline`
- `stale_reporting`
- All cross-bureau violations

---

### MEDIUM-017: Global Random State Pollution Risk
**Location:** `app/services/renderer/engine.py:53`
```python
random.seed(plan.variation_seed)
```
**Issue:** Using `random.seed()` affects the global random state. If any other code runs `random.*` between seed and render completion, determinism is broken.

**Correction Required:** Use `random.Random(seed)` instance instead of global.

---

# PHASE 6 — Client-Control Module Sweep

## Findings

### (Already reported as CRITICAL-001)
AuditResult mutation when filtering selected violations.

---

### MEDIUM-018: No Validation of Selected Violation IDs
**Location:** `app/routers/letters.py:81-85`
**Issue:** The API accepts any violation IDs without verifying they exist in the AuditResult. Invalid IDs are silently ignored.

**Correction Required:** Validate IDs and return error for invalid selections.

---

### MEDIUM-019: No Furnisher-Type-Aware Selection Validation
**Issue:** The spec states consumers should not be able to dispute violations that are invalid for the furnisher type (e.g., disputing "17A vs 17B" on a collector).

**Current State:** No validation exists. Any violation can be selected regardless of furnisher type.

---

### LOW-010: Severity Indicator Not Exposed in API
**Issue:** The spec requires "Severity indicator" in the UI, but `ViolationResponse` already includes `severity`. However, there's no plain-English severity description.

---

# PHASE 7 — End-to-End Determinism Sweep

## Findings

### (Already reported as HIGH-002)
Non-deterministic seed generation.

---

### LOW-011: Time-Dependent Behavior in Rules
**Locations:**
- `app/services/audit/rules.py:172` - `today = date.today()`
- `app/services/audit/rules.py:356` - `today = date.today()`
- `app/services/audit/rules.py:401` - `today = date.today()`
- `app/services/renderer/engine.py:121` - `today = date.today().strftime(...)`

**Issue:** Using `date.today()` means the same report audited on different days can produce different results (e.g., an account becoming obsolete).

**Acceptable:** This is expected behavior for credit reporting, but should be documented.

---

### Determinism Verification
With a fixed variation_seed:
- ✅ Same input → same letter content (if seed provided)
- ✅ Different seed → different letter (same violations)
- ⚠️ No hidden state *except* global random state risk

---

# PHASE 8 — Metro-2 Compliance Sweep

## Findings

### HIGH-006 (Duplicate Reference)
DOFD not being extracted from parser.

---

### HIGH-020: Incomplete Metro-2 Field Validation
**Issue:** The system references Metro-2 fields but doesn't validate the actual codes.

**Missing Validations:**
- Account Status codes (valid values: 05, 11, 13, 61, 62, 63, 64, 65, 71, 78, 80, 82, 83, 84, 88, 89, 93, 94, 95, 96, 97)
- Payment Rating codes
- Special Comment codes
- Compliance Condition codes

---

### Verified Metro-2 Logic
- ✅ 7-year reporting period from DOFD (§605(a))
- ✅ Field 17A (current balance) referenced
- ✅ Field 17B (past due amount) referenced
- ✅ Field 10 (date opened) referenced
- ✅ Field 11 (DOFD) referenced

---

# PHASE 9 — FCRA Compliance Sweep

## Findings

### VERIFIED FCRA Section References
- ✅ §605(a) - Obsolete information (7-year limit)
- ✅ §605(c)(1) - DOFD requirement for derogatory items
- ✅ §611(a) - Accuracy requirements
- ✅ §611(a)(5)(A) - Referenced for OC balance reporting

---

### LOW-012: §611(a)(1)(A) Method of Verification Not Fully Leveraged
**Issue:** The spec mentions "method of verification accuracy" but the system doesn't generate disputes specifically targeting verification procedures.

---

### Missing FCRA Coverage
- §623(a)(1)(A) - Furnisher accuracy duties (not cited in rules)
- §623(a)(2) - Duty to correct and update (not cited)
- §623(b) - Duties upon notice of dispute (not cited)

---

# PHASE 10 — Final Consolidation

## Corrections Required

### Immediate (CRITICAL)

1. **Fix AuditResult mutation** in `letters.py`:
```python
# WRONG
audit_result.violations = [v for v in audit_result.violations if ...]

# CORRECT
filtered_violations = [v for v in audit_result.violations if v.violation_id in request.selected_violations]
# Pass filtered_violations to create_letter_plan separately
```

2. **Implement cross-bureau rules** - This is a major advertised feature that doesn't work.

3. **Fix DOFD extraction** in HTML parser.

4. **Implement missing single-bureau rules**.

### High Priority

5. **Remove template markers** from renderer.

6. **Add narrative tone** to phrasebanks.

7. **Fix non-deterministic seed generation**.

8. **Fix bureau assignment** for multi-bureau reports.

9. **Fix wrong violation type** for missing original creditor.

10. **Complete 17A/17B rules** for all furnisher types.

### Medium Priority

11. Add violation ID validation in API.

12. Add furnisher-type-aware selection validation.

13. Use `random.Random(seed)` instance instead of global.

14. Add violation phrases for all types.

15. Extract date_closed from HTML.

16. Add frivolous violation filtering.

### Low Priority

17. Implement PDF/XML/JSON parsers.

18. Add public records parsing.

19. Add plain-English severity descriptions.

---

## Summary: System Readiness

| Component | Status | Notes |
|-----------|--------|-------|
| SSOT Architecture | ⚠️ Mostly Sound | 1 critical mutation bug |
| Parsing Layer | ⚠️ Partial | Only HTML, missing DOFD extraction |
| Single-Bureau Rules | ⚠️ Partial | 6 rules missing |
| Cross-Bureau Rules | ❌ Not Implemented | Major feature gap |
| Furnisher Rules | ⚠️ Partial | 17A/17B incomplete |
| Temporal Rules | ⚠️ Partial | 2 rules missing |
| Strategy Selector | ✅ Working | Minor improvements needed |
| Renderer | ⚠️ Template Risk | Structure too rigid |
| Client Control | ⚠️ Issues | Mutation bug, no validation |
| Determinism | ⚠️ Conditional | Only if seed provided |
| Metro-2 Compliance | ⚠️ Partial | Field codes not validated |
| FCRA Compliance | ✅ Good | Core sections covered |

---

## Recommended Action Plan

**Phase A (Foundation Fixes):**
1. Fix AuditResult mutation bug
2. Fix seed generation
3. Add DOFD extraction
4. Fix bureau assignment

**Phase B (Rule Completion):**
5. Implement all missing single-bureau rules
6. Implement cross-bureau rules
7. Complete furnisher rules

**Phase C (Template Resistance):**
8. Remove rigid structure markers
9. Randomize violation rendering order
10. Add all missing phrasebank entries

**Phase D (Validation):**
11. Add API validation
12. Add furnisher-aware filtering
13. End-to-end test suite

---

*Report generated by Credit Engine 2.0 System Sweep*
