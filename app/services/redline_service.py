from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.services.clause_llm import batch_analyze_matter_clauses


def generate_redline(original_clause: str, risk: dict[str, Any]) -> dict[str, Any]:
    risk_type = str(risk.get("type") or "")
    if risk_type in {"indemnity", "unlimited_liability"}:
        suggested = "Party shall indemnify only for direct damages finally awarded or agreed, capped at the contract value, excluding indirect or consequential losses."
        safer = "Limit liability to direct damages up to fees paid or contract value, with negotiated carve-outs only where necessary."
    elif risk_type == "auto_renewal":
        suggested = "Renewal requires written notice at least 30 days before expiry and either party may decline renewal without penalty."
        safer = "Use explicit renewal approval with a clear opt-out window."
    else:
        suggested = f"[Review required] {original_clause}"
        safer = "Narrow the obligation, define scope, add objective triggers, and cap exposure where appropriate."
    return {"original": original_clause, "suggested": suggested, "explanation": f"AI-generated draft for {risk_type}; lawyer review required.", "safer_alternative": safer, "provenance_verified": False}


def generate_redline_for_matter(tenant_id: str, matter_id: str) -> dict[str, Any]:
    analysis = batch_analyze_matter_clauses(tenant_id, matter_id)
    redlines = []
    for risk in analysis.get("combined_risks", []):
        original = str(risk.get("matched_text") or risk.get("clause_quote") or "")
        redline = generate_redline(original, risk)
        redlines.append({"risk_type": risk.get("type"), "original_snippet": original, "redline_suggestion": redline["suggested"], "severity": risk.get("severity"), "explanation": redline["explanation"], "provenance_verified": False})
    result = {"matter_id": matter_id, "redlines": redlines, "generated_at": datetime.now(timezone.utc).isoformat(), "provenance_verified": False}
    path = Path("app/storage/vault") / tenant_id / "matters" / matter_id / "redlines.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return result
