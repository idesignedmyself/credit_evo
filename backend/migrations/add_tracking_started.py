"""
Migration: Add tracking_started column to disputes table.

This supports the new workflow where disputes are created in "pending tracking" state
and the deadline clock doesn't start until the user confirms the send date.
"""
from sqlalchemy import create_engine, text
import os

# Use same DB URL pattern as main app
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql://{os.getenv('USER', 'postgres')}@localhost:5432/credit_engine"
)

def run_migration():
    """Add tracking_started column and make dispute_date/deadline_date nullable."""
    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        # Check if tracking_started column exists
        result = conn.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'disputes' AND column_name = 'tracking_started'
        """))

        if result.fetchone():
            print("tracking_started column already exists")
        else:
            conn.execute(text("""
                ALTER TABLE disputes
                ADD COLUMN tracking_started BOOLEAN DEFAULT FALSE
            """))
            print("Added tracking_started column to disputes table")

            # Update existing disputes to have tracking_started = true
            # (since they were created under the old flow)
            conn.execute(text("""
                UPDATE disputes
                SET tracking_started = TRUE
                WHERE dispute_date IS NOT NULL
            """))
            print("Updated existing disputes to have tracking_started = TRUE")

        # Make dispute_date nullable (if not already)
        result = conn.execute(text("""
            SELECT is_nullable
            FROM information_schema.columns
            WHERE table_name = 'disputes' AND column_name = 'dispute_date'
        """))
        row = result.fetchone()
        if row and row[0] == 'NO':
            conn.execute(text("""
                ALTER TABLE disputes
                ALTER COLUMN dispute_date DROP NOT NULL
            """))
            print("Made dispute_date nullable")
        else:
            print("dispute_date is already nullable")

        # Make deadline_date nullable (if not already)
        result = conn.execute(text("""
            SELECT is_nullable
            FROM information_schema.columns
            WHERE table_name = 'disputes' AND column_name = 'deadline_date'
        """))
        row = result.fetchone()
        if row and row[0] == 'NO':
            conn.execute(text("""
                ALTER TABLE disputes
                ALTER COLUMN deadline_date DROP NOT NULL
            """))
            print("Made deadline_date nullable")
        else:
            print("deadline_date is already nullable")

        conn.commit()

if __name__ == "__main__":
    run_migration()
