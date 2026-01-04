"""
Channel Wrappers

Same blocks, different framing based on delivery channel:
- CRA: FCRA §611 framing, reinsertion warning, CRA responsibility
- FURNISHER: FCRA §623(a) and (b), integrity obligations, direct correction
- MOV: Procedure disclosure, verification methodology, source requirements

Templates are HARD-LOCKED - no deviation allowed.
"""

from typing import List, Optional

from app.models.letter_object import (
    LetterChannel,
    LetterBlock,
    LetterSection,
)
from app.models.ssot import Severity


# =============================================================================
# CRA CHANNEL TEMPLATES
# =============================================================================

CRA_OPENING_TEMPLATE = (
    "This is a formal dispute submitted pursuant to the Fair Credit Reporting Act, "
    "15 U.S.C. § 1681i.\n\n"
    "I am exercising my right to dispute the accuracy of information contained in my "
    "consumer credit file. Under FCRA § 611(a), you are required to conduct a reasonable "
    "investigation of this dispute within 30 days."
)

CRA_REINSERTION_WARNING = (
    "Pursuant to FCRA § 611(a)(5)(B), if any deleted information is reinserted into my "
    "credit file, you must notify me in writing within 5 business days and provide the "
    "name, address, and phone number of the furnisher."
)

CRA_CLOSING_TEMPLATE = (
    "Please provide written confirmation of the results of your investigation within "
    "the statutory timeframe.\n\n"
    "This dispute has been sent via certified mail, return receipt requested."
)


# =============================================================================
# FURNISHER CHANNEL TEMPLATES
# =============================================================================

FURNISHER_OPENING_TEMPLATE = (
    "This is a formal notice of disputed information submitted pursuant to the Fair "
    "Credit Reporting Act, 15 U.S.C. § 1681s-2.\n\n"
    "As a furnisher of information to consumer reporting agencies, you have a duty under "
    "FCRA § 623(a)(1) to provide accurate information and under FCRA § 623(b) to conduct "
    "a reasonable investigation upon notice of dispute."
)

FURNISHER_OBLIGATION_REMINDER = (
    "Under FCRA § 623(a)(2), you are prohibited from furnishing information that you "
    "know or have reasonable cause to believe is inaccurate. Additionally, FCRA § 623(b)(1) "
    "requires you to conduct an investigation with respect to the disputed information and "
    "report the results to the consumer reporting agency."
)

FURNISHER_CLOSING_TEMPLATE = (
    "Please correct the inaccurate information with all consumer reporting agencies to "
    "which you have furnished data.\n\n"
    "Provide written confirmation of the corrections made and the date on which each "
    "consumer reporting agency was notified."
)


# =============================================================================
# MOV CHANNEL TEMPLATES
# =============================================================================

MOV_OPENING_TEMPLATE = (
    "This is a formal request for verification methodology and source documentation "
    "pursuant to the Fair Credit Reporting Act.\n\n"
    "I am requesting disclosure of the procedures used to verify the accuracy of the "
    "disputed information."
)

MOV_PROCEDURE_REQUEST = (
    "Please provide the following:\n\n"
    "1. The specific procedures used to verify the accuracy of this account\n"
    "2. The source documentation reviewed during verification\n"
    "3. The name and contact information of the person who conducted the verification\n"
    "4. The date on which verification was performed\n"
    "5. All documents relied upon in determining the information is accurate"
)

MOV_CLOSING_TEMPLATE = (
    "Failure to provide this information may constitute a failure to conduct a reasonable "
    "investigation as required by FCRA § 611(a)(1).\n\n"
    "A response is required within 30 days."
)


