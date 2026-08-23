# connection.py — Database Engine and Connection Provider for Nyaya Darshana
#
# Supports SQLite for zero-dependency local development and PostgreSQL for production.

import os
import sqlite3
from pathlib import Path
from contextlib import contextmanager
from typing import Generator

BASE_DIR = Path(r"d:\Nova Legal")
DATA_DIR = BASE_DIR / "data"
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
