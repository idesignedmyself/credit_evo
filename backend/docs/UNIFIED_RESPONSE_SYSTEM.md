# Unified Response → Paper Trail → Escalation System

## System Overview

This document defines the complete enforcement automation framework for FCRA/FDCPA regulatory compliance. The system operates as a deterministic state machine that tracks disputes, responses, deadlines, and escalations across Credit Reporting Agencies (CRAs), Furnishers, and Debt Collectors.

**Core Principle:** The user provides facts. The system makes legal determinations.

---

## 1. Entity Classification

### 1.1 Entity Types

| Entity Type | Definition | Primary Statutes |
|-------------|------------|------------------|
| CRA | Consumer Reporting Agency (Equifax, Experian, TransUnion) | FCRA §§ 611, 623 |
| Furnisher | Original Creditor or Data Furnisher | FCRA § 623(b), FDCPA § 1692g |
| Debt Collector | Third-party collector subject to FDCPA | FDCPA §§ 1692e, 1692f, 1692g |

### 1.2 Entity Identities

**CRAs:**
- Equifax Information Services LLC
- Experian Information Solutions Inc.
- TransUnion LLC

**Furnishers/Collectors:**
- Resolved from `creditor_name` field in violation data
- Normalized via `normalize_creditor_name()` for matching

---

## 2. Response Input System

### 2.1 User Interface Flow

```
Step 1: Select Entity Type
        └─→ CRA | Furnisher | Debt Collector

Step 2: Select Entity Identity
        └─→ [Dropdown populated based on Step 1]

Step 3: Select Response Type
        └─→ Deleted | Verified | Updated | Investigating | No Response | Rejected/Frivolous

Step 4: Enter Response Date
        └─→ [Date picker, cannot be future date]

Step 5: Attach Evidence (Optional)
        └─→ [File upload: PDF, image, or text entry]
```

### 2.2 Response Types

| Response Code | Display Label | Definition |
|---------------|---------------|------------|
| `DELETED` | Deleted | Entity confirms removal of disputed item |
| `VERIFIED` | Verified | Entity confirms accuracy without modification |
| `UPDATED` | Updated | Entity modified reported data |
| `INVESTIGATING` | Investigating | Entity claims investigation ongoing |
| `NO_RESPONSE` | No Response | Deadline passed with no communication |
| `REJECTED` | Rejected / Frivolous | Entity refuses to investigate |

---

## 3. Response → Violation Mapping

### 3.1 DELETED Response

**Legal Interpretation:**
Dispute successful. Item removed from consumer file.

**New Violations Created:**
- None (favorable outcome)

**Validation Required:**
- YES — Must verify deletion persists on next report
- Reinsertion triggers FCRA § 611(a)(5)(B) violation

**Deadline Recalculation:**
- No active deadline
- Reinsertion watch: 90-day monitoring period begins

**Escalation Queued:**
- No (unless reinsertion detected)

**Next State:** `RESOLVED_DELETED`

---

### 3.2 VERIFIED Response

**Legal Interpretation:**
Entity claims disputed information is accurate. This response COMPOUNDS liability if underlying violation exists.

**New Violations Created:**

| Condition | Violation | Statute |
|-----------|-----------|---------|
| CRA verified without furnisher contact | Failure to Conduct Reasonable Investigation | FCRA § 611(a)(1)(A) |
| Furnisher verified without substantiation | Failure to Investigate | FCRA § 623(b)(1) |
| Collector verified disputed debt | Continued Collection During Dispute | FDCPA § 1692g(b) |
| Any verification of provably false data | Willful Noncompliance | FCRA § 616 |

**Validation Required:**
- YES — User must confirm reported values unchanged
- System compares against original violation evidence

**Deadline Recalculation:**
- Method of Verification (MOV) demand deadline: 15 days from verification
- Escalation deadline: 30 days from verification

**Escalation Queued:**
- YES — Immediate escalation to `NON_COMPLIANT` state

**Next State:** `VERIFIED_DISPUTED`

---

### 3.3 UPDATED Response

**Legal Interpretation:**
Entity modified data. Modification may be partial, cosmetic, or substantive.

**New Violations Created:**

| Condition | Violation | Statute |
|-----------|-----------|---------|
| Update does not cure original violation | Continued Inaccuracy | FCRA § 623(a)(2) |
| Update creates new inconsistency | New Data Integrity Violation | FCRA § 607(b) |
| Partial update (some fields, not others) | Incomplete Investigation | FCRA § 611(a)(1)(A) |

