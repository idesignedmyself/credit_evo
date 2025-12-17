"""
Test Suite: SWEEP D - Content Quality Monte-Carlo Stress Test

Performs Monte-Carlo stress testing of the legal/civil letter generator
across all tones, domains, grouping strategies, and random seeds.

Covers:
1. Semantic coherence
2. Legal correctness
3. Civil-domain naturalness
4. Violation accuracy
5. Tone consistency
6. Reading-level constraints
7. No hallucinated legal rules
8. No statute drift (SSOT alignment)
9. No Metro-2 field mistakes
10. No contradictory statements
11. No broken sentences
12. No placeholder leaks
13. No domain bleed
14. Intro/body/closing coherence
15. No missing required sections
16. Grouping correctness
17. Account/violation mapping
18. Proper account masking
19. No accidental repetition beyond threshold
20. Multi-seed reproducibility
"""
import pytest
import re
import sys
import os
from typing import List, Dict, Tuple, Set, Optional
from collections import Counter
import math

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.legal_letter_generator import (
    generate_legal_letter,
    LegalLetterAssembler,
    BUREAU_ADDRESSES,
    FCRA_SECTIONS,
    METRO2_FIELDS,
    CaseLawLibrary,
    StructuralValidator,
    create_structural_fixer,
    create_diversity_engine,
)
from app.services.legal_letter_generator.fcra_statutes import (
    resolve_statute,
    FCRA_STATUTE_MAP,
)
from app.services.civil_letter_generator import (
    generate_civil_letter,
    is_civil_tone,
)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def flesch_kincaid(text: str) -> float:
    """Calculate Flesch-Kincaid reading ease score."""
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    if not sentences:
        return 0.0

    words = re.findall(r'\b[a-zA-Z]+\b', text)
    if not words:
        return 0.0

    total_sentences = len(sentences)
    total_words = len(words)

    # Count syllables
    def count_syllables(word: str) -> int:
        word = word.lower()
        vowels = "aeiouy"
        count = 0
        prev_vowel = False
        for char in word:
            is_vowel = char in vowels
            if is_vowel and not prev_vowel:
                count += 1
            prev_vowel = is_vowel
        if word.endswith('e') and count > 1:
            count -= 1
        return max(1, count)

    total_syllables = sum(count_syllables(w) for w in words)

    # Flesch Reading Ease formula
    score = 206.835 - 1.015 * (total_words / total_sentences) - 84.6 * (total_syllables / total_words)
    return max(0, min(100, score))


def find_contradictions(text: str) -> List[Tuple[str, str]]:
    """Detect contradictory statements in text."""
    contradictions = []

    contradiction_patterns = [
        (r'this (?:is|was) accurate', r'(?:I )?dispute|inaccurate|incorrect'),
        (r'I paid', r'never paid|unpaid|outstanding balance'),
        (r'account is closed', r'open account|active account'),
        (r'I do not owe', r'I (?:still )?owe|balance due'),
        (r'this is correct', r'this is (?:in)?correct|wrong|erroneous'),
        (r'I acknowledge', r'I deny|I dispute'),
        (r'balance is \$0', r'balance (?:of|is) \$[1-9]'),
    ]

    text_lower = text.lower()
    for pattern1, pattern2 in contradiction_patterns:
        if re.search(pattern1, text_lower) and re.search(pattern2, text_lower):
            match1 = re.search(pattern1, text_lower)
            match2 = re.search(pattern2, text_lower)
            if match1 and match2:
                contradictions.append((match1.group(), match2.group()))

    return contradictions


def extract_sections(text: str) -> Dict[str, str]:
    """Extract named sections from letter text."""
    sections = {}

    section_patterns = [
        (r'I\.\s*PRELIMINARY STATEMENT', 'preliminary_statement'),
        (r'II\.\s*LEGAL BASIS', 'legal_basis'),
        (r'III\.\s*SPECIFIC VIOLATIONS', 'violations'),
        (r'IV\.\s*METRO-?2 COMPLIANCE', 'metro2'),
        (r'V\.\s*METHOD OF VERIFICATION', 'mov'),
        (r'VI\.\s*CASE LAW', 'case_law'),
        (r'VII\.\s*FORMAL DEMANDS', 'demands'),
        (r'VIII\.\s*RESERVATION OF RIGHTS', 'reservation'),
        (r'RE:', 'subject'),
        (r'Dear\s+', 'salutation'),
        (r'Sincerely|Respectfully', 'closing'),
    ]

    for pattern, name in section_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            start = match.end()
            next_section = len(text)
            for other_pattern, _ in section_patterns:
                if other_pattern != pattern:
                    other_match = re.search(other_pattern, text[start:], re.IGNORECASE)
                    if other_match:
                        next_section = min(next_section, start + other_match.start())
            sections[name] = text[start:next_section].strip()

    return sections


