from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any


VAULT_ROOT = Path("app/storage/vault")


def _tenant_matters_root(tenant_id: str) -> Path:
    root = VAULT_ROOT.resolve()
    path = (root / tenant_id / "matters").resolve()
    if not path.is_relative_to(root):
        raise ValueError("Unsafe tenant path")
    return path


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _parse_iso_date(value: Any) -> date | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        return None


def _ics_escape(value: Any) -> str:
    text = str(value or "")
    return text.replace("\\", "\\\\").replace("\n", "\\n").replace(",", "\\,").replace(";", "\\;")


def _event_uid(tenant_id: str, matter_id: str, event_type: str, event_date: str, title: str) -> str:
    digest = hashlib.sha256(f"{tenant_id}:{matter_id}:{event_type}:{event_date}:{title}".encode("utf-8")).hexdigest()
    return f"{digest[:24]}@nyaya-darshana.local"


def _all_events(tenant_id: str) -> list[dict[str, Any]]:
    matters_root = _tenant_matters_root(tenant_id)
    if not matters_root.exists():
        return []
    events: list[dict[str, Any]] = []
    for extracted_path in sorted(matters_root.glob("*/extracted.json")):
        matter_id = extracted_path.parent.name
        extracted = _read_json(extracted_path)
        case_no = str(extracted.get("case_no") or matter_id)
        hearing_date = _parse_iso_date(extracted.get("next_hearing_date"))
        if hearing_date:
            events.append(
                {
                    "date": hearing_date.isoformat(),
                    "type": "hearing",
                    "matter_id": matter_id,
                    "title": f"{case_no} next hearing",
                    "description": f"Next hearing before {extracted.get('court') or 'court not captured'}",
                    "case_no": case_no,
                    "provenance_verified": False,
                }
            )
        for obligation in extracted.get("obligations") or []:
            if not isinstance(obligation, dict):
                continue
            due_date = _parse_iso_date(obligation.get("due_date"))
            if not due_date:
                continue
            description = str(obligation.get("description") or "Obligation due").strip()
            events.append(
                {
                    "date": due_date.isoformat(),
                    "type": "obligation",
                    "matter_id": matter_id,
                    "title": f"{case_no} obligation due",
                    "description": description,
                    "case_no": case_no,
                    "provenance_verified": False,
                }
            )
    return sorted(events, key=lambda item: (item["date"], item["matter_id"], item["type"]))


def get_calendar_events(tenant_id: str, from_date: str | date, to_date: str | date) -> list[dict[str, Any]]:
    start = from_date if isinstance(from_date, date) else date.fromisoformat(from_date)
    end = to_date if isinstance(to_date, date) else date.fromisoformat(to_date)
    if end < start:
        return []
    return [event for event in _all_events(tenant_id) if start <= date.fromisoformat(event["date"]) <= end]


def build_ics(tenant_id: str) -> str:
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Nyaya Darshana//Matter Calendar//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]
    for event in _all_events(tenant_id):
        title = event["title"]
        description = f"{event['description']}\\nprovenance_verified:false; human review required before reliance"
        lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:{_event_uid(tenant_id, event['matter_id'], event['type'], event['date'], title)}",
                f"DTSTART;VALUE=DATE:{event['date'].replace('-', '')}",
                f"SUMMARY:{_ics_escape(title)}",
                f"DESCRIPTION:{_ics_escape(description)}",
                f"CATEGORIES:{_ics_escape(event['type'])}",
                "END:VEVENT",
            ]
        )
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"
