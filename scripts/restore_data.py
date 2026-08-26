"""Validate and restore a Nyaya Darshana backup while the application is stopped."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
from pathlib import Path, PurePosixPath
from zipfile import ZipFile

from app.config import APP_DB_PATH, RAW_DIR
from database.connection import SQLITE_DB_PATH


def validate_backup(backup: Path) -> dict:
    with ZipFile(backup) as archive:
        names = set(archive.namelist())
        if "manifest.json" not in names:
            raise ValueError("Backup manifest is missing")
        manifest = json.loads(archive.read("manifest.json"))
        if manifest.get("format") != "nyaya-backup-v1":
            raise ValueError("Unsupported backup format")
        for name, expected_hash in manifest.get("files", {}).items():
            path = PurePosixPath(name)
            if path.is_absolute() or ".." in path.parts or name not in names:
                raise ValueError(f"Unsafe or missing backup entry: {name}")
            actual_hash = hashlib.sha256(archive.read(name)).hexdigest()
            if actual_hash != expected_hash:
                raise ValueError(f"Checksum mismatch: {name}")
    return manifest


def restore_backup(backup: Path, confirmation: str) -> None:
    if confirmation != "RESTORE_NYAYA_DATA":
        raise ValueError("Pass --confirm RESTORE_NYAYA_DATA to authorize replacement")
    manifest = validate_backup(backup)
    with tempfile.TemporaryDirectory(prefix="nyaya-restore-") as temp_value, ZipFile(backup) as archive:
        temp = Path(temp_value)
        for name in manifest["files"]:
            destination = temp / Path(*PurePosixPath(name).parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(archive.read(name))
        mappings = {
            "databases/product.db": SQLITE_DB_PATH,
            "databases/vault.db": APP_DB_PATH,
        }
        for archive_name, target in mappings.items():
            source = temp / Path(archive_name)
            if archive_name in manifest["files"]:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
        for name in manifest["files"]:
            if name.startswith("uploads/"):
                relative = Path(*PurePosixPath(name).parts[1:])
                target = (RAW_DIR / relative).resolve()
                target.relative_to(RAW_DIR.resolve())
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(temp / Path(name), target)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("backup", type=Path)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--confirm", default="")
    args = parser.parse_args()
    manifest = validate_backup(args.backup)
    if not args.validate_only:
        restore_backup(args.backup, args.confirm)
    print(json.dumps({"valid": True, "created_at": manifest["created_at"], "restored": not args.validate_only}, indent=2))


if __name__ == "__main__":
    main()
