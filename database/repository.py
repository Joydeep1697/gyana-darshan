# repository.py — Typed Repository CRUD Interface for Nyaya Darshana Database
#
# Provides safe parameterized database access for:
# Users, Sessions, Conversations, Messages, Legal Answers, Evidence, Usage, and Audit.

import uuid
import json
import sqlite3
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple

from database.connection import get_db_connection

def now_iso() -> str:
    """Current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()

class UserRepository:
    @staticmethod
    def create_user(email: str, password_hash: str, full_name: str, role: str = "USER") -> Dict[str, Any]:
        user_id = str(uuid.uuid4())
        created_at = now_iso()
        with get_db_connection() as conn:
            conn.execute(
                """
                INSERT INTO users (id, email, password_hash, full_name, role, is_verified, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 1, ?, ?)
                """,
                (user_id, email.lower().strip(), password_hash, full_name.strip(), role.upper(), created_at, created_at)
            )
        return UserRepository.get_by_id(user_id) # type: ignore

    @staticmethod
    def get_by_email(email: str) -> Optional[Dict[str, Any]]:
        with get_db_connection() as conn:
            cursor = conn.execute("SELECT * FROM users WHERE email = ?", (email.lower().strip(),))
            row = cursor.fetchone()
            return dict(row) if row else None

    @staticmethod
    def get_by_id(user_id: str) -> Optional[Dict[str, Any]]:
        with get_db_connection() as conn:
            cursor = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    @staticmethod
    def count_users() -> int:
        with get_db_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM users")
            return cursor.fetchone()[0]

class SessionRepository:
    @staticmethod
    def create_session(user_id: str, token_hash: str, expires_at: str) -> Dict[str, Any]:
        session_id = str(uuid.uuid4())
        created_at = now_iso()
        with get_db_connection() as conn:
            conn.execute(
                """
                INSERT INTO sessions (id, user_id, token_hash, expires_at, created_at, revoked_at)
                VALUES (?, ?, ?, ?, ?, NULL)
                """,
                (session_id, user_id, token_hash, expires_at, created_at)
            )
        return {"id": session_id, "user_id": user_id, "token_hash": token_hash, "expires_at": expires_at}

    @staticmethod
    def get_active_session(token_hash: str) -> Optional[Dict[str, Any]]:
        with get_db_connection() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM sessions 
                WHERE token_hash = ? AND revoked_at IS NULL AND expires_at > ?
                """,
                (token_hash, now_iso())
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    @staticmethod
    def revoke_session(token_hash: str) -> bool:
        with get_db_connection() as conn:
            cursor = conn.execute(
                "UPDATE sessions SET revoked_at = ? WHERE token_hash = ? AND revoked_at IS NULL",
                (now_iso(), token_hash)
            )
            return cursor.rowcount > 0

    @staticmethod
    def revoke_all_user_sessions(user_id: str) -> int:
        with get_db_connection() as conn:
            cursor = conn.execute(
                "UPDATE sessions SET revoked_at = ? WHERE user_id = ? AND revoked_at IS NULL",
                (now_iso(), user_id)
            )
            return cursor.rowcount

class ConversationRepository:
    @staticmethod
    def create_conversation(user_id: str, title: str = "New Legal Consultation") -> Dict[str, Any]:
        conv_id = str(uuid.uuid4())
        created_at = now_iso()
        with get_db_connection() as conn:
            conn.execute(
                """
                INSERT INTO conversations (id, user_id, title, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (conv_id, user_id, title, created_at, created_at)
            )
        return {"id": conv_id, "user_id": user_id, "title": title, "created_at": created_at, "updated_at": created_at}

    @staticmethod
    def get_conversation(conv_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        with get_db_connection() as conn:
            if user_id:
                cursor = conn.execute("SELECT * FROM conversations WHERE id = ? AND user_id = ?", (conv_id, user_id))
            else:
                cursor = conn.execute("SELECT * FROM conversations WHERE id = ?", (conv_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    @staticmethod
    def list_user_conversations(user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        with get_db_connection() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM conversations 
                WHERE user_id = ? 
                ORDER BY updated_at DESC 
                LIMIT ?
                """,
                (user_id, limit)
            )
            return [dict(r) for r in cursor.fetchall()]

    @staticmethod
    def update_title(conv_id: str, title: str, user_id: str) -> bool:
        with get_db_connection() as conn:
            cursor = conn.execute(
                "UPDATE conversations SET title = ?, updated_at = ? WHERE id = ? AND user_id = ?",
                (title, now_iso(), conv_id, user_id)
            )
            return cursor.rowcount > 0

    @staticmethod
    def touch_conversation(conv_id: str) -> None:
        with get_db_connection() as conn:
            conn.execute("UPDATE conversations SET updated_at = ? WHERE id = ?", (now_iso(), conv_id))

    @staticmethod
    def delete_conversation(conv_id: str, user_id: str) -> bool:
        with get_db_connection() as conn:
            cursor = conn.execute("DELETE FROM conversations WHERE id = ? AND user_id = ?", (conv_id, user_id))
            return cursor.rowcount > 0

