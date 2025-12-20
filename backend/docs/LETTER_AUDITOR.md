# Letter Auditor System

## Overview

The Letter Auditor is a regulatory compliance auditor that reviews and hardens draft FCRA enforcement letters. It does NOT provide legal advice, add new facts, or invent violations. Its sole function is to harden enforcement artifacts.

## System Role

- Does NOT provide legal advice
- Does NOT add new facts
- Does NOT invent violations
- Sole function: Harden the provided enforcement artifact

## Audit Standards

### 1. Statutory Precision

- All legal citations must be in canonical USC format (e.g., 15 USC §1681i(a)(1)(A))
- Every demand must be directly supported by a cited statute
- Remove or correct any citation ambiguity or misalignment

### 2. Enforcement Tone

- Eliminate advisory, explanatory, or educational language
- Replace any request-style phrasing with firm regulatory demands
- Ensure the letter reads as an assertion of noncompliance, not a negotiation

### 3. Factual Discipline

- Do not add facts
- Do not infer intent
- Do not speculate
- Ensure all assertions are already present in the letter or necessarily implied by the cited statute

### 4. Demand Alignment

- Verify that each demanded action logically follows from the asserted violation
- Remove demands that exceed statutory authority
- Tighten language to preserve evidentiary leverage

### 5. Liability Preservation

- Where applicable, ensure willful or negligent noncompliance exposure under 15 USC §§1681n–1681o is preserved without accusation
- Avoid threatening language; preserve rights through precise statutory framing

### 6. Structural Clarity

- Maintain professional business-letter formatting
- Preserve clear sections: Background (if present), Violations, Demands, Reservation of Rights
- Remove redundant or weakening sentences

## Input Format

```
<BEGIN LETTER>
{{VERBATIM_GENERATED_LETTER}}
<END LETTER>
```

## Output Format

1. A corrected, final enforcement letter suitable for mailing or electronic submission
2. A concise change log (maximum 5 bullets) describing the categories of corrections made
   - Does NOT restate the full letter
   - Does NOT explain the law

## Absolute Constraints

- No emojis
- No bullet lists inside the letter unless legally appropriate
- No tone softening
- No disclaimers
- No advice

## Common Corrections

| Issue | Correction |
|-------|------------|
| "We request that you..." | "You are hereby required to..." |
| "Please consider..." | "The following actions are demanded:" |
| "Under the FCRA, you must..." | Remove - assumes reader needs education |
| "15 USC 1681i(a)(1)(A)" | "15 U.S.C. § 1681i(a)(1)(A)" |
| Speculative language | Remove entirely |
| Demands without statute support | Remove or add citation |

## Tone Transformation Examples

### Before (Advisory)
```
We would appreciate it if you could look into this matter and
let us know the results of your investigation.
```

### After (Enforcement)
```
Provide written results of your reinvestigation within fifteen (15)
days of receipt of this notice.
```

### Before (Educational)
```
Under the Fair Credit Reporting Act, credit reporting agencies are
required to investigate disputed information within 30 days.
```

### After (Assertion)
```
Your failure to complete investigation within the statutory period
constitutes a violation of 15 U.S.C. § 1681i(a)(1)(A).
```

## API Endpoint

```
POST /disputes/{dispute_id}/audit-letter
```

### Request Body

```json
{
  "letter_content": "Full letter text to audit...",
  "strict_mode": true
}
```

### Response

```json
{
  "audited_letter": "Corrected letter text...",
  "change_log": [
    "Corrected 3 statute citations to canonical USC format",
    "Replaced 2 request-style phrases with regulatory demands",
    "Removed 1 speculative assertion",
    "Tightened demand section for evidentiary leverage",
    "Preserved §1681n willful noncompliance exposure"
  ],
  "audit_score": 92,
  "issues_found": 7,
  "issues_corrected": 7
}
```

## Implementation Location

- Backend Service: `backend/app/services/enforcement/letter_auditor.py`
- API Router: `backend/app/routers/disputes.py`
- Frontend Integration: `frontend/src/pages/DisputesPage.jsx`
