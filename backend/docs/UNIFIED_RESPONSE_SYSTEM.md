# Unified Response → Paper Trail → Escalation System

## System Overview

This document defines the complete enforcement automation framework for FCRA/FDCPA regulatory compliance. The system operates as a deterministic state machine that tracks disputes, responses, deadlines, and escalations across Credit Reporting Agencies (CRAs), Furnishers, and Debt Collectors.

**Core Principle:** The user provides facts. The system makes legal determinations.

---

## 1. Authority Model

### 1.1 User-Authorized Actions

The user may perform the following actions. These require explicit user initiation:

| Action | Description | System Role |
|--------|-------------|-------------|
| Initiate Dispute | User decides to dispute a violation | System generates letter |
| Log Response | User reports entity response received | System evaluates response |
| Upload Report | User provides new credit report | System ingests and compares |
| Confirm Mailing | User confirms letter was sent | System starts deadline clock |

### 1.2 System-Authoritative Actions

The following actions are executed by the system WITHOUT user confirmation:

| Action | Trigger | Authority |
|--------|---------|-----------|
| Deadline Breach Detection | `CURRENT_DATE > DEADLINE_DATE` | Automatic |
| NO_RESPONSE Violation Creation | Deadline breach + no response logged | Automatic |
| Reinsertion Detection | Deleted item reappears on new report | Automatic |
| Reinsertion Violation Creation | Reinsertion detected + no 5-day notice | Automatic |
| State Escalation | Non-compliance confirmed | Automatic |
| INVESTIGATING → NO_RESPONSE Conversion | 15-day stall limit exceeded | Automatic |
| Cross-Entity Violation Detection | Pattern match across entities | Automatic |

### 1.3 Authority Boundary

```
USER BOUNDARY:
    - Reports facts (dates, responses, evidence)
    - Initiates dispute process
    - Uploads new reports for validation

SYSTEM BOUNDARY:
    - Interprets legal significance
    - Creates violations
    - Calculates deadlines
    - Triggers escalations
    - Detects reinsertion
    - Generates documents
```

---

## 2. Entity Classification

### 2.1 Entity Types

| Entity Type | Definition | Primary Statutes |
|-------------|------------|------------------|
| CRA | Consumer Reporting Agency (Equifax, Experian, TransUnion) | FCRA §§ 611, 607 |
| Furnisher | Original Creditor or Data Furnisher | FCRA § 623(a), § 623(b) |
| Debt Collector | Third-party collector subject to FDCPA | FDCPA §§ 1692e, 1692f, 1692g |

### 2.2 Entity Identities

**CRAs:**
- Equifax Information Services LLC
- Experian Information Solutions Inc.
- TransUnion LLC

**Furnishers/Collectors:**
- Resolved from `creditor_name` field in violation data
- Normalized via `normalize_creditor_name()` for matching

---

## 3. Response Input System

### 3.1 User Interface Flow

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

### 3.2 Response Types

| Response Code | Display Label | Definition | Source |
|---------------|---------------|------------|--------|
| `DELETED` | Deleted | Entity confirms removal of disputed item | User-reported |
| `VERIFIED` | Verified | Entity confirms accuracy without modification | User-reported |
| `UPDATED` | Updated | Entity modified reported data | User-reported |
| `INVESTIGATING` | Investigating | Entity claims investigation ongoing | User-reported |
| `NO_RESPONSE` | No Response | Deadline passed with no communication | User-reported OR System-detected |
| `REJECTED` | Rejected / Frivolous | Entity refuses to investigate | User-reported |

---

## 4. Response → Violation Mapping

### 4.1 DELETED Response

**Legal Interpretation:**
Dispute successful. Item removed from consumer file.

**New Violations Created:**
- None (favorable outcome)

**Validation Required:**
- YES — System activates reinsertion monitoring (see Section 6)

**Deadline Recalculation:**
- No active deadline
- Reinsertion watch: 90-day monitoring window begins

**Escalation Queued:**
- No (unless reinsertion detected by system)

**Next State:** `RESOLVED_DELETED`

---

### 4.2 VERIFIED Response

**Legal Interpretation:**
Entity claims disputed information is accurate. This response COMPOUNDS liability if underlying violation exists.

