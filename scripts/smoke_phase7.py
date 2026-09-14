from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

import app.routers.matters as matters_router
from api.auth.dependencies import get_current_user, get_workspace_context, require_workspace_writer
from app.database import Database, get_db
from app.main import app


ROOT = Path(__file__).resolve().parents[1]
TENANT_ID = "personal-test"
MATTER_ID = "test-matter-001"
MATTER_DIR = ROOT / "app" / "storage" / "vault" / TENANT_ID / "matters" / MATTER_ID
EXTRACTED_PATH = MATTER_DIR / "extracted.json"


def _ensure_vault_fixture() -> None:
    status_path = MATTER_DIR / "obligation_status.json"
    if status_path.exists():
        status_path.unlink()
    MATTER_DIR.mkdir(parents=True, exist_ok=True)
    if not EXTRACTED_PATH.exists():
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
    provenance = MATTER_DIR / "provenance.json"
    if not provenance.exists():
        provenance.write_text(
            json.dumps({"source_hash": "smoke", "extracted_at": "2025-12-01T00:00:00+00:00", "provenance_verified": False}, indent=2),
            encoding="utf-8",
        )


def _insert_matter(db: Database) -> None:
    now = db.now()
    with db.connect() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO legal_matters
               (id, organization_id, title, matter_type, status, priority, description, owner_user_id, due_date, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                MATTER_ID,
                TENANT_ID,
                "CS 123/2024",
                "litigation",
                "in_review",
                "medium",
                "Phase 7 smoke fixture",
                "smoke-user",
                "2025-12-15",
                now,
                now,
            ),
        )


def main() -> None:
    _ensure_vault_fixture()
    before = EXTRACTED_PATH.read_bytes()

    db_path = ROOT / ".agent" / "smoke_phase7.sqlite3"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    db = Database(db_path)
    _insert_matter(db)

    workspace = {"user": {"id": "smoke-user"}, "organization": {"id": TENANT_ID}, "role": "OWNER"}
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: workspace["user"]
    app.dependency_overrides[get_workspace_context] = lambda: workspace
    app.dependency_overrides[require_workspace_writer] = lambda: workspace

    try:
        with TestClient(app) as client:
            chat_response = client.post("/api/chat", json={"query": "When is next hearing for CS 123/2024"})
            assert chat_response.status_code == 200, chat_response.text
            chat_payload = chat_response.json()
            assert "2025-12-15" in chat_payload["answer"], chat_payload
            assert chat_payload["provenance_verified"] is False
            assert any(item["matter_id"] == MATTER_ID for item in chat_payload["citations"]), chat_payload

            matter_response = client.get(f"/api/matters/{MATTER_ID}")
            assert matter_response.status_code == 200, matter_response.text
            matter_payload = matter_response.json()
            assert len(matter_payload["timeline"]) == 2, matter_payload
            assert matter_payload["provenance_verified"] is False

            ics_response = client.get("/api/calendar/ics")
            assert ics_response.status_code == 200
            assert "BEGIN:VEVENT" in ics_response.text
    finally:
        app.dependency_overrides.clear()

    frontend_root = ROOT / "frontend" / "src"
    assert (frontend_root / "components" / "ChatPanel.tsx").is_file()
    assert (frontend_root / "pages" / "MatterDetail.tsx").is_file()
    assert "ChatPanel" in (frontend_root / "components" / "ChatPanel.tsx").read_text(encoding="utf-8")
    assert "MatterDetail" in (frontend_root / "pages" / "MatterDetail.tsx").read_text(encoding="utf-8")
    assert EXTRACTED_PATH.read_bytes() == before
    stored = json.loads(EXTRACTED_PATH.read_text(encoding="utf-8"))
    assert stored["provenance_verified"] is False
    print("SMOKE PASSED")


if __name__ == "__main__":
    main()
