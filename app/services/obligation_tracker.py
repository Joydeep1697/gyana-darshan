from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Literal


VAULT_ROOT = Path("app/storage/vault")
ObligationStatus = Literal["pending", "done", "dismissed"]


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


def _obligation_id(obligation: dict[str, Any], index: int) -> str:
    payload = json.dumps(obligation, ensure_ascii=False, sort_keys=True)
    digest = hashlib.sha256(f"{index}:{payload}".encode("utf-8")).hexdigest()[:16]
    return f"obl-{digest}"


def _iter_obligations(tenant_id: str) -> list[dict[str, Any]]:
    matters_root = _tenant_matters_root(tenant_id)
    if not matters_root.exists():
        return []
    rows: list[dict[str, Any]] = []
    for extracted_path in sorted(matters_root.glob("*/extracted.json")):
        matter_id = extracted_path.parent.name
        extracted = _read_json(extracted_path)
        if not extracted:
            continue
        statuses = _read_json(extracted_path.parent / "obligation_status.json")
        for index, obligation in enumerate(extracted.get("obligations") or []):
            if not isinstance(obligation, dict):
                continue
            due = _parse_iso_date(obligation.get("due_date"))
            if not due:
                continue
            obligation_id = str(obligation.get("id") or _obligation_id(obligation, index))
            rows.append(
                {
                    **obligation,
                    "obligation_id": obligation_id,
                    "status": statuses.get(obligation_id, "pending"),
                    "matter_id": matter_id,
                    "case_no": extracted.get("case_no"),
                    "court": extracted.get("court"),
                    "due_date": due.isoformat(),
                    "provenance_verified": False,
                }
            )
    return sorted(rows, key=lambda item: (item["due_date"], item["matter_id"], item["obligation_id"]))


def get_upcoming_obligations(tenant_id: str, days: int = 7, today: date | None = None) -> list[dict[str, Any]]:
    anchor = today or date.today()
    end = anchor + timedelta(days=max(0, days))
    return [
        row
        for row in _iter_obligations(tenant_id)
        if anchor <= date.fromisoformat(row["due_date"]) <= end and row.get("status") == "pending"
    ]


def get_overdue_obligations(tenant_id: str, today: date | None = None) -> list[dict[str, Any]]:
    anchor = today or date.today()
    return [
        row
        for row in _iter_obligations(tenant_id)
        if date.fromisoformat(row["due_date"]) < anchor and row.get("status") == "pending"
    ]


def mark_obligation_status(
    tenant_id: str,
    matter_id: str,
    obligation_id: str,
    status: ObligationStatus,
) -> dict[str, Any]:
    if status not in {"pending", "done", "dismissed"}:
        raise ValueError("Unsupported obligation status")
    matter_dir = (_tenant_matters_root(tenant_id) / matter_id).resolve()
    if not matter_dir.is_relative_to(_tenant_matters_root(tenant_id)) or not (matter_dir / "extracted.json").is_file():
        raise FileNotFoundError("Matter extraction not found")
    extracted = _read_json(matter_dir / "extracted.json")
    known_ids = {
        str(obligation.get("id") or _obligation_id(obligation, index))
        for index, obligation in enumerate(extracted.get("obligations") or [])
        if isinstance(obligation, dict)
    }
    if obligation_id not in known_ids:
        raise KeyError("Obligation not found")

    status_path = matter_dir / "obligation_status.json"
    statuses = _read_json(status_path)
    statuses[obligation_id] = status
    status_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=status_path.parent, delete=False) as handle:
        json.dump(statuses, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        tmp_name = handle.name
    os.replace(tmp_name, status_path)
    return {
        "tenant_id": tenant_id,
        "matter_id": matter_id,
        "obligation_id": obligation_id,
        "status": status,
        "provenance_verified": False,
    }
