"""
Coexistence Classifier

3-way classification for Original Creditor (OC) and Collector/Debt Buyer tradeline coexistence.
Determines whether dual reporting is valid, a double-jeopardy violation, or an ownership conflict.

Classifications:
1. VALID_COEXISTENCE - OC reports $0 balance, collector reports >$0 (proper handoff)
2. DOUBLE_BALANCE_VIOLATION - Both OC and collector report active balances (double jeopardy)
3. OWNERSHIP_CONFLICT_DOC_DEMAND - Chain-of-title unclear, documentation demanded

This module bridges legacy text-based status parsing with Metro 2 code-based validation.
"""

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class CoexistenceType(Enum):
    """Classification result types."""
    VALID_COEXISTENCE = "valid_coexistence"
    DOUBLE_BALANCE_VIOLATION = "double_balance_violation"
    OWNERSHIP_CONFLICT_DOC_DEMAND = "ownership_conflict_doc_demand"
    INSUFFICIENT_DATA = "insufficient_data"
    SINGLE_TRADELINE = "single_tradeline"


class TradelineRole(Enum):
    """Role of tradeline in debt lifecycle."""
    ORIGINAL_CREDITOR = "original_creditor"
    COLLECTION_AGENCY = "collection_agency"
    DEBT_BUYER = "debt_buyer"
    UNKNOWN = "unknown"


@dataclass
class TradelineInfo:
    """Extracted information about a tradeline."""
    role: TradelineRole
    account_type: Optional[str] = None
    account_status: Optional[str] = None
    balance: float = 0.0
    original_creditor_name: Optional[str] = None
    creditor_name: Optional[str] = None
    date_opened: Optional[date] = None
    date_reported: Optional[date] = None
    has_j1_segment: bool = False
    has_k1_segment: bool = False
    k1_indicator: Optional[str] = None  # "Purchased From" or "Sold To"
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "role": self.role.value,
            "account_type": self.account_type,
            "account_status": self.account_status,
            "balance": self.balance,
            "original_creditor_name": self.original_creditor_name,
            "creditor_name": self.creditor_name,
            "date_opened": self.date_opened.isoformat() if self.date_opened else None,
            "date_reported": self.date_reported.isoformat() if self.date_reported else None,
            "has_j1_segment": self.has_j1_segment,
            "has_k1_segment": self.has_k1_segment,
            "k1_indicator": self.k1_indicator,
        }


@dataclass
class CoexistenceResult:
    """Result of coexistence classification."""
    classification: CoexistenceType
    severity: str
    description: str
    oc_tradeline: Optional[TradelineInfo] = None
    collector_tradeline: Optional[TradelineInfo] = None
    evidence: Dict[str, Any] = field(default_factory=dict)
    rule_code: Optional[str] = None
    cfpb_recommend: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "classification": self.classification.value,
            "severity": self.severity,
            "description": self.description,
            "oc_tradeline": self.oc_tradeline.to_dict() if self.oc_tradeline else None,
            "collector_tradeline": self.collector_tradeline.to_dict() if self.collector_tradeline else None,
            "evidence": self.evidence,
            "rule_code": self.rule_code,
            "cfpb_recommend": self.cfpb_recommend,
        }


