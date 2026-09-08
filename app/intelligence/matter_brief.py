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
    obligations = detail.get("obligations") or []
    documents = detail.get("documents") or []
    notes = detail.get("notes") or []
    playbooks = detail.get("playbooks") or []
    deadlines = detail.get("deadlines") or []

    open_tasks = [task for task in tasks if task.get("status") != "done"]
    open_obligations = [item for item in obligations if item.get("status") not in {"done", "waived"}]
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
    for obligation in open_obligations[:5]:
        due = f", due {obligation['due_date']}" if obligation.get("due_date") else ""
        next_steps.append(f"- Contract obligation: {_compact(obligation.get('title'))} ({_compact(obligation.get('priority'), 'medium')} priority{due})")
    for contract in high_risk_contracts[:3]:
        next_steps.append(f"- Review high-risk contract: {_compact(contract.get('title'))} ({_compact(contract.get('risk_level'))})")
    for contract in renewal_items[:3]:
        days = contract.get("days_to_renewal")
        timing = "overdue" if isinstance(days, int) and days < 0 else f"due in {days} days" if isinstance(days, int) else "due"
        next_steps.append(f"- Renewal follow-up: {_compact(contract.get('title'))} ({timing})")
    urgent_deadlines = [item for item in deadlines if item.get("status") in {"overdue", "due_today", "due"}]
    for item in urgent_deadlines[:5]:
        when = _compact(item.get("deadline_date"), "unscheduled")
        next_steps.append(f"- Deadline: {_compact(item.get('title'), 'Untitled deadline')} ({_compact(item.get('status'), 'scheduled')}, {when})")
    if not next_steps:
        next_steps.append("- No open task, high-risk contract, renewal follow-up, or urgent deadline is recorded.")

    deadline_lines = []
    for item in deadlines[:12]:
        days = item.get("days_until")
        timing = "overdue" if isinstance(days, int) and days < 0 else f"due in {days} days" if isinstance(days, int) else _compact(item.get("status"), "scheduled")
        deadline_lines.append(
            "- "
            + "; ".join([
                _compact(item.get("title"), "Untitled deadline"),
                f"date {_compact(item.get('deadline_date'), 'not recorded')}",
                f"status {_compact(item.get('status'), 'scheduled')}",
                f"timing {timing}",
                f"source {_compact(item.get('source_label'), item.get('kind') or 'record')}",
                f"description {_compact(item.get('description'), 'not recorded')}",
            ])
        )
    if not deadline_lines:
        deadline_lines.append("- No dated matter action is recorded.")

    source_notes = []
    for intake in intakes[:3]:
        source_notes.append(f"- Intake: {_compact(intake.get('title'))} - {_compact(intake.get('summary'), 'No summary')}")
    for note in notes[:5]:
        source_notes.append(f"- Note: {_compact(note.get('body'))}")
    for document in documents[:5]:
        source_notes.append(
            f"- Vault document: {_compact(document.get('filename'))} ({_compact(document.get('status'), 'unknown')})"
        )
    for playbook in playbooks[:3]:
        source_notes.append(
            f"- Playbook: {_compact(playbook.get('title'))} - {_compact(playbook.get('body'), 'No guidance text')[:280]}"
        )
    if not source_notes:
        source_notes.append("- No intake summary, notes, linked Vault document metadata, or relevant playbook is recorded.")

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

    obligation_lines = []
    for obligation in obligations[:8]:
        obligation_lines.append(
            "- "
            + "; ".join([
                _compact(obligation.get("title"), "Untitled obligation"),
                f"status {_compact(obligation.get('status'), 'open')}",
                f"owner {_compact(obligation.get('owner'), 'not recorded')}",
                f"due {_compact(obligation.get('due_date'), 'not recorded')}",
                f"source {_compact(obligation.get('source_clause'), 'not recorded')}",
            ])
        )
    if not obligation_lines:
        obligation_lines.append("- No contractual obligations are linked to this matter.")

    brief = "\n\n".join([
        "Matter Brief",
        "Overview\n" + "\n".join(overview),
        "Recommended Follow-Up\n" + "\n".join(next_steps),
        "Deadline Calendar\n" + "\n".join(deadline_lines),
        "Source Notes\n" + "\n".join(source_notes),
        "Contract Position\n" + "\n".join(contract_lines),
        "Contractual Obligations\n" + "\n".join(obligation_lines),
        "Internal Guidance\n" + ("\n".join(f"- {_compact(item.get('title'), 'Untitled playbook')}: {_compact(item.get('playbook_type'), 'general')}" for item in playbooks[:5]) if playbooks else "- No matching active playbook is recorded for this matter type."),
        "Limits\n- This brief is assembled from workspace records and internal playbooks only. Playbooks are team guidance, not legal authority. This brief does not verify legal merits or replace lawyer review.",
    ])

    sources = []
    if matter.get("id"):
        sources.append({"kind": "matter", "id": matter["id"], "label": _compact(matter.get("title"), "Matter")})
    sources.extend({"kind": "intake", "id": item["id"], "label": _compact(item.get("title"), "Intake")} for item in intakes if item.get("id"))
    sources.extend({"kind": "note", "id": item["id"], "label": "Matter note"} for item in notes if item.get("id"))
    sources.extend({"kind": "task", "id": item["id"], "label": _compact(item.get("title"), "Task")} for item in tasks if item.get("id"))
    sources.extend({"kind": "contract", "id": item["id"], "label": _compact(item.get("title"), "Contract")} for item in contracts if item.get("id"))
    sources.extend({"kind": "obligation", "id": item["id"], "label": _compact(item.get("title"), "Obligation")} for item in obligations if item.get("id"))
    sources.extend({"kind": "document", "id": item["id"], "label": _compact(item.get("filename"), "Vault document")} for item in documents if item.get("id"))
    sources.extend({"kind": "playbook", "id": item["id"], "label": _compact(item.get("title"), "Playbook")} for item in playbooks if item.get("id"))
    sources.extend({"kind": "deadline", "id": str(item["source_id"]), "label": _compact(item.get("title"), "Deadline")} for item in deadlines if item.get("source_id"))

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
            "obligations": len(obligations),
            "intakes": len(intakes),
            "playbooks": len(playbooks),
            "deadlines": len(deadlines),
        },
    }
