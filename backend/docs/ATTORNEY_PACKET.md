# Attorney Packet Generator

**Status:** SHIPPED
**Tier:** Product Tier 5 — Revenue Leverage
**Endpoint:** `GET /disputes/{dispute_id}/attorney-packet`

---

## Overview

The Attorney Packet Generator creates printable litigation-ready documents for consumers to give to FCRA attorneys. When a dispute reaches Tier-3 (exhausted all internal remedies), the system packages all evidence, violations, examiner failures, and legal analysis into a single document.

**Key Principle:** The consumer prints this document and hands it to an attorney. No login required for the attorney. Everything they need is in the packet.

---

## API Usage

### Get Printable Document (Default)

```
GET /disputes/{dispute_id}/attorney-packet
```

Returns a formatted text document ready for printing.

### Get JSON Data

```
GET /disputes/{dispute_id}/attorney-packet?format=json
```

Returns structured JSON for programmatic access.

---

## Document Sections

The printed attorney packet contains the following sections:

| Section | Contents |
|---------|----------|
| **Header** | Case reference ID, generation date, status |
| **Parties Involved** | Consumer (redacted), CRA, Furnisher |
| **Violations Detected** | Each violation with rule code, severity, statute |
| **Dispute History** | Timeline from initial dispute to Tier-3 promotion |
| **Examiner Failure Analysis** | Which regulatory checks failed and why |
| **Basis for Legal Action** | Tier-3 classification + cure attempt summary |
| **Elements of FCRA Claim** | 4 elements with satisfaction status |
| **Willfulness Indicators** | Checkboxes showing willful conduct |
| **Damages Available** | Statutory range, punitive eligibility, attorney fees |
| **Statutes Violated** | List of all applicable statutes |
| **Attached Exhibits** | Reference to evidence documents |
| **Footer** | Packet ID, generation timestamp, integrity hash |

---

## Example Output

