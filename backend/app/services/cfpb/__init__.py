"""
CFPB Channel Adapter - Service Package

Provides CFPB-specific escalation track that mirrors CRA lifecycle.
Same facts, same contradictions, same severity, same remedies - different audience rendering.
"""
from .cfpb_state_machine import CFPBStateMachine
from .cfpb_letter_generator import CFPBLetterGenerator
from .cfpb_service import CFPBService, CFPBServiceError

__all__ = [
    "CFPBStateMachine",
    "CFPBLetterGenerator",
    "CFPBService",
    "CFPBServiceError",
]
