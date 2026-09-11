"""Authenticated tenant-scoped retrieval routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from api.auth.dependencies import get_workspace_context
from retrieval.search import search as retrieval_search

router = APIRouter()


class RetrievalSearchRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=500)
    top_k: int = Field(default=10, ge=1, le=25)


@router.post("/search")
async def search(request: RetrievalSearchRequest, workspace: dict = Depends(get_workspace_context)) -> dict[str, Any]:
    """Search public fallback corpus and the authenticated workspace's Vault files."""
    tenant_id = workspace["organization"]["id"]
    results = retrieval_search(request.query, tenant_id, top_k=request.top_k)
    return {"query": request.query, "tenant_id": tenant_id, "results": results, "total": len(results)}
