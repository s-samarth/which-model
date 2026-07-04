"""Application configuration.

All environment-dependent values live here, loaded from `.env` via pydantic-settings.
Swapping the serving model or backend is a `.env` change only.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings, loaded from environment / .env file."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # LLM serving (OpenAI-compatible)
    openai_base_url: str = "http://localhost:11434/v1"
    openai_api_key: str = "ollama"
    model_name: str = "qwen3.5:4b"
    llm_timeout_s: float = 120.0
    llm_temperature: float = 0.2
    # For thinking models (qwen3.5 family): "none" disables reasoning tokens,
    # which a 4B model does not need for extraction and keeps replies fast.
    # Set empty to omit the parameter for backends that reject it.
    llm_reasoning_effort: str = "none"
    # Ollama unloads idle models after ~5 minutes; slow human turns then pay a
    # full model reload. Keep it warm for the session. Empty to omit.
    llm_keep_alive: str = "30m"

    # Data
    db_path: Path = Path("data/models.db")
    kb_dir: Path = Path("kb")
    snippets_path: Path = Path("data/hardware_snippets.yaml")

    # Retrieval: hybrid (BM25 + embeddings, default), bm25, or embedding.
    # Hybrid degrades to BM25 automatically if the embedding model is missing.
    retriever_backend: str = "hybrid"
    embed_model_name: str = "nomic-embed-text"
    embed_cache_path: Path = Path("data/kb_embeddings.json")

    # Web search: "ddgs" (DuckDuckGo, no key) or "off".
    web_search: str = "ddgs"

    # Server
    host: str = "127.0.0.1"
    port: int = 8000
    session_ttl_s: int = 3600

    # Display
    usd_to_inr: float = 84.0

    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings singleton."""
    return Settings()
