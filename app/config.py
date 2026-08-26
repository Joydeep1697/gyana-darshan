"""Nyaya Darshana — Configuration Management.

Reads environment variables (with .env fallback) and provides
centralized path and LLM configuration for the entire application.
"""

from __future__ import annotations

import os
import sys
import shutil
from pathlib import Path

from dotenv import load_dotenv

# ── Load .env file if present ─────────────────────────────────────
_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"
if _ENV_FILE.exists():
    load_dotenv(_ENV_FILE)

# Prevent Hugging Face from making slow online network checks
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

# ── Environment & Production Guard ────────────────────────────────
ENV = os.getenv("ENVIRONMENT", os.getenv("ENV", "development")).lower()
IS_PRODUCTION = ENV in ["production", "prod"]


def validate_production_config():
    """Fail-closed validation when running in production mode."""
    if not IS_PRODUCTION:
        return

    # 1. NYAYA_API_KEY must be configured
    api_key = os.getenv("NYAYA_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "FAIL-CLOSED: NYAYA_API_KEY is required in production mode. Refusing startup."
        )

    # 2. ALLOWED_ORIGINS must be explicitly configured and cannot be wildcard
    raw_origins = os.getenv("ALLOWED_ORIGINS", "").strip()
    if not raw_origins or raw_origins == "*":
        raise RuntimeError(
            "FAIL-CLOSED: Explicit non-wildcard ALLOWED_ORIGINS is required in production mode. Refusing startup."
        )

    # 3. Authentication tokens must never use a public or predictable secret.
    jwt_secret = os.getenv("NYAYA_JWT_SECRET", "").strip()
    if len(jwt_secret) < 32:
        raise RuntimeError(
            "FAIL-CLOSED: NYAYA_JWT_SECRET must contain at least 32 characters in production mode."
        )

    # 4. If AI_PROVIDER is nvidia, NVIDIA_API_KEY must be configured.
    if LLM_PROVIDER == "nvidia":
        nv_key = os.getenv("NVIDIA_API_KEY", "").strip()
        if not nv_key:
            raise RuntimeError(
                "FAIL-CLOSED: NVIDIA_API_KEY is required when LLM_PROVIDER=nvidia in production mode."
            )

    # 5. Refuse known-retired hosted models before serving traffic.
    validate_ai_model_configuration()
    if len(get_configured_ai_models()) < 2:
        raise RuntimeError(
            "FAIL-CLOSED: Production requires at least one AI_FALLBACK_MODEL distinct from AI_MODEL."
        )


# ── Base directories ──────────────────────────────────────────────

ROOT_DIR = Path(__file__).resolve().parent.parent
INDIAN_LEGAL_DIR = Path(
    os.getenv("INDIAN_LEGAL_DIR", str(ROOT_DIR / "Indian Legal"))
)

# Ensure the Indian Legal backend modules are importable
if str(INDIAN_LEGAL_DIR) not in sys.path:
    sys.path.insert(0, str(INDIAN_LEGAL_DIR))

RAW_DIR = Path(os.getenv("RAW_DIR", str(INDIAN_LEGAL_DIR / "raw")))
CORPUS_DIR = Path(os.getenv("CORPUS_DIR", str(INDIAN_LEGAL_DIR / "processed_corpus")))
INDEX_DIR = Path(os.getenv("INDEX_DIR", str(INDIAN_LEGAL_DIR / "nova_rag_index")))
CATEGORY_DIR = Path(os.getenv("CATEGORY_DIR", str(INDIAN_LEGAL_DIR / "Category")))
CLASSIFICATION_REPORTS_DIR = INDIAN_LEGAL_DIR / "classification_reports"
CATEGORY_REGISTRY_DB = INDIAN_LEGAL_DIR / "category_registry.sqlite3"

# ── App database ──────────────────────────────────────────────────

DATA_DIR = Path(os.getenv("NYAYA_DATA_DIR", str(ROOT_DIR / "data"))).expanduser()
APP_DB_PATH = DATA_DIR / "nyaya_app.sqlite3"

# ── AI Provider ──────────────────────────────────────────────────

AI_PROVIDER = os.getenv("AI_PROVIDER", os.getenv("LLM_PROVIDER", "nvidia")).strip().lower()
# Backward-compatible alias for deployments that still use LLM_PROVIDER.
LLM_PROVIDER = AI_PROVIDER
SUPPORTED_LLM_PROVIDERS = {"nvidia"}

AI_BASE_URL = os.getenv(
    "AI_BASE_URL",
    os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"),
).strip().rstrip("/")

AI_MODEL = os.getenv(
    "AI_MODEL",
    os.getenv("NVIDIA_LLM_MODEL", "nvidia/nemotron-3-super-120b-a12b"),
).strip()


def _parse_models(raw: str) -> tuple[str, ...]:
    """Return a stable, de-duplicated model list from a comma-separated value."""
    return tuple(dict.fromkeys(part.strip() for part in raw.split(",") if part.strip()))


AI_FALLBACK_MODELS = _parse_models(
    os.getenv(
        "AI_FALLBACK_MODELS",
        os.getenv(
            "AI_FALLBACK_MODEL",
            os.getenv("NVIDIA_FALLBACK_MODEL", "nvidia/nemotron-3.5-lightning-30b-a3b"),
        ),
    )
)

