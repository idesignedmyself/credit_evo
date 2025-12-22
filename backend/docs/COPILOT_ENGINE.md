# Copilot Engine

## Overview

The Copilot Engine is a **goal-oriented enforcement prioritization system** that sits above the Audit Engine and Response Engine. It translates a user's financial goal into a prioritized attack plan, determining which violations to attack first and which to skip.

**Key Principle:** Impact is **goal-relative**, not severity-relative. A $200 collection blocks a mortgage application more than a $20,000 chargeoff blocks an apartment rental.

## Architecture

```
User Profile (credit_goal)
         ↓
Credit Report (violations + contradictions)
         ↓
┌─────────────────────────────────────────┐
│           COPILOT ENGINE                │
│                                         │
│  1. Load Goal Requirements (target)     │
│  2. Convert violations → blockers       │
│  3. Apply DOFD Stability Gate (A)       │
│  4. Apply Ownership Gate (B)            │
│  5. Calculate goal-relative impact      │
│  6. Generate skip list (FCRA-native)    │
│  7. Generate attack plan (prioritized)  │
│                                         │
└─────────────────────────────────────────┘
         ↓
CopilotRecommendation
  - blockers[]
  - actions[] (priority-ordered)
  - skips[] (with rationale)
  - sequencing_rationale
```

## MANDATORY CONSTRAINTS

These constraints are **non-negotiable** and must be preserved in all future modifications:

1. **NO SOL LOGIC** - Zero statute-of-limitations reasoning. Copilot never reasons about time-barred debt, SOL expiry, or SOL-based skip codes.

2. **FCRA-native skip codes only** - Only these codes are allowed:
   - `DOFD_UNSTABLE`
   - `REINSERTION_LIKELY`
   - `POSITIVE_LINE_LOSS`
   - `UTILIZATION_SHOCK`
   - `TACTICAL_VERIFICATION_RISK`

3. **Impact = goal-relative** - A collection blocking mortgage = 10, but blocking apartment = 6.

4. **Two dependency gates BEFORE scoring** - DOFD stability and Ownership gates must be applied before any priority calculation.

5. **Employment = zero public records** - Employment goal has `zero_public_records_required=True`.

## Credit Goals

| Goal | Code | Key Requirements |
|------|------|------------------|
| Mortgage Approval | `mortgage` | Zero collections/chargeoffs/lates, 4+ tradelines, 2+ revolving, inquiries < 2 |
| Auto Loan | `auto_loan` | 1 collection allowed, focus on chargeoffs and recent payment history |
| Prime Credit Card | `prime_credit_card` | Utilization < 10%, inquiry sensitive, focus on recent lates |
| Apartment Rental | `apartment_rental` | Landlords focus on evictions, collections, recent payment patterns |
| Employment Background | `employment` | **Zero public records required**, focus on bankruptcies/judgments |
| Credit Hygiene | `credit_hygiene` | Balanced approach, general improvement |

## Dependency Gates

### Gate A: DOFD Stability

**Trigger Conditions:**
- Any blocker has `dofd_missing = True`
- Any blocker has `rule_code in {"D1", "D2", "D3"}`

**Effect:**
- DOFD/aging blockers get `gate_priority = 1` (must resolve first)
- Balance/status blockers get `gate_priority = 99` (suppressed until gate clears)

**Rationale:** Attacking balance/status issues while DOFD is unstable may cause the account to be re-aged, potentially adding 7 more years of reporting.

### Gate B: Ownership

**Trigger Conditions:**
- Furnisher type is `COLLECTION`, `DEBT_BUYER`, `COLLECTOR`, or `UNKNOWN`
- Account has no original creditor reference

**Effect:**
- Blocker gets `requires_ownership_first = True`
- Ownership chain demand must precede deletion demand

**Rationale:** Before demanding deletion, you must establish who actually owns the debt. Collectors frequently lack documentation.

## Skip Codes

