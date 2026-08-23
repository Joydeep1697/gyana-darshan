# router.py — Product Conversation & Evidence API Router for Nyaya Darshana
#
# Provides:
# POST   /api/conversations
# GET    /api/conversations
# GET    /api/conversations/{id}
# PATCH  /api/conversations/{id}
# DELETE /api/conversations/{id}
# POST   /api/conversations/{id}/messages
# GET    /api/conversations/{id}/messages

import time
import asyncio
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Request, status

from api.auth.dependencies import get_current_user, get_user_quota_limits
from api.conversations.schemas import (
    CreateConversationRequest, UpdateConversationRequest, SendMessageRequest,
    SendMessageResponse, ConversationSummary, ConversationDetailResponse,
    MessageSchema, LegalAnswerSchema, EvidenceRecordSchema
)
from database.repository import (
    ConversationRepository, MessageRepository, LegalAnswerRepository,
    UsageRepository, AuditRepository
)
from retrieval.hybrid_retriever import AuthoritativeLegalRetriever
from verification.claim_firewall import LegalVerificationFirewall
from app.intelligence.legal_generation import LegalGenerationError, generate_grounded_legal_answer

router = APIRouter(prefix="/api/conversations", tags=["Conversations & Consultations"])

# Frozen Legal Engine Singletons
retriever = AuthoritativeLegalRetriever()
firewall = LegalVerificationFirewall()

# Engine Versioning Constants
ENGINE_VERSION = "1.0.0"
CORPUS_VERSION = "2026.08.18"
RETRIEVER_VERSION = "1.0.0"
FIREWALL_VERSION = "1.0.0"

def compute_group_period(dt_str: str) -> str:
    """Group conversations into 'Today', 'Yesterday', or 'Older'."""
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday_start = today_start - timedelta(days=1)

        if dt >= today_start:
            return "Today"
        elif dt >= yesterday_start:
            return "Yesterday"
        else:
            return "Older"
    except Exception:
        return "Older"

@router.post("", response_model=ConversationSummary, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    req: CreateConversationRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Create a new consultation session for the authenticated user."""
    title = req.title.strip() if req.title and req.title.strip() else "New Legal Consultation"
    conv = ConversationRepository.create_conversation(current_user["id"], title)
    return ConversationSummary(
        id=conv["id"],
        user_id=conv["user_id"],
        title=conv["title"],
        created_at=conv["created_at"],
        updated_at=conv["updated_at"],
        group_period="Today"
    )

@router.get("", response_model=List[ConversationSummary])
async def list_conversations(current_user: Dict[str, Any] = Depends(get_current_user)):
    """List all consultations for the authenticated user, grouped chronologically."""
    rows = ConversationRepository.list_user_conversations(current_user["id"])
    result = []
    for r in rows:
        result.append(ConversationSummary(
            id=r["id"],
            user_id=r["user_id"],
            title=r["title"],
            created_at=r["created_at"],
            updated_at=r["updated_at"],
            group_period=compute_group_period(r["updated_at"])
        ))
    return result

@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Retrieve consultation details and message history (with IDOR protection)."""
    conv = ConversationRepository.get_conversation(conversation_id, user_id=current_user["id"])
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consultation not found or access denied."
        )
    
    msg_rows = MessageRepository.list_conversation_messages(conversation_id)
    messages = []
    for m in msg_rows:
        la_schema = None
        if m.get("legal_answer_id"):
            ev_list = [
                EvidenceRecordSchema(
                    id=e.get("id"),
                    statute=e.get("statute", "BNS"),
                    act_number=e.get("act_number", "Act 45 of 2023"),
                    section=e.get("section", ""),
                    heading=e.get("heading", ""),
                    source=e.get("source", "Official Gazette of India"),
                    text_snippet=e.get("text_snippet", ""),
                    provenance=e.get("provenance", "Official Gazette of India")
                )
                for e in m.get("evidence", [])
            ]
            la_schema = LegalAnswerSchema(
                id=m["legal_answer_id"],
                grounding_status=m["grounding_status"],
                firewall_status=m["firewall_status"],
                intervention_count=m["intervention_count"],
                engine_version=m.get("engine_version", ENGINE_VERSION),
                corpus_version=m.get("corpus_version", CORPUS_VERSION),
                evidence=ev_list
            )
        
        messages.append(MessageSchema(
            id=m["id"],
            conversation_id=m["conversation_id"],
            role=m["role"],
            content=m["content"],
            latency_ms=m.get("latency_ms", 0.0),
            created_at=m["created_at"],
            legal_answer=la_schema
        ))

    return ConversationDetailResponse(
        conversation=ConversationSummary(
            id=conv["id"],
            user_id=conv["user_id"],
            title=conv["title"],
            created_at=conv["created_at"],
            updated_at=conv["updated_at"],
            group_period=compute_group_period(conv["updated_at"])
        ),
        messages=messages
    )

