"""Evidence-grounded legal answer generation for Nyaya Darshan."""

from __future__ import annotations

import logging

from openai import AsyncOpenAI

from app import config

logger = logging.getLogger("nyaya-darshan-app")

SYSTEM_PROMPT = (
    "You are Nyaya Darshan, an Indian legal research assistant. "
    "Answer the user's question using only the supplied authoritative statutory evidence. "
    "Cite the statute and section for every material legal assertion. "
    "Clearly distinguish current law, repealed law, transition provisions, and special statutes. "
    "If the evidence does not establish an answer, say that the available evidence is insufficient. "
    "Never invent a statute, section, precedent, deadline, penalty, or citation."
)


class LegalGenerationError(RuntimeError):
    """Raised when a configured production model cannot generate an answer."""


def _evidence_only_response(query: str, evidence_context: str) -> str:
    """Expose retrieved source material without claiming model inference occurred."""
    return (
        "AI-generated analysis is unavailable because no cloud model is configured. "
        "The retrieved authoritative statutory evidence is provided below for review.\n\n"
        f"Question: {query}\n\n"
        f"Authoritative statutory evidence:\n{evidence_context}"
    )


async def generate_grounded_legal_answer(query: str, evidence_context: str) -> str:
    """Generate a cited answer, with an explicit evidence-only development mode."""
    try:
        client_kwargs = config.get_llm_client_kwargs()
    except RuntimeError as exc:
        if config.IS_PRODUCTION:
            raise LegalGenerationError("The legal AI provider is not configured.") from exc
        logger.info("Legal AI is not configured; returning retrieved evidence only.")
        return _evidence_only_response(query, evidence_context)

    try:
        client = AsyncOpenAI(**client_kwargs, timeout=30.0, max_retries=1)
        completion = await client.chat.completions.create(
            model=config.LLM_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        "Authoritative statutory evidence:\n"
                        f"{evidence_context}\n\n"
                        f"Legal question: {query}\n\n"
                        "Give a direct, properly cited answer based only on the evidence."
                    ),
                },
            ],
            temperature=0.1,
            max_tokens=1200,
        )
        answer = (completion.choices[0].message.content or "").strip()
        if not answer:
            raise LegalGenerationError("The legal AI provider returned an empty answer.")
        return answer
    except LegalGenerationError:
        raise
    except Exception as exc:
        logger.exception("Cloud legal answer generation failed.")
        raise LegalGenerationError("The legal AI provider is temporarily unavailable.") from exc
