"""Deterministic, evidence-labeled matter drafting helpers."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from retrieval.hybrid_retriever import AuthoritativeLegalRetriever


@lru_cache(maxsize=1)
def _retriever() -> AuthoritativeLegalRetriever:
    return AuthoritativeLegalRetriever()


def _compact(value: Any, fallback: str = "Not recorded") -> str:
    text = " ".join(str(value or "").split())
    return text or fallback


def build_grounded_matter_draft(
    detail: dict[str, Any],
    *,
    question: str = "",
    precedent_records: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    matter = detail
    prompt = _compact(question, _compact(matter.get("description"), matter.get("title", "Matter")))
    statutory_records: list[dict[str, Any]] = []
    try:
        pack = _retriever().retrieve_evidence_pack(prompt, top_k=6)
        statutory_records = [item for item in pack.get("retrieved_sections", []) if item.get("text") or item.get("heading")]
    except Exception:
        statutory_records = []

    precedents = precedent_records or []
    sources: list[dict[str, Any]] = []
    for item in statutory_records[:6]:
        short_name = item.get("short_name") or item.get("statute") or "Statute"
        section = item.get("section") or ""
        sources.append({
            "kind": "statute",
            "id": str(item.get("id") or f"{short_name}-{section}"),
            "label": f"{short_name} section {section}".strip(),
            "citation": f"{short_name} section {section}".strip(),
            "excerpt": _compact(item.get("text") or item.get("heading"), "No excerpt stored")[:900],
            "status": "authoritative corpus",
        })
    for item in precedents[:8]:
        sources.append({
            "kind": "precedent",
            "id": str(item.get("id") or ""),
            "label": _compact(item.get("title"), "Untitled judgment"),
            "citation": _compact(item.get("citation") or item.get("case_number"), "Unreported"),
            "excerpt": _compact(item.get("excerpt"), "No source excerpt stored")[:1200],
            "status": _compact(item.get("provenance_status"), "uploaded"),
        })

    facts = [
        f"Matter: {_compact(matter.get('title'))}",
        f"Type: {_compact(matter.get('matter_type'))}",
        f"Description: {_compact(matter.get('description'))}",
    ]
    for intake in (matter.get("intakes") or [])[:3]:
        facts.append(f"Intake: {_compact(intake.get('title'))} — {_compact(intake.get('summary'))}")
    for note in (matter.get("notes") or [])[:5]:
        facts.append(f"Workspace note: {_compact(note.get('body'))}")

    authority_lines = [
        f"- [{source['citation']}] {source['excerpt']}"
        for source in sources
        if source["kind"] == "statute"
    ] or ["- No statutory provision was retrieved for this question."]
    precedent_lines = [
        f"- {source['label']} ({source['citation']}; {source['status']}): {source['excerpt']}"
        for source in sources
        if source["kind"] == "precedent"
    ] or ["- No selected or matching precedent was available."]

    unsupported = []
    if not statutory_records:
        unsupported.append("No statutory authority was retrieved; legal conclusions require manual authority selection.")
    if not precedents:
        unsupported.append("No precedent was selected or matched; this draft contains no case-law proposition.")
    unsupported.append("Application of the authorities to the facts remains for qualified legal review.")

    draft = "\n\n".join([
        f"# Grounded draft: {_compact(matter.get('title'), 'Untitled matter')}",
        "Research question\n" + prompt,
        "Recorded matter facts\n" + "\n".join(f"- {fact}" for fact in facts),
        "Statutory authorities for review\n" + "\n".join(authority_lines),
        "Precedents for review\n" + "\n".join(precedent_lines),
        "Drafting position\n- Use the quoted authorities and recorded facts to prepare the final submission. Each proposition must be checked against the cited source before filing or relying on it.",
        "Review flags\n" + "\n".join(f"- {item}" for item in unsupported),
        "Limits\n- This is an evidence-organizing draft, not legal advice, a filed pleading, or a conclusion on the merits. Verify current law, source status, procedural posture, and every citation with a qualified lawyer.",
    ])
    return {
        "matter_id": matter.get("id", ""),
        "title": f"Grounded draft: {_compact(matter.get('title'), 'Untitled matter')}",
        "question": prompt,
        "draft": draft,
        "sources": sources,
        "unsupported_claims": unsupported,
        "generated_from": {"statutes": len(statutory_records), "precedents": len(precedents), "notes": len(matter.get("notes") or []), "documents": len(matter.get("documents") or [])},
    }
