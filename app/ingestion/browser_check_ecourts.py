"""Playwright browser verification for eCourts Phase 2 ingestion."""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from playwright.async_api import async_playwright

from app.ingestion.bns_crawler import DEFAULT_USER_AGENT, robots_allows

URL = "https://ecourts.gov.in/ecourts_home/"
OUTPUT_HTML = Path("corpus_integrity") / "judgments" / "browser_check_ecourts.html"
OUTPUT_PNG = Path("corpus_integrity") / "judgments" / "browser_check_ecourts.png"
LOG = Path("app") / "ingestion" / "browser_check_log.jsonl"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _log(entry: dict) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


async def _rate_limit() -> None:
    await asyncio.sleep(1.0)


async def check() -> dict:
    if not robots_allows(URL, user_agent=DEFAULT_USER_AGENT):
        entry = {
            "timestamp": _utc_now(),
            "url": URL,
            "status": 0,
            "html_length": 0,
            "has_captcha": False,
            "has_ecourts_text": False,
            "screenshot": None,
            "method": "playwright_chromium_headful",
            "error": "robots.txt blocks eCourts browser check",
        }
        _log(entry)
        print(json.dumps(entry, indent=2, ensure_ascii=False))
        return entry

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=False)
        try:
            context = await browser.new_context(user_agent=DEFAULT_USER_AGENT)
            page = await context.new_page()
            print(f"Opening {URL}")
            await _rate_limit()
            response = await page.goto(URL, wait_until="domcontentloaded", timeout=60000)
            status = response.status if response else 0
            await page.wait_for_timeout(5000)
            html = await page.content()
            OUTPUT_HTML.parent.mkdir(parents=True, exist_ok=True)
            OUTPUT_HTML.write_text(html, encoding="utf-8")
            await page.screenshot(path=str(OUTPUT_PNG), full_page=True)
            lower_html = html.casefold()
            has_captcha = "captcha" in lower_html
            has_ecourts = "ecourts" in html or "District Court" in html
            entry = {
                "timestamp": _utc_now(),
                "url": URL,
                "status": status,
                "html_length": len(html),
                "has_captcha": has_captcha,
                "has_ecourts_text": has_ecourts,
                "screenshot": str(OUTPUT_PNG),
                "html_file": str(OUTPUT_HTML),
                "method": "playwright_chromium_headful",
                "error": None,
            }
            if has_captcha and has_ecourts:
                from app.ingestion.ops_integration import create_human_review_task, default_browser_check_tenant

                task_id = create_human_review_task(
                    tenant_id=default_browser_check_tenant(),
                    source="ecourts",
                    url=URL,
                    html_path=OUTPUT_HTML,
                    png_path=OUTPUT_PNG,
                    reason="CAPTCHA detected in eCourts home - manual court selection required",
                    metadata={"status": status, "has_captcha": True, "has_ecourts_text": has_ecourts},
                )
                entry["ops_task_id"] = task_id
            _log(entry)
            print(json.dumps(entry, indent=2, ensure_ascii=False))
            return entry
        except Exception as exc:
            entry = {
                "timestamp": _utc_now(),
                "url": URL,
                "status": 0,
                "html_length": 0,
                "has_captcha": False,
                "has_ecourts_text": False,
                "screenshot": None,
                "method": "playwright_chromium_headful",
                "error": str(exc),
            }
            _log(entry)
            print(json.dumps(entry, indent=2, ensure_ascii=False))
            return entry
        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(check())
