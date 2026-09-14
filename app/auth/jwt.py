from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException


SECRET = os.getenv("JWT_SECRET") or os.getenv("NYAYA_JWT_SECRET") or "dev-secret-change-me-32chars"
ALGO = "HS256"


def _b64e(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64d(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def create_access_token(data: dict[str, Any], expires_delta: timedelta = timedelta(hours=8)) -> str:
    now = datetime.now(timezone.utc)
    payload = dict(data)
    payload.update({"exp": int((now + expires_delta).timestamp()), "iat": int(now.timestamp())})
    header = {"alg": ALGO, "typ": "JWT"}
    signing_input = f"{_b64e(json.dumps(header, separators=(',', ':')).encode())}.{_b64e(json.dumps(payload, separators=(',', ':')).encode())}"
    signature = hmac.new(SECRET.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256).digest()
    return f"{signing_input}.{_b64e(signature)}"


def verify_token(token: str) -> dict[str, Any]:
    try:
        header_b64, payload_b64, sig_b64 = token.split(".", 2)
        signing_input = f"{header_b64}.{payload_b64}"
        expected = _b64e(hmac.new(SECRET.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256).digest())
        if not hmac.compare_digest(expected, sig_b64):
            raise ValueError("bad signature")
        payload = json.loads(_b64d(payload_b64))
        if int(payload.get("exp", 0)) < int(datetime.now(timezone.utc).timestamp()):
            raise ValueError("expired")
        return payload
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc


def hash_password(pwd: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", pwd.encode("utf-8"), salt, 210_000)
    return f"pbkdf2_sha256${_b64e(salt)}${_b64e(digest)}"


def verify_password(plain: str, hashed: str) -> bool:
    try:
        scheme, salt_b64, digest_b64 = hashed.split("$", 2)
        if scheme != "pbkdf2_sha256":
            return False
        salt = _b64d(salt_b64)
        expected = _b64d(digest_b64)
        actual = hashlib.pbkdf2_hmac("sha256", plain.encode("utf-8"), salt, 210_000)
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False
