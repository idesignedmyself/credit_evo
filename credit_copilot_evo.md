credit_copilot_evo.md
Below is a **GitHub-style README** for **Credit Engine 2.0**, clean, professional, and ready to drop into a repo.
No fluff. No commentary. No filler.
Just a sharp, production-grade documentation file.

---

# **Credit Engine 2.0**

### *Deterministic Credit Report Auditing & Human-Grade Dispute Letter Generation*

---

## **Overview**

**Credit Engine 2.0** is a deterministic, Metro-2-aware credit auditing engine that parses credit reports, normalizes bureau formats, detects reporting violations, performs cross-bureau discrepancy analysis, classifies furnisher type, and generates human-sounding dispute letters with template-resistant variation.

The system is **SSOT-driven**, fully deterministic, and requires **zero LLMs** for the auditing logic.
LLMs may be used *only* for stylistic variation during letter rendering.

---

## **System Goals**

1. **Full end-to-end automation**

   * Upload → Parse → Audit → Strategy → Letter

2. **Strict single-source-of-truth (SSOT) design**

   * `NormalizedReport` = SSOT for parsed data
   * `AuditResult` = SSOT for violations/discrepancies
   * `Violation` objects = SSOT for letter reasoning

3. **Human-sounding letters with controlled variation**

   * No templates
   * No repeated structures
   * No detectable automation markers

4. **Consumer-directed dispute selection**

   * Client can toggle which violations to dispute
   * If no selections are made → all valid violations included

5. **Accurate furnisher-type classification**

   * Collector vs OC-charge-off vs OC-non-charge-off
   * 17A/17B rules applied correctly based on furnisher type

---

## **Architecture**

### **Pipeline Overview**

```
Client Upload
      ↓
Parsing Layer
      ↓
NormalizedReport (SSOT #1)
      ↓
Audit Engine
      ↓
AuditResult (SSOT #2)
      ↓
Strategy Selector
      ↓
LetterPlan
      ↓
Renderer (Controlled Variation)
      ↓
Final Dispute Letter(s)
```

---

# **Single Source of Truth (SSOT)**

### **1. NormalizedReport = SSOT for parsed data**

All modules must reference normalized schema, never raw PDFs/HTML.

### **2. AuditResult = SSOT for violations & discrepancies**

No module downstream may re-run rules or derive new logic.

### **3. Violation objects = SSOT for dispute reasoning**

Letters rely exclusively on these objects for content.

### **4. Furnisher classification = SSOT**

Collector / OC-charge-off / OC-non-charge-off classification is final.

### **5. Cross-bureau comparisons = SSOT**

Letters cannot re-compare fields across reports.

### **6. VariationSeed = SSOT for stylistic randomness**

All variation must be deterministic and seed-controlled.

### **7. Phrasebanks = SSOT for all wording**

Renderer uses only:

* `VariantPool`
* `StructureTemplates`
* `TransitionBank`

No free-form generation permitted.

---

# **1. Parsing Layer**

### **Pipeline**

```
RawReport → BureauParser(TU|EX|EQ) → NormalizedReport
```

### **Responsibilities**

* Parse HTML/PDF/XML/JSON
* Identify bureau format
* Extract accounts, inquiries, public records
* Map bureau fields to unified schema

### **NormalizedReport Schema**

```json
{
  "consumer": {},
  "bureau": "TU|EX|EQ",
  "report_date": "YYYY-MM-DD",
  "accounts": [],
  "inquiries": [],
  "public_records": [],
  "personal_info": {},
  "account_summary": {}
}
```

---

## **HTML Parser Location**

**File:** `backend/app/services/parsing/html_parser.py`

### **Parser Methods Summary**

| Method | Line | What It Parses | Output Model |
|--------|------|----------------|--------------|
| `_extract_consumer()` | 407 | Basic consumer info (name, address, DOB) | `Consumer` |
| `_extract_accounts_merged()` | 461 | All tradeline accounts (merged across bureaus) | `List[Account]` |
| `_extract_account_data_for_header()` | 614 | Per-account bureau-specific data | `Dict[Bureau, BureauAccountData]` |
| `_extract_inquiries()` | 726 | Hard/soft inquiries with type_of_business & bureau | `List[Inquiry]` |
| `_extract_public_records()` | 755 | Bankruptcies, judgments, liens | `List[PublicRecord]` |
| `_extract_report_date()` | 765 | Credit report date | `date` |
| `_extract_credit_scores()` | 776 | Credit scores per bureau | `CreditScore` |
| `_extract_personal_info()` | 884 | Detailed personal info per bureau | `PersonalInfo` |
| `_extract_account_summary()` | 1036 | Account statistics per bureau | `AccountSummary` |
| `_extract_creditor_contacts()` | 1100+ | Creditor contact info (name, address, phone) | `List[CreditorContact]` |

