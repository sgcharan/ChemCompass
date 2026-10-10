from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CORPUS_DB = REPO_ROOT / "data" / "pyq-corpus" / "corpus.sqlite"

CORPUS_DB = Path(os.environ.get("PYQ_CORPUS_DB", str(DEFAULT_CORPUS_DB)))

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL = os.environ.get("PYQ_LLM_MODEL", "gpt-4o-mini")

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")

USE_OLLAMA = os.environ.get("USE_OLLAMA", "").lower() in ("1", "true", "yes")
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2")

# auto | openai | gemini | ollama | local
LLM_PROVIDER = os.environ.get("PYQ_LLM_PROVIDER", "auto").lower()

API_PORT = int(os.environ.get("PORT", "8787"))


def cors_allow_origins() -> list[str]:
    """Local dev origins plus PYQ_CORS_ORIGINS (comma-separated) for production UI."""
    origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    extra = os.environ.get("PYQ_CORS_ORIGINS", "").strip()
    if extra:
        for part in extra.split(","):
            o = part.strip()
            if o and o not in origins:
                origins.append(o)
    return origins


def is_local_openai_endpoint() -> bool:
    u = OPENAI_BASE_URL.lower()
    return "127.0.0.1" in u or "localhost" in u


def is_cloud_openai() -> bool:
    key = OPENAI_API_KEY
    if not key or key == "not-needed":
        return False
    return not is_local_openai_endpoint()


def openai_auth_key() -> str:
    return OPENAI_API_KEY if OPENAI_API_KEY else "not-needed"


LLM_CONFIGURED = bool(
    GEMINI_API_KEY
    or is_cloud_openai()
    or USE_OLLAMA
    or is_local_openai_endpoint()
    or LLM_PROVIDER == "ollama"
)


def active_llm_provider() -> str | None:
    if LLM_PROVIDER == "ollama" or (LLM_PROVIDER == "auto" and USE_OLLAMA):
        return "ollama"
    if LLM_PROVIDER == "gemini" and GEMINI_API_KEY:
        return "gemini"
    if LLM_PROVIDER == "openai":
        return "openai"
    if LLM_PROVIDER == "local" or (LLM_PROVIDER == "auto" and is_local_openai_endpoint()):
        return "openai"
    if LLM_PROVIDER == "auto":
        if GEMINI_API_KEY:
            return "gemini"
        if is_cloud_openai():
            return "openai"
        if USE_OLLAMA:
            return "ollama"
        if is_local_openai_endpoint():
            return "openai"
    if GEMINI_API_KEY:
        return "gemini"
    if is_cloud_openai():
        return "openai"
    if USE_OLLAMA:
        return "ollama"
    if is_local_openai_endpoint():
        return "openai"
    return None
