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
  "public_records": []
}
```

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
