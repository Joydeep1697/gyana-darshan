import logging
import asyncio
import os
import uuid
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, UploadFile, File, BackgroundTasks, HTTPException, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import JSONResponse
from app.database import get_db, Database
from app.models import DocumentResponse, SearchResponse, SearchRequest
from app.config import RAW_DIR, get_llm_client_kwargs
from api.auth.dependencies import get_current_user
from api.auth.service import decode_jwt_token

logger = logging.getLogger("nyaya-darshan-app")
router = APIRouter()
MAX_UPLOAD_BYTES = int(os.getenv("NYAYA_MAX_UPLOAD_BYTES", str(25 * 1024 * 1024)))
UPLOAD_CHUNK_BYTES = 1024 * 1024


def _public_document(document: dict) -> dict:
    return {key: value for key, value in document.items() if key not in {"raw_path", "category_path", "owner_id"}}


def _owned_document(db: Database, doc_id: str, owner_id: str) -> dict:
    document = db.get_document(doc_id)
    if not document or document.get("owner_id") != owner_id:
        raise HTTPException(404, "Document not found")
    return document

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
            
            # Save to DB - assuming appropriate db methods exist
            # db.save_entities(doc_id, entities=...)
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
async def upload_document(background_tasks: BackgroundTasks, file: UploadFile = File(...), db: Database = Depends(get_db), user: dict = Depends(get_current_user)):
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
        
    doc_id = db.create_document(original_filename, total_size, str(file_path), owner_id=user["id"])
    background_tasks.add_task(process_document, doc_id, str(file_path))
    return {"doc_id": doc_id, "status": "processing"}

@router.get("/documents")
async def list_documents(status: Optional[str] = None, category: Optional[str] = None, domain: Optional[str] = None, limit: int = Query(10, ge=1, le=100), offset: int = Query(0, ge=0), db: Database = Depends(get_db), user: dict = Depends(get_current_user)):
    """List documents with optional filters and pagination."""
    docs = db.list_documents(status=status, category=category, domain=domain, limit=limit, offset=offset, owner_id=user["id"])
    return {"documents": [_public_document(doc) for doc in docs]}

@router.get("/documents/{doc_id}")
async def get_document(doc_id: str, db: Database = Depends(get_db), user: dict = Depends(get_current_user)):
    """Get full details of a specific document including entities, clauses, deadlines, and links."""
    return _public_document(_owned_document(db, doc_id, user["id"]))

@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str, db: Database = Depends(get_db), user: dict = Depends(get_current_user)):
    """Delete a document from DB and filesystem."""
    doc = _owned_document(db, doc_id, user["id"])
    if doc.get("raw_path"):
        raw_path = Path(doc["raw_path"]).resolve()
        if not raw_path.is_relative_to(RAW_DIR.resolve()):
            logger.error("Refusing to delete document outside the upload directory: %s", doc_id)
            raise HTTPException(500, "Document storage configuration is invalid")
        raw_path.unlink(missing_ok=True)
    db.delete_document(doc_id)
    return {"status": "success"}

@router.post("/search", response_model=SearchResponse)
async def search(req: SearchRequest, db: Database = Depends(get_db), user: dict = Depends(get_current_user)):
    """Intelligent search using local_search."""
    try:
        from gyana_darshan_rag_nvidia import local_search
        from app.config import INDEX_DIR
        results = await asyncio.to_thread(local_search, req.query, INDEX_DIR)
        return SearchResponse(results=results)
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(500, "Search failed")

@router.get("/stats")
async def get_stats(db: Database = Depends(get_db), user: dict = Depends(get_current_user)):
    """Return vault statistics from DB."""
    return db.get_document_stats(owner_id=user["id"])

@router.websocket("/ws/processing")
async def ws_processing(websocket: WebSocket, doc_id: str = Query(...), token: str = Query("")):
    """WebSocket endpoint to stream background processing progress."""
    payload = decode_jwt_token(token) if token else None
    document = get_db().get_document(doc_id) if payload and payload.get("sub") else None
    if not document or document.get("owner_id") != payload["sub"]:
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
