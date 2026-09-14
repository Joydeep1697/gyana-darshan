from __future__ import annotations

from fastapi import APIRouter, Depends

from api.auth.dependencies import get_workspace_context
from app.services.matter_service import get_matter
from app.database import Database, get_db

router = APIRouter()


@router.get("/pwa/manifest")
def manifest(workspace: dict = Depends(get_workspace_context)):
    return {"name": "Gyana Darshan", "short_name": "Gyana", "display": "standalone", "tenant_id": workspace["organization"]["id"]}


@router.get("/pwa/offline-data/{matter_id}")
def offline_data(matter_id: str, db: Database = Depends(get_db), workspace: dict = Depends(get_workspace_context)):
    matter = get_matter(db, workspace["organization"]["id"], matter_id)
    return {"matter": matter.model_dump(), "timeline": [event.model_dump() for event in matter.timeline], "obligations": matter.obligations, "risks": [], "provenance_verified": False}
