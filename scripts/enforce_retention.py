"""Preview or enforce organization data-retention policies."""

from __future__ import annotations

import argparse
import json
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.config import RAW_DIR
from app.database import get_db
from database.connection import get_db_connection


def enforce_retention(apply: bool = False, now: datetime | None = None) -> dict:
    current = now or datetime.now(timezone.utc)
    report = {"mode": "apply" if apply else "dry-run", "organizations": []}
    vault = get_db()
    with get_db_connection() as conn:
        policies = conn.execute(
            "SELECT id, retention_days FROM organizations WHERE retention_days IS NOT NULL"
        ).fetchall()
        for policy in policies:
            cutoff = (current - timedelta(days=policy["retention_days"])).isoformat()
            conversations = conn.execute(
                "SELECT id FROM conversations WHERE organization_id = ? AND updated_at < ?",
                (policy["id"], cutoff),
            ).fetchall()
            documents = vault.list_documents(organization_id=policy["id"], limit=100000)
            expired_documents = [doc for doc in documents if doc["upload_time"] < cutoff]
            validated_paths: dict[str, Path] = {}
            for document in expired_documents:
                if document.get("raw_path"):
                    raw_path = Path(document["raw_path"]).resolve()
                    raw_path.relative_to(RAW_DIR.resolve())
                    validated_paths[document["id"]] = raw_path
            if apply:
                conn.execute(
                    "DELETE FROM conversations WHERE organization_id = ? AND updated_at < ?",
                    (policy["id"], cutoff),
                )
                for document in expired_documents:
                    if raw_path := validated_paths.get(document["id"]):
                        raw_path.unlink(missing_ok=True)
                    vault.delete_document(document["id"])
                conn.execute(
                    """INSERT INTO audit_events
                       (id, user_id, event_type, metadata_json, created_at, organization_id)
                       VALUES (?, NULL, 'RETENTION_ENFORCED', ?, ?, ?)""",
                    (
                        str(uuid.uuid4()),
                        json.dumps({"conversations": len(conversations), "documents": len(expired_documents)}),
                        current.isoformat(),
                        policy["id"],
                    ),
                )
            report["organizations"].append({
                "organization_id": policy["id"],
                "retention_days": policy["retention_days"],
                "conversations": len(conversations),
                "documents": len(expired_documents),
            })
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Delete expired data; default is dry-run")
    args = parser.parse_args()
    print(json.dumps(enforce_retention(apply=args.apply), indent=2))


if __name__ == "__main__":
    main()