class MessageRepository:
    @staticmethod
    def add_message(conversation_id: str, role: str, content: str, latency_ms: float = 0.0) -> Dict[str, Any]:
        msg_id = str(uuid.uuid4())
        created_at = now_iso()
        with get_db_connection() as conn:
            conn.execute(
                """
                INSERT INTO messages (id, conversation_id, role, content, latency_ms, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (msg_id, conversation_id, role, content, latency_ms, created_at)
            )
            # Touch conversation timestamp
            conn.execute("UPDATE conversations SET updated_at = ? WHERE id = ?", (created_at, conversation_id))
        return {
            "id": msg_id,
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
            "latency_ms": latency_ms,
            "created_at": created_at
        }

    @staticmethod
    def list_conversation_messages(conversation_id: str) -> List[Dict[str, Any]]:
        with get_db_connection() as conn:
            cursor = conn.execute(
                """
                SELECT m.*, 
                       la.id as legal_answer_id, la.grounding_status, la.firewall_status, 
                       la.intervention_count, la.engine_version, la.corpus_version
                FROM messages m
                LEFT JOIN legal_answers la ON la.message_id = m.id
                WHERE m.conversation_id = ?
                ORDER BY m.created_at ASC
                """,
                (conversation_id,)
            )
            rows = [dict(r) for r in cursor.fetchall()]

            # Attach evidence records to answers
            for row in rows:
                if row.get("legal_answer_id"):
                    ev_cursor = conn.execute(
                        "SELECT * FROM evidence_records WHERE legal_answer_id = ?",
                        (row["legal_answer_id"],)
                    )
                    row["evidence"] = [dict(e) for e in ev_cursor.fetchall()]
                else:
                    row["evidence"] = []
            return rows

class LegalAnswerRepository:
    @staticmethod
    def record_legal_answer(
        message_id: str,
        grounding_status: str,
        firewall_status: str,
        intervention_count: int,
        evidence_items: List[Dict[str, Any]],
        engine_version: str = "1.0.0",
        corpus_version: str = "2026.08.18",
        retriever_version: str = "1.0.0",
        firewall_version: str = "1.0.0"
    ) -> Dict[str, Any]:
        answer_id = str(uuid.uuid4())
        created_at = now_iso()
        with get_db_connection() as conn:
            conn.execute(
                """
                INSERT INTO legal_answers (
                    id, message_id, grounding_status, firewall_status, intervention_count,
                    engine_version, corpus_version, retriever_version, firewall_version, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    answer_id, message_id, grounding_status, firewall_status, intervention_count,
                    engine_version, corpus_version, retriever_version, firewall_version, created_at
                )
            )

            # Insert all evidence items
            for item in evidence_items:
                ev_id = str(uuid.uuid4())
                conn.execute(
                    """
                    INSERT INTO evidence_records (
                        id, legal_answer_id, statute, act_number, section, heading, source, text_snippet, provenance
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        ev_id,
                        answer_id,
                        item.get("statute", "BNS"),
                        item.get("act_number", "Act 45 of 2023"),
                        str(item.get("section", "")),
                        item.get("heading", ""),
                        item.get("source", "Official Gazette of India"),
                        item.get("text_snippet", "")[:1000],
                        item.get("provenance", "Official Gazette of India")
                    )
                )

        return {
            "id": answer_id,
            "message_id": message_id,
            "grounding_status": grounding_status,
            "evidence_count": len(evidence_items),
            "engine_version": engine_version
        }

class UsageRepository:
    @staticmethod
    def record_usage(user_id: Optional[str], endpoint: str, tokens: int = 1, metadata: Optional[Dict[str, Any]] = None) -> None:
        usage_id = str(uuid.uuid4())
        created_at = now_iso()
        meta_str = json.dumps(metadata) if metadata else None
        with get_db_connection() as conn:
            conn.execute(
                """
                INSERT INTO usage_events (id, user_id, endpoint, tokens_used, created_at, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (usage_id, user_id, endpoint, tokens, created_at, meta_str)
            )

    @staticmethod
    def get_user_daily_query_count(user_id: str) -> int:
        """Count total queries by user in the past 24 hours."""
        with get_db_connection() as conn:
            cursor = conn.execute(
                """
                SELECT COUNT(*) FROM usage_events 
                WHERE user_id = ? AND created_at >= datetime('now', '-1 day')
                """,
                (user_id,)
            )
            return cursor.fetchone()[0]

    @staticmethod
    def get_ip_daily_query_count(client_ip: str) -> int:
        """Count total queries by IP in the past 24 hours."""
        with get_db_connection() as conn:
            cursor = conn.execute(
                """
                SELECT COUNT(*) FROM audit_events 
                WHERE client_ip = ? AND created_at >= datetime('now', '-1 day')
                """,
                (client_ip,)
            )
            return cursor.fetchone()[0]

class AuditRepository:
    @staticmethod
    def log_audit(
        event_type: str,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
        client_ip: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        audit_id = str(uuid.uuid4())
        created_at = now_iso()
        meta_str = json.dumps(metadata) if metadata else None
        with get_db_connection() as conn:
            conn.execute(
                """
                INSERT INTO audit_events (id, user_id, event_type, request_id, client_ip, metadata_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (audit_id, user_id, event_type, request_id, client_ip, meta_str, created_at)
            )