```
================================================================================
                         FCRA VIOLATION CASE PACKET
                    Prepared for Attorney Consultation
================================================================================

CASE REFERENCE: PKT-2026-0101-A7B3C
GENERATED:      January 01, 2026
STATUS:         ATTORNEY-READY (Tier-3 Exhausted)

================================================================================
                              PARTIES INVOLVED
================================================================================

CONSUMER:           [Name Redacted]

CREDIT BUREAU:      TransUnion LLC

FURNISHER:          Midland Credit Management LLC

================================================================================
                              VIOLATIONS DETECTED
================================================================================

VIOLATION #1: TEMPORAL IMPOSSIBILITY (Rule T1)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Date Opened (2019-03-15) occurs AFTER Date of First Delinquency
(2018-11-20). This is logically impossible - a consumer cannot become
delinquent on an account before it was opened.

    Severity:    CRITICAL
    Statute:     FCRA § 1681e(b)

================================================================================
                              DISPUTE HISTORY
================================================================================

DATE           ACTION
────────────────────────────────────────────────────────────────────────────────
Nov 05, 2025   Initial dispute created - 2 violations detected
Nov 06, 2025   Formal dispute letter sent to TransUnion
Dec 04, 2025   Response received: VERIFIED - No changes made
Dec 04, 2025   Examiner check: FAIL_PERFUNCTORY
Dec 05, 2025   Second dispute initiated
Dec 20, 2025   Response received: VERIFIED (again)
Dec 20, 2025   Tier-3 classification: REPEATED_VERIFICATION_FAILURE

================================================================================
                          EXAMINER FAILURE ANALYSIS
================================================================================

CHECK #1: Perfunctory Investigation
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    Result:    FAILED
    Finding:   Entity verified account despite receiving documentary
               evidence proving logical impossibility

================================================================================
                          BASIS FOR LEGAL ACTION
================================================================================

REPEATED VERIFICATION FAILURE:

    The credit reporting agency verified disputed information multiple times
    despite receiving documentary evidence proving the information is inaccurate.
    This pattern indicates willful noncompliance with FCRA investigation
    requirements.

CURE ATTEMPT EXHAUSTED:

    • Dispute rounds completed: 2
    • Examiner failures recorded: 2
    • Consumer remedies through dispute process: EXHAUSTED

================================================================================
                          ELEMENTS OF FCRA CLAIM
================================================================================

1. INACCURATE INFORMATION REPORTED                      ✓ SATISFIED
────────────────────────────────────────────────────────────────────────────────

2. CONSUMER DISPUTED THE INACCURACY                     ✓ SATISFIED
────────────────────────────────────────────────────────────────────────────────

3. FAILURE TO CONDUCT REASONABLE INVESTIGATION          ✓ SATISFIED
────────────────────────────────────────────────────────────────────────────────

4. CONTINUED REPORTING OF INACCURATE INFORMATION        ✓ SATISFIED
────────────────────────────────────────────────────────────────────────────────

================================================================================
                          WILLFULNESS INDICATORS
================================================================================

The following factors suggest WILLFUL rather than negligent noncompliance:

    ☒ Verified disputed information multiple times
    ☒ Multiple examiner check failures
    ☒ Critical violation: TEMPORAL_IMPOSSIBILITY
    ☒ Pattern consistent with automated verification without human review

================================================================================
                            DAMAGES AVAILABLE
================================================================================

STATUTORY DAMAGES (15 U.S.C. § 1681n(a)(1)(A))
    Range: $200 – $2,000 per willful violation

PUNITIVE DAMAGES (15 U.S.C. § 1681n(a)(2))
    Available where willfulness is established
    No statutory cap

ACTUAL DAMAGES
    • Credit denials or adverse terms
    • Increased interest rates paid
    • Emotional distress
    • Time spent disputing

ATTORNEY'S FEES (15 U.S.C. § 1681n(a)(3))
    Recoverable by prevailing plaintiff

================================================================================
                            ATTACHED EXHIBITS
================================================================================

    Exhibit A:  Credit report with violations highlighted
    Exhibit B:  Dispute letters with certified mail receipts
    Exhibit C:  Entity response letters
    Exhibit D:  Current credit report showing unchanged data
    Exhibit E:  Evidence integrity hashes (3 documents)

================================================================================

    This packet was generated by an automated FCRA enforcement system.
    All violations were detected using deterministic rules applied to
    Metro 2 credit data schema fields. No AI interpretation was used
    in violation detection.

    Case Packet ID: PKT-2026-0101-A7B3C
    Generated: 2026-01-01 14:32:00 UTC
    Integrity Hash: 07ec89e13fa48ecc...

================================================================================
```

---

## Tier-3 Classifications

The packet explains why the dispute reached Tier-3:

| Classification | Meaning |
|----------------|---------|
| `REPEATED_VERIFICATION_FAILURE` | CRA verified disputed data multiple times despite evidence |
| `FRIVOLOUS_DEFLECTION` | CRA improperly rejected dispute as frivolous |
| `CURE_WINDOW_EXPIRED` | CRA failed to respond within 30-day statutory window |

---

## Willfulness Analysis

The packet identifies willfulness indicators for punitive damages:

- **Verified logical impossibility** — Data that is mathematically self-contradicting
- **Ignored documentary evidence** — Consumer sent proof, CRA still verified
- **Repeated same response** — After examiner failure, CRA responded identically
- **Critical severity violations** — T1-T4 temporal/mathematical impossibilities

---

## Evidence Integrity

Each packet includes:

- **Packet ID** — Unique identifier for this case packet
- **Integrity Hash** — SHA-256 hash of packet contents
- **Document Hashes** — Hashes of all evidence documents in the execution ledger

This creates an immutable audit trail proving the packet contents match the original evidence.

---

## Requirements

- Dispute must be at **Tier-3** (locked/exhausted)
- Consumer must own the dispute
- At least one violation must exist

---

## Files

| File | Purpose |
|------|---------|
| `services/artifacts/attorney_packet_builder.py` | Core builder + render_document() |
| `routers/disputes.py` | API endpoint |

---

## Related Documentation

- [Tier 2 Supervisory Enforcement](./TIER2_SUPERVISORY_ENFORCEMENT.md)
- [Response Letter Generator](./RESPONSE_LETTER_GENERATOR.md)
- [System Checklist](../system_checklist.md)
