"""
Credit Engine 2.0 - Rendering Engine

Takes LetterPlan (SSOT #3) and renders DisputeLetter (SSOT #4).
Uses phrasebanks for template-resistant letter generation.

The variation_seed is used to select phrases deterministically,
ensuring the same seed always produces the same letter.

TEMPLATE RESISTANCE:
- Uses instance-based Random (not global state)
- No rigid structure markers (no "Item 1:", "---", etc.)
- Natural prose flow
- Randomized element ordering
"""
from __future__ import annotations
import logging
import random
from datetime import date
from typing import List

from ...models.ssot import (
    LetterPlan, DisputeLetter, LetterMetadata, Violation,
    Tone, ViolationType
)
from .phrasebanks import PHRASEBANKS

logger = logging.getLogger(__name__)


class RenderingEngine:
    """
    Render dispute letters from LetterPlan.

    Input: LetterPlan (SSOT #3)
    Output: DisputeLetter (SSOT #4)

    Uses variation_seed for deterministic phrase selection.
    Renderer CANNOT re-audit or change violation classifications.
    """

    def __init__(self, phrasebanks=None):
        """Initialize with phrasebanks."""
        self.phrasebanks = phrasebanks or PHRASEBANKS
        self.rng = None  # Instance-based random generator

    def render(self, plan: LetterPlan) -> DisputeLetter:
        """
        Render a dispute letter from a LetterPlan.

        Args:
            plan: LetterPlan (SSOT #3) from strategy selector

        Returns:
            DisputeLetter (SSOT #4) - final output
        """
        logger.info(f"Rendering letter with seed={plan.variation_seed}")

        # Use instance-based Random (not global state) for determinism
        self.rng = random.Random(plan.variation_seed)

        # Build letter content
        content_parts = []

        # 1. Header (consumer info and date)
        content_parts.append(self._render_header(plan))

        # 2. Bureau address
        content_parts.append(self._render_bureau_address(plan))

        # 3. Subject line
        content_parts.append(self._render_subject_line())

        # 4. Opening paragraph
        content_parts.append(self._render_opening(plan.tone))

        # 5. Consumer identification
        content_parts.append(self._render_consumer_id(plan))

        # 6. Disputed items
        content_parts.append(self._render_disputed_items(plan))

        # 7. Closing
        content_parts.append(self._render_closing(plan.tone))

        # 8. Signature block
        content_parts.append(self._render_signature(plan))

        # Combine all parts
        content = "\n\n".join(filter(None, content_parts))

        # Calculate word count
        word_count = len(content.split())

        # Collect all violation types cited
        violations_cited = []
        for violations in plan.grouped_violations.values():
            for v in violations:
                if v.violation_type not in violations_cited:
                    violations_cited.append(v.violation_type)

        # Collect all account IDs disputed
        accounts_disputed = []
        for violations in plan.grouped_violations.values():
            for v in violations:
                if v.account_id not in accounts_disputed:
                    accounts_disputed.append(v.account_id)

        # Build DisputeLetter
        letter = DisputeLetter(
            content=content,
            bureau=plan.bureau,
            accounts_disputed=accounts_disputed,
            violations_cited=violations_cited,
            metadata=LetterMetadata(
                variation_seed_used=plan.variation_seed,
                tone_used=plan.tone,
                word_count=word_count
            )
        )

        logger.info(f"Rendered letter: {word_count} words, {len(violations_cited)} violation types")
        return letter

    def _render_header(self, plan: LetterPlan) -> str:
        """Render the letter header with consumer info and date."""
        consumer = plan.consumer
        today = date.today().strftime("%B %d, %Y")

        return f"""{consumer.full_name}
{consumer.address}
{consumer.city}, {consumer.state} {consumer.zip_code}

{today}"""

    def _render_bureau_address(self, plan: LetterPlan) -> str:
        """Render the bureau address."""
        return plan.bureau_address

    def _render_subject_line(self) -> str:
        """Render the subject line."""
        subjects = [
            "RE: Formal Dispute of Credit Report Items",
            "RE: Request for Investigation - Credit Report Errors",
            "RE: Dispute of Inaccurate Information",
            "Subject: Credit Report Dispute",
            "RE: Credit Report Inaccuracies",
        ]
        return self.rng.choice(subjects)

    def _render_opening(self, tone: Tone) -> str:
        """Render the opening paragraph based on tone."""
        tone_key = tone.value
        openings = self.phrasebanks["openings"].get(tone_key, self.phrasebanks["openings"]["formal"])
        return self.rng.choice(openings)

    def _render_consumer_id(self, plan: LetterPlan) -> str:
        """Render consumer identification section."""
        consumer = plan.consumer

        id_phrases = [
            "For identification purposes:",
            "Please use the following information to locate my file:",
            "My identification information is as follows:",
            "To identify my credit file:",
        ]

        parts = [self.rng.choice(id_phrases)]
        parts.append(f"Name: {consumer.full_name}")
        parts.append(f"Address: {consumer.address}, {consumer.city}, {consumer.state} {consumer.zip_code}")

        if consumer.ssn_last4:
            parts.append(f"SSN (last 4): XXX-XX-{consumer.ssn_last4}")

        if consumer.date_of_birth:
            parts.append(f"Date of Birth: {consumer.date_of_birth.strftime('%m/%d/%Y')}")

        return "\n".join(parts)

    def _render_disputed_items(self, plan: LetterPlan) -> str:
        """Render the disputed items section using natural prose (NO template markers)."""
        parts = []

        intro_phrases = [
            "I am disputing the following items:",
            "The items I am disputing are listed below:",
            "Please investigate the following disputed items:",
            "I dispute the following information as inaccurate:",
            "The following accounts contain errors that require investigation:",
        ]
        parts.append(self.rng.choice(intro_phrases))

        # Transition phrases for natural flow (NO numbered lists)
        transitions = [
            "Regarding",
            "With respect to",
            "Concerning",
            "As for",
            "Looking at",
        ]

        # Flatten all violations for natural rendering
        all_violations = []
        for group_key, violations in plan.grouped_violations.items():
            all_violations.extend(violations)

        # Render each violation with natural transitions (NO "Item 1:", "---", etc.)
        for i, v in enumerate(all_violations):
            if i > 0:
                parts.append("")  # Paragraph break
                transition = self.rng.choice(transitions)
                parts.append(f"{transition} the account with {v.creditor_name}:")
            parts.append(self._render_single_violation(v))

        return "\n".join(parts)

    def _render_single_violation(self, violation: Violation) -> str:
        """Render a single violation in natural prose (NO rigid structure)."""
        parts = []

        # Build natural sentence about the account
        account_refs = [
            f"The account with {violation.creditor_name}",
            f"My {violation.creditor_name} account",
            f"This {violation.creditor_name} tradeline",
        ]
        if violation.account_number_masked:
            account_refs.append(f"Account {violation.account_number_masked} ({violation.creditor_name})")

        account_ref = self.rng.choice(account_refs)

        # Add specific violation phrase if available
        violation_key = violation.violation_type.value
        if violation_key in self.phrasebanks["violations"]:
            phrases = self.phrasebanks["violations"][violation_key]
            violation_phrase = self.rng.choice(phrases)
            parts.append(f"{account_ref}: {violation_phrase}")
        else:
            parts.append(f"{account_ref}: {violation.description}")

        # Randomly include supporting details (varies the structure)
        include_fcra = self.rng.random() > 0.3
        include_metro = self.rng.random() > 0.5
        include_expected = self.rng.random() > 0.4

        # FCRA reference (varied inclusion)
        if include_fcra and violation.fcra_section:
            fcra_key = violation.fcra_section
            if fcra_key in self.phrasebanks["fcra_references"]:
                refs = self.phrasebanks["fcra_references"][fcra_key]
                parts.append(self.rng.choice(refs))
            else:
                parts.append(f"This violates FCRA §{violation.fcra_section}.")

        # Metro 2 field reference (varied inclusion)
        if include_metro and violation.metro2_field:
            metro_phrases = [
                f"This relates to Metro 2 Field {violation.metro2_field}.",
                f"The error is in Metro 2 Field {violation.metro2_field}.",
            ]
            parts.append(self.rng.choice(metro_phrases))

        # Expected vs Actual (varied inclusion and format)
        if include_expected and violation.expected_value and violation.actual_value:
            comparison_phrases = [
                f"It should show {violation.expected_value}, but instead shows {violation.actual_value}.",
                f"The expected value is {violation.expected_value}, not {violation.actual_value}.",
            ]
            parts.append(self.rng.choice(comparison_phrases))

        # Requested action (varied phrasing)
        action_phrases = [
            "Please investigate and correct this error.",
            "This item must be corrected or deleted.",
            "Please verify this information with the furnisher.",
            "I request that this inaccuracy be investigated and resolved.",
            "This requires immediate correction.",
        ]
        parts.append(self.rng.choice(action_phrases))

        return " ".join(parts)

    def _render_closing(self, tone: Tone) -> str:
        """Render the closing paragraph."""
        tone_key = tone.value
        closings = self.phrasebanks["closings"].get(tone_key, self.phrasebanks["closings"]["formal"])
        return self.rng.choice(closings)

    def _render_signature(self, plan: LetterPlan) -> str:
        """Render the signature block."""
        consumer = plan.consumer

        signature_phrases = [
            "Sincerely,",
            "Respectfully,",
            "Thank you for your attention to this matter,",
            "Regards,",
        ]

        return f"""{self.rng.choice(signature_phrases)}


_______________________
{consumer.full_name}"""


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

def render_letter(plan: LetterPlan) -> DisputeLetter:
    """
    Factory function to render a dispute letter.

    Args:
        plan: LetterPlan (SSOT #3)

    Returns:
        DisputeLetter (SSOT #4) - the final output
    """
    engine = RenderingEngine()
    return engine.render(plan)
