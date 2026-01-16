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
Letters generated for Equifax/Experian violations were incorrectly addressed to TransUnion.

**Root Causes (Multiple):**

1. **Parser defaults to TransUnion:** The HTML parser sets `bureau=Bureau.TRANSUNION` as default because IdentityIQ reports are multi-bureau. This report-level bureau is meaningless.

2. **LetterPage auto-set effect overwrites bureau:** An effect in LetterPage.jsx was auto-setting bureau from `auditResult.bureau` (always "transunion") which overwrote the correct bureau set before navigation.

3. **Bureau should come from violations, not report:** Each violation has its own `bureau` field (equifax, experian, transunion). The letter should use the bureau from the selected violations.

**Fix:**
1. Modified `AuditPage.jsx` to get bureau from selected violations (not from auditResult)
2. Modified `ViolationList.jsx` strategy view callback to also set bureau from violations
3. **Removed** the auto-set bureau effect in `LetterPage.jsx` that was overwriting the correct value

**Key Insight:**
- Report-level `auditResult.bureau` is always "transunion" for multi-bureau reports
- Violation-level `violation.bureau` has the correct bureau per violation
- Letter generation must use violation-level bureau

**Files Changed:**
- `frontend/src/pages/AuditPage.jsx` - Get bureau from selected violations
- `frontend/src/pages/LetterPage.jsx` - Removed auto-set bureau effect
- `frontend/src/components/ViolationList.jsx` - Added bureau setting to strategy view callback
