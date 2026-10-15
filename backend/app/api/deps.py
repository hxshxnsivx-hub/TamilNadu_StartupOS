"""Shared FastAPI dependencies (current-user resolution, etc.)."""

from __future__ import annotations

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.security import decode_token
from app.db.session import get_session
from app.models.user import User

# tokenUrl documents the login endpoint for Swagger's "Authorize" button.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session),
) -> User:
    if not token:
        raise AppError("NOT_AUTHENTICATED", "Authentication required", status_code=401)
    payload = decode_token(token, expected_type="access")
    user = await session.get(User, payload["sub"])
    if user is None:
        raise AppError("USER_NOT_FOUND", "Account no longer exists", status_code=401)
    if not user.is_active:
        raise AppError("ACCOUNT_DISABLED", "This account is disabled", status_code=403)
    return user
