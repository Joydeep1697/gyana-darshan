from __future__ import annotations

import shutil
import tempfile
import json
import hashlib
from pathlib import Path
from typing import Any

from fastapi import HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from app.database import Database
from app.ingestion.matter_extractor import extract_matter_data
from app.retrieval.matter_indexer import index_tenant, search_tenant
from app.services.timeline_builder import TimelineEvent, build_timeline
from app.storage.vault_writer import save_matter


class Matter(BaseModel):
    id: str
    title: str
    organization_id: str
    case_no: str | None = None
    court: str | None = None
    parties: dict[str, Any] = Field(default_factory=dict)
    next_hearing_date: str | None = None
    obligations: list[dict[str, Any]] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    timeline: list[TimelineEvent] = Field(default_factory=list)
    provenance_verified: bool = False


def _title_from_extracted(extracted: dict[str, Any], fallback: str) -> str:
    case_no = extracted.get("case_no")
    parties = extracted.get("parties") or {}
    plaintiff = parties.get("plaintiff")
    defendant = parties.get("defendant")
    if case_no:
        return str(case_no)
    if plaintiff and defendant:
        return f"{plaintiff} v. {defendant}"[:160]
    return fallback[:160] or "Uploaded matter"


def _matter_payload(db_matter: dict[str, Any], extracted: dict[str, Any]) -> Matter:
    tenant_id = db_matter["organization_id"]
    matter_id = db_matter["id"]
    statuses = _read_statuses(tenant_id, matter_id)
    return Matter(
        id=matter_id,
        title=db_matter.get("title") or "Matter",
        organization_id=tenant_id,
        case_no=extracted.get("case_no"),
        court=extracted.get("court"),
        parties=extracted.get("parties") or {},
        next_hearing_date=extracted.get("next_hearing_date"),
        obligations=_enrich_obligations(extracted.get("obligations") or [], statuses),
        risk_flags=extracted.get("risk_flags") or [],
        timeline=[TimelineEvent(**event) for event in build_timeline(extracted)],
        provenance_verified=False,
    )


def _obligation_id(obligation: dict[str, Any], index: int) -> str:
    payload = json.dumps(obligation, ensure_ascii=False, sort_keys=True)
    digest = hashlib.sha256(f"{index}:{payload}".encode("utf-8")).hexdigest()[:16]
    return f"obl-{digest}"


def _read_statuses(tenant_id: str, matter_id: str) -> dict[str, str]:
    path = Path("app/storage/vault") / tenant_id / "matters" / matter_id / "obligation_status.json"
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return {str(key): str(value) for key, value in data.items()} if isinstance(data, dict) else {}


def _enrich_obligations(obligations: list[dict[str, Any]], statuses: dict[str, str]) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for index, obligation in enumerate(obligations):
        if not isinstance(obligation, dict):
            continue
        item = dict(obligation)
        obligation_id = str(item.get("id") or _obligation_id(item, index))
        item["obligation_id"] = obligation_id
        item["status"] = statuses.get(obligation_id, "pending")
        item["provenance_verified"] = False
        enriched.append(item)
    return enriched


def _read_extracted(tenant_id: str, matter_id: str) -> dict[str, Any]:
    path = Path("app/storage/vault") / tenant_id / "matters" / matter_id / "extracted.json"
    if not path.is_file():
        return {"provenance_verified": False}

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"provenance_verified": False}
    data["provenance_verified"] = False
    return data


async def upload_matter_pdf(db: Database, tenant_id: str, user_id: str, upload: UploadFile) -> Matter:
    filename = Path(upload.filename or "matter.pdf").name
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only PDF uploads are supported")

    with tempfile.NamedTemporaryFile(prefix="matter-upload-", suffix=".pdf", delete=False) as tmp:
        tmp_path = Path(tmp.name)
        shutil.copyfileobj(upload.file, tmp)

    try:
        extracted = extract_matter_data(tmp_path)
        extracted["provenance_verified"] = False
        title = _title_from_extracted(extracted, filename)
        matter = db.create_matter(
            tenant_id,
            title,
            matter_type="litigation",
            status="in_review",
            priority="medium",
            owner_user_id=user_id,
            due_date=extracted.get("next_hearing_date"),
            description=f"Uploaded and deterministically extracted from {filename}",
        )
        document_id = db.create_document(filename, tmp_path.stat().st_size, "", owner_id=user_id, organization_id=tenant_id)
        saved = save_matter(tenant_id, matter["id"], extracted, tmp_path)
        db.update_document(
            document_id,
            status="ready",
            raw_path=saved["source_pdf"],
            sha256=saved["source_hash"],
            file_size=tmp_path.stat().st_size,
        )
        db.link_document_to_matter(tenant_id, matter["id"], document_id)
        index_tenant(tenant_id)
        return _matter_payload(matter, extracted)
    finally:
        tmp_path.unlink(missing_ok=True)


def get_matter(db: Database, tenant_id: str, matter_id: str) -> Matter:
    matter = db.get_matter(matter_id, tenant_id)
    if not matter:
        vault_root = Path("app/storage/vault").resolve()
        for extracted_path in vault_root.glob(f"*/matters/{matter_id}/extracted.json"):
            if extracted_path.parts[-4] != tenant_id:
                raise HTTPException(status_code=403, detail="Cross-tenant access denied")
        raise HTTPException(status_code=404, detail="Matter not found")
    return _matter_payload(matter, _read_extracted(tenant_id, matter_id))


def list_matters(db: Database, tenant_id: str, limit: int = 100) -> list[Matter]:
    return [_matter_payload(item, _read_extracted(tenant_id, item["id"])) for item in db.list_matters(tenant_id, limit=limit)]


def search_matters(tenant_id: str, q: str = "", search_type: str | None = None, before: str | None = None) -> list[dict[str, Any]]:
    return search_tenant(tenant_id, q=q, search_type=search_type, before=before)
