from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from app.services.doc_compare import compare_versions


DATE_RE = r"\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b|\b\d{1,2} (?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]* \d{4}\b"


def _date(value: str) -> str | None:
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y", "%d %b %Y", "%d %B %Y"):
        try:
            return datetime.strptime(value.strip(), fmt).date().isoformat()
        except ValueError:
            continue
    return None


def extract_obligations_v2(text: str) -> list[dict[str, Any]]:
    obligations = []
    for sentence in re.split(r"(?<=[.\n])\s+", text):
        if not re.search(r"\b(file|submit|serve|pay|comply|due|shall|must|required)\b", sentence, re.I):
            continue
        match = re.search(DATE_RE, sentence, re.I)
        if not match:
            continue
        due = _date(match.group(0))
        if not due:
            continue
        obligations.append({"type": "filing_or_compliance", "due_date": due, "responsible": "unassigned", "description": sentence.strip()[:500], "confidence": 0.82, "source_sentence": sentence.strip(), "provenance_verified": False})
    return obligations


def re_extract_matter(tenant_id: str, matter_id: str, use_llm: bool = False) -> dict[str, Any]:
    matter_dir = Path("app/storage/vault") / tenant_id / "matters" / matter_id
    source = matter_dir / "extracted.json"
    data = json.loads(source.read_text(encoding="utf-8"))
    text = "\n".join([str(data.get("case_no") or ""), str(data.get("court") or ""), *[str(item.get("description") or "") for item in data.get("obligations", []) if isinstance(item, dict)]])
    v2 = dict(data)
    v2["obligations"] = extract_obligations_v2(text)
    v2["provenance_verified"] = False
    diff = compare_versions(tenant_id, matter_id, data, v2)
    (matter_dir / "extracted_v2.json").write_text(json.dumps(v2, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    (matter_dir / "extraction_diff.json").write_text(json.dumps(diff, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return {"matter_id": matter_id, "extracted_v2": v2, "diff": diff, "llm_used": False, "provenance_verified": False}
