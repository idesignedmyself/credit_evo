"""Credit Engine 2.0 - Audit Engine

This layer audits NormalizedReport and outputs AuditResult (SSOT #2).
All violations are computed here - downstream modules CANNOT re-audit.
"""
from .engine import AuditEngine, audit_report
from .rules import (
    SingleBureauRules,
    FurnisherRules,
    TemporalRules,
)
from .cross_bureau_rules import (
    CrossBureauRules,
    audit_cross_bureau,
    match_accounts_across_bureaus,
)

__all__ = [
    "AuditEngine",
    "audit_report",
    "SingleBureauRules",
    "FurnisherRules",
    "TemporalRules",
    "CrossBureauRules",
    "audit_cross_bureau",
    "match_accounts_across_bureaus",
]
