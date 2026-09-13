from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


VAULT_ROOT = Path("app/storage/vault")


def _safe_child(root: Path, *parts: str) -> Path:
    resolved_root = root.resolve()
    path = resolved_root.joinpath(*parts).resolve()
    if not path.is_relative_to(resolved_root):
        raise ValueError("Unsafe vault path")
    return path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def _version_existing(matter_dir: Path) -> None:
    tracked = [matter_dir / "extracted.json", matter_dir / "provenance.json", matter_dir / "source.pdf"]
    if not any(path.exists() for path in tracked):
        return
    version_dir = matter_dir / "versions" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    version_dir.mkdir(parents=True, exist_ok=False)
    for path in tracked:
        if path.exists():
            shutil.copy2(path, version_dir / path.name)


def save_matter(
    tenant_id: str,
    matter_id: str,
    extracted: dict[str, Any],
    source_pdf_path: str | Path,
) -> dict[str, Any]:
    source_path = Path(source_pdf_path)
    if not source_path.is_file():
        raise FileNotFoundError(f"Source PDF not found: {source_path}")

    matter_dir = _safe_child(VAULT_ROOT, tenant_id, "matters", matter_id)
    matter_dir.mkdir(parents=True, exist_ok=True)
    _version_existing(matter_dir)

    stored_extracted = dict(extracted)
    stored_extracted["provenance_verified"] = False

    source_hash = _sha256(source_path)
    provenance = {
        "source_hash": source_hash,
        "source_filename": source_path.name,
        "extracted_at": datetime.now(timezone.utc).isoformat(),
        "provenance_verified": False,
    }

    stored_pdf = matter_dir / "source.pdf"
    shutil.copy2(source_path, stored_pdf)
    _write_json(matter_dir / "extracted.json", stored_extracted)
    _write_json(matter_dir / "provenance.json", provenance)

    return {
        "tenant_id": tenant_id,
        "matter_id": matter_id,
        "matter_dir": str(matter_dir),
        "extracted_file": str(matter_dir / "extracted.json"),
        "provenance_file": str(matter_dir / "provenance.json"),
        "source_pdf": str(stored_pdf),
        "source_hash": source_hash,
        "provenance_verified": False,
    }
