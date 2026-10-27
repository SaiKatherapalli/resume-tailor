"""
Database connection.

  engine  = the connection pool to the database (one per app)
  Session = one "conversation" with the database (one per request)
"""

from collections.abc import Iterator
from pathlib import Path

from fastapi import Request
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session


class Base(DeclarativeBase):
    """Every table class inherits from this."""


def make_engine(url: str) -> Engine:
    connect_args = {}
    if url.startswith("sqlite:///"):
        Path(url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
        connect_args = {"check_same_thread": False}  # FastAPI uses several threads
    return create_engine(url, connect_args=connect_args, pool_pre_ping=True)


def get_db(request: Request) -> Iterator[Session]:
    """FastAPI dependency: open a session for one request, always close it after."""
    with Session(request.app.state.engine) as session:
        yield session
