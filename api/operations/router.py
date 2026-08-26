from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, Depends

from api.auth.dependencies import require_admin
from app.config import APP_DB_PATH, RAW_DIR
from app.database import get_db
from app.intelligence.ai_provider import get_ai_status
from database.connection import SQLITE_DB_PATH, get_db_connection

router = APIRouter(prefix="/api/operations", tags=["Operations"])


def _directory_size(path: Path) -> int:
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file()) if path.exists() else 0


@router.get("/status")
async def operations_status(_: Dict[str, Any] = Depends(require_admin)):
    """Return non-secret operational signals for authorized administrators."""
    with get_db_connection() as conn:
        product = {
            "users": conn.execute("SELECT COUNT(*) FROM users").fetchone()[0],
            "organizations": conn.execute("SELECT COUNT(*) FROM organizations WHERE is_personal = 0").fetchone()[0],
            "conversations": conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0],
            "audit_events_24h": conn.execute(
                "SELECT COUNT(*) FROM audit_events WHERE created_at >= datetime('now', '-1 day')"
            ).fetchone()[0],
        }
    vault = get_db().get_document_stats()
    return {
        "status": "operational",
        "ai": get_ai_status(),
        "product": product,
        "vault": vault,
        "storage_bytes": {
            "product_database": SQLITE_DB_PATH.stat().st_size if SQLITE_DB_PATH.exists() else 0,
            "vault_database": APP_DB_PATH.stat().st_size if APP_DB_PATH.exists() else 0,
            "uploads": _directory_size(RAW_DIR),
        },
    }
