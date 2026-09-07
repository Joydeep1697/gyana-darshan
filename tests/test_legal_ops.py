"""Legal operations workspace regressions."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from app.main import app


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


def test_legal_ops_workspace_covers_matter_intake_tasks_contracts_and_reports():
    client = TestClient(app)
    owner_headers, _ = _account(client, "legal-ops-owner")
    viewer_headers, viewer_email = _account(client, "legal-ops-viewer")
    outsider_headers, _ = _account(client, "legal-ops-outsider")

    created = client.post(
        "/api/organizations",
        json={"name": "Legal Ops Team", "slug": f"legal-ops-{uuid.uuid4().hex[:8]}"},
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

    matter = client.post(
        "/api/legal-ops/matters",
        json={"title": "Vendor NDA review", "matter_type": "contract", "priority": "high", "description": "Review incoming vendor NDA."},
        headers=owner_workspace,
    )
    assert matter.status_code == 201
    matter_id = matter.json()["id"]

    intake = client.post(
        "/api/legal-ops/intake",
        json={"title": "Need NDA review", "request_type": "contract_review", "summary": "Vendor wants signature this week.", "urgency": "critical", "matter_id": matter_id},
        headers=owner_workspace,
    )
    assert intake.status_code == 201
    assert intake.json()["matter_id"] == matter_id

    task = client.post(
        "/api/legal-ops/tasks",
        json={"title": "Check confidentiality carve-outs", "priority": "high", "matter_id": matter_id, "due_date": "2026-09-10"},
        headers=owner_workspace,
    )
    assert task.status_code == 201
    task_id = task.json()["id"]

    contract = client.post(
        "/api/legal-ops/contracts",
        json={"title": "Vendor Mutual NDA", "counterparty": "Vendor Ltd", "contract_type": "nda", "status": "in_review", "risk_level": "high", "matter_id": matter_id, "renewal_date": "2026-10-01"},
        headers=owner_workspace,
    )
    assert contract.status_code == 201

    from app.database import Database

    db = Database()
    document_id = db.create_document("Vendor NDA.pdf", 10, "/tmp/vendor-nda.pdf", "owner", organization_id)
    db.update_document(document_id, status="indexed", category="Contract", domain="Commercial", summary="Vendor confidentiality agreement")
    other_document_id = db.create_document("Other NDA.pdf", 10, "/tmp/other-nda.pdf", "owner", "other-org")
    db.update_document(other_document_id, status="indexed", category="Contract", domain="Commercial")

    assert client.post(
        f"/api/legal-ops/matters/{matter_id}/documents",
        json={"document_id": document_id},
        headers=owner_workspace,
    ).status_code == 201
    assert client.post(
        f"/api/legal-ops/matters/{matter_id}/documents",
        json={"document_id": other_document_id},
        headers=owner_workspace,
    ).status_code == 422
    note = client.post(
        f"/api/legal-ops/matters/{matter_id}/notes",
        json={"body": "Client prefers a mutual NDA and standard carve-outs."},
        headers=owner_workspace,
    )
    assert note.status_code == 201

    detail = client.get(f"/api/legal-ops/matters/{matter_id}", headers=viewer_workspace)
    assert detail.status_code == 200
    assert detail.json()["documents"][0]["filename"] == "Vendor NDA.pdf"
    assert detail.json()["notes"][0]["body"].startswith("Client prefers")
    assert detail.json()["tasks"][0]["id"] == task_id
    assert detail.json()["contracts"][0]["title"] == "Vendor Mutual NDA"

    search = client.get("/api/legal-ops/search", params={"q": "Vendor"}, headers=viewer_workspace)
    assert search.status_code == 200
    assert {item["kind"] for item in search.json()["results"]} >= {"matter", "contract", "document"}
    assert client.get("/api/legal-ops/search", params={"q": "x"}, headers=viewer_workspace).status_code == 422

    updated_task = client.patch(f"/api/legal-ops/tasks/{task_id}", json={"status": "done"}, headers=owner_workspace)
    assert updated_task.status_code == 200
    assert updated_task.json()["status"] == "done"

    workspace = client.get("/api/legal-ops/workspace", headers=viewer_workspace)
    assert workspace.status_code == 200
    data = workspace.json()
    assert [item["title"] for item in data["matters"]] == ["Vendor NDA review"]
    assert [item["title"] for item in data["intakes"]] == ["Need NDA review"]
    assert [item["title"] for item in data["tasks"]] == ["Check confidentiality carve-outs"]
    assert [item["title"] for item in data["contracts"]] == ["Vendor Mutual NDA"]
    assert data["summary"]["high_risk_contracts"] == 1
    assert data["summary"]["tasks_by_status"]["done"] == 1

    assert client.post("/api/legal-ops/tasks", json={"title": "Forbidden"}, headers=viewer_workspace).status_code == 403
    assert client.get("/api/legal-ops/workspace", headers=outsider_workspace).status_code == 404
    assert client.post("/api/legal-ops/tasks", json={"title": "Bad matter", "matter_id": "missing"}, headers=owner_workspace).status_code == 422
