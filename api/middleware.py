"""
Things that run around EVERY request.

  - Logging: one line per request:  method, path, status, time, request id
  - Request id: a short id per request, sent back in the X-Request-ID header.
    When a user reports a problem, the id finds the exact log lines.
  - Login rate limit: stops password guessing.

We never log request bodies: they contain resumes and passwords.
"""

import logging
import re
import time
import uuid
from collections import defaultdict, deque

from fastapi import FastAPI, HTTPException, Request, status

log = logging.getLogger("api.requests")
_SAFE_ID = re.compile(r"^[A-Za-z0-9-]{1,64}$")  # a client-sent id must not inject text into our logs


def setup_logging(level: str) -> None:
    logging.basicConfig(level=level.upper(), format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def add_request_logging(app: FastAPI) -> None:
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", "")
        if not _SAFE_ID.match(request_id):
            request_id = uuid.uuid4().hex[:12]
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            log.exception("%s %s failed [%s]", request.method, request.url.path, request_id)
            raise
        ms = (time.perf_counter() - start) * 1000
        log.info(
            "%s %s %s %.0fms [%s]", request.method, request.url.path, response.status_code, ms, request_id
        )
        response.headers["X-Request-ID"] = request_id
        return response


class RateLimiter:
    """
    At most `limit` hits per key in `window` seconds (key = IP address).

    Kept in memory: fine for ONE server process. With several servers,
    use a shared store like Redis so they all see the same counts.
    """

    def __init__(self, limit: int, window: float):
        self.limit, self.window = limit, window
        self.hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str) -> None:
        now = time.monotonic()
        hits = self.hits[key]
        while hits and hits[0] <= now - self.window:  # forget old hits
            hits.popleft()
        if len(hits) >= self.limit:
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS, "Too many attempts. Try again in a few minutes."
            )
        hits.append(now)
