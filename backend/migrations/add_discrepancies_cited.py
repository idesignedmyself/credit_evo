"""
Migration: Add discrepancies_cited column to letters table

This column stores cross-bureau discrepancies included in the letter.
"""
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text


def run_migration():
    """Add discrepancies_cited column to letters table."""
    database_url = os.getenv(
        "DATABASE_URL",
        f"postgresql://{os.getenv('USER', 'postgres')}@localhost:5432/credit_engine"
    )

    engine = create_engine(database_url)

    with engine.connect() as conn:
        # Check if column already exists
        result = conn.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'letters' AND column_name = 'discrepancies_cited'
        """))

        if result.fetchone():
            print("Column 'discrepancies_cited' already exists in 'letters' table")
            return True

        # Add the column
        print("Adding 'discrepancies_cited' column to 'letters' table...")
        conn.execute(text("""
            ALTER TABLE letters
            ADD COLUMN discrepancies_cited JSONB DEFAULT '[]'::jsonb
        """))
        conn.commit()
        print("SUCCESS: Column 'discrepancies_cited' added to 'letters' table")
        return True


if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
