"""Credit Engine 2.0 - Strategy Selector

This layer takes AuditResult and creates LetterPlan (SSOT #3).
It decides how to group violations and which strategy to use.
"""
from .selector import StrategySelector, create_letter_plan

__all__ = ["StrategySelector", "create_letter_plan"]
