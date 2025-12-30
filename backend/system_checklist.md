# Credit Engine System Checklist

## Product Tiers — Roadmap

| Product Tier | Name | Purpose | Status |
|--------------|------|---------|--------|
| Product Tier 1 | Data-Level Enforcement | Prove reported data is impossible or inconsistent | ✅ SHIPPED |
| Product Tier 2 | Supervisory Enforcement | Prove responses fail examiner standards | ✅ SHIPPED |
| Product Tier 3 | Examiner Priority Modeling | Predict escalation likelihood | ✅ SHIPPED |
| Product Tier 4 | Counterparty Risk Intelligence | Model CRA / furnisher behavior | 🔲 DEFERRED |
| Product Tier 5 | Product & Revenue Leverage | B2B, attorneys, outcome pricing | 🔲 DEFERRED |
| Product Tier 6 | Copilot as Regulator Translator | UX trust & explanation layer | 🔲 DEFERRED |

> **Note:** "Product Tiers" (1-6) describe feature capabilities. "Enforcement Tiers" (1-3) describe a dispute's escalation state. See [Enforcement Tier Lifecycle](#enforcement-tier-lifecycle) below.

---

### Product Tier 1 — Contradiction Detection (Data Layer)
**Status:** ✅ SHIPPED
Detects Metro 2 data contradictions and generates violations.

### Product Tier 2 — Supervisory Enforcement (Response Layer)
**Status:** ✅ SHIPPED
**Tests:** 21/21 passing
**Scope:** Locked

Product Tier 2 adds examiner-standard enforcement to the system.

**Capabilities Delivered:**
- Response-layer violations created for VERIFIED / NO RESPONSE failures
- Deterministic examiner checks (no NLP, no heuristics)
- Severity promotion based on examiner failure
- Examiner-driven escalation (replacing attempt-count logic)
- Automatic letter posture upgrade
- Immutable ledger capture of examiner failures
- **Tier-2 Canonical Letter Templates** (fact-first, BASIS FOR NON-COMPLIANCE)

**Examiner Triggers Implemented:**
- PERFUNCTORY_INVESTIGATION
- NOTICE_OF_RESULTS_FAILURE
- SYSTEMIC_ACCURACY_FAILURE (same tradeline, same cycle)
- UDAAP_MISLEADING_VERIFICATION (CRITICAL impossibility only)

**Tier-2 Canonical Letters:**
- ✅ VERIFIED — Verification Without Reasonable Investigation
- ✅ REJECTED — Improper Frivolous/Irrelevant Determination
- ✅ NO_RESPONSE — Failure to Provide Results of Reinvestigation
- ✅ REINSERTION — Reinsertion Without Required Certification and Notice

**Tier-2 Exhaustion → Tier-3 Promotion:**
- ✅ Mark Tier-2 Notice Sent (explicit lifecycle tracking)
- ✅ Tier-2 Adjudication UI (integrated into violation cards)
- ✅ Non-CURED responses auto-promote to Tier-3
- ✅ Tier-3 locks violation record (immutable)
- ✅ Tier-3 classifies examiner failure type
- ✅ Tier-3 writes immutable ledger entry
- ✅ 19 tests covering Tier-3 promotion flow

Product Tier 1 behavior unchanged.
Product Tier 4+ explicitly deferred.

*This tier is sufficient for monetization.*

See: [docs/TIER2_SUPERVISORY_ENFORCEMENT.md](docs/TIER2_SUPERVISORY_ENFORCEMENT.md)

---

### Enforcement Tier Lifecycle

Individual disputes progress through **Enforcement Tiers** (separate from Product Tiers):

| Enforcement Tier | State | Trigger |
|------------------|-------|---------|
| Enforcement Tier 1 | Dispute Active | Initial dispute letter sent |
| Enforcement Tier 2 | Supervisory Escalation | Tier-2 supervisory notice sent |
| Enforcement Tier 3 | Locked/Closed | Non-CURED response after Tier-2 |

**Enforcement Tier 3 = Terminal State:**
- Violation record locked (immutable)
- Examiner failure classified
- Ledger entry written
- No further escalation in system (regulatory/litigation is external)

