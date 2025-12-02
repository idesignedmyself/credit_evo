# Credit Engine 2.0 Backend

## Development Rules

**IMPORTANT: Never commit or push code without explicit user permission.**

## Recent Bug Fixes

### FCRA 605(a) 7-Year Obsolete Account Bug (Partial Fix)
- **Issue**: Accounts >7 years old were being classified as `stale_reporting` instead of `obsolete_account` in civil letters, causing letters to demand "verification" instead of "deletion"
- **Root Cause**: Violations were cached in the database at upload time. The audit rules were fixed but civil letters read from the cached violations_data.
- **Fix**: Added `reclassify_obsolete_violations()` function in `app/routers/letters.py` that re-classifies violations at letter generation time based on `days_since_update` in evidence field.
- **FCRA 605(a)**: Mandates DELETION for accounts >7 years (2555 days)
- **Status**: Partially fixed - violations are now correctly reclassified at letter generation time. Full fix would require re-running audit on cached reports.