### **Inquiry Fields**

Each inquiry includes:
- **creditor_name**: Name of the creditor who pulled the report
- **inquiry_date**: Date of the inquiry
- **inquiry_type**: Hard or soft inquiry
- **type_of_business**: Type of business (e.g., "Bank", "Finance Company", "Bank Credit Cards")
- **bureau**: Which bureau reported this inquiry (TransUnion, Experian, or Equifax)

### **Creditor Contact Fields**

Each creditor contact includes:
- **creditor_name**: Name of the creditor
- **address**: Street address (parsed from full address)
- **city**: City (parsed)
- **state**: State (parsed)
- **zip_code**: ZIP code (parsed)
- **phone**: Phone number (format: `(XXX) XXX-XXXX`)

### **CSS Selectors for IdentityIQ Reports**

| Section | CSS Path |
|---------|----------|
| Personal Information | `#ctrlCreditReport > transunion-report > div.ng-binding.ng-scope > div:nth-child(7)` |
| Account Summary | `#ctrlCreditReport > transunion-report > div.ng-binding.ng-scope > div:nth-child(11) > table.re-even-odd.rpt_content_table.rpt_content_header.rpt_table4column` |

### **Personal Information Fields (per bureau: TU/EX/EQ)**

- Credit Report Date
- Name
- Also Known As
- Former (names)
- Date of Birth
- Current Address(es)
- Previous Address(es)
- Employers

### **Account Summary Fields (per bureau: TU/EX/EQ)**

- Total Accounts
- Open Accounts
- Closed Accounts
- Delinquent
- Derogatory
- Collection
- Balances
- Payments
- Public Records
- Inquiries (2 years)

---

## **DOFD Inference Logic**

**Location:** `backend/app/services/parsing/html_parser.py` (Line 137)

**Function:** `_infer_dofd_from_payment_history()`

### **The Problem**

IdentityIQ HTML reports (and many bureau formats) **do not always explicitly report the Date of First Delinquency (DOFD)**. However, DOFD is critical for:
- Determining the 7-year reporting period under FCRA §605(a)
- Flagging obsolete accounts that should be removed
- Calculating when negative items "fall off" the report

### **The Solution: Payment History Inference**

When DOFD is missing, the parser **infers it from the payment history** using this logic:

```
Payment History → Find oldest delinquent month → Use as DOFD
```

### **How It Works**

1. **Parse Payment History**: Extract the 24-month payment history grid
   ```
   [{"month": "Jan", "year": 2024, "status": "OK"},
    {"month": "Dec", "year": 2023, "status": "30"},
    {"month": "Nov", "year": 2023, "status": "60"}, ...]
   ```

2. **Identify Delinquent Statuses**: Any status that is NOT "OK" is delinquent
   - `30`, `60`, `90`, `120` = Days late
   - `CO` = Charge-off
   - Empty/dash = OK (current)

3. **Find the Oldest Delinquency**: Sort all delinquent months and return the earliest date

4. **Set as DOFD**: Use the 1st of that month as the inferred DOFD

### **Priority Order**

```python
# Try explicit DOFD first, then infer from payment history
explicit_dofd = _parse_date(bureau_data.get("dofd"))
inferred_dofd = _infer_dofd_from_payment_history(payment_history) if not explicit_dofd else None
final_dofd = explicit_dofd or inferred_dofd
```

**Priority:**
1. **Explicit DOFD** (if bureau reports it) → Use as-is
2. **Inferred DOFD** (from payment history) → Fallback when explicit is missing

### **Example**

Payment history shows:
| Month | Year | Status |
|-------|------|--------|
| Jan | 2024 | OK |
| Dec | 2023 | 30 |
| Nov | 2023 | 60 |
| Oct | 2023 | 30 |
| Sep | 2023 | OK |

**Result:** DOFD inferred as `2023-10-01` (October 2023 = first delinquency)

### **Explicit DOFD Field Labels**

