# Credit Engine 2.0 - Systems Checklist

This document tracks the status of all system components and configurations.

---

## Database Configuration

| Component | Status | Configuration |
|-----------|--------|---------------|
| Database Type | PostgreSQL | `postgresql://localhost:5432/credit_engine` |
| SQLite | REMOVED | Was stale 0-byte file - deleted |
| ORM | SQLAlchemy | Uses `get_db()` dependency injection |

**Note:** The app uses PostgreSQL exclusively. Any `credit_engine.db` SQLite files should be removed.

---

## Data Flow Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  HTML Report    │ --> │   HTML Parser   │ --> │ NormalizedReport│
│  (IdentityIQ)   │     │ (html_parser.py)│     │    (SSOT #1)    │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                         │
                                                         v
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  AuditResult    │ <-- │   Audit Engine  │ <-- │  User Profile   │
│    (SSOT #2)    │     │   (engine.py)   │     │  (PostgreSQL)   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

---

## Parsing Layer

| Component | Status | Description |
|-----------|--------|-------------|
| HTML Parser | ACTIVE | `app/services/parsing/html_parser.py` |
| Report Data Storage | PostgreSQL `report_data` JSON | Full parsed report including consumer info |
| Consumer Data | EXTRACTED | `full_name`, `date_of_birth`, `state`, `address`, `ssn_last4` |

---

## Identity Integrity Testing

**Last Tested:** 2024-12-07

| Check | Status | Notes |
|-------|--------|-------|
| Name + Middle Initial | PASS | Correctly extracts and matches middle initial from report |
| Date of Birth | PASS | Parsed from `report_data.consumer.date_of_birth` |
| State | PASS | Matches user profile state against report state |
| Suffix (Jr/Sr) | PASS | Detects mixed file indicators |
| SSN Last 4 | PASS | Only validates if both have 4 digits |
| Deceased Indicator | ACTIVE | CRITICAL - Detects living consumer marked as deceased (score = 0) |
| Child Identity Theft | ACTIVE | CRITICAL - Detects accounts opened when consumer was a minor (<18) |

**Test Results (Sample User):**
```
User Profile: Tiffany C Brown, DOB: 1975-10-05, State: NY
Report Data:  TIFFANYCBROWN-, DOB: 1975-10-05, State: NY
Result:       ALL CHECKS PASSED
```

---

## Audit Engine Components

| Component | Status | Location |
|-----------|--------|----------|
| SingleBureauRules | ACTIVE | `app/services/audit/rules.py` |
| CrossBureauRules | ACTIVE | `app/services/audit/cross_bureau_rules.py` |
| InquiryRules | ACTIVE | `app/services/audit/rules.py` |
| IdentityRules | ACTIVE | `app/services/audit/rules.py` |
| FurnisherRules | ACTIVE | `app/services/audit/rules.py` |
| TemporalRules | ACTIVE | `app/services/audit/rules.py` |
| PublicRecordRules | ACTIVE | `app/services/audit/rules.py` |
| MedicalDebtRules | ACTIVE | `app/services/audit/rules.py` (NCAP 2022/2023 Bureau Policy) |
| PostSettlementRules | ACTIVE | `app/services/audit/rules.py` (Zombie History Detection) |
| MissingTradelineRules | ACTIVE | `app/services/audit/cross_bureau_rules.py` (Cross-Bureau Gaps) |

---

## Frontend Profile System

| Component | Status | Notes |
|-----------|--------|-------|
| Profile Save | FIXED | Merged two forms into single form wrapper |
| Identity Fields | ACTIVE | first_name, middle_name, last_name, suffix, DOB, SSN last 4 |
| Address Fields | ACTIVE | street, city, state, zip, move_in_date |
| Previous Addresses | ACTIVE | JSON array in PostgreSQL |

---

## API Endpoints

| Endpoint | Method | Status | Auth Required |
|----------|--------|--------|---------------|
| `/auth/register` | POST | ACTIVE | No |
| `/auth/login` | POST | ACTIVE | No |
| `/auth/me` | GET | ACTIVE | Yes |
| `/auth/profile` | GET | ACTIVE | Yes |
| `/auth/profile` | PUT | ACTIVE | Yes |
| `/auth/password` | PUT | ACTIVE | Yes |
| `/reports/upload` | POST | ACTIVE | Yes |
| `/reports/{id}/audit` | GET | ACTIVE | Yes |
| `/letters/generate` | POST | ACTIVE | Yes |
| `/cfpb/letters/generate` | POST | ACTIVE | Yes |
| `/cfpb/complaints/submit` | POST | ACTIVE | Yes |
| `/cfpb/complaints/response` | POST | ACTIVE | Yes |
| `/cfpb/evaluate` | POST | ACTIVE | Yes |
| `/cfpb/cases` | GET | ACTIVE | Yes |
| `/cfpb/cases/{id}` | GET | ACTIVE | Yes |
| `/cfpb/cases/{id}/events` | GET | ACTIVE | Yes |

---

## CFPB Channel Adapter

| Component | Status | Location |
|-----------|--------|----------|
| CFPBService | ACTIVE | `app/services/cfpb/cfpb_service.py` |
| CFPBStateMachine | ACTIVE | `app/services/cfpb/cfpb_state_machine.py` |
| CFPBLetterGenerator | ACTIVE | `app/services/cfpb/cfpb_letter_generator.py` |
| CFPB Router | ACTIVE | `app/routers/cfpb.py` |
| Database Tables | ACTIVE | `cfpb_cases`, `cfpb_events` |

**State Flow:** NONE → INITIAL_SUBMITTED → RESPONSE_RECEIVED → ESCALATION_SUBMITTED → ESCALATION_RESPONSE_RECEIVED → FINAL_SUBMITTED → CLOSED

**Gating Rules:** Escalation requires CRA exhaustion (VERIFIED/NO_RESPONSE/REJECTED) AND unresolved_contradictions_count > 0

---

## Known Issues

- None at this time

---

## Recent Fixes

1. **Profile Form Fix** - Merged two separate `<form>` elements in ProfilePage.jsx into single form
2. **Database Cleanup** - Removed stale SQLite file, confirmed PostgreSQL is active database
3. **Identity Check Verification** - Confirmed DOB, name+middle initial, state all parse correctly from `report_data` JSON
4. **Deceased Indicator Detection** - CRITICAL: Detects living consumer erroneously marked as deceased (score=0)
5. **Child Identity Theft Detection** - CRITICAL: Detects accounts opened when consumer was a minor (<18 years old)
6. **Public Records Audit** - NEW: Detects NCAP violations (judgments/liens post-2017), satisfied judgments with balance, and obsolete bankruptcies
7. **Medical Debt Compliance** - NEW: Catches "zombie medical bills" that should have been deleted under NCAP 2022/2023 (paid medical, under $500)
8. **Post-Settlement Negative Reporting** - NEW: Detects "zombie history" where late markers are reported AFTER an account was closed/settled (artificially refreshes Date of Last Activity)
9. **Missing Tradelines Detection** - NEW: Detects accounts appearing on some bureaus but missing from others (explains score discrepancies between bureaus)
10. **CFPB Channel Adapter** - NEW: CFPB-specific escalation track mirroring CRA lifecycle. Same facts/contradictions/severity, different audience rendering. Includes state machine with escalation gating, 3 letter variants, and full ledger integration.

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://localhost:5432/credit_engine` |
| `JWT_SECRET_KEY` | JWT signing key | (required) |
| `VITE_API_URL` | Frontend API base URL | `http://localhost:8000` |

---

*Last Updated: 2026-01-01*