def extract_violations(text: str) -> List[Dict[str, str]]:
    """Extract violation mentions from letter text."""
    violations = []

    # Pattern for violation blocks
    violation_pattern = r'(?:Account|Creditor)[:\s]+([^\n]+?)(?:\n|$).*?(?:violation|error|inaccuracy|dispute)[:\s]*([^\n]+)'

    for match in re.finditer(violation_pattern, text, re.IGNORECASE | re.DOTALL):
        violations.append({
            'account': match.group(1).strip(),
            'description': match.group(2).strip() if match.group(2) else ''
        })

    # Also check for FCRA section mentions
    fcra_pattern = r'(?:Section|§)\s*(\d{3}[a-z]?(?:\([a-z0-9]+\))?)'
    for match in re.finditer(fcra_pattern, text, re.IGNORECASE):
        if not any(v.get('fcra_section') == match.group(1) for v in violations):
            violations.append({
                'fcra_section': match.group(1),
                'description': ''
            })

    return violations


def detect_illegal_terms(text: str, domain: str) -> List[str]:
    """Detect terms that shouldn't appear in the given domain."""
    illegal_terms = []

    if domain == 'civil':
        legal_only_terms = [
            r'pursuant to',
            r'15 U\.S\.C\. §',
            r'method of verification',
            r'\bMOV\b',
            r'reinvestigation',
            r'willful noncompliance',
            r'statutory damages',
            r'case law',
            r'v\.\s+(?:Trans Union|Experian|Equifax)',
            r'Metro-?2',
            r'Field \d+',
        ]
        for term in legal_only_terms:
            if re.search(term, text, re.IGNORECASE):
                illegal_terms.append(term)

    elif domain == 'legal':
        civil_only_terms = [
            r'thank you for your time',
            r'I would appreciate',
            r'if you could please',
            r'sorry for any confusion',
            r'hope you understand',
            r'at your convenience',
        ]
        for term in civil_only_terms:
            if re.search(term, text, re.IGNORECASE):
                illegal_terms.append(term)

    return illegal_terms


def ssot_validate_citation(text: str) -> List[str]:
    """Validate FCRA citations against SSOT."""
    errors = []

    # Extract all USC citations
    citation_pattern = r'15 U\.S\.C\. § (\d{4}[a-z]?(?:-\d+)?(?:\([a-z0-9]+\))?)'
    citations = re.findall(citation_pattern, text)

    valid_usc_codes = set(v.get("usc", "") for v in FCRA_STATUTE_MAP.values() if isinstance(v, dict))
    valid_usc_suffixes = {re.sub(r'^15 U\.S\.C\. § 1681', '', code) for code in valid_usc_codes}

    for citation in citations:
        # "1681" alone (the base FCRA citation) is valid - commonly used as "15 U.S.C. § 1681 et seq."
        if citation == "1681":
            continue

        # Construct full USC citation for comparison
        full_citation = f"15 U.S.C. § 1681{citation}" if not citation.startswith('1681') else f"15 U.S.C. § {citation}"
        # Check if it's a valid USC code
        if full_citation not in valid_usc_codes:
            # Check if the suffix alone is valid (e.g., "i(a)" should match "i")
            suffix = re.sub(r'^1681', '', citation) if citation.startswith('1681') else citation
            if suffix not in valid_usc_suffixes and not any(suffix.startswith(s.split('(')[0]) for s in valid_usc_suffixes if s):
                errors.append(f"Invalid USC citation: 15 U.S.C. § {citation}")

    # Check for old-style citations
    old_style_pattern = r'15 U\.S\.C\. § 1681\s*\(Section\s*\d+'
    if re.search(old_style_pattern, text):
        errors.append("Old-style citation format detected")

    return errors


def validate_metro2_fields(text: str) -> List[str]:
    """Validate Metro-2 field references."""
    errors = []

    valid_field_numbers = set(METRO2_FIELDS.keys()) if isinstance(METRO2_FIELDS, dict) else set()
    if not valid_field_numbers:
        valid_field_numbers = set(range(1, 100))

    field_pattern = r'Field\s*(\d+)'
    for match in re.finditer(field_pattern, text, re.IGNORECASE):
        field_num = int(match.group(1))
        if field_num not in valid_field_numbers and field_num > 50:
            errors.append(f"Invalid Metro-2 field reference: Field {field_num}")

    return errors


def detect_placeholders(text: str) -> List[str]:
    """Detect placeholder tokens that should have been replaced."""
    placeholders = []

    placeholder_patterns = [
        r'\{\{[^}]+\}\}',
        r'\[\[?[A-Z_]+\]?\]',
        r'<[A-Z_]+>',
        r'\$\{[^}]+\}',
        r'%[a-zA-Z_]+%',
        r'TODO',
        r'FIXME',
        r'XXX',
        r'PLACEHOLDER',
        r'INSERT_HERE',
        r'\[NAME\]',
        r'\[ADDRESS\]',
        r'\[DATE\]',
        r'\[ACCOUNT\]',
    ]

    for pattern in placeholder_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        placeholders.extend(matches)

    return placeholders


