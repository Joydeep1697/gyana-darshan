from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.auth.dependencies import get_workspace_context
from app.auth.rbac import require_permission
from app.services.clause_risk import get_risk_summary, scan_matter_for_risks
from app.services.doc_compare import compare_matters
from app.services.redline_service import generate_redline_for_matter

router = APIRouter()


class CompareRequest(BaseModel):
    matter_id_a: str
    matter_id_b: str


@router.post("/matters/compare")
def compare(payload: CompareRequest, workspace: dict = Depends(get_workspace_context), _user=Depends(require_permission("compare:read"))):
    return compare_matters(workspace["organization"]["id"], payload.matter_id_a, payload.matter_id_b)


@router.post("/matters/{matter_id}/risk-scan")
def risk_scan(matter_id: str, workspace: dict = Depends(get_workspace_context), _user=Depends(require_permission("risk:read"))):
    try:
        return scan_matter_for_risks(workspace["organization"]["id"], matter_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Matter extraction not found") from exc


@router.get("/risks/summary")
def risks_summary(workspace: dict = Depends(get_workspace_context), _user=Depends(require_permission("risk:read"))):
    return get_risk_summary(workspace["organization"]["id"])


@router.get("/matters/{matter_id}/redline/diff")
def redline_diff(matter_id: str, workspace: dict = Depends(get_workspace_context), _user=Depends(require_permission("risk:read"))):
    redlines = generate_redline_for_matter(workspace["organization"]["id"], matter_id)
    return {"matter_id": matter_id, "redlines": redlines.get("redlines", []), "view": "side_by_side", "provenance_verified": False}
