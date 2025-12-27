"""
Execution Ledger Service (B7)

Core append-only telemetry layer for capturing real-world enforcement outcomes.

Core Principles:
1. The Ledger records reality. It never decides. It never edits history.
2. Executions are born at send-time (confirm_mailing), not plan-time.
3. Append-only - no updates or deletes.
4. Event-sourced - every state change is a new record.
5. Copilot never writes - ledger feeds inputs only.
6. Response Engine is sole executor.

MANDATORY CONSTRAINTS:
- No raw letter text in ledger
- No probabilities
- No ML inference
- No manual overrides
- No retroactive edits
"""
from uuid import uuid4
from datetime import datetime
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import func

from ...models.db_models import (
    ExecutionSuppressionEventDB,
    ExecutionEventDB,
    ExecutionResponseDB,
    ExecutionOutcomeDB,
    DownstreamOutcomeDB,
    CopilotSignalCacheDB,
    SuppressionReason,
    ExecutionStatus,
    FinalOutcome,
    DownstreamEventType,
)


class ExecutionLedgerService:
    """
    Core service for the append-only execution ledger.

    Provides emit methods for each source:
    - SOURCE 0: Suppression events
    - SOURCE 1: Execution events
    - SOURCE 2: Response events
    - SOURCE 3: Outcome events
    - SOURCE 4: Downstream events

    Also provides read-only interface for Copilot signals.
    """

    COPILOT_VERSION = "2.0.0"

    def __init__(self, db: Session):
        self.db = db

    # =========================================================================
    # SOURCE 0: Suppression Events
    # =========================================================================

    def emit_suppression_event(
        self,
        dispute_session_id: str,
        user_id: str,
        suppression_reason: SuppressionReason,
        credit_goal: str,
        suppressed_at: Optional[datetime] = None,
        report_id: Optional[str] = None,
        account_id: Optional[str] = None,
    ) -> ExecutionSuppressionEventDB:
        """
        Emit a suppression event (SOURCE 0).

        Records intentional non-action by the system.
        NOT user hesitation. NOT failure. Intentional restraint.

        Does NOT feed Copilot. Admin + audit only.

        Args:
            dispute_session_id: Correlation ID for the session
            user_id: User whose action was suppressed
            suppression_reason: Why the action was suppressed
            credit_goal: User's credit goal at decision time
            suppressed_at: When suppression occurred (default: now)
            report_id: Optional report context
            account_id: Optional account context

        Returns:
            The created suppression event record
        """
        event = ExecutionSuppressionEventDB(
            id=str(uuid4()),
            dispute_session_id=dispute_session_id,
            user_id=user_id,
            report_id=report_id,
            account_id=account_id,
            credit_goal=credit_goal,
            copilot_version=self.COPILOT_VERSION,
            suppression_reason=suppression_reason,
            suppressed_at=suppressed_at or datetime.utcnow(),
        )
        self.db.add(event)
        self.db.flush()  # Get ID without committing
        return event

    # =========================================================================
    # SOURCE 1: Execution Events
    # =========================================================================

    def emit_execution_event(
        self,
        dispute_session_id: str,
        user_id: str,
        executed_at: datetime,
        action_type: str,
        credit_goal: str,
        report_id: Optional[str] = None,
        account_id: Optional[str] = None,
        dispute_id: Optional[str] = None,
        letter_id: Optional[str] = None,
        target_state_hash: Optional[str] = None,
        response_posture: Optional[str] = None,
        violation_type: Optional[str] = None,
        contradiction_rule: Optional[str] = None,
        bureau: Optional[str] = None,
        furnisher_type: Optional[str] = None,
        creditor_name: Optional[str] = None,
        account_fingerprint: Optional[str] = None,
        gate_applied: Optional[Dict[str, bool]] = None,
        risk_flags: Optional[List[str]] = None,
        document_hash: Optional[str] = None,
        artifact_pointer: Optional[str] = None,
        due_by: Optional[datetime] = None,
    ) -> ExecutionEventDB:
        """
        Emit an execution event (SOURCE 1).

        Born at confirm_mailing(). The AUTHORITY MOMENT.
        Anything not sent does not exist to the Ledger.

        Args:
            dispute_session_id: Correlation ID for the session
            user_id: User who executed the action
            executed_at: When the letter was confirmed mailed
            action_type: Type of action (DELETE_DEMAND, CORRECT_DEMAND, etc.)
            credit_goal: User's credit goal at execution time
            report_id: The report context
            account_id: Account being disputed
            dispute_id: Link to dispute record
            letter_id: Link to letter record
            target_state_hash: SHA256 of target credit state
            response_posture: Expected response posture
            violation_type: Type of violation being disputed
            contradiction_rule: Rule code (T1, D1, M2, etc.)
            bureau: Target bureau
            furnisher_type: Type of furnisher
            creditor_name: Name of creditor
            account_fingerprint: Unique account identifier
            gate_applied: Which gates were applied
            risk_flags: Risk flags at send time
            document_hash: SHA256 of the letter
            artifact_pointer: Path to stored letter
            due_by: Response deadline

        Returns:
            The created execution event record
        """
        event = ExecutionEventDB(
            id=str(uuid4()),
            dispute_session_id=dispute_session_id,
            user_id=user_id,
            report_id=report_id,
            account_id=account_id,
            dispute_id=dispute_id,
            letter_id=letter_id,
            credit_goal=credit_goal,
            target_state_hash=target_state_hash,
            copilot_version=self.COPILOT_VERSION,
            action_type=action_type,
            response_posture=response_posture,
            violation_type=violation_type,
            contradiction_rule=contradiction_rule,
            bureau=bureau,
            furnisher_type=furnisher_type,
            creditor_name=creditor_name,
            account_fingerprint=account_fingerprint,
            gate_applied=gate_applied,
            risk_flags=risk_flags,
            document_hash=document_hash,
            artifact_pointer=artifact_pointer,
            executed_at=executed_at,
            due_by=due_by,
            execution_status=ExecutionStatus.PENDING,
        )
        self.db.add(event)
        self.db.flush()
        return event

    # =========================================================================
    # SOURCE 2: Response Events
    # =========================================================================

    def emit_execution_response(
        self,
        execution_id: str,
        dispute_session_id: str,
        response_type: str,
        response_received_at: datetime,
        bureau: Optional[str] = None,
        response_reason: Optional[str] = None,
        document_hash: Optional[str] = None,
        artifact_pointer: Optional[str] = None,
        balance_changed: bool = False,
        dofd_changed: bool = False,
        status_changed: bool = False,
        reinsertion_flag: bool = False,
        # TIER 2: Examiner Standard Fields
        examiner_standard_result: Optional[str] = None,
        examiner_failure_reason: Optional[str] = None,
        response_layer_violation_id: Optional[str] = None,
        escalation_basis: Optional[str] = None,
    ) -> ExecutionResponseDB:
        """
        Emit an execution response (SOURCE 2).

        Emitted when entity response is logged.
        Tracks what the bureau/furnisher actually said.

        Args:
            execution_id: Link to the execution event
            dispute_session_id: Correlation ID for the session
            response_type: Type of response (DELETED, VERIFIED, etc.)
            response_received_at: When response was received
            bureau: Which bureau responded
            response_reason: Optional reason text from entity
            document_hash: SHA256 of response document
            artifact_pointer: Path to evidence file
            balance_changed: Did balance change?
            dofd_changed: Did DOFD change?
            status_changed: Did status change?
            reinsertion_flag: Was reinsertion detected?
            examiner_standard_result: PASS, FAIL_PERFUNCTORY, etc. (Tier 2)
            examiner_failure_reason: Human-readable failure reason (Tier 2)
            response_layer_violation_id: UUID of Tier 2 violation created
            escalation_basis: What triggered escalation eligibility (Tier 2)

        Returns:
            The created response record
        """
        response = ExecutionResponseDB(
            id=str(uuid4()),
            execution_id=execution_id,
            dispute_session_id=dispute_session_id,
            bureau=bureau,
            response_type=response_type,
            response_reason=response_reason,
            document_hash=document_hash,
            artifact_pointer=artifact_pointer,
            balance_changed=balance_changed,
            dofd_changed=dofd_changed,
            status_changed=status_changed,
            reinsertion_flag=reinsertion_flag,
            response_received_at=response_received_at,
            # Tier 2 Examiner fields
            examiner_standard_result=examiner_standard_result,
            examiner_failure_reason=examiner_failure_reason,
            response_layer_violation_id=response_layer_violation_id,
            escalation_basis=escalation_basis,
        )
        self.db.add(response)
        self.db.flush()

        # Update execution status to RESPONDED
        execution = self.db.query(ExecutionEventDB).filter(
            ExecutionEventDB.id == execution_id
        ).first()
        if execution and execution.execution_status == ExecutionStatus.PENDING:
            execution.execution_status = ExecutionStatus.RESPONDED

        return response

    # =========================================================================
    # SOURCE 3: Outcome Events
    # =========================================================================

    def emit_execution_outcome(
        self,
        execution_id: str,
        dispute_session_id: str,
        final_outcome: FinalOutcome,
        resolved_at: datetime,
        new_report_id: Optional[str] = None,
        previous_state_hash: Optional[str] = None,
        current_state_hash: Optional[str] = None,
        days_until_reinsertion: Optional[int] = None,
        durability_score: Optional[int] = None,
        account_removed: bool = False,
        negative_status_removed: bool = False,
        utilization_impact: Optional[float] = None,
    ) -> ExecutionOutcomeDB:
        """
        Emit an execution outcome (SOURCE 3).

        Emitted during report re-ingestion diff.
        Detects actual changes using snapshot verification.

        Args:
            execution_id: Link to the execution event
            dispute_session_id: Correlation ID for the session
            final_outcome: Final outcome classification
            resolved_at: When outcome was determined
            new_report_id: The new report that revealed the outcome
            previous_state_hash: SHA256 of account state before
            current_state_hash: SHA256 of account state after
            days_until_reinsertion: If reinserted, days until return
            durability_score: 0-100, higher = more durable
            account_removed: Was account removed entirely?
            negative_status_removed: Was negative status cleared?
            utilization_impact: Change in utilization ratio

        Returns:
            The created outcome record
        """
        outcome = ExecutionOutcomeDB(
            id=str(uuid4()),
            execution_id=execution_id,
            dispute_session_id=dispute_session_id,
            new_report_id=new_report_id,
            final_outcome=final_outcome,
            previous_state_hash=previous_state_hash,
            current_state_hash=current_state_hash,
            days_until_reinsertion=days_until_reinsertion,
            durability_score=durability_score,
            account_removed=account_removed,
            negative_status_removed=negative_status_removed,
            utilization_impact=utilization_impact,
            resolved_at=resolved_at,
        )
        self.db.add(outcome)
        self.db.flush()

        # Update execution status to CLOSED
        execution = self.db.query(ExecutionEventDB).filter(
            ExecutionEventDB.id == execution_id
        ).first()
        if execution:
            execution.execution_status = ExecutionStatus.CLOSED

        return outcome

    # =========================================================================
    # SOURCE 4: Downstream Events
    # =========================================================================

    def emit_downstream_outcome(
        self,
        user_id: str,
        credit_goal: str,
        event_type: DownstreamEventType,
        reported_at: datetime,
        dispute_session_id: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> DownstreamOutcomeDB:
        """
        Emit a downstream outcome (SOURCE 4).

        User-reported downstream results (loan approvals, etc.).
        Never used directly for enforcement decisions.
        Informational only - not fed to Copilot.

        Args:
            user_id: The user reporting the outcome
            credit_goal: User's credit goal
            event_type: Type of downstream event
            reported_at: When user reported the event
            dispute_session_id: Optional link to dispute session
            notes: Optional user notes

        Returns:
            The created downstream outcome record
        """
        outcome = DownstreamOutcomeDB(
            id=str(uuid4()),
            user_id=user_id,
            dispute_session_id=dispute_session_id,
            credit_goal=credit_goal,
            event_type=event_type,
            notes=notes,
            reported_at=reported_at,
        )
        self.db.add(outcome)
        self.db.flush()
        return outcome

    # =========================================================================
    # Copilot Signal Interface (READ-ONLY)
    # =========================================================================

    def get_all_copilot_signals(
        self,
        scope_type: str = "GLOBAL",
        scope_value: Optional[str] = None,
    ) -> Dict[str, float]:
        """
        Get all Copilot signals for a given scope.

        Copilot reads ONLY aggregated signals from the cache.
        Never reads: Suppression events, raw text, user IDs,
        downstream approvals, probabilities.

        Args:
            scope_type: GLOBAL, BUREAU, FURNISHER_TYPE, CREDITOR
            scope_value: Value for the scope (e.g., "EXPERIAN")

        Returns:
            Dictionary of signal_type -> signal_value
        """
        now = datetime.utcnow()

        query = self.db.query(CopilotSignalCacheDB).filter(
            CopilotSignalCacheDB.scope_type == scope_type,
            CopilotSignalCacheDB.window_end >= now,
        )

        if scope_value:
            query = query.filter(CopilotSignalCacheDB.scope_value == scope_value)
        else:
            query = query.filter(CopilotSignalCacheDB.scope_value.is_(None))

        # Only return non-expired signals
        query = query.filter(
            (CopilotSignalCacheDB.expires_at.is_(None)) |
            (CopilotSignalCacheDB.expires_at > now)
        )

        results = query.all()

        return {r.signal_type: r.signal_value for r in results}

    def get_signal(
        self,
        signal_type: str,
        scope_type: str = "GLOBAL",
        scope_value: Optional[str] = None,
        default: float = 0.0,
    ) -> float:
        """
        Get a specific Copilot signal.

        Args:
            signal_type: The signal to retrieve
            scope_type: GLOBAL, BUREAU, FURNISHER_TYPE, CREDITOR
            scope_value: Value for the scope
            default: Default value if signal not found

        Returns:
            The signal value, or default if not found
        """
        signals = self.get_all_copilot_signals(scope_type, scope_value)
        return signals.get(signal_type, default)

    # =========================================================================
    # Query Helpers (for internal use)
    # =========================================================================

    def get_executions_by_fingerprint(
        self,
        account_fingerprint: str,
        user_id: Optional[str] = None,
        status: Optional[ExecutionStatus] = None,
    ) -> List[ExecutionEventDB]:
        """
        Get all executions for an account fingerprint.

        Args:
            account_fingerprint: The account to query
            user_id: Optional user filter
            status: Optional status filter

        Returns:
            List of execution events
        """
        query = self.db.query(ExecutionEventDB).filter(
            ExecutionEventDB.account_fingerprint == account_fingerprint
        )

        if user_id:
            query = query.filter(ExecutionEventDB.user_id == user_id)

        if status:
            query = query.filter(ExecutionEventDB.execution_status == status)

        return query.order_by(ExecutionEventDB.executed_at.desc()).all()

    def get_pending_executions_for_user(
        self,
        user_id: str,
    ) -> List[ExecutionEventDB]:
        """
        Get all pending executions for a user.

        Args:
            user_id: The user to query

        Returns:
            List of pending execution events
        """
        return (
            self.db.query(ExecutionEventDB)
            .filter(
                ExecutionEventDB.user_id == user_id,
                ExecutionEventDB.execution_status == ExecutionStatus.PENDING,
            )
            .order_by(ExecutionEventDB.executed_at.desc())
            .all()
        )

    def get_execution_by_id(
        self,
        execution_id: str,
    ) -> Optional[ExecutionEventDB]:
        """
        Get an execution by its ID.

        Args:
            execution_id: The execution ID

        Returns:
            The execution event, or None
        """
        return (
            self.db.query(ExecutionEventDB)
            .filter(ExecutionEventDB.id == execution_id)
            .first()
        )

    def get_execution_for_dispute(
        self,
        dispute_id: str,
    ) -> Optional[ExecutionEventDB]:
        """
        Get the execution event linked to a dispute.

        Args:
            dispute_id: The dispute ID

        Returns:
            The execution event, or None
        """
        return (
            self.db.query(ExecutionEventDB)
            .filter(ExecutionEventDB.dispute_id == dispute_id)
            .first()
        )
