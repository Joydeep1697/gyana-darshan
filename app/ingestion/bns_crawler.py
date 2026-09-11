"""Ingest Bharatiya Nyaya Sanhita sections from public India Code sources.

The crawler is intentionally conservative: it checks robots.txt, rate limits
requests, records source provenance in every output file, and fails closed when
the requested section cannot be extracted from the fetched material.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

if __package__ in {None, ""}:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.ingestion.base import IngestionLogger, save_with_provenance

BNS_SOURCE_URL = "https://www.indiacode.nic.in/indiacode/handle/123456789/20062?col=123456789%2F1362&view_type=search"
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36"
DEFAULT_OUTPUT_DIR = Path("corpus_integrity") / "bns"
LOCAL_BNS_JSONL = Path("corpus_integrity") / "bns_2023_corpus.jsonl"
LOGGER = IngestionLogger()


class IngestionError(RuntimeError):
    """Raised when a source cannot be fetched or parsed safely."""


@dataclass(frozen=True)
class IngestedSection:
    section: str
    heading: str
    text: str
    source_url: str
    fetched_with: str

    @property
    def filename(self) -> str:
        return f"section_{int(self.section):03d}.md"

    def to_markdown(self) -> str:
        title = f"BNS Section {self.section}"
        if self.heading:
            title = f"{title}: {self.heading}"
        return (
            f"# {title}\n\n"
            f"- Statute: Bharatiya Nyaya Sanhita, 2023\n"
            f"- Section: {self.section}\n"
            "## Text\n\n"
            f"{self.text.strip()}\n"
        )


def _robots_url(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}/robots.txt"


def robots_allows(url: str, user_agent: str = DEFAULT_USER_AGENT, timeout: int = 10) -> bool:
    parser = RobotFileParser()
    parser.set_url(_robots_url(url))
    try:
        parser.read()
    except Exception as exc:
        raise IngestionError(f"Could not read robots.txt for {urlparse(url).netloc}: {exc}") from exc
    return parser.can_fetch(user_agent, url)


def rate_limit(last_request_at: Optional[float], minimum_interval_seconds: float = 1.0) -> float:
    if last_request_at is not None:
        elapsed = time.monotonic() - last_request_at
        if elapsed < minimum_interval_seconds:
            time.sleep(minimum_interval_seconds - elapsed)
    return time.monotonic()


def _extract_pdf_text(content: bytes) -> str:
    try:
        import fitz
    except ImportError as exc:
        raise IngestionError("PyMuPDF is required to extract text from India Code PDFs.") from exc

    with fitz.open(stream=content, filetype="pdf") as document:
        return "\n\n".join(page.get_text("text") for page in document)


def _looks_like_pdf(content: bytes, content_type: str = "") -> bool:
    return content.startswith(b"%PDF-") or "pdf" in content_type.casefold()


def discover_pdf_url(html: str, base_url: str) -> Optional[str]:
    candidates = re.findall(r"""href=["']([^"']+(?:bitstream|download|pdf)[^"']*)["']""", html, flags=re.I)
    for candidate in candidates:
        candidate_url = urljoin(base_url, candidate.replace("&amp;", "&"))
        if candidate_url.startswith("http"):
            return candidate_url
    return None


def _response_to_text_and_pdf_url(response: object, url: str) -> tuple[str, Optional[str]]:
    content = getattr(response, "content", b"") or b""
    headers = getattr(response, "headers", {}) or {}
    content_type = headers.get("content-type", "") if hasattr(headers, "get") else ""
    if _looks_like_pdf(content, content_type):
        return _extract_pdf_text(content), url
    html = getattr(response, "text", "") or ""
    discovered_pdf = discover_pdf_url(html, url)
    return html, discovered_pdf


