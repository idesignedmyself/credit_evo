# K1 Collection Agency Detection System

## Overview

The K1 Segment (Original Creditor Name) is a Metro 2 field that **only applies to third-party collectors and debt buyers**. Original Creditors (OCs) reporting their own accounts do NOT need K1 - they ARE the original creditor.

This document explains how the system distinguishes between:
- **Original Creditors (OCs):** Banks, lenders, utilities reporting their own accounts
- **Third-Party Collectors:** Agencies that bought or were assigned debt from OCs

---

## How Detection Works

### Location
`backend/app/services/audit/rules.py` → `FurnisherRules.check_collector_missing_original_creditor()`

### Logic
The system checks if the **creditor name** contains collection agency keywords:

```python
collection_agency_keywords = [
    "collection", "coll svcs", "credit collection", "recovery",
    "midland", "lvnv", "cavalry", "encore", "portfolio recovery",
    "convergent", "ic system", "transworld", "debt buyer",
    "credit management", "financial recovery", "asset acceptance",
    "jefferson capital", "unifin", "enhanced recovery"
]

is_collection_agency = any(kw in creditor_name.lower() for kw in collection_agency_keywords)
```

### Decision Flow
```
IF creditor name contains collection keywords:
    → TRUE collection agency
    → K1 IS required
    → Fire violation if K1 missing

ELSE:
    → Likely an Original Creditor
    → K1 NOT required
    → Suppress K1 violation
```

---

## Known Collection Agencies & Debt Buyers

### Major Debt Buyers (MUST be in list)
| Company | Keyword | Notes |
|---------|---------|-------|
| Midland Credit Management | `midland` | Encore Capital subsidiary |
| LVNV Funding | `lvnv` | Resurgent Capital subsidiary |
| Cavalry Portfolio Services | `cavalry` | |
| Encore Capital Group | `encore` | Parent of Midland |
| Portfolio Recovery Associates | `portfolio recovery` | PRA Group |
| Jefferson Capital Systems | `jefferson capital` | |
| CACH LLC | `cach` | *Consider adding* |
| Velocity Investments | `velocity` | *Consider adding* |

### Major Collection Agencies
| Company | Keyword | Notes |
|---------|---------|-------|
| Convergent Outsourcing | `convergent` | |
| IC System | `ic system` | |
| Transworld Systems | `transworld` | |
| Enhanced Recovery Company | `enhanced recovery` | |
| Asset Acceptance | `asset acceptance` | |
| Unifin | `unifin` | |
| National Credit Systems | `credit` | Caught by generic keyword |
| Allied Collection Service | `collection` | Caught by generic keyword |

### Generic Keywords (Catch Most Collectors)
| Keyword | What It Catches |
|---------|-----------------|
| `collection` | "ABC Collection Agency", "Credit Collection Services" |
| `recovery` | "Financial Recovery", "Debt Recovery Inc" |
| `debt` | "Debt Solutions", "Debt Management" |
| `credit management` | Various credit management companies |

---

## Known Original Creditors (Should NOT trigger K1)

These are examples of OCs that should NEVER have K1 violations:

### Banks & Credit Card Issuers
- Capital One
- Chase / JP Morgan
- Bank of America
- Citibank
- Wells Fargo
- Discover
- American Express
- Synchrony Bank
- Barclays

### Telecommunications
- Verizon
- AT&T
- T-Mobile
- Sprint
- Comcast / Xfinity

### Utilities
- Local electric companies
- Gas companies
- Water utilities

### Auto Lenders
- Toyota Financial
- Honda Financial
- Ford Credit
- Ally Financial
- Capital One Auto

### Student Loans
- Navient
- Nelnet
- Great Lakes
- FedLoan (MOHELA)

**Note:** These do NOT need to be added to any list. The system works by detecting collectors, not OCs. If a creditor name doesn't match collection keywords, it's treated as an OC.

---

## Adding New Collection Agencies

### When To Add
Add a new keyword when you discover a collection agency that:
1. Is missing K1 (should have it)
2. Has a name that doesn't contain existing keywords
3. Is confirmed to be a third-party collector (not an OC)

### How To Add

**Step 1:** Open `backend/app/services/audit/rules.py`

**Step 2:** Find the `collection_agency_keywords` list (around line 2258):

```python
collection_agency_keywords = [
    "collection", "coll svcs", "credit collection", "recovery",
    "midland", "lvnv", "cavalry", "encore", "portfolio recovery",
    "convergent", "ic system", "transworld", "debt buyer",
    "credit management", "financial recovery", "asset acceptance",
    "jefferson capital", "unifin", "enhanced recovery"
]
```

**Step 3:** Add the new keyword:

```python
collection_agency_keywords = [
    "collection", "coll svcs", "credit collection", "recovery",
    "midland", "lvnv", "cavalry", "encore", "portfolio recovery",
    "convergent", "ic system", "transworld", "debt buyer",
    "credit management", "financial recovery", "asset acceptance",
    "jefferson capital", "unifin", "enhanced recovery",
    "newcompany"  # Added: New Collection Agency Name
]
```

**Step 4:** Restart the backend

**Step 5:** Re-audit the report

### Keyword Best Practices

| Do | Don't |
|----|-------|
| Use lowercase | Use exact case matching |
| Use unique identifiers | Use common words like "financial", "services" |
| Use company-specific terms | Add entire company names |
| Add parent company names | Duplicate existing keywords |

**Example:**
- Good: `"midland"` (unique identifier)
- Bad: `"midland credit management inc"` (too specific, wastes space)
- Bad: `"services"` (too generic, would match OCs)

---

## Troubleshooting

### False Positive (OC getting K1 violation)
**Symptom:** Original Creditor like "VERIZON" shows K1 violation
**Cause:** Creditor name somehow matches a collection keyword
**Fix:** Check if the creditor name contains an unintended match. If so, the classification logic may need refinement.

### False Negative (Collector NOT getting K1 violation)
**Symptom:** Known collection agency missing K1 but no violation fires
**Cause:** Creditor name doesn't contain any keywords
**Fix:** Add a keyword that matches their name (see "How To Add" above)

### How To Verify Classification
Check the account's `furnisher_type` in the audit results:
- `collector` = System thinks it's a collection agency
- `oc_chargeoff` = System thinks it's an OC with chargeoff
- `oc_non_chargeoff` = System thinks it's a regular OC

---

## Future Improvements

### Option 1: Maintain External List
Move keywords to a configuration file (`collection_agencies.json`) for easier updates without code changes.

### Option 2: Account Type Detection
Parse Metro 2 Account Type field:
- Type 48 = Collection Agency/Attorney
- Type 0C = Debt Purchaser

If account type is 48 or 0C → K1 is definitely required.

### Option 3: Community Database
Maintain a shared database of known collectors that gets updated as new ones are discovered.

---

## Related Documentation

- `rule_logic_location.md` - B6 K1 Segment Scope Guard section
- `letter_fixes.md` - December 2024 K1 fix documentation
- `kb_stage/metro2.md` - Metro 2 format specification
