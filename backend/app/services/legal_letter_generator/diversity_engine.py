"""
Diversity Engine - Main orchestration engine for letter variation.
Combines entropy control, mutation engine, phrase pools, and paragraph shuffling.
"""
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import random
import hashlib
import re

from .entropy import EntropyController, EntropyLevel, EntropyConfig, create_entropy_controller
from .mutation import MutationEngine, create_mutation_engine
from .phrase_pools import (
    PhrasePoolManager,
    get_pool,
    get_transition,
    get_template,
    LEGAL_PHRASE_POOLS,
    CIVIL_PHRASE_POOLS,
    TRANSITION_POOLS,
    TEMPLATE_POOLS,
)


class MutationStrength(str, Enum):
    """Mutation strength levels."""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    MAXIMUM = "maximum"


@dataclass
class DiversityConfig:
    """Configuration for diversity engine."""
    entropy_level: EntropyLevel = EntropyLevel.MEDIUM
    mutation_strength: MutationStrength = MutationStrength.MEDIUM
    domain: str = "legal"
    seed: Optional[int] = None
    enable_shuffling: bool = True
    enable_mutations: bool = True
    enable_phrase_variation: bool = True
    preserve_critical_order: bool = True  # Keep demands after violations


class ParagraphShuffler:
    """
    Controlled paragraph shuffling with structural constraints.
    Maintains logical flow while introducing variation.
    """

    # Paragraph types that have ordering constraints
    ORDERED_TYPES = {
        "intro": 0,           # Must be first
        "context": 1,         # After intro
        "violations": 2,      # After context
        "demands": 3,         # After violations
        "closure": 4,         # Must be last
    }

    # Paragraphs within these groups can be shuffled
    SHUFFLEABLE_GROUPS = {
        "violations",         # Individual violation items can be reordered
        "demands",            # Demand items can be reordered
        "context",            # Context paragraphs can be reordered
    }

    def __init__(self, entropy_controller: EntropyController):
        self.entropy = entropy_controller

    def classify_paragraph(self, paragraph: str, index: int, total: int) -> str:
        """Classify a paragraph into a structural type."""
        lower = paragraph.lower()

        # First paragraph is always intro
        if index == 0:
            return "intro"

        # Last paragraph is always closure
        if index == total - 1:
            return "closure"

        # Check for violation indicators
        violation_patterns = [
            "violat", "inaccurat", "incorrect", "false", "error",
            "disputed", "wrong", "misleading", "not mine"
        ]
        if any(p in lower for p in violation_patterns):
            return "violations"

        # Check for demand indicators
        demand_patterns = [
            "demand", "require", "request", "must", "shall",
            "delete", "remove", "correct", "investigate"
        ]
        if any(p in lower for p in demand_patterns):
            return "demands"

        return "context"

    def shuffle_paragraphs(
        self,
        paragraphs: List[str],
        preserve_structure: bool = True
    ) -> List[str]:
        """
        Shuffle paragraphs while maintaining structural integrity.

        Args:
            paragraphs: List of paragraph strings
            preserve_structure: If True, maintain intro/violations/demands/closure order

        Returns:
            Shuffled paragraph list
        """
        if not paragraphs or len(paragraphs) <= 2:
            return paragraphs

        if not preserve_structure:
            # Full shuffle (except first and last)
            result = [paragraphs[0]]
            middle = paragraphs[1:-1]
            self.entropy.shuffle_list(middle)
            result.extend(middle)
            result.append(paragraphs[-1])
            return result

        # Classify paragraphs
        classified: Dict[str, List[Tuple[int, str]]] = {
            "intro": [],
            "context": [],
            "violations": [],
            "demands": [],
            "closure": [],
        }

        for i, para in enumerate(paragraphs):
            ptype = self.classify_paragraph(para, i, len(paragraphs))
            classified[ptype].append((i, para))

        # Shuffle within shuffleable groups
        for group in self.SHUFFLEABLE_GROUPS:
            if len(classified[group]) > 1:
                items = [item[1] for item in classified[group]]
                self.entropy.shuffle_list(items)
                classified[group] = [(0, item) for item in items]

        # Reconstruct in correct order
        result = []
        for ptype in ["intro", "context", "violations", "demands", "closure"]:
            for _, para in classified[ptype]:
                result.append(para)

        return result

    def shuffle_within_paragraph(self, paragraph: str) -> str:
        """
        Shuffle sentences within a paragraph while maintaining coherence.
        Only shuffles middle sentences, keeping first and last in place.
        """
        sentences = re.split(r'(?<=[.!?])\s+', paragraph.strip())

        if len(sentences) <= 2:
            return paragraph

        # Keep first and last, shuffle middle
        result = [sentences[0]]
        middle = sentences[1:-1]
        self.entropy.shuffle_list(middle)
        result.extend(middle)
        result.append(sentences[-1])

        return ' '.join(result)


