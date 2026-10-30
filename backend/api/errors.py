"""
Turn LLM errors into clear API answers, instead of a generic "500 Internal Server Error".
"""

import re

import groq
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from core.llm import LLMNotConfiguredError

_OWN_KEY = " Or add your own Groq key under 'Use your own Groq key' on the Tailor page."


def _round_wait(text: str) -> str:
    """Groq says '15m17.568s' or '2h3m4.5s'. Keep it short: '16 minutes', '2 hours'."""
    hours = int(m.group(1)) if (m := re.search(r"(\d+)h", text)) else 0
    minutes = int(m.group(1)) if (m := re.search(r"(\d+)m", text)) else 0
    seconds = float(m.group(1)) if (m := re.search(r"([\d.]+)s", text)) else 0.0
    if hours:
        return f"{hours + (minutes >= 30)} hour{'s' if hours + (minutes >= 30) != 1 else ''}"
    total = minutes + (seconds > 0)
    return f"{max(total, 1)} minute{'s' if total != 1 else ''}"


def llm_error_message(e: Exception) -> tuple[int, str]:
    """(HTTP status, safe message for the user). Also used for background job errors."""
    if isinstance(e, LLMNotConfiguredError):
        return 503, "The server has no Groq API key. Send your own in the X-Groq-Api-Key header."
    if isinstance(e, groq.AuthenticationError):
        return 401, "The Groq API key is invalid."
    if isinstance(e, groq.RateLimitError):
        text = str(e)
        wait = re.search(r"try again in ([0-9hms.]+)", text)
        when = f" Try again in about {_round_wait(wait.group(1))}." if wait else ""
        if "per day" in text:
            return 429, f"The free daily AI limit is used up.{when}{_OWN_KEY}"
        return 429, f"The AI is busy right now.{when or ' Wait a minute.'}{_OWN_KEY}"
    if isinstance(e, groq.APIError):
        return 502, "The LLM service failed. Please try again."
    return 500, "Something went wrong. Please try again."


def add_error_handlers(app: FastAPI) -> None:
    async def handle(request: Request, e: Exception) -> JSONResponse:
        code, message = llm_error_message(e)
        return JSONResponse(status_code=code, content={"detail": message})

    app.add_exception_handler(LLMNotConfiguredError, handle)
    app.add_exception_handler(groq.APIError, handle)
