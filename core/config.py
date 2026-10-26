"""
Application settings.

Values are read from environment variables, or from a `.env` file in the project root.
Example: the env variable GROQ_API_KEY fills the field `groq_api_key` (names are case-insensitive).
"""

from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,  # `GROQ_API_KEY=` (empty) counts as "not set", not as ""
        extra="ignore",  # unknown variables in .env are ignored instead of causing an error
    )

    # ---------- LLM providers ----------
    # NoDecode: read "groq,gemini" as plain text; the validator below splits it into a list.
    llm_providers: Annotated[list[str], NoDecode] = ["groq", "gemini"]

    groq_api_key: SecretStr | None = None
    groq_model: str = "llama-3.3-70b-versatile"

    google_api_key: SecretStr | None = None
    gemini_model: str = "gemini-2.5-flash"

    llm_temperature: float = Field(default=0.2, ge=0.0, le=1.0)

    @field_validator("llm_providers", mode="before")
    @classmethod
    def split_comma_list(cls, value: object) -> object:
        if isinstance(value, str):
            return [p.strip().lower() for p in value.split(",") if p.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    """Create the settings once, then reuse the same object everywhere."""
    return Settings()
