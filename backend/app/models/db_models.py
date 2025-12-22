"""
Credit Engine 2.0 - SQLAlchemy ORM Models
PostgreSQL database models for persistent storage
"""
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, String, Integer, Float, DateTime, Text, JSON, ForeignKey, Enum as SQLEnum, Boolean, Date
from sqlalchemy.orm import relationship
from ..database import Base


# =============================================================================
# ENUMS FOR DISPUTE/ENFORCEMENT SYSTEM
# =============================================================================

class EntityType(str, Enum):
    """Entity types for dispute routing."""
    CRA = "CRA"
    FURNISHER = "FURNISHER"
    COLLECTOR = "COLLECTOR"


class ResponseType(str, Enum):
    """Response types from entities."""
    DELETED = "DELETED"
    VERIFIED = "VERIFIED"
    UPDATED = "UPDATED"
    INVESTIGATING = "INVESTIGATING"
    NO_RESPONSE = "NO_RESPONSE"
    REJECTED = "REJECTED"
    REINSERTION = "REINSERTION"


class DisputeSource(str, Enum):
    """Source of dispute submission."""
    DIRECT = "DIRECT"
    ANNUAL_CREDIT_REPORT = "ANNUAL_CREDIT_REPORT"


class DisputeStatus(str, Enum):
    """Overall dispute status."""
    OPEN = "OPEN"
    RESPONDED = "RESPONDED"
    BREACHED = "BREACHED"
    CLOSED = "CLOSED"


class EscalationState(str, Enum):
    """States in the escalation state machine."""
    DETECTED = "DETECTED"
    DISPUTED = "DISPUTED"
    RESPONDED = "RESPONDED"
    NO_RESPONSE = "NO_RESPONSE"
    EVALUATED = "EVALUATED"
    NON_COMPLIANT = "NON_COMPLIANT"
    PROCEDURAL_ENFORCEMENT = "PROCEDURAL_ENFORCEMENT"
    SUBSTANTIVE_ENFORCEMENT = "SUBSTANTIVE_ENFORCEMENT"
    REGULATORY_ESCALATION = "REGULATORY_ESCALATION"
    LITIGATION_READY = "LITIGATION_READY"
    RESOLVED_DELETED = "RESOLVED_DELETED"
    RESOLVED_CURED = "RESOLVED_CURED"


class ReinsertionWatchStatus(str, Enum):
    """Status of reinsertion monitoring."""
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    REINSERTION_DETECTED = "REINSERTION_DETECTED"
    NOTICE_RECEIVED = "NOTICE_RECEIVED"


class ActorType(str, Enum):
    """Actor types for paper trail."""
    USER = "USER"
    SYSTEM = "SYSTEM"
    ENTITY = "ENTITY"


class UserDB(Base):
    """User account model with full profile for audit engine integration."""
    __tablename__ = "users"

    id = Column(String(36), primary_key=True)  # UUID
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # ==========================================================================
    # IDENTITY INFORMATION - Fuels "Mixed File" detection
    # ==========================================================================
    first_name = Column(String(100), nullable=True)
    middle_name = Column(String(100), nullable=True)  # Critical for mixed file detection
    last_name = Column(String(100), nullable=True)
    suffix = Column(String(10), nullable=True)  # Jr, Sr, II, III, IV - Critical for Jr/Sr mixed files
    date_of_birth = Column(DateTime, nullable=True)  # Distinguishes common names
    ssn_last_4 = Column(String(4), nullable=True)  # Last 4 digits only for matching
    phone = Column(String(20), nullable=True)

    # ==========================================================================
    # LOCATION INFORMATION - Fuels Statute of Limitations (SOL) engine
    # ==========================================================================
    # Current Address
    street_address = Column(String(255), nullable=True)
    unit = Column(String(50), nullable=True)  # Apt, Suite, etc.
    city = Column(String(100), nullable=True)
    state = Column(String(2), nullable=True)  # 2-letter code - FEEDS THE SOL ENGINE
    zip_code = Column(String(10), nullable=True)
    move_in_date = Column(DateTime, nullable=True)  # When they moved to current address

    # Previous Addresses (stored as JSON array for flexibility)
    # Format: [{"street": "...", "city": "...", "state": "XX", "zip": "..."}]
    previous_addresses = Column(JSON, nullable=True, default=list)

    # ==========================================================================
    # PROFILE COMPLETENESS
    # ==========================================================================
    profile_complete = Column(Integer, default=0)  # Percentage 0-100

    # ==========================================================================
    # CREDIT GOAL (for Copilot Engine)
    # ==========================================================================
    # User's financial goal - determines enforcement strategy prioritization
    # Valid values: mortgage, auto_loan, prime_credit_card, apartment_rental, employment, credit_hygiene
    credit_goal = Column(String(50), nullable=True, default="credit_hygiene")

    # Relationships
    reports = relationship("ReportDB", back_populates="user", cascade="all, delete-orphan")


