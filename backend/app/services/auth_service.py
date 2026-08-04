"""Authentication business logic — registration, login, token issuance/refresh."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.auth_schemas import TokenPair
from app.models.user import User


async def register_user(session: AsyncSession, *, email: str, password: str) -> User:
    email = email.lower().strip()
    existing = await session.scalar(select(User).where(User.email == email))
    if existing is not None:
        raise AppError(
            "EMAIL_TAKEN",
            "An account with this email already exists",
            status_code=409,
            suggestions=["Sign in instead", "Use a different email address"],
        )
    user = User(email=email, hashed_password=hash_password(password))
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def authenticate_user(session: AsyncSession, *, email: str, password: str) -> User:
    email = email.lower().strip()
    user = await session.scalar(select(User).where(User.email == email))
    # Verify even when the user is missing to avoid leaking which emails exist.
    if user is None or not verify_password(password, user.hashed_password):
        raise AppError("INVALID_CREDENTIALS", "Incorrect email or password", status_code=401)
    if not user.is_active:
        raise AppError("ACCOUNT_DISABLED", "This account is disabled", status_code=403)
    return user


def issue_token_pair(user: User) -> TokenPair:
    subject = str(user.user_id)
    return TokenPair(
        access_token=create_access_token(subject),
        refresh_token=create_refresh_token(subject),
    )


async def refresh_token_pair(session: AsyncSession, *, refresh_token: str) -> TokenPair:
    payload = decode_token(refresh_token, expected_type="refresh")
    user = await session.get(User, payload["sub"])
    if user is None or not user.is_active:
        raise AppError("INVALID_TOKEN", "Token subject is no longer valid", status_code=401)
    return issue_token_pair(user)
