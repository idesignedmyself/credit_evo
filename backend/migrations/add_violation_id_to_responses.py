"""
Migration: Add violation_id column to dispute_responses table.

This allows tracking per-violation responses within a dispute.
"""
from sqlalchemy import create_engine, text
import os

# Use same DB URL pattern as main app - no password needed for local Homebrew postgres
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql://{os.getenv('USER', 'postgres')}@localhost:5432/credit_engine"
)

def run_migration():
    """Add violation_id column to dispute_responses table."""
    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        # Check if column already exists
        result = conn.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'dispute_responses' AND column_name = 'violation_id'
        """))

        if result.fetchone():
            print("Column 'violation_id' already exists in dispute_responses table")
            return

        # Add the column
        conn.execute(text("""
            ALTER TABLE dispute_responses
            ADD COLUMN violation_id VARCHAR(36)
        """))

        # Create index
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_dispute_responses_violation_id
            ON dispute_responses(violation_id)
        """))

        conn.commit()
        print("Successfully added 'violation_id' column to dispute_responses table")

if __name__ == "__main__":
    run_migration()