class ReportDB(Base):
    """Persisted credit report."""
    __tablename__ = "reports"

    id = Column(String(36), primary_key=True)  # UUID
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    consumer_name = Column(String(255), nullable=False)
    consumer_address = Column(String(500))
    consumer_city = Column(String(100))
    consumer_state = Column(String(50))
    consumer_zip = Column(String(20))

    bureau = Column(String(50), default="transunion")
    report_date = Column(DateTime)
    source_file = Column(String(500))

    # Store full report data as JSON for flexibility
    report_data = Column(JSON)
    # Explicit accounts array for reliable retrieval
    accounts_json = Column(JSON)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("UserDB", back_populates="reports")
    audit_results = relationship("AuditResultDB", back_populates="report", cascade="all, delete-orphan")
    letters = relationship("LetterDB", back_populates="report")  # No cascade - letters persist when reports deleted


class AuditResultDB(Base):
    """Persisted audit results."""
    __tablename__ = "audit_results"

    id = Column(String(36), primary_key=True)  # UUID
    report_id = Column(String(36), ForeignKey("reports.id", ondelete="CASCADE"), nullable=False)

    bureau = Column(String(50), default="transunion")
    total_accounts_audited = Column(Integer, default=0)
    total_violations_found = Column(Integer, default=0)

    # Store violations as JSON array
    violations_data = Column(JSON)
    # Store cross-bureau discrepancies as JSON array
    discrepancies_data = Column(JSON)
    clean_accounts = Column(JSON)  # List of account IDs

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    report = relationship("ReportDB", back_populates="audit_results")


class LetterDB(Base):
    """Persisted generated letters."""
    __tablename__ = "letters"

    id = Column(String(36), primary_key=True)  # UUID
    report_id = Column(String(36), ForeignKey("reports.id", ondelete="SET NULL"), nullable=True)  # Letters persist when reports deleted
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)  # Direct ownership for orphaned letters
    dispute_id = Column(String(36), ForeignKey("disputes.id", ondelete="SET NULL"), nullable=True, index=True)  # For response letters

    content = Column(Text, nullable=False)
    edited_content = Column(Text, nullable=True)  # User-edited version
    bureau = Column(String(50), default="transunion")
    tone = Column(String(50), default="formal")
    letter_category = Column(String(20), default="dispute")  # "dispute" or "response"
    response_type = Column(String(50), nullable=True)  # For response letters: NO_RESPONSE, VERIFIED, etc.

    # Metadata
    accounts_disputed = Column(JSON)  # List of creditor names
    violations_cited = Column(JSON)   # List of violation types
    account_numbers = Column(JSON)    # List of masked account numbers (parallel to violations_cited)
    word_count = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    report = relationship("ReportDB", back_populates="letters")


# =============================================================================
# DISPUTE / ENFORCEMENT SYSTEM MODELS
# =============================================================================

