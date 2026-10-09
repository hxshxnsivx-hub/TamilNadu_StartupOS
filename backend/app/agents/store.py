"""Where ideation conversations are kept (SYSTEM-DESIGN.md §2 class D, §4.3).

Two stores behind one interface, holding the same JSON document:

    MemoryStore  tests and offline development
    SqlStore     PostgreSQL, the source of truth in deployment

Both apply the same rules: a save carries the version it loaded and is refused
if the stored version moved on (no silent lost updates), and a session idle
for more than six hours is treated as gone.

AGENT_STORE picks one: "database", "memory", or "auto" (the database when it
answers and the table exists; otherwise memory, with a warning).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Protocol

from app.agents.ideation import AgentSession
from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger("agent_store")
IDLE_EXPIRY = timedelta(hours=6)


class VersionConflict(Exception):
    """Someone saved this session after it was loaded; reload and retry."""


class SessionStore(Protocol):
    name: str

    async def get(self, session_id: str) -> AgentSession | None: ...

    async def create(self, s: AgentSession) -> None: ...

    async def save(self, s: AgentSession) -> None: ...

    async def delete(self, session_id: str) -> bool: ...


def _expired(s: AgentSession) -> bool:
    return datetime.now(UTC) - s.updated_at > IDLE_EXPIRY


class MemoryStore:
    """Keeps serialised copies, so it behaves like the database (no shared objects)."""

    name = "memory"

    def __init__(self) -> None:
        self._docs: dict[str, str] = {}

    async def get(self, session_id: str) -> AgentSession | None:
        doc = self._docs.get(session_id)
        if doc is None:
            return None
        s = AgentSession.from_dict(json.loads(doc))
        return None if _expired(s) else s

    async def create(self, s: AgentSession) -> None:
        s.version = 1
        self._docs[s.id] = json.dumps(s.to_dict(), default=str)

    async def save(self, s: AgentSession) -> None:
        doc = self._docs.get(s.id)
        stored = json.loads(doc)["version"] if doc else 0
        if stored != s.version:
            raise VersionConflict(s.id)
        s.version += 1
        self._docs[s.id] = json.dumps(s.to_dict(), default=str)

    async def delete(self, session_id: str) -> bool:
        return self._docs.pop(session_id, None) is not None


class SqlStore:
    name = "database"

    async def get(self, session_id: str) -> AgentSession | None:
        from app.db.session import SessionLocal
        from app.models.agent_session import AgentSessionRow

        async with SessionLocal() as db:
            row = await db.get(AgentSessionRow, session_id)
            if row is None:
                return None
            s = AgentSession.from_dict({**row.data, "version": row.version})
            return None if _expired(s) else s

    async def create(self, s: AgentSession) -> None:
        from app.db.session import SessionLocal
        from app.models.agent_session import AgentSessionRow

        s.version = 1
        async with SessionLocal() as db:
            db.add(_row(AgentSessionRow, s))
            await db.commit()

    async def save(self, s: AgentSession) -> None:
        from sqlalchemy import update

        from app.db.session import SessionLocal
        from app.models.agent_session import AgentSessionRow

        doc = {**s.to_dict(), "version": s.version + 1}
        async with SessionLocal() as db:
            result = await db.execute(
                update(AgentSessionRow)
                .where(
                    AgentSessionRow.session_id == s.id,
                    AgentSessionRow.version == s.version,
                )
                .values(
                    version=s.version + 1,
                    idea_version=s.idea_version,
                    private=s.private,
                    last_active=s.updated_at,
                    data=json.loads(json.dumps(doc, default=str)),
                )
            )
            if result.rowcount != 1:
                await db.rollback()
                raise VersionConflict(s.id)
            await db.commit()
        s.version += 1

    async def delete(self, session_id: str) -> bool:
        from sqlalchemy import delete

        from app.db.session import SessionLocal
        from app.models.agent_session import AgentSessionRow

        async with SessionLocal() as db:
            result = await db.execute(
                delete(AgentSessionRow).where(AgentSessionRow.session_id == session_id)
            )
            await db.commit()
            return result.rowcount == 1


def _row(model, s: AgentSession):
    return model(
        session_id=s.id,
        user_id=s.user_id,
        version=s.version,
        idea_version=s.idea_version,
        private=s.private,
        last_active=s.updated_at,
        data=json.loads(json.dumps(s.to_dict(), default=str)),
    )


async def _database_ready() -> bool:
    from sqlalchemy import text

    from app.db.session import engine

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1 FROM agent_sessions LIMIT 1"))
        return True
    except Exception as exc:  # no database, or the migration has not been run
        log.warning("agent_store.database_unavailable", error=type(exc).__name__)
        return False


_store: SessionStore | None = None


async def get_store() -> SessionStore:
    global _store
    if _store is None:
        mode = get_settings().agent_store
        if mode == "memory":
            _store = MemoryStore()
        elif mode == "database":
            _store = SqlStore()
        else:
            _store = SqlStore() if await _database_ready() else MemoryStore()
        log.info("agent_store.selected", store=_store.name)
    return _store


def set_store(store: SessionStore | None) -> None:
    """Tests: use this store (None: choose again on next use)."""
    global _store
    _store = store
