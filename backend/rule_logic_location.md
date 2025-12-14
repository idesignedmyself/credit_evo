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
| Delinquency Jump | `delinquency_jump` | Field 18 (payment history jumps levels, e.g., 0→60) |
| Stagnant Delinquency | `stagnant_delinquency` | Field 18 (same late status for consecutive months) |
| Missing Original Creditor | `missing_original_creditor` | K1 Segment (Chain of Title - collection without OC) |
| Time-Barred Debt Risk | `time_barred_debt_risk` | State SOL / FDCPA §1692e(5) |
| Inquiry Misclassification | `inquiry_misclassification` | FCRA §604(a)(3) (soft-pull as hard) |
| Collection Fishing Inquiry | `collection_fishing_inquiry` | FCRA §604(a)(3)(A) (collector without tradeline) |
| Duplicate Inquiry | `duplicate_inquiry` | FCRA §604 (same creditor <14 days) |
| Student Loan Portfolio Mismatch | `metro2_portfolio_mismatch` | Field 8 (student loan as Open/Revolving instead of Installment) |
| Deceased Indicator Error | `deceased_indicator_error` | Field 37/38 (ECOA Code X or Consumer Info Indicator X/Y/Z) |
| Child Identity Theft | `child_identity_theft` | Field 10 (Date Opened) vs User DOB - Account opened when minor |
| NCAP Violation (Judgment/Lien) | `ncap_violation_judgment` | Public Record (Civil Judgments/Tax Liens banned post-2017 NCAP) |
| Judgment Not Updated | `judgment_not_updated` | Public Record (Satisfied judgment still reporting balance > $0) |
| Bankruptcy Date Error | `bankruptcy_date_error` | Public Record (Filed date is in the future - impossible) |
| Bankruptcy Obsolete | `bankruptcy_obsolete` | Public Record (Ch7 > 10 years or Ch13 > 7 years per FCRA §605(a)(1)) |
| Medical Under $500 | `medical_under_500` | Bureau Policy / NCAP 2023 (Unpaid medical < $500 banned April 2023) |
| Medical Paid Reporting | `medical_paid_reporting` | Bureau Policy / NCAP 2022 (Paid medical collections banned July 2022) |
| Post-Settlement Negative | `post_settlement_negative` | Field 18/24 (Late markers reported AFTER account closed/settled - "Zombie History") |
| Missing Tradeline | `missing_tradeline_inconsistency` | Cross-Bureau (Account appears on some bureaus but missing from others) |

**Time-Barred Debt Detection:**
- `check_time_barred_debt()` - Main detection logic comparing anchor date vs state SOL
- `get_sol_category()` - Infers debt category (open/written/promissory) from account fields
- `_infer_dofd_from_payment_history()` - DOFD inference using "Reverse Contiguous Chain" algorithm
- `is_sol_tolled_by_bankruptcy()` - Checks if SOL is paused due to active bankruptcy
- `check_governing_law_opportunity()` - Maps bank creditors to HQ state for Choice of Law strategy
- `check_zombie_revival_risk()` - Detects payment made after SOL expired (zombie debt trap)

**DOFD Inference Algorithm ("Reverse Contiguous Chain"):**
Under FCRA/Metro 2®, DOFD is the "commencement of the delinquency which IMMEDIATELY PRECEDED the collection/charge-off." This means cured delinquencies are ignored.

Algorithm:
1. Flatten all payment history entries across bureaus
2. Sort by date (newest → oldest)
3. Walk backwards until hitting an "OK/Current" status (cure point)
4. Return oldest date in the UNBROKEN delinquency chain

Example: Late 2018 → Cured 2019 → Default 2021
- Old (wrong): Returns 2018 (7 years = "time-barred")
- New (correct): Returns 2021 (4 years = NOT time-barred)

**Bankruptcy Tolling:**
- Checks Metro 2 Compliance Condition Codes: A, D, E, H, I, L, Q, Z
- Scans remarks for keywords: bankruptcy, chapter 7, chapter 13, chapter 11, bk filed
- If detected, SOL is tolled (paused) - violation not flagged until BK discharged

