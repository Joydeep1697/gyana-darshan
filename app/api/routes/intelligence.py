from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.auth.dependencies import get_workspace_context
from app.auth.rbac import require_permission, require_role
from app.services.risk_scoring import get_risk_trends
from app.services.clause_llm import batch_analyze_matter_clauses
from app.services.obligation_extractor_v2 import re_extract_matter
from app.services.redline_service import generate_redline_for_matter

router = APIRouter()


class AnalyzeRequest(BaseModel):
    use_llm: bool = True


@router.post("/intelligence/matter/{matter_id}/analyze")
def analyze_matter(matter_id: str, _payload: AnalyzeRequest = AnalyzeRequest(), workspace: dict = Depends(get_workspace_context), _perm=Depends(require_permission("risk:read")), _role=Depends(require_role(["admin", "lawyer"]))):
    return batch_analyze_matter_clauses(workspace["organization"]["id"], matter_id)


@router.get("/intelligence/matter/{matter_id}/risks")
def matter_risks(matter_id: str, workspace: dict = Depends(get_workspace_context), _perm=Depends(require_permission("risk:read"))):
    matter_dir = Path("app/storage/vault") / workspace["organization"]["id"] / "matters" / matter_id
    payload = {"matter_id": matter_id, "risk_scan": {}, "risk_scan_llm": {}, "provenance_verified": False}
    for name in ("risk_scan.json", "risk_scan_llm.json"):
        path = matter_dir / name
        if path.exists():
            try:
                payload[name.removesuffix(".json")] = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                payload[name.removesuffix(".json")] = {}
    return payload


@router.post("/intelligence/matter/{matter_id}/redline")
def create_redline(matter_id: str, workspace: dict = Depends(get_workspace_context), _role=Depends(require_role(["admin", "lawyer"]))):
    return generate_redline_for_matter(workspace["organization"]["id"], matter_id)


@router.get("/intelligence/matter/{matter_id}/redline")
def get_redline(matter_id: str, workspace: dict = Depends(get_workspace_context)):
    path = Path("app/storage/vault") / workspace["organization"]["id"] / "matters" / matter_id / "redlines.json"
    if not path.exists():
        return {"matter_id": matter_id, "redlines": [], "provenance_verified": False}
    return json.loads(path.read_text(encoding="utf-8"))


@router.post("/intelligence/matter/{matter_id}/reextract")
def reextract(matter_id: str, payload: AnalyzeRequest, workspace: dict = Depends(get_workspace_context), _role=Depends(require_role(["admin", "lawyer"]))):
    try:
        return re_extract_matter(workspace["organization"]["id"], matter_id, use_llm=payload.use_llm)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Matter extraction not found") from exc


@router.get("/intelligence/trends")
def trends(days: int = 30, workspace: dict = Depends(get_workspace_context), _perm=Depends(require_permission("risk:read"))):
    return {"trends": get_risk_trends(workspace["organization"]["id"], days=days), "provenance_verified": False}
