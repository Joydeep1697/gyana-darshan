"""Nyaya Darshan — Application Database.

Manages the web-application SQLite database (``nova_app.sqlite3``).
This is separate from the existing classifier/RAG databases and tracks:
  - Vault document state & metadata
  - Chat sessions & messages
  - Knowledge graph edges
  - Extracted entities, clauses, deadlines
  - Compliance gaps & activity log
  - Search analytics
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Generator, Optional

from app.config import APP_DB_PATH

# ── Schema ────────────────────────────────────────────────────────

_SCHEMA = """
-- Vault documents (tracks every uploaded PDF through the processing pipeline)
CREATE TABLE IF NOT EXISTS vault_documents (
    id              TEXT PRIMARY KEY,
    filename        TEXT NOT NULL,
    sha256          TEXT,
    file_size       INTEGER DEFAULT 0,
    status          TEXT DEFAULT 'uploading',   -- uploading/extracting/parsing/classifying/entities/clauses/linking/indexing/indexed/failed
    category        TEXT,
    domain          TEXT,
    authority_level TEXT,
    authority_weight REAL DEFAULT 1.0,
    risk_score      INTEGER DEFAULT 0,          -- 0-100
    pages           INTEGER DEFAULT 0,
    clauses_count   INTEGER DEFAULT 0,
    citations_count INTEGER DEFAULT 0,
    summary         TEXT,                       -- AI-generated summary (cached)
    raw_path        TEXT,                       -- path in raw/
    category_path   TEXT,                       -- path in Category/<cat>/
    error_msg       TEXT,
    upload_time     TEXT NOT NULL,
    process_time    TEXT
);

-- Extracted entities (courts, judges, parties, sections, etc.)
CREATE TABLE IF NOT EXISTS document_entities (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id          TEXT NOT NULL REFERENCES vault_documents(id) ON DELETE CASCADE,
    entity_type     TEXT NOT NULL,              -- court/judge/party_petitioner/party_respondent/section/rule/article/citation/notification/act_name/year/decision_date/case_number
    entity_value    TEXT NOT NULL,
    context_snippet TEXT
);
CREATE INDEX IF NOT EXISTS idx_entities_doc ON document_entities(doc_id);
CREATE INDEX IF NOT EXISTS idx_entities_type ON document_entities(entity_type);

-- Detected legal clauses
CREATE TABLE IF NOT EXISTS document_clauses (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id          TEXT NOT NULL REFERENCES vault_documents(id) ON DELETE CASCADE,
    clause_type     TEXT NOT NULL,              -- indemnity/limitation_of_liability/force_majeure/termination/confidentiality/governing_law/arbitration/ip_assignment/non_compete/data_protection
    clause_text     TEXT NOT NULL,
    risk_level      TEXT DEFAULT 'low',         -- low/medium/high
    start_page      INTEGER
);
CREATE INDEX IF NOT EXISTS idx_clauses_doc ON document_clauses(doc_id);

-- Deadlines extracted from documents
CREATE TABLE IF NOT EXISTS document_deadlines (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id          TEXT NOT NULL REFERENCES vault_documents(id) ON DELETE CASCADE,
    deadline_type   TEXT NOT NULL,              -- filing/renewal/expiry/limitation/compliance
    deadline_date   TEXT,                       -- ISO date
    description     TEXT,
    status          TEXT DEFAULT 'upcoming'     -- upcoming/overdue/cleared
);
CREATE INDEX IF NOT EXISTS idx_deadlines_doc ON document_deadlines(doc_id);
CREATE INDEX IF NOT EXISTS idx_deadlines_date ON document_deadlines(deadline_date);

-- Knowledge graph edges (citation links between documents)
CREATE TABLE IF NOT EXISTS knowledge_graph (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source_doc_id   TEXT NOT NULL REFERENCES vault_documents(id) ON DELETE CASCADE,
    target_doc_id   TEXT REFERENCES vault_documents(id) ON DELETE SET NULL,
    relationship    TEXT NOT NULL,              -- cites/amends/repeals/supersedes/interprets/conflicts_with/applies
    source_ref      TEXT,                       -- e.g. "Section 12 of RTI Act"
    target_ref      TEXT,                       -- matched reference in target doc
    confidence      REAL DEFAULT 0.5
);
CREATE INDEX IF NOT EXISTS idx_kg_source ON knowledge_graph(source_doc_id);
CREATE INDEX IF NOT EXISTS idx_kg_target ON knowledge_graph(target_doc_id);

-- Global section index (all section/rule/article refs across corpus)
CREATE TABLE IF NOT EXISTS section_index (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    section_ref     TEXT NOT NULL,              -- e.g. "Section 302 IPC"
    doc_id          TEXT NOT NULL REFERENCES vault_documents(id) ON DELETE CASCADE,
    context_type    TEXT DEFAULT 'citing',      -- defining/citing/amending/interpreting
    snippet         TEXT
);
CREATE INDEX IF NOT EXISTS idx_sections_ref ON section_index(section_ref);
CREATE INDEX IF NOT EXISTS idx_sections_doc ON section_index(doc_id);

-- Organization-scoped case-law metadata indexed from uploaded judgments
CREATE TABLE IF NOT EXISTS case_law_records (
    id                  TEXT PRIMARY KEY,
    organization_id     TEXT NOT NULL,
    document_id         TEXT NOT NULL REFERENCES vault_documents(id) ON DELETE CASCADE,
    title               TEXT NOT NULL,
    citation            TEXT DEFAULT '',
    court               TEXT DEFAULT '',
    judges_json         TEXT DEFAULT '[]',
    petitioner          TEXT DEFAULT '',
    respondent          TEXT DEFAULT '',
    case_number         TEXT DEFAULT '',
    decision_date       TEXT DEFAULT '',
    year                INTEGER,
    sections_json       TEXT DEFAULT '[]',
    source_excerpt      TEXT DEFAULT '',
    source_page         INTEGER DEFAULT 1,
    created_at          TEXT NOT NULL,
    updated_at          TEXT NOT NULL,
    UNIQUE(organization_id, document_id)
);
CREATE INDEX IF NOT EXISTS idx_case_law_org ON case_law_records(organization_id);
CREATE INDEX IF NOT EXISTS idx_case_law_citation ON case_law_records(citation);
CREATE INDEX IF NOT EXISTS idx_case_law_court ON case_law_records(court);
CREATE INDEX IF NOT EXISTS idx_case_law_year ON case_law_records(year);

