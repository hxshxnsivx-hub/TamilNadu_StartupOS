"""Shared test fixtures."""

import httpx
import pytest
import pytest_asyncio
from app.core.redis import set_redis
from app.main import create_app
from app.research import sources


@pytest.fixture(autouse=True)
def _no_free_models(monkeypatch):
    """No test reaches Gemini or the local Ollama unless it sets them up itself,
    whatever backend/.env holds; breakers start closed."""
    from app.agents.providers import PROVIDERS
    from app.core.config import get_settings

    st = get_settings()
    monkeypatch.setattr(st, "gemini_api_key", "")
    monkeypatch.setattr(st, "ollama_model", "")
    for p in PROVIDERS.values():
        p.breaker.succeed()


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
