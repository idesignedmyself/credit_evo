"""
Migration: Add tier and channel columns to letters table.

Enables multi-channel letter organization:
- tier: 0=initial, 1=tier-1 response, 2=tier-2 response
- channel: CRA, CFPB, LAWYER

Supports the Letters page tab restructure with:
- Mailed Disputes tab (channel=CRA)
- CFPB Complaints tab (channel=CFPB)
- Litigation Packets tab (channel=LAWYER)
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
            WHERE table_name = :table_name AND column_name = :column_name
        )
    """), {"table_name": table_name, "column_name": column_name})
    return result.fetchone()[0]


def run_migration():
    """Add tier and channel columns to letters table."""
    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        # =================================================================
        # COLUMN 1: tier (Integer, default=0)
        # 0 = Initial Dispute Letter
        # 1 = Tier-1 Response Letter (before supervisory notice)
        # 2 = Tier-2 Final Response Letter (after supervisory notice)
        # =================================================================
        if column_exists(conn, "letters", "tier"):
            print("tier column already exists")
        else:
            conn.execute(text("""
                ALTER TABLE letters
                ADD COLUMN tier INTEGER DEFAULT 0 NOT NULL
            """))
            print("Added tier column")

        # =================================================================
        # COLUMN 2: channel (VARCHAR(20), default='CRA')
        # CRA = Credit Reporting Agency letters (Mailed Disputes)
        # CFPB = Consumer Financial Protection Bureau letters
        # LAWYER = Litigation/Attorney packets
        # =================================================================
        if column_exists(conn, "letters", "channel"):
            print("channel column already exists")
        else:
            conn.execute(text("""
                ALTER TABLE letters
                ADD COLUMN channel VARCHAR(20) DEFAULT 'CRA' NOT NULL
            """))
            print("Added channel column")

        # =================================================================
        # INDEX: Composite index for efficient filtering
        # =================================================================
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_letters_channel_tier
            ON letters(channel, tier)
        """))
        print("Created composite index on channel + tier")

        conn.commit()
        print("\nLetters tier/channel migration completed successfully!")


def rollback_migration():
    """Remove tier and channel columns from letters table."""
    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        # Drop index first
        conn.execute(text("""
            DROP INDEX IF EXISTS idx_letters_channel_tier
        """))
        print("Dropped idx_letters_channel_tier index")

        # Drop columns
        for column in ["tier", "channel"]:
            if column_exists(conn, "letters", column):
                conn.execute(text(f"""
                    ALTER TABLE letters
                    DROP COLUMN {column}
                """))
                print(f"Dropped {column} column")

        conn.commit()
        print("\nRollback completed successfully!")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        rollback_migration()
    else:
        run_migration()
