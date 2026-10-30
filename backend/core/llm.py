"""
The only file that knows which LLM provider we use (Groq).

Other files ask for "an LLM that fills this Pydantic model" and never deal with
API keys, model names or provider SDKs.
"""

from langchain_core.exceptions import OutputParserException
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
        max_tokens=settings.llm_max_tokens,
        reasoning_effort=settings.llm_reasoning_effort,
        max_retries=3,  # retry automatically on rate limits / temporary errors
        timeout=60,  # seconds; never wait forever
    )


def get_structured_llm(schema: type[BaseModel], api_key: str | None = None) -> Runnable:
    """An LLM that answers by filling `schema` and returns a validated Pydantic object.

    method="json_schema": the model is forced to return JSON matching the schema.
    (The default "tool calling" method failed on big outputs: the model sometimes
    answered in plain text instead of calling the tool.)
    """
    structured = get_chat_model(api_key).with_structured_output(schema, method="json_schema")
    # Now and then the model answers with a copy of the schema instead of values. Just ask again.
    return structured.with_retry(retry_if_exception_type=(OutputParserException,), stop_after_attempt=3)