**Validation Required:**
- YES — MANDATORY re-ingestion or manual value entry
- User must input new values for all updated fields
- System compares old → new → ground truth

**Deadline Recalculation:**
- If violation persists: New 30-day dispute cycle
- If cured: Close violation, maintain paper trail

**Escalation Queued:**
- Conditional — Only if update does not cure violation

**Next State:** `UPDATED_PENDING_VALIDATION`

---

### 3.4 INVESTIGATING Response

**Legal Interpretation:**
Entity claims ongoing investigation. This is a STALL TACTIC if received after statutory deadline.

**New Violations Created:**

| Condition | Violation | Statute |
|-----------|-----------|---------|
| Received after 30-day deadline | Failure to Complete Investigation | FCRA § 611(a)(1) |
| Received after 45-day deadline (ACR) | Failure to Complete Extended Investigation | FCRA § 612(a) |
| No final response within 15 days of this notice | Constructive No Response | FCRA § 611(a)(1) |

**Validation Required:**
- No (interim response)

**Deadline Recalculation:**
- Hard deadline: 15 days from "Investigating" notice
- If no final response by then: Auto-convert to `NO_RESPONSE`

**Escalation Queued:**
- YES — Flags entity for deadline monitoring

**Next State:** `INVESTIGATING_MONITORED`

---

### 3.5 NO_RESPONSE Response

**Legal Interpretation:**
Entity failed to respond within statutory period. This is an automatic violation.

**New Violations Created:**

| Entity Type | Violation | Statute |
|-------------|-----------|---------|
| CRA | Failure to Investigate Within 30 Days | FCRA § 611(a)(1)(A) |
| Furnisher | Failure to Investigate Notice of Dispute | FCRA § 623(b)(1)(A) |
| Collector | Failure to Cease Collection / Provide Validation | FDCPA § 1692g(b) |

**Validation Required:**
- No (failure state)

**Deadline Recalculation:**
- N/A — Deadline already breached

**Escalation Queued:**
- YES — Immediate escalation to `NON_COMPLIANT`

**Next State:** `NON_COMPLIANT`

---

### 3.6 REJECTED / FRIVOLOUS Response

**Legal Interpretation:**
Entity refuses to investigate, claiming dispute is frivolous or irrelevant. Heavily regulated under FCRA § 611(a)(3).

**Procedural Requirements for Valid Rejection:**

| Requirement | Statute | Description |
|-------------|---------|-------------|
| 5-Day Notice | § 611(a)(3)(A) | Must notify consumer within 5 business days |
| Specific Reason | § 611(a)(3)(B) | Must state specific reason for determination |
| Missing Information | § 611(a)(3)(B) | Must identify what information is needed |

**New Violations Created:**

| Condition | Violation | Statute |
|-----------|-----------|---------|
| No 5-day notice provided | Procedural Rejection Violation | FCRA § 611(a)(3)(A) |
| No specific reason stated | Invalid Frivolous Determination | FCRA § 611(a)(3)(B) |
| No cure opportunity provided | Denial of Procedural Rights | FCRA § 611(a)(3)(B) |
| Rejection of valid dispute | Willful Failure to Investigate | FCRA § 616 |

**Procedural Cure Logic:**
```
IF rejection lacks required specificity:
    → Generate Procedural Cure Letter
    → Demand specific deficiency identification
    → 15-day response deadline

IF consumer provides requested information:
    → New 30-day investigation deadline begins
    → Track as fresh dispute with same evidence chain

IF rejection is substantively invalid:
    → Flag as Illegal Refusal
    → Immediate escalation to REGULATORY_ESCALATION
```

**Validation Required:**
- YES — Must validate rejection meets procedural requirements

**Deadline Recalculation:**
- If procedurally valid: Cure deadline 30 days
- If procedurally invalid: Immediate escalation

**Escalation Queued:**
- YES — Either cure path or enforcement path

**Next State:** `REJECTED_PENDING_CURE` or `NON_COMPLIANT`

---

## 4. Deadline Engine

### 4.1 Source-Aware Deadlines

