# CREDIT ENGINE 2.0 - READY FOR FRONTEND

**Date:** November 27, 2025
**Backend Status:** VERIFIED AND STABLE
**All Tests:** 37/37 PASSED

---

## API ENDPOINTS

### Base URL
```
http://localhost:8000
```

### Health Check
```
GET /health
```
Response: `{"status": "healthy"}`

### Upload Report
```
POST /reports/upload
Content-Type: multipart/form-data
Body: file=<credit_report.html>
```
Response:
```json
{
  "report_id": "uuid",
  "bureau": "transunion|experian|equifax",
  "accounts_found": 15,
  "violations_found": 8
}
```

### Get Audit Results
```
GET /reports/{report_id}/audit
```
Response: Full AuditResult with violations list

### Generate Letter
```
POST /letters/generate
Content-Type: application/json
Body: {
  "report_id": "uuid",
  "selected_violations": ["violation_id_1", "violation_id_2"],  // optional
  "tone": "formal|assertive|conversational|narrative",
  "grouping_strategy": "by_violation_type|by_account|by_bureau"
}
```
Response:
```json
{
  "letter_id": "uuid",
  "content": "Full letter text...",
  "word_count": 450,
  "violations_cited": ["missing_dofd", "obsolete_account"],
  "accounts_disputed": ["acc_001", "acc_002"]
}
```

### Get Available Tones
```
GET /letters/tones
```
Response:
```json
{
  "tones": ["formal", "assertive", "conversational", "narrative"]
}
```

---

## SSOT FLOW

```
1. HTML Upload
      ↓
2. NormalizedReport (SSOT #1)
      ↓
3. AuditResult (SSOT #2) - violations computed here ONLY
      ↓
4. LetterPlan (SSOT #3) - strategy/grouping applied
      ↓
5. DisputeLetter (SSOT #4) - final rendered output
```

---

## VIOLATION TYPES

The system detects these violations:

### Data Quality
- `missing_dofd` - Missing Date of First Delinquency
- `missing_date_opened` - Missing Date Opened
- `missing_dla` - Missing Date Last Activity
- `missing_original_creditor` - Collection missing original creditor

### Balance Issues
- `negative_balance` - Impossible negative balance
- `past_due_exceeds_balance` - Past due > total balance
- `balance_exceeds_high_credit` - Balance > high credit
- `negative_credit_limit` - Impossible negative limit

### Temporal Issues
- `obsolete_account` - Past 7-year FCRA limit
- `future_date` - Future dates reported
- `stale_reporting` - No update in 90+ days
- `impossible_timeline` - Dates don't make logical sense

### Furnisher-Specific
- `closed_oc_reporting_balance` - Closed OC with balance
- `closed_oc_reporting_past_due` - Closed OC with past due
- `chargeoff_missing_dofd` - Charge-off without DOFD

### Cross-Bureau (when 2+ reports uploaded)
- `dofd_mismatch` - Different DOFD across bureaus
- `date_opened_mismatch` - Date opened differs significantly
- `balance_mismatch` - Balance differs by >10%
- `status_mismatch` - Different account statuses
- `payment_history_mismatch` - Payment patterns differ
- `past_due_mismatch` - Past due amounts differ
- `closed_vs_open_conflict` - Open on one, closed on another
- `creditor_name_mismatch` - Significantly different names
- `account_number_mismatch` - Account numbers differ

---

## TONE OPTIONS

| Tone | Description |
|------|-------------|
| `formal` | Professional, legal-focused language citing FCRA sections |
| `assertive` | Direct, demanding tone with emphasis on compliance |
| `conversational` | Friendly, approachable tone |
| `narrative` | Storytelling style, explaining the situation |

---

## GROUPING STRATEGIES

| Strategy | Description |
|----------|-------------|
| `by_violation_type` | Groups violations by type (default) |
| `by_account` | Groups all violations for each account together |
| `by_bureau` | Groups violations by reporting bureau |

---

## DETERMINISM GUARANTEE

- Same `report_id` + same `selected_violations` + same `tone` = identical letter
- Variation seed derived from SHA256(report_id)
- Use different seeds (via different report_ids) for letter variation

---

## FRONTEND WORKFLOW

### Typical User Flow

1. **Upload** - User uploads credit report HTML
2. **Review** - Display violations found (grouped by type or account)
3. **Select** - User selects which violations to dispute
4. **Customize** - User picks tone and grouping strategy
5. **Generate** - API generates letter
6. **Download** - User downloads letter as PDF/DOCX

### Key UI Elements

- Violation severity badges (HIGH/MEDIUM/LOW)
- Account cards with violation counts
- Tone preview samples
- Letter preview before download
- Cross-bureau comparison view (when multiple reports)

---

## ERROR HANDLING

| Error Code | Meaning |
|------------|---------|
| 400 | Invalid request (bad file format, missing required fields) |
| 404 | Report not found (invalid report_id) |
| 422 | Validation error (invalid tone, invalid violation IDs) |
| 500 | Server error (check logs) |

---

## TESTING THE BACKEND

```bash
# Health check
curl http://localhost:8000/health

# Get tones
curl http://localhost:8000/letters/tones

# Upload a report (example)
curl -X POST http://localhost:8000/reports/upload \
  -F "file=@sample_report.html"

# Generate letter
curl -X POST http://localhost:8000/letters/generate \
  -H "Content-Type: application/json" \
  -d '{"report_id": "YOUR_REPORT_ID", "tone": "formal"}'
```

---

## NEXT STEPS FOR FRONTEND

1. Set up React/Next.js project
2. Implement file upload component
3. Build violation review interface
4. Create letter customization panel
5. Add letter preview and download
6. Implement cross-bureau comparison (optional)

**Backend server runs on port 8000. CORS is enabled.**
