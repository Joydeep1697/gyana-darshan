# service.py — Authentication, Password Hashing & JWT Session Token Service
#
# Implements:
# - PBKDF2-HMAC-SHA256 password hashing with 600,000 iterations and cryptographically secure random salt
# - JWT generation & cryptographic HMAC-SHA256 signature verification (zero-external-dependency standard library implementation)
# - Session token lifecycle with expiration, revocation, and refresh support

import os
import hmac
import base64
import json
import time
import secrets
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Tuple

from database.repository import UserRepository, SessionRepository

# Development uses a random process-local signing key. Production requires a
# persistent deployment secret so tokens remain valid across worker processes.
_DEVELOPMENT_JWT_SECRET = secrets.token_urlsafe(48)


def get_jwt_secret_key() -> str:
    configured_secret = os.environ.get("NYAYA_JWT_SECRET", "").strip()
    environment = os.environ.get("ENVIRONMENT", os.environ.get("ENV", "development")).lower()
    if environment in {"production", "prod"}:
        if len(configured_secret) < 32:
            raise RuntimeError(
                "NYAYA_JWT_SECRET must contain at least 32 characters in production mode."
            )
        return configured_secret
    return configured_secret or _DEVELOPMENT_JWT_SECRET


ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # 24 hours
REFRESH_TOKEN_EXPIRE_DAYS = 30

def hash_password(password: str) -> str:
    """Hash password using PBKDF2-HMAC-SHA256 with 600,000 iterations and 16-byte random salt."""
    salt = secrets.token_bytes(16)
    iterations = 600000
    derived = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, iterations)
    # Format: pbkdf2_sha256$iterations$salt_b64$hash_b64
    salt_b64 = base64.b64encode(salt).decode('ascii')
    hash_b64 = base64.b64encode(derived).decode('ascii')
    return f"pbkdf2_sha256${iterations}${salt_b64}${hash_b64}"

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against PBKDF2-HMAC-SHA256 stored hash in constant time."""
    try:
        parts = hashed.split('$')
        if len(parts) != 4 or parts[0] != 'pbkdf2_sha256':
            return False
        iterations = int(parts[1])
        salt = base64.b64decode(parts[2].encode('ascii'))
        expected_hash = base64.b64decode(parts[3].encode('ascii'))
        candidate_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, iterations)
        return hmac.compare_digest(candidate_hash, expected_hash)
    except Exception:
        return False

def _b64_url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode('ascii').rstrip('=')

def _b64_url_decode(data_str: str) -> bytes:
    padding = '=' * (-len(data_str) % 4)
    return base64.urlsafe_b64decode((data_str + padding).encode('ascii'))

def create_jwt_token(payload: Dict[str, Any], expires_delta: timedelta) -> str:
    """Generate a standard HS256-signed JWT token."""
    header = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())
    exp = now + int(expires_delta.total_seconds())
    
    full_payload = dict(payload)
    full_payload.update({"iat": now, "exp": exp})

    header_bytes = json.dumps(header, separators=(',', ':')).encode('utf-8')
    payload_bytes = json.dumps(full_payload, separators=(',', ':')).encode('utf-8')

    segments = [_b64_url_encode(header_bytes), _b64_url_encode(payload_bytes)]
    signing_input = ".".join(segments).encode('ascii')
    signature = hmac.new(get_jwt_secret_key().encode('utf-8'), signing_input, hashlib.sha256).digest()
    segments.append(_b64_url_encode(signature))
    return ".".join(segments)

def decode_jwt_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify signature and expiration of an HS256-signed JWT token."""
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return None
        
        signing_input = f"{parts[0]}.{parts[1]}".encode('ascii')
        expected_sig = hmac.new(get_jwt_secret_key().encode('utf-8'), signing_input, hashlib.sha256).digest()
        provided_sig = _b64_url_decode(parts[2])

        if not hmac.compare_digest(expected_sig, provided_sig):
            return None
        
        payload = json.loads(_b64_url_decode(parts[1]).decode('utf-8'))
        now = int(time.time())
        if payload.get("exp", 0) < now:
            return None # Expired
        
        return payload
    except Exception:
        return None

class AuthService:
    @staticmethod
    def register_user(email: str, password: str, full_name: str, role: str = "USER") -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Register a new user account."""
        clean_email = email.lower().strip()
        if not clean_email or "@" not in clean_email:
            return None, "Invalid email address format."
        if len(password) < 8:
            return None, "Password must be at least 8 characters long."
        if not full_name.strip():
            return None, "Full name cannot be empty."

        existing = UserRepository.get_by_email(clean_email)
        if existing:
            return None, "An account with this email already exists."

        pwd_hash = hash_password(password)
        # Public registration must never grant administrative privileges based
        # on timing; administrator provisioning requires a separate trusted flow.
        user = UserRepository.create_user(clean_email, pwd_hash, full_name, role)
        return user, None

    @staticmethod
    def authenticate_user(email: str, password: str) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, str]], Optional[str]]:
        """Validate credentials and issue access + refresh tokens."""
        clean_email = email.lower().strip()
        user = UserRepository.get_by_email(clean_email)
        if not user or not verify_password(password, user["password_hash"]):
            return None, None, "Invalid email or password."

        # Create access token
        access_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_jwt_token({
            "sub": user["id"],
            "email": user["email"],
            "role": user["role"],
            "type": "access"
        }, access_delta)

        # Create refresh token & record session in DB
        refresh_delta = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        refresh_token = secrets.token_urlsafe(48)
        refresh_hash = hashlib.sha256(refresh_token.encode('utf-8')).hexdigest()
        expires_at = (datetime.now(timezone.utc) + refresh_delta).isoformat()
        
        SessionRepository.create_session(user["id"], refresh_hash, expires_at)

        tokens = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in_seconds": int(access_delta.total_seconds())
        }
        return user, tokens, None

    @staticmethod
    def refresh_access_token(refresh_token: str) -> Tuple[Optional[str], Optional[str]]:
        """Validate refresh token and issue a fresh access token."""
        refresh_hash = hashlib.sha256(refresh_token.encode('utf-8')).hexdigest()
        session = SessionRepository.get_active_session(refresh_hash)
        if not session:
            return None, "Invalid or expired refresh token."

        user = UserRepository.get_by_id(session["user_id"])
        if not user:
            return None, "User associated with this session no longer exists."

        access_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        new_access_token = create_jwt_token({
            "sub": user["id"],
            "email": user["email"],
            "role": user["role"],
            "type": "access"
        }, access_delta)

        return new_access_token, None

    @staticmethod
    def logout(refresh_token: str) -> bool:
        """Revoke the active session."""
        refresh_hash = hashlib.sha256(refresh_token.encode('utf-8')).hexdigest()
        return SessionRepository.revoke_session(refresh_hash)
