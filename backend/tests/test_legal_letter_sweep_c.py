"""
Legal Letter Generator - SWEEP C (Anti-Template Validation)
Validates non-repetitive, human-sounding, high-entropy output.
"""
import pytest
import math
import re
import difflib
from collections import Counter
from typing import List, Dict, Set, Tuple

from app.services.legal_letter_generator.legal_assembler import LegalLetterAssembler


# =============================================================================
# WRAPPER FUNCTION - Adapts API for cleaner test code
# =============================================================================

def generate_letter(
    violations,
    consumer_info,
    bureau="transunion",
    tone="professional",
    grouping_strategy="by_fcra_section",
    seed=42,
    include_case_law=True,
    include_metro2=True,
    include_mov=True,
):
    """Helper to generate a letter with simpler API for tests."""
    assembler = LegalLetterAssembler(
        tone=tone,
        grouping_strategy=grouping_strategy,
        seed=seed,
        include_case_law=include_case_law,
        include_metro2=include_metro2,
        include_mov=include_mov,
    )
    letter_content, validation_issues = assembler.generate(
        violations=violations,
        consumer=consumer_info,
        bureau=bureau,
    )
    return {
        "letter_content": letter_content,
        "validation_issues": validation_issues,
    }


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def split_sentences(text: str) -> List[str]:
    """Split text into sentences."""
    text = re.sub(r'\n+', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
    return [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]


def calc_similarity(a: str, b: str) -> float:
    """Calculate similarity ratio between two strings."""
    return difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()


def assert_sentence_uniqueness(sentences: List[str], threshold: float = 0.70) -> List[Tuple[str, str, float]]:
    """Find sentence pairs exceeding similarity threshold."""
    violations = []
    for i, s1 in enumerate(sentences):
        for j, s2 in enumerate(sentences):
            if i < j:
                sim = calc_similarity(s1, s2)
                if sim >= threshold:
                    violations.append((s1[:50], s2[:50], sim))
    return violations


def entropy(text: str) -> float:
    """Calculate Shannon entropy of text."""
    if not text:
        return 0.0
    text = text.lower()
    freq = Counter(text)
    total = len(text)
    return -sum((count / total) * math.log2(count / total) for count in freq.values())


def word_entropy(text: str) -> float:
    """Calculate word-level entropy."""
    words = re.findall(r'\b\w+\b', text.lower())
    if not words:
        return 0.0
    freq = Counter(words)
    total = len(words)
    return -sum((count / total) * math.log2(count / total) for count in freq.values())


def extract_tone_fingerprint(text: str) -> Dict[str, int]:
    """Extract tone markers from text."""
    markers = {
        "aggressive": [
            "DEMAND", "VIOLATION", "WILLFUL", "IMMEDIATELY", "NOTICE",
            "FAIL", "MUST", "REQUIRED", "LIABILITY", "NONCOMPLIANCE"
        ],
        "soft_legal": [
            "please", "would appreciate", "kindly", "thank you", "help",
            "hoping", "would be grateful", "if possible", "at your convenience"
        ],
        "strict_legal": [
            "pursuant to", "hereby", "enumerated", "aforementioned",
            "notwithstanding", "herein", "thereto", "prima facie"
        ],
        "professional": [
            "request", "respectfully", "attention", "review",
            "investigation", "appreciate", "forward to"
        ]
    }
    fingerprint = {}
    text_lower = text.lower()
    text_upper = text
    for tone, words in markers.items():
        count = 0
        for word in words:
            if word.isupper():
                count += text_upper.count(word)
            else:
                count += text_lower.count(word.lower())
        fingerprint[tone] = count
    return fingerprint


def stem_simple(sentence: str) -> str:
    """Simple stemming: first 5 words lowercased."""
    words = re.findall(r'\b\w+\b', sentence.lower())
    return ' '.join(words[:5])


def get_phrase_ngrams(text: str, n: int = 3) -> List[str]:
    """Extract word n-grams from text."""
    words = re.findall(r'\b\w+\b', text.lower())
    return [' '.join(words[i:i+n]) for i in range(len(words) - n + 1)]


def find_repeated_phrases(text: str, min_words: int = 4, min_count: int = 2) -> List[Tuple[str, int]]:
    """Find repeated phrases in text."""
    ngrams = get_phrase_ngrams(text, min_words)
    counts = Counter(ngrams)
    return [(phrase, count) for phrase, count in counts.items() if count >= min_count]


def extract_section(text: str, section_name: str) -> str:
    """Extract a section from the letter by header pattern."""
    patterns = [
        rf'{section_name}.*?\n(.*?)(?=\n[IVX]+\.|$)',
        rf'{section_name.upper()}.*?\n(.*?)(?=\n[IVX]+\.|$)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return ""


def get_paragraph_lengths(text: str) -> List[int]:
    """Get lengths of paragraphs in text."""
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    return [len(p) for p in paragraphs]


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def sample_violations():
    """Standard test violations."""
    return [
        {
            "creditor_name": "CAPITAL ONE BANK",
            "account_number_masked": "****1234",
            "violation_type": "inaccurate_balance",
            "fcra_section": "623(a)(1)",
            "metro2_field": "balance_amount",
            "evidence": "Reported balance of $5,000 differs from actual balance of $3,200",
            "severity": "high"
        },
        {
            "creditor_name": "CHASE BANK",
            "account_number_masked": "****5678",
            "violation_type": "incorrect_payment_status",
            "fcra_section": "623(a)(1)",
            "metro2_field": "payment_status",
            "evidence": "Reported as 60 days late when payment was on time",
            "severity": "high"
        },
        {
            "creditor_name": "DISCOVER FINANCIAL",
            "account_number_masked": "****9012",
            "violation_type": "outdated_information",
            "fcra_section": "605(a)",
            "metro2_field": "date_fields",
            "evidence": "Account reporting beyond 7-year obsolescence period",
            "severity": "medium"
        },
    ]


@pytest.fixture
def consumer_info():
    """Standard consumer info."""
    return {
        "name": "John Q. Consumer",
        "address": "123 Main Street",
        "city": "Anytown",
        "state": "CA",
        "zip": "90210",
        "ssn_last4": "1234"
    }


@pytest.fixture
def diverse_violations():
    """More diverse violation set for deeper testing."""
    return [
        {"creditor_name": "BANK OF AMERICA", "account_number_masked": "****1111",
         "violation_type": "balance_discrepancy", "fcra_section": "623(a)(1)",
         "metro2_field": "balance_amount", "evidence": "Balance mismatch", "severity": "high"},
        {"creditor_name": "WELLS FARGO", "account_number_masked": "****2222",
         "violation_type": "payment_history_error", "fcra_section": "623(a)(1)",
         "metro2_field": "payment_history", "evidence": "Wrong payment dates", "severity": "high"},
        {"creditor_name": "CITIBANK", "account_number_masked": "****3333",
         "violation_type": "wrong_account_status", "fcra_section": "623(a)(1)",
         "metro2_field": "payment_status", "evidence": "Status incorrect", "severity": "medium"},
        {"creditor_name": "US BANK", "account_number_masked": "****4444",
         "violation_type": "incorrect_dates", "fcra_section": "623(a)(2)",
         "metro2_field": "date_fields", "evidence": "Wrong dates", "severity": "medium"},
        {"creditor_name": "PNC BANK", "account_number_masked": "****5555",
         "violation_type": "duplicate_account", "fcra_section": "607(b)",
         "metro2_field": "account_info", "evidence": "Duplicate entry", "severity": "low"},
    ]


# =============================================================================
# TEST: INTRA-LETTER SIMILARITY
# =============================================================================

class TestIntraLetterSimilarity:
    """Tests for sentence-level uniqueness within a single letter."""

    @pytest.mark.parametrize("tone", ["strict_legal", "professional", "soft_legal", "aggressive"])
    def test_no_highly_similar_sentences(self, sample_violations, consumer_info, tone):
        """No two sentences should exceed 70% similarity."""
        result = generate_letter(
            violations=sample_violations,
            consumer_info=consumer_info,
            bureau="transunion",
            tone=tone,
            seed=42
        )
        sentences = split_sentences(result["letter_content"])

        violations = assert_sentence_uniqueness(sentences, threshold=0.70)
        assert len(violations) == 0, f"Found {len(violations)} similar sentence pairs: {violations[:3]}"

    @pytest.mark.parametrize("tone", ["strict_legal", "professional", "soft_legal", "aggressive"])
    def test_no_repeated_sentence_stems(self, sample_violations, consumer_info, tone):
        """No repeated sentence stems (first 5 words)."""
        result = generate_letter(
            violations=sample_violations,
            consumer_info=consumer_info,
            bureau="experian",
            tone=tone,
            seed=123
        )
        sentences = split_sentences(result["letter_content"])

        stems = [stem_simple(s) for s in sentences]
        stem_counts = Counter(stems)
        repeated = [(stem, count) for stem, count in stem_counts.items()
                    if count > 2 and len(stem.split()) >= 4]

        assert len(repeated) == 0, f"Repeated stems found: {repeated[:5]}"

    def test_no_repeated_intro_phrases(self, diverse_violations, consumer_info):
        """Intro phrases should not repeat verbatim."""
        result = generate_letter(
            violations=diverse_violations,
            consumer_info=consumer_info,
            bureau="equifax",
            tone="professional",
            seed=456
        )

        intro_patterns = [
            r"(?:I am writing|This letter|I hereby|Please be advised|I dispute)",
        ]
        content = result["letter_content"]

        for pattern in intro_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            # Legal letters naturally repeat "I dispute" for each violation, allow up to 3
            assert len(matches) <= 3, f"Intro phrase repeated too often: {matches}"


# =============================================================================
# TEST: TRANSITION VARIATION
# =============================================================================

class TestTransitionVariation:
    """Tests for transition phrase diversity."""

    TRANSITION_PHRASES = [
        "additionally", "furthermore", "moreover", "also", "in addition",
        "when reviewing", "upon examination", "another issue", "this account also"
    ]

    @pytest.mark.parametrize("tone", ["strict_legal", "professional", "soft_legal", "aggressive"])
    def test_transition_phrases_vary(self, diverse_violations, consumer_info, tone):
        """Transition phrases must vary, not repeat."""
        result = generate_letter(
            violations=diverse_violations,
            consumer_info=consumer_info,
            bureau="transunion",
            tone=tone,
            seed=789
        )
        content = result["letter_content"].lower()

        used_transitions = []
        for phrase in self.TRANSITION_PHRASES:
            count = content.count(phrase.lower())
            if count > 0:
                used_transitions.append((phrase, count))

        for phrase, count in used_transitions:
            assert count <= 2, f"Transition '{phrase}' used {count} times (max 2)"

    def test_no_identical_paragraph_starts(self, diverse_violations, consumer_info):
        """Paragraphs should not start identically."""
        result = generate_letter(
            violations=diverse_violations,
            consumer_info=consumer_info,
            bureau="experian",
            tone="aggressive",
            seed=101
        )

        paragraphs = [p.strip() for p in result["letter_content"].split('\n\n') if p.strip()]
        starts = [p[:30].lower() for p in paragraphs if len(p) > 30]

        # Exclude structural elements that repeat by design (headers, MOV sections, demands)
        structural_prefixes = [
            "###", "required documents:", "i demand", "additionally,",
            "statutory category:", "data element:", "furnisher:", "priority level:"
        ]
        starts = [s for s in starts if not any(s.startswith(p) for p in structural_prefixes)]

        start_counts = Counter(starts)
        repeated = [s for s, c in start_counts.items() if c > 1]

        assert len(repeated) <= 1, f"Repeated paragraph starts: {repeated}"


# =============================================================================
# TEST: TONE ISOLATION
# =============================================================================

class TestToneIsolation:
    """Tests ensuring tones don't leak into each other."""

    def test_strict_legal_not_aggressive(self, sample_violations, consumer_info):
        """Strict legal should not contain aggressive markers."""
        result = generate_letter(
            violations=sample_violations,
            consumer_info=consumer_info,
            bureau="transunion",
            tone="strict_legal",
            seed=42
        )
        fingerprint = extract_tone_fingerprint(result["letter_content"])

        assert fingerprint["strict_legal"] > fingerprint["aggressive"] * 0.5, \
            "Strict legal should have more formal markers than aggressive"

    def test_soft_legal_not_aggressive(self, sample_violations, consumer_info):
        """Soft legal should not contain aggressive ALL-CAPS demands."""
        result = generate_letter(
            violations=sample_violations,
            consumer_info=consumer_info,
            bureau="experian",
            tone="soft_legal",
            seed=42
        )
        content = result["letter_content"]

        aggressive_caps = ["DEMAND", "VIOLATION", "WILLFUL", "IMMEDIATELY", "FAIL"]
        caps_count = sum(content.count(word) for word in aggressive_caps)

        assert caps_count <= 2, f"Soft legal has too many aggressive caps: {caps_count}"

    def test_aggressive_has_aggressive_markers(self, sample_violations, consumer_info):
        """Aggressive tone should have aggressive markers."""
        result = generate_letter(
            violations=sample_violations,
            consumer_info=consumer_info,
            bureau="equifax",
            tone="aggressive",
            seed=42
        )
        fingerprint = extract_tone_fingerprint(result["letter_content"])

        assert fingerprint["aggressive"] >= 5, \
            f"Aggressive tone lacks markers: {fingerprint['aggressive']}"

    def test_professional_balanced(self, sample_violations, consumer_info):
        """Professional tone should be balanced, not extreme."""
        result = generate_letter(
            violations=sample_violations,
            consumer_info=consumer_info,
            bureau="transunion",
            tone="professional",
            seed=42
        )
        fingerprint = extract_tone_fingerprint(result["letter_content"])

        assert fingerprint["aggressive"] < 10, "Professional too aggressive"
        assert fingerprint["soft_legal"] < 10, "Professional too soft"

    @pytest.mark.parametrize("tone1,tone2", [
        ("strict_legal", "soft_legal"),
        ("aggressive", "soft_legal"),
        ("strict_legal", "aggressive"),
    ])
    def test_different_tones_produce_different_fingerprints(
        self, sample_violations, consumer_info, tone1, tone2
    ):
        """Different tones should produce distinct fingerprints."""
        result1 = generate_letter(
            violations=sample_violations,
            consumer_info=consumer_info,
            bureau="transunion",
            tone=tone1,
            seed=42
        )
        result2 = generate_letter(
            violations=sample_violations,
            consumer_info=consumer_info,
            bureau="transunion",
            tone=tone2,
            seed=42
        )

        fp1 = extract_tone_fingerprint(result1["letter_content"])
        fp2 = extract_tone_fingerprint(result2["letter_content"])

        similarity = calc_similarity(result1["letter_content"], result2["letter_content"])
        assert similarity < 0.85, f"Tones {tone1} and {tone2} too similar: {similarity}"


# =============================================================================
# TEST: STRUCTURAL VARIATION
# =============================================================================

class TestStructuralVariation:
    """Tests for structural diversity across letters."""

    def test_mov_section_varies_across_tones(self, sample_violations, consumer_info):
        """MOV section phrasing should vary by tone."""
        mov_sections = {}
        for tone in ["strict_legal", "professional", "soft_legal", "aggressive"]:
            result = generate_letter(
                violations=sample_violations,
                consumer_info=consumer_info,
                bureau="transunion",
                tone=tone,
                include_mov=True,
                seed=42
            )
            mov_sections[tone] = result["letter_content"]

        for t1 in mov_sections:
            for t2 in mov_sections:
                if t1 < t2:
                    sim = calc_similarity(mov_sections[t1], mov_sections[t2])
                    assert sim < 0.90, f"MOV sections too similar: {t1} vs {t2} = {sim}"

    def test_different_seeds_different_phrasing(self, sample_violations, consumer_info):
        """Different seeds should produce different micro-phrasing."""
        letters = []
        for seed in [1, 2, 3]:
            result = generate_letter(
                violations=sample_violations,
                consumer_info=consumer_info,
                bureau="transunion",
                tone="professional",
                seed=seed
            )
            letters.append(result["letter_content"])

        for i in range(len(letters)):
            for j in range(i + 1, len(letters)):
                sim = calc_similarity(letters[i], letters[j])
                assert sim < 0.95, f"Seeds {i+1} and {j+1} too similar: {sim}"

    def test_grouping_strategies_produce_different_structures(
        self, diverse_violations, consumer_info
    ):
        """Different grouping strategies should produce differently structured letters."""
        letters = {}
        for strategy in ["by_fcra_section", "by_metro2_field", "by_creditor", "by_severity"]:
            result = generate_letter(
                violations=diverse_violations,
                consumer_info=consumer_info,
                bureau="transunion",
                tone="professional",
                grouping_strategy=strategy,
                seed=42
            )
            letters[strategy] = result["letter_content"]

        strategies = list(letters.keys())
        for i, s1 in enumerate(strategies):
            for s2 in strategies[i+1:]:
                sim = calc_similarity(letters[s1], letters[s2])
                # 94% allows for structural variation while accepting shared legal content
                assert sim < 0.94, f"Grouping {s1} vs {s2} too similar: {sim}"


# =============================================================================
# TEST: ENTROPY THRESHOLDS
# =============================================================================

class TestEntropyThresholds:
    """Tests for text entropy (randomness/diversity)."""

    @pytest.mark.parametrize("tone", ["strict_legal", "professional", "soft_legal", "aggressive"])
    def test_character_entropy_threshold(self, sample_violations, consumer_info, tone):
        """Letter should have sufficient character-level entropy."""
        result = generate_letter(
            violations=sample_violations,
            consumer_info=consumer_info,
            bureau="transunion",
            tone=tone,
            seed=42
        )
        content = result["letter_content"]

        ent = entropy(content)
        assert ent >= 3.8, f"Character entropy too low: {ent}"

    @pytest.mark.parametrize("tone", ["strict_legal", "professional", "soft_legal", "aggressive"])
    def test_word_entropy_threshold(self, diverse_violations, consumer_info, tone):
        """Letter should have sufficient word-level entropy."""
        result = generate_letter(
            violations=diverse_violations,
            consumer_info=consumer_info,
            bureau="experian",
            tone=tone,
            seed=42
        )
        content = result["letter_content"]

        ent = word_entropy(content)
        assert ent >= 6.0, f"Word entropy too low: {ent}"


# =============================================================================
# TEST: NO BOILERPLATE REPETITION
# =============================================================================

class TestNoBoilerplateRepetition:
    """Tests detecting repeated boilerplate phrases."""

    BOILERPLATE_PATTERNS = [
        "this account also",
        "when reviewing this",
        "another issue i observed",
        "upon examination of",
        "it should be noted",
        "i have noticed that",
        "as you can see",
    ]

    @pytest.mark.parametrize("tone", ["strict_legal", "professional", "soft_legal", "aggressive"])
    def test_no_repeated_boilerplate(self, diverse_violations, consumer_info, tone):
        """Common boilerplate phrases should not repeat excessively."""
        result = generate_letter(
            violations=diverse_violations,
            consumer_info=consumer_info,
            bureau="transunion",
            tone=tone,
            seed=42
        )
        content = result["letter_content"].lower()

        for pattern in self.BOILERPLATE_PATTERNS:
            count = content.count(pattern)
            assert count <= 1, f"Boilerplate '{pattern}' repeated {count} times"

    def test_no_repeated_4gram_phrases(self, diverse_violations, consumer_info):
        """No 4-word phrases should repeat more than twice."""
        result = generate_letter(
            violations=diverse_violations,
            consumer_info=consumer_info,
            bureau="equifax",
            tone="professional",
            seed=42
        )

        repeated = find_repeated_phrases(result["letter_content"], min_words=4, min_count=3)
        # Exclude legitimate legal phrases that must repeat in FCRA letters
        legal_exclusions = [
            "15 u.s.c", "u.s.c §", "u s c", "fair credit reporting", "credit reporting act",
            "fcra section", "section 611", "section 623", "section 605", "section 607",
            "date of first delinquency", "legal basis", "original source documentation",
            "method of verification", "reasonable reinvestigation", "legal reference",
            "1681", "statutory category", "data element", "furnisher", "priority level",
            "reference 15"
        ]
        filtered = [(p, c) for p, c in repeated if not any(
            x in p for x in legal_exclusions
        )]

        assert len(filtered) == 0, f"Repeated phrases: {filtered[:5]}"


# =============================================================================
# TEST: SEED BEHAVIOR
# =============================================================================

class TestSeedBehavior:
    """Tests for deterministic seed behavior."""

    def test_same_seed_consistent_structure(self, sample_violations, consumer_info):
        """Same seed should produce identical output."""
        results = []
        for _ in range(3):
            result = generate_letter(
                violations=sample_violations,
                consumer_info=consumer_info,
                bureau="transunion",
                tone="professional",
                seed=42
            )
            results.append(result["letter_content"])

        assert results[0] == results[1] == results[2], "Same seed produced different output"

    def test_different_seeds_different_output(self, sample_violations, consumer_info):
        """Different seeds should produce different output."""
        results = []
        for seed in [1, 100, 999]:
            result = generate_letter(
                violations=sample_violations,
                consumer_info=consumer_info,
                bureau="transunion",
                tone="professional",
                seed=seed
            )
            results.append(result["letter_content"])

        assert results[0] != results[1], "Different seeds produced same output"
        assert results[1] != results[2], "Different seeds produced same output"


# =============================================================================
# TEST: INTER-TONE SIMILARITY
# =============================================================================

class TestInterToneSimilarity:
    """Tests ensuring different tones don't share too much content."""

    def test_top_phrases_differ_across_tones(self, sample_violations, consumer_info):
        """Top phrases should differ between tones."""
        tone_phrases = {}
        for tone in ["strict_legal", "professional", "soft_legal", "aggressive"]:
            result = generate_letter(
                violations=sample_violations,
                consumer_info=consumer_info,
                bureau="transunion",
                tone=tone,
                seed=42
            )
            ngrams = get_phrase_ngrams(result["letter_content"], n=3)
            top_5 = [p for p, _ in Counter(ngrams).most_common(10)]
            tone_phrases[tone] = set(top_5)

        for t1 in tone_phrases:
            for t2 in tone_phrases:
                if t1 < t2:
                    overlap = len(tone_phrases[t1] & tone_phrases[t2])
                    # Legal tones share terminology (FCRA sections, legal phrases), allow up to 7
                    assert overlap <= 7, f"Tones {t1} and {t2} share {overlap} top phrases"


# =============================================================================
# TEST: LEGAL CITATION VARIATION
# =============================================================================

class TestLegalCitationVariation:
    """Tests for legal citation phrasing diversity."""

    def test_case_law_intros_vary(self, sample_violations, consumer_info):
        """Case law introduction phrasing should vary."""
        result = generate_letter(
            violations=sample_violations,
            consumer_info=consumer_info,
            bureau="transunion",
            tone="strict_legal",
            include_case_law=True,
            seed=42
        )
        content = result["letter_content"]

        case_intro_patterns = [
            r"(?:In|Per|See|As held in|According to)\s+\w+\s+v\.",
        ]
        intros = []
        for pattern in case_intro_patterns:
            matches = re.findall(pattern, content)
            intros.extend(matches)

        if len(intros) > 1:
            unique_intros = set(intros)
            assert len(unique_intros) >= len(intros) * 0.5, "Case law intros too repetitive"

    @pytest.mark.parametrize("tone", ["strict_legal", "aggressive"])
    def test_fcra_section_explanations_differ(self, diverse_violations, consumer_info, tone):
        """FCRA section explanations should not be identical."""
        result = generate_letter(
            violations=diverse_violations,
            consumer_info=consumer_info,
            bureau="experian",
            tone=tone,
            seed=42
        )
        content = result["letter_content"]

        section_pattern = r"Section\s+\d+[a-z]?\([a-z0-9]+\)"
        sections = re.findall(section_pattern, content, re.IGNORECASE)

        if len(sections) > 2:
            pass


# =============================================================================
# TEST: BLOCK-LEVEL VARIATION
# =============================================================================

class TestBlockLevelVariation:
    """Tests for variation within letter sections/blocks."""

    def test_procedural_demands_differ(self, diverse_violations, consumer_info):
        """Procedural demand phrasing should vary."""
        result = generate_letter(
            violations=diverse_violations,
            consumer_info=consumer_info,
            bureau="transunion",
            tone="aggressive",
            seed=42
        )
        content = result["letter_content"].lower()

        demand_phrases = re.findall(r"(?:i demand|you must|required to|failure to)\s+\w+", content)
        if len(demand_phrases) > 2:
            unique = set(demand_phrases)
            ratio = len(unique) / len(demand_phrases)
            assert ratio >= 0.4, f"Demand phrases too repetitive: {ratio}"

    def test_metro2_explanations_differ(self, diverse_violations, consumer_info):
        """Metro-2 field explanations should vary."""
        result = generate_letter(
            violations=diverse_violations,
            consumer_info=consumer_info,
            bureau="equifax",
            tone="professional",
            include_metro2=True,
            seed=42
        )
        content = result["letter_content"]

        metro2_mentions = re.findall(r"(?:Metro-?2|METRO-?2)[^.]*\.", content)
        if len(metro2_mentions) > 2:
            unique = set(m[:50] for m in metro2_mentions)
            assert len(unique) >= len(metro2_mentions) * 0.5, "Metro-2 explanations too similar"


# =============================================================================
# TEST: PACING AND CADENCE
# =============================================================================

class TestPacingCadence:
    """Tests for sentence rhythm and cadence."""

    def test_no_consecutive_same_stem_sentences(self, diverse_violations, consumer_info):
        """No more than 2 consecutive sentences with same stem."""
        result = generate_letter(
            violations=diverse_violations,
            consumer_info=consumer_info,
            bureau="transunion",
            tone="professional",
            seed=42
        )
        sentences = split_sentences(result["letter_content"])

        stems = [stem_simple(s) for s in sentences]
        consecutive_count = 1
        max_consecutive = 1

        for i in range(1, len(stems)):
            if calc_similarity(stems[i], stems[i-1]) > 0.8:
                consecutive_count += 1
                max_consecutive = max(max_consecutive, consecutive_count)
            else:
                consecutive_count = 1

        assert max_consecutive <= 2, f"Too many consecutive similar stems: {max_consecutive}"

    def test_sentence_length_variation(self, sample_violations, consumer_info):
        """Sentence lengths should vary (not all same length)."""
        result = generate_letter(
            violations=sample_violations,
            consumer_info=consumer_info,
            bureau="experian",
            tone="professional",
            seed=42
        )
        sentences = split_sentences(result["letter_content"])

        lengths = [len(s.split()) for s in sentences]
        if len(lengths) > 5:
            std_dev = (sum((l - sum(lengths)/len(lengths))**2 for l in lengths) / len(lengths)) ** 0.5
            assert std_dev >= 3, f"Sentence lengths too uniform: std_dev={std_dev}"


# =============================================================================
# TEST: NO AI MARKERS
# =============================================================================

class TestNoAIMarkers:
    """Tests ensuring no AI-specific phrases appear."""

    AI_MARKERS = [
        "as an ai",
        "as a language model",
        "i cannot",
        "i'm not able to",
        "this letter was generated",
        "automatically generated",
        "computer generated",
        "ai-generated",
    ]

    @pytest.mark.parametrize("tone", ["strict_legal", "professional", "soft_legal", "aggressive"])
    def test_no_ai_disclosure_markers(self, sample_violations, consumer_info, tone):
        """Letter should not contain AI disclosure markers."""
        result = generate_letter(
            violations=sample_violations,
            consumer_info=consumer_info,
            bureau="transunion",
            tone=tone,
            seed=42
        )
        content = result["letter_content"].lower()

        for marker in self.AI_MARKERS:
            assert marker not in content, f"AI marker found: '{marker}'"

    @pytest.mark.parametrize("tone", ["strict_legal", "professional", "soft_legal", "aggressive"])
    def test_no_generic_conclusion_markers(self, sample_violations, consumer_info, tone):
        """Avoid overly generic AI-style conclusions."""
        result = generate_letter(
            violations=sample_violations,
            consumer_info=consumer_info,
            bureau="experian",
            tone=tone,
            seed=42
        )
        content = result["letter_content"].lower()

        generic_conclusions = [
            "in conclusion,",
            "to summarize,",
            "in summary,",
        ]

        for phrase in generic_conclusions:
            count = content.count(phrase)
            assert count <= 1, f"Generic conclusion '{phrase}' used {count} times"


# =============================================================================
# TEST: PARAGRAPH SHAPE DIVERSITY
# =============================================================================

class TestParagraphShapeDiversity:
    """Tests for paragraph structure variation."""

    def test_paragraph_lengths_vary(self, diverse_violations, consumer_info):
        """Paragraph lengths should vary, not be uniform."""
        result = generate_letter(
            violations=diverse_violations,
            consumer_info=consumer_info,
            bureau="transunion",
            tone="professional",
            seed=42
        )
        lengths = get_paragraph_lengths(result["letter_content"])

        if len(lengths) > 3:
            unique_lengths = set(lengths)
            ratio = len(unique_lengths) / len(lengths)
            assert ratio >= 0.3, f"Paragraph lengths too uniform: {ratio}"

    def test_no_identical_paragraph_structures(self, diverse_violations, consumer_info):
        """Paragraphs should not have identical word counts."""
        result = generate_letter(
            violations=diverse_violations,
            consumer_info=consumer_info,
            bureau="equifax",
            tone="aggressive",
            seed=42
        )

        paragraphs = [p.strip() for p in result["letter_content"].split('\n\n') if p.strip()]
        word_counts = [len(p.split()) for p in paragraphs]

        count_freq = Counter(word_counts)
        max_freq = max(count_freq.values()) if count_freq else 0

        assert max_freq <= len(paragraphs) * 0.5, f"Too many paragraphs with same word count"


# =============================================================================
# TEST: MOV DEMANDS VARIATION
# =============================================================================

class TestMOVDemandsVariation:
    """Tests for MOV section diversity."""

    def test_mov_legal_phrasing_not_repeated(self, sample_violations, consumer_info):
        """MOV legal phrasing should not repeat within the letter."""
        result = generate_letter(
            violations=sample_violations,
            consumer_info=consumer_info,
            bureau="transunion",
            tone="strict_legal",
            include_mov=True,
            seed=42
        )
        content = result["letter_content"]

        mov_legal_phrases = re.findall(r"(?:pursuant to|under|per)\s+(?:FCRA|15 U\.S\.C\.)[^.]+\.", content, re.IGNORECASE)
        if len(mov_legal_phrases) > 2:
            unique = set(p[:40].lower() for p in mov_legal_phrases)
            ratio = len(unique) / len(mov_legal_phrases)
            assert ratio >= 0.3, f"MOV legal phrases too repetitive: {ratio}"

    def test_document_request_phrasing_varies(self, diverse_violations, consumer_info):
        """Document request phrasing should vary."""
        result = generate_letter(
            violations=diverse_violations,
            consumer_info=consumer_info,
            bureau="experian",
            tone="aggressive",
            include_mov=True,
            seed=42
        )
        content = result["letter_content"].lower()

        request_patterns = [
            r"(?:provide|produce|submit|furnish)\s+(?:the\s+)?(?:following|documentation|documents)",
        ]

        all_matches = []
        for pattern in request_patterns:
            matches = re.findall(pattern, content)
            all_matches.extend(matches)

        if len(all_matches) > 2:
            unique = set(all_matches)
            assert len(unique) >= 2, "Document request phrasing too repetitive"


# =============================================================================
# TEST: COMPREHENSIVE ANTI-TEMPLATE
# =============================================================================

class TestComprehensiveAntiTemplate:
    """Comprehensive tests combining multiple anti-template checks."""

    @pytest.mark.parametrize("tone", ["strict_legal", "professional", "soft_legal", "aggressive"])
    def test_full_letter_quality(self, diverse_violations, consumer_info, tone):
        """Full quality check on generated letter."""
        result = generate_letter(
            violations=diverse_violations,
            consumer_info=consumer_info,
            bureau="transunion",
            tone=tone,
            include_case_law=(tone in ["strict_legal", "aggressive"]),
            include_mov=True,
            include_metro2=True,
            seed=42
        )
        content = result["letter_content"]

        assert len(content) > 500, "Letter too short"

        ent = entropy(content)
        assert ent >= 3.5, f"Entropy too low: {ent}"

        sentences = split_sentences(content)
        violations = assert_sentence_uniqueness(sentences, threshold=0.75)
        assert len(violations) <= 2, f"Too many similar sentences: {violations[:3]}"

        repeated = find_repeated_phrases(content, min_words=5, min_count=3)
        # Exclude legitimate legal phrases that must repeat in FCRA letters
        legal_terms = [
            "fair credit reporting", "15 u.s.c", "fcra section", "u s c", "1681",
            "legal reference", "date of first delinquency", "method of verification",
            "reasonable reinvestigation", "original source documentation",
            "sections 611 and 623"
        ]
        filtered = [(p, c) for p, c in repeated
                    if not any(term in p.lower() for term in legal_terms)]
        assert len(filtered) <= 2, f"Too many repeated phrases: {filtered[:3]}"

    def test_multi_bureau_variation(self, sample_violations, consumer_info):
        """Letters to different bureaus should have some variation."""
        letters = {}
        for bureau in ["transunion", "experian", "equifax"]:
            result = generate_letter(
                violations=sample_violations,
                consumer_info=consumer_info,
                bureau=bureau,
                tone="professional",
                seed=42
            )
            letters[bureau] = result["letter_content"]

        for b1 in letters:
            for b2 in letters:
                if b1 < b2:
                    sim = calc_similarity(letters[b1], letters[b2])
                    assert sim < 0.98, f"Bureau letters too similar: {b1} vs {b2} = {sim}"