**New Violations Created:**

| Condition | Violation | Statute |
|-----------|-----------|---------|
| CRA verified without furnisher contact | Failure to Conduct Reasonable Investigation | FCRA § 611(a)(1)(A) |
| Furnisher verified without substantiation | Failure to Investigate | FCRA § 623(b)(1) |
| Collector verified disputed debt | See §1692g(b) Guardrail (Section 5) | Conditional |
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

### 4.3 UPDATED Response

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

### 4.4 INVESTIGATING Response

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
- System auto-converts to `NO_RESPONSE` if deadline passes (no user input required)

**Escalation Queued:**
- YES — Flags entity for deadline monitoring

**Next State:** `INVESTIGATING_MONITORED`

---

### 4.5 NO_RESPONSE Response

**Legal Interpretation:**
Entity failed to respond within statutory period. This is an automatic violation.

**Detection Methods:**
1. **User-reported:** User explicitly logs "No Response"
2. **System-detected:** Deadline passes with no response logged

**New Violations Created:**

| Entity Type | Violation | Statute | Preconditions |
|-------------|-----------|---------|---------------|
| CRA | Failure to Investigate Within 30 Days | FCRA § 611(a)(1)(A) | None |
| Furnisher | Failure to Investigate Notice of Dispute | FCRA § 623(b)(1)(A) | None |
| Collector | Failure to Provide Validation | FDCPA § 1692g(b) | See §1692g(b) Guardrail |

**Validation Required:**
- No (failure state)

**Deadline Recalculation:**
- N/A — Deadline already breached

**Escalation Queued:**
- YES — Immediate escalation to `NON_COMPLIANT` (system-triggered)

**Next State:** `NON_COMPLIANT`

---

### 4.6 REJECTED / FRIVOLOUS Response

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

## 5. FDCPA § 1692g(b) Guardrail

### 5.1 Statutory Preconditions

FDCPA § 1692g(b) applies ONLY when ALL of the following conditions are met:

| Precondition | Description | Required |
|--------------|-------------|----------|
| Entity is Debt Collector | Third-party collector, not original creditor | YES |
| Debt Validation Request Exists | Consumer sent written validation request within 30 days of initial communication | YES |
| Collection Continued Before Validation | Collector continued collection activity OR credit reporting before providing validation | YES |

### 5.2 Guardrail Logic

```
FUNCTION can_cite_1692g_b(entity, dispute):
    IF entity.type != DEBT_COLLECTOR:
        RETURN FALSE

    IF NOT dispute.has_validation_request:
        RETURN FALSE

    IF NOT dispute.collection_continued_before_validation:
        RETURN FALSE

    RETURN TRUE
```

### 5.3 Application Rules

| Scenario | §1692g(b) Applicable | Reason |
|----------|----------------------|--------|
| Collector verified disputed debt, validation request sent | YES | All preconditions met |
| Collector verified disputed debt, no validation request | NO | Missing validation request precondition |
| Furnisher verified disputed debt | NO | Entity is not debt collector |
| Collector no response, validation request sent | YES | Failure to validate per §1692g(b) |
| Collector no response, no validation request | NO | Missing validation request precondition |

### 5.4 Alternative Statutes

When §1692g(b) preconditions are NOT met, use:

| Scenario | Alternative Statute |
|----------|---------------------|
| Collector reports inaccurate information | FDCPA § 1692e(8) |
| Collector uses unfair collection practices | FDCPA § 1692f |
| Collector makes false representations | FDCPA § 1692e |

---

## 6. Reinsertion Detection System

### 6.1 System Classification

Reinsertion is a **SYSTEM-DETECTED** violation, not a user-reported response.

| Attribute | Value |
|-----------|-------|
| Detection Method | Automatic comparison during report ingestion |
| User Input Required | NO |
| Trigger | New report uploaded during monitoring window |
| Authority | System-authoritative |

### 6.2 Monitoring Window

```
ON response_type == DELETED:
    monitoring_start = response_date
    monitoring_end = response_date + 90 days
    deleted_item_fingerprint = generate_fingerprint(violation.account)

    INSERT INTO reinsertion_watch (
        violation_id,
        account_fingerprint,
        monitoring_start,
        monitoring_end,
        status = 'ACTIVE'
    )
```

