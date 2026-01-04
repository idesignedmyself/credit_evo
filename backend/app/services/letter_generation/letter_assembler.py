"""
Letter Assembler

Assembles complete letters from compiled blocks.

This is the final assembly layer that:
1. Compiles violations into FACTUAL_INACCURACIES blocks
2. Resolves demand type and creates DEMAND block
3. Wraps with channel-specific framing blocks
4. Produces a deterministic LetterObject

The assembler ONLY assembles - it does not render.
Rendering is the responsibility of the presentation layer.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.models.ssot import Violation, Consumer, Severity
from app.models.letter_object import (
    LetterObject,
    LetterBlock,
    LetterChannel,
    LetterSection,
    DemandType,
)

from .block_compiler import BlockCompiler, get_compiler
from .demand_resolver import DemandResolver, get_resolver
from .channel_wrapper import ChannelWrapper, get_wrapper


class LetterAssembler:
    """
    Assembles complete letters from violations.

    Assembly order:
    1. Channel opening (HEADER)
    2. Parties (PARTIES) - if provided
    3. Account identification (ACCOUNT_IDENTIFICATION) - if provided
    4. Compiled violation blocks (FACTUAL_INACCURACIES)
    5. Statutory authority (STATUTORY_AUTHORITY)
    6. Demand block (DEMAND)
    7. Channel closing (CLOSING)

    The assembler produces deterministic output:
    - Same violations → same blocks → same hash
    """

    def __init__(
        self,
        compiler: Optional[BlockCompiler] = None,
        resolver: Optional[DemandResolver] = None,
        wrapper: Optional[ChannelWrapper] = None,
    ):
        """
        Initialize the letter assembler.

        Args:
            compiler: BlockCompiler instance (defaults to singleton)
            resolver: DemandResolver instance (defaults to singleton)
            wrapper: ChannelWrapper instance (defaults to singleton)
        """
        self.compiler = compiler or get_compiler()
        self.resolver = resolver or get_resolver()
        self.wrapper = wrapper or get_wrapper()

    def assemble(
        self,
        violations: List[Violation],
        channel: LetterChannel,
        consumer: Optional[Consumer] = None,
        account_info: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> LetterObject:
        """
        Assemble a complete letter from violations.

        Args:
            violations: List of Violation objects
            channel: Target delivery channel (CRA, FURNISHER, MOV)
            consumer: Optional consumer information for PARTIES section
            account_info: Optional account info for ACCOUNT_IDENTIFICATION section
            metadata: Optional metadata (dispute_session_id, report_hash, etc.)

        Returns:
            LetterObject containing all assembled blocks

        Raises:
            KeyError: If any violation type has no factual failure mapping
        """
        # Resolve demand type
        demand_type = self.resolver.resolve(violations)

        # Create letter object
        letter = LetterObject(
            channel=channel,
            demand_type=demand_type,
            metadata=metadata or {},
            generated_at=datetime.now(timezone.utc),
        )

        # 1. Add channel opening block (HEADER)
        opening_block = self.wrapper.create_opening_block(channel)
        letter.add_block(opening_block)

        # 2. Add parties block if consumer provided (PARTIES)
        if consumer:
            parties_block = self._create_parties_block(consumer)
            letter.add_block(parties_block)

        # 3. Add account identification block if provided (ACCOUNT_IDENTIFICATION)
        if account_info:
            account_block = self._create_account_block(account_info)
            letter.add_block(account_block)

        # 4. Compile and add violation blocks (FACTUAL_INACCURACIES)
        violation_blocks = self.compiler.compile_many(violations)
        for block in violation_blocks:
            letter.add_block(block)

        # 5. Add statutory authority block (STATUTORY_AUTHORITY)
        statutory_block = self.wrapper.create_statutory_block(channel)
        letter.add_block(statutory_block)

        # 6. Add demand block (DEMAND)
        demand_block = self.resolver.create_demand_block(violations, demand_type)
        letter.add_block(demand_block)

        # 7. Add channel closing block (CLOSING)
        closing_block = self.wrapper.create_closing_block(channel)
        letter.add_block(closing_block)

        return letter

    def _create_parties_block(self, consumer: Consumer) -> LetterBlock:
        """
        Create parties identification block.

        Args:
            consumer: Consumer information

        Returns:
            LetterBlock for PARTIES section
        """
        # Build parties text deterministically
        lines = [
            f"Consumer: {consumer.full_name}",
        ]

        if hasattr(consumer, 'address') and consumer.address:
            lines.append(f"Address: {consumer.address}")

        if hasattr(consumer, 'ssn_last_four') and consumer.ssn_last_four:
            lines.append(f"SSN (Last 4): XXX-XX-{consumer.ssn_last_four}")

        text = "\n".join(lines)

        return LetterBlock(
            block_id="parties_consumer",
            violation_id="parties",
            severity=Severity.LOW,
            section=LetterSection.PARTIES,
            text=text,
            anchors=[],
            statutes=[],
            metro2_field=None,
        )

    def _create_account_block(self, account_info: Dict[str, Any]) -> LetterBlock:
        """
        Create account identification block.

        Args:
            account_info: Account information dictionary

        Returns:
            LetterBlock for ACCOUNT_IDENTIFICATION section
        """
        # Build account text deterministically
        lines = []

        if account_info.get("creditor_name"):
            lines.append(f"Creditor: {account_info['creditor_name']}")

        if account_info.get("account_number_masked"):
            lines.append(f"Account Number: {account_info['account_number_masked']}")

        if account_info.get("account_type"):
            lines.append(f"Account Type: {account_info['account_type']}")

        if account_info.get("date_opened"):
            lines.append(f"Date Opened: {account_info['date_opened']}")

        if account_info.get("current_balance"):
            lines.append(f"Current Balance: {account_info['current_balance']}")

        text = "\n".join(lines) if lines else "Account information on file"

        return LetterBlock(
            block_id="account_identification",
            violation_id="account",
            severity=Severity.LOW,
            section=LetterSection.ACCOUNT_IDENTIFICATION,
            text=text,
            anchors=[],
            statutes=[],
            metro2_field=None,
        )

    def assemble_for_all_channels(
        self,
        violations: List[Violation],
        consumer: Optional[Consumer] = None,
        account_info: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[LetterChannel, LetterObject]:
        """
        Assemble letters for all three channels.

        Args:
            violations: List of Violation objects
            consumer: Optional consumer information
            account_info: Optional account information
            metadata: Optional metadata

        Returns:
            Dict mapping each channel to its assembled LetterObject
        """
        return {
            channel: self.assemble(
                violations=violations,
                channel=channel,
                consumer=consumer,
                account_info=account_info,
                metadata=metadata,
            )
            for channel in LetterChannel
        }


# =============================================================================
# MODULE-LEVEL SINGLETON
# =============================================================================

_assembler: Optional[LetterAssembler] = None


def get_assembler() -> LetterAssembler:
    """Get or create the default letter assembler singleton."""
    global _assembler
    if _assembler is None:
        _assembler = LetterAssembler()
    return _assembler


def assemble_letter(
    violations: List[Violation],
    channel: LetterChannel,
    consumer: Optional[Consumer] = None,
    account_info: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> LetterObject:
    """
    Convenience function to assemble a letter.

    Args:
        violations: List of Violation objects
        channel: Target delivery channel
        consumer: Optional consumer information
        account_info: Optional account information
        metadata: Optional metadata

    Returns:
        LetterObject containing all assembled blocks
    """
    return get_assembler().assemble(
        violations=violations,
        channel=channel,
        consumer=consumer,
        account_info=account_info,
        metadata=metadata,
    )
