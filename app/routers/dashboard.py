import logging
import asyncio
import json
import time
from pathlib import Path
from fastapi import APIRouter, Depends
import openai
from app.database import get_db, Database
from app.config import get_llm_client_kwargs, LLM_MODEL, INDEX_DIR
from api.auth.dependencies import get_current_user

logger = logging.getLogger("nyaya-darshan-app")
router = APIRouter()

# Simple cache for daily briefing
_briefing_cache = {"data": None, "time": 0}

@router.get("/stats")
async def get_stats(db: Database = Depends(get_db), user: dict = Depends(get_current_user)):
    """Return DashboardStats."""
    return db.get_document_stats(owner_id=user["id"])

@router.get("/briefing")
async def get_briefing(db: Database = Depends(get_db), user: dict = Depends(get_current_user)):
    """AI-generated daily briefing, cached for 1 hour."""
    if _briefing_cache["data"] and _briefing_cache.get("owner_id") == user["id"] and (time.time() - _briefing_cache["time"] < 3600):
        return {"briefing": _briefing_cache["data"]}
        
    stats = db.get_document_stats(owner_id=user["id"])
    
    def generate_briefing():
        client = openai.OpenAI(**get_llm_client_kwargs())
        prompt = f"Write a short 3-paragraph executive legal briefing based on these stats: {stats}"
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": "You are a concise Indian legal AI advisor."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content

    try:
        briefing = await asyncio.to_thread(generate_briefing)
        _briefing_cache["data"] = briefing
        _briefing_cache["time"] = time.time()
        _briefing_cache["owner_id"] = user["id"]
        return {"briefing": briefing}
    except Exception as e:
        logger.error(f"Briefing generation failed: {e}")
        return {"briefing": "Unable to generate briefing at this time."}

@router.get("/risk-heatmap")
async def get_risk_heatmap(db: Database = Depends(get_db), user: dict = Depends(get_current_user)):
    """Risk levels across domains."""
    return {"heatmap": db.get_risk_heatmap(owner_id=user["id"])}

@router.get("/coverage")
async def get_coverage(db: Database = Depends(get_db), user: dict = Depends(get_current_user)):
    """Corpus coverage analysis per domain."""
    return {"coverage": db.get_domain_counts(owner_id=user["id"])}

@router.get("/activity")
async def get_activity(db: Database = Depends(get_db), user: dict = Depends(get_current_user)):
    """Recent activity from activity log."""
    return {"activity": db.get_recent_activity(owner_id=user["id"])}

@router.get("/trends")
async def get_trends(db: Database = Depends(get_db), user: dict = Depends(get_current_user)):
    """Upload timeline data grouped by date."""
    return {"trends": db.get_upload_trends(owner_id=user["id"])}

@router.get("/index-info")
async def get_index_info():
    """Read nova_rag_index/index_config.json and stats."""
    try:
        config_path = Path(INDEX_DIR) / "index_config.json"
        if config_path.exists():
            with open(config_path, "r") as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error reading index info: {e}")
    return {"status": "unavailable"}
