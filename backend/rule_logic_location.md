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
| Balance > High Credit (Installment) | `balance_exceeds_high_credit` | Field 21 & Field 12 (MEDIUM severity) |
| Balance > High Credit (Student Loan) | `student_loan_capitalized_interest` | Field 21 & Field 12 (LOW severity - review only) |
| Balance > High Credit (Mortgage) | `mortgage_balance_review` | Field 21 & Field 12 (LOW severity - review only) |
| Balance > Credit Limit (Revolving only) | `balance_exceeds_credit_limit` | Field 21 & Field 16 |
| Negative Balance | `negative_balance` | Field 21 (Current Balance) |
| Negative Credit Limit | `negative_credit_limit` | Field 16 (Revolving only) |
| Collection Balance Inflation | `collection_balance_inflation` | Field 21 & Field 12 (FDCPA §1692f - HIGH severity) |
| Status/Payment History Mismatch | `status_payment_history_mismatch` | Field 17A & Field 18 |
| Phantom Late Payment | `phantom_late_payment` | Field 15/25 (late markers during $0 due or forbearance) |
| Paid Status with Balance | `paid_status_with_balance` | Field 17A & Field 21 (status=Paid but balance>$0) |
| Zero Balance Not Paid | `zero_balance_not_paid` | Field 17A (collection with $0 but not marked Paid) |
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

### B6 Balance Rules System (CRRG 2024-2025 Compliant)

**Authoritative Metro 2 Field Reference:**

| Field # | Name | Purpose |
|---------|------|---------|
| **Field 12** | High Credit / Original Loan Amount | Installment/Student Loans/Mortgages |
| **Field 16** | Credit Limit | Revolving accounts ONLY |
| **Field 17A** | Account Status Code | Status indicator (NEVER monetary) |
| **Field 18** | Payment History Profile | 24-month payment pattern |
| **Field 19** | Amount Past Due | Past due balance |
| **Field 21** | Current Balance | Current balance owed |

**Balance Rule Matrix (Account Type Scoped):**

| Account Type | Comparison | Metro 2 Fields | Severity | Auto-Dispute |
|--------------|------------|----------------|----------|--------------|
| **Revolving** | Balance > Credit Limit | Field 21 vs Field 16 | MEDIUM | YES |
| **Revolving** | Balance > High Credit | — | NEVER FIRE | NO |
| **Installment** | Balance > High Credit | Field 21 vs Field 12 | *Threshold-Gated* | *Conditional* |
| **Student Loan** | Balance > High Credit | Field 21 vs Field 12 | LOW | NO (review only) |
| **Mortgage** | Balance > High Credit | Field 21 vs Field 12 | LOW | NO (review only) |
| **Collection** | Balance > Original Debt | Field 21 vs Field 12 | HIGH | YES (FDCPA §1692f) |

**Installment Loan Threshold-Based Severity Gating:**

| Condition | Severity | Auto-Dispute | Rationale |
|-----------|----------|--------------|-----------|
| Overage < 3% OR < $100 | LOW | NO | Likely fees/noise |
| Overage ≥ 3% AND ≥ $100 | MEDIUM | YES | Material deviation |

*Conservative gating: MEDIUM requires BOTH thresholds exceeded.*

**Critical Scoping Rules:**

1. **Field 17A (Account Status)** — NEVER cite for monetary discrepancies
2. **Field 16 (Credit Limit)** — Revolving accounts ONLY (credit cards, HELOCs)
3. **Field 12 (High Credit)** — Installment, Student Loan, Mortgage, Collection
4. **Student Loans** — Capitalized interest is LEGAL; LOW severity, review-only
5. **Mortgages** — Escrow/negative amortization possible; LOW severity, review-only
6. **Collections** — Balance increases are PRESUMPTIVELY UNLAWFUL under FDCPA §1692f(1)

**Student Loan Detection Keywords:**
```
educational, student loan, student, dept of ed, dept ed, nelnet, navient,
mohela, fedloan, sallie mae, great lakes, acs education, edfinancial,
pheaa, ecmc, firstmark, cornerstone, granite state, osla, tiva,
department of education
```

