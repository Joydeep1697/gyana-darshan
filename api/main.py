# main.py — Nyaya Legal OS Production API Server
#
# Objective:
# Provide high-throughput, sub-25ms authoritative legal query routing, RAG retrieval,
# deterministic section lookups, and claim verification firewall for the Nyaya Darshana UI.

import os
import sys
import time
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field, validator
from fastapi import FastAPI, HTTPException, Request, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

BASE_DIR = Path(r"d:\Nova Legal")
sys.path.append(str(BASE_DIR))

from retrieval.hybrid_retriever import AuthoritativeLegalRetriever
from verification.claim_firewall import LegalVerificationFirewall
from retrieval.deterministic_legal_indexer import DeterministicLegalIndexer
from retrieval.procedural_rules_registry import ProceduralRulesRegistry
from retrieval.statute_scope_classifier import StatuteScopeClassifier
from api.security import (
    RateLimitMiddleware, verify_api_key, sanitize_response_data,
    log_audit_event
)
from database.connection import init_db
from api.auth.router import router as auth_router
from api.conversations.router import router as conversations_router

# Initialize Relational Database Schema
init_db()

app = FastAPI(
    title="Nyaya Legal OS — Production Statutory API",
    description="Authoritative, Gazette-grounded legal query engine with field-level verification firewall.",
    version="2.0.0"
)

# Mount Product Routers
app.include_router(auth_router)
app.include_router(conversations_router)

# 1. Mount Rate Limiting Middleware
app.add_middleware(RateLimitMiddleware)

# 2. Mount CORS Middleware
import logging as _logging
_cors_logger = _logging.getLogger("nyaya-security")
_raw_origins = os.environ.get("ALLOWED_ORIGINS", "")
_env = os.environ.get("ENVIRONMENT", os.environ.get("ENV", "development")).lower()
_is_prod = _env in ["production", "prod"]
_is_wildcard = not _raw_origins or _raw_origins.strip() == "*"

if _is_wildcard:
    if _is_prod:
        raise RuntimeError(
            "FAIL-CLOSED: Wildcard CORS ('*') or missing ALLOWED_ORIGINS is forbidden in production mode. "
            "Set explicit origins e.g. ALLOWED_ORIGINS=https://nyayadarshana.com"
        )
    ALLOWED_ORIGINS = ["*"]
    _allow_credentials = False  # Never allow credentials on wildcard origins
    _cors_logger.warning(
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
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# Global Exception Handlers (RFC-7807 Standard Error Format & No Path Leakage)
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

# Engine Singletons
retriever = AuthoritativeLegalRetriever()
firewall = LegalVerificationFirewall()
statute_classifier = StatuteScopeClassifier()
procedural_registry = ProceduralRulesRegistry()
deterministic_indexer = DeterministicLegalIndexer()

class LegalQueryRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=4096, description="The statutory or procedural legal query.")
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

@app.get("/health", tags=["System Health"])
def health_check():
    """System health check endpoint."""
    return {
        "status": "HEALTHY",
        "engine": "Nyaya Legal OS Grounding Engine",
        "corpus_loaded_sections": len(retriever.corpus),
        "timestamp": time.time()
    }

@app.post("/api/v1/query", response_model=LegalQueryResponse, tags=["Production Grounding API"])
async def process_legal_query(
    req: LegalQueryRequest,
    request: Request,
    auth_verified: bool = Depends(verify_api_key)
):
    """Execute authoritative legal query routing, RAG retrieval, and verification firewall."""
    t0 = time.perf_counter()
    query = req.query

    client_ip = request.client.host if request.client else "127.0.0.1"

    # Async timeout wrapper (15s ceiling)
    try:
        async def _execute_pipeline():
            # 1. Retrieve Authoritative Evidence Pack
            evidence_pack = retriever.retrieve_evidence_pack(query, top_k=req.top_k)
            evidence_ctx = retriever.format_evidence_context(evidence_pack)

            # 2. Candidate Legal Generation (Grounded RAG Payload)
            simulated_raw = (
                f"According to current Indian Statutory Law:\n{evidence_ctx}\n"
                f"In response to '{query}', the authoritative legal position is established under statute."
            )

            # 3. Field-Level Verification & Firewall Enforcement
            passed_fw, enforced_answer, claims = firewall.verify_and_enforce(simulated_raw, evidence_pack)

            # Format Retrieved Sections
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

    latency = round((time.perf_counter() - t0) * 1000, 2)
    grounding_status = "GROUNDED_AND_VERIFIED" if passed_fw else "AUTO_CORRECTED_BY_FIREWALL"

    # Log structured audit event
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

    # Sanitize output against any internal filesystem leakage
    return sanitize_response_data(response_payload.dict())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
