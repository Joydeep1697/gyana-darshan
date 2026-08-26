"""Resilient, configuration-driven AI provider routing for Nyaya Darshana."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
import time
import weakref
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.error import URLError
from urllib.request import Request, urlopen

try:
    from openai import AsyncOpenAI
except ImportError:  # The stdlib HTTPS transport remains available.
    AsyncOpenAI = None

from app import config

logger = logging.getLogger("nyaya-darshan-app")


@dataclass(frozen=True)
class AICompletion:
    """A successful completion plus safe routing metadata."""

    content: str
    model: str
    fallback_used: bool


class AIProviderError(RuntimeError):
    """Base class for safe, user-displayable AI service failures."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        model: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.model = model


class AIConfigurationError(AIProviderError):
    """Raised when the provider route or credentials are invalid."""


class AIProviderUnavailable(AIProviderError):
    """Raised when every eligible configured model has failed."""


_state_lock = threading.Lock()
_state: dict[str, object] = {
    "status": "unknown",
    "active_model": None,
    "fallback_active": False,
    "last_error_code": None,
    "last_success_at": None,
    "last_failure_at": None,
    "consecutive_failures": 0,
}
_cooldown_until: dict[str, float] = {}
_semaphore_lock = threading.Lock()
_semaphores: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _status_code(exc: Exception | None) -> int | None:
    if exc is None:
        return None
    value = getattr(exc, "status_code", getattr(exc, "code", None))
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _error_code(exc: Exception | None) -> str:
    status = _status_code(exc)
    if status:
        return f"HTTP_{status}"
    return type(exc).__name__.upper() if exc is not None else "UNKNOWN"


def _is_timeout(exc: Exception) -> bool:
    return isinstance(exc, (TimeoutError, asyncio.TimeoutError)) or type(exc).__name__ == "APITimeoutError"


def _is_connection_error(exc: Exception) -> bool:
    return isinstance(exc, (ConnectionError, URLError)) or type(exc).__name__ == "APIConnectionError"


def _is_retryable(exc: Exception) -> bool:
    return _status_code(exc) in {408, 409, 429, 500, 502, 503, 504} or _is_timeout(exc) or _is_connection_error(exc)


def _allows_model_fallback(exc: Exception) -> bool:
    """Fallback only for lifecycle, capacity, or transport failures—not bad auth/input."""
    return _status_code(exc) in {404, 408, 409, 410, 429, 500, 502, 503, 504} or _is_timeout(exc) or _is_connection_error(exc)


def _safe_failure_message(exc: Exception | None) -> str:
    status = _status_code(exc)
    if status in {401, 403}:
        return "The AI provider rejected its configured credentials."
    if status in {404, 410}:
        return "The configured AI models are unavailable or have reached end of life."
    if status == 429:
        return "The AI provider is temporarily rate-limiting requests."
    if exc is not None and _is_timeout(exc):
        return "The AI provider timed out before completing the request."
    if exc is not None and _is_connection_error(exc):
        return "Nyaya Darshana could not reach the AI provider."
    return "The AI provider is temporarily unavailable."


def _provider_semaphore() -> asyncio.Semaphore:
    loop = asyncio.get_running_loop()
    with _semaphore_lock:
        semaphore = _semaphores.get(loop)
        if semaphore is None:
            semaphore = asyncio.Semaphore(config.LEGAL_MAX_CONCURRENCY)
            _semaphores[loop] = semaphore
        return semaphore


def _record_success(model: str, fallback_used: bool) -> None:
    with _state_lock:
        _state.update({
            "status": "degraded" if fallback_used else "available",
            "active_model": model,
            "fallback_active": fallback_used,
            "last_error_code": _state.get("last_error_code") if fallback_used else None,
            "last_success_at": _utc_now(),
            "consecutive_failures": 0,
        })


def _record_failure(exc: Exception, model: str, *, terminal: bool) -> None:
    status = _status_code(exc)
    cooldown = (
        config.AI_MODEL_LIFECYCLE_COOLDOWN_SECONDS
        if status in {404, 410}
        else config.AI_MODEL_FAILURE_COOLDOWN_SECONDS
    )
    with _state_lock:
        _state.update({
            "status": "unavailable" if terminal else "degraded",
            "active_model": None if terminal else _state.get("active_model"),
            "fallback_active": False if terminal else _state.get("fallback_active", False),
            "last_error_code": _error_code(exc),
            "last_failure_at": _utc_now(),
            "consecutive_failures": int(_state.get("consecutive_failures", 0)) + 1,
        })
        if _allows_model_fallback(exc):
            _cooldown_until[model] = time.monotonic() + cooldown


def reset_ai_provider_state() -> None:
    """Reset in-memory provider health and circuits (primarily for tests)."""
    with _state_lock:
        _state.update({
            "status": "unknown",
            "active_model": None,
            "fallback_active": False,
            "last_error_code": None,
            "last_success_at": None,
            "last_failure_at": None,
            "consecutive_failures": 0,
        })
        _cooldown_until.clear()
    with _semaphore_lock:
        _semaphores.clear()


