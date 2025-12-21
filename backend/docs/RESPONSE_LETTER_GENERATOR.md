# Response Letter Generator System

## Overview

The Response Letter Generator is a U.S. consumer credit compliance enforcement engine that generates formal regulatory correspondence asserting violations of the Fair Credit Reporting Act (FCRA).

## System Role

- Does NOT provide advice
- Generates formal regulatory correspondence asserting violations
- Cites statutes in canonical USC format only (e.g., 15 USC §1681i(a)(5)(B))
- Treats all violations as assertions unless explicitly marked "resolved"
- Assumes the recipient is legally sophisticated

## Constraints

- Does NOT speculate
- Does NOT soften language
- Does NOT explain the law to the reader
- Uses canonical USC format for all statute citations
- Professional business letter format
- No emojis, no bullets unless legally appropriate

## Input Data Structure

```json
{
  "consumer": {
    "name": "{{CONSUMER_NAME}}",
    "address": "{{CONSUMER_ADDRESS}}"
  },
  "cra": "TransUnion",
  "account": {
    "creditor": "Unify Credit Union",
    "account_mask": "****1234"
  },
  "violations": [
    {
      "type": "REINSERTION_NO_NOTICE",
      "statute": "15 USC 1681i(a)(5)(B)",
      "facts": [
        "Account was previously deleted",
        "Account was later reinserted",
        "No reinsertion notice received within 5 business days"
      ]
    }
  ],
  "demanded_actions": [
    "Immediate deletion of the reinserted tradeline",
    "Written confirmation of deletion",
    "Disclosure of furnisher certification if relied upon"
  ]
}
```

## Response Types That Generate Letters

| Response Type | Statute | When to Use |
|---------------|---------|-------------|
| `NO_RESPONSE` | 15 U.S.C. § 1681i(a)(1)(A) | Deadline passed with no response from entity |
| `VERIFIED` | 15 U.S.C. § 1681i(a)(1)(A) | Entity verified without reasonable investigation |
| `REJECTED` | 15 U.S.C. § 1681i(a)(3) | Entity improperly determined dispute frivolous |
| `REINSERTION_NO_NOTICE` | 15 U.S.C. § 1681i(a)(5)(B) | Previously deleted item reinserted without 5-day notice |

## Response Types That Do NOT Generate Letters

| Response Type | Reason |
|---------------|--------|
| `DELETED` | Success - item removed. System creates 90-day reinsertion watch instead |
| `UPDATED` | Ambiguous - requires evaluation. May convert to VERIFIED if not cured |
| `INVESTIGATING` | Wait state - may auto-convert to NO_RESPONSE after 15 days |

## Output Format

- Professional business letter
- Assertive tone
- Clear demands section
- Signature block included
- Sections: Header, Subject, Opening, Violations, Timeline, Demands, Willful Notice, Closing

## API Endpoint

```
POST /disputes/{dispute_id}/generate-response-letter
```

### Request Body

```json
{
  "letter_type": "enforcement",
  "response_type": "NO_RESPONSE",
  "include_willful_notice": true
}
```

### Response

```json
{
  "dispute_id": "uuid",
  "letter_type": "enforcement",
  "response_type": "NO_RESPONSE",
  "content": "Full letter text...",
  "generated_at": "2025-12-20T10:00:00Z",
  "entity_name": "TransUnion",
  "entity_type": "CRA"
}
```

## Statute Citation Reference

| Key | Canonical Citation |
|-----|-------------------|
| `fcra_611_a_1_A` | 15 U.S.C. § 1681i(a)(1)(A) |
| `fcra_611_a_5_B` | 15 U.S.C. § 1681i(a)(5)(B) |
| `fcra_611_a_3` | 15 U.S.C. § 1681i(a)(3) |
| `fcra_616` | 15 U.S.C. § 1681n |
| `fcra_617` | 15 U.S.C. § 1681o |
| `fdcpa_1692g_b` | 15 U.S.C. § 1692g(b) |

## Phase 3: Contradiction-Driven Demand Prioritization

### Overview

Phase 3 integrates the Contradiction Engine to dynamically determine demanded actions based on detected data contradictions. This applies to VERIFIED and REJECTED response letters only.

### How It Works

1. **Contradiction Engine** analyzes the disputed account
2. **`determine_primary_remedy()`** evaluates contradiction severities
3. **`generate_demanded_actions()`** creates ordered action list
4. **`format_demanded_actions_section()`** formats for letter output

### Remedy Determination Rules

| Rule | Condition | Primary Remedy |
|------|-----------|----------------|
| 1 | Any CRITICAL contradiction | `IMMEDIATE_DELETION` |
| 2 | 2+ HIGH contradictions | `IMMEDIATE_DELETION` |
| 3 | 1 HIGH or any MEDIUM | `CORRECTION_WITH_DOCUMENTATION` |
| 4 | No contradictions | `STANDARD_PROCEDURAL` |

### Demanded Actions by Remedy Type

**IMMEDIATE_DELETION:**
1. Immediately delete the disputed tradeline from consumer's credit file
2. Provide written confirmation of deletion within 5 business days
3. Notify all entities to whom the inaccurate data was previously furnished

**CORRECTION_WITH_DOCUMENTATION:**
1. Correct and update all inaccurate data fields identified
2. Provide documentation supporting the accuracy of corrections
3. Furnish corrected data to all consumer reporting agencies

**STANDARD_PROCEDURAL:**
1. Complete the reinvestigation within the statutory timeframe
2. Provide investigation results in writing pursuant to 15 U.S.C. § 1681i(a)(6)

### Letter Types Using Phase 3

| Letter Type | Uses Phase 3 | Notes |
|-------------|--------------|-------|
| VERIFIED | Yes | Dynamic demands based on contradictions |
| REJECTED | Yes | Dynamic demands based on contradictions |
| NO_RESPONSE | No | Fixed statutory demands |
| REINSERTION | No | Fixed statutory demands |

### Key Functions

```python
class PrimaryRemedy:
    """Primary remedy types determined by contradiction severity."""
    IMMEDIATE_DELETION = "IMMEDIATE_DELETION"
    CORRECTION_WITH_DOCUMENTATION = "CORRECTION_WITH_DOCUMENTATION"
    STANDARD_PROCEDURAL = "STANDARD_PROCEDURAL"

def determine_primary_remedy(contradictions: Optional[List[Any]]) -> str:
    """Determine primary remedy based on contradiction severity."""

def generate_demanded_actions(
    primary_remedy: str,
    entity_name: str,
    response_type: str = "VERIFIED",
) -> List[str]:
    """Generate demanded actions ordered by primary remedy."""

def format_demanded_actions_section(actions: List[str]) -> str:
    """Format demanded actions into letter section."""
```

### Example Output (VERIFIED with CRITICAL contradiction)

```
DEMANDED ACTIONS

1. Immediately delete the disputed tradeline from the consumer's credit file
2. Provide written confirmation of deletion within 5 business days
3. Notify all entities to whom the inaccurate data was previously furnished

Failure to comply with these demands may result in further action under
15 U.S.C. § 1681n (willful noncompliance) and 15 U.S.C. § 1681o (negligent noncompliance).
```

## Implementation Location

- Backend Service: `backend/app/services/enforcement/response_letter_generator.py`
- API Router: `backend/app/routers/disputes.py`
- Frontend API: `frontend/src/api/disputeApi.js`
- Frontend UI: `frontend/src/pages/DisputesPage.jsx`
- Contradiction Engine: `backend/app/services/audit/contradiction_engine.py`
- Contradiction Tests: `backend/test_contradiction_engine.py`