class DisputeDB(Base):
    """
    Tracks a dispute filed against an entity for a specific violation.
    Core table for the enforcement automation system.
    """
    __tablename__ = "disputes"

    id = Column(String(36), primary_key=True)  # UUID
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    violation_id = Column(String(64), nullable=True, index=True)  # References violation from audit or generated ID like {letter_id}-v{idx}

    # Entity Information
    entity_type = Column(SQLEnum(EntityType), nullable=False)
    entity_name = Column(String(255), nullable=False)  # Equifax, Experian, TransUnion, or creditor name

    # Dispute Details
    dispute_date = Column(Date, nullable=True)  # Date dispute was sent (null until tracking started)
    deadline_date = Column(Date, nullable=True)  # Calculated deadline for response (null until tracking started)
    tracking_started = Column(Boolean, default=False)  # Has user started tracking (confirmed send date)?
    source = Column(SQLEnum(DisputeSource), default=DisputeSource.DIRECT)

    # State Machine
    status = Column(SQLEnum(DisputeStatus), default=DisputeStatus.OPEN)
    current_state = Column(SQLEnum(EscalationState), default=EscalationState.DISPUTED)

    # FDCPA §1692g(b) Guardrail Fields
    has_validation_request = Column(Boolean, default=False)  # Did consumer send validation request?
    collection_continued = Column(Boolean, default=False)    # Did collector continue before validation?

    # Evidence
    letter_id = Column(String(36), ForeignKey("letters.id", ondelete="SET NULL"), nullable=True)
    account_fingerprint = Column(String(255), nullable=True)  # For reinsertion detection
    original_violation_data = Column(JSON, nullable=True)  # Snapshot of violation at dispute time

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    responses = relationship("DisputeResponseDB", back_populates="dispute", cascade="all, delete-orphan")
    escalation_log = relationship("EscalationLogDB", back_populates="dispute", cascade="all, delete-orphan")
    paper_trail = relationship("PaperTrailDB", back_populates="dispute", cascade="all, delete-orphan")
    reinsertion_watch = relationship("ReinsertionWatchDB", back_populates="dispute", cascade="all, delete-orphan")


class DisputeResponseDB(Base):
    """
    Tracks responses received from entities.
    Maps to violations based on response type.
    """
    __tablename__ = "dispute_responses"

    id = Column(String(36), primary_key=True)  # UUID
    dispute_id = Column(String(36), ForeignKey("disputes.id", ondelete="CASCADE"), nullable=False, index=True)
    violation_id = Column(String(64), nullable=True, index=True)  # Which specific violation this response is for (can be generated ID like {letter_id}-v{idx})

    # Response Details
    response_type = Column(SQLEnum(ResponseType), nullable=False)
    response_date = Column(Date, nullable=True)  # Date response was received
    reported_by = Column(SQLEnum(ActorType), nullable=False)  # USER or SYSTEM (for deadline breach)

    # For UPDATED responses - track what changed
    updated_fields = Column(JSON, nullable=True)  # {"field_name": {"old": x, "new": y}}

    # For REJECTED responses - track procedural compliance
    rejection_reason = Column(Text, nullable=True)
    has_5_day_notice = Column(Boolean, nullable=True)
    has_specific_reason = Column(Boolean, nullable=True)
    has_missing_info_request = Column(Boolean, nullable=True)

    # Evidence
    evidence_path = Column(String(500), nullable=True)  # File path to uploaded evidence
    evidence_hash = Column(String(64), nullable=True)   # SHA-256 hash for integrity

    # New violations created by this response
    new_violations = Column(JSON, nullable=True)  # Array of violation objects

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    dispute = relationship("DisputeDB", back_populates="responses")


