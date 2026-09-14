from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from app.auth.seed_users import create_seed_users
from app.database import Database, get_db
from app.main import app


ROOT = Path(__file__).resolve().parents[1]
TENANT = "personal-test"
MATTER = "test-matter-001"
EXTRACTED = ROOT / "app" / "storage" / "vault" / TENANT / "matters" / MATTER / "extracted.json"


def _fixture() -> Database:
    EXTRACTED.parent.mkdir(parents=True, exist_ok=True)
    if not EXTRACTED.exists():
        EXTRACTED.write_text(json.dumps({"case_no": "CS 123/2024", "next_hearing_date": "2025-12-15", "obligations": [], "provenance_verified": False}, indent=2), encoding="utf-8")
    path = ROOT / ".agent" / "smoke_phase11.sqlite3"
    if path.exists():
        path.unlink()
    db = Database(path)
    now = db.now()
    with db.connect() as conn:
        conn.execute("""INSERT OR REPLACE INTO legal_matters (id, organization_id, title, matter_type, status, priority, description, owner_user_id, due_date, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (MATTER, TENANT, "CS 123/2024", "litigation", "in_review", "medium", "fixture", "u_admin_001", "2025-12-15", now, now))
    return db


def main() -> None:
    create_seed_users()
    before = EXTRACTED.read_bytes() if EXTRACTED.exists() else b""
    db = _fixture()
    manifest = json.loads((ROOT / "frontend" / "public" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["name"] == "Gyana Darshan" and manifest["display"] == "standalone"
    assert "IndexedDB" in (ROOT / "frontend" / "src" / "pwa" / "db.ts").read_text(encoding="utf-8")
    assert "saveMatterToIDB" in (ROOT / "frontend" / "src" / "pwa" / "db.ts").read_text(encoding="utf-8")
    sw = (ROOT / "frontend" / "public" / "service-worker.js").read_text(encoding="utf-8")
    assert "fetch" in sw and "offline" in sw and "queueRequest" in sw
    assert "serviceWorker.register" in (ROOT / "frontend" / "src" / "App.tsx").read_text(encoding="utf-8")

    app.dependency_overrides[get_db] = lambda: db
    try:
        with TestClient(app) as client:
            no_token = client.post("/api/notifications/push-subscribe", json={"subscription": {"endpoint": "stub"}})
            assert no_token.status_code in {401, 403}
            login = client.post("/api/auth/login", json={"email": "admin@test.com", "password": "Test@1234"})
            token = login.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            ok = client.post("/api/notifications/push-subscribe", json={"subscription": {"endpoint": "stub"}}, headers=headers)
            assert ok.status_code == 200, ok.text
            sync = client.get("/api/notifications/sync?since=2025-12-01T00:00:00Z", headers=headers)
            assert sync.status_code == 200 and sync.json()["matters"] == [] and sync.json()["since"]
    finally:
        app.dependency_overrides.clear()
    index = (ROOT / "frontend" / "dist" / "index.html")
    if index.exists():
        assert "manifest" in index.read_text(encoding="utf-8")
    assert EXTRACTED.read_bytes() == before
    assert json.loads(EXTRACTED.read_text(encoding="utf-8"))["provenance_verified"] is False
    print("SMOKE PASSED")


if __name__ == "__main__":
    main()
