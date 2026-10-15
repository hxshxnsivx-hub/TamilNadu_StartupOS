"""Password hashing and JWT token creation/verification (Task 1.9.1 · auth).

Access and refresh tokens are HS256 JWTs carrying a ``type`` claim so a refresh
token can never be used as an access token. All decode failures surface as an
``AppError`` with a stable code, so the API returns the standard error envelope.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings
from app.core.errors import AppError

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
_ALGO = "HS256"

TokenType = Literal["access", "refresh"]


# ── passwords ─────────────────────────────────────────────────────────────
def hash_password(plain: str) -> str:
    return _pwd.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd.verify(plain, hashed)


# ── tokens ────────────────────────────────────────────────────────────────
def _create_token(subject: str, token_type: TokenType, expires_delta: timedelta) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, get_settings().secret_key, algorithm=_ALGO)


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    s = get_settings()
    return _create_token(
        subject, "access", expires_delta or timedelta(minutes=s.access_token_expire_minutes)
    )


def create_refresh_token(subject: str, expires_delta: timedelta | None = None) -> str:
    s = get_settings()
    return _create_token(
        subject, "refresh", expires_delta or timedelta(days=s.refresh_token_expire_days)
    )


def decode_token(token: str, *, expected_type: TokenType | None = None) -> dict[str, Any]:
    """Decode and validate a JWT; raise AppError(401) on any problem."""
    try:
        payload = jwt.decode(token, get_settings().secret_key, algorithms=[_ALGO])
    except jwt.ExpiredSignatureError as exc:  # type: ignore[attr-defined]
        raise AppError(
            "TOKEN_EXPIRED",
            "Your session has expired",
            status_code=401,
            suggestions=["Sign in again", "Use your refresh token to obtain a new access token"],
        ) from exc
    except JWTError as exc:
        raise AppError("INVALID_TOKEN", "Invalid authentication token", status_code=401) from exc

    if expected_type is not None and payload.get("type") != expected_type:
        raise AppError(
            "WRONG_TOKEN_TYPE",
            f"Expected a {expected_type} token",
            status_code=401,
        )
    return payload
