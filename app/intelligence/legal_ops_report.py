"""Deterministic Legal Ops reporting from workspace records."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any


def _compact(value: Any, fallback: str = "") -> str:
    text = " ".join(str(value or "").split())
    return text or fallback


def _money(amount: Any, currency: str = "INR") -> str:
    try:
        numeric = float(amount or 0)
    except (TypeError, ValueError):
        numeric = 0.0
    return f"{currency or 'INR'} {numeric:,.2f}"


def _counts(items: list[dict[str, Any]], field: str = "status") -> dict[str, int]:
    return dict(Counter(_compact(item.get(field), "unknown") for item in items))


def _top_vendors(spend_entries: list[dict[str, Any]], vendors: list[dict[str, Any]]) -> list[str]:
    vendor_names = {vendor["id"]: vendor.get("name") or "Unnamed vendor" for vendor in vendors if vendor.get("id")}
    totals: dict[str, float] = defaultdict(float)
    currencies: dict[str, str] = {}
    for entry in spend_entries:
        vendor_id = entry.get("vendor_id") or "unassigned"
        totals[vendor_id] += float(entry.get("amount") or 0)
        currencies.setdefault(vendor_id, entry.get("currency") or "INR")
    ranked = sorted(totals.items(), key=lambda item: item[1], reverse=True)
    return [
        f"- {_compact(vendor_names.get(vendor_id), 'Unassigned vendor')}: {_money(total, currencies.get(vendor_id, 'INR'))}"
        for vendor_id, total in ranked[:5]
    ]


def _deadline_lines(deadlines: list[dict[str, Any]]) -> list[str]:
    actionable = [item for item in deadlines if item.get("status") != "cleared"]
    ranked = sorted(actionable, key=lambda item: (item.get("deadline_date") or "9999-12-31", item.get("matter_title") or ""))
    lines = []
    for item in ranked[:12]:
        days = item.get("days_until")
        timing = "overdue" if isinstance(days, int) and days < 0 else f"due in {days} days" if isinstance(days, int) else _compact(item.get("status"), "scheduled")
        matter = f" for {_compact(item.get('matter_title'))}" if item.get("matter_title") else ""
        description = f" Description: {_compact(item.get('description'))}." if item.get("description") else ""
        lines.append(
            f"- {_compact(item.get('title'), 'Untitled deadline')}{matter}: "
            f"{_compact(item.get('deadline_date'), 'not dated')}, {_compact(item.get('status'), 'scheduled')}, {timing}."
            f"{description}"
        )
    return lines or ["- No open matter deadline is recorded."]


def _matter_lines(matters: list[dict[str, Any]], spend_entries: list[dict[str, Any]]) -> list[str]:
    spend_by_matter: dict[str, float] = defaultdict(float)
    currency_by_matter: dict[str, str] = {}
    for entry in spend_entries:
        matter_id = entry.get("matter_id")
        if not matter_id:
            continue
        spend_by_matter[matter_id] += float(entry.get("amount") or 0)
        currency_by_matter.setdefault(matter_id, entry.get("currency") or "INR")
    lines = []
    for matter in matters[:10]:
        matter_id = matter.get("id")
        spend = _money(spend_by_matter.get(matter_id, 0), currency_by_matter.get(matter_id, "INR"))
        due = f", due {_compact(matter.get('due_date'))}" if matter.get("due_date") else ""
        lines.append(
            f"- {_compact(matter.get('title'), 'Untitled matter')} "
            f"({_compact(matter.get('status'), 'open')}, {_compact(matter.get('priority'), 'medium')} priority{due}) - spend {spend}"
        )
    return lines or ["- No matters are recorded."]


def build_legal_ops_report(workspace: dict[str, Any]) -> dict[str, Any]:
    """Build a source-labeled management report without adding legal conclusions."""
    summary = workspace.get("summary") or {}
    matters = workspace.get("matters") or []
    intakes = workspace.get("intakes") or []
    tasks = workspace.get("tasks") or []
    contracts = workspace.get("contracts") or []
    obligations = workspace.get("obligations") or []
    reminders = workspace.get("contract_reminders") or []
    vendors = workspace.get("vendors") or []
    spend_entries = workspace.get("spend_entries") or []
    playbooks = workspace.get("playbooks") or []
    matter_deadlines = workspace.get("matter_deadlines") or []

    open_tasks = [task for task in tasks if task.get("status") != "done"]
    open_obligations = [item for item in obligations if item.get("status") not in {"done", "waived"}]
    high_priority_matters = [matter for matter in matters if matter.get("priority") in {"high", "critical"} and matter.get("status") != "closed"]
    high_risk_contracts = [contract for contract in contracts if contract.get("risk_level") in {"high", "critical"}]
    open_spend = float(summary.get("open_spend_total") or 0)
    paid_spend = float(summary.get("paid_spend_total") or 0)

    report = "\n\n".join([
        "Legal Ops Report",
        f"Generated: {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        "Executive Snapshot\n"
        + "\n".join([
            f"- Matters: {len(matters)} total; {_counts(matters).get('open', 0)} open; {len(high_priority_matters)} high-priority open.",
            f"- Intake: {len(intakes)} total; {_counts(intakes).get('new', 0)} new.",
            f"- Tasks: {len(tasks)} total; {len(open_tasks)} open or in progress; {summary.get('overdue_tasks', 0)} overdue.",
            f"- Contracts: {len(contracts)} total; {len(high_risk_contracts)} high-risk; {summary.get('renewals_due_60_days', 0)} renewals due within 60 days; {summary.get('pending_signature_contracts', 0)} pending signature.",
            f"- Obligations: {len(obligations)} total; {len(open_obligations)} open; {summary.get('overdue_contract_obligations', 0)} overdue.",
            f"- Spend: {_money(open_spend)} open; {_money(paid_spend)} paid; {summary.get('overdue_invoices', 0)} overdue invoices.",
            f"- Deadlines: {summary.get('open_matter_deadlines', 0)} open; {summary.get('overdue_matter_deadlines', 0)} overdue; {summary.get('matter_deadlines_due_14_days', 0)} due within 14 days.",
            f"- Knowledge: {len(vendors)} vendors; {summary.get('active_playbooks', 0)} active playbooks.",
        ]),
        "Matter Status\n" + "\n".join(_matter_lines(matters, spend_entries)),
        "Matter Deadlines\n" + "\n".join(_deadline_lines(matter_deadlines)),
        "Risk and Renewal Queue\n"
        + "\n".join(
            [
                f"- {_compact(contract.get('title'), 'Untitled contract')}: {_compact(contract.get('risk_level'), 'unknown')} risk, {_compact(contract.get('status'), 'draft')} status"
                for contract in high_risk_contracts[:8]
            ]
            + [
                f"- Renewal: {_compact(item.get('title'), 'Untitled contract')} due in {item.get('days_to_renewal')} days"
                for item in reminders[:8]
            ]
            or ["- No high-risk contract or renewal reminder is recorded."]
        ),
        "Open Work\n"
        + "\n".join(
            [
                f"- {_compact(task.get('title'), 'Untitled task')}: {_compact(task.get('status'), 'open')}, {_compact(task.get('priority'), 'medium')} priority"
                for task in open_tasks[:10]
            ]
            or ["- No open tasks are recorded."]
        ),
        "Contractual Obligations\n"
        + "\n".join(
            [
                f"- {_compact(item.get('title'), 'Untitled obligation')}: {_compact(item.get('status'), 'open')}, {_compact(item.get('priority'), 'medium')} priority, owner {_compact(item.get('owner'), 'not recorded')}, due {_compact(item.get('due_date'), 'not recorded')}"
                for item in open_obligations[:10]
            ]
            or ["- No open contractual obligations are recorded."]
        ),
        "Vendor Spend\n" + "\n".join(_top_vendors(spend_entries, vendors) or ["- No vendor spend is recorded."]),
        "Playbooks\n"
        + "\n".join(
            [
                f"- {_compact(playbook.get('title'), 'Untitled playbook')}: {_compact(playbook.get('playbook_type'), 'general')} ({_compact(playbook.get('status'), 'active')})"
                for playbook in playbooks[:10]
            ]
            or ["- No playbooks are recorded."]
        ),
        "Limits\n- This report is assembled from workspace operational records only. It is not legal advice, financial approval, or an independent audit.",
    ])

    return {
        "title": "Legal Ops Report",
        "report": report,
        "generated_from": {
            "matters": len(matters),
            "intakes": len(intakes),
            "tasks": len(tasks),
            "contracts": len(contracts),
            "obligations": len(obligations),
            "vendors": len(vendors),
            "spend_entries": len(spend_entries),
            "playbooks": len(playbooks),
            "matter_deadlines": len(matter_deadlines),
        },
    }
