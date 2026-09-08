"""Nyaya Darshan — Pydantic Request / Response Models."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Vault Documents ───────────────────────────────────────────────

class DocumentResponse(BaseModel):
    id: str
    filename: str
    sha256: Optional[str] = None
    file_size: int = 0
    status: str = "uploading"
    category: Optional[str] = None
    domain: Optional[str] = None
    authority_level: Optional[str] = None
    authority_weight: float = 1.0
    risk_score: int = 0
    pages: int = 0
    clauses_count: int = 0
    citations_count: int = 0
    summary: Optional[str] = None
    upload_time: str = ""
    process_time: Optional[str] = None
    error_msg: Optional[str] = None


class DocumentDetail(DocumentResponse):
    entities: list[EntityItem] = []
    clauses: list[ClauseItem] = []
    deadlines: list[DeadlineItem] = []
    links: list[GraphEdge] = []
    related: list[RelatedDocument] = []


class DocumentUploadResponse(BaseModel):
    id: str
    filename: str
    message: str = "Upload received — processing started"


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]
    total: int
    offset: int = 0
    limit: int = 100


class DocumentQuestionRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=3000)
    document_ids: list[str] = Field(..., min_length=1, max_length=3)


class DocumentQuestionSource(BaseModel):
    document_id: str
    filename: str
    page: int
    snippet: str


class DocumentQuestionResponse(BaseModel):
    answer: str
    sources: list[DocumentQuestionSource]


class PrecedentSearchResult(BaseModel):
    id: str
    document_id: str
    filename: str = ""
    title: str = ""
    citation: str = ""
    court: str = ""
    judges: list[str] = []
    petitioner: str = ""
    respondent: str = ""
    case_number: str = ""
    decision_date: str = ""
    year: Optional[int] = None
    sections: list[str] = []
    excerpt: str = ""
    source_page: int = 1
    source_name: str = ""
    source_url: str = ""
    provenance_status: str = "uploaded"
    scope: str = "workspace"
    paragraphs: list[dict[str, Any]] = []
    relevance: float = 0.0


class PrecedentSearchResponse(BaseModel):
    results: list[PrecedentSearchResult]
    total: int
    query: str
    filters: dict[str, Any] = {}


class ContractClauseFinding(BaseModel):
    type: str
    risk: str = "low"
    page: Optional[int] = None
    excerpt: str


class ContractRiskFinding(BaseModel):
    level: str
    title: str
    explanation: str
    clause_type: str = ""
    excerpt: str = ""


class ContractObligationSuggestion(BaseModel):
    id: str
    title: str
    category: str = "general"
    priority: str = "medium"
    due_date: Optional[str] = None
    source_page: Optional[int] = None
    source_clause: str
    confidence: str = "medium"


class NdaReviewProfile(BaseModel):
    detected: bool = False
    kind: str = "general_contract"
    signals: list[str] = []
    missing: list[str] = []


class ContractReviewResponse(BaseModel):
    filename: str
    document_type: str = "contract"
    overall_risk: str = "low"
    summary: str
    clauses: list[ContractClauseFinding]
    risks: list[ContractRiskFinding]
    obligation_suggestions: list[ContractObligationSuggestion] = []
    nda: NdaReviewProfile
    review_recommended: bool = True
    review_reason: str


class ContractObligationAcceptRequest(BaseModel):
    suggestion: ContractObligationSuggestion
    contract_id: Optional[str] = None
    matter_id: Optional[str] = None
    owner: str = Field(default="", max_length=180)


class ContractObligationAcceptResponse(BaseModel):
    contract: "LegalContractResponse"
    obligation: "LegalContractObligationResponse"


# ── Entities ──────────────────────────────────────────────────────

class EntityItem(BaseModel):
    entity_type: str
    entity_value: str
    context_snippet: Optional[str] = None


# ── Clauses ───────────────────────────────────────────────────────

class ClauseItem(BaseModel):
    clause_type: str
    clause_text: str
    risk_level: str = "low"
    start_page: Optional[int] = None


# ── Deadlines ─────────────────────────────────────────────────────

class DeadlineItem(BaseModel):
    id: Optional[int] = None
    doc_id: Optional[str] = None
    filename: Optional[str] = None
    deadline_type: str
    deadline_date: Optional[str] = None
    description: Optional[str] = None
    status: str = "upcoming"


# ── Knowledge Graph ───────────────────────────────────────────────

class GraphEdge(BaseModel):
    source_doc_id: str
    target_doc_id: Optional[str] = None
    target_filename: Optional[str] = None
    relationship: str
    source_ref: str = ""
    target_ref: str = ""
    confidence: float = 0.5


class RelatedDocument(BaseModel):
    id: str
    filename: str
    category: Optional[str] = None
    domain: Optional[str] = None
    relationship: str = "related"
    relevance: float = 0.0


class SectionEntry(BaseModel):
    section_ref: str
    doc_id: str
    filename: Optional[str] = None
    category: Optional[str] = None
    context_type: str = "citing"
    snippet: Optional[str] = None


class GraphNetwork(BaseModel):
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]




# ── Legal Operations ──────────────────────────────────────────────

class LegalMatterCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=160)
    matter_type: str = Field(default="general", max_length=60)
    status: str = Field(default="open", max_length=30)
    priority: str = Field(default="medium", max_length=30)
    description: str = Field(default="", max_length=3000)
    due_date: Optional[str] = Field(default=None, max_length=30)


class LegalMatterUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=2, max_length=160)
    matter_type: Optional[str] = Field(default=None, max_length=60)
    status: Optional[str] = Field(default=None, max_length=30)
    priority: Optional[str] = Field(default=None, max_length=30)
    description: Optional[str] = Field(default=None, max_length=3000)
    due_date: Optional[str] = Field(default=None, max_length=30)


class LegalMatterResponse(BaseModel):
    id: str
    organization_id: str
    title: str
    matter_type: str = "general"
    status: str = "open"
    priority: str = "medium"
    description: str = ""
    owner_user_id: Optional[str] = None
    due_date: Optional[str] = None
    created_at: str
    updated_at: str


class LegalIntakeCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=180)
    request_type: str = Field(default="general", max_length=60)
    summary: str = Field(default="", max_length=4000)
    urgency: str = Field(default="medium", max_length=30)
    matter_id: Optional[str] = None


class LegalIntakeUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=2, max_length=180)
    request_type: Optional[str] = Field(default=None, max_length=60)
    summary: Optional[str] = Field(default=None, max_length=4000)
    urgency: Optional[str] = Field(default=None, max_length=30)
    status: Optional[str] = Field(default=None, max_length=30)
    matter_id: Optional[str] = None


class LegalIntakeConvertRequest(BaseModel):
    matter_title: Optional[str] = Field(default=None, min_length=2, max_length=160)
    matter_type: Optional[str] = Field(default=None, max_length=60)
    priority: Optional[str] = Field(default=None, max_length=30)
    due_date: Optional[str] = Field(default=None, max_length=30)


class LegalIntakeResponse(BaseModel):
    id: str
    organization_id: str
    matter_id: Optional[str] = None
    requester_user_id: Optional[str] = None
    request_type: str = "general"
    title: str
    summary: str = ""
    urgency: str = "medium"
    status: str = "new"
    created_at: str
    updated_at: str


class LegalIntakeConvertResponse(BaseModel):
    intake: LegalIntakeResponse
    matter: LegalMatterResponse


class LegalTaskCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=180)
    matter_id: Optional[str] = None
    priority: str = Field(default="medium", max_length=30)
    due_date: Optional[str] = Field(default=None, max_length=30)


class LegalTaskUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=2, max_length=180)
    matter_id: Optional[str] = None
    status: Optional[str] = Field(default=None, max_length=30)
    priority: Optional[str] = Field(default=None, max_length=30)
    due_date: Optional[str] = Field(default=None, max_length=30)


class LegalTaskResponse(BaseModel):
    id: str
    organization_id: str
    matter_id: Optional[str] = None
    title: str
    status: str = "open"
    priority: str = "medium"
    assignee_user_id: Optional[str] = None
    due_date: Optional[str] = None
    created_at: str
    updated_at: str


class LegalContractCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=180)
    counterparty: str = Field(default="", max_length=180)
    contract_type: str = Field(default="general", max_length=80)
    status: str = Field(default="draft", max_length=30)
    risk_level: str = Field(default="unknown", max_length=30)
    matter_id: Optional[str] = None
    document_id: Optional[str] = None
    effective_date: Optional[str] = Field(default=None, max_length=30)
    expiry_date: Optional[str] = Field(default=None, max_length=30)
    renewal_date: Optional[str] = Field(default=None, max_length=30)


class LegalContractUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=2, max_length=180)
    counterparty: Optional[str] = Field(default=None, max_length=180)
    contract_type: Optional[str] = Field(default=None, max_length=80)
    status: Optional[str] = Field(default=None, max_length=30)
    risk_level: Optional[str] = Field(default=None, max_length=30)
    matter_id: Optional[str] = None
    document_id: Optional[str] = None
    effective_date: Optional[str] = Field(default=None, max_length=30)
    expiry_date: Optional[str] = Field(default=None, max_length=30)
    renewal_date: Optional[str] = Field(default=None, max_length=30)


class LegalContractResponse(BaseModel):
    id: str
    organization_id: str
    document_id: Optional[str] = None
    matter_id: Optional[str] = None
    title: str
    counterparty: str = ""
    contract_type: str = "general"
    status: str = "draft"
    risk_level: str = "unknown"
    effective_date: Optional[str] = None
    expiry_date: Optional[str] = None
    renewal_date: Optional[str] = None
    lifecycle_stage: str = "draft"
    reminder_status: str = "none"
    days_to_renewal: Optional[int] = None
    created_at: str
    updated_at: str


class LegalContractReminderResponse(BaseModel):
    id: str
    title: str
    counterparty: str = ""
    status: str = "draft"
    risk_level: str = "unknown"
    renewal_date: str
    days_to_renewal: int
    reminder_status: str
    matter_id: Optional[str] = None


class LegalContractObligationCreate(BaseModel):
    contract_id: str
    matter_id: Optional[str] = None
    title: str = Field(..., min_length=2, max_length=180)
    owner: str = Field(default="", max_length=180)
    category: str = Field(default="general", max_length=80)
    status: str = Field(default="open", max_length=30)
    priority: str = Field(default="medium", max_length=30)
    due_date: Optional[str] = Field(default=None, max_length=30)
    source_clause: str = Field(default="", max_length=1000)


class LegalContractObligationUpdate(BaseModel):
    contract_id: Optional[str] = None
    matter_id: Optional[str] = None
    title: Optional[str] = Field(default=None, min_length=2, max_length=180)
    owner: Optional[str] = Field(default=None, max_length=180)
    category: Optional[str] = Field(default=None, max_length=80)
    status: Optional[str] = Field(default=None, max_length=30)
    priority: Optional[str] = Field(default=None, max_length=30)
    due_date: Optional[str] = Field(default=None, max_length=30)
    source_clause: Optional[str] = Field(default=None, max_length=1000)


class LegalContractObligationResponse(BaseModel):
    id: str
    organization_id: str
    contract_id: str
    matter_id: Optional[str] = None
    title: str
    owner: str = ""
    category: str = "general"
    status: str = "open"
    priority: str = "medium"
    due_date: Optional[str] = None
    source_clause: str = ""
    created_at: str
    updated_at: str


class LegalVendorCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=180)
    vendor_type: str = Field(default="outside_counsel", max_length=60)
    contact_email: str = Field(default="", max_length=255)
    practice_area: str = Field(default="", max_length=120)
    status: str = Field(default="active", max_length=30)
    hourly_rate: float = Field(default=0, ge=0)
    currency: str = Field(default="INR", max_length=10)


class LegalVendorUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=180)
    vendor_type: Optional[str] = Field(default=None, max_length=60)
    contact_email: Optional[str] = Field(default=None, max_length=255)
    practice_area: Optional[str] = Field(default=None, max_length=120)
    status: Optional[str] = Field(default=None, max_length=30)
    hourly_rate: Optional[float] = Field(default=None, ge=0)
    currency: Optional[str] = Field(default=None, max_length=10)


class LegalVendorResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    vendor_type: str = "outside_counsel"
    contact_email: str = ""
    practice_area: str = ""
    status: str = "active"
    hourly_rate: float = 0
    currency: str = "INR"
    created_at: str
    updated_at: str


class LegalSpendCreate(BaseModel):
    matter_id: Optional[str] = None
    vendor_id: Optional[str] = None
    invoice_number: str = Field(default="", max_length=120)
    description: str = Field(default="", max_length=2000)
    amount: float = Field(..., gt=0)
    currency: str = Field(default="INR", max_length=10)
    status: str = Field(default="pending", max_length=30)
    issue_date: Optional[str] = Field(default=None, max_length=30)
    due_date: Optional[str] = Field(default=None, max_length=30)
    paid_date: Optional[str] = Field(default=None, max_length=30)


class LegalSpendUpdate(BaseModel):
    matter_id: Optional[str] = None
    vendor_id: Optional[str] = None
    invoice_number: Optional[str] = Field(default=None, max_length=120)
    description: Optional[str] = Field(default=None, max_length=2000)
    amount: Optional[float] = Field(default=None, gt=0)
    currency: Optional[str] = Field(default=None, max_length=10)
    status: Optional[str] = Field(default=None, max_length=30)
    issue_date: Optional[str] = Field(default=None, max_length=30)
    due_date: Optional[str] = Field(default=None, max_length=30)
    paid_date: Optional[str] = Field(default=None, max_length=30)


class LegalSpendResponse(BaseModel):
    id: str
    organization_id: str
    matter_id: Optional[str] = None
    vendor_id: Optional[str] = None
    invoice_number: str = ""
    description: str = ""
    amount: float
    currency: str = "INR"
    status: str = "pending"
    issue_date: Optional[str] = None
    due_date: Optional[str] = None
    paid_date: Optional[str] = None
    created_at: str
    updated_at: str




class LegalPlaybookCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=180)
    playbook_type: str = Field(default="general", max_length=80)
    body: str = Field(default="", max_length=8000)
    tags: str = Field(default="", max_length=500)
    status: str = Field(default="active", max_length=30)


class LegalPlaybookUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=2, max_length=180)
    playbook_type: Optional[str] = Field(default=None, max_length=80)
    body: Optional[str] = Field(default=None, max_length=8000)
    tags: Optional[str] = Field(default=None, max_length=500)
    status: Optional[str] = Field(default=None, max_length=30)


class LegalPlaybookResponse(BaseModel):
    id: str
    organization_id: str
    title: str
    playbook_type: str = "general"
    body: str = ""
    tags: str = ""
    status: str = "active"
    created_at: str
    updated_at: str


class LegalMatterNoteCreate(BaseModel):
    body: str = Field(..., min_length=1, max_length=4000)


class LegalMatterNoteResponse(BaseModel):
    id: str
    organization_id: str
    matter_id: str
    author_user_id: Optional[str] = None
    body: str
    created_at: str


class LegalMatterDocumentLinkCreate(BaseModel):
    document_id: str


class LegalMatterDocumentResponse(BaseModel):
    link_id: str
    linked_at: str
    id: str
    filename: str
    category: Optional[str] = None
    domain: Optional[str] = None
    status: str = "uploading"
    pages: int = 0
    file_size: int = 0


class LegalMatterActivityResponse(BaseModel):
    kind: str
    id: str
    label: str
    detail: str = ""
    timestamp: str


class LegalMatterBriefSource(BaseModel):
    kind: str
    id: str
    label: str


class LegalMatterBriefResponse(BaseModel):
    matter_id: str
    title: str
    brief: str
    sources: list[LegalMatterBriefSource]
    generated_from: dict[str, int]


class LegalMatterDraftRequest(BaseModel):
    prompt: str = Field(default="", max_length=3000)
    precedent_ids: list[str] = Field(default_factory=list, max_length=20)


class LegalMatterDraftEvidence(BaseModel):
    kind: str
    id: str
    label: str
    citation: str = ""
    excerpt: str = ""
    status: str = ""


class LegalMatterDraftResponse(BaseModel):
    id: Optional[str] = None
    matter_id: str
    organization_id: Optional[str] = None
    title: str
    question: str
    draft: str
    review_status: str = "draft"
    reviewer_note: str = ""
    sources: list[LegalMatterDraftEvidence]
    unsupported_claims: list[str] = []
    generated_from: dict[str, int]
    created_by_user_id: Optional[str] = None
    reviewed_by_user_id: Optional[str] = None
    reviewed_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class LegalMatterDraftListResponse(BaseModel):
    drafts: list[LegalMatterDraftResponse]
    total: int


class LegalMatterDraftReviewUpdate(BaseModel):
    review_status: str = Field(default="reviewed", max_length=30)
    reviewer_note: str = Field(default="", max_length=4000)


class LegalOpsReportResponse(BaseModel):
    title: str
    report: str
    generated_from: dict[str, int]


class LegalMatterDetailResponse(LegalMatterResponse):
    documents: list[LegalMatterDocumentResponse] = []
    notes: list[LegalMatterNoteResponse] = []
    tasks: list[LegalTaskResponse] = []
    contracts: list[LegalContractResponse] = []
    obligations: list[LegalContractObligationResponse] = []
    spend_entries: list[LegalSpendResponse] = []
    playbooks: list[LegalPlaybookResponse] = []
    intakes: list[LegalIntakeResponse] = []
    drafts: list[LegalMatterDraftResponse] = []
    activity: list[LegalMatterActivityResponse] = []


class LegalOpsSearchResponseItem(BaseModel):
    kind: str
    id: str
    title: str
    status: str = ""
    secondary: str = ""
    snippet: str = ""
    timestamp: str = ""


class LegalOpsSearchResponse(BaseModel):
    results: list[LegalOpsSearchResponseItem]


class LegalOpsSummary(BaseModel):
    matters_by_status: dict[str, int]
    intake_by_status: dict[str, int]
    tasks_by_status: dict[str, int]
    contracts_by_status: dict[str, int]
    high_risk_contracts: int = 0
    overdue_tasks: int = 0
    renewals_due_60_days: int = 0
    overdue_contract_renewals: int = 0
    pending_signature_contracts: int = 0
    open_contract_obligations: int = 0
    overdue_contract_obligations: int = 0
    open_spend_total: float = 0
    paid_spend_total: float = 0
    overdue_invoices: int = 0
    active_playbooks: int = 0


class LegalOpsWorkspaceResponse(BaseModel):
    summary: LegalOpsSummary
    matters: list[LegalMatterResponse]
    intakes: list[LegalIntakeResponse]
    tasks: list[LegalTaskResponse]
    contracts: list[LegalContractResponse]
    obligations: list[LegalContractObligationResponse] = []
    vendors: list[LegalVendorResponse] = []
    spend_entries: list[LegalSpendResponse] = []
    playbooks: list[LegalPlaybookResponse] = []
    contract_reminders: list[LegalContractReminderResponse] = []


# ── Chat ──────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=5000)
    session_id: Optional[str] = None
    top_k: int = Field(default=10, ge=1, le=50)
    use_reranker: bool = True


class ChatSource(BaseModel):
    doc_id: Optional[str] = None
    title: str = ""
    pages: str = ""
    section: str = ""
    relevance: float = 0.0
    category: str = ""
    snippet: str = ""


class ReasoningStep(BaseModel):
    step: str
    status: str = "pending"  # pending/active/done/error
    ms: int = 0


class ChatResponse(BaseModel):
    answer: str
    grounding_status: str = "INSUFFICIENT_EVIDENCE"
    review_recommended: bool = True
    review_priority: Optional[str] = None
    review_reason: Optional[str] = None
    sources: list[ChatSource] = []
    reasoning_steps: list[ReasoningStep] = []
    follow_ups: list[str] = []
    session_id: Optional[str] = None


class ChatSessionResponse(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str


class ChatMessageResponse(BaseModel):
    id: int
    session_id: str
    role: str
    content: str
    sources: list[dict] = []
    follow_ups: list[str] = []
    reasoning_steps: list[dict] = []
    created_at: str


# ── Search ────────────────────────────────────────────────────────

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    category: Optional[str] = None
    domain: Optional[str] = None
    year_from: Optional[int] = None
    year_to: Optional[int] = None
    doc_type: Optional[str] = None
    top_k: int = Field(default=20, ge=1, le=100)


class SearchResult(BaseModel):
    doc_id: Optional[str] = None
    title: str = ""
    snippet: str = ""
    relevance: float = 0.0
    category: str = ""
    domain: str = ""
    pages: str = ""
    authority_weight: float = 1.0


class SearchResponse(BaseModel):
    results: list[SearchResult]
    total: int
    query_expanded: str = ""
    facets: dict[str, dict[str, int]] = {}


# ── Dashboard ─────────────────────────────────────────────────────

class DashboardStats(BaseModel):
    total_documents: int = 0
    indexed: int = 0
    processing: int = 0
    failed: int = 0
    avg_risk_score: float = 0.0
    total_pages: int = 0
    total_clauses: int = 0
    categories: dict[str, int] = {}
    domains: dict[str, int] = {}


class RiskHeatmapEntry(BaseModel):
    domain: str
    doc_count: int = 0
    avg_risk: float = 0.0
    max_risk: int = 0
    coverage: str = "none"  # none/low/medium/good


class IndexInfo(BaseModel):
    chunk_count: int = 0
    document_count: int = 0
    faiss_size_mb: float = 0.0
    sqlite_size_mb: float = 0.0
    embed_model: str = ""


class TrendPoint(BaseModel):
    date: str
    count: int
    category: str = ""


# ── Classifier ────────────────────────────────────────────────────

class CategoryInfo(BaseModel):
    name: str
    doc_count: int = 0
    domains: list[str] = []


class ClassifyResponse(BaseModel):
    doc_id: str
    category: str
    domain: str
    confidence: float
    authority_level: str
    authority_weight: float


# ── Proactive Intelligence ────────────────────────────────────────

class ComplianceGap(BaseModel):
    domain: str
    gap_description: str
    severity: str = "medium"
    detected_at: str = ""


class StalenessAlert(BaseModel):
    doc_id: str
    filename: str
    issue: str
    referenced_act: str = ""
    severity: str = "medium"


class ContradictionAlert(BaseModel):
    doc_a_id: str
    doc_a_name: str
    doc_b_id: str
    doc_b_name: str
    description: str
    clause_a: str = ""
    clause_b: str = ""
    confidence: float = 0.5


# ── Fix forward references ───────────────────────────────────────
# DocumentDetail references EntityItem, ClauseItem, etc. which are
# defined after it.  Pydantic v2 resolves these automatically, but
# we call model_rebuild() explicitly for safety.

DocumentDetail.model_rebuild()