class CoexistenceClassifier:
    """
    Classifies OC/Collector tradeline coexistence scenarios.

    When a debt is sold or assigned to collection, both the original creditor (OC)
    and the collector/debt buyer may report the tradeline. This classifier determines
    whether the reporting is compliant or represents a violation.
    """

    # Account types for collectors
    COLLECTOR_ACCOUNT_TYPES: Set[str] = {"47", "95"}  # Collection Agency, Summary

    # Account types for debt buyers
    DEBT_BUYER_ACCOUNT_TYPES: Set[str] = {"43"}

    # Account statuses indicating paid/closed (OC should zero balance)
    PAID_CLOSED_STATUSES: Set[str] = {
        "13",  # Paid or Closed Account/Zero Balance
        "61", "62", "63", "64", "65",  # Paid derogatory variants
    }

    # Account statuses indicating transferred/sold
    TRANSFERRED_STATUSES: Set[str] = {"93"}  # Assigned to Collections

    # Text patterns for legacy status parsing
    SOLD_PATTERNS = [
        "sold", "transferred", "assigned", "purchased by",
        "bought by", "acquired by", "now owned by"
    ]

    COLLECTION_PATTERNS = [
        "collection", "placed for collection", "in collections",
        "sent to collection", "charged off"
    ]

    # Balance threshold for considering "zero balance"
    ZERO_BALANCE_THRESHOLD: float = 0.01

    def __init__(self):
        """Initialize the classifier."""
        pass

    def _determine_role(
        self,
        account_type: Optional[str],
        status_text: Optional[str],
        has_j1: bool,
        has_k1: bool,
    ) -> TradelineRole:
        """
        Determine tradeline role from Metro 2 codes and text.

        Args:
            account_type: Metro 2 account type code
            status_text: Legacy status text
            has_j1: Whether J1 segment (original creditor name) is present
            has_k1: Whether K1 segment (purchased from/sold to) is present

        Returns:
            TradelineRole enum value
        """
        # Check Metro 2 account type first
        if account_type:
            if account_type in self.DEBT_BUYER_ACCOUNT_TYPES:
                return TradelineRole.DEBT_BUYER
            if account_type in self.COLLECTOR_ACCOUNT_TYPES:
                return TradelineRole.COLLECTION_AGENCY

        # Check for J1/K1 segments (indicates collector/debt buyer)
        if has_j1 or has_k1:
            if account_type in self.DEBT_BUYER_ACCOUNT_TYPES:
                return TradelineRole.DEBT_BUYER
            return TradelineRole.COLLECTION_AGENCY

        # Fall back to text parsing
        if status_text:
            text_lower = status_text.lower()

            # Check for collection patterns
            for pattern in self.COLLECTION_PATTERNS:
                if pattern in text_lower:
                    return TradelineRole.COLLECTION_AGENCY

            # Check for sold patterns (suggests OC that sold)
            for pattern in self.SOLD_PATTERNS:
                if pattern in text_lower:
                    # This is the OC side of a sold account
                    return TradelineRole.ORIGINAL_CREDITOR

        # Default to OC if no collection indicators
        return TradelineRole.ORIGINAL_CREDITOR

    def _is_zero_balance(self, balance: Any) -> bool:
        """Check if balance is effectively zero."""
        try:
            bal = float(balance) if balance is not None else 0.0
            return abs(bal) < self.ZERO_BALANCE_THRESHOLD
        except (TypeError, ValueError):
            return True  # Treat unparseable as zero

    def _parse_balance(self, balance: Any) -> float:
        """Parse balance from various formats."""
        if balance is None:
            return 0.0
        try:
            if isinstance(balance, str):
                # Remove currency symbols and commas
                cleaned = balance.replace("$", "").replace(",", "").strip()
                return float(cleaned)
            return float(balance)
        except (TypeError, ValueError):
            return 0.0

    def extract_tradeline_info(
        self,
        account_data: Dict[str, Any],
        status_text: Optional[str] = None,
    ) -> TradelineInfo:
        """
        Extract standardized tradeline info from account data.

        Args:
            account_data: Dictionary with account fields
            status_text: Optional legacy status text

        Returns:
            TradelineInfo with extracted data
        """
        account_type = account_data.get("account_type") or account_data.get("accountType")
        account_status = account_data.get("account_status") or account_data.get("accountStatus")
        balance = self._parse_balance(
            account_data.get("balance") or
            account_data.get("current_balance") or
            account_data.get("currentBalance") or
            0.0
        )

        # Check for J1/K1 segments
        has_j1 = bool(
            account_data.get("j1_segment") or
            account_data.get("original_creditor_name") or
            account_data.get("originalCreditorName")
        )
        has_k1 = bool(
            account_data.get("k1_segment") or
            account_data.get("purchased_from") or
            account_data.get("sold_to")
        )

        k1_indicator = None
        if account_data.get("purchased_from"):
            k1_indicator = "Purchased From"
        elif account_data.get("sold_to"):
            k1_indicator = "Sold To"

        role = self._determine_role(account_type, status_text, has_j1, has_k1)

        return TradelineInfo(
            role=role,
            account_type=account_type,
            account_status=account_status,
            balance=balance,
            original_creditor_name=(
                account_data.get("original_creditor_name") or
                account_data.get("originalCreditorName")
            ),
            creditor_name=(
                account_data.get("creditor_name") or
                account_data.get("creditorName") or
                account_data.get("subscriber_name")
            ),
            has_j1_segment=has_j1,
            has_k1_segment=has_k1,
            k1_indicator=k1_indicator,
            raw_data=account_data,
        )

    def classify(
        self,
        oc_data: Optional[Dict[str, Any]] = None,
        collector_data: Optional[Dict[str, Any]] = None,
        oc_status_text: Optional[str] = None,
        collector_status_text: Optional[str] = None,
    ) -> CoexistenceResult:
        """
        Classify coexistence scenario between OC and collector tradelines.

        Args:
            oc_data: Original creditor account data
            collector_data: Collector/debt buyer account data
            oc_status_text: Legacy OC status text
            collector_status_text: Legacy collector status text

        Returns:
            CoexistenceResult with classification
        """
        # Handle single tradeline case
        if oc_data is None and collector_data is None:
            return CoexistenceResult(
                classification=CoexistenceType.INSUFFICIENT_DATA,
                severity="LOW",
                description="No tradeline data provided for classification.",
            )

        if oc_data is None or collector_data is None:
            return CoexistenceResult(
                classification=CoexistenceType.SINGLE_TRADELINE,
                severity="INFO",
                description="Only single tradeline found. Coexistence analysis requires both OC and collector tradelines.",
            )

        # Extract tradeline info
        oc_info = self.extract_tradeline_info(oc_data, oc_status_text)
        collector_info = self.extract_tradeline_info(collector_data, collector_status_text)

        # Override roles based on input position
        oc_info.role = TradelineRole.ORIGINAL_CREDITOR
        if collector_info.role == TradelineRole.ORIGINAL_CREDITOR:
            # Determine if debt buyer or collection agency
            if collector_info.account_type in self.DEBT_BUYER_ACCOUNT_TYPES:
                collector_info.role = TradelineRole.DEBT_BUYER
            else:
                collector_info.role = TradelineRole.COLLECTION_AGENCY

        oc_balance = oc_info.balance
        collector_balance = collector_info.balance

        oc_zero = self._is_zero_balance(oc_balance)
        collector_zero = self._is_zero_balance(collector_balance)

        # Classification logic
        if oc_zero and not collector_zero:
            # Valid coexistence: OC zeroed out, collector reports balance
            return CoexistenceResult(
                classification=CoexistenceType.VALID_COEXISTENCE,
                severity="INFO",
                description="Valid coexistence: Original creditor reports $0 balance, "
                            f"collector reports ${collector_balance:.2f}. "
                            "This is proper handoff reporting per Metro 2 guidelines.",
                oc_tradeline=oc_info,
                collector_tradeline=collector_info,
                rule_code="VALID_COEXISTENCE",
                evidence={
                    "oc_balance": oc_balance,
                    "collector_balance": collector_balance,
                    "oc_status": oc_info.account_status,
                    "collector_status": collector_info.account_status,
                }
            )

        elif not oc_zero and not collector_zero:
            # Double balance violation: Both reporting balances
            return CoexistenceResult(
                classification=CoexistenceType.DOUBLE_BALANCE_VIOLATION,
                severity="HIGH",
                description=f"Double jeopardy violation: Original creditor reports "
                            f"${oc_balance:.2f} AND collector reports ${collector_balance:.2f}. "
                            "Consumer is being penalized twice for the same debt.",
                oc_tradeline=oc_info,
                collector_tradeline=collector_info,
                rule_code="DOUBLE_JEOPARDY",
                cfpb_recommend=True,
                evidence={
                    "oc_balance": oc_balance,
                    "collector_balance": collector_balance,
                    "combined_reported_balance": oc_balance + collector_balance,
                    "oc_status": oc_info.account_status,
                    "collector_status": collector_info.account_status,
                }
            )

        elif not oc_zero and collector_zero:
            # Ownership conflict: OC has balance but collector is reporting
            # This suggests unclear chain of title
            return CoexistenceResult(
                classification=CoexistenceType.OWNERSHIP_CONFLICT_DOC_DEMAND,
                severity="MEDIUM",
                description=f"Ownership conflict: Original creditor reports ${oc_balance:.2f} "
                            "but collector shows $0 balance. Chain of title is unclear. "
                            "Documentation of debt sale/assignment should be demanded.",
                oc_tradeline=oc_info,
                collector_tradeline=collector_info,
                rule_code="OWNERSHIP_CONFLICT_DOC_DEMAND",
                cfpb_recommend=False,
                evidence={
                    "oc_balance": oc_balance,
                    "collector_balance": collector_balance,
                    "oc_status": oc_info.account_status,
                    "collector_status": collector_info.account_status,
                    "chain_of_title_unclear": True,
                }
            )

        else:
            # Both zero - could be resolved or duplicate zeroed accounts
            return CoexistenceResult(
                classification=CoexistenceType.VALID_COEXISTENCE,
                severity="INFO",
                description="Both tradelines report $0 balance. Account appears resolved.",
                oc_tradeline=oc_info,
                collector_tradeline=collector_info,
                evidence={
                    "oc_balance": 0.0,
                    "collector_balance": 0.0,
                    "both_resolved": True,
                }
            )

    def classify_from_tradelines(
        self,
        tradelines: List[Dict[str, Any]],
        original_creditor_hint: Optional[str] = None,
    ) -> List[CoexistenceResult]:
        """
        Classify coexistence from a list of potentially related tradelines.

        Args:
            tradelines: List of tradeline dictionaries
            original_creditor_hint: Name of original creditor to match

        Returns:
            List of CoexistenceResult for each found pair
        """
        results = []

        # Separate into OC and collector tradelines
        oc_lines = []
        collector_lines = []

        for tl in tradelines:
            info = self.extract_tradeline_info(tl)

            if info.role in (TradelineRole.COLLECTION_AGENCY, TradelineRole.DEBT_BUYER):
                collector_lines.append((tl, info))
            else:
                oc_lines.append((tl, info))

        # Match OC to collectors by original creditor name
        for collector_data, collector_info in collector_lines:
            matching_oc = None

            # Try to match by original creditor name
            if collector_info.original_creditor_name:
                oc_name_lower = collector_info.original_creditor_name.lower()
                for oc_data, oc_info in oc_lines:
                    if oc_info.creditor_name and oc_name_lower in oc_info.creditor_name.lower():
                        matching_oc = oc_data
                        break

            # Fall back to hint
            if matching_oc is None and original_creditor_hint:
                hint_lower = original_creditor_hint.lower()
                for oc_data, oc_info in oc_lines:
                    if oc_info.creditor_name and hint_lower in oc_info.creditor_name.lower():
                        matching_oc = oc_data
                        break

            if matching_oc:
                result = self.classify(
                    oc_data=matching_oc,
                    collector_data=collector_data,
                )
                results.append(result)
            else:
                # Collector without matching OC - could be normal
                results.append(CoexistenceResult(
                    classification=CoexistenceType.SINGLE_TRADELINE,
                    severity="INFO",
                    description="Collector tradeline without matching original creditor tradeline.",
                    collector_tradeline=collector_info,
                ))

        return results


def classify_coexistence(
    oc_data: Optional[Dict[str, Any]] = None,
    collector_data: Optional[Dict[str, Any]] = None,
) -> CoexistenceResult:
    """
    Convenience function to classify OC/collector coexistence.

    Args:
        oc_data: Original creditor account data
        collector_data: Collector/debt buyer account data

    Returns:
        CoexistenceResult with classification
    """
    classifier = CoexistenceClassifier()
    return classifier.classify(oc_data=oc_data, collector_data=collector_data)
