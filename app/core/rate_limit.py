from __future__ import annotations

import json
import time
from collections import defaultdict
from pathlib import Path
from typing import Awaitable, Callable

from starlette.requests import Request
from starlette.responses import JSONResponse, Response


LOGIN_ATTEMPTS: dict[str, list[float]] = defaultdict(list)
LOG_PATH = Path("app/storage/ratelimit.jsonl")


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For", "").split(",", 1)[0].strip()
    return forwarded or (request.client.host if request.client else "127.0.0.1")


async def login_rate_limit_middleware(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    if request.url.path != "/api/auth/login" or request.method.upper() != "POST":
        return await call_next(request)
    ip = _client_ip(request)
    now = time.time()
    LOGIN_ATTEMPTS[ip] = [stamp for stamp in LOGIN_ATTEMPTS[ip] if now - stamp < 60]
    if len(LOGIN_ATTEMPTS[ip]) >= 5:
        retry_after = int(60 - (now - LOGIN_ATTEMPTS[ip][0]))
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"timestamp": int(now), "ip": ip, "path": request.url.path, "status": 429}) + "\n")
        return JSONResponse(
            status_code=429,
            content={"detail": "Too many login attempts. Retry later."},
            headers={"Retry-After": str(max(1, retry_after))},
        )
    LOGIN_ATTEMPTS[ip].append(now)
    return await call_next(request)
