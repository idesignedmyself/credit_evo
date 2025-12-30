"""
Migration: Add Tier-2 Responses table and Tier-3 promotion fields.

Creates tier2_responses table for tracking final Tier-2 supervisory responses.
Adds tier_reached and locked columns to disputes table for Tier-3 promotion.

Tier-2 Response Types:
- CURED: Entity corrected the issue
- REPEAT_VERIFIED: Entity re-verified without correction
- DEFLECTION_FRIVOLOUS: Entity called dispute frivolous
- NO_RESPONSE_AFTER_CURE_WINDOW: Entity failed to respond within cure window

Tier-3 Promotion:
- Non-CURED responses auto-promote to Tier-3
- Tier-3 locks the violation record
- Tier-3 classifies the examiner failure
- Tier-3 writes immutable ledger entry
"""
from sqlalchemy import create_engine, text
import os

# Use same DB URL pattern as main app
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql://{os.getenv('USER', 'postgres')}@localhost:5432/credit_engine"
)


def table_exists(conn, table_name: str) -> bool:
    """Check if a table exists."""
    result = conn.execute(text("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = :table_name
        )
    """), {"table_name": table_name})
    return result.fetchone()[0]


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
    """Add Tier-2/Tier-3 tables and fields."""
    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        # =================================================================
        # 1. Create tier2_responses table
        # =================================================================
        if table_exists(conn, "tier2_responses"):
            print("tier2_responses table already exists")
        else:
            conn.execute(text("""
                CREATE TABLE tier2_responses (
                    id VARCHAR(36) PRIMARY KEY,
                    dispute_id VARCHAR(36) NOT NULL REFERENCES disputes(id) ON DELETE CASCADE,
                    response_type VARCHAR(50) NOT NULL,
                    response_date DATE NOT NULL,
                    tier3_promoted BOOLEAN DEFAULT FALSE,
                    tier3_promotion_date TIMESTAMP,
                    tier3_classification VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            print("Created tier2_responses table")

            # Create index on dispute_id
            conn.execute(text("""
                CREATE INDEX idx_tier2_responses_dispute_id
                ON tier2_responses(dispute_id)
            """))
            print("Created index on tier2_responses.dispute_id")

        # =================================================================
        # 2. Add tier_reached column to disputes
        # =================================================================
        if column_exists(conn, "disputes", "tier_reached"):
            print("tier_reached column already exists")
        else:
            conn.execute(text("""
                ALTER TABLE disputes
                ADD COLUMN tier_reached INTEGER DEFAULT 1
            """))
            print("Added tier_reached column to disputes")

        # =================================================================
        # 3. Add locked column to disputes
        # =================================================================
        if column_exists(conn, "disputes", "locked"):
            print("locked column already exists")
        else:
            conn.execute(text("""
                ALTER TABLE disputes
                ADD COLUMN locked BOOLEAN DEFAULT FALSE
            """))
            print("Added locked column to disputes")

        # =================================================================
        # 4. Create index for filtering locked/tier3 disputes
        # =================================================================
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_disputes_tier3_locked
            ON disputes(tier_reached, locked)
            WHERE tier_reached = 3
        """))
        print("Created index for Tier-3 disputes")

        conn.commit()
        print("\nTier-2/Tier-3 migration completed successfully!")


def rollback_migration():
    """Remove Tier-2/Tier-3 tables and fields."""
    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        # Drop index first
        conn.execute(text("""
            DROP INDEX IF EXISTS idx_disputes_tier3_locked
        """))
        print("Dropped idx_disputes_tier3_locked index")

        # Drop columns from disputes
        for column in ["locked", "tier_reached"]:
            if column_exists(conn, "disputes", column):
                conn.execute(text(f"""
                    ALTER TABLE disputes
                    DROP COLUMN {column}
                """))
                print(f"Dropped {column} column from disputes")

        # Drop tier2_responses table
        if table_exists(conn, "tier2_responses"):
            conn.execute(text("""
                DROP TABLE tier2_responses
            """))
            print("Dropped tier2_responses table")

        conn.commit()
        print("\nTier-2/Tier-3 rollback completed!")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        rollback_migration()
    else:
        run_migration()
