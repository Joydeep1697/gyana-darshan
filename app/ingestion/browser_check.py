"""Playwright browser check for the India Code BNS handle."""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from playwright.async_api import async_playwright

from app.ingestion.bns_crawler import BNS_SOURCE_URL, DEFAULT_USER_AGENT, robots_allows

HOME_URL = "https://www.indiacode.nic.in/"
OUTPUT = Path("corpus_integrity") / "bns" / "browser_check_103.html"
LOG = Path("app") / "ingestion" / "browser_check_log.jsonl"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _has_bns_text(html: str) -> bool:
    text = html.casefold()
    return "bharatiya nyaya sanhita" in text or ("section 103" in text and "murder" in text)


def _log(entry: dict) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


async def _rate_limit() -> None:
    await asyncio.sleep(1.0)


async def check_in_browser(url: str = BNS_SOURCE_URL) -> dict:
    if not robots_allows(url, user_agent=DEFAULT_USER_AGENT):
        entry = {
            "timestamp": _utc_now(),
            "url": url,
            "status": 0,
            "html_length": 0,
            "has_bns_text": False,
            "file": None,
            "method": "playwright_chromium",
            "error": f"robots.txt does not allow fetching {urlparse(url).path}",
        }
        _log(entry)
        return entry

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        try:
            context = await browser.new_context(
                user_agent=DEFAULT_USER_AGENT,
                extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
            )
            page = await context.new_page()

            await _rate_limit()
            home_response = await page.goto(HOME_URL, wait_until="domcontentloaded", timeout=30000)

            await _rate_limit()
            response = await page.goto(url, wait_until="domcontentloaded", timeout=30000, referer=HOME_URL)
            status = response.status if response else 0
            html = await page.content()

            OUTPUT.parent.mkdir(parents=True, exist_ok=True)
            OUTPUT.write_text(html, encoding="utf-8")

            entry = {
                "timestamp": _utc_now(),
                "url": url,
                "status": status,
                "html_length": len(html),
                "has_bns_text": _has_bns_text(html),
                "file": str(OUTPUT),
                "method": "playwright_chromium_home_then_handle",
                "home_status": home_response.status if home_response else 0,
                "error": None,
            }
            _log(entry)
            return entry
        except Exception as exc:
            html = ""
            try:
                html = await page.content()
            except Exception:
                html = ""
            if html:
                OUTPUT.parent.mkdir(parents=True, exist_ok=True)
                OUTPUT.write_text(html, encoding="utf-8")
            entry = {
                "timestamp": _utc_now(),
                "url": url,
                "status": 0,
                "html_length": len(html),
                "has_bns_text": _has_bns_text(html),
                "file": str(OUTPUT) if html else None,
                "method": "playwright_chromium_home_then_handle",
                "home_status": None,
                "error": str(exc),
            }
            _log(entry)
            return entry
        finally:
            await browser.close()


def main() -> int:
    result = asyncio.run(check_in_browser())
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("status") and not result.get("error") else 1


if __name__ == "__main__":
    raise SystemExit(main())