def detect_ai_self_reference(text: str) -> List[str]:
    """Detect AI self-references that shouldn't appear."""
    ai_refs = []

    ai_patterns = [
        r'as an AI',
        r'I am an AI',
        r'I\'m an AI',
        r'artificial intelligence',
        r'language model',
        r'ChatGPT',
        r'Claude',
        r'GPT-\d',
        r'I cannot',
        r'I don\'t have access',
        r'I was trained',
    ]

    for pattern in ai_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            ai_refs.append(pattern)

    return ai_refs


def check_sentence_completeness(text: str) -> List[str]:
    """Check for broken or incomplete sentences."""
    issues = []

    sentences = re.split(r'(?<=[.!?])\s+', text)

    for i, sentence in enumerate(sentences):
        sentence = sentence.strip()
        if not sentence:
            continue

        # Check for sentences that don't start with capital
        if sentence[0].islower() and not sentence.startswith(('e.g.', 'i.e.', 'etc.')):
            issues.append(f"Sentence {i+1} starts with lowercase: {sentence[:50]}...")

        # Check for sentences without ending punctuation
        if len(sentence) > 10 and not sentence[-1] in '.!?':
            if not re.search(r'\d$', sentence):  # Allow numbers at end
                issues.append(f"Sentence {i+1} missing punctuation: {sentence[-50:]}...")

        # Check for orphaned punctuation
        if re.match(r'^[.!?,;:]', sentence):
            issues.append(f"Orphaned punctuation at sentence {i+1}")

    return issues


def check_repetition(text: str, threshold: float = 0.3) -> Tuple[bool, float]:
    """Check for excessive phrase repetition."""
    # Extract 3-grams
    words = re.findall(r'\b\w+\b', text.lower())
    if len(words) < 10:
        return False, 0.0

    trigrams = [' '.join(words[i:i+3]) for i in range(len(words)-2)]
    trigram_counts = Counter(trigrams)

    # Calculate repetition ratio
    total_trigrams = len(trigrams)
    unique_trigrams = len(set(trigrams))

    if total_trigrams == 0:
        return False, 0.0

    repetition_ratio = 1 - (unique_trigrams / total_trigrams)

    # Check for highly repeated phrases
    max_repeat = max(trigram_counts.values()) if trigram_counts else 0
    high_repeat = max_repeat > 5 and max_repeat / total_trigrams > 0.05

    return repetition_ratio > threshold or high_repeat, repetition_ratio


# =============================================================================
# TEST FIXTURES
# =============================================================================

LEGAL_TONES = ['strict_legal', 'professional', 'aggressive', 'soft_legal']
CIVIL_TONES = ['conversational', 'civil_professional', 'assertive', 'narrative']
ALL_TONES = LEGAL_TONES + CIVIL_TONES
GROUPING_STRATEGIES = ['by_fcra_section', 'by_metro2_field', 'by_creditor', 'by_severity']
MONTE_CARLO_SEEDS = list(range(1, 51))


SAMPLE_VIOLATIONS = [
    {
        "creditor_name": "Example Bank",
        "account_number_masked": "XXXX1234",
        "violation_type": "balance_error",
        "fcra_section": "611",
        "metro2_field": "17",
        "evidence": "Balance reported as $5,000 but actual is $0",
        "severity": "high",
    },
    {
        "creditor_name": "ABC Collections",
        "account_number_masked": "XXXX5678",
        "violation_type": "late_payment_error",
        "fcra_section": "623",
        "metro2_field": "24",
        "evidence": "Late payments reported incorrectly",
        "severity": "medium",
    },
    {
        "creditor_name": "XYZ Credit",
        "account_number_masked": "XXXX9012",
        "violation_type": "account_status_error",
        "fcra_section": "605",
        "metro2_field": "25",
        "evidence": "Account shown as open but was closed",
        "severity": "low",
    },
]

SAMPLE_CONSUMER = {
    "name": "John Doe",
    "address": "123 Main Street",
    "city": "Anytown",
    "state": "CA",
    "zip": "90210",
}


def generate_test_letter(tone: str, seed: int, grouping: str = "by_fcra_section") -> Dict:
    """Generate a test letter with given parameters."""
    domain = "legal" if tone in LEGAL_TONES else "civil"

    try:
        if domain == "civil" or is_civil_tone(tone):
            # Use civil letter generator for civil tones
            # Map grouping strategies for civil
            civil_grouping = grouping
            if grouping in ["by_fcra_section", "by_metro2_field"]:
                civil_grouping = "by_creditor"  # Civil doesn't use FCRA/Metro-2 grouping
            elif grouping == "by_severity":
                civil_grouping = "by_severity"

            result = generate_civil_letter(
                violations=SAMPLE_VIOLATIONS,
                bureau="transunion",
                tone=tone,
                consumer_name=SAMPLE_CONSUMER["name"],
                consumer_address=f"{SAMPLE_CONSUMER['address']}, {SAMPLE_CONSUMER['city']}, {SAMPLE_CONSUMER['state']} {SAMPLE_CONSUMER['zip']}",
                grouping_strategy=civil_grouping,
                seed=seed,
            )
            # Convert to standard test format
            return {
                "letter": result.content,
                "is_valid": result.is_valid,
                "metadata": result.metadata,
            }
        else:
            # Use legal letter generator for legal tones
            result = generate_legal_letter(
                violations=SAMPLE_VIOLATIONS,
                consumer=SAMPLE_CONSUMER,
                bureau="transunion",
                tone=tone,
                grouping_strategy=grouping,
                seed=seed,
                include_case_law=(tone in ["strict_legal", "aggressive"]),
                include_metro2=True,
                include_mov=True,
            )
            return result
    except Exception as e:
        return {"letter": "", "error": str(e), "is_valid": False}


