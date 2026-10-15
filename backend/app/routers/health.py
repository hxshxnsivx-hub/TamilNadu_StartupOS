"""Health & readiness endpoints."""

from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(tags=["system"])


@router.get("/health")
async def health() -> dict:
    """Liveness probe — always cheap, no external calls."""
    settings = get_settings()
    return {"status": "ok", "app": settings.app_name, "env": settings.app_env}


@router.get("/api/v1/version")
async def version() -> dict:
    """Deployed version marker."""
    return {"name": "vanigam-backend", "version": "0.1.0", "api": "v1"}
