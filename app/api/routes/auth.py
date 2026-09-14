from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.auth.jwt import create_access_token, hash_password, verify_password
from app.auth.middleware import USERS_PATH, User, find_user, get_current_user, load_users, sanitize_tenant_id

router = APIRouter(prefix="/api/auth", tags=["Phase 8 Auth"])
LOGIN_LOG = Path("app/storage/auth/login_attempts.jsonl")


class RegisterRequest(BaseModel):
    email: str
    password: str = Field(..., min_length=8)
    tenant_id: str
    role: str = "viewer"


class LoginRequest(BaseModel):
    email: str
    password: str


def _write_users(users: list[dict]) -> None:
    USERS_PATH.parent.mkdir(parents=True, exist_ok=True)
    USERS_PATH.write_text(json.dumps(users, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def _log_attempt(request: Request, email: str, status_text: str) -> None:
    LOGIN_LOG.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "email": email.lower(),
        "status": status_text,
        "ip": request.client.host if request.client else "127.0.0.1",
    }
    with LOGIN_LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest):
    tenant_id = sanitize_tenant_id(payload.tenant_id)
    role = payload.role if payload.role in {"admin", "lawyer", "clerk", "viewer"} else "viewer"
    users = load_users()
    if any(str(user.get("email", "")).lower() == payload.email.lower() for user in users):
        raise HTTPException(status_code=400, detail="Email already registered")
    user = {
        "user_id": f"u_{uuid.uuid4().hex[:12]}",
        "email": payload.email.lower(),
        "password_hash": hash_password(payload.password),
        "tenant_id": tenant_id,
        "role": role,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    users.append(user)
    _write_users(users)
    return {"user_id": user["user_id"], "provenance_verified": False}


@router.post("/login")
def login(payload: LoginRequest, request: Request):
    user = find_user(payload.email)
    if not user or not verify_password(payload.password, str(user.get("password_hash") or "")):
        _log_attempt(request, payload.email, "failed")
        raise HTTPException(status_code=401, detail="Invalid email or password")
    _log_attempt(request, payload.email, "success")
    token = create_access_token(
        {
            "user_id": user["user_id"],
            "tenant_id": user["tenant_id"],
            "role": user["role"],
            "email": user["email"],
        }
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {"email": user["email"], "tenant_id": user["tenant_id"], "role": user["role"]},
    }


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return user.model_dump()