def _fetch_with_powershell(url: str, user_agent: str, timeout: int) -> tuple[str, Optional[str]]:
    executable = shutil.which("pwsh") or shutil.which("powershell") or "powershell"
    command = [
        executable,
        "-NoProfile",
        "-Command",
        (
            "$ProgressPreference='SilentlyContinue'; "
            "$headers=@{'User-Agent'=$env:NYAYA_INGEST_USER_AGENT}; "
            "$r=Invoke-WebRequest -Uri $env:NYAYA_INGEST_URL -UseBasicParsing -MaximumRedirection 5 "
            "-TimeoutSec ([int]$env:NYAYA_INGEST_TIMEOUT) -Headers $headers; "
            "if ($r.Content) { $r.Content }"
        ),
    ]
    env = {
        **os.environ,
        "NYAYA_INGEST_URL": url,
        "NYAYA_INGEST_USER_AGENT": user_agent,
        "NYAYA_INGEST_TIMEOUT": str(timeout),
    }
    completed = subprocess.run(command, check=False, capture_output=True, text=True, timeout=timeout + 10, env=env)
    if completed.returncode != 0:
        raise IngestionError((completed.stderr or completed.stdout or "PowerShell fetch failed").strip())
    html = completed.stdout
    return html, discover_pdf_url(html, url)


def fetch_with_curl_cffi(url: str, user_agent: str = DEFAULT_USER_AGENT, timeout: int = 30) -> tuple[str, Optional[str], str]:
    try:
        from curl_cffi import requests as curl_requests
    except ImportError as exc:
        raise IngestionError("curl_cffi is required for India Code ingestion. Install requirements.txt first.") from exc

    response = curl_requests.get(
        url,
        impersonate="chrome116",
        headers={"User-Agent": user_agent},
        timeout=timeout,
    )
    if response.status_code < 400:
        text, discovered_pdf = _response_to_text_and_pdf_url(response, url)
        return text, discovered_pdf, "curl_cffi chrome116"

    try:
        import requests as standard_requests
    except ImportError as exc:
        raise IngestionError(f"India Code returned HTTP {response.status_code} for {url}") from exc
    fallback = standard_requests.get(
        url,
        headers={"User-Agent": user_agent},
        timeout=timeout,
    )
    if fallback.status_code >= 400:
        try:
            text, discovered_pdf = _fetch_with_powershell(url, user_agent, timeout)
            return text, discovered_pdf, f"PowerShell fallback after curl_cffi HTTP {response.status_code} and requests HTTP {fallback.status_code}"
        except Exception as exc:
            raise IngestionError(
                f"India Code returned HTTP {response.status_code} with curl_cffi and HTTP {fallback.status_code} with requests for {url}"
            ) from exc
    text, discovered_pdf = _response_to_text_and_pdf_url(fallback, url)
    return text, discovered_pdf, f"requests fallback after curl_cffi HTTP {response.status_code}"


def fetch_with_scrapling(url: str) -> str:
    try:
        import scrapling
    except ImportError as exc:
        raise IngestionError("scrapling is required for adaptive section extraction. Install requirements.txt first.") from exc

    page = scrapling.Fetcher.get(url, adaptive=True)
    chunks: list[str] = []
    try:
        for item in page.css(".act-section"):
            text = getattr(item, "text", None)
            chunks.append(text() if callable(text) else str(item))
    except Exception:
        chunks = []
    return "\n\n".join(chunk.strip() for chunk in chunks if chunk and chunk.strip()) or str(page)


async def fetch_markdown_with_crawl4ai(url: str) -> str:
    try:
        from crawl4ai import AsyncWebCrawler
    except ImportError as exc:
        raise IngestionError("crawl4ai is required for Markdown extraction. Install requirements.txt first.") from exc

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=url)
    return (getattr(result, "markdown", "") or "").strip()


def _normalise_text(value: str) -> str:
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def _extract_section_from_jsonl(section: str, source_url: str) -> Optional[IngestedSection]:
    if not LOCAL_BNS_JSONL.exists():
        return None
    with LOCAL_BNS_JSONL.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            if str(record.get("section")) == str(section):
                heading = _normalise_text(record.get("heading") or "")
                body = _normalise_text(record.get("text") or "")
                combined = _normalise_text(f"{heading}\n{body}")
                next_section = str(int(section) + 1)
                combined = re.split(rf"(?m)\n?\s*{re.escape(next_section)}\.\s*", combined, maxsplit=1)[0].strip()
                return IngestedSection(
                    section=str(section),
                    heading=heading.split(".")[0].strip()[:180],
                    text=combined,
                    source_url=source_url,
                    fetched_with="local authoritative BNS JSONL fallback",
                )
    return None


