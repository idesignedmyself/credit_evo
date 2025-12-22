"""
Migration: Add Execution Ledger tables (B7).

Creates 6 new tables for the append-only telemetry layer:
1. execution_suppression_events - SOURCE 0: Intentional non-action
2. execution_events - SOURCE 1: Born at confirm_mailing()
3. execution_responses - SOURCE 2: Bureau response intake
4. execution_outcomes - SOURCE 3: Report re-ingestion diff
5. downstream_outcomes - SOURCE 4: User-reported downstream
6. copilot_signal_cache - Aggregated signals for Copilot

Core principle: The Ledger records reality. It never decides. It never edits history.
"""
from sqlalchemy import create_engine, text
import os

# Use same DB URL pattern as main app
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql://{os.getenv('USER', 'postgres')}@localhost:5432/credit_engine"
)


def table_exists(conn, table_name: str) -> bool:
    """Check if a table exists in the database."""
    result = conn.execute(text("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = :table_name
        )
    """), {"table_name": table_name})
    return result.fetchone()[0]


def run_migration():
    """Create all execution ledger tables."""
    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        # =================================================================
        # TABLE 1: execution_suppression_events (SOURCE 0)
        # =================================================================
        if table_exists(conn, "execution_suppression_events"):
            print("execution_suppression_events table already exists")
        else:
            conn.execute(text("""
                CREATE TABLE execution_suppression_events (
                    id VARCHAR(36) PRIMARY KEY,
                    dispute_session_id VARCHAR(36) NOT NULL,
                    user_id VARCHAR(36) NOT NULL REFERENCES users(id),
                    report_id VARCHAR(36) REFERENCES reports(id),
                    account_id VARCHAR(64),
                    credit_goal VARCHAR(50) NOT NULL,
                    copilot_version VARCHAR(20),
                    suppression_reason VARCHAR(50) NOT NULL,
                    suppressed_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text("""
                CREATE INDEX idx_suppression_session ON execution_suppression_events(dispute_session_id)
            """))
            conn.execute(text("""
                CREATE INDEX idx_suppression_user ON execution_suppression_events(user_id)
            """))
            print("Created execution_suppression_events table")

        # =================================================================
        # TABLE 2: execution_events (SOURCE 1)
        # =================================================================
        if table_exists(conn, "execution_events"):
            print("execution_events table already exists")
        else:
            conn.execute(text("""
                CREATE TABLE execution_events (
                    id VARCHAR(36) PRIMARY KEY,
                    dispute_session_id VARCHAR(36) NOT NULL,
                    user_id VARCHAR(36) NOT NULL REFERENCES users(id),
                    report_id VARCHAR(36) REFERENCES reports(id),
                    account_id VARCHAR(64),
                    dispute_id VARCHAR(36) REFERENCES disputes(id),
                    letter_id VARCHAR(36) REFERENCES letters(id),
                    credit_goal VARCHAR(50) NOT NULL,
                    target_state_hash VARCHAR(64),
                    copilot_version VARCHAR(20),
                    action_type VARCHAR(50) NOT NULL,
                    response_posture VARCHAR(50),
                    violation_type VARCHAR(100),
                    contradiction_rule VARCHAR(20),
                    bureau VARCHAR(50),
                    furnisher_type VARCHAR(50),
                    creditor_name VARCHAR(255),
                    account_fingerprint VARCHAR(255),
                    gate_applied JSONB,
                    risk_flags JSONB,
                    document_hash VARCHAR(64),
                    artifact_pointer VARCHAR(500),
                    executed_at TIMESTAMP NOT NULL,
                    due_by TIMESTAMP,
                    execution_status VARCHAR(20) DEFAULT 'PENDING',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text("""
                CREATE INDEX idx_execution_session ON execution_events(dispute_session_id)
            """))
            conn.execute(text("""
                CREATE INDEX idx_execution_user ON execution_events(user_id)
            """))
            conn.execute(text("""
                CREATE INDEX idx_execution_fingerprint ON execution_events(account_fingerprint)
            """))
            print("Created execution_events table")

        # =================================================================
        # TABLE 3: execution_responses (SOURCE 2)
        # =================================================================
        if table_exists(conn, "execution_responses"):
            print("execution_responses table already exists")
        else:
            conn.execute(text("""
                CREATE TABLE execution_responses (
                    id VARCHAR(36) PRIMARY KEY,
                    execution_id VARCHAR(36) NOT NULL REFERENCES execution_events(id),
                    dispute_session_id VARCHAR(36) NOT NULL,
                    bureau VARCHAR(50),
                    response_type VARCHAR(50) NOT NULL,
                    response_reason TEXT,
                    document_hash VARCHAR(64),
                    artifact_pointer VARCHAR(500),
                    balance_changed BOOLEAN DEFAULT FALSE,
                    dofd_changed BOOLEAN DEFAULT FALSE,
                    status_changed BOOLEAN DEFAULT FALSE,
                    reinsertion_flag BOOLEAN DEFAULT FALSE,
                    response_received_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text("""
                CREATE INDEX idx_response_execution ON execution_responses(execution_id)
            """))
            conn.execute(text("""
                CREATE INDEX idx_response_session ON execution_responses(dispute_session_id)
            """))
            print("Created execution_responses table")

        # =================================================================
        # TABLE 4: execution_outcomes (SOURCE 3)
        # =================================================================
        if table_exists(conn, "execution_outcomes"):
            print("execution_outcomes table already exists")
        else:
            conn.execute(text("""
                CREATE TABLE execution_outcomes (
                    id VARCHAR(36) PRIMARY KEY,
                    execution_id VARCHAR(36) NOT NULL REFERENCES execution_events(id),
                    dispute_session_id VARCHAR(36) NOT NULL,
                    new_report_id VARCHAR(36) REFERENCES reports(id),
                    final_outcome VARCHAR(20) NOT NULL,
                    previous_state_hash VARCHAR(64),
                    current_state_hash VARCHAR(64),
                    days_until_reinsertion INTEGER,
                    durability_score INTEGER,
                    account_removed BOOLEAN DEFAULT FALSE,
                    negative_status_removed BOOLEAN DEFAULT FALSE,
                    utilization_impact FLOAT,
                    resolved_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text("""
                CREATE INDEX idx_outcome_execution ON execution_outcomes(execution_id)
            """))
            conn.execute(text("""
                CREATE INDEX idx_outcome_session ON execution_outcomes(dispute_session_id)
            """))
            print("Created execution_outcomes table")

        # =================================================================
        # TABLE 5: downstream_outcomes (SOURCE 4)
        # =================================================================
        if table_exists(conn, "downstream_outcomes"):
            print("downstream_outcomes table already exists")
        else:
            conn.execute(text("""
                CREATE TABLE downstream_outcomes (
                    id VARCHAR(36) PRIMARY KEY,
                    user_id VARCHAR(36) NOT NULL REFERENCES users(id),
                    dispute_session_id VARCHAR(36),
                    credit_goal VARCHAR(50) NOT NULL,
                    event_type VARCHAR(50) NOT NULL,
                    notes TEXT,
                    reported_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text("""
                CREATE INDEX idx_downstream_user ON downstream_outcomes(user_id)
            """))
            conn.execute(text("""
                CREATE INDEX idx_downstream_session ON downstream_outcomes(dispute_session_id)
            """))
            print("Created downstream_outcomes table")

        # =================================================================
        # TABLE 6: copilot_signal_cache
        # =================================================================
        if table_exists(conn, "copilot_signal_cache"):
            print("copilot_signal_cache table already exists")
        else:
            conn.execute(text("""
                CREATE TABLE copilot_signal_cache (
                    id VARCHAR(36) PRIMARY KEY,
                    scope_type VARCHAR(50) NOT NULL,
                    scope_value VARCHAR(255),
                    signal_type VARCHAR(100) NOT NULL,
                    signal_value FLOAT NOT NULL,
                    sample_count INTEGER DEFAULT 0,
                    window_start TIMESTAMP NOT NULL,
                    window_end TIMESTAMP NOT NULL,
                    computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP
                )
            """))
            conn.execute(text("""
                CREATE INDEX idx_signal_scope ON copilot_signal_cache(scope_type, scope_value)
            """))
            conn.execute(text("""
                CREATE INDEX idx_signal_type ON copilot_signal_cache(signal_type)
            """))
            print("Created copilot_signal_cache table")

        conn.commit()
        print("\nExecution Ledger migration completed successfully!")


if __name__ == "__main__":
    run_migration()
