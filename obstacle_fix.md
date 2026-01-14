# Credit Engine 2.0 - Obstacle Fix Log

This document tracks bugs, issues, and obstacles encountered during development along with their solutions. Use this as a reference for similar issues in the future.

---

## Table of Contents

1. [B6: Bureau Ghost Guard - Cross-Bureau Data Bleed](#b6-bureau-ghost-guard---cross-bureau-data-bleed)
2. [B6: Payment History Ghost Detection](#b6-payment-history-ghost-detection)
3. [B6: Violation Type Label Mismatch](#b6-violation-type-label-mismatch)
4. [B6: Account Dropdown Label Case Mismatch](#b6-account-dropdown-label-case-mismatch)
5. [B6: UI Semantic Layer - Violations vs Advisories](#b6-ui-semantic-layer---violations-vs-advisories)
6. [B6: Metro 2 Field Citation Duplication](#b6-metro-2-field-citation-duplication)
7. [B7: UserDB Attribute Mismatch in Letter Generation](#b7-userdb-attribute-mismatch-in-letter-generation)
8. [B7: MUI Tooltip/Span Wrapper Breaking Select Dropdown](#b7-mui-tooltipspan-wrapper-breaking-select-dropdown)
9. [B7: Test Mode Toggle Not Accessible for Response Selection](#b7-test-mode-toggle-not-accessible-for-response-selection)
10. [B7: VERIFIED Letter Production Hardening](#b7-verified-letter-production-hardening)
11. [B7: REJECTED/FRIVOLOUS Letter Production Hardening](#b7-rejectedfrivolous-letter-production-hardening)
12. [B7: REINSERTION Letter Production Hardening](#b7-reinsertion-letter-production-hardening)
13. [B14: Cross-Bureau Contradictions Not Included in Letters](#b14-cross-bureau-contradictions-not-included-in-letters)
14. [B15: Tier-2 Adjudication UI Not Appearing](#b15-tier-2-adjudication-ui-not-appearing)
15. [B15: Date Picker Showing Wrong Date](#b15-date-picker-showing-wrong-date-off-by-one-day)
16. [B15: datetime.utcnow() Deprecation Warnings](#b15-datetimeutcnow-deprecation-warnings)
17. [B16: Cross-Bureau Discrepancies Not Showing on Letters Page](#b16-cross-bureau-discrepancies-not-showing-on-letters-page)
18. [B16: Cross-Bureau Discrepancies Not Showing on Disputes Page](#b16-cross-bureau-discrepancies-not-showing-on-disputes-page)
19. [B16: Import Path Error in dispute_service.py](#b16-import-path-error-in-dispute_servicepy)
20. [B16: Discrepancies Not Appearing in "Log Response" Section](#b16-discrepancies-not-appearing-in-log-response-section)
21. [B16: Letter Generation Failing for Cross-Bureau Discrepancies](#b16-letter-generation-failing-for-cross-bureau-discrepancies)
22. [B16: VERIFIED Letter Missing Statutory Double-Tap](#b16-verified-letter-missing-statutory-double-tap)
23. [B6: Tier-2 UI Reset Bug + Missing Generate Letter Button](#b6-tier-2-ui-reset-bug--missing-generate-letter-button)
24. [B17: letterApi.js Not Passing Channel Parameter](#b17-letterapijs-not-passing-channel-parameter)
25. [B17: LetterDB Invalid `letter_type` Keyword](#b17-letterdb-invalid-letter_type-keyword)
26. [B17: Account Number Extraction vs Passthrough](#b17-account-number-extraction-vs-passthrough)
27. [B17: Missing `date` Import in letters.py](#b17-missing-date-import-in-letterspy)
28. [B18: Litigation Packet Missing DOFD Accounts (Index Bug)](#b18-litigation-packet-missing-dofd-accounts-index-bug)
29. [B18: Litigation Packet CRA-First Language for CFPB Routes](#b18-litigation-packet-cra-first-language-for-cfpb-routes)

---

## B6: Bureau Ghost Guard - Cross-Bureau Data Bleed

**Date:** December 2024

**Symptom:**
"Missing Account Open Date" violations appearing for TransUnion and Experian when only Equifax actually reported the tradeline. UI showed empty columns for TU/EX but validator still fired violations.

**Root Cause:**
When parsing merged credit reports, the system creates `BureauAccountData` objects for all three bureaus even when a bureau didn't report the account. Validation rules then fire on these empty "ghost" tradelines.

**Solution:**
Added `is_bureau_ghost()` function in `backend/app/services/audit/engine.py` that checks for substantive data before allowing validation:
- Financial data (balance, high_credit, credit_limit, past_due_amount)
- Date fields (date_opened, date_closed, date_reported, etc.)
- Status fields (payment_status, account_status_raw)
- Payment history (at least one non-empty status entry)

**Files Modified:**
- `backend/app/services/audit/engine.py`

---

## B6: Payment History Ghost Detection

**Date:** December 2024

**Symptom:**
Ghost detection wasn't working - bureaus with empty data still passed as "not a ghost" because `payment_history` array contained 24 entries with empty `status: ''` strings.

**Root Cause:**
Original check `bool(bureau_data.payment_history) and len(bureau_data.payment_history) > 0` returned True for arrays with empty status strings.

**Solution:**
Updated ghost detection to iterate through payment_history entries and check for at least one non-empty status value:
```python
has_payment_history = False
if bureau_data.payment_history:
    for entry in bureau_data.payment_history:
        status = entry.get('status', '') if isinstance(entry, dict) else ''
        if status and str(status).strip():
            has_payment_history = True
            break
```

**Files Modified:**
- `backend/app/services/audit/engine.py`

---

## B6: Violation Type Label Mismatch

**Date:** December 2024

**Symptom:**
Dropdown filter showed labels like "Missing Dofd" while "Group by Type" tab showed "Missing Date Of First Delinquency". Inconsistent user experience.

**Root Cause:**
`CompactFilterBar.jsx` used a generic `formatLabel()` function that did simple underscore-to-space conversion, while `ViolationList.jsx` used `getViolationLabel()` from the shared mapping.

**Solution:**
- Updated `CompactFilterBar.jsx` and `FilterToolbar.jsx` to use `getViolationLabel()` for category options
- Added 70+ violation types to `VIOLATION_LABELS` mapping in `formatViolation.js`

**Files Modified:**
- `frontend/src/components/CompactFilterBar.jsx`
- `frontend/src/components/FilterToolbar.jsx`
- `frontend/src/utils/formatViolation.js`

---

## B6: Account Dropdown Label Case Mismatch

**Date:** December 2024

**Symptom:**
Account dropdown showed "Bk of amer" (Title Case) while "Group by Account" tab showed "BK OF AMER" (ALL CAPS from credit report).

**Root Cause:**
`CompactFilterBar.jsx` was applying `formatLabel()` to account names, converting them to Title Case.

**Solution:**
Updated `formatTypeLabel()` to pass account names through unchanged:
```javascript
if (filterType === 'accounts') {
  return str;  // Keep as-is to match Group by Account tab
}
```

**Files Modified:**
- `frontend/src/components/CompactFilterBar.jsx`

---

## B6: UI Semantic Layer - Violations vs Advisories

**Date:** December 2024

**Symptom:**
LOW severity items (like "Student Loan Capitalized Interest") displayed with alarming "DISCREPANCY DETECTED" language and "EXPECTED vs ACTUAL" labels, creating unnecessary user alarm for informational review items.

**Root Cause:**
All items were rendered with the same violation-oriented language regardless of severity. No distinction between actionable violations and informational advisories.

**Solution:**
Created UI semantic layer with `getViolationUI()` function that returns mode-specific rendering:
- **LOW severity (advisory):** "Review Details", "Reference/Reported" labels, neutral gray colors
- **MEDIUM/HIGH severity (violation):** "Discrepancy Detected", "Expected/Actual" labels, green/red colors

**Files Modified:**
- `frontend/src/utils/formatViolation.js` (added `getViolationUI()` function)
- `frontend/src/components/ViolationToggle.jsx` (dynamic rendering based on severity)

---

## B6: Metro 2 Field Citation Duplication

**Date:** December 2024

**Symptom:**
Metro 2 citations displayed as "Metro 2 Field Field 12 (High Credit...)" - the word "Field" appeared twice.

**Root Cause:**
String concatenation issue. The UI prefixed with "Metro 2 Field " but `violation.metro2_field` already contained "Field 12 (...)".

**Solution:**
Defensive normalization - strip leading "Field " from the value before adding prefix:
```javascript
metroDisplay: violation.metro2_field
  ? `Metro 2 Field ${violation.metro2_field.replace(/^Field\s+/i, '')}`
  : null,
```

**Files Modified:**
- `frontend/src/utils/formatViolation.js`

---

## B7: UserDB Attribute Mismatch in Letter Generation

**Date:** December 2024

**Symptom:**
Clicking "Generate Letter" for a violation threw a 500 Internal Server Error: `AttributeError: 'UserDB' object has no attribute 'full_name'`

**Root Cause:**
The letter generation endpoint assumed `UserDB` had `full_name` and `address` attributes, but the actual model uses separate fields:
- Name: `first_name`, `middle_name`, `last_name`, `suffix`
- Address: `street_address`, `unit`, `city`, `state`, `zip_code`

**Solution:**
Build consumer name and address from individual fields:
```python
# Build consumer name from first/last name fields
consumer_name = "[CONSUMER NAME]"
if user:
    name_parts = [user.first_name, user.last_name]
    name_parts = [p for p in name_parts if p]
    if name_parts:
        consumer_name = " ".join(name_parts)

# Build consumer address from individual fields
consumer_address = "[CONSUMER ADDRESS]"
if user and user.street_address:
    addr_parts = [user.street_address]
    if user.unit:
        addr_parts[0] += f" {user.unit}"
    if user.city or user.state or user.zip_code:
        city_state_zip = ", ".join(filter(None, [user.city, user.state]))
        if user.zip_code:
            city_state_zip += f" {user.zip_code}"
        addr_parts.append(city_state_zip)
    consumer_address = "\n".join(addr_parts)
```

**Files Modified:**
- `backend/app/routers/disputes.py`

---

## Common Patterns & Lessons Learned

### 1. Data Bleed Issues
When working with multi-dimensional data (bureaus, accounts, dates), always validate that the dimension actually has data before processing. Empty containers can pass truthy checks.

### 2. Label Consistency
Use centralized mapping functions for display labels. Never duplicate formatting logic across components.

### 3. String Composition
When building display strings, check if source data already contains formatting. Use defensive normalization to strip duplicates.

### 4. Severity-Based UI
Different severity levels warrant different UI treatment. Don't use alarming language for informational items.

### 5. Case Sensitivity
Be intentional about text case. Credit report data is often ALL CAPS - decide whether to normalize or preserve.

---

## B7: MUI Tooltip/Span Wrapper Breaking Select Dropdown

**Date:** December 20, 2024

**Symptom:**
Response type dropdown in Dispute Tracking showed all options as enabled (black text), but clicking any option did nothing. The selection wouldn't register.

**Root Cause:**
MUI's `<Tooltip>` component wraps children in a `<span>` by default. We also had an explicit `<span>` wrapper for handling tooltip display on disabled MenuItems. This double-wrapping broke MUI Select's internal click handling - the Select component expects MenuItem to be direct children without intermediate wrapper DOM elements.

**Solution:**
Only use the span wrapper for disabled items (where selection doesn't matter anyway). Enabled items get plain MenuItem with native HTML `title` attribute:
```javascript
// Disabled items: Use Tooltip + span wrapper (needed for tooltip on disabled element)
if (isNoResponseBlocked) {
  return (
    <Tooltip key={key} title={disabledReason} placement="right" arrow>
      <span>
        <MenuItem value={key} disabled>{config.label}</MenuItem>
      </span>
    </Tooltip>
  );
}

// Enabled items: Plain MenuItem with native title attribute
// NO wrapper elements - this is critical for Select click handling to work
return (
  <MenuItem key={key} value={key} title={config.description}>
    {config.label}
  </MenuItem>
);
```

**Files Modified:**
- `frontend/src/pages/DisputesPage.jsx`

---

## B7: Test Mode Toggle Not Accessible for Response Selection

**Date:** December 20, 2024

**Symptom:**
Test mode toggle was only in the letter generation dialog, but users needed to enable test mode BEFORE selecting NO_RESPONSE (which is deadline-gated). Chicken-and-egg problem: couldn't open letter dialog without selecting a response first.

**Root Cause:**
Test mode state existed but the toggle UI was only rendered inside the letter generation dialog. The response dropdown's deadline check ran before users could enable test mode.

**Solution:**
Added test mode toggle to the expanded dispute row, synced with the main testMode state:
1. Added `testMode` prop to `ViolationResponseRow` component
2. Added `onTestModeChange` callback to `ExpandedRowContent`
3. Rendered toggle switch next to "Log Response from [entity]" header
4. Updated `isNoResponseAvailable()` to bypass deadline check when `testMode === true`

**Files Modified:**
- `frontend/src/pages/DisputesPage.jsx`

---

## B7: VERIFIED Letter Production Hardening

**Date:** December 20, 2024

**Symptom:**
VERIFIED enforcement letters included:
- Non-canonical entity names ("TransUnion" instead of "TransUnion LLC")
- Full damages lecture under willful notice section
- CFPB/Attorney General cc references at bottom
- Multiple violation entries (one per original violation) instead of single statutory theory
- Empty statutes for some violation types

**Root Cause:**
Letter generator was designed for comprehensive output, not production legal correspondence. Multiple statutory theories dilute enforceability; damages lectures are premature at enforcement stage.

**Solution:**
Refactored `generate_verified_response_letter()` for production:
1. **Canonical entity names:** Added `CANONICAL_ENTITY_NAMES` mapping and `canonicalize_entity_name()` function (TransUnion → TransUnion LLC, etc.)
2. **Single rights-preservation sentence:** Replaced damages lecture with "Nothing in this correspondence shall be construed as a waiver of any rights or remedies available under 15 U.S.C. §§ 1681n or 1681o for negligent or willful noncompliance."
3. **Removed regulatory cc:** No CFPB/AG references at this enforcement stage
4. **Single statutory theory:** Only "Verification Without Reasonable Investigation" under §1681i(a)(1)(A). Original violations referenced as facts, not separate entries.
5. **Auto-assign statutes:** Added `VIOLATION_STATUTE_DEFAULTS` mapping (e.g., Missing DOFD → §1681e(b))

**Files Modified:**
- `backend/app/services/enforcement/response_letter_generator.py`

---

## B7: REJECTED/FRIVOLOUS Letter Production Hardening

**Date:** December 20, 2024

**Symptom:**
REJECTED/FRIVOLOUS enforcement letters included:
- Non-canonical entity names ("TransUnion" instead of "TransUnion LLC")
- Missing statutory framework explaining §1681i(a)(3)(B) requirements
- No timeline showing failure to provide required 5-day written notice
- Violations without assigned statutes
- Damages language and CFPB/AG cc references

**Root Cause:**
Letter generator lacked specific handling for REJECTED response type. The frivolous determination requires specific statutory elements: the 5-day notice requirement, identification of specific deficiencies, and proper statutory framework citation.

**Solution:**
Created new `generate_rejected_response_letter()` function for production:
1. **Canonical entity names:** Uses shared `canonicalize_entity_name()` function
2. **STATUTORY FRAMEWORK section:** Full breakdown of 15 U.S.C. § 1681i(a)(3)(B) requirements
3. **Timeline with deficiency tracking:** Shows "5-Day Written Notice with Specific Deficiencies: NOT PROVIDED"
4. **Auto-assign statutes:** All disputed items get statute assignments (e.g., Missing DOFD → 15 U.S.C. § 1681e(b))
5. **Single statutory theory:** Improper Frivolous/Irrelevant Determination under §1681i(a)(3)(B)
6. **Rights-preservation clause:** Single sentence, no damages lecture
7. **No regulatory cc:** Clean ending without CFPB/AG references

**Files Modified:**
- `backend/app/services/enforcement/response_letter_generator.py`
- `backend/app/routers/disputes.py`

---

## B7: REINSERTION Letter Production Hardening

**Date:** December 20, 2024

**Symptom:**
REINSERTION enforcement letters included:
- Non-canonical entity names ("transunion" lowercase)
- Generic "FORMAL NOTICE OF STATUTORY VIOLATIONS" subject line
- Wrong violation type (Missing DOFD instead of Reinsertion Without Required Notice)
- Empty statute field
- Generic timeline with 30-day dispute deadline (not reinsertion-specific)
- Generic demands not tailored to reinsertion violations
- References to "reasonable investigation" which doesn't apply to reinsertion

**Root Cause:**
Letter generator was using the generic enforcement template for reinsertion cases. Reinsertion violations require specific statutory elements under §1681i(a)(5)(B): the 5-day written notice requirement, furnisher identification, and reinsertion-specific demands.

**Solution:**
Created new `generate_reinsertion_response_letter()` function for production:
1. **Canonical entity names:** Uses shared `canonicalize_entity_name()` function
2. **STATUTORY FRAMEWORK section:** Full breakdown of 15 U.S.C. § 1681i(a)(5)(B) requirements including:
   - Certification of completeness/accuracy requirement
   - 5-business-day written notice requirement
   - Notice content requirements (statement of reinsertion, furnisher info, dispute rights)
3. **Single statutory theory:** Reinsertion Without Required Notice under §1681i(a)(5)(B)
4. **Timeline with reinsertion-specific dates:**
   - Prior deletion date (or "previously deleted per dispute results" if unknown)
   - Reinsertion detected date
   - Written notice received: NONE (or date if deficient notice)
5. **Reinsertion-specific demands:**
   - Immediate deletion unless statutory compliance proven
   - Written certification of reinsertion source and furnisher verification
   - Production of alleged reinsertion notice
   - Identification of furnisher with name, address, and notification date
   - Updated consumer disclosure reflecting removal
6. **NO mention of "reasonable investigation" or 30-day dispute deadline**
7. **Rights-preservation clause:** Single sentence, no damages lecture
8. **No regulatory cc:** Clean ending without CFPB/AG references

**Files Modified:**
- `backend/app/services/enforcement/response_letter_generator.py`
- `backend/app/routers/disputes.py`

---

## B14: Cross-Bureau Contradictions Not Included in Letters

**Date:** December 2024

**Symptom:**
When a Copilot batch contained both violations AND cross-bureau contradictions:
- Violations (e.g., `missing_dofd`) appeared in generated letters
- Cross-bureau contradictions (e.g., `date_opened_mismatch`) were NOT included in letters

User expected ALL items in a selected batch to appear in the generated letter with appropriate legal citations.

**Root Cause:**
Multiple issues in the data flow:
1. **ID Mismatch:** Copilot engine used `c.get("id")` to create blocker source IDs, but stored discrepancies have `discrepancy_id` field
2. **Missing separation:** Batch engine only tracked `violation_ids`, not `contradiction_ids` separately
3. **No category:** PDF Format Assembler lacked a `CROSS_BUREAU_CONTRADICTION` category for grouping these items
4. **Frontend gap:** UI didn't pass contradiction IDs to letter generation API

**Solution:**

1. **Fixed ID mapping** in `copilot_engine.py`:
   ```python
   source_id=str(c.get("discrepancy_id") or c.get("id") or c.get("rule_code") or str(uuid4()))
   ```

2. **Added `contradiction_ids` field** to `DisputeBatch` model and `batch_engine.py`:
   ```python
   contradiction_ids = list(set(
       a.blocker_source_id for a in actions
       if a.source_type == "CONTRADICTION"
   ))
   ```

3. **Added `ViolationCategory.CROSS_BUREAU_CONTRADICTION`** to PDF Format Assembler with:
   - CategoryConfig citing FCRA §623(a)(1)(A), §611(a)(1), §607(b)
   - Classification logic for cross-bureau violation types
   - Proper ordering in letter sections

4. **Updated case law mapping** to link cross-bureau types to `CaseLawCategory.ACCURACY`:
   - `dofd_mismatch`, `balance_mismatch`, `status_mismatch`, `date_opened_mismatch`, etc.

5. **Frontend updates:**
   - Added `getBatchContradictionIds()` to copilotStore
   - Added `setSelectedDiscrepancies()` to violationStore
   - **Critical Fix:** Updated `handleSelectBatch` in RecommendedPlanTab to set BOTH `selectedViolationIds` AND `selectedDiscrepancyIds` when a batch is selected. Previously, only violations were set, so if user navigated to LetterPage without clicking "Generate Dispute Letter" button, discrepancies were empty.
   - Updated `handleGenerateLetter` to pass both violation and contradiction IDs to callback
   - Updated `handleOverrideConfirm` to also set discrepancies when overriding a locked batch
   - Updated `ViolationList` callback to set both selections and navigate to letter page

**Expected Letter Output:**
```
III. Cross-Bureau Reporting Contradictions

When the same account is reported with contradictory information across
credit bureaus, at least one bureau is necessarily receiving inaccurate data.
Under FCRA §623(a)(1)(A), furnishers have a duty to report accurate information
to ALL consumer reporting agencies.

• BK OF AMER (Account #440066301380****):
  Field: Date Opened
    TRANSUNION: 2018-03-15
    EXPERIAN: 2018-06-22
    EQUIFAX: 2018-03-15
```

**Files Modified:**
- `backend/app/models/copilot_models.py` - Added `contradiction_ids` field
- `backend/app/services/copilot/batch_engine.py` - Extract and pass contradiction IDs
- `backend/app/services/copilot/copilot_engine.py` - Fixed ID mapping for discrepancies
- `backend/app/routers/copilot.py` - Added `contradiction_ids` to API response
- `backend/app/services/legal_letter_generator/pdf_format_assembler.py` - Added cross-bureau category
- `backend/app/services/legal_letter_generator/case_law.py` - Mapped cross-bureau to case law
- `frontend/src/components/copilot/BatchAccordion.jsx` - Fixed broken JSX
- `frontend/src/state/copilotStore.js` - Added `getBatchContradictionIds()`
- `frontend/src/state/violationStore.js` - Added `setSelectedDiscrepancies()`
- `frontend/src/components/copilot/RecommendedPlanTab.jsx` - Pass both ID types
- `frontend/src/components/ViolationList.jsx` - Set selections and navigate

---

## B15: Tier-2 Adjudication UI Not Appearing

**Date:** December 29, 2024

**Symptom:**
Tier-2 supervisory response UI never appeared in the frontend after logging a response, even though Tier-2 letters were generated.

**Root Cause:**
Multiple issues in the data flow:

1. **Missing `violation_id` in Contradiction-Based Violations:**
   Violations generated from the contradiction engine use `account_id` instead of `violation_id`. When responses were saved, they stored `violation_id = null`, causing backend enrichment to fail silently.

2. **Backend Assumed Dict Format:**
   The `log_response` method called `.get()` on `original_violation_data` assuming it was always a dict, but letter generation stores it as a list.
   ```
   Error: 'list' object has no attribute 'get'
   ```

3. **Legacy Response Matching:**
   Responses saved before the fix had `violation_id = null` and couldn't be matched to violations during enrichment.

**Solution:**

1. **Generate `violation_id` if not present:**
   ```python
   # In dispute_service.py enrichment
   if not v_copy.get("violation_id"):
       v_copy["violation_id"] = v.get("account_id") or f"{d.id}-v{idx}"
   ```

2. **Check type before accessing dict methods:**
   ```python
   if isinstance(dispute.original_violation_data, dict):
       original_contradictions = dispute.original_violation_data.get("contradictions", [])
   else:
       # It's a list, handle accordingly
       pass
   ```

3. **Add fallback matching for legacy responses:**
   ```python
   responses_without_vid = [r for r in d.responses if not r.violation_id]
   responses_without_vid_idx = 0

   for idx, v in enumerate(violation_data):
       # ... try violation_id match first ...
       # Fallback: assign legacy responses in order
       elif responses_without_vid_idx < len(responses_without_vid):
           v_copy["logged_response"] = responses_without_vid[responses_without_vid_idx]
           responses_without_vid_idx += 1
   ```

**Files Modified:**
- `backend/app/services/enforcement/dispute_service.py`

---

## B15: Date Picker Showing Wrong Date (Off by One Day)

**Date:** December 29, 2024

**Symptom:**
Date picker displayed "12/30" when today was "12/29". User couldn't even select the 30th in the calendar.

**Root Cause:**
UTC timestamp was missing the 'Z' suffix. JavaScript's `new Date()` treated the timestamp as local time instead of UTC, causing timezone offset issues.

**Solution:**
Add 'Z' suffix to indicate UTC:
```python
# Before
"tier2_notice_sent_at": now.isoformat()  # "2024-12-29T10:30:00"

# After
"tier2_notice_sent_at": now.isoformat() + "Z"  # "2024-12-29T10:30:00Z"
```

**Files Modified:**
- `backend/app/services/enforcement/dispute_service.py`

---

## B15: `datetime.utcnow()` Deprecation Warnings

**Date:** December 29, 2024

**Symptom:**
Python 3.12+ shows deprecation warnings during test runs:
```
DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled
for removal in a future version. Use timezone-aware objects to represent
datetimes in UTC: datetime.datetime.now(datetime.UTC).
```

**Root Cause:**
Using deprecated `datetime.utcnow()` method throughout codebase.

**Solution:**
Replace all instances with timezone-aware alternative:
```python
# Before
from datetime import datetime
now = datetime.utcnow()

# After
from datetime import datetime, timezone
now = datetime.now(timezone.utc)
```

For `datetime.fromtimestamp()`, also add timezone:
```python
# Before
datetime.fromtimestamp(exp)

# After
datetime.fromtimestamp(exp, tz=timezone.utc)
```

**Files Modified (38 instances across 15 files):**
- `app/auth.py`
- `app/routers/admin.py`
- `app/routers/outcomes.py`
- `app/routers/scheduler.py`
- `app/services/copilot/batch_engine.py`
- `app/services/copilot/copilot_engine.py`
- `app/services/enforcement/deadline_engine.py`
- `app/services/enforcement/dispute_service.py`
- `app/services/enforcement/execution_ledger.py`
- `app/services/enforcement/execution_outcome_detector.py`
- `app/services/enforcement/ledger_signal_aggregator.py`
- `app/services/enforcement/reinsertion_detector.py`
- `app/services/enforcement/state_machine.py`
- `app/services/enforcement/tier3_promotion.py`
- `dry_run_execution.py`
- `test_execution_ledger.py`

---

## Quick Reference: Data Format Handling

When working with `original_violation_data`, always check the format:

```python
raw_data = dispute.original_violation_data or []

if isinstance(raw_data, dict):
    # From audit/contradiction engine
    violations = (
        raw_data.get("violations") or
        raw_data.get("contradictions") or
        raw_data.get("items") or
        []
    )
else:
    # From letter generation (list format)
    violations = raw_data
```

---

## B16: Cross-Bureau Discrepancies Not Showing on Letters Page

**Date:** January 2025

**Symptom:**
Discrepancies were included in letter text but not displayed in UI metadata on `/letter/:id` page.

**Root Cause:**
`LetterDB` model lacked `discrepancies_cited` column.

**Solution:**
1. Add column to model (`app/models/db_models.py`):
   ```python
   discrepancies_cited = Column(JSON)  # List of cross-bureau discrepancies
   ```

2. Create migration (`migrations/add_discrepancies_cited.py`):
   ```sql
   ALTER TABLE letters
   ADD COLUMN discrepancies_cited JSONB DEFAULT '[]'::jsonb;
   ```

3. Update letter generation to persist discrepancies when creating letters.

4. Update API response to return `discrepancies_cited` field.

**Files Modified:**
- `backend/app/models/db_models.py`
- `backend/migrations/add_discrepancies_cited.py`
- `backend/app/routers/letters.py`

---

## B16: Cross-Bureau Discrepancies Not Showing on Disputes Page

**Date:** January 2025

**Symptom:**
```
AttributeError: 'DisputeDB' object has no attribute 'discrepancies_data'
```

**Root Cause:**
`DisputeDB` model had no `discrepancies_data` column in database.

**Solution:**
1. Add column to model (`app/models/db_models.py`):
   ```python
   discrepancies_data = Column(JSON, nullable=True)  # Cross-bureau discrepancies from letter
   ```

2. Create migration (`migrations/add_discrepancies_to_disputes.py`):
   ```sql
   ALTER TABLE disputes
   ADD COLUMN discrepancies_data JSONB;
   ```

3. Copy discrepancies from letter to dispute when creating dispute:
   ```python
   if letter_id:
       from app.models.db_models import LetterDB
       letter = self.db.query(LetterDB).filter(LetterDB.id == letter_id).first()
       if letter and letter.discrepancies_cited:
           discrepancies_data = letter.discrepancies_cited
   ```

**Files Modified:**
- `backend/app/models/db_models.py`
- `backend/migrations/add_discrepancies_to_disputes.py`
- `backend/app/services/enforcement/dispute_service.py`

---

## B16: Import Path Error in dispute_service.py

**Date:** January 2025

**Symptom:**
```
ModuleNotFoundError: No module named 'app.services.models'
```

**Root Cause:**
Relative import `from ..models.db_models import LetterDB` failed in nested service module.

**Solution:**
Use absolute import:
```python
from app.models.db_models import LetterDB
```

**Rule:** Always use absolute imports for cross-module references in services.

**Files Modified:**
- `backend/app/services/enforcement/dispute_service.py`

---

## B16: Discrepancies Not Appearing in "Log Response" Section

**Date:** January 2025

**Symptom:**
Cross-bureau discrepancies showed in dispute summary but not in the "Log Response from [bureau]" section where users log responses.

**Root Cause:**
Only violations were mapped to `ViolationResponseRow` component. Discrepancies were displayed but not actionable.

**Solution:**
Reuse existing `ViolationResponseRow` component by adapting discrepancy shape:
```jsx
{dispute.discrepancies_data?.map((d, idx) => (
  <ViolationResponseRow
    key={`discrepancy-${d.discrepancy_id || idx}`}
    violation={{
      violation_id: d.discrepancy_id,        // Required for backend API
      violation_type: 'CROSS_BUREAU',
      creditor_name: d.creditor_name,
      account_number_masked: d.account_number_masked,
      description: `${d.field_name} mismatch across bureaus`,
      logged_response: d.logged_response,
      severity: 'MEDIUM',
    }}
    disputeId={dispute.id}
    // ... other props
  />
))}
```

**Principle:** Don't create duplicate components. Adapt data shape to fit existing components.

**Files Modified:**
- `frontend/src/pages/DisputesPage.jsx`

---

## B16: Letter Generation Failing for Cross-Bureau Discrepancies

**Date:** January 2025

**Symptom:**
```
Violation not found. Looking for: cf5e876e-1866-4fa7-b0bb-15a3a4709899.
Available: ['e6e25dfb-e2ac-4c80-916a-2e0a3af551179-v0', ...]
```

**Root Cause:**
Letter generation endpoint only searched `original_violation_data`, not `discrepancies_data`.

**Solution:**
Update `app/routers/disputes.py` to search both sources:
```python
all_violations = dispute.original_violation_data or []
all_discrepancies = dispute.discrepancies_data or []

if request.violation_id:
    violations = [v for v in all_violations if str(v.get('violation_id', '')) == str(request.violation_id)]

    # If not found in violations, check discrepancies
    if not violations:
        matching_discrepancies = [
            d for d in all_discrepancies
            if str(d.get('discrepancy_id', '')) == str(request.violation_id)
        ]
        if matching_discrepancies:
            d = matching_discrepancies[0]
            violations = [{
                'violation_id': d.get('discrepancy_id'),
                'violation_type': 'CROSS_BUREAU',
                'creditor_name': d.get('creditor_name'),
                'account_number_masked': d.get('account_number_masked'),
                'field_name': d.get('field_name'),
                'description': f"{d.get('field_name', 'Field')} mismatch across bureaus",
                'severity': 'MEDIUM',
                'logged_response': d.get('logged_response'),
                'is_discrepancy': True,
            }]
```

**Important:** Always include `logged_response` when adapting discrepancies for consistent response state reasoning.

**Files Modified:**
- `backend/app/routers/disputes.py`

---

## B16: VERIFIED Letter Missing Statutory Double-Tap

**Date:** January 2025

**Symptom:**
VERIFIED letter only cited § 1681i(a)(1)(A) (failure to investigate), missing the § 1681e(b) (maximum possible accuracy) argument that creates a legal trap.

**Root Cause:**
Letter template was designed with single statutory theory. Cross-bureau discrepancies require the "logical impossibility" argument.

**Solution:**
Add statutory double-tap in `response_letter_generator.py`:

1. **Subject line:**
   ```
   Verification Without Reasonable Investigation & Failure to Assure Accuracy
   ```

2. **Statutory Framework:** Add § 1681e(b):
   ```
   Additionally, pursuant to 15 U.S.C. § 1681e(b), a consumer reporting agency must follow
   reasonable procedures to assure maximum possible accuracy of the information reported.
   ```

3. **Add CROSS_BUREAU basis template:**
   ```python
   "cross_bureau": """A single tradeline cannot possess multiple values for the same field
   across consumer reporting agencies. At least one reported value is necessarily inaccurate.
   Verification of information that is contradicted across bureaus is not a verification of
   accuracy, but a confirmation of defective data."""
   ```

4. **Cure period framing:**
   ```
   within fifteen (15) days of receipt of this notice as a good-faith cure period
   ```

**Strategic value:** Forces bureau into a trap - they either admit they didn't investigate (§ 1681i) or admit they verified an impossibility (§ 1681e(b)). The "good-faith cure period" framing sets up willful violation (§ 1681n) for punitive damages if ignored.

**Files Modified:**
- `backend/app/services/enforcement/response_letter_generator.py`

---

## B6: Tier-2 UI Reset Bug + Missing Generate Letter Button

**Date:** January 2025

**Symptom:**
1. After clicking "Mark Tier-2 Notice Sent", the UI would reset to empty state (dropdown cleared, Verified chip disappeared)
2. User had to re-select the response type to see the Tier-2 adjudication section
3. No "Generate Letter" button in the Tier-2 section - users couldn't generate letters for Tier-2 responses

**Root Cause:**
1. UI Reset: `handleMarkTier2Sent()` called `onResponseLogged?.()` which triggered `setRefreshKey((k) => k + 1)` causing a full data refresh that reset the UI state
2. Missing Button: Tier-2 response types (REPEAT_VERIFIED, DEFLECTION_FRIVOLOUS, NO_RESPONSE_AFTER_CURE_WINDOW) were not wired to the letter generation endpoint

**Solution:**

1. **Fix UI Reset** - Remove `onResponseLogged?.()` from `handleMarkTier2Sent()`:
```javascript
const handleMarkTier2Sent = async () => {
  // ...
  setTier2NoticeSent(true);
  setTier2NoticeSentAt(response.tier2_notice_sent_at);
  // Local state update only - don't trigger refresh
};
```

2. **Add Generate Letter Button** to Tier-2 section:
```jsx
{tier2ResponseType && tier2ResponseType !== 'CURED' && (
  <Button
    variant="outlined"
    size="small"
    startIcon={<DescriptionIcon />}
    onClick={() => onGenerateLetter(violation, tier2ResponseType)}
  >
    Generate Letter
  </Button>
)}
```

3. **Wire Backend Routing** - Map Tier-2 types to existing Canonical letter generators:
```python
elif response_type == "REPEAT_VERIFIED":
    letter_content = generate_verified_response_letter(...)
elif response_type == "DEFLECTION_FRIVOLOUS":
    letter_content = generate_rejected_response_letter(...)
elif response_type == "NO_RESPONSE_AFTER_CURE_WINDOW":
    letter_content = generate_no_response_letter(...)
elif response_type == "CURED":
    return {"content": None, "message": "No letter needed"}
```

**Key Insight:** Tier-2 is not a new letter type - it's a new trigger-point for existing Canonical rebuttal letters. The Tier-2 Canonical structure (with BASIS FOR NON-COMPLIANCE sections) already exists in the response letter generators.

**Files Modified:**
- `frontend/src/pages/DisputesPage.jsx` - Fixed UI reset, added Generate Letter button
- `backend/app/routers/disputes.py` - Added Tier-2 response type routing

---

## B17: letterApi.js Not Passing Channel Parameter

**Date:** January 2025

**Symptom:**
Selecting "CFPB Complaint" in the 3-channel document selector had no effect - letters were always generated as standard mailed disputes regardless of selection.

**Root Cause:**
The `channel` parameter was being passed to the `generate()` function but was silently dropped because:
1. It wasn't destructured from the incoming params object
2. It wasn't included in the payload sent to the API

**Solution:**
Add `channel` to destructured params and include in payload:
```javascript
generate: async ({
  reportId,
  violationIds,
  discrepancyIds = [],
  channel = 'MAILED',  // Added
}) => {
  const payload = {
    report_id: reportId,
    violation_ids: violationIds,
    discrepancy_ids: discrepancyIds,
    channel,  // Added
  };
  // ...
}
```

**Files Modified:**
- `frontend/src/api/letterApi.js`

---

## B17: LetterDB Invalid `letter_type` Keyword

**Date:** January 2025

**Symptom:**
```
TypeError: __init__() got an unexpected keyword argument 'letter_type'
```
When generating CFPB or Litigation letters.

**Root Cause:**
The letters router was passing `letter_type="cfpb"` and `letter_type="litigation"` to `LetterDB()` constructor, but the model only has: `tone`, `channel`, `tier`.

**Solution:**
Remove `letter_type` keyword arguments and use `channel` instead:
```python
# Before
letter_db = LetterDB(letter_type="cfpb", ...)

# After
letter_db = LetterDB(channel="CFPB", ...)
```

**Files Modified:**
- `backend/app/routers/letters.py`

---

## B17: Account Number Extraction vs Passthrough

**Date:** January 2025

**Symptom:**
CFPB complaint showed "Account ending ****" with asterisks instead of the actual masked account number like "440066301380****".

**Root Cause:**
Initial implementation created `_extract_account_suffix()` helper that tried to extract the last 4 visible digits. But user feedback clarified: show numbers exactly as they appear in the credit report, including the asterisks.

**Solution:**
Changed from extraction to passthrough - display `account_number_masked` exactly as stored:
```python
# Before (extraction)
def _extract_account_suffix(self, masked: str) -> str:
    digits = ''.join(c for c in masked if c.isdigit())
    return digits[-4:] if len(digits) >= 4 else digits or '****'

# After (passthrough)
lines.append("Affected accounts:")
for v in violations:
    acct = getattr(v, "account_number_masked", None)
    if acct and acct.strip():
        lines.append(f"  • {v.creditor_name} — Account: {acct}")
    else:
        lines.append(f"  • {v.creditor_name} — Account: (masked)")
```

**Lesson:** Credit report data should be displayed exactly as received. Don't assume masked formats.

**Files Modified:**
- `backend/app/services/cfpb/cfpb_letter_generator.py`

---

## B17: Missing `date` Import in letters.py

**Date:** January 2025

**Symptom:**
```
NameError: name 'date' is not defined
```
When generating letters with deadline calculations.

**Root Cause:**
`date.today()` was used but only `datetime` was imported, not `date`.

**Solution:**
Add explicit import:
```python
from datetime import date, datetime
```

**Files Modified:**
- `backend/app/routers/letters.py`

---

## B18: Litigation Packet CRA-First Language for CFPB Routes

**Date:** January 14, 2026

**Symptom:**
Litigation packet showed CRA-dispute-first language for CFPB-route cases:
- "Consumer filed 0 formal dispute(s)"
- "0 formal disputes filed by consumer"
- "CONSUMER PROVIDED NOTICE VIA DISPUTE"

This was inconsistent for cases initiated via CFPB regulatory complaint, not traditional §1681i CRA dispute.

**Root Cause:**
The `render_document()` method in `attorney_packet_builder.py` had hardcoded CRA-dispute-first template language. It didn't detect the case route (CFPB vs CRA) to adjust language accordingly.

**Solution:**
Added route detection and conditional template language:

```python
# Detect if this is CFPB-first route
is_cfpb_route = (
    self.tier3_classification == "CFPB" or
    any("cfpb" in t.event_type.lower() for t in self.timeline)
)

# Phase 2: Route-aware language
if is_cfpb_route:
    lines.append("PHASE 2: POST-NOTICE PERSISTENCE (CFPB)")
    lines.append("    • Consumer filed CFPB regulatory complaint identifying violations")
    lines.append("    • Defendant received formal notice via CFPB complaint process")
else:
    lines.append("PHASE 2: POST-DISPUTE PERSISTENCE")
    lines.append(f"    • Consumer filed {dispute_count} formal dispute(s)")
```

**CFPB-route output:**
```
PHASE 2: POST-NOTICE PERSISTENCE (CFPB)
    • Consumer filed CFPB regulatory complaint identifying violations
    • Defendant received formal notice via CFPB complaint process
    • Defendant had full opportunity to cure after regulatory notice
    • Violations PERSISTED after notice — Defendant failed to cure

2. CONSUMER PROVIDED NOTICE VIA CFPB COMPLAINT
    Evidence: CFPB complaint and company response attached
```

**CRA-route output (unchanged):**
```
PHASE 2: POST-DISPUTE PERSISTENCE
    • Consumer filed 1 formal dispute(s)
    • Defendant received written notice identifying specific inaccuracies

2. CONSUMER PROVIDED NOTICE VIA DISPUTE
    Evidence: Dispute letters with certified mail receipts attached
```

**Files Modified:**
- `backend/app/services/artifacts/attorney_packet_builder.py`

---

## B18: Litigation Packet Missing DOFD Accounts (Index Bug)

**Date:** January 14, 2026

**Symptom:**
CFPB Stage 1 & 2 showed 2 accounts for "Missing Date of First Delinquency":
- 440066301380****
- 440066175522****

But Litigation packet showed only 1 account:
- 440066301380****

This under-pleaded the case and weakened willfulness leverage unnecessarily.

**Root Cause:**
The legal-packet endpoint (`letters.py:1351-1352`) has a legacy fallback for letters that store violations as type strings (e.g., `["missing_dofd", "missing_dofd"]`) instead of full objects.

The bug was in the fallback code:
```python
elif isinstance(v, str):
    violations.append({
        "violation_type": v,
        "creditor_name": letter.accounts_disputed[0],      # ← ALWAYS [0]!
        "account_number_masked": letter.account_numbers[0], # ← ALWAYS [0]!
        ...
    })
```

It **always used index `[0]`** instead of the loop index. When there were 2 `"missing_dofd"` strings with different accounts in the parallel `account_numbers` array, both got mapped to the first account. Deduplication then removed the "duplicate", leaving only 1 account.

**Evidence from database:**
```
violations_cited:  ["missing_dofd", "missing_dofd"]
accounts_disputed: ["BK OF AMER", "BK OF AMER"]
account_numbers:   ["440066301380****", "440066175522****"]  ← 2 DIFFERENT accounts!
```

The data was stored correctly in parallel arrays, but the code was accessing them wrong.

**Solution:**
Use `enumerate()` to get the loop index and access parallel arrays correctly:

```python
# Before (Bug):
for v in letter.violations_cited:
    ...
    "creditor_name": letter.accounts_disputed[0],
    "account_number_masked": letter.account_numbers[0],

# After (Fix):
for i, v in enumerate(letter.violations_cited):
    ...
    "creditor_name": letter.accounts_disputed[i] if i < len(letter.accounts_disputed or []) else "Unknown",
    "account_number_masked": letter.account_numbers[i] if i < len(letter.account_numbers or []) else "N/A",
```

**Why This Is Safe:**
1. Full dict violations (CFPB/LITIGATION channels) bypass this code path entirely
2. Old letters with string violations now work correctly without regeneration
3. Parallel arrays are guaranteed to be same length (built from same `filtered_violations` loop)

**Files Modified:**
- `backend/app/routers/letters.py` (line 1343)

---

## Adding New Entries

When documenting a new fix, include:
1. **Date** - When the fix was implemented
2. **Symptom** - What the user saw / reported
3. **Root Cause** - Technical explanation of why it happened
4. **Solution** - How it was fixed (include code snippets if helpful)
5. **Files Modified** - Which files were changed
