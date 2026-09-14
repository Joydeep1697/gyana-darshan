from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from api.auth.dependencies import get_workspace_context
from app.services.calendar_service import build_ics, get_calendar_events

router = APIRouter()


@router.get("/calendar/events")
def calendar_events(
    from_: str = Query(..., alias="from"),
    to: str = Query(...),
    workspace: dict = Depends(get_workspace_context),
):
    tenant_id = workspace["organization"]["id"]
    try:
        date.fromisoformat(from_)
        date.fromisoformat(to)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="from and to must be ISO dates") from exc
    return {"tenant_id": tenant_id, "events": get_calendar_events(tenant_id, from_, to), "provenance_verified": False}


@router.get("/calendar/ics")
def calendar_ics(workspace: dict = Depends(get_workspace_context)):
    tenant_id = workspace["organization"]["id"]
    return Response(
        content=build_ics(tenant_id),
        media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="nyaya-matters.ics"'},
    )