**Governing Law / Choice of Law:**
- Bank headquarters state may apply under card agreement choice-of-law clause
- Bank mapping: Chase/JPM→DE, Discover→DE, Barclays→DE, Capital One→VA, Citi→SD, etc.
- Strategy: Consumer state SOL vs bank state SOL - shorter one may apply

**Zombie Revival Risk:**
- Detects when date_last_payment occurred AFTER SOL would have expired
- Making any payment on time-barred debt can restart the SOL clock in many states
- HIGH risk warning added to violation description to alert consumer

**Inquiry Violation Detection (FCRA §604):**
- `InquiryRules` class - Static methods for inquiry-specific violations
- `SOFT_PULL_INDUSTRIES` - Set of keywords for soft-pull-only industries (insurance, staffing, screening, rental, utility, telecom)
- `COLLECTOR_KEYWORDS` - Set of keywords for debt collection agencies (recovery, collection, receivables, portfolio, midland, etc.)
- `_normalize_creditor_name()` - Maps creditor aliases to root entity (COAF → CAPITAL ONE, AMERICREDIT → ALLY FINANCIAL)
- `check_inquiry_misclassification()` - Detects hard pulls from soft-pull industries
- `check_collection_fishing_inquiry()` - Detects collectors who pulled credit without owning a tradeline
- `check_duplicate_inquiries()` - Two-phase detection: same-day "Double Tap" + within-window duplicates
- `audit_inquiries()` - Main entry point that runs all inquiry checks

**Creditor Normalizer Mappings:**
| Aliases | Normalized To |
|---------|---------------|
| COAF, CAP ONE, CAPITAL ONE, CAPITAL 1, CAPONE | CAPITAL ONE |
| ALLY, AMERICREDIT, AMCR | ALLY FINANCIAL |
| JPM, CHASE, JP MORGAN, JPMCB | JPMORGAN CHASE |
| SYNCB, SYNCHRONY, AMAZON/SYNC | SYNCHRONY BANK |
| DEPT OF ED, NELNET, NAVIENT, MOHELA, FEDLOAN, GREAT LAKES | DEPT OF EDUCATION |
| DISCOVER, DFS, DISCOVERBANK | DISCOVER |
| BANK OF AMERICA, BOA, BOFA, B OF A | BANK OF AMERICA |
| WELLS FARGO, WELLSFARGO, WF | WELLS FARGO |
| CITI, CITIBANK, CITICORP | CITIBANK |
| AMEX, AMERICAN EXPRESS | AMERICAN EXPRESS |
| TOYOTA, TFS, LEXUS | TOYOTA FINANCIAL |
| HONDA, AHFC, ACURA | HONDA FINANCIAL |
| FORD, FMC, LINCOLN | FORD CREDIT |
| GM FINANCIAL, GMAC, GENERAL MOTORS | GM FINANCIAL |
| SANTANDER, SCUSA | SANTANDER |

**Inquiry Detection Logic:**
| Check | Detection Method | Legal Basis |
|-------|-----------------|-------------|
| Misclassification | Creditor name contains SOFT_PULL_INDUSTRIES keywords | FCRA §604(a)(3) |
| Fishing Expedition | Creditor matches COLLECTOR_KEYWORDS but has no matching tradeline | FCRA §604(a)(3)(A) |
| Double Tap | Same bureau + same normalized creditor + same DATE | FCRA §604 |
| Within-Window | Same bureau + same normalized creditor within 14 days | FCRA §604 / Scoring |

**Student Loan Portfolio Mismatch Detection:**
- `check_student_loan_portfolio_mismatch()` - Detects student loans misclassified as Open/Revolving
- Under Metro 2 standards, Educational Loans MUST be Portfolio Type I (Installment)
- Incorrect classification damages Credit Mix scoring factor (10% of FICO)
- Student loan keywords: educational, student loan, dept of ed, nelnet, navient, mohela, fedloan, sallie mae, great lakes, acs education, edfinancial, pheaa, ecmc
- Checks both `account_type_detail` and `creditor_name` for student loan indicators
- Flags when `account_type` contains "open" or "revolving" instead of "installment"

