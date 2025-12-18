"""
Migration: Add account_numbers column to letters table.

Stores masked account numbers parallel to violations_cited array,
so they can be displayed in the violations summary on saved letters.
"""
from sqlalchemy import create_engine, text
import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql://{os.getenv('USER', 'postgres')}@localhost:5432/credit_engine"
)

def run_migration():
    """Add account_numbers column to letters table."""
    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        # Check if account_numbers column exists
        result = conn.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'letters' AND column_name = 'account_numbers'
        """))

        if result.fetchone():
            print("account_numbers column already exists")
        else:
            conn.execute(text("""
                ALTER TABLE letters
                ADD COLUMN account_numbers JSON
            """))
            print("Added account_numbers column to letters table")

        conn.commit()

if __name__ == "__main__":
    run_migration()
