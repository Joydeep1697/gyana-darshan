"""IndianKanoon public-judgment ingestion for BNS queries."""

from __future__ import annotations

import argparse
import asyncio
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional
from urllib.parse import quote_plus, urljoin

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.ingestion.base import IngestionLogger, save_with_provenance
from app.ingestion.bns_crawler import DEFAULT_USER_AGENT, IngestionError, robots_allows

INDIANKANOON_BASE = "https://indiankanoon.org"
DEFAULT_QUERY = "BNS 103"
OUTPUT_DIR = Path("corpus_integrity") / "judgments"
LOGGER = IngestionLogger(Path("app") / "ingestion" / "ingestion_log.jsonl")


@dataclass(frozen=True)
class IndianKanoonResult:
    status: str
    query: str
    entries: list[dict[str, Any]]
    files: list[str]


def search_url(query: str) -> str:
    return f"{INDIANKANOON_BASE}/search/?formInput={quote_plus(query)}"


def _rate_limit(last_request_at: Optional[float], seconds: float = 1.0) -> float:
    if last_request_at is not None:
        elapsed = time.monotonic() - last_request_at
        if elapsed < seconds:
            time.sleep(seconds - elapsed)
    return time.monotonic()


def _fetch(url: str, retries: int = 3) -> str:
    try:
        from curl_cffi import requests
    except ImportError as exc:
        raise IngestionError("curl_cffi is required for IndianKanoon ingestion. Install requirements.txt first.") from exc

    delay = 1.0
    last_error = ""
    for attempt in range(retries):
        try:
            response = requests.get(url, impersonate="chrome116", headers={"User-Agent": DEFAULT_USER_AGENT}, timeout=30)
            if response.status_code == 402:
                raise IngestionError("IndianKanoon returned a payment-required response; paywalled content will not be scraped.")
            if response.status_code < 400:
                return response.text
            last_error = f"HTTP {response.status_code}"
        except Exception as exc:
            last_error = str(exc)
        if attempt < retries - 1:
            time.sleep(delay)
            delay *= 2
    raise IngestionError(f"IndianKanoon fetch failed for {url}: {last_error}")


async def _crawl_markdown(url: str) -> str:
    try:
        from crawl4ai import AsyncWebCrawler
    except ImportError:
        return ""
    try:
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(url=url)
        return (getattr(result, "markdown", "") or "").strip()
    except Exception:
        return ""


def _extract_text_with_scrapling(html: str, url: str) -> str:
    try:
        from scrapling import Adaptor
    except ImportError:
        return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()

    adaptor = Adaptor(html, url=url)
    for selector in ("#judgments", ".judgments", ".judgment", "article", "body"):
        try:
            elements = adaptor.css(selector)
        except Exception:
            elements = []
        text = "\n\n".join((getattr(element, "text", "") or "").strip() for element in elements)
        if len(text) > 200:
            return text
    return (getattr(adaptor, "text", "") or "").strip()


def _discover_case_urls(html: str) -> list[str]:
    urls: list[str] = []
    for href in re.findall(r"""href=["']([^"']+)["']""", html, flags=re.I):
        if re.match(r"^/doc(?:fragment)?/\d+/?", href):
            absolute = urljoin(INDIANKANOON_BASE, href)
            if absolute not in urls:
                urls.append(absolute)
    return urls


def _case_id(url: str) -> str:
    match = re.search(r"/doc(?:fragment)?/(\d+)", url)
    return match.group(1) if match else re.sub(r"\W+", "_", url).strip("_")[:80]


async def ingest_indiankanoon(query: str = DEFAULT_QUERY, limit: int = 10) -> IndianKanoonResult:
    url = search_url(query)
    if not robots_allows(url, user_agent=DEFAULT_USER_AGENT):
        entry = LOGGER.log("INDIANKANOON", query, url, "ROBOTS_BLOCKED")
        return IndianKanoonResult("blocked", query, [entry], [])

    entries: list[dict[str, Any]] = []
    files: list[str] = []
    last_request_at: Optional[float] = None
    try:
        last_request_at = _rate_limit(last_request_at)
        html = _fetch(url)
        markdown = await _crawl_markdown(url)
        case_urls = _discover_case_urls(html)[: max(1, min(limit, 25))]
        entries.append(LOGGER.log("INDIANKANOON", query, url, "SEARCH_OK", result_count=len(case_urls)))
        for case_url in case_urls:
            if not robots_allows(case_url, user_agent=DEFAULT_USER_AGENT):
                entries.append(LOGGER.log("INDIANKANOON", query, case_url, "ROBOTS_BLOCKED"))
                continue
            last_request_at = _rate_limit(last_request_at)
            case_html = _fetch(case_url)
            case_markdown = await _crawl_markdown(case_url)
            text = case_markdown or _extract_text_with_scrapling(case_html, case_url)
            if len(text.strip()) < 200:
                entries.append(LOGGER.log("INDIANKANOON", query, case_url, "EMPTY_TEXT"))
                continue
            case_id = _case_id(case_url)
            output_path = OUTPUT_DIR / f"bns_103_{case_id}.md"
            saved = save_with_provenance(
                text.strip(),
                output_path,
                case_url,
                "INDIANKANOON",
                query,
                "curl_cffi chrome116 + crawl4ai + scrapling adaptive",
            )
            files.append(str(saved))
            entries.append(LOGGER.log("INDIANKANOON", query, case_url, "SAVED", file_path=str(saved), case_id=case_id))
        if not case_urls and markdown:
            output_path = OUTPUT_DIR / "bns_103_search_results.md"
            saved = save_with_provenance(markdown, output_path, url, "INDIANKANOON", query, "crawl4ai search-result fallback")
            files.append(str(saved))
            entries.append(LOGGER.log("INDIANKANOON", query, url, "SAVED_SEARCH_MARKDOWN", file_path=str(saved)))
        return IndianKanoonResult("saved" if files else "no_results", query, entries, files)
    except Exception as exc:
        entries.append(LOGGER.log("INDIANKANOON", query, url, "FAILED", error=str(exc)))
        return IndianKanoonResult("failed", query, entries, files)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Ingest public IndianKanoon judgments.")
    parser.add_argument("--query", default=DEFAULT_QUERY)
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args(argv)
    result = asyncio.run(ingest_indiankanoon(args.query, args.limit))
    print(result)
    return 0 if result.status in {"saved", "no_results", "blocked"} else 1


if __name__ == "__main__":
    raise SystemExit(main())