### 6.3 Detection Logic

```
ON new_report_ingestion:
    active_watches = SELECT * FROM reinsertion_watch
                     WHERE status = 'ACTIVE'
                     AND monitoring_end > CURRENT_DATE

    FOR each watch IN active_watches:
        current_accounts = extract_account_fingerprints(new_report)

        IF watch.account_fingerprint IN current_accounts:
            # REINSERTION DETECTED
            reinsertion_detected(watch, new_report)
```

### 6.4 Violation Creation

```
FUNCTION reinsertion_detected(watch, new_report):
    # Check for 5-day advance notice
    notice_received = check_reinsertion_notice(watch.violation_id)

    IF NOT notice_received:
        # Create FCRA § 611(a)(5)(B) violation
        CREATE violation:
            type = REINSERTION_WITHOUT_NOTICE
            statute = "FCRA § 611(a)(5)(B)"
            severity = CRITICAL
            description = "Item previously deleted was reinserted without required 5-day advance notice"
            evidence = {
                original_deletion_date: watch.monitoring_start,
                reinsertion_date: new_report.report_date,
                account_fingerprint: watch.account_fingerprint,
                notice_received: FALSE
            }

        # Flag as willful noncompliance
        SET violation.willful_indicator = TRUE
        SET violation.statute_616_exposure = TRUE

        # Auto-escalate (no user confirmation required)
        escalate_to_state(REGULATORY_ESCALATION)

        # Create furnisher violation
        CREATE violation:
            type = FURNISHER_REINSERTION
            statute = "FCRA § 623(a)(6)"
            entity = watch.furnisher_name
            severity = CRITICAL
```

### 6.5 Reinsertion Notice Validation

If user reports receiving a reinsertion notice:

```
FUNCTION log_reinsertion_notice(watch_id, notice_date, notice_content):
    IF notice_date < reinsertion_date - 5 business days:
        # Valid notice - no violation
        UPDATE reinsertion_watch SET status = 'NOTICE_RECEIVED'
        RETURN no_violation
    ELSE:
        # Invalid notice - late
        CREATE violation:
            type = LATE_REINSERTION_NOTICE
            statute = "FCRA § 611(a)(5)(B)(ii)"
            severity = HIGH
```

### 6.6 Cross-Reference Points

Reinsertion detection is referenced in:
- **Validation Loop (Section 8):** Triggered during report re-ingestion
- **Deadline Engine (Section 7):** Daily scheduler checks monitoring windows
- **Escalation State Machine (Section 10):** Auto-escalates to REGULATORY_ESCALATION
- **Cross-Entity Intelligence (Section 9):** Pattern 1 (Bureau deletes, furnisher re-reports)

---

## 7. Deadline Engine

### 7.1 Source-Aware Deadlines

| Dispute Source | Standard Deadline | Statute |
|----------------|-------------------|---------|
| Direct to CRA | 30 calendar days | FCRA § 611(a)(1)(A) |
| AnnualCreditReport.com | 45 calendar days | FCRA § 612(a) |
| Direct to Furnisher | 30 calendar days | FCRA § 623(b)(1) |
| Debt Validation Request | 30 calendar days | FDCPA § 1692g(b) (if preconditions met) |

### 7.2 Deadline Calculation Rules

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

### 7.3 Deadline Breach Handling (System-Triggered)

```
ON deadline_breach:
    # NO USER CONFIRMATION REQUIRED
    1. Create NO_RESPONSE violation automatically
    2. Set entity_status = NON_COMPLIANT
    3. Queue escalation letter generation
    4. Log immutable timestamp
    5. Calculate statutory damages eligibility
    6. Trigger state transition to NON_COMPLIANT
```

### 7.4 Scheduler Logic

**Daily Scheduler Tasks (System-Authoritative):**

| Task | Frequency | Action | User Confirmation |
|------|-----------|--------|-------------------|
| Deadline Check | Daily 00:00 UTC | Scan all open disputes for breaches | NO |
| Reinsertion Watch | Daily 00:00 UTC | Check active monitoring windows | NO |
| Stall Detection | Daily 00:00 UTC | Convert stale INVESTIGATING to NO_RESPONSE | NO |
| Escalation Queue | Daily 06:00 UTC | Generate queued escalation documents | NO |

