# dependencies.py — FastAPI Authentication & Role-Based Access Guards

from typing import Optional, Dict, Any
from fastapi import Depends, Header, HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from api.auth.service import decode_jwt_token
from database.repository import OrganizationRepository, UserRepository, UsageRepository

http_bearer = HTTPBearer(auto_error=False)

def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(http_bearer)
) -> Optional[Dict[str, Any]]:
    """Extract authenticated user if token is present and valid; return None if anonymous."""
    if not credentials or not credentials.credentials:
        return None
    
    token = credentials.credentials.strip()
    payload = decode_jwt_token(token)
    if not payload or not payload.get("sub"):
        return None
    
    user = UserRepository.get_by_id(payload["sub"])
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
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    user = UserRepository.get_by_id(payload["sub"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found or deactivated.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
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
        # Anonymous limit
        return {"limit": 5, "used": 0, "remaining": 5}
    
    role = user.get("role", "USER")
    if role in ["ADMIN", "SUPERADMIN"]:
        return {"limit": 999999, "used": 0, "remaining": 999999}
    
    used = UsageRepository.get_user_daily_query_count(user["id"])
    limit = 100
    remaining = max(0, limit - used)
    return {"limit": limit, "used": used, "remaining": remaining}
