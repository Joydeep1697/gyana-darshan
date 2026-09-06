"""Explicit public pages sharing the existing zero-build application shell."""

from html import escape
import os
from pathlib import Path
import re
from urllib.parse import urlsplit

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.routers.billing import PLANS, get_public_billing_config

router = APIRouter()
STATIC = Path(__file__).resolve().parents[1] / "static"
PAGES = {
    "about": ("About Us", "Our purpose, product approach, team information and careers."),
    "services": ("Research Services", "Explore statutory research, transition analysis, PDF document work and team workspaces."),
    "use-cases": ("Use Cases", "Illustrative workflows for Indian legal research and document review."),
    "pricing": ("Pricing", "Understand workspace access, payment availability and usage limits."),
    "contact": ("Contact & Support", "Find product help, contact information and official profiles."),
    "privacy": ("Privacy Information", "How this application handles accounts, research and uploaded documents."),
    "terms": ("Terms of Use", "Understand the scope and limitations of this legal research tool."),
}


def contact_html() -> str:
    # Reject address headers, URL schemes and markup; configuration is still input.
    address = os.getenv("PUBLIC_CONTACT_EMAIL", "").strip()
    if len(address) <= 254 and re.fullmatch(r"[A-Za-z0-9._+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,63}", address):
        safe = escape(address, quote=True)
        return f'<p>Email the product team at <a href="mailto:{safe}">{safe}</a>. Include the issue and steps to reproduce it; omit passwords and confidential case documents.</p>'
    return '<p>A public contact email has not been published for this deployment. Use the support guidance below to troubleshoot common issues.</p>'


def social_html() -> str:
    profiles = []
    for variable, label, domains in (
        ("PUBLIC_LINKEDIN_URL", "LinkedIn", {"linkedin.com", "www.linkedin.com"}),
        ("PUBLIC_GITHUB_URL", "GitHub", {"github.com", "www.github.com"}),
    ):
        value = os.getenv(variable, "").strip()
        try:
            url = urlsplit(value)
            valid = (url.scheme == "https" and url.hostname in domains and not url.username
                     and not url.password and url.port in (None, 443)
                     and not any(ord(char) < 33 for char in value))
        except ValueError:
            valid = False
        if valid:
            profiles.append(f'<a href="{escape(value, quote=True)}" rel="noopener noreferrer">{label}</a>')
    return '<p>' + (' · '.join(profiles) if profiles else 'Official social profiles have not been published here.') + '</p>'


def pricing_html() -> str:
    if not get_public_billing_config()["enabled"]:
        return '<p class="site-notice">Paid checkout is currently unavailable on this deployment. You can create an account and use the displayed workspace allowance.</p>'
    prices = ''.join(
        f'<li><strong>{escape(plan)}</strong>: ₹{amount / 100:,.0f} access activation</li>'
        for plan, amount in PLANS.items()
    )
    return ('<ul>' + prices + '</ul><p>These are the configured activation amounts, not monthly prices. '
            'A payment records plan activation; it does not currently increase the role-based daily query allowance. '
            'Review available checkout options in Account &amp; access before paying.</p>')


@router.get("/about", response_class=HTMLResponse, include_in_schema=False)
@router.get("/services", response_class=HTMLResponse, include_in_schema=False)
@router.get("/use-cases", response_class=HTMLResponse, include_in_schema=False)
@router.get("/pricing", response_class=HTMLResponse, include_in_schema=False)
@router.get("/contact", response_class=HTMLResponse, include_in_schema=False)
@router.get("/privacy", response_class=HTMLResponse, include_in_schema=False)
@router.get("/terms", response_class=HTMLResponse, include_in_schema=False)
def public_page(request: Request) -> HTMLResponse:
    slug = request.url.path.strip("/")
    title, description = PAGES[slug]
    content = (STATIC / "pages" / f"{slug}.html").read_text(encoding="utf-8")
    content = content.replace("<!-- CONTACT -->", contact_html())
    content = content.replace("<!-- SOCIAL -->", social_html())
    content = content.replace("<!-- PRICING -->", pricing_html())
    shell = (STATIC / "index.html").read_text(encoding="utf-8")
    before, marker, rest = shell.partition('<main id="mainContent">')
    _, closing, after = rest.partition("</main>")
    if not marker or not closing:
        raise RuntimeError("Public shell is missing its main content boundary")
    result = before + marker + content + closing + after
    result = re.sub(r"<title>.*?</title>", f"<title>{escape(title)} | Nyaya Darshana</title>", result, count=1)
    result = re.sub(r'<meta name="description" content="[^"]*">',
                    f'<meta name="description" content="{escape(description, quote=True)}">', result, count=1)
    return HTMLResponse(result, headers={"Cache-Control": "no-store"})
