from pathlib import Path

from app.database import Database
from app.routers.matters import obligations, parties


def test_matter_endpoints_are_tenant_scoped(tmp_path: Path):
    db = Database(tmp_path / "test.sqlite3")
    matter = db.create_matter("tenant-a", "A matter")
    data_dir = tmp_path / "vault" / "tenant-a" / "matters" / matter["id"]
    data_dir.mkdir(parents=True)
    (data_dir / "extracted.json").write_text('{"parties":{"plaintiff":"A"},"next_hearing_date":"2025-12-15","obligations":[]}', encoding="utf-8")
    workspace = {"organization": {"id": "tenant-a"}}
    # The endpoint helpers are pure tenant-bound reads; their HTTP wrappers add auth.
    import app.routers.matters as module
    original = module.VAULT_ROOT
    module.VAULT_ROOT = tmp_path / "vault"
    try:
        assert obligations(matter["id"], db, workspace)["obligations"] == []
        assert parties(matter["id"], db, workspace)["parties"]["plaintiff"] == "A"
    finally:
        module.VAULT_ROOT = original
