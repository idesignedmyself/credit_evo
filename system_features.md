# Credit Engine 2.0 - System Features

## Violation Filtering Engine

**Added:** December 2024

### Overview
Multi-dimensional filtering system that allows users to slice violations by Bureau, Severity, and Violation Type with instant filtering and dynamic filter option extraction.

### Components

#### 1. `useCreditFilter` Hook
**Location:** `frontend/src/hooks/useCreditFilter.js`

Core filtering logic that acts as a "SQL engine in JavaScript":

```javascript
// Filter state structure
{
  bureaus: [],     // e.g. ['TransUnion', 'Equifax']
  severities: [],  // e.g. ['HIGH', 'MEDIUM']
  categories: [],  // e.g. ['missing_dofd', 'obsolete_account']
}
```

**Key Features:**
- Dynamic filter option extraction from violation data
- AND logic between filter types (Bureau AND Severity AND Type)
- Memoized filtering for performance
- Returns `filteredData`, `filterOptions`, `toggleFilter`, `clearFilters`, `hasActiveFilters`

**API Property Mapping:**
- Bureau: `violation.bureau`
- Severity: `violation.severity`
- Violation Type: `violation.violation_type` (note: uses underscore, not `type`)

#### 2. FilterToolbar Component
**Location:** `frontend/src/components/FilterToolbar.jsx`

Clean Fintech styled UI with:
- Collapsible filter panel (click header to expand/collapse)
- Chip-based filters with visual selection state
- Categories sorted alphabetically
- Show More/Less toggle for Violation Types (8 visible by default)
- Count indicators on each filter group label
- "Clear All" button when filters are active

**Styling:**
- Unselected chips: Gray border (`#E2E8F0`), transparent background
- Selected chips: Solid blue (`#2563EB`), white text
- Hover states with smooth transitions

#### 3. ViolationList Integration
**Location:** `frontend/src/components/ViolationList.jsx`

Integration points:
- Uses `useCreditFilter(violations)` hook
- Passes `filteredData` to all grouping functions
- Displays "X of Y Violations Found" when filters active
- Shows FilterToolbar above violation list

### Bug Fix: Missing Violation Type Filter Group

**Issue:** The "Violation Type" filter group wasn't appearing in the UI.

**Root Cause:** Property name mismatch between API response and filter hook.
- API returns: `violation_type` (with underscore)
- Hook was looking for: `type` (no underscore)

**Fix Applied:**
```javascript
// useCreditFilter.js - Line 32
// BEFORE:
filters.categories.includes(violation.type)
// AFTER:
filters.categories.includes(violation.violation_type)

// useCreditFilter.js - Line 48
// BEFORE:
allViolations.map(v => v.type)
// AFTER:
allViolations.map(v => v.violation_type)
```

### Usage Example

```jsx
import { useCreditFilter } from '../hooks/useCreditFilter';
import FilterToolbar from './FilterToolbar';

const MyComponent = ({ violations }) => {
  const {
    filteredData,
    filters,
    filterOptions,
    toggleFilter,
    clearFilters,
    hasActiveFilters,
    totalCount,
    filteredCount
  } = useCreditFilter(violations);

  return (
    <>
      <FilterToolbar
        filters={filters}
        filterOptions={filterOptions}
        toggleFilter={toggleFilter}
        clearFilters={clearFilters}
        hasActiveFilters={hasActiveFilters}
        filteredCount={filteredCount}
        totalCount={totalCount}
      />
      {/* Render filteredData */}
    </>
  );
};
```

### Violation Types Supported

The system dynamically extracts violation types from data. Common types include:
- `missing_dofd` - Missing Date of First Delinquency
- `missing_date_opened` - Missing Account Open Date
- `obsolete_account` - Account Past 7-Year Limit
- `balance_mismatch` - Balance Differs Across Bureaus
- `status_mismatch` - Status Differs Across Bureaus
- `dofd_mismatch` - DOFD Differs Across Bureaus
- And many more (see `formatViolation.js` for full mapping)

---

## Premium Fintech UI Theme

**Added:** December 2024

### Overview
"Bloomberg Terminal" / "High-End Fintech" aesthetic with slate color palette, professional shadows, and clean typography.

### Theme Configuration
**Location:** `frontend/src/theme.js`

**Color Palette:**
- Primary: `#0F172A` (Dark Slate Blue - institutional, not bright)
- Secondary: `#3B82F6` (Bright Blue - for accents/buttons)
- Background: `#F8FAFC` (Very light slate gray)
- Text Primary: `#1E293B` (Slate 900)
- Text Secondary: `#64748B` (Slate 500)

**Bureau Colors:**
- TransUnion: `#00AEEF`
- Experian: `#ED1C24`
- Equifax: `#00B140`

