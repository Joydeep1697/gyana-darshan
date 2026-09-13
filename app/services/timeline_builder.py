from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, Field


class TimelineEvent(BaseModel):
    event_type: str = Field(..., min_length=1)
    date: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    description: str = ""
    provenance_verified: bool = False


def _valid_iso_date(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return date.fromisoformat(value.strip()).isoformat()
    except ValueError:
        return None


def build_timeline(extracted: dict[str, Any]) -> list[dict[str, Any]]:
    events: list[TimelineEvent] = []

    hearing_date = _valid_iso_date(extracted.get("next_hearing_date"))
    if hearing_date:
        events.append(
            TimelineEvent(
                event_type="hearing",
                date=hearing_date,
                title="Next hearing",
                description=f"Listed before {extracted.get('court') or 'court not captured'}",
            )
        )

    for obligation in extracted.get("obligations") or []:
        if not isinstance(obligation, dict):
            continue
        due_date = _valid_iso_date(obligation.get("due_date"))
        if not due_date:
            continue
        events.append(
            TimelineEvent(
                event_type=str(obligation.get("type") or "obligation"),
                date=due_date,
                title="Obligation due",
                description=str(obligation.get("description") or "").strip(),
            )
        )

    return [
        event.model_dump()
        for event in sorted(events, key=lambda item: (item.date, item.event_type, item.title))
    ]
