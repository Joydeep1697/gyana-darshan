from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from app.services.calendar_service import get_calendar_events
from app.services.obligation_tracker import get_overdue_obligations, get_upcoming_obligations


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