**Deceased Indicator Error Detection (CRITICAL - Score = 0):**
- `check_deceased_indicator()` - Account-level detection of erroneous deceased marker on tradeline
- `check_deceased_indicator_consumer()` - Consumer-level detection in report header
- Under Metro 2, "Death on Credit" occurs when a living consumer is erroneously marked as deceased
- This causes credit score to drop to ZERO and results in complete credit denial
- Detection sources:
  - ECOA Code 'X' (Metro 2 Field 37) - Deceased indicator
  - Consumer Information Indicator 'X', 'Y', 'Z' (Metro 2 Field 38) - Deceased/death notice
  - Remarks containing "deceased", "death", "consumer deceased" keywords
  - Payment status or compliance condition codes indicating death
- Legal basis: FCRA §611(a) (willful noncompliance), §623(a)(2) (reasonable procedures)
- Case law: Sloane v. Equifax (defamatory reporting of deceased status)

**Child Identity Theft Detection (Account Opened While Minor):**
- `check_child_identity_theft()` - Compares account Date Opened vs consumer's DOB from profile
- Under contract law, minors (<18) lack the legal capacity to enter into binding contracts
- CRITICAL EXCEPTION: Authorized Users (ECOA Code 3) are allowed to be minors - parents often add children as AUs
- Detection logic:
  1. Compare account.date_opened vs user_profile.date_of_birth
  2. Calculate age at opening: (date_opened - dob).days / 365.25
  3. Skip if ECOA Code 3 (Authorized User) - this is legal
  4. Flag if age < 18 AND consumer is liable (Individual/Joint)
- Legal basis: Contract Law (Capacity to Contract), FCRA §611(a)
- Strong indicator of identity theft or synthetic fraud

**Identity Integrity Rules (FCRA §607(b) - Maximum Possible Accuracy):**
- `IdentityRules` class - Static methods for identity validation against user profile
- `check_identity_integrity(report, user_profile)` - Main entry point, runs all identity checks
- `check_suffix_mismatch(report_name, user_profile)` - Detects Jr/Sr mixed file indicators
- `check_ssn_mismatch(report_ssn, user_profile)` - Validates SSN last 4 digits match
- `check_state_mismatch(report_state, report_address, user_profile)` - Validates state consistency
- `check_name_mismatch(report_name, user_profile)` - Validates name (first, middle initial, last)

**Identity Check Data Flow:**
```
HTML Report → Parser (html_parser.py) → NormalizedReport.consumer → IdentityRules
                                              ↓
                                        Contains: full_name, date_of_birth, state, address, ssn_last4
                                              ↓
User Profile (PostgreSQL users table) → IdentityRules → Violations
```

**Identity Violation Types:**
| Check | Detection Method | Legal Basis |
|-------|-----------------|-------------|
| Suffix Mismatch | Jr vs Sr/II/III/IV conflicts | FCRA §607(b) - Mixed File |
| SSN Mismatch | Last 4 digits don't match | FCRA §607(b) - Wrong File |
| State Mismatch | Report state vs user profile state | FCRA §607(b) - Mixed File |
| Name Mismatch | First/Middle/Last comparison | FCRA §607(b) - Mixed File |
| Deceased Indicator | ECOA Code X / Consumer Info X/Y/Z / Remarks | FCRA §611(a) / §623(a)(2) - CRITICAL |
| Child Identity Theft | Date Opened vs DOB, age < 18 (skip ECOA 3 AUs) | Contract Law / FCRA §611(a) - CRITICAL |

**Public Records Rules (Bankruptcies, Judgments, Liens):**
- `PublicRecordRules` class - Static methods for public record-specific violations
- `check_ncap_compliance(record)` - Flags Civil Judgments and Tax Liens appearing post-2017 (banned under NCAP settlement)
- `check_judgment_status(record)` - Flags satisfied/paid judgments still reporting a balance > $0
- `check_bankruptcy_dates(record)` - Flags impossible dates (future) and obsolete bankruptcies
- `audit_public_records(records)` - Main entry point that runs all public record checks

**Public Record Violation Types:**
| Check | Detection Method | Legal Basis |
|-------|-----------------|-------------|
| NCAP Violation | Civil Judgment or Tax Lien appearing after July 1, 2017 | NCAP Settlement (2015) |
| Judgment Not Updated | Satisfied/Paid judgment with balance > $0 | FCRA §623(a)(2) / Metro 2 accuracy |
| Bankruptcy Date Error | Filed date is in the future | FCRA §623(a)(1) - impossible data |
| Bankruptcy Obsolete | Ch7/11 > 10 years OR Ch13 > 7 years | FCRA §605(a)(1) |

