from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile

from app.database import Database, get_db
from api.auth.dependencies import get_workspace_context, require_workspace_writer
from app.services.matter_service import Matter, get_matter as get_matter_detail, list_matters as list_matter_details, upload_matter_pdf

router = APIRouter()
VAULT_ROOT = Path("app/storage/vault")


def _extracted(organization_id: str, matter_id: str) -> dict:
    path = (VAULT_ROOT / organization_id / "matters" / matter_id / "extracted.json").resolve()
    if not path.is_relative_to(VAULT_ROOT.resolve()) or not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _matter(db: Database, workspace: dict, matter_id: str) -> tuple[str, dict]:
    organization_id = workspace["organization"]["id"]
    matter = db.get_matter(matter_id, organization_id)
    if not matter:
        raise HTTPException(404, "Matter not found")
    return organization_id, matter


@router.post("/upload", response_model=Matter)
async def upload_matter(
    file: UploadFile = File(...),
    db: Database = Depends(get_db),
    workspace: dict = Depends(require_workspace_writer),
):
    return await upload_matter_pdf(db, workspace["organization"]["id"], workspace["user"]["id"], file)


@router.get("", response_model=list[Matter])
def list_matters(
    limit: int = Query(default=100, ge=1, le=200),
    db: Database = Depends(get_db),
    workspace: dict = Depends(get_workspace_context),
):
    return list_matter_details(db, workspace["organization"]["id"], limit=limit)


@router.get("/{matter_id}", response_model=Matter)
def get_matter(
    matter_id: str,
    db: Database = Depends(get_db),
    workspace: dict = Depends(get_workspace_context),
):
    return get_matter_detail(db, workspace["organization"]["id"], matter_id)


@router.get("/{matter_id}/obligations")
def obligations(matter_id: str, db: Database = Depends(get_db), workspace: dict = Depends(get_workspace_context)):
    organization_id, _ = _matter(db, workspace, matter_id)
    data = _extracted(organization_id, matter_id)
    return {"matter_id": matter_id, "obligations": data.get("obligations", []), "provenance_verified": False}


@router.get("/{matter_id}/deadlines")
def deadlines(matter_id: str, db: Database = Depends(get_db), workspace: dict = Depends(get_workspace_context)):
    organization_id, _ = _matter(db, workspace, matter_id)
    return {"matter_id": matter_id, "deadlines": db.list_matter_deadlines(organization_id, matter_id)}


@router.get("/{matter_id}/parties")
def parties(matter_id: str, db: Database = Depends(get_db), workspace: dict = Depends(get_workspace_context)):
    organization_id, _ = _matter(db, workspace, matter_id)
    data = _extracted(organization_id, matter_id)
    return {"matter_id": matter_id, "parties": data.get("parties", {}), "case_no": data.get("case_no"), "court": data.get("court"), "next_hearing_date": data.get("next_hearing_date"), "risk_flags": data.get("risk_flags", []), "provenance_verified": False}
