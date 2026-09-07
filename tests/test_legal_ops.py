"""Legal operations workspace regressions."""

from __future__ import annotations

import uuid
from datetime import date, timedelta

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

    renewal_date = (date.today() + timedelta(days=30)).isoformat()
    contract = client.post(
        "/api/legal-ops/contracts",
        json={"title": "Vendor Mutual NDA", "counterparty": "Vendor Ltd", "contract_type": "nda", "status": "in_review", "risk_level": "high", "matter_id": matter_id, "renewal_date": renewal_date},
        headers=owner_workspace,
    )
    assert contract.status_code == 201
    contract_id = contract.json()["id"]
    assert contract.json()["lifecycle_stage"] == "renewal_due"
    assert contract.json()["reminder_status"] == "due"
    assert 0 <= contract.json()["days_to_renewal"] <= 60

    obligation = client.post(
        "/api/legal-ops/obligations",
        json={
            "contract_id": contract_id,
            "title": "Return confidential material after termination",
            "owner": "Legal operations",
            "priority": "critical",
            "due_date": "2026-09-20",
            "source_clause": "Confidential materials must be returned or destroyed after termination.",
        },
        headers=owner_workspace,
    )
    assert obligation.status_code == 201
    obligation_id = obligation.json()["id"]
    assert obligation.json()["matter_id"] == matter_id
    assert obligation.json()["status"] == "open"

    vendor = client.post(
        "/api/legal-ops/vendors",
        json={"name": "Acme Legal LLP", "practice_area": "Commercial contracts", "hourly_rate": 7500, "currency": "INR"},
        headers=owner_workspace,
    )
    assert vendor.status_code == 201
    vendor_id = vendor.json()["id"]

    spend = client.post(
        "/api/legal-ops/spend",
        json={
            "matter_id": matter_id,
            "vendor_id": vendor_id,
            "invoice_number": "INV-001",
            "description": "NDA negotiation and review",
            "amount": 125000,
            "currency": "INR",
            "due_date": "2026-09-30",
        },
        headers=owner_workspace,
    )
    assert spend.status_code == 201
    spend_id = spend.json()["id"]
    assert spend.json()["status"] == "pending"
    assert spend.json()["matter_id"] == matter_id
    assert spend.json()["vendor_id"] == vendor_id

    playbook = client.post(
        "/api/legal-ops/playbooks",
        json={
            "title": "NDA review checklist",
            "playbook_type": "contract",
            "tags": "nda, confidentiality, vendor",
            "body": "Check mutuality, confidentiality carve-outs, residual knowledge, term length, and escalation for uncapped liability.",
        },
        headers=owner_workspace,
    )
    assert playbook.status_code == 201
    playbook_id = playbook.json()["id"]

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
    assert detail.json()["obligations"][0]["title"] == "Return confidential material after termination"
    assert detail.json()["spend_entries"][0]["invoice_number"] == "INV-001"
    assert detail.json()["playbooks"][0]["title"] == "NDA review checklist"
    assert {item["kind"] for item in detail.json()["activity"]} >= {"document", "note", "task", "contract", "obligation", "intake", "spend"}

    brief = client.post(f"/api/legal-ops/matters/{matter_id}/brief", headers=viewer_workspace)
    assert brief.status_code == 200
    brief_data = brief.json()
    assert brief_data["matter_id"] == matter_id
    assert "Matter Brief" in brief_data["brief"]
    assert "Vendor wants signature this week." in brief_data["brief"]
    assert "Check confidentiality carve-outs" in brief_data["brief"]
    assert "Vendor Mutual NDA" in brief_data["brief"]
    assert "Return confidential material after termination" in brief_data["brief"]
    assert "NDA review checklist" in brief_data["brief"]
    assert "Playbooks are team guidance, not legal authority" in brief_data["brief"]
    assert "not verify legal merits" in brief_data["brief"]
    assert {source["kind"] for source in brief_data["sources"]} >= {"matter", "intake", "note", "task", "contract", "obligation", "document", "playbook"}
    assert brief_data["generated_from"]["documents"] == 1
    assert brief_data["generated_from"]["obligations"] == 1
    assert brief_data["generated_from"]["playbooks"] == 1

    search = client.get("/api/legal-ops/search", params={"q": "Vendor"}, headers=viewer_workspace)
    assert search.status_code == 200
    assert {item["kind"] for item in search.json()["results"]} >= {"matter", "contract", "document"}

    vendor_search = client.get("/api/legal-ops/search", params={"q": "Acme"}, headers=viewer_workspace)
    assert vendor_search.status_code == 200
    assert {item["kind"] for item in vendor_search.json()["results"]} >= {"vendor"}

    invoice_search = client.get("/api/legal-ops/search", params={"q": "INV-001"}, headers=viewer_workspace)
    assert invoice_search.status_code == 200
    assert {item["kind"] for item in invoice_search.json()["results"]} >= {"spend"}

    playbook_search = client.get("/api/legal-ops/search", params={"q": "residual knowledge"}, headers=viewer_workspace)
    assert playbook_search.status_code == 200
    assert {item["kind"] for item in playbook_search.json()["results"]} >= {"playbook"}
    obligation_search = client.get("/api/legal-ops/search", params={"q": "confidential material"}, headers=viewer_workspace)
    assert obligation_search.status_code == 200
    assert {item["kind"] for item in obligation_search.json()["results"]} >= {"obligation"}
    assert client.get("/api/legal-ops/search", params={"q": "x"}, headers=viewer_workspace).status_code == 422

    updated_task = client.patch(f"/api/legal-ops/tasks/{task_id}", json={"status": "done"}, headers=owner_workspace)
    assert updated_task.status_code == 200
    assert updated_task.json()["status"] == "done"

    approved_contract = client.patch(f"/api/legal-ops/contracts/{contract_id}", json={"status": "approved"}, headers=owner_workspace)
    assert approved_contract.status_code == 200
    assert approved_contract.json()["status"] == "approved"
    assert approved_contract.json()["reminder_status"] == "due"

    workspace = client.get("/api/legal-ops/workspace", headers=viewer_workspace)
    assert workspace.status_code == 200
    data = workspace.json()
    assert [item["title"] for item in data["matters"]] == ["Vendor NDA review"]
    assert [item["title"] for item in data["intakes"]] == ["Need NDA review"]
    assert [item["title"] for item in data["tasks"]] == ["Check confidentiality carve-outs"]
    assert [item["title"] for item in data["contracts"]] == ["Vendor Mutual NDA"]
    assert data["summary"]["high_risk_contracts"] == 1
    assert data["summary"]["tasks_by_status"]["done"] == 1
    assert data["summary"]["renewals_due_60_days"] == 1
    assert data["summary"]["pending_signature_contracts"] == 1
    assert data["summary"]["open_contract_obligations"] == 1
    assert data["summary"]["overdue_contract_obligations"] == 0
    assert data["obligations"][0]["id"] == obligation_id
    assert data["contract_reminders"][0]["id"] == contract_id
    assert data["contract_reminders"][0]["reminder_status"] == "due"
    assert data["vendors"][0]["name"] == "Acme Legal LLP"
    assert data["spend_entries"][0]["invoice_number"] == "INV-001"
    assert data["summary"]["open_spend_total"] == 125000
    assert data["summary"]["paid_spend_total"] == 0
    assert data["summary"]["active_playbooks"] == 1
    assert data["playbooks"][0]["title"] == "NDA review checklist"

    report = client.get("/api/legal-ops/report", headers=viewer_workspace)
    assert report.status_code == 200
    report_data = report.json()
    assert report_data["title"] == "Legal Ops Report"
    assert "Executive Snapshot" in report_data["report"]
    assert "Matter Status" in report_data["report"]
    assert "Vendor Spend" in report_data["report"]
    assert "Contractual Obligations" in report_data["report"]
    assert "Playbooks" in report_data["report"]
    assert "Vendor NDA review" in report_data["report"]
    assert "Return confidential material after termination" in report_data["report"]
    assert "Acme Legal LLP" in report_data["report"]
    assert "NDA review checklist" in report_data["report"]
    assert "not legal advice" in report_data["report"]
    assert report_data["generated_from"] == {
        "matters": 1,
        "intakes": 1,
        "tasks": 1,
        "contracts": 1,
        "obligations": 1,
        "vendors": 1,
        "spend_entries": 1,
        "playbooks": 1,
    }
    assert client.get("/api/legal-ops/report", headers=outsider_workspace).status_code == 404

    archived_playbook = client.patch(f"/api/legal-ops/playbooks/{playbook_id}", json={"status": "archived"}, headers=owner_workspace)
    assert archived_playbook.status_code == 200
    assert archived_playbook.json()["status"] == "archived"
    restored_playbook = client.patch(f"/api/legal-ops/playbooks/{playbook_id}", json={"status": "active"}, headers=owner_workspace)
    assert restored_playbook.status_code == 200
    assert restored_playbook.json()["status"] == "active"

    paid_spend = client.patch(f"/api/legal-ops/spend/{spend_id}", json={"status": "paid"}, headers=owner_workspace)
    assert paid_spend.status_code == 200
    assert paid_spend.json()["status"] == "paid"
    assert paid_spend.json()["paid_date"]
    updated_workspace = client.get("/api/legal-ops/workspace", headers=viewer_workspace).json()
    assert updated_workspace["summary"]["open_spend_total"] == 0
    assert updated_workspace["summary"]["paid_spend_total"] == 125000

    completed_obligation = client.patch(f"/api/legal-ops/obligations/{obligation_id}", json={"status": "done"}, headers=owner_workspace)
    assert completed_obligation.status_code == 200
    assert completed_obligation.json()["status"] == "done"
    obligation_workspace = client.get("/api/legal-ops/workspace", headers=viewer_workspace).json()
    assert obligation_workspace["summary"]["open_contract_obligations"] == 0

    assert client.post("/api/legal-ops/playbooks", json={"title": "Forbidden playbook"}, headers=viewer_workspace).status_code == 403
    assert client.patch(f"/api/legal-ops/playbooks/{playbook_id}", json={"status": "archived"}, headers=viewer_workspace).status_code == 403
    assert client.post("/api/legal-ops/vendors", json={"name": "Forbidden Vendor"}, headers=viewer_workspace).status_code == 403
    assert client.post("/api/legal-ops/spend", json={"amount": 10}, headers=viewer_workspace).status_code == 403
    assert client.post("/api/legal-ops/obligations", json={"contract_id": contract_id, "title": "Forbidden obligation"}, headers=viewer_workspace).status_code == 403
    assert client.patch(f"/api/legal-ops/obligations/{obligation_id}", json={"status": "waived"}, headers=viewer_workspace).status_code == 403
    assert client.post("/api/legal-ops/spend", json={"amount": 10, "matter_id": "missing"}, headers=owner_workspace).status_code == 422
    assert client.post("/api/legal-ops/spend", json={"amount": 10, "vendor_id": "missing"}, headers=owner_workspace).status_code == 422
    assert client.post("/api/legal-ops/obligations", json={"contract_id": "missing", "title": "Bad obligation"}, headers=owner_workspace).status_code == 422

    assert client.post("/api/legal-ops/tasks", json={"title": "Forbidden"}, headers=viewer_workspace).status_code == 403
    assert client.patch(f"/api/legal-ops/contracts/{contract_id}", json={"status": "signed"}, headers=viewer_workspace).status_code == 403
    assert client.get("/api/legal-ops/workspace", headers=outsider_workspace).status_code == 404
    assert client.post("/api/legal-ops/tasks", json={"title": "Bad matter", "matter_id": "missing"}, headers=owner_workspace).status_code == 422


