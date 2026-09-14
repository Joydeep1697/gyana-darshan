from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any


def calculate_risk_score(risks: list[dict[str, Any]]) -> int:
    total = 0
    llm_scores: list[int] = []
    for risk in risks:
        if "risk_score" in risk:
            try:
                llm_scores.append(int(risk["risk_score"]))
            except (TypeError, ValueError):
                pass
        severity = str(risk.get("severity", "")).lower()
        total += 25 if severity == "high" else 10 if severity == "medium" else 3 if severity == "low" else 0
    regex_score = min(100, total)
    if llm_scores:
        return min(100, round((sum(llm_scores) / len(llm_scores)) * 0.6 + regex_score * 0.4))
    return regex_score


def get_risk_tier(score: int) -> str:
    if score <= 30:
        return "low"
    if score <= 60:
        return "medium"
    return "high"


def get_risk_trends(tenant_id: str, days: int = 30) -> list[dict[str, Any]]:
    root = Path("app/storage/vault") / tenant_id / "matters"
    rows: dict[str, list[int]] = {}
    if root.exists():
        for path in root.glob("*/risk_scan_llm.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            day = str(data.get("analyzed_at", date.today().isoformat()))[:10]
            rows.setdefault(day, []).append(int(data.get("risk_score_combined") or 0))
    return [
        {"date": day, "avg_score": round(sum(scores) / len(scores), 2), "high_count": sum(1 for score in scores if score > 60)}
        for day, scores in sorted(rows.items())[-max(1, min(days, 365)):]
    ]
