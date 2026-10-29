"""
Shapes of API requests and responses.

Separate from the database tables on purpose: the API never sends back
columns like password_hash by accident.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RegisterIn(BaseModel):
    email: str = Field(max_length=320, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email", mode="before")  # runs before the pattern check
    @classmethod
    def normalize_email(cls, v):
        # " Sai@Gmail.com" and "sai@gmail.com" are the same user
        return v.strip().lower() if isinstance(v, str) else v


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # can be built from a database row

    id: str
    email: str
    created_at: datetime


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class JobCreate(BaseModel):
    job_description: str = Field(min_length=50, max_length=20_000)


class JobLinkRequest(BaseModel):
    url: str = Field(min_length=4, max_length=2000)


class JobLinkOut(BaseModel):
    """The job read from a link. The user checks it, then sends it to POST /jobs as usual."""

    job_description: str
    job_title: str = ""
    company: str = ""


class JobSummary(BaseModel):
    """Short version for the list of jobs."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    status: str
    created_at: datetime
    finished_at: datetime | None
    job_title: str | None = None
    company: str | None = None
    job_number: str | None = None


class JobOut(JobSummary):
    """Full version: the result and error too."""

    job_description: str
    result: dict | None
    error: str | None