class ReinsertionWatchDB(Base):
    """
    Monitors deleted items for reinsertion.
    System-detected violations, not user-reported.
    """
    __tablename__ = "reinsertion_watch"

    id = Column(String(36), primary_key=True)  # UUID
    dispute_id = Column(String(36), ForeignKey("disputes.id", ondelete="CASCADE"), nullable=False, index=True)

    # Account Identification
    account_fingerprint = Column(String(255), nullable=False)  # Unique identifier for account
    furnisher_name = Column(String(255), nullable=True)
    bureau = Column(String(50), nullable=True)

    # Monitoring Window
    monitoring_start = Column(Date, nullable=False)  # Date deletion confirmed
    monitoring_end = Column(Date, nullable=False)    # 90 days after deletion

    # Status
    status = Column(SQLEnum(ReinsertionWatchStatus), default=ReinsertionWatchStatus.ACTIVE)

    # Detection Results
    reinsertion_date = Column(Date, nullable=True)      # When reinsertion was detected
    notice_date = Column(Date, nullable=True)           # When reinsertion notice was received (if any)
    notice_received = Column(Boolean, default=False)    # Did we get 5-day advance notice?

    # Violation created on reinsertion detection
    reinsertion_violation_id = Column(String(36), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    dispute = relationship("DisputeDB", back_populates="reinsertion_watch")


class EscalationLogDB(Base):
    """
    Immutable log of state machine transitions.
    Append-only - records every state change.
    """
    __tablename__ = "escalation_log"

    id = Column(String(36), primary_key=True)  # UUID
    dispute_id = Column(String(36), ForeignKey("disputes.id", ondelete="CASCADE"), nullable=False, index=True)

    # State Transition
    from_state = Column(SQLEnum(EscalationState), nullable=True)  # NULL for initial state
    to_state = Column(SQLEnum(EscalationState), nullable=False)

    # Trigger Information
    trigger = Column(String(100), nullable=False)  # What caused the transition
    actor = Column(SQLEnum(ActorType), nullable=False)  # Who/what triggered it

    # Legal Context
    statutes_activated = Column(JSON, nullable=True)  # Array of statute citations
    violations_created = Column(JSON, nullable=True)  # Array of violation IDs

    # Timestamps (immutable)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    dispute = relationship("DisputeDB", back_populates="escalation_log")


class PaperTrailDB(Base):
    """
    Immutable record of all dispute events.
    Everything is timestamped and cannot be modified.
    """
    __tablename__ = "paper_trail"

    id = Column(String(36), primary_key=True)  # UUID
    dispute_id = Column(String(36), ForeignKey("disputes.id", ondelete="CASCADE"), nullable=False, index=True)

    # Event Details
    event_type = Column(String(50), nullable=False)  # dispute_created, response_logged, deadline_breach, etc.
    actor = Column(SQLEnum(ActorType), nullable=False)
    description = Column(Text, nullable=False)

    # Evidence
    evidence_hash = Column(String(64), nullable=True)  # SHA-256 for any attached evidence

    # Artifact Information
    artifact_type = Column(String(50), nullable=True)  # initial_letter, cure_letter, mov_demand, etc.
    artifact_path = Column(String(500), nullable=True)

    # Event Metadata (renamed from 'metadata' which is reserved in SQLAlchemy)
    event_metadata = Column(JSON, nullable=True)  # Additional context

    # Timestamps (immutable)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    dispute = relationship("DisputeDB", back_populates="paper_trail")


class SchedulerTaskDB(Base):
    """
    Tracks scheduled tasks for the enforcement system.
    Deadline checks, reinsertion scans, stall detection.
    """
    __tablename__ = "scheduler_tasks"

    id = Column(String(36), primary_key=True)  # UUID

    # Task Details
    task_type = Column(String(50), nullable=False)  # deadline_check, reinsertion_scan, stall_detection
    dispute_id = Column(String(36), ForeignKey("disputes.id", ondelete="CASCADE"), nullable=True, index=True)

    # Scheduling
    scheduled_for = Column(DateTime, nullable=False)  # When to run
    executed_at = Column(DateTime, nullable=True)     # When it ran

    # Status
    status = Column(String(20), default="pending")  # pending, running, completed, failed
    result = Column(JSON, nullable=True)            # Task result/output
    error_message = Column(Text, nullable=True)     # If failed

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)


# =============================================================================
# EXECUTION LEDGER SYSTEM MODELS (B7)
# =============================================================================
# Append-only telemetry layer for capturing real-world enforcement outcomes.
# Core principle: The Ledger records reality. It never decides. It never edits history.
# Executions are born at send-time (confirm_mailing), not plan-time.
# =============================================================================

class SuppressionReason(str, Enum):
    """Reasons for intentional non-action by the system."""
    DUPLICATE_IN_FLIGHT = "DUPLICATE_IN_FLIGHT"
    COOLDOWN_ACTIVE = "COOLDOWN_ACTIVE"
    DOFD_GATE_BLOCK = "DOFD_GATE_BLOCK"
    OWNERSHIP_GATE_BLOCK = "OWNERSHIP_GATE_BLOCK"
    VERIFICATION_RISK_SPIKE = "VERIFICATION_RISK_SPIKE"
    COMPLIANCE_HOLD = "COMPLIANCE_HOLD"


class ExecutionStatus(str, Enum):
    """Status of an execution event."""
    PENDING = "PENDING"
    RESPONDED = "RESPONDED"
    ESCALATED = "ESCALATED"
    CLOSED = "CLOSED"


class FinalOutcome(str, Enum):
    """Final outcome of an enforcement action."""
    DELETED = "DELETED"
    VERIFIED = "VERIFIED"
    UPDATED = "UPDATED"
    REINSERTED = "REINSERTED"
    IGNORED = "IGNORED"


