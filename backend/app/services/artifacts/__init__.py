"""
Tier 5 — Product & Revenue Leverage

Package Tier-3 outcomes into monetizable artifacts.
All components consume ledger outputs only.
No auto-sending — generation only.
"""

from .attorney_packet_builder import AttorneyPacketBuilder, AttorneyPacket
from .referral_artifact import ReferralArtifact, ReferralArtifactBuilder

__all__ = [
    "AttorneyPacketBuilder",
    "AttorneyPacket",
    "ReferralArtifact",
    "ReferralArtifactBuilder",
]
