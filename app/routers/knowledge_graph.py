import logging
from fastapi import APIRouter, Depends, HTTPException
from app.database import get_db, Database
from api.auth.dependencies import get_current_user

logger = logging.getLogger("nyaya-darshan-app")
router = APIRouter()

@router.get("/document/{doc_id}/links")
async def get_document_links(doc_id: str, db: Database = Depends(get_db), user: dict = Depends(get_current_user)):
    """Get all citation links for a document from DB."""
    document = db.get_document(doc_id)
    if not document or document.get("owner_id") != user["id"]:
        raise HTTPException(404, "Document not found")
    return {"links": [link for link in db.get_document_links(doc_id) if not link.get("target_doc_id") or (db.get_document(link["target_doc_id"]) or {}).get("owner_id") == user["id"]]}

@router.get("/document/{doc_id}/related")
async def get_related_documents(doc_id: str, db: Database = Depends(get_db), user: dict = Depends(get_current_user)):
    """Suggest related documents."""
    document = db.get_document(doc_id)
    if not document or document.get("owner_id") != user["id"]:
        raise HTTPException(404, "Document not found")
    return {"related": [item for item in db.get_related_documents(doc_id) if (db.get_document(item["id"]) or {}).get("owner_id") == user["id"]]}

@router.get("/section/{ref}")
async def get_section_references(ref: str, db: Database = Depends(get_db), user: dict = Depends(get_current_user)):
    """Search section_index table for all docs referencing a section."""
    return {"documents": db.get_docs_by_section(ref, owner_id=user["id"])}

@router.get("/section/{ref}/impact")
async def get_section_impact(ref: str, db: Database = Depends(get_db), user: dict = Depends(get_current_user)):
    """List documents affected if a section changes."""
    return {"impacted": db.get_section_impact(ref, owner_id=user["id"])}

@router.get("/contradictions")
async def get_contradictions(db: Database = Depends(get_db), user: dict = Depends(get_current_user)):
    """Get detected contradictions."""
    owned_domains = {item["domain"] for item in db.get_domain_counts(owner_id=user["id"])}
    return {"contradictions": [gap for gap in db.get_compliance_gaps(gap_type="contradiction") if gap.get("domain") in owned_domains]}

@router.get("/network")
async def get_network(db: Database = Depends(get_db), user: dict = Depends(get_current_user)):
    """Full graph data for visualization."""
    return db.get_full_graph(owner_id=user["id"])
