"""
Migration: Add ui_state JSONB column to disputes table.

Stores the exact UI state from the frontend for dispute tracking persistence.
When a user views a saved letter, the UI restores exactly as they left it.

Schema:
{
    "stageData": {...},
    "responseTypes": {...},
    "finalResponseTypes": {...},
    "expandedPanels": [...],
    "activeTab": "tracking"
}
"""
from sqlalchemy import create_engine, text
import os

# Use same DB URL pattern as main app
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql://{os.getenv('USER', 'postgres')}@localhost:5432/credit_engine"
)

DEFAULT_UI_STATE = '{"stageData": {}, "responseTypes": {}, "finalResponseTypes": {}, "expandedPanels": [], "activeTab": "tracking"}'


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
    """Add ui_state JSONB column to disputes table."""
    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        if column_exists(conn, "disputes", "ui_state"):
            print("ui_state column already exists")
        else:
            # Step 1: Add column as nullable
            conn.execute(text("""
                ALTER TABLE disputes
                ADD COLUMN ui_state JSONB
            """))
            print("Added ui_state column (nullable)")

            # Step 2: Backfill existing rows with default value
            conn.execute(text(f"""
                UPDATE disputes
                SET ui_state = '{DEFAULT_UI_STATE}'::jsonb
                WHERE ui_state IS NULL
            """))
            print("Backfilled existing rows with default ui_state")

            # Step 3: Make column non-nullable with default
            conn.execute(text(f"""
                ALTER TABLE disputes
                ALTER COLUMN ui_state SET DEFAULT '{DEFAULT_UI_STATE}'::jsonb,
                ALTER COLUMN ui_state SET NOT NULL
            """))
            print("Set ui_state to NOT NULL with default")

        conn.commit()
        print("\nui_state migration completed successfully!")


def rollback_migration():
    """Remove ui_state column from disputes table."""
    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        if column_exists(conn, "disputes", "ui_state"):
            conn.execute(text("""
                ALTER TABLE disputes
                DROP COLUMN ui_state
            """))
            print("Dropped ui_state column")
        else:
            print("ui_state column does not exist")

        conn.commit()
        print("\nui_state rollback completed!")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        rollback_migration()
    else:
        run_migration()
