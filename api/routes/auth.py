"""Register, log in, and "who am I"."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from api.deps import DB, CurrentUser
from api.models import User
from api.schemas import RegisterIn, TokenOut, UserOut
from api.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(body: RegisterIn, db: DB) -> UserOut:
    user = User(email=body.email, password_hash=hash_password(body.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:  # the email column is unique
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "This email is already registered.") from None
    db.refresh(user)
    return UserOut.model_validate(user)


@router.post("/login")
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], db: DB) -> TokenOut:
    """Standard OAuth2 form: 'username' (= email) and 'password'."""
    user = db.scalar(select(User).where(User.email == form.username.strip().lower()))
    if not verify_password(form.password, user.password_hash if user else None):
        # Same message for "no such user" and "wrong password": don't tell attackers which one
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong email or password.")
    return TokenOut(access_token=create_access_token(user.id))


@router.get("/me")
def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)
