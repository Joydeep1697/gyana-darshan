"""Check internal public links and local corpus audit links.

This script is intentionally lightweight: it uses the FastAPI TestClient for
application routes and direct filesystem checks for corpus_integrity links.
"""

from __future__ import annotations

from collections import deque
from html.parser import HTMLParser
from pathlib import Path
import sys
from urllib.parse import urldefrag, urlsplit

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.main import app

PUBLIC_START = ["/", "/about", "/services", "/use-cases", "/pricing", "/contact", "/faq", "/privacy", "/terms"]


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[str] = []
        self.ids: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {name: value or "" for name, value in attrs}
        if values.get("id"):
            self.ids.add(values["id"])
        if tag in {"a", "link", "script", "img"}:
            for attr in ("href", "src"):
                if values.get(attr):
                    self.links.append(values[attr])


def _is_private_or_external(href: str) -> bool:
    parsed = urlsplit(href)
    if parsed.scheme in {"mailto", "tel"}:
        return True
    if parsed.scheme or parsed.netloc:
        return True
    return parsed.path.startswith(("/api/", "/app/storage/"))


def check_routes() -> list[str]:
    client = TestClient(app)
    failures: list[str] = []
    seen: set[str] = set()
    queue: deque[str] = deque(PUBLIC_START)
    page_ids: dict[str, set[str]] = {}

    while queue:
        path = queue.popleft()
        route, fragment = urldefrag(path)
        route = route or "/"
        if route in seen:
            continue
        seen.add(route)
        response = client.get(route)
        if response.status_code >= 400:
            failures.append(f"{route} returned {response.status_code}")
            continue
        parser = LinkParser()
        if response.headers.get("content-type", "").startswith("text/html"):
            parser.feed(response.text)
            page_ids[route] = parser.ids
            for href in parser.links:
                if _is_private_or_external(href):
                    continue
                target, _ = urldefrag(href)
                parsed = urlsplit(target)
                if parsed.path and parsed.path.startswith("/"):
                    queue.append(parsed.path)
        if fragment and fragment not in page_ids.get(route, set()):
            failures.append(f"{path} missing anchor #{fragment}")

    for path in ("/robots.txt", "/sitemap.xml", "/favicon.ico"):
        response = client.get(path)
        if response.status_code != 200:
            failures.append(f"{path} returned {response.status_code}")
    return failures


def check_corpus_links() -> list[str]:
    failures: list[str] = []
    corpus = ROOT / "corpus_integrity"
    if not corpus.exists():
        return failures
    for file in corpus.rglob("*"):
        if file.is_file() and file.suffix.lower() in {".html", ".md", ".json", ".jsonl", ".txt", ".png"} and file.stat().st_size == 0:
            failures.append(f"{file.relative_to(ROOT)} is empty")
    return failures


def main() -> int:
    failures = [*check_routes(), *check_corpus_links()]
    if failures:
        print("Broken link check failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Broken link check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
