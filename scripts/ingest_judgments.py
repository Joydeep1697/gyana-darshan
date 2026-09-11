"""CLI entry point for judgment ingestion jobs."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ingestion.ecourts_crawler import ingest_ecourts
from app.ingestion.indiankanoon_crawler import ingest_indiankanoon


async def run(source: str, query: str, limit: int, tenant_id: str) -> object:
    if source == "ecourts":
        return await ingest_ecourts(query=query, tenant_id=tenant_id, limit=limit)
    if source == "indiankanoon":
        return await ingest_indiankanoon(query=query, limit=limit)
    raise ValueError(f"Unsupported source: {source}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run judgment ingestion for eCourts or IndianKanoon.")
    parser.add_argument("--source", choices=("ecourts", "indiankanoon"), required=True)
    parser.add_argument("--query", default="BNS 103")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--tenant-id", default="local-cron")
    args = parser.parse_args()
    result = asyncio.run(run(args.source, args.query, max(1, min(args.limit, 25)), args.tenant_id))
    print(result)
    status = getattr(result, "status", "")
    return 0 if status in {"saved", "no_results", "blocked", "needs_human_action"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
