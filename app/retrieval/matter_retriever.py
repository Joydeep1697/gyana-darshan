from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


VAULT_ROOT = Path("app/storage/vault")


def _tenant_root(tenant_id: str) -> Path:
    root = VAULT_ROOT.resolve()
    path = (root / tenant_id / "matters").resolve()
    if not path.is_relative_to(root):
        raise ValueError("Unsafe tenant path")
    return path


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _tokens(value: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", value.lower()) if len(token) >= 2}


def _blob(extracted: dict[str, Any]) -> str:
    parts: list[str] = []
    parties = extracted.get("parties") or {}
    if isinstance(parties, dict):
        parts.extend(str(item) for item in parties.values() if item)
    parts.extend(str(extracted.get(key) or "") for key in ("case_no", "court", "next_hearing_date"))
    for obligation in extracted.get("obligations") or []:
        if isinstance(obligation, dict):
            parts.extend(str(obligation.get(key) or "") for key in ("description", "due_date", "responsible", "type"))
    return " ".join(parts)


def _snippet(extracted: dict[str, Any], query_tokens: set[str]) -> str:
    candidates: list[str] = []
    if extracted.get("next_hearing_date"):
        candidates.append(f"Next hearing: {extracted['next_hearing_date']}")
    for obligation in extracted.get("obligations") or []:
        if isinstance(obligation, dict):
            candidates.append(f"Obligation: {obligation.get('due_date')} - {obligation.get('description')}")
    for candidate in candidates:
        if not query_tokens or _tokens(candidate) & query_tokens:
            return candidate[:500]
    return " | ".join(candidates)[:500]


def _record(matter_id: str, extracted: dict[str, Any], score: int, query_tokens: set[str]) -> dict[str, Any]:
    return {
        "matter_id": matter_id,
        "case_no": extracted.get("case_no"),
        "score": score,
        "snippet": _snippet(extracted, query_tokens),
        "next_hearing_date": extracted.get("next_hearing_date"),
        "obligations": extracted.get("obligations") or [],
        "provenance_verified": False,
    }


def retrieve(tenant_id: str, query: str, top_k: int = 5) -> list[dict[str, Any]]:
    query_tokens = _tokens(query)
    if not query_tokens:
        return []
    rows: list[dict[str, Any]] = []
    matters_root = _tenant_root(tenant_id)
    if not matters_root.exists():
        return []
    for extracted_path in sorted(matters_root.glob("*/extracted.json")):
        extracted = _read_json(extracted_path)
        if not extracted:
            continue
        blob_tokens = _tokens(_blob(extracted))
        score = len(query_tokens & blob_tokens)
        case_no = str(extracted.get("case_no") or "").lower()
        if case_no and case_no in query.lower():
            score += 5
        if score <= 0:
            continue
        rows.append(_record(extracted_path.parent.name, extracted, score, query_tokens))
    return sorted(rows, key=lambda item: (-item["score"], item["matter_id"]))[: max(1, min(top_k, 20))]


def retrieve_by_matter(tenant_id: str, matter_id: str) -> dict[str, Any] | None:
    matter_dir = (_tenant_root(tenant_id) / matter_id).resolve()
    if not matter_dir.is_relative_to(_tenant_root(tenant_id)):
        raise ValueError("Unsafe matter path")
    extracted = _read_json(matter_dir / "extracted.json")
    if not extracted:
        return None
    return _record(matter_id, extracted, score=999, query_tokens=set())
