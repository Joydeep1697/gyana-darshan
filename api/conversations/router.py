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
import re
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Request, Query, status
from fastapi.responses import Response

from api.auth.dependencies import get_current_user, get_user_quota_limits
from api.conversations.schemas import (
    AnswerFeedbackRequest,
    AnswerFeedbackResponse,
    ConversationDetailResponse,
    ConversationSummary,
    CreateConversationRequest,
    EvidenceRecordSchema,
    LegalAnswerSchema,
    MessageSchema,
    SendMessageRequest,
    SendMessageResponse,
    UpdateConversationRequest,
)
from database.repository import (
    ConversationRepository, MessageRepository, LegalAnswerRepository,
    UsageRepository, AuditRepository, FeedbackRepository
)
from retrieval.hybrid_retriever import AuthoritativeLegalRetriever
from verification.claim_firewall import LegalVerificationFirewall
from app.intelligence.legal_generation import LegalGenerationError, generate_grounded_legal_answer
from app.source_presenter import format_cited_evidence
from app.intelligence.clarification import clarification_questions
from app.exports.legal_memo import consultation_docx, consultation_markdown

router = APIRouter(prefix="/api/conversations", tags=["Conversations & Consultations"])

# Frozen Legal Engine Singletons
retriever = AuthoritativeLegalRetriever()
firewall = LegalVerificationFirewall()

# Engine Versioning Constants
ENGINE_VERSION = "1.1.0"
CORPUS_VERSION = "2026.08.26-transition"
RETRIEVER_VERSION = "1.1.0"
FIREWALL_VERSION = "1.1.0"

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
                    provenance=e.get("provenance", "Official Gazette of India"),
                    supporting_claim=e.get("supporting_claim") or None,
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


@router.get("/{conversation_id}/export")
async def export_conversation(
    conversation_id: str,
    format: str = Query(default="docx", pattern="^(docx|markdown)$"),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Export an owned consultation as an editable legal research memorandum."""
    conversation = ConversationRepository.get_conversation(conversation_id, user_id=current_user["id"])
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consultation not found.")
    messages = MessageRepository.list_conversation_messages(conversation_id)
    safe_name = re.sub(r"[^A-Za-z0-9_-]+", "-", conversation["title"]).strip("-")[:80] or "consultation"
    if format == "markdown":
        payload = consultation_markdown(conversation, messages).encode("utf-8")
        media_type = "text/markdown; charset=utf-8"
        extension = "md"
    else:
        payload = consultation_docx(conversation, messages)
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        extension = "docx"
    return Response(
        content=payload,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{safe_name}.{extension}"'},
    )


@router.put(
    "/{conversation_id}/messages/{message_id}/feedback",
    response_model=AnswerFeedbackResponse,
)
async def record_answer_feedback(
    conversation_id: str,
    message_id: str,
    feedback: AnswerFeedbackRequest,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Capture structured feedback only for an assistant answer owned by the user."""
    conversation = ConversationRepository.get_conversation(conversation_id, user_id=current_user["id"])
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consultation not found.")
    message = next(
        (
            item for item in MessageRepository.list_conversation_messages(conversation_id)
            if item["id"] == message_id and item["role"] == "assistant"
        ),
        None,
    )
    if not message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Answer not found.")
    saved = FeedbackRepository.record_feedback(
        message_id=message_id,
        user_id=current_user["id"],
        rating=feedback.rating,
        reason=feedback.reason,
        comment=feedback.comment.strip() if feedback.comment else None,
    )
    AuditRepository.log_audit(
        event_type="ANSWER_FEEDBACK_RECORDED",
        user_id=current_user["id"],
        client_ip=request.client.host if request.client else "127.0.0.1",
        metadata={"conversation_id": conversation_id, "message_id": message_id, "rating": feedback.rating},
    )
    return AnswerFeedbackResponse(
        message_id=message_id,
        rating=saved["rating"],
        reason=saved.get("reason"),
        comment=saved.get("comment"),
        updated_at=saved["updated_at"],
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

    questions = clarification_questions(query)
    if questions:
        if conv["title"] == "New Legal Consultation":
            auto_title = query[:45].strip() + ("..." if len(query) > 45 else "")
            ConversationRepository.update_title(conversation_id, auto_title, current_user["id"])
        MessageRepository.add_message(conversation_id, role="user", content=query, latency_ms=0.0)
        clarification = "I need one legally material detail before I can route this reliably:\n\n" + "\n".join(
            f"{index}. {question}" for index, question in enumerate(questions, start=1)
        )
        assistant = MessageRepository.add_message(
            conversation_id, role="assistant", content=clarification, latency_ms=0.0
        )
        return SendMessageResponse(
            message_id=assistant["id"],
            role="assistant",
            answer=clarification,
            grounding_status="CLARIFICATION_REQUIRED",
            latency_ms=0.0,
            engine_version=ENGINE_VERSION,
            corpus_version=CORPUS_VERSION,
            evidence=[],
            remaining_quota=quota["remaining"],
            response_type="clarification",
            clarification_questions=questions,
        )

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
    formatted_evidence = format_cited_evidence(enforced_answer, evidence_pack)

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
