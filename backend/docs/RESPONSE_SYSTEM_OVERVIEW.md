# Response System Overview

## What This System Does

The Unified Response System transforms Credit Engine from a **violation detector** into a **full enforcement automation platform**. It tracks what happens AFTER you send a dispute letter and guides users through the entire regulatory enforcement process.

## The Problem It Solves

Currently:
1. User uploads credit report
2. System detects violations
3. User generates dispute letter
4. **...then what?**

The gap: There's no system to track responses, detect new violations from those responses, manage deadlines, or escalate when entities fail to comply.

## How It Works

### Phase 1: Response Tracking

When a user receives a response from a CRA, Furnisher, or Debt Collector, they log it:

```
Entity: Equifax
Response Type: Verified
Response Date: 2025-12-15
```

The system then:
- Maps the response to new potential violations
- Calculates next deadlines
- Determines escalation path

### Phase 2: Response Types & Their Meaning

| They Said | What It Means | What Happens Next |
|-----------|---------------|-------------------|
| **Deleted** | They removed the item | Watch for reinsertion (90 days) |
| **Verified** | They claim it's accurate | Demand Method of Verification |
| **Updated** | They changed something | Validate the change fixed the issue |
| **Investigating** | Stalling | 15-day hard deadline set |
| **No Response** | Deadline passed silently | Automatic violation created |
| **Rejected** | They refuse to investigate | Check if rejection is legally valid |

### Phase 3: Escalation State Machine

Every dispute moves through states:

```
DETECTED → DISPUTED → RESPONDED → EVALUATED → ...
```

If the entity fails at any point:

```
... → NON_COMPLIANT → PROCEDURAL_ENFORCEMENT → SUBSTANTIVE_ENFORCEMENT → REGULATORY_ESCALATION → LITIGATION_READY
```

Each state has:
- Specific entry/exit conditions
- Available document types to generate
- Tone posture (informational → enforcement → regulatory)

### Phase 4: Cross-Entity Intelligence

The system detects patterns across entities:

| Pattern | Meaning |
|---------|---------|
| Bureau deletes, furnisher re-reports | Reinsertion violation |
| One bureau verifies, another deletes | First bureau's verification is invalid |
| Bureau verifies, furnisher is silent | Bureau verified without source confirmation |

### Phase 5: Document Generation

At each stage, the system can generate appropriate documents:

| Stage | Documents |
|-------|-----------|
| Initial | Dispute Letter |
| Non-Compliant | Escalation Notice |
| Procedural | Cure Letter, MOV Demand |
| Substantive | Failure-to-Investigate Letter |
| Regulatory | CFPB Complaint Packet |
| Litigation | Attorney Evidence Bundle |

## Key Design Principles

### 1. User = Fact Reporter, System = Legal Decider

The user never interprets law. They just answer:
- "What entity responded?"
- "What did they say?"
- "When?"

The system determines legal consequences.

### 2. Silence Is An Action

If deadline passes with no response, the system automatically:
- Creates a NO_RESPONSE violation
- Escalates the dispute
- Queues enforcement documents

### 3. Verification Compounds Liability

When an entity "verifies" information that the system already determined is inaccurate, this suggests willful noncompliance (higher damages).

### 4. Everything Is Timestamped & Immutable

Every action is logged with UTC timestamp. States cannot be reversed. This creates an audit trail suitable for litigation.

### 5. Deadlines Are Source-Aware

- Standard dispute: 30 days
- AnnualCreditReport.com: 45 days
- Frivolous rejection cure: 15 days

## Implementation Status

| Component | Status |
|-----------|--------|
| Response Input UI | Pending |
| Deadline Engine | Pending |
| Escalation State Machine | Pending |
| Cross-Entity Detection | Pending |
| Document Generation | Existing (letters) |
| CFPB Complaint Generator | Pending |

## Files

- `docs/UNIFIED_RESPONSE_SYSTEM.md` - Complete technical specification
- `docs/RESPONSE_SYSTEM_OVERVIEW.md` - This file (high-level explainer)

## Next Steps

1. Build Response Input UI (dropdowns for entity/response type)
2. Create `disputes` and `dispute_responses` database tables
3. Implement deadline scheduler (daily cron job)
4. Build escalation state machine with transition logic
5. Add cross-entity intelligence queries
6. Generate CFPB complaint packet template
