import groq
import httpx

from api.errors import llm_error_message


def rate_limit(message: str) -> groq.RateLimitError:
    request = httpx.Request("POST", "https://api.groq.com/x")
    return groq.RateLimitError(message, response=httpx.Response(429, request=request), body=None)


def test_daily_limit_says_how_long_to_wait():
    status, message = llm_error_message(
        rate_limit("Rate limit reached on tokens per day (TPD). Please try again in 15m17.5s.")
    )
    assert status == 429
    assert "daily" in message and "16 minutes" in message


def test_hours_are_rounded():
    _, message = llm_error_message(rate_limit("tokens per day. Please try again in 2h3m4.5s."))
    assert "2 hours" in message


def test_short_limit_asks_to_wait_a_minute():
    _, message = llm_error_message(rate_limit("tokens per minute. Please try again in 6.2s."))
    assert "busy" in message and "1 minute" in message
