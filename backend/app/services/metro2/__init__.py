"""
Metro 2 V2.0 Module

Schema validators, DOFD state machine, K2 guardrails, and coexistence classifier
for Metro 2 format compliance per CRRG 2024-2025.
"""

from .validators import (
    Metro2SchemaValidator,
    ValidationMode,
    ValidationResult,
)
from .citation_injector import (
    CitationInjector,
    CRRGCitation,
    InjectionResult,
    get_injector,
    inject_citation_into_violation,
)
from .dofd_state import (
    DOFDStateMachine,
    DOFDState,
    DOFDEventType,
    DOFDViolation,
    DOFDStateSnapshot,
    validate_dofd,
)
from .k2_guardrails import (
    K2Guardrails,
    K2ValidationLevel,
    K2ValidationResult,
    K2Violation,
    validate_k2,
)
from .coexistence import (
    CoexistenceClassifier,
    CoexistenceType,
    CoexistenceResult,
    TradelineRole,
    TradelineInfo,
    classify_coexistence,
)

__all__ = [
    # Validators
    "Metro2SchemaValidator",
    "ValidationMode",
    "ValidationResult",
    # Citation Injector
    "CitationInjector",
    "CRRGCitation",
    "InjectionResult",
    "get_injector",
    "inject_citation_into_violation",
    # DOFD State Machine
    "DOFDStateMachine",
    "DOFDState",
    "DOFDEventType",
    "DOFDViolation",
    "DOFDStateSnapshot",
    "validate_dofd",
    # K2 Guardrails
    "K2Guardrails",
    "K2ValidationLevel",
    "K2ValidationResult",
    "K2Violation",
    "validate_k2",
    # Coexistence Classifier
    "CoexistenceClassifier",
    "CoexistenceType",
    "CoexistenceResult",
    "TradelineRole",
    "TradelineInfo",
    "classify_coexistence",
]