---

## 8. Validation Loop

### 8.1 Mandatory Validation Triggers

| Response Type | Validation Action | Trigger |
|---------------|-------------------|---------|
| DELETED | Reinsertion monitoring activated | System-automatic |
| UPDATED | Force value re-entry or report re-ingestion | User-initiated |
| VERIFIED | Confirm values unchanged, compare to ground truth | User-initiated |

### 8.2 Ground Truth Comparison

```
FOR each disputed_field IN violation:
    original_value = violation.evidence[field]
    current_value = latest_report.get_field(field)
    entity_claimed_value = response.updated_value (if applicable)

    IF current_value != original_value AND response_type == VERIFIED:
        → Create "Verification of Inaccurate Data" violation (system-created)

    IF current_value == original_value AND response_type == UPDATED:
        → Create "Cosmetic Update / No Change" violation (system-created)

    IF current_value != entity_claimed_value:
        → Create "Entity Misrepresentation" violation (system-created)
```

### 8.3 Report Re-Ingestion Flow

```
ON user_uploads_new_report:
    1. Parse report (existing parser)
    2. Check reinsertion watches (system-automatic)
    3. Compare updated fields against pending validations
    4. Create violations for mismatches (system-automatic)
    5. Update validation status
```

### 8.4 Mismatch Handling

| Mismatch Type | Resolution | Authority |
|---------------|------------|-----------|
| User vs Bureau | User ground truth prevails; document discrepancy | System determination |
| Bureau vs Furnisher | Cross-entity intelligence triggered | System-automatic |
| Bureau vs Bureau | Cross-bureau discrepancy violation created | System-automatic |

---

## 9. Cross-Entity Intelligence

### 9.1 Detection Patterns (System-Automatic)

All cross-entity patterns are detected automatically by the system during response evaluation or report ingestion.

#### Pattern 1: Bureau Deletes, Furnisher Re-Reports

```
CONDITION:
    CRA response = DELETED
    AND same account reappears within 90 days (detected by reinsertion system)
    AND furnisher did not send reinsertion notice

VIOLATIONS (system-created):
    - FCRA § 611(a)(5)(B): Reinsertion Without Notice (CRA)
    - FCRA § 623(a)(6): Reporting Previously Deleted Information (Furnisher)

ESCALATION: REGULATORY_ESCALATION (automatic)
```

#### Pattern 2: One Bureau Verifies, Another Deletes

```
CONDITION:
    Bureau_A response = VERIFIED
    AND Bureau_B response = DELETED
    AND same underlying account (fingerprint match)

VIOLATIONS (system-created):
    - FCRA § 611(a)(1)(A): Failure to Conduct Reasonable Investigation (Bureau_A)
    - Evidence: Deletion by peer bureau demonstrates inaccuracy

ESCALATION: NON_COMPLIANT (Bureau_A only, automatic)
```

#### Pattern 3: Bureau Verifies Without Furnisher Substantiation

```
CONDITION:
    CRA response = VERIFIED
    AND Furnisher response = NO_RESPONSE or DELETED

VIOLATIONS (system-created):
    - FCRA § 611(a)(1)(A): Verification Without Source Confirmation
    - Evidence: Furnisher silence contradicts CRA verification

ESCALATION: NON_COMPLIANT (automatic)
```

#### Pattern 4: Cross-Bureau DOFD/Status Inconsistency

```
CONDITION:
    Account appears on multiple bureaus
    AND DOFD variance > 30 days
    OR Status codes conflict (e.g., "Paid" vs "Collection")

VIOLATIONS (system-created):
    - FCRA § 623(a)(2): Failure to Report Accurate Information
    - FCRA § 607(b): Failure to Maintain Maximum Possible Accuracy

ESCALATION: SUBSTANTIVE_ENFORCEMENT (automatic)
```

---

## 10. Escalation State Machine

### 10.1 State Diagram

