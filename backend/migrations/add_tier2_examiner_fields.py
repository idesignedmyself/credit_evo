"""
Migration: Add Tier 2 Examiner Standard fields to execution_responses.

Adds 4 new columns to track examiner standard evaluation results:
1. examiner_standard_result - PASS, FAIL_PERFUNCTORY, FAIL_NO_RESULTS, etc.
2. examiner_failure_reason - Human-readable explanation
3. response_layer_violation_id - UUID of Tier 2 violation created
4. escalation_basis - What triggered escalation eligibility

These fields support Tier 2 Supervisory Enforcement which evaluates
whether VERIFIED and NO_RESPONSE outcomes met examiner standards.
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
    """Add Tier 2 examiner fields to execution_responses table."""
    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        # Column 1: examiner_standard_result
        if column_exists(conn, "execution_responses", "examiner_standard_result"):
            print("examiner_standard_result column already exists")
        else:
            conn.execute(text("""
                ALTER TABLE execution_responses
                ADD COLUMN examiner_standard_result VARCHAR(50)
            """))
            print("Added examiner_standard_result column")

        # Column 2: examiner_failure_reason
        if column_exists(conn, "execution_responses", "examiner_failure_reason"):
            print("examiner_failure_reason column already exists")
        else:
            conn.execute(text("""
                ALTER TABLE execution_responses
                ADD COLUMN examiner_failure_reason TEXT
            """))
            print("Added examiner_failure_reason column")

        # Column 3: response_layer_violation_id
        if column_exists(conn, "execution_responses", "response_layer_violation_id"):
            print("response_layer_violation_id column already exists")
        else:
            conn.execute(text("""
                ALTER TABLE execution_responses
                ADD COLUMN response_layer_violation_id VARCHAR(36)
            """))
            print("Added response_layer_violation_id column")

        # Column 4: escalation_basis
        if column_exists(conn, "execution_responses", "escalation_basis"):
            print("escalation_basis column already exists")
        else:
            conn.execute(text("""
                ALTER TABLE execution_responses
                ADD COLUMN escalation_basis VARCHAR(100)
            """))
            print("Added escalation_basis column")

        # Create index on examiner_standard_result for efficient filtering
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_response_examiner_result
            ON execution_responses(examiner_standard_result)
            WHERE examiner_standard_result IS NOT NULL
        """))
        print("Created index on examiner_standard_result")

        conn.commit()
        print("\nTier 2 Examiner fields migration completed successfully!")


def rollback_migration():
    """Remove Tier 2 examiner fields from execution_responses table."""
    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        # Drop index first
        conn.execute(text("""
            DROP INDEX IF EXISTS idx_response_examiner_result
        """))

        # Drop columns
        for column in [
            "escalation_basis",
            "response_layer_violation_id",
            "examiner_failure_reason",
            "examiner_standard_result",
        ]:
            if column_exists(conn, "execution_responses", column):
                conn.execute(text(f"""
                    ALTER TABLE execution_responses
                    DROP COLUMN {column}
                """))
                print(f"Dropped {column} column")

        conn.commit()
        print("\nTier 2 Examiner fields rollback completed!")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        rollback_migration()
    else:
        run_migration()
