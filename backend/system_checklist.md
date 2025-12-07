# Credit Engine System Checklist

## Current Status Overview
- **Full Coverage:** 25 violation types
- **Partial Coverage:** 11 violation types
- **Not Detected:** 7 violation types

---

## Priority 1: High-Value Missing Violations (>60% Success Rate)

### [ ] Deceased Indicator Error (80% success)
- **Category:** Identity & Account Ownership
- **Description:** Living consumer marked as deceased
- **Legal Basis:** FCRA §623(a)(1)
- **Implementation:** Parse deceased indicator field, flag if present on living consumer
- **File:** `app/services/audit/rules.py`

### [ ] Medical Debt <$500 (70% success)
- **Category:** Collection-Specific Violations
- **Description:** Unpaid medical debt under $500 (2022 FCRA amendment)
- **Legal Basis:** FCRA §605(a)(6)
- **Implementation:** Check collection accounts for medical indicator + balance <$500
- **File:** `app/services/audit/rules.py`

### [ ] Civil Judgments Post-2017 (70% success)
- **Category:** Public Records Errors
- **Description:** Civil judgments should not appear per NCAP requirements
- **Legal Basis:** NCAP Standards
- **Implementation:** Flag any civil judgment records (removed from reports since 2017)
- **File:** `app/services/audit/rules.py`

---

## Priority 2: Medium-Value Missing Violations (50-60% Success Rate)

### [x] Missing Original Creditor / Chain of Title (55% success) - ✅ IMPLEMENTED
- **Category:** Collection-Specific Violations
- **Description:** Collections without original creditor identification (K1 Segment)
- **Legal Basis:** FCRA §623(a)(7) - furnisher accuracy duty for debt ownership
- **Status:** ✅ Fully implemented with Chain of Title legal language
- **Rule:** `check_collector_missing_original_creditor()` in `app/services/audit/rules.py:933`
- **ViolationType:** `MISSING_ORIGINAL_CREDITOR`
- **Severity:** HIGH (deletion candidate - debt ownership is unverifiable)
- **Metro 2 Field:** K1 Segment (Original Creditor Name)
- **Criteria:**
  - Fires when `furnisher_type == COLLECTOR` and `original_creditor` is missing or whitespace-only
  - Uses "Chain of Title" legal terminology in dispute letters
  - Compliant accounts (like your Midland examples with OC listed) correctly pass

### [x] Duplicate Delinquencies / Illogical Progression (55% success) - ✅ IMPLEMENTED
- **Category:** Payment History Errors
- **Description:** Impossible delinquency progression (skipped levels) or stagnant lates
- **Legal Basis:** FCRA §623(a)(1) - accurate reporting requirement
- **Status:** ✅ Fully implemented with two violation types
- **Rules:**
  1. `check_illogical_delinquency_progression()` - Detects two patterns:
     - DELINQUENCY_JUMP (HIGH): History jumps levels (0→60, 30→90) - impossible
     - STAGNANT_DELINQUENCY (MEDIUM): Same late level for consecutive months (30→30)
- **ViolationTypes:** `DELINQUENCY_JUMP`, `STAGNANT_DELINQUENCY`
- **File:** `app/services/audit/rules.py`
- **Criteria:**
  - "Skipped Rung": Delinquency cannot jump levels (must go 0→30→60→90 sequentially)
  - "Stagnant Late": Same late status for 2+ consecutive months is suspicious (requires payment to maintain)

### [x] Authorized User Misreporting (50% success) - ✅ IMPLEMENTED
- **Category:** Identity & Account Ownership
- **Description:** AU accounts reported with derogatory marks (AU is not liable for the debt)
- **Legal Basis:** Metro 2 ECOA / FCRA §623(a)(1) / Equal Credit Opportunity Act
- **Status:** ✅ Implemented via `check_authorized_user_derogatory()` in cross-bureau rules
- **ViolationType:** `AUTHORIZED_USER_DEROGATORY`
- **File:** `app/services/audit/cross_bureau_rules.py`
- **Note:** Combined with ECOA Code Errors implementation above

