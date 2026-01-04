"""
Letter Generation - Phase 3 Deterministic Letter Assembly

This module provides deterministic, block-based dispute letter generation.

Core Principle: Letters are ASSEMBLED, not WRITTEN.

Components:
- LetterBlock: Atomic unit of letter content (one per violation)
- LetterObject: Complete letter assembled from blocks
- BlockCompiler: Violation → Block compiler
- DemandResolver: Severity → Demand type resolver
- ChannelWrapper: Channel-specific framing (CRA, FURNISHER, MOV)
- LetterAssembler: Final letter assembly

Phase 3 Invariants:
- Zero narrative variance
- Fully deterministic (same inputs → same outputs → same hashes)
- Regulator-legible
- No free-text, no tone customization, no storytelling
"""

from app.models.letter_object import (
    LetterBlock,
    LetterObject,
    LetterChannel,
    LetterSection,
    DemandType,
    HeaderContent,
    PartiesContent,
    AccountContent,
    DemandContent,
)

from .block_compiler import (
    BlockCompiler,
    FACTUAL_FAILURE_MAP,
    get_compiler,
    compile_violation,
    compile_violations,
)

from .demand_resolver import (
    DemandResolver,
    get_resolver,
    resolve_demand,
    create_demand_block,
)

from .channel_wrapper import (
    ChannelWrapper,
    get_wrapper,
    create_channel_blocks,
)

from .letter_assembler import (
    LetterAssembler,
    get_assembler,
    assemble_letter,
)

__all__ = [
    # Letter Objects
    "LetterBlock",
    "LetterObject",
    "LetterChannel",
    "LetterSection",
    "DemandType",
    "HeaderContent",
    "PartiesContent",
    "AccountContent",
    "DemandContent",
    # Block Compiler
    "BlockCompiler",
    "FACTUAL_FAILURE_MAP",
    "get_compiler",
    "compile_violation",
    "compile_violations",
    # Demand Resolver
    "DemandResolver",
    "get_resolver",
    "resolve_demand",
    "create_demand_block",
    # Channel Wrapper
    "ChannelWrapper",
    "get_wrapper",
    "create_channel_blocks",
    # Letter Assembler
    "LetterAssembler",
    "get_assembler",
    "assemble_letter",
]