| Dispute Source | Standard Deadline | Extended Deadline | Statute |
|----------------|-------------------|-------------------|---------|
| Direct to CRA | 30 calendar days | N/A | FCRA § 611(a)(1)(A) |
| AnnualCreditReport.com | 45 calendar days | N/A | FCRA § 612(a) |
| Direct to Furnisher | 30 calendar days | N/A | FCRA § 623(b)(1) |
| Debt Validation Request | 30 calendar days | N/A | FDCPA § 1692g(b) |

### 4.2 Deadline Calculation Rules

```
DEADLINE_DATE = DISPUTE_SENT_DATE + DEADLINE_DAYS

IF dispute_source == "ANNUAL_CREDIT_REPORT":
    DEADLINE_DAYS = 45
ELSE:
    DEADLINE_DAYS = 30

IF entity provides additional_information_request:
    DEADLINE_DATE = ADDITIONAL_INFO_DATE + 15

DEADLINE_BREACH = CURRENT_DATE > DEADLINE_DATE AND response IS NULL
```

### 4.3 Deadline Breach Handling

```
ON deadline_breach:
    1. Create NO_RESPONSE violation automatically
    2. Set entity_status = NON_COMPLIANT
    3. Queue escalation letter generation
    4. Log immutable timestamp
    5. Calculate statutory damages eligibility
```

### 4.4 Scheduler Logic

**Daily Scheduler Tasks:**

| Task | Frequency | Action |
|------|-----------|--------|
| Deadline Check | Daily 00:00 UTC | Scan all open disputes for breaches |
| Reinsertion Watch | Daily 00:00 UTC | Flag deleted items for monitoring |
| Stall Detection | Daily 00:00 UTC | Convert stale INVESTIGATING to NO_RESPONSE |
| Escalation Queue | Daily 06:00 UTC | Generate queued escalation documents |

---

## 5. Validation Loop

### 5.1 Mandatory Validation Triggers

| Response Type | Validation Action |
|---------------|-------------------|
| DELETED | Reinsertion watch (90 days) |
| UPDATED | Force value re-entry or report re-ingestion |
| VERIFIED | Confirm values unchanged, compare to ground truth |

### 5.2 Ground Truth Comparison

```
FOR each disputed_field IN violation:
    original_value = violation.evidence[field]
    current_value = latest_report.get_field(field)
    entity_claimed_value = response.updated_value (if applicable)

    IF current_value != original_value AND response_type == VERIFIED:
        → Create "Verification of Inaccurate Data" violation

    IF current_value == original_value AND response_type == UPDATED:
        → Create "Cosmetic Update / No Change" violation

    IF current_value != entity_claimed_value:
        → Create "Entity Misrepresentation" violation
```

### 5.3 Reinsertion Detection

```
ON new_report_ingestion:
    FOR each previously_deleted_item:
        IF item reappears within 90 days:
            IF no 5-day advance notice received:
                → Create FCRA § 611(a)(5)(B) violation
                → Severity = CRITICAL
                → Auto-escalate to REGULATORY_ESCALATION
```

### 5.4 Mismatch Handling

| Mismatch Type | Resolution |
|---------------|------------|
| User vs Bureau | User ground truth prevails; document discrepancy |
| Bureau vs Furnisher | Cross-entity intelligence triggered |
| Bureau vs Bureau | Cross-bureau discrepancy violation created |

---

## 6. Cross-Entity Intelligence

### 6.1 Detection Patterns

#### Pattern 1: Bureau Deletes, Furnisher Re-Reports

```
CONDITION:
    CRA response = DELETED
    AND same account reappears within 90 days
    AND furnisher did not send reinsertion notice

VIOLATIONS:
    - FCRA § 611(a)(5)(B): Reinsertion Without Notice (CRA)
    - FCRA § 623(a)(6): Reporting Previously Deleted Information (Furnisher)

ESCALATION: REGULATORY_ESCALATION
```

#### Pattern 2: One Bureau Verifies, Another Deletes

```
CONDITION:
    Bureau_A response = VERIFIED
    AND Bureau_B response = DELETED
    AND same underlying account

VIOLATIONS:
    - FCRA § 611(a)(1)(A): Failure to Conduct Reasonable Investigation (Bureau_A)
    - Evidence: Deletion by peer bureau demonstrates inaccuracy

ESCALATION: NON_COMPLIANT (Bureau_A only)
```

#### Pattern 3: Bureau Verifies Without Furnisher Substantiation

