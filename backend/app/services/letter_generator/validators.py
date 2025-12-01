"""
Credit Copilot - Validation and Repetition Detection

Ensures generated letters:
- Don't reuse phrases within same letter
- Track usage across consumer's letter history
- Meet bureau word count requirements
- Pass quality checks
"""
from typing import Dict, List, Set, Any, Optional
from dataclasses import dataclass, field
from collections import defaultdict
import re


# =============================================================================
# USAGE TRACKER - Prevents repetition within and across letters
# =============================================================================

@dataclass
class UsageTracker:
    """
    Tracks phrase usage to prevent repetition.

    - Within letter: Never repeat same expression
    - Across letters: Don't reuse within 10 letters for same consumer
    """
    # Phrases used in current letter
    current_letter: Set[str] = field(default_factory=set)

    # History per consumer (consumer_id -> list of last 10 letter phrases)
    consumer_history: Dict[str, List[Set[str]]] = field(default_factory=lambda: defaultdict(list))

    # Maximum letters to track per consumer
    max_history: int = 10

    def is_available(self, phrase: str, consumer_id: Optional[str] = None) -> bool:
        """Check if a phrase can be used (not recently used)."""
        # Check current letter
        if phrase in self.current_letter:
            return False

        # Check consumer history if provided
        if consumer_id and consumer_id in self.consumer_history:
            for past_letter_phrases in self.consumer_history[consumer_id]:
                if phrase in past_letter_phrases:
                    return False

        return True

    def mark_used(self, phrase: str):
        """Mark a phrase as used in current letter."""
        self.current_letter.add(phrase)

    def finalize_letter(self, consumer_id: Optional[str] = None):
        """Complete current letter and add to consumer history."""
        if consumer_id and self.current_letter:
            history = self.consumer_history[consumer_id]
            history.append(self.current_letter.copy())

            # Keep only last N letters
            while len(history) > self.max_history:
                history.pop(0)

        # Reset for next letter
        self.current_letter = set()

    def get_available_from_list(
        self,
        options: List[str],
        consumer_id: Optional[str] = None
    ) -> List[str]:
        """Filter a list to only available options."""
        return [opt for opt in options if self.is_available(opt, consumer_id)]


# =============================================================================
# LETTER VALIDATORS
# =============================================================================

class LetterValidator:
    """Validates generated letter content."""

    # Template markers to avoid (would trigger eOscar filtering)
    TEMPLATE_MARKERS = [
        r'^Item\s*\d+[:\.]',           # "Item 1:", "Item 2."
        r'^Dispute\s*#?\d+',            # "Dispute #1"
        r'^\d+\.\s+',                   # "1. ", "2. " at line start
        r'^[•●○]\s+',                   # Bullet points
        r'^[-*]\s+',                    # Dash/asterisk bullets
        r'\[ACCOUNT\]',                 # Placeholder markers
        r'\[NAME\]',
        r'\[DATE\]',
        r'\{.*?\}',                     # Template variables
        r'<<.*?>>',                     # Template blocks
        r'pursuant to section \d+',     # Legal template language
        r'under the provisions of',
        r'I hereby demand',
        r'be advised that',
        r'please be informed',
    ]

    # FCRA citation patterns
    FCRA_PATTERNS = [
        r'FCRA',
        r'Fair Credit Reporting Act',
        r'15 U\.?S\.?C\.?\s*§?\s*168[1-9]',
        r'Section 611',
        r'Section 609',
    ]

    def __init__(self):
        self.template_regex = [re.compile(p, re.IGNORECASE | re.MULTILINE)
                               for p in self.TEMPLATE_MARKERS]
        self.fcra_regex = [re.compile(p, re.IGNORECASE)
                          for p in self.FCRA_PATTERNS]

    def check_template_markers(self, content: str) -> List[str]:
        """Check for template-like patterns that could trigger filtering."""
        issues = []

        for pattern in self.template_regex:
            matches = pattern.findall(content)
            if matches:
                issues.append(f"Template marker detected: {matches[0][:30]}")

        return issues

    def count_fcra_citations(self, content: str) -> int:
        """Count FCRA citations in content."""
        count = 0
        for pattern in self.fcra_regex:
            count += len(pattern.findall(content))
        return count

    def check_fcra_usage(self, content: str, max_citations: int = 1) -> List[str]:
        """Verify FCRA citations don't exceed limit."""
        issues = []
        count = self.count_fcra_citations(content)

        if count > max_citations:
            issues.append(f"Too many FCRA citations: {count} (max {max_citations})")

        return issues

    def check_word_count(
        self,
        content: str,
        min_words: int = 250,
        max_words: int = 450
    ) -> List[str]:
        """Verify word count is within acceptable range."""
        issues = []
        words = len(content.split())

        if words < min_words:
            issues.append(f"Letter too short: {words} words (min {min_words})")
        elif words > max_words:
            issues.append(f"Letter too long: {words} words (max {max_words})")

        return issues

    def check_sentence_variety(self, content: str) -> List[str]:
        """Check for varied sentence structure."""
        issues = []

        # Split into sentences
        sentences = re.split(r'[.!?]+', content)
        sentences = [s.strip() for s in sentences if s.strip()]

        if len(sentences) < 3:
            return issues  # Not enough sentences to analyze

        # Check sentence length variety
        lengths = [len(s.split()) for s in sentences]
        avg_length = sum(lengths) / len(lengths)

        # Calculate variance
        variance = sum((l - avg_length) ** 2 for l in lengths) / len(lengths)

        if variance < 10:  # Low variance = too similar lengths
            issues.append("Sentence lengths are too uniform - vary structure more")

        # Check for repeated sentence starters
        starters = [s.split()[0].lower() if s.split() else '' for s in sentences]
        starter_counts = defaultdict(int)
        for starter in starters:
            starter_counts[starter] += 1

        for starter, count in starter_counts.items():
            if count > 2 and len(sentences) > 4:
                issues.append(f"Repeated sentence starter '{starter}' ({count} times)")

        return issues

    def check_repetition(self, content: str) -> List[str]:
        """Check for repeated phrases within the letter."""
        issues = []

        # Extract phrases (3-5 word sequences)
        words = content.lower().split()
        phrases = defaultdict(int)

        for n in [3, 4, 5]:
            for i in range(len(words) - n + 1):
                phrase = ' '.join(words[i:i+n])
                phrases[phrase] += 1

        # Flag phrases that appear more than once
        for phrase, count in phrases.items():
            if count > 1:
                # Filter out common phrases that are OK to repeat
                common_ok = ['on my credit', 'my credit report', 'this account',
                           'the account', 'i have', 'i am', 'to be']
                if not any(c in phrase for c in common_ok):
                    issues.append(f"Repeated phrase: '{phrase}'")

        return issues[:5]  # Limit to 5 issues

    def validate(
        self,
        content: str,
        min_words: int = 250,
        max_words: int = 450,
        max_fcra: int = 1
    ) -> Dict[str, Any]:
        """Run all validations and return results."""
        all_issues = []

        # Run checks
        all_issues.extend(self.check_template_markers(content))
        all_issues.extend(self.check_fcra_usage(content, max_fcra))
        all_issues.extend(self.check_word_count(content, min_words, max_words))
        all_issues.extend(self.check_sentence_variety(content))
        all_issues.extend(self.check_repetition(content))

        return {
            "valid": len(all_issues) == 0,
            "issues": all_issues,
            "word_count": len(content.split()),
            "fcra_count": self.count_fcra_citations(content),
            "sentence_count": len(re.split(r'[.!?]+', content)),
        }