def extract_section(section: str, source_text: str, source_url: str, fetched_with: str) -> IngestedSection:
    section_number = re.escape(str(section))
    text = _normalise_text(source_text)
    patterns = [
        rf"(?is)(?:^|\n)\s*(?:section\s+)?{section_number}\.?\s+(.+?)(?=\n\s*(?:section\s+)?{int(section) + 1}\.?\s+|\Z)",
        rf"(?is)(?:^|\n)\s*{section_number}\s+(.+?)(?=\n\s*{int(section) + 1}\s+|\Z)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        body = _normalise_text(match.group(1))
        if len(body) < 80:
            continue
        first_line = body.splitlines()[0].strip()
        heading = first_line[:180] if first_line else ""
        return IngestedSection(section=str(section), heading=heading, text=body, source_url=source_url, fetched_with=fetched_with)

    fallback = _extract_section_from_jsonl(str(section), source_url)
    if fallback:
        return fallback
    raise IngestionError(f"BNS Section {section} was not found in fetched India Code material.")


async def ingest_bns_section(
    section: str = "103",
    url: str = BNS_SOURCE_URL,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    user_agent: str = DEFAULT_USER_AGENT,
) -> Path:
    LOGGER.log("BNS", section, url, "STARTED")
    try:
        if not robots_allows(url, user_agent=user_agent):
            raise IngestionError(f"robots.txt does not allow fetching {url}")

        last_request_at: Optional[float] = None
        source_parts: list[tuple[str, str]] = []

        try:
            last_request_at = rate_limit(last_request_at)
            curl_text, discovered_pdf, fetch_method = fetch_with_curl_cffi(url, user_agent=user_agent)
            source_parts.append((fetch_method, curl_text))
        except IngestionError as exc:
            fallback = _extract_section_from_jsonl(str(section), url)
            if not fallback:
                raise
            output_path = output_dir / fallback.filename
            fallback_record = IngestedSection(
                section=fallback.section,
                heading=fallback.heading,
                text=fallback.text,
                source_url=fallback.source_url,
                fetched_with=f"local authoritative BNS JSONL fallback after live India Code fetch failure: {exc}",
            )
            saved_path = save_with_provenance(
                fallback_record.to_markdown(),
                output_path,
                fallback_record.source_url,
                "BNS",
                fallback_record.section,
                fallback_record.fetched_with,
            )
            LOGGER.log("BNS", section, url, "SAVED_FROM_LOCAL_FALLBACK", file_path=str(saved_path), error=str(exc))
            return saved_path

        if discovered_pdf and robots_allows(discovered_pdf, user_agent=user_agent):
            last_request_at = rate_limit(last_request_at)
            pdf_text, _, pdf_fetch_method = fetch_with_curl_cffi(discovered_pdf, user_agent=user_agent)
            source_parts.append((f"{pdf_fetch_method} discovered PDF", pdf_text))

        try:
            last_request_at = rate_limit(last_request_at)
            source_parts.append(("Scrapling adaptive", fetch_with_scrapling(url)))
        except IngestionError:
            if not source_parts:
                raise

        try:
            last_request_at = rate_limit(last_request_at)
            source_parts.append(("Crawl4AI markdown", await fetch_markdown_with_crawl4ai(url)))
        except IngestionError:
            if not source_parts:
                raise

        combined_text = "\n\n".join(part for _, part in source_parts if part)
        section_record = extract_section(section, combined_text, url, "curl_cffi chrome116 + Scrapling adaptive + Crawl4AI")
        output_path = output_dir / section_record.filename
        saved_path = save_with_provenance(
            section_record.to_markdown(),
            output_path,
            section_record.source_url,
            "BNS",
            section_record.section,
            section_record.fetched_with,
        )
        LOGGER.log("BNS", section, url, "SAVED", file_path=str(saved_path))
        return saved_path
    except Exception as exc:
        LOGGER.log("BNS", section, url, "FAILED", error=str(exc))
        raise


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Ingest a BNS section from public India Code sources.")
    parser.add_argument("--section", default="103", help="BNS section number to extract.")
    parser.add_argument("--url", default=BNS_SOURCE_URL, help="Public India Code source URL.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Directory for section Markdown files.")
    args = parser.parse_args(argv)
    output = asyncio.run(ingest_bns_section(args.section, args.url, Path(args.output_dir)))
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
