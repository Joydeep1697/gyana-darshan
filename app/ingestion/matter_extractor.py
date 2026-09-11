"""Deterministic, reviewable extraction of basic matter facts from judgment PDFs."""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from PyPDF2 import PdfReader
except ModuleNotFoundError:  # PyMuPDF is already a project dependency.
    import fitz

    class PdfReader:  # type: ignore[no-redef]
        def __init__(self, path: str):
            document = fitz.open(path)
            self.pages = [_Page(page) for page in document]


    class _Page:
        def __init__(self, page):
            self._page = page

        def extract_text(self) -> str:
            return self._page.get_text()

DATE_RE = r"(?:\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}|\d{4}-\d{1,2}-\d{1,2}|\d{1,2}\s+[A-Za-z]+\s+\d{4})"


def _text(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _date(value: str) -> str | None:
    value = value.strip().replace(".", "/").replace("-", "/")
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y/%m/%d", "%d %B %Y", "%d %b %Y"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _field(text: str, labels: str) -> str | None:
    match = re.search(rf"(?im)^\s*(?:{labels})\s*[:\-]\s*(.+?)\s*$", text)
    return re.sub(r"\s+", " ", match.group(1)).strip() if match else None


def extract_matter_data(pdf_path: str | Path) -> dict[str, Any]:
    raw = _text(Path(pdf_path))
    compact = re.sub(r"[ \t]+", " ", raw)
    hearing = re.search(rf"(?i)(?:next\s+hearing|next\s+date|hearing\s+date)\s*[:\-]?\s*({DATE_RE})", compact)
    next_hearing_date = _date(hearing.group(1)) if hearing else None
    parties = {
        "plaintiff": _field(raw, r"plaintiff|petitioner|complainant|applicant"),
        "defendant": _field(raw, r"defendant|respondent|accused"),
    }
    case_no = _field(raw, r"case\s*(?:no|number)|cnr(?:\s*no)?")
    court_match = re.search(r"(?im)^\s*((?:in the )?.{0,120}court.{0,120})\s*$", raw)
    court = re.sub(r"\s+", " ", court_match.group(1)).strip() if court_match else None
    obligations: list[dict[str, Any]] = []
    for line in (line.strip() for line in raw.splitlines() if line.strip()):
        match = re.search(rf"(?i)\b(?:shall|must|required to|due by|file .*? by)\b.*?({DATE_RE})", line)
        if not match:
            continue
        due_date = _date(match.group(1))
        if due_date:
            obligations.append({"type": "filing_or_compliance", "due_date": due_date, "responsible": parties.get("defendant") or "unassigned", "description": re.sub(r"\s+", " ", line)[:500]})
    risk_flags = []
    if not next_hearing_date: risk_flags.append("hearing_date_missing")
    if not any(parties.values()): risk_flags.append("party_names_missing")
    if not case_no: risk_flags.append("case_number_missing")
    if not court: risk_flags.append("court_missing")
    return {"parties": parties, "case_no": case_no, "court": court, "next_hearing_date": next_hearing_date, "obligations": obligations, "risk_flags": risk_flags}