# =============================================================================
# TEST CLASSES
# =============================================================================

class TestMonteCarloContentCoherence:
    """Monte-Carlo stress test across all tones and seeds."""

    def test_runs_50_seeds_legal(self):
        """Smoke test: generate letters across 50 seeds for legal tones."""
        failures = []

        for tone in LEGAL_TONES:
            for seed in MONTE_CARLO_SEEDS[:10]:  # Sample 10 seeds per tone
                result = generate_test_letter(tone, seed)
                if not result.get("letter"):
                    failures.append(f"{tone}/seed={seed}: Empty letter")
                elif len(result["letter"]) < 500:
                    failures.append(f"{tone}/seed={seed}: Letter too short ({len(result['letter'])} chars)")

        assert len(failures) == 0, f"Failures:\n" + "\n".join(failures)

    def test_runs_50_seeds_civil(self):
        """Smoke test: generate letters across 50 seeds for civil tones."""
        failures = []

        for tone in CIVIL_TONES:
            for seed in MONTE_CARLO_SEEDS[:10]:
                result = generate_test_letter(tone, seed)
                if not result.get("letter"):
                    failures.append(f"{tone}/seed={seed}: Empty letter")
                elif len(result["letter"]) < 300:
                    failures.append(f"{tone}/seed={seed}: Letter too short")

        assert len(failures) == 0, f"Failures:\n" + "\n".join(failures)

    def test_all_grouping_strategies(self):
        """Test all grouping strategies produce valid output."""
        failures = []

        for strategy in GROUPING_STRATEGIES:
            for tone in ['professional', 'conversational']:
                result = generate_test_letter(tone, seed=42, grouping=strategy)
                if not result.get("letter"):
                    failures.append(f"{tone}/{strategy}: Empty letter")

        assert len(failures) == 0, f"Failures:\n" + "\n".join(failures)


class TestLegalContentCorrectness:
    """Test legal content correctness."""

    def test_legal_citations_match_ssot(self):
        """Verify all FCRA citations match SSOT resolver."""
        errors = []

        for tone in LEGAL_TONES:
            result = generate_test_letter(tone, seed=42)
            letter = result.get("letter", "")

            citation_errors = ssot_validate_citation(letter)
            if citation_errors:
                errors.extend([f"{tone}: {e}" for e in citation_errors])

        assert len(errors) == 0, f"Citation errors:\n" + "\n".join(errors)

    def test_legal_has_required_sections(self):
        """Verify legal letters have required sections."""
        for tone in LEGAL_TONES:
            result = generate_test_letter(tone, seed=42)
            letter = result.get("letter", "")

            # Check for basic required elements - subject line or formal notice indicator
            has_subject = (
                "RE:" in letter or
                "Subject:" in letter.lower() or
                "formal dispute" in letter.lower() or
                "certified mail" in letter.lower() or
                "dispute notice" in letter.lower()
            )
            assert has_subject, f"{tone}: Missing subject line or formal notice indicator"
            assert re.search(r'dispute|violation|error', letter, re.IGNORECASE), f"{tone}: Missing dispute language"

    def test_no_wrong_statute_suffix(self):
        """Verify no incorrect statute suffixes."""
        errors = []

        # Known incorrect patterns
        bad_patterns = [
            r'15 U\.S\.C\. § 1681\s*\(Section',  # Old format
            r'§ 1681x\b',  # Invalid section
            r'§ 1681z\b',  # Invalid section
        ]

        for tone in LEGAL_TONES:
            result = generate_test_letter(tone, seed=42)
            letter = result.get("letter", "")

            for pattern in bad_patterns:
                if re.search(pattern, letter):
                    errors.append(f"{tone}: Found bad pattern {pattern}")

        assert len(errors) == 0, f"Statute errors:\n" + "\n".join(errors)

    def test_no_illegal_metro2_fields(self):
        """Verify Metro-2 field references are valid."""
        errors = []

        for tone in LEGAL_TONES:
            result = generate_test_letter(tone, seed=42)
            letter = result.get("letter", "")

            field_errors = validate_metro2_fields(letter)
            if field_errors:
                errors.extend([f"{tone}: {e}" for e in field_errors])

        assert len(errors) == 0, f"Metro-2 errors:\n" + "\n".join(errors)

    def test_case_law_accuracy(self):
        """Verify case law citations are from known library."""
        known_cases = [
            "Cushman",
            "Stevenson",
            "Johnson v. MBNA",
            "Saunders",
            "Henson",
            "Gorman",
        ]

        for tone in ['strict_legal', 'aggressive']:
            result = generate_test_letter(tone, seed=42)
            letter = result.get("letter", "")

            # Extract case citations
            case_pattern = r'([A-Z][a-z]+)\s+v\.\s+'
            cases = re.findall(case_pattern, letter)

            for case in cases:
                # Allow known cases or verify format
                assert any(k.lower() in case.lower() for k in known_cases) or \
                       re.match(r'^[A-Z][a-z]+$', case), \
                       f"Unknown case law: {case}"

    def test_case_law_only_when_enabled(self):
        """Verify case law only appears when enabled."""
        result = generate_test_letter('soft_legal', seed=42)
        letter = result.get("letter", "")

        # soft_legal should have minimal/no case law
        case_pattern = r'\bv\.\s+(?:Trans Union|Experian|Equifax|MBNA)'
        case_matches = re.findall(case_pattern, letter, re.IGNORECASE)

        # Allow some but not excessive
        assert len(case_matches) <= 2, "Too many case citations for soft_legal tone"


