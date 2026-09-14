from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


LOG_DIR = Path("app/storage/notifications")


def _append_log(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def send_email(to: str, subject: str, html: str) -> dict[str, Any]:
    _append_log(
        LOG_DIR / "email.log",
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "to": to,
            "subject": subject,
            "html_preview": html[:2000],
            "status": "logged_stub",
            "provider": "sendgrid_stub",
        },
    )
    return {"sent": True, "mode": "stub", "provider": "sendgrid_stub"}


def send_whatsapp(to: str, text: str) -> dict[str, Any]:
    _append_log(
        LOG_DIR / "whatsapp.log",
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "to": to,
            "text_preview": text[:1000],
            "status": "logged_stub",
            "provider": "twilio_stub",
        },
    )
    return {"sent": True, "mode": "stub", "provider": "twilio_stub"}


def format_email_html(digest: dict[str, Any]) -> str:
    def rows(items: list[dict[str, Any]]) -> str:
        if not items:
            return "<tr><td colspan='4'>None</td></tr>"
        cells = []
        for item in items:
            cells.append(
                "<tr>"
                f"<td>{item.get('case_no') or item.get('matter_id') or ''}</td>"
                f"<td>{item.get('date') or item.get('due_date') or ''}</td>"
                f"<td>{item.get('description') or item.get('title') or ''}</td>"
                f"<td>{item.get('status') or 'pending'}</td>"
                "</tr>"
            )
        return "".join(cells)

    return (
        f"<h2>Gyana Darshan Daily Digest - {digest.get('date')}</h2>"
        "<p>Data is NOT VERIFIED - Human review required - provenance_verified:false</p>"
        "<h3>Upcoming Hearings</h3><table>"
        f"{rows(digest.get('upcoming_hearings') or [])}</table>"
        "<h3>Upcoming Obligations</h3><table>"
        f"{rows(digest.get('upcoming_obligations') or [])}</table>"
        "<h3>Overdue</h3><table>"
        f"{rows(digest.get('overdue') or [])}</table>"
    )


def format_whatsapp_text(digest: dict[str, Any]) -> str:
    items = (digest.get("upcoming_obligations") or [])[:3]
    lines = [
        f"Gyana Darshan Daily Digest - {digest.get('date')}",
        "NOT VERIFIED - provenance_verified:false",
        f"Hearings: {len(digest.get('upcoming_hearings') or [])}",
        f"Upcoming obligations: {len(digest.get('upcoming_obligations') or [])}",
        f"Overdue: {len(digest.get('overdue') or [])}",
    ]
    lines.extend(f"- {item.get('case_no')}: {item.get('due_date')} {item.get('description')}" for item in items)
    return "\n".join(lines)
