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

## Adding New Entries

When documenting a new fix, include:
1. **Date** - When the fix was implemented
2. **Symptom** - What the user saw / reported
3. **Root Cause** - Technical explanation of why it happened
4. **Solution** - How it was fixed (include code snippets if helpful)
5. **Files Modified** - Which files were changed
