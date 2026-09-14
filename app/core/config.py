from __future__ import annotations

import os
from pathlib import Path

from pydantic import BaseModel, Field, field_validator


class Settings(BaseModel):
    environment: str = Field(default_factory=lambda: os.getenv("ENVIRONMENT", os.getenv("ENV", "development")))
    jwt_secret: str = Field(default_factory=lambda: os.getenv("JWT_SECRET", os.getenv("NYAYA_JWT_SECRET", "")))
    allowed_origins: list[str] = Field(default_factory=list)
    storage_dir: Path = Field(default_factory=lambda: Path(os.getenv("NYAYA_STORAGE_DIR", "app/storage")))
    tenant_encryption_key: str = Field(default_factory=lambda: os.getenv("TENANT_ENCRYPTION_KEY", ""))

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_origins(cls, value):
        if isinstance(value, list):
            return value
        raw = value or os.getenv("CORS_ORIGINS", os.getenv("ALLOWED_ORIGINS", ""))
        return [item.strip() for item in str(raw).split(",") if item.strip()]

    @field_validator("jwt_secret")
    @classmethod
    def validate_jwt_secret(cls, value: str) -> str:
        env = os.getenv("ENVIRONMENT", os.getenv("ENV", "development")).lower()
        if env in {"production", "prod"} and len(value) < 32:
            raise ValueError("JWT_SECRET or NYAYA_JWT_SECRET must be at least 32 characters in production")
        return value

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in {"production", "prod"}


def get_settings() -> Settings:
    return Settings()
