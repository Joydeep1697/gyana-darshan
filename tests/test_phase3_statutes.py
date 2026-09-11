from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


def _token(client: TestClient) -> str:
    email = "phase3-statutes@example.test"
    password = "SecurePassword2026!"
    client.post("/api/auth/register", json={"email": email, "password": password, "full_name": "Phase 3 Statutes"})
    return client.post("/api/auth/login", json={"email": email, "password": password}).json()["access_token"]


def test_phase3_full_statute_and_evidence_corpus_exists():
    assert len(list(Path("corpus_integrity/bns").glob("section_*.md"))) > 100
    assert len(list(Path("corpus_integrity/bnss").glob("section_*.md"))) > 100
    assert len(list(Path("corpus_integrity/bsa").glob("section_*.md"))) > 100
    assert Path("corpus_integrity/egazette/browser_check_egazette.html").exists()
    assert Path("corpus_integrity/egazette/evidence.md").exists()
    assert Path("corpus_integrity/prs/browser_check_prs.html").exists()
    assert Path("corpus_integrity/prs/evidence.md").exists()


def test_phase3_retrieval_returns_bnss_and_egazette_with_honest_provenance():
    client = TestClient(app)
    token = _token(client)

    bnss = client.post(
        "/api/retrieval/search",
        json={"query": "BNSS 35", "top_k": 5},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert bnss.status_code == 200
    bnss_results = bnss.json()["results"]
    assert any(result["file_path"].endswith("corpus_integrity/bnss/section_035.md") for result in bnss_results)
    assert all(result["provenance_verified"] is False for result in bnss_results if "corpus_integrity/bnss/" in result["file_path"])

    egazette = client.post(
        "/api/retrieval/search",
        json={"query": "eGazette 2024", "top_k": 5},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert egazette.status_code == 200
    egazette_results = egazette.json()["results"]
    evidence = [result for result in egazette_results if result["file_path"].endswith("corpus_integrity/egazette/evidence.md")]
    assert evidence
    assert evidence[0]["fetched_with"] == "needs_human_action"
    assert evidence[0]["provenance_verified"] is False