**Mortgage Detection Keywords:**
```
mortgage, home loan, real estate, mtg, heloc, home equity, deed of trust,
fannie mae, freddie mac, va loan, fha loan, usda loan, jumbo loan,
conventional loan
```

**Collection Balance Inflation (FDCPA §1692f):**
- Presumption: Balance increase by collector is UNLAWFUL
- Consumer payments are NON-EXCULPATORY (do not prove authorization)
- Requires explicit authorization to downgrade severity:
  - Contractual post-default interest
  - Court judgment with interest award
  - State law permitting post-charge-off interest

---

### B6 K1 Segment Scope Guard (December 2024)

**Issue:** OC charge-offs were triggering false K1 (Missing Original Creditor) violations.

**Root Cause:** The furnisher classification logic in `html_parser.py` uses `combined_text` (which includes status) to detect collectors. When status contains "collection" (e.g., "Collection/Chargeoff"), the account gets classified as `COLLECTOR` even when it's an Original Creditor reporting their own charged-off account.

**Metro 2 Rule (CRRG 2024-2025):**
- K1 Segment (Original Creditor Name) is ONLY required for:
  - Account Type 48 (Collection Agency/Attorney)
  - Account Type 0C (Debt Purchaser)
- K1 is NOT required when the reporting entity IS the Original Creditor

**Scope Guard Location:** `app/services/audit/rules.py` → `FurnisherRules.check_collector_missing_original_creditor()`

**Guard Logic:**
```python
# K1 only fires if creditor NAME contains collection agency keywords
collection_agency_keywords = [
    "collection", "coll svcs", "recovery", "midland", "lvnv",
    "cavalry", "encore", "portfolio recovery", "convergent",
    "ic system", "transworld", "debt buyer", etc.
]
is_collection_agency = any(kw in creditor_lower for kw in collection_agency_keywords)

# Suppress K1 if creditor name doesn't indicate a collection agency
if not is_collection_agency:
    return violations  # No K1 violation for OCs like VERIZON, CAPITAL ONE, etc.
```

**Result:**
| Scenario | K1 Violation? |
|----------|---------------|
| VERIZON (OC) with collection status | ❌ Suppressed |
| MIDLAND CREDIT missing K1 | ✅ Fires (HIGH) |
| PORTFOLIO RECOVERY missing K1 | ✅ Fires (HIGH) |

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
| Contradiction Engine (all rules) | `app/services/audit/contradiction_engine.py` |
| Phase 1 contradictions (D1-A2) | `app/services/audit/contradiction_engine.py` (`_check_phase1_contradictions`) |
| Phase 2.1 contradictions (X1, K1, P1) | `app/services/audit/contradiction_engine.py` (`_check_phase21_contradictions`) |
| Contradiction ViolationType enums | `app/models/ssot.py` |
| Primary remedy determination | `app/services/enforcement/response_letter_generator.py` (`determine_primary_remedy`) |
| Dynamic demanded actions | `app/services/enforcement/response_letter_generator.py` (`generate_demanded_actions`) |

---

## Contradiction Engine (Dec 2025)

### Overview

The Contradiction Engine is a deterministic audit system that detects internal data contradictions within tradeline data. Unlike violation rules that check regulatory compliance, contradictions identify logical impossibilities that prove data inaccuracy.

**Primary File:** `app/services/audit/contradiction_engine.py`

### Architecture

```
app/services/audit/
├── contradiction_engine.py    # Contradiction detection engine
├── rules.py                   # Existing violation rules (separate)
└── engine.py                  # Main audit orchestration
```

### Contradiction vs Violation

| Aspect | Violation | Contradiction |
|--------|-----------|---------------|
| What it detects | Regulatory non-compliance | Logical impossibility |
| Example | Missing DOFD (Metro 2 required) | Balance increased after charge-off |
| Legal basis | FCRA §623, Metro 2 standards | Data accuracy / self-refutation |
| Use case | Initial dispute letter | Response enforcement letter |

### Phase 1 Contradictions (Core Rules)

