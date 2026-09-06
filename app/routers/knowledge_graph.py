import logging
from fastapi import APIRouter, Depends, HTTPException
from app.database import get_db, Database
from api.auth.dependencies import get_workspace_context

logger = logging.getLogger("nyaya-darshan-app")
router = APIRouter()

@router.get("/document/{doc_id}/links")
async def get_document_links(doc_id: str, db: Database = Depends(get_db), workspace: dict = Depends(get_workspace_context)):
    """Get all citation links for a document from DB."""
    organization_id = workspace["organization"]["id"]
    document = db.get_document(doc_id)
    if not document or document.get("organization_id") != organization_id:
        raise HTTPException(404, "Document not found")
    return {"links": db.get_document_links(doc_id, organization_id=organization_id)}

@router.get("/document/{doc_id}/related")
async def get_related_documents(doc_id: str, db: Database = Depends(get_db), workspace: dict = Depends(get_workspace_context)):
    """Suggest related documents."""
    organization_id = workspace["organization"]["id"]
    document = db.get_document(doc_id)
    if not document or document.get("organization_id") != organization_id:
        raise HTTPException(404, "Document not found")
    return {"related": db.get_related_documents(doc_id, organization_id=organization_id)}

@router.get("/section/{ref}")
async def get_section_references(ref: str, db: Database = Depends(get_db), workspace: dict = Depends(get_workspace_context)):
    """Search section_index table for all docs referencing a section."""
    return {"documents": db.get_docs_by_section(ref, organization_id=workspace["organization"]["id"])}

@router.get("/section/{ref}/impact")
async def get_section_impact(ref: str, db: Database = Depends(get_db), workspace: dict = Depends(get_workspace_context)):
    """List documents affected if a section changes."""
    return {"impacted": db.get_section_impact(ref, organization_id=workspace["organization"]["id"])}

@router.get("/contradictions")
async def get_contradictions(db: Database = Depends(get_db), workspace: dict = Depends(get_workspace_context)):
    """Get detected contradictions."""
    return {"contradictions": db.get_compliance_gaps(gap_type="contradiction", organization_id=workspace["organization"]["id"])}

@router.get("/network")
async def get_network(db: Database = Depends(get_db), workspace: dict = Depends(get_workspace_context)):
    """Full graph data for visualization."""
    return db.get_full_graph(organization_id=workspace["organization"]["id"])
