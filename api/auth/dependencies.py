# dependencies.py — FastAPI Authentication & Role-Based Access Guards

from typing import Optional, Dict, Any
from fastapi import Depends, Header, HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from api.auth.service import decode_jwt_token
from database.repository import OrganizationRepository, UserRepository, UsageRepository, SessionRepository
from app.auth.jwt import verify_token as verify_phase8_token
from app.auth.middleware import load_users, sanitize_tenant_id

http_bearer = HTTPBearer(auto_error=False)
FREE_DAILY_CONSULTATION_LIMIT = 10
ANONYMOUS_DAILY_CONSULTATION_LIMIT = 5
ADMIN_DAILY_CONSULTATION_LIMIT = 999999

def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(http_bearer)
) -> Optional[Dict[str, Any]]:
    """Extract authenticated user if token is present and valid; return None if anonymous."""
    if not credentials or not credentials.credentials:
        return None
    
    token = credentials.credentials.strip()
    payload = decode_jwt_token(token)
    if not payload or not payload.get("sub"):
        try:
            phase8_payload = verify_phase8_token(token)
        except HTTPException:
            return None
        return {
            "id": phase8_payload.get("user_id"),
            "email": phase8_payload.get("email"),
            "tenant_id": phase8_payload.get("tenant_id"),
            "role": str(phase8_payload.get("role") or "viewer").upper(),
            "_phase8_auth": True,
        }
    
    user = UserRepository.get_by_id(payload["sub"])
    if payload.get("sid"):
        session = SessionRepository.get_active_session_by_id(payload["sid"])
        if not user or not session or session.get("user_id") != user["id"] or session.get("device_id") != payload.get("device_id"):
            return None
    return user

def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(http_bearer)
) -> Dict[str, Any]:
    """Enforce valid Bearer JWT authentication."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide a valid Bearer token in the Authorization header.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    token = credentials.credentials.strip()
    payload = decode_jwt_token(token)
    if not payload or not payload.get("sub"):
        try:
            phase8_payload = verify_phase8_token(token)
        except HTTPException as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired session token. Please log in again.",
                headers={"WWW-Authenticate": "Bearer"}
            ) from exc
        tenant_id = sanitize_tenant_id(str(phase8_payload.get("tenant_id") or ""))
        user_id = str(phase8_payload.get("user_id") or "")
        for stored_user in load_users():
            if stored_user.get("user_id") == user_id and sanitize_tenant_id(str(stored_user.get("tenant_id") or "")) == tenant_id:
                return {
                    "id": user_id,
                    "email": stored_user.get("email"),
                    "tenant_id": tenant_id,
                    "role": str(stored_user.get("role") or "viewer").upper(),
                    "_phase8_auth": True,
                }
        raise HTTPException(status_code=401, detail="User account not found or deactivated.")
    
    user = UserRepository.get_by_id(payload["sub"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found or deactivated.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    if not payload.get("sid"):
        raise HTTPException(status_code=401, detail="Session must be renewed. Please log in again.")
    session = SessionRepository.get_active_session_by_id(payload["sid"])
    if not session or session.get("user_id") != user["id"] or session.get("device_id") != payload.get("device_id"):
        raise HTTPException(status_code=401, detail="This session is no longer active on this device.")
    return user

def require_admin(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Require ADMIN or SUPERADMIN role."""
    if user.get("role") not in ["ADMIN", "SUPERADMIN"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Administrative privileges required."
        )
    return user

def require_superadmin(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Require SUPERADMIN role."""
    if user.get("role") != "SUPERADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Superadmin privileges required."
        )
    return user


def get_workspace_context(
    organization_id: Optional[str] = Header(default=None, alias="X-Organization-ID"),
    user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Resolve an authenticated organization scope; default to the private workspace."""
    if user.get("_phase8_auth"):
        selected_id = sanitize_tenant_id(organization_id or user["tenant_id"])
        token_tenant = sanitize_tenant_id(user["tenant_id"])
        if selected_id != token_tenant:
            raise HTTPException(status_code=403, detail="Cross-tenant access denied")
        role = str(user.get("role") or "VIEWER").upper()
        return {
            "user": user,
            "organization": {"id": token_tenant, "name": token_tenant, "membership_role": role},
            "role": role,
        }
    selected_id = organization_id or OrganizationRepository.personal_organization_id(user["id"])
    organization = OrganizationRepository.get_for_member(selected_id, user["id"])
    if not organization:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return {"user": user, "organization": organization, "role": organization["membership_role"]}


def require_workspace_writer(
    workspace: Dict[str, Any] = Depends(get_workspace_context),
) -> Dict[str, Any]:
    if workspace["role"] == "VIEWER":
        raise HTTPException(status_code=403, detail="Workspace is read-only for this member")
    return workspace

def get_user_quota_limits(user: Optional[Dict[str, Any]]) -> Dict[str, int]:
    """Calculate daily limits and remaining quota based on user role."""
    if not user:
        return {
            "limit": ANONYMOUS_DAILY_CONSULTATION_LIMIT,
            "used": 0,
            "remaining": ANONYMOUS_DAILY_CONSULTATION_LIMIT,
        }
    
    role = user.get("role", "USER")
    if role in ["ADMIN", "SUPERADMIN"]:
        return {
            "limit": ADMIN_DAILY_CONSULTATION_LIMIT,
            "used": 0,
            "remaining": ADMIN_DAILY_CONSULTATION_LIMIT,
        }
    
    used = UsageRepository.get_user_daily_query_count(user["id"])
    limit = FREE_DAILY_CONSULTATION_LIMIT
    remaining = max(0, limit - used)
    return {"limit": limit, "used": used, "remaining": remaining}
