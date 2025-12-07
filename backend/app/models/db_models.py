"""
Credit Engine 2.0 - SQLAlchemy ORM Models
PostgreSQL database models for persistent storage
"""
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, Text, JSON, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from ..database import Base


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

    content = Column(Text, nullable=False)
    edited_content = Column(Text, nullable=True)  # User-edited version
    bureau = Column(String(50), default="transunion")
    tone = Column(String(50), default="formal")

    # Metadata
    accounts_disputed = Column(JSON)  # List of account IDs
    violations_cited = Column(JSON)   # List of violation types
    word_count = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    report = relationship("ReportDB", back_populates="letters")