---

## Current Status Overview
- **Full Coverage:** 30 violation types
- **Partial Coverage:** 11 violation types
- **Not Detected:** 3 violation types

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

### [x] Unauthorized Hard Inquiries / Inquiry Misclassification (50% success) - ✅ IMPLEMENTED
- **Category:** Inquiry Violations
- **Description:** Soft-pull industries (insurance, employment, utilities) coded as hard inquiries
- **Legal Basis:** FCRA §604(a)(3) - Permissible Purpose / §1681b
- **Status:** ✅ Fully implemented via InquiryRules class
- **Rule:** `check_inquiry_misclassification()` in `app/services/audit/rules.py`
- **ViolationType:** `INQUIRY_MISCLASSIFICATION`
- **Severity:** MEDIUM
- **Criteria:**
  - Detects hard pulls from industries that should only do soft pulls
  - SOFT_PULL_INDUSTRIES: insurance, staffing, screening, rental, property management, utility, electric, gas, water, telecom
  - Suggests disputing as "unauthorized hard inquiry - should be soft pull"
- **File:** `app/services/audit/rules.py`

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

### [x] Collection Fishing Inquiries (45% success) - ✅ IMPLEMENTED
- **Category:** Inquiry Violations
- **Description:** Debt collectors pulling credit without owning a tradeline (fishing expedition)
- **Legal Basis:** FCRA §604(a)(3)(A) - No permissible purpose without existing debt relationship
- **Status:** ✅ Fully implemented via InquiryRules class
- **Rule:** `check_collection_fishing_inquiry()` in `app/services/audit/rules.py`
- **ViolationType:** `COLLECTION_FISHING_INQUIRY`
- **Severity:** HIGH (deletion candidate - no permissible purpose)
- **Criteria:**
  - Detects collectors who pulled credit but have NO matching tradeline
  - COLLECTOR_KEYWORDS: recovery, collection, receivables, portfolio, midland, encore, cavalry, lvnv, etc.
  - Cross-references inquiry creditor names against all account creditor names
  - If no match found → collector had no permissible purpose to pull
- **File:** `app/services/audit/rules.py`

### [x] Time-Barred Debt (40% success) - ✅ IMPLEMENTED
- **Category:** Collection-Specific Violations
- **Description:** Collections past statute of limitations still reporting active
- **Legal Basis:** FDCPA §1692e(5) - Threat to take action that cannot legally be taken / State SOL Laws
- **Status:** ✅ Fully implemented with 50-state SOL database + advanced features
- **Rules:**
  - `check_time_barred_debt()` in `app/services/audit/rules.py` - Main detection
  - `get_sol_category()` - Infers debt category (open/written/promissory) from account fields
  - `_infer_dofd_from_payment_history()` - DOFD inference using "Reverse Contiguous Chain" algorithm
  - `is_sol_tolled_by_bankruptcy()` - Bankruptcy tolling detection (SOL paused during BK)
  - `check_governing_law_opportunity()` - Bank headquarters state mapping for Choice of Law
  - `check_zombie_revival_risk()` - Detects payments after SOL expired (zombie debt trap)
- **ViolationType:** `TIME_BARRED_DEBT_RISK`
- **Severity:** CRITICAL (if legal threats detected or zombie risk) / HIGH (otherwise)
- **Files:**
  - `app/services/audit/rules.py` - Detection logic + DOFD inference + helper methods
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
- **Advanced Features:**
  - **Bankruptcy Tolling:** Detects active BK via Metro 2 Compliance Condition Codes (D/A/E/H/I/L/Q/Z) or remarks containing bankruptcy keywords. SOL is tolled (paused) during BK proceedings.
  - **Governing Law / Choice of Law:** Maps major bank creditors to their headquarters state (Chase→DE, Citi→SD, Capital One→VA, etc.). Contract choice-of-law clauses may apply shorter SOL.
  - **Zombie Revival Risk:** Detects when date_last_payment occurred AFTER the SOL would have expired. Making a payment on time-barred debt can restart the SOL clock in many states - a common debt buyer trap.
