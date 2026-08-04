"""Shared test fixtures."""

import httpx
import pytest_asyncio
from app.main import create_app


@pytest_asyncio.fixture
async def client():
    """Async HTTP client bound to the ASGI app (no live server or DB needed)."""
    app = create_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
