from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from app.auth.seed_users import create_seed_users
from app.database import Database, get_db
from app.main import app
from app.services.clause_llm import analyze_clause_with_llm
from app.services.obligation_extractor_v2 import extract_obligations_v2
from app.services.redline_service import generate_redline


ROOT = Path(__file__).resolve().parents[1]
TENANT = "personal-test"
MATTER = "test-matter-001"
MATTER_DIR = ROOT / "app" / "storage" / "vault" / TENANT / "matters" / MATTER
EXTRACTED = MATTER_DIR / "extracted.json"


def _fixture() -> None:
    MATTER_DIR.mkdir(parents=True, exist_ok=True)
    EXTRACTED.write_text(json.dumps({
        "case_no": "CS 123/2024",
        "court": "District Court",
        "parties": {"plaintiff": "Asha Rao", "defendant": "Bharat Mehta"},
        "next_hearing_date": "2025-12-15",
        "obligations": [{"due_date": "2025-12-10", "type": "filing_or_compliance", "responsible": "Bharat Mehta", "description": "The party shall indemnify and hold harmless against unlimited liability and auto-renew for 5 years"}],
        "risk_flags": [],
        "provenance_verified": False,
    }, indent=2, sort_keys=True), encoding="utf-8")


def _db() -> Database:
    path = ROOT / ".agent" / "smoke_phase10.sqlite3"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    db = Database(path)
    now = db.now()
    with db.connect() as conn:
        conn.execute("""INSERT OR REPLACE INTO legal_matters (id, organization_id, title, matter_type, status, priority, description, owner_user_id, due_date, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (MATTER, TENANT, "CS 123/2024", "litigation", "in_review", "medium", "fixture", "u_admin_001", "2025-12-15", now, now))
    return db


def main() -> None:
    create_seed_users()
    _fixture()
    before = EXTRACTED.read_bytes()
    clause = "The party shall indemnify and hold harmless against unlimited liability and auto-renew for 5 years"
    llm = analyze_clause_with_llm(clause, {"case_no": "CS 123/2024", "court": "District Court"})
    assert llm["provenance_verified"] is False and "risk_score" in llm and llm["risks"], llm
    redline = generate_redline(clause, {"type": "indemnity"})
    assert "direct damages" in redline["suggested"] or "limited" in redline["suggested"], redline
    obligations = extract_obligations_v2("File written statement by 15 Dec 2025")
    assert obligations and obligations[0]["due_date"] == "2025-12-15", obligations

    db = _db()
    app.dependency_overrides[get_db] = lambda: db
    try:
        with TestClient(app) as client:
            login = client.post("/api/auth/login", json={"email": "admin@test.com", "password": "Test@1234"})
            assert login.status_code == 200, login.text
            headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
            analyze = client.post(f"/api/intelligence/matter/{MATTER}/analyze", json={"use_llm": True}, headers=headers)
            assert analyze.status_code == 200, analyze.text
            assert any(risk["type"] == "indemnity" for risk in analyze.json()["combined_risks"]), analyze.json()
            post_redline = client.post(f"/api/intelligence/matter/{MATTER}/redline", headers=headers)
            assert post_redline.status_code == 200, post_redline.text
            got_redline = client.get(f"/api/intelligence/matter/{MATTER}/redline", headers=headers)
            assert got_redline.status_code == 200 and got_redline.json()["redlines"], got_redline.text
    finally:
        app.dependency_overrides.clear()

    assert (MATTER_DIR / "risk_scan_llm.json").exists()
    assert json.loads((MATTER_DIR / "risk_scan_llm.json").read_text(encoding="utf-8"))["provenance_verified"] is False
    assert (MATTER_DIR / "redlines.json").exists()
    assert EXTRACTED.read_bytes() == before
    assert json.loads(EXTRACTED.read_text(encoding="utf-8"))["provenance_verified"] is False
    print("SMOKE PASSED")


if __name__ == "__main__":
    main()
