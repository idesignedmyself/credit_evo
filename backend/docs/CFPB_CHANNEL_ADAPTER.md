# CFPB Channel Adapter

**Status:** SHIPPED
**Tests:** All imports verified
**Scope:** Locked

The CFPB Channel Adapter provides a CFPB-specific escalation track that mirrors the CRA dispute lifecycle. This is a **channel adapter** - same facts, same contradictions, same severity, same remedies - different audience rendering.

## Overview

When CRA disputes are exhausted but contradictions remain unresolved, consumers can escalate to the CFPB. This adapter:

1. **Reuses existing engine data** - No new contradiction logic, severity models, or remedy selection
2. **Renders for CFPB audience** - Neutral tone, procedural framing, timeline emphasis
3. **Tracks CFPB-specific state** - Separate from CRA dispute state machine
4. **Maintains full audit trail** - All events logged to execution ledger

## State Machine

```
NONE
    ↓ (submit initial)
INITIAL_SUBMITTED
    ↓ (log response)
RESPONSE_RECEIVED
    ↓ (submit escalation - gated)
ESCALATION_SUBMITTED
    ↓ (log response)
ESCALATION_RESPONSE_RECEIVED
    ↓ (submit final - gated)
FINAL_SUBMITTED
    ↓ (close)
CLOSED
```

### Escalation Gating Rules

Escalation/Final submissions require:
1. **CRA exhaustion** - Response = VERIFIED | NO_RESPONSE | REJECTED
2. **Unresolved contradictions** - `unresolved_contradictions_count > 0`

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/cfpb/letters/generate` | POST | Generate CFPB letter draft (no state change) |
| `/cfpb/complaints/submit` | POST | Submit complaint (state change) |
| `/cfpb/complaints/response` | POST | Log CFPB response (state change) |
| `/cfpb/evaluate` | POST | Evaluate response (read-only) |
| `/cfpb/cases` | GET | List user's CFPB cases |
| `/cfpb/cases/{id}` | GET | Get case details |
| `/cfpb/cases/{id}/events` | GET | Get case event history |

### Generate Letter (No State Change)

```json
POST /cfpb/letters/generate
{
  "dispute_session_id": "uuid",
  "cfpb_stage": "initial | escalation | final"
}
```

### Submit Complaint (State Change)

```json
POST /cfpb/complaints/submit
{
  "dispute_session_id": "uuid",
  "cfpb_stage": "initial | escalation | final",
  "submission_payload": {
    "complaint_text": "...",
    "attachments": []
  },
  "cfpb_case_number": "optional - from CFPB portal"
}
```

### Log Response (State Change)

```json
POST /cfpb/complaints/response
{
  "cfpb_case_id": "uuid",
  "response_text": "...",
  "responding_entity": "CRA | Furnisher",
  "response_date": "YYYY-MM-DD"
}
```

### Evaluate (Read-Only)

```json
POST /cfpb/evaluate
{
  "cfpb_case_id": "uuid"
}
```

Returns recommendations based on state and unresolved contradictions.

## Letter Rendering Rules

| Parameter | CRA Letter | CFPB Letter |
|-----------|-----------|-------------|
| Tone | Variable | `neutral_formal` |
| Statute Density | High | Low |
| Contradiction Visibility | Medium | **High** |
| Remedy Language | Demand | **Request** |
| Timeline | Optional | **Mandatory** |
| Framing | Legal threat | **Procedural failure** |

### Rights Language Rule

| Stage | Include "Reserve Rights"? |
|-------|---------------------------|
| Initial | No |
| Escalation | No |
| Final | **Yes** (single line at end) |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    CFPB CHANNEL ADAPTER                      │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ CFPBService  │  │ StateMachine │  │ LetterGenerator  │   │
│  │              │──│              │──│                  │   │
│  │ Orchestrator │  │ State Enum   │  │ 3 Variants       │   │
│  └──────────────┘  └──────────────┘  └──────────────────┘   │
│         │                                                    │
│         ▼                                                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              EXISTING ENGINE (REUSED)                 │   │
│  │  Contradictions | Severity | Remedy | Audit Result   │   │
│  └──────────────────────────────────────────────────────┘   │
│         │                                                    │
│         ▼                                                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                EXECUTION LEDGER                       │   │
│  │  CFPB_INITIAL_SUBMITTED | CFPB_ESCALATION_SUBMITTED  │   │
│  │  CFPB_FINAL_SUBMITTED | CFPB_RESPONSE_RECEIVED       │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Files Created/Modified

### New Files

| File | Purpose |
|------|---------|
| `app/routers/cfpb.py` | API endpoints |
| `app/services/cfpb/__init__.py` | Service package |
| `app/services/cfpb/cfpb_service.py` | Core orchestrator |
| `app/services/cfpb/cfpb_state_machine.py` | State machine with gating |
| `app/services/cfpb/cfpb_letter_generator.py` | Letter rendering |
| `migrations/add_cfpb_tables.py` | Database migration |

### Modified Files

| File | Changes |
|------|---------|
| `app/models/ssot.py` | Added CFPBState, CFPBEventType, CFPBResponseClassification |
| `app/models/db_models.py` | Added CFPBCaseDB, CFPBEventDB |
| `app/main.py` | Registered CFPB router |
| `app/routers/__init__.py` | Exported cfpb_router |
| `app/services/enforcement/execution_ledger.py` | Added CFPB event types |

## Database Schema

### cfpb_cases

```sql
id VARCHAR(36) PRIMARY KEY
dispute_session_id VARCHAR(36) NOT NULL
user_id VARCHAR(36) NOT NULL
cfpb_case_number VARCHAR(100)  -- From CFPB portal
cfpb_state VARCHAR(50) NOT NULL  -- Single state enum
created_at TIMESTAMP
updated_at TIMESTAMP
```

### cfpb_events

```sql
id VARCHAR(36) PRIMARY KEY
cfpb_case_id VARCHAR(36) NOT NULL
event_type VARCHAR(50) NOT NULL  -- SUBMISSION | RESPONSE | EVALUATION
payload JSON
timestamp TIMESTAMP
```

## Constraints (Enforced)

- No new contradiction logic
- No new severity models
- No CFPB before CRA exhaustion
- No auto-submission without user confirmation
- Everything replayable from ledger
- Single CFPB_STATE enum (no Stage/Status confusion)
- Case continuity (one case number per lifecycle)
- /evaluate is read-only
- Escalation gated on unresolved contradictions only

## Response Classification

Response text is classified (informational only, does not gate state):

| Classification | Meaning |
|----------------|---------|
| ADDRESSED_FACTS | Response addressed specific contradictions |
| IGNORED_FACTS | Response ignored documented contradictions |
| GENERIC_RESPONSE | Boilerplate response without specifics |

## Ledger Events

| Event Type | When Logged |
|------------|-------------|
| CFPB_INITIAL_SUBMITTED | Initial complaint submitted |
| CFPB_ESCALATION_SUBMITTED | Escalation submitted |
| CFPB_FINAL_SUBMITTED | Final submission submitted |
| CFPB_RESPONSE_RECEIVED | CFPB response logged |

---

**This is a channel adapter - reuses all existing engine data.**

No changes to Tier 1 (contradiction detection), Tier 2 (examiner enforcement), or any other existing functionality.

---

## Related Documentation

- **Tier 1:** Contradiction Detection
- **Tier 2:** Supervisory Enforcement → `docs/TIER2_SUPERVISORY_ENFORCEMENT.md`
- **CRA Dispute Lifecycle:** Response System → `docs/RESPONSE_SYSTEM_OVERVIEW.md`
