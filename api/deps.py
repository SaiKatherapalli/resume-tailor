"""
FastAPI dependencies: small functions FastAPI runs BEFORE an endpoint, and passes the result in.

    def my_endpoint(user: CurrentUser, db: DB): ...

  DB          -> a database session
  CurrentUser -> the logged-in user (or 401 if the token is missing / wrong)
"""

from typing import Annotated

from fastapi import Depends, HTTPException, status
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