```
┌─────────────┐
│  DETECTED   │ ← Initial violation discovery
└──────┬──────┘
       │ User initiates dispute (USER ACTION)
       ▼
┌─────────────┐
│  DISPUTED   │ ← Dispute sent, awaiting response
└──────┬──────┘
       │ Response received (USER) OR deadline passes (SYSTEM)
       ▼
┌─────────────────────┐
│ RESPONDED/NO_RESPONSE│
└──────┬──────────────┘
       │ System evaluates response (SYSTEM ACTION)
       ▼
┌─────────────┐
│  EVALUATED  │ ← Legal determination made
└──────┬──────┘
       │ Response inadequate or absent (SYSTEM DETERMINATION)
       ▼
┌───────────────┐
│ NON_COMPLIANT │ ← Entity failed statutory duty
└──────┬────────┘
       │ Procedural remedy available (SYSTEM DETERMINATION)
       ▼
┌─────────────────────────┐
│ PROCEDURAL_ENFORCEMENT  │ ← Cure letters, MOV demands
└──────┬──────────────────┘
       │ Procedural remedy exhausted (SYSTEM DETERMINATION)
       ▼
┌─────────────────────────┐
│ SUBSTANTIVE_ENFORCEMENT │ ← Failure-to-investigate letters
└──────┬──────────────────┘
       │ Entity remains non-compliant (SYSTEM DETERMINATION)
       ▼
┌───────────────────────┐
│ REGULATORY_ESCALATION │ ← CFPB complaint, AG referral
└──────┬────────────────┘
       │ All remedies exhausted (SYSTEM DETERMINATION)
       ▼
┌──────────────────┐
│ LITIGATION_READY │ ← Evidence bundle complete
└──────────────────┘

SPECIAL PATH (Reinsertion):
┌─────────────────┐
│ RESOLVED_DELETED│
└──────┬──────────┘
       │ Reinsertion detected (SYSTEM-AUTOMATIC)
       ▼
┌───────────────────────┐
│ REGULATORY_ESCALATION │ ← Bypasses intermediate states
└───────────────────────┘
```

### 10.2 State Specifications

#### DETECTED

| Property | Value |
|----------|-------|
| Entry Conditions | Violation identified by audit engine (system) |
| Exit Conditions | User generates dispute letter (user action) |
| Allowed Outputs | Initial dispute letter |
| Statutes Activated | Underlying violation statute |
| Tone Posture | Informational |
| Authority | System entry, user exit |

---

#### DISPUTED

| Property | Value |
|----------|-------|
| Entry Conditions | Dispute letter sent, send date recorded (user confirms) |
| Exit Conditions | Response received (user) OR deadline passes (system) |
| Allowed Outputs | None (waiting state) |
| Statutes Activated | FCRA § 611(a)(1) / § 623(b)(1) |
| Tone Posture | Informational |
| Authority | User entry, user OR system exit |

---

#### RESPONDED / NO_RESPONSE

| Property | Value |
|----------|-------|
| Entry Conditions | User logs response OR deadline breach detected (system) |
| Exit Conditions | System completes legal evaluation |
| Allowed Outputs | Validation prompts |
| Statutes Activated | Response-specific (see Section 4) |
| Tone Posture | Informational |
| Authority | User or system entry, system exit |

---

#### EVALUATED

| Property | Value |
|----------|-------|
| Entry Conditions | Response mapped to violations (system) |
| Exit Conditions | Compliance or non-compliance determined (system) |
| Allowed Outputs | Evaluation summary |
| Statutes Activated | All applicable based on response |
| Tone Posture | Informational |
| Authority | System only |

---

#### NON_COMPLIANT

| Property | Value |
|----------|-------|
| Entry Conditions | Entity failed statutory duty (system determination) |
| Exit Conditions | Procedural enforcement initiated (system) |
| Allowed Outputs | Escalation notice, procedural cure letter |
| Statutes Activated | § 611(a), § 623(b), § 1692g (if preconditions met) |
| Tone Posture | Assertive |
| Authority | System only |

---

#### PROCEDURAL_ENFORCEMENT

| Property | Value |
|----------|-------|
| Entry Conditions | Non-compliance confirmed, cure available (system) |
| Exit Conditions | Cure period expires (system) OR entity cures (user reports) |
| Allowed Outputs | MOV demand, procedural cure letter |
| Statutes Activated | § 611(a)(6)(B)(iii), § 623(b)(1)(B) |
| Tone Posture | Enforcement |
| Authority | System entry, system or user exit |

