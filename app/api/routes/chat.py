from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.auth.dependencies import get_workspace_context
from app.services.rag_service import chat as rag_chat
from app.services.rag_service import get_chat_history

router = APIRouter()


class Citation(BaseModel):
    matter_id: str
    case_no: str | None = None
    field: str


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    matter_id: str | None = Field(default=None, max_length=128)
    history: list[dict] = Field(default_factory=list)


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation]
    provenance_verified: bool = False
    retrieved_count: int
    llm_placeholder: bool = True


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, workspace: dict = Depends(get_workspace_context)):
    try:
        return rag_chat(
            workspace["organization"]["id"],
            request.query,
            matter_id=request.matter_id,
            history=request.history,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/chat/matter/{matter_id}", response_model=ChatResponse)
def matter_chat(matter_id: str, request: ChatRequest, workspace: dict = Depends(get_workspace_context)):
    try:
        return rag_chat(workspace["organization"]["id"], request.query, matter_id=matter_id, history=request.history)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/chat/history/{matter_id}")
def history(matter_id: str, workspace: dict = Depends(get_workspace_context)):
    return {
        "matter_id": matter_id,
        "history": get_chat_history(workspace["organization"]["id"], matter_id),
        "provenance_verified": False,
    }