```
CONDITION:
    CRA response = VERIFIED
    AND Furnisher response = NO_RESPONSE or DELETED

VIOLATIONS:
    - FCRA § 611(a)(1)(A): Verification Without Source Confirmation
    - Evidence: Furnisher silence contradicts CRA verification

ESCALATION: NON_COMPLIANT
```

#### Pattern 4: Cross-Bureau DOFD/Status Inconsistency

```
CONDITION:
    Account appears on multiple bureaus
    AND DOFD variance > 30 days
    OR Status codes conflict (e.g., "Paid" vs "Collection")

VIOLATIONS:
    - FCRA § 623(a)(2): Failure to Report Accurate Information
    - FCRA § 607(b): Failure to Maintain Maximum Possible Accuracy

ESCALATION: SUBSTANTIVE_ENFORCEMENT
```

---

## 7. Escalation State Machine

### 7.1 State Definitions

```
┌─────────────┐
│  DETECTED   │ ← Initial violation discovery
└──────┬──────┘
       │ User initiates dispute
       ▼
┌─────────────┐
│  DISPUTED   │ ← Dispute sent, awaiting response
└──────┬──────┘
       │ Response received OR deadline passes
       ▼
┌─────────────────────┐
│ RESPONDED/NO_RESPONSE│
└──────┬──────────────┘
       │ System evaluates response
       ▼
┌─────────────┐
│  EVALUATED  │ ← Legal determination made
└──────┬──────┘
       │ Response inadequate or absent
       ▼
┌───────────────┐
│ NON_COMPLIANT │ ← Entity failed statutory duty
└──────┬────────┘
       │ Procedural remedy available
       ▼
┌─────────────────────────┐
│ PROCEDURAL_ENFORCEMENT  │ ← Cure letters, MOV demands
└──────┬──────────────────┘
       │ Procedural remedy exhausted
       ▼
┌─────────────────────────┐
│ SUBSTANTIVE_ENFORCEMENT │ ← Failure-to-investigate letters
└──────┬──────────────────┘
       │ Entity remains non-compliant
       ▼
┌───────────────────────┐
│ REGULATORY_ESCALATION │ ← CFPB complaint, AG referral
└──────┬────────────────┘
       │ All remedies exhausted
       ▼
┌──────────────────┐
│ LITIGATION_READY │ ← Evidence bundle complete
└──────────────────┘
```

### 7.2 State Specifications

#### DETECTED

| Property | Value |
|----------|-------|
| Entry Conditions | Violation identified by audit engine |
| Exit Conditions | User generates dispute letter |
| Allowed Outputs | Initial dispute letter |
| Statutes Activated | Underlying violation statute |
| Tone Posture | Informational |

---

#### DISPUTED

| Property | Value |
|----------|-------|
| Entry Conditions | Dispute letter sent, send date recorded |
| Exit Conditions | Response received OR deadline passes |
| Allowed Outputs | None (waiting state) |
| Statutes Activated | FCRA § 611(a)(1) / § 623(b)(1) |
| Tone Posture | Informational |

---

#### RESPONDED / NO_RESPONSE

| Property | Value |
|----------|-------|
| Entry Conditions | User logs response OR deadline breach detected |
| Exit Conditions | System completes legal evaluation |
| Allowed Outputs | Validation prompts |
| Statutes Activated | Response-specific (see Section 3) |
| Tone Posture | Informational |

---

#### EVALUATED

| Property | Value |
|----------|-------|
| Entry Conditions | Response mapped to violations |
| Exit Conditions | Compliance or non-compliance determined |
| Allowed Outputs | Evaluation summary |
| Statutes Activated | All applicable based on response |
| Tone Posture | Informational |

---

#### NON_COMPLIANT

| Property | Value |
|----------|-------|
| Entry Conditions | Entity failed statutory duty |
| Exit Conditions | Procedural enforcement initiated |
| Allowed Outputs | Escalation notice, procedural cure letter |
| Statutes Activated | § 611(a), § 623(b), § 1692g |
| Tone Posture | Assertive |

---

#### PROCEDURAL_ENFORCEMENT

| Property | Value |
|----------|-------|
| Entry Conditions | Non-compliance confirmed, cure available |
| Exit Conditions | Cure period expires OR entity cures |
| Allowed Outputs | MOV demand, procedural cure letter |
| Statutes Activated | § 611(a)(6)(B)(iii), § 623(b)(1)(B) |
| Tone Posture | Enforcement |

