# Legal Letter Generator - Correction Options & Patch History

## SSOT Corrections Applied

### FCRA Statute SSOT Patch (v1.0) ✅ ACCOMPLISHED
**Status:** COMPLETE
**Date:** 2024-11-30
**Files Modified:**
- `fcra_statutes.py` (NEW) - Authoritative SSOT for FCRA section → USC mappings
- `legal_assembler.py` - Fixed line 327 citation format
- `grouping_strategies.py` - Fixed fallback citation format
- `diversity.py` - Fixed `get_fcra_citation()` fallback

**Problem Fixed:**
Incorrect FCRA citations like `15 U.S.C. § 1681 (Section 611(a))` were being generated.

**Correct Format:**
- `611(a)` → `15 U.S.C. § 1681i(a)`
- `623(b)` → `15 U.S.C. § 1681s-2(b)`
- `605(a)` → `15 U.S.C. § 1681c(a)`
- `607(b)` → `15 U.S.C. § 1681e(b)`

---

### Civil Mask Patch Pack (v2.0) ✅ ACCOMPLISHED
**Status:** COMPLETE
**Date:** 2024-11-30
**Files Added:**
- `tone_mask.py` - Two-mask system for tone isolation
- `tones/civil_conversational.py` - Friendly civilian tone
- `tones/civil_professional.py` - Businesslike civilian tone
- `tones/civil_assertive.py` - Direct civilian tone
- `tones/civil_narrative.py` - Storytelling civilian tone

**Files Modified:**
- `tones/__init__.py` - Added civil tone registry
- `tones/strict_legal.py` - Added mask application
- `tones/professional.py` - Added mask application
- `tones/soft_legal.py` - Added mask application
- `tones/aggressive.py` - Added mask application
- `legal_assembler.py` - Added mask metadata

**Problem Fixed:**
Cross-contamination between legal and civil letter domains:
- Legal phrasing leaking into civil letters
- Civil phrasing appearing in legal letters
- Template detection through stem repetition
- Structural bleed between tone types

**Solution:**
Two-mask system with:
1. **LEGAL_MASK**: Requires legal basis block, statutory category, MOV block; Forbids soft/civil phrasing
2. **CIVIL_MASK**: Forbids case law, FCRA citations, USC sections, MOV, reinvestigation language

---

## Tone Categories

### Legal Tones (require FCRA citations, case law, MOV)
| Tone | Formality | Case Law | FCRA Density |
|------|-----------|----------|--------------|
| strict_legal | 10 | Required | High |
| professional | 7 | Optional | Moderate |
| soft_legal | 5 | None | Low |
| aggressive | 9 | Required | Maximum |

### Civil Tones (forbidden: legal terms, case law, MOV)
| Tone | Formality | Style | Use Case |
|------|-----------|-------|----------|
| conversational | 3 | Friendly | First disputes |
| civil_professional | 5 | Businesslike | Formal but accessible |
| assertive | 6 | Direct | Demanding attention |
| narrative | 4 | Storytelling | Complex situations |

---

## Mask Rules

### LEGAL_MASK Enforcements
**Required Blocks:**
- Legal basis section with FCRA citations
- Statutory category for grouped violations
- MOV block (if `include_case_law=True`)

**Forbidden Phrases:**
- "thank you for your time"
- "I would appreciate"
- "if you could please"
- "I hope"
- "sorry for any confusion"
- "I understand you're busy"

**Filters Applied:**
- Conversational language markers
- Softening expressions
- Apologies and gratitude
- Uncertain tone indicators

### CIVIL_MASK Enforcements
**Forbidden Terms:**
- Case law citations (e.g., "Cushman v. Trans Union")
- USC sections (e.g., "15 U.S.C. §")
- FCRA statutory references
- "pursuant to"
- "under the provisions of"
- "reinvestigation"
- "statutory category"
- "method of verification"
- "MOV"
- "willful noncompliance"
- "reasonable reinvestigation"

**Required Elements:**
- Plain language explanations
- Personal narrative voice
- Clear action requests
- Accessible formatting

---

## SWEEP C Compliance

The mask system ensures SWEEP C passes by:
1. **Stem Repetition Prevention**: Unique phrase pools per tone domain
2. **Tone Overlap Prevention**: Cross-domain phrase filtering
3. **Structural Bleed Prevention**: Domain-specific section templates
4. **Template Detection Avoidance**: Randomized phrase selection with seed

---

## Usage

```python
from .tone_mask import ToneMask, LetterDomain

# For legal letters
mask = ToneMask(LetterDomain.LEGAL, tone="strict_legal")
filtered_content = mask.apply(raw_content)
metadata = mask.get_metadata()

# For civil letters
mask = ToneMask(LetterDomain.CIVIL, tone="conversational")
filtered_content = mask.apply(raw_content)
```