---

#### SUBSTANTIVE_ENFORCEMENT

| Property | Value |
|----------|-------|
| Entry Conditions | Procedural remedies exhausted (system) |
| Exit Conditions | Entity cures (user reports) OR regulatory escalation (system) |
| Allowed Outputs | Failure-to-investigate letter, formal demand |
| Statutes Activated | § 616, § 617, § 1692k (if preconditions met) |
| Tone Posture | Enforcement |
| Authority | System entry, system or user exit |

---

#### REGULATORY_ESCALATION

| Property | Value |
|----------|-------|
| Entry Conditions | Substantive enforcement failed (system) OR reinsertion detected (system) |
| Exit Conditions | Regulatory complaint filed (user confirms) |
| Allowed Outputs | CFPB complaint packet, AG referral |
| Statutes Activated | § 621 (CFPB enforcement authority) |
| Tone Posture | Regulatory |
| Authority | System entry, user exit |

---

#### LITIGATION_READY

| Property | Value |
|----------|-------|
| Entry Conditions | All remedies exhausted, damages documented (system) |
| Exit Conditions | None (terminal state) |
| Allowed Outputs | Attorney evidence bundle |
| Statutes Activated | § 616 (willful), § 617 (negligent), § 1692k |
| Tone Posture | Litigation |
| Authority | System only (terminal) |

---

## 11. UI Access & Observability Layer

### 11.1 Functional UI Surfaces

The following UI access points expose enforcement system data to users WITHOUT granting legal control.

#### 11.1.1 Dispute Timeline View

| Attribute | Description |
|-----------|-------------|
| Purpose | Display chronological, immutable record of all dispute events |
| Data Source | `paper_trail` table, `escalation_log` table |
| User Actions | View only (no modification) |
| Content | Timestamps, actions, actors, state transitions, evidence hashes |

**Display Elements:**
- Date/time of each event (UTC)
- Actor label: `USER` | `SYSTEM` | `ENTITY`
- Action description
- State before → after
- Attached evidence (if any)
- Statute citations (if violation created)

---

#### 11.1.2 Current State Indicator

| Attribute | Description |
|-----------|-------------|
| Purpose | Show current position in escalation state machine |
| Data Source | `disputes.status`, `escalation_log.to_state` |
| User Actions | View only |
| Content | Current state name, available actions, next deadline |

**Display Elements:**
- State name (e.g., "PROCEDURAL_ENFORCEMENT")
- State description
- Available outputs at this state
- Days until next system action
- Tone posture indicator

---

#### 11.1.3 System-Triggered Events Panel

| Attribute | Description |
|-----------|-------------|
| Purpose | Display pending and completed system-automatic actions |
| Data Source | Scheduler queue, `escalation_log` where actor = 'SYSTEM' |
| User Actions | View only |
| Content | Upcoming deadlines, reinsertion alerts, auto-escalations |

**Display Elements:**
- Upcoming deadline breaches (with countdown)
- Active reinsertion monitoring windows
- Pending auto-escalations
- Recently executed system actions
- Cross-entity pattern alerts

---

#### 11.1.4 Response Input Form

| Attribute | Description |
|-----------|-------------|
| Purpose | Capture user-reported entity responses |
| Data Source | User input |
| User Actions | Select entity, select response type, enter date, attach evidence |
| Content | Dropdowns, date picker, file upload |

**Display Elements:**
- Entity type selector
- Entity name selector (filtered by type)
- Response type dropdown
- Response date picker
- Evidence attachment
- Submission confirmation

---

#### 11.1.5 Artifact Generation Panel

| Attribute | Description |
|-----------|-------------|
| Purpose | Display available documents for current state |
| Data Source | State → artifact mapping |
| User Actions | Request document generation, download |
| Content | List of available artifacts, generation status |

**Display Elements:**
- Available artifact types for current state
- Previously generated artifacts
- Generation button
- Download links
- Send confirmation input

---

### 11.2 User vs System Action Separation

| UI Element | User Actions | System Actions (Display Only) |
|------------|--------------|-------------------------------|
| Timeline | View | All events with SYSTEM actor |
| State Indicator | View | State transitions, escalations |
| Events Panel | View | Deadline breaches, reinsertion detection |
| Response Form | Input response data | Violation creation, evaluation |
| Artifact Panel | Request generation, download | Auto-queued escalation letters |

