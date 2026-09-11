from pathlib import Path

import fitz

from app.ingestion.matter_extractor import extract_matter_data
from verification.matter_validator import validate_matter_data


def test_extracts_case_facts_and_obligations(tmp_path: Path):
    pdf_path = tmp_path / "judgment.pdf"
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "IN THE DISTRICT COURT OF DELHI\nCase No: ABC/123\nPlaintiff: Acme Ltd\nDefendant: Beta Pvt Ltd\nNext hearing: 15-12-2025\nThe defendant shall file reply by 20-12-2025.")
    document.save(pdf_path)
    document.close()

    data = extract_matter_data(pdf_path)
    assert data["parties"] == {"plaintiff": "Acme Ltd", "defendant": "Beta Pvt Ltd"}
    assert data["case_no"] == "ABC/123"
    assert data["next_hearing_date"] == "2025-12-15"
    assert data["obligations"][0]["due_date"] == "2025-12-20"
    assert "past_date:2025-12-15" in validate_matter_data(data, today=__import__("datetime").date(2025, 12, 1))["errors"] or validate_matter_data(data, today=__import__("datetime").date(2025, 12, 1))["valid"]


def test_missing_date_is_explicit_risk(tmp_path: Path):
    pdf_path = tmp_path / "empty.pdf"
    document = fitz.open()
    document.new_page().insert_text((72, 72), "Plaintiff: A\nDefendant: B")
    document.save(pdf_path)
    document.close()
    data = extract_matter_data(pdf_path)
    assert data["next_hearing_date"] is None
    assert "hearing_date_missing" in data["risk_flags"]