| ID | Name | Severity | Detection Logic |
|----|------|----------|-----------------|
| D1 | Missing DOFD on Derogatory | CRITICAL | Derogatory status but no DOFD date |
| T1 | DOFD Before Open Date | HIGH | DOFD predates account open date |
| S1 | Status/Balance Contradiction | HIGH | Chargeoff/Collection but $0 balance |
| S2 | Closed Status Active Payments | HIGH | Closed status with recent scheduled payment |
| B1 | Negative Balance Contradiction | HIGH | Balance reported as negative |
| M1 | Balance Exceeds Original (Collection) | HIGH | Collection balance > original debt |
| M2 | Balance Increase After Chargeoff | HIGH | Balance increased post-chargeoff |
| A1 | Impossible Payment History | MEDIUM | Payments reported before account opened |
| A2 | Payment Amount Exceeds Balance | MEDIUM | Payment > balance (installment only) |

### Phase 2.1 Contradictions (Additional Rules)

| ID | Name | Severity | Detection Logic |
|----|------|----------|-----------------|
| X1 | Stale Data | MEDIUM | Last activity date older than status updates |
| K1 | Missing Original Creditor Elevated | MEDIUM | Collection/debt buyer without original creditor |
| P1 | Missing Scheduled Payment | MEDIUM | Scheduled payment exists but no payment history |

### Key Classes

**ContradictionEngine:**
```python
class ContradictionEngine:
    """Deterministic contradiction detection engine."""

    def analyze_account(self, account: Dict[str, Any]) -> List[Contradiction]:
        """Run all contradiction checks on a single account."""

    def analyze_accounts(self, accounts: List[Dict[str, Any]]) -> Dict[str, List[Contradiction]]:
        """Run contradiction analysis on multiple accounts."""
```

**Contradiction (dataclass):**
```python
@dataclass
class Contradiction:
    rule_id: str           # e.g., "D1", "T1", "M2"
    rule_name: str         # e.g., "MISSING_DOFD_DEROGATORY"
    severity: str          # CRITICAL, HIGH, MEDIUM
    field_a: str           # First field in contradiction
    value_a: Any           # Value of first field
    field_b: str           # Second field in contradiction
    value_b: Any           # Value of second field
    explanation: str       # Human-readable explanation
    violation_type: str    # ViolationType enum value
```

### Detection Methods (contradiction_engine.py)

| Method | Rules Checked | Lines |
|--------|---------------|-------|
| `_check_phase1_contradictions()` | D1, T1, S1, S2, B1, M1, M2, A1, A2 | ~50-200 |
| `_check_phase21_contradictions()` | X1, K1, P1 | ~200-300 |
| `_check_d1_missing_dofd()` | D1 | Individual |
| `_check_t1_dofd_before_open()` | T1 | Individual |
| `_check_s1_status_balance()` | S1 | Individual |
| `_check_s2_closed_active_payments()` | S2 | Individual |
| `_check_b1_negative_balance()` | B1 | Individual |
| `_check_m1_balance_exceeds_original()` | M1 | Individual |
| `_check_m2_balance_increase_chargeoff()` | M2 | Individual |
| `_check_a1_impossible_payment_history()` | A1 | Individual |
| `_check_a2_payment_exceeds_balance()` | A2 | Individual |
| `_check_x1_stale_data()` | X1 | Individual |
| `_check_k1_missing_original_creditor_elevated()` | K1 | Individual |
| `_check_p1_missing_scheduled_payment()` | P1 | Individual |

### ViolationType Enums (ssot.py)

Phase 1 and 2.1 contradictions are mapped to ViolationType enums for consistency:

