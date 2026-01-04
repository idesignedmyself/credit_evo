"""
Migration: Add discrepancies_data column to disputes table

This column stores cross-bureau discrepancies inherited from the originating letter.
"""
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text


def run_migration():
    """Add discrepancies_data column to disputes table."""
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
            WHERE table_name = 'disputes' AND column_name = 'discrepancies_data'
        """))

        if result.fetchone():
            print("Column 'discrepancies_data' already exists in 'disputes' table")
            return True

        # Add the column
        print("Adding 'discrepancies_data' column to 'disputes' table...")
        conn.execute(text("""
            ALTER TABLE disputes
            ADD COLUMN discrepancies_data JSONB
        """))
        conn.commit()
        print("SUCCESS: Column 'discrepancies_data' added to 'disputes' table")
        return True


if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
