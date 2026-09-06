"""Legacy metadata must not reintroduce unsupported verification claims."""

import importlib
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from database.connection import init_db
from database.repository import LegalAnswerRepository, MessageRepository


ANSWER = "The accused is guilty (BNSS section 173)."
SOURCE = {"id": "test-173", "short_name": "BNSS", "section": "173", "text": "Synthetic source excerpt."}


def account(client):
    init_db()
    credentials = {"email": f"truth-{uuid4().hex[:12]}@example.test", "password": "SafeTestPassword2026!"}
    assert client.post("/api/auth/register", json={**credentials, "full_name": "Truth State Tester"}).status_code == 201
    login = client.post("/api/auth/login", json=credentials)
    assert login.status_code == 200
    return {"Authorization": "Bearer " + login.json()["access_token"]}


@pytest.mark.parametrize("stored_status", ["GROUNDED_AND_VERIFIED", "AUTO_CORRECTED_BY_FIREWALL", "PARTIALLY_GROUNDED", "INSUFFICIENT_EVIDENCE", "EVIDENCE_CONFLICT"])
def test_history_projects_safe_status_and_review_without_rewriting_the_audit_record(stored_status):
    client = TestClient(app)
    headers = account(client)
    created = client.post("/api/conversations", json={"title": "Legacy truth test"}, headers=headers)
    assert created.status_code == 201
    conv_id = created.json()["id"]
    message = MessageRepository.add_message(conv_id, "assistant", ANSWER)
    LegalAnswerRepository.record_legal_answer(message["id"], stored_status, "PASS", 0, [])
    response = client.get(f"/api/conversations/{conv_id}", headers=headers)
    assert response.status_code == 200
    legal = response.json()["messages"][0]["legal_answer"]
    expected = "EVIDENCE_CONFLICT" if stored_status == "EVIDENCE_CONFLICT" else "INSUFFICIENT_EVIDENCE"
    assert legal["grounding_status"] == expected
    assert legal["recorded_grounding_status"] == stored_status
    assert legal["review_recommended"] is True
    assert legal["review_priority"] == "HIGH"
    assert legal["review_reason"]
    assert MessageRepository.list_conversation_messages(conv_id)[0]["grounding_status"] == stored_status
    other_headers = account(client)
    assert client.get(f"/api/conversations/{conv_id}", headers=other_headers).status_code == 404


def stub_pipeline(monkeypatch, module, records):
    monkeypatch.setattr(module.retriever, "retrieve_evidence_pack", lambda *a, **kw: {"retrieved_sections": records})
    monkeypatch.setattr(module.retriever, "format_evidence_context", lambda *a: "BNSS section 173: Synthetic source.")
    monkeypatch.setattr(module, "generate_grounded_legal_answer", AsyncMock(return_value=ANSWER))
    monkeypatch.setattr(module.firewall, "verify_and_enforce", lambda *a: (True, ANSWER, []))


@pytest.mark.parametrize("entry_point", ["app.main", "api.main"])
@pytest.mark.parametrize("records", [[], [SOURCE]])
def test_public_api_does_not_certify_unverified_provenance(monkeypatch, entry_point, records):
    module = importlib.import_module(entry_point)
    stub_pipeline(monkeypatch, module, records)
    response = TestClient(module.app).post("/api/v1/query", json={"query": "What does the provision say?"})
    assert response.status_code == 200
    assert response.json()["verification_firewall"]["provenance_verified"] is False


def test_legacy_chat_reports_abstention_and_no_fabricated_verification_steps(monkeypatch):
    module = importlib.import_module("app.routers.chat")
    stub_pipeline(monkeypatch, module, [SOURCE])
    client = TestClient(app)
    headers = account(client)
    response = client.post("/api/chat/ask", json={"query": "What does the provision say?"}, headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body.get("grounding_status") == "INSUFFICIENT_EVIDENCE"
    assert body["review_recommended"] is True
    assert body["review_priority"] == "HIGH"
    assert all("verified" not in step["step"].lower() for step in body["reasoning_steps"])
    assert len(body["reasoning_steps"]) == 1
    assert body["reasoning_steps"][0]["ms"] >= 0


@pytest.mark.parametrize("status", ["CLARIFICATION_REQUIRED", "INPUT_NEEDS_CORRECTION"])
def test_history_input_requests_do_not_turn_into_legal_conclusions(status):
    from app.intelligence.grounding_verdict import historical_grounding_verdict
    from app.intelligence.human_review import recommend_human_review
    verdict = historical_grounding_verdict("Please supply the missing facts.", status)
    assert verdict.status == status
    assert not recommend_human_review(verdict).required
