from fastapi.testclient import TestClient

from app.main import app


def test_bns_103_search_returns_jsonl_fallback_provenance():
    client = TestClient(app)
    email = "retrieval-provenance@example.test"
    password = "SecurePassword2026!"
    client.post("/api/auth/register", json={"email": email, "password": password, "full_name": "Retrieval Provenance"})
    token = client.post("/api/auth/login", json={"email": email, "password": password}).json()["access_token"]

    response = client.post(
        "/api/retrieval/search",
        json={"query": "BNS 103 Bharatiya Nyaya Sanhita murder", "top_k": 10},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    results = response.json()["results"]
    assert results
    first = results[0]
    assert first["file_path"].endswith("corpus_integrity/bns/section_103.md")
    assert first["fetched_with"] == "jsonl_fallback"
    assert first["provenance_verified"] is False
    assert "murder" in first["text"].lower()
