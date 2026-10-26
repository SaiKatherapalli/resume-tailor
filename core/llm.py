"""
The only file that knows which LLM provider we use (Groq).

Other files ask for "an LLM that fills this Pydantic model" and never deal with
API keys, model names or provider SDKs.
"""

from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import Runnable
from langchain_groq import ChatGroq
from pydantic import BaseModel

from core.config import get_settings


class LLMNotConfiguredError(RuntimeError):
    """Raised when no API key is available."""


def get_chat_model(api_key: str | None = None) -> BaseChatModel:
    """
    Create a Groq chat model.

    api_key: a user's own key (later, in the API). If not given, the key from .env is used.
    """
    settings = get_settings()
    key = api_key or (settings.groq_api_key.get_secret_value() if settings.groq_api_key else None)
    if not key:
        raise LLMNotConfiguredError("GROQ_API_KEY is not set. Add it to your .env file.")

    return ChatGroq(
        model=settings.groq_model,
        api_key=key,
        temperature=settings.llm_temperature,
        max_retries=3,  # retry automatically on rate limits / temporary errors
        timeout=60,  # seconds; never wait forever
    )


def get_structured_llm(schema: type[BaseModel], api_key: str | None = None) -> Runnable:
    """An LLM that answers by filling `schema` and returns a validated Pydantic object."""
    return get_chat_model(api_key).with_structured_output(schema)
