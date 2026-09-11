import logging
import asyncio
import os
import re
import uuid
import json
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, UploadFile, File, BackgroundTasks, HTTPException, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import JSONResponse
from app.database import get_db, Database
from app.models import (
    DocumentResponse, SearchResponse, SearchRequest,
    DocumentQuestionRequest, DocumentQuestionResponse, ContractObligationAcceptRequest,
    ContractObligationAcceptResponse, ContractReviewResponse, PrecedentSearchResponse,
)
from app.config import RAW_DIR
from app.intelligence.ai_provider import AIProviderError
from app.intelligence.summarizer import generate_summary
from app.intelligence.document_grounding import (
    answer_from_documents, extract_pdf_pages, select_relevant_pages,
)
from app.intelligence.contract_review import review_contract
from api.auth.dependencies import get_workspace_context, require_workspace_writer
from api.auth.service import decode_jwt_token
from database.repository import AuditRepository, OrganizationRepository
from app.ingestion.base import IngestionLogger
from retrieval.indexer import index_tenant_files

logger = logging.getLogger("nyaya-darshan-app")
router = APIRouter()
MAX_UPLOAD_BYTES = int(os.getenv("NYAYA_MAX_UPLOAD_BYTES", str(25 * 1024 * 1024)))
UPLOAD_CHUNK_BYTES = 1024 * 1024
INGESTION_LOGGER = IngestionLogger(Path("app") / "ingestion" / "ingestion_log.jsonl")


def _public_document(document: dict) -> dict:
    return {key: value for key, value in document.items() if key not in {"raw_path", "category_path", "owner_id", "organization_id"}}


def _workspace_document(db: Database, doc_id: str, organization_id: str) -> dict:
    document = db.get_document(doc_id)
    if not document or document.get("organization_id") != organization_id:
        raise HTTPException(404, "Document not found")
    return document


