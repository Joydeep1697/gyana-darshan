"""Daily corpus ingestion entry point for Render Cron or local maintenance."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ingestion.bns_crawler import BNS_SOURCE_URL, DEFAULT_OUTPUT_DIR, export_all_statutory_fallbacks, ingest_bns_section
from app.ingestion.sources import SOURCES


def latest_browser_check_status(log_path: Path = Path("app") / "ingestion" / "browser_check_log.jsonl") -> int | None:
    if not log_path.exists():
        return None
    for line in reversed(log_path.read_text(encoding="utf-8", errors="ignore").splitlines()):
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if item.get("url") == BNS_SOURCE_URL and isinstance(item.get("status"), int):
            return item["status"]
    return None


def latest_source_statuses(log_path: Path = Path("app") / "ingestion" / "browser_check_log.jsonl") -> dict[str, int]:
    statuses: dict[str, int] = {}
    if not log_path.exists():
        return statuses
    for line in log_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        source = item.get("source")
        status = item.get("status")
        if source in SOURCES and isinstance(status, int):
            statuses[source] = status
        elif item.get("url") == BNS_SOURCE_URL and isinstance(status, int):
            statuses["bns"] = status
    return statuses


async def run_daily_ingestion(section: str = "103", url: str = BNS_SOURCE_URL, output_dir: Path = DEFAULT_OUTPUT_DIR) -> Path:
    return await ingest_bns_section(section=section, url=url, output_dir=output_dir)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run scheduled free-source legal corpus ingestion.")
    parser.add_argument("--section", default="103", help="BNS section number to refresh.")
    parser.add_argument("--url", default=BNS_SOURCE_URL, help="Public India Code source URL.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Directory for refreshed Markdown files.")
    parser.add_argument("--all-statutes", action="store_true", help="Refresh BNS, BNSS, and BSA Markdown from local JSONL fallbacks.")
    args = parser.parse_args(argv)
    if args.all_statutes:
        counts = export_all_statutory_fallbacks()
        print(f"Exported statutory fallback corpus: {json.dumps(counts, sort_keys=True)}")
        for source, status in latest_source_statuses().items():
            if status == 200:
                print(f"ALERT: {source} browser check is HTTP 200. Re-run live verification before continuing fallback claims.")
        return 0
    output = asyncio.run(run_daily_ingestion(args.section, args.url, Path(args.output_dir)))
    print(f"Ingested {output}")
    if latest_browser_check_status() == 200:
        print("ALERT: India Code browser check is now HTTP 200. Re-run live verification before continuing JSONL fallback claims.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
