"""
FastAPI dependencies: small functions FastAPI runs BEFORE an endpoint, and passes the result in.

    def my_endpoint(user: CurrentUser, db: DB): ...

  DB          -> a database session
  CurrentUser -> the logged-in user (or 401 if the token is missing / wrong)
  GroqKey     -> the user's own Groq key from the X-Groq-Api-Key header, or None
"""

from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from api.db import get_db
from api.models import User
from api.security import read_access_token

# Reads "Authorization: Bearer <token>". tokenUrl makes the "Authorize" button work in /docs.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

DB = Annotated[Session, Depends(get_db)]


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db: DB) -> User:
    user_id = read_access_token(token)
    user = db.get(User, user_id) if user_id else None
    if user is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid or expired token. Log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_groq_key(
    x_groq_api_key: Annotated[str | None, Header(description="Optional: your own Groq API key")] = None,
) -> str | None:
    """BYOK (bring your own key): a user can send their own free Groq key.
    Then their usage counts against their own rate limit, not the server's.
    The key is only used for this request and never stored."""
    return x_groq_api_key.strip() if x_groq_api_key and x_groq_api_key.strip() else None


GroqKey = Annotated[str | None, Depends(get_groq_key)]
