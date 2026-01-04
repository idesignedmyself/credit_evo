# Obstacle Fixes & Solutions

This document tracks errors encountered during development and their solutions for future reference.

---

## 1. Cross-Bureau Discrepancies Not Showing on Letters Page

**Error:** Discrepancies were included in letter text but not displayed in UI metadata.

**Root Cause:** `LetterDB` model lacked `discrepancies_cited` column.

**Fix:**
1. Add column to model (`app/models/db_models.py`):
   ```python
   discrepancies_cited = Column(JSON)  # List of cross-bureau discrepancies
   ```

2. Create migration (`migrations/add_discrepancies_cited.py`):
   ```sql
   ALTER TABLE letters
   ADD COLUMN discrepancies_cited JSONB DEFAULT '[]'::jsonb;
   ```

3. Update letter generation to persist discrepancies when creating letters.

4. Update API response to return `discrepancies_cited` field.

---

## 2. Cross-Bureau Discrepancies Not Showing on Disputes Page

**Error:**
```
AttributeError: 'DisputeDB' object has no attribute 'discrepancies_data'
```

**Root Cause:** `DisputeDB` model had no `discrepancies_data` column in database.

**Fix:**
1. Add column to model (`app/models/db_models.py`):
   ```python
   discrepancies_data = Column(JSON, nullable=True)  # Cross-bureau discrepancies from letter
   ```

2. Create migration (`migrations/add_discrepancies_to_disputes.py`):
   ```sql
   ALTER TABLE disputes
   ADD COLUMN discrepancies_data JSONB;
   ```

3. Copy discrepancies from letter to dispute when creating dispute:
   ```python
   if letter_id:
       from app.models.db_models import LetterDB
       letter = self.db.query(LetterDB).filter(LetterDB.id == letter_id).first()
       if letter and letter.discrepancies_cited:
           discrepancies_data = letter.discrepancies_cited
   ```

---

## 3. Import Path Error in dispute_service.py

**Error:**
```
ModuleNotFoundError: No module named 'app.services.models'
```

**Root Cause:** Relative import `from ..models.db_models import LetterDB` failed.

**Fix:** Use absolute import:
```python
from app.models.db_models import LetterDB
```

**Rule:** Always use absolute imports for cross-module references in services.

---

## 4. Discrepancies Not Appearing in "Log Response" Section

**Error:** Cross-bureau discrepancies showed in summary but not in response logging UI.

**Root Cause:** Only violations were mapped to `ViolationResponseRow` component.

**Fix:** Reuse existing component by adapting discrepancy shape:
```jsx
{dispute.discrepancies_data?.map((d, idx) => (
  <ViolationResponseRow
    key={`discrepancy-${d.discrepancy_id || idx}`}
    violation={{
      violation_id: d.discrepancy_id,        // Required for backend API
      violation_type: 'CROSS_BUREAU',
      creditor_name: d.creditor_name,
      account_number_masked: d.account_number_masked,
      description: `${d.field_name} mismatch across bureaus`,
      logged_response: d.logged_response,
      severity: 'MEDIUM',
    }}
    disputeId={dispute.id}
    // ... other props
  />
))}
```

**Principle:** Don't create duplicate components. Adapt data shape to fit existing components.

---

## 5. Letter Generation Failing for Cross-Bureau Discrepancies

**Error:**
```
Violation not found. Looking for: cf5e876e-1866-4fa7-b0bb-15a3a4709899.
Available: ['e6e25dfb-e2ac-4c80-916a-2e0a3af551179-v0', ...]
```

**Root Cause:** Letter generation endpoint only searched `original_violation_data`, not `discrepancies_data`.

**Fix:** Update `app/routers/disputes.py` to search both:
```python
all_violations = dispute.original_violation_data or []
all_discrepancies = dispute.discrepancies_data or []

if request.violation_id:
    violations = [v for v in all_violations if str(v.get('violation_id', '')) == str(request.violation_id)]

    # If not found in violations, check discrepancies
    if not violations:
        matching_discrepancies = [
            d for d in all_discrepancies
            if str(d.get('discrepancy_id', '')) == str(request.violation_id)
        ]
        if matching_discrepancies:
            d = matching_discrepancies[0]
            violations = [{
                'violation_id': d.get('discrepancy_id'),
                'violation_type': 'CROSS_BUREAU',
                'creditor_name': d.get('creditor_name'),
                'account_number_masked': d.get('account_number_masked'),
                'field_name': d.get('field_name'),
                'description': f"{d.get('field_name', 'Field')} mismatch across bureaus",
                'severity': 'MEDIUM',
                'logged_response': d.get('logged_response'),
                'is_discrepancy': True,
            }]
```

**Important:** Always include `logged_response` when adapting discrepancies for consistent response state reasoning.

---

## 6. VERIFIED Letter Missing Statutory Teeth

**Issue:** Letter only cited § 1681i(a)(1)(A), missing the "maximum possible accuracy" argument.

**Fix:** Add statutory double-tap in `response_letter_generator.py`:

1. **Subject line:**
   ```
   Verification Without Reasonable Investigation & Failure to Assure Accuracy
   ```

2. **Statutory Framework:** Add § 1681e(b):
   ```
   Additionally, pursuant to 15 U.S.C. § 1681e(b), a consumer reporting agency must follow
   reasonable procedures to assure maximum possible accuracy of the information reported.
   ```

3. **Add CROSS_BUREAU basis template:**
   ```python
   "cross_bureau": """A single tradeline cannot possess multiple values for the same field
   across consumer reporting agencies. At least one reported value is necessarily inaccurate.
   Verification of information that is contradicted across bureaus is not a verification of
   accuracy, but a confirmation of defective data."""
   ```

4. **Cure period framing:**
   ```
   within fifteen (15) days of receipt of this notice as a good-faith cure period
   ```

**Strategic value:** Forces bureau into a trap - they either admit they didn't investigate (§ 1681i) or admit they verified an impossibility (§ 1681e(b)).

---

## Common Patterns

### Database Column Missing
1. Add to SQLAlchemy model
2. Create migration script
3. Run migration
4. Update API responses to include new field

### Data Not Flowing Between Entities
1. Check creation pipeline (e.g., dispute creation from letter)
2. Ensure source data is copied to destination
3. Update API serialization to return the data

### Frontend Not Displaying Data
1. Check API response includes the data
2. Check component receives the data as prop
3. Adapt data shape if reusing existing components

### "Not Found" Errors
1. Check all data sources (violations AND discrepancies)
2. Search by multiple ID field names (violation_id, id, discrepancy_id)
3. Adapt shape when found in secondary source
