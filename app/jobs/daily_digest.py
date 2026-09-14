from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from app.services.calendar_service import get_calendar_events
from app.services.notification_service import format_email_html, send_email
from app.services.obligation_tracker import get_overdue_obligations, get_upcoming_obligations
from app.auth.middleware import load_users


def build_daily_digest(tenant_id: str, today: date | None = None) -> dict[str, Any]:
    anchor = today or date.today()
    upcoming_hearings = [
        event
        for event in get_calendar_events(tenant_id, anchor, anchor + timedelta(days=7))
        if event.get("type") == "hearing"
    ]
    digest = {
        "date": anchor.isoformat(),
        "tenant_id": tenant_id,
        "upcoming_hearings": upcoming_hearings,
        "upcoming_obligations": get_upcoming_obligations(tenant_id, days=7, today=anchor),
        "overdue": get_overdue_obligations(tenant_id, today=anchor),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "provenance_verified": False,
    }
    print(
        "daily_digest",
        {
            "tenant_id": tenant_id,
            "date": digest["date"],
            "hearings": len(digest["upcoming_hearings"]),
            "upcoming_obligations": len(digest["upcoming_obligations"]),
            "overdue": len(digest["overdue"]),
            "provenance_verified": False,
        },
    )
    return digest


def build_digest_for_all_tenants(today: date | None = None) -> list[dict[str, Any]]:
    tenants = sorted({str(user.get("tenant_id")) for user in load_users() if user.get("tenant_id")})
    return [build_daily_digest(tenant, today=today) for tenant in tenants]


def run_and_notify(tenant_id: str, today: date | None = None) -> dict[str, Any]:
    digest = build_daily_digest(tenant_id, today=today)
    html = format_email_html(digest)
    recipients = [user for user in load_users() if user.get("tenant_id") == tenant_id]
    for user in recipients:
        send_email(str(user["email"]), f"Gyana Darshan Daily Digest - {digest['date']}", html)
    log_dir = Path("app/storage/vault") / tenant_id / "notifications"
    log_dir.mkdir(parents=True, exist_ok=True)
    with (log_dir / f"{digest['date']}.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"type": "daily_digest", "digest": digest}, ensure_ascii=False, sort_keys=True) + "\n")
    return digest
