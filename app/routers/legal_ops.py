"""Workspace legal operations routes for matters, intake, tasks, contracts, and reports."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from api.auth.dependencies import get_workspace_context, require_workspace_writer
from app.database import Database, get_db
from app.intelligence.matter_brief import build_matter_brief
from app.models import (
    LegalContractCreate,
    LegalContractResponse,
    LegalContractUpdate,
    LegalIntakeCreate,
    LegalIntakeConvertRequest,
    LegalIntakeConvertResponse,
    LegalIntakeResponse,
    LegalIntakeUpdate,
    LegalMatterCreate,
    LegalMatterBriefResponse,
    LegalMatterDetailResponse,
    LegalMatterDocumentLinkCreate,
    LegalMatterResponse,
    LegalMatterNoteCreate,
    LegalMatterNoteResponse,
    LegalMatterUpdate,
    LegalOpsSearchResponse,
    LegalPlaybookCreate,
    LegalPlaybookResponse,
    LegalPlaybookUpdate,
    LegalSpendCreate,
    LegalSpendResponse,
    LegalSpendUpdate,
    LegalVendorCreate,
    LegalVendorResponse,
    LegalVendorUpdate,
    LegalOpsWorkspaceResponse,
    LegalTaskCreate,
    LegalTaskResponse,
    LegalTaskUpdate,
)
from database.repository import AuditRepository

router = APIRouter()


def _org_id(workspace: dict) -> str:
    return workspace["organization"]["id"]


def _user_id(workspace: dict) -> str:
    return workspace["user"]["id"]


def _not_found() -> HTTPException:
    return HTTPException(status_code=404, detail="Legal operations record not found")


def _bad_reference(error: ValueError) -> HTTPException:
    return HTTPException(status_code=422, detail=str(error))


@router.get("/workspace", response_model=LegalOpsWorkspaceResponse)
async def get_legal_ops_workspace(
    db: Database = Depends(get_db),
    workspace: dict = Depends(get_workspace_context),
):
    organization_id = _org_id(workspace)
    return {
        "summary": db.get_legal_ops_summary(organization_id),
        "matters": db.list_matters(organization_id),
        "intakes": db.list_intakes(organization_id),
        "tasks": db.list_tasks(organization_id),
        "contracts": db.list_contract_records(organization_id),
        "vendors": db.list_vendors(organization_id),
        "spend_entries": db.list_spend_entries(organization_id),
        "playbooks": db.list_playbooks(organization_id),
        "contract_reminders": db.list_contract_reminders(organization_id),
    }




@router.get("/search", response_model=LegalOpsSearchResponse)
async def search_legal_ops(
    q: str,
    limit: int = 30,
    db: Database = Depends(get_db),
    workspace: dict = Depends(get_workspace_context),
):
    query = q.strip()
    if len(query) < 2:
        raise HTTPException(status_code=422, detail="Search query must be at least 2 characters")
    return {"results": db.search_legal_ops(_org_id(workspace), query, limit=limit)}


@router.get("/matters/{matter_id}", response_model=LegalMatterDetailResponse)
async def get_matter_detail(
    matter_id: str,
    db: Database = Depends(get_db),
    workspace: dict = Depends(get_workspace_context),
):
    detail = db.get_matter_detail(_org_id(workspace), matter_id)
    if not detail:
        raise _not_found()
    return detail


@router.post("/matters/{matter_id}/brief", response_model=LegalMatterBriefResponse)
async def generate_matter_brief(
    matter_id: str,
    db: Database = Depends(get_db),
    workspace: dict = Depends(get_workspace_context),
):
    organization_id = _org_id(workspace)
    detail = db.get_matter_detail(organization_id, matter_id)
    if not detail:
        raise _not_found()
    return build_matter_brief(detail)


@router.post("/matters/{matter_id}/documents", status_code=status.HTTP_201_CREATED)
async def link_matter_document(
    matter_id: str,
    payload: LegalMatterDocumentLinkCreate,
    db: Database = Depends(get_db),
    workspace: dict = Depends(require_workspace_writer),
):
    organization_id = _org_id(workspace)
    try:
        link = db.link_document_to_matter(organization_id, matter_id, payload.document_id)
    except ValueError as error:
        raise _bad_reference(error)
    AuditRepository.log_audit("LEGAL_MATTER_DOCUMENT_LINKED", user_id=_user_id(workspace), organization_id=organization_id, metadata={"matter_id": matter_id, "document_id": payload.document_id})
    return link


@router.post("/matters/{matter_id}/notes", response_model=LegalMatterNoteResponse, status_code=status.HTTP_201_CREATED)
async def add_matter_note(
    matter_id: str,
    payload: LegalMatterNoteCreate,
    db: Database = Depends(get_db),
    workspace: dict = Depends(require_workspace_writer),
):
    organization_id = _org_id(workspace)
    try:
        note = db.add_matter_note(organization_id, matter_id, _user_id(workspace), payload.body)
    except ValueError as error:
        raise _bad_reference(error)
    AuditRepository.log_audit("LEGAL_MATTER_NOTE_CREATED", user_id=_user_id(workspace), organization_id=organization_id, metadata={"matter_id": matter_id, "note_id": note["id"]})
    return note


@router.post("/matters", response_model=LegalMatterResponse, status_code=status.HTTP_201_CREATED)
async def create_matter(
    payload: LegalMatterCreate,
    db: Database = Depends(get_db),
    workspace: dict = Depends(require_workspace_writer),
):
    organization_id = _org_id(workspace)
    matter = db.create_matter(organization_id, payload.title, **payload.model_dump(exclude={"title"}), owner_user_id=_user_id(workspace))
    AuditRepository.log_audit(
        "LEGAL_MATTER_CREATED",
        user_id=_user_id(workspace),
        organization_id=organization_id,
        metadata={"matter_id": matter["id"], "title": matter["title"]},
    )
    return matter


@router.patch("/matters/{matter_id}", response_model=LegalMatterResponse)
async def update_matter(
    matter_id: str,
    payload: LegalMatterUpdate,
    db: Database = Depends(get_db),
    workspace: dict = Depends(require_workspace_writer),
):
    organization_id = _org_id(workspace)
    matter = db.update_matter(matter_id, organization_id, **payload.model_dump(exclude_unset=True))
    if not matter:
        raise _not_found()
    AuditRepository.log_audit("LEGAL_MATTER_UPDATED", user_id=_user_id(workspace), organization_id=organization_id, metadata={"matter_id": matter_id})
    return matter


@router.post("/intake", response_model=LegalIntakeResponse, status_code=status.HTTP_201_CREATED)
async def create_intake(
    payload: LegalIntakeCreate,
    db: Database = Depends(get_db),
    workspace: dict = Depends(require_workspace_writer),
):
    organization_id = _org_id(workspace)
    try:
        intake = db.create_intake(organization_id, _user_id(workspace), payload.title, **payload.model_dump(exclude={"title"}))
    except ValueError as error:
        raise _bad_reference(error)
    AuditRepository.log_audit(
        "LEGAL_INTAKE_CREATED",
        user_id=_user_id(workspace),
        organization_id=organization_id,
        metadata={"intake_id": intake["id"], "title": intake["title"]},
    )
    return intake


@router.patch("/intake/{intake_id}", response_model=LegalIntakeResponse)
async def update_intake(
    intake_id: str,
    payload: LegalIntakeUpdate,
    db: Database = Depends(get_db),
    workspace: dict = Depends(require_workspace_writer),
):
    organization_id = _org_id(workspace)
    try:
        intake = db.update_intake(intake_id, organization_id, **payload.model_dump(exclude_unset=True))
    except ValueError as error:
        raise _bad_reference(error)
    if not intake:
        raise _not_found()
    AuditRepository.log_audit("LEGAL_INTAKE_UPDATED", user_id=_user_id(workspace), organization_id=organization_id, metadata={"intake_id": intake_id})
    return intake


@router.post("/intake/{intake_id}/convert", response_model=LegalIntakeConvertResponse)
async def convert_intake_to_matter(
    intake_id: str,
    payload: LegalIntakeConvertRequest,
    db: Database = Depends(get_db),
    workspace: dict = Depends(require_workspace_writer),
):
    organization_id = _org_id(workspace)
    converted = db.convert_intake_to_matter(intake_id, organization_id, _user_id(workspace), **payload.model_dump(exclude_unset=True))
    if not converted:
        raise _not_found()
    AuditRepository.log_audit(
        "LEGAL_INTAKE_CONVERTED_TO_MATTER",
        user_id=_user_id(workspace),
        organization_id=organization_id,
        metadata={"intake_id": intake_id, "matter_id": converted["matter"]["id"]},
    )
    return converted


@router.post("/tasks", response_model=LegalTaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    payload: LegalTaskCreate,
    db: Database = Depends(get_db),
    workspace: dict = Depends(require_workspace_writer),
):
    organization_id = _org_id(workspace)
    try:
        task = db.create_task(organization_id, payload.title, **payload.model_dump(exclude={"title"}), assignee_user_id=_user_id(workspace))
    except ValueError as error:
        raise _bad_reference(error)
    AuditRepository.log_audit("LEGAL_TASK_CREATED", user_id=_user_id(workspace), organization_id=organization_id, metadata={"task_id": task["id"], "title": task["title"]})
    return task


@router.patch("/tasks/{task_id}", response_model=LegalTaskResponse)
async def update_task(
    task_id: str,
    payload: LegalTaskUpdate,
    db: Database = Depends(get_db),
    workspace: dict = Depends(require_workspace_writer),
):
    organization_id = _org_id(workspace)
    try:
        task = db.update_task(task_id, organization_id, **payload.model_dump(exclude_unset=True))
    except ValueError as error:
        raise _bad_reference(error)
    if not task:
        raise _not_found()
    AuditRepository.log_audit("LEGAL_TASK_UPDATED", user_id=_user_id(workspace), organization_id=organization_id, metadata={"task_id": task_id})
    return task


@router.post("/playbooks", response_model=LegalPlaybookResponse, status_code=status.HTTP_201_CREATED)
async def create_playbook(
    payload: LegalPlaybookCreate,
    db: Database = Depends(get_db),
    workspace: dict = Depends(require_workspace_writer),
):
    organization_id = _org_id(workspace)
    playbook = db.create_playbook(organization_id, payload.title, **payload.model_dump(exclude={"title"}))
    AuditRepository.log_audit("LEGAL_PLAYBOOK_CREATED", user_id=_user_id(workspace), organization_id=organization_id, metadata={"playbook_id": playbook["id"], "title": playbook["title"]})
    return playbook


@router.patch("/playbooks/{playbook_id}", response_model=LegalPlaybookResponse)
async def update_playbook(
    playbook_id: str,
    payload: LegalPlaybookUpdate,
    db: Database = Depends(get_db),
    workspace: dict = Depends(require_workspace_writer),
):
    organization_id = _org_id(workspace)
    playbook = db.update_playbook(playbook_id, organization_id, **payload.model_dump(exclude_unset=True))
    if not playbook:
        raise _not_found()
    AuditRepository.log_audit("LEGAL_PLAYBOOK_UPDATED", user_id=_user_id(workspace), organization_id=organization_id, metadata={"playbook_id": playbook_id, "status": playbook.get("status")})
    return playbook


@router.post("/vendors", response_model=LegalVendorResponse, status_code=status.HTTP_201_CREATED)
async def create_vendor(
    payload: LegalVendorCreate,
    db: Database = Depends(get_db),
    workspace: dict = Depends(require_workspace_writer),
):
    organization_id = _org_id(workspace)
    vendor = db.create_vendor(organization_id, payload.name, **payload.model_dump(exclude={"name"}))
    AuditRepository.log_audit("LEGAL_VENDOR_CREATED", user_id=_user_id(workspace), organization_id=organization_id, metadata={"vendor_id": vendor["id"], "name": vendor["name"]})
    return vendor


@router.patch("/vendors/{vendor_id}", response_model=LegalVendorResponse)
async def update_vendor(
    vendor_id: str,
    payload: LegalVendorUpdate,
    db: Database = Depends(get_db),
    workspace: dict = Depends(require_workspace_writer),
):
    organization_id = _org_id(workspace)
    vendor = db.update_vendor(vendor_id, organization_id, **payload.model_dump(exclude_unset=True))
    if not vendor:
        raise _not_found()
    AuditRepository.log_audit("LEGAL_VENDOR_UPDATED", user_id=_user_id(workspace), organization_id=organization_id, metadata={"vendor_id": vendor_id})
    return vendor


@router.post("/spend", response_model=LegalSpendResponse, status_code=status.HTTP_201_CREATED)
async def create_spend_entry(
    payload: LegalSpendCreate,
    db: Database = Depends(get_db),
    workspace: dict = Depends(require_workspace_writer),
):
    organization_id = _org_id(workspace)
    try:
        spend = db.create_spend_entry(organization_id, payload.amount, **payload.model_dump(exclude={"amount"}))
    except ValueError as error:
        raise _bad_reference(error)
    AuditRepository.log_audit("LEGAL_SPEND_CREATED", user_id=_user_id(workspace), organization_id=organization_id, metadata={"spend_id": spend["id"], "matter_id": spend.get("matter_id"), "vendor_id": spend.get("vendor_id")})
    return spend


@router.patch("/spend/{spend_id}", response_model=LegalSpendResponse)
async def update_spend_entry(
    spend_id: str,
    payload: LegalSpendUpdate,
    db: Database = Depends(get_db),
    workspace: dict = Depends(require_workspace_writer),
):
    organization_id = _org_id(workspace)
    try:
        spend = db.update_spend_entry(spend_id, organization_id, **payload.model_dump(exclude_unset=True))
    except ValueError as error:
        raise _bad_reference(error)
    if not spend:
        raise _not_found()
    AuditRepository.log_audit("LEGAL_SPEND_UPDATED", user_id=_user_id(workspace), organization_id=organization_id, metadata={"spend_id": spend_id, "status": spend.get("status")})
    return spend


@router.post("/contracts", response_model=LegalContractResponse, status_code=status.HTTP_201_CREATED)
async def create_contract(
    payload: LegalContractCreate,
    db: Database = Depends(get_db),
    workspace: dict = Depends(require_workspace_writer),
):
    organization_id = _org_id(workspace)
    try:
        contract = db.create_contract_record(organization_id, payload.title, **payload.model_dump(exclude={"title"}))
    except ValueError as error:
        raise _bad_reference(error)
    AuditRepository.log_audit("LEGAL_CONTRACT_CREATED", user_id=_user_id(workspace), organization_id=organization_id, metadata={"contract_id": contract["id"], "title": contract["title"]})
    return contract


@router.patch("/contracts/{contract_id}", response_model=LegalContractResponse)
async def update_contract(
    contract_id: str,
    payload: LegalContractUpdate,
    db: Database = Depends(get_db),
    workspace: dict = Depends(require_workspace_writer),
):
    organization_id = _org_id(workspace)
    try:
        contract = db.update_contract_record(contract_id, organization_id, **payload.model_dump(exclude_unset=True))
    except ValueError as error:
        raise _bad_reference(error)
    if not contract:
        raise _not_found()
    AuditRepository.log_audit("LEGAL_CONTRACT_UPDATED", user_id=_user_id(workspace), organization_id=organization_id, metadata={"contract_id": contract_id})
    return contract
