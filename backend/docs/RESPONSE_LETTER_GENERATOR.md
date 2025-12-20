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

## Implementation Location

- Backend Service: `backend/app/services/enforcement/response_letter_generator.py`
- API Router: `backend/app/routers/disputes.py`
- Frontend API: `frontend/src/api/disputeApi.js`
- Frontend UI: `frontend/src/pages/DisputesPage.jsx`
