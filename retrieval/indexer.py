"""Tenant-scoped retrieval index builder for public fallback and Vault files."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
CORPUS_ROOT = ROOT / "corpus_integrity"
CORPUS_BNS = CORPUS_ROOT / "bns" / "section_103.md"
PUBLIC_CORPUS_DIRS = ("bns", "bnss", "bsa", "egazette", "prs")
VAULT_ROOT = ROOT / "app" / "storage" / "vault"
INDEX_ROOT = ROOT / "app" / "storage" / "retrieval_index"
INGESTION_LOG = ROOT / "app" / "ingestion" / "ingestion_log.jsonl"


@dataclass(frozen=True)
class IndexedChunk:
    chunk_id: str
    tenant_id: str
    text: str
    source_url: str
    file_path: str
    fetched_with: str
    provenance_verified: bool
    ingestion_date: str
    matter_id: str | None = None
    evidence_html_path: str | None = None
    evidence_screenshot_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _safe_tenant(tenant_id: str) -> str:
    if not tenant_id or not re.fullmatch(r"[A-Za-z0-9_.:-]+", tenant_id):
        raise ValueError("tenant_id contains unsupported characters")
    return tenant_id


def index_path(tenant_id: str) -> Path:
    return INDEX_ROOT / f"{_safe_tenant(tenant_id)}.jsonl"


def _frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    metadata: dict[str, str] = {}
    for line in parts[1].splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            metadata[key.strip()] = value.strip()
    return metadata, parts[2].strip()


def _tokens(text: str) -> list[str]:
    return re.findall(r"\w+|[^\w\s]", text)


def _chunk_text(text: str, *, size: int = 500, overlap: int = 50) -> Iterable[str]:
    tokens = _tokens(text)
    if not tokens:
        return
    step = max(1, size - overlap)
    for start in range(0, len(tokens), step):
        chunk = " ".join(tokens[start:start + size]).strip()
        if chunk:
            yield re.sub(r"\s+([.,;:!?])", r"\1", chunk)


def _read_pdf(path: Path) -> str:
    try:
        import fitz  # PyMuPDF, already in requirements
    except Exception:
        return ""
    try:
        with fitz.open(path) as doc:
            return "\n".join(page.get_text("text") for page in doc)
    except Exception:
        return ""


def _read_text(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        return _read_pdf(path)
    if path.suffix.lower() == ".json":
        try:
            return json.dumps(json.loads(path.read_text(encoding="utf-8")), ensure_ascii=True, indent=2)
        except (OSError, json.JSONDecodeError):
            return ""
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _human_task_evidence() -> dict[str, dict[str, str]]:
    evidence: dict[str, dict[str, str]] = {}
    if not INGESTION_LOG.exists():
        return evidence
    for line in INGESTION_LOG.read_text(encoding="utf-8", errors="ignore").splitlines():
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        task_id = item.get("file") or item.get("file_path")
        if item.get("status") == "HUMAN_TASK_CREATED" and task_id:
            evidence[str(task_id)] = {
                "source_url": item.get("source_url") or "",
                "evidence_html_path": item.get("evidence_html") or "",
                "evidence_screenshot_path": item.get("evidence_screenshot") or "",
            }
    return evidence


def _metadata_for_path(path: Path, tenant_id: str) -> dict[str, Any]:
    rel = path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else str(path)
    now = datetime.now(timezone.utc).isoformat()
    if path.is_relative_to(CORPUS_ROOT):
        meta, _ = _frontmatter(_read_text(path))
        source_folder = path.relative_to(CORPUS_ROOT).parts[0] if path.relative_to(CORPUS_ROOT).parts else ""
        fetched_with = meta.get("fetched_with") or ("needs_human_action" if source_folder in {"egazette", "prs"} else "jsonl_fallback")
        provenance_value = (meta.get("provenance_verified") or "false").strip().lower()
        return {
            "tenant_id": tenant_id,
            "source_url": meta.get("source_url", ""),
            "fetched_with": fetched_with,
            "provenance_verified": provenance_value == "true",
            "ingestion_date": meta.get("fetched_at") or now,
            "file_path": rel,
            "matter_id": None,
            "evidence_html_path": meta.get("evidence_html_path") or None,
            "evidence_screenshot_path": meta.get("evidence_screenshot_path") or None,
        }
    parts = path.parts
    matter_id = None
    if "matters" in parts:
        idx = parts.index("matters")
        if idx + 1 < len(parts):
            matter_id = parts[idx + 1]
    fetched_with = "live_upload"
    provenance_verified = True
    if "ecourts" in parts:
        fetched_with = "live_upload"
    return {
        "tenant_id": tenant_id,
        "source_url": "",
        "fetched_with": fetched_with,
        "provenance_verified": provenance_verified,
        "ingestion_date": now,
        "file_path": rel,
        "matter_id": matter_id,
    }


def _tenant_files(tenant_id: str) -> list[Path]:
    safe = _safe_tenant(tenant_id)
    files: list[Path] = []
    for folder in PUBLIC_CORPUS_DIRS:
        corpus_dir = CORPUS_ROOT / folder
        if corpus_dir.exists():
            for path in corpus_dir.rglob("*"):
                if path.is_file() and path.suffix.lower() in {".md", ".txt", ".html", ".json"}:
                    files.append(path)
    tenant_root = (VAULT_ROOT / safe).resolve()
    if tenant_root.exists() and tenant_root.is_relative_to(VAULT_ROOT.resolve()):
        for path in tenant_root.rglob("*"):
            if path.is_file() and path.suffix.lower() in {".pdf", ".md", ".txt", ".json"}:
                files.append(path)
    return files


def chunks_for_tenant(tenant_id: str) -> list[IndexedChunk]:
    chunks: list[IndexedChunk] = []
    for path in _tenant_files(tenant_id):
        text = _read_text(path)
        if not text.strip():
            continue
        frontmatter, body = _frontmatter(text)
        meta = _metadata_for_path(path, tenant_id)
        if path.is_relative_to(CORPUS_ROOT):
            parts = path.relative_to(CORPUS_ROOT).parts
            source_label = parts[0].upper() if parts else "CORPUS"
            body = f"{source_label} statutory corpus public evidence\n{body}"
        for idx, chunk in enumerate(_chunk_text(body)):
            digest = hashlib.sha256(f"{tenant_id}:{path}:{idx}:{chunk[:80]}".encode("utf-8")).hexdigest()[:24]
            chunks.append(IndexedChunk(chunk_id=digest, text=chunk, **meta))
    return chunks


def index_tenant_files(tenant_id: str) -> list[dict[str, Any]]:
    chunks = chunks_for_tenant(tenant_id)
    path = index_path(tenant_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for chunk in chunks:
            handle.write(json.dumps(chunk.to_dict(), ensure_ascii=False) + "\n")
    return [chunk.to_dict() for chunk in chunks]


def load_tenant_index(tenant_id: str, *, refresh: bool = True) -> list[dict[str, Any]]:
    path = index_path(tenant_id)
    if refresh or not path.exists():
        return index_tenant_files(tenant_id)
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows
