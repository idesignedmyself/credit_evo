"""
Execution Outcome Detector (B7)

Detects outcomes during report re-ingestion by comparing
the new report against pending executions.

Uses snapshot hashing (previous_state_hash, current_state_hash)
to prevent parser hallucinations and ensure accurate outcome detection.
"""
import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from sqlalchemy.orm import Session

from ...models.db_models import (
    ExecutionEventDB,
    ExecutionOutcomeDB,
    ExecutionStatus,
    FinalOutcome,
    ReportDB,
)
from .execution_ledger import ExecutionLedgerService


@dataclass
class OutcomeDetectionResult:
    """Result of outcome detection for a single execution."""
    execution_id: str
    dispute_session_id: str
    account_fingerprint: str
    final_outcome: FinalOutcome
    previous_state_hash: str
    current_state_hash: str
    account_removed: bool
    negative_status_removed: bool
    utilization_impact: Optional[float]
    outcome_emitted: bool


class ExecutionOutcomeDetector:
    """
    Detects outcomes by comparing new reports against pending executions.

    Process:
    1. Get all pending executions for the user
    2. For each execution, find the matching account in the new report
    3. Compare state hashes to detect changes
    4. Emit outcome events based on detected changes

    Uses snapshot hashing to prevent parser hallucinations.
    """

    # Fields that contribute to account state hash
    STATE_HASH_FIELDS = [
        'account_number',
        'creditor_name',
        'account_type',
        'balance',
        'credit_limit',
        'payment_status',
        'date_opened',
        'date_of_first_delinquency',
        'account_status',
        'high_balance',
        'past_due_amount',
    ]

    # Negative statuses that indicate derogatory items
    NEGATIVE_STATUSES = [
        'COLLECTION',
        'CHARGEOFF',
        'CHARGE_OFF',
        'CHARGED_OFF',
        'DELINQUENT',
        'LATE',
        '30_DAYS_LATE',
        '60_DAYS_LATE',
        '90_DAYS_LATE',
        '120_DAYS_LATE',
        'REPOSSESSION',
        'FORECLOSURE',
        'BANKRUPTCY',
    ]

    def __init__(self, db: Session):
        self.db = db
        self.ledger = ExecutionLedgerService(db)

    def compute_account_state_hash(self, account: Dict[str, Any]) -> str:
        """
        Compute a SHA256 hash of the account's relevant state fields.

        This hash is used to detect changes between report ingestions.
        Only fields that matter for outcome detection are included.

        Args:
            account: Account dictionary from parsed report

        Returns:
            SHA256 hex digest of the account state
        """
        state_dict = {}
        for field in self.STATE_HASH_FIELDS:
            value = account.get(field)
            # Normalize the value for consistent hashing
            if value is not None:
                if isinstance(value, str):
                    value = value.strip().upper()
                state_dict[field] = value

        # Sort keys for deterministic ordering
        state_json = json.dumps(state_dict, sort_keys=True, default=str)
        return hashlib.sha256(state_json.encode()).hexdigest()

    def create_account_fingerprint(self, account: Dict[str, Any]) -> str:
        """
        Create a fingerprint to uniquely identify an account across reports.

        Uses account number + creditor name combination.

        Args:
            account: Account dictionary

        Returns:
            Fingerprint string
        """
        account_number = account.get('account_number', '')
        creditor_name = account.get('creditor_name', '') or account.get('subscriber_name', '')

        # Normalize
        account_number = str(account_number).strip().upper() if account_number else ''
        creditor_name = str(creditor_name).strip().upper() if creditor_name else ''

        return f"{creditor_name}|{account_number}"

    def is_negative_status(self, account: Dict[str, Any]) -> bool:
        """
        Check if account has a negative status.

        Args:
            account: Account dictionary

        Returns:
            True if account has negative/derogatory status
        """
        status = account.get('account_status', '') or account.get('payment_status', '')
        if not status:
            return False

        status_upper = str(status).strip().upper()

        for neg in self.NEGATIVE_STATUSES:
            if neg in status_upper:
                return True

        return False

    def detect_outcomes(
        self,
        user_id: str,
        new_report_id: str,
        new_accounts: List[Dict[str, Any]],
    ) -> List[OutcomeDetectionResult]:
        """
        Detect outcomes by comparing new report against pending executions.

        For each pending execution:
        1. Find matching account in new report by fingerprint
        2. Compare state hashes
        3. Determine outcome (DELETED, VERIFIED, UPDATED, etc.)
        4. Emit outcome event

        Args:
            user_id: The user whose report was uploaded
            new_report_id: ID of the newly uploaded report
            new_accounts: List of account dictionaries from the new report

        Returns:
            List of outcome detection results
        """
        results = []

        # Build fingerprint map for new accounts
        new_account_map: Dict[str, Dict[str, Any]] = {}
        for account in new_accounts:
            fingerprint = self.create_account_fingerprint(account)
            if fingerprint and fingerprint != '|':  # Skip empty fingerprints
                new_account_map[fingerprint] = account

        # Get all pending executions for this user
        pending_executions = self.ledger.get_pending_executions_for_user(user_id)

        for execution in pending_executions:
            if not execution.account_fingerprint:
                continue

            result = self._process_execution(
                execution=execution,
                new_report_id=new_report_id,
                new_account_map=new_account_map,
            )

            if result:
                results.append(result)

        return results

    def _process_execution(
        self,
        execution: ExecutionEventDB,
        new_report_id: str,
        new_account_map: Dict[str, Dict[str, Any]],
    ) -> Optional[OutcomeDetectionResult]:
        """
        Process a single execution against the new report.

        Args:
            execution: The execution event to check
            new_report_id: ID of the new report
            new_account_map: Map of fingerprint -> account data

        Returns:
            OutcomeDetectionResult if outcome detected, None otherwise
        """
        fingerprint = execution.account_fingerprint

        # Get previous state from the execution context
        # The previous_state_hash might be stored in gate_applied or we compute it
        previous_state_hash = self._get_previous_state_hash(execution)

        # Check if account exists in new report
        new_account = new_account_map.get(fingerprint)

        if new_account is None:
            # Account not found = DELETED
            outcome = FinalOutcome.DELETED
            current_state_hash = ""
            account_removed = True
            negative_status_removed = True  # If deleted, negative is gone
            utilization_impact = self._estimate_utilization_impact(execution, removed=True)

        else:
            # Account found - compare states
            current_state_hash = self.compute_account_state_hash(new_account)

            if previous_state_hash and current_state_hash == previous_state_hash:
                # No change detected - might be VERIFIED or still pending
                # Only emit if we're confident this is a verification
                # For now, don't emit outcome if nothing changed
                return None

            # State changed - determine what kind of change
            was_negative = True  # We only dispute negative items
            is_negative = self.is_negative_status(new_account)

            if not is_negative:
                # Negative status removed = UPDATED (cured)
                outcome = FinalOutcome.UPDATED
                negative_status_removed = True
            else:
                # Still negative but state changed = VERIFIED (with updates)
                outcome = FinalOutcome.VERIFIED
                negative_status_removed = False

            account_removed = False
            utilization_impact = self._estimate_utilization_impact(
                execution,
                new_account=new_account,
            )

        # Emit the outcome
        self.ledger.emit_execution_outcome(
            execution_id=execution.id,
            dispute_session_id=execution.dispute_session_id,
            final_outcome=outcome,
            resolved_at=datetime.now(timezone.utc),
            new_report_id=new_report_id,
            previous_state_hash=previous_state_hash,
            current_state_hash=current_state_hash,
            account_removed=account_removed,
            negative_status_removed=negative_status_removed,
            utilization_impact=utilization_impact,
            durability_score=self._compute_durability_score(outcome),
        )

        return OutcomeDetectionResult(
            execution_id=execution.id,
            dispute_session_id=execution.dispute_session_id,
            account_fingerprint=fingerprint,
            final_outcome=outcome,
            previous_state_hash=previous_state_hash or "",
            current_state_hash=current_state_hash,
            account_removed=account_removed,
            negative_status_removed=negative_status_removed,
            utilization_impact=utilization_impact,
            outcome_emitted=True,
        )

    def _get_previous_state_hash(self, execution: ExecutionEventDB) -> Optional[str]:
        """
        Get the previous state hash for an execution.

        This would ideally be computed and stored at execution time.
        For now, we try to get it from the original report if available.

        Args:
            execution: The execution event

        Returns:
            Previous state hash or None
        """
        if not execution.report_id:
            return None

        # Get the original report
        report = self.db.query(ReportDB).filter(
            ReportDB.id == execution.report_id
        ).first()

        if not report or not report.accounts_json:
            return None

        # Find the account in the original report
        for account in report.accounts_json:
            fingerprint = self.create_account_fingerprint(account)
            if fingerprint == execution.account_fingerprint:
                return self.compute_account_state_hash(account)

        return None

    def _estimate_utilization_impact(
        self,
        execution: ExecutionEventDB,
        removed: bool = False,
        new_account: Optional[Dict[str, Any]] = None,
    ) -> Optional[float]:
        """
        Estimate the impact on credit utilization.

        Rough estimation based on account type and limit.
        Full calculation would require knowing total limits/balances.

        Args:
            execution: The execution event
            removed: Was the account removed?
            new_account: New account state if available

        Returns:
            Estimated utilization change (-1 to 1) or None
        """
        # This is a simplified estimation
        # A proper calculation would track total revolving limits and balances
        if execution.furnisher_type in ['COLLECTION', 'DEBT_BUYER']:
            # Removing a collection doesn't directly affect utilization
            return None

        if removed:
            # Removing a revolving account could increase utilization
            # by reducing available credit
            return 0.05  # Slight increase

        return None

    def _compute_durability_score(self, outcome: FinalOutcome) -> int:
        """
        Compute initial durability score based on outcome.

        Durability is tracked over time as deletions may be reinserted.
        Initial score is based on outcome type.

        Args:
            outcome: The final outcome

        Returns:
            Durability score 0-100
        """
        if outcome == FinalOutcome.DELETED:
            return 80  # High initial score, may decrease on reinsertion
        elif outcome == FinalOutcome.UPDATED:
            return 90  # Very durable - item was cured not deleted
        elif outcome == FinalOutcome.VERIFIED:
            return 50  # Medium - verified means it wasn't deleted
        else:
            return 0


def detect_reinsertion(
    db: Session,
    user_id: str,
    new_accounts: List[Dict[str, Any]],
    days_threshold: int = 90,
) -> List[Tuple[ExecutionOutcomeDB, Dict[str, Any]]]:
    """
    Detect reinsertions of previously deleted accounts.

    Checks for accounts that:
    1. Were previously marked as DELETED
    2. Reappear in a new report within the threshold period

    Args:
        db: Database session
        user_id: User to check
        new_accounts: Accounts from new report
        days_threshold: Days to look back for deletions

    Returns:
        List of (outcome, account) tuples for reinserted items
    """
    detector = ExecutionOutcomeDetector(db)
    ledger = ExecutionLedgerService(db)

    # Build fingerprint set for new accounts
    new_fingerprints = set()
    fingerprint_to_account = {}
    for account in new_accounts:
        fp = detector.create_account_fingerprint(account)
        if fp and fp != '|':
            new_fingerprints.add(fp)
            fingerprint_to_account[fp] = account

    # Find recent DELETED outcomes
    from sqlalchemy import and_
    from datetime import timedelta

    cutoff = datetime.now(timezone.utc) - timedelta(days=days_threshold)

    deleted_outcomes = (
        db.query(ExecutionOutcomeDB)
        .join(ExecutionEventDB)
        .filter(
            ExecutionEventDB.user_id == user_id,
            ExecutionOutcomeDB.final_outcome == FinalOutcome.DELETED,
            ExecutionOutcomeDB.resolved_at >= cutoff,
        )
        .all()
    )

    reinsertions = []

    for outcome in deleted_outcomes:
        execution = outcome.execution
        if not execution or not execution.account_fingerprint:
            continue

        if execution.account_fingerprint in new_fingerprints:
            # Reinsertion detected!
            account = fingerprint_to_account[execution.account_fingerprint]

            # Emit REINSERTED outcome
            days_since_deletion = (datetime.now(timezone.utc) - outcome.resolved_at).days

            ledger.emit_execution_outcome(
                execution_id=execution.id,
                dispute_session_id=execution.dispute_session_id,
                final_outcome=FinalOutcome.REINSERTED,
                resolved_at=datetime.now(timezone.utc),
                previous_state_hash=outcome.current_state_hash,
                current_state_hash=detector.compute_account_state_hash(account),
                days_until_reinsertion=days_since_deletion,
                durability_score=0,  # Failed durability
                account_removed=False,
            )

            reinsertions.append((outcome, account))

    return reinsertions
