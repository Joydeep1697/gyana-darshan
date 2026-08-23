# schemas.py — Pydantic Schemas for Conversations, Messages & Persistent Evidence

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class CreateConversationRequest(BaseModel):
    title: Optional[str] = Field(default="New Legal Consultation", max_length=200)

class UpdateConversationRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)

class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=2, max_length=4096, description="Legal question or scenario")
    top_k: Optional[int] = Field(default=4, ge=1, le=10)

class EvidenceRecordSchema(BaseModel):
    id: Optional[str] = None
    statute: str
    act_number: Optional[str] = "Act 45 of 2023"
    section: str
    heading: str
    source: str
    text_snippet: str
    provenance: str

class LegalAnswerSchema(BaseModel):
    id: Optional[str] = None
    grounding_status: str
    firewall_status: str
    intervention_count: int
    engine_version: str = "1.0.0"
    corpus_version: str = "2026.08.18"
    retriever_version: str = "1.0.0"
    firewall_version: str = "1.0.0"
    evidence: List[EvidenceRecordSchema] = []

class MessageSchema(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    latency_ms: float
    created_at: str
    legal_answer: Optional[LegalAnswerSchema] = None

class ConversationSummary(BaseModel):
    id: str
    user_id: str
    title: str
    created_at: str
    updated_at: str
    group_period: Optional[str] = None # 'Today', 'Yesterday', 'Older'

class ConversationDetailResponse(BaseModel):
    conversation: ConversationSummary
    messages: List[MessageSchema]

class SendMessageResponse(BaseModel):
    message_id: str
    role: str
    answer: str
    grounding_status: str
    latency_ms: float
    engine_version: str
    corpus_version: str
    evidence: List[EvidenceRecordSchema]
    remaining_quota: int