```python
# PHASE-1 CONTRADICTIONS
MISSING_DOFD_DEROGATORY = "missing_dofd_derogatory"  # D1: CRITICAL
DOFD_BEFORE_OPEN_DATE = "dofd_before_open_date"      # T1: HIGH
STATUS_BALANCE_CONTRADICTION = "status_balance_contradiction"  # S1: HIGH
CLOSED_STATUS_ACTIVE_PAYMENTS = "closed_status_active_payments"  # S2: HIGH
NEGATIVE_BALANCE_CONTRADICTION = "negative_balance_contradiction"  # B1: HIGH
BALANCE_EXCEEDS_ORIGINAL_COLLECTION = "balance_exceeds_original_collection"  # M1: HIGH
BALANCE_INCREASE_AFTER_CHARGEOFF = "balance_increase_after_chargeoff"  # M2: HIGH
IMPOSSIBLE_PAYMENT_HISTORY = "impossible_payment_history"  # A1: MEDIUM
PAYMENT_AMOUNT_EXCEEDS_BALANCE = "payment_amount_exceeds_balance"  # A2: MEDIUM

# PHASE-2.1 ADDITIONAL CONTRADICTIONS
STALE_DATA = "stale_data"  # X1: MEDIUM
MISSING_ORIGINAL_CREDITOR_ELEVATED = "missing_original_creditor_elevated"  # K1: MEDIUM
MISSING_SCHEDULED_PAYMENT_CONTRADICTION = "missing_scheduled_payment_contradiction"  # P1: MEDIUM
```

### Quick Reference - Contradiction Engine

| Task | File |
|------|------|
| Add new contradiction rule | `app/services/audit/contradiction_engine.py` |
| Add ViolationType for contradiction | `app/models/ssot.py` |
| View contradiction severity levels | `app/services/audit/contradiction_engine.py` → `Severity` class |
| Run contradiction analysis | `ContradictionEngine().analyze_account(account)` |
| Test contradictions | `test_contradiction_engine.py` |

---

## Phase 3: Deterministic Demand Prioritization (Dec 2025)

### Overview

Phase 3 introduces deterministic demand prioritization that analyzes contradiction severity to determine the primary remedy and ordered Demanded Actions for VERIFIED and REJECTED response letters.

**Primary File:** `app/services/enforcement/response_letter_generator.py`

### Primary Remedy Types

| Remedy | When Applied |
|--------|--------------|
| `IMMEDIATE_DELETION` | Any CRITICAL contradiction OR 2+ HIGH contradictions |
| `CORRECTION_WITH_DOCUMENTATION` | 1 HIGH contradiction OR any MEDIUM contradictions |
| `STANDARD_PROCEDURAL` | No contradictions detected |

### Determination Rules (Deterministic)

```python
def determine_primary_remedy(contradictions: Optional[List[Any]]) -> str:
    """
    Rules:
    1. If any contradiction has severity = CRITICAL → IMMEDIATE_DELETION
    2. Else if 2+ contradictions have severity = HIGH → IMMEDIATE_DELETION
    3. Else if 1 HIGH or any MEDIUM contradictions exist → CORRECTION_WITH_DOCUMENTATION
    4. Else → STANDARD_PROCEDURAL (fall back to statutory demands)
    """
```

### Demanded Actions by Remedy

**IMMEDIATE_DELETION:**
1. Immediately delete the disputed tradeline
2. Provide written confirmation within 5 business days
3. Notify all entities to whom data was furnished

**CORRECTION_WITH_DOCUMENTATION:**
1. Correct and update all inaccurate data fields
2. Provide documentation supporting corrections
3. Furnish corrected data to all agencies

**STANDARD_PROCEDURAL:**
1. Complete investigation within statutory timeframe
2. Provide results in writing per 15 USC §1681i(a)(6)

### Integration with Response Letters

Only VERIFIED and REJECTED letters use Phase 3 logic:

```python
# In generate_verified_letter():
primary_remedy = determine_primary_remedy(contradictions)
actions = generate_demanded_actions(primary_remedy, canonical_entity, "VERIFIED")
demands = format_demanded_actions_section(actions)
letter_parts.append(demands)
```

NO_RESPONSE and REINSERTION letters remain unchanged (they have fixed statutory demands).

### Key Functions (response_letter_generator.py)

| Function | Purpose | Lines |
|----------|---------|-------|
| `determine_primary_remedy()` | Analyze contradictions → remedy type | ~100-140 |
| `generate_demanded_actions()` | Remedy → ordered action list | ~145-200 |
| `format_demanded_actions_section()` | Action list → formatted letter section | ~205-230 |

### Quick Reference - Phase 3

