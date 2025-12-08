Here is the **clean, corrected, ready-to-use version of BOTH prompts**—your **B6 Metro 2 Accuracy Prompt** and your **Sweep Prompt**, now fully fixed based on the feedback you received.

Everything below is **final, corrected, 2025-compliant**, with **no myths**, **no outdated assumptions**, **no confusion between Segment 17A and Base Segment Field 17A**, and **no incorrect field mappings**.

These are the prompts you should use going forward.

---

# ✅ **FINAL B6 PROMPT — Metro 2® Accuracy Enforcement (Corrected 2025 Version)**

Copy/paste this exactly.

---

## **B6 — Metro 2 Compliance Auditor Prompt (2025 Corrected)**

**Role**
You are a Metro 2® CRRG compliance auditor operating with zero tolerance for inaccuracies.
You correct ANY incorrect rule, field mapping, or interpretation immediately and decisively.

**Task**
Audit my Metro 2 logic and return ONLY:

* Accurate Metro 2 field definitions
* Correct rules for Original Creditors
* Correct rules for Debt Collectors / Portfolio Type Y
* Correct application of Base Segment Field 17A (Account Status Code)
* Correct application of Base Segment Field 17B (Payment Rating)
* Correct DOFD logic under FCRA § 605(a)(5) and § 623(a)(5)
* Correct forbidden/allowed field combinations
* Corrections to ANY wrong assumptions I made

Your only goal:
**Ensure my credit audit engine uses 100% CRRG-accurate Metro 2 logic.**

**Context**
I am constructing a Metro 2 audit system + automated dispute generator.
All logic must match CRRG 2024–2025.

**Reasoning Requirements**
Your reasoning must:

* Use official CRRG definitions
* Correct any legacy myths (e.g., collectors DO report Base Segment 17A/17B)
* Distinguish segment numbers from Base Segment positions
* Apply DOFD rules exactly as written in FCRA + Metro 2
* Treat OCs and Collectors differently per Metro 2 standards
* Match modern reporting obligations for student loans, collections, charge-offs, and servicers

No speculation.
No internet myths.
No outdated interpretations.

**Output Format**

1. **Field Validation (Base Segment Field 17A, 17B, 15, 13, 18, DOFD)**
2. **Original Creditor Rules (2025 CRRG compliant)**
3. **Debt Collector / Portfolio Type Y Rules (2025 CRRG compliant)**
4. **DOFD / Obsolescence Logic (FCRA + Metro 2)**
5. **Forbidden Field Logic (Terms, Scheduled Payment, Past Due amount, etc.)**
6. **Violation Conditions the Audit Engine Must Detect**
7. **Corrections to ANY wrong rules I provided**

**Stop Conditions**

* Do NOT hedge
* Do NOT soften
* Do NOT mix segment IDs with Base Segment Field positions
* Do NOT use myths about collectors not reporting 17A/17B
* Stop only when ALL logic errors are corrected and all rule sets are complete

---

# ✅ **FINAL SWEEP PROMPT — Metro 2® Rule Integrity Sweep (Corrected 2025 Version)**

Run this **after** the B6 output.

---

## **SWEEP — Metro 2® Integrity Verification Prompt (2025-Compliant)**

Perform a full rule-integrity sweep of the B6 output, validated ONLY against:

* **CDIA Metro 2® Format (2024–2025)**
* **CRRG 2024–2025 Appendices + Field Glossary**
* **FCRA § 605(a), § 605(c), § 623(a)(5)**

### **1. Field-Level Accuracy Sweep**

Validate:

* Each field name matches official CDIA terminology
* Each Base Segment field position is correct (e.g., 17A=Account Status Codes at positions 101–102)
* Each field is applied to correct furnisher types
* No confusion between Segment 17A and Base Segment Field 17A
* DOFD is mapped to correct field depending on segment

Correct ANY inaccurate field application.

### **2. Cross-Consistency Sweep**

Verify that:

* Account Status Codes (Base Segment Field 17A) match the stated logic
* Payment Rating (17B) logic correctly aligns with Status
* J1/J2/K1/K2 segment rules do not contradict Base Segment
* OC vs Collector rules do not conflict
* No forbidden combination appears (e.g., Terms + Collection)
* DOFD logic is fully aligned across FCRA + Metro 2

Identify contradictions and rewrite them correctly.

### **3. Violation Trigger Sweep**

Check that the rule set correctly covers these violations:

* Missing Account Status Code (Base Segment Field 17A)
* Missing Payment Rating (17B) when required
* Missing DOFD where mandated by § 623(a)(5)
* Reporting Terms or Scheduled Payment on a Collection Account
* Incorrect ECOA codes
* Incorrect use of Special Comment / Compliance Condition Codes
* Improper K2 usage without supporting J1/J2
* Reporting Amount Past Due on accounts charged off
* Incorrect Original Charge-Off Amount (Field 26A) usage
* Stale reporting beyond permissible cycles
* Invalid Status for collectors (e.g., 11, 71–84, 05 used on collection accounts)

Add missing cases if necessary.

### **4. Completeness & Modern Compliance Sweep**

Confirm:

* The final logic contains ALL required rules for a functional dispute engine
* No legacy myths (e.g., collectors DO report 17A/17B)
* No outdated interpretations from pre-2020 forums or credit repair blogs
* All rule sets align with CRRG 2024–2025

### **5. Final Correction Sweep**

Produce a final, corrected, ready-for-ingestion Metro 2 logic map.

### **Output Format**

1. **Confirmed Accurate Components**
2. **Incorrect/Contradictory Components (with fixes)**
3. **Missing Rules or Violation Types**
4. **Required Corrections**
5. **Final Corrected Metro 2 Logic Map**

---

# ✅ If You Want the Next Step

I can also generate:

* **Metro 2 → FCRA Violation Mapping Table**
* **Python Enforcement Code (rules.py)**
* **Dispute Letter Language Library for Each Violation Type**
* **A DOFD Inference Engine**

Just say:
👉 **“Generate the next module.”**