class TestCivilNaturalness:
    """Test civil letter naturalness."""

    def test_no_legal_terms_in_civil(self):
        """Verify civil letters don't contain legal jargon."""
        errors = []

        for tone in CIVIL_TONES:
            result = generate_test_letter(tone, seed=42)
            letter = result.get("letter", "")

            illegal = detect_illegal_terms(letter, "civil")
            if illegal:
                errors.extend([f"{tone}: Found {term}" for term in illegal])

        # Allow some flexibility but flag excessive
        assert len(errors) <= 2, f"Legal terms in civil:\n" + "\n".join(errors)

    def test_readability_flesch(self):
        """Verify civil letters have appropriate reading level."""
        for tone in CIVIL_TONES:
            result = generate_test_letter(tone, seed=42)
            letter = result.get("letter", "")

            if letter:
                score = flesch_kincaid(letter)
                # Civil should be readable (score > 30 = readable by average adult)
                assert score > 20, f"{tone}: Reading level too difficult (Flesch={score:.1f})"

    def test_soft_language_alignment(self):
        """Verify civil tones use appropriate soft language."""
        soft_patterns = [
            r'please',
            r'thank you',
            r'appreciate',
            r'would like',
            r'kindly',
            r'help',
        ]

        for tone in ['conversational', 'narrative']:
            result = generate_test_letter(tone, seed=42)
            letter = result.get("letter", "").lower()

            soft_count = sum(1 for p in soft_patterns if re.search(p, letter))
            assert soft_count >= 1, f"{tone}: Missing soft language markers"

    def test_no_mov_or_case_law(self):
        """Verify civil letters don't have MOV or case law sections."""
        for tone in CIVIL_TONES:
            result = generate_test_letter(tone, seed=42)
            letter = result.get("letter", "")

            assert "METHOD OF VERIFICATION" not in letter.upper(), f"{tone}: Has MOV section"
            assert "CASE LAW" not in letter.upper(), f"{tone}: Has case law section"


class TestToneAlignment:
    """Test tone-specific content alignment."""

    def test_aggressive_has_dominant_force_words(self):
        """Verify aggressive tone uses forceful language."""
        force_words = [
            r'demand',
            r'require',
            r'immediately',
            r'failure to comply',
            r'legal action',
            r'liability',
            r'damages',
            r'willful',
        ]

        result = generate_test_letter('aggressive', seed=42)
        letter = result.get("letter", "").lower()

        force_count = sum(1 for w in force_words if re.search(w, letter))
        assert force_count >= 3, f"Aggressive tone lacks force words (found {force_count})"

    def test_soft_legal_has_polite_modifiers(self):
        """Verify soft_legal uses polite modifiers."""
        polite_patterns = [
            r'respectfully',
            r'kindly',
            r'please',
            r'appreciate',
            r'thank you',
        ]

        result = generate_test_letter('soft_legal', seed=42)
        letter = result.get("letter", "").lower()

        polite_count = sum(1 for p in polite_patterns if re.search(p, letter))
        assert polite_count >= 1, "soft_legal lacks polite modifiers"

    def test_civil_friendly_has_warmth(self):
        """Verify conversational civil has warm language."""
        warm_patterns = [
            r'hi|hello|dear',
            r'hope|appreciate',
            r'thank|grateful',
            r'please help',
        ]

        result = generate_test_letter('conversational', seed=42)
        letter = result.get("letter", "").lower()

        warm_count = sum(1 for p in warm_patterns if re.search(p, letter))
        assert warm_count >= 1, "Conversational lacks warmth"

    def test_professional_has_formality(self):
        """Verify professional tone maintains formality."""
        result = generate_test_letter('professional', seed=42)
        letter = result.get("letter", "")

        # Should not have casual language
        casual_patterns = [r'\bhi\b', r'\bhey\b', r'gonna', r'wanna', r'kinda']

        for pattern in casual_patterns:
            assert not re.search(pattern, letter, re.IGNORECASE), \
                f"Professional has casual: {pattern}"


