"""Public route, navigation integrity, and deployment-controlled copy contracts."""

from collections import Counter
from html.parser import HTMLParser
from urllib.parse import urlsplit

from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.routers.public_site import PAGES
from app.routers.billing import PLANS


class Document(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.ids = []
        self.links = []
        self.h1_count = 0
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.append(attrs["id"])
        if tag == "a" and "href" in attrs:
            self.links.append(attrs["href"])
        if tag == "h1":
            self.h1_count += 1


@pytest.mark.parametrize("slug", PAGES)
def test_public_pages_are_directly_addressable_and_keep_the_app_shell(slug):
    response = TestClient(app).get(f"/{slug}")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert response.headers["cache-control"] == "no-store"
    source = response.text
    doc = Document(source)
    assert doc.h1_count == 2  # One per mutually exclusive public/app shell.
    assert not [key for key, count in Counter(doc.ids).items() if count > 1]
    assert 'id="appShell"' in source and 'id="authForm"' in source
    assert 'aria-label="Breadcrumb"' in source
    assert '/static/public-site.css' in source
    assert '<!-- CONTACT -->' not in source
    assert '<!-- PRICING -->' not in source
    assert '<!-- SOCIAL -->' not in source
    assert '—' not in source
    assert 'Web Development' not in source


def test_every_public_internal_link_resolves_to_a_real_page_and_anchor():
    client = TestClient(app)
    pages = {path: Document(client.get(path).text) for path in ["/", *[f"/{slug}" for slug in PAGES]]}
    for path, doc in pages.items():
        for href in doc.links:
            link = urlsplit(href)
            if link.scheme or link.netloc:
                continue
            target = link.path or path
            assert target in pages, (path, href)
            if link.fragment:
                assert link.fragment in pages[target].ids or link.fragment in {"consultation", "vault", "account"}, (path, href)
    assert client.get('/unpublished-page').status_code == 404
    assert client.get('/api/auth/me').status_code == 401


def test_pricing_uses_server_amounts_and_does_not_advertise_disabled_checkout(monkeypatch):
    client = TestClient(app)
    monkeypatch.delenv("RAZORPAY_KEY_ID", raising=False)
    monkeypatch.delenv("RAZORPAY_KEY_SECRET", raising=False)
    source = client.get('/pricing').text.split('</main>', 1)[0]
    assert 'Paid checkout is currently unavailable' in source
    assert '₹3,999' not in source
    monkeypatch.setenv("RAZORPAY_KEY_ID", "public-key-fixture")
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", "private-secret-fixture")
    source = client.get('/pricing').text
    for amount in PLANS.values():
        assert f'₹{amount / 100:,.0f}' in source
    assert 'does not currently increase' in source
    assert 'private-secret-fixture' not in source
    assert 'public-key-fixture' not in source


def test_contact_configuration_is_optional_and_safely_rendered(monkeypatch):
    client = TestClient(app)
    for key in ('PUBLIC_CONTACT_EMAIL', 'PUBLIC_LINKEDIN_URL', 'PUBLIC_GITHUB_URL'):
        monkeypatch.delenv(key, raising=False)
    assert 'A public contact email has not been published' in client.get('/contact').text
    monkeypatch.setenv('PUBLIC_CONTACT_EMAIL', 'support@example.test')
    monkeypatch.setenv('PUBLIC_LINKEDIN_URL', 'https://www.linkedin.com/company/example')
    source = client.get('/contact').text
    assert 'href="mailto:support@example.test"' in source
    assert 'href="https://www.linkedin.com/company/example"' in source
    monkeypatch.setenv('PUBLIC_CONTACT_EMAIL', 'bad@example.test?bcc=intruder@example.test')
    monkeypatch.setenv('PUBLIC_LINKEDIN_URL', 'javascript:alert(999)')
    monkeypatch.setenv('PUBLIC_GITHUB_URL', 'https://github.com.attacker.test/profile')
    source = client.get('/contact').text
    assert 'mailto:' not in source
    assert 'javascript:alert(999)' not in source
    assert 'github.com.attacker.test' not in source
    assert 'Official social profiles have not been published here' in source


def test_public_mobile_navigation_and_destination_preservation():
    source = TestClient(app).get('/services').text
    assert 'aria-controls="publicNavigation" aria-expanded="false"' in source
    assert 'id="publicNavigation"' in source
    assert "const requestedView=location.hash.slice(1)" in source
    assert "includes(requestedView)?requestedView:'consultation'" in source
    assert "location.pathname==='/'&&!hash" in source
