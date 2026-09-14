from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
STORAGE = ROOT / "app" / "storage"
VAULT = STORAGE / "vault"
BACKUPS = STORAGE / "backups"


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _iter_backup_files(tenant_id: str | None) -> list[Path]:
    files: list[Path] = []
    if tenant_id:
        tenant_root = VAULT / tenant_id
        if tenant_root.exists():
            files.extend(path for path in tenant_root.rglob("*") if path.is_file())
    elif VAULT.exists():
        files.extend(path for path in VAULT.rglob("*") if path.is_file())
    for extra in [STORAGE / "users.json", STORAGE / "notifications"]:
        if extra.is_file():
            files.append(extra)
        elif extra.is_dir():
            files.extend(path for path in extra.rglob("*") if path.is_file())
    return sorted(files)


def backup(tenant_id: str | None = None) -> Path:
    BACKUPS.mkdir(parents=True, exist_ok=True)
    label = tenant_id or "all"
    created = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    zip_path = BACKUPS / f"backup-{label}-{created}.zip"
    manifest: dict[str, Any] = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "tenant_id": tenant_id,
        "files": [],
        "note": "extracted.json provenance_verified:false values must be preserved",
        "provenance_verified": False,
    }
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in _iter_backup_files(tenant_id):
            rel = path.relative_to(ROOT).as_posix()
            data = path.read_bytes()
            archive.writestr(rel, data)
            manifest["files"].append({"path": rel, "sha256": _sha256_bytes(data), "bytes": len(data)})
        archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return zip_path


def restore(zip_path: str | Path) -> dict[str, Any]:
    source = Path(zip_path)
    if not source.is_file():
        raise FileNotFoundError(source)
    with zipfile.ZipFile(source) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        expected = {item["path"]: item["sha256"] for item in manifest.get("files", [])}
        for rel, digest in expected.items():
            data = archive.read(rel)
            if _sha256_bytes(data) != digest:
                raise ValueError(f"Backup integrity check failed for {rel}")
        for rel in expected:
            if rel == ".env" or rel.endswith("/.env"):
                continue
            target = (ROOT / rel).resolve()
            if not target.is_relative_to(ROOT.resolve()):
                raise ValueError(f"Unsafe restore path: {rel}")
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(rel) as src, target.open("wb") as dst:
                shutil.copyfileobj(src, dst)
    return {"restored": True, "files": len(expected), "provenance_verified": False}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tenant")
    parser.add_argument("--backup", action="store_true")
    parser.add_argument("--restore")
    args = parser.parse_args()
    if args.backup:
        print(backup(args.tenant))
    elif args.restore:
        print(json.dumps(restore(args.restore), sort_keys=True))
    else:
        parser.error("Use --backup or --restore ZIP_PATH")


if __name__ == "__main__":
    main()
