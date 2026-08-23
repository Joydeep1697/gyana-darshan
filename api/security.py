# security.py — Nyaya Legal OS Production Security, Rate Limiting & Audit Logging Layer
#
# Objective:
# Provide production-grade security controls:
# 1. API Key / Bearer Authentication boundary (with environment override).
# 2. In-memory sliding-window Rate Limiter (e.g. 60 req/min per IP with standard HTTP headers).
# 3. Path & Trace Sanitizer (ensures zero internal filesystem/path leakage in responses).
# 4. Structured JSON Audit Logger (writes to logs/nyaya_api_audit.jsonl).

import os
import time
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials

logger = logging.getLogger("nyaya-security")
BASE_DIR = Path(r"d:\Gyana Darshan")
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)
AUDIT_LOG_FILE = LOGS_DIR / "nyaya_api_audit.jsonl"

# -------------------------------------------------------------
# 1. AUTHENTICATION BOUNDARY
# -------------------------------------------------------------
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)
http_bearer = HTTPBearer(auto_error=False)

# Configurable master key (empty or 'dev' means open access for dev/testing)
def get_master_api_key() -> str:
    return os.environ.get("NYAYA_API_KEY", "").strip()

def verify_api_key(
    api_key: Optional[str] = Security(api_key_header),
    bearer_token: Optional[HTTPAuthorizationCredentials] = Security(http_bearer)
) -> bool:
    """Validate API key or Bearer token if configured; fail-closed in production."""
    master_key = get_master_api_key()
    env = os.environ.get("ENVIRONMENT", os.environ.get("ENV", "development")).lower()
    is_prod = env in ["production", "prod"]

    if is_prod and not master_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server security error: NYAYA_API_KEY is not configured in production mode."
        )

    if not master_key:
        return True  # Open in dev/local mode

    token = api_key or (bearer_token.credentials if bearer_token else None)
    if not token or token.strip() != master_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key. Provide via X-API-Key header or Authorization Bearer token."
        )
    return True


# -------------------------------------------------------------
# 2. IN-MEMORY SLIDING-WINDOW RATE LIMITER
# -------------------------------------------------------------
class InMemoryRateLimiter:
    def __init__(self, requests_per_minute: int = 60):
        self.rpm = requests_per_minute
        self.window = 60.0  # seconds
        self.clients: Dict[str, List[float]] = {}

    def is_allowed(self, client_ip: str) -> Tuple[bool, int, int]:
        now = time.time()
        timestamps = self.clients.get(client_ip, [])
        # Expire older timestamps
        timestamps = [t for t in timestamps if now - t < self.window]
        
        remaining = max(0, self.rpm - len(timestamps))
        reset_time = int(self.window - (now - timestamps[0])) if timestamps else int(self.window)

        if len(timestamps) >= self.rpm:
            self.clients[client_ip] = timestamps
            return False, 0, reset_time

        timestamps.append(now)
        self.clients[client_ip] = timestamps
        return True, remaining - 1, reset_time

rate_limiter = InMemoryRateLimiter(requests_per_minute=300)

class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Exclude health check and static assets from strict rate limits
        if request.url.path in ["/health", "/docs", "/openapi.json"] or request.url.path.startswith("/static"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "127.0.0.1"
        allowed, remaining, reset_time = rate_limiter.is_allowed(client_ip)

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Too Many Requests",
                    "detail": f"Rate limit exceeded. Maximum {rate_limiter.rpm} requests per minute allowed.",
                    "retry_after_seconds": reset_time
                },
                headers={
                    "X-RateLimit-Limit": str(rate_limiter.rpm),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_time),
                    "Retry-After": str(reset_time)
                }
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(rate_limiter.rpm)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_time)
        return response

# -------------------------------------------------------------
# 3. PATH & TRACE SANITIZER
# -------------------------------------------------------------
LEAK_PATTERNS = [
    r"d:\\gyana darshan", r"d:/gyana darshan",
    r"c:\\users\\", r"c:/users/",
    r"\.venv", r"site-packages",
    r"__pycache__"
]

def sanitize_text(text: str) -> str:
    """Strip local filesystem paths and environment paths from responses."""
    if not isinstance(text, str):
        return text
    sanitized = text
    import re
    for pattern in LEAK_PATTERNS:
        sanitized = re.sub(pattern, "[SECURE_INTERNAL_PATH]", sanitized, flags=re.IGNORECASE)
    return sanitized

def sanitize_response_data(data: Any) -> Any:
    """Recursively sanitize dict/list objects."""
    if isinstance(data, dict):
        return {k: sanitize_response_data(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_response_data(item) for item in data]
    elif isinstance(data, str):
        return sanitize_text(data)
    return data

# -------------------------------------------------------------
# 4. STRUCTURED AUDIT LOGGER
# -------------------------------------------------------------
def log_audit_event(
    endpoint: str,
    client_ip: str,
    query: str,
    grounding_status: str,
    interventions_count: int,
    evidence_count: int,
    latency_ms: float,
    status_code: int = 200,
    session_id: Optional[str] = None
):
    """Write structured audit event to jsonl log file."""
    event = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "endpoint": endpoint,
        "client_ip": client_ip,
        "session_id": session_id or "anonymous",
        "query_length": len(query),
        "query_snippet": query[:120],
        "grounding_status": grounding_status,
        "interventions_count": interventions_count,
        "evidence_records_retrieved": evidence_count,
        "latency_ms": latency_ms,
        "status_code": status_code
    }
    try:
        with open(AUDIT_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")
    except Exception as e:
        logger.error(f"Failed to write audit log: {e}")