---

#### SUBSTANTIVE_ENFORCEMENT

| Property | Value |
|----------|-------|
| Entry Conditions | Procedural remedies exhausted |
| Exit Conditions | Entity cures OR regulatory escalation |
| Allowed Outputs | Failure-to-investigate letter, formal demand |
| Statutes Activated | § 616, § 617, § 1692k |
| Tone Posture | Enforcement |

---

#### REGULATORY_ESCALATION

| Property | Value |
|----------|-------|
| Entry Conditions | Substantive enforcement failed |
| Exit Conditions | Regulatory complaint filed |
| Allowed Outputs | CFPB complaint packet, AG referral |
| Statutes Activated | § 621 (CFPB enforcement authority) |
| Tone Posture | Regulatory |

---

#### LITIGATION_READY

| Property | Value |
|----------|-------|
| Entry Conditions | All remedies exhausted, damages documented |
| Exit Conditions | None (terminal state) |
| Allowed Outputs | Attorney evidence bundle |
| Statutes Activated | § 616 (willful), § 617 (negligent), § 1692k |
| Tone Posture | Litigation |

---

## 8. Output Artifacts

### 8.1 Artifact Generation by State

| State | Available Artifacts |
|-------|---------------------|
| DETECTED | Initial Dispute Letter |
| DISPUTED | Dispute Tracking Summary |
| NON_COMPLIANT | Escalation Notice |
| PROCEDURAL_ENFORCEMENT | Procedural Cure Letter, MOV Demand |
| SUBSTANTIVE_ENFORCEMENT | Failure-to-Investigate Letter, Formal Demand |
| REGULATORY_ESCALATION | CFPB Complaint Packet, AG Referral Letter |
| LITIGATION_READY | Attorney Evidence Bundle |

### 8.2 Artifact Specifications

#### Initial Dispute Letter
- Entity-routed (CRA/Furnisher/Collector)
- Statute-cited violations
- Evidence summary
- Response deadline stated
- Return receipt requested

#### Procedural Cure Letter
- Identifies specific procedural failure
- Cites § 611(a)(3) requirements
- Provides cure deadline (15 days)
- Warns of escalation

#### Method of Verification Demand
- Cites § 611(a)(6)(B)(iii)
- Demands description of reinvestigation procedure
- Demands business name/address of information source
- Demands telephone number of source (if reasonably available)
- 15-day response deadline

#### Failure-to-Investigate Letter
- Documents complete timeline
- Lists all statutory violations
- Calculates statutory damages range
- Demands immediate deletion
- Final opportunity before regulatory action

#### CFPB Complaint Packet
- Structured complaint narrative
- Complete evidence timeline
- All correspondence attached
- Statutory violations enumerated
- Damages documented

#### Attorney Evidence Bundle
- Chronological event log
- All letters sent/received
- Response analysis
- Violation summary with statutes
- Damages calculation
- Witness statement (consumer declaration)

---

## 9. Design Constraints

### 9.1 Immutability Rules

| Element | Immutability |
|---------|--------------|
| Violation detection timestamp | Immutable |
| Dispute send date | Immutable |
| Response received date | Immutable |
| Deadline calculations | Immutable once set |
| State transitions | Append-only log |

### 9.2 Non-Reversible States

The following states cannot be reversed:
- `NON_COMPLIANT` → Cannot return to `EVALUATED`
- `REGULATORY_ESCALATION` → Cannot return to `SUBSTANTIVE_ENFORCEMENT`
- `LITIGATION_READY` → Terminal state

### 9.3 Silence as Action

```
IF entity_response IS NULL AND deadline_passed:
    entity_action = NO_RESPONSE
    # Silence is treated as affirmative failure to act
```

### 9.4 Verification Compounds Liability

```
IF response_type == VERIFIED AND original_violation_valid:
    liability_multiplier = 2.0
    # Verification of known inaccuracy suggests willfulness
    # Willful noncompliance: $100-$1,000 per violation (§ 616)
```

### 9.5 Timestamp Requirements

All events must record:
- UTC timestamp
- Actor (user, system, entity)
- Action taken
- Evidence hash (if applicable)
- State before/after

---

## 10. Database Schema (Conceptual)

### 10.1 Core Tables

