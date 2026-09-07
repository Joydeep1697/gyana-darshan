"""Validation and ingestion helpers for curated case-law JSONL records."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from app.database import Database

ALLOWED_PROVENANCE = {"verified", "unverified", "retracted"}


def validate_case_law_record(record: dict[str, Any], *, source_name: str | None = None) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise ValueError("each case-law record must be a JSON object")
    corpus_key = str(record.get("corpus_key") or "").strip()
    title = str(record.get("title") or "").strip()
    citation = str(record.get("citation") or "").strip()
    case_number = str(record.get("case_number") or "").strip()
    court = str(record.get("court") or "").strip()
    resolved_source = str(source_name or record.get("source_name") or "").strip()
    if not corpus_key:
        raise ValueError("corpus_key is required")
    if not title:
        raise ValueError("title is required")
    if not citation and not case_number:
        raise ValueError("citation or case_number is required")
    if not court:
        raise ValueError("court is required")
    if not resolved_source:
        raise ValueError("source_name is required")
    year = record.get("year")
    if year is not None and (not isinstance(year, int) or not 1800 <= year <= 2200):
        raise ValueError("year must be between 1800 and 2200")
    status = str(record.get("provenance_status") or "unverified").strip().lower()
    if status not in ALLOWED_PROVENANCE:
        raise ValueError("provenance_status must be verified, unverified, or retracted")
    excerpt = str(record.get("source_excerpt") or "").strip()
    paragraphs = record.get("paragraphs") or []
    if not isinstance(paragraphs, list) or any(not isinstance(item, dict) or not str(item.get("text") or "").strip() for item in paragraphs):
        raise ValueError("paragraphs must be a list of objects with text")
    return {
        **record,
        "corpus_key": corpus_key,
        "title": title,
        "citation": citation,
        "case_number": case_number,
        "court": court,
        "source_name": resolved_source,
        "source_url": str(record.get("source_url") or "").strip(),
        "source_excerpt": excerpt,
        "provenance_status": status,
        "paragraphs": paragraphs,
        "judges": record.get("judges") or [],
        "sections": record.get("sections") or [],
        "source_page": int(record.get("source_page") or 1),
    }


def read_case_law_jsonl(path: Path, *, source_name: str | None = None) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            try:
                raw = json.loads(line)
                yield validate_case_law_record(raw, source_name=source_name)
            except (json.JSONDecodeError, ValueError, TypeError) as exc:
                raise ValueError(f"{path}:{line_number}: {exc}") from exc


def ingest_case_law_jsonl(db: Database, path: Path, *, source_name: str | None = None) -> dict[str, int]:
    inserted = 0
    for record in read_case_law_jsonl(path, source_name=source_name):
        db.upsert_case_law_corpus_record(record)
        inserted += 1
    return {"records": inserted}
