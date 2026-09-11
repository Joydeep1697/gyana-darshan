"""Playwright browser verification for PRS India evidence."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.ingestion.browser_source_check import check_source
from app.ingestion.sources import SOURCES


async def check() -> dict:
    return await check_source(SOURCES["prs"], ("prs", "legislative", "bill"))


if __name__ == "__main__":
    asyncio.run(check())

