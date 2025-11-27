"""Credit Engine 2.0 - Rendering Engine

This layer takes LetterPlan (SSOT #3) and renders DisputeLetter (SSOT #4).
Uses phrasebanks for template-resistant letter generation.
"""
from .engine import RenderingEngine, render_letter
from .phrasebanks import PHRASEBANKS

__all__ = ["RenderingEngine", "render_letter", "PHRASEBANKS"]
