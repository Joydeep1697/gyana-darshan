import logging
import asyncio
from fastapi import APIRouter, Depends, BackgroundTasks
from app.database import get_db, Database
from api.auth.dependencies import get_workspace_context

logger = logging.getLogger("nyaya-darshan-app")
router = APIRouter()

@router.get("/compliance-gaps")
async def get_compliance_gaps(db: Database = Depends(get_db), workspace: dict = Depends(get_workspace_context)):
    """Return compliance_gaps from DB."""
    return {"gaps": db.get_compliance_gaps(organization_id=workspace["organization"]["id"])}

@router.get("/deadlines")
async def get_deadlines(status: str = None, db: Database = Depends(get_db), workspace: dict = Depends(get_workspace_context)):
    """Return deadlines from DB, optionally filtered by status."""
    return {"deadlines": db.get_deadlines(status=status, organization_id=workspace["organization"]["id"])}

@router.get("/staleness")
async def check_staleness(db: Database = Depends(get_db), workspace: dict = Depends(get_workspace_context)):
    """Check documents for references to outdated/repealed acts."""
    return {"stale_documents": db.check_staleness(organization_id=workspace["organization"]["id"])}

def run_corpus_scan():
    """Background task for full corpus intelligence scan."""
    logger.info("Starting full corpus intelligence scan...")
    # Add actual background logic that calls DB/models
    logger.info("Scan complete.")

@router.post("/scan")
async def trigger_scan(background_tasks: BackgroundTasks):
    """Trigger full corpus intelligence scan in the background."""
    background_tasks.add_task(run_corpus_scan)
    return {"status": "Scan started in background"}