### [x] Phantom Late Payments - Forbearance (50% success) - ✅ IMPLEMENTED
- **Category:** Payment History Errors
- **Description:** Late markers during $0 due or forbearance periods
- **Legal Basis:** FCRA §623(a)(1)
- **Status:** ✅ Fully implemented with forbearance detection
- **Rule:** `check_phantom_late_payment()` in `app/services/audit/rules.py:556`
- **ViolationType:** `PHANTOM_LATE_PAYMENT`
- **Criteria:**
  - Fires when scheduled_payment == $0 (no payment due) AND late markers exist in payment history
  - Also fires when remarks indicate forbearance/deferment/hardship AND late markers exist
  - Detects: COVID forbearance, CARES Act, student loan deferment, hardship programs
  - Late markers detected: 30, 60, 90, 120, 150, 180, CO, FC, RP
- **Forbearance Indicators Detected:** forbearance, deferment, hardship, COVID, CARES Act, pandemic, payment pause, in-school, grace period, military/SCRA, unemployment deferment

### [x] Double Jeopardy / Duplicate Debt Reporting (60% success) - ✅ IMPLEMENTED
- **Category:** Collection-Specific Violations / Cross-Tradeline
- **Description:** Original Creditor AND Debt Collector BOTH report balance for same debt
- **Legal Basis:** FCRA §607(b) - Maximum Possible Accuracy / Metro 2 Transfer Logic
- **Status:** ✅ Fully implemented as cross-tradeline check in engine.py
- **Rule:** `_check_double_jeopardy()` in `app/services/audit/engine.py:255`
- **ViolationType:** `DOUBLE_JEOPARDY`
- **Severity:** HIGH (deletion candidate - artificially doubles consumer's debt load)
- **Metro 2 Field:** Field 21 (Current Balance)
- **Criteria:**
  - Fires when: Collection account has original_creditor info AND balance > $0
  - AND: A matching OC account exists in same bureau with balance > $0
  - Uses `normalize_creditor_name()` for fuzzy matching OC names
  - Under Metro 2 transfer logic, OC must update balance to $0 when selling debt
  - Flags the OC account (usually easier to get deleted/updated)
- **Impact:** Artificially doubles consumer's debt load, destroys DTI ratios

### [ ] Unauthorized Hard Inquiries (50% success)
- **Category:** Inquiry Violations
- **Description:** Pulls without permissible purpose
- **Legal Basis:** FCRA §604(a)(3) / §1681b
- **Current:** In roadmap (§604 disputes)
- **Implementation:** Inquiry parsing and dispute generation
- **File:** `app/services/audit/rules.py`, `app/services/parsing/html_parser.py`

---

## Priority 3: Lower-Value Missing Violations (30-45% Success Rate)

### [x] ECOA Code Errors (45% success) - ✅ IMPLEMENTED
- **Category:** Metro 2 Format Violations / Cross-Bureau Discrepancy
- **Description:** Wrong or inconsistent designation for joint/individual/authorized user accounts
- **Legal Basis:** FCRA §623(a)(1), Equal Credit Opportunity Act (ECOA)
- **Status:** ✅ Fully implemented as two cross-bureau checks
- **Rules:**
  1. `check_ecoa_code_mismatch()` - Detects when bureaus report different liability codes (Individual vs Joint, etc.)
  2. `check_authorized_user_derogatory()` - Detects when AU accounts have derogatory marks (AU is not liable)
- **ViolationTypes:** `ECOA_CODE_MISMATCH`, `AUTHORIZED_USER_DEROGATORY`
- **File:** `app/services/audit/cross_bureau_rules.py`
- **Letter Support:** Cross-bureau discrepancies section with FCRA §623(a)(1) and ECOA citations

### [ ] Soft as Hard Inquiry Misclassification (45% success)
- **Category:** Inquiry Violations
- **Description:** Promotional/review inquiries classified as hard pulls
- **Legal Basis:** FCRA §604
- **Implementation:** Classify inquiry types and flag mismatches
- **File:** `app/services/audit/rules.py`

### [x] Time-Barred Debt (40% success) - ✅ IMPLEMENTED
- **Category:** Collection-Specific Violations
- **Description:** Collections past statute of limitations still reporting active
- **Legal Basis:** FDCPA §1692e(5) - Threat to take action that cannot legally be taken / State SOL Laws
- **Status:** ✅ Fully implemented with 50-state SOL database
- **Rules:**
  - `check_time_barred_debt()` in `app/services/audit/rules.py`
  - `get_sol_category()` - Infers debt category (open/written/promissory) from account fields
  - `_infer_dofd_from_payment_history()` - DOFD inference using "Reverse Contiguous Chain" algorithm
- **ViolationType:** `TIME_BARRED_DEBT_RISK`
- **Severity:** CRITICAL (if legal threats detected) / HIGH (otherwise)
- **Files:**
  - `app/services/audit/rules.py` - Detection logic + DOFD inference
  - `app/services/audit/sol_data.py` - 50-state SOL database with citations
  - `app/services/audit/engine.py` - Wired into audit pipeline
  - `app/services/legal_letter_generator/pdf_format_assembler.py` - Letter category
- **Criteria:**
  - Only applies to COLLECTOR or OC_CHARGEOFF accounts
  - Anchor date priority: Explicit DOFD > Inferred DOFD (from payment history) > DLA > DLP
  - DOFD inference uses "Reverse Contiguous Chain" algorithm (finds start of CURRENT delinquency, not oldest ever)
  - Compares anchor date against state-specific SOL for the debt category
  - Defaults to NY (3-year SOL under CPLR § 214-i), user_state parameter for future expansion
- **DOFD Inference Algorithm ("Reverse Contiguous Chain"):**
  - Sorts payment history newest → oldest
  - Walks backwards looking for delinquent statuses (30, 60, 90, 120, CO, etc.)
  - STOPS at the first "OK/Current" status (the cure point)
  - Returns oldest date in the UNBROKEN delinquency chain
  - This prevents false "time-barred" findings when old delinquencies were cured

### [x] Missing Compliance Condition Codes / Dispute Flag Mismatch (35% success) - ✅ IMPLEMENTED
- **Category:** Metro 2 Format Violations / Cross-Bureau Discrepancy
- **Description:** XB, XC, XH codes for disputed accounts - detects when one bureau shows dispute but another doesn't
- **Legal Basis:** FCRA §623(a)(3) - furnisher must report dispute status to ALL bureaus
- **Status:** ✅ Fully implemented as cross-bureau discrepancy check
- **Rule:** `check_dispute_flag_mismatch()` in `app/services/audit/cross_bureau_rules.py`
- **ViolationType:** `DISPUTE_FLAG_MISMATCH`
- **Criteria:**
  - Parses Comments/Remarks field for dispute indicator phrases
  - Active dispute (XB code): "disputed by consumer", "consumer disputes", etc.
  - Resolved dispute (XH/XC): "dispute resolved", "was in dispute", etc.
  - Flags when one bureau shows dispute text but another bureau has no dispute flag
- **Letter Support:** Cross-bureau discrepancies section with FCRA §623(a)(3) citation

### [ ] Duplicate Inquiries (30% success)
- **Category:** Inquiry Violations
- **Description:** Same creditor multiple pulls in short window
- **Legal Basis:** FCRA §604 / Scoring Logic
- **Implementation:** Group inquiries by creditor and flag duplicates within 14-45 days
- **File:** `app/services/audit/rules.py`

---

## Partial Coverage - Needs Enhancement

### [x] Balance > Credit Limit (40% success) - ✅ IMPLEMENTED
- **Category:** Metro 2 Format Violations
- **Description:** Balance exceeds limit without explanation (OPEN accounts only)
- **Status:** ✅ Fully implemented with proper exclusions
- **Rule:** `check_balance_exceeds_credit_limit()` in `app/services/audit/rules.py:299`
- **ViolationType:** `BALANCE_EXCEEDS_CREDIT_LIMIT`
- **Criteria:** Only fires for open accounts. Excludes charged-off, collection, and derogatory accounts (where balance > limit is expected due to fees/interest)

### [x] Invalid Status Codes (50% success) - ✅ IMPLEMENTED
- **Category:** Metro 2 Format Violations
- **Description:** Payment Status inconsistent with Payment History Profile
- **Status:** ✅ Fully implemented with false-positive prevention
- **Rule:** `check_status_payment_history_mismatch()` in `app/services/audit/rules.py:418`
- **ViolationType:** `STATUS_PAYMENT_HISTORY_MISMATCH`
- **Criteria:**
  - ONLY fires when **Payment Status** explicitly indicates chargeoff/collection/recovery/repo/foreclosure
  - Does NOT fire on Comments alone (avoids "Closed by Credit Grantor" false positives)
  - Requires 80%+ of payment history showing "OK" to be a contradiction
- **Valid Triggers:** "Collection/Chargeoff", "Transferred to recovery", "Charge-off", "Repossession"
- **False Positive Prevention:** Benign statuses like "Paid", "Closed", "Current" won't trigger even with suspicious comments

### [ ] Missing Tradelines (35% success)
- **Category:** Cross-Bureau Inconsistencies
- **Description:** Account on 1-2 bureaus but not all 3
- **Current:** Not explicitly flagged
- **Enhancement:** Add cross-bureau presence check
- **File:** `app/services/audit/rules.py`

### [x] Paid Collection Contradictions (65% success) - ✅ IMPLEMENTED
- **Category:** Collection-Specific Violations
- **Description:** Status/Balance contradictions in paid or zero-balance collections
- **Status:** ✅ Fully implemented with two violation types
- **Rule:** `check_paid_collection_contradiction()` in `app/services/audit/rules.py:857`
- **ViolationTypes:** `PAID_STATUS_WITH_BALANCE`, `ZERO_BALANCE_NOT_PAID`
- **Criteria:**
  - **Scenario 1:** Status says "Paid" but balance > $0 or past_due > $0 (fires PAID_STATUS_WITH_BALANCE)
  - **Scenario 2:** Collection has $0 balance but not marked "Paid" (fires ZERO_BALANCE_NOT_PAID)
  - **Exception:** Sold/Transferred accounts exempt from Scenario 2 (correct to show $0 but not "Paid")
- **Paid Indicators Detected:** paid, settled, satisfied, paid in full, paid collection
- **Sold Indicators (exemption):** sold, transferred, purchased by, assigned to

### [ ] Post-Settlement Negative Reporting (50% success)
- **Category:** Payment History Errors
- **Description:** Continued derogatory marks after settlement
- **Current:** Would require settlement date parsing
- **Enhancement:** Parse settlement status and validate payment history
- **File:** `app/services/audit/rules.py`, `app/services/parsing/html_parser.py`

### [ ] Fraudulent Accounts (65% success)
- **Category:** Identity & Account Ownership
- **Description:** Identity theft tradelines
- **Current:** Fraud alert detection present
- **Enhancement:** More robust fraud indicator parsing
- **File:** `app/services/audit/rules.py`

### [ ] Incorrect Personal Identifiers (55% success)
- **Category:** Identity & Account Ownership
- **Description:** Wrong SSN, DOB, address, name
- **Current:** Personal info parsing planned
- **Enhancement:** Implement personal info validation
- **File:** `app/services/parsing/html_parser.py`

### [ ] Satisfied Judgments Still Reporting (60% success)
- **Category:** Public Records Errors
- **Description:** Paid judgments not updated/removed
- **Current:** Parsing shows 'None Reported' only
- **Enhancement:** Full public records parsing
- **File:** `app/services/parsing/html_parser.py`

### [ ] Bankruptcy Date Errors (55% success)
- **Category:** Public Records Errors
- **Description:** Incorrect filing/disposition dates
- **Current:** Public records not fully parsed
- **Enhancement:** Parse and validate bankruptcy dates
- **File:** `app/services/parsing/html_parser.py`

---

## Currently Working Well (Full Coverage)

| Violation | Success Rate | Status |
|-----------|--------------|--------|
| Obsolete Information (>7 years) | 70-80% | ✅ Full |
| Stale Reporting (10mo - 7yr) | 20-30% | ✅ Full |
| Re-aged DOFD | 60-70% | ✅ Full |
| Missing DOFD | 50-60% | ✅ Full |
| Incorrect Open/Closed Dates | 40-50% | ✅ Full |
| Past Due + No Scheduled Payment | 60% | ✅ Full |
| Open Status + Charged-Off Data | 80% | ✅ Full |
| Derogatory + No Payment (context) | 30% | ✅ Refined |
| Balance Down + Past Due Up | 60% | ✅ Full |
| Closed + Continuing History | 55% | ✅ Full |
| Balance Variations >10% | 40% | ✅ Full |
| Status Code Conflicts | 45% | ✅ Full |
| Date Opened Discrepancies | 40% | ✅ Full |
| Duplicate Collections | 60% | ✅ Full |
| Balance > Credit Limit | 40% | ✅ Full |
| ECOA Code Mismatch (cross-bureau) | 45% | ✅ Full |
| Authorized User Derogatory | 50% | ✅ Full |
| Dispute Flag Mismatch (cross-bureau) | 35% | ✅ Full |
| Delinquency Jump (impossible progression) | 55% | ✅ Full |
| Stagnant Delinquency (rolling lates) | 55% | ✅ Full |
| Double Jeopardy (OC + Collector both with balance) | 60% | ✅ Full |
| Time-Barred Debt (SOL expired collections) | 40% | ✅ Full |

---

## Implementation Order Recommendation

### Phase 1: Quick Wins (Easy to implement, high success)
1. [ ] Deceased Indicator Error
2. [ ] Medical Debt <$500
3. [ ] Missing Original Creditor
4. [x] Balance > Credit Limit rule ✅ DONE

### Phase 2: Metro 2 Enhancements
5. [x] ECOA Code Errors ✅ DONE
6. [x] Missing Compliance Condition Codes (XA/XB/XC) ✅ DONE (Dispute Flag Mismatch)
7. [ ] Invalid Status Codes expansion

### Phase 3: Payment History Deep Dive
8. [ ] Duplicate Delinquencies
9. [x] Phantom Late Payments (forbearance) ✅ DONE
10. [ ] Post-Settlement Negative Reporting

### Phase 4: Inquiry System
11. [ ] Unauthorized Hard Inquiries
12. [ ] Duplicate Inquiries
13. [ ] Soft as Hard Misclassification

### Phase 5: Complex Implementations
14. [x] Time-Barred Debt (requires SOL database) ✅ DONE
15. [ ] Public Records parsing (judgments, bankruptcy)
16. [x] Authorized User Misreporting ✅ DONE

---

## Files to Modify

| File | Purpose |
|------|---------|
| `app/services/audit/rules.py` | Add new violation detection rules |
| `app/services/parsing/html_parser.py` | Extract new fields (ECOA, special comments, etc.) |
| `app/models/__init__.py` | Add new ViolationType enum values |
| `app/services/legal_letter_generator/pdf_format_assembler.py` | Route new violations to sections |
| `app/routers/letters.py` | Handle new violation types in letter generation |

---

## Reference Documents

- `violation_comparison.xlsx` - Full comparison spreadsheet
- `letter_fixes.md` - Recent fixes and Metro 2 field reference
- Metro 2 Format Guide - CDIA official documentation
- FCRA Full Text - 15 U.S.C. §1681 et seq.
