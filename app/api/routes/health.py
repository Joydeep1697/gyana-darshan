from __future__ import annotations

import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter

router = APIRouter(tags=["Health"])
STORAGE_DIR = Path("app/storage")
VAULT_DIR = STORAGE_DIR / "vault"
USERS_PATH = STORAGE_DIR / "users.json"
NOTIFICATIONS_DIR = STORAGE_DIR / "notifications"


def _writable(path: Path) -> bool:
    path.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.NamedTemporaryFile(dir=path, delete=True) as handle:
            handle.write(b"ok")
        return True
    except OSError:
        return False


@router.get("/health/detailed")
def health_detailed():
    usage = shutil.disk_usage(STORAGE_DIR if STORAGE_DIR.exists() else Path("."))
    return {
        "status": "ok",
        "version": "0.9",
        "vault_writable": _writable(VAULT_DIR),
        "users_json_readable": USERS_PATH.is_file() and os.access(USERS_PATH, os.R_OK),
        "notifications_dir": str(NOTIFICATIONS_DIR),
        "notifications_writable": _writable(NOTIFICATIONS_DIR),
        "disk_usage": {"total": usage.total, "used": usage.used, "free": usage.free},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