class ChannelWrapper:
    """
    Wraps letter blocks with channel-specific framing.

    Same blocks, different wrapper content based on:
    - CRA: Consumer reporting agency dispute
    - FURNISHER: Direct data furnisher dispute
    - MOV: Method of verification request
    """

    def create_opening_block(self, channel: LetterChannel) -> LetterBlock:
        """
        Create the opening block for a channel.

        Args:
            channel: Target delivery channel

        Returns:
            LetterBlock for the HEADER section
        """
        if channel == LetterChannel.CRA:
            text = CRA_OPENING_TEMPLATE
            statutes = ["15 U.S.C. § 1681i(a)"]
        elif channel == LetterChannel.FURNISHER:
            text = FURNISHER_OPENING_TEMPLATE
            statutes = ["15 U.S.C. § 1681s-2(a)(1)", "15 U.S.C. § 1681s-2(b)"]
        else:  # MOV
            text = MOV_OPENING_TEMPLATE
            statutes = ["15 U.S.C. § 1681i(a)(1)"]

        return LetterBlock(
            block_id=f"opening_{channel.value.lower()}",
            violation_id="opening",
            severity=Severity.MEDIUM,
            section=LetterSection.HEADER,
            text=text,
            anchors=[],
            statutes=statutes,
            metro2_field=None,
        )

    def create_statutory_block(self, channel: LetterChannel) -> LetterBlock:
        """
        Create the statutory authority block for a channel.

        Args:
            channel: Target delivery channel

        Returns:
            LetterBlock for the STATUTORY_AUTHORITY section
        """
        if channel == LetterChannel.CRA:
            text = CRA_REINSERTION_WARNING
            statutes = ["15 U.S.C. § 1681i(a)(5)(B)", "15 U.S.C. § 1681n"]
        elif channel == LetterChannel.FURNISHER:
            text = FURNISHER_OBLIGATION_REMINDER
            statutes = ["15 U.S.C. § 1681s-2(a)(2)", "15 U.S.C. § 1681s-2(b)(1)"]
        else:  # MOV
            text = MOV_PROCEDURE_REQUEST
            statutes = ["15 U.S.C. § 1681i(a)(1)"]

        return LetterBlock(
            block_id=f"statutory_{channel.value.lower()}",
            violation_id="statutory",
            severity=Severity.MEDIUM,
            section=LetterSection.STATUTORY_AUTHORITY,
            text=text,
            anchors=[],
            statutes=statutes,
            metro2_field=None,
        )

    def create_closing_block(self, channel: LetterChannel) -> LetterBlock:
        """
        Create the closing block for a channel.

        Args:
            channel: Target delivery channel

        Returns:
            LetterBlock for the CLOSING section
        """
        if channel == LetterChannel.CRA:
            text = CRA_CLOSING_TEMPLATE
        elif channel == LetterChannel.FURNISHER:
            text = FURNISHER_CLOSING_TEMPLATE
        else:  # MOV
            text = MOV_CLOSING_TEMPLATE

        return LetterBlock(
            block_id=f"closing_{channel.value.lower()}",
            violation_id="closing",
            severity=Severity.LOW,
            section=LetterSection.CLOSING,
            text=text,
            anchors=[],
            statutes=[],
            metro2_field=None,
        )

    def wrap(self, channel: LetterChannel) -> List[LetterBlock]:
        """
        Get all wrapper blocks for a channel.

        Args:
            channel: Target delivery channel

        Returns:
            List of LetterBlocks for opening, statutory, and closing sections
        """
        return [
            self.create_opening_block(channel),
            self.create_statutory_block(channel),
            self.create_closing_block(channel),
        ]


# =============================================================================
# MODULE-LEVEL SINGLETON
# =============================================================================

_wrapper: Optional[ChannelWrapper] = None


def get_wrapper() -> ChannelWrapper:
    """Get or create the default channel wrapper singleton."""
    global _wrapper
    if _wrapper is None:
        _wrapper = ChannelWrapper()
    return _wrapper


def create_channel_blocks(channel: LetterChannel) -> List[LetterBlock]:
    """
    Convenience function to create channel wrapper blocks.

    Args:
        channel: Target delivery channel

    Returns:
        List of LetterBlocks for the channel wrapper
    """
    return get_wrapper().wrap(channel)