```sql
-- Dispute tracking
CREATE TABLE disputes (
    id UUID PRIMARY KEY,
    violation_id UUID REFERENCES violations(id),
    entity_type ENUM('CRA', 'FURNISHER', 'COLLECTOR'),
    entity_name VARCHAR(255),
    dispute_date DATE NOT NULL,
    deadline_date DATE NOT NULL,
    source ENUM('DIRECT', 'ANNUAL_CREDIT_REPORT'),
    status ENUM('OPEN', 'RESPONDED', 'BREACHED', 'CLOSED'),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Response tracking
CREATE TABLE dispute_responses (
    id UUID PRIMARY KEY,
    dispute_id UUID REFERENCES disputes(id),
    response_type ENUM('DELETED', 'VERIFIED', 'UPDATED', 'INVESTIGATING', 'NO_RESPONSE', 'REJECTED'),
    response_date DATE,
    evidence_path VARCHAR(500),
    new_violations JSON,
    created_at TIMESTAMP DEFAULT NOW()
);

-- State machine log
CREATE TABLE escalation_log (
    id UUID PRIMARY KEY,
    dispute_id UUID REFERENCES disputes(id),
    from_state VARCHAR(50),
    to_state VARCHAR(50),
    trigger VARCHAR(100),
    statutes_activated JSON,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Paper trail
CREATE TABLE paper_trail (
    id UUID PRIMARY KEY,
    dispute_id UUID REFERENCES disputes(id),
    artifact_type VARCHAR(50),
    artifact_path VARCHAR(500),
    generated_at TIMESTAMP DEFAULT NOW(),
    sent_at TIMESTAMP,
    delivery_confirmed BOOLEAN DEFAULT FALSE
);
```

---

## 11. API Endpoints (Conceptual)

```
POST   /api/disputes                    # Create new dispute
GET    /api/disputes/{id}               # Get dispute details
POST   /api/disputes/{id}/response      # Log entity response
GET    /api/disputes/{id}/timeline      # Get full paper trail
POST   /api/disputes/{id}/escalate      # Manual escalation trigger
GET    /api/disputes/{id}/artifacts     # List generated documents
POST   /api/disputes/{id}/artifacts     # Generate new artifact
GET    /api/scheduler/deadlines         # Get upcoming deadlines
POST   /api/validation/compare          # Compare ground truth
```

---

## 12. Implementation Checklist

| Component | Status |
|-----------|--------|
| Response Input UI | PENDING |
| Response → Violation Mapping | PENDING |
| Deadline Engine | PENDING |
| Validation Loop | PENDING |
| Cross-Entity Intelligence | PENDING |
| Escalation State Machine | PENDING |
| Artifact Generation | PENDING |
| Paper Trail Database | PENDING |
| Daily Scheduler | PENDING |
| CFPB Complaint Generator | PENDING |

---

## Appendix A: Statute Quick Reference

| Statute | Description | Applies To |
|---------|-------------|------------|
| FCRA § 607(b) | Maximum Possible Accuracy | CRA |
| FCRA § 611(a)(1)(A) | Duty to Investigate | CRA |
| FCRA § 611(a)(3) | Frivolous Dispute Procedures | CRA |
| FCRA § 611(a)(5)(B) | Reinsertion Notice | CRA |
| FCRA § 611(a)(6)(B)(iii) | Method of Verification | CRA |
| FCRA § 616 | Willful Noncompliance | CRA, Furnisher |
| FCRA § 617 | Negligent Noncompliance | CRA, Furnisher |
| FCRA § 623(a)(2) | Duty to Report Accurately | Furnisher |
| FCRA § 623(b)(1) | Duty to Investigate | Furnisher |
| FDCPA § 1692e | False Representations | Collector |
| FDCPA § 1692f | Unfair Practices | Collector |
| FDCPA § 1692g | Validation of Debts | Collector |
| FDCPA § 1692k | Civil Liability | Collector |

---

## Appendix B: Damages Reference

| Violation Type | Statutory Damages | Actual Damages |
|----------------|-------------------|----------------|
| FCRA Negligent (§ 617) | N/A | Actual damages + attorney fees |
| FCRA Willful (§ 616) | $100 - $1,000 per violation | Actual damages + punitive + attorney fees |
| FDCPA (§ 1692k) | Up to $1,000 per case | Actual damages + attorney fees |
| FDCPA Class Action | Up to $500,000 or 1% of net worth | Per class member |

---

*Document Version: 1.0*
*System Status: SPECIFICATION COMPLETE*
