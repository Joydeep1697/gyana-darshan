# connection.py — Database Engine and Connection Provider for Nyaya Darshana
#
# Supports SQLite for zero-dependency local development and PostgreSQL for production.

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from contextlib import contextmanager
from typing import Generator

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("NYAYA_DATA_DIR", str(BASE_DIR / "data"))).expanduser()
DATA_DIR.mkdir(parents=True, exist_ok=True)

SQLITE_DB_PATH = DATA_DIR / "nyaya_product.db"
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{SQLITE_DB_PATH}")

def get_sqlite_conn() -> sqlite3.Connection:
    """Create a new thread-safe SQLite connection with row factory and foreign keys enabled."""
    conn = sqlite3.connect(str(SQLITE_DB_PATH), timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn

@contextmanager
def get_db_connection() -> Generator[sqlite3.Connection, None, None]:
    """Context manager for database connections."""
    conn = get_sqlite_conn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    """Initialize relational database tables and indexes."""
    from database.models import SCHEMA_DDL
    with get_db_connection() as conn:
        conn.executescript(SCHEMA_DDL)
        evidence_columns = {
            row["name"] for row in conn.execute("PRAGMA table_info(evidence_records)")
        }
        if "supporting_claim" not in evidence_columns:
            conn.execute("ALTER TABLE evidence_records ADD COLUMN supporting_claim TEXT")
        conversation_columns = {
            row["name"] for row in conn.execute("PRAGMA table_info(conversations)")
        }
        if "organization_id" not in conversation_columns:
            conn.execute("ALTER TABLE conversations ADD COLUMN organization_id TEXT")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_conversations_org ON conversations(organization_id, updated_at DESC)"
        )
        audit_columns = {
            row["name"] for row in conn.execute("PRAGMA table_info(audit_events)")
        }
        if "organization_id" not in audit_columns:
            conn.execute("ALTER TABLE audit_events ADD COLUMN organization_id TEXT")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_audit_org ON audit_events(organization_id, created_at DESC)"
        )

        # Existing accounts receive private workspaces without changing ownership semantics.
        users = conn.execute("SELECT id, full_name FROM users").fetchall()
        for user in users:
            org_id = f"personal-{user['id']}"
            timestamp = datetime.now(timezone.utc).isoformat()
            conn.execute(
                """INSERT OR IGNORE INTO organizations
                   (id, name, slug, is_personal, created_by, created_at, updated_at)
                   VALUES (?, ?, ?, 1, ?, ?, ?)""",
                (org_id, f"{user['full_name']}'s workspace", org_id, user["id"], timestamp, timestamp),
            )
            conn.execute(
                """INSERT OR IGNORE INTO organization_members
                   (organization_id, user_id, role, created_at) VALUES (?, ?, 'OWNER', ?)""",
                (org_id, user["id"], timestamp),
            )
            conn.execute(
                "UPDATE conversations SET organization_id = ? WHERE user_id = ? AND organization_id IS NULL",
                (org_id, user["id"]),
            )