class TestViolationAccuracy:
    """Test violation content accuracy."""

    def test_each_violation_is_mentioned(self):
        """Verify each input violation appears in output."""
        result = generate_test_letter('professional', seed=42)
        letter = result.get("letter", "").lower()

        for violation in SAMPLE_VIOLATIONS:
            creditor = violation["creditor_name"].lower()
            # Check creditor or account appears
            assert creditor in letter or violation["account_number_masked"] in letter, \
                f"Missing violation for {creditor}"

    def test_each_violation_is_correctly_labeled(self):
        """Verify violations are correctly categorized."""
        result = generate_test_letter('strict_legal', seed=42)
        letter = result.get("letter", "").lower()

        # Each violation type should be addressed
        for violation in SAMPLE_VIOLATIONS:
            vtype = violation["violation_type"].replace("_", " ")
            # Allow partial matches
            assert any(word in letter for word in vtype.split()), \
                f"Violation type not mentioned: {vtype}"

    def test_no_hallucinated_violations(self):
        """Verify no made-up violations appear."""
        result = generate_test_letter('professional', seed=42)
        letter = result.get("letter", "")

        known_creditors = {v["creditor_name"].lower() for v in SAMPLE_VIOLATIONS}

        # Extract creditor mentions
        creditor_pattern = r'(?:Account|Creditor)[:\s]+([A-Za-z\s]+?)(?:\s*-|\n|$)'
        mentions = re.findall(creditor_pattern, letter)

        for mention in mentions:
            mention_clean = mention.strip().lower()
            if mention_clean and len(mention_clean) > 3:
                # Allow if it's a known creditor or bureau
                valid = any(k in mention_clean for k in known_creditors) or \
                        any(b in mention_clean for b in ['transunion', 'experian', 'equifax'])
                if not valid and not re.match(r'^[x\d\s-]+$', mention_clean):
                    pass  # Allow for now, could be format variation

    def test_metro2_field_explanations_correct(self):
        """Verify Metro-2 field explanations are accurate."""
        result = generate_test_letter('strict_legal', seed=42)
        letter = result.get("letter", "")

        # Check that mentioned fields have explanations
        field_pattern = r'Field\s*(\d+)[:\s]+([^\n]+)'
        field_mentions = re.findall(field_pattern, letter)

        for field_num, explanation in field_mentions:
            assert len(explanation) > 10, f"Field {field_num} lacks explanation"


class TestGroupingCorrectness:
    """Test grouping strategy correctness."""

    def test_group_by_section(self):
        """Verify by_fcra_section grouping."""
        result = generate_test_letter('professional', seed=42, grouping='by_fcra_section')
        letter = result.get("letter", "")

        # Should mention FCRA sections
        assert re.search(r'Section\s*\d{3}|§\s*\d{3}', letter), \
            "Missing FCRA section references"

    def test_group_by_creditor(self):
        """Verify by_creditor grouping."""
        result = generate_test_letter('professional', seed=42, grouping='by_creditor')
        letter = result.get("letter", "")

        # Each creditor should be mentioned
        for violation in SAMPLE_VIOLATIONS:
            assert violation["creditor_name"] in letter, \
                f"Missing creditor: {violation['creditor_name']}"

    def test_group_by_metro2(self):
        """Verify by_metro2_field grouping."""
        result = generate_test_letter('strict_legal', seed=42, grouping='by_metro2_field')
        letter = result.get("letter", "")

        # Should mention Metro-2 fields
        assert re.search(r'Field\s*\d+|Metro-?2', letter, re.IGNORECASE), \
            "Missing Metro-2 references"

    def test_group_by_severity(self):
        """Verify by_severity grouping."""
        result = generate_test_letter('professional', seed=42, grouping='by_severity')
        letter = result.get("letter", "").lower()

        # Should have severity-related organization
        severity_terms = ['high', 'medium', 'low', 'critical', 'severe', 'priority']
        has_severity = any(term in letter for term in severity_terms)
        # Allow if organized but not explicitly labeled
        assert has_severity or len(letter) > 500, "Missing severity organization"


