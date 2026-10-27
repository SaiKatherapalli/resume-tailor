"""
Application settings.

Values are read from environment variables, or from a `.env` file in the project root.
Example: the env variable GROQ_API_KEY fills the field `groq_api_key` (names are case-insensitive).
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,  # `GROQ_API_KEY=` (empty) counts as "not set", not as ""
        extra="ignore",  # unknown variables in .env are ignored instead of causing an error
    )

    # ---------- LLM (Groq) ----------
    groq_api_key: SecretStr | None = None
    groq_model: str = "openai/gpt-oss-120b"
    llm_temperature: float = Field(default=0.2, ge=0.0, le=1.0)
    llm_max_tokens: int = 8192  # room for the answer (reasoning models also "think" inside this)
    llm_reasoning_effort: Literal["low", "medium", "high"] = "low"  # how long the model thinks

    # ---------- Embeddings (runs locally) ----------
    embedding_model: str = "BAAI/bge-small-en-v1.5"

    # ---------- Database ----------
    # Local: a SQLite file. Server: postgresql+psycopg://user:pass@host/db
    database_url: str = f"sqlite:///{PROJECT_ROOT / 'storage' / 'app.db'}"

    # ---------- API ----------
    environment: Literal["dev", "prod"] = "dev"
    # Signs login tokens. MUST be set in prod. See .env.example for how to make one.
    jwt_secret: SecretStr | None = None
    jwt_expire_minutes: int = 60 * 24  # 1 day

    # ---------- Limits (protect the free Groq quota) ----------
    max_active_jobs_per_user: int = 2  # queued + running at the same time
    max_jobs_per_day: int = 20  # per user, per 24 hours
    max_login_attempts: int = 10  # per IP address, per 5 minutes

    # ---------- Server ----------
    log_level: str = "INFO"
    # Websites allowed to call this API from a browser (the future frontend), comma separated.
    # Example: https://resume.example.com,http://localhost:3000
    cors_origins: str = ""


@lru_cache
def get_settings() -> Settings:
    """Create the settings once, then reuse the same object everywhere."""
    return Settings()
