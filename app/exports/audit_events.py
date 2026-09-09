"""Workspace audit event export helpers."""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from typing import Any


LIMITS = (
    "This export is an operational audit trail assembled from application records. "
    "It is not legal advice, a forensic certification, or an independent compliance audit."
)


def _compact(value: Any, fallback: str = "") -> str:
    text = " ".join(str(value or "").split())
    return text or fallback


def build_audit_export(events: list[dict[str, Any]], *, organization_id: str, exported_by: str) -> dict[str, Any]:
    return {
        "export_version": "2026-09-09.audit.v1",
        "exported_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "exported_by_user_id": exported_by,
        "organization_id": organization_id,
        "limits": LIMITS,
        "event_count": len(events),
        "events": events,
    }


def audit_export_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, default=str)


def audit_export_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Workspace Audit Export",
        "",
        f"- Organization: `{_compact(payload.get('organization_id'))}`",
        f"- Exported at: {_compact(payload.get('exported_at'))}",
        f"- Exported by: `{_compact(payload.get('exported_by_user_id'))}`",
        f"- Events: {int(payload.get('event_count') or 0)}",
        "",
        "## Limits",
        "",
        _compact(payload.get("limits"), LIMITS),
        "",
        "## Events",
        "",
    ]
    events = payload.get("events") or []
    if not events:
        lines.append("No audit events matched the selected filters.")
    for event in events:
        metadata = event.get("metadata") or {}
        metadata_text = ", ".join(f"{key}={value}" for key, value in sorted(metadata.items())) or "none"
        lines.extend(
            [
                f"### {_compact(event.get('event_type'), 'AUDIT_EVENT')}",
                "",
                f"- Event ID: `{_compact(event.get('id'))}`",
                f"- Actor: {_compact(event.get('actor_email'), 'Unknown actor')} (`{_compact(event.get('user_id'))}`)",
                f"- Created: {_compact(event.get('created_at'))}",
                f"- Request ID: `{_compact(event.get('request_id'), 'not recorded')}`",
                f"- Client IP: `{_compact(event.get('client_ip'), 'not recorded')}`",
                f"- Metadata: {metadata_text}",
                "",
            ]
        )
    return "\n".join(lines)


def audit_export_csv(events: list[dict[str, Any]]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=["id", "created_at", "event_type", "user_id", "actor_email", "request_id", "client_ip", "metadata_json"],
        lineterminator="\n",
    )
    writer.writeheader()
    for event in events:
        writer.writerow(
            {
                "id": event.get("id") or "",
                "created_at": event.get("created_at") or "",
                "event_type": event.get("event_type") or "",
                "user_id": event.get("user_id") or "",
                "actor_email": event.get("actor_email") or "",
                "request_id": event.get("request_id") or "",
                "client_ip": event.get("client_ip") or "",
                "metadata_json": json.dumps(event.get("metadata") or {}, sort_keys=True, default=str),
            }
        )
    return output.getvalue()
