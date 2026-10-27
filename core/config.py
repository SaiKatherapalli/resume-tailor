"""
Application settings.

Values are read from environment variables, or from a `.env` file in the project root.
Example: the env variable GROQ_API_KEY fills the field `groq_api_key` (names are case-insensitive).
"""

from functools import lru_cache
from pathlib import Path

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

    # ---------- Embeddings (runs locally) ----------
    embedding_model: str = "BAAI/bge-small-en-v1.5"


@lru_cache
def get_settings() -> Settings:
    """Create the settings once, then reuse the same object everywhere."""
    return Settings()
