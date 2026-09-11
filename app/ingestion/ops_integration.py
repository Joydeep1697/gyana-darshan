"""Nyaya Ops integration for human-action ingestion boundaries."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

from app.database import Database, get_db
from app.ingestion.base import IngestionLogger
from database.repository import AuditRepository

LOGGER = IngestionLogger(Path("app") / "ingestion" / "ingestion_log.jsonl")


def _task_title(source: str) -> str:
    clean_source = (source or "ingestion").strip()[:40]
    return f"[Human Action Required] {clean_source} CAPTCHA/manual review"


def create_human_review_task(
    tenant_id: str,
    source: str,
    url: str,
    html_path: Path,
    png_path: Optional[Path],
    reason: str = "CAPTCHA/manual court selection detected",
    metadata: Optional[dict[str, Any]] = None,
    *,
    db: Optional[Database] = None,
    user_id: Optional[str] = None,
) -> str:
    """Create a workspace-scoped Nyaya Ops task for human ingestion follow-up."""
    if not tenant_id:
        raise ValueError("tenant_id is required for human review task creation")
    database = db or get_db()
    task = database.create_task(
        tenant_id,
        _task_title(source),
        status="open",
        priority="high",
        assignee_user_id=user_id,
    )
    task_id = task["id"]
    payload = {
        "task_id": task_id,
        "source": source,
        "source_url": url,
        "evidence_html": str(html_path),
        "evidence_screenshot": str(png_path) if png_path else None,
        "reason": reason,
        "metadata": metadata or {},
        "instructions": [
            "Open the source URL in a normal browser.",
            "Complete CAPTCHA and required court/district selection manually.",
            "Download judgment PDFs only when publicly available.",
            "Upload authorized PDFs to the tenant Vault.",
            "Keep provenance_verified false until legal review.",
        ],
    }
    AuditRepository.log_audit(
        "INGESTION_HUMAN_REVIEW_TASK_CREATED",
        user_id=user_id,
        organization_id=tenant_id,
        metadata=payload,
    )
    LOGGER.log(
        "OPS_TASK",
        source,
        url,
        "HUMAN_TASK_CREATED",
        file_path=task_id,
        tenant_id=tenant_id,
        evidence_html=str(html_path),
        evidence_screenshot=str(png_path) if png_path else None,
        reason=reason,
    )
    print(f"[OPS_TASK_CREATED] {task_id} for tenant {tenant_id} - {reason}")
    return task_id


def default_browser_check_tenant() -> str:
    return os.getenv("NYAYA_BROWSER_CHECK_TENANT_ID", "default_tenant").strip() or "default_tenant"