| Task | File |
|------|------|
| Modify remedy determination logic | `app/services/enforcement/response_letter_generator.py` → `determine_primary_remedy()` |
| Add new remedy type | `app/services/enforcement/response_letter_generator.py` → `PrimaryRemedy` class |
| Modify demanded actions | `app/services/enforcement/response_letter_generator.py` → `generate_demanded_actions()` |
| Test Phase 3 logic | `test_contradiction_engine.py` → Phase 3 tests |

---

## Copilot Engine (Dec 2025)

### Purpose

The Copilot Engine is a goal-oriented enforcement prioritization system that sits above the Audit Engine and Response Engine. It translates a user's financial goal (mortgage, auto loan, etc.) into a prioritized attack plan.

**Key Principle:** Impact is **goal-relative**, not severity-relative. A $200 collection blocks a mortgage application more than a $20,000 chargeoff blocks an apartment rental.

### Architecture

```
User selects goal → ProfilePage.jsx
         ↓
Goal stored → UserDB.credit_goal
         ↓
Report audited → AuditEngine + ContradictionEngine
         ↓
Copilot analyzes:
   1. Apply DOFD stability gate (GATE A)
   2. Apply Ownership gate (GATE B)
   3. Classify blockers (goal-relative impact)
   4. Generate attack plan (priority-ordered)
   5. Generate skip list (FCRA-native reasons)
         ↓
Output → CopilotRecommendation
```

### Files

| File | Purpose |
|------|---------|
| `app/models/copilot_models.py` | Dataclasses, enums, goal requirements |
| `app/services/copilot/copilot_engine.py` | Main analysis engine |
| `app/routers/copilot.py` | API endpoints |
| `test_copilot_engine.py` | Unit tests (43 tests) |

### Credit Goals

| Goal | Key Requirements |
|------|------------------|
| `mortgage` | Zero collections/chargeoffs/lates, 4+ tradelines, 2+ revolving |
| `auto_loan` | 1 collection allowed, focus on chargeoffs |
| `prime_credit_card` | Utilization <10%, inquiry sensitive |
| `apartment_rental` | Evictions/collections focus |
| `employment` | **Zero public records required** (bankruptcies/judgments) |
| `credit_hygiene` | Balanced approach to all negatives |

### MANDATORY CONSTRAINTS

1. **NO SOL LOGIC** - Zero statute-of-limitations reasoning. Copilot never reasons about SOL.
2. **FCRA-native skip codes only** - See below
3. **Impact = goal-relative** (not severity-relative)
4. **Two dependency gates** applied BEFORE scoring
5. **Employment = zero public records required**

### Two Dependency Gates

**GATE A: DOFD Stability** (`_apply_dofd_stability_gate`)

If ANY blocker has:
- `dofd_missing = True`
- OR `rule_code in {"D1", "D2", "D3"}`

THEN:
- Force DOFD/aging actions to priority 1
- Suppress balance/status deletions until DOFD resolved

**GATE B: Ownership** (`_apply_ownership_gate`)

If furnisher is:
- Collection agency
- Debt buyer
- Unknown chain-of-title

THEN:
- Ownership/authority actions precede deletion posture
- Must establish who owns debt before demanding deletion

### Skip Codes (FCRA-Native Only)

| Code | Rationale |
|------|-----------|
| `DOFD_UNSTABLE` | DOFD missing/unstable; attacking may refresh/re-age account |
| `REINSERTION_LIKELY` | High probability item returns after deletion |
| `POSITIVE_LINE_LOSS` | Attacking removes positive tradeline age/limit |
| `UTILIZATION_SHOCK` | Deleting revolving line spikes overall utilization |
| `TACTICAL_VERIFICATION_RISK` | May force "verified with updated fields" outcome |

**CRITICAL:** NO SOL-based skip codes. Copilot does not reason about time-barred debt.

### Priority Formula

```
priority = impact × deletability ÷ (1 + risk)
```

| Factor | Scale | Description |
|--------|-------|-------------|
| Impact | 1-10 | Goal-relative blocking severity |
| Deletability | 0.2 / 0.6 / 1.0 | LOW / MEDIUM / HIGH |
| Risk | 0-5 | Skip code risk factors |