# These hosted endpoints are known to have completed their published lifecycle.
# A custom/self-hosted NIM base URL may still serve the same model identifiers.
RETIRED_NVIDIA_HOSTED_MODELS = frozenset({
    "nvidia/llama-3.3-nemotron-super-49b-v1",
    "nvidia/llama-3.3-nemotron-super-49b-v1.5",
})


def get_configured_ai_models() -> tuple[str, ...]:
    """Return primary then fallback models, without duplicates."""
    return tuple(dict.fromkeys((AI_MODEL, *AI_FALLBACK_MODELS)))


def ai_model_signature() -> str:
    """Stable cache-key component for the complete configured model route."""
    return "|".join(get_configured_ai_models())


def validate_ai_model_configuration() -> None:
    """Reject malformed or known-retired NVIDIA hosted model routes."""
    if LLM_PROVIDER not in SUPPORTED_LLM_PROVIDERS:
        raise RuntimeError(
            f"Unsupported AI_PROVIDER={LLM_PROVIDER!r}. Configure AI_PROVIDER=nvidia."
        )
    models = get_configured_ai_models()
    if not models or not models[0]:
        raise RuntimeError("AI_MODEL must name a primary model.")
    for model in models:
        if any(character.isspace() for character in model) or "/" not in model:
            raise RuntimeError(f"Invalid AI model identifier: {model!r}")
    if "integrate.api.nvidia.com" in AI_BASE_URL:
        retired = [model for model in models if model in RETIRED_NVIDIA_HOSTED_MODELS]
        if retired:
            raise RuntimeError(
                "Configured NVIDIA hosted model has reached end of life: " + ", ".join(retired)
            )


def get_llm_client_kwargs() -> dict:
    """Return kwargs for ``openai.OpenAI(...)`` matching the active provider."""
    if LLM_PROVIDER not in SUPPORTED_LLM_PROVIDERS:
        raise RuntimeError(
            f"Unsupported LLM_PROVIDER={LLM_PROVIDER!r}. Configure LLM_PROVIDER=nvidia."
        )

    api_key = os.getenv("NVIDIA_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "NVIDIA_API_KEY environment variable is required when LLM_PROVIDER=nvidia"
        )
    return {
        "base_url": AI_BASE_URL,
        "api_key": api_key,
    }


# Backward-compatible alias for older modules; new code uses AI_MODEL.
LLM_MODEL = AI_MODEL
RERANK_MODEL = os.getenv("NVIDIA_RERANK_MODEL", "nvidia/llama-nemotron-rerank-1b-v2")
AI_STARTUP_PROBE = os.getenv("AI_STARTUP_PROBE", "true").strip().lower() in {"1", "true", "yes", "on"}
AI_STARTUP_PROBE_TIMEOUT = float(os.getenv("AI_STARTUP_PROBE_TIMEOUT", "12"))
AI_MAX_RETRIES = int(os.getenv("AI_MAX_RETRIES", os.getenv("LEGAL_MAX_RETRIES", "2")))
AI_MODEL_FAILURE_COOLDOWN_SECONDS = float(os.getenv("AI_MODEL_FAILURE_COOLDOWN_SECONDS", "60"))
AI_MODEL_LIFECYCLE_COOLDOWN_SECONDS = float(os.getenv("AI_MODEL_LIFECYCLE_COOLDOWN_SECONDS", "3600"))
LEGAL_REQUEST_TIMEOUT = float(os.getenv("LEGAL_REQUEST_TIMEOUT", "75"))
LEGAL_MODEL_TIMEOUT = float(os.getenv("LEGAL_MODEL_TIMEOUT", "60"))
LEGAL_MAX_TOKENS = int(os.getenv("LEGAL_MAX_TOKENS", "320"))
LEGAL_SCENARIO_MAX_TOKENS = int(os.getenv("LEGAL_SCENARIO_MAX_TOKENS", "1100"))
LEGAL_SCENARIO_MAX_WORDS = int(os.getenv("LEGAL_SCENARIO_MAX_WORDS", "550"))
LEGAL_SCENARIO_MAX_SOURCES = int(os.getenv("LEGAL_SCENARIO_MAX_SOURCES", "12"))
LEGAL_CACHE_TTL_SECONDS = int(os.getenv("LEGAL_CACHE_TTL_SECONDS", "300"))
LEGAL_MAX_CONCURRENCY = int(os.getenv("LEGAL_MAX_CONCURRENCY", "4"))
LEGAL_MAX_RETRIES = int(os.getenv("LEGAL_MAX_RETRIES", "2"))
RERANK_BASE_URL = os.getenv(
    "NVIDIA_RERANK_URL",
    "https://ai.api.nvidia.com/v1/retrieval/nvidia/llama-nemotron-rerank-1b-v2/reranking",
)

# ── OCR ───────────────────────────────────────────────────────────

TESSERACT_CMD = os.getenv("TESSERACT_CMD", shutil.which("tesseract") or "")
OCR_LANGUAGE = os.getenv("OCR_LANGUAGE", "eng")
OCR_ENABLED = bool(TESSERACT_CMD) and Path(TESSERACT_CMD).is_file()

# ── Server ────────────────────────────────────────────────────────

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

# ── Embedding model (local, no API needed) ────────────────────────

EMBED_MODEL_NAME = os.getenv(
    "EMBED_MODEL", "sentence-transformers/all-mpnet-base-v2"
)

# ── Static files ──────────────────────────────────────────────────

STATIC_DIR = Path(__file__).resolve().parent / "static"