@router.patch("/{conversation_id}", response_model=ConversationSummary)
async def update_conversation(
    conversation_id: str,
    req: UpdateConversationRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Update consultation title (with IDOR protection)."""
    conv = ConversationRepository.get_conversation(conversation_id, user_id=current_user["id"])
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consultation not found.")
    
    ConversationRepository.update_title(conversation_id, req.title.strip(), current_user["id"])
    updated = ConversationRepository.get_conversation(conversation_id, user_id=current_user["id"])
    return ConversationSummary(
        id=updated["id"],
        user_id=updated["user_id"],
        title=updated["title"],
        created_at=updated["created_at"],
        updated_at=updated["updated_at"],
        group_period=compute_group_period(updated["updated_at"])
    )

@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Delete consultation and all attached messages and evidence (with IDOR protection)."""
    deleted = ConversationRepository.delete_conversation(conversation_id, current_user["id"])
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consultation not found or access denied.")
    return None

@router.post("/{conversation_id}/messages", response_model=SendMessageResponse)
async def send_message(
    conversation_id: str,
    req: SendMessageRequest,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Submit a legal inquiry into a consultation, invoke frozen grounding engine, and persist auditable evidence."""
    conv = ConversationRepository.get_conversation(conversation_id, user_id=current_user["id"])
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consultation not found.")

    # 1. Enforce User Daily Quota
    quota = get_user_quota_limits(current_user)
    if quota["remaining"] <= 0:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Daily legal consultation quota reached ({quota['limit']} queries/day). Please upgrade or try again tomorrow."
        )

    t0 = time.perf_counter()
    query = req.content.strip()

    # 2. Invoke Frozen Legal Grounding Engine
    evidence_pack = retriever.retrieve_evidence_pack(query, top_k=req.top_k)
    evidence_ctx = retriever.format_evidence_context(evidence_pack)

    try:
        generated_answer = await generate_grounded_legal_answer(query, evidence_ctx)
    except LegalGenerationError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    passed_fw, enforced_answer, claims = firewall.verify_and_enforce(generated_answer, evidence_pack)
    latency = round((time.perf_counter() - t0) * 1000, 2)
    grounding_status = "GROUNDED_AND_VERIFIED" if passed_fw else "AUTO_CORRECTED_BY_FIREWALL"

    # 3. Format Evidence Items
    formatted_evidence = []
    for s in evidence_pack.get("retrieved_sections", []):
        formatted_evidence.append({
            "statute": s.get("statute", "BNS"),
            "act_number": s.get("act_number", "Act 45 of 2023"),
            "section": str(s.get("section", "")),
            "heading": s.get("heading", ""),
            "source": s.get("source", "Official Gazette of India"),
            "text_snippet": s.get("text", "")[:450],
            "provenance": "Official Gazette of India (Extraordinary, Part II)"
        })

    # 4. Auto-update Conversation Title if still default
    if conv["title"] == "New Legal Consultation":
        auto_title = query[:45].strip() + ("..." if len(query) > 45 else "")
        ConversationRepository.update_title(conversation_id, auto_title, current_user["id"])

    # 5. Persist User Message, Assistant Message, Legal Answer, and Evidence Records
    MessageRepository.add_message(conversation_id, role="user", content=query, latency_ms=0.0)
    asst_msg = MessageRepository.add_message(conversation_id, role="assistant", content=enforced_answer, latency_ms=latency)

    LegalAnswerRepository.record_legal_answer(
        message_id=asst_msg["id"],
        grounding_status=grounding_status,
        firewall_status="PASS" if passed_fw else "MODIFIED",
        intervention_count=len(claims),
        evidence_items=formatted_evidence,
        engine_version=ENGINE_VERSION,
        corpus_version=CORPUS_VERSION,
        retriever_version=RETRIEVER_VERSION,
        firewall_version=FIREWALL_VERSION
    )

    # 6. Record Usage & Audit Event
    client_ip = request.client.host if request.client else "127.0.0.1"
    UsageRepository.record_usage(
        user_id=current_user["id"],
        endpoint="/api/conversations/messages",
        tokens=1,
        metadata={"latency_ms": latency, "grounding_status": grounding_status}
    )
    AuditRepository.log_audit(
        event_type="LEGAL_CONSULTATION_QUERY",
        user_id=current_user["id"],
        client_ip=client_ip,
        metadata={
            "conversation_id": conversation_id,
            "grounding_status": grounding_status,
            "evidence_count": len(formatted_evidence),
            "latency_ms": latency
        }
    )

    updated_quota = get_user_quota_limits(current_user)

    return SendMessageResponse(
        message_id=asst_msg["id"],
        role="assistant",
        answer=enforced_answer,
        grounding_status=grounding_status,
        latency_ms=latency,
        engine_version=ENGINE_VERSION,
        corpus_version=CORPUS_VERSION,
        evidence=[EvidenceRecordSchema(**e) for e in formatted_evidence],
        remaining_quota=updated_quota["remaining"]
    )
