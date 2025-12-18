"""
Migration: Make violation_id nullable in disputes table

Run this script to update the database schema.
Usage: python -m migrations.make_violation_id_nullable
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import engine
from sqlalchemy import text


def run_migration():
    """Make violation_id column nullable in disputes table."""
    with engine.connect() as conn:
        # Check current state
        result = conn.execute(text("""
            SELECT column_name, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'disputes' AND column_name = 'violation_id'
        """))
        row = result.fetchone()

        if row:
            print(f"Current state: violation_id is_nullable = {row[1]}")

            if row[1] == 'NO':
                print("Altering column to allow NULL values...")
                conn.execute(text("""
                    ALTER TABLE disputes
                    ALTER COLUMN violation_id DROP NOT NULL
                """))
                conn.commit()
                print("Migration complete: violation_id is now nullable")
            else:
                print("Column is already nullable, no changes needed")
        else:
            print("ERROR: Column 'violation_id' not found in 'disputes' table")


if __name__ == "__main__":
    run_migration()
