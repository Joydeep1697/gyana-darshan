"""Evidence-grounded legal answer generation for Nyaya Darshan."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import time
from collections import OrderedDict
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from openai import AsyncOpenAI

from app import config
from retrieval.legal_reasoning import build_reasoning_plan, deterministic_grounded_answer, verify_answer

logger = logging.getLogger("nyaya-darshan-app")

SYSTEM_PROMPT = (
    "You are Nyaya Darshan, an Indian legal research assistant. "
    "Answer the user's question using only the supplied authoritative statutory evidence. "
    "Cite the statute and section for every material legal assertion. "
    "Clearly distinguish current law, repealed law, transition provisions, and special statutes. "
    "If the evidence does not establish an answer, say that the available evidence is insufficient. "
    "Never invent a statute, section, precedent, deadline, penalty, or citation. "
    "Give the conclusion first, distinguish each independent issue, and omit generic disclaimers."
)

_cache: OrderedDict[str, tuple[float, str]] = OrderedDict()
_semaphore: asyncio.Semaphore | None = None


def _cache_key(query: str, evidence_context: str) -> str:
    return hashlib.sha256(f"{query}\0{evidence_context}\0{config.LLM_MODEL}".encode()).hexdigest()


def _get_cached(key: str) -> str | None:
    item = _cache.get(key)
    if not item:
        return None
    created, answer = item
    if time.monotonic() - created > config.LEGAL_CACHE_TTL_SECONDS:
        _cache.pop(key, None)
        return None
    _cache.move_to_end(key)
    return answer


def _store_cached(key: str, answer: str) -> None:
    _cache[key] = (time.monotonic(), answer)
    _cache.move_to_end(key)
    while len(_cache) > 512:
        _cache.popitem(last=False)


def _provider_semaphore() -> asyncio.Semaphore:
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(config.LEGAL_MAX_CONCURRENCY)
    return _semaphore


def _retryable(exc: Exception) -> bool:
    status = getattr(exc, "status_code", getattr(exc, "code", None))
    return status in {408, 409, 429, 500, 502, 503, 504} or isinstance(
        exc, (TimeoutError, asyncio.TimeoutError, ConnectionError, URLError)
    ) or type(exc).__name__ in {"APIConnectionError", "APITimeoutError"}


def _provider_failure_message(exc: Exception | None) -> str:
    status = getattr(exc, "status_code", getattr(exc, "code", None))
    if status in {401, 403}:
        return "NVIDIA rejected the API key. Check NVIDIA_API_KEY in your .env file."
    if status == 404:
        return "The NVIDIA model was not found. Check NVIDIA_LLM_MODEL in your .env file."
    if status == 429:
        return "NVIDIA is temporarily rate-limiting requests. Please retry shortly."
    if isinstance(exc, (TimeoutError, asyncio.TimeoutError)) or type(exc).__name__ == "APITimeoutError":
        return "NVIDIA took too long to answer. Retry or increase LEGAL_MODEL_TIMEOUT."
    if isinstance(exc, (ConnectionError, URLError)) or type(exc).__name__ == "APIConnectionError":
        return "Nyaya Darshan could not reach NVIDIA. Check your internet, proxy, or firewall."
    return "The legal AI provider is temporarily unavailable."


async def _generate_with_standard_http(
    client_kwargs: dict, messages: list[dict], max_tokens: int | None = None
) -> str:
    """Bypass a broken OpenAI/httpx installation using Python's HTTPS client."""
    payload = json.dumps({
        "model": config.LLM_MODEL,
        "messages": messages,
        "temperature": 0.0,
        "max_tokens": max_tokens or config.LEGAL_MAX_TOKENS,
    }).encode("utf-8")
    endpoint = client_kwargs["base_url"].rstrip("/") + "/chat/completions"
    request = Request(
        endpoint, data=payload,
        headers={
            "Authorization": "Bearer " + client_kwargs["api_key"],
            "Content-Type": "application/json",
        },
        method="POST",
    )

    def request_answer() -> str:
        with urlopen(request, timeout=config.LEGAL_MODEL_TIMEOUT) as response:
            result = json.loads(response.read())
        return (result["choices"][0]["message"]["content"] or "").strip()

    return await asyncio.to_thread(request_answer)


def _verified_evidence_excerpt(evidence_context: str) -> str:
    """Exclude planner instructions when deciding which citations were actually retrieved."""
    marker = "AUTHORITATIVE STATUTORY EXCERPTS:"
    return evidence_context.split(marker, 1)[-1] if marker in evidence_context else evidence_context


def _citation_is_grounded(statute: str, section: str, evidence_context: str) -> bool:
    excerpt = _verified_evidence_excerpt(evidence_context)
    pattern = (
        r"\b" + re.escape(statute) + r"\b[^\n]{0,80}\bsections?\s*"
        + re.escape(section) + r"(?!\d)"
    )
    return bool(re.search(pattern, excerpt, re.IGNORECASE))


