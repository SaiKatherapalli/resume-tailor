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