class TemplateResolver:
    """Resolves templates with placeholder substitution."""

    def __init__(self, pool_manager: PhrasePoolManager, entropy: EntropyController):
        self.pool_manager = pool_manager
        self.entropy = entropy

    def resolve_template(
        self,
        template: str,
        data: Dict[str, Any],
        fallbacks: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Resolve a template by substituting placeholders with data.

        Args:
            template: Template string with {placeholders}
            data: Dictionary of values to substitute
            fallbacks: Default values for missing keys

        Returns:
            Resolved template string
        """
        fallbacks = fallbacks or {}
        result = template

        # Find all placeholders
        placeholders = re.findall(r'\{(\w+)\}', template)

        for placeholder in placeholders:
            value = data.get(placeholder, fallbacks.get(placeholder, f"[{placeholder}]"))
            result = result.replace(f"{{{placeholder}}}", str(value))

        return result

    def get_random_template(
        self,
        category: str,
        data: Dict[str, Any],
        fallbacks: Optional[Dict[str, str]] = None
    ) -> str:
        """Get a random template from a category and resolve it."""
        template = self.pool_manager.get_template(
            category,
            self.entropy.get_random_index(100)
        )
        if not template:
            return ""
        return self.resolve_template(template, data, fallbacks)


class DiversityEngine:
    """
    Main diversity engine orchestrating all variation systems.

    Provides:
    - Entropy-controlled randomization
    - Sentence-level mutations
    - Phrase pool variation
    - Paragraph shuffling
    - Template resolution
    - Domain isolation (legal vs civil)
    """

    def __init__(self, config: Optional[DiversityConfig] = None):
        """Initialize diversity engine with configuration."""
        self.config = config or DiversityConfig()

        # Initialize entropy controller with mutation strength
        mutation_strength_value = self._get_mutation_strength_value()
        self.entropy = create_entropy_controller(
            entropy_level=self.config.entropy_level,
            mutation_strength=mutation_strength_value,
            seed=self.config.seed if self.config.seed else 0
        )

        # Initialize mutation engine using the entropy controller
        self.mutation = create_mutation_engine(
            domain=self.config.domain,
            entropy=self.entropy
        )

        # Initialize phrase pool manager
        self.pool_manager = PhrasePoolManager(self.config.domain)

        # Initialize paragraph shuffler
        self.shuffler = ParagraphShuffler(self.entropy)

        # Initialize template resolver
        self.template_resolver = TemplateResolver(self.pool_manager, self.entropy)

    def _get_mutation_strength_value(self) -> int:
        """Convert mutation strength enum to numeric value (1-10 scale)."""
        values = {
            MutationStrength.NONE: 1,
            MutationStrength.LOW: 3,
            MutationStrength.MEDIUM: 5,
            MutationStrength.HIGH: 7,
            MutationStrength.MAXIMUM: 10,
        }
        return values.get(self.config.mutation_strength, 5)

    def get_phrase(self, category: str) -> str:
        """Get a varied phrase from a category."""
        if not self.config.enable_phrase_variation:
            pool = self.pool_manager.pools.get(category, [])
            return pool[0] if pool else ""

        index = self.entropy.get_random_index(self.pool_manager.pool_size(category))
        return self.pool_manager.get_phrase(category, index)

    def get_multiple_phrases(self, category: str, count: int) -> List[str]:
        """Get multiple unique phrases from a category."""
        pool_size = self.pool_manager.pool_size(category)
        if pool_size == 0:
            return []

        if count >= pool_size:
            # Return all available phrases shuffled
            phrases = self.pool_manager.get_phrases(category, pool_size)
            if self.config.enable_phrase_variation:
                self.entropy.shuffle_list(phrases)
            return phrases

        # Get unique random phrases
        indices = set()
        while len(indices) < count:
            indices.add(self.entropy.get_random_index(pool_size))

        return [self.pool_manager.get_phrase(category, idx) for idx in indices]

    def get_transition(self, category: str) -> str:
        """Get a transition phrase."""
        pool_size = self.pool_manager.transition_size(category)
        if pool_size == 0:
            return ""
        index = self.entropy.get_random_index(pool_size)
        return self.pool_manager.get_transition(category, index)

    def get_template(self, category: str, data: Dict[str, Any]) -> str:
        """Get a resolved template."""
        return self.template_resolver.get_random_template(category, data)

    def mutate_text(self, text: str) -> str:
        """Apply mutations to text."""
        if not self.config.enable_mutations:
            return text
        result = self.mutation.mutate(text)
        return result.text

    def mutate_sentence(self, sentence: str) -> str:
        """Apply all mutation types to a sentence."""
        if not self.config.enable_mutations:
            return sentence
        result = self.mutation.mutate(sentence)
        return result.text

    def shuffle_paragraphs(
        self,
        paragraphs: List[str],
        preserve_structure: bool = True
    ) -> List[str]:
        """Shuffle paragraphs with optional structure preservation."""
        if not self.config.enable_shuffling:
            return paragraphs
        return self.shuffler.shuffle_paragraphs(
            paragraphs,
            preserve_structure and self.config.preserve_critical_order
        )

    def diversify_letter(
        self,
        sections: Dict[str, str],
        violations: List[Dict[str, Any]],
        demands: List[str]
    ) -> Dict[str, str]:
        """
        Apply full diversification to a letter.

        Args:
            sections: Dictionary of section name to content
            violations: List of violation data
            demands: List of demand strings

        Returns:
            Diversified sections dictionary
        """
        result = {}

        for section_name, content in sections.items():
            # Apply phrase variation
            if self.config.enable_phrase_variation:
                content = self._apply_phrase_variation(content, section_name)

            # Apply mutations
            if self.config.enable_mutations:
                content = self.mutate_text(content)

            result[section_name] = content

        # Shuffle violations if present
        if violations and self.config.enable_shuffling:
            self.entropy.shuffle_list(violations)

        # Shuffle demands if present
        if demands and self.config.enable_shuffling:
            self.entropy.shuffle_list(demands)

        return result

    def _apply_phrase_variation(self, content: str, section_type: str) -> str:
        """Apply phrase variation based on section type."""
        # Map section types to phrase categories
        category_map = {
            "intro": "dispute_intro",
            "opening": "dispute_intro",
            "violations": "demand_verification" if self.config.domain == "legal" else "request_verification",
            "demands": "deletion_demand" if self.config.domain == "legal" else "deletion_request",
            "closing": "closure",
            "closure": "closure",
        }

        category = category_map.get(section_type)
        if not category:
            return content

        # Get a varied phrase to potentially replace generic openings
        varied_phrase = self.get_phrase(category)
        if varied_phrase:
            # Only replace if content starts with a generic phrase
            generic_patterns = [
                r'^I am writing to',
                r'^This letter',
                r'^I hereby',
                r'^Pursuant to',
                r'^I\'m writing',
                r'^I wanted to',
            ]
            for pattern in generic_patterns:
                if re.match(pattern, content, re.IGNORECASE):
                    # Replace first sentence with varied phrase
                    sentences = re.split(r'(?<=[.!?])\s+', content, maxsplit=1)
                    if len(sentences) > 1:
                        content = varied_phrase + ". " + sentences[1]
                    else:
                        content = varied_phrase + "."
                    break

        return content

    def generate_unique_id(self, base_content: str) -> str:
        """Generate a unique ID for tracking letter variations."""
        # Combine base content with entropy state
        combined = f"{base_content}:{self.entropy.random.random()}"
        return hashlib.sha256(combined.encode()).hexdigest()[:16]

    def get_variation_stats(self) -> Dict[str, Any]:
        """Get statistics about available variations."""
        stats = {
            "domain": self.config.domain,
            "entropy_level": self.config.entropy_level.value,
            "mutation_strength": self.config.mutation_strength.value,
            "phrase_pools": {},
            "transition_pools": {},
            "total_phrases": 0,
            "total_transitions": 0,
        }

        for category in self.pool_manager.list_categories():
            size = self.pool_manager.pool_size(category)
            stats["phrase_pools"][category] = size
            stats["total_phrases"] += size

        for category in self.pool_manager.list_transition_categories():
            size = self.pool_manager.transition_size(category)
            stats["transition_pools"][category] = size
            stats["total_transitions"] += size

        return stats


def create_diversity_engine(
    entropy_level: str = "medium",
    mutation_strength: str = "medium",
    domain: str = "legal",
    seed: Optional[int] = None
) -> DiversityEngine:
    """
    Factory function to create a diversity engine.

    Args:
        entropy_level: One of "low", "medium", "high", "maximum"
        mutation_strength: One of "none", "low", "medium", "high", "maximum"
        domain: Either "legal" or "civil"
        seed: Optional random seed for reproducibility

    Returns:
        Configured DiversityEngine instance
    """
    # Parse entropy level
    entropy_map = {
        "low": EntropyLevel.LOW,
        "medium": EntropyLevel.MEDIUM,
        "high": EntropyLevel.HIGH,
        "maximum": EntropyLevel.MAXIMUM,
    }
    entropy = entropy_map.get(entropy_level.lower(), EntropyLevel.MEDIUM)

    # Parse mutation strength
    mutation_map = {
        "none": MutationStrength.NONE,
        "low": MutationStrength.LOW,
        "medium": MutationStrength.MEDIUM,
        "high": MutationStrength.HIGH,
        "maximum": MutationStrength.MAXIMUM,
    }
    mutation = mutation_map.get(mutation_strength.lower(), MutationStrength.MEDIUM)

    config = DiversityConfig(
        entropy_level=entropy,
        mutation_strength=mutation,
        domain=domain,
        seed=seed,
    )

    return DiversityEngine(config)


# Convenience functions for direct use
def diversify_text(
    text: str,
    domain: str = "legal",
    entropy_level: str = "medium",
    mutation_strength: str = "medium"
) -> str:
    """Convenience function to diversify text."""
    engine = create_diversity_engine(
        entropy_level=entropy_level,
        mutation_strength=mutation_strength,
        domain=domain
    )
    return engine.mutate_text(text)


def get_varied_phrase(
    category: str,
    domain: str = "legal",
    seed: Optional[int] = None
) -> str:
    """Convenience function to get a varied phrase."""
    engine = create_diversity_engine(domain=domain, seed=seed)
    return engine.get_phrase(category)


def get_varied_transition(
    category: str,
    seed: Optional[int] = None
) -> str:
    """Convenience function to get a varied transition."""
    engine = create_diversity_engine(seed=seed)
    return engine.get_transition(category)
