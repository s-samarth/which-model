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

    # Data
    db_path: Path = Path("data/models.db")
    kb_dir: Path = Path("kb")
    snippets_path: Path = Path("data/hardware_snippets.yaml")

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
