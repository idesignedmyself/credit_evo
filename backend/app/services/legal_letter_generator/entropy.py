"""
Entropy Controller - Controls variation intensity across the letter generation system.
Provides deterministic randomness based on seed values with configurable entropy levels.
"""
from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
import hashlib


class EntropyLevel(Enum):
    """Entropy levels controlling variation intensity."""
    LOW = "low"           # Stable, predictable phrasing
    MEDIUM = "medium"     # Moderate mutation
    HIGH = "high"         # Significant variation
    MAXIMUM = "maximum"   # Maximum entropy for high-volume generation


@dataclass
class EntropyConfig:
    """Configuration for entropy-controlled generation."""
    level: EntropyLevel = EntropyLevel.MEDIUM
    mutation_strength: int = 5  # 1-10 scale
    seed: int = 0

    # Derived settings based on level
    @property
    def phrase_variation_factor(self) -> float:
        """How much to vary phrase selection (0.0-1.0)."""
        factors = {
            EntropyLevel.LOW: 0.2,
            EntropyLevel.MEDIUM: 0.5,
            EntropyLevel.HIGH: 0.8,
            EntropyLevel.MAXIMUM: 1.0,
        }
        return factors[self.level] * (self.mutation_strength / 10)

    @property
    def structural_variation(self) -> bool:
        """Whether to allow structural variations."""
        return self.level in (EntropyLevel.HIGH, EntropyLevel.MAXIMUM)

    @property
    def synonym_replacement_rate(self) -> float:
        """Rate of synonym replacement (0.0-1.0)."""
        rates = {
            EntropyLevel.LOW: 0.1,
            EntropyLevel.MEDIUM: 0.3,
            EntropyLevel.HIGH: 0.5,
            EntropyLevel.MAXIMUM: 0.7,
        }
        return rates[self.level]

    @property
    def clause_flip_probability(self) -> float:
        """Probability of flipping clause order."""
        probs = {
            EntropyLevel.LOW: 0.0,
            EntropyLevel.MEDIUM: 0.2,
            EntropyLevel.HIGH: 0.4,
            EntropyLevel.MAXIMUM: 0.6,
        }
        return probs[self.level]

    @property
    def filler_modification_rate(self) -> float:
        """Rate of filler word addition/removal."""
        rates = {
            EntropyLevel.LOW: 0.05,
            EntropyLevel.MEDIUM: 0.15,
            EntropyLevel.HIGH: 0.25,
            EntropyLevel.MAXIMUM: 0.35,
        }
        return rates[self.level]

    @property
    def transition_pool_depth(self) -> int:
        """How deep into transition pools to sample."""
        depths = {
            EntropyLevel.LOW: 5,
            EntropyLevel.MEDIUM: 15,
            EntropyLevel.HIGH: 30,
            EntropyLevel.MAXIMUM: 50,
        }
        return depths[self.level]


class _SeededRandom:
    """Simple seeded random number generator wrapper."""

    def __init__(self, seed: int):
        import random as _random
        self._rng = _random.Random(seed)

    def random(self) -> float:
        """Generate a random float between 0 and 1."""
        return self._rng.random()

    def randint(self, a: int, b: int) -> int:
        """Generate a random integer between a and b (inclusive)."""
        return self._rng.randint(a, b)


