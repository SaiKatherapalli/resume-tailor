"""
The FastAPI app.

Run:   uvicorn api.main:app --reload
Docs:  http://127.0.0.1:8000/docs   (FastAPI makes this page for free)
"""

from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from api import models  # noqa: F401  (import so the tables are registered on Base)
from api.db import Base, get_db, make_engine
from api.errors import add_error_handlers
from api.middleware import RateLimiter, add_request_logging, setup_logging
from api.routes import auth, career_bank, jobs
from api.worker import fail_interrupted_jobs
from core.config import get_settings


def create_app(database_url: str | None = None) -> FastAPI:
    """Build the app. Tests pass their own database_url, so they never touch the real database."""
    settings = get_settings()
    if settings.environment == "prod" and settings.jwt_secret is None:
        raise RuntimeError("JWT_SECRET must be set in prod.")
    setup_logging(settings.log_level)
    engine = make_engine(database_url or settings.database_url)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Runs once at startup.
        # dev: create missing tables right away. prod: tables come from `alembic upgrade head`.
        if settings.environment == "dev":
            Base.metadata.create_all(engine)
        fail_interrupted_jobs(engine)
        yield
        engine.dispose()  # runs once at shutdown

    app = FastAPI(title="Resume Tailor API", version="0.1.0", lifespan=lifespan)
    app.state.engine = engine
    app.state.login_limiter = RateLimiter(limit=settings.max_login_attempts, window=5 * 60)

    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    if origins:  # let the frontend's website call this API from the browser
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_methods=["*"],
            allow_headers=["Authorization", "Content-Type", "X-Groq-Api-Key", "X-Request-ID"],
            expose_headers=["X-Request-ID", "Content-Disposition"],
        )
    add_request_logging(app)
    add_error_handlers(app)
    app.include_router(auth.router)
    app.include_router(career_bank.router)
    app.include_router(jobs.router)

    @app.get("/health", tags=["system"])
    def health(db: Annotated[Session, Depends(get_db)]) -> dict:
        """Is the app up, and can it reach the database? Used by Docker and the server."""
        db.execute(text("SELECT 1"))
        return {"status": "ok"}

    return app


app = create_app()
