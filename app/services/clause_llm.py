from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.services.risk_scoring import calculate_risk_score, get_risk_tier
from app.services.clause_risk import scan_matter_for_risks
from app.services.doc_compare import load_matter_text
from app.services.llm_client import chat_completion


CLAUSE_SYSTEM_PROMPT = "You are legal clause risk analyzer for Indian contracts. Analyze clause for risks, return JSON {risks:[{type,severity:high|medium|low,reason,clause_quote,redline_suggestion}], risk_score 0-100, summary}"


def analyze_clause_with_llm(clause_text: str, context: dict[str, Any]) -> dict[str, Any]:
    prompt = f"Context: {json.dumps(context, ensure_ascii=False)}\nClause: {clause_text}"
    raw = chat_completion(CLAUSE_SYSTEM_PROMPT, prompt, json_mode=True)
    try:
        payload = json.loads(raw.get("content") or "{}")
    except json.JSONDecodeError:
        payload = {"risks": [], "risk_score": 0, "summary": "LLM output was not parseable"}
    risks = payload.get("risks") if isinstance(payload.get("risks"), list) else []
    safe_risks = [risk for risk in risks if isinstance(risk, dict)]
    score = int(payload.get("risk_score") or calculate_risk_score(safe_risks))
    return {"risks": safe_risks, "risk_score": max(0, min(score, 100)), "summary": str(payload.get("summary") or ""), "llm_used": not raw.get("is_stub"), "llm_model": raw.get("model", "stub"), "provenance_verified": False}


def batch_analyze_matter_clauses(tenant_id: str, matter_id: str) -> dict[str, Any]:
    matter_text = load_matter_text(tenant_id, matter_id)
    regex = scan_matter_for_risks(tenant_id, matter_id)
    llm = analyze_clause_with_llm(matter_text, {"case_no": regex.get("case_no"), "court": ""})
    by_type: dict[str, dict[str, Any]] = {}
    for risk in regex.get("risks", []):
        by_type[str(risk.get("type"))] = {**risk, "source": "regex"}
    for risk in llm.get("risks", []):
        by_type.setdefault(str(risk.get("type")), {**risk, "source": "llm"})
    combined = list(by_type.values())
    score = calculate_risk_score([*combined, {"risk_score": llm.get("risk_score", 0)}])
    result = {
        "matter_id": matter_id,
        "case_no": regex.get("case_no"),
        "regex_risks": regex.get("risks", []),
        "llm_risks": llm.get("risks", []),
        "combined_risks": combined,
        "risk_score_combined": score,
        "risk_tier": get_risk_tier(score),
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "llm_model": llm.get("llm_model", "stub"),
        "llm_used": llm.get("llm_used", False),
        "provenance_verified": False,
    }
    out = Path("app/storage/vault") / tenant_id / "matters" / matter_id / "risk_scan_llm.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return result
