import sqlite3
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status

from api.auth.dependencies import get_current_user
from api.organizations.schemas import (
    MemberRequest,
    MemberRoleRequest,
    OrganizationCreateRequest,
    RetentionPolicyRequest,
)
from app.exports.audit_events import audit_export_csv, audit_export_json, audit_export_markdown, build_audit_export
from database.repository import AuditRepository, OrganizationRepository, UserRepository

router = APIRouter(prefix="/api/organizations", tags=["Organization Workspaces"])


def _organization_for_admin(organization_id: str, user: Dict[str, Any]) -> Dict[str, Any]:
    organization = OrganizationRepository.get_for_member(organization_id, user["id"])
    if not organization:
        raise HTTPException(404, "Workspace not found")
    if organization["membership_role"] not in {"OWNER", "ADMIN"}:
        raise HTTPException(403, "Workspace administrator privileges required")
    return organization


@router.get("")
async def list_organizations(user: Dict[str, Any] = Depends(get_current_user)):
    return {"organizations": OrganizationRepository.list_for_user(user["id"])}


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_organization(
    payload: OrganizationCreateRequest,
    request: Request,
    user: Dict[str, Any] = Depends(get_current_user),
):
    try:
        organization = OrganizationRepository.create(payload.name, payload.slug, user["id"])
    except sqlite3.IntegrityError as exc:
        raise HTTPException(409, "That workspace slug is already in use") from exc
    AuditRepository.log_audit(
        "ORGANIZATION_CREATED",
        user_id=user["id"],
        client_ip=request.client.host if request.client else None,
        organization_id=organization["id"],
        metadata={"name": organization["name"]},
    )
    return organization


@router.get("/{organization_id}/members")
async def list_members(
    organization_id: str,
    user: Dict[str, Any] = Depends(get_current_user),
):
    if not OrganizationRepository.get_for_member(organization_id, user["id"]):
        raise HTTPException(404, "Workspace not found")
    return {"members": OrganizationRepository.list_members(organization_id)}


@router.post("/{organization_id}/members", status_code=status.HTTP_201_CREATED)
async def add_member(
    organization_id: str,
    payload: MemberRequest,
    request: Request,
    user: Dict[str, Any] = Depends(get_current_user),
):
    organization = _organization_for_admin(organization_id, user)
    if organization["is_personal"]:
        raise HTTPException(409, "Members cannot be added to a private workspace")
    member = UserRepository.get_by_email(payload.email)
    if not member:
        raise HTTPException(404, "No account exists for that email address")
    OrganizationRepository.upsert_member(organization_id, member["id"], payload.role)
    AuditRepository.log_audit(
        "ORGANIZATION_MEMBER_ADDED",
        user_id=user["id"],
        client_ip=request.client.host if request.client else None,
        organization_id=organization_id,
        metadata={"member_id": member["id"], "role": payload.role},
    )
    return {"member_id": member["id"], "role": payload.role}


@router.patch("/{organization_id}/members/{member_id}")
async def update_member(
    organization_id: str,
    member_id: str,
    payload: MemberRoleRequest,
    request: Request,
    user: Dict[str, Any] = Depends(get_current_user),
):
    _organization_for_admin(organization_id, user)
    existing = OrganizationRepository.get_for_member(organization_id, member_id)
    if not existing:
        raise HTTPException(404, "Member not found")
    if existing["membership_role"] == "OWNER":
        raise HTTPException(409, "The workspace owner role cannot be changed")
    OrganizationRepository.upsert_member(organization_id, member_id, payload.role)
    AuditRepository.log_audit(
        "ORGANIZATION_MEMBER_ROLE_CHANGED",
        user_id=user["id"], organization_id=organization_id,
        client_ip=request.client.host if request.client else None,
        metadata={"member_id": member_id, "role": payload.role},
    )
    return {"member_id": member_id, "role": payload.role}