**Severity Badge Colors:**
- HIGH: Red (`#FEE2E2` bg, `#991B1B` text)
- MEDIUM: Amber (`#FEF3C7` bg, `#92400E` text)
- LOW: Green (`#D1FAE5` bg, `#065F46` text)

### Typography
- Font Family: Inter, Roboto, Helvetica, Arial
- Tight letter-spacing on headers for financial look
- No ALL CAPS buttons (`textTransform: 'none'`)

---

## Marketing Landing Page

**Added:** December 2024

### Overview
Full-featured marketing landing page with integrated login form, replacing the standalone login page. Features a gradient background, transparent navbar, and multiple marketing sections.

### Location
`frontend/src/pages/LandingPage.jsx`

### Sections

#### 1. Navbar
- Transparent background (blends with gradient)
- "Credit Copilot" branding with document icon
- Clickable logo scrolls to top with smooth animation
- Login/Register navigation links

#### 2. Hero Section
- Split layout: Marketing content (left) + Login form (right)
- Gradient background: `linear-gradient(135deg, #0F172A 0%, #1E3A5F 50%, #1E40AF 100%)`
- Trust indicators: 98% Success Rate, 150+ Violation Types, 24/7 Automated Monitoring
- Embedded login form matching LoginPage proportions (500px maxWidth)

#### 3. Features Section
- 6 feature cards with icons
- Credit Monitoring, Violation Detection, Letter Generation, etc.
- Light background for contrast

#### 4. Pricing Section
- 3-tier pricing (Basic, Pro, Enterprise)
- Pro tier highlighted as recommended
- Slate gradient background

#### 5. About Section
- Company information
- "Get Started" CTA button

#### 6. Footer
- Copyright notice
- Links to Privacy Policy, Terms of Service, Contact

### Route Configuration
**Location:** `frontend/src/App.jsx`

```jsx
// Landing page at root for non-authenticated users
<Route path="/" element={isAuthenticated ? <Navigate to="/dashboard" replace /> : <LandingPage />} />

// /login redirects to landing page
<Route path="/login" element={isAuthenticated ? <Navigate to="/dashboard" replace /> : <Navigate to="/" replace />} />

// Protected routes redirect to / instead of /login
if (!isAuthenticated) {
  return <Navigate to="/" state={{ from: location }} replace />;
}
```

### Styling Details
- **Background Gradient:** Deep navy to blue (`#0F172A` → `#1E3A5F` → `#1E40AF`)
- **Accent Color:** Light blue (`#60A5FA`) for highlighted text
- **Form Container:** White background, 500px maxWidth, borderRadius 4
- **Button Style:** Blue (`#2563EB`), no text transform, 600 font weight

---

## Legal Letter Generator

### PDF Format Assembler
**Location:** `backend/app/services/legal_letter_generator/pdf_format_assembler.py`

Features:
- Roman numeral grouping for violations
- Full description display (no truncation)
- FCRA and Metro 2 citations
- Consumer/bureau address formatting

### Letter Tone Engines
- Legal tone with factual evidence
- Civil tone for standard disputes
- Auto-routing based on violation severity

---

## API Endpoints

### Reports Router
**Location:** `backend/app/routers/reports.py`

Key Response Models:
```python
class ViolationResponse(BaseModel):
    violation_id: str
    violation_type: str  # Used for filtering
    severity: str        # HIGH, MEDIUM, LOW
    bureau: str          # transunion, experian, equifax
    creditor_name: str
    account_number_masked: str
    description: str
    expected_value: Optional[str]
    actual_value: Optional[str]
    fcra_section: Optional[str]
    metro2_field: Optional[str]
```

---

## Collapsible Violation Groups

**Added:** December 2024

### Overview
Violation group headers (by Type, Account, Bureau) are now clickable accordions that expand/collapse for easier navigation.

### Location
`frontend/src/components/VirtualizedViolationList.jsx`

### Features
- **Clickable Headers:** Click any group header to expand/collapse that section
- **Expand/Collapse Icons:** Visual indicators (chevron up/down) on the right side
- **Collapsed by Default:** All groups start collapsed to reduce scrolling
- **Smooth Animation:** Uses MUI `Collapse` component for smooth transitions
- **Hover Effect:** Headers highlight on hover to show they're interactive

### Affected Tabs
- Group by Type
- Group by Account
- Group by Bureau

### Usage
Click any header like "GM FINANCIAL (6)" or "Missing Scheduled Payment (3)" to toggle visibility of violations in that group.

---

## Account Filter

**Added:** December 2024

### Overview
Added Account filter dropdown to the compact filter bar, allowing users to filter violations by creditor/account name.

### Location
- `frontend/src/components/CompactFilterBar.jsx`
- `frontend/src/hooks/useCreditFilter.js`
- `frontend/src/state/filterStore.js`

### Filter Bar Layout
```
Bureau | Severity | Type | Account
```

