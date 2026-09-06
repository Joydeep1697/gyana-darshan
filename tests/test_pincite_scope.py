"""Synthetic source attacks: a real section must not validate a false pinpoint."""

import pytest

from app.intelligence.grounding_verdict import assess_grounding


SOURCE = (
    "Section 173(1). Information may be given electronically.\n"
    "Section 173(2). A copy must be supplied."
)
CONTEXT = "AUTHORITATIVE STATUTORY EXCERPTS:\n- BNSS section 173: " + SOURCE


def assess(answer, source=SOURCE):
    return assess_grounding(
        "What does the provision say?", answer, CONTEXT, True, answer,
        [{"id": "synthetic-173", "short_name": "BNSS", "section": "173",
          "country": "India", "integrity_status": "verified", "text": source}],
    )


@pytest.mark.parametrize("answer,source", [
    ('BNSS section 173(2) says "Information may be given electronically".', SOURCE),
    ('Section 173(2) of BNSS says "Information may be given electronically".', SOURCE),
    ('Bharatiya Nagarik Suraksha Sanhita section 173(2) says "Information may be given electronically".', SOURCE),
    ('BNSS section 173(9) applies.', "Section 173(1). The reference to subsection (9) is commentary."),
    ('BNSS section 173(1) and BNSS section 173(9) apply.', SOURCE),
    ('BNSS sections 173(1) and 173(9) apply.', SOURCE),
    ('BNSS section 173(1)(z) applies.', SOURCE),
    ('BNSS section 173(2) applies.', "Section 174(2). A different section applies."),
    ('BNSS section 173(1) says "A copy must be supplied".', SOURCE),
    ('BNSS section 173(1) applies.', "(1) First version.\n(1) Conflicting duplicate."),
    ('BNSS section 173(1) applies.', "Section 174(1). Wrong section.\n(1) Still wrong section."),
    ('BNSS sections 173(1) to 173(2) apply.', SOURCE),
    ('BNSS section 173 (9) applies.', SOURCE),
])
def test_wrong_or_unresolvable_pinpoint_never_receives_verified_status(answer, source):
    verdict = assess(answer, source)
    assert verdict.status != "GROUNDED_AND_VERIFIED"
    item = verdict.evidence_verifications[0]
    assert item.pinpoint_status.value == "MISMATCH" or item.quote_status.value == "MISMATCH"


def test_verified_quote_records_the_exact_subsection_beyond_the_excerpt_limit():
    prefix = "Section 173(1). " + "Background information. " * 60 + "\n"
    subsection = "Section 173(2). A copy must be supplied."
    verdict = assess('BNSS section 173(2) says "A copy must be supplied".', prefix + subsection)
    item = verdict.evidence_verifications[0]
    assert item.pinpoint_status.value == "VERIFIED"
    assert item.quote_status.value == "VERIFIED"
    assert item.evidence_span == subsection


def test_layout_only_changes_preserve_a_valid_scoped_quote():
    verdict = assess(
        'Section 173(2) of BNSS says "A copy must be supplied".',
        "(1) Information may be given electronically.\n(2) A copy must\n be supplied.",
    )
    item = verdict.evidence_verifications[0]
    assert item.pinpoint_status.value == "VERIFIED"
    assert item.quote_status.value == "VERIFIED"
    assert item.evidence_span == "(2) A copy must\n be supplied."


@pytest.mark.parametrize("authenticated", [False, True])
def test_api_never_promotes_wrong_pinpoint_even_when_generator_and_firewall_accept_it(monkeypatch, authenticated):
    """Exercise both production callers; mock upstream trust, keep verdict real."""
    import importlib
    from unittest.mock import AsyncMock
    from uuid import uuid4

    from fastapi.testclient import TestClient
    from app.main import app
    from database.connection import init_db

    module = importlib.import_module("api.conversations.router" if authenticated else "app.main")
    answer = 'BNSS section 173(2) says "Information may be given electronically".'
    pack = {"retrieved_sections": [{
        "id": "synthetic-173", "short_name": "BNSS", "section": "173",
        "country": "India", "integrity_status": "verified", "text": SOURCE,
    }]}
    monkeypatch.setattr(module.retriever, "retrieve_evidence_pack", lambda *a, **kw: pack)
    monkeypatch.setattr(module.retriever, "format_evidence_context", lambda *a: CONTEXT)
    monkeypatch.setattr(module, "generate_grounded_legal_answer", AsyncMock(return_value=answer))
    monkeypatch.setattr(module.firewall, "verify_and_enforce", lambda *a: (True, answer, []))
    client = TestClient(app)
    query = "What does the provision say?"
    if authenticated:
        init_db()
        credentials = {"email": f"pinpoint-{uuid4().hex[:12]}@example.test", "password": "SafeTestPassword2026!"}
        registration = client.post("/api/auth/register", json={**credentials, "full_name": "Pinpoint Test"})
        assert registration.status_code == 201
        login = client.post("/api/auth/login", json=credentials)
        assert login.status_code == 200
        headers = {"Authorization": "Bearer " + login.json()["access_token"]}
        conversation = client.post("/api/conversations", json={"title": "Pinpoint test"}, headers=headers)
        assert conversation.status_code == 201
        response = client.post(
            f"/api/conversations/{conversation.json()['id']}/messages",
            json={"content": query}, headers=headers,
        )
    else:
        response = client.post("/api/v1/query", json={"query": query})
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["grounding_status"] != "GROUNDED_AND_VERIFIED"
    assert payload["review_recommended"] is True