# =============================================================================
# QUALITY SCORING
# =============================================================================

def calculate_quality_score(validation_result: Dict[str, Any]) -> float:
    """
    Calculate a quality score for the letter (0-100).
    Higher is better.
    """
    score = 100.0

    # Deduct for issues
    for issue in validation_result.get("issues", []):
        if "Template marker" in issue:
            score -= 15  # Template markers are serious
        elif "FCRA" in issue:
            score -= 10
        elif "word" in issue.lower():
            score -= 5
        elif "Repeated" in issue:
            score -= 5
        elif "sentence" in issue.lower():
            score -= 3
        else:
            score -= 2

    return max(0, score)


def calculate_variation_score(
    letter_content: str,
    previous_letters: List[str]
) -> float:
    """
    Calculate how different this letter is from previous ones (0-100).
    Higher means more unique.
    """
    if not previous_letters:
        return 100.0

    # Extract significant phrases from current letter
    current_phrases = set()
    words = letter_content.lower().split()
    for n in [4, 5, 6]:
        for i in range(len(words) - n + 1):
            current_phrases.add(' '.join(words[i:i+n]))

    # Compare against previous letters
    overlap_scores = []

    for prev_letter in previous_letters:
        prev_phrases = set()
        prev_words = prev_letter.lower().split()
        for n in [4, 5, 6]:
            for i in range(len(prev_words) - n + 1):
                prev_phrases.add(' '.join(prev_words[i:i+n]))

        if current_phrases and prev_phrases:
            overlap = len(current_phrases & prev_phrases)
            total = len(current_phrases | prev_phrases)
            similarity = overlap / total if total > 0 else 0
            overlap_scores.append(similarity)

    if not overlap_scores:
        return 100.0

    # Average similarity, convert to uniqueness score
    avg_similarity = sum(overlap_scores) / len(overlap_scores)
    return (1 - avg_similarity) * 100


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_unique_phrase(
    options: List[str],
    tracker: UsageTracker,
    rng,
    consumer_id: Optional[str] = None
) -> Optional[str]:
    """
    Get a phrase that hasn't been used recently.
    Returns None if all options are exhausted.
    """
    available = tracker.get_available_from_list(options, consumer_id)

    if not available:
        # All options used - fall back to any option
        available = options

    if not available:
        return None

    phrase = rng.choice(available)
    tracker.mark_used(phrase)
    return phrase


def ensure_minimum_variation(
    content: str,
    rng,
    min_changes: int = 3
) -> str:
    """
    Apply minor variations to ensure letter doesn't match previous versions.
    Used as a last resort if variation score is too low.
    """
    variations = [
        # Swap word pairs
        ("I am", "I'm"),
        ("I have", "I've"),
        ("I would", "I'd"),
        ("cannot", "can't"),
        ("do not", "don't"),
        ("does not", "doesn't"),
        ("will not", "won't"),
        ("is not", "isn't"),
        ("are not", "aren't"),
        ("that is", "that's"),
        # Word substitutions
        ("investigate", "look into"),
        ("inaccurate", "incorrect"),
        ("verify", "confirm"),
        ("correct", "fix"),
        ("error", "mistake"),
        ("dispute", "challenge"),
        ("request", "ask"),
        ("information", "data"),
        ("regarding", "about"),
        ("however", "but"),
        ("additionally", "also"),
        ("furthermore", "moreover"),
    ]

    changes_made = 0
    for old, new in variations:
        if changes_made >= min_changes:
            break

        if old in content and rng.random() > 0.5:
            content = content.replace(old, new, 1)
            changes_made += 1
        elif new in content and rng.random() > 0.5:
            content = content.replace(new, old, 1)
            changes_made += 1

    return content