class DownstreamEventType(str, Enum):
    """Types of user-reported downstream outcomes."""
    LOAN_APPROVED = "LOAN_APPROVED"
    APARTMENT_APPROVED = "APARTMENT_APPROVED"
    EMPLOYMENT_CLEARED = "EMPLOYMENT_CLEARED"


class ExecutionSuppressionEventDB(Base):
    """
    SOURCE 0: Records intentional suppression of action by the system.
    Not user hesitation. Not failure. Intentional restraint.

    ❌ Does NOT feed Copilot
    ❌ Does NOT affect scoring
    ✅ Admin + audit only
    ✅ Distinguishes restraint from failure

    Append-only. Immutable after insert.
    """
    __tablename__ = "execution_suppression_events"

    id = Column(String(36), primary_key=True)  # UUID

    # Correlation - links entire enforcement lifecycle
    dispute_session_id = Column(String(36), nullable=False, index=True)

    # Context
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    report_id = Column(String(36), ForeignKey("reports.id"), nullable=True)
    account_id = Column(String(64), nullable=True)
    credit_goal = Column(String(50), nullable=False)
    copilot_version = Column(String(20), nullable=True)

    # Suppression details
    suppression_reason = Column(SQLEnum(SuppressionReason), nullable=False)

    # Timestamps
    suppressed_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class ExecutionEventDB(Base):
    """
    SOURCE 1: Born at confirm_mailing(). The AUTHORITY MOMENT.
    Anything not sent does not exist to the Ledger.

    🔒 Immutable after insert.
    Append-only. Event-sourced.
    """
    __tablename__ = "execution_events"

    id = Column(String(36), primary_key=True)  # UUID

    # Correlation - links entire enforcement lifecycle
    dispute_session_id = Column(String(36), nullable=False, index=True)

    # Identity
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    report_id = Column(String(36), ForeignKey("reports.id"), nullable=True)
    account_id = Column(String(64), nullable=True)
    dispute_id = Column(String(36), ForeignKey("disputes.id"), nullable=True)
    letter_id = Column(String(36), ForeignKey("letters.id"), nullable=True)

    # Copilot snapshot (frozen at execution time)
    credit_goal = Column(String(50), nullable=False)
    target_state_hash = Column(String(64), nullable=True)  # SHA256 of target state
    copilot_version = Column(String(20), nullable=True)

    # Execution details
    action_type = Column(String(50), nullable=False)  # DELETE_DEMAND, CORRECT_DEMAND, etc.
    response_posture = Column(String(50), nullable=True)  # VERIFIED, NO_RESPONSE, etc.
    violation_type = Column(String(100), nullable=True)
    contradiction_rule = Column(String(20), nullable=True)  # T1, D1, M2, etc.

    # Recipient
    bureau = Column(String(50), nullable=True)
    furnisher_type = Column(String(50), nullable=True)
    creditor_name = Column(String(255), nullable=True)
    account_fingerprint = Column(String(255), nullable=True, index=True)

    # Gates applied at execution time
    gate_applied = Column(JSON, nullable=True)  # {"dofd_gate": true, "ownership_gate": false}

    # Risk flags at send-time
    risk_flags = Column(JSON, nullable=True)  # ["TACTICAL_VERIFICATION_RISK", "REINSERTION_LIKELY"]

    # Evidence anchor
    document_hash = Column(String(64), nullable=True)  # SHA256
    artifact_pointer = Column(String(500), nullable=True)  # s3://, gcs://, file path, etc.

    # Timing
    executed_at = Column(DateTime, nullable=False)  # AUTHORITY MOMENT - when letter was confirmed mailed
    due_by = Column(DateTime, nullable=True)  # Response deadline

    # Status
    execution_status = Column(SQLEnum(ExecutionStatus), default=ExecutionStatus.PENDING)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    responses = relationship("ExecutionResponseDB", back_populates="execution")
    outcomes = relationship("ExecutionOutcomeDB", back_populates="execution")


