# models.py — Declarative Schema & DDL for Nyaya Darshana Product Database
#
# Covers: users, sessions, conversations, messages, legal_answers, evidence, usage_events, audit_events

SCHEMA_DDL = """
-- 1. Users Table
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'USER', -- 'USER', 'ADMIN', 'SUPERADMIN'
    is_verified INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);

-- Organizations and explicit workspace membership
CREATE TABLE IF NOT EXISTS organizations (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    is_personal INTEGER NOT NULL DEFAULT 0,
    created_by TEXT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    retention_days INTEGER CHECK (retention_days IS NULL OR retention_days >= 30),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS organization_members (
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('OWNER', 'ADMIN', 'MEMBER', 'VIEWER')),
    created_at TEXT NOT NULL,
    PRIMARY KEY (organization_id, user_id)
);
CREATE INDEX IF NOT EXISTS idx_org_members_user ON organization_members(user_id);

-- 2. Sessions Table
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    revoked_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token_hash);

-- 3. Conversations Table
CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    organization_id TEXT REFERENCES organizations(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_updated ON conversations(updated_at DESC);

-- 4. Messages Table
CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL, -- 'user', 'assistant', 'system'
    content TEXT NOT NULL,
    latency_ms REAL DEFAULT 0.0,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_created ON messages(created_at ASC);

-- 5. Legal Answers Table (Engine Decisions & Auditing)
CREATE TABLE IF NOT EXISTS legal_answers (
    id TEXT PRIMARY KEY,
    message_id TEXT NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    grounding_status TEXT NOT NULL, -- 'GROUNDED_AND_VERIFIED', 'AUTO_CORRECTED_BY_FIREWALL'
    firewall_status TEXT NOT NULL,
    intervention_count INTEGER NOT NULL DEFAULT 0,
    engine_version TEXT NOT NULL DEFAULT '1.0.0',
    corpus_version TEXT NOT NULL DEFAULT '2026.08.18',
    retriever_version TEXT NOT NULL DEFAULT '1.0.0',
    firewall_version TEXT NOT NULL DEFAULT '1.0.0',
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_legal_answers_msg ON legal_answers(message_id);

-- 6. Evidence Records Table (Persistent Official Gazette Citations)
CREATE TABLE IF NOT EXISTS evidence_records (
    id TEXT PRIMARY KEY,
    legal_answer_id TEXT NOT NULL REFERENCES legal_answers(id) ON DELETE CASCADE,
    statute TEXT NOT NULL,
    act_number TEXT,
    section TEXT NOT NULL,
    heading TEXT NOT NULL,
    source TEXT NOT NULL,
    text_snippet TEXT NOT NULL,
    provenance TEXT NOT NULL,
    supporting_claim TEXT
);
CREATE INDEX IF NOT EXISTS idx_evidence_answer ON evidence_records(legal_answer_id);
CREATE INDEX IF NOT EXISTS idx_evidence_section ON evidence_records(statute, section);

-- 7. Structured Answer Feedback
CREATE TABLE IF NOT EXISTS answer_feedback (
    id TEXT PRIMARY KEY,
    message_id TEXT NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    rating TEXT NOT NULL CHECK (rating IN ('helpful', 'not_helpful')),
    reason TEXT CHECK (reason IN ('incorrect_section', 'missing_issue', 'unsupported_citation', 'unclear', 'other') OR reason IS NULL),
    comment TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(message_id, user_id)
);
CREATE INDEX IF NOT EXISTS idx_feedback_message ON answer_feedback(message_id);
CREATE INDEX IF NOT EXISTS idx_feedback_user ON answer_feedback(user_id);

-- 8. Usage Events Table (Quota & Rate Limit Auditing)
CREATE TABLE IF NOT EXISTS usage_events (
    id TEXT PRIMARY KEY,
    user_id TEXT REFERENCES users(id) ON DELETE SET NULL,
    endpoint TEXT NOT NULL,
    tokens_used INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    metadata_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_usage_user ON usage_events(user_id);
CREATE INDEX IF NOT EXISTS idx_usage_created ON usage_events(created_at);

-- 9. Audit Events Table (Security & Governance Trail)
CREATE TABLE IF NOT EXISTS audit_events (
    id TEXT PRIMARY KEY,
    user_id TEXT REFERENCES users(id) ON DELETE SET NULL,
    event_type TEXT NOT NULL,
    request_id TEXT,
    client_ip TEXT,
    metadata_json TEXT,
    created_at TEXT NOT NULL,
    organization_id TEXT REFERENCES organizations(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_events(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_type ON audit_events(event_type);
"""
