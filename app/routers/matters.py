from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from app.database import Database, get_db
from api.auth.dependencies import get_workspace_context

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