**NCAP Settlement Background (2015):**
- National Consumer Assistance Plan required bureaus to improve accuracy
- Key provision: Civil Judgments and Tax Liens must contain full PII (name, address, SSN or DOB)
- Effective July 1, 2017: All Civil Judgments and Tax Liens removed (none could meet PII standards)
- Exception: Child support and divorce-related judgments are still allowed

**Bankruptcy Obsolescence (FCRA §605(a)(1)):**
- Chapter 7 and Chapter 11: 10 years from filing date
- Chapter 13: 7 years from filing date
- "Filed date" is the anchor, not discharge date

**Medical Debt Compliance (NCAP 2022/2023 Bureau Policy):**
- `check_medical_debt_compliance(account, bureau)` - Checks for "zombie medical bills" that bureaus should have purged
- Two specific violations detected:
  1. **Medical Under $500** (April 2023): Unpaid medical collections < $500 should be deleted
  2. **Medical Paid Reporting** (July 2022): ANY paid medical collection should be deleted immediately
- Medical detection uses keyword matching: medical, health, hospital, clinic, radiology, etc.
- Bureau policy violations - the bureaus agreed to these rules but systems don't always filter correctly

**Medical Debt Violation Types:**
| Check | Detection Method | Legal Basis |
|-------|-----------------|-------------|
| Under $500 | Balance > 0 AND Balance < 500 AND is_medical | Bureau Policy / NCAP 2023 |
| Paid Reporting | is_paid (status=Paid/Settled OR $0 balance) AND is_medical | Bureau Policy / NCAP 2022 |

**To add a new rule:** Create a new function in this file following the existing pattern.

---

### 2. `app/services/audit/engine.py` - Audit Engine

**Purpose:** Orchestrates running rules against accounts and collecting violations.

**What lives here:**
- `audit_report()` function - main entry point
- Rule execution loop
- Violation aggregation
- Clean account tracking
- Cross-tradeline checks (Double Jeopardy)

**Flow:**
```
NormalizedReport → audit_report() → runs rules.py → AuditResult
```