def get_ai_status() -> dict[str, object]:
    """Return diagnostics that contain model IDs but never credentials or prompts."""
    configured = bool(os.getenv("NVIDIA_API_KEY", "").strip())
    with _state_lock:
        snapshot = dict(_state)
    if not configured:
        snapshot["status"] = "unconfigured"
    return {
        "provider": config.AI_PROVIDER,
        "configured": configured,
        "status": snapshot["status"],
        "primary_model": config.AI_MODEL,
        "fallback_models": list(config.AI_FALLBACK_MODELS),
        "active_model": snapshot["active_model"],
        "fallback_active": snapshot["fallback_active"],
        "last_error_code": snapshot["last_error_code"],
        "last_success_at": snapshot["last_success_at"],
        "last_failure_at": snapshot["last_failure_at"],
        "consecutive_failures": snapshot["consecutive_failures"],
    }


async def _stdlib_completion(
    *,
    client_kwargs: dict,
    model: str,
    messages: list[dict[str, str]],
    max_tokens: int,
    temperature: float,
    timeout: float,
) -> str:
    payload = json.dumps({
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }).encode("utf-8")
    request = Request(
        client_kwargs["base_url"].rstrip("/") + "/chat/completions",
        data=payload,
        headers={
            "Authorization": "Bearer " + client_kwargs["api_key"],
            "Content-Type": "application/json",
        },
        method="POST",
    )

    def request_answer() -> str:
        with urlopen(request, timeout=timeout) as response:
            result = json.loads(response.read())
        return (result["choices"][0]["message"]["content"] or "").strip()

    return await asyncio.to_thread(request_answer)


async def _sdk_completion(
    *,
    client_kwargs: dict,
    model: str,
    messages: list[dict[str, str]],
    max_tokens: int,
    temperature: float,
    timeout: float,
) -> str:
    if AsyncOpenAI is None:
        return await _stdlib_completion(
            client_kwargs=client_kwargs,
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout=timeout,
        )
    client = AsyncOpenAI(**client_kwargs, timeout=timeout, max_retries=0)
    response = await client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return (response.choices[0].message.content or "").strip()


async def _call_model(
    *,
    client_kwargs: dict,
    model: str,
    messages: list[dict[str, str]],
    max_tokens: int,
    temperature: float,
    timeout: float,
) -> str:
    last_error: Exception | None = None
    for attempt in range(config.AI_MAX_RETRIES + 1):
        try:
            result = await _sdk_completion(
                client_kwargs=client_kwargs,
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=timeout,
            )
            if not result:
                raise AIProviderUnavailable(
                    "The AI provider returned an empty response.",
                    status_code=502,
                    model=model,
                )
            return result
        except AIProviderError:
            raise
        except Exception as exc:
            last_error = exc
            if attempt >= config.AI_MAX_RETRIES or not _is_retryable(exc):
                break
            await asyncio.sleep(min(0.5 * (2 ** attempt), 2.0))

    # A status-less SDK/runtime failure may be local incompatibility. In that
    # narrow case, retry the same model through the dependency-free transport.
    if last_error is not None and _status_code(last_error) is None and AsyncOpenAI is not None:
        try:
            return await _stdlib_completion(
                client_kwargs=client_kwargs,
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=timeout,
            )
        except Exception as transport_error:
            last_error = transport_error
    assert last_error is not None
    raise last_error


async def complete_text(
    messages: list[dict[str, str]],
    *,
    max_tokens: int,
    temperature: float = 0.0,
    timeout: float | None = None,
    purpose: str = "generation",
) -> AICompletion:
    """Call the primary model, then bounded fallbacks for eligible failures."""
    try:
        config.validate_ai_model_configuration()
        client_kwargs = config.get_llm_client_kwargs()
    except RuntimeError as exc:
        raise AIConfigurationError("The AI provider is not configured correctly.") from exc

    models = config.get_configured_ai_models()
    now = time.monotonic()
    with _state_lock:
        eligible = [model for model in models if _cooldown_until.get(model, 0) <= now]
    if not eligible:
        # Let the last fallback probe recovery instead of failing forever on an
        # in-memory circuit that may outlive a short provider incident.
        eligible = [models[-1]]

    request_timeout = timeout or config.LEGAL_MODEL_TIMEOUT
    last_error: Exception | None = None
    async with _provider_semaphore():
        for model in eligible:
            fallback_used = model != models[0]
            try:
                content = await _call_model(
                    client_kwargs=client_kwargs,
                    model=model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    timeout=request_timeout,
                )
                _record_success(model, fallback_used)
                if fallback_used:
                    logger.warning(
                        "AI request completed on configured fallback model=%s purpose=%s",
                        model,
                        purpose,
                    )
                return AICompletion(content=content, model=model, fallback_used=fallback_used)
            except Exception as exc:
                last_error = exc
                terminal = model == eligible[-1] or not _allows_model_fallback(exc)
                _record_failure(exc, model, terminal=terminal)
                logger.warning(
                    "AI model request failed model=%s purpose=%s code=%s fallback_allowed=%s",
                    model,
                    purpose,
                    _error_code(exc),
                    _allows_model_fallback(exc),
                )
                if terminal:
                    break

    raise AIProviderUnavailable(
        _safe_failure_message(last_error),
        status_code=_status_code(last_error),
        model=getattr(last_error, "model", None),
    ) from last_error


async def probe_ai_provider() -> dict[str, object]:
    """Validate the configured route with a tiny startup completion."""
    await complete_text(
        [
            {"role": "system", "content": "Return only OK."},
            {"role": "user", "content": "Health check"},
        ],
        max_tokens=4,
        temperature=0.0,
        timeout=config.AI_STARTUP_PROBE_TIMEOUT,
        purpose="startup-probe",
    )
    return get_ai_status()
