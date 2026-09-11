"""Shared Playwright source-evidence checks for public legal sources."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from playwright.async_api import async_playwright

from app.ingestion.base import IngestionLogger
from app.ingestion.bns_crawler import DEFAULT_USER_AGENT, robots_allows
from app.ingestion.ops_integration import create_human_review_task, default_browser_check_tenant
from app.ingestion.sources import IngestionSource

LOG = Path("app") / "ingestion" / "browser_check_log.jsonl"
INGESTION_LOGGER = IngestionLogger(Path("app") / "ingestion" / "ingestion_log.jsonl")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_jsonl(path: Path, entry: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _log_metadata(entry: dict[str, Any]) -> dict[str, Any]:
    blocked = {"status", "source_url", "file", "error"}
    return {key: value for key, value in entry.items() if key not in blocked}


def write_manual_evidence(source: IngestionSource, entry: dict[str, Any]) -> Path:
    source.evidence_dir.mkdir(parents=True, exist_ok=True)
    status = entry.get("status", 0)
    html_file = entry.get("html_file") or source.evidence_dir / f"browser_check_{source.key}.html"
    screenshot = entry.get("screenshot")
    evidence = source.evidence_dir / "evidence.md"
    evidence.write_text(
        "---\n"
        f"act: {source.label}\n"
        "section: evidence\n"
        f"source_url: {source.url}\n"
        f"fetched_at: {_utc_now()}\n"
        "fetched_with: needs_human_action\n"
        "provenance_verified: false\n"
        f"corpus: corpus_integrity/{source.key}\n"
        f"evidence_html_path: {html_file}\n"
        f"evidence_screenshot_path: {screenshot or ''}\n"
        "---\n\n"
        f"# {source.label} Evidence\n\n"
        f"{source.label} 2024 source check requires human review before any live verification claim.\n\n"
        f"- Source URL: {source.url}\n"
        f"- Status code: {status}\n"
        f"- CAPTCHA/manual action detected: {bool(entry.get('has_captcha'))}\n"
        f"- Robots blocked: {bool(entry.get('robots_blocks'))}\n"
        "- Provenance verified: false\n",
        encoding="utf-8",
    )
    return evidence


async def check_source(source: IngestionSource, text_markers: tuple[str, ...]) -> dict[str, Any]:
    if not robots_allows(source.url, user_agent=DEFAULT_USER_AGENT):
        entry = {
            "timestamp": _utc_now(),
            "source": source.key,
            "source_url": source.url,
            "url": source.url,
            "status": 0,
            "status_code": 0,
            "html_length": 0,
            "has_captcha": False,
            "robots_blocks": True,
            "fetched_with": "robots_blocked",
            "provenance_verified": False,
            "html_file": None,
            "screenshot": None,
            "error": "robots.txt blocks source check",
        }
        evidence = write_manual_evidence(source, entry)
        entry["file"] = str(evidence)
        _write_jsonl(LOG, entry)
        INGESTION_LOGGER.log(source.key.upper(), "evidence", source.url, "ROBOTS_BLOCKED", file_path=str(evidence), **_log_metadata(entry))
        print(json.dumps(entry, indent=2, ensure_ascii=False))
        return entry

    source.evidence_dir.mkdir(parents=True, exist_ok=True)
    html_path = source.evidence_dir / f"browser_check_{source.key}.html"
    png_path = source.evidence_dir / f"browser_check_{source.key}.png"
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        try:
            context = await browser.new_context(user_agent=DEFAULT_USER_AGENT)
            page = await context.new_page()
            await asyncio.sleep(1.0)
            response = await page.goto(source.url, wait_until="domcontentloaded", timeout=60000)
            status = response.status if response else 0
            await page.wait_for_timeout(1500)
            html = await page.content()
            html_path.write_text(html, encoding="utf-8")
            await page.screenshot(path=str(png_path), full_page=True)
            lower = html.casefold()
            has_captcha = "captcha" in lower or "i am not a robot" in lower
            has_marker = any(marker.casefold() in lower for marker in text_markers)
            entry = {
                "timestamp": _utc_now(),
                "source": source.key,
                "source_url": source.url,
                "url": source.url,
                "status": status,
                "status_code": status,
                "html_length": len(html),
                "has_captcha": has_captcha,
                "has_source_text": has_marker,
                "robots_blocks": False,
                "fetched_with": "needs_human_action" if has_captcha else "playwright_chromium_headless",
                "provenance_verified": False,
                "html_file": str(html_path),
                "screenshot": str(png_path),
                "error": None,
            }
            evidence = write_manual_evidence(source, entry)
            entry["file"] = str(evidence)
            if has_captcha:
                entry["ops_task_id"] = create_human_review_task(
                    tenant_id=default_browser_check_tenant(),
                    source=source.key,
                    url=source.url,
                    html_path=html_path,
                    png_path=png_path,
                    reason=f"CAPTCHA/manual action detected for {source.label}",
                    metadata={"status": status, "has_captcha": has_captcha},
                )
            _write_jsonl(LOG, entry)
            INGESTION_LOGGER.log(source.key.upper(), "evidence", source.url, "EVIDENCE_SAVED", file_path=str(evidence), **_log_metadata(entry))
            print(json.dumps(entry, indent=2, ensure_ascii=False))
            return entry
        except Exception as exc:
            entry = {
                "timestamp": _utc_now(),
                "source": source.key,
                "source_url": source.url,
                "url": source.url,
                "status": 0,
                "status_code": 0,
                "html_length": 0,
                "has_captcha": False,
                "robots_blocks": False,
                "fetched_with": "needs_human_action",
                "provenance_verified": False,
                "html_file": str(html_path),
                "screenshot": None,
                "error": str(exc),
            }
            evidence = write_manual_evidence(source, entry)
            entry["file"] = str(evidence)
            _write_jsonl(LOG, entry)
            INGESTION_LOGGER.log(source.key.upper(), "evidence", source.url, "FAILED", file_path=str(evidence), error=str(exc), **_log_metadata(entry))
            print(json.dumps(entry, indent=2, ensure_ascii=False))
            return entry
        finally:
            await browser.close()
