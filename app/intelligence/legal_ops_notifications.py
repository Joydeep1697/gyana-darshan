"""Deterministic Legal Ops notification and calendar exports."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _compact(value: Any, fallback: str = "") -> str:
    text = " ".join(str(value or "").split())
    return text or fallback


def _ics_text(value: Any) -> str:
    return _compact(value).replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def build_legal_ops_notification_digest(workspace: dict[str, Any]) -> dict[str, Any]:
    """Build an email-ready operational digest from workspace records."""
    summary = workspace.get("summary") or {}
    alerts = workspace.get("action_alerts") or []
    deadlines = [item for item in workspace.get("matter_deadlines") or [] if item.get("status") != "cleared"]
    tasks = [item for item in workspace.get("tasks") or [] if item.get("status") != "done"]
    contracts = [item for item in workspace.get("contracts") or [] if item.get("status") == "approved"]

    ranked_alerts = sorted(alerts, key=lambda item: ({"critical": 0, "high": 1, "medium": 2, "low": 3}.get(item.get("severity") or "medium", 2), item.get("due_date") or "9999-12-31"))
    ranked_deadlines = sorted(deadlines, key=lambda item: (item.get("deadline_date") or "9999-12-31", item.get("title") or ""))
    ranked_tasks = sorted(tasks, key=lambda item: ({"critical": 0, "high": 1, "medium": 2, "low": 3}.get(item.get("priority") or "medium", 2), item.get("due_date") or "9999-12-31"))

    lines = [
        "Legal Ops Notification Digest",
        f"Generated: {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        "",
        "Snapshot",
        f"- {summary.get('open_action_alerts', len(alerts))} open action alerts.",
        f"- {summary.get('open_matter_deadlines', len(deadlines))} open deadlines; {summary.get('overdue_matter_deadlines', 0)} overdue.",
        f"- {len(tasks)} open or in-progress tasks.",
        f"- {summary.get('pending_signature_contracts', len(contracts))} contracts pending signature follow-through.",
        "",
        "Priority alerts",
    ]
    lines.extend(
        [
            f"- [{_compact(item.get('severity'), 'medium')}] {_compact(item.get('title'), 'Untitled alert')} — {_compact(item.get('message'), 'Review required')}"
            for item in ranked_alerts[:8]
        ]
        or ["- No action alert is currently open."]
    )
    lines.extend(["", "Upcoming calendar items"])
    lines.extend(
        [
            f"- {_compact(item.get('deadline_date'), 'No date')}: {_compact(item.get('title'), 'Untitled deadline')} ({_compact(item.get('matter_title'), 'No matter')})"
            for item in ranked_deadlines[:10]
        ]
        or ["- No open deadline is currently recorded."]
    )
    lines.extend(["", "Open task follow-up"])
    lines.extend(
        [
            f"- {_compact(item.get('title'), 'Untitled task')}: {_compact(item.get('priority'), 'medium')} priority, {_compact(item.get('status'), 'open')} status, assignee {_compact(item.get('assignee_name') or item.get('assignee_email'), 'not assigned')}"
            for item in ranked_tasks[:10]
        ]
        or ["- No open task is currently recorded."]
    )
    lines.extend(["", "Limits", "- This digest is assembled from workspace records only. It is not legal advice, delivery confirmation, or proof that external notifications were sent."])

    return {
        "title": "Legal Ops Notification Digest",
        "digest": "\n".join(lines),
        "generated_from": {
            "action_alerts": len(alerts),
            "matter_deadlines": len(deadlines),
            "tasks": len(tasks),
            "pending_signature_contracts": len(contracts),
        },
    }


def build_legal_ops_calendar_ics(workspace: dict[str, Any]) -> str:
    """Export open Legal Ops deadlines as an RFC 5545-compatible all-day calendar."""
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Nyaya Darshana//Legal Ops Calendar//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:Nyaya Darshana Legal Ops",
    ]
    deadlines = [item for item in workspace.get("matter_deadlines") or [] if item.get("status") != "cleared" and _compact(item.get("deadline_date"))]
    for item in sorted(deadlines, key=lambda row: (row.get("deadline_date") or "9999-12-31", row.get("title") or ""))[:200]:
        date_value = _compact(item.get("deadline_date"))[:10].replace("-", "")
        if len(date_value) != 8 or not date_value.isdigit():
            continue
        uid = f"nyaya-{_compact(item.get('kind'), 'deadline')}-{_compact(item.get('source_id'), item.get('id'))}@nyaya-darshana.local"
        description = f"{_compact(item.get('status'), 'scheduled')} · {_compact(item.get('priority'), 'medium')} priority · {_compact(item.get('description'), 'No description')}"
        lines.extend([
            "BEGIN:VEVENT",
            f"UID:{_ics_text(uid)}",
            f"DTSTAMP:{now}",
            f"DTSTART;VALUE=DATE:{date_value}",
            f"SUMMARY:{_ics_text(item.get('title') or 'Legal Ops deadline')}",
            f"DESCRIPTION:{_ics_text(description)}",
            f"CATEGORIES:{_ics_text(item.get('kind') or 'legal_ops')}",
            "END:VEVENT",
        ])
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"
