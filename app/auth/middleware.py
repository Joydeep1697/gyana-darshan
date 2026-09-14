from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from fastapi import Header, HTTPException
from pydantic import BaseModel

from app.auth.jwt import verify_token


STORAGE_ROOT = Path("app/storage")
USERS_PATH = STORAGE_ROOT / "users.json"
TENANT_RE = re.compile(r"^[a-z0-9-]{3,64}$")


class User(BaseModel):
    user_id: str
    email: str
    tenant_id: str
    role: str


def sanitize_tenant_id(tenant_id: str) -> str:
    cleaned = tenant_id.strip().lower()
    if not TENANT_RE.fullmatch(cleaned):
        raise HTTPException(status_code=400, detail="Invalid tenant_id")
    return cleaned


def get_tenant_vault_path(tenant_id: str) -> Path:
    tenant = sanitize_tenant_id(tenant_id)
    root = (STORAGE_ROOT / "vault").resolve()
    path = (root / tenant).resolve()
    if not path.is_relative_to(root):
        raise HTTPException(status_code=400, detail="Invalid tenant path")
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_users() -> list[dict[str, Any]]:
    if not USERS_PATH.exists():
        return []
    try:
        data = json.loads(USERS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return data if isinstance(data, list) else []


def find_user(email: str) -> dict[str, Any] | None:
    normalized = email.strip().lower()
    for user in load_users():
        if str(user.get("email", "")).lower() == normalized:
            return user
    return None


async def get_current_user(authorization: str | None = Header(default=None, alias="Authorization")) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")
    payload = verify_token(authorization.split(" ", 1)[1].strip())
    user_id = str(payload.get("user_id") or "")
    tenant_id = sanitize_tenant_id(str(payload.get("tenant_id") or ""))
    for user in load_users():
        if user.get("user_id") == user_id and sanitize_tenant_id(str(user.get("tenant_id") or "")) == tenant_id:
            return User(user_id=user_id, email=str(user["email"]), tenant_id=tenant_id, role=str(user.get("role") or "viewer"))
    raise HTTPException(status_code=401, detail="User not found for token")
