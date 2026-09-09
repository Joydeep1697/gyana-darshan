"""Exports for saved Legal Ops KPI snapshot history."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from app.intelligence.legal_ops_analytics import LIMITS, compare_legal_ops_snapshots


EXPORT_LIMITS = (
    "Operational KPI record only. These snapshots are calculated from saved workspace records. "
    "They are not legal advice, financial approval, performance certification, or an independent audit."
)


def build_kpi_snapshot_history_export(
    organization_id: str,
    snapshots: list[dict[str, Any]],
    *,
    exported_by: str,
) -> dict[str, Any]:
    """Build a stable export envelope for saved KPI snapshots."""
    current = snapshots[0] if snapshots else None
    previous = snapshots[1] if len(snapshots) > 1 else None
    return {
        "export_version": "1.0",
        "title": "Legal Ops KPI Snapshot History",
        "exported_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "exported_by_user_id": exported_by,
        "organization_id": organization_id,
        "limits": EXPORT_LIMITS,
        "snapshot_count": len(snapshots),
        "comparison": compare_legal_ops_snapshots(current, previous) if current and previous else None,
        "snapshots": snapshots,
    }


def kpi_snapshot_history_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _metric_value(snapshot: dict[str, Any], section: str, key: str, default: Any = 0) -> Any:
    analytics = snapshot.get("analytics") or {}
    return (analytics.get(section) or {}).get(key, default)


def kpi_snapshot_history_markdown(payload: dict[str, Any]) -> str:
    sections = [
        "# Legal Ops KPI Snapshot History",
        "",
        f"- Organization ID: `{payload.get('organization_id') or ''}`",
        f"- Exported at: {payload.get('exported_at') or ''}",
        f"- Exported by user ID: `{payload.get('exported_by_user_id') or ''}`",
        f"- Snapshot count: {payload.get('snapshot_count') or 0}",
        "",
        f"> **Use limit:** {payload.get('limits') or LIMITS}",
    ]
    comparison = payload.get("comparison") or {}
    deltas = comparison.get("deltas") or []
    sections.extend(["", "## Latest trend comparison", ""])
    if not deltas:
        sections.append("No comparison is available until at least two snapshots exist.")
    else:
        for delta in deltas:
            sections.append(
                f"- **{delta.get('label') or 'Metric'}:** current {delta.get('current')}, "
                f"previous {delta.get('previous')}, delta {delta.get('delta')}"
            )
    sections.extend(["", "## Saved snapshots", ""])
    snapshots = payload.get("snapshots") or []
    if not snapshots:
        sections.append("No saved KPI snapshots.")
    for snapshot in snapshots:
        label = snapshot.get("label") or "Unlabeled snapshot"
        sections.extend([
            f"### {label}",
            "",
            f"- Snapshot ID: `{snapshot.get('id') or ''}`",
            f"- Created at: {snapshot.get('created_at') or ''}",
            f"- Open matters: {_metric_value(snapshot, 'workload', 'open_matters')}",
            f"- Open tasks: {_metric_value(snapshot, 'workload', 'open_tasks')}",
            f"- Converted intake rate: {_metric_value(snapshot, 'intake_conversion', 'conversion_rate_percent')}%",
            f"- Open deadlines: {_metric_value(snapshot, 'deadline_health', 'open_deadlines')}",
            f"- High-risk contracts: {_metric_value(snapshot, 'contract_health', 'high_risk_contracts')}",
            f"- Total spend recorded: {_metric_value(snapshot, 'spend', 'total_spend_recorded')}",
            f"- Action alerts: {_metric_value(snapshot, 'risk_queue', 'open_action_alerts')}",
            "",
        ])
    return "\n".join(sections).rstrip() + "\n"