**Cross-Tradeline Checks (run in engine.py):**
| Check | Description | Legal Basis |
|-------|-------------|-------------|
| Double Jeopardy | OC and Collector BOTH report balance for same debt | FCRA §607(b) |
| Time-Barred Debt | Collections past state SOL still reporting | FDCPA §1692e(5) |
| Inquiry Audits | Runs InquiryRules.audit_inquiries() on all inquiries | FCRA §604 |

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
| ECOA code mismatch | Different liability designation (Individual vs Joint) | FCRA §623(a)(1) |
| Authorized User derogatory | AU account with negative marks (AU not liable) | FCRA §623(a)(1) / ECOA |
| Missing tradeline | Account appears on some bureaus but missing from others | Informational (explains score gaps) |

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
| Change DOFD inference (parsing) | `app/services/parsing/html_parser.py` |
| Change DOFD inference (SOL/time-barred) | `app/services/audit/rules.py` (`_infer_dofd_from_payment_history`) |
| Add cross-bureau check | `app/services/audit/cross_bureau_rules.py` |
| Change letter sections | `app/services/legal_letter_generator/pdf_format_assembler.py` |
| Update field name display | `app/routers/letters.py` |
| Add new ViolationType | `app/models/ssot.py` or `app/models/__init__.py` |
| Modify state SOL data | `app/services/audit/sol_data.py` |
| Bankruptcy tolling logic | `app/services/audit/rules.py` (`is_sol_tolled_by_bankruptcy`) |
| Bank choice-of-law mapping | `app/services/audit/rules.py` (`check_governing_law_opportunity`) |
| Zombie debt detection | `app/services/audit/rules.py` (`check_zombie_revival_risk`) |
| Add inquiry violation | `app/services/audit/rules.py` (`InquiryRules` class) |
| Inquiry misclassification | `app/services/audit/rules.py` (`InquiryRules.check_inquiry_misclassification`) |
| Collection fishing inquiry | `app/services/audit/rules.py` (`InquiryRules.check_collection_fishing_inquiry`) |
| Duplicate inquiry detection | `app/services/audit/rules.py` (`InquiryRules.check_duplicate_inquiries`) |
| Student loan portfolio mismatch | `app/services/audit/rules.py` (`SingleBureauRules.check_student_loan_portfolio_mismatch`) |
| Identity integrity checks | `app/services/audit/rules.py` (`IdentityRules.check_identity_integrity`) |
| Suffix/Jr/Sr mismatch | `app/services/audit/rules.py` (`IdentityRules.check_suffix_mismatch`) |
| SSN last 4 mismatch | `app/services/audit/rules.py` (`IdentityRules.check_ssn_mismatch`) |
| State mismatch | `app/services/audit/rules.py` (`IdentityRules.check_state_mismatch`) |
| Name mismatch | `app/services/audit/rules.py` (`IdentityRules.check_name_mismatch`) |
| Deceased indicator (account-level) | `app/services/audit/rules.py` (`SingleBureauRules.check_deceased_indicator`) |
| Deceased indicator (consumer-level) | `app/services/audit/rules.py` (`IdentityRules.check_deceased_indicator_consumer`) |
| Child identity theft | `app/services/audit/rules.py` (`SingleBureauRules.check_child_identity_theft`) |
| Public records audit | `app/services/audit/rules.py` (`PublicRecordRules.audit_public_records`) |
| NCAP compliance (judgments/liens) | `app/services/audit/rules.py` (`PublicRecordRules.check_ncap_compliance`) |
| Judgment status (satisfied w/balance) | `app/services/audit/rules.py` (`PublicRecordRules.check_judgment_status`) |
| Bankruptcy dates (future/obsolete) | `app/services/audit/rules.py` (`PublicRecordRules.check_bankruptcy_dates`) |
| Medical debt under $500 | `app/services/audit/rules.py` (`SingleBureauRules.check_medical_debt_compliance`) |
| Paid medical still reporting | `app/services/audit/rules.py` (`SingleBureauRules.check_medical_debt_compliance`) |
| Post-settlement negative (zombie history) | `app/services/audit/rules.py` (`SingleBureauRules.check_post_settlement_reporting`) |
| Missing tradeline (cross-bureau gap) | `app/services/audit/cross_bureau_rules.py` (`CrossBureauRules.check_missing_tradelines`) |

---

## Frontend Dashboard (Dec 2025 Upgrade)

### Architecture Overview

```
frontend/src/
├── layouts/
│   └── DashboardLayout.jsx      # Responsive sidebar + content area
├── pages/
│   ├── DashboardPage.jsx        # Auto-redirect to latest report audit
│   ├── AuditPage.jsx            # Score dashboard + violation list
│   ├── UploadPage.jsx           # PDF report upload
│   ├── ReportHistoryPage.jsx    # List of all uploaded reports
│   ├── LetterPage.jsx           # Letter generation workflow
│   ├── LettersPage.jsx          # My Letters - saved letter history
│   └── ProfilePage.jsx          # User profile management
├── components/
│   ├── ScoreDashboard.jsx       # 3-bureau score cards with circular gauges
│   └── ViolationToggle.jsx      # Violation list with selection toggles
├── state/
│   ├── authStore.js             # Zustand - authentication state
│   └── reportStore.js           # Zustand - report state + latestReportId
├── theme.js                     # MUI theme (blue primary, clean typography)
└── api/
    └── index.js                 # Axios API client
```

### Key Features

| Feature | File | Description |
|---------|------|-------------|
| Smart Dashboard | `DashboardPage.jsx` | Auto-redirects to `/audit/{latestReportId}` or shows empty state |
| Latest Report ID | `reportStore.js` | Zustand store caches `latestReportId` for instant navigation |
| Score Gauges | `ScoreDashboard.jsx` | Circular progress indicators for TU/EX/EQ scores |
| Sidebar Navigation | `DashboardLayout.jsx` | Responsive drawer with mobile hamburger menu |
| Letter History | `LettersPage.jsx` | Lists all saved letters with download/delete options |

### Dashboard Navigation Flow

