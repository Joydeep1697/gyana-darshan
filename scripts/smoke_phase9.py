from __future__ import annotations

import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app
from scripts.backup_vault import backup
from scripts.restore_verify import verify_backup


ROOT = Path(__file__).resolve().parents[1]
TENANT_ID = "personal-test"
MATTER_ID = "test-matter-001"
EXTRACTED_PATH = ROOT / "app" / "storage" / "vault" / TENANT_ID / "matters" / MATTER_ID / "extracted.json"


def _ensure_fixture() -> None:
    EXTRACTED_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not EXTRACTED_PATH.exists():
        EXTRACTED_PATH.write_text(
            json.dumps(
                {
                    "case_no": "CS 123/2024",
                    "court": "District Court",
                    "parties": {"plaintiff": "Asha Rao", "defendant": "Bharat Mehta"},
                    "next_hearing_date": "2025-12-15",
                    "obligations": [{"due_date": "2025-12-10", "description": "File written statement"}],
                    "risk_flags": [],
                    "provenance_verified": False,
                },
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )


def _docker_compose_config() -> bool:
    command = shutil.which("docker-compose")
    args = [command, "config"] if command else ["docker", "compose", "config"]
    try:
        subprocess.run(args, cwd=ROOT, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except (OSError, subprocess.CalledProcessError):
        return False


def main() -> None:
    _ensure_fixture()
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["status"] == "HEALTHY", body
        detailed = client.get("/health/detailed")
        assert detailed.status_code == 200, detailed.text
        assert detailed.json()["vault_writable"] is True, detailed.text

    zip_path = backup(TENANT_ID)
    verified = verify_backup(zip_path)
    assert verified["ok"] is True
    with zipfile.ZipFile(zip_path) as archive:
        assert "manifest.json" in archive.namelist()
        extracted_names = [name for name in archive.namelist() if name.endswith("extracted.json")]
        assert extracted_names, archive.namelist()
        for name in extracted_names:
            payload = json.loads(archive.read(name).decode("utf-8"))
            assert payload["provenance_verified"] is False

    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert "JWT_SECRET=" in env_example
    assert "TENANT_ENCRYPTION_KEY=" in env_example
    settings = get_settings()
    assert settings.storage_dir
    assert (ROOT / "frontend" / "dist" / "index.html").exists()
    compose_ok = _docker_compose_config()
    print(f"docker_compose_config={'ok' if compose_ok else 'skipped'}")
    print("SMOKE PASSED")


if __name__ == "__main__":
    main()
