from __future__ import annotations

import json
import shutil
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from app.auth.jwt import create_access_token
from app.auth.seed_users import create_seed_users
from app.auth.middleware import USERS_PATH, load_users
from app.database import Database, get_db
from app.jobs.nudge_scheduler import check_and_nudge
from app.main import app
from app.services.notification_service import LOG_DIR, format_email_html, send_email
from app.services.obligation_tracker import get_upcoming_obligations


ROOT = Path(__file__).resolve().parents[1]
TENANT_ID = "personal-test"
MATTER_ID = "test-matter-001"
MATTER_2_ID = "test-matter-002"
MATTER_DIR = ROOT / "app" / "storage" / "vault" / TENANT_ID / "matters" / MATTER_ID
MATTER_2_DIR = ROOT / "app" / "storage" / "vault" / TENANT_ID / "matters" / MATTER_2_ID
EXTRACTED_PATH = MATTER_DIR / "extracted.json"


def _ensure_users() -> None:
    users = create_seed_users()
    if not any(user.get("tenant_id") == "other-tenant" for user in users):
        other = dict(users[0])
        other.update({"user_id": "u_admin_other", "email": "other@test.com", "tenant_id": "other-tenant", "role": "admin"})
        users.append(other)
        USERS_PATH.write_text(json.dumps(users, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def _token(email: str) -> str:
    user = next(item for item in load_users() if item["email"] == email)
    return create_access_token({"user_id": user["user_id"], "tenant_id": user["tenant_id"], "role": user["role"], "email": user["email"]})


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _ensure_fixture() -> None:
    MATTER_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "case_no": "CS 123/2024",
        "court": "District Court",
        "parties": {"plaintiff": "Asha Rao", "defendant": "Bharat Mehta"},
        "next_hearing_date": "2025-12-15",
        "obligations": [
            {
                "due_date": "2025-12-10",
                "type": "filing_or_compliance",
                "responsible": "Bharat Mehta",
                "description": "File written statement",
            }
        ],
        "risk_flags": [],
        "provenance_verified": False,
    }
    EXTRACTED_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    (MATTER_DIR / "provenance.json").write_text(
        json.dumps({"source_hash": "smoke", "extracted_at": "2025-12-01T00:00:00+00:00", "provenance_verified": False}, indent=2),
        encoding="utf-8",
    )
    status = MATTER_DIR / "obligation_status.json"
    if status.exists():
        status.unlink()


def _create_compare_fixture() -> None:
    MATTER_2_DIR.mkdir(parents=True, exist_ok=True)
    data = json.loads(EXTRACTED_PATH.read_text(encoding="utf-8"))
    data["obligations"][0]["description"] = "File written statement by 10-12-2025 - URGENT indemnify and hold harmless"
    (MATTER_2_DIR / "extracted.json").write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    (MATTER_2_DIR / "provenance.json").write_text(
        json.dumps({"source_hash": "smoke2", "extracted_at": "2025-12-01T00:00:00+00:00", "provenance_verified": False}, indent=2),
        encoding="utf-8",
    )


def _insert_matter(db: Database, matter_id: str, title: str) -> None:
    now = db.now()
    with db.connect() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO legal_matters
               (id, organization_id, title, matter_type, status, priority, description, owner_user_id, due_date, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (matter_id, TENANT_ID, title, "litigation", "in_review", "medium", "Phase 8 smoke fixture", "smoke-user", "2025-12-15", now, now),
        )


def main() -> None:
    _ensure_users()
    _ensure_fixture()
    before = EXTRACTED_PATH.read_bytes()
    if LOG_DIR.exists():
        shutil.rmtree(LOG_DIR)

    db_path = ROOT / ".agent" / "smoke_phase8.sqlite3"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    db = Database(db_path)
    _insert_matter(db, MATTER_ID, "CS 123/2024")

    app.dependency_overrides[get_db] = lambda: db
    try:
        with TestClient(app) as client:
            admin_login = client.post("/api/auth/login", json={"email": "admin@test.com", "password": "Test@1234"})
            assert admin_login.status_code == 200, admin_login.text
            admin_token = admin_login.json()["access_token"]
            assert client.get("/api/matters").status_code in {401, 403}
            matters = client.get("/api/matters", headers=_headers(admin_token))
            assert matters.status_code == 200, matters.text
            assert any(item["id"] == MATTER_ID for item in matters.json())
            wrong_token = _token("other@test.com")
            wrong = client.get(f"/api/matters/{MATTER_ID}", headers=_headers(wrong_token))
            assert wrong.status_code == 403, wrong.text
            viewer_login = client.post("/api/auth/login", json={"email": "viewer@test.com", "password": "Test@1234"})
            assert viewer_login.status_code == 200, viewer_login.text
            viewer_token = viewer_login.json()["access_token"]
            assert client.get("/api/auth/me", headers=_headers(viewer_token)).json()["role"] == "viewer"
            viewer_compare = client.post("/api/matters/compare", headers=_headers(viewer_token), json={"matter_id_a": MATTER_ID, "matter_id_b": MATTER_ID})
            assert viewer_compare.status_code == 403, viewer_compare.text

            upcoming = get_upcoming_obligations(TENANT_ID, days=9, today=date(2025, 12, 1))
            assert len(upcoming) == 1 and upcoming[0]["due_date"] == "2025-12-10", upcoming
            digest = {
                "date": "2025-12-01",
                "upcoming_hearings": [],
                "upcoming_obligations": upcoming,
                "overdue": [],
                "provenance_verified": False,
            }
            assert send_email("test@example.com", "Digest", format_email_html(digest))["sent"] is True
            assert "CS 123/2024" in (LOG_DIR / "email.log").read_text(encoding="utf-8")
            assert "2025-12-10" in (LOG_DIR / "email.log").read_text(encoding="utf-8")
            nudges = check_and_nudge(TENANT_ID, today=date(2025, 12, 8))
            assert len(nudges) == 1, nudges
            assert (ROOT / "app" / "storage" / "vault" / TENANT_ID / "notifications" / "2025-12-08.jsonl").exists()

            _create_compare_fixture()
            _insert_matter(db, MATTER_2_ID, "CS 123/2024 revised")
            compare = client.post("/api/matters/compare", headers=_headers(admin_token), json={"matter_id_a": MATTER_ID, "matter_id_b": MATTER_2_ID})
            assert compare.status_code == 200, compare.text
            diff = compare.json()
            assert diff["provenance_verified"] is False
            assert diff["changed"] or diff["added"], diff
            risk = client.post(f"/api/matters/{MATTER_2_ID}/risk-scan", headers=_headers(admin_token))
            assert risk.status_code == 200, risk.text
            risks = risk.json()["risks"]
            assert any(item["type"] == "indemnity" and item["severity"] == "high" and "indemnify" in item["matched_text"] for item in risks), risks
            summary = client.get("/api/risks/summary", headers=_headers(admin_token))
            assert summary.status_code == 200 and summary.json()["total_matters"] >= 1
    finally:
        app.dependency_overrides.clear()
        if MATTER_2_DIR.exists():
            shutil.rmtree(MATTER_2_DIR)

    assert EXTRACTED_PATH.read_bytes() == before
    assert json.loads(EXTRACTED_PATH.read_text(encoding="utf-8"))["provenance_verified"] is False
    print("SMOKE PASSED")


if __name__ == "__main__":
    main()
