"""Static product-quality checks for the zero-build web interface."""

from __future__ import annotations

from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "app" / "static" / "index.html"
LOGO = ROOT / "app" / "static" / "logo-scales-v2.png"
FAVICON = ROOT / "app" / "static" / "favicon-scales.png"


class ProductHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tags: list[tuple[str, dict[str, str]]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.append((tag, {name: value or "" for name, value in attrs}))


def _parsed() -> tuple[str, ProductHTMLParser]:
    source = INDEX.read_text(encoding="utf-8")
    parser = ProductHTMLParser()
    parser.feed(source)
    return source, parser


def test_frontend_has_one_coherent_accessible_document_contract():
    source, parser = _parsed()
    html = next(attrs for tag, attrs in parser.tags if tag == "html")
    ids = [attrs["id"] for _, attrs in parser.tags if attrs.get("id")]
    buttons = [attrs for tag, attrs in parser.tags if tag == "button"]

    assert html.get("lang") == "en"
    assert len(ids) == len(set(ids)), [item for item, count in Counter(ids).items() if count > 1]
    assert all(button.get("type") == "button" or button.get("type") == "submit" for button in buttons)
    # Public and authenticated shells are mutually exclusive; each owns one H1.
    assert source.count("<h1") == 2
    assert 'class="skip-link"' in source
    assert 'aria-live="polite"' in source
    assert "@media(prefers-reduced-motion:reduce)" in source
    assert "@media(max-width:720px)" in source


def test_frontend_loads_without_render_blocking_third_party_assets():
    _, parser = _parsed()
    scripts = [attrs.get("src", "") for tag, attrs in parser.tags if tag == "script"]
    stylesheets = [
        attrs.get("href", "")
        for tag, attrs in parser.tags
        if tag == "link" and attrs.get("rel") == "stylesheet"
    ]
    assert not [src for src in scripts if src.startswith(("http://", "https://"))]
    assert not [href for href in stylesheets if href.startswith(("http://", "https://"))]


def test_frontend_uses_the_approved_scales_brand_assets():
    source, parser = _parsed()
    logo_images = [
        attrs
        for tag, attrs in parser.tags
        if tag == "img" and attrs.get("class") == "brand-logo"
    ]
    icons = [attrs for tag, attrs in parser.tags if tag == "link" and "icon" in attrs.get("rel", "")]

    assert LOGO.is_file() and LOGO.stat().st_size > 0
    assert FAVICON.is_file() and FAVICON.stat().st_size > 0
    assert len(logo_images) == 4
    assert all(image.get("src") == "/static/logo-scales-v2.png" for image in logo_images)
    assert all(image.get("alt") == "" for image in logo_images)
    assert any(icon.get("href") == "/static/favicon-scales.png" for icon in icons)
    assert 'class="mark"' not in source


def test_frontend_uses_real_product_routes_and_current_response_shapes():
    source, _ = _parsed()
    assert "documents.documents||[]" in source
    assert "method:'POST'" in source
    assert "/api/vault/documents/${encodeURIComponent(doc.id)}/summary" in source
    assert "/api/conversations/${encodeURIComponent(state.activeConversation.id)}/messages" in source
    assert "/api/auth/google/config" in source
    assert "application/pdf,.pdf" in source


def test_frontend_does_not_reintroduce_mock_operational_claims_or_reasoning_theatre():
    source, _ = _parsed()
    forbidden = (
        "Mission Control",
        "Active agents",
        "Memory synced",
        "Reasoning Trail",
        "Verification Trail",
        "Dedicated Multi-Agent",
        "DOCX/TXT/HTML/XLSX",
    )
    for phrase in forbidden:
        assert phrase.casefold() not in source.casefold()
    assert not re.search(r"Nyaya Darshan(?!a)", source)
