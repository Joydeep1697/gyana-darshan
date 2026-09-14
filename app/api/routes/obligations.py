from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from api.auth.dependencies import get_workspace_context, require_workspace_writer
from app.services.obligation_tracker import (
    get_overdue_obligations,
    get_upcoming_obligations,
    mark_obligation_status,
)

router = APIRouter()


class ObligationStatusUpdate(BaseModel):
    status: Literal["pending", "done", "dismissed"]


@router.get("/obligations/upcoming")
def upcoming_obligations(days: int = Query(default=7, ge=0, le=365), workspace: dict = Depends(get_workspace_context)):
    tenant_id = workspace["organization"]["id"]
    return {"tenant_id": tenant_id, "obligations": get_upcoming_obligations(tenant_id, days=days), "provenance_verified": False}


@router.get("/obligations/overdue")
def overdue_obligations(workspace: dict = Depends(get_workspace_context)):
    tenant_id = workspace["organization"]["id"]
    return {"tenant_id": tenant_id, "obligations": get_overdue_obligations(tenant_id), "provenance_verified": False}


@router.post("/obligations/{matter_id}/{obligation_id}/status")
def update_obligation_status(
    matter_id: str,
    obligation_id: str,
    payload: ObligationStatusUpdate,
    workspace: dict = Depends(require_workspace_writer),
):
    tenant_id = workspace["organization"]["id"]
    try:
        return mark_obligation_status(tenant_id, matter_id, obligation_id, payload.status)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Matter extraction not found") from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Obligation not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