### Goal-Relative Impact Scoring

```python
def _calculate_goal_relative_impact(goal, target, category) -> int:
    """
    Impact = how much this item blocks the target credit state.
    NOT severity-based.
    """
    if goal == CreditGoal.MORTGAGE:
        if category == "collection": return 10  # Absolute blocker
        if category == "chargeoff": return 10
        if category == "late": return 8
        if category == "inquiry": return 4

    elif goal == CreditGoal.EMPLOYMENT:
        if category == "public_record": return 10  # CRITICAL
        if category == "collection": return 9
        if category == "chargeoff": return 5  # Less critical

    elif goal == CreditGoal.APARTMENT_RENTAL:
        if category == "collection": return 6  # More tolerant
        if category == "public_record": return 8
```

### API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/copilot/goals` | GET | List available goals with descriptions |
| `/copilot/goals/{goal_code}/requirements` | GET | Get target state for a goal |
| `/copilot/recommendation/{report_id}` | GET | Generate recommendation for report |
| `/copilot/analyze` | POST | Run analysis with provided data |

### Quick Reference - Copilot Engine

| Task | File |
|------|------|
| Add new credit goal | `app/models/copilot_models.py` → `CreditGoal` enum + `GOAL_REQUIREMENTS` |
| Modify impact scoring | `app/services/copilot/copilot_engine.py` → `_calculate_goal_relative_impact()` |
| Add new skip code | `app/models/copilot_models.py` → `SkipCode` enum |
| Modify dependency gates | `app/services/copilot/copilot_engine.py` → `_apply_dofd_stability_gate()` / `_apply_ownership_gate()` |
| Modify priority formula | `app/services/copilot/copilot_engine.py` → `_generate_attack_plan()` |
| Test Copilot logic | `test_copilot_engine.py` |

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

## Frontend UI Improvements (Dec 2025)

### Violation List Redesign

**Purpose:** Unify the violation display with a clean table-style layout matching the Report History page design.

**Files Modified:**
```
frontend/src/components/
├── ViolationList.jsx           # Main violation list with integrated tabs
├── VirtualizedViolationList.jsx # Table-style grouped violations
└── AccountAccordion.jsx         # Added embedded prop for inline rendering
```

### Changes Made

**1. Removed Redundant Header**
- Removed "X Violations Found" header from ViolationList
- Count already shown in CompactFilterBar stats
- Location: `AuditPage.jsx` passes `hideHeader` prop

**2. Unified Table Container**
- All tabs now wrapped in single TableContainer with Paper
- Tabs integrated into table header area (not separate)
- Rounded corners, border styling matching ReportHistoryPage

**3. Dynamic Column Headers**
| Tab | Column 1 | Column 2 |
|-----|----------|----------|
| Group by Type | Violation Type | Count |
| Group by Account | Violation Type | Count |
| Group by Bureau | Violation Type | Count |
| Cross-Bureau | Account | Issues |
| Accounts | Account | Count |

**4. Consistent Table Format for All Tabs**
- Cross-Bureau: Groups discrepancies by creditor name
- Accounts: Lists all accounts with bureau count
- Same CollapsibleTableRow component used across tabs

**5. CollapsibleTableRow Component** (`ViolationList.jsx` lines 48-80)
```jsx
const CollapsibleTableRow = ({ label, count, isExpanded, onToggle, children }) => (
  // TableRow with expand/collapse icon
  // Collapse section for children content
);
```

**6. AccountAccordion Embedded Mode** (`AccountAccordion.jsx` line 52)
```jsx
const AccountAccordion = React.memo(({ account, embedded = false }) => {
  // embedded=true: Returns content only (no Paper wrapper, no header)
  // embedded=false: Full standalone card with header and collapse
});
```

### Quick Reference - Frontend Logic Locations

