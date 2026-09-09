"""Portable exports for organization-scoped Nyaya Ops matter records."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any


LIMITS = (
    "Operational record only. This export is not legal advice, a filing, a signing instruction, "
    "or an independent audit of legal merits. Verify source documents and current law before use."
)


def build_matter_export(detail: dict[str, Any], precedents: list[dict[str, Any]], *, exported_by: str) -> dict[str, Any]:
    """Return a stable, auditable export envelope without document file contents."""
    return {
        "export_version": "1.0",
        "exported_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "exported_by_user_id": exported_by,
        "organization_id": detail.get("organization_id"),
        "matter_id": detail.get("id"),
        "limits": LIMITS,
        "matter": detail,
        "precedents": precedents,
        "source_references": {
            "document_ids": [item.get("id") for item in detail.get("documents") or [] if item.get("id")],
            "draft_source_ids": sorted({source.get("id") for draft in detail.get("drafts") or [] for source in draft.get("sources") or [] if source.get("id")}),
            "precedent_ids": [item.get("id") for item in precedents if item.get("id")],
        },
    }


def matter_export_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def matter_export_markdown(payload: dict[str, Any]) -> str:
    matter = payload.get("matter") or {}
    sections = [
        f"# Matter export: {matter.get('title') or 'Untitled matter'}",
        "",
        f"- Matter ID: `{payload.get('matter_id') or ''}`",
        f"- Organization ID: `{payload.get('organization_id') or ''}`",
        f"- Exported at: {payload.get('exported_at') or ''}",
        f"- Exported by user ID: `{payload.get('exported_by_user_id') or ''}`",
        "",
        f"> **Use limit:** {payload.get('limits') or LIMITS}",
        "",
        "## Matter facts",
        "",
        f"- Status: {matter.get('status') or 'unknown'}",
        f"- Priority: {matter.get('priority') or 'unknown'}",
        f"- Type: {matter.get('matter_type') or 'unknown'}",
        f"- Description: {matter.get('description') or 'No description recorded.'}",
    ]
    for key, title, fields in (
        ("intakes", "Intake requests", ("title", "status", "urgency", "summary")),
        ("tasks", "Tasks", ("title", "status", "priority", "assignee_name", "due_date")),
        ("contracts", "Contracts", ("title", "status", "counterparty", "risk_level", "signature_owner_user_id")),
        ("obligations", "Obligations", ("title", "status", "priority", "owner", "due_date", "source_clause")),
        ("spend_entries", "Spend", ("invoice_number", "status", "amount", "currency", "due_date", "description")),
        ("notes", "Notes", ("author_name", "link_kind", "body", "created_at")),
        ("deadlines", "Deadlines", ("kind", "title", "status", "deadline_date", "description")),
        ("drafts", "Drafts", ("title", "review_status", "reviewer_note", "created_at")),
        ("precedents", "Precedents", ("title", "citation", "court", "year", "source_excerpt")),
    ):
        sections.extend(["", f"## {title}", ""])
        records = payload.get(key) if key == "precedents" else matter.get(key)
        records = records or []
        if not records:
            sections.append("No records.")
            continue
        for record in records:
            label = record.get("title") or record.get("invoice_number") or record.get("kind") or "Record"
            details = "; ".join(f"{field.replace('_', ' ')}: {record.get(field)}" for field in fields if record.get(field) not in (None, ""))
            sections.append(f"- **{label}**{': ' + details if details else ''}")
    refs = payload.get("source_references") or {}
    sections.extend(["", "## Source references", "", f"- Vault documents: {', '.join(refs.get('document_ids') or []) or 'None'}", f"- Draft source IDs: {', '.join(refs.get('draft_source_ids') or []) or 'None'}", f"- Precedent IDs: {', '.join(refs.get('precedent_ids') or []) or 'None'}", ""])
    return "\n".join(sections)
