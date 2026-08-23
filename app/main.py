"""Nyaya Darshan — FastAPI Application Entry Point.

Serves the Nyaya Darshan web interface, mounts routers for Knowledge Vault,
AI Chat, and the Production Dual-Panel Evidence API (/api/v1/query).
"""

from __future__ import annotations

import os
import sys
import logging
import time
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator, Dict, List, Any, Optional

from fastapi import FastAPI, HTTPException, Request, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field, validator

import torch
torch.set_num_threads(1)

from app import config
from app.database import get_db
from app.intelligence.legal_generation import LegalGenerationError, generate_grounded_legal_answer

from retrieval.hybrid_retriever import AuthoritativeLegalRetriever
from verification.claim_firewall import LegalVerificationFirewall
from retrieval.deterministic_legal_indexer import DeterministicLegalIndexer
from retrieval.procedural_rules_registry import ProceduralRulesRegistry
from retrieval.statute_scope_classifier import StatuteScopeClassifier
from api.security import (
    RateLimitMiddleware, verify_api_key, sanitize_response_data,
    log_audit_event
)

logger = logging.getLogger("nyaya-darshan-app")

# Singletons
retriever = AuthoritativeLegalRetriever()
firewall = LegalVerificationFirewall()

# ── Lifespan ───────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncGenerator[None, None]:
    """Startup: validate production config, init DB, verify statutory corpus."""
    logger.info("Nyaya Darshan Legal OS starting up...")
    config.validate_production_config()
    db = get_db()
    logger.info("Statutory Corpus loaded: %d Bare Act sections", len(retriever.corpus))
    logger.info("Nyaya Darshan ready — serving on http://%s:%s", config.HOST, config.PORT)
    yield
    logger.info("Nyaya Darshan shutting down...")

# ── Create FastAPI app ────────────────────────────────────────────

app = FastAPI(
    title="Nyaya Darshan",
    description="Indian Legal Intelligence Operating System — Powered by Authoritative Gazette RAG & Legal Verification Firewall",
    version="2.0.0",
    lifespan=lifespan,
)

# ── Rate Limiting & CORS ──────────────────────────────────────────

app.add_middleware(RateLimitMiddleware)

_raw_origins = os.environ.get("ALLOWED_ORIGINS", "")
_is_wildcard = not _raw_origins or _raw_origins.strip() == "*"

if _is_wildcard:
    if config.IS_PRODUCTION:
        raise RuntimeError(
            "FAIL-CLOSED: Wildcard CORS ('*') or missing ALLOWED_ORIGINS is forbidden in production mode. "
            "Set explicit origins e.g. ALLOWED_ORIGINS=https://nyayadarshana.com"
        )
    ALLOWED_ORIGINS = ["*"]
    _allow_credentials = False  # Never allow credentials on wildcard origins
    logger.warning(
        "SECURITY: ALLOWED_ORIGINS is not configured — CORS wildcard (*) is active (credentials disabled). "
        "Set ALLOWED_ORIGINS=https://yourdomain.com in production."
    )
else:
    ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]
    _allow_credentials = True

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=_allow_credentials,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# ── Global Exception Handlers ─────────────────────────────────────

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    clean_errors = []
    for err in exc.errors():
        err_dict = dict(err)
        if "ctx" in err_dict and isinstance(err_dict["ctx"], dict):
            err_dict["ctx"] = {k: str(v) for k, v in err_dict["ctx"].items()}
        clean_errors.append(err_dict)

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "type": "https://nyayadarshana.com/errors/validation-error",
            "title": "Unprocessable Entity",
            "status": 422,
            "detail": "Request query validation failed. Ensure query is a non-empty string under 4,096 characters.",
            "errors": sanitize_response_data(clean_errors)
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "type": f"https://nyayadarshana.com/errors/{exc.status_code}",
            "title": "HTTP Exception",
            "status": exc.status_code,
            "detail": sanitize_response_data(exc.detail)
        }
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "type": "https://nyayadarshana.com/errors/internal-server-error",
            "title": "Internal Server Error",
            "status": 500,
            "detail": "An unexpected error occurred in the legal reasoning pipeline. No internal details are leaked."
        }
    )

# ── Mount Routers ─────────────────────────────────────────────────

from app.routers import vault, chat, classifier, dashboard, knowledge_graph, proactive  # noqa: E402
from api.auth.router import router as auth_router
from api.conversations.router import router as conversations_router
from database.connection import init_db

# Initialize Relational Database Schema
init_db()

