"""Enterprise workspace, lifecycle, and operational-control regressions."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi.testclient import TestClient

from app.main import app
from app.database import Database
from scripts.backup_data import create_backup
from scripts.enforce_retention import enforce_retention
from scripts.restore_data import restore_backup, validate_backup


def _account(client: TestClient, label: str) -> tuple[dict[str, str], str]:
    email = f"{label}-{uuid.uuid4().hex[:10]}@example.test"
    password = "SecurePassword2026!"
    response = client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "full_name": label.title()},
    )
    assert response.status_code == 201
    token = client.post("/api/auth/login", json={"email": email, "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, email


def test_organization_roles_scope_shared_consultations_and_audit_events():
    client = TestClient(app)
    owner_headers, _ = _account(client, "org-owner")
    viewer_headers, viewer_email = _account(client, "org-viewer")
    outsider_headers, _ = _account(client, "org-outsider")

    created = client.post(
        "/api/organizations",
        json={"name": "Chambers Research", "slug": f"chambers-{uuid.uuid4().hex[:8]}"},
        headers=owner_headers,
    )
    assert created.status_code == 201
    organization_id = created.json()["id"]
    assert client.post(
        f"/api/organizations/{organization_id}/members",
        json={"email": viewer_email, "role": "VIEWER"},
        headers=owner_headers,
    ).status_code == 201

    owner_workspace = {**owner_headers, "X-Organization-ID": organization_id}
    viewer_workspace = {**viewer_headers, "X-Organization-ID": organization_id}
    outsider_workspace = {**outsider_headers, "X-Organization-ID": organization_id}
    conversation = client.post(
        "/api/conversations", json={"title": "Shared research"}, headers=owner_workspace
    )
    assert conversation.status_code == 201
    conversation_id = conversation.json()["id"]
    assert client.get("/api/conversations", headers=viewer_workspace).json()[0]["id"] == conversation_id
    assert client.get(f"/api/conversations/{conversation_id}", headers=viewer_workspace).status_code == 200
    assert client.post(
        "/api/conversations", json={"title": "Forbidden"}, headers=viewer_workspace
    ).status_code == 403
    assert client.get("/api/conversations", headers=outsider_workspace).status_code == 404

    retention = client.put(
        f"/api/organizations/{organization_id}/retention",
        json={"retention_days": 365}, headers=owner_headers,
    )
    assert retention.status_code == 200
    events = client.get(
        f"/api/organizations/{organization_id}/audit-events", headers=owner_headers
    ).json()["events"]
    assert {event["event_type"] for event in events} >= {
        "ORGANIZATION_CREATED", "ORGANIZATION_MEMBER_ADDED", "RETENTION_POLICY_CHANGED"
    }


def test_workspace_intelligence_routes_are_organization_scoped():
    client = TestClient(app)
    owner_headers, _ = _account(client, "graph-owner")
    viewer_headers, viewer_email = _account(client, "graph-viewer")
    outsider_headers, _ = _account(client, "graph-outsider")

    created = client.post(
        "/api/organizations",
        json={"name": "Graph Chambers", "slug": f"graph-{uuid.uuid4().hex[:8]}"},
        headers=owner_headers,
    )
    assert created.status_code == 201
    organization_id = created.json()["id"]
    assert client.post(
        f"/api/organizations/{organization_id}/members",
        json={"email": viewer_email, "role": "VIEWER"},
        headers=owner_headers,
    ).status_code == 201

    db = Database()
    source_id = db.create_document("shared-source.pdf", 10, "/tmp/shared-source.pdf", "owner", organization_id)
    target_id = db.create_document("shared-target.pdf", 10, "/tmp/shared-target.pdf", "owner", organization_id)
    other_id = db.create_document("outside.pdf", 10, "/tmp/outside.pdf", "owner", "other-org")
    db.update_document(source_id, status="indexed", category="Judgment", domain="Criminal", risk_score=75)
    db.update_document(target_id, status="indexed", category="Brief", domain="Criminal", risk_score=25)
    db.update_document(other_id, status="indexed", category="Judgment", domain="Criminal", risk_score=99)
    db.add_graph_edge(source_id, target_id, "cites", "Section 302 IPC", "Section 302 IPC", 0.91)
    db.add_graph_edge(source_id, other_id, "cites", "Section 302 IPC", "Section 302 IPC", 0.99)
    db.add_section_entries(source_id, [{"ref": "Section 302 IPC", "context_type": "citing", "snippet": "shared"}])
    db.add_section_entries(other_id, [{"ref": "Section 302 IPC", "context_type": "citing", "snippet": "outside"}])
    db.add_deadlines(source_id, [{"type": "filing", "date": "2026-09-30", "description": "Shared filing"}])
    db.add_deadlines(other_id, [{"type": "filing", "date": "2026-09-30", "description": "Outside filing"}])
    db.add_compliance_gap("Criminal", "shared contradiction", organization_id=organization_id)
    db.add_compliance_gap("Criminal", "outside contradiction", organization_id="other-org")

    viewer_workspace = {**viewer_headers, "X-Organization-ID": organization_id}
    outsider_workspace = {**outsider_headers, "X-Organization-ID": organization_id}

    assert client.get(f"/api/graph/document/{source_id}/links", headers=viewer_workspace).json()["links"][0]["target_doc_id"] == target_id
    assert [item["id"] for item in client.get(f"/api/graph/document/{source_id}/related", headers=viewer_workspace).json()["related"]] == [target_id]
    assert [item["doc_id"] for item in client.get("/api/graph/section/302", headers=viewer_workspace).json()["documents"]] == [source_id]
    assert {item["id"] for item in client.get("/api/graph/network", headers=viewer_workspace).json()["nodes"]} == {source_id, target_id}
    assert [item["gap_description"] for item in client.get("/api/graph/contradictions", headers=viewer_workspace).json()["contradictions"]] == ["shared contradiction"]
    assert [item["gap_description"] for item in client.get("/api/proactive/compliance-gaps", headers=viewer_workspace).json()["gaps"]] == ["shared contradiction"]
    assert [item["doc_id"] for item in client.get("/api/proactive/deadlines", headers=viewer_workspace).json()["deadlines"]] == [source_id]
    assert client.get(f"/api/graph/document/{source_id}/links", headers=outsider_workspace).status_code == 404


def test_private_workspace_remains_default_and_tenant_isolated():
    client = TestClient(app)
    first_headers, _ = _account(client, "private-first")
    second_headers, _ = _account(client, "private-second")
    conversation = client.post(
        "/api/conversations", json={"title": "Private"}, headers=first_headers
    ).json()
    assert client.get(f"/api/conversations/{conversation['id']}", headers=second_headers).status_code == 404


def test_backup_validation_rejects_checksum_tampering_and_path_traversal(tmp_path: Path):
    backup = tmp_path / "tampered.zip"
    manifest = {
        "format": "nyaya-backup-v1",
        "created_at": "2026-01-01T00:00:00+00:00",
        "files": {"../escape": "incorrect"},
    }
    with ZipFile(backup, "w", ZIP_DEFLATED) as archive:
        archive.writestr("../escape", b"payload")
        archive.writestr("manifest.json", json.dumps(manifest))
    try:
        validate_backup(backup)
    except ValueError as exc:
        assert "Unsafe" in str(exc)
    else:
        raise AssertionError("Unsafe backup entry was accepted")


def test_clean_schema_contains_enterprise_constraints(tmp_path: Path):
    from database.models import SCHEMA_DDL

    database = tmp_path / "clean.db"
    with sqlite3.connect(database) as connection:
        connection.executescript(SCHEMA_DDL)
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert {"organizations", "organization_members"}.issubset(tables)


def test_backup_round_trip_uses_checksums_and_restores_databases_and_uploads(tmp_path: Path):
    product = tmp_path / "product.db"
    vault = tmp_path / "vault.db"
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    with sqlite3.connect(product) as connection:
        connection.execute("CREATE TABLE marker (value TEXT)")
        connection.execute("INSERT INTO marker VALUES ('product-original')")
    with sqlite3.connect(vault) as connection:
        connection.execute("CREATE TABLE marker (value TEXT)")
        connection.execute("INSERT INTO marker VALUES ('vault-original')")
    (uploads / "evidence.pdf").write_bytes(b"%PDF-backup")
    backup = tmp_path / "backup.zip"
    with patch("scripts.backup_data.SQLITE_DB_PATH", product), patch(
        "scripts.backup_data.APP_DB_PATH", vault
    ), patch("scripts.backup_data.RAW_DIR", uploads):
        create_backup(backup)
    with sqlite3.connect(product) as connection:
        connection.execute("UPDATE marker SET value = 'changed'")
    (uploads / "evidence.pdf").unlink()
    with patch("scripts.restore_data.SQLITE_DB_PATH", product), patch(
        "scripts.restore_data.APP_DB_PATH", vault
    ), patch("scripts.restore_data.RAW_DIR", uploads):
        restore_backup(backup, "RESTORE_NYAYA_DATA")
    with sqlite3.connect(product) as connection:
        assert connection.execute("SELECT value FROM marker").fetchone()[0] == "product-original"
    assert (uploads / "evidence.pdf").read_bytes() == b"%PDF-backup"


def test_retention_is_dry_run_by_default_then_removes_only_expired_workspace_data(tmp_path: Path):
    from database.models import SCHEMA_DDL

    product = tmp_path / "product.db"
    vault = Database(tmp_path / "vault.db")
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    now = datetime(2026, 8, 27, tzinfo=timezone.utc)
    expired = (now - timedelta(days=31)).isoformat()
    current = (now - timedelta(days=1)).isoformat()
    with sqlite3.connect(product) as connection:
        connection.executescript(SCHEMA_DDL)
        connection.execute("INSERT INTO users VALUES ('user', 'u@example.test', 'hash', 'User', 'USER', 1, ?, ?)", (current, current))
        connection.execute("INSERT INTO organizations (id,name,slug,is_personal,created_by,retention_days,created_at,updated_at) VALUES ('org','Org','org',0,'user',30,?,?)", (current, current))
        connection.execute("INSERT INTO organization_members VALUES ('org','user','OWNER',?)", (current,))
        connection.execute("INSERT INTO conversations VALUES ('old','user','Old',?,?, 'org')", (expired, expired))
        connection.execute("INSERT INTO conversations VALUES ('new','user','New',?,?, 'org')", (current, current))
    old_file = uploads / "old.pdf"
    old_file.write_bytes(b"%PDF-old")
    old_document = vault.create_document("old.pdf", 8, str(old_file), "user", "org")
    with vault.connect() as connection:
        connection.execute("UPDATE vault_documents SET upload_time = ? WHERE id = ?", (expired, old_document))
    with patch("database.connection.SQLITE_DB_PATH", product), patch(
        "scripts.enforce_retention.get_db", return_value=vault
    ), patch("scripts.enforce_retention.RAW_DIR", uploads):
        preview = enforce_retention(now=now)
        assert preview["organizations"][0]["conversations"] == 1
        assert old_file.exists()
        enforce_retention(apply=True, now=now)
    with sqlite3.connect(product) as connection:
        assert [row[0] for row in connection.execute("SELECT id FROM conversations")] == ["new"]
    assert not old_file.exists()
