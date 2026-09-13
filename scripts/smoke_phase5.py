from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import fitz

from app.ingestion.matter_extractor import extract_matter_data
from app.retrieval.matter_indexer import index_tenant, search_tenant
from app.services.timeline_builder import build_timeline
from app.storage.vault_writer import save_matter


ROOT = Path(__file__).resolve().parents[1]
TENANT_ID = "phase5-smoke-tenant"
MATTER_ID = "phase5-smoke-matter"
PDF_PATH = ROOT / "sample_phase5_judgment.pdf"


def _make_pdf(path: Path) -> None:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(
        (72, 72),
        "\n".join(
            [
                "In the District Court of Delhi",
                "Case No: BNS-103/2026",
                "Plaintiff: State of NCT Delhi",
                "Defendant: Ravi Kumar",
                "Next Hearing: 2026-10-15",
                "The defendant shall file compliance affidavit by 2026-10-01.",
            ]
        ),
    )
    doc.save(path)
    doc.close()


def main() -> None:
    tenant_root = ROOT / "app" / "storage" / "vault" / TENANT_ID
    if tenant_root.exists():
        shutil.rmtree(tenant_root)
    if PDF_PATH.exists():
        PDF_PATH.unlink()

    _make_pdf(PDF_PATH)
    extracted = extract_matter_data(PDF_PATH)
    saved = save_matter(TENANT_ID, MATTER_ID, extracted, PDF_PATH)
    index = index_tenant(TENANT_ID)
    case_results = search_tenant(TENANT_ID, q="BNS-103/2026")
    timeline = build_timeline(extracted)

    extracted_file = Path(saved["extracted_file"])
    provenance_file = Path(saved["provenance_file"])
    stored_extracted = json.loads(extracted_file.read_text(encoding="utf-8"))
    stored_provenance = json.loads(provenance_file.read_text(encoding="utf-8"))

    assert extracted_file.exists(), "extracted.json was not written"
    assert provenance_file.exists(), "provenance.json was not written"
    assert Path(saved["source_pdf"]).exists(), "source PDF was not stored"
    assert stored_extracted["provenance_verified"] is False
    assert stored_provenance["provenance_verified"] is False
    assert case_results and case_results[0]["matter_id"] == MATTER_ID
    assert len(timeline) == 2, timeline
    assert [event["date"] for event in timeline] == sorted(event["date"] for event in timeline)
    assert index and index[0]["provenance_verified"] is False

    print("SMOKE PASSED")


if __name__ == "__main__":
    main()