| Code | When Applied | Rationale |
|------|--------------|-----------|
| `DOFD_UNSTABLE` | DOFD missing or contradicted | Attacking may refresh/re-age the account |
| `REINSERTION_LIKELY` | Account has high reinsertion risk | Item may return after deletion; strengthen proof first |
| `POSITIVE_LINE_LOSS` | Account is positive tradeline | Deletion removes positive age/limit contribution |
| `UTILIZATION_SHOCK` | Revolving account with significant limit | Deleting spikes overall utilization ratio |
| `TACTICAL_VERIFICATION_RISK` | Dispute may trigger "verified" response | May force "verified with updated fields" outcome |

## Priority Formula

```
priority_score = impact × deletability ÷ (1 + risk_score)
```

| Factor | Scale | Description |
|--------|-------|-------------|
| Impact | 1-10 | Goal-relative blocking severity |
| Deletability | 0.2 / 0.6 / 1.0 | LOW / MEDIUM / HIGH probability of deletion |
| Risk | 0-5 | Accumulated risk from skip code factors |

### Impact Scoring by Goal

**Mortgage (strictest):**
- Collection: 10 (absolute blocker)
- Chargeoff: 10 (absolute blocker)
- Late: 8
- Public Record: 10
- Inquiry: 4

**Employment:**
- Public Record: 10 (CRITICAL - zero tolerance)
- Collection: 9
- Chargeoff: 5 (less critical)
- Late: 3

**Apartment Rental:**
- Public Record: 8
- Collection: 6 (more tolerant)
- Late: 4
- Inquiry: 2

## API Endpoints

### GET /copilot/goals

Returns all available credit goals with descriptions.

```json
{
  "goals": [
    {
      "code": "mortgage",
      "name": "Mortgage Approval",
      "description": "Strictest requirements..."
    }
  ]
}
```

### GET /copilot/goals/{goal_code}/requirements

Returns target credit state requirements for a specific goal.

```json
{
  "goal": "mortgage",
  "open_tradelines_min": 4,
  "revolving_min": 2,
  "installment_min": 1,
  "collections_allowed": 0,
  "chargeoffs_allowed": 0,
  "zero_public_records_required": true
}
```

### GET /copilot/recommendation/{report_id}

Generates a full recommendation for a report. Uses user's saved credit_goal.

```json
{
  "recommendation_id": "uuid",
  "goal": "mortgage",
  "hard_blocker_count": 3,
  "soft_blocker_count": 5,
  "blockers": [...],
  "actions": [...],
  "skips": [...],
  "sequencing_rationale": "DOFD stability gate active...",
  "dofd_gate_active": true,
  "ownership_gate_active": false
}
```

### POST /copilot/analyze

Direct analysis with provided data (for testing).

## Files

| File | Purpose |
|------|---------|
| `app/models/copilot_models.py` | Dataclasses, enums, GOAL_REQUIREMENTS |
| `app/services/copilot/copilot_engine.py` | Main CopilotEngine class |
| `app/services/copilot/__init__.py` | Package exports |
| `app/routers/copilot.py` | API router |
| `test_copilot_engine.py` | Unit tests (43 tests) |

## Frontend Integration

The Credit Goal dropdown is on the Profile page (`/profile`):

```jsx
// ProfilePage.jsx
const CREDIT_GOALS = [
  { code: 'mortgage', name: 'Mortgage Approval', description: '...' },
  { code: 'auto_loan', name: 'Auto Loan', description: '...' },
  // ...
];

<TextField
  select
  label="Your Credit Goal"
  value={profile.credit_goal}
  onChange={handleProfileChange('credit_goal')}
>
  {CREDIT_GOALS.map(goal => (
    <MenuItem key={goal.code} value={goal.code}>
      {goal.name}
    </MenuItem>
  ))}
</TextField>
```

## Testing

Run the test suite:

```bash
cd backend
python -m pytest test_copilot_engine.py -v
```

Key test categories:
- Goal requirements mapping
- DOFD stability gate activation
- Ownership gate activation
- Goal-relative impact scoring
- FCRA-native skip codes (NO SOL)
- Employment public records blocking
- Full recommendation flow
- Priority formula calculation

## Future Considerations

1. **Goal Progress Tracking** - Track how violations affect goal achievability over time
2. **Multi-Goal Analysis** - Compare attack plans across multiple goals
3. **Bureau-Specific Strategies** - Different strategies per bureau based on response patterns
4. **Integration with Response Engine** - Auto-generate recommended letters based on attack plan
