"""Playwright browser verification for IndianKanoon robots/search behavior."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

from playwright.async_api import async_playwright

SEARCH_URL = "https://indiankanoon.org/search/?formInput=BNS%20103"
ROBOTS_URL = "https://indiankanoon.org/robots.txt"
OUTPUT_HTML = Path("corpus_integrity") / "judgments" / "browser_check_indiankanoon.html"
LOG = Path("app") / "ingestion" / "browser_check_log.jsonl"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/116.0.0.0"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _log(entry: dict) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


async def _rate_limit() -> None:
    await asyncio.sleep(1.0)


async def check() -> dict:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        try:
            context = await browser.new_context(user_agent=USER_AGENT)
            page = await context.new_page()
            print(f"Checking robots {ROBOTS_URL}")
            await _rate_limit()
            robots_response = await page.goto(ROBOTS_URL, wait_until="domcontentloaded", timeout=60000)
            robots = await page.text_content("body") or await page.content()
            print(f"Robots length {len(robots)}")
            print(f"Checking search {SEARCH_URL}")
            await _rate_limit()
            response = await page.goto(SEARCH_URL, wait_until="domcontentloaded", timeout=60000)
            status = response.status if response else 0
            html = await page.content()
            OUTPUT_HTML.parent.mkdir(parents=True, exist_ok=True)
            OUTPUT_HTML.write_text(html, encoding="utf-8")
            blocked_by_robots = "Disallow: /search" in robots or "Disallow:/search" in robots.replace(" ", "")
            entry = {
                "timestamp": _utc_now(),
                "search_url": SEARCH_URL,
                "robots_url": ROBOTS_URL,
                "status": status,
                "robots_status": robots_response.status if robots_response else 0,
                "html_length": len(html),
                "robots_length": len(robots),
                "robots_blocks_search": blocked_by_robots,
                "html_file": str(OUTPUT_HTML),
                "method": "playwright",
                "error": None,
            }
            _log(entry)
            print(json.dumps(entry, indent=2, ensure_ascii=False))
            return entry
        except Exception as exc:
            entry = {
                "timestamp": _utc_now(),
                "search_url": SEARCH_URL,
                "robots_url": ROBOTS_URL,
                "status": 0,
                "robots_status": 0,
                "html_length": 0,
                "robots_length": 0,
                "robots_blocks_search": False,
                "html_file": None,
                "method": "playwright",
                "error": str(exc),
            }
            _log(entry)
            print(json.dumps(entry, indent=2, ensure_ascii=False))
            return entry
        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(check())
