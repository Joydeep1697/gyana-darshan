"""Shared ingestion helpers for provenance-aware corpus refreshes."""

from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


class IngestionLogger:
    """Append-only audit trail for corpus refresh attempts."""

    def __init__(self, log_path: Path = Path("logs") / "ingestion_log.jsonl"):
        self.log_path = log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log(
        self,
        act: str,
        section: str,
        url: str,
        status: str,
        file_path: Optional[str] = None,
        error: Optional[str] = None,
        **metadata: Any,
    ) -> dict[str, Any]:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "act": act,
            "section": section,
            "source_url": url,
            "status": status,
            "file": file_path,
            "error": error,
            "hash": hashlib.sha256(f"{act}-{section}-{url}".encode("utf-8")).hexdigest()[:12],
        }
        entry.update({key: value for key, value in metadata.items() if value is not None})
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return entry


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def save_with_provenance(content: str, output_path: Path, source_url: str, act: str, section: str, fetched_with: str) -> Path:
    """Save Markdown with frontmatter for audit and source verification."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fetched_at = utc_now()
    frontmatter = (
        "---\n"
        f"act: {act}\n"
        f"section: {section}\n"
        f"source_url: {source_url}\n"
        f"fetched_at: {fetched_at}\n"
        f"fetched_with: {fetched_with}\n"
        "provenance_verified: false\n"
        "corpus: corpus_integrity/bns\n"
        "---\n\n"
        f"> Source: {source_url}\n"
        f"> Fetched: {fetched_at}\n\n"
    )
    output_path.write_text(frontmatter + content, encoding="utf-8")
    return output_path


def sleep_rate_limit(seconds: float = 1.0) -> None:
    time.sleep(seconds)