```
User logs in → DashboardLayout fetches latestReportId
                     ↓
            Navigate to /dashboard
                     ↓
        DashboardPage checks latestReportId
                     ↓
    ┌─────────────────┴─────────────────┐
    ↓                                   ↓
Has report                         No reports
    ↓                                   ↓
<Navigate to="/audit/{id}">     Show "Upload First Report" CTA
```

### State Management (Zustand)

**reportStore.js:**
```javascript
{
  currentReport: null,      // Currently loaded report data
  reports: [],              // List of all reports
  latestReportId: null,     // Cached for instant dashboard redirect
  uploadProgress: 0,        // Upload progress percentage
  isUploading: false,       // Upload in progress flag
  error: null               // Error message
}
```

**Key actions:**
- `fetchLatestReportId()` - Called on mount to get most recent report
- `uploadReport(file)` - Handles PDF upload with progress tracking
- `fetchReport(reportId)` - Loads specific report data

---

## Letter Generation Data Sources

### Consumer Address Priority (Dec 2025 Fix)

**File:** `app/routers/letters.py` - `reconstruct_consumer()`

Consumer data is now sourced in priority order:

1. **User Profile (UserDB)** - Preferred source
   - `first_name`, `middle_name`, `last_name`, `suffix`
   - `street_address`, `unit`, `city`, `state`, `zip_code`

2. **Parsed Report (ReportDB)** - Fallback only
   - `consumer_name`, `consumer_address`
   - `consumer_city`, `consumer_state`, `consumer_zip`

**Why this matters:**
- Parsed credit report addresses often have formatting issues
- User profile data is manually entered and verified
- Prevents issues like "NY10026-" (missing space, trailing dash)

### Address Formatting

**File:** `app/services/legal_letter_generator/pdf_format_assembler.py` - `_format_city_state_zip()`

Handles edge cases:
- Removes trailing punctuation: "10026-," → "10026"
- Fixes state/zip concatenation: "NY10026" → "NY 10026"
- Cleans up double commas: "CITY,, STATE" → "CITY, STATE"

---

## FDCPA Parity & Multi-Statute System (Dec 2025)

### Overview

The system now supports multi-statute violations with FCRA, FDCPA, and future statute types. Violations can have:
- **Primary statute**: The main legal basis for the violation
- **Secondary statutes**: Supporting/corroborating legal claims
- **Stacking**: Multiple related violations grouped into one logical violation

### New Files Created

```
app/services/legal_letter_generator/
├── fdcpa_statutes.py      # FDCPA SSOT with 60+ statute entries
├── violation_statutes.py   # Unified statute routing (StatuteType, ActorType enums)
└── citation_utils.py       # Citation normalization to canonical format
```

### FDCPA Statute System (`fdcpa_statutes.py`)

**Purpose:** Single Source of Truth for FDCPA statute definitions and resolution.

**Key Components:**
| Component | Description |
|-----------|-------------|
| `FDCPA_STATUTE_MAP` | 60+ statute entries with section, title, description |
| `resolve_fdcpa_statute(section)` | Converts any format to canonical "15 U.S.C. § {section}" |
| `FDCPA_ACTOR_SCOPE` | Defines which actors FDCPA applies to (collector, debt_buyer) |
| `CREDIT_REPORT_DETECTABLE_SECTIONS` | FDCPA sections detectable from credit reports |

**Authorized FDCPA Rules (Credit-Report-Detectable):**
| Section | Violation Type | Description |
|---------|---------------|-------------|
| §1692e(5) | time_barred_debt_risk | Threat on time-barred debt |
| §1692e(2)(A) | false_debt_status | False legal status |
| §1692e(8) | unverified_debt_reporting | False credit reporting |
| §1692f(1) | collection_balance_inflation | Unauthorized amounts/balance inflation |

**Excluded from Automation (Not Credit-Report-Detectable):**
- §1692g (validation timing) - requires communication analysis
- §1692c/§1692d (communications, harassment) - requires call/letter analysis

### Unified Statute Routing (`violation_statutes.py`)

**Purpose:** Route violations to correct statutes based on violation type AND actor type.