### Features
- **Account Dropdown:** Filter violations by creditor name (e.g., "GM FINANCIAL", "BMW FIN SVC")
- **Alphabetically Sorted:** Account options are sorted A-Z for easy navigation
- **Multi-Select:** Select multiple accounts to filter
- **Visual Feedback:** Selected count badge appears when filters are active
- **Removed Filter Icon:** Unnecessary filter list icon removed from left side

### Filter State Structure
```javascript
{
  bureaus: [],     // e.g. ['TransUnion', 'Equifax']
  severities: [],  // e.g. ['HIGH', 'MEDIUM']
  categories: [],  // e.g. ['missing_dofd', 'obsolete_account']
  accounts: [],    // e.g. ['GM FINANCIAL', 'BMW FIN SVC']
}
```

---

## Sidebar Styling Improvements

**Added:** December 2024

### Overview
Fixed visual inconsistencies between the sidebar and main content area for a cohesive look.

### Location
`frontend/src/layouts/DashboardLayout.jsx`

### Fixes Applied

#### 1. Background Color Consistency
- **Issue:** Sidebar used hardcoded `#f1f5f9` while main content used `background.default` (`#F8FAFC`)
- **Fix:** Changed sidebar to use `background.default` from theme
- **Result:** Sidebar and main content now have matching backgrounds

#### 2. Border Matching Score Cards
- **Issue:** Sidebar floating card had no border, while score cards had `border: 1px solid #E2E8F0`
- **Fix:** Added matching border to sidebar card
- **Result:** Sidebar now has same visual weight as score cards

### Styling Applied
```javascript
// Sidebar floating card
{
  bgcolor: 'background.paper',
  borderRadius: '12px',
  boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
  border: '1px solid #E2E8F0',  // Added for consistency
}
```

---

## Bureau Ghost Guard (B6)

**Added:** December 2024

### Overview
Prevents false positive violations from cross-bureau data bleed. When an account is reported by only some bureaus (e.g., Equifax only), the validation engine now correctly skips violations for bureaus that never reported the tradeline (e.g., TransUnion, Experian).

### Problem Solved
**Before:** If NAVY FCU reported an account only on Equifax, but the UI showed empty columns for TransUnion/Experian, the audit engine would incorrectly fire "Missing Account Open Date" violations for TU/EX - even though those bureaus never reported the account.

**After:** Ghost tradelines (bureaus with no substantive data) are detected and skipped at validation time. Only bureaus that actually reported the tradeline are audited.

### Implementation

#### 1. Ghost Detection Function
**Location:** `backend/app/services/audit/engine.py`

```python
def is_bureau_ghost(bureau_data: BureauAccountData) -> bool:
    """
    Returns True if the bureau column represents a non-existent (ghost) tradeline.
    A bureau cannot violate FCRA/Metro 2 rules on data it never reported.
    """
    # Checks for ANY substantive data:
    # - Financial: balance, high_credit, credit_limit, past_due_amount
    # - Dates: date_opened, date_closed, date_reported, date_last_activity, dofd
    # - Status: payment_status, account_status_raw
    # - Payment History: At least one non-empty status entry

    # Ghost = NO substantive data from this bureau
    return not has_any_data
```

#### 2. Ghost Guard Checkpoints
The ghost guard is applied in multiple locations:

1. **`_audit_account_bureau()`** - Skips all single-bureau rules for ghost tradelines
2. **`_convert_bureau_data_to_accounts()`** - Skips cross-bureau comparison for ghost data
3. **Double Jeopardy check** - Skips ghost tradelines in duplicate reporting detection
4. **Child Identity Theft check** - Skips ghost tradelines in identity validation
5. **Medical Debt Compliance** - Skips ghost tradelines in HIPAA/FCRA compliance checks

### Key Design Decisions
- **Validation-layer only**: Parsing and UI rendering unchanged (empty columns still display)
- **Preserves cross-bureau discrepancy detection**: Only applied to single-bureau rules
- **Payment history check**: Empty status strings (`''`) don't count as real data

---

## Dynamic Filter Dropdown

**Added:** December 2024

### Overview
The violation type filter dropdown is dynamically populated based on violations that exist in the current audit results. If no accounts have a particular violation type, that type won't appear in the filter dropdown.

### Benefits
- **No dead options**: Users only see violation types that actually exist in their report
- **Cleaner UX**: No confusion from selecting a filter that returns zero results
- **Automatic updates**: As violations are resolved or new reports uploaded, dropdown updates accordingly

### Implementation

**Location:** `frontend/src/hooks/useCreditFilter.js`

```javascript
// Extract unique values from data for dynamic filter options
const filterOptions = useMemo(() => {
  const categories = [...new Set(allViolations.map(v => v.violation_type).filter(Boolean))];
  return { bureaus, severities, categories, accounts };
}, [allViolations]);
```

