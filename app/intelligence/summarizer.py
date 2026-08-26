"""AI-assisted summaries routed through the resilient provider service."""

from __future__ import annotations

import logging

from app import config
from app.intelligence.ai_provider import AIProviderError, complete_text

logger = logging.getLogger("nyaya-darshan-app")


async def _complete(messages: list[dict[str, str]], *, max_tokens: int, purpose: str) -> str:
    try:
        return (await complete_text(
            messages,
            max_tokens=max_tokens,
            temperature=0.0,
            timeout=config.LEGAL_MODEL_TIMEOUT,
            purpose=purpose,
        )).content
    except AIProviderError:
        logger.warning("AI generation unavailable purpose=%s", purpose)
        raise


async def generate_summary(text: str, doc_type: str, metadata: dict) -> str:
    """Generate a concise, structured legal-document summary."""
    truncated_text = text[:4000]
    prompt = (
        f"Document Type: {doc_type}\n"
        f"Metadata: {metadata}\n"
        f"Text Excerpt: {truncated_text}\n\n"
        "Based only on the text and metadata above, generate three short paragraphs:\n"
        "1. What the document is.\n"
        "2. Its key provisions or holdings.\n"
        "3. Its practical implications.\n"
        "Do not invent provisions, holdings, dates, parties, or citations."
    )
    return await _complete(
        [
            {"role": "system", "content": "You are a source-grounded senior Indian legal analyst."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=450,
        purpose="vault-summary",
    )


async def generate_follow_ups(question: str, answer: str, context_snippets: list[str]) -> list[str]:
    """Generate three contextual follow-up questions."""
    context_str = "\n".join(context_snippets)
    prompt = (
        f"Context: {context_str}\n"
        f"User Question: {question}\n"
        f"Answer Provided: {answer}\n\n"
        "Generate exactly three relevant follow-up questions. "
        "Output one question per line without numbering or bullets."
    )
    raw_text = await _complete(
        [
            {"role": "system", "content": "You are a source-grounded Indian legal assistant."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=160,
        purpose="follow-up-suggestions",
    )
    questions = [line.strip("- 1234567890. ") for line in raw_text.splitlines() if line.strip()]
    return questions[:3]


async def generate_briefing(stats: dict, gaps: list, deadlines: list, recent_activity: list) -> str:
    """Generate a one-paragraph legal-workspace briefing."""
    prompt = (
        f"Stats: {stats}\n"
        f"Gaps: {gaps}\n"
        f"Deadlines: {deadlines}\n"
        f"Recent Activity: {recent_activity}\n\n"
        "Write one concise paragraph summarising the workspace state, deadlines, risks, and activity. "
        "Use only the supplied data."
    )
    return await _complete(
        [
            {"role": "system", "content": "You are a concise executive legal assistant."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=240,
        purpose="workspace-briefing",
    )
