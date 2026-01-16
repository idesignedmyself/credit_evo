# Obstacle Fixes

Log of issues encountered and their solutions.

---

## 2026-01-16: Foreign Key Constraint Blocking Report Deletion

**Error:**
```
psycopg2.errors.ForeignKeyViolation: update or delete on table "reports" violates foreign key constraint "execution_suppression_events_report_id_fkey" on table "execution_suppression_events"
```

**Root Cause:**
Three tables had `report_id` foreign keys without `ON DELETE` behavior:
- `execution_suppression_events.report_id`
- `execution_events.report_id`
- `execution_outcomes.new_report_id`

When trying to delete a report, PostgreSQL blocked it because these tables still referenced the report.

**Fix:**
1. Updated `db_models.py` to add `ondelete="SET NULL"` to the foreign key definitions
2. Ran SQL to alter the existing constraints:
```sql
ALTER TABLE execution_suppression_events DROP CONSTRAINT execution_suppression_events_report_id_fkey;
ALTER TABLE execution_suppression_events ADD CONSTRAINT execution_suppression_events_report_id_fkey
    FOREIGN KEY (report_id) REFERENCES reports(id) ON DELETE SET NULL;
-- (same for execution_events and execution_outcomes)
```

**Files Changed:**
- `backend/app/models/db_models.py` - Added `ondelete="SET NULL"` to 3 foreign keys

---

## 2026-01-16: Bureau Routing Bug - Letters Addressed to Wrong Bureau

**Error:**
Letters generated for Equifax violations were incorrectly addressed to TransUnion.

**Root Cause:**
1. `AuditResultResponse` model was missing `bureau` field - frontend couldn't read it
2. UI store defaulted `selectedBureau` to `'transunion'`
3. Letter generation used the default instead of the actual report bureau

**Fix:**
1. Added `bureau: str` to `AuditResultResponse` Pydantic model
2. Added `bureau=audit.bureau` to the API response
3. Modified `AuditPage.jsx` to call `setBureau()` before navigating to LetterPage
4. Modified `violationStore.js` cache to refetch if `auditResult?.bureau` is missing

**Files Changed:**
- `backend/app/routers/reports.py` - Added bureau to response model and endpoint
- `frontend/src/pages/AuditPage.jsx` - Set bureau before navigation
- `frontend/src/state/violationStore.js` - Cache invalidation for missing bureau
