from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


LOG_PATH = Path("app/storage/logs/llm.log")
_LAST_CALL = 0.0


def _log(event: dict[str, Any]) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"timestamp": datetime.now(timezone.utc).isoformat(), **event}, ensure_ascii=False, sort_keys=True) + "\n")


def _stub(user_prompt: str) -> dict[str, Any]:
    lower = user_prompt.lower()
    risks = []
    if "indemn" in lower or "hold harmless" in lower:
        risks.append({"type": "indemnity", "severity": "high", "reason": "Indemnity wording shifts liability.", "clause_quote": user_prompt[:240], "redline_suggestion": "Limit indemnity to direct damages, exclude indirect losses, and cap exposure."})
    if "unlimited" in lower and "liab" in lower:
        risks.append({"type": "unlimited_liability", "severity": "high", "reason": "Unlimited liability may create uncapped exposure.", "clause_quote": user_prompt[:240], "redline_suggestion": "Cap liability at fees paid or contract value, with negotiated exceptions."})
    if "auto-renew" in lower or "auto renew" in lower:
        risks.append({"type": "auto_renewal", "severity": "medium", "reason": "Auto renewal can extend obligations without active approval.", "clause_quote": user_prompt[:240], "redline_suggestion": "Require written renewal notice and a clear opt-out period."})
    return {"risks": risks, "risk_score": min(100, 25 * sum(1 for risk in risks if risk["severity"] == "high") + 10 * sum(1 for risk in risks if risk["severity"] == "medium")), "summary": "LLM stub - deterministic clause analysis - provenance_verified:false", "is_stub": True}


def chat_completion(system_prompt: str, user_prompt: str, json_mode: bool = False) -> dict[str, Any]:
    global _LAST_CALL
    provider = os.getenv("LLM_PROVIDER", "stub").strip().lower()
    model = os.getenv("LLM_MODEL", "stub")
    api_key = os.getenv("LLM_API_KEY", "").strip()
    elapsed = time.monotonic() - _LAST_CALL
    if elapsed < 0.5:
        time.sleep(0.5 - elapsed)
    _LAST_CALL = time.monotonic()
    try:
        if provider == "openai" and api_key:
            from openai import OpenAI

            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                response_format={"type": "json_object"} if json_mode else None,
            )
            content = response.choices[0].message.content or ""
            result = {"content": content, "usage": getattr(response, "usage", None), "is_stub": False, "model": model}
        else:
            content = json.dumps(_stub(user_prompt), ensure_ascii=False) if json_mode else f"LLM stub - {user_prompt[:500]} - provenance_verified:false"
            result = {"content": content, "usage": {}, "is_stub": True, "model": "stub"}
        _log({"provider": provider, "model": result["model"], "json_mode": json_mode, "status": "ok", "is_stub": result["is_stub"]})
        return result
    except Exception as exc:
        content = json.dumps(_stub(user_prompt), ensure_ascii=False) if json_mode else f"LLM stub - {user_prompt[:500]} - provenance_verified:false"
        _log({"provider": provider, "model": model, "json_mode": json_mode, "status": "fallback_stub", "error": exc.__class__.__name__})
        return {"content": content, "usage": {}, "is_stub": True, "model": "stub"}
