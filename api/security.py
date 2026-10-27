"""
Passwords and login tokens.

Password: we store only a HASH (argon2). A hash can be checked, but not turned back into the password.
Token (JWT): after login the user gets a signed token: {"sub": user_id, "exp": time}.
  The user sends it with every request. We check the signature, so nobody can fake one.
"""

import secrets
from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash

from core.config import get_settings

ALGORITHM = "HS256"

_hasher = PasswordHash.recommended()  # argon2
_DUMMY_HASH = _hasher.hash("dummy-password-for-timing")
_DEV_SECRET = secrets.token_urlsafe(32)  # dev only: new on every restart, so old tokens stop working


def _secret() -> str:
    s = get_settings().jwt_secret
    return s.get_secret_value() if s else _DEV_SECRET


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    """If the user doesn't exist we still check a dummy hash, so the answer takes the same time.
    Otherwise attackers could learn which emails are registered by measuring the time."""
    if password_hash is None:
        _hasher.verify(password, _DUMMY_HASH)
        return False
    return _hasher.verify(password, password_hash)


def create_access_token(user_id: str) -> str:
    now = datetime.now(UTC)
    payload = {"sub": user_id, "iat": now, "exp": now + timedelta(minutes=get_settings().jwt_expire_minutes)}
    return jwt.encode(payload, _secret(), algorithm=ALGORITHM)


def read_access_token(token: str) -> str | None:
    """Return the user id, or None if the token is fake, broken or expired."""
    try:
        return jwt.decode(token, _secret(), algorithms=[ALGORITHM])["sub"]
    except (jwt.PyJWTError, KeyError):
        return None
