"""
Dispute Session Service (B7 Execution Ledger)

Generates and manages dispute session IDs - the correlation ID that
links the entire enforcement lifecycle.

Generated at: Copilot decision time
Passed to: Response Engine, Ledger, Bureau intake, Re-audit diffing
Survives: Suppressions, Retries, Silent updates, Delayed responses

This solves race conditions and attribution permanently.
"""
from uuid import uuid4
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from ...models.db_models import (
    ExecutionEventDB,
    ExecutionSuppressionEventDB,
    ExecutionResponseDB,
    ExecutionOutcomeDB,
    ExecutionStatus,
)


class DisputeSessionService:
    """
    Generates and manages dispute session IDs.
    Called at Copilot decision time to create correlation ID.
    """

    def __init__(self, db: Session):
        self.db = db

    def create_session(
        self,
        user_id: str,
        report_id: str,
        credit_goal: str,
    ) -> str:
        """
        Generate a new dispute session ID (UUID).

        Called at Copilot decision time. This ID will be passed through:
        - Suppression events (if action blocked)
        - Execution events (at confirm_mailing)
        - Response events (at log_response)
        - Outcome events (at report re-ingestion)

        Args:
            user_id: The user initiating the dispute session
            report_id: The report being disputed
            credit_goal: The user's credit goal at decision time

        Returns:
            A new UUID string to correlate all events in this session
        """
        return str(uuid4())

    def get_active_sessions(self, user_id: str) -> List[str]:
        """
        Get all active dispute sessions for a user.

        A session is active if it has executions in PENDING status.

        Args:
            user_id: The user to query

        Returns:
            List of dispute_session_id strings
        """
        results = (
            self.db.query(ExecutionEventDB.dispute_session_id)
            .filter(
                ExecutionEventDB.user_id == user_id,
                ExecutionEventDB.execution_status == ExecutionStatus.PENDING,
            )
            .distinct()
            .all()
        )
        return [r[0] for r in results]

    def get_session_status(self, dispute_session_id: str) -> dict:
        """
        Get the status of a dispute session.

        Args:
            dispute_session_id: The session to query

        Returns:
            Dictionary with session status information
        """
        # Count executions by status
        executions = (
            self.db.query(ExecutionEventDB)
            .filter(ExecutionEventDB.dispute_session_id == dispute_session_id)
            .all()
        )

        # Count responses
        response_count = (
            self.db.query(ExecutionResponseDB)
            .filter(ExecutionResponseDB.dispute_session_id == dispute_session_id)
            .count()
        )

        # Count outcomes
        outcome_count = (
            self.db.query(ExecutionOutcomeDB)
            .filter(ExecutionOutcomeDB.dispute_session_id == dispute_session_id)
            .count()
        )

        # Count suppressions
        suppression_count = (
            self.db.query(ExecutionSuppressionEventDB)
            .filter(ExecutionSuppressionEventDB.dispute_session_id == dispute_session_id)
            .count()
        )

        # Aggregate execution statuses
        status_counts = {}
        for exec in executions:
            status = exec.execution_status.value if exec.execution_status else "UNKNOWN"
            status_counts[status] = status_counts.get(status, 0) + 1

        return {
            "dispute_session_id": dispute_session_id,
            "execution_count": len(executions),
            "execution_statuses": status_counts,
            "response_count": response_count,
            "outcome_count": outcome_count,
            "suppression_count": suppression_count,
            "is_active": status_counts.get("PENDING", 0) > 0,
        }

    def get_sessions_by_account_fingerprint(
        self,
        account_fingerprint: str,
        user_id: Optional[str] = None,
    ) -> List[str]:
        """
        Find all dispute sessions that targeted a specific account.

        Useful for checking if there's already an action in flight
        for a particular account.

        Args:
            account_fingerprint: The account fingerprint to query
            user_id: Optional - filter by user

        Returns:
            List of dispute_session_id strings
        """
        query = (
            self.db.query(ExecutionEventDB.dispute_session_id)
            .filter(ExecutionEventDB.account_fingerprint == account_fingerprint)
        )

        if user_id:
            query = query.filter(ExecutionEventDB.user_id == user_id)

        results = query.distinct().all()
        return [r[0] for r in results]

    def has_pending_execution(
        self,
        account_fingerprint: str,
        user_id: str,
    ) -> bool:
        """
        Check if there's already a pending execution for an account.

        Used for DUPLICATE_IN_FLIGHT suppression check.

        Args:
            account_fingerprint: The account to check
            user_id: The user's ID

        Returns:
            True if there's a pending execution for this account
        """
        count = (
            self.db.query(ExecutionEventDB)
            .filter(
                ExecutionEventDB.account_fingerprint == account_fingerprint,
                ExecutionEventDB.user_id == user_id,
                ExecutionEventDB.execution_status == ExecutionStatus.PENDING,
            )
            .count()
        )
        return count > 0

    def get_last_execution_date(
        self,
        account_fingerprint: str,
        user_id: str,
    ) -> Optional[datetime]:
        """
        Get the date of the last execution for an account.

        Used for cooldown checks.

        Args:
            account_fingerprint: The account to check
            user_id: The user's ID

        Returns:
            The executed_at timestamp of the most recent execution, or None
        """
        result = (
            self.db.query(ExecutionEventDB.executed_at)
            .filter(
                ExecutionEventDB.account_fingerprint == account_fingerprint,
                ExecutionEventDB.user_id == user_id,
            )
            .order_by(ExecutionEventDB.executed_at.desc())
            .first()
        )
        return result[0] if result else None
