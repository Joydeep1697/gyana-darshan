from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, HTTPException

from app.auth.middleware import User, get_current_user


ROLES = ["admin", "lawyer", "clerk", "viewer"]
PERMISSIONS = {
    "admin": ["matters:read", "matters:write", "obligations:write", "calendar:read", "chat:read", "chat:write", "compare:read", "risk:read", "notifications:read"],
    "lawyer": ["matters:read", "matters:write", "obligations:write", "calendar:read", "chat:read", "chat:write", "compare:read", "risk:read"],
    "clerk": ["matters:read", "obligations:write", "calendar:read", "chat:read", "compare:read"],
    "viewer": ["matters:read", "calendar:read", "chat:read"],
}


def require_role(allowed_roles: list[str]) -> Callable[[User], User]:
    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Insufficient role")
        return user
    return dependency


def require_permission(perm: str) -> Callable[[User], User]:
    def dependency(user: User = Depends(get_current_user)) -> User:
        if perm not in PERMISSIONS.get(user.role, []):
            raise HTTPException(status_code=403, detail="Insufficient permission")
        return user
    return dependency
