"""
Migration: Expand violation_id column in disputes and dispute_responses tables from VARCHAR(36) to VARCHAR(64).

This allows storing generated IDs like {letter_id}-v{idx} which exceed 36 characters.
"""
from sqlalchemy import create_engine, text
import os

# Use same DB URL pattern as main app - no password needed for local Homebrew postgres
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql://{os.getenv('USER', 'postgres')}@localhost:5432/credit_engine"
)

def run_migration():
    """Expand violation_id columns to VARCHAR(64)."""
    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        # Expand disputes.violation_id
        result = conn.execute(text("""
            SELECT character_maximum_length
            FROM information_schema.columns
            WHERE table_name = 'disputes' AND column_name = 'violation_id'
        """))

        row = result.fetchone()
        if row and row[0] >= 64:
            print("disputes.violation_id is already VARCHAR(64) or larger")
        else:
            conn.execute(text("""
                ALTER TABLE disputes
                ALTER COLUMN violation_id TYPE VARCHAR(64)
            """))
            print("Successfully expanded disputes.violation_id to VARCHAR(64)")

        # Expand dispute_responses.violation_id
        result = conn.execute(text("""
            SELECT character_maximum_length
            FROM information_schema.columns
            WHERE table_name = 'dispute_responses' AND column_name = 'violation_id'
        """))

        row = result.fetchone()
        if row and row[0] and row[0] >= 64:
            print("dispute_responses.violation_id is already VARCHAR(64) or larger")
        elif row:
            conn.execute(text("""
                ALTER TABLE dispute_responses
                ALTER COLUMN violation_id TYPE VARCHAR(64)
            """))
            print("Successfully expanded dispute_responses.violation_id to VARCHAR(64)")
        else:
            print("dispute_responses.violation_id column not found (may not exist yet)")

        conn.commit()

if __name__ == "__main__":
    run_migration()
