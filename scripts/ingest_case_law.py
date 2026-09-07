"""Validate and ingest a curated case-law JSONL file into Nyaya Darshana."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.database import Database
from app.intelligence.case_law_corpus import ingest_case_law_jsonl


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="JSONL file containing provenance-aware case-law records")
    parser.add_argument("--source-name", default=None, help="Override source_name for every record")
    args = parser.parse_args()
    result = ingest_case_law_jsonl(Database(), args.path.resolve(), source_name=args.source_name)
    print(json.dumps({"path": str(args.path.resolve()), **result}, indent=2))


if __name__ == "__main__":
    main()