def _enforce_guardrails(query: str, answer: str, evidence_context: str = "") -> str:
    """Restore omitted issues using only citations present in retrieved excerpts."""
    plan = build_reasoning_plan(query)
    result = verify_answer(answer, plan, [])
    if result["passed"] and not (plan.safeguards and plan.is_complex):
        return answer
    missing = set(result["missing_citations"])
    additions = []
    for issue in plan.issues:
        expected = [f"{issue.statute} {section}" for section in issue.sections]
        if not missing.intersection(expected):
            continue
        supported = [
            section for section in issue.sections
            if _citation_is_grounded(issue.statute, section, evidence_context)
        ]
        if not supported:
            continue
        citations = ", ".join(f"{issue.statute} section {section}" for section in supported)
        additions.append(
            f"**{issue.category.replace('_', ' ').title()}:** {issue.guidance} ({citations}.)"
        )
    if result["contradictions"]:
        additions.extend(result["contradictions"])
    if any("proof at trial" in safeguard.lower() for safeguard in plan.safeguards):
        additions.append(
            "**Evidentiary limits:** These facts describe allegations, not established guilt; "
            "identity, intent, age, authenticity, and disputed facts require admissible proof."
        )
    if not additions:
        return answer
    return answer.rstrip() + "\n\n" + "\n\n".join(dict.fromkeys(additions))


def _is_complex_scenario(query: str) -> bool:
    plan = build_reasoning_plan(query)
    numbered_questions = len(re.findall(r"(?:^|\n)\s*\d+[.)]\s+", query))
    return plan.is_complex or numbered_questions >= 2 or (len(query) > 450 and len(plan.issues) >= 1)


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
    complex_scenario = _is_complex_scenario(query)
    if not complex_scenario:
        direct_answer = deterministic_grounded_answer(query, evidence_context)
        if direct_answer:
            logger.info("Answered a single statutory issue locally without a cloud model request.")
            return direct_answer
    try:
        client_kwargs = config.get_llm_client_kwargs()
    except RuntimeError as exc:
        if config.IS_PRODUCTION:
            raise LegalGenerationError("The legal AI provider is not configured.") from exc
        logger.info("Legal AI is not configured; returning retrieved evidence only.")
        return _evidence_only_response(query, evidence_context)

    key = _cache_key(query, evidence_context)
    cached = _get_cached(key)
    if cached is not None:
        return cached

    client = AsyncOpenAI(**client_kwargs, timeout=config.LEGAL_MODEL_TIMEOUT, max_retries=0)
    max_tokens = config.LEGAL_SCENARIO_MAX_TOKENS if complex_scenario else config.LEGAL_MAX_TOKENS
    max_words = config.LEGAL_SCENARIO_MAX_WORDS if complex_scenario else 160
    instructions = (
        f"Answer in at most {max_words} words. Apply every deterministic safeguard. "
        "Use only supplied excerpts and cite each material conclusion."
    )
    if complex_scenario:
        instructions += (
            " Address EVERY numbered question and EVERY verified legal issue in separate labeled sections. "
            "Distinguish offence classification, child status and consent, mandatory reporting, "
            "threats or intimidation, FIR procedure, electronic evidence, and limits on proving guilt "
            "whenever those issues arise. If an issue lacks a retrieved statutory excerpt, identify the "
            "evidence gap rather than inventing a section. End with a concise practical conclusion."
        )
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": (
            f"{evidence_context}\n\nQUESTION: {query}\n\n"
            f"{instructions}"
        )},
    ]
    last_error: Exception | None = None
    async with _provider_semaphore():
        for attempt in range(config.LEGAL_MAX_RETRIES + 1):
            try:
                completion = await client.chat.completions.create(
                    model=config.LLM_MODEL,
                    messages=messages,
                    temperature=0.0,
                    max_tokens=max_tokens,
                )
                answer = (completion.choices[0].message.content or "").strip()
                if not answer:
                    raise LegalGenerationError("The legal AI provider returned an empty answer.")
                answer = _enforce_guardrails(query, answer, evidence_context)
                _store_cached(key, answer)
                return answer
            except LegalGenerationError:
                raise
            except Exception as exc:
                last_error = exc
                if attempt >= config.LEGAL_MAX_RETRIES or not _retryable(exc):
                    break
                await asyncio.sleep(min(0.5 * (2 ** attempt), 2.0))
    logger.warning("Primary NVIDIA client failed: %s; trying standard HTTPS fallback.", type(last_error).__name__)
    try:
        answer = await _generate_with_standard_http(client_kwargs, messages, max_tokens=max_tokens)
        if not answer:
            raise LegalGenerationError("The legal AI provider returned an empty answer.")
        answer = _enforce_guardrails(query, answer, evidence_context)
        _store_cached(key, answer)
        return answer
    except LegalGenerationError:
        raise
    except Exception as fallback_error:
        logger.error("NVIDIA HTTPS fallback failed: %s", type(fallback_error).__name__)
        raise LegalGenerationError(_provider_failure_message(fallback_error)) from fallback_error
