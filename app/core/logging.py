from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Awaitable, Callable

from starlette.requests import Request
from starlette.responses import Response


LOG_DIR = Path("app/storage/logs")
APP_LOG = LOG_DIR / "app.log"


def write_json_log(event: dict) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    payload = {"timestamp": datetime.now(timezone.utc).isoformat(), **event}
    with APP_LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


async def request_logging_middleware(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
    started = time.perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        auth_hint = request.headers.get("Authorization", "")
        tenant = request.headers.get("X-Organization-ID", "")
        write_json_log(
            {
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": status_code,
                "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                "tenant": tenant or "unknown",
                "user_id": "bearer" if auth_hint.lower().startswith("bearer ") else "anonymous",
            }
        )