app.include_router(auth_router)
app.include_router(conversations_router)
app.include_router(vault.router, prefix="/api/vault", tags=["Knowledge Vault"])
app.include_router(chat.router, prefix="/api/chat", tags=["AI Chat"])
app.include_router(classifier.router, prefix="/api/classifier", tags=["Classifier"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(knowledge_graph.router, prefix="/api/graph", tags=["Knowledge Graph"])
app.include_router(proactive.router, prefix="/api/proactive", tags=["Proactive Intelligence"])

# ── Production Dual-Panel Evidence API ────────────────────────────

class LegalQueryRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=4096, description="The statutory or procedural query.")
    session_id: Optional[str] = Field(default=None, max_length=128, description="Client session identifier.")
    top_k: Optional[int] = Field(default=4, ge=1, le=10, description="Number of statutory sections to retrieve.")

    @validator("query")
    def validate_query_content(cls, v):
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Query cannot be empty or whitespace only.")
        return cleaned

class EvidenceSection(BaseModel):
    statute: str
    section: str
    heading: str
    chapter: str
    text_snippet: str

class VerificationDetails(BaseModel):
    passed_clean: bool
    interventions_count: int
    claims_verified: List[Dict[str, Any]]
    provenance_verified: bool

class LegalQueryResponse(BaseModel):
    query: str
    answer: str
    grounding_status: str
    statute_scope: Optional[Dict[str, Any]]
    evidence_pack: Dict[str, Any]
    retrieved_sections: List[EvidenceSection]
    verification_firewall: VerificationDetails
    latency_ms: float

@app.post("/api/v1/query", response_model=LegalQueryResponse, tags=["Production Grounding API"])
async def process_legal_query(
    req: LegalQueryRequest,
    request: Request,
    auth_verified: bool = Depends(verify_api_key)
):
    t0 = time.perf_counter()
    query = req.query
    client_ip = request.client.host if request.client else "127.0.0.1"

    try:
        async def _execute_pipeline():
            evidence_pack = retriever.retrieve_evidence_pack(query, top_k=req.top_k)
            evidence_ctx = retriever.format_evidence_context(evidence_pack)

            generated_answer = await generate_grounded_legal_answer(query, evidence_ctx)

            passed_fw, enforced_answer, claims = firewall.verify_and_enforce(generated_answer, evidence_pack)

            formatted_sections = []
            for s in evidence_pack.get("retrieved_sections", []):
                formatted_sections.append(EvidenceSection(
                    statute=s.get("statute", ""),
                    section=str(s.get("section", "")),
                    heading=s.get("heading", ""),
                    chapter=s.get("chapter", ""),
                    text_snippet=s.get("text", "")[:350]
                ))

            return passed_fw, enforced_answer, claims, evidence_pack, formatted_sections

        passed_fw, enforced_answer, claims, evidence_pack, formatted_sections = await asyncio.wait_for(
            _execute_pipeline(), timeout=15.0
        )

    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="The legal reasoning pipeline timed out. Please retry with a more specific query."
        )
    except LegalGenerationError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    latency = round((time.perf_counter() - t0) * 1000, 2)
    grounding_status = "GROUNDED_AND_VERIFIED" if passed_fw else "AUTO_CORRECTED_BY_FIREWALL"

    log_audit_event(
        endpoint="/api/v1/query",
        client_ip=client_ip,
        query=query,
        grounding_status=grounding_status,
        interventions_count=len(claims),
        evidence_count=len(formatted_sections),
        latency_ms=latency,
        session_id=req.session_id
    )

    response_payload = LegalQueryResponse(
        query=query,
        answer=enforced_answer,
        grounding_status=grounding_status,
        statute_scope=evidence_pack.get("statute_scope"),
        evidence_pack={
            "authoritative_facts": evidence_pack.get("authoritative_facts", []),
            "source_authority": "Official Gazette of India (Act 45, 46, 47 of 2023)"
        },
        retrieved_sections=formatted_sections,
        verification_firewall=VerificationDetails(
            passed_clean=passed_fw,
            interventions_count=len(claims),
            claims_verified=claims,
            provenance_verified=True
        ),
        latency_ms=latency
    )

    return sanitize_response_data(response_payload.dict())

# ── Serve Static Frontend ────────────────────────────────────────

STATIC_DIR = config.STATIC_DIR
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/", include_in_schema=False)
async def serve_frontend():
    """Serve the Nyaya Darshan frontend without browser caching."""
    index = STATIC_DIR / "index.html"
    if index.exists():
        return FileResponse(
            str(index),
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )
    return {"message": "Nyaya Darshan API is running. Frontend not found at app/static/index.html"}

@app.get("/health", tags=["System Health"])
async def health_check():
    """Quick health check endpoint."""
    return {
        "status": "HEALTHY",
        "engine": "Nyaya Darshan Legal OS",
        "corpus_loaded_sections": len(retriever.corpus)
    }