def _compact_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _safe_storage_name(value: str, fallback: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", (value or "").strip()).strip("._")
    return (cleaned[:120] or fallback).lower()


def _human_task_evidence(task_id: str) -> dict:
    log_path = Path("app") / "ingestion" / "ingestion_log.jsonl"
    if not log_path.exists():
        return {}
    for line in reversed(log_path.read_text(encoding="utf-8", errors="ignore").splitlines()):
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if (item.get("file") or item.get("file_path")) == task_id and item.get("status") == "HUMAN_TASK_CREATED":
            return {
                "source_url": item.get("source_url") or "",
                "evidence_html_path": item.get("evidence_html") or "",
                "evidence_screenshot_path": item.get("evidence_screenshot") or "",
                "reason": item.get("reason") or "",
            }
    return {}

# WebSocket connections tracking
_ws_connections: dict[str, list[WebSocket]] = {}

async def broadcast_progress(doc_id: str, message: dict):
    if doc_id in _ws_connections:
        dead_connections = []
        for ws in _ws_connections[doc_id]:
            try:
                await ws.send_json(message)
            except Exception:
                dead_connections.append(ws)
        for dead_ws in dead_connections:
            _ws_connections[doc_id].remove(dead_ws)

def process_document(doc_id: str, file_path: str):
    db = get_db()
    try:
        # Step 1: Save file -> update status
        asyncio.run(broadcast_progress(doc_id, {"status": "extracting", "progress": 10}))
        db.update_document(doc_id, status="extracting")
        
        # Imports from backend
        try:
            from gyana_darshan_classifier import (
                extract_pdf, classify_rules, detect_domain, authority_for,
                extract_sections, extract_rules, extract_articles, extract_court,
                extract_judges, extract_parties, extract_citations, extract_case_number,
                extract_dates, extract_year, title_from_text
            )
            from app.config import OCR_ENABLED, OCR_LANGUAGE
        except ImportError as e:
            logger.error(f"Failed to import backend modules: {e}")
            db.update_document(doc_id, status="failed")
            asyncio.run(broadcast_progress(doc_id, {"status": "failed", "error": "Backend modules unavailable"}))
            return

        # Step 2: extract_pdf
        try:
            extracted = extract_pdf(file_path, OCR_ENABLED, OCR_LANGUAGE)
            pages = extracted.page_count
            text = extracted.text
        except Exception as e:
            logger.error(f"Failed to extract PDF: {e}")
            db.update_document(doc_id, status="failed")
            asyncio.run(broadcast_progress(doc_id, {"status": "failed", "error": "PDF extraction failed"}))
            return
            
        asyncio.run(broadcast_progress(doc_id, {"status": "classifying", "progress": 40}))
        
        # Step 3: Classify
        filename = Path(file_path).name
        try:
            title = title_from_text(text, filename)
            category, confidence, _, _ = classify_rules(filename, text, None, 0.5)
            domain = detect_domain(text, title)
            authority_level, _ = authority_for(category)
        except Exception as e:
            logger.error(f"Classification failed: {e}")
            category, domain, authority_level = "Unknown", "Unknown", 0
            
        asyncio.run(broadcast_progress(doc_id, {"status": "extracting_entities", "progress": 60}))

        # Step 4: Extract entities
        try:
            sections = extract_sections(text)
            rules = extract_rules(text)
            articles = extract_articles(text)
            court = extract_court(text)
            judges = extract_judges(text)
            parties = extract_parties(text)
            citations = extract_citations(text)
            case_num = extract_case_number(text)
            dates = extract_dates(text)
            year = extract_year(text, filename)
            neutral_citation, reported_citations = citations
            organization_id = db.get_document(doc_id).get("organization_id")
            if organization_id and (court or case_num or neutral_citation or reported_citations):
                excerpt = re.sub(r"\s+", " ", text).strip()[:2200]
                db.upsert_case_law_record(
                    organization_id,
                    doc_id,
                    {
                        "title": title,
                        "citation": neutral_citation or (reported_citations[0] if reported_citations else ""),
                        "court": court,
                        "judges": judges,
                        "petitioner": parties.get("petitioner_or_appellant"),
                        "respondent": parties.get("respondent"),
                        "case_number": case_num,
                        "decision_date": dates,
                        "year": year,
                        "sections": sections,
                        "source_excerpt": excerpt,
                        "source_page": 1,
                    },
                )
        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")

        asyncio.run(broadcast_progress(doc_id, {"status": "analyzing_clauses", "progress": 80}))

        # Step 5 & 6: Clauses and Knowledge Graph
        try:
            from app.intelligence.clause_detector import detect_clauses
            clauses = detect_clauses(text, category)
            if clauses:
                db.add_clauses(doc_id, clauses)
                db.update_document(doc_id, clauses_count=len(clauses))
        except ImportError:
            pass
        except Exception:
            logger.exception("Clause analysis failed for document %s", doc_id)

        # Step 7: Done
        db.update_document(doc_id, status="indexed", category=category, domain=domain, pages=pages)
        # In a real system: db.set_process_time(doc_id, ...)
        asyncio.run(broadcast_progress(doc_id, {"status": "indexed", "progress": 100}))

    except Exception as e:
        logger.exception("Unexpected error in process_document")
        db.update_document(doc_id, status="failed")
        asyncio.run(broadcast_progress(doc_id, {"status": "failed", "error": "Document processing failed"}))

@router.post("/upload")
async def upload_document(background_tasks: BackgroundTasks, file: UploadFile = File(...), db: Database = Depends(get_db), workspace: dict = Depends(require_workspace_writer)):
    """Upload a PDF and start background processing."""
    original_filename = Path(file.filename or "").name
    if not original_filename or len(original_filename) > 200 or Path(original_filename).suffix.lower() != ".pdf":
        raise HTTPException(400, "Only PDF files are supported")
    
    # Ensure RAW_DIR exists
    os.makedirs(RAW_DIR, exist_ok=True)
    file_path = RAW_DIR / f"{uuid.uuid4().hex}_{original_filename}"
    total_size = 0
    try:
        with open(file_path, "xb") as destination:
            while chunk := await file.read(UPLOAD_CHUNK_BYTES):
                total_size += len(chunk)
                if total_size > MAX_UPLOAD_BYTES:
                    raise HTTPException(413, "The uploaded PDF exceeds the permitted size")
                if total_size == len(chunk) and not chunk.startswith(b"%PDF-"):
                    raise HTTPException(400, "The uploaded file is not a valid PDF")
                destination.write(chunk)
        if total_size < 5:
            raise HTTPException(400, "The uploaded file is not a valid PDF")
    except Exception:
        file_path.unlink(missing_ok=True)
        raise
    finally:
        await file.close()
        
    user = workspace["user"]
    organization_id = workspace["organization"]["id"]
    doc_id = db.create_document(original_filename, total_size, str(file_path), owner_id=user["id"], organization_id=organization_id)
    AuditRepository.log_audit(
        "VAULT_DOCUMENT_UPLOADED", user_id=user["id"], organization_id=organization_id,
        metadata={"document_id": doc_id, "filename": original_filename, "size": total_size},
    )
    background_tasks.add_task(process_document, doc_id, str(file_path))
    return {"doc_id": doc_id, "status": "processing"}

@router.get("/documents")
async def list_documents(status: Optional[str] = None, category: Optional[str] = None, domain: Optional[str] = None, limit: int = Query(10, ge=1, le=100), offset: int = Query(0, ge=0), db: Database = Depends(get_db), workspace: dict = Depends(get_workspace_context)):
    """List documents with optional filters and pagination."""
    docs = db.list_documents(status=status, category=category, domain=domain, limit=limit, offset=offset, organization_id=workspace["organization"]["id"])
    return {"documents": [_public_document(doc) for doc in docs]}


@router.get("/precedents", response_model=PrecedentSearchResponse)
async def search_precedents(
    q: str = Query(..., min_length=2, max_length=300),
    court: Optional[str] = Query(default=None, max_length=120),
    year_from: Optional[int] = Query(default=None, ge=1800, le=2200),
    year_to: Optional[int] = Query(default=None, ge=1800, le=2200),
    limit: int = Query(default=20, ge=1, le=100),
    db: Database = Depends(get_db),
    workspace: dict = Depends(get_workspace_context),
):
    """Search organization-scoped case-law metadata and source excerpts."""
    if year_from is not None and year_to is not None and year_from > year_to:
        raise HTTPException(422, "year_from must be less than or equal to year_to")
    results = db.search_case_law_records(
        workspace["organization"]["id"], q.strip(), court=court, year_from=year_from, year_to=year_to, limit=limit,
    )
    return PrecedentSearchResponse(
        results=results,
        total=len(results),
        query=q.strip(),
        filters={"court": court, "year_from": year_from, "year_to": year_to},
    )


@router.post("/ingest/ecourts")
async def ingest_ecourts_judgments(
    q: str = Query(default="BNS 103", min_length=2, max_length=300),
    limit: int = Query(default=10, ge=1, le=10),
    state: str = Query(default="", max_length=120),
    court: str = Query(default="", max_length=200),
    db: Database = Depends(get_db),
    workspace: dict = Depends(require_workspace_writer),
):
    """Start a tenant-scoped eCourts ingestion attempt without bypassing CAPTCHA."""
    from app.ingestion.ecourts_crawler import ingest_ecourts
    from app.ingestion.ops_integration import create_human_review_task

    organization_id = workspace["organization"]["id"]
    result = await ingest_ecourts(
        query=q.strip(),
        tenant_id=organization_id,
        limit=limit,
        state=state.strip(),
        court=court.strip(),
        db=db,
        owner_id=workspace["user"]["id"],
    )
    human_review_task_id = None
    if result.status == "needs_human_action":
        human_review_task_id = create_human_review_task(
            tenant_id=organization_id,
            source="ecourts",
            url=result.source_url,
            html_path=Path("corpus_integrity") / "judgments" / "browser_check_ecourts.html",
            png_path=Path("corpus_integrity") / "judgments" / "browser_check_ecourts.png",
            reason=result.message or "CAPTCHA/manual court selection detected",
            metadata={
                "query": q.strip(),
                "limit": limit,
                "state": state.strip(),
                "court": court.strip(),
                "ingestion_status": result.status,
                "ingestion_files": result.files,
            },
            db=db,
            user_id=workspace["user"]["id"],
        )
    AuditRepository.log_audit(
        "VAULT_ECOURTS_INGESTION_REQUESTED",
        user_id=workspace["user"]["id"],
        organization_id=organization_id,
        metadata={
            "query": q.strip(),
            "limit": limit,
            "status": result.status,
            "files": result.files,
            "human_review_task_id": human_review_task_id,
        },
    )
    return {
        "status": result.status,
        "source_url": result.source_url,
        "tenant_id": result.tenant_id,
        "query": result.query,
        "files": result.files,
        "ingestion_log": result.entries,
        "message": result.message,
        "human_review_task_id": human_review_task_id,
    }


@router.post("/ingest/indiankanoon")
async def ingest_indiankanoon_judgments(
    q: str = Query(default="BNS 103", min_length=2, max_length=300),
    limit: int = Query(default=10, ge=1, le=25),
    workspace: dict = Depends(require_workspace_writer),
):
    """Ingest free public IndianKanoon judgment pages into the audited corpus."""
    from app.ingestion.indiankanoon_crawler import ingest_indiankanoon

    result = await ingest_indiankanoon(query=q.strip(), limit=limit)
    AuditRepository.log_audit(
        "VAULT_INDIANKANOON_INGESTION_REQUESTED",
        user_id=workspace["user"]["id"],
        organization_id=workspace["organization"]["id"],
        metadata={"query": q.strip(), "limit": limit, "status": result.status, "files": result.files},
    )
    return {
        "status": result.status,
        "query": result.query,
        "files": result.files,
        "ingestion_log": result.entries,
    }


@router.get("/ops/human-review-pending")
async def list_human_review_pending(
    db: Database = Depends(get_db),
    workspace: dict = Depends(get_workspace_context),
):
    """List pending ingestion human-action tasks for the active workspace."""
    organization_id = workspace["organization"]["id"]
    tasks = [
        task
        for task in db.list_tasks(organization_id, limit=200)
        if task.get("status") != "done" and (task.get("title") or "").startswith("[Human Action Required]")
    ]
    return {
        "tasks": [
            {
                "id": task["id"],
                "title": task["title"],
                "status": task["status"],
                "priority": task.get("priority") or "medium",
                "created_at": task["created_at"],
                "updated_at": task["updated_at"],
                **_human_task_evidence(task["id"]),
            }
            for task in tasks
        ],
        "total": len(tasks),
    }


@router.post("/ops/human-review/{task_id}/resolve")
async def resolve_human_review_task(
    task_id: str,
    file: UploadFile = File(...),
    case_no: str = Query(default="", max_length=120),
    db: Database = Depends(get_db),
    workspace: dict = Depends(require_workspace_writer),
):
    """Resolve a human-action ingestion task by uploading a public judgment PDF."""
    organization_id = workspace["organization"]["id"]
    task = db.get_task(task_id, organization_id)
    if not task or not (task.get("title") or "").startswith("[Human Action Required]"):
        raise HTTPException(404, "Human review task not found")
    if task.get("status") == "done":
        raise HTTPException(409, "Human review task is already done")
    original_filename = Path(file.filename or "").name
    if not original_filename or Path(original_filename).suffix.lower() != ".pdf":
        raise HTTPException(400, "Only PDF judgment uploads are supported")
    storage_root = (Path("app") / "storage" / "vault" / _safe_storage_name(organization_id, "tenant") / "ecourts").resolve()
    expected_root = (Path("app") / "storage" / "vault").resolve()
    if not storage_root.is_relative_to(expected_root):
        raise HTTPException(500, "Tenant storage path is invalid")
    storage_root.mkdir(parents=True, exist_ok=True)
    stem = _safe_storage_name(case_no, Path(original_filename).stem or "judgment")
    destination = storage_root / f"{stem}_{uuid.uuid4().hex[:10]}.pdf"
    total_size = 0
    try:
        with destination.open("xb") as handle:
            while chunk := await file.read(UPLOAD_CHUNK_BYTES):
                total_size += len(chunk)
                if total_size > MAX_UPLOAD_BYTES:
                    raise HTTPException(413, "The uploaded PDF exceeds the permitted size")
                if total_size == len(chunk) and not chunk.startswith(b"%PDF-"):
                    raise HTTPException(400, "The uploaded file is not a valid PDF")
                handle.write(chunk)
        if total_size < 5:
            raise HTTPException(400, "The uploaded file is not a valid PDF")
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    finally:
        await file.close()

    user = workspace["user"]
    doc_id = db.create_document(original_filename, total_size, str(destination), owner_id=user["id"], organization_id=organization_id)
    db.update_document(doc_id, status="indexed", category="judgment", domain="case_law")
    from app.ingestion.matter_extractor import extract_matter_data
    from verification.matter_validator import validate_matter_data
    matter_id = task.get("matter_id")
    if not matter_id:
        matter = db.create_matter(organization_id, f"Judgment review: {case_no or original_filename}", matter_type="case_law", owner_user_id=user["id"])
        matter_id = matter["id"]
        db.update_task(task_id, organization_id, matter_id=matter_id)
    extracted = extract_matter_data(destination)
    extracted.update({"matter_id": matter_id, "source_pdf": str(destination), "provenance_verified": False, "validation": validate_matter_data(extracted)})
    matter_root = (Path("app") / "storage" / "vault" / _safe_storage_name(organization_id, "tenant") / "matters" / _safe_storage_name(matter_id, "matter")).resolve()
    if not matter_root.is_relative_to(expected_root):
        raise HTTPException(500, "Matter storage path is invalid")
    matter_root.mkdir(parents=True, exist_ok=True)
    (matter_root / "extracted.json").write_text(json.dumps(extracted, indent=2, ensure_ascii=True), encoding="utf-8")
    db.link_document_to_matter(organization_id, matter_id, doc_id)
    for obligation in extracted.get("obligations", []):
        db.create_task(organization_id, f"Extracted obligation: {obligation.get('description', 'Review obligation')}", matter_id=matter_id, due_date=obligation.get("due_date"), priority="high", metadata={"source": "matter_extractor", "provenance_verified": False})
    if extracted.get("next_hearing_date"):
        db.create_task(organization_id, f"Next hearing: {extracted['next_hearing_date']}", matter_id=matter_id, due_date=extracted["next_hearing_date"], priority="high", metadata={"source": "matter_extractor", "kind": "next_hearing", "provenance_verified": False})
    updated = db.update_task(task_id, organization_id, status="done", metadata={"matter_id": matter_id, "document_id": doc_id, "extracted_json": str(matter_root / "extracted.json"), "provenance_verified": False})
    evidence = _human_task_evidence(task_id)
    AuditRepository.log_audit(
        "INGESTION_HUMAN_REVIEW_RESOLVED",
        user_id=user["id"],
        organization_id=organization_id,
        metadata={"task_id": task_id, "document_id": doc_id, "file": str(destination), "case_no": case_no},
    )
    INGESTION_LOGGER.log(
        "OPS_TASK",
        "ecourts",
        evidence.get("source_url") or "",
        "HUMAN_TASK_RESOLVED",
        file_path=str(destination),
        tenant_id=organization_id,
        task_id=task_id,
        resolved_by=user["id"],
        document_id=doc_id,
    )
    await asyncio.to_thread(index_tenant_files, organization_id)
    return {
        "task": updated,
        "document_id": doc_id,
        "file": str(destination),
        "status": "indexed",
    }


@router.post("/documents/ask", response_model=DocumentQuestionResponse)
async def ask_documents(
    request: DocumentQuestionRequest,
    db: Database = Depends(get_db),
    workspace: dict = Depends(get_workspace_context),
):
    """Answer from one to three owned PDFs with page-level source excerpts."""
    unique_ids = list(dict.fromkeys(request.document_ids))
    if len(unique_ids) != len(request.document_ids):
        raise HTTPException(400, "Choose each document only once")
    prepared = []
    for doc_id in unique_ids:
        document = _workspace_document(db, doc_id, workspace["organization"]["id"])
        raw_value = document.get("raw_path")
        if not raw_value:
            raise HTTPException(409, f"{document['filename']} is not available for questions")
        raw_path = Path(raw_value).resolve()
        if not raw_path.is_relative_to(RAW_DIR.resolve()):
            logger.error("Refusing to read a document outside the upload directory: %s", doc_id)
            raise HTTPException(500, "Document storage configuration is invalid")
        if not raw_path.is_file():
            raise HTTPException(404, f"{document['filename']} is no longer available")
        pages = await asyncio.to_thread(extract_pdf_pages, raw_path)
        if not pages:
            raise HTTPException(422, f"No readable text was found in {document['filename']}")
        prepared.append({"id": doc_id, "filename": document["filename"], "pages": pages})
    selected = select_relevant_pages(request.question, prepared)
    try:
        answer = await answer_from_documents(request.question, selected)
    except AIProviderError as exc:
        raise HTTPException(503, str(exc)) from exc
    sources = [
        {
            "document_id": page["doc_id"],
            "filename": page["filename"],
            "page": page["page"],
            "snippet": page["text"][:700],
        }
        for page in selected
    ]
    return DocumentQuestionResponse(answer=answer, sources=sources)

@router.get("/documents/{doc_id}")
async def get_document(doc_id: str, db: Database = Depends(get_db), workspace: dict = Depends(get_workspace_context)):
    """Get full details of a specific document including entities, clauses, deadlines, and links."""
    return _public_document(_workspace_document(db, doc_id, workspace["organization"]["id"]))


@router.post("/documents/{doc_id}/summary")
async def generate_document_summary(doc_id: str, db: Database = Depends(get_db), workspace: dict = Depends(require_workspace_writer)):
    """Generate and cache a grounded summary for an owned PDF."""
    document = _workspace_document(db, doc_id, workspace["organization"]["id"])
    if document.get("summary"):
        return {"summary": document["summary"], "cached": True}

    raw_value = document.get("raw_path")
    if not raw_value:
        raise HTTPException(409, "The source PDF is not available for summarisation")
    raw_path = Path(raw_value).resolve()
    if not raw_path.is_relative_to(RAW_DIR.resolve()):
        logger.error("Refusing to summarise a document outside the upload directory: %s", doc_id)
        raise HTTPException(500, "Document storage configuration is invalid")
    if not raw_path.is_file():
        raise HTTPException(404, "The source PDF is no longer available")

    try:
        from gyana_darshan_classifier import extract_pdf
        from app.config import OCR_ENABLED, OCR_LANGUAGE

        extracted = await asyncio.to_thread(extract_pdf, str(raw_path), OCR_ENABLED, OCR_LANGUAGE)
        text = (getattr(extracted, "text", "") or "").strip()
        if not text:
            raise HTTPException(422, "No readable text could be extracted from this PDF")
        metadata = {
            "filename": document.get("filename"),
            "category": document.get("category"),
            "domain": document.get("domain"),
            "pages": document.get("pages"),
        }
        summary = await generate_summary(
            text,
            document.get("category") or "Legal document",
            metadata,
        )
    except HTTPException:
        raise
    except ImportError:
        logger.exception("PDF extraction backend is unavailable")
        raise HTTPException(503, "PDF extraction is temporarily unavailable")
    except AIProviderError as exc:
        logger.warning("Vault summary unavailable because the AI provider route failed")
        raise HTTPException(503, str(exc)) from exc
    except Exception:
        logger.exception("Summary extraction failed for document %s", doc_id)
        raise HTTPException(500, "The document could not be summarised")

    if not summary:
        raise HTTPException(503, "Summary generation is temporarily unavailable")
    db.update_document(doc_id, summary=summary)
    return {"summary": summary, "cached": False}


@router.post("/documents/{doc_id}/contract-review", response_model=ContractReviewResponse)
async def review_document_contract(doc_id: str, db: Database = Depends(get_db), workspace: dict = Depends(get_workspace_context)):
    """Run a document-grounded contract review for a workspace PDF."""
    document = _workspace_document(db, doc_id, workspace["organization"]["id"])
    raw_value = document.get("raw_path")
    if not raw_value:
        raise HTTPException(409, "The source PDF is not available for contract review")
    raw_path = Path(raw_value).resolve()
    if not raw_path.is_relative_to(RAW_DIR.resolve()):
        logger.error("Refusing to review a document outside the upload directory: %s", doc_id)
        raise HTTPException(500, "Document storage configuration is invalid")
    if not raw_path.is_file():
        raise HTTPException(404, "The source PDF is no longer available")

    try:
        pages = await asyncio.to_thread(extract_pdf_pages, raw_path)
    except Exception:
        logger.exception("Contract review extraction failed for document %s", doc_id)
        raise HTTPException(500, "The contract could not be reviewed")
    text = "\n\n".join(page.get("text", "") for page in pages).strip()
    if not text:
        raise HTTPException(422, "No readable text could be extracted from this PDF")

    result = review_contract(
        text,
        filename=document.get("filename") or "",
        category=document.get("category") or "",
    )
    return ContractReviewResponse(**result)


@router.post("/documents/{doc_id}/contract-obligations", response_model=ContractObligationAcceptResponse)
async def accept_document_contract_obligation(
    doc_id: str,
    payload: ContractObligationAcceptRequest,
    db: Database = Depends(get_db),
    workspace: dict = Depends(require_workspace_writer),
):
    """Accept one source-quoted obligation suggestion into Nyaya Ops."""
    organization_id = workspace["organization"]["id"]
    user_id = workspace["user"]["id"]
    document = _workspace_document(db, doc_id, organization_id)
    suggestion = payload.suggestion
    source_clause = _compact_text(suggestion.source_clause)
    if not source_clause:
        raise HTTPException(422, "Accepted obligation must include source clause text")
    raw_value = document.get("raw_path")
    if not raw_value:
        raise HTTPException(409, "The source PDF is not available for obligation acceptance")
    raw_path = Path(raw_value).resolve()
    if not raw_path.is_relative_to(RAW_DIR.resolve()):
        logger.error("Refusing to accept obligations from a document outside the upload directory: %s", doc_id)
        raise HTTPException(500, "Document storage configuration is invalid")
    if not raw_path.is_file():
        raise HTTPException(404, "The source PDF is no longer available")
    try:
        pages = await asyncio.to_thread(extract_pdf_pages, raw_path)
    except Exception:
        logger.exception("Contract obligation source validation failed for document %s", doc_id)
        raise HTTPException(500, "The contract obligation source could not be validated")
    document_text = _compact_text(" ".join(page.get("text", "") for page in pages))
    validation_clause = source_clause[:-3].rstrip() if source_clause.endswith("...") else source_clause
    if validation_clause not in document_text:
        raise HTTPException(422, "Accepted obligation source clause was not found in the document text")
    try:
        if payload.contract_id:
            contract = db.get_contract_record(payload.contract_id, organization_id)
            if not contract:
                raise ValueError("Contract not found in workspace")
            if contract.get("document_id") and contract.get("document_id") != doc_id:
                raise ValueError("Contract is linked to a different document")
        else:
            contract = db.get_contract_record_by_document(doc_id, organization_id)
            if not contract:
                contract = db.create_contract_record(
                    organization_id,
                    document.get("filename") or "Reviewed contract",
                    document_id=doc_id,
                    matter_id=payload.matter_id,
                    contract_type="nda" if "nda" in (document.get("filename") or "").casefold() else "general",
                    status="in_review",
                    risk_level=suggestion.priority if suggestion.priority in {"high", "critical"} else "medium",
                )
        obligation = db.create_contract_obligation(
            organization_id,
            contract["id"],
            suggestion.title,
            matter_id=payload.matter_id or contract.get("matter_id"),
            owner=payload.owner,
            category=suggestion.category,
            status="open",
            priority=suggestion.priority,
            due_date=suggestion.due_date,
            source_clause=source_clause,
        )
    except ValueError as error:
        raise HTTPException(422, str(error))
    AuditRepository.log_audit(
        "VAULT_CONTRACT_OBLIGATION_ACCEPTED",
        user_id=user_id,
        organization_id=organization_id,
        metadata={"document_id": doc_id, "contract_id": contract["id"], "obligation_id": obligation["id"], "suggestion_id": suggestion.id},
    )
    return {"contract": contract, "obligation": obligation}

@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str, db: Database = Depends(get_db), workspace: dict = Depends(require_workspace_writer)):
    """Delete a document from DB and filesystem."""
    user = workspace["user"]
    organization_id = workspace["organization"]["id"]
    doc = _workspace_document(db, doc_id, organization_id)
    if doc.get("raw_path"):
        raw_path = Path(doc["raw_path"]).resolve()
        if not raw_path.is_relative_to(RAW_DIR.resolve()):
            logger.error("Refusing to delete document outside the upload directory: %s", doc_id)
            raise HTTPException(500, "Document storage configuration is invalid")
        raw_path.unlink(missing_ok=True)
    db.delete_document(doc_id)
    AuditRepository.log_audit(
        "VAULT_DOCUMENT_DELETED", user_id=user["id"], organization_id=organization_id,
        metadata={"document_id": doc_id, "filename": doc.get("filename")},
    )
    return {"status": "success"}