**Key Enums:**
```python
class StatuteType(str, Enum):
    FCRA = "fcra"
    FDCPA = "fdcpa"
    ECOA = "ecoa"
    STATE = "state"
    # ... future expansion

class ActorType(str, Enum):
    BUREAU = "bureau"
    FURNISHER = "furnisher"
    COLLECTOR = "collector"
    ORIGINAL_CREDITOR = "original_creditor"
    DEBT_BUYER = "debt_buyer"
```

**Key Functions:**
| Function | Description |
|----------|-------------|
| `get_primary_statute(violation_type, actor_type)` | Returns primary statute for violation |
| `get_applicable_citations(violation_type, actor_type)` | Returns all applicable statutes |
| `map_furnisher_type_to_actor(furnisher_type)` | Maps FurnisherType enum to actor string |

### Citation Normalization (`citation_utils.py`)

**Purpose:** Normalize all citation formats to canonical "15 U.S.C. § {section}" format.

**Handles Input Formats:**
- "FDCPA 1692e(5)" → "15 U.S.C. § 1692e(5)"
- "§1692e(5)" → "15 U.S.C. § 1692e(5)"
- "15 USC 1692e(5)" → "15 U.S.C. § 1692e(5)"
- "611" (FCRA) → "15 U.S.C. § 1681i"

**Key Functions:**
| Function | Description |
|----------|-------------|
| `normalize_citation(citation)` | Converts any format to canonical |
| `_detect_statute_type(citation)` | Detects FCRA vs FDCPA from citation |
| `format_citation_for_letter(citation)` | Formats for consumer-facing output |

### Inquiry Violation Stacking (`rules.py` lines 3226-3373)

**Purpose:** Group related inquiry violations by creditor+bureau+date into ONE stacked violation.

**Location:** `app/services/audit/rules.py` - `InquiryRules._stack_inquiry_violations()`

**Stacking Logic:**
1. Run all inquiry checks independently (fishing, duplicate, misclassification)
2. Group violations by (normalized_creditor, bureau, date)
3. Sort by priority: fishing > misclassification > duplicate
4. Create ONE stacked violation with:
   - Primary statute: highest priority violation
   - Secondary statutes: other violations as supporting evidence
   - Merged evidence: shows total violation count

**Priority Order:**
| Priority | Violation Type | Rationale |
|----------|---------------|-----------|
| 1 | COLLECTION_FISHING_INQUIRY | Strongest claim (no permissible purpose) |
| 2 | INQUIRY_MISCLASSIFICATION | Industry shouldn't do hard pulls |
| 3 | DUPLICATE_INQUIRY | Technical/procedural issue |

**Example (ALLY FINANCIAL):**
```
Input: 2 hard inquiries on 12/28/2023, Experian, no tradeline
  → 2 COLLECTION_FISHING_INQUIRY violations
  → 1 DUPLICATE_INQUIRY violation
  → Total: 3 raw violations

Output: 1 stacked violation
  → Primary: COLLECTION_FISHING_INQUIRY (15 U.S.C. § 604(a)(3)(A))
  → Secondary: ['15 U.S.C. § 604(a)(3)'] (duplicate as supporting evidence)
  → Evidence: stacked_violation=True, violation_count=3
```

### Violation Model Updates (`ssot.py` lines 469-533)

**New Fields on Violation class:**
```python
@dataclass
class Violation:
    # ... existing fields ...
    primary_statute: Optional[str] = None      # "15 U.S.C. § 604(a)(3)(A)"
    primary_statute_type: Optional[str] = None # "fcra", "fdcpa", etc.
    secondary_statutes: Optional[List[str]] = None  # Supporting statutes
```

**Backward Compatibility:**
- `__post_init__()` auto-migrates legacy `fcra_section` to `primary_statute`
- Uses `normalize_citation()` for consistent format

### Letter Rendering Fixes (`pdf_format_assembler.py`)

**Issue:** Inquiry violations weren't rendering because:
1. Categories missing from `category_order` list
2. No handlers in `_format_account_bullet()` for inquiry types

**Fix 1: Added Categories to Render Order (lines 1554-1597)**
```python
category_order = [
    # ... existing categories ...
    # Inquiry violations (FCRA § 604)
    ViolationCategory.UNAUTHORIZED_INQUIRY,
    ViolationCategory.DUPLICATE_INQUIRY,
    ViolationCategory.INQUIRY_MISCLASSIFICATION,
    # ... rest of categories ...
]
```

