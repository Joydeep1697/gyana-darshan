from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.database import Database
from app.intelligence.contract_review import review_contract
from app.models import ContractObligationAcceptRequest
from app.routers import vault


def test_contract_review_detects_nda_risks_from_document_text():
    text = """
    Mutual Non-Disclosure Agreement. Each party may disclose Confidential Information to the other party.
    The receiving party shall hold confidential information in strict confidence and shall not disclose it.
    Confidentiality obligations survive for three years after termination.
    The receiving party must return or destroy confidential materials upon request.
    The agreement is governed by the laws of India and courts at Bengaluru have jurisdiction.
    Liability shall not exceed the fees paid in the previous twelve months.
    """

    result = review_contract(text, filename="mutual-nda.pdf", category="Contract")

    assert result["document_type"] == "nda"
    assert result["nda"]["kind"] == "mutual"
    assert "standard confidentiality carve-outs" not in result["nda"]["signals"]
    assert "term or survival period" in result["nda"]["signals"]
    assert "return or destruction duty" in result["nda"]["signals"]
    assert any("Standard exclusions" in item for item in result["nda"]["missing"])
    assert any(clause["type"] == "confidentiality" for clause in result["clauses"])
    assert any(risk["title"].startswith("NDA missing check") for risk in result["risks"])
    assert result["obligation_suggestions"]
    assert any(item["category"] == "return_destruction" for item in result["obligation_suggestions"])
    assert all(item["source_clause"] and item["source_clause"] in text.replace("\n", " ") for item in result["obligation_suggestions"])
    assert result["review_recommended"] is True
    assert "not legal approval" in result["summary"]


def test_vault_contract_review_is_workspace_scoped_and_uses_pdf_text(tmp_path: Path):
    db = Database(tmp_path / "vault.sqlite3")
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    pdf_path = raw_dir / "contract.pdf"
    pdf_path.write_bytes(b"%PDF-test")
    doc_id = db.create_document("contract.pdf", 9, str(pdf_path), "owner", "org-1")
    db.create_document("other.pdf", 9, str(raw_dir / "other.pdf"), "owner", "org-2")
    workspace = {"user": {"id": "viewer"}, "organization": {"id": "org-1"}, "role": "VIEWER"}

    with patch("app.routers.vault.RAW_DIR", raw_dir), patch(
        "app.routers.vault.extract_pdf_pages",
        return_value=[{"page": 1, "text": "This NDA contains confidential information and unlimited liability."}],
    ):
        result = asyncio.run(vault.review_document_contract(doc_id, db=db, workspace=workspace))

    assert result.filename == "contract.pdf"
    assert result.document_type == "nda"
    assert result.overall_risk == "high"
    assert any(risk.level == "high" for risk in result.risks)

    with pytest.raises(HTTPException) as raised:
        asyncio.run(vault.review_document_contract(doc_id, db=db, workspace={"organization": {"id": "org-2"}}))

    assert raised.value.status_code == 404


def test_accepting_contract_obligation_suggestion_creates_grounded_legal_ops_record(tmp_path: Path):
    db = Database(tmp_path / "vault.sqlite3")
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    pdf_path = raw_dir / "vendor-nda.pdf"
    pdf_path.write_bytes(b"%PDF-test")
    doc_id = db.create_document("vendor-nda.pdf", 9, str(pdf_path), "owner", "org-1")
    db.update_document(doc_id, status="indexed", category="Contract", domain="Commercial")
    workspace = {"user": {"id": "writer"}, "organization": {"id": "org-1"}, "role": "MEMBER"}
    source_text = "The receiving party must return or destroy confidential materials upon termination."
    suggestion = review_contract(source_text, filename="vendor-nda.pdf", category="Contract")["obligation_suggestions"][0]

    with patch("app.routers.vault.RAW_DIR", raw_dir), patch(
        "app.routers.vault.extract_pdf_pages",
        return_value=[{"page": 1, "text": source_text}],
    ), patch("app.routers.vault.AuditRepository.log_audit"):
        result = asyncio.run(
            vault.accept_document_contract_obligation(
                doc_id,
                ContractObligationAcceptRequest(suggestion=suggestion, owner="Legal"),
                db=db,
                workspace=workspace,
            )
        )

    assert result["contract"]["document_id"] == doc_id
    assert result["contract"]["title"] == "vendor-nda.pdf"
    assert result["obligation"]["contract_id"] == result["contract"]["id"]
    assert result["obligation"]["title"] == suggestion["title"]
    assert result["obligation"]["owner"] == "Legal"
    assert result["obligation"]["source_clause"] == suggestion["source_clause"]
    assert db.list_contract_obligations("org-1")[0]["id"] == result["obligation"]["id"]

    with patch("app.routers.vault.RAW_DIR", raw_dir), patch(
        "app.routers.vault.extract_pdf_pages",
        return_value=[{"page": 1, "text": source_text}],
    ), patch("app.routers.vault.AuditRepository.log_audit"):
        tampered = {**suggestion, "source_clause": "Invented obligation text that is not in the document."}
        with pytest.raises(HTTPException) as raised:
            asyncio.run(
                vault.accept_document_contract_obligation(
                    doc_id,
                    ContractObligationAcceptRequest(suggestion=tampered),
                    db=db,
                    workspace=workspace,
                )
            )

    assert raised.value.status_code == 422
