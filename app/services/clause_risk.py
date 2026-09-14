from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


RISK_PATTERNS = [
    {"type": "indemnity", "severity": "high", "pattern": r"indemnif(y|ication)|hold harmless", "desc": "Indemnity clause shifts liability"},
    {"type": "unlimited_liability", "severity": "high", "pattern": r"unlimited.*liab|liab.*unlimited", "desc": "Unlimited liability exposure"},
    {"type": "auto_renewal", "severity": "medium", "pattern": r"auto[\s-]?renew", "desc": "Auto-renewal without notice"},
    {"type": "unilateral_termination", "severity": "high", "pattern": r"terminat.*sole discretion|unilateral.*terminat", "desc": "Unilateral termination right"},
    {"type": "high_penalty", "severity": "high", "pattern": r"penalty.*\d+%|interest.*1[8-9]%|interest.*\d{2,}%", "desc": "High penalty/interest"},
    {"type": "non_compete", "severity": "medium", "pattern": r"non[\s-]?compete", "desc": "Non-compete restriction"},
    {"type": "confidentiality_perpetual", "severity": "medium", "pattern": r"confidential.*perpetual|indefinite.*confidential", "desc": "Perpetual confidentiality"},
]


def _path(tenant_id: str, matter_id: str, name: str) -> Path:
    root = Path("app/storage/vault").resolve()
    path = (root / tenant_id / "matters" / matter_id / name).resolve()
    if not path.is_relative_to(root):
        raise ValueError("Unsafe matter path")
    return path


def _load(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _matter_text(extracted: dict[str, Any]) -> str:
    parts = [str(extracted.get("case_no") or ""), str(extracted.get("court") or "")]
    parties = extracted.get("parties") or {}
    if isinstance(parties, dict):
        parts.extend(str(value) for value in parties.values() if value)
    for obligation in extracted.get("obligations") or []:
        if isinstance(obligation, dict):
            parts.append(str(obligation.get("description") or ""))
    return "\n".join(parts)


def scan_text_for_risks(text: str) -> list[dict[str, Any]]:
    risks: list[dict[str, Any]] = []
    for pattern in RISK_PATTERNS:
        for match in re.finditer(pattern["pattern"], text, flags=re.IGNORECASE | re.DOTALL):
            start = max(0, match.start() - 60)
            end = min(len(text), match.end() + 60)
            risks.append({**pattern, "matched_text": text[start:end][:120], "start_idx": match.start()})
    return risks


def scan_matter_for_risks(tenant_id: str, matter_id: str) -> dict[str, Any]:
    extracted = _load(_path(tenant_id, matter_id, "extracted.json"))
    if not extracted:
        raise FileNotFoundError("Matter extraction not found")
    risks = scan_text_for_risks(_matter_text(extracted))
    risk_score = sum(3 if item["severity"] == "high" else 1 for item in risks)
    result = {
        "matter_id": matter_id,
        "case_no": extracted.get("case_no"),
        "risks": risks,
        "risk_score": risk_score,
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "provenance_verified": False,
    }
    _path(tenant_id, matter_id, "risk_scan.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return result


def get_risk_summary(tenant_id: str) -> dict[str, Any]:
    root = Path("app/storage/vault") / tenant_id / "matters"
    total = high = medium = 0
    if root.exists():
        for matter_dir in root.iterdir():
            if not matter_dir.is_dir() or not (matter_dir / "extracted.json").exists():
                continue
            total += 1
            scan = _load(matter_dir / "risk_scan.json")
            risks = scan.get("risks") if scan else scan_matter_for_risks(tenant_id, matter_dir.name).get("risks")
            if any(item.get("severity") == "high" for item in risks or []):
                high += 1
            if any(item.get("severity") == "medium" for item in risks or []):
                medium += 1
    return {"tenant_id": tenant_id, "total_matters": total, "high_risk_count": high, "medium_risk_count": medium, "provenance_verified": False}
