"""
Test Suite for B7 Execution Ledger

Tests the append-only telemetry layer for enforcement outcomes.

Key tests:
1. Dispute session ID generation
2. Suppression event emission
3. Execution event emission
4. Response event emission
5. Outcome event emission
6. Downstream outcome emission
7. Signal aggregation
8. Copilot signal reading
9. Outcome detection from reports
10. Snapshot hashing consistency
"""
import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from unittest.mock import MagicMock, patch

# Import models and enums
from app.models.db_models import (
    SuppressionReason,
    ExecutionStatus,
    FinalOutcome,
    DownstreamEventType,
    ExecutionSuppressionEventDB,
    ExecutionEventDB,
    ExecutionResponseDB,
    ExecutionOutcomeDB,
    DownstreamOutcomeDB,
    CopilotSignalCacheDB,
)

# Import services
from app.services.enforcement.dispute_session import DisputeSessionService
from app.services.enforcement.execution_ledger import ExecutionLedgerService
from app.services.enforcement.execution_outcome_detector import (
    ExecutionOutcomeDetector,
    OutcomeDetectionResult,
)
from app.services.enforcement.ledger_signal_aggregator import (
    LedgerSignalAggregator,
    SignalResult,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def mock_db():
    """Create a mock database session."""
    db = MagicMock()
    db.add = MagicMock()
    db.flush = MagicMock()
    db.commit = MagicMock()
    db.query = MagicMock()
    return db


@pytest.fixture
def session_service(mock_db):
    """Create DisputeSessionService instance."""
    return DisputeSessionService(mock_db)


@pytest.fixture
def ledger_service(mock_db):
    """Create ExecutionLedgerService instance."""
    return ExecutionLedgerService(mock_db)


@pytest.fixture
def outcome_detector(mock_db):
    """Create ExecutionOutcomeDetector instance."""
    return ExecutionOutcomeDetector(mock_db)


@pytest.fixture
def signal_aggregator(mock_db):
    """Create LedgerSignalAggregator instance."""
    return LedgerSignalAggregator(mock_db)


# =============================================================================
# DISPUTE SESSION ID TESTS
# =============================================================================

class TestDisputeSessionService:
    """Test dispute session ID generation and management."""

    def test_create_session_returns_uuid(self, session_service):
        """Create session returns a valid UUID string."""
        session_id = session_service.create_session(
            user_id="user-123",
            report_id="report-456",
            credit_goal="mortgage",
        )

        assert session_id is not None
        assert isinstance(session_id, str)
        assert len(session_id) == 36  # UUID format

    def test_create_session_is_unique(self, session_service):
        """Each session ID should be unique."""
        sessions = set()
        for _ in range(100):
            session_id = session_service.create_session(
                user_id="user-123",
                report_id="report-456",
                credit_goal="mortgage",
            )
            sessions.add(session_id)

        assert len(sessions) == 100


# =============================================================================
# LEDGER SERVICE TESTS
# =============================================================================

class TestExecutionLedgerService:
    """Test execution ledger emit methods."""

    def test_emit_suppression_event(self, ledger_service, mock_db):
        """Suppression events are created correctly."""
        event = ledger_service.emit_suppression_event(
            dispute_session_id="session-123",
            user_id="user-456",
            suppression_reason=SuppressionReason.DUPLICATE_IN_FLIGHT,
            credit_goal="mortgage",
        )

        assert event is not None
        assert event.dispute_session_id == "session-123"
        assert event.user_id == "user-456"
        assert event.suppression_reason == SuppressionReason.DUPLICATE_IN_FLIGHT
        assert event.credit_goal == "mortgage"
        mock_db.add.assert_called()

    def test_emit_execution_event(self, ledger_service, mock_db):
        """Execution events are created correctly."""
        executed_at = datetime.now(timezone.utc)

        event = ledger_service.emit_execution_event(
            dispute_session_id="session-123",
            user_id="user-456",
            executed_at=executed_at,
            action_type="DELETE_DEMAND",
            credit_goal="mortgage",
            creditor_name="Test Creditor",
            account_fingerprint="TEST|1234",
        )

        assert event is not None
        assert event.dispute_session_id == "session-123"
        assert event.user_id == "user-456"
        assert event.action_type == "DELETE_DEMAND"
        assert event.credit_goal == "mortgage"
        assert event.creditor_name == "Test Creditor"
        assert event.execution_status == ExecutionStatus.PENDING
        mock_db.add.assert_called()

    def test_emit_execution_response(self, ledger_service, mock_db):
        """Response events are created correctly."""
        response = ledger_service.emit_execution_response(
            execution_id="exec-123",
            dispute_session_id="session-123",
            response_type="DELETED",
            response_received_at=datetime.now(timezone.utc),
            bureau="EXPERIAN",
            dofd_changed=True,
        )

        assert response is not None
        assert response.execution_id == "exec-123"
        assert response.dispute_session_id == "session-123"
        assert response.response_type == "DELETED"
        assert response.dofd_changed == True
        mock_db.add.assert_called()

    def test_emit_execution_outcome(self, ledger_service, mock_db):
        """Outcome events are created correctly."""
        outcome = ledger_service.emit_execution_outcome(
            execution_id="exec-123",
            dispute_session_id="session-123",
            final_outcome=FinalOutcome.DELETED,
            resolved_at=datetime.now(timezone.utc),
            account_removed=True,
            durability_score=80,
        )

        assert outcome is not None
        assert outcome.execution_id == "exec-123"
        assert outcome.final_outcome == FinalOutcome.DELETED
        assert outcome.account_removed == True
        assert outcome.durability_score == 80
        mock_db.add.assert_called()

    def test_emit_downstream_outcome(self, ledger_service, mock_db):
        """Downstream outcomes are created correctly."""
        outcome = ledger_service.emit_downstream_outcome(
            user_id="user-456",
            credit_goal="mortgage",
            event_type=DownstreamEventType.LOAN_APPROVED,
            reported_at=datetime.now(timezone.utc),
            notes="30-year fixed approved!",
        )

        assert outcome is not None
        assert outcome.user_id == "user-456"
        assert outcome.event_type == DownstreamEventType.LOAN_APPROVED
        assert outcome.notes == "30-year fixed approved!"
        mock_db.add.assert_called()


# =============================================================================
# OUTCOME DETECTOR TESTS
# =============================================================================

class TestExecutionOutcomeDetector:
    """Test outcome detection from reports."""

    def test_compute_account_state_hash(self, outcome_detector):
        """State hash is computed deterministically."""
        account = {
            "account_number": "1234567890",
            "creditor_name": "Test Creditor",
            "balance": 1000,
            "account_status": "OPEN",
        }

        hash1 = outcome_detector.compute_account_state_hash(account)
        hash2 = outcome_detector.compute_account_state_hash(account)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex length

    def test_state_hash_differs_on_change(self, outcome_detector):
        """State hash changes when account data changes."""
        account1 = {
            "account_number": "1234567890",
            "creditor_name": "Test Creditor",
            "balance": 1000,
        }
        account2 = {
            "account_number": "1234567890",
            "creditor_name": "Test Creditor",
            "balance": 0,  # Changed
        }

        hash1 = outcome_detector.compute_account_state_hash(account1)
        hash2 = outcome_detector.compute_account_state_hash(account2)

        assert hash1 != hash2

    def test_create_account_fingerprint(self, outcome_detector):
        """Account fingerprint is created correctly."""
        account = {
            "account_number": "1234567890",
            "creditor_name": "Test Creditor",
        }

        fingerprint = outcome_detector.create_account_fingerprint(account)

        assert fingerprint == "TEST CREDITOR|1234567890"

    def test_is_negative_status(self, outcome_detector):
        """Negative status detection works."""
        negative_account = {"account_status": "COLLECTION"}
        positive_account = {"account_status": "OPEN"}

        assert outcome_detector.is_negative_status(negative_account) == True
        assert outcome_detector.is_negative_status(positive_account) == False


# =============================================================================
# SIGNAL AGGREGATOR TESTS
# =============================================================================

class TestLedgerSignalAggregator:
    """Test signal aggregation."""

    def test_signal_result_dataclass(self):
        """SignalResult dataclass works correctly."""
        result = SignalResult(
            signal_type="reinsertion_rate",
            signal_value=0.25,
            sample_count=100,
            scope_type="GLOBAL",
            scope_value=None,
        )

        assert result.signal_type == "reinsertion_rate"
        assert result.signal_value == 0.25
        assert result.sample_count == 100

    def test_min_sample_size_constant(self, signal_aggregator):
        """Minimum sample size is set correctly."""
        assert signal_aggregator.MIN_SAMPLE_SIZE == 5


# =============================================================================
# SUPPRESSION REASON TESTS
# =============================================================================

class TestSuppressionReasons:
    """Test suppression reason enum."""

    def test_all_suppression_reasons_exist(self):
        """All expected suppression reasons are defined."""
        expected = [
            "DUPLICATE_IN_FLIGHT",
            "COOLDOWN_ACTIVE",
            "DOFD_GATE_BLOCK",
            "OWNERSHIP_GATE_BLOCK",
            "VERIFICATION_RISK_SPIKE",
            "COMPLIANCE_HOLD",
        ]

        for reason in expected:
            assert hasattr(SuppressionReason, reason)
            assert SuppressionReason[reason].value == reason


# =============================================================================
# EXECUTION STATUS TESTS
# =============================================================================

class TestExecutionStatus:
    """Test execution status enum."""

    def test_all_statuses_exist(self):
        """All expected execution statuses are defined."""
        expected = ["PENDING", "RESPONDED", "ESCALATED", "CLOSED"]

        for status in expected:
            assert hasattr(ExecutionStatus, status)
            assert ExecutionStatus[status].value == status


# =============================================================================
# FINAL OUTCOME TESTS
# =============================================================================

class TestFinalOutcome:
    """Test final outcome enum."""

    def test_all_outcomes_exist(self):
        """All expected final outcomes are defined."""
        expected = ["DELETED", "VERIFIED", "UPDATED", "REINSERTED", "IGNORED"]

        for outcome in expected:
            assert hasattr(FinalOutcome, outcome)
            assert FinalOutcome[outcome].value == outcome


# =============================================================================
# DOWNSTREAM EVENT TYPE TESTS
# =============================================================================

class TestDownstreamEventType:
    """Test downstream event type enum."""

    def test_all_event_types_exist(self):
        """All expected downstream event types are defined."""
        expected = ["LOAN_APPROVED", "APARTMENT_APPROVED", "EMPLOYMENT_CLEARED"]

        for event_type in expected:
            assert hasattr(DownstreamEventType, event_type)
            assert DownstreamEventType[event_type].value == event_type


# =============================================================================
# COPILOT VERSION TESTS
# =============================================================================

class TestCopilotVersion:
    """Test Copilot version tracking."""

    def test_copilot_version_is_set(self, ledger_service):
        """Copilot version is set on the service."""
        assert ledger_service.COPILOT_VERSION == "2.0.0"


# =============================================================================
# APPEND-ONLY CONSTRAINT TESTS
# =============================================================================

class TestAppendOnlyConstraints:
    """Test that ledger maintains append-only semantics."""

    def test_suppression_event_has_created_at(self, ledger_service, mock_db):
        """Suppression events have created_at timestamp."""
        event = ledger_service.emit_suppression_event(
            dispute_session_id="session-123",
            user_id="user-456",
            suppression_reason=SuppressionReason.COOLDOWN_ACTIVE,
            credit_goal="mortgage",
        )

        # The model should set created_at automatically
        assert hasattr(event, 'created_at')

    def test_execution_event_has_created_at(self, ledger_service, mock_db):
        """Execution events have created_at timestamp."""
        event = ledger_service.emit_execution_event(
            dispute_session_id="session-123",
            user_id="user-456",
            executed_at=datetime.now(timezone.utc),
            action_type="DELETE_DEMAND",
            credit_goal="mortgage",
        )

        assert hasattr(event, 'created_at')


# =============================================================================
# CORRELATION ID TESTS
# =============================================================================

class TestCorrelationIds:
    """Test dispute_session_id correlation."""

    def test_all_events_share_session_id(self, ledger_service, mock_db):
        """All events in a session share the same session ID."""
        session_id = "session-correlate-123"

        suppression = ledger_service.emit_suppression_event(
            dispute_session_id=session_id,
            user_id="user-1",
            suppression_reason=SuppressionReason.DUPLICATE_IN_FLIGHT,
            credit_goal="mortgage",
        )

        execution = ledger_service.emit_execution_event(
            dispute_session_id=session_id,
            user_id="user-1",
            executed_at=datetime.now(timezone.utc),
            action_type="DELETE_DEMAND",
            credit_goal="mortgage",
        )

        assert suppression.dispute_session_id == session_id
        assert execution.dispute_session_id == session_id


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
