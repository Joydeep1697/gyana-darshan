from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from api.auth.dependencies import get_workspace_context
from app.services.matter_service import search_matters

router = APIRouter()


@router.get("/search")
def search(
    q: str = Query(default=""),
    type: str | None = Query(default=None),
    before: str | None = Query(default=None),
    workspace: dict = Depends(get_workspace_context),
):
    tenant_id = workspace["organization"]["id"]
    return {
        "tenant_id": tenant_id,
        "q": q,
        "type": type,
        "before": before,
        "results": search_matters(tenant_id, q=q, search_type=type, before=before),
        "provenance_verified": False,
    }
