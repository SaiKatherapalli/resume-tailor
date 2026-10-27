"""
Turn LLM errors into clear API answers, instead of a generic "500 Internal Server Error".
"""

import groq
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from core.llm import LLMNotConfiguredError


def llm_error_message(e: Exception) -> tuple[int, str]:
    """(HTTP status, safe message for the user). Also used for background job errors."""
    if isinstance(e, LLMNotConfiguredError):
        return 503, "The server has no Groq API key. Send your own in the X-Groq-Api-Key header."
    if isinstance(e, groq.AuthenticationError):
        return 401, "The Groq API key is invalid."
    if isinstance(e, groq.RateLimitError):
        return 429, "Groq rate limit reached. Wait a minute, or use your own key (X-Groq-Api-Key)."
    if isinstance(e, groq.APIError):
        return 502, "The LLM service failed. Please try again."
    return 500, "Something went wrong. Please try again."


def add_error_handlers(app: FastAPI) -> None:
    async def handle(request: Request, e: Exception) -> JSONResponse:
        code, message = llm_error_message(e)
        return JSONResponse(status_code=code, content={"detail": message})

    app.add_exception_handler(LLMNotConfiguredError, handle)
    app.add_exception_handler(groq.APIError, handle)
