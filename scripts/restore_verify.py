from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path


def verify_backup(zip_path: str | Path) -> dict:
    source = Path(zip_path)
    with zipfile.ZipFile(source) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        for item in manifest.get("files", []):
            data = archive.read(item["path"])
            if hashlib.sha256(data).hexdigest() != item["sha256"]:
                raise ValueError(f"sha256 mismatch: {item['path']}")
            if item["path"].endswith("extracted.json"):
                payload = json.loads(data.decode("utf-8"))
                if payload.get("provenance_verified") is not False:
                    raise ValueError(f"provenance_verified was not false in {item['path']}")
    return {"ok": True, "files": len(manifest.get("files", [])), "provenance_verified": False}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("zip_path")
    args = parser.parse_args()
    print(json.dumps(verify_backup(args.zip_path), sort_keys=True))


if __name__ == "__main__":
    main()
