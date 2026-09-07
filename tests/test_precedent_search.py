from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from fastapi import HTTPException

from app.database import Database
from app.routers import vault


def test_case_law_index_is_org_scoped_and_searches_source_metadata(tmp_path: Path):
    db = Database(tmp_path / "precedents.sqlite3")
    shared = db.create_document("kesavananda.pdf", 10, str(tmp_path / "kesavananda.pdf"), "u1", "org-1")
    outside = db.create_document("outside.pdf", 10, str(tmp_path / "outside.pdf"), "u2", "org-2")
    fields = {
        "title": "Kesavananda Bharati v State of Kerala",
        "citation": "(1973) 4 SCC 225",
        "court": "Supreme Court of India",
        "judges": ["Sikri C.J."],
        "petitioner": "Kesavananda Bharati",
        "respondent": "State of Kerala",
        "case_number": "W.P. No. 135 of 1970",
        "decision_date": "24 April 1973",
        "year": 1973,
        "sections": ["Article 368"],
        "source_excerpt": "The basic structure of the Constitution cannot be destroyed by amendment.",
        "source_page": 1,
    }
    db.upsert_case_law_record("org-1", shared, fields)
    db.upsert_case_law_record("org-2", outside, {**fields, "title": "Outside judgment"})

    results = db.search_case_law_records("org-1", "basic structure")
    assert len(results) == 1
    assert results[0]["document_id"] == shared
    assert results[0]["citation"] == "(1973) 4 SCC 225"
    assert results[0]["excerpt"].startswith("The basic structure")
    assert results[0]["judges"] == ["Sikri C.J."]

    assert db.search_case_law_records("org-1", "basic structure", year_from=1974) == []


def test_precedent_search_route_rejects_invalid_year_range_and_returns_results(tmp_path: Path):
    db = Database(tmp_path / "precedents.sqlite3")
    document_id = db.create_document("judgment.pdf", 10, str(tmp_path / "judgment.pdf"), "u1", "org-1")
    db.upsert_case_law_record(
        "org-1",
        document_id,
        {
            "title": "R v State",
            "citation": "2020 INSC 10",
            "court": "Supreme Court of India",
            "year": 2020,
            "source_excerpt": "The court considered the statutory issue.",
        },
    )

    response = asyncio.run(vault.search_precedents("statutory", court=None, year_from=None, year_to=None, limit=20, db=db, workspace={"organization": {"id": "org-1"}}))
    assert response.total == 1
    assert response.results[0].citation == "2020 INSC 10"

    with pytest.raises(HTTPException) as raised:
        asyncio.run(vault.search_precedents("statutory", year_from=2021, year_to=2020, db=db, workspace={"organization": {"id": "org-1"}}))
    assert raised.value.status_code == 422