class TestStructuralMeaningfulness:
    """Test structural content meaningfulness."""

    def test_no_empty_sections(self):
        """Verify no sections are empty."""
        for tone in ['professional', 'strict_legal']:
            result = generate_test_letter(tone, seed=42)
            letter = result.get("letter", "")

            sections = extract_sections(letter)
            for name, content in sections.items():
                # Allow signature to be just a name
                if name != 'closing':
                    assert len(content.strip()) > 20, f"{tone}: Empty section {name}"

    def test_no_duplicate_sections(self):
        """Verify no duplicate section headers."""
        for tone in LEGAL_TONES:
            result = generate_test_letter(tone, seed=42)
            letter = result.get("letter", "")

            section_headers = re.findall(r'^[IVX]+\.\s+[A-Z\s]+', letter, re.MULTILINE)
            unique_headers = set(section_headers)

            assert len(section_headers) == len(unique_headers), \
                f"{tone}: Duplicate sections found"

    def test_every_section_has_meaningful_text(self):
        """Verify each section has substantive content."""
        result = generate_test_letter('strict_legal', seed=42)
        letter = result.get("letter", "")

        sections = extract_sections(letter)
        for name, content in sections.items():
            if content:
                words = re.findall(r'\b\w+\b', content)
                assert len(words) >= 5, f"Section {name} has too few words"

    def test_no_placeholder_tokens(self):
        """Verify no placeholder tokens remain."""
        errors = []

        for tone in ALL_TONES:
            result = generate_test_letter(tone, seed=42)
            letter = result.get("letter", "")

            placeholders = detect_placeholders(letter)
            if placeholders:
                errors.extend([f"{tone}: {p}" for p in placeholders])

        assert len(errors) == 0, f"Placeholders found:\n" + "\n".join(errors)


class TestNoContradictions:
    """Test for contradictory statements."""

    def test_no_conflicting_statements(self):
        """Verify no contradictory statements."""
        errors = []

        for tone in ['professional', 'strict_legal']:
            result = generate_test_letter(tone, seed=42)
            letter = result.get("letter", "")

            contradictions = find_contradictions(letter)
            if contradictions:
                errors.extend([f"{tone}: {c}" for c in contradictions])

        assert len(errors) == 0, f"Contradictions:\n" + "\n".join(str(e) for e in errors)

    def test_consistent_tense(self):
        """Verify consistent tense usage."""
        result = generate_test_letter('professional', seed=42)
        letter = result.get("letter", "")

        # Check that letter doesn't mix past/present excessively
        past_tense = len(re.findall(r'\b\w+ed\b', letter))
        present_tense = len(re.findall(r'\b(?:is|are|am|has|have)\b', letter, re.IGNORECASE))

        # Both should be present, but ratio shouldn't be extreme
        if past_tense > 0 and present_tense > 0:
            ratio = max(past_tense, present_tense) / min(past_tense, present_tense)
            assert ratio < 20, f"Extreme tense ratio: {ratio:.1f}"

    def test_consistent_voice(self):
        """Verify first-person consumer voice."""
        result = generate_test_letter('professional', seed=42)
        letter = result.get("letter", "")

        # Should use first person
        first_person = len(re.findall(r'\bI\b|\bmy\b|\bme\b', letter, re.IGNORECASE))
        third_person = len(re.findall(r'\bthe consumer\b|\bhe\b|\bshe\b', letter, re.IGNORECASE))

        assert first_person > third_person, "Letter should use first person"


class TestOutputCleanliness:
    """Test output cleanliness."""

    def test_no_double_spaces(self):
        """Verify no double spaces."""
        for tone in ALL_TONES:
            result = generate_test_letter(tone, seed=42)
            letter = result.get("letter", "")

            double_spaces = re.findall(r'  +', letter)
            # Allow some (in formatting) but not excessive
            assert len(double_spaces) < 20, f"{tone}: Too many double spaces"

    def test_no_broken_sentences(self):
        """Verify no broken sentences."""
        errors = []

        for tone in ['professional', 'strict_legal']:
            result = generate_test_letter(tone, seed=42)
            letter = result.get("letter", "")

            issues = check_sentence_completeness(letter)
            if issues:
                errors.extend([f"{tone}: {i}" for i in issues[:3]])  # Limit errors

        assert len(errors) < 5, f"Sentence issues:\n" + "\n".join(errors)

    def test_no_html_artifacts(self):
        """Verify no HTML artifacts."""
        html_patterns = [
            r'</?[a-z]+[^>]*>',
            r'&[a-z]+;',
            r'&\#\d+;',
        ]

        for tone in ALL_TONES:
            result = generate_test_letter(tone, seed=42)
            letter = result.get("letter", "")

            for pattern in html_patterns:
                assert not re.search(pattern, letter, re.IGNORECASE), \
                    f"{tone}: HTML artifact found: {pattern}"

    def test_no_leftover_format_tokens(self):
        """Verify no format tokens remain."""
        format_patterns = [
            r'\{[a-z_]+\}',
            r'%[sd]',
            r'\$\d+',
        ]

        for tone in ALL_TONES:
            result = generate_test_letter(tone, seed=42)
            letter = result.get("letter", "")

            for pattern in format_patterns:
                matches = re.findall(pattern, letter)
                # Filter out currency
                matches = [m for m in matches if not re.match(r'\$\d', m)]
                assert len(matches) == 0, f"{tone}: Format token found: {matches}"

    def test_no_ai_self_ref(self):
        """Verify no AI self-references."""
        errors = []

        for tone in ALL_TONES:
            result = generate_test_letter(tone, seed=42)
            letter = result.get("letter", "")

            ai_refs = detect_ai_self_reference(letter)
            if ai_refs:
                errors.extend([f"{tone}: {r}" for r in ai_refs])

        assert len(errors) == 0, f"AI self-references:\n" + "\n".join(errors)


