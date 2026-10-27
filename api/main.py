"""
The FastAPI app.

Run:   uvicorn api.main:app --reload
Docs:  http://127.0.0.1:8000/docs   (FastAPI makes this page for free)
"""

from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from api import models  # noqa: F401  (import so the tables are registered on Base)
from api.db import Base, get_db, make_engine
from core.config import get_settings


def create_app(database_url: str | None = None) -> FastAPI:
    """Build the app. Tests pass their own database_url, so they never touch the real database."""
    engine = make_engine(database_url or get_settings().database_url)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Runs once at startup. Creates missing tables. (Step 21: Alembic migrations instead.)
        Base.metadata.create_all(engine)
        yield
        engine.dispose()  # runs once at shutdown

    app = FastAPI(title="Resume Tailor API", version="0.1.0", lifespan=lifespan)
    app.state.engine = engine

    @app.get("/health", tags=["system"])
    def health(db: Annotated[Session, Depends(get_db)]) -> dict:
        """Is the app up, and can it reach the database? Used by Docker and the server."""
        db.execute(text("SELECT 1"))
        return {"status": "ok"}

    return app


app = create_app()
