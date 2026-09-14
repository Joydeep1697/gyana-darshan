from __future__ import annotations

import difflib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _extracted_path(tenant_id: str, matter_id: str) -> Path:
    root = Path("app/storage/vault").resolve()
    path = (root / tenant_id / "matters" / matter_id / "extracted.json").resolve()
    if not path.is_relative_to(root):
        raise ValueError("Unsafe matter path")
    return path


def _load(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _text_from_extracted(extracted: dict[str, Any]) -> str:
    parts = [str(extracted.get("case_no") or ""), str(extracted.get("court") or "")]
    parties = extracted.get("parties") or {}
    if isinstance(parties, dict):
        parts.extend(str(value) for value in parties.values() if value)
    for obligation in extracted.get("obligations") or []:
        if isinstance(obligation, dict):
            parts.append(str(obligation.get("description") or ""))
    return "\n".join(part for part in parts if part)


def load_matter_text(tenant_id: str, matter_id: str) -> str:
    return _text_from_extracted(_load(_extracted_path(tenant_id, matter_id)))


def _sentences(text: str) -> list[str]:
    return [item.strip() for item in re.split(r"[.\n]+", text) if item.strip()]


def compare_texts(text_a: str, text_b: str) -> dict[str, Any]:
    a = _sentences(text_a)
    b = _sentences(text_b)
    matcher = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    added: list[str] = []
    removed: list[str] = []
    changed: list[dict[str, Any]] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "insert":
            added.extend(b[j1:j2])
        elif tag == "delete":
            removed.extend(a[i1:i2])
        elif tag == "replace":
            old = " ".join(a[i1:i2])
            new = " ".join(b[j1:j2])
            changed.append({"old": old, "new": new, "similarity": round(difflib.SequenceMatcher(None, old, new).ratio(), 3)})
    return {
        "added": added,
        "removed": removed,
        "changed": changed,
        "summary": {"added_count": len(added), "removed_count": len(removed), "changed_count": len(changed)},
        "compared_at": datetime.now(timezone.utc).isoformat(),
        "provenance_verified": False,
    }


def compare_versions(tenant_id: str, matter_id: str, v1_extracted: dict[str, Any], v2_extracted: dict[str, Any]) -> dict[str, Any]:
    diff = compare_texts(_text_from_extracted(v1_extracted), _text_from_extracted(v2_extracted))
    return {"matter_id": matter_id, **diff}


def compare_matters(tenant_id: str, matter_id_a: str, matter_id_b: str) -> dict[str, Any]:
    diff = compare_texts(load_matter_text(tenant_id, matter_id_a), load_matter_text(tenant_id, matter_id_b))
    return {"matter_a": matter_id_a, "matter_b": matter_id_b, **diff}
