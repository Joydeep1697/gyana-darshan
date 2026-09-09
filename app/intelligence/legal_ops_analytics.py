"""Deterministic KPI analytics for Legal Ops workspace records."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any


LIMITS = (
    "These KPIs are calculated from workspace operational records only. "
    "They are not legal advice, financial approval, performance certification, or an independent audit."
)


def _compact(value: Any, fallback: str = "") -> str:
    text = " ".join(str(value or "").split())
    return text or fallback


def _counts(items: list[dict[str, Any]], field: str = "status") -> dict[str, int]:
    return dict(Counter(_compact(item.get(field), "unknown") for item in items))


def _rate(part: int, whole: int) -> float:
    if whole <= 0:
        return 0.0
    return round((part / whole) * 100, 2)


def _amount(value: Any) -> float:
    try:
        return round(float(value or 0), 2)
    except (TypeError, ValueError):
        return 0.0


def _open_status(item: dict[str, Any], closed: set[str]) -> bool:
    return _compact(item.get("status"), "open") not in closed


def _member_label(member: dict[str, Any]) -> str:
    return _compact(member.get("full_name")) or _compact(member.get("email")) or "Unknown member"


def _team_task_rows(tasks: list[dict[str, Any]], members: list[dict[str, Any]]) -> list[dict[str, Any]]:
    members_by_id = {member.get("id"): member for member in members if member.get("id")}
    rows: dict[str, dict[str, Any]] = {}
    for task in tasks:
        assignee_id = task.get("assignee_user_id") or "unassigned"
        member = members_by_id.get(assignee_id, {})
        row = rows.setdefault(
            assignee_id,
            {
                "assignee_user_id": "" if assignee_id == "unassigned" else assignee_id,
                "assignee_name": "Unassigned" if assignee_id == "unassigned" else _member_label(member),
                "open_tasks": 0,
                "in_progress_tasks": 0,
                "completed_tasks": 0,
                "overdue_tasks": 0,
                "critical_or_high_tasks": 0,
                "total_tasks": 0,
            },
        )
        row["total_tasks"] += 1
        status = _compact(task.get("status"), "open")
        if status == "done":
            row["completed_tasks"] += 1
        elif status == "in_progress":
            row["in_progress_tasks"] += 1
        else:
            row["open_tasks"] += 1
        if task.get("is_overdue"):
            row["overdue_tasks"] += 1
        if _compact(task.get("priority"), "medium") in {"critical", "high"} and status != "done":
            row["critical_or_high_tasks"] += 1
    return sorted(rows.values(), key=lambda item: (-item["critical_or_high_tasks"], -item["open_tasks"], item["assignee_name"]))


def _top_vendors(spend_entries: list[dict[str, Any]], vendors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    names = {vendor.get("id"): _compact(vendor.get("name"), "Unnamed vendor") for vendor in vendors if vendor.get("id")}
    totals: dict[str, float] = defaultdict(float)
    currencies: dict[str, str] = {}
    for entry in spend_entries:
        vendor_id = entry.get("vendor_id") or "unassigned"
        totals[vendor_id] += _amount(entry.get("amount"))
        currencies.setdefault(vendor_id, _compact(entry.get("currency"), "INR"))
    ranked = sorted(totals.items(), key=lambda item: item[1], reverse=True)
    return [
        {
            "vendor_id": "" if vendor_id == "unassigned" else vendor_id,
            "vendor_name": names.get(vendor_id, "Unassigned vendor"),
            "amount": round(total, 2),
            "currency": currencies.get(vendor_id, "INR"),
        }
        for vendor_id, total in ranked[:5]
    ]


def build_legal_ops_analytics(workspace: dict[str, Any]) -> dict[str, Any]:
    """Build structured management KPIs without model-generated conclusions."""
    summary = workspace.get("summary") or {}
    matters = workspace.get("matters") or []
    intakes = workspace.get("intakes") or []
    tasks = workspace.get("tasks") or []
    contracts = workspace.get("contracts") or []
    obligations = workspace.get("obligations") or []
    vendors = workspace.get("vendors") or []
    spend_entries = workspace.get("spend_entries") or []
    playbooks = workspace.get("playbooks") or []
    matter_deadlines = workspace.get("matter_deadlines") or []
    alerts = workspace.get("action_alerts") or []
    members = workspace.get("members") or []

    open_matters = [item for item in matters if _open_status(item, {"closed"})]
    high_priority_open_matters = [item for item in open_matters if _compact(item.get("priority"), "medium") in {"critical", "high"}]
    converted_intakes = [item for item in intakes if item.get("matter_id") or _compact(item.get("status")) == "converted"]
    open_intakes = [item for item in intakes if _open_status(item, {"closed", "converted"})]
    open_tasks = [item for item in tasks if _open_status(item, {"done"})]
    completed_tasks = [item for item in tasks if _compact(item.get("status")) == "done"]
    open_obligations = [item for item in obligations if _open_status(item, {"done", "waived"})]
    open_deadlines = [item for item in matter_deadlines if _compact(item.get("status")) != "cleared"]

    for task in tasks:
        task["is_overdue"] = bool(
            task.get("status") != "done"
            and task.get("due_date")
            and task.get("due_date") < datetime.now(timezone.utc).date().isoformat()
        )

    open_spend_total = _amount(summary.get("open_spend_total"))
    paid_spend_total = _amount(summary.get("paid_spend_total"))

    return {
        "title": "Legal Ops KPI Analytics",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "limits": LIMITS,
        "workload": {
            "total_matters": len(matters),
            "open_matters": len(open_matters),
            "high_priority_open_matters": len(high_priority_open_matters),
            "total_tasks": len(tasks),
            "open_tasks": len(open_tasks),
            "completed_tasks": len(completed_tasks),
            "overdue_tasks": int(summary.get("overdue_tasks") or 0),
            "unassigned_open_tasks": len([item for item in open_tasks if not item.get("assignee_user_id")]),
            "matters_by_status": _counts(matters),
            "tasks_by_status": _counts(tasks),
            "matters_by_priority": _counts(matters, "priority"),
            "tasks_by_priority": _counts(tasks, "priority"),
        },
        "intake_conversion": {
            "total_intake": len(intakes),
            "open_intake": len(open_intakes),
            "new_intake": int((summary.get("intake_by_status") or {}).get("new", 0)),
            "converted_intake": len(converted_intakes),
            "conversion_rate_percent": _rate(len(converted_intakes), len(intakes)),
            "intake_by_status": _counts(intakes),
            "intake_by_urgency": _counts(intakes, "urgency"),
        },
        "deadline_health": {
            "total_deadlines": len(matter_deadlines),
            "open_deadlines": len(open_deadlines),
            "overdue_deadlines": int(summary.get("overdue_matter_deadlines") or 0),
            "due_14_days": int(summary.get("matter_deadlines_due_14_days") or 0),
            "deadlines_by_source": _counts(matter_deadlines, "kind"),
            "deadlines_by_status": _counts(matter_deadlines),
        },
        "contract_health": {
            "total_contracts": len(contracts),
            "high_risk_contracts": int(summary.get("high_risk_contracts") or 0),
            "pending_signature_contracts": int(summary.get("pending_signature_contracts") or 0),
            "renewals_due_60_days": int(summary.get("renewals_due_60_days") or 0),
            "open_obligations": len(open_obligations),
            "overdue_obligations": int(summary.get("overdue_contract_obligations") or 0),
            "contracts_by_status": _counts(contracts),
            "contracts_by_risk": _counts(contracts, "risk_level"),
            "obligations_by_status": _counts(obligations),
        },
        "spend": {
            "open_spend_total": open_spend_total,
            "paid_spend_total": paid_spend_total,
            "total_spend_recorded": round(open_spend_total + paid_spend_total, 2),
            "overdue_invoices": int(summary.get("overdue_invoices") or 0),
            "spend_by_status": _counts(spend_entries),
            "top_vendors": _top_vendors(spend_entries, vendors),
        },
        "team_throughput": {
            "workspace_members": len(members),
            "assigned_open_tasks": len([item for item in open_tasks if item.get("assignee_user_id")]),
            "completed_tasks": len(completed_tasks),
            "completion_rate_percent": _rate(len(completed_tasks), len(tasks)),
            "tasks_by_assignee": _team_task_rows(tasks, members),
        },
        "knowledge_assets": {
            "vendors": len(vendors),
            "active_playbooks": int(summary.get("active_playbooks") or 0),
            "playbooks_by_status": _counts(playbooks),
        },
        "risk_queue": {
            "open_action_alerts": len(alerts),
            "high_priority_action_alerts": int(summary.get("high_priority_action_alerts") or 0),
            "alerts_by_kind": _counts(alerts, "kind"),
            "alerts_by_severity": _counts(alerts, "severity"),
        },
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
            "action_alerts": len(alerts),
        },
    }


TREND_METRICS = (
    ("workload", "open_matters", "Open matters"),
    ("workload", "open_tasks", "Open tasks"),
    ("workload", "overdue_tasks", "Overdue tasks"),
    ("intake_conversion", "conversion_rate_percent", "Intake conversion rate"),
    ("deadline_health", "overdue_deadlines", "Overdue deadlines"),
    ("deadline_health", "due_14_days", "Deadlines due in 14 days"),
    ("contract_health", "high_risk_contracts", "High-risk contracts"),
    ("contract_health", "pending_signature_contracts", "Pending signature contracts"),
    ("spend", "open_spend_total", "Open spend"),
    ("spend", "paid_spend_total", "Paid spend"),
    ("team_throughput", "completion_rate_percent", "Task completion rate"),
    ("risk_queue", "open_action_alerts", "Open action alerts"),
)


def _snapshot_analytics(snapshot: dict[str, Any] | None) -> dict[str, Any]:
    if not snapshot:
        return {}
    if "analytics" in snapshot:
        return snapshot.get("analytics") or {}
    return snapshot


def _metric(snapshot: dict[str, Any] | None, section: str, key: str) -> float:
    value = (_snapshot_analytics(snapshot).get(section) or {}).get(key, 0)
    try:
        return round(float(value or 0), 2)
    except (TypeError, ValueError):
        return 0.0


def compare_legal_ops_snapshots(current: dict[str, Any], previous: dict[str, Any] | None) -> dict[str, Any]:
    """Compare two saved KPI snapshots with deterministic numeric deltas."""
    current_analytics = _snapshot_analytics(current)
    previous_analytics = _snapshot_analytics(previous)
    deltas = []
    for section, key, label in TREND_METRICS:
        current_value = _metric(current, section, key)
        previous_value = _metric(previous, section, key)
        delta = round(current_value - previous_value, 2)
        deltas.append({
            "section": section,
            "key": key,
            "label": label,
            "current": current_value,
            "previous": previous_value,
            "delta": delta,
            "direction": "up" if delta > 0 else "down" if delta < 0 else "flat",
        })
    return {
        "title": "Legal Ops KPI Trend Comparison",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "limits": LIMITS,
        "current_snapshot_id": (current or {}).get("id", ""),
        "previous_snapshot_id": (previous or {}).get("id", ""),
        "current_generated_at": current_analytics.get("generated_at") or (current or {}).get("created_at", ""),
        "previous_generated_at": previous_analytics.get("generated_at") or (previous or {}).get("created_at", ""),
        "deltas": deltas,
    }