class ExecutionResponseDB(Base):
    """
    SOURCE 2: Emitted when entity response is logged.
    Tracks what the bureau/furnisher actually said.

    Append-only. Immutable after insert.
    """
    __tablename__ = "execution_responses"

    id = Column(String(36), primary_key=True)  # UUID
    execution_id = Column(String(36), ForeignKey("execution_events.id"), nullable=False, index=True)
    dispute_session_id = Column(String(36), nullable=False, index=True)

    bureau = Column(String(50), nullable=True)

    # Response classification
    response_type = Column(String(50), nullable=False)  # DELETED, VERIFIED, UPDATED, PARTIAL, NO_RESPONSE
    response_reason = Column(Text, nullable=True)  # Optional reason text from entity

    # Evidence anchor
    document_hash = Column(String(64), nullable=True)  # SHA256 of response document
    artifact_pointer = Column(String(500), nullable=True)  # Path to evidence file

    # Observed changes
    balance_changed = Column(Boolean, default=False)
    dofd_changed = Column(Boolean, default=False)
    status_changed = Column(Boolean, default=False)
    reinsertion_flag = Column(Boolean, default=False)

    # Timestamps
    response_received_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    execution = relationship("ExecutionEventDB", back_populates="responses")


class ExecutionOutcomeDB(Base):
    """
    SOURCE 3: Emitted during report re-ingestion diff.
    Detects actual changes on the credit report using snapshot verification.

    Append-only. Immutable after insert.
    Uses state hashes to prevent parser hallucinations.
    """
    __tablename__ = "execution_outcomes"

    id = Column(String(36), primary_key=True)  # UUID
    execution_id = Column(String(36), ForeignKey("execution_events.id"), nullable=False, index=True)
    dispute_session_id = Column(String(36), nullable=False, index=True)
    new_report_id = Column(String(36), ForeignKey("reports.id"), nullable=True)

    # Outcome classification
    final_outcome = Column(SQLEnum(FinalOutcome), nullable=False)

    # Snapshot verification - prevents parser hallucinations
    previous_state_hash = Column(String(64), nullable=True)  # SHA256 of account state before
    current_state_hash = Column(String(64), nullable=True)   # SHA256 of account state after

    # Durability tracking
    days_until_reinsertion = Column(Integer, nullable=True)  # If reinserted, how many days until it came back
    durability_score = Column(Integer, nullable=True)  # 0-100, higher = more durable deletion

    # Credit state impact
    account_removed = Column(Boolean, default=False)  # Was account removed entirely?
    negative_status_removed = Column(Boolean, default=False)  # Was negative status cleared?
    utilization_impact = Column(Float, nullable=True)  # Change in utilization ratio

    # Timestamps
    resolved_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    execution = relationship("ExecutionEventDB", back_populates="outcomes")


class DownstreamOutcomeDB(Base):
    """
    SOURCE 4: User-reported downstream outcomes.
    Records real-world results like loan approvals.

    ⚠️ Never used directly for enforcement decisions.
    ⚠️ Informational only - not fed to Copilot.

    Append-only. Immutable after insert.
    """
    __tablename__ = "downstream_outcomes"

    id = Column(String(36), primary_key=True)  # UUID
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    dispute_session_id = Column(String(36), nullable=True, index=True)
    credit_goal = Column(String(50), nullable=False)

    # Event details
    event_type = Column(SQLEnum(DownstreamEventType), nullable=False)
    notes = Column(Text, nullable=True)

    # Timestamps
    reported_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class CopilotSignalCacheDB(Base):
    """
    Materialized view of aggregated ledger signals.
    Copilot reads ONLY from this table.

    Computed nightly by LedgerSignalAggregator.
    Signals include: reinsertion_rate, dofd_change_rate,
    verification_spike_rate, deletion_durability.

    ⚠️ Suppression frequency is NOT exposed here (admin-only).
    """
    __tablename__ = "copilot_signal_cache"

    id = Column(String(36), primary_key=True)  # UUID

    # Scope - determines granularity of signal
    scope_type = Column(String(50), nullable=False)  # GLOBAL, BUREAU, FURNISHER_TYPE, CREDITOR
    scope_value = Column(String(255), nullable=True)  # e.g., "EXPERIAN", "COLLECTION", "Capital One"

    # Signal data
    signal_type = Column(String(100), nullable=False)  # reinsertion_rate, dofd_change_rate, etc.
    signal_value = Column(Float, nullable=False)  # The computed signal value
    sample_count = Column(Integer, default=0)  # Number of data points used

    # Time window for aggregation
    window_start = Column(DateTime, nullable=False)
    window_end = Column(DateTime, nullable=False)

    # Timestamps
    computed_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)  # When this cache entry becomes stale
