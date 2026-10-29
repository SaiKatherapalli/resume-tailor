"""
Database tables. One class = one table, one attribute = one column.

  users         who can log in
  career_banks  each user's career facts (the CareerBank as JSON)
  tailor_jobs   each "tailor my resume to this job" request and its result
"""

import uuid
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from api.db import Base


def now() -> datetime:
    return datetime.now(UTC)


def new_id() -> str:
    return uuid.uuid4().hex  # random ids: users can't guess other users' ids


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))  # never the real password
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CareerBankRecord(Base):
    __tablename__ = "career_banks"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    data: Mapped[dict] = mapped_column(JSON)  # CareerBank.model_dump()
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class TailorJob(Base):
    """Tailoring takes 20-60 seconds, so it runs in the background and the user checks the status."""

    __tablename__ = "tailor_jobs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(16), default=JobStatus.QUEUED)
    job_description: Mapped[str] = mapped_column(Text)
    result: Mapped[dict | None] = mapped_column(JSON, default=None)  # resume + validation report
    tex: Mapped[str | None] = mapped_column(Text, default=None)
    error: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    @property
    def job_title(self) -> str | None:
        """Role name from the analysis, for the job list. None until the job is done."""
        return ((self.result or {}).get("analysis") or {}).get("job_title") or None

    @property
    def company(self) -> str | None:
        return ((self.result or {}).get("analysis") or {}).get("company") or None

    @property
    def job_number(self) -> str | None:
        """The posting's own job ID (e.g. Amazon's 'Job ID'), to tell apart two postings of one role."""
        return ((self.result or {}).get("analysis") or {}).get("job_number") or None
