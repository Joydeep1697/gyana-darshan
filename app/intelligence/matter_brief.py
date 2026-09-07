"""Deterministic matter brief generation for Legal Ops."""

from __future__ import annotations

from typing import Any


def _compact(value: Any, fallback: str = "") -> str:
    text = " ".join(str(value or "").split())
    return text or fallback


def _line(label: str, value: Any) -> str:
    return f"- {label}: {_compact(value, 'Not recorded')}"


def build_matter_brief(detail: dict[str, Any]) -> dict[str, Any]:
    """Build a source-labeled matter brief without adding legal conclusions."""
    matter = detail
    intakes = detail.get("intakes") or []
    tasks = detail.get("tasks") or []
    contracts = detail.get("contracts") or []
    documents = detail.get("documents") or []
    notes = detail.get("notes") or []

    open_tasks = [task for task in tasks if task.get("status") != "done"]
    high_risk_contracts = [
        contract for contract in contracts
        if contract.get("risk_level") in {"high", "critical"}
    ]
    renewal_items = [
        contract for contract in contracts
        if contract.get("reminder_status") in {"due", "overdue"}
    ]

    overview = [
        _line("Matter", matter.get("title")),
        _line("Type", matter.get("matter_type")),
        _line("Status", matter.get("status")),
        _line("Priority", matter.get("priority")),
        _line("Due date", matter.get("due_date")),
        _line("Description", matter.get("description")),
    ]

    next_steps = []
    for task in open_tasks[:5]:
        due = f", due {task['due_date']}" if task.get("due_date") else ""
        next_steps.append(f"- Task: {_compact(task.get('title'))} ({_compact(task.get('priority'), 'medium')} priority{due})")
    for contract in high_risk_contracts[:3]:
        next_steps.append(f"- Review high-risk contract: {_compact(contract.get('title'))} ({_compact(contract.get('risk_level'))})")
    for contract in renewal_items[:3]:
        days = contract.get("days_to_renewal")
        timing = "overdue" if isinstance(days, int) and days < 0 else f"due in {days} days" if isinstance(days, int) else "due"
        next_steps.append(f"- Renewal follow-up: {_compact(contract.get('title'))} ({timing})")
    if not next_steps:
        next_steps.append("- No open task, high-risk contract, or renewal follow-up is recorded.")

    source_notes = []
    for intake in intakes[:3]:
        source_notes.append(f"- Intake: {_compact(intake.get('title'))} - {_compact(intake.get('summary'), 'No summary')}")
    for note in notes[:5]:
        source_notes.append(f"- Note: {_compact(note.get('body'))}")
    for document in documents[:5]:
        source_notes.append(
            f"- Vault document: {_compact(document.get('filename'))} ({_compact(document.get('status'), 'unknown')})"
        )
    if not source_notes:
        source_notes.append("- No intake summary, notes, or linked Vault document metadata is recorded.")

    contract_lines = []
    for contract in contracts[:5]:
        contract_lines.append(
            "- "
            + "; ".join([
                _compact(contract.get("title"), "Untitled contract"),
                f"status {_compact(contract.get('status'), 'draft')}",
                f"risk {_compact(contract.get('risk_level'), 'unknown')}",
                f"counterparty {_compact(contract.get('counterparty'), 'not recorded')}",
                f"renewal {_compact(contract.get('renewal_date'), 'not recorded')}",
            ])
        )
    if not contract_lines:
        contract_lines.append("- No contract records are linked to this matter.")

    brief = "\n\n".join([
        "Matter Brief",
        "Overview\n" + "\n".join(overview),
        "Recommended Follow-Up\n" + "\n".join(next_steps),
        "Source Notes\n" + "\n".join(source_notes),
        "Contract Position\n" + "\n".join(contract_lines),
        "Limits\n- This brief is assembled from workspace records only. It does not verify legal merits or replace lawyer review.",
    ])

    sources = []
    if matter.get("id"):
        sources.append({"kind": "matter", "id": matter["id"], "label": _compact(matter.get("title"), "Matter")})
    sources.extend({"kind": "intake", "id": item["id"], "label": _compact(item.get("title"), "Intake")} for item in intakes if item.get("id"))
    sources.extend({"kind": "note", "id": item["id"], "label": "Matter note"} for item in notes if item.get("id"))
    sources.extend({"kind": "task", "id": item["id"], "label": _compact(item.get("title"), "Task")} for item in tasks if item.get("id"))
    sources.extend({"kind": "contract", "id": item["id"], "label": _compact(item.get("title"), "Contract")} for item in contracts if item.get("id"))
    sources.extend({"kind": "document", "id": item["id"], "label": _compact(item.get("filename"), "Vault document")} for item in documents if item.get("id"))

    return {
        "matter_id": matter.get("id", ""),
        "title": f"Matter brief: {_compact(matter.get('title'), 'Untitled matter')}",
        "brief": brief,
        "sources": sources[:50],
        "generated_from": {
            "documents": len(documents),
            "notes": len(notes),
            "tasks": len(tasks),
            "contracts": len(contracts),
            "intakes": len(intakes),
        },
    }
