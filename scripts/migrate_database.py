"""
Database migration script for Phase 2 schema updates.

This script updates the database schema to match the updated models:
1. Adds analysis_details column to bias_reports
2. Renames calculated_at to created_at in bias_reports
3. Creates new indexes for performance
4. Enables foreign keys

Run with: python migrate_database.py
"""

import sqlite3
import os

DB_PATH = "rlcf.db"

def migrate_database():
    """Run all migrations on the database."""
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found at {DB_PATH}")
        print("   Creating new database with updated schema...")
        # The database will be created automatically when the app starts
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("🔧 Starting database migration...")

    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys=ON")
    print("✅ Foreign keys enabled")

    # Check if bias_reports table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='bias_reports'")
    if cursor.fetchone():
        # Get current columns
        cursor.execute("PRAGMA table_info(bias_reports)")
        columns = {col[1]: col for col in cursor.fetchall()}

        # Check if migration is needed
        needs_migration = False

        if 'calculated_at' in columns and 'created_at' not in columns:
            print("📝 Migrating bias_reports: calculated_at -> created_at")
            cursor.execute("""
                ALTER TABLE bias_reports RENAME COLUMN calculated_at TO created_at
            """)
            needs_migration = True

        if 'analysis_details' not in columns:
            print("📝 Adding analysis_details column to bias_reports")
            cursor.execute("""
                ALTER TABLE bias_reports ADD COLUMN analysis_details JSON
            """)
            needs_migration = True

        if needs_migration:
            print("✅ bias_reports table migrated")
        else:
            print("✅ bias_reports already up to date")
    else:
        print("ℹ️  bias_reports table doesn't exist yet (will be created on first run)")

    # Create indexes if they don't exist
    indexes = [
        ("ix_legal_tasks_task_type", "CREATE INDEX IF NOT EXISTS ix_legal_tasks_task_type ON legal_tasks(task_type)"),
        ("ix_legal_tasks_status", "CREATE INDEX IF NOT EXISTS ix_legal_tasks_status ON legal_tasks(status)"),
        ("ix_legal_tasks_created_at", "CREATE INDEX IF NOT EXISTS ix_legal_tasks_created_at ON legal_tasks(created_at)"),
        ("ix_feedback_user_id", "CREATE INDEX IF NOT EXISTS ix_feedback_user_id ON feedback(user_id)"),
        ("ix_feedback_response_id", "CREATE INDEX IF NOT EXISTS ix_feedback_response_id ON feedback(response_id)"),
        ("ix_feedback_submitted_at", "CREATE INDEX IF NOT EXISTS ix_feedback_submitted_at ON feedback(submitted_at)"),
        ("ix_bias_reports_task_id", "CREATE INDEX IF NOT EXISTS ix_bias_reports_task_id ON bias_reports(task_id)"),
    ]

    for index_name, sql in indexes:
        try:
            cursor.execute(sql)
            print(f"✅ Created index: {index_name}")
        except sqlite3.OperationalError as e:
            if "already exists" in str(e):
                print(f"ℹ️  Index {index_name} already exists")
            else:
                print(f"⚠️  Failed to create index {index_name}: {e}")

    # Commit all changes
    conn.commit()
    conn.close()

    print("\n🎉 Database migration completed successfully!")
    print("\nNext steps:")
    print("  1. Run tests: python -m pytest tests/ -v")
    print("  2. Start the server: uvicorn rlcf_framework.main:app --reload")
    print("  3. Optionally seed data: python -m rlcf_framework.seed_data")

if __name__ == "__main__":
    migrate_database()
