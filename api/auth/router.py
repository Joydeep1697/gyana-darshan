# router.py — Authentication Endpoints for Nyaya Darshana
#
# Provides:
# POST /api/auth/register
# POST /api/auth/login
# POST /api/auth/logout
# POST /api/auth/refresh
# GET  /api/auth/me

import asyncio
import hmac
import json
import secrets

from fastapi import APIRouter, HTTPException, Depends, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import Dict, Any

from api.auth.schemas import (
    UserRegisterRequest, UserLoginRequest, RefreshTokenRequest,
    LogoutRequest, TokenResponse, UserProfileResponse
)
from api.auth.service import AuthService
from api.auth.google_oauth import (
    exchange_google_code, google_authorization_url, google_oauth_enabled,
)
from api.auth.dependencies import get_current_user, get_user_quota_limits
from database.repository import AuditRepository, UserRepository

router = APIRouter(prefix="/api/auth", tags=["User Authentication & Accounts"])

@router.post("/register", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def register(req: UserRegisterRequest, request: Request):
    """Register a new Nyaya Darshana user account."""
    client_ip = request.client.host if request.client else "127.0.0.1"
    user, error = AuthService.register_user(
        email=req.email,
        password=req.password,
        full_name=req.full_name
    )
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    
    AuditRepository.log_audit(
        event_type="USER_REGISTERED",
        user_id=user["id"],
        client_ip=client_ip,
        metadata={"email": user["email"], "role": user["role"]}
    )

    return {
        "status": "SUCCESS",
        "message": "Account created successfully. Please log in.",
        "user_id": user["id"],
        "email": user["email"]
    }

@router.post("/login", response_model=TokenResponse)
async def login(req: UserLoginRequest, request: Request):
    """Authenticate with email and password, issuing access and refresh tokens."""
    client_ip = request.client.host if request.client else "127.0.0.1"
    user, tokens, error = AuthService.authenticate_user(
        email=req.email,
        password=req.password
    )
    if error:
        AuditRepository.log_audit(
            event_type="AUTH_FAILURE",
            client_ip=client_ip,
            metadata={"email": req.email, "reason": error}
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=error)
    
    AuditRepository.log_audit(
        event_type="AUTH_SUCCESS",
        user_id=user["id"],
        client_ip=client_ip,
        metadata={"email": user["email"], "role": user["role"]}
    )

    return TokenResponse(**tokens)


@router.get("/google/config")
async def google_sign_in_configuration():
    """Expose only whether Google login is configured; never expose credentials."""
    return {"enabled": google_oauth_enabled()}


@router.get("/google")
async def start_google_sign_in(request: Request):
    if not google_oauth_enabled():
        raise HTTPException(status_code=503, detail="Google sign-in is not configured yet.")
    state = secrets.token_urlsafe(32)
    response = RedirectResponse(google_authorization_url(state), status_code=302)
    response.set_cookie(
        "nyaya_google_oauth_state", state, max_age=600, httponly=True,
        secure=request.url.scheme == "https", samesite="lax", path="/api/auth/google",
    )
    return response


@router.get("/google/callback")
async def google_sign_in_callback(request: Request, code: str = "", state: str = "", error: str = ""):
    if error:
        raise HTTPException(status_code=400, detail="Google sign-in was cancelled or denied.")
    expected_state = request.cookies.get("nyaya_google_oauth_state", "")
    if not code or not state or not expected_state or not hmac.compare_digest(state, expected_state):
        raise HTTPException(status_code=400, detail="Invalid or expired Google sign-in state.")
    try:
        profile = await asyncio.to_thread(exchange_google_code, code)
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Google sign-in could not be verified.") from exc

    email = profile["email"].strip().lower()
    user = UserRepository.get_by_email(email)
    if not user:
        user, registration_error = AuthService.register_user(
            email=email,
            password=secrets.token_urlsafe(48),
            full_name=profile.get("name") or email.split("@")[0],
        )
        if registration_error or not user:
            raise HTTPException(status_code=400, detail=registration_error or "Account creation failed.")
    tokens = AuthService.issue_tokens_for_user(user)
    AuditRepository.log_audit(
        event_type="GOOGLE_AUTH_SUCCESS", user_id=user["id"],
        client_ip=request.client.host if request.client else "127.0.0.1",
        metadata={"provider": "google", "email": email},
    )
    payload = json.dumps({
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
    }).replace("</", "<\\/")
    html = (
        "<!doctype html><html><head><meta name=\"referrer\" content=\"no-referrer\"></head>"
        "<body><script>const session=" + payload + ";"
        "localStorage.setItem('nyaya_access_token',session.access_token);"
        "localStorage.setItem('nyaya_refresh_token',session.refresh_token);"
        "window.location.replace('/');</script></body></html>"
    )
    response = HTMLResponse(html, headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"})
    response.delete_cookie("nyaya_google_oauth_state", path="/api/auth/google")
    return response

@router.post("/refresh", response_model=Dict[str, Any])
async def refresh_token(req: RefreshTokenRequest):
    """Obtain a fresh access token using a valid refresh token."""
    new_access_token, error = AuthService.refresh_access_token(req.refresh_token)
    if error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=error)
    
    return {
        "access_token": new_access_token,
        "token_type": "bearer",
        "expires_in_seconds": 60 * 24 * 60
    }

@router.post("/logout", response_model=Dict[str, Any])
async def logout(req: LogoutRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    """Revoke active session refresh token."""
    revoked = AuthService.logout(req.refresh_token)
    AuditRepository.log_audit(
        event_type="USER_LOGOUT",
        user_id=current_user["id"],
        metadata={"revoked": revoked}
    )
    return {"status": "SUCCESS", "message": "Session revoked successfully."}

@router.get("/me", response_model=UserProfileResponse)
async def get_my_profile(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Retrieve current authenticated user details and daily query quota."""
    quota = get_user_quota_limits(current_user)
    return UserProfileResponse(
        id=current_user["id"],
        email=current_user["email"],
        full_name=current_user["full_name"],
        role=current_user["role"],
        is_verified=bool(current_user.get("is_verified", 1)),
        daily_quota_limit=quota["limit"],
        daily_quota_used=quota["used"],
        daily_quota_remaining=quota["remaining"],
        created_at=current_user["created_at"]
    )
