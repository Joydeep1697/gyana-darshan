from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.auth.jwt import hash_password
from app.auth.middleware import USERS_PATH


def create_seed_users() -> list[dict[str, str]]:
    USERS_PATH.parent.mkdir(parents=True, exist_ok=True)
    users = [
        {
            "user_id": "u_admin_001",
            "email": "admin@test.com",
            "password_hash": hash_password("Test@1234"),
            "tenant_id": "personal-test",
            "role": "admin",
            "created_at": "2025-12-01T00:00:00Z",
        },
        {
            "user_id": "u_viewer_001",
            "email": "viewer@test.com",
            "password_hash": hash_password("Test@1234"),
            "tenant_id": "personal-test",
            "role": "viewer",
            "created_at": "2025-12-01T00:00:00Z",
        },
    ]
    existing_by_email = {}
    if USERS_PATH.exists():
        try:
            existing_by_email = {item["email"]: item for item in json.loads(USERS_PATH.read_text(encoding="utf-8")) if isinstance(item, dict) and item.get("email")}
        except (OSError, json.JSONDecodeError):
            existing_by_email = {}
    for user in users:
        existing_by_email[user["email"]] = user
    payload = list(existing_by_email.values())
    USERS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return payload


if __name__ == "__main__":
    create_seed_users()
    print(f"Seeded users at {USERS_PATH}")