---

## 12. Output Artifacts

### 12.1 Artifact Generation by State

| State | Available Artifacts | Generation Authority |
|-------|---------------------|----------------------|
| DETECTED | Initial Dispute Letter | User-requested |
| DISPUTED | Dispute Tracking Summary | User-requested |
| NON_COMPLIANT | Escalation Notice | System-queued OR user-requested |
| PROCEDURAL_ENFORCEMENT | Procedural Cure Letter, MOV Demand | User-requested |
| SUBSTANTIVE_ENFORCEMENT | Failure-to-Investigate Letter, Formal Demand | User-requested |
| REGULATORY_ESCALATION | CFPB Complaint Packet, AG Referral Letter | User-requested |
| LITIGATION_READY | Attorney Evidence Bundle | User-requested |

### 12.2 Artifact Specifications

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

## 13. Design Constraints

### 13.1 Immutability Rules

| Element | Immutability |
|---------|--------------|
| Violation detection timestamp | Immutable |
| Dispute send date | Immutable |
| Response received date | Immutable |
| Deadline calculations | Immutable once set |
| State transitions | Append-only log |
| Reinsertion detection | Immutable |

### 13.2 Non-Reversible States

The following states cannot be reversed:
- `NON_COMPLIANT` → Cannot return to `EVALUATED`
- `REGULATORY_ESCALATION` → Cannot return to `SUBSTANTIVE_ENFORCEMENT`
- `LITIGATION_READY` → Terminal state

### 13.3 Silence as Action

```
IF entity_response IS NULL AND deadline_passed:
    entity_action = NO_RESPONSE
    # Silence is treated as affirmative failure to act
    # System creates violation automatically (no user confirmation)
```

### 13.4 Verification Compounds Liability

```
IF response_type == VERIFIED AND original_violation_valid:
    liability_multiplier = 2.0
    willful_indicator = TRUE
    # Verification of known inaccuracy suggests willfulness
    # Willful noncompliance: $100-$1,000 per violation (§ 616)
```

### 13.5 Timestamp Requirements

All events must record:
- UTC timestamp
- Actor: `USER` | `SYSTEM` | `ENTITY`
- Action taken
- Evidence hash (if applicable)
- State before/after

---

## 14. Database Schema