- **Bank Headquarters Mapping:**
  | Bank | State | SOL Impact |
  |------|-------|------------|
  | Chase / JP Morgan | DE | 3 years |
  | Discover | DE | 3 years |
  | Barclays | DE | 3 years |
  | Capital One | VA | 5 years |
  | Citi / Citibank | SD | 6 years |
  | Wells Fargo | SD | 6 years |
  | American Express | UT | 6 years |
  | Synchrony | UT | 6 years |
  | Goldman Sachs (Apple Card) | UT | 6 years |

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

### [x] Duplicate Inquiries / Double Tap (30% success) - ✅ IMPLEMENTED
- **Category:** Inquiry Violations
- **Description:** Same creditor pulling same bureau multiple times (same-day or within 14-day window)
- **Legal Basis:** FCRA §604 / Scoring Logic
- **Status:** ✅ Fully implemented via InquiryRules class with Creditor Normalizer
- **Rule:** `check_duplicate_inquiries()` in `app/services/audit/rules.py`
- **ViolationType:** `DUPLICATE_INQUIRY`
- **Severity:** MEDIUM (same-day "Double Tap") / LOW (within-window)
- **Criteria:**
  - **Phase 1 - Double Tap:** Same bureau + same normalized creditor + same DATE = technical glitch
  - **Phase 2 - Within Window:** Same bureau + same normalized creditor within 14 days = should merge
  - Uses `_normalize_creditor_name()` to handle aliases (COAF, CAP ONE AF, CAPITAL ONE AUTO FIN → CAPITAL ONE)
  - Cross-bureau same-day pulls are NOT flagged (normal for auto/mortgage applications)
- **Creditor Normalizer Mappings:**
  | Alias | Normalized To |
  |-------|---------------|
  | COAF, CAP ONE, CAPITAL ONE, CAPITAL 1 | CAPITAL ONE |
  | ALLY, AMERICREDIT, AMCR | ALLY FINANCIAL |
  | JPM, CHASE, JPMCB | JPMORGAN CHASE |
  | SYNCB, SYNCHRONY | SYNCHRONY BANK |
  | DEPT OF ED, NELNET, NAVIENT, MOHELA | DEPT OF EDUCATION |
- **File:** `app/services/audit/rules.py`

### [x] Student Loan Portfolio Mismatch (35% success) - ✅ IMPLEMENTED
- **Category:** Metro 2 Format Violations
- **Description:** Student loans reported as "Open" or "Revolving" instead of "Installment"
- **Legal Basis:** Metro 2 Format Field 8 (Portfolio Type) / FCRA §623(a)(1)
- **Status:** ✅ Fully implemented via SingleBureauRules class
- **Rule:** `check_student_loan_portfolio_mismatch()` in `app/services/audit/rules.py`
- **ViolationType:** `METRO2_PORTFOLIO_MISMATCH`
- **Severity:** MEDIUM
- **Metro 2 Field:** Field 8 (Portfolio Type: I=Installment, O=Open, R=Revolving)
- **Criteria:**
  - Detects student loans identified by creditor name or account type detail
  - Student loan keywords: educational, student loan, dept of ed, nelnet, navient, mohela, fedloan, sallie mae, great lakes, acs education, edfinancial, pheaa, ecmc
  - Flags when account_type is "Open" or "Revolving" instead of "Installment"
  - Under Metro 2 standards, Educational Loans are Installment contracts (Portfolio Type I)
- **Impact:** Incorrect portfolio type damages Credit Mix scoring factor (10% of FICO score)
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
| Inquiry Misclassification (soft-pull as hard) | 50% | ✅ Full |
| Collection Fishing Inquiries (no tradeline) | 45% | ✅ Full |
| Duplicate Inquiries (same creditor <14 days) | 30% | ✅ Full |
| Student Loan Portfolio Mismatch (Open vs Installment) | 35% | ✅ Full |

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
11. [x] Unauthorized Hard Inquiries / Inquiry Misclassification ✅ DONE
12. [x] Duplicate Inquiries ✅ DONE
13. [x] Collection Fishing Inquiries ✅ DONE

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