---

## Unified Violation Type Labels

**Added:** December 2024

### Overview
Violation type labels are now consistent between the dropdown filter and the "Group by Type" tab. All labels use Title Case formatting with proper human-readable names.

### Problem Solved
**Before:** Dropdown showed raw values like "Missing Dofd" while the tab showed "Missing Date Of First Delinquency"

**After:** Both use the same `getViolationLabel()` function from `formatViolation.js`

### Implementation

#### 1. Label Mapping
**Location:** `frontend/src/utils/formatViolation.js`

```javascript
const VIOLATION_LABELS = {
  missing_dofd: 'Missing Date Of First Delinquency',
  missing_date_opened: 'Missing Account Open Date',
  stale_reporting: 'Stale/Outdated Data',
  obsolete_account: 'Account Past 7-Year Limit',
  // ... 70+ violation types mapped
};

export const getViolationLabel = (violationType) => {
  return VIOLATION_LABELS[violationType] ||
    violationType.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
};
```

#### 2. Component Integration
Both filter components now use `getViolationLabel`:

- **CompactFilterBar.jsx** - Uses `formatTypeLabel()` which calls `getViolationLabel()` for category options
- **FilterToolbar.jsx** - Uses `getViolationLabel()` directly for chip labels

---

## UI Semantic Layer (Violations vs Advisories)

**Added:** December 2024

### Overview
Dynamic UI layer that distinguishes between hard violations (actionable) and soft advisories (informational) based on severity. This prevents LOW severity items from being presented with alarming "DISCREPANCY DETECTED" language.

### Problem Solved
**Before:** All items displayed with "DISCREPANCY DETECTED", "EXPECTED vs ACTUAL" language, creating unnecessary user alarm for informational review items.

**After:** LOW severity items use neutral advisory language; MEDIUM/HIGH use violation language.

### UI Modes

| Severity | UI Mode   | Header Text                  | Column Labels            |
|----------|-----------|------------------------------|--------------------------|
| LOW      | advisory  | ℹ️ ACCOUNT REVIEW SIGNAL     | REFERENCE / REPORTED     |
| MEDIUM   | violation | ⚠️ DISCREPANCY DETECTED      | EXPECTED / ACTUAL        |
| HIGH     | violation | ⛔ POTENTIAL LEGAL VIOLATION | EXPECTED / ACTUAL        |

### Implementation

#### 1. UI Configuration Function
**Location:** `frontend/src/utils/formatViolation.js`

```javascript
export const getViolationUI = (violationType, severity) => {
  const isAdvisory = severity?.toUpperCase() === 'LOW';

  if (isAdvisory) {
    return {
      mode: 'advisory',
      boxTitle: 'Review Details',
      expectedLabel: 'Reference',
      actualLabel: 'Reported',
      // Neutral gray colors, no dispute CTA
    };
  }
  // Returns violation mode with actionable language
};
```

#### 2. Type-Specific Overrides
Special violation types get custom titles:
- `student_loan_capitalized_interest` → "ℹ️ BALANCE REVIEW (CAPITALIZED INTEREST)"
- `collection_balance_inflation` → "⛔ POTENTIAL FDCPA VIOLATION"
- `obsolete_account` → "⛔ OBSOLETE ACCOUNT (7-YEAR LIMIT)"

#### 3. Component Integration
**Location:** `frontend/src/components/ViolationToggle.jsx`

The component reads `uiConfig = getViolationUI(violation.violation_type, violation.severity)` and renders:
- Dynamic box titles
- Dynamic column labels (Reference/Reported vs Expected/Actual)
- Dynamic colors (neutral gray vs green/red)
- "Reference Standards" vs "Cited Statutes" based on mode

### Design Principles
- ❌ Does NOT change backend detection logic
- ❌ Does NOT reclassify severity
- ❌ Does NOT infer legality
- ✅ ONLY controls presentation/rendering
- ✅ Fail-safe defaults to advisory mode for unknown types

---

## Recent Commits

| Commit | Description |
|--------|-------------|
| `TBD` | UI Semantic Layer - Violations vs Advisories |
| `TBD` | B6: Bureau Ghost Guard - prevent cross-bureau data bleed |
| `TBD` | Unify violation type labels between dropdown and tabs |
| `9079259` | Add Account filter dropdown and remove filter icon |
| `a8596d8` | Add collapsible accordion headers to violation groups |
| `830c649` | Fix sidebar background color and add border for visual consistency |
| `29f5334` | Add violation filtering engine with multi-dimensional filters |
| `e0aa2df` | Upgrade UI to premium fintech aesthetic |
| `d1a1ed1` | Remove description truncation in legal letter bullets |
| `f940f4d` | Fix legal letter bullet formatting to show field values |
| `4fae27d` | Add PDF format legal letter assembler with Roman numeral grouping |
