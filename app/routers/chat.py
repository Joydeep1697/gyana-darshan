# chat.py — Nyaya Legal OS Chat Router (Integrated with Gazette Grounding Engine & Firewall)

import logging
import asyncio
import json
import time
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Request
from app.database import get_db, Database
from app.models import ChatResponse, ChatRequest
from app.intelligence.legal_generation import LegalGenerationError, generate_grounded_legal_answer
from app.intelligence.grounding_verdict import assess_grounding
from app.intelligence.human_review import recommend_human_review
from api.auth.dependencies import get_current_user

from retrieval.hybrid_retriever import AuthoritativeLegalRetriever
from verification.claim_firewall import LegalVerificationFirewall
from retrieval.deterministic_legal_indexer import DeterministicLegalIndexer
from retrieval.procedural_rules_registry import ProceduralRulesRegistry
from retrieval.statute_scope_classifier import StatuteScopeClassifier
from retrieval.legal_reasoning import build_reasoning_plan
from app import config
from app.source_presenter import format_cited_evidence

logger = logging.getLogger("nyaya-darshan-app")
router = APIRouter()

# Singletons
retriever = AuthoritativeLegalRetriever()
firewall = LegalVerificationFirewall()

@router.post("/ask", response_model=ChatResponse)
async def ask(req: ChatRequest, db: Database = Depends(get_db), user: dict = Depends(get_current_user)):
    """Authoritative legal Q&A with Gazette RAG and field-level verification firewall."""
    t0 = time.perf_counter()
    query = req.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    # 1. Retrieve Authoritative Evidence Pack
    reasoning_plan = build_reasoning_plan(query)
    requested_sources = min(req.top_k, config.LEGAL_SCENARIO_MAX_SOURCES)
    minimum_sources = len(reasoning_plan.required_citations) if reasoning_plan.is_complex else 4
    top_k = max(4, requested_sources, min(minimum_sources, config.LEGAL_SCENARIO_MAX_SOURCES))
    evidence_pack = retriever.retrieve_evidence_pack(query, top_k=top_k)
    evidence_ctx = retriever.format_evidence_context(evidence_pack)

    # 2. Generate an evidence-grounded answer through the configured cloud model.
    try:
        generated_answer = await generate_grounded_legal_answer(query, evidence_ctx)
    except LegalGenerationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    # 3. Field-Level Verification & Firewall Enforcement
    passed_fw, enforced_answer, claims = firewall.verify_and_enforce(generated_answer, evidence_pack)
    verdict = assess_grounding(
        query, enforced_answer, evidence_ctx, passed_fw,
        evidence_records=evidence_pack.get("retrieved_sections", []),
    )
    review = recommend_human_review(verdict)

    # Show unique authorities cited in the enforced answer, not every retrieved
    # candidate.  This keeps the source count meaningful and avoids duplicate OCR titles.
    sources = []
    for source in format_cited_evidence(enforced_answer, evidence_pack):
        sources.append({
            "title": f"{source['statute']} § {source['section']} — {source['heading']}",
            "snippet": source["text_snippet"],
            "category": source["statute"],
        })

    elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)

    reasoning_steps = [
        {"step": "Response prepared; legal review required", "status": "done", "ms": int(elapsed_ms)}
    ]

    follow_ups = [
        f"What are the related procedural guidelines for {query}?",
        f"Which transitional provisions govern pending cases for this section?",
        f"Are there any landmark Supreme Court rulings interpreting this provision?"
    ]

    return ChatResponse(
        answer=enforced_answer,
        grounding_status=verdict.status,
        review_recommended=review.required,
        review_priority=review.priority,
        review_reason=review.reason,
        sources=sources,
        reasoning_steps=reasoning_steps,
        follow_ups=follow_ups
    )