| Feature | File | Location |
|---------|------|----------|
| Unified table container | `ViolationList.jsx` | Lines 204-339 |
| Integrated tabs | `ViolationList.jsx` | Lines 215-235 |
| Dynamic column headers | `ViolationList.jsx` | `getColumnHeaders()` (lines 143-153) |
| CollapsibleTableRow | `ViolationList.jsx` | Lines 48-80 |
| Cross-Bureau table format | `ViolationList.jsx` | Lines 275-308 |
| Accounts table format | `ViolationList.jsx` | Lines 311-338 |
| Group header row | `VirtualizedViolationList.jsx` | `GroupHeaderRow` (lines 25-70) |
| AccountAccordion embedded | `AccountAccordion.jsx` | Lines 238-241 |

### Visual Design

**Consistent Shadow Styling:**
All card-like components use the same shadow for visual consistency:
```javascript
boxShadow: '0 2px 8px rgba(0,0,0,0.08)'
borderRadius: 3
```

Applied to:
- `ScoreDashboard.jsx` - Score cards (line 88)
- `CompactFilterBar.jsx` - Filter bar (line 169)
- `AuditPage.jsx` - Action bar (line 129)
- `ViolationList.jsx` - Table container (line 210)

**Table Styling:**
- `TableContainer` with `Paper`, `elevation={0}`, `borderRadius: 3`
- Header bg: `#f9fafb`
- Row hover: `#f1f5f9`
- Expanded row bg: `#f8fafc`
- Collapsed content bg: `#fafafa`

**Icons:**
- `ChevronRightIcon` - collapsed state
- `ExpandMoreIcon` - expanded state

### Score Card Lender Tiers

Score cards display "Estimated Lender Tier" based on credit score ranges:

| Tier | Name | Score Range |
|------|------|-------------|
| 1 | Prime / Super Prime | 720+ |
| 2 | Prime / Near-Prime | 680-719 |
| 3 | Subprime Tier 3 | 630-679 |
| 4 | Subprime Tier 4 | 550-629 |
| 5 | Deep Subprime | <550 |

**Implementation:** `ScoreDashboard.jsx` - `getLenderTier()` function (lines 27-35)

**Goal Progress** shows points needed to reach next tier:
- From Deep Subprime: X pts to Tier 4
- From Tier 4: X pts to Tier 3
- From Tier 3: X pts to Near-Prime
- From Near-Prime: X pts to Prime
- At Prime: "Top Tier!"

### Violation List Tabs Header

The violation list uses a unified tabs header with count label:
- Tabs on left, "Count" label on right
- No separate column header row
- Dynamic content based on selected tab

```javascript
// ViolationList.jsx - Tabs header with count (lines 214-230)
<Box sx={{
  bgcolor: '#f9fafb',
  borderBottom: '1px solid',
  borderColor: 'divider',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  pr: 2,
}}>
  <Tabs>...</Tabs>
  <Typography variant="body2" sx={{ fontWeight: 600 }}>Count</Typography>
</Box>
```

### Filter Bar Stats

The filter bar displays only essential stats:
- Accounts count (with AccountBalanceIcon)
- Violations count (with WarningIcon)

Removed: Critical count, Clean count (not actionable)

### Landing Page Navbar

Full-width navbar with edge-to-edge positioning:
```javascript
// LandingPage.jsx - Navbar (lines 42-68)
<Box sx={{
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  py: 2.5,
  px: { xs: 3, md: 6 }  // Pushes logo left, links right
}}>
  {/* Logo on left */}
  <Stack direction="row" spacing={5}>  {/* spacing={5} for more gap between links */}
    {/* Nav links on right */}
  </Stack>
</Box>
```

---

## Related Documentation

- `letter_fixes.md` - Recent fixes and Metro 2 field reference
- `system_checklist.md` - Full violation coverage checklist
- `docs/UNIFIED_RESPONSE_SYSTEM.md` - Complete response tracking and escalation framework
- `docs/RESPONSE_SYSTEM_OVERVIEW.md` - High-level system explainer
- `docs/CONTRADICTION_ENGINE.md` - Cross-bureau contradiction detection (Phase 1-3)
- `docs/COPILOT_ENGINE.md` - Goal-oriented enforcement prioritization
- `violation_comparison.xlsx` - Comparison with industry standards