@router.post("/search", response_model=SearchResponse)
async def search(req: SearchRequest, db: Database = Depends(get_db), workspace: dict = Depends(get_workspace_context)):
    """Search metadata and cached summaries within the authenticated user's vault."""
    documents = db.search_documents(
        req.query,
        organization_id=workspace["organization"]["id"],
        category=req.category,
        domain=req.domain,
        limit=req.top_k,
    )
    results = [
        {
            "doc_id": document["id"],
            "title": document["filename"],
            "snippet": (document.get("summary") or "")[:360],
            "relevance": 1.0,
            "category": document.get("category") or "",
            "domain": document.get("domain") or "",
            "pages": str(document.get("pages") or ""),
            "authority_weight": document.get("authority_weight") or 1.0,
        }
        for document in documents
    ]
    return SearchResponse(results=results, total=len(results))

@router.get("/stats")
async def get_stats(db: Database = Depends(get_db), workspace: dict = Depends(get_workspace_context)):
    """Return vault statistics from DB."""
    return db.get_document_stats(organization_id=workspace["organization"]["id"])

@router.websocket("/ws/processing")
async def ws_processing(websocket: WebSocket, doc_id: str = Query(...), token: str = Query(""), organization_id: str = Query("")):
    """WebSocket endpoint to stream background processing progress."""
    payload = decode_jwt_token(token) if token else None
    user_id = payload.get("sub") if payload else None
    scope_id = organization_id or (f"personal-{user_id}" if user_id else "")
    membership = OrganizationRepository.get_for_member(scope_id, user_id) if user_id else None
    document = get_db().get_document(doc_id) if membership else None
    if not document or document.get("organization_id") != scope_id:
        await websocket.close(code=1008, reason="Authentication required")
        return
    await websocket.accept()
    if doc_id not in _ws_connections:
        _ws_connections[doc_id] = []
    _ws_connections[doc_id].append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if doc_id in _ws_connections and websocket in _ws_connections[doc_id]:
            _ws_connections[doc_id].remove(websocket)