@router.delete("/{organization_id}/members/{member_id}", status_code=204)
async def remove_member(
    organization_id: str,
    member_id: str,
    request: Request,
    user: Dict[str, Any] = Depends(get_current_user),
):
    _organization_for_admin(organization_id, user)
    if not OrganizationRepository.remove_member(organization_id, member_id):
        raise HTTPException(409, "Member not found or workspace owner cannot be removed")
    AuditRepository.log_audit(
        "ORGANIZATION_MEMBER_REMOVED",
        user_id=user["id"], organization_id=organization_id,
        client_ip=request.client.host if request.client else None,
        metadata={"member_id": member_id},
    )


@router.put("/{organization_id}/retention")
async def set_retention_policy(
    organization_id: str,
    payload: RetentionPolicyRequest,
    request: Request,
    user: Dict[str, Any] = Depends(get_current_user),
):
    _organization_for_admin(organization_id, user)
    OrganizationRepository.set_retention(organization_id, payload.retention_days)
    AuditRepository.log_audit(
        "RETENTION_POLICY_CHANGED",
        user_id=user["id"], organization_id=organization_id,
        client_ip=request.client.host if request.client else None,
        metadata={"retention_days": payload.retention_days},
    )
    return {"organization_id": organization_id, "retention_days": payload.retention_days}


@router.get("/{organization_id}/audit-events")
async def list_audit_events(
    organization_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    event_type: str | None = Query(default=None, max_length=120),
    user_id: str | None = Query(default=None, max_length=80),
    matter_id: str | None = Query(default=None, max_length=80),
    record_id: str | None = Query(default=None, max_length=80),
    date_from: str | None = Query(default=None, max_length=10),
    date_to: str | None = Query(default=None, max_length=10),
    user: Dict[str, Any] = Depends(get_current_user),
):
    _organization_for_admin(organization_id, user)
    return {
        "events": AuditRepository.list_for_organization(
            organization_id,
            limit,
            event_type=event_type,
            user_id=user_id,
            matter_id=matter_id,
            record_id=record_id,
            date_from=date_from,
            date_to=date_to,
        )
    }


@router.get("/{organization_id}/audit-events/export")
async def export_audit_events(
    organization_id: str,
    format: str = Query(default="json", pattern="^(json|markdown|csv)$"),
    limit: int = Query(default=500, ge=1, le=500),
    event_type: str | None = Query(default=None, max_length=120),
    user_id: str | None = Query(default=None, max_length=80),
    matter_id: str | None = Query(default=None, max_length=80),
    record_id: str | None = Query(default=None, max_length=80),
    date_from: str | None = Query(default=None, max_length=10),
    date_to: str | None = Query(default=None, max_length=10),
    user: Dict[str, Any] = Depends(get_current_user),
):
    _organization_for_admin(organization_id, user)
    events = AuditRepository.list_for_organization(
        organization_id,
        limit,
        event_type=event_type,
        user_id=user_id,
        matter_id=matter_id,
        record_id=record_id,
        date_from=date_from,
        date_to=date_to,
    )
    payload = build_audit_export(events, organization_id=organization_id, exported_by=user["id"])
    AuditRepository.log_audit(
        "AUDIT_EVENTS_EXPORTED",
        user_id=user["id"],
        organization_id=organization_id,
        metadata={"format": format, "event_count": len(events), "event_type": event_type or "", "matter_id": matter_id or "", "record_id": record_id or ""},
    )
    if format == "markdown":
        return Response(
            content=audit_export_markdown(payload),
            media_type="text/markdown",
            headers={"Content-Disposition": 'attachment; filename="nyaya-workspace-audit.md"'},
        )
    if format == "csv":
        return Response(
            content=audit_export_csv(events),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="nyaya-workspace-audit.csv"'},
        )
    return Response(
        content=audit_export_json(payload),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="nyaya-workspace-audit.json"'},
    )
