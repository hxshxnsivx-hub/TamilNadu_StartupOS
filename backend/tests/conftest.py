"""Shared test fixtures."""

import httpx
import pytest
import pytest_asyncio
from app.core.redis import set_redis
from app.main import create_app
from app.research import sources


@pytest.fixture(autouse=True)
def _isolated_limits():
    """No Redis unless a test brings its own; no pause or count leaks between tests."""
    set_redis(None)
    sources._local_pause.clear()
    sources._local_count.clear()
    yield
    sources._local_pause.clear()
    sources._local_count.clear()


@pytest_asyncio.fixture
async def client():
    """Async HTTP client bound to the ASGI app (no live server or DB needed)."""
    app = create_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
