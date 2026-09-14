from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from api.auth.dependencies import get_workspace_context
from app.auth.rbac import require_role
from app.jobs.daily_digest import run_and_notify
from app.jobs.nudge_scheduler import check_and_nudge, get_nudge_history

router = APIRouter()


class PushSubscribeRequest(BaseModel):
    subscription: dict[str, Any]


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


@router.post("/notifications/push-subscribe")
def push_subscribe(payload: PushSubscribeRequest, workspace: dict = Depends(get_workspace_context)):
    tenant_id = workspace["organization"]["id"]
    path = Path("app/storage/notifications/push_subscriptions.jsonl")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"tenant_id": tenant_id, "subscription": payload.subscription, "created_at": datetime.now(timezone.utc).isoformat(), "provenance_verified": False}, ensure_ascii=False, sort_keys=True) + "\n")
    return {"subscribed": True, "mode": "stub", "provenance_verified": False}


@router.post("/notifications/push-test")
def push_test(matter_id: str = "", workspace: dict = Depends(get_workspace_context)):
    tenant_id = workspace["organization"]["id"]
    path = Path("app/storage/notifications/push.log")
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"to": tenant_id, "title": "Gyana Darshan", "body": "Push notification stub", "matter_id": matter_id, "status": "logged_stub", "created_at": datetime.now(timezone.utc).isoformat(), "provenance_verified": False}
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
    return payload


@router.get("/notifications/sync")
def sync(since: str = "", workspace: dict = Depends(get_workspace_context)):
    return {"tenant_id": workspace["organization"]["id"], "since": since, "matters": [], "obligations": [], "provenance_verified": False}