def test_legal_ops_intake_can_be_triaged_into_a_matter_once():
    client = TestClient(app)
    owner_headers, _ = _account(client, "legal-intake-owner")
    viewer_headers, viewer_email = _account(client, "legal-intake-viewer")

    created = client.post(
        "/api/organizations",
        json={"name": "Intake Conversion Team", "slug": f"intake-conversion-{uuid.uuid4().hex[:8]}"},
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

    intake = client.post(
        "/api/legal-ops/intake",
        json={"title": "Employee data request", "request_type": "privacy", "summary": "HR needs advice on employee access data.", "urgency": "high"},
        headers=owner_workspace,
    )
    assert intake.status_code == 201
    intake_id = intake.json()["id"]

    assert client.post(f"/api/legal-ops/intake/{intake_id}/convert", json={}, headers=viewer_workspace).status_code == 403

    converted = client.post(
        f"/api/legal-ops/intake/{intake_id}/convert",
        json={"due_date": "2026-09-30"},
        headers=owner_workspace,
    )
    assert converted.status_code == 200
    payload = converted.json()
    matter_id = payload["matter"]["id"]
    assert payload["matter"]["title"] == "Employee data request"
    assert payload["matter"]["matter_type"] == "privacy"
    assert payload["matter"]["priority"] == "high"
    assert payload["matter"]["description"] == "HR needs advice on employee access data."
    assert payload["intake"]["matter_id"] == matter_id
    assert payload["intake"]["status"] == "in_progress"

    repeated = client.post(f"/api/legal-ops/intake/{intake_id}/convert", json={"matter_title": "Should not duplicate"}, headers=owner_workspace)
    assert repeated.status_code == 200
    assert repeated.json()["matter"]["id"] == matter_id

    workspace = client.get("/api/legal-ops/workspace", headers=owner_workspace).json()
    assert [matter["id"] for matter in workspace["matters"]].count(matter_id) == 1
    assert workspace["intakes"][0]["matter_id"] == matter_id
