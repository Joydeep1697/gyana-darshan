"""Generator identity and firewall success are not independent claim evidence."""

import importlib
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.intelligence.grounding_verdict import (
    ClaimCriticality, ClaimStatus, ClaimVerdict, GroundingVerdict, assess_grounding,
)
from app.intelligence.human_review import recommend_human_review


QUERY = "What does this provision establish?"
SOURCE = {
    "id": "synthetic-bnss-173", "short_name": "BNSS", "section": "173",
    "country": "India", "integrity_status": "verified",
    "text": "Information may be given by electronic communication.",
}
CONTEXT = "AUTHORITATIVE STATUTORY EXCERPTS:\n- BNSS section 173: " + SOURCE["text"]
ATTACKS = (
    "An electronic FIR is always conclusive proof of guilt (BNSS section 173).",
    "Every electronic FIR requires automatic acquittal (BNSS section 173).",
    "The accused must pay a fine of 999999 rupees (BNSS section 173).",
    "An electronic FIR is unlawful (BNSS section 173).",
    'The provision permits electronic information and proves guilt: "Information may be given by electronic communication" (BNSS section 173).',
)


@pytest.mark.parametrize("answer", ATTACKS)
def test_generator_template_identity_cannot_verify_a_false_proposition(answer):
    verdict = assess_grounding(QUERY, answer, CONTEXT, True, answer, [SOURCE])
    assert verdict.status == "INSUFFICIENT_EVIDENCE"
    assert verdict.citation_coverage == 1.0
    assert verdict.citation_completeness == 0.0
    assert all(claim.status == ClaimStatus.INSUFFICIENT_EVIDENCE for claim in verdict.claims)
    assert all(record.proposition_status == ClaimStatus.INSUFFICIENT_EVIDENCE for record in verdict.evidence_verifications)
    assert recommend_human_review(verdict).required


def test_generator_identity_does_not_change_any_verification_result():
    answer = ATTACKS[0]
    baseline = assess_grounding(QUERY, answer, CONTEXT, True, None, [SOURCE])
    assert assess_grounding(QUERY, answer, CONTEXT, True, answer, [SOURCE]) == baseline
    assert assess_grounding(QUERY, answer, CONTEXT, True, "another template", [SOURCE]) == baseline


def test_citation_in_context_without_retrieved_record_is_not_proof_or_coverage():
    verdict = assess_grounding(QUERY, ATTACKS[0], CONTEXT, True, ATTACKS[0], [])
    assert verdict.status == "INSUFFICIENT_EVIDENCE"
    assert verdict.citation_coverage == 0.0
    assert verdict.claims[0].status == ClaimStatus.UNSUPPORTED


def test_verified_label_cannot_suppress_review_of_unsupported_claims():
    critical = ClaimVerdict("The accused is guilty.", ClaimStatus.UNSUPPORTED, (), ClaimCriticality.CRITICAL)
    review = recommend_human_review(GroundingVerdict("GROUNDED_AND_VERIFIED", (critical,)))
    assert review.required and review.priority == "HIGH"
    assert recommend_human_review(GroundingVerdict("GROUNDED_AND_VERIFIED", ())).required


@pytest.mark.parametrize("entry_point", ["app.main", "api.main", "api.conversations.router"])
def test_each_api_requires_independent_proof_and_preserves_the_abstention_in_history(monkeypatch, entry_point):
    from fastapi.testclient import TestClient
    from app.main import app
    from database.connection import init_db

    module = importlib.import_module(entry_point)
    answer = ATTACKS[0]
    pack = {"retrieved_sections": [SOURCE]}
    monkeypatch.setattr(module.retriever, "retrieve_evidence_pack", lambda *a, **kw: pack)
    monkeypatch.setattr(module.retriever, "format_evidence_context", lambda *a: CONTEXT)
    generator = AsyncMock(return_value=answer)
    monkeypatch.setattr(module, "generate_grounded_legal_answer", generator)
    monkeypatch.setattr(module.firewall, "verify_and_enforce", lambda *a: (True, answer, []))
    # Legacy callers previously regenerated the answer and trusted equality.
    if hasattr(module, "deterministic_answer_for_evidence"):
        monkeypatch.setattr(module, "deterministic_answer_for_evidence", lambda *a: answer)
    client = TestClient(module.app if entry_point == "api.main" else app)
    authenticated = entry_point == "api.conversations.router"
    if authenticated:
        init_db()
        credentials = {"email": f"proof-{uuid4().hex[:12]}@example.test", "password": "SafeTestPassword2026!"}
        assert client.post("/api/auth/register", json={**credentials, "full_name": "Proof Test"}).status_code == 201
        login = client.post("/api/auth/login", json=credentials)
        assert login.status_code == 200
        headers = {"Authorization": "Bearer " + login.json()["access_token"]}
        created = client.post("/api/conversations", json={"title": "Proof test"}, headers=headers)
        assert created.status_code == 201
        path = f"/api/conversations/{created.json()['id']}"
        response = client.post(path + "/messages", json={"content": QUERY}, headers=headers)
    else:
        response = client.post("/api/v1/query", json={"query": QUERY})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["answer"] == answer
    assert body["grounding_status"] == "INSUFFICIENT_EVIDENCE"
    assert body["review_recommended"] is True
    assert body["review_priority"] == "HIGH"
    generator.assert_awaited_once()
    if authenticated:
        history = client.get(path, headers=headers)
        assert history.status_code == 200
        assistant = next(message for message in history.json()["messages"] if message["role"] == "assistant")
        assert assistant["legal_answer"]["grounding_status"] == body["grounding_status"]
