"""Authentication endpoints — register, login, refresh, me (Task 1.9.1)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_session
from app.models.auth_schemas import LoginIn, RefreshIn, RegisterIn, TokenPair, UserRead
from app.models.user import User
from app.services import auth_service

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register", response_model=TokenPair, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterIn, session: AsyncSession = Depends(get_session)) -> TokenPair:
    user = await auth_service.register_user(session, email=body.email, password=body.password)
    return auth_service.issue_token_pair(user)


@router.post("/login", response_model=TokenPair)
async def login(body: LoginIn, session: AsyncSession = Depends(get_session)) -> TokenPair:
    user = await auth_service.authenticate_user(session, email=body.email, password=body.password)
    return auth_service.issue_token_pair(user)


@router.post("/refresh", response_model=TokenPair)
async def refresh(body: RefreshIn, session: AsyncSession = Depends(get_session)) -> TokenPair:
    return await auth_service.refresh_token_pair(session, refresh_token=body.refresh_token)


@router.get("/me", response_model=UserRead)
async def me(current: User = Depends(get_current_user)) -> User:
    return current
