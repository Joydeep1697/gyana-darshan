from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from api.auth.dependencies import get_workspace_context
from app.auth.rbac import require_role
from app.jobs.daily_digest import run_and_notify
from app.jobs.nudge_scheduler import check_and_nudge, get_nudge_history

router = APIRouter()


@router.get("/notifications")
def notifications(days: int = Query(default=7, ge=1, le=90), workspace: dict = Depends(get_workspace_context)):
    tenant_id = workspace["organization"]["id"]
    return {"tenant_id": tenant_id, "notifications": get_nudge_history(tenant_id, days=days), "provenance_verified": False}


@router.post("/notifications/test-digest")
def test_digest(workspace: dict = Depends(get_workspace_context), _user=Depends(require_role(["admin", "lawyer"]))):
    return run_and_notify(workspace["organization"]["id"])


@router.post("/notifications/test-nudge")
def test_nudge(workspace: dict = Depends(get_workspace_context), _user=Depends(require_role(["admin", "lawyer"]))):
    return {"nudges": check_and_nudge(workspace["organization"]["id"]), "provenance_verified": False}
