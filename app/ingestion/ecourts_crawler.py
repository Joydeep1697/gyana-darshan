"""Tenant-scoped eCourts ingestion scaffold.

eCourts workflows often require state/court choices and CAPTCHA validation.
This module prepares Browser Use and Crawlee integration points, but it does
not bypass CAPTCHA or fabricate judgment downloads when the public site needs
human action.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.config import ROOT_DIR
from app.ingestion.base import IngestionLogger, save_with_provenance
from app.ingestion.bns_crawler import DEFAULT_USER_AGENT, robots_allows

ECOURTS_HOME_URL = "https://ecourts.gov.in/"
DEFAULT_QUERY = "BNS 103"
DEFAULT_TENANT_ID = "local-cron"
LOGGER = IngestionLogger(Path("app") / "ingestion" / "ingestion_log.jsonl")


@dataclass(frozen=True)
class ECourtsIngestionResult:
    status: str
    source_url: str
    tenant_id: str
    query: str
    files: list[str]
    entries: list[dict[str, Any]]
    message: str


def tenant_ecourts_dir(tenant_id: str) -> Path:
    safe_tenant = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in tenant_id).strip("_")
    if not safe_tenant:
        raise ValueError("tenant_id is required for eCourts ingestion")
    root = (ROOT_DIR / "app" / "storage" / "vault" / safe_tenant / "ecourts").resolve()
    expected = (ROOT_DIR / "app" / "storage" / "vault").resolve()
    if not root.is_relative_to(expected):
        raise ValueError("Invalid tenant storage path")
    root.mkdir(parents=True, exist_ok=True)
    return root


async def _rate_limit() -> None:
    await asyncio.sleep(1.0)


async def _prepare_crawlee_queue(query: str, limit: int) -> dict[str, Any]:
    try:
        import crawlee  # noqa: F401
    except Exception as exc:
        return {"available": False, "reason": f"crawlee is unavailable: {exc}"}
    return {"available": True, "query": query, "limit": limit, "state": "queue-ready"}


async def _run_browser_use_probe(query: str, limit: int) -> dict[str, Any]:
    try:
        import browser_use  # noqa: F401
    except Exception as exc:
        return {"available": False, "reason": f"browser-use is unavailable: {exc}"}
    task = (
        "Go to ecourts.gov.in, select state, court, search "
        f"{query}, get latest {limit} case numbers, download judgment PDFs if available. "
        "Stop and report needs_human_action if CAPTCHA or account-specific input is required."
    )
    return {"available": True, "task": task, "state": "manual-or-llm-configuration-required"}


def register_pdf_with_vault(
    pdf_path: Path,
    tenant_id: str,
    filename: Optional[str] = None,
    owner_id: Optional[str] = None,
    db: Any = None,
) -> str:
    """Register a downloaded PDF through the existing Vault database path."""
    from app.database import get_db

    database = db or get_db()
    resolved = pdf_path.resolve()
    storage_root = tenant_ecourts_dir(tenant_id).resolve()
    if not resolved.is_relative_to(storage_root):
        raise ValueError("Refusing to index a PDF outside the tenant eCourts storage directory")
    return database.create_document(
        filename or resolved.name,
        resolved.stat().st_size,
        str(resolved),
        owner_id=owner_id,
        organization_id=tenant_id,
    )


async def ingest_ecourts(
    query: str = DEFAULT_QUERY,
    tenant_id: str = DEFAULT_TENANT_ID,
    limit: int = 10,
    state: str = "",
    court: str = "",
    db: Any = None,
    owner_id: Optional[str] = None,
) -> ECourtsIngestionResult:
    if not robots_allows(ECOURTS_HOME_URL, user_agent=DEFAULT_USER_AGENT):
        entry = LOGGER.log(
            "ECOURTS",
            query,
            ECOURTS_HOME_URL,
            "ROBOTS_BLOCKED",
            tenant_id=tenant_id,
            court=court,
            case_no="",
        )
        return ECourtsIngestionResult("blocked", ECOURTS_HOME_URL, tenant_id, query, [], [entry], "robots.txt blocked eCourts ingestion")

    storage_dir = tenant_ecourts_dir(tenant_id)
    await _rate_limit()
    crawlee_state = await _prepare_crawlee_queue(query, limit)
    await _rate_limit()
    browser_state = await _run_browser_use_probe(query, limit)

    message = (
        "eCourts ingestion requires human state/court selection and CAPTCHA completion before PDFs can be downloaded. "
        "No judgment PDFs were fetched or indexed."
    )
    entry = LOGGER.log(
        "ECOURTS",
        query,
        ECOURTS_HOME_URL,
        "NEEDS_HUMAN_ACTION",
        tenant_id=tenant_id,
        court=court or state,
        case_no="",
        storage_dir=str(storage_dir),
        crawlee=crawlee_state,
        browser_use=browser_state,
    )
    return ECourtsIngestionResult("needs_human_action", ECOURTS_HOME_URL, tenant_id, query, [], [entry], message)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run tenant-scoped eCourts judgment ingestion.")
    parser.add_argument("--query", default=DEFAULT_QUERY)
    parser.add_argument("--tenant-id", default=DEFAULT_TENANT_ID)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--state", default="")
    parser.add_argument("--court", default="")
    args = parser.parse_args(argv)
    result = asyncio.run(ingest_ecourts(args.query, args.tenant_id, max(1, min(args.limit, 10)), args.state, args.court))
    print(result)
    return 0 if result.status in {"saved", "needs_human_action", "blocked"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
