"""Daily corpus ingestion entry point for Render Cron or local maintenance."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ingestion.bns_crawler import BNS_SOURCE_URL, DEFAULT_OUTPUT_DIR, ingest_bns_section


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


async def run_daily_ingestion(section: str = "103", url: str = BNS_SOURCE_URL, output_dir: Path = DEFAULT_OUTPUT_DIR) -> Path:
    return await ingest_bns_section(section=section, url=url, output_dir=output_dir)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run scheduled free-source legal corpus ingestion.")
    parser.add_argument("--section", default="103", help="BNS section number to refresh.")
    parser.add_argument("--url", default=BNS_SOURCE_URL, help="Public India Code source URL.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Directory for refreshed Markdown files.")
    args = parser.parse_args(argv)
    output = asyncio.run(run_daily_ingestion(args.section, args.url, Path(args.output_dir)))
    print(f"Ingested {output}")
    if latest_browser_check_status() == 200:
        print("ALERT: India Code browser check is now HTTP 200. Re-run live verification before continuing JSONL fallback claims.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
