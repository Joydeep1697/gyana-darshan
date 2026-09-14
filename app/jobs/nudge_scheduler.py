from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from app.auth.middleware import load_users
from app.services.notification_service import send_email
from app.services.obligation_tracker import get_upcoming_obligations


def _notification_dir(tenant_id: str) -> Path:
    path = Path("app/storage/vault") / tenant_id / "notifications"
    path.mkdir(parents=True, exist_ok=True)
    return path


def check_and_nudge(tenant_id: str, today: date | None = None) -> list[dict[str, Any]]:
    anchor = today or date.today()
    nudges: list[dict[str, Any]] = []
    for obligation in get_upcoming_obligations(tenant_id, days=2, today=anchor):
        due = date.fromisoformat(obligation["due_date"])
        days_left = (due - anchor).days
        if days_left not in {0, 1, 2} or obligation.get("status") == "done":
            continue
        description = str(obligation.get("description") or "Obligation")
        message = f"Obligation '{description}' due in {days_left} days for {obligation.get('case_no') or obligation['matter_id']}"
        nudge_id = hashlib.sha256(f"{tenant_id}:{obligation['matter_id']}:{obligation['obligation_id']}:{anchor}".encode()).hexdigest()[:16]
        nudge = {
            "nudge_id": nudge_id,
            "matter_id": obligation["matter_id"],
            "case_no": obligation.get("case_no"),
            "due_date": obligation["due_date"],
            "days_left": days_left,
            "message": message,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "provenance_verified": False,
        }
        nudges.append(nudge)
    if nudges:
        path = _notification_dir(tenant_id) / f"{anchor.isoformat()}.jsonl"
        with path.open("a", encoding="utf-8") as handle:
            for nudge in nudges:
                handle.write(json.dumps({"type": "nudge", **nudge}, ensure_ascii=False, sort_keys=True) + "\n")
        for user in load_users():
            if user.get("tenant_id") == tenant_id and user.get("role") in {"admin", "lawyer"}:
                send_email(str(user["email"]), "Gyana Darshan obligation nudge", "\n".join(nudge["message"] for nudge in nudges))
    return nudges


def get_nudge_history(tenant_id: str, days: int = 30) -> list[dict[str, Any]]:
    history: list[dict[str, Any]] = []
    for path in sorted(_notification_dir(tenant_id).glob("*.jsonl"), reverse=True)[: max(1, min(days, 365))]:
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict):
                item["provenance_verified"] = False
                history.append(item)
    return history
