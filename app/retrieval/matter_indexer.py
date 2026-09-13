from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.services.timeline_builder import build_timeline


VAULT_ROOT = Path("app/storage/vault")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _search_blob(extracted: dict[str, Any]) -> str:
    parts: list[str] = []
    parties = extracted.get("parties") or {}
    if isinstance(parties, dict):
        parts.extend(str(value) for value in parties.values() if value)
    parts.extend(str(extracted.get(key) or "") for key in ("case_no", "court", "next_hearing_date"))
    for obligation in extracted.get("obligations") or []:
        if isinstance(obligation, dict):
            parts.extend(str(value) for value in obligation.values() if value)
    return " ".join(parts).lower()


def index_tenant(tenant_id: str) -> list[dict[str, Any]]:
    tenant_root = (VAULT_ROOT / tenant_id / "matters").resolve()
    if not tenant_root.is_relative_to(VAULT_ROOT.resolve()):
        raise ValueError("Unsafe tenant path")
    index: list[dict[str, Any]] = []
    if not tenant_root.exists():
        return index

    for extracted_path in sorted(tenant_root.glob("*/extracted.json")):
        matter_id = extracted_path.parent.name
        extracted = _read_json(extracted_path)
        if not extracted:
            continue
        provenance = _read_json(extracted_path.parent / "provenance.json")
        index.append(
            {
                "tenant_id": tenant_id,
                "matter_id": matter_id,
                "case_no": extracted.get("case_no"),
                "court": extracted.get("court"),
                "parties": extracted.get("parties") or {},
                "next_hearing_date": extracted.get("next_hearing_date"),
                "obligations": extracted.get("obligations") or [],
                "timeline": build_timeline(extracted),
                "source_hash": provenance.get("source_hash"),
                "provenance_verified": False,
                "search_text": _search_blob(extracted),
            }
        )

    index_path = VAULT_ROOT / tenant_id / "matter_index.json"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return index


def search_tenant(tenant_id: str, q: str = "", search_type: str | None = None, before: str | None = None) -> list[dict[str, Any]]:
    index = index_tenant(tenant_id)
    query = (q or "").strip().lower()
    results: list[dict[str, Any]] = []
    for item in index:
        if search_type == "obligation_due":
            due_obligations = []
            for obligation in item.get("obligations") or []:
                if not isinstance(obligation, dict):
                    continue
                due_date = str(obligation.get("due_date") or "")
                if before and due_date and due_date <= before:
                    due_obligations.append(obligation)
            if due_obligations:
                copy = dict(item)
                copy["obligations"] = due_obligations
                results.append(copy)
            continue
        if query and query not in str(item.get("case_no") or "").lower() and query not in item.get("search_text", ""):
            continue
        results.append(item)
    return results
