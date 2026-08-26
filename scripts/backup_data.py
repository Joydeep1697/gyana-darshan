"""Create a consistent, portable backup of Nyaya Darshana application data."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import tempfile
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from app.config import APP_DB_PATH, RAW_DIR
from database.connection import SQLITE_DB_PATH


def _snapshot(source: Path, destination: Path) -> None:
    if not source.exists():
        return
    with closing(sqlite3.connect(source)) as source_db, closing(sqlite3.connect(destination)) as target_db:
        source_db.backup(target_db)


def create_backup(output: Path, include_uploads: bool = True) -> dict:
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite existing backup: {output}")
    manifest = {
        "format": "nyaya-backup-v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "files": {},
    }
    with tempfile.TemporaryDirectory(prefix="nyaya-backup-") as temp_value:
        temp = Path(temp_value)
        snapshots = {
            "databases/product.db": SQLITE_DB_PATH,
            "databases/vault.db": APP_DB_PATH,
        }
        for archive_name, source in snapshots.items():
            target = temp / Path(archive_name).name
            _snapshot(source, target)
            if target.exists():
                manifest["files"][archive_name] = hashlib.sha256(target.read_bytes()).hexdigest()
        if include_uploads and RAW_DIR.exists():
            for source in RAW_DIR.rglob("*"):
                if source.is_file():
                    relative = source.resolve().relative_to(RAW_DIR.resolve())
                    archive_name = f"uploads/{relative.as_posix()}"
                    manifest["files"][archive_name] = hashlib.sha256(source.read_bytes()).hexdigest()
        with ZipFile(output, "x", ZIP_DEFLATED) as archive:
            for archive_name in sorted(manifest["files"]):
                if archive_name == "databases/product.db":
                    source = temp / "product.db"
                elif archive_name == "databases/vault.db":
                    source = temp / "vault.db"
                else:
                    source = RAW_DIR / Path(archive_name).relative_to("uploads")
                archive.write(source, archive_name)
            archive.writestr("manifest.json", json.dumps(manifest, indent=2))
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--without-uploads", action="store_true")
    args = parser.parse_args()
    manifest = create_backup(args.output, include_uploads=not args.without_uploads)
    print(json.dumps({"backup": str(args.output.resolve()), "file_count": len(manifest["files"])}, indent=2))


if __name__ == "__main__":
    main()
