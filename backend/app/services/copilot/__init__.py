"""
Credit Engine 2.0 - Goal-Oriented Copilot Engine

Translates user financial goals into prioritized enforcement strategies.
Read-only with respect to credit data. Deterministic. No ML.

Tier 6: ExplanationRenderer for human-readable outcome explanations.
"""

from .copilot_engine import CopilotEngine
from .batch_engine import BatchEngine
from .explanation_renderer import ExplanationRenderer, Explanation, ExplanationDialect

__all__ = [
    "CopilotEngine",
    "BatchEngine",
    "ExplanationRenderer",
    "Explanation",
    "ExplanationDialect",
]