**Fix 2: Added Inquiry Bullet Handlers (lines 1040-1140)**

| Violation Type | Handler Output |
|---------------|----------------|
| `collection_fishing_inquiry` | Inquiry date, bureau, no-tradeline evidence, numerosity language (if duplicate), stacked violations |
| `duplicate_inquiry` | Double-tap detection, dates, same-day/window info |
| `inquiry_misclassification` | Industry type, soft/hard classification error |

### Explicit Numerosity Language (lines 1063-1094)

**Purpose:** CRAs process disputes operationally, not legally. Explicit language improves deletion outcomes.

**Trigger Condition:**
- Stacked violation includes `DUPLICATE_INQUIRY` in secondary_violations
- Same date, same bureau (guaranteed by stacking logic)

**Canonical Sentence Template:**
```
On {inquiry_date}, {creditor_name} accessed my {bureau_name} consumer report
{inquiry_count} separate times in connection with a single credit application,
without any resulting account or tradeline.
```

**Count Formatting:**
| Count | Rendered As |
|-------|-------------|
| 2 | "two (2) separate times" |
| 3 | "three (3) separate times" |
| N | "{N} ({N}) separate times" |

**Safety Constraints:**
- Only renders when data is certain (stacked + has duplicate evidence + date + bureau present)
- Does NOT inject for single violations
- Does NOT inject without duplicate_inquiry in secondary_violations
- Does NOT alter statute hierarchy or stacking logic

**Sample Output (with numerosity):**
```
I. Unauthorized Hard Inquiries - No Permissible Purpose (FCRA § 604(a)(3)(A))

• ALLY FINANCIAL: Hard Inquiry Date: December 28, 2023; Bureau: EXPERIAN;
  No associated tradeline, account, or loan found on credit file;
  Without a legitimate business transaction, creditor lacks permissible
  purpose under 15 U.S.C. § 1681b(a)(3)(A)

  On December 28, 2023, ALLY FINANCIAL accessed my EXPERIAN consumer report
  two (2) separate times in connection with a single credit application,
  without any resulting account or tradeline.

  SUPPORTING EVIDENCE (3 total violations grouped):
    • Collection Fishing Inquiry (FCRA § 604(a)(3)(A))
    • Duplicate Inquiry (FCRA § 604(a)(3))
```

### Quick Reference - New Logic Locations

| Feature | File | Location |
|---------|------|----------|
| FDCPA statute definitions | `fdcpa_statutes.py` | Full file |
| Unified statute routing | `violation_statutes.py` | Full file |
| Citation normalization | `citation_utils.py` | Full file |
| Inquiry violation stacking | `rules.py` | `InquiryRules._stack_inquiry_violations()` (lines 3226-3337) |
| Stacked violation creation | `rules.py` | `InquiryRules.audit_inquiries()` (lines 3339-3373) |
| Inquiry category configs | `pdf_format_assembler.py` | `CATEGORY_CONFIGS` (lines 378-428) |
| Inquiry bullet formatters | `pdf_format_assembler.py` | `_format_account_bullet()` (lines 1040-1140) |
| Explicit numerosity language | `pdf_format_assembler.py` | `_format_account_bullet()` (lines 1063-1094) |
| Category render order | `pdf_format_assembler.py` | `category_order` (lines 1554-1597) |
| Violation model fields | `ssot.py` | `Violation` class (lines 469-533) |

### Testing

**Test File:** `tests/test_statute_system.py`

**Test Categories:**
1. `TestFDCPAStatutes` - FDCPA resolution and mapping
2. `TestViolationStatutes` - Unified routing
3. `TestCitationUtils` - Citation normalization
4. `TestViolationModelBackwardCompat` - Legacy migration
5. `TestInquiryStacking` - Stacking logic

**Run Tests:**
```bash
cd backend
python3 -m pytest tests/test_statute_system.py -v
```

---

## Related Documentation

- `letter_fixes.md` - Recent fixes and Metro 2 field reference
- `system_checklist.md` - Full violation coverage checklist
- `violation_comparison.xlsx` - Comparison with industry standards
