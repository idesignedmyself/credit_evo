"""
Migration: Add CFPB Channel Adapter tables.

Creates 2 new tables for CFPB escalation tracking:
1. cfpb_cases - CFPB case tracking with single state enum
2. cfpb_events - CFPB event log (convenience layer)

Key design principles:
- Single CFPBState enum is the source of truth (no Stage/Status separation)
- One cfpb_case_number per lifecycle (case continuity)
- Execution ledger remains canonical audit trail
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
    """Create CFPB channel adapter tables."""
    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        # =================================================================
        # TABLE 1: cfpb_cases
        # =================================================================
        if table_exists(conn, "cfpb_cases"):
            print("cfpb_cases table already exists")
        else:
            conn.execute(text("""
                CREATE TABLE cfpb_cases (
                    id VARCHAR(36) PRIMARY KEY,
                    dispute_session_id VARCHAR(36) NOT NULL,
                    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    cfpb_case_number VARCHAR(100),
                    cfpb_state VARCHAR(50) NOT NULL DEFAULT 'NONE',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text("""
                CREATE INDEX idx_cfpb_cases_session ON cfpb_cases(dispute_session_id)
            """))
            conn.execute(text("""
                CREATE INDEX idx_cfpb_cases_user ON cfpb_cases(user_id)
            """))
            conn.execute(text("""
                CREATE INDEX idx_cfpb_cases_number ON cfpb_cases(cfpb_case_number)
            """))
            print("Created cfpb_cases table")

        # =================================================================
        # TABLE 2: cfpb_events
        # =================================================================
        if table_exists(conn, "cfpb_events"):
            print("cfpb_events table already exists")
        else:
            conn.execute(text("""
                CREATE TABLE cfpb_events (
                    id VARCHAR(36) PRIMARY KEY,
                    cfpb_case_id VARCHAR(36) NOT NULL REFERENCES cfpb_cases(id) ON DELETE CASCADE,
                    event_type VARCHAR(20) NOT NULL,
                    payload JSONB,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
                )
            """))
            conn.execute(text("""
                CREATE INDEX idx_cfpb_events_case ON cfpb_events(cfpb_case_id)
            """))
            conn.execute(text("""
                CREATE INDEX idx_cfpb_events_type ON cfpb_events(event_type)
            """))
            print("Created cfpb_events table")

        conn.commit()
        print("\nCFPB Channel Adapter migration completed successfully!")


if __name__ == "__main__":
    run_migration()