-- Curated case-law corpus records with explicit provenance
CREATE TABLE IF NOT EXISTS case_law_corpus_records (
    id                  TEXT PRIMARY KEY,
    corpus_key          TEXT NOT NULL UNIQUE,
    title               TEXT NOT NULL,
    citation            TEXT DEFAULT '',
    court               TEXT DEFAULT '',
    judges_json         TEXT DEFAULT '[]',
    petitioner          TEXT DEFAULT '',
    respondent          TEXT DEFAULT '',
    case_number         TEXT DEFAULT '',
    decision_date       TEXT DEFAULT '',
    year                INTEGER,
    sections_json       TEXT DEFAULT '[]',
    paragraphs_json     TEXT DEFAULT '[]',
    source_excerpt      TEXT DEFAULT '',
    source_page         INTEGER DEFAULT 1,
    source_name         TEXT NOT NULL,
    source_url          TEXT DEFAULT '',
    provenance_status   TEXT DEFAULT 'unverified',
    created_at          TEXT NOT NULL,
    updated_at          TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_case_law_corpus_citation ON case_law_corpus_records(citation);
CREATE INDEX IF NOT EXISTS idx_case_law_corpus_court ON case_law_corpus_records(court);
CREATE INDEX IF NOT EXISTS idx_case_law_corpus_year ON case_law_corpus_records(year);
CREATE INDEX IF NOT EXISTS idx_case_law_corpus_status ON case_law_corpus_records(provenance_status);

-- Chat sessions
CREATE TABLE IF NOT EXISTS chat_sessions (
    id              TEXT PRIMARY KEY,
    title           TEXT DEFAULT 'New Conversation',
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);

-- Chat messages
CREATE TABLE IF NOT EXISTS chat_messages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role            TEXT NOT NULL,              -- user/assistant/system
    content         TEXT NOT NULL,
    sources_json    TEXT,                       -- JSON array of source objects
    follow_ups_json TEXT,                       -- JSON array of follow-up questions
    reasoning_json  TEXT,                       -- JSON array of reasoning steps
    created_at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_messages_session ON chat_messages(session_id);

-- Activity log
CREATE TABLE IF NOT EXISTS activity_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    action          TEXT NOT NULL,              -- upload/classify/search/chat/scan/error
    detail          TEXT,
    doc_id          TEXT,
    timestamp       TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_activity_time ON activity_log(timestamp);

-- Compliance gaps
CREATE TABLE IF NOT EXISTS compliance_gaps (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_id TEXT,
    domain          TEXT NOT NULL,
    gap_description TEXT NOT NULL,
    severity        TEXT DEFAULT 'medium',      -- low/medium/high/critical
    detected_at     TEXT NOT NULL
);



-- Legal operations matters
CREATE TABLE IF NOT EXISTS legal_matters (
    id              TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    title           TEXT NOT NULL,
    matter_type     TEXT DEFAULT 'general',
    status          TEXT DEFAULT 'open',
    priority        TEXT DEFAULT 'medium',
    description     TEXT DEFAULT '',
    owner_user_id   TEXT,
    due_date        TEXT,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_legal_matters_org ON legal_matters(organization_id);
CREATE INDEX IF NOT EXISTS idx_legal_matters_status ON legal_matters(status);



-- Documents linked to legal matters
CREATE TABLE IF NOT EXISTS legal_matter_documents (
    id              TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    matter_id       TEXT NOT NULL REFERENCES legal_matters(id) ON DELETE CASCADE,
    document_id     TEXT NOT NULL REFERENCES vault_documents(id) ON DELETE CASCADE,
    created_at      TEXT NOT NULL,
    UNIQUE(matter_id, document_id)
);
CREATE INDEX IF NOT EXISTS idx_legal_matter_documents_org ON legal_matter_documents(organization_id);
CREATE INDEX IF NOT EXISTS idx_legal_matter_documents_matter ON legal_matter_documents(matter_id);

-- Matter notes and timeline entries
CREATE TABLE IF NOT EXISTS legal_matter_notes (
    id              TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    matter_id       TEXT NOT NULL REFERENCES legal_matters(id) ON DELETE CASCADE,
    author_user_id  TEXT,
    body            TEXT NOT NULL,
    created_at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_legal_matter_notes_org ON legal_matter_notes(organization_id);
CREATE INDEX IF NOT EXISTS idx_legal_matter_notes_matter ON legal_matter_notes(matter_id);

-- Legal intake requests
CREATE TABLE IF NOT EXISTS legal_intake_requests (
    id              TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    matter_id       TEXT REFERENCES legal_matters(id) ON DELETE SET NULL,
    requester_user_id TEXT,
    request_type    TEXT DEFAULT 'general',
    title           TEXT NOT NULL,
    summary         TEXT DEFAULT '',
    urgency         TEXT DEFAULT 'medium',
    status          TEXT DEFAULT 'new',
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_legal_intake_org ON legal_intake_requests(organization_id);
CREATE INDEX IF NOT EXISTS idx_legal_intake_status ON legal_intake_requests(status);

-- Legal tasks
CREATE TABLE IF NOT EXISTS legal_tasks (
    id              TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    matter_id       TEXT REFERENCES legal_matters(id) ON DELETE SET NULL,
    title           TEXT NOT NULL,
    status          TEXT DEFAULT 'open',
    priority        TEXT DEFAULT 'medium',
    assignee_user_id TEXT,
    due_date        TEXT,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_legal_tasks_org ON legal_tasks(organization_id);
CREATE INDEX IF NOT EXISTS idx_legal_tasks_matter ON legal_tasks(matter_id);

-- Contract lifecycle records
CREATE TABLE IF NOT EXISTS legal_contracts (
    id              TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    document_id     TEXT REFERENCES vault_documents(id) ON DELETE SET NULL,
    matter_id       TEXT REFERENCES legal_matters(id) ON DELETE SET NULL,
    title           TEXT NOT NULL,
    counterparty    TEXT DEFAULT '',
    contract_type   TEXT DEFAULT 'general',
    status          TEXT DEFAULT 'draft',
    risk_level      TEXT DEFAULT 'unknown',
    effective_date  TEXT,
    expiry_date     TEXT,
    renewal_date    TEXT,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_legal_contracts_org ON legal_contracts(organization_id);
CREATE INDEX IF NOT EXISTS idx_legal_contracts_status ON legal_contracts(status);

-- Contract obligations
CREATE TABLE IF NOT EXISTS legal_contract_obligations (
    id              TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    contract_id     TEXT NOT NULL REFERENCES legal_contracts(id) ON DELETE CASCADE,
    matter_id       TEXT REFERENCES legal_matters(id) ON DELETE SET NULL,
    title           TEXT NOT NULL,
    owner           TEXT DEFAULT '',
    category        TEXT DEFAULT 'general',
    status          TEXT DEFAULT 'open',
    priority        TEXT DEFAULT 'medium',
    due_date        TEXT,
    source_clause   TEXT DEFAULT '',
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_legal_contract_obligations_org ON legal_contract_obligations(organization_id);
CREATE INDEX IF NOT EXISTS idx_legal_contract_obligations_contract ON legal_contract_obligations(contract_id);
CREATE INDEX IF NOT EXISTS idx_legal_contract_obligations_matter ON legal_contract_obligations(matter_id);
CREATE INDEX IF NOT EXISTS idx_legal_contract_obligations_status ON legal_contract_obligations(status);

-- Legal vendors and outside counsel
CREATE TABLE IF NOT EXISTS legal_vendors (
    id              TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    name            TEXT NOT NULL,
    vendor_type     TEXT DEFAULT 'outside_counsel',
    contact_email   TEXT DEFAULT '',
    practice_area   TEXT DEFAULT '',
    status          TEXT DEFAULT 'active',
    hourly_rate     REAL DEFAULT 0,
    currency        TEXT DEFAULT 'INR',
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_legal_vendors_org ON legal_vendors(organization_id);
CREATE INDEX IF NOT EXISTS idx_legal_vendors_status ON legal_vendors(status);

-- Legal spend and invoice tracking
CREATE TABLE IF NOT EXISTS legal_spend_entries (
    id              TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    matter_id       TEXT REFERENCES legal_matters(id) ON DELETE SET NULL,
    vendor_id       TEXT REFERENCES legal_vendors(id) ON DELETE SET NULL,
    invoice_number  TEXT DEFAULT '',
    description     TEXT DEFAULT '',
    amount          REAL NOT NULL,
    currency        TEXT DEFAULT 'INR',
    status          TEXT DEFAULT 'pending',
    issue_date      TEXT,
    due_date        TEXT,
    paid_date       TEXT,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_legal_spend_org ON legal_spend_entries(organization_id);
CREATE INDEX IF NOT EXISTS idx_legal_spend_matter ON legal_spend_entries(matter_id);
CREATE INDEX IF NOT EXISTS idx_legal_spend_vendor ON legal_spend_entries(vendor_id);
CREATE INDEX IF NOT EXISTS idx_legal_spend_status ON legal_spend_entries(status);

-- Legal team playbooks and institutional guidance
CREATE TABLE IF NOT EXISTS legal_playbooks (
    id              TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    title           TEXT NOT NULL,
    playbook_type   TEXT DEFAULT 'general',
    body            TEXT DEFAULT '',
    tags            TEXT DEFAULT '',
    status          TEXT DEFAULT 'active',
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_legal_playbooks_org ON legal_playbooks(organization_id);
CREATE INDEX IF NOT EXISTS idx_legal_playbooks_type ON legal_playbooks(playbook_type);
CREATE INDEX IF NOT EXISTS idx_legal_playbooks_status ON legal_playbooks(status);

-- Search analytics
CREATE TABLE IF NOT EXISTS search_analytics (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    query           TEXT NOT NULL,
    result_count    INTEGER DEFAULT 0,
    timestamp       TEXT NOT NULL
);
"""


# ── Database Manager ──────────────────────────────────────────────

class Database:
    """Thread-safe SQLite database manager for the Nyaya Darshan web app."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or APP_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _init_schema(self) -> None:
        with self.connect() as conn:
            conn.executescript(_SCHEMA)
            columns = {row["name"] for row in conn.execute("PRAGMA table_info(vault_documents)")}
            if "owner_id" not in columns:
                conn.execute("ALTER TABLE vault_documents ADD COLUMN owner_id TEXT")
            if "organization_id" not in columns:
                conn.execute("ALTER TABLE vault_documents ADD COLUMN organization_id TEXT")
            conn.execute(
                """UPDATE vault_documents SET organization_id = 'personal-' || owner_id
                   WHERE organization_id IS NULL AND owner_id IS NOT NULL"""
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_vault_documents_owner ON vault_documents(owner_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_vault_documents_org ON vault_documents(organization_id)")
            gap_columns = {row["name"] for row in conn.execute("PRAGMA table_info(compliance_gaps)")}
            if "organization_id" not in gap_columns:
                conn.execute("ALTER TABLE compliance_gaps ADD COLUMN organization_id TEXT")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_compliance_gaps_org ON compliance_gaps(organization_id)")

    @contextmanager
    def connect(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(str(self.db_path), timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # ── Helpers ───────────────────────────────────────────────────

    @staticmethod
    def new_id() -> str:
        return str(uuid.uuid4())

    @staticmethod
    def now() -> str:
        return datetime.now(timezone.utc).isoformat()

    # ── Vault Documents ───────────────────────────────────────────

    def create_document(self, filename: str, file_size: int, raw_path: str, owner_id: Optional[str] = None, organization_id: Optional[str] = None) -> str:
        doc_id = self.new_id()
        with self.connect() as conn:
            conn.execute(
                """INSERT INTO vault_documents
                   (id, filename, file_size, status, raw_path, upload_time, owner_id, organization_id)
                   VALUES (?, ?, ?, 'uploading', ?, ?, ?, ?)""",
                (doc_id, filename, file_size, raw_path, self.now(), owner_id, organization_id or (f"personal-{owner_id}" if owner_id else None)),
            )
        self.log_activity("upload", f"Uploaded {filename}", doc_id)
        return doc_id

    def update_document(self, doc_id: str, **kwargs: Any) -> None:
        if not kwargs:
            return
        permitted = {"sha256", "file_size", "status", "category", "domain", "authority_level", "authority_weight", "risk_score", "pages", "clauses_count", "citations_count", "summary", "raw_path", "category_path", "error_msg", "process_time"}
        if invalid := set(kwargs) - permitted:
            raise ValueError(f"Unsupported document update fields: {', '.join(sorted(invalid))}")
        cols = ", ".join(f"{k} = ?" for k in kwargs)
        vals = list(kwargs.values()) + [doc_id]
        with self.connect() as conn:
            conn.execute(f"UPDATE vault_documents SET {cols} WHERE id = ?", vals)

    def get_document(self, doc_id: str) -> Optional[dict]:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM vault_documents WHERE id = ?", (doc_id,)
            ).fetchone()
            return dict(row) if row else None

    def list_documents(
        self,
        status: Optional[str] = None,
        category: Optional[str] = None,
        domain: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        owner_id: Optional[str] = None,
        organization_id: Optional[str] = None,
    ) -> list[dict]:
        query = "SELECT * FROM vault_documents WHERE 1=1"
        params: list[Any] = []
        if organization_id is not None:
            query += " AND organization_id = ?"
            params.append(organization_id)
        elif owner_id is not None:
            query += " AND owner_id = ?"
            params.append(owner_id)
        if status:
            query += " AND status = ?"
            params.append(status)
        if category:
            query += " AND category = ?"
            params.append(category)
        if domain:
            query += " AND domain = ?"
            params.append(domain)
        query += " ORDER BY upload_time DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        with self.connect() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    def search_documents(
        self,
        query: str,
        *,
        owner_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        category: Optional[str] = None,
        domain: Optional[str] = None,
        limit: int = 20,
    ) -> list[dict]:
        """Search only metadata and cached summaries owned by one account."""
        needle = f"%{query.strip()}%"
        sql = """
            SELECT * FROM vault_documents
            WHERE organization_id = ?
              AND (
                filename LIKE ? COLLATE NOCASE
                OR COALESCE(category, '') LIKE ? COLLATE NOCASE
                OR COALESCE(domain, '') LIKE ? COLLATE NOCASE
                OR COALESCE(summary, '') LIKE ? COLLATE NOCASE
              )
        """
        scope_id = organization_id or (f"personal-{owner_id}" if owner_id else None)
        if not scope_id:
            raise ValueError("A workspace scope is required")
        params: list[Any] = [scope_id, needle, needle, needle, needle]
        if category:
            sql += " AND category = ?"
            params.append(category)
        if domain:
            sql += " AND domain = ?"
            params.append(domain)
        sql += " ORDER BY upload_time DESC LIMIT ?"
        params.append(max(1, min(limit, 100)))
        with self.connect() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [dict(row) for row in rows]

    def count_documents(self, status: Optional[str] = None) -> int:
        query = "SELECT COUNT(*) FROM vault_documents"
        params: list[Any] = []
        if status:
            query += " WHERE status = ?"
            params.append(status)
        with self.connect() as conn:
            return conn.execute(query, params).fetchone()[0]

    def delete_document(self, doc_id: str) -> bool:
        with self.connect() as conn:
            cur = conn.execute("DELETE FROM vault_documents WHERE id = ?", (doc_id,))
            deleted = cur.rowcount > 0
        if deleted:
            self.log_activity("delete", f"Deleted document {doc_id}", doc_id)
        return deleted

    def get_document_stats(self, owner_id: Optional[str] = None, organization_id: Optional[str] = None) -> dict:
        with self.connect() as conn:
            scope_column = "organization_id" if organization_id is not None else "owner_id"
            scope_value = organization_id if organization_id is not None else owner_id
            scope = f" WHERE {scope_column} = ?" if scope_value is not None else ""
            args = (scope_value,) if scope_value is not None else ()
            total = conn.execute("SELECT COUNT(*) FROM vault_documents" + scope, args).fetchone()[0]
            indexed = conn.execute(
                "SELECT COUNT(*) FROM vault_documents WHERE status = 'indexed'" + (f" AND {scope_column} = ?" if scope_value is not None else ""), args
            ).fetchone()[0]
            failed = conn.execute(
                "SELECT COUNT(*) FROM vault_documents WHERE status = 'failed'" + (f" AND {scope_column} = ?" if scope_value is not None else ""), args
            ).fetchone()[0]
            processing = total - indexed - failed
            cats = conn.execute(
                "SELECT category, COUNT(*) as cnt FROM vault_documents WHERE category IS NOT NULL" + (f" AND {scope_column} = ?" if scope_value is not None else "") + " GROUP BY category ORDER BY cnt DESC", args
            ).fetchall()
            domains = conn.execute(
                "SELECT domain, COUNT(*) as cnt FROM vault_documents WHERE domain IS NOT NULL" + (f" AND {scope_column} = ?" if scope_value is not None else "") + " GROUP BY domain ORDER BY cnt DESC", args
            ).fetchall()
            avg_risk = conn.execute(
                "SELECT AVG(risk_score) FROM vault_documents WHERE risk_score > 0" + (f" AND {scope_column} = ?" if scope_value is not None else ""), args
            ).fetchone()[0] or 0
            total_pages = conn.execute(
                "SELECT SUM(pages) FROM vault_documents" + scope, args
            ).fetchone()[0] or 0
            total_clauses = conn.execute(
                "SELECT SUM(clauses_count) FROM vault_documents" + scope, args
            ).fetchone()[0] or 0
            return {
                "total_documents": total,
                "indexed": indexed,
                "processing": processing,
                "failed": failed,
                "avg_risk_score": round(avg_risk, 1),
                "total_pages": total_pages,
                "total_clauses": total_clauses,
                "categories": {r["category"]: r["cnt"] for r in cats},
                "domains": {r["domain"]: r["cnt"] for r in domains},
            }

    # ── Entities ──────────────────────────────────────────────────

    def add_entities(self, doc_id: str, entities: list[dict]) -> None:
        with self.connect() as conn:
            conn.executemany(
                """INSERT INTO document_entities (doc_id, entity_type, entity_value, context_snippet)
                   VALUES (?, ?, ?, ?)""",
                [(doc_id, e["type"], e["value"], e.get("snippet")) for e in entities],
            )

    def get_entities(self, doc_id: str) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM document_entities WHERE doc_id = ?", (doc_id,)
            ).fetchall()
            return [dict(r) for r in rows]

    # ── Clauses ───────────────────────────────────────────────────

    def add_clauses(self, doc_id: str, clauses: list[dict]) -> None:
        with self.connect() as conn:
            conn.executemany(
                """INSERT INTO document_clauses (doc_id, clause_type, clause_text, risk_level, start_page)
                   VALUES (?, ?, ?, ?, ?)""",
                [(doc_id, c["type"], c["text"], c.get("risk", "low"), c.get("page")) for c in clauses],
            )

    def get_clauses(self, doc_id: str) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM document_clauses WHERE doc_id = ?", (doc_id,)
            ).fetchall()
            return [dict(r) for r in rows]

    # ── Deadlines ─────────────────────────────────────────────────

    def add_deadlines(self, doc_id: str, deadlines: list[dict]) -> None:
        with self.connect() as conn:
            conn.executemany(
                """INSERT INTO document_deadlines (doc_id, deadline_type, deadline_date, description, status)
                   VALUES (?, ?, ?, ?, ?)""",
                [
                    (doc_id, d["type"], d.get("date"), d.get("description"), d.get("status", "upcoming"))
                    for d in deadlines
                ],
            )

    def get_deadlines(
        self,
        status: Optional[str] = None,
        doc_id: Optional[str] = None,
        owner_id: Optional[str] = None,
        organization_id: Optional[str] = None,
    ) -> list[dict]:
        query = "SELECT d.*, v.filename FROM document_deadlines d JOIN vault_documents v ON d.doc_id = v.id WHERE 1=1"
        params: list[Any] = []
        if organization_id is not None:
            query += " AND v.organization_id = ?"
            params.append(organization_id)
        elif owner_id is not None:
            query += " AND v.owner_id = ?"
            params.append(owner_id)
        if status:
            query += " AND d.status = ?"
            params.append(status)
        if doc_id:
            query += " AND d.doc_id = ?"
            params.append(doc_id)
        query += " ORDER BY d.deadline_date ASC"
        with self.connect() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    # ── Knowledge Graph ───────────────────────────────────────────

    def add_graph_edge(self, source_id: str, target_id: Optional[str], relationship: str,
                       source_ref: str = "", target_ref: str = "", confidence: float = 0.5) -> None:
        with self.connect() as conn:
            conn.execute(
                """INSERT INTO knowledge_graph (source_doc_id, target_doc_id, relationship, source_ref, target_ref, confidence)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (source_id, target_id, relationship, source_ref, target_ref, confidence),
            )

    def get_document_links(self, doc_id: str, organization_id: Optional[str] = None) -> list[dict]:
        with self.connect() as conn:
            scope = ""
            params: list[Any] = [doc_id, doc_id]
            if organization_id is not None:
                scope = " AND source.organization_id = ? AND (target.organization_id = ? OR kg.target_doc_id IS NULL)"
                params.extend([organization_id, organization_id])
            rows = conn.execute(
                f"""SELECT kg.*, target.filename as target_filename
                   FROM knowledge_graph kg
                   JOIN vault_documents source ON source.id = kg.source_doc_id
                   LEFT JOIN vault_documents target ON kg.target_doc_id = target.id
                   WHERE (kg.source_doc_id = ? OR kg.target_doc_id = ?){scope}""",
                params,
            ).fetchall()
            return [dict(r) for r in rows]

    def get_full_graph(self, owner_id: Optional[str] = None, organization_id: Optional[str] = None) -> dict:
        with self.connect() as conn:
            node_scope = ""
            node_params: tuple[Any, ...] = ()
            edge_scope = ""
            edge_params: tuple[Any, ...] = ()
            if organization_id is not None:
                node_scope = " AND organization_id = ?"
                node_params = (organization_id,)
                edge_scope = " WHERE source.organization_id = ? AND (target.organization_id = ? OR kg.target_doc_id IS NULL)"
                edge_params = (organization_id, organization_id)
            elif owner_id is not None:
                node_scope = " AND owner_id = ?"
                node_params = (owner_id,)
                edge_scope = " WHERE source.owner_id = ? AND (target.owner_id = ? OR kg.target_doc_id IS NULL)"
                edge_params = (owner_id, owner_id)
            nodes = conn.execute(
                "SELECT id, filename, category, domain, risk_score FROM vault_documents WHERE status = 'indexed'" + node_scope,
                node_params,
            ).fetchall()
            edges = conn.execute(
                "SELECT kg.source_doc_id, kg.target_doc_id, kg.relationship, kg.confidence FROM knowledge_graph kg JOIN vault_documents source ON source.id = kg.source_doc_id LEFT JOIN vault_documents target ON target.id = kg.target_doc_id" + edge_scope,
                edge_params,
            ).fetchall()
            return {
                "nodes": [dict(n) for n in nodes],
                "edges": [dict(e) for e in edges],
            }

    # ── Section Index ─────────────────────────────────────────────

    def add_section_entries(self, doc_id: str, entries: list[dict]) -> None:
        with self.connect() as conn:
            conn.executemany(
                """INSERT INTO section_index (section_ref, doc_id, context_type, snippet)
                   VALUES (?, ?, ?, ?)""",
                [(e["ref"], doc_id, e.get("context_type", "citing"), e.get("snippet")) for e in entries],
            )

    def search_section(
        self,
        ref: str,
        owner_id: Optional[str] = None,
        organization_id: Optional[str] = None,
    ) -> list[dict]:
        with self.connect() as conn:
            scope = ""
            params: tuple[Any, ...] = (f"%{ref}%",)
            if organization_id is not None:
                scope = " AND v.organization_id = ?"
                params = (f"%{ref}%", organization_id)
            elif owner_id is not None:
                scope = " AND v.owner_id = ?"
                params = (f"%{ref}%", owner_id)
            rows = conn.execute(
                """SELECT si.*, v.filename, v.category
                   FROM section_index si
                   JOIN vault_documents v ON si.doc_id = v.id
                   WHERE si.section_ref LIKE ?""" + scope + " ORDER BY si.context_type",
                params,
            ).fetchall()
            return [dict(r) for r in rows]

    # ── Case-law index ───────────────────────────────────────────

    def upsert_case_law_record(self, organization_id: str, document_id: str, fields: dict[str, Any]) -> dict:
        now = self.now()
        judges = fields.get("judges") or []
        sections = fields.get("sections") or []
        with self.connect() as conn:
            existing = conn.execute(
                "SELECT id FROM case_law_records WHERE organization_id = ? AND document_id = ?",
                (organization_id, document_id),
            ).fetchone()
            values = (
                fields.get("title") or "Untitled judgment",
                fields.get("citation") or "",
                fields.get("court") or "",
                json.dumps(judges, ensure_ascii=False),
                fields.get("petitioner") or "",
                fields.get("respondent") or "",
                fields.get("case_number") or "",
                fields.get("decision_date") or "",
                fields.get("year"),
                json.dumps(sections, ensure_ascii=False),
                fields.get("source_excerpt") or "",
            )
            if existing:
                record_id = existing["id"]
                conn.execute(
                    """UPDATE case_law_records SET title = ?, citation = ?, court = ?, judges_json = ?,
                       petitioner = ?, respondent = ?, case_number = ?, decision_date = ?, year = ?,
                       sections_json = ?, source_excerpt = ?, source_page = ?, updated_at = ? WHERE id = ? AND organization_id = ?""",
                    (*values, fields.get("source_page") or 1, now, record_id, organization_id),
                )
            else:
                record_id = self.new_id()
                conn.execute(
                    """INSERT INTO case_law_records
                       (id, organization_id, document_id, title, citation, court, judges_json,
                        petitioner, respondent, case_number, decision_date, year, sections_json,
                        source_excerpt, source_page, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (record_id, organization_id, document_id, *values, fields.get("source_page") or 1, now, now),
                )
            row = conn.execute(
                """SELECT c.*, v.filename FROM case_law_records c
                   JOIN vault_documents v ON v.id = c.document_id
                   WHERE c.id = ? AND c.organization_id = ?""",
                (record_id, organization_id),
            ).fetchone()
        return self._decode_case_law_record(dict(row))

    @staticmethod
    def _decode_case_law_record(record: dict) -> dict:
        for field in ("judges_json", "sections_json", "paragraphs_json"):
            raw = record.pop(field, "[]")
            try:
                record[field.removesuffix("_json")] = json.loads(raw or "[]")
            except (TypeError, json.JSONDecodeError):
                record[field.removesuffix("_json")] = []
        record["excerpt"] = record.pop("source_excerpt", "")
        return record

    def upsert_case_law_corpus_record(self, record: dict[str, Any]) -> dict:
        now = self.now()
        corpus_key = str(record.get("corpus_key") or "").strip()
        if not corpus_key:
            raise ValueError("case-law corpus records require corpus_key")
        source_name = str(record.get("source_name") or "").strip()
        if not source_name:
            raise ValueError("case-law corpus records require source_name")
        values = (
            str(record.get("title") or "Untitled judgment").strip(),
            str(record.get("citation") or "").strip(),
            str(record.get("court") or "").strip(),
            json.dumps(record.get("judges") or [], ensure_ascii=False),
            str(record.get("petitioner") or "").strip(),
            str(record.get("respondent") or "").strip(),
            str(record.get("case_number") or "").strip(),
            str(record.get("decision_date") or "").strip(),
            record.get("year"),
            json.dumps(record.get("sections") or [], ensure_ascii=False),
            json.dumps(record.get("paragraphs") or [], ensure_ascii=False),
            str(record.get("source_excerpt") or "").strip(),
            int(record.get("source_page") or 1),
            source_name,
            str(record.get("source_url") or "").strip(),
            str(record.get("provenance_status") or "unverified").strip().lower(),
        )
        with self.connect() as conn:
            existing = conn.execute("SELECT id FROM case_law_corpus_records WHERE corpus_key = ?", (corpus_key,)).fetchone()
            if existing:
                record_id = existing["id"]
                conn.execute(
                    """UPDATE case_law_corpus_records SET title = ?, citation = ?, court = ?, judges_json = ?,
                       petitioner = ?, respondent = ?, case_number = ?, decision_date = ?, year = ?, sections_json = ?,
                       paragraphs_json = ?, source_excerpt = ?, source_page = ?, source_name = ?, source_url = ?,
                       provenance_status = ?, updated_at = ? WHERE id = ?""",
                    (*values, now, record_id),
                )
            else:
                record_id = self.new_id()
                conn.execute(
                    """INSERT INTO case_law_corpus_records
                       (id, corpus_key, title, citation, court, judges_json, petitioner, respondent, case_number,
                        decision_date, year, sections_json, paragraphs_json, source_excerpt, source_page, source_name,
                        source_url, provenance_status, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (record_id, corpus_key, *values, now, now),
                )
            row = conn.execute("SELECT * FROM case_law_corpus_records WHERE id = ?", (record_id,)).fetchone()
        decoded = self._decode_case_law_record(dict(row))
        decoded.update({"scope": "curated", "document_id": "", "filename": decoded.get("source_name", "")})
        return decoded

    def search_case_law_corpus_records(
        self,
        query: str,
        *,
        court: Optional[str] = None,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        limit: int = 100,
    ) -> list[dict]:
        where = ["provenance_status != 'retracted'"]
        params: list[Any] = []
        if court:
            where.append("court LIKE ? COLLATE NOCASE")
            params.append(f"%{court}%")
        if year_from is not None:
            where.append("year >= ?")
            params.append(year_from)
        if year_to is not None:
            where.append("year <= ?")
            params.append(year_to)
        with self.connect() as conn:
            rows = [dict(row) for row in conn.execute(
                "SELECT * FROM case_law_corpus_records WHERE " + " AND ".join(where) + " ORDER BY updated_at DESC LIMIT 500",
                params,
            ).fetchall()]
        terms = [term.casefold() for term in query.split() if len(term.strip()) >= 2]
        scored = []
        for row in rows:
            haystack = " ".join(str(row.get(key) or "") for key in ("title", "citation", "court", "petitioner", "respondent", "case_number", "decision_date", "source_excerpt", "sections_json", "paragraphs_json")).casefold()
            score = sum(1.0 for term in terms if term in haystack)
            if query.casefold().strip() in haystack:
                score += 3.0
            if score > 0 or not terms:
                decoded = self._decode_case_law_record(row)
                decoded.update({"scope": "curated", "document_id": "", "filename": decoded.get("source_name", ""), "relevance": round(score, 3)})
                scored.append(decoded)
        scored.sort(key=lambda item: (-item["relevance"], item.get("updated_at", "")))
        return scored[: max(1, min(limit, 100))]

    def get_case_law_records_by_ids(self, organization_id: str, record_ids: list[str]) -> list[dict]:
        ids = list(dict.fromkeys(item for item in record_ids if item))[:20]
        if not ids:
            return []
        placeholders = ",".join("?" for _ in ids)
        with self.connect() as conn:
            uploaded = [dict(row) for row in conn.execute(
                """SELECT c.*, v.filename FROM case_law_records c JOIN vault_documents v ON v.id = c.document_id
                   WHERE c.organization_id = ? AND c.id IN (""" + placeholders + ")",
                [organization_id, *ids],
            ).fetchall()]
            curated = [dict(row) for row in conn.execute(
                "SELECT * FROM case_law_corpus_records WHERE id IN (" + placeholders + ") AND provenance_status != 'retracted'",
                ids,
            ).fetchall()]
        records = []
        for row in uploaded:
            decoded = self._decode_case_law_record(row)
            decoded.update({"scope": "workspace", "source_name": decoded.get("filename", ""), "source_url": "", "provenance_status": "uploaded"})
            records.append(decoded)
        for row in curated:
            decoded = self._decode_case_law_record(row)
            decoded.update({"scope": "curated", "document_id": "", "filename": decoded.get("source_name", "")})
            records.append(decoded)
        order = {record_id: index for index, record_id in enumerate(ids)}
        return sorted(records, key=lambda item: order.get(item.get("id", ""), len(ids)))

    def search_case_law_records(
        self,
        organization_id: str,
        query: str,
        *,
        court: Optional[str] = None,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        limit: int = 20,
    ) -> list[dict]:
        terms = [term.casefold() for term in query.split() if len(term.strip()) >= 2]
        where = ["c.organization_id = ?"]
        params: list[Any] = [organization_id]
        if court:
            where.append("c.court LIKE ? COLLATE NOCASE")
            params.append(f"%{court}%")
        if year_from is not None:
            where.append("c.year >= ?")
            params.append(year_from)
        if year_to is not None:
            where.append("c.year <= ?")
            params.append(year_to)
        with self.connect() as conn:
            rows = [dict(row) for row in conn.execute(
                """SELECT c.*, v.filename FROM case_law_records c
                   JOIN vault_documents v ON v.id = c.document_id
                   WHERE """ + " AND ".join(where) + " ORDER BY c.updated_at DESC LIMIT 500",
                params,
            ).fetchall()]
        scored = []
        for row in rows:
            haystack = " ".join(
                str(row.get(key) or "")
                for key in ("title", "citation", "court", "petitioner", "respondent", "case_number", "decision_date", "source_excerpt", "sections_json")
            ).casefold()
            score = sum(1.0 for term in terms if term in haystack)
            if query.casefold().strip() and query.casefold().strip() in haystack:
                score += 3.0
            if score > 0 or not terms:
                row = self._decode_case_law_record(row)
                row.update({"scope": "workspace", "source_name": row.get("filename", ""), "source_url": "", "provenance_status": "uploaded"})
                row["relevance"] = round(score, 3)
                scored.append(row)
        scored.sort(key=lambda item: (-item["relevance"], item.get("updated_at", "")))
        curated = self.search_case_law_corpus_records(query, court=court, year_from=year_from, year_to=year_to, limit=limit)
        combined = scored + curated
        combined.sort(key=lambda item: (-item["relevance"], item.get("updated_at", "")))
        return combined[: max(1, min(limit, 100))]

    # ── Chat Sessions ─────────────────────────────────────────────

    def create_chat_session(self, title: str = "New Conversation") -> str:
        session_id = self.new_id()
        now = self.now()
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO chat_sessions (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (session_id, title, now, now),
            )
        return session_id

    def list_chat_sessions(self) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM chat_sessions ORDER BY updated_at DESC"
            ).fetchall()
            return [dict(r) for r in rows]

    def get_chat_messages(self, session_id: str) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM chat_messages WHERE session_id = ? ORDER BY created_at ASC",
                (session_id,),
            ).fetchall()
            result = []
            for r in rows:
                d = dict(r)
                d["sources"] = json.loads(d["sources_json"]) if d["sources_json"] else []
                d["follow_ups"] = json.loads(d["follow_ups_json"]) if d["follow_ups_json"] else []
                d["reasoning_steps"] = json.loads(d["reasoning_json"]) if d["reasoning_json"] else []
                result.append(d)
            return result

    def add_chat_message(
        self,
        session_id: str,
        role: str,
        content: str,
        sources: Optional[list] = None,
        follow_ups: Optional[list] = None,
        reasoning_steps: Optional[list] = None,
    ) -> int:
        now = self.now()
        with self.connect() as conn:
            cur = conn.execute(
                """INSERT INTO chat_messages
                   (session_id, role, content, sources_json, follow_ups_json, reasoning_json, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    session_id, role, content,
                    json.dumps(sources) if sources else None,
                    json.dumps(follow_ups) if follow_ups else None,
                    json.dumps(reasoning_steps) if reasoning_steps else None,
                    now,
                ),
            )
            conn.execute(
                "UPDATE chat_sessions SET updated_at = ?, title = CASE WHEN title = 'New Conversation' THEN ? ELSE title END WHERE id = ?",
                (now, content[:60] + "..." if len(content) > 60 else content, session_id),
            )
            return cur.lastrowid  # type: ignore[return-value]

    def delete_chat_session(self, session_id: str) -> bool:
        with self.connect() as conn:
            cur = conn.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
            return cur.rowcount > 0

    # ── Activity Log ──────────────────────────────────────────────

    def log_activity(self, action: str, detail: str = "", doc_id: Optional[str] = None) -> None:
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO activity_log (action, detail, doc_id, timestamp) VALUES (?, ?, ?, ?)",
                (action, detail, doc_id, self.now()),
            )

    def get_recent_activity(
        self,
        limit: int = 20,
        owner_id: Optional[str] = None,
        organization_id: Optional[str] = None,
    ) -> list[dict]:
        with self.connect() as conn:
            scope = ""
            params: tuple[Any, ...] = (limit,)
            if organization_id is not None:
                scope = " JOIN vault_documents ON vault_documents.id = activity_log.doc_id WHERE vault_documents.organization_id = ?"
                params = (organization_id, limit)
            elif owner_id is not None:
                scope = " JOIN vault_documents ON vault_documents.id = activity_log.doc_id WHERE vault_documents.owner_id = ?"
                params = (owner_id, limit)
            rows = conn.execute(
                "SELECT activity_log.* FROM activity_log" + scope + " ORDER BY activity_log.timestamp DESC LIMIT ?",
                params,
            ).fetchall()
            return [dict(r) for r in rows]

    # ── Compliance Gaps ───────────────────────────────────────────

    def add_compliance_gap(
        self,
        domain: str,
        description: str,
        severity: str = "medium",
        organization_id: Optional[str] = None,
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO compliance_gaps (organization_id, domain, gap_description, severity, detected_at) VALUES (?, ?, ?, ?, ?)",
                (organization_id, domain, description, severity, self.now()),
            )

    def get_compliance_gaps(
        self,
        gap_type: Optional[str] = None,
        organization_id: Optional[str] = None,
    ) -> list[dict]:
        with self.connect() as conn:
            filters = []
            params: list[Any] = []
            if gap_type:
                filters.append("(domain = ? OR gap_description LIKE ?)")
                params.extend([gap_type, f"%{gap_type}%"])
            if organization_id is not None:
                filters.append("organization_id = ?")
                params.append(organization_id)
            where = " WHERE " + " AND ".join(filters) if filters else ""
            rows = conn.execute("SELECT * FROM compliance_gaps" + where + " ORDER BY detected_at DESC", params).fetchall()
            return [dict(r) for r in rows]

    def update_document_classification(self, doc_id: str, category: str, domain: str) -> None:
        self.update_document(doc_id, category=category, domain=domain)

    def get_domain_counts(self, owner_id: Optional[str] = None, organization_id: Optional[str] = None) -> list[dict]:
        with self.connect() as conn:
            scope = ""
            params: tuple[Any, ...] = ()
            if organization_id is not None:
                scope = " AND organization_id = ?"
                params = (organization_id,)
            elif owner_id is not None:
                scope = " AND owner_id = ?"
                params = (owner_id,)
            return [dict(row) for row in conn.execute("SELECT domain, COUNT(*) AS count FROM vault_documents WHERE domain IS NOT NULL" + scope + " GROUP BY domain ORDER BY count DESC", params).fetchall()]

    def get_risk_heatmap(self, owner_id: Optional[str] = None, organization_id: Optional[str] = None) -> list[dict]:
        with self.connect() as conn:
            scope = ""
            params: tuple[Any, ...] = ()
            if organization_id is not None:
                scope = " WHERE organization_id = ?"
                params = (organization_id,)
            elif owner_id is not None:
                scope = " WHERE owner_id = ?"
                params = (owner_id,)
            return [dict(row) for row in conn.execute("SELECT COALESCE(domain, 'Unclassified') AS domain, COUNT(*) AS document_count, ROUND(AVG(risk_score), 1) AS average_risk, MAX(risk_score) AS maximum_risk FROM vault_documents" + scope + " GROUP BY domain ORDER BY average_risk DESC", params).fetchall()]

    def get_upload_trends(self, days: int = 30, owner_id: Optional[str] = None, organization_id: Optional[str] = None) -> list[dict]:
        days = max(1, min(days, 365))
        with self.connect() as conn:
            scope = ""
            params: tuple[Any, ...] = (f"-{days} days",)
            if organization_id is not None:
                scope = " AND organization_id = ?"
                params = (f"-{days} days", organization_id)
            elif owner_id is not None:
                scope = " AND owner_id = ?"
                params = (f"-{days} days", owner_id)
            return [dict(row) for row in conn.execute("SELECT DATE(upload_time) AS date, COUNT(*) AS count FROM vault_documents WHERE DATE(upload_time) >= DATE('now', ?)" + scope + " GROUP BY DATE(upload_time) ORDER BY date", params).fetchall()]

    def get_docs_by_section(
        self,
        ref: str,
        owner_id: Optional[str] = None,
        organization_id: Optional[str] = None,
    ) -> list[dict]:
        return self.search_section(ref, owner_id=owner_id, organization_id=organization_id)

    def get_section_impact(
        self,
        ref: str,
        owner_id: Optional[str] = None,
        organization_id: Optional[str] = None,
    ) -> list[dict]:
        return self.search_section(ref, owner_id=owner_id, organization_id=organization_id)

    def get_related_documents(
        self,
        doc_id: str,
        limit: int = 20,
        organization_id: Optional[str] = None,
    ) -> list[dict]:
        with self.connect() as conn:
            scope = ""
            params: list[Any] = [doc_id, doc_id, doc_id]
            if organization_id is not None:
                scope = " AND v.organization_id = ?"
                params.append(organization_id)
            params.append(max(1, min(limit, 100)))
            return [dict(row) for row in conn.execute("SELECT DISTINCT v.id, v.filename, v.category, v.domain, kg.relationship, kg.confidence AS relevance FROM knowledge_graph kg JOIN vault_documents v ON v.id = CASE WHEN kg.source_doc_id = ? THEN kg.target_doc_id ELSE kg.source_doc_id END WHERE (kg.source_doc_id = ? OR kg.target_doc_id = ?)" + scope + " ORDER BY kg.confidence DESC LIMIT ?", params).fetchall()]

    def check_staleness(self, owner_id: Optional[str] = None, organization_id: Optional[str] = None) -> list[dict]:
        obsolete_references = ("Indian Penal Code", "Code of Criminal Procedure", "Indian Evidence Act")
        with self.connect() as conn:
            references = tuple(f"%{ref}%" for ref in obsolete_references)
            scope = ""
            params = references
            if organization_id is not None:
                scope = " AND v.organization_id = ?"
                params = references + (organization_id,)
            elif owner_id is not None:
                scope = " AND v.owner_id = ?"
                params = references + (owner_id,)
            return [dict(row) for row in conn.execute("SELECT DISTINCT v.id, v.filename, v.category, v.domain, si.section_ref AS outdated_reference FROM vault_documents v JOIN section_index si ON si.doc_id = v.id WHERE (si.section_ref LIKE ? OR si.section_ref LIKE ? OR si.section_ref LIKE ?)" + scope + " ORDER BY v.upload_time DESC", params).fetchall()]

    # ── Legal Operations ─────────────────────────────────────────

    @staticmethod
    def _bounded(value: Optional[str], default: str, allowed: set[str]) -> str:
        candidate = (value or default).strip().lower().replace(" ", "_")
        return candidate if candidate in allowed else default

    @staticmethod
    def _parse_iso_date(value: Optional[str]) -> Optional[date]:
        if not value:
            return None
        try:
            return date.fromisoformat(str(value)[:10])
        except ValueError:
            return None

    def _decorate_contract_record(self, contract: dict) -> dict:
        status = contract.get("status") or "draft"
        renewal_date = self._parse_iso_date(contract.get("renewal_date"))
        expiry_date = self._parse_iso_date(contract.get("expiry_date"))
        today = datetime.now(timezone.utc).date()
        days_to_renewal = (renewal_date - today).days if renewal_date else None

        lifecycle_stage = status
        reminder_status = "none"
        if status == "expired" or (expiry_date and expiry_date < today):
            lifecycle_stage = "expired"
        elif days_to_renewal is not None and days_to_renewal < 0 and status not in {"expired", "signed"}:
            lifecycle_stage = "renewal_overdue"
            reminder_status = "overdue"
        elif days_to_renewal is not None and days_to_renewal <= 60 and status not in {"expired", "draft"}:
            lifecycle_stage = "renewal_due"
            reminder_status = "due"
        elif status == "approved":
            lifecycle_stage = "pending_signature"
        elif status == "signed":
            lifecycle_stage = "active"
        elif status == "in_review":
            lifecycle_stage = "in_review"

        return {
            **contract,
            "lifecycle_stage": lifecycle_stage,
            "reminder_status": reminder_status,
            "days_to_renewal": days_to_renewal,
        }

    def _get_org_row(self, table: str, item_id: str, organization_id: str) -> Optional[dict]:
        allowed = {"legal_matters", "legal_intake_requests", "legal_tasks", "legal_contracts", "legal_contract_obligations", "legal_vendors", "legal_spend_entries", "legal_playbooks"}
        if table not in allowed:
            raise ValueError("Unsupported legal operations table")
        with self.connect() as conn:
            row = conn.execute(f"SELECT * FROM {table} WHERE id = ? AND organization_id = ?", (item_id, organization_id)).fetchone()
            return dict(row) if row else None

    def create_matter(self, organization_id: str, title: str, **kwargs: Any) -> dict:
        now = self.now()
        item_id = self.new_id()
        matter_type = (kwargs.get("matter_type") or "general").strip()[:60]
        status = self._bounded(kwargs.get("status"), "open", {"open", "in_review", "waiting", "closed"})
        priority = self._bounded(kwargs.get("priority"), "medium", {"low", "medium", "high", "critical"})
        with self.connect() as conn:
            conn.execute(
                """INSERT INTO legal_matters (id, organization_id, title, matter_type, status, priority, description, owner_user_id, due_date, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (item_id, organization_id, title.strip()[:160], matter_type, status, priority, (kwargs.get("description") or "")[:3000], kwargs.get("owner_user_id"), kwargs.get("due_date"), now, now),
            )
        return self.get_matter(item_id, organization_id) or {}

    def get_matter(self, matter_id: str, organization_id: str) -> Optional[dict]:
        return self._get_org_row("legal_matters", matter_id, organization_id)

    def list_matters(self, organization_id: str, status: Optional[str] = None, limit: int = 100) -> list[dict]:
        sql = "SELECT * FROM legal_matters WHERE organization_id = ?"
        params: list[Any] = [organization_id]
        if status:
            sql += " AND status = ?"
            params.append(status)
        sql += " ORDER BY updated_at DESC LIMIT ?"
        params.append(max(1, min(limit, 200)))
        with self.connect() as conn:
            return [dict(row) for row in conn.execute(sql, params).fetchall()]

    def update_matter(self, matter_id: str, organization_id: str, **kwargs: Any) -> Optional[dict]:
        permitted = {"title", "matter_type", "status", "priority", "description", "owner_user_id", "due_date"}
        fields = {k: v for k, v in kwargs.items() if k in permitted and v is not None}
        if "status" in fields:
            fields["status"] = self._bounded(fields["status"], "open", {"open", "in_review", "waiting", "closed"})
        if "priority" in fields:
            fields["priority"] = self._bounded(fields["priority"], "medium", {"low", "medium", "high", "critical"})
        if "title" in fields:
            fields["title"] = str(fields["title"]).strip()[:160]
        if not fields:
            return self.get_matter(matter_id, organization_id)
        fields["updated_at"] = self.now()
        cols = ", ".join(f"{k} = ?" for k in fields)
        vals = list(fields.values()) + [matter_id, organization_id]
        with self.connect() as conn:
            cur = conn.execute(f"UPDATE legal_matters SET {cols} WHERE id = ? AND organization_id = ?", vals)
            if cur.rowcount == 0:
                return None
        return self.get_matter(matter_id, organization_id)


    def link_document_to_matter(self, organization_id: str, matter_id: str, document_id: str) -> dict:
        if not self.get_matter(matter_id, organization_id):
            raise ValueError("Matter not found in workspace")
        document = self.get_document(document_id)
        if not document or document.get("organization_id") != organization_id:
            raise ValueError("Document not found in workspace")
        link_id = self.new_id()
        now = self.now()
        with self.connect() as conn:
            conn.execute(
                """INSERT OR IGNORE INTO legal_matter_documents (id, organization_id, matter_id, document_id, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (link_id, organization_id, matter_id, document_id, now),
            )
        return {"id": link_id, "organization_id": organization_id, "matter_id": matter_id, "document_id": document_id, "created_at": now}

    def add_matter_note(self, organization_id: str, matter_id: str, author_user_id: str, body: str) -> dict:
        if not self.get_matter(matter_id, organization_id):
            raise ValueError("Matter not found in workspace")
        note_id = self.new_id()
        now = self.now()
        with self.connect() as conn:
            conn.execute(
                """INSERT INTO legal_matter_notes (id, organization_id, matter_id, author_user_id, body, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (note_id, organization_id, matter_id, author_user_id, body.strip()[:4000], now),
            )
            conn.execute("UPDATE legal_matters SET updated_at = ? WHERE id = ? AND organization_id = ?", (now, matter_id, organization_id))
        return {"id": note_id, "organization_id": organization_id, "matter_id": matter_id, "author_user_id": author_user_id, "body": body.strip()[:4000], "created_at": now}

    def get_matter_detail(self, organization_id: str, matter_id: str) -> Optional[dict]:
        matter = self.get_matter(matter_id, organization_id)
        if not matter:
            return None
        with self.connect() as conn:
            linked_documents = [dict(row) for row in conn.execute(
                """SELECT l.id AS link_id, l.created_at AS linked_at, d.id, d.filename, d.category, d.domain, d.status, d.pages, d.file_size
                   FROM legal_matter_documents l JOIN vault_documents d ON d.id = l.document_id
                   WHERE l.organization_id = ? AND l.matter_id = ? ORDER BY l.created_at DESC""",
                (organization_id, matter_id),
            ).fetchall()]
            notes = [dict(row) for row in conn.execute(
                "SELECT * FROM legal_matter_notes WHERE organization_id = ? AND matter_id = ? ORDER BY created_at DESC",
                (organization_id, matter_id),
            ).fetchall()]
            tasks = [dict(row) for row in conn.execute(
                "SELECT * FROM legal_tasks WHERE organization_id = ? AND matter_id = ? ORDER BY updated_at DESC",
                (organization_id, matter_id),
            ).fetchall()]
            contracts = [dict(row) for row in conn.execute(
                "SELECT * FROM legal_contracts WHERE organization_id = ? AND matter_id = ? ORDER BY updated_at DESC",
                (organization_id, matter_id),
            ).fetchall()]
            obligations = [dict(row) for row in conn.execute(
                "SELECT * FROM legal_contract_obligations WHERE organization_id = ? AND matter_id = ? ORDER BY updated_at DESC",
                (organization_id, matter_id),
            ).fetchall()]
            intakes = [dict(row) for row in conn.execute(
                "SELECT * FROM legal_intake_requests WHERE organization_id = ? AND matter_id = ? ORDER BY updated_at DESC",
                (organization_id, matter_id),
            ).fetchall()]
            spend_entries = [dict(row) for row in conn.execute(
                "SELECT * FROM legal_spend_entries WHERE organization_id = ? AND matter_id = ? ORDER BY updated_at DESC",
                (organization_id, matter_id),
            ).fetchall()]
            playbook_key = f"%{matter.get('matter_type') or ''}%"
            playbooks = [dict(row) for row in conn.execute(
                """SELECT * FROM legal_playbooks
                   WHERE organization_id = ? AND status = 'active'
                   AND (? = '%%' OR playbook_type LIKE ? COLLATE NOCASE OR title LIKE ? COLLATE NOCASE OR tags LIKE ? COLLATE NOCASE)
                   ORDER BY updated_at DESC LIMIT 10""",
                (organization_id, playbook_key, playbook_key, playbook_key, playbook_key),
            ).fetchall()]
        activity = []
        activity.extend({"kind": "document", "id": row["id"], "label": "Document linked", "detail": row["filename"], "timestamp": row["linked_at"]} for row in linked_documents)
        activity.extend({"kind": "note", "id": row["id"], "label": "Note added", "detail": row["body"], "timestamp": row["created_at"]} for row in notes)
        activity.extend({"kind": "task", "id": row["id"], "label": f"Task: {row['title']}", "detail": row["status"], "timestamp": row["updated_at"]} for row in tasks)
        activity.extend({"kind": "contract", "id": row["id"], "label": f"Contract: {row['title']}", "detail": row["status"], "timestamp": row["updated_at"]} for row in contracts)
        activity.extend({"kind": "obligation", "id": row["id"], "label": f"Obligation: {row['title']}", "detail": row["status"], "timestamp": row["updated_at"]} for row in obligations)
        activity.extend({"kind": "intake", "id": row["id"], "label": f"Intake: {row['title']}", "detail": row["status"], "timestamp": row["updated_at"]} for row in intakes)
        activity.extend({"kind": "spend", "id": row["id"], "label": f"Invoice: {row.get('invoice_number') or 'Unnumbered spend'}", "detail": f"{row['status']} {row['currency']} {float(row['amount']):.2f}", "timestamp": row["updated_at"]} for row in spend_entries)
        activity.sort(key=lambda item: item["timestamp"] or "", reverse=True)
        return {**matter, "documents": linked_documents, "notes": notes, "tasks": tasks, "contracts": contracts, "obligations": obligations, "spend_entries": spend_entries, "playbooks": playbooks, "intakes": intakes, "activity": activity[:100]}

    def search_legal_ops(self, organization_id: str, query: str, limit: int = 30) -> list[dict]:
        needle = f"%{query.strip()}%"
        capped = max(1, min(limit, 100))
        results: list[dict] = []
        with self.connect() as conn:
            searches = [
                ("matter", "SELECT id, title, status, priority AS secondary, description AS snippet, updated_at AS timestamp FROM legal_matters WHERE organization_id = ? AND (title LIKE ? COLLATE NOCASE OR description LIKE ? COLLATE NOCASE OR matter_type LIKE ? COLLATE NOCASE)"),
                ("intake", "SELECT id, title, status, urgency AS secondary, summary AS snippet, updated_at AS timestamp FROM legal_intake_requests WHERE organization_id = ? AND (title LIKE ? COLLATE NOCASE OR summary LIKE ? COLLATE NOCASE OR request_type LIKE ? COLLATE NOCASE)"),
                ("task", "SELECT id, title, status, priority AS secondary, '' AS snippet, updated_at AS timestamp FROM legal_tasks WHERE organization_id = ? AND title LIKE ? COLLATE NOCASE"),
                ("contract", "SELECT id, title, status, risk_level AS secondary, counterparty AS snippet, updated_at AS timestamp FROM legal_contracts WHERE organization_id = ? AND (title LIKE ? COLLATE NOCASE OR counterparty LIKE ? COLLATE NOCASE OR contract_type LIKE ? COLLATE NOCASE)"),
                ("obligation", "SELECT id, title, status, priority AS secondary, source_clause AS snippet, updated_at AS timestamp FROM legal_contract_obligations WHERE organization_id = ? AND (title LIKE ? COLLATE NOCASE OR owner LIKE ? COLLATE NOCASE OR category LIKE ? COLLATE NOCASE OR source_clause LIKE ? COLLATE NOCASE)"),
                ("vendor", "SELECT id, name AS title, status, practice_area AS secondary, contact_email AS snippet, updated_at AS timestamp FROM legal_vendors WHERE organization_id = ? AND (name LIKE ? COLLATE NOCASE OR practice_area LIKE ? COLLATE NOCASE OR vendor_type LIKE ? COLLATE NOCASE OR contact_email LIKE ? COLLATE NOCASE)"),
                ("spend", "SELECT id, COALESCE(NULLIF(invoice_number, ''), 'Unnumbered spend') AS title, status, currency AS secondary, description AS snippet, updated_at AS timestamp FROM legal_spend_entries WHERE organization_id = ? AND (invoice_number LIKE ? COLLATE NOCASE OR description LIKE ? COLLATE NOCASE OR status LIKE ? COLLATE NOCASE OR currency LIKE ? COLLATE NOCASE)"),
                ("playbook", "SELECT id, title, status, playbook_type AS secondary, body AS snippet, updated_at AS timestamp FROM legal_playbooks WHERE organization_id = ? AND (title LIKE ? COLLATE NOCASE OR body LIKE ? COLLATE NOCASE OR tags LIKE ? COLLATE NOCASE OR playbook_type LIKE ? COLLATE NOCASE)"),
                ("document", "SELECT id, filename AS title, status, COALESCE(domain, category, '') AS secondary, COALESCE(summary, '') AS snippet, upload_time AS timestamp FROM vault_documents WHERE organization_id = ? AND (filename LIKE ? COLLATE NOCASE OR COALESCE(category, '') LIKE ? COLLATE NOCASE OR COALESCE(domain, '') LIKE ? COLLATE NOCASE OR COALESCE(summary, '') LIKE ? COLLATE NOCASE)"),
            ]
            for kind, sql in searches:
                if kind == "task":
                    params = [organization_id, needle]
                elif kind in {"document", "vendor", "spend", "playbook", "obligation"}:
                    params = [organization_id, needle, needle, needle, needle]
                else:
                    params = [organization_id, needle, needle, needle]
                rows = conn.execute(sql + " ORDER BY timestamp DESC LIMIT ?", (*params, capped)).fetchall()
                for row in rows:
                    item = dict(row)
                    item["kind"] = kind
                    results.append(item)
        results.sort(key=lambda item: item.get("timestamp") or "", reverse=True)
        return results[:capped]

    def create_intake(self, organization_id: str, requester_user_id: str, title: str, **kwargs: Any) -> dict:
        matter_id = kwargs.get("matter_id")
        if matter_id and not self.get_matter(matter_id, organization_id):
            raise ValueError("Matter not found in workspace")
        now = self.now()
        item_id = self.new_id()
        request_type = (kwargs.get("request_type") or "general").strip()[:60]
        urgency = self._bounded(kwargs.get("urgency"), "medium", {"low", "medium", "high", "critical"})
        status = self._bounded(kwargs.get("status"), "new", {"new", "triaged", "in_progress", "closed"})
        with self.connect() as conn:
            conn.execute(
                """INSERT INTO legal_intake_requests (id, organization_id, matter_id, requester_user_id, request_type, title, summary, urgency, status, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (item_id, organization_id, matter_id, requester_user_id, request_type, title.strip()[:180], (kwargs.get("summary") or "")[:4000], urgency, status, now, now),
            )
        return self.get_intake(item_id, organization_id) or {}

    def get_intake(self, intake_id: str, organization_id: str) -> Optional[dict]:
        return self._get_org_row("legal_intake_requests", intake_id, organization_id)

    def list_intakes(self, organization_id: str, limit: int = 100) -> list[dict]:
        with self.connect() as conn:
            return [dict(row) for row in conn.execute("SELECT * FROM legal_intake_requests WHERE organization_id = ? ORDER BY updated_at DESC LIMIT ?", (organization_id, max(1, min(limit, 200)))).fetchall()]

    def update_intake(self, intake_id: str, organization_id: str, **kwargs: Any) -> Optional[dict]:
        permitted = {"matter_id", "request_type", "title", "summary", "urgency", "status"}
        fields = {k: v for k, v in kwargs.items() if k in permitted and v is not None}
        if "matter_id" in fields and fields["matter_id"] and not self.get_matter(fields["matter_id"], organization_id):
            raise ValueError("Matter not found in workspace")
        if "urgency" in fields:
            fields["urgency"] = self._bounded(fields["urgency"], "medium", {"low", "medium", "high", "critical"})
        if "status" in fields:
            fields["status"] = self._bounded(fields["status"], "new", {"new", "triaged", "in_progress", "closed"})
        if not fields:
            return self.get_intake(intake_id, organization_id)
        fields["updated_at"] = self.now()
        cols = ", ".join(f"{k} = ?" for k in fields)
        vals = list(fields.values()) + [intake_id, organization_id]
        with self.connect() as conn:
            cur = conn.execute(f"UPDATE legal_intake_requests SET {cols} WHERE id = ? AND organization_id = ?", vals)
            if cur.rowcount == 0:
                return None
        return self.get_intake(intake_id, organization_id)

    def convert_intake_to_matter(self, intake_id: str, organization_id: str, owner_user_id: str, **kwargs: Any) -> Optional[dict]:
        intake = self.get_intake(intake_id, organization_id)
        if not intake:
            return None
        if intake.get("matter_id"):
            matter = self.get_matter(intake["matter_id"], organization_id)
            return {"intake": intake, "matter": matter} if matter else None

        priority_map = {"low": "low", "medium": "medium", "high": "high", "critical": "critical"}
        urgency = (intake.get("urgency") or "medium").strip().lower()
        priority = self._bounded(kwargs.get("priority") or priority_map.get(urgency), "medium", {"low", "medium", "high", "critical"})
        title = (kwargs.get("matter_title") or intake.get("title") or "Legal matter").strip()[:160]
        matter_type = (kwargs.get("matter_type") or intake.get("request_type") or "general").strip()[:60]
        description = (intake.get("summary") or "")[:3000]
        matter = self.create_matter(
            organization_id,
            title,
            matter_type=matter_type,
            priority=priority,
            description=description,
            owner_user_id=owner_user_id,
            due_date=kwargs.get("due_date"),
        )
        updated = self.update_intake(intake_id, organization_id, matter_id=matter["id"], status="in_progress")
        return {"intake": updated, "matter": matter} if updated else None

    def create_task(self, organization_id: str, title: str, **kwargs: Any) -> dict:
        matter_id = kwargs.get("matter_id")
        if matter_id and not self.get_matter(matter_id, organization_id):
            raise ValueError("Matter not found in workspace")
        now = self.now()
        item_id = self.new_id()
        status = self._bounded(kwargs.get("status"), "open", {"open", "in_progress", "done"})
        priority = self._bounded(kwargs.get("priority"), "medium", {"low", "medium", "high", "critical"})
        with self.connect() as conn:
            conn.execute(
                """INSERT INTO legal_tasks (id, organization_id, matter_id, title, status, priority, assignee_user_id, due_date, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (item_id, organization_id, matter_id, title.strip()[:180], status, priority, kwargs.get("assignee_user_id"), kwargs.get("due_date"), now, now),
            )
        return self.get_task(item_id, organization_id) or {}

    def get_task(self, task_id: str, organization_id: str) -> Optional[dict]:
        return self._get_org_row("legal_tasks", task_id, organization_id)

    def list_tasks(self, organization_id: str, limit: int = 100) -> list[dict]:
        with self.connect() as conn:
            return [dict(row) for row in conn.execute("SELECT * FROM legal_tasks WHERE organization_id = ? ORDER BY updated_at DESC LIMIT ?", (organization_id, max(1, min(limit, 200)))).fetchall()]

    def update_task(self, task_id: str, organization_id: str, **kwargs: Any) -> Optional[dict]:
        permitted = {"matter_id", "title", "status", "priority", "assignee_user_id", "due_date"}
        fields = {k: v for k, v in kwargs.items() if k in permitted and v is not None}
        if "matter_id" in fields and fields["matter_id"] and not self.get_matter(fields["matter_id"], organization_id):
            raise ValueError("Matter not found in workspace")
        if "status" in fields:
            fields["status"] = self._bounded(fields["status"], "open", {"open", "in_progress", "done"})
        if "priority" in fields:
            fields["priority"] = self._bounded(fields["priority"], "medium", {"low", "medium", "high", "critical"})
        if not fields:
            return self.get_task(task_id, organization_id)
        fields["updated_at"] = self.now()
        cols = ", ".join(f"{k} = ?" for k in fields)
        vals = list(fields.values()) + [task_id, organization_id]
        with self.connect() as conn:
            cur = conn.execute(f"UPDATE legal_tasks SET {cols} WHERE id = ? AND organization_id = ?", vals)
            if cur.rowcount == 0:
                return None
        return self.get_task(task_id, organization_id)

    def create_contract_record(self, organization_id: str, title: str, **kwargs: Any) -> dict:
        document_id = kwargs.get("document_id")
        if document_id:
            document = self.get_document(document_id)
            if not document or document.get("organization_id") != organization_id:
                raise ValueError("Document not found in workspace")
        matter_id = kwargs.get("matter_id")
        if matter_id and not self.get_matter(matter_id, organization_id):
            raise ValueError("Matter not found in workspace")
        now = self.now()
        item_id = self.new_id()
        status = self._bounded(kwargs.get("status"), "draft", {"draft", "in_review", "approved", "signed", "expired"})
        risk_level = self._bounded(kwargs.get("risk_level"), "unknown", {"unknown", "low", "medium", "high", "critical"})
        with self.connect() as conn:
            conn.execute(
                """INSERT INTO legal_contracts (id, organization_id, document_id, matter_id, title, counterparty, contract_type, status, risk_level, effective_date, expiry_date, renewal_date, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (item_id, organization_id, document_id, matter_id, title.strip()[:180], (kwargs.get("counterparty") or "")[:180], (kwargs.get("contract_type") or "general")[:80], status, risk_level, kwargs.get("effective_date"), kwargs.get("expiry_date"), kwargs.get("renewal_date"), now, now),
            )
        return self.get_contract_record(item_id, organization_id) or {}

    def get_contract_record(self, contract_id: str, organization_id: str) -> Optional[dict]:
        contract = self._get_org_row("legal_contracts", contract_id, organization_id)
        return self._decorate_contract_record(contract) if contract else None

    def get_contract_record_by_document(self, document_id: str, organization_id: str) -> Optional[dict]:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM legal_contracts WHERE organization_id = ? AND document_id = ? ORDER BY updated_at DESC LIMIT 1",
                (organization_id, document_id),
            ).fetchone()
        return self._decorate_contract_record(dict(row)) if row else None

    def list_contract_records(self, organization_id: str, limit: int = 100) -> list[dict]:
        with self.connect() as conn:
            rows = [dict(row) for row in conn.execute("SELECT * FROM legal_contracts WHERE organization_id = ? ORDER BY updated_at DESC LIMIT ?", (organization_id, max(1, min(limit, 200)))).fetchall()]
        return [self._decorate_contract_record(row) for row in rows]

    def list_contract_reminders(self, organization_id: str, limit: int = 25) -> list[dict]:
        contracts = self.list_contract_records(organization_id, limit=200)
        reminders = [
            contract
            for contract in contracts
            if contract.get("renewal_date")
            and contract.get("days_to_renewal") is not None
            and contract["days_to_renewal"] <= 60
            and contract.get("status") not in {"expired", "draft"}
        ]
        reminders.sort(key=lambda item: item["days_to_renewal"])
        return [
            {
                "id": item["id"],
                "title": item["title"],
                "counterparty": item.get("counterparty") or "",
                "status": item.get("status") or "draft",
                "risk_level": item.get("risk_level") or "unknown",
                "renewal_date": item["renewal_date"],
                "days_to_renewal": item["days_to_renewal"],
                "reminder_status": item.get("reminder_status") or "none",
                "matter_id": item.get("matter_id"),
            }
            for item in reminders[: max(1, min(limit, 100))]
        ]

    def update_contract_record(self, contract_id: str, organization_id: str, **kwargs: Any) -> Optional[dict]:
        permitted = {"document_id", "matter_id", "title", "counterparty", "contract_type", "status", "risk_level", "effective_date", "expiry_date", "renewal_date"}
        fields = {k: v for k, v in kwargs.items() if k in permitted and v is not None}
        if "document_id" in fields and fields["document_id"]:
            document = self.get_document(fields["document_id"])
            if not document or document.get("organization_id") != organization_id:
                raise ValueError("Document not found in workspace")
        if "matter_id" in fields and fields["matter_id"] and not self.get_matter(fields["matter_id"], organization_id):
            raise ValueError("Matter not found in workspace")
        if "status" in fields:
            fields["status"] = self._bounded(fields["status"], "draft", {"draft", "in_review", "approved", "signed", "expired"})
        if "risk_level" in fields:
            fields["risk_level"] = self._bounded(fields["risk_level"], "unknown", {"unknown", "low", "medium", "high", "critical"})
        if not fields:
            return self.get_contract_record(contract_id, organization_id)
        fields["updated_at"] = self.now()
        cols = ", ".join(f"{k} = ?" for k in fields)
        vals = list(fields.values()) + [contract_id, organization_id]
        with self.connect() as conn:
            cur = conn.execute(f"UPDATE legal_contracts SET {cols} WHERE id = ? AND organization_id = ?", vals)
            if cur.rowcount == 0:
                return None
        return self.get_contract_record(contract_id, organization_id)


    def create_contract_obligation(self, organization_id: str, contract_id: str, title: str, **kwargs: Any) -> dict:
        contract = self.get_contract_record(contract_id, organization_id)
        if not contract:
            raise ValueError("Contract not found in workspace")
        matter_id = kwargs.get("matter_id") or contract.get("matter_id")
        if matter_id and not self.get_matter(matter_id, organization_id):
            raise ValueError("Matter not found in workspace")
        now = self.now()
        item_id = self.new_id()
        status = self._bounded(kwargs.get("status"), "open", {"open", "in_progress", "blocked", "done", "waived"})
        priority = self._bounded(kwargs.get("priority"), "medium", {"low", "medium", "high", "critical"})
        with self.connect() as conn:
            conn.execute(
                """INSERT INTO legal_contract_obligations (id, organization_id, contract_id, matter_id, title, owner, category, status, priority, due_date, source_clause, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    item_id,
                    organization_id,
                    contract_id,
                    matter_id,
                    title.strip()[:180],
                    (kwargs.get("owner") or "")[:180],
                    (kwargs.get("category") or "general")[:80],
                    status,
                    priority,
                    kwargs.get("due_date"),
                    (kwargs.get("source_clause") or "")[:1000],
                    now,
                    now,
                ),
            )
            conn.execute("UPDATE legal_contracts SET updated_at = ? WHERE id = ? AND organization_id = ?", (now, contract_id, organization_id))
            if matter_id:
                conn.execute("UPDATE legal_matters SET updated_at = ? WHERE id = ? AND organization_id = ?", (now, matter_id, organization_id))
        return self.get_contract_obligation(item_id, organization_id) or {}

    def get_contract_obligation(self, obligation_id: str, organization_id: str) -> Optional[dict]:
        return self._get_org_row("legal_contract_obligations", obligation_id, organization_id)

    def list_contract_obligations(self, organization_id: str, limit: int = 100) -> list[dict]:
        with self.connect() as conn:
            return [dict(row) for row in conn.execute("SELECT * FROM legal_contract_obligations WHERE organization_id = ? ORDER BY updated_at DESC LIMIT ?", (organization_id, max(1, min(limit, 200)))).fetchall()]

    def update_contract_obligation(self, obligation_id: str, organization_id: str, **kwargs: Any) -> Optional[dict]:
        permitted = {"contract_id", "matter_id", "title", "owner", "category", "status", "priority", "due_date", "source_clause"}
        existing = self.get_contract_obligation(obligation_id, organization_id)
        if not existing:
            return None
        fields = {k: v for k, v in kwargs.items() if k in permitted and v is not None}
        if "contract_id" in fields and fields["contract_id"]:
            contract = self.get_contract_record(fields["contract_id"], organization_id)
            if not contract:
                raise ValueError("Contract not found in workspace")
            if not fields.get("matter_id") and contract.get("matter_id"):
                fields["matter_id"] = contract["matter_id"]
        if "matter_id" in fields and fields["matter_id"] and not self.get_matter(fields["matter_id"], organization_id):
            raise ValueError("Matter not found in workspace")
        if "status" in fields:
            fields["status"] = self._bounded(fields["status"], "open", {"open", "in_progress", "blocked", "done", "waived"})
        if "priority" in fields:
            fields["priority"] = self._bounded(fields["priority"], "medium", {"low", "medium", "high", "critical"})
        if "title" in fields:
            fields["title"] = str(fields["title"]).strip()[:180]
        if "owner" in fields:
            fields["owner"] = str(fields["owner"]).strip()[:180]
        if "category" in fields:
            fields["category"] = str(fields["category"]).strip()[:80] or "general"
        if "source_clause" in fields:
            fields["source_clause"] = str(fields["source_clause"]).strip()[:1000]
        if not fields:
            return existing
        fields["updated_at"] = self.now()
        cols = ", ".join(f"{k} = ?" for k in fields)
        vals = list(fields.values()) + [obligation_id, organization_id]
        with self.connect() as conn:
            cur = conn.execute(f"UPDATE legal_contract_obligations SET {cols} WHERE id = ? AND organization_id = ?", vals)
            if cur.rowcount == 0:
                return None
            contract_id = fields.get("contract_id") or existing.get("contract_id")
            matter_id = fields.get("matter_id") or existing.get("matter_id")
            if contract_id:
                conn.execute("UPDATE legal_contracts SET updated_at = ? WHERE id = ? AND organization_id = ?", (fields["updated_at"], contract_id, organization_id))
            if matter_id:
                conn.execute("UPDATE legal_matters SET updated_at = ? WHERE id = ? AND organization_id = ?", (fields["updated_at"], matter_id, organization_id))
        return self.get_contract_obligation(obligation_id, organization_id)



    def create_playbook(self, organization_id: str, title: str, **kwargs: Any) -> dict:
        now = self.now()
        item_id = self.new_id()
        status = self._bounded(kwargs.get("status"), "active", {"active", "draft", "archived"})
        with self.connect() as conn:
            conn.execute(
                """INSERT INTO legal_playbooks (id, organization_id, title, playbook_type, body, tags, status, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    item_id,
                    organization_id,
                    title.strip()[:180],
                    (kwargs.get("playbook_type") or "general").strip()[:80],
                    (kwargs.get("body") or "").strip()[:8000],
                    (kwargs.get("tags") or "").strip()[:500],
                    status,
                    now,
                    now,
                ),
            )
        return self.get_playbook(item_id, organization_id) or {}

    def get_playbook(self, playbook_id: str, organization_id: str) -> Optional[dict]:
        return self._get_org_row("legal_playbooks", playbook_id, organization_id)

    def list_playbooks(self, organization_id: str, limit: int = 100) -> list[dict]:
        with self.connect() as conn:
            return [dict(row) for row in conn.execute("SELECT * FROM legal_playbooks WHERE organization_id = ? ORDER BY updated_at DESC LIMIT ?", (organization_id, max(1, min(limit, 200)))).fetchall()]

    def update_playbook(self, playbook_id: str, organization_id: str, **kwargs: Any) -> Optional[dict]:
        permitted = {"title", "playbook_type", "body", "tags", "status"}
        fields = {k: v for k, v in kwargs.items() if k in permitted and v is not None}
        if "status" in fields:
            fields["status"] = self._bounded(fields["status"], "active", {"active", "draft", "archived"})
        for key, limit in {"title": 180, "playbook_type": 80, "body": 8000, "tags": 500}.items():
            if key in fields:
                fields[key] = str(fields[key]).strip()[:limit]
        if not fields:
            return self.get_playbook(playbook_id, organization_id)
        fields["updated_at"] = self.now()
        cols = ", ".join(f"{k} = ?" for k in fields)
        vals = list(fields.values()) + [playbook_id, organization_id]
        with self.connect() as conn:
            cur = conn.execute(f"UPDATE legal_playbooks SET {cols} WHERE id = ? AND organization_id = ?", vals)
            if cur.rowcount == 0:
                return None
        return self.get_playbook(playbook_id, organization_id)

    def create_vendor(self, organization_id: str, name: str, **kwargs: Any) -> dict:
        now = self.now()
        item_id = self.new_id()
        status = self._bounded(kwargs.get("status"), "active", {"active", "preferred", "inactive"})
        hourly_rate = max(0.0, float(kwargs.get("hourly_rate") or 0))
        with self.connect() as conn:
            conn.execute(
                """INSERT INTO legal_vendors (id, organization_id, name, vendor_type, contact_email, practice_area, status, hourly_rate, currency, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    item_id,
                    organization_id,
                    name.strip()[:180],
                    (kwargs.get("vendor_type") or "outside_counsel").strip()[:60],
                    (kwargs.get("contact_email") or "").strip()[:255],
                    (kwargs.get("practice_area") or "").strip()[:120],
                    status,
                    hourly_rate,
                    (kwargs.get("currency") or "INR").strip().upper()[:10],
                    now,
                    now,
                ),
            )
        return self.get_vendor(item_id, organization_id) or {}

    def get_vendor(self, vendor_id: str, organization_id: str) -> Optional[dict]:
        return self._get_org_row("legal_vendors", vendor_id, organization_id)

    def list_vendors(self, organization_id: str, limit: int = 100) -> list[dict]:
        with self.connect() as conn:
            return [dict(row) for row in conn.execute("SELECT * FROM legal_vendors WHERE organization_id = ? ORDER BY updated_at DESC LIMIT ?", (organization_id, max(1, min(limit, 200)))).fetchall()]

    def update_vendor(self, vendor_id: str, organization_id: str, **kwargs: Any) -> Optional[dict]:
        permitted = {"name", "vendor_type", "contact_email", "practice_area", "status", "hourly_rate", "currency"}
        fields = {k: v for k, v in kwargs.items() if k in permitted and v is not None}
        if "status" in fields:
            fields["status"] = self._bounded(fields["status"], "active", {"active", "preferred", "inactive"})
        if "hourly_rate" in fields:
            fields["hourly_rate"] = max(0.0, float(fields["hourly_rate"] or 0))
        if "currency" in fields:
            fields["currency"] = str(fields["currency"] or "INR").strip().upper()[:10]
        for key, limit in {"name": 180, "vendor_type": 60, "contact_email": 255, "practice_area": 120}.items():
            if key in fields:
                fields[key] = str(fields[key]).strip()[:limit]
        if not fields:
            return self.get_vendor(vendor_id, organization_id)
        fields["updated_at"] = self.now()
        cols = ", ".join(f"{k} = ?" for k in fields)
        vals = list(fields.values()) + [vendor_id, organization_id]
        with self.connect() as conn:
            cur = conn.execute(f"UPDATE legal_vendors SET {cols} WHERE id = ? AND organization_id = ?", vals)
            if cur.rowcount == 0:
                return None
        return self.get_vendor(vendor_id, organization_id)

    def create_spend_entry(self, organization_id: str, amount: float, **kwargs: Any) -> dict:
        matter_id = kwargs.get("matter_id")
        if matter_id and not self.get_matter(matter_id, organization_id):
            raise ValueError("Matter not found in workspace")
        vendor_id = kwargs.get("vendor_id")
        if vendor_id and not self.get_vendor(vendor_id, organization_id):
            raise ValueError("Vendor not found in workspace")
        now = self.now()
        item_id = self.new_id()
        status = self._bounded(kwargs.get("status"), "pending", {"pending", "approved", "paid", "disputed", "rejected"})
        paid_date = kwargs.get("paid_date") or (now[:10] if status == "paid" else None)
        with self.connect() as conn:
            conn.execute(
                """INSERT INTO legal_spend_entries (id, organization_id, matter_id, vendor_id, invoice_number, description, amount, currency, status, issue_date, due_date, paid_date, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    item_id,
                    organization_id,
                    matter_id,
                    vendor_id,
                    (kwargs.get("invoice_number") or "").strip()[:120],
                    (kwargs.get("description") or "").strip()[:2000],
                    float(amount),
                    (kwargs.get("currency") or "INR").strip().upper()[:10],
                    status,
                    kwargs.get("issue_date"),
                    kwargs.get("due_date"),
                    paid_date,
                    now,
                    now,
                ),
            )
            if matter_id:
                conn.execute("UPDATE legal_matters SET updated_at = ? WHERE id = ? AND organization_id = ?", (now, matter_id, organization_id))
        return self.get_spend_entry(item_id, organization_id) or {}

    def get_spend_entry(self, spend_id: str, organization_id: str) -> Optional[dict]:
        return self._get_org_row("legal_spend_entries", spend_id, organization_id)

    def list_spend_entries(self, organization_id: str, limit: int = 100) -> list[dict]:
        with self.connect() as conn:
            return [dict(row) for row in conn.execute("SELECT * FROM legal_spend_entries WHERE organization_id = ? ORDER BY updated_at DESC LIMIT ?", (organization_id, max(1, min(limit, 200)))).fetchall()]

    def update_spend_entry(self, spend_id: str, organization_id: str, **kwargs: Any) -> Optional[dict]:
        permitted = {"matter_id", "vendor_id", "invoice_number", "description", "amount", "currency", "status", "issue_date", "due_date", "paid_date"}
        fields = {k: v for k, v in kwargs.items() if k in permitted and v is not None}
        if "matter_id" in fields and fields["matter_id"] and not self.get_matter(fields["matter_id"], organization_id):
            raise ValueError("Matter not found in workspace")
        if "vendor_id" in fields and fields["vendor_id"] and not self.get_vendor(fields["vendor_id"], organization_id):
            raise ValueError("Vendor not found in workspace")
        if "status" in fields:
            fields["status"] = self._bounded(fields["status"], "pending", {"pending", "approved", "paid", "disputed", "rejected"})
            if fields["status"] == "paid" and "paid_date" not in fields:
                fields["paid_date"] = self.now()[:10]
        if "amount" in fields:
            fields["amount"] = float(fields["amount"])
        if "currency" in fields:
            fields["currency"] = str(fields["currency"] or "INR").strip().upper()[:10]
        for key, limit in {"invoice_number": 120, "description": 2000}.items():
            if key in fields:
                fields[key] = str(fields[key]).strip()[:limit]
        if not fields:
            return self.get_spend_entry(spend_id, organization_id)
        fields["updated_at"] = self.now()
        cols = ", ".join(f"{k} = ?" for k in fields)
        vals = list(fields.values()) + [spend_id, organization_id]
        with self.connect() as conn:
            cur = conn.execute(f"UPDATE legal_spend_entries SET {cols} WHERE id = ? AND organization_id = ?", vals)
            if cur.rowcount == 0:
                return None
            matter_id = fields.get("matter_id") or (self.get_spend_entry(spend_id, organization_id) or {}).get("matter_id")
            if matter_id:
                conn.execute("UPDATE legal_matters SET updated_at = ? WHERE id = ? AND organization_id = ?", (fields["updated_at"], matter_id, organization_id))
        return self.get_spend_entry(spend_id, organization_id)

    def get_legal_ops_summary(self, organization_id: str) -> dict:
        with self.connect() as conn:
            matter_rows = conn.execute("SELECT status, COUNT(*) AS count FROM legal_matters WHERE organization_id = ? GROUP BY status", (organization_id,)).fetchall()
            intake_rows = conn.execute("SELECT status, COUNT(*) AS count FROM legal_intake_requests WHERE organization_id = ? GROUP BY status", (organization_id,)).fetchall()
            task_rows = conn.execute("SELECT status, COUNT(*) AS count FROM legal_tasks WHERE organization_id = ? GROUP BY status", (organization_id,)).fetchall()
            contract_rows = conn.execute("SELECT status, COUNT(*) AS count FROM legal_contracts WHERE organization_id = ? GROUP BY status", (organization_id,)).fetchall()
            high_risk = conn.execute("SELECT COUNT(*) FROM legal_contracts WHERE organization_id = ? AND risk_level IN ('high', 'critical')", (organization_id,)).fetchone()[0]
            overdue_tasks = conn.execute("SELECT COUNT(*) FROM legal_tasks WHERE organization_id = ? AND status != 'done' AND due_date IS NOT NULL AND DATE(due_date) < DATE('now')", (organization_id,)).fetchone()[0]
            upcoming_contracts = conn.execute("SELECT COUNT(*) FROM legal_contracts WHERE organization_id = ? AND renewal_date IS NOT NULL AND DATE(renewal_date) BETWEEN DATE('now') AND DATE('now', '+60 days')", (organization_id,)).fetchone()[0]
            overdue_contracts = conn.execute("SELECT COUNT(*) FROM legal_contracts WHERE organization_id = ? AND status NOT IN ('expired', 'signed', 'draft') AND renewal_date IS NOT NULL AND DATE(renewal_date) < DATE('now')", (organization_id,)).fetchone()[0]
            pending_signature = conn.execute("SELECT COUNT(*) FROM legal_contracts WHERE organization_id = ? AND status = 'approved'", (organization_id,)).fetchone()[0]
            open_obligations = conn.execute("SELECT COUNT(*) FROM legal_contract_obligations WHERE organization_id = ? AND status NOT IN ('done', 'waived')", (organization_id,)).fetchone()[0]
            overdue_obligations = conn.execute("SELECT COUNT(*) FROM legal_contract_obligations WHERE organization_id = ? AND status NOT IN ('done', 'waived') AND due_date IS NOT NULL AND DATE(due_date) < DATE('now')", (organization_id,)).fetchone()[0]
            open_spend = conn.execute("SELECT COALESCE(SUM(amount), 0) FROM legal_spend_entries WHERE organization_id = ? AND status != 'paid'", (organization_id,)).fetchone()[0]
            paid_spend = conn.execute("SELECT COALESCE(SUM(amount), 0) FROM legal_spend_entries WHERE organization_id = ? AND status = 'paid'", (organization_id,)).fetchone()[0]
            overdue_invoices = conn.execute("SELECT COUNT(*) FROM legal_spend_entries WHERE organization_id = ? AND status != 'paid' AND due_date IS NOT NULL AND DATE(due_date) < DATE('now')", (organization_id,)).fetchone()[0]
            active_playbooks = conn.execute("SELECT COUNT(*) FROM legal_playbooks WHERE organization_id = ? AND status = 'active'", (organization_id,)).fetchone()[0]
        return {
            "matters_by_status": {row["status"]: row["count"] for row in matter_rows},
            "intake_by_status": {row["status"]: row["count"] for row in intake_rows},
            "tasks_by_status": {row["status"]: row["count"] for row in task_rows},
            "contracts_by_status": {row["status"]: row["count"] for row in contract_rows},
            "high_risk_contracts": high_risk,
            "overdue_tasks": overdue_tasks,
            "renewals_due_60_days": upcoming_contracts,
            "overdue_contract_renewals": overdue_contracts,
            "pending_signature_contracts": pending_signature,
            "open_contract_obligations": open_obligations,
            "overdue_contract_obligations": overdue_obligations,
            "open_spend_total": float(open_spend or 0),
            "paid_spend_total": float(paid_spend or 0),
            "overdue_invoices": overdue_invoices,
            "active_playbooks": active_playbooks,
        }

    # ── Search Analytics ──────────────────────────────────────────

    def log_search(self, query: str, result_count: int) -> None:
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO search_analytics (query, result_count, timestamp) VALUES (?, ?, ?)",
                (query, result_count, self.now()),
            )


# ── Singleton ─────────────────────────────────────────────────────

_db: Optional[Database] = None


def get_db() -> Database:
    """Get or create the singleton Database instance."""
    global _db
    if _db is None:
        _db = Database()
    return _db
