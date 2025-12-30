"""
Migration: Add Tier-2 Notice Sent tracking fields.

Adds tier2_notice_sent and tier2_notice_sent_at columns to disputes table.
These fields track the explicit "sent" lifecycle event for Tier-2 supervisory notices.

The Tier-2 adjudication UI only appears after tier2_notice_sent = True.
"""
from sqlalchemy import create_engine, text
import os

# Use same DB URL pattern as main app
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql://{os.getenv('USER', 'postgres')}@localhost:5432/credit_engine"
)


def column_exists(conn, table_name: str, column_name: str) -> bool:
    """Check if a column exists in the table."""
    result = conn.execute(text("""
        SELECT EXISTS (
            SELECT FROM information_schema.columns
            WHERE table_name = :table_name
            AND column_name = :column_name
        )
    """), {"table_name": table_name, "column_name": column_name})
    return result.fetchone()[0]


def run_migration():
    """Add Tier-2 notice sent tracking fields to disputes table."""
    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        # Column 1: tier2_notice_sent (Boolean)
        if column_exists(conn, "disputes", "tier2_notice_sent"):
            print("tier2_notice_sent column already exists")
        else:
            conn.execute(text("""
                ALTER TABLE disputes
                ADD COLUMN tier2_notice_sent BOOLEAN DEFAULT FALSE
            """))
            print("Added tier2_notice_sent column")

        # Column 2: tier2_notice_sent_at (DateTime)
        if column_exists(conn, "disputes", "tier2_notice_sent_at"):
            print("tier2_notice_sent_at column already exists")
        else:
            conn.execute(text("""
                ALTER TABLE disputes
                ADD COLUMN tier2_notice_sent_at TIMESTAMP
            """))
            print("Added tier2_notice_sent_at column")

        # Create index for filtering disputes with Tier-2 notices sent
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_disputes_tier2_sent
            ON disputes(tier2_notice_sent)
            WHERE tier2_notice_sent = TRUE
        """))
        print("Created index on tier2_notice_sent")

        conn.commit()
        print("\nTier-2 notice sent fields migration completed successfully!")


def rollback_migration():
    """Remove Tier-2 notice sent tracking fields from disputes table."""
    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        # Drop index first
        conn.execute(text("""
            DROP INDEX IF EXISTS idx_disputes_tier2_sent
        """))
        print("Dropped idx_disputes_tier2_sent index")

        # Drop columns
        for column in ["tier2_notice_sent_at", "tier2_notice_sent"]:
            if column_exists(conn, "disputes", column):
                conn.execute(text(f"""
                    ALTER TABLE disputes
                    DROP COLUMN {column}
                """))
                print(f"Dropped {column} column")

        conn.commit()
        print("\nTier-2 notice sent fields rollback completed!")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        rollback_migration()
    else:
        run_migration()
