"""Integration tests for saved ideation conversations (PostgreSQL store).

Requires a reachable PostgreSQL; skipped automatically when there is none, so
the default unit run stays green without infrastructure.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from app.agents.ideation import new_session, turn
from app.agents.store import SqlStore, VersionConflict
from app.core.config import get_settings
from app.db.session import engine
from app.elicitation.slots import Sector
from app.models import Base
from sqlalchemy import text

pytestmark = pytest.mark.integration


@pytest_asyncio.fixture
async def store(monkeypatch):
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
            await conn.run_sync(Base.metadata.create_all)
    except Exception as exc:  # pragma: no cover - infra-dependent
        pytest.skip(f"database unavailable: {exc}")
    monkeypatch.setattr(get_settings(), "anthropic_api_key", "")
    yield SqlStore()


async def test_session_round_trip_and_version_guard(store, monkeypatch):
    from app.research import scan as research

    real_scan = research.scan

    async def private_scan(text, *, elements=None, queries=None, client=None, private=False):
        return await real_scan(text, client=client, private=True)

    monkeypatch.setattr(research, "scan", private_scan)
    from app.research import novelty

    real_novelty = novelty.check

    async def private_novelty(idea, **kw):
        return await real_novelty(idea, **{**kw, "private": True})

    monkeypatch.setattr(novelty, "check", private_novelty)
    s, _ = new_session("Kavya")
    await store.create(s)
    await turn(s, "textile finishing unit for weavers in Erode")
    await store.save(s)

    back = await store.get(s.id)
    assert back is not None and back.version == s.version
    assert back.elicitation.slots["sector"].value is Sector.TEXTILE
    assert back.pending_slot == s.pending_slot

    stale = await store.get(s.id)
    await store.save(back)
    with pytest.raises(VersionConflict):
        await store.save(stale)

    assert await store.delete(s.id)
    assert await store.get(s.id) is None
