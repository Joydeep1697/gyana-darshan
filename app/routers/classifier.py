import logging
import asyncio
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from app.database import get_db, Database
from app.config import CATEGORY_DIR
from api.auth.dependencies import get_current_user

logger = logging.getLogger("nyaya-darshan-app")
router = APIRouter()

@router.post("/classify/{doc_id}")
async def reclassify_document(doc_id: str, db: Database = Depends(get_db), user: dict = Depends(get_current_user)):
    """Re-classify a document by running extract_pdf + classify_rules + detect_domain."""
    doc = db.get_document(doc_id)
    if not doc or doc.get("owner_id") != user["id"]:
        raise HTTPException(404, "Document not found")
        
    def do_reclassify():
        from gyana_darshan_classifier import extract_pdf, classify_rules, detect_domain
        from app.config import OCR_ENABLED, OCR_LANGUAGE
        extracted = extract_pdf(doc['raw_path'], OCR_ENABLED, OCR_LANGUAGE)
        filename = Path(doc['raw_path']).name
        category, confidence, _, _ = classify_rules(filename, extracted.text, None, 0.5)
        domain = detect_domain(extracted.text, filename)
        return category, domain

    try:
        category, domain = await asyncio.to_thread(do_reclassify)
        db.update_document_classification(doc_id, category, domain)
        return {"category": category, "domain": domain}
    except Exception as e:
        logger.error(f"Reclassification error: {e}")
        raise HTTPException(500, "Reclassification failed")

@router.get("/categories")
async def list_categories():
    """List all categories by scanning CATEGORY_DIR."""
    categories = []
    try:
        cat_dir = Path(CATEGORY_DIR)
        if cat_dir.exists():
            for subdir in cat_dir.iterdir():
                if subdir.is_dir():
                    count = len(list(subdir.glob("*")))
                    categories.append({"name": subdir.name, "count": count})
    except Exception as e:
        logger.error(f"Categories list error: {e}")
    return {"categories": categories}

@router.get("/domains")
async def list_domains(db: Database = Depends(get_db), user: dict = Depends(get_current_user)):
    """List all domains with document counts."""
    return {"domains": db.get_domain_counts(owner_id=user["id"])}

@router.get("/stats")
async def get_classification_stats(db: Database = Depends(get_db), user: dict = Depends(get_current_user)):
    """Get classification statistics from classification reports."""
    stats = db.get_document_stats(owner_id=user["id"])
    return {"accuracy": None, "total_classified": stats["indexed"], "total_documents": stats["total_documents"], "categories": stats["categories"]}
