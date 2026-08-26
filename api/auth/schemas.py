# schemas.py — Pydantic Schemas for Authentication & User Accounts

import re
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator

class UserRegisterRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=255, description="User email address")
    password: str = Field(..., min_length=8, max_length=128, description="Strong password (min 8 chars)")
    full_name: str = Field(..., min_length=2, max_length=128, description="Full name of the account holder")

    @field_validator("email")
    def validate_email_format(cls, v):
        clean = v.strip().lower()
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", clean):
            raise ValueError("Invalid email format.")
        return clean

class UserLoginRequest(BaseModel):
    email: str = Field(..., description="User email address")
    password: str = Field(..., description="User password")

class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., description="Refresh token issued upon login")

class LogoutRequest(BaseModel):
    refresh_token: str = Field(..., description="Refresh token to revoke")

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in_seconds: int

class UserProfileResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    is_verified: bool
    daily_quota_limit: int
    daily_quota_used: int
    daily_quota_remaining: int
    created_at: str