class EntropyController:
    """
    Controls deterministic randomness for letter generation.
    Ensures reproducibility when seeded while providing variation.
    """

    def __init__(self, config: EntropyConfig):
        self.config = config
        self._state = self._initialize_state()
        self.random = _SeededRandom(config.seed)

    def _initialize_state(self) -> int:
        """Initialize random state from seed."""
        return self.config.seed

    def _advance_state(self) -> int:
        """Advance the random state deterministically."""
        self._state = (self._state * 1103515245 + 12345) & 0x7FFFFFFF
        return self._state

    def get_index(self, pool_size: int, weight_bias: float = 0.0) -> int:
        """
        Get a deterministic index into a pool.

        Args:
            pool_size: Size of the pool to index into
            weight_bias: Bias toward beginning (negative) or end (positive) of pool

        Returns:
            Index into the pool
        """
        if pool_size <= 0:
            return 0

        raw = self._advance_state()
        normalized = (raw % 10000) / 10000.0

        # Apply entropy-based variation
        variation = self.config.phrase_variation_factor
        effective_range = int(pool_size * max(0.1, variation))

        # Apply weight bias
        if weight_bias != 0:
            normalized = max(0, min(1, normalized + weight_bias * 0.3))

        # Map to index with entropy-controlled range
        base_index = int(normalized * effective_range)
        return min(base_index, pool_size - 1)

    def get_random_index(self, pool_size: int) -> int:
        """Get a random index into a pool (alias for get_index)."""
        return self.get_index(pool_size)

    def shuffle_list(self, items: List[Any]) -> None:
        """Shuffle a list in-place using controlled randomness."""
        if len(items) <= 1:
            return
        # Fisher-Yates shuffle
        for i in range(len(items) - 1, 0, -1):
            j = self._advance_state() % (i + 1)
            items[i], items[j] = items[j], items[i]

    def should_mutate(self, mutation_type: str) -> bool:
        """
        Determine if a mutation should occur based on entropy settings.

        Args:
            mutation_type: Type of mutation (synonym, clause_flip, filler, etc.)

        Returns:
            Whether the mutation should occur
        """
        thresholds = {
            "synonym": self.config.synonym_replacement_rate,
            "clause_flip": self.config.clause_flip_probability,
            "filler": self.config.filler_modification_rate,
            "prepositional": self.config.clause_flip_probability * 0.8,
            "rhetorical": self.config.phrase_variation_factor * 0.5,
        }

        threshold = thresholds.get(mutation_type, 0.3)
        roll = (self._advance_state() % 1000) / 1000.0
        return roll < threshold

    def select_from_pool(self, pool: List[Any], count: int = 1) -> List[Any]:
        """
        Select items from a pool with entropy-controlled distribution.

        Args:
            pool: Pool to select from
            count: Number of items to select

        Returns:
            List of selected items
        """
        if not pool:
            return []

        results = []
        used_indices = set()

        for _ in range(min(count, len(pool))):
            attempts = 0
            while attempts < 100:
                idx = self.get_index(len(pool))
                if idx not in used_indices:
                    used_indices.add(idx)
                    results.append(pool[idx])
                    break
                attempts += 1
                self._advance_state()

        return results

    def shuffle_order(self, items: List[Any], preserve_first: bool = False,
                      preserve_last: bool = False) -> List[Any]:
        """
        Shuffle items with entropy-controlled intensity.

        Args:
            items: Items to shuffle
            preserve_first: Keep first item in place
            preserve_last: Keep last item in place

        Returns:
            Shuffled items
        """
        if len(items) <= 1:
            return items.copy()

        if not self.config.structural_variation:
            return items.copy()

        result = items.copy()
        start_idx = 1 if preserve_first else 0
        end_idx = len(result) - 1 if preserve_last else len(result)

        # Fisher-Yates shuffle with entropy control
        shuffle_range = list(range(start_idx, end_idx))
        shuffle_intensity = self.config.phrase_variation_factor

        for i in range(len(shuffle_range) - 1, 0, -1):
            if (self._advance_state() % 100) / 100.0 < shuffle_intensity:
                j = self._advance_state() % (i + 1)
                actual_i = shuffle_range[i]
                actual_j = shuffle_range[j]
                result[actual_i], result[actual_j] = result[actual_j], result[actual_i]

        return result

    def get_weighted_choice(self, options: List[Tuple[Any, float]]) -> Any:
        """
        Make a weighted choice with entropy influence.

        Args:
            options: List of (option, weight) tuples

        Returns:
            Selected option
        """
        if not options:
            return None

        # Normalize weights
        total_weight = sum(w for _, w in options)
        if total_weight <= 0:
            return options[0][0]

        # Apply entropy-based flattening
        flatten_factor = self.config.phrase_variation_factor
        adjusted_weights = []
        for opt, weight in options:
            # Flatten toward uniform as entropy increases
            uniform = total_weight / len(options)
            adjusted = weight * (1 - flatten_factor) + uniform * flatten_factor
            adjusted_weights.append((opt, adjusted))

        # Select based on adjusted weights
        roll = (self._advance_state() % 10000) / 10000.0 * sum(w for _, w in adjusted_weights)
        cumulative = 0
        for opt, weight in adjusted_weights:
            cumulative += weight
            if roll <= cumulative:
                return opt

        return adjusted_weights[-1][0]

    def derive_subseed(self, context: str) -> int:
        """
        Derive a deterministic subseed from context.

        Args:
            context: Context string (e.g., "violation_1", "intro_section")

        Returns:
            Derived seed value
        """
        combined = f"{self.config.seed}:{context}"
        hash_val = int(hashlib.md5(combined.encode()).hexdigest()[:8], 16)
        return hash_val

    def create_subcontroller(self, context: str) -> 'EntropyController':
        """
        Create a sub-controller with derived seed for isolated randomness.

        Args:
            context: Context for seed derivation

        Returns:
            New EntropyController with derived seed
        """
        new_config = EntropyConfig(
            level=self.config.level,
            mutation_strength=self.config.mutation_strength,
            seed=self.derive_subseed(context)
        )
        return EntropyController(new_config)

    def get_variation_set(self, base_items: List[Any], target_size: int) -> List[Any]:
        """
        Generate a varied set from base items.

        Args:
            base_items: Base pool of items
            target_size: Desired output size

        Returns:
            List of items with controlled variation
        """
        if not base_items:
            return []

        if target_size <= len(base_items):
            return self.select_from_pool(base_items, target_size)

        # Need to repeat items - do so with variation
        result = []
        while len(result) < target_size:
            batch = self.select_from_pool(base_items, min(len(base_items), target_size - len(result)))
            result.extend(batch)

        return result[:target_size]


def create_entropy_controller(
    entropy_level: str = "medium",
    mutation_strength: int = 5,
    seed: int = 0
) -> EntropyController:
    """
    Factory function to create an entropy controller.

    Args:
        entropy_level: One of "low", "medium", "high", "maximum" (string or EntropyLevel enum)
        mutation_strength: 1-10 scale for mutation intensity
        seed: Random seed for reproducibility

    Returns:
        Configured EntropyController
    """
    # Handle both string and EntropyLevel enum inputs
    if isinstance(entropy_level, EntropyLevel):
        level = entropy_level
    else:
        level_map = {
            "low": EntropyLevel.LOW,
            "medium": EntropyLevel.MEDIUM,
            "high": EntropyLevel.HIGH,
            "maximum": EntropyLevel.MAXIMUM,
        }
        level = level_map.get(entropy_level.lower(), EntropyLevel.MEDIUM)

    strength = max(1, min(10, mutation_strength))

    config = EntropyConfig(level=level, mutation_strength=strength, seed=seed)
    return EntropyController(config)