### 14.1 Core Tables

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
    current_state VARCHAR(50) NOT NULL,
    has_validation_request BOOLEAN DEFAULT FALSE,  -- For §1692g(b) guardrail
    collection_continued BOOLEAN DEFAULT FALSE,     -- For §1692g(b) guardrail
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Response tracking
CREATE TABLE dispute_responses (
    id UUID PRIMARY KEY,
    dispute_id UUID REFERENCES disputes(id),
    response_type ENUM('DELETED', 'VERIFIED', 'UPDATED', 'INVESTIGATING', 'NO_RESPONSE', 'REJECTED'),
    response_date DATE,
    reported_by ENUM('USER', 'SYSTEM') NOT NULL,
    evidence_path VARCHAR(500),
    new_violations JSON,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Reinsertion monitoring
CREATE TABLE reinsertion_watch (
    id UUID PRIMARY KEY,
    violation_id UUID REFERENCES violations(id),
    account_fingerprint VARCHAR(255) NOT NULL,
    furnisher_name VARCHAR(255),
    monitoring_start DATE NOT NULL,
    monitoring_end DATE NOT NULL,
    status ENUM('ACTIVE', 'EXPIRED', 'REINSERTION_DETECTED', 'NOTICE_RECEIVED'),
    reinsertion_date DATE,
    notice_date DATE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- State machine log (immutable)
CREATE TABLE escalation_log (
    id UUID PRIMARY KEY,
    dispute_id UUID REFERENCES disputes(id),
    from_state VARCHAR(50),
    to_state VARCHAR(50),
    trigger VARCHAR(100),
    actor ENUM('USER', 'SYSTEM', 'ENTITY') NOT NULL,
    statutes_activated JSON,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Paper trail (immutable)
CREATE TABLE paper_trail (
    id UUID PRIMARY KEY,
    dispute_id UUID REFERENCES disputes(id),
    event_type VARCHAR(50) NOT NULL,
    actor ENUM('USER', 'SYSTEM', 'ENTITY') NOT NULL,
    description TEXT,
    evidence_hash VARCHAR(64),
    artifact_type VARCHAR(50),
    artifact_path VARCHAR(500),
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 15. API Endpoints

```
# User-authorized endpoints
POST   /api/disputes                    # Create new dispute (user)
POST   /api/disputes/{id}/response      # Log entity response (user)
POST   /api/disputes/{id}/confirm-sent  # Confirm letter mailed (user)
POST   /api/disputes/{id}/artifacts     # Request artifact generation (user)
POST   /api/reports                     # Upload new report for validation (user)

# Read-only endpoints
GET    /api/disputes/{id}               # Get dispute details
GET    /api/disputes/{id}/timeline      # Get full paper trail (immutable)
GET    /api/disputes/{id}/state         # Get current state
GET    /api/disputes/{id}/artifacts     # List generated documents
GET    /api/scheduler/deadlines         # Get upcoming deadlines
GET    /api/scheduler/reinsertion       # Get active monitoring windows
GET    /api/disputes/{id}/system-events # Get system-triggered events

# System-only endpoints (internal scheduler)
POST   /api/internal/deadline-check     # Daily deadline breach scan
POST   /api/internal/reinsertion-scan   # Daily reinsertion check
POST   /api/internal/stall-detection    # Convert stale INVESTIGATING
```

---

## 16. Implementation Checklist

| Component | Status |
|-----------|--------|
| Response Input UI | PENDING |
| Response → Violation Mapping | PENDING |
| §1692g(b) Guardrail Logic | PENDING |
| Reinsertion Detection System | PENDING |
| Deadline Engine | PENDING |
| Validation Loop | PENDING |
| Cross-Entity Intelligence | PENDING |
| Escalation State Machine | PENDING |
| UI Observability Layer | PENDING |
| Artifact Generation | PENDING |
| Paper Trail Database | PENDING |
| Daily Scheduler | PENDING |
| CFPB Complaint Generator | PENDING |

---

## Appendix A: Statute Quick Reference

| Statute | Description | Applies To | Preconditions |
|---------|-------------|------------|---------------|
| FCRA § 607(b) | Maximum Possible Accuracy | CRA | None |
| FCRA § 611(a)(1)(A) | Duty to Investigate | CRA | None |
| FCRA § 611(a)(3) | Frivolous Dispute Procedures | CRA | None |
| FCRA § 611(a)(5)(B) | Reinsertion Notice | CRA | Prior deletion |
| FCRA § 611(a)(6)(B)(iii) | Method of Verification | CRA | Verification response |
| FCRA § 616 | Willful Noncompliance | CRA, Furnisher | None |
| FCRA § 617 | Negligent Noncompliance | CRA, Furnisher | None |
| FCRA § 623(a)(2) | Duty to Report Accurately | Furnisher | None |
| FCRA § 623(a)(6) | Reinsertion by Furnisher | Furnisher | Prior deletion |
| FCRA § 623(b)(1) | Duty to Investigate | Furnisher | None |
| FDCPA § 1692e | False Representations | Collector | None |
| FDCPA § 1692f | Unfair Practices | Collector | None |
| FDCPA § 1692g(b) | Validation of Debts | Collector | Validation request + continued collection |
| FDCPA § 1692k | Civil Liability | Collector | Underlying FDCPA violation |

---

## Appendix B: Damages Reference

| Violation Type | Statutory Damages | Actual Damages |
|----------------|-------------------|----------------|
| FCRA Negligent (§ 617) | N/A | Actual damages + attorney fees |
| FCRA Willful (§ 616) | $100 - $1,000 per violation | Actual damages + punitive + attorney fees |
| FDCPA (§ 1692k) | Up to $1,000 per case | Actual damages + attorney fees |
| FDCPA Class Action | Up to $500,000 or 1% of net worth | Per class member |

---

*Document Version: 2.0*
*System Status: SPECIFICATION COMPLETE*
*Refinements: Authority model, reinsertion automation, §1692g(b) guardrail, UI observability layer*
