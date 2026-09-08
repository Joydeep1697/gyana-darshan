"""Legal operations workspace regressions."""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from io import BytesIO
from zipfile import ZipFile

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
    member_snapshot = client.get("/api/legal-ops/workspace", headers=owner_workspace)
    assert member_snapshot.status_code == 200
    members_by_email = {member["email"]: member for member in member_snapshot.json()["members"]}
    viewer_user_id = members_by_email[viewer_email]["id"]
    owner_user_id = next(member["id"] for member in member_snapshot.json()["members"] if member["role"] == "OWNER")

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

    invalid_assignee = client.post(
        "/api/legal-ops/tasks",
        json={"title": "Bad assignee", "assignee_user_id": "not-a-workspace-member"},
        headers=owner_workspace,
    )
    assert invalid_assignee.status_code == 422

    task = client.post(
        "/api/legal-ops/tasks",
        json={"title": "Check confidentiality carve-outs", "priority": "high", "matter_id": matter_id, "assignee_user_id": viewer_user_id, "due_date": "2026-09-10"},
        headers=owner_workspace,
    )
    assert task.status_code == 201
    task_id = task.json()["id"]
    assert task.json()["assignee_user_id"] == viewer_user_id
    assert task.json()["assignee_email"] == viewer_email
    assert task.json()["assignee_name"] == "Legal-Ops-Viewer"

    undated_task = client.post(
        "/api/legal-ops/tasks",
        json={"title": "Confirm signature owner", "priority": "critical", "matter_id": matter_id, "assignee_user_id": viewer_user_id},
        headers=owner_workspace,
    )
    assert undated_task.status_code == 201
    undated_task_id = undated_task.json()["id"]

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
    db.add_deadlines(document_id, [{"type": "response_deadline", "date": "2026-09-25", "description": "File NDA redline response."}])
    precedent_record = db.upsert_case_law_record(
        organization_id,
        document_id,
        {
            "title": "Vendor Confidentiality Authority v State",
            "citation": "2026 ND 42",
            "court": "Supreme Court of India",
            "year": 2026,
            "source_excerpt": "Confidential information obligations must be interpreted against the recorded contractual undertaking.",
        },
    )
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
        json={"body": "Client prefers a mutual NDA and standard carve-outs.", "link_kind": "task", "link_source_id": task_id},
        headers=owner_workspace,
    )
    assert note.status_code == 201
    assert note.json()["author_name"] == "Legal-Ops-Owner"
    assert note.json()["link_kind"] == "task"
    assert note.json()["link_source_id"] == task_id
    assert client.post(
        f"/api/legal-ops/matters/{matter_id}/notes",
        json={"body": "Invalid linked note", "link_kind": "unsupported"},
        headers=owner_workspace,
    ).status_code == 422

    detail = client.get(f"/api/legal-ops/matters/{matter_id}", headers=viewer_workspace)
    assert detail.status_code == 200
    assert detail.json()["documents"][0]["filename"] == "Vendor NDA.pdf"
    assert detail.json()["notes"][0]["body"].startswith("Client prefers")
    assert detail.json()["notes"][0]["author_name"] == "Legal-Ops-Owner"
    assert detail.json()["notes"][0]["link_kind"] == "task"
    assert detail.json()["notes"][0]["link_source_id"] == task_id
    detail_tasks = {item["id"]: item for item in detail.json()["tasks"]}
    assert detail_tasks[task_id]["assignee_user_id"] == viewer_user_id
    assert detail_tasks[task_id]["assignee_email"] == viewer_email
    assert detail_tasks[undated_task_id]["assignee_user_id"] == viewer_user_id
    assert detail.json()["contracts"][0]["title"] == "Vendor Mutual NDA"
    assert client.patch(f"/api/legal-ops/matters/{matter_id}", json={"status": "waiting"}, headers=viewer_workspace).status_code == 403
    moved_matter = client.patch(f"/api/legal-ops/matters/{matter_id}", json={"status": "in_review"}, headers=owner_workspace)
    assert moved_matter.status_code == 200
    assert moved_matter.json()["status"] == "in_review"
    assert detail.json()["obligations"][0]["title"] == "Return confidential material after termination"
    assert detail.json()["spend_entries"][0]["invoice_number"] == "INV-001"
    assert detail.json()["playbooks"][0]["title"] == "NDA review checklist"
    matter_export_json = client.get(f"/api/legal-ops/matters/{matter_id}/export?format=json", headers=viewer_workspace)
    assert matter_export_json.status_code == 200
    assert matter_export_json.headers["content-type"].startswith("application/json")
    export_payload = matter_export_json.json()
    assert export_payload["matter_id"] == matter_id
    assert export_payload["organization_id"] == organization_id
    assert export_payload["matter"]["contracts"][0]["title"] == "Vendor Mutual NDA"
    assert export_payload["precedents"][0]["citation"] == "2026 ND 42"
    assert "not legal advice" in export_payload["limits"]
    matter_export_markdown = client.get(f"/api/legal-ops/matters/{matter_id}/export?format=markdown", headers=viewer_workspace)
    assert matter_export_markdown.status_code == 200
    assert matter_export_markdown.headers["content-type"].startswith("text/markdown")
    assert "## Source references" in matter_export_markdown.text
    assert "Vendor Confidentiality Authority v State" in matter_export_markdown.text
    assert client.get(f"/api/legal-ops/matters/{matter_id}/export?format=json", headers=outsider_workspace).status_code == 404
    deadline_kinds = {item["kind"] for item in detail.json()["deadlines"]}
    assert deadline_kinds >= {"task", "contract_renewal", "obligation", "invoice", "document_deadline"}
    assert any(item["description"] == "File NDA redline response." for item in detail.json()["deadlines"])
    assert {item["kind"] for item in detail.json()["activity"]} >= {"document", "note", "task", "contract", "obligation", "intake", "spend", "deadline"}
    note_activity = next(item for item in detail.json()["activity"] if item["kind"] == "note")
    assert note_activity["actor_name"] == "Legal-Ops-Owner"
    assert note_activity["link_kind"] == "task"
    assert note_activity["link_source_id"] == task_id

    deadline_route = client.get(f"/api/legal-ops/matters/{matter_id}/deadlines", headers=viewer_workspace)
    assert deadline_route.status_code == 200
    assert {item["kind"] for item in deadline_route.json()} >= deadline_kinds
    assert client.get(f"/api/legal-ops/matters/{matter_id}/deadlines", headers=outsider_workspace).status_code == 404

    deadline_queue = client.get("/api/legal-ops/deadlines", params={"kind": "document_deadline"}, headers=viewer_workspace)
    assert deadline_queue.status_code == 200
    assert [item["kind"] for item in deadline_queue.json()] == ["document_deadline"]
    assert deadline_queue.json()[0]["description"] == "File NDA redline response."
    due_queue = client.get("/api/legal-ops/deadlines", params={"window": "due_14_days"}, headers=viewer_workspace)
    assert due_queue.status_code == 200
    assert all(0 <= item["days_until"] <= 14 for item in due_queue.json() if item["days_until"] is not None)
    assert client.get("/api/legal-ops/deadlines", headers=outsider_workspace).status_code == 404
    document_deadline_id = deadline_queue.json()[0]["source_id"]
    assert client.post(f"/api/legal-ops/deadlines/document_deadline/{document_deadline_id}/clear", headers=viewer_workspace).status_code == 403

    brief = client.post(f"/api/legal-ops/matters/{matter_id}/brief", headers=viewer_workspace)
    assert brief.status_code == 200
    brief_data = brief.json()
    assert brief_data["matter_id"] == matter_id
    assert "Matter Brief" in brief_data["brief"]
    assert "Vendor wants signature this week." in brief_data["brief"]
    assert "Check confidentiality carve-outs" in brief_data["brief"]
    assert "Vendor Mutual NDA" in brief_data["brief"]
    assert "Return confidential material after termination" in brief_data["brief"]
    assert "Deadline Calendar" in brief_data["brief"]
    assert "File NDA redline response." in brief_data["brief"]
    assert "NDA review checklist" in brief_data["brief"]
    assert "Playbooks are team guidance, not legal authority" in brief_data["brief"]
    assert "not verify legal merits" in brief_data["brief"]
    assert {source["kind"] for source in brief_data["sources"]} >= {"matter", "intake", "note", "task", "contract", "obligation", "document", "playbook", "deadline"}
    assert brief_data["generated_from"]["documents"] == 1
    assert brief_data["generated_from"]["obligations"] == 1
    assert brief_data["generated_from"]["playbooks"] == 1
    assert brief_data["generated_from"]["deadlines"] >= 5

    draft = client.post(
        f"/api/legal-ops/matters/{matter_id}/draft",
        json={"prompt": "What statutory provisions govern the reported conduct?", "precedent_ids": [precedent_record["id"]]},
        headers=owner_workspace,
    )
    assert draft.status_code == 200
    draft_data = draft.json()
    assert draft_data["matter_id"] == matter_id
    assert draft_data["id"]
    draft_id = draft_data["id"]
    assert draft_data["organization_id"] == organization_id
    assert draft_data["review_status"] == "draft"
    assert draft_data["reviewer_note"] == ""
    assert "Grounded draft" in draft_data["title"]
    assert "Recorded matter facts" in draft_data["draft"]
    assert "Review flags" in draft_data["draft"]
    assert "Vendor Confidentiality Authority v State" in draft_data["draft"]
    assert "2026 ND 42" in draft_data["draft"]
    assert "Application of the authorities" in draft_data["unsupported_claims"][-1]
    assert "No precedent was selected or matched" not in draft_data["unsupported_claims"]
    assert draft_data["generated_from"]["statutes"] >= 0
    assert draft_data["generated_from"]["precedents"] == 1
    assert any(source["kind"] == "precedent" and source["id"] == precedent_record["id"] for source in draft_data["sources"])
    assert client.post(
        f"/api/legal-ops/matters/{matter_id}/draft",
        json={"prompt": "Viewer should not persist a draft", "precedent_ids": []},
        headers=viewer_workspace,
    ).status_code == 403

    reviewed_draft = client.patch(
        f"/api/legal-ops/matters/{matter_id}/drafts/{draft_id}",
        json={"review_status": "reviewed", "reviewer_note": "Authorities checked for internal discussion."},
        headers=owner_workspace,
    )
    assert reviewed_draft.status_code == 200
    assert reviewed_draft.json()["review_status"] == "reviewed"
    assert reviewed_draft.json()["reviewer_note"] == "Authorities checked for internal discussion."
    assert reviewed_draft.json()["reviewed_by_user_id"]
    assert reviewed_draft.json()["reviewed_at"]
    assert client.patch(
        f"/api/legal-ops/matters/{matter_id}/drafts/{draft_id}",
        json={"review_status": "approved", "reviewer_note": "Viewer cannot approve."},
        headers=viewer_workspace,
    ).status_code == 403

    approved_draft = client.patch(
        f"/api/legal-ops/matters/{matter_id}/drafts/{draft_id}",
        json={"review_status": "approved", "reviewer_note": "Approved for supervised use."},
        headers=owner_workspace,
    )
    assert approved_draft.status_code == 200
    assert approved_draft.json()["review_status"] == "approved"
    second_draft = client.post(
        f"/api/legal-ops/matters/{matter_id}/draft",
        json={"prompt": "Updated draft with same precedent", "precedent_ids": [precedent_record["id"]]},
        headers=owner_workspace,
    )
    assert second_draft.status_code == 200
    second_draft_id = second_draft.json()["id"]
    assert client.patch(
        f"/api/legal-ops/matters/{matter_id}/drafts/{second_draft_id}",
        json={"review_status": "approved", "reviewer_note": "New approved version."},
        headers=owner_workspace,
    ).status_code == 200

    draft_history = client.get(f"/api/legal-ops/matters/{matter_id}/drafts", headers=viewer_workspace)
    assert draft_history.status_code == 200
    assert draft_history.json()["total"] == 2
    history_by_id = {item["id"]: item for item in draft_history.json()["drafts"]}
    assert history_by_id[draft_id]["review_status"] == "superseded"
    assert history_by_id[second_draft_id]["review_status"] == "approved"
    assert history_by_id[draft_id]["sources"] == draft_data["sources"]

    reopened_draft = client.get(f"/api/legal-ops/matters/{matter_id}/drafts/{draft_id}", headers=viewer_workspace)
    assert reopened_draft.status_code == 200
    assert reopened_draft.json()["draft"] == draft_data["draft"]
    assert reopened_draft.json()["generated_from"] == draft_data["generated_from"]
    assert reopened_draft.json()["review_status"] == "superseded"

    detail_after_draft = client.get(f"/api/legal-ops/matters/{matter_id}", headers=viewer_workspace)
    assert detail_after_draft.status_code == 200
    assert {item["id"] for item in detail_after_draft.json()["drafts"]} >= {draft_id, second_draft_id}
    assert "draft" in {item["kind"] for item in detail_after_draft.json()["activity"]}

    markdown = client.post(
        f"/api/legal-ops/matters/{matter_id}/draft/export?format=markdown&draft_id={draft_id}",
        headers=viewer_workspace,
    )
    assert markdown.status_code == 200
    assert markdown.headers["content-type"].startswith("text/markdown")
    assert "Grounded draft" in markdown.text
    assert draft_data["draft"] in markdown.text
    assert "Vendor Confidentiality Authority v State" in markdown.text
    assert "Review status: superseded" in markdown.text
    assert "Approved for supervised use." in markdown.text

    docx = client.post(
        f"/api/legal-ops/matters/{matter_id}/draft/export?format=docx&draft_id={draft_id}",
        headers=viewer_workspace,
    )
    assert docx.status_code == 200
    assert docx.headers["content-type"].startswith("application/vnd.openxmlformats")
    assert docx.content.startswith(b"PK")
    with ZipFile(BytesIO(docx.content)) as archive:
        document_xml = archive.read("word/document.xml").decode("utf-8")
    assert "Evidence record" in document_xml
    assert "Review status: superseded" in document_xml

    assert client.get(f"/api/legal-ops/matters/{matter_id}/drafts", headers=outsider_workspace).status_code == 404
    assert client.get(f"/api/legal-ops/matters/{matter_id}/drafts/{draft_id}", headers=outsider_workspace).status_code == 404
    assert client.post(f"/api/legal-ops/matters/{matter_id}/draft/export?format=markdown&draft_id={draft_id}", headers=outsider_workspace).status_code == 404

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

    bad_reassignment = client.patch(f"/api/legal-ops/tasks/{task_id}", json={"assignee_user_id": "not-a-workspace-member"}, headers=owner_workspace)
    assert bad_reassignment.status_code == 422
    reassigned_task = client.patch(f"/api/legal-ops/tasks/{task_id}", json={"assignee_user_id": owner_user_id}, headers=owner_workspace)
    assert reassigned_task.status_code == 200
    assert reassigned_task.json()["assignee_user_id"] == owner_user_id
    assert reassigned_task.json()["assignee_name"] == "Legal-Ops-Owner"
    updated_task = client.patch(f"/api/legal-ops/tasks/{task_id}", json={"status": "done"}, headers=owner_workspace)
    assert updated_task.status_code == 200
    assert updated_task.json()["status"] == "done"

    approved_contract = client.patch(f"/api/legal-ops/contracts/{contract_id}", json={"status": "approved", "signature_owner_user_id": owner_user_id, "signature_note": "Route through commercial lead."}, headers=owner_workspace)
    assert approved_contract.status_code == 200
    assert approved_contract.json()["status"] == "approved"
    assert approved_contract.json()["reminder_status"] == "due"
    assert approved_contract.json()["signature_owner_user_id"] == owner_user_id
    assert approved_contract.json()["signature_note"] == "Route through commercial lead."
    sent_contract = client.patch(f"/api/legal-ops/contracts/{contract_id}", json={"status": "sent", "signature_sent_at": "2026-09-09T12:00:00Z"}, headers=owner_workspace)
    assert sent_contract.status_code == 200
    assert sent_contract.json()["lifecycle_stage"] == "pending_signature"
    assert sent_contract.json()["signature_sent_at"] == "2026-09-09T12:00:00Z"

    alerts = client.get("/api/legal-ops/alerts", headers=viewer_workspace)
    assert alerts.status_code == 200
    alert_data = alerts.json()
    assert {item["kind"] for item in alert_data} >= {"deadline", "assigned_task", "signature"}
    assert any(item["kind"] == "deadline" and item["source_kind"] == "obligation" for item in alert_data)
    assigned_alert = next(item for item in alert_data if item["source_id"] == undated_task_id)
    assert assigned_alert["kind"] == "assigned_task"
    assert assigned_alert["severity"] == "high"
    signature_alert = next(item for item in alert_data if item["kind"] == "signature")
    assert signature_alert["source_id"] == contract_id
    assert signature_alert["matter_id"] == matter_id
    assert client.post(f"/api/legal-ops/alerts/{signature_alert['id']}/task", headers=viewer_workspace).status_code == 403
    signature_note = client.post(f"/api/legal-ops/alerts/{signature_alert['id']}/note", json={"body": "Escalate signature follow-through to commercial lead."}, headers=owner_workspace)
    assert signature_note.status_code == 201
    assert signature_note.json()["note"]["matter_id"] == matter_id
    assert signature_note.json()["note"]["link_kind"] == "contract"
    assert signature_note.json()["note"]["link_source_id"] == contract_id
    signature_task = client.post(f"/api/legal-ops/alerts/{signature_alert['id']}/task", headers=owner_workspace)
    assert signature_task.status_code == 201
    assert signature_task.json()["task"]["title"].startswith("Follow up: Signature pending")
    assert signature_task.json()["task"]["assignee_user_id"] == owner_user_id
    assert client.post(f"/api/legal-ops/alerts/{signature_alert['id']}/resolve", headers=owner_workspace).status_code == 422
    assigned_resolution = client.post(f"/api/legal-ops/alerts/{assigned_alert['id']}/resolve", headers=owner_workspace)
    assert assigned_resolution.status_code == 200
    assert assigned_resolution.json()["source_kind"] == "task"
    assert assigned_resolution.json()["task"]["status"] == "done"
    high_alerts = client.get("/api/legal-ops/alerts", params={"severity": "high"}, headers=viewer_workspace)
    assert high_alerts.status_code == 200
    assert all(item["severity"] == "high" for item in high_alerts.json())
    viewer_assigned_alerts = client.get("/api/legal-ops/alerts", params={"assigned_to_me": "true"}, headers=viewer_workspace)
    assert viewer_assigned_alerts.status_code == 200
    assert task_id not in {item["source_id"] for item in viewer_assigned_alerts.json()}
    owner_assigned_alerts = client.get("/api/legal-ops/alerts", params={"assigned_to_me": "true"}, headers=owner_workspace)
    assert owner_assigned_alerts.status_code == 200
    assert task_id not in {item["source_id"] for item in owner_assigned_alerts.json()}
    assert client.get("/api/legal-ops/alerts", headers=outsider_workspace).status_code == 404

    digest = client.get("/api/legal-ops/notifications/digest", headers=owner_workspace)
    assert digest.status_code == 200
    digest_payload = digest.json()
    assert digest_payload["title"] == "Legal Ops Notification Digest"
    assert "Priority alerts" in digest_payload["digest"]
    assert "delivery confirmation" in digest_payload["digest"]
    assert digest_payload["generated_from"]["tasks"] >= 1

    calendar = client.get("/api/legal-ops/deadlines/calendar.ics", headers=viewer_workspace)
    assert calendar.status_code == 200
    assert calendar.headers["content-type"].startswith("text/calendar")
    calendar_text = calendar.text
    assert "BEGIN:VCALENDAR" in calendar_text
    assert "BEGIN:VEVENT" in calendar_text
    assert "SUMMARY:Obligation: Return confidential material after termination" in calendar_text

    workspace = client.get("/api/legal-ops/workspace", headers=viewer_workspace)
    assert workspace.status_code == 200
    data = workspace.json()
    assert [item["title"] for item in data["matters"]] == ["Vendor NDA review"]
    assert data["matters"][0]["status"] == "in_review"
    assert [item["title"] for item in data["intakes"]] == ["Need NDA review"]
    assert {item["title"] for item in data["tasks"]} >= {"Check confidentiality carve-outs", "Confirm signature owner"}
    workspace_tasks = {item["id"]: item for item in data["tasks"]}
    assert workspace_tasks[task_id]["assignee_user_id"] == owner_user_id
    assert workspace_tasks[task_id]["assignee_name"] == "Legal-Ops-Owner"
    assert {member["email"] for member in data["members"]} >= {viewer_email}
    assert [item["title"] for item in data["contracts"]] == ["Vendor Mutual NDA"]
    refreshed_detail = client.get(f"/api/legal-ops/matters/{matter_id}", headers=viewer_workspace).json()
    assert any(note["body"].startswith("Escalate signature") and note["link_kind"] == "contract" for note in refreshed_detail["notes"])
    assert data["summary"]["high_risk_contracts"] == 1
    assert data["summary"]["tasks_by_status"]["done"] == 2
    assert data["summary"]["renewals_due_60_days"] == 1
    assert data["summary"]["pending_signature_contracts"] == 1
    assert data["summary"]["open_contract_obligations"] == 1
    assert data["summary"]["overdue_contract_obligations"] == 0
    assert data["summary"]["open_matter_deadlines"] >= 4
    assert data["summary"]["matter_deadlines_due_14_days"] >= 1
    assert data["summary"]["open_action_alerts"] >= 2
    assert data["summary"]["high_priority_action_alerts"] >= 1
    assert {item["kind"] for item in data["action_alerts"]} >= {"deadline", "signature"}
    assert undated_task_id not in {item["source_id"] for item in data["action_alerts"]}
    assert {item["kind"] for item in data["matter_deadlines"]} >= {"task", "contract_renewal", "obligation", "invoice", "document_deadline"}
    assert any(item["description"] == "File NDA redline response." for item in data["matter_deadlines"])
    assert data["obligations"][0]["id"] == obligation_id
    assert data["contract_reminders"][0]["id"] == contract_id
    assert data["contract_reminders"][0]["reminder_status"] == "due"
    assert data["vendors"][0]["name"] == "Acme Legal LLP"
    assert data["spend_entries"][0]["invoice_number"] == "INV-001"
    assert data["summary"]["open_spend_total"] == 125000
    assert data["summary"]["paid_spend_total"] == 0
    assert data["summary"]["active_playbooks"] == 1
    assert data["playbooks"][0]["title"] == "NDA review checklist"

    analytics = client.get("/api/legal-ops/analytics", headers=viewer_workspace)
    assert analytics.status_code == 200
    kpis = analytics.json()
    assert kpis["title"] == "Legal Ops KPI Analytics"
    assert "not legal advice" in kpis["limits"]
    assert kpis["workload"]["total_matters"] == 1
    assert kpis["workload"]["open_tasks"] == 1
    assert kpis["workload"]["completed_tasks"] == 2
    assert kpis["intake_conversion"]["total_intake"] == 1
    assert kpis["intake_conversion"]["converted_intake"] == 1
    assert kpis["intake_conversion"]["conversion_rate_percent"] == 100
    assert kpis["deadline_health"]["open_deadlines"] >= 4
    assert kpis["contract_health"]["high_risk_contracts"] == 1
    assert kpis["contract_health"]["pending_signature_contracts"] == 1
    assert kpis["spend"]["open_spend_total"] == 125000
    assert kpis["spend"]["top_vendors"][0]["vendor_name"] == "Acme Legal LLP"
    assert kpis["team_throughput"]["completed_tasks"] == 2
    assert any(row["assignee_name"] == "Legal-Ops-Owner" for row in kpis["team_throughput"]["tasks_by_assignee"])
    assert kpis["risk_queue"]["open_action_alerts"] >= 2
    assert kpis["generated_from"]["matter_deadlines"] == 6
    assert client.get("/api/legal-ops/analytics", headers=outsider_workspace).status_code == 404

    report = client.get("/api/legal-ops/report", headers=viewer_workspace)
    assert report.status_code == 200
    report_data = report.json()
    assert report_data["title"] == "Legal Ops Report"
    assert "Executive Snapshot" in report_data["report"]
    assert "Matter Status" in report_data["report"]
    assert "Matter Deadlines" in report_data["report"]
    assert "File NDA redline response." in report_data["report"]
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
        "tasks": 3,
        "contracts": 1,
        "obligations": 1,
        "vendors": 1,
        "spend_entries": 1,
        "playbooks": 1,
        "matter_deadlines": 6,
    }
    assert client.get("/api/legal-ops/report", headers=outsider_workspace).status_code == 404

    renewal_deadline = next(item for item in data["matter_deadlines"] if item["kind"] == "contract_renewal")
    assert client.post(f"/api/legal-ops/deadlines/contract_renewal/{renewal_deadline['source_id']}/clear", headers=owner_workspace).status_code == 422
    assert client.post(f"/api/legal-ops/deadlines/contract_renewal/{renewal_deadline['source_id']}/task", headers=viewer_workspace).status_code == 403
    deadline_task = client.post(f"/api/legal-ops/deadlines/contract_renewal/{renewal_deadline['source_id']}/task", headers=owner_workspace)
    assert deadline_task.status_code == 201
    assert deadline_task.json()["deadline"]["kind"] == "contract_renewal"
    assert deadline_task.json()["task"]["matter_id"] == matter_id
    assert deadline_task.json()["task"]["title"].startswith("Follow up: Renewal: Vendor Mutual NDA")

    cleared_document_deadline = client.post(f"/api/legal-ops/deadlines/document_deadline/{document_deadline_id}/clear", headers=owner_workspace)
    assert cleared_document_deadline.status_code == 200
    assert cleared_document_deadline.json()["status"] == "cleared"
    document_deadline_after_clear = client.get("/api/legal-ops/deadlines", params={"kind": "document_deadline"}, headers=viewer_workspace)
    assert document_deadline_after_clear.status_code == 200
    assert document_deadline_after_clear.json()[0]["status"] == "cleared"

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

    assert client.post(f"/api/legal-ops/intake/{intake_id}/task", headers=viewer_workspace).status_code == 403
    triage_task = client.post(f"/api/legal-ops/intake/{intake_id}/task", headers=owner_workspace)
    assert triage_task.status_code == 201
    triage_payload = triage_task.json()
    assert triage_payload["intake"]["status"] == "triaged"
    assert triage_payload["task"]["title"] == "Triage intake: Employee data request"
    assert triage_payload["task"]["priority"] == "high"
    assert triage_payload["task"]["assignee_email"]

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
    assert any(task["title"] == "Triage intake: Employee data request" for task in workspace["tasks"])

    assert client.post("/api/legal-ops/intake/missing/task", headers=owner_workspace).status_code == 422
