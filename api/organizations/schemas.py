from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


class OrganizationCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    slug: str = Field(min_length=2, max_length=60, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class MemberRequest(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    role: Literal["ADMIN", "MEMBER", "VIEWER"] = "MEMBER"

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class MemberRoleRequest(BaseModel):
    role: Literal["ADMIN", "MEMBER", "VIEWER"]


class RetentionPolicyRequest(BaseModel):
    retention_days: Optional[int] = Field(default=None, ge=30, le=3650)