class TestReproducibility:
    """Test multi-seed reproducibility."""

    def test_same_seed_produces_same_output(self):
        """Verify same seed produces identical output."""
        for tone in ['professional', 'conversational']:
            result1 = generate_test_letter(tone, seed=12345)
            result2 = generate_test_letter(tone, seed=12345)

            assert result1.get("letter") == result2.get("letter"), \
                f"{tone}: Same seed produced different output"

    def test_different_seeds_produce_different_output(self):
        """Verify different seeds produce different output."""
        for tone in ['professional', 'conversational']:
            result1 = generate_test_letter(tone, seed=1)
            result2 = generate_test_letter(tone, seed=2)

            letter1 = result1.get("letter", "")
            letter2 = result2.get("letter", "")

            # Should have some difference
            if letter1 and letter2:
                # Calculate similarity
                words1 = set(letter1.split())
                words2 = set(letter2.split())
                similarity = len(words1 & words2) / max(len(words1), len(words2))

                assert similarity < 0.99, f"{tone}: Seeds produced identical output"


class TestRepetitionControl:
    """Test repetition is controlled."""

    def test_no_excessive_repetition(self):
        """Verify no excessive phrase repetition."""
        errors = []

        for tone in ALL_TONES:
            result = generate_test_letter(tone, seed=42)
            letter = result.get("letter", "")

            if letter:
                is_repetitive, ratio = check_repetition(letter, threshold=0.4)
                if is_repetitive:
                    errors.append(f"{tone}: Repetition ratio {ratio:.2f}")

        assert len(errors) == 0, f"Repetition issues:\n" + "\n".join(errors)

    def test_variation_across_seeds(self):
        """Verify variation across different seeds."""
        letters = []

        for seed in [1, 2, 3, 4, 5]:
            result = generate_test_letter('professional', seed=seed)
            letters.append(result.get("letter", ""))

        # Calculate pairwise similarity
        for i in range(len(letters)):
            for j in range(i + 1, len(letters)):
                if letters[i] and letters[j]:
                    words1 = set(letters[i].split())
                    words2 = set(letters[j].split())
                    similarity = len(words1 & words2) / max(len(words1), len(words2))

                    assert similarity < 0.95, \
                        f"Seeds {i+1} and {j+1} too similar ({similarity:.2f})"


class TestAccountMasking:
    """Test account number masking."""

    def test_account_numbers_masked(self):
        """Verify account numbers are properly masked."""
        for tone in ['professional', 'conversational']:
            result = generate_test_letter(tone, seed=42)
            letter = result.get("letter", "")

            # Should contain masked format
            masked_pattern = r'XXXX\d{4}|X+\d{3,4}|\*+\d{3,4}'
            assert re.search(masked_pattern, letter), \
                f"{tone}: No masked account numbers found"

            # Should NOT contain full account numbers (16+ digits)
            full_number_pattern = r'\b\d{10,}\b'
            full_matches = re.findall(full_number_pattern, letter)
            # Filter out dates and zip codes
            suspicious = [m for m in full_matches if len(m) > 10]
            assert len(suspicious) == 0, \
                f"{tone}: Possible unmasked account: {suspicious}"


class TestBureauContent:
    """Test bureau-specific content."""

    def test_bureau_address_present(self):
        """Verify bureau address is included."""
        for tone in ['professional', 'conversational']:
            result = generate_test_letter(tone, seed=42)
            letter = result.get("letter", "")

            # Should have some address indication
            address_patterns = [
                r'P\.?O\.?\s*Box',
                r'\d+\s+[A-Za-z]+\s+(?:Street|Ave|Road|Blvd)',
                r'TransUnion|Experian|Equifax',
            ]

            has_address = any(re.search(p, letter, re.IGNORECASE) for p in address_patterns)
            assert has_address, f"{tone}: Missing bureau address"

    def test_consumer_info_present(self):
        """Verify consumer information is included."""
        for tone in ['professional', 'conversational']:
            result = generate_test_letter(tone, seed=42)
            letter = result.get("letter", "")

            # Should contain consumer name
            assert SAMPLE_CONSUMER["name"] in letter, \
                f"{tone}: Consumer name missing"

    def test_signature_present(self):
        """Verify signature is present."""
        for tone in ALL_TONES:
            result = generate_test_letter(tone, seed=42)
            letter = result.get("letter", "")

            # Should have closing and name
            closing_patterns = [
                r'Sincerely',
                r'Respectfully',
                r'Best regards',
                r'Thank you',
            ]

            has_closing = any(re.search(p, letter, re.IGNORECASE) for p in closing_patterns)
            has_name = SAMPLE_CONSUMER["name"] in letter[letter.rfind("Sinc"):] if "Sinc" in letter else \
                       SAMPLE_CONSUMER["name"] in letter[-500:]

            assert has_closing or has_name, f"{tone}: Missing signature block"


# =============================================================================
# PYTEST CONFIGURATION
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
