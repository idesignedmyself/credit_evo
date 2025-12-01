"""
Phrase Pools - Large-scale phrase variation pools for letter diversity.
Contains 300-700 variations per pool across legal and civil domains.
"""
from typing import Dict, List, Any
from .legal_pools import LEGAL_PHRASE_POOLS
from .civil_pools import CIVIL_PHRASE_POOLS
from .transitions import TRANSITION_POOLS
from .templates import TEMPLATE_POOLS

__all__ = [
    "LEGAL_PHRASE_POOLS",
    "CIVIL_PHRASE_POOLS",
    "TRANSITION_POOLS",
    "TEMPLATE_POOLS",
    "get_pool",
    "get_transition",
    "get_template",
    "PhrasePoolManager",
]


def get_pool(domain: str, category: str) -> List[str]:
    """Get a phrase pool by domain and category."""
    if domain == "legal":
        return LEGAL_PHRASE_POOLS.get(category, [])
    else:
        return CIVIL_PHRASE_POOLS.get(category, [])


def get_transition(category: str) -> List[str]:
    """Get transition phrases by category."""
    return TRANSITION_POOLS.get(category, [])


def get_template(domain: str, category: str) -> List[str]:
    """Get replacement templates by domain and category."""
    templates = TEMPLATE_POOLS.get(domain, {})
    return templates.get(category, [])


class PhrasePoolManager:
    """
    Manages phrase pool access with entropy-controlled selection.
    """

    def __init__(self, domain: str):
        self.domain = domain
        self.pools = LEGAL_PHRASE_POOLS if domain == "legal" else CIVIL_PHRASE_POOLS
        self.transitions = TRANSITION_POOLS
        self.templates = TEMPLATE_POOLS.get(domain, {})

    def get_phrase(self, category: str, index: int) -> str:
        """Get a phrase from a category by index."""
        pool = self.pools.get(category, [])
        if not pool:
            return ""
        return pool[index % len(pool)]

    def get_phrases(self, category: str, count: int, start_index: int = 0) -> List[str]:
        """Get multiple phrases from a category."""
        pool = self.pools.get(category, [])
        if not pool:
            return []
        result = []
        for i in range(count):
            idx = (start_index + i) % len(pool)
            result.append(pool[idx])
        return result

    def get_transition(self, category: str, index: int) -> str:
        """Get a transition phrase."""
        pool = self.transitions.get(category, [])
        if not pool:
            return ""
        return pool[index % len(pool)]

    def get_template(self, category: str, index: int) -> str:
        """Get a template."""
        pool = self.templates.get(category, [])
        if not pool:
            return ""
        return pool[index % len(pool)]

    def pool_size(self, category: str) -> int:
        """Get the size of a phrase pool."""
        return len(self.pools.get(category, []))

    def transition_size(self, category: str) -> int:
        """Get the size of a transition pool."""
        return len(self.transitions.get(category, []))

    def list_categories(self) -> List[str]:
        """List all available phrase categories."""
        return list(self.pools.keys())

    def list_transition_categories(self) -> List[str]:
        """List all available transition categories."""
        return list(self.transitions.keys())
