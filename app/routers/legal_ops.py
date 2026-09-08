"""Workspace legal operations routes for matters, intake, tasks, contracts, and reports."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import Response

from api.auth.dependencies import get_workspace_context, require_workspace_writer
from app.database import Database, get_db
from app.intelligence.matter_brief import build_matter_brief
from app.intelligence.legal_brief import build_grounded_matter_draft
from app.intelligence.legal_ops_analytics import build_legal_ops_analytics
from app.intelligence.legal_ops_report import build_legal_ops_report
from app.intelligence.legal_ops_notifications import build_legal_ops_calendar_ics, build_legal_ops_notification_digest
from app.exports.legal_memo import matter_draft_docx, matter_draft_markdown
from app.exports.legal_ops_matter import build_matter_export, matter_export_json, matter_export_markdown
from app.models import (
    LegalContractCreate,
    LegalContractObligationCreate,
    LegalContractObligationResponse,
    LegalContractObligationUpdate,
    LegalContractResponse,
    LegalContractUpdate,
    LegalIntakeCreate,
    LegalIntakeConvertRequest,
    LegalIntakeConvertResponse,
    LegalIntakeTaskCreateResponse,
    LegalIntakeResponse,
    LegalIntakeUpdate,
    LegalMatterCreate,
    LegalMatterBriefResponse,
    LegalMatterDeadlineResponse,
    LegalMatterDeadlineTaskCreateResponse,
    LegalOpsAlertResponse,
    LegalOpsAlertNoteCreate,
    LegalOpsAlertNoteCreateResponse,
    LegalOpsAlertResolveResponse,
    LegalOpsAlertTaskCreateResponse,
    LegalMatterDraftListResponse,
    LegalMatterDraftRequest,
    LegalMatterDraftReviewUpdate,
    LegalMatterDraftResponse,
    LegalMatterDetailResponse,
    LegalMatterDocumentLinkCreate,
    LegalMatterResponse,
    LegalMatterNoteCreate,
    LegalMatterNoteResponse,
    LegalMatterUpdate,
    LegalOpsAnalyticsResponse,
    LegalOpsReportResponse,
    LegalOpsNotificationDigestResponse,
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
from database.repository import AuditRepository, OrganizationRepository

router = APIRouter()


def _org_id(workspace: dict) -> str:
    return workspace["organization"]["id"]


def _user_id(workspace: dict) -> str:
    return workspace["user"]["id"]


def _not_found() -> HTTPException:
    return HTTPException(status_code=404, detail="Legal operations record not found")


def _workspace_members(organization_id: str) -> list[dict]:
    return OrganizationRepository.list_members(organization_id)


def _member_map(members: list[dict]) -> dict[str, dict]:
    return {member["id"]: member for member in members if member.get("id")}


def _validate_assignee(organization_id: str, assignee_user_id: str | None) -> None:
    if not assignee_user_id:
        return
    if assignee_user_id not in _member_map(_workspace_members(organization_id)):
        raise ValueError("Assignee is not a member of this workspace")


def _enrich_task(task: dict, members_by_id: dict[str, dict]) -> dict:
    assignee = members_by_id.get(task.get("assignee_user_id") or "")
    return {
        **task,
        "assignee_name": (assignee or {}).get("full_name") or "",
        "assignee_email": (assignee or {}).get("email") or "",
    }


def _enrich_alert(alert: dict, members_by_id: dict[str, dict]) -> dict:
    assignee = members_by_id.get(alert.get("assignee_user_id") or "")
    return {
        **alert,
        "assignee_name": (assignee or {}).get("full_name") or "",
        "assignee_email": (assignee or {}).get("email") or "",
    }


def _enrich_note(note: dict, members_by_id: dict[str, dict]) -> dict:
    author = members_by_id.get(note.get("author_user_id") or "")
    return {
        **note,
        "author_name": (author or {}).get("full_name") or "",
        "author_email": (author or {}).get("email") or "",
    }


def _enrich_activity(activity: dict, members_by_id: dict[str, dict]) -> dict:
    actor = members_by_id.get(activity.get("actor_user_id") or "")
    return {**activity, "actor_name": (actor or {}).get("full_name") or ""}


def _enrich_matter_detail(detail: dict, members: list[dict]) -> dict:
    members_by_id = _member_map(members)
    return {
        **detail,
        "tasks": [_enrich_task(task, members_by_id) for task in detail.get("tasks") or []],
        "notes": [_enrich_note(note, members_by_id) for note in detail.get("notes") or []],
        "activity": [_enrich_activity(item, members_by_id) for item in detail.get("activity") or []],
    }


def _bad_reference(error: ValueError) -> HTTPException:
    return HTTPException(status_code=422, detail=str(error))


@router.get("/workspace", response_model=LegalOpsWorkspaceResponse)
async def get_legal_ops_workspace(
    db: Database = Depends(get_db),
    workspace: dict = Depends(get_workspace_context),
):
    return _workspace_payload(db, _org_id(workspace))


def _workspace_payload(db: Database, organization_id: str) -> dict:
    members = _workspace_members(organization_id)
    members_by_id = _member_map(members)
    return {
        "summary": db.get_legal_ops_summary(organization_id),
        "matters": db.list_matters(organization_id),
        "intakes": db.list_intakes(organization_id),
        "tasks": [_enrich_task(task, members_by_id) for task in db.list_tasks(organization_id)],
        "contracts": db.list_contract_records(organization_id),
        "obligations": db.list_contract_obligations(organization_id),
        "vendors": db.list_vendors(organization_id),
        "spend_entries": db.list_spend_entries(organization_id),
        "playbooks": db.list_playbooks(organization_id),
        "contract_reminders": db.list_contract_reminders(organization_id),
        "matter_deadlines": db.list_workspace_matter_deadlines(organization_id),
        "action_alerts": [_enrich_alert(alert, members_by_id) for alert in db.list_legal_ops_alerts(organization_id)],
        "members": members,
    }


@router.get("/alerts", response_model=list[LegalOpsAlertResponse])
async def list_legal_ops_alerts(
    severity: str | None = None,
    kind: str | None = None,
    assigned_to_me: bool = False,
    limit: int = 100,
    db: Database = Depends(get_db),
    workspace: dict = Depends(get_workspace_context),
):
    organization_id = _org_id(workspace)
    members_by_id = _member_map(_workspace_members(organization_id))
    alerts = db.list_legal_ops_alerts(
        organization_id,
        limit=limit,
        severity=severity,
        kind=kind,
        assigned_user_id=_user_id(workspace) if assigned_to_me else None,
    )
    return [_enrich_alert(alert, members_by_id) for alert in alerts]


@router.post("/alerts/{alert_id}/task", response_model=LegalOpsAlertTaskCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_task_from_legal_ops_alert(
    alert_id: str,
    db: Database = Depends(get_db),
    workspace: dict = Depends(require_workspace_writer),
):
    organization_id = _org_id(workspace)
    members_by_id = _member_map(_workspace_members(organization_id))
    try:
        alert, task = db.create_task_from_alert(organization_id, alert_id, assignee_user_id=_user_id(workspace))
    except ValueError as error:
        raise _bad_reference(error)
    AuditRepository.log_audit("LEGAL_ALERT_TASK_CREATED", user_id=_user_id(workspace), organization_id=organization_id, metadata={"alert_id": alert_id, "task_id": task.get("id"), "source_kind": alert.get("source_kind"), "source_id": alert.get("source_id")})
    return {"alert": _enrich_alert(alert, members_by_id), "task": _enrich_task(task, members_by_id)}


@router.post("/alerts/{alert_id}/note", response_model=LegalOpsAlertNoteCreateResponse, status_code=status.HTTP_201_CREATED)
async def add_note_from_legal_ops_alert(
    alert_id: str,
    payload: LegalOpsAlertNoteCreate,
    db: Database = Depends(get_db),
    workspace: dict = Depends(require_workspace_writer),
):
    organization_id = _org_id(workspace)
    members_by_id = _member_map(_workspace_members(organization_id))
    try:
        alert, note = db.add_note_from_alert(organization_id, alert_id, _user_id(workspace), body=payload.body)
    except ValueError as error:
        raise _bad_reference(error)
    AuditRepository.log_audit("LEGAL_ALERT_NOTE_CREATED", user_id=_user_id(workspace), organization_id=organization_id, metadata={"alert_id": alert_id, "note_id": note.get("id"), "source_kind": alert.get("source_kind"), "source_id": alert.get("source_id")})
    return {"alert": _enrich_alert(alert, members_by_id), "note": _enrich_note(note, members_by_id)}


@router.post("/alerts/{alert_id}/resolve", response_model=LegalOpsAlertResolveResponse)
async def resolve_legal_ops_alert(
    alert_id: str,
    db: Database = Depends(get_db),
    workspace: dict = Depends(require_workspace_writer),
):
    organization_id = _org_id(workspace)
    members_by_id = _member_map(_workspace_members(organization_id))
    try:
        result = db.resolve_legal_ops_alert(organization_id, alert_id)
    except ValueError as error:
        raise _bad_reference(error)
    if result.get("task"):
        result["task"] = _enrich_task(result["task"], members_by_id)
    AuditRepository.log_audit("LEGAL_ALERT_RESOLVED", user_id=_user_id(workspace), organization_id=organization_id, metadata={"alert_id": alert_id, "source_kind": result.get("source_kind"), "source_id": result.get("source_id")})
    return result


@router.get("/report", response_model=LegalOpsReportResponse)
async def get_legal_ops_report(
    db: Database = Depends(get_db),
    workspace: dict = Depends(get_workspace_context),
):
    return build_legal_ops_report(_workspace_payload(db, _org_id(workspace)))


@router.get("/analytics", response_model=LegalOpsAnalyticsResponse)
async def get_legal_ops_analytics(
    db: Database = Depends(get_db),
    workspace: dict = Depends(get_workspace_context),
):
    return build_legal_ops_analytics(_workspace_payload(db, _org_id(workspace)))


@router.get("/notifications/digest", response_model=LegalOpsNotificationDigestResponse)
async def get_legal_ops_notification_digest(
    db: Database = Depends(get_db),
    workspace: dict = Depends(get_workspace_context),
):
    return build_legal_ops_notification_digest(_workspace_payload(db, _org_id(workspace)))


@router.get("/deadlines/calendar.ics")
async def export_legal_ops_deadline_calendar(
    db: Database = Depends(get_db),
    workspace: dict = Depends(get_workspace_context),
):
    return Response(
        content=build_legal_ops_calendar_ics(_workspace_payload(db, _org_id(workspace))),
        media_type="text/calendar",
        headers={"Content-Disposition": 'attachment; filename="nyaya-legal-ops-calendar.ics"'},
    )


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


@router.get("/deadlines", response_model=list[LegalMatterDeadlineResponse])
async def list_legal_ops_deadlines(
    status_filter: str | None = Query(default=None, alias="status"),
    kind: str | None = None,
    matter_id: str | None = None,
    window: str | None = None,
    limit: int = 200,
    db: Database = Depends(get_db),
    workspace: dict = Depends(get_workspace_context),
):
    return db.list_workspace_matter_deadlines(_org_id(workspace), limit=limit, status=status_filter, kind=kind, matter_id=matter_id, window=window)


@router.post("/deadlines/{kind}/{source_id}/clear", response_model=LegalMatterDeadlineResponse)
async def clear_legal_ops_deadline(
    kind: str,
    source_id: str,
    db: Database = Depends(get_db),
    workspace: dict = Depends(require_workspace_writer),
):
    organization_id = _org_id(workspace)
    try:
        deadline = db.clear_matter_deadline(organization_id, kind, source_id)
    except ValueError as error:
        raise _bad_reference(error)
    if not deadline:
        raise _not_found()
    AuditRepository.log_audit("LEGAL_DEADLINE_CLEARED", user_id=_user_id(workspace), organization_id=organization_id, metadata={"kind": kind, "source_id": source_id})
    return deadline


@router.post("/deadlines/{kind}/{source_id}/task", response_model=LegalMatterDeadlineTaskCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_task_from_legal_ops_deadline(
    kind: str,
    source_id: str,
    db: Database = Depends(get_db),
    workspace: dict = Depends(require_workspace_writer),
):
    organization_id = _org_id(workspace)
    try:
        task = db.create_task_from_deadline(organization_id, kind, source_id, assignee_user_id=_user_id(workspace))
    except ValueError as error:
        raise _bad_reference(error)
    if not task:
        raise _not_found()
    deadline = db.find_matter_deadline(organization_id, kind, source_id)
    if not deadline:
        raise _not_found()
    AuditRepository.log_audit("LEGAL_DEADLINE_TASK_CREATED", user_id=_user_id(workspace), organization_id=organization_id, metadata={"kind": kind, "source_id": source_id, "task_id": task["id"]})
    return {"deadline": deadline, "task": _enrich_task(task, _member_map(_workspace_members(organization_id)))}


@router.get("/matters/{matter_id}", response_model=LegalMatterDetailResponse)
async def get_matter_detail(
    matter_id: str,
    db: Database = Depends(get_db),
    workspace: dict = Depends(get_workspace_context),
):
    detail = db.get_matter_detail(_org_id(workspace), matter_id)
    if not detail:
        raise _not_found()
    return _enrich_matter_detail(detail, _workspace_members(_org_id(workspace)))


@router.get("/matters/{matter_id}/export")
async def export_matter_record(
    matter_id: str,
    format: str = Query(default="json", pattern="^(json|markdown)$"),
    db: Database = Depends(get_db),
    workspace: dict = Depends(get_workspace_context),
):
    organization_id = _org_id(workspace)
    detail = db.get_matter_detail(organization_id, matter_id)
    if not detail:
        raise _not_found()
    document_ids = [item.get("id") for item in detail.get("documents") or [] if item.get("id")]
    precedents = db.get_case_law_records_for_documents(organization_id, document_ids)
    payload = build_matter_export({**detail, "organization_id": organization_id}, precedents, exported_by=_user_id(workspace))
    AuditRepository.log_audit("LEGAL_MATTER_EXPORTED", user_id=_user_id(workspace), organization_id=organization_id, metadata={"matter_id": matter_id, "format": format})
    if format == "markdown":
        return Response(content=matter_export_markdown(payload), media_type="text/markdown", headers={"Content-Disposition": 'attachment; filename="nyaya-matter-export.md"'})
    return Response(content=matter_export_json(payload), media_type="application/json", headers={"Content-Disposition": 'attachment; filename="nyaya-matter-export.json"'})


@router.get("/matters/{matter_id}/deadlines", response_model=list[LegalMatterDeadlineResponse])
async def get_matter_deadlines(
    matter_id: str,
    db: Database = Depends(get_db),
    workspace: dict = Depends(get_workspace_context),
):
    organization_id = _org_id(workspace)
    if not db.get_matter(matter_id, organization_id):
        raise _not_found()
    return db.list_matter_deadlines(organization_id, matter_id)


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


@router.post("/matters/{matter_id}/draft", response_model=LegalMatterDraftResponse)
async def generate_grounded_matter_draft(
    matter_id: str,
    payload: LegalMatterDraftRequest | None = None,
    db: Database = Depends(get_db),
    workspace: dict = Depends(require_workspace_writer),
):
    """Assemble a source-labeled draft from matter facts, statutes, and selected precedents."""
    organization_id = _org_id(workspace)
    detail = db.get_matter_detail(organization_id, matter_id)
    if not detail:
        raise _not_found()
    request = payload or LegalMatterDraftRequest()
    precedents = db.get_case_law_records_by_ids(organization_id, request.precedent_ids)
    draft = build_grounded_matter_draft(detail, question=request.prompt, precedent_records=precedents)
    saved = db.save_matter_draft(organization_id, matter_id, _user_id(workspace), draft)
    AuditRepository.log_audit("LEGAL_MATTER_DRAFT_GENERATED", user_id=_user_id(workspace), organization_id=organization_id, metadata={"matter_id": matter_id, "draft_id": saved.get("id"), "precedent_count": len(precedents)})
    return saved


@router.get("/matters/{matter_id}/drafts", response_model=LegalMatterDraftListResponse)
async def list_grounded_matter_drafts(
    matter_id: str,
    db: Database = Depends(get_db),
    workspace: dict = Depends(get_workspace_context),
):
    organization_id = _org_id(workspace)
    if not db.get_matter(organization_id=organization_id, matter_id=matter_id):
        raise _not_found()
    drafts = db.list_matter_drafts(organization_id, matter_id)
    return {"drafts": drafts, "total": len(drafts)}


@router.get("/matters/{matter_id}/drafts/{draft_id}", response_model=LegalMatterDraftResponse)
async def get_grounded_matter_draft(
    matter_id: str,
    draft_id: str,
    db: Database = Depends(get_db),
    workspace: dict = Depends(get_workspace_context),
):
    draft = db.get_matter_draft(_org_id(workspace), matter_id, draft_id)
    if not draft:
        raise _not_found()
    return draft


@router.patch("/matters/{matter_id}/drafts/{draft_id}", response_model=LegalMatterDraftResponse)
async def update_grounded_matter_draft_review(
    matter_id: str,
    draft_id: str,
    payload: LegalMatterDraftReviewUpdate,
    db: Database = Depends(get_db),
    workspace: dict = Depends(require_workspace_writer),
):
    organization_id = _org_id(workspace)
    draft = db.update_matter_draft_review(
        organization_id,
        matter_id,
        draft_id,
        _user_id(workspace),
        payload.review_status,
        payload.reviewer_note,
    )
    if not draft:
        raise _not_found()
    AuditRepository.log_audit("LEGAL_MATTER_DRAFT_REVIEW_UPDATED", user_id=_user_id(workspace), organization_id=organization_id, metadata={"matter_id": matter_id, "draft_id": draft_id, "review_status": draft["review_status"]})
    return draft


@router.post("/matters/{matter_id}/draft/export")
async def export_grounded_matter_draft(
    matter_id: str,
    payload: LegalMatterDraftRequest | None = None,
    draft_id: str | None = None,
    format: str = Query(default="markdown", pattern="^(markdown|docx)$"),
    db: Database = Depends(get_db),
    workspace: dict = Depends(get_workspace_context),
):
    organization_id = _org_id(workspace)
    detail = db.get_matter_detail(organization_id, matter_id)
    if not detail:
        raise _not_found()
    if draft_id:
        draft = db.get_matter_draft(organization_id, matter_id, draft_id)
        if not draft:
            raise _not_found()
    else:
        request = payload or LegalMatterDraftRequest()
        precedents = db.get_case_law_records_by_ids(organization_id, request.precedent_ids)
        draft = build_grounded_matter_draft(detail, question=request.prompt, precedent_records=precedents)
    if format == "docx":
        return Response(
            content=matter_draft_docx(draft),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": 'attachment; filename="nyaya-grounded-draft.docx"'},
        )
    return Response(
        content=matter_draft_markdown(draft),
        media_type="text/markdown",
        headers={"Content-Disposition": 'attachment; filename="nyaya-grounded-draft.md"'},
    )


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
        note = db.add_matter_note(organization_id, matter_id, _user_id(workspace), payload.body, link_kind=payload.link_kind, link_source_id=payload.link_source_id)
    except ValueError as error:
        raise _bad_reference(error)
    AuditRepository.log_audit("LEGAL_MATTER_NOTE_CREATED", user_id=_user_id(workspace), organization_id=organization_id, metadata={"matter_id": matter_id, "note_id": note["id"], "link_kind": note.get("link_kind"), "link_source_id": note.get("link_source_id")})
    return _enrich_note(note, _member_map(_workspace_members(organization_id)))


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


@router.post("/intake/{intake_id}/task", response_model=LegalIntakeTaskCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_task_from_intake(
    intake_id: str,
    db: Database = Depends(get_db),
    workspace: dict = Depends(require_workspace_writer),
):
    organization_id = _org_id(workspace)
    try:
        intake, task = db.create_task_from_intake(organization_id, intake_id, assignee_user_id=_user_id(workspace))
    except ValueError as error:
        raise _bad_reference(error)
    AuditRepository.log_audit("LEGAL_INTAKE_TASK_CREATED", user_id=_user_id(workspace), organization_id=organization_id, metadata={"intake_id": intake_id, "task_id": task.get("id")})
    return {"intake": intake, "task": _enrich_task(task, _member_map(_workspace_members(organization_id)))}


@router.post("/tasks", response_model=LegalTaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    payload: LegalTaskCreate,
    db: Database = Depends(get_db),
    workspace: dict = Depends(require_workspace_writer),
):
    organization_id = _org_id(workspace)
    task_payload = payload.model_dump(exclude={"title"})
    task_payload["assignee_user_id"] = task_payload.get("assignee_user_id") or _user_id(workspace)
    try:
        _validate_assignee(organization_id, task_payload.get("assignee_user_id"))
        task = db.create_task(organization_id, payload.title, **task_payload)
    except ValueError as error:
        raise _bad_reference(error)
    AuditRepository.log_audit("LEGAL_TASK_CREATED", user_id=_user_id(workspace), organization_id=organization_id, metadata={"task_id": task["id"], "title": task["title"]})
    return _enrich_task(task, _member_map(_workspace_members(organization_id)))


@router.patch("/tasks/{task_id}", response_model=LegalTaskResponse)
async def update_task(
    task_id: str,
    payload: LegalTaskUpdate,
    db: Database = Depends(get_db),
    workspace: dict = Depends(require_workspace_writer),
):
    organization_id = _org_id(workspace)
    task_payload = payload.model_dump(exclude_unset=True)
    try:
        _validate_assignee(organization_id, task_payload.get("assignee_user_id"))
        task = db.update_task(task_id, organization_id, **task_payload)
    except ValueError as error:
        raise _bad_reference(error)
    if not task:
        raise _not_found()
    AuditRepository.log_audit("LEGAL_TASK_UPDATED", user_id=_user_id(workspace), organization_id=organization_id, metadata={"task_id": task_id})
    return _enrich_task(task, _member_map(_workspace_members(organization_id)))


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
    _validate_assignee(organization_id, payload.signature_owner_user_id)
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
    _validate_assignee(organization_id, payload.signature_owner_user_id)
    try:
        contract = db.update_contract_record(contract_id, organization_id, **payload.model_dump(exclude_unset=True))
    except ValueError as error:
        raise _bad_reference(error)
    if not contract:
        raise _not_found()
    AuditRepository.log_audit("LEGAL_CONTRACT_UPDATED", user_id=_user_id(workspace), organization_id=organization_id, metadata={"contract_id": contract_id})
    return contract


@router.post("/obligations", response_model=LegalContractObligationResponse, status_code=status.HTTP_201_CREATED)
async def create_contract_obligation(
    payload: LegalContractObligationCreate,
    db: Database = Depends(get_db),
    workspace: dict = Depends(require_workspace_writer),
):
    organization_id = _org_id(workspace)
    try:
        obligation = db.create_contract_obligation(organization_id, payload.contract_id, payload.title, **payload.model_dump(exclude={"contract_id", "title"}))
    except ValueError as error:
        raise _bad_reference(error)
    AuditRepository.log_audit(
        "LEGAL_CONTRACT_OBLIGATION_CREATED",
        user_id=_user_id(workspace),
        organization_id=organization_id,
        metadata={"obligation_id": obligation["id"], "contract_id": obligation["contract_id"], "matter_id": obligation.get("matter_id")},
    )
    return obligation


@router.patch("/obligations/{obligation_id}", response_model=LegalContractObligationResponse)
async def update_contract_obligation(
    obligation_id: str,
    payload: LegalContractObligationUpdate,
    db: Database = Depends(get_db),
    workspace: dict = Depends(require_workspace_writer),
):
    organization_id = _org_id(workspace)
    try:
        obligation = db.update_contract_obligation(obligation_id, organization_id, **payload.model_dump(exclude_unset=True))
    except ValueError as error:
        raise _bad_reference(error)
    if not obligation:
        raise _not_found()
    AuditRepository.log_audit(
        "LEGAL_CONTRACT_OBLIGATION_UPDATED",
        user_id=_user_id(workspace),
        organization_id=organization_id,
        metadata={"obligation_id": obligation_id, "status": obligation.get("status")},
    )
    return obligation
