from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.retrieval.matter_retriever import retrieve, retrieve_by_matter


VAULT_ROOT = Path("app/storage/vault")


def _tenant_root(tenant_id: str) -> Path:
    root = VAULT_ROOT.resolve()
    path = (root / tenant_id / "matters").resolve()
    if not path.is_relative_to(root):
        raise ValueError("Unsafe tenant path")
    return path


def _history_path(tenant_id: str, matter_id: str) -> Path:
    matter_dir = (_tenant_root(tenant_id) / matter_id).resolve()
    if not matter_dir.is_relative_to(_tenant_root(tenant_id)):
        raise ValueError("Unsafe matter path")
    matter_dir.mkdir(parents=True, exist_ok=True)
    return matter_dir / "chat_history.jsonl"


def _append_history(tenant_id: str, matter_id: str, entry: dict[str, Any]) -> None:
    path = _history_path(tenant_id, matter_id)
    line = json.dumps(entry, ensure_ascii=False, sort_keys=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def get_chat_history(tenant_id: str, matter_id: str, limit: int = 50) -> list[dict[str, Any]]:
    path = _history_path(tenant_id, matter_id)
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines()[-max(1, min(limit, 200)):]:
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            item["provenance_verified"] = False
            rows.append(item)
    return rows


def build_context(retrieved: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for item in retrieved:
        obligations = item.get("obligations") or []
        if obligations:
            for obligation in obligations:
                if not isinstance(obligation, dict):
                    continue
                lines.append(
                    "Source: "
                    f"{item.get('case_no') or 'Unknown case'} ({item['matter_id']}) | "
                    f"Hearing: {item.get('next_hearing_date') or 'not captured'} | "
                    f"Obligation: {obligation.get('due_date') or 'not captured'} - {obligation.get('description') or ''} | "
                    "Provenance: NOT VERIFIED"
                )
        else:
            lines.append(
                "Source: "
                f"{item.get('case_no') or 'Unknown case'} ({item['matter_id']}) | "
                f"Hearing: {item.get('next_hearing_date') or 'not captured'} | "
                "Obligation: none captured | Provenance: NOT VERIFIED"
            )
    return "\n".join(lines)


def _citations(retrieved: list[dict[str, Any]]) -> list[dict[str, Any]]:
    citations: list[dict[str, Any]] = []
    for item in retrieved:
        if item.get("next_hearing_date"):
            citations.append({"matter_id": item["matter_id"], "case_no": item.get("case_no"), "field": "next_hearing_date"})
        for obligation in item.get("obligations") or []:
            if isinstance(obligation, dict):
                citations.append({"matter_id": item["matter_id"], "case_no": item.get("case_no"), "field": "obligations"})
                break
    return citations


def chat(
    tenant_id: str,
    query: str,
    matter_id: str | None = None,
    history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    clean_query = query.strip()
    if not clean_query:
        raise ValueError("query is required")
    if matter_id:
        scoped = retrieve_by_matter(tenant_id, matter_id)
        retrieved = [scoped] if scoped else []
    else:
        retrieved = retrieve(tenant_id, clean_query, top_k=5)

    context = build_context(retrieved)
    answer = (
        "NOT VERIFIED - Human review required before legal reliance.\n\n"
        f"Question: {clean_query}\n\n"
        f"{context if context else 'No matching matter facts were found in the tenant vault.'}\n\n"
        "This is a deterministic RAG placeholder response over extracted vault facts. "
        "It does not verify provenance and is not legal advice."
    )
    response = {
        "answer": answer,
        "citations": _citations(retrieved),
        "provenance_verified": False,
        "retrieved_count": len(retrieved),
        "llm_placeholder": True,
    }
    if matter_id:
        _append_history(
            tenant_id,
            matter_id,
            {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "query": clean_query,
                "history": history or [],
                "response": response,
                "provenance_verified": False,
            },
        )
    return response
