from __future__ import annotations

import json
import shutil
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.jobs.daily_digest import build_daily_digest
from app.services.calendar_service import build_ics, get_calendar_events
from app.services.obligation_tracker import get_upcoming_obligations, mark_obligation_status


ROOT = Path(__file__).resolve().parents[1]
TENANT_ID = "personal-test"
MATTER_ID = "test-matter-001"
MATTER_DIR = ROOT / "app" / "storage" / "vault" / TENANT_ID / "matters" / MATTER_ID
EXTRACTED_PATH = MATTER_DIR / "extracted.json"


def _ensure_fixture() -> None:
    MATTER_DIR.mkdir(parents=True, exist_ok=True)
    if EXTRACTED_PATH.exists():
        return
    payload = {
        "case_no": "CS 123/2024",
        "court": "District Court",
        "parties": {"plaintiff": "Asha Rao", "defendant": "Bharat Mehta"},
        "next_hearing_date": "2025-12-15",
        "obligations": [
            {
                "due_date": "2025-12-10",
                "type": "filing_or_compliance",
                "responsible": "Bharat Mehta",
                "description": "File written statement",
            }
        ],
        "risk_flags": [],
        "provenance_verified": False,
    }
    EXTRACTED_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    (MATTER_DIR / "provenance.json").write_text(
        json.dumps({"source_hash": "smoke", "extracted_at": "2025-12-01T00:00:00+00:00", "provenance_verified": False}, indent=2),
        encoding="utf-8",
    )


def main() -> None:
    status_path = MATTER_DIR / "obligation_status.json"
    if status_path.exists():
        status_path.unlink()
    if (MATTER_DIR / "versions").exists():
        shutil.rmtree(MATTER_DIR / "versions")

    _ensure_fixture()
    before = EXTRACTED_PATH.read_bytes()
    upcoming = get_upcoming_obligations(TENANT_ID, days=9, today=date(2025, 12, 1))
    assert len(upcoming) == 1, upcoming
    assert upcoming[0]["due_date"] == "2025-12-10"
    assert upcoming[0]["case_no"] == "CS 123/2024"

    ics = build_ics(TENANT_ID)
    assert "BEGIN:VCALENDAR" in ics
    assert "BEGIN:VEVENT" in ics
    assert "CS 123/2024" in ics
    assert "provenance_verified:false" in ics

    events = get_calendar_events(TENANT_ID, "2025-12-01", "2025-12-31")
    assert [event["date"] for event in events] == sorted(event["date"] for event in events)
    assert {event["type"] for event in events} == {"hearing", "obligation"}

    status = mark_obligation_status(TENANT_ID, MATTER_ID, upcoming[0]["obligation_id"], "done")
    assert status["status"] == "done"
    assert status_path.exists()
    assert EXTRACTED_PATH.read_bytes() == before
    stored = json.loads(EXTRACTED_PATH.read_text(encoding="utf-8"))
    assert stored["provenance_verified"] is False

    digest = build_daily_digest(TENANT_ID, today=date(2025, 12, 1))
    assert digest["provenance_verified"] is False
    print("SMOKE PASSED")


if __name__ == "__main__":
    main()