The parser looks for these labels in the HTML:
- `Date of First Delinquency:`
- `Date of 1st Delinquency:`
- `DOFD:`
- `First Delinquency:`

---

# **2. Audit Engine**

### **Pipeline**

```
NormalizedReport(s) → RuleEngine → AuditResult
```

### **Rule Categories**

#### **Single-Bureau Rules**

* Missing DOFD
* Missing Date Last Payment
* Missing Date Opened
* Missing Scheduled Payment (OC non-charge-off)
* Negative balances
* Past Due > Balance
* DOFD after Date Opened
* Invalid Metro-2 codes
* Closed OC reporting 17A > 0

#### **Cross-Bureau Rules**

* DOFD mismatch
* Balance mismatch
* Status mismatch
* Payment history mismatch
* Closed vs Open conflict
* Creditor name differences
* Account number differences
* Date Opened mismatch

#### **Temporal Rules**

* Stale reporting
* Re-aging
* DOFD replaced with Date Opened
* Impossible timelines

#### **Furnisher-Type Rules**

**Debt Collectors / Charge-Off Furnishers**

* 17A = full balance → correct
* 17B = 0 → correct
* Do not flag these

**Original Creditor (Non-Charge-Off)**

* Closed OC must report:

  * 17A = 0
  * 17B = 0
* Flag if violated

**Original Creditor (Charge-Off)**

* Follows collector rules
* DOFD mandatory

---

### **AuditResult Schema**

```json
{
  "report_id": "uuid",
  "bureau": "TU|EX|EQ",
  "violations": [],
  "discrepancies": [],
  "clean_accounts": [],
  "audit_timestamp": "ISO8601"
}
```

---

# **3. Strategy Selector**

### **Pipeline**

```
AuditResult → StrategySelector → LetterPlan
```

### **Responsibilities**

* Filter invalid or weak violations
* Group by type, creditor, or severity
* Determine number of letters
* Assign `variation_seed`
* Select tone

### **LetterPlan Schema**

```json
{
  "bureau": "",
  "consumer": {},
  "grouped_violations": {},
  "grouping_strategy": "",
  "variation_seed": 0,
  "tone": ""
}
```

---

# **4. Rendering Engine (Human-Sounding & Template-Resistant)**

### **Pipeline**

```
LetterPlan → Renderer → DisputeLetter
```

### **Components**

#### **VariantPool (SSOT)**

Human-sounding variants for each violation type.

#### **StructureTemplates (SSOT)**

Multiple natural letter skeletons.

#### **TransitionBank (SSOT)**

Connective phrasing for human pacing.

#### **VariationSeed (SSOT)**

Controls tone, flow, sentence ordering, phrase selection.

#### **Interpolator**

Injects account-specific details from Violation objects.

---

### **DisputeLetter Schema**

```json
{
  "content": "string",
  "bureau": "",
  "accounts_disputed": [],
  "violations_cited": [],
  "metadata": {}
}
```

---

# **User-Directed Violation Selection**

Credit Engine 2.0 includes full client control:

### **Flow**

1. Audit produces full violation list
2. Client can toggle any violation
3. Renderer only includes selected violations
4. If no selections → include all valid violations

### **UI Requirements**

* Plain English explanations
* Severity indicator
* Creditor-type indicator
* 1-click toggles
* Final preview

### **Compliance Rationale**

* Consumer-directed disputes
* Transparency
* Avoid unintended disputes
* Supports excluding sensitive tradelines
* Enhances trust

---

# **No-Template, Human-Sounding Letters**

The renderer avoids template detection by:

* Multiple letter skeletons
* Large variation pools
* Controlled randomness via variation_seed
* No repeated paragraph blocks
* Narrative-style grouping (not “Account 1 / Account 2”)
* Human pacing and transition phrases
* No robotic legal formatting
* No boilerplate dispute language

---

# **Contributing**

All contributions must honor:

* SSOT principles
* Deterministic logic
* Zero LLMs in auditing
* Pure, testable rule functions
* Controlled phrasing only through phrasebanks

---

# **License**

Proprietary — All rights reserved.

---

If you want, I can also generate:

✔ a `/docs` folder with module-by-module READMEs
✔ UML diagrams
✔ mermaid.js system flowcharts
✔ OpenAPI schema for client-side integration
✔ a full project folder scaffold (src/, tests/, data/, docs/, etc.)

Just say the word.
