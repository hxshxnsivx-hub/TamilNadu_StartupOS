"""Results of background work, kept apart from the conversation document.

Evidence, novelty and council results are written by jobs while the founder
keeps talking. Storing them in their own rows, keyed by session, version (the
research key: what the search would send, ideation.research_key, task 1.2.3)
and kind, means a job never collides with a turn saving the session (no
version conflicts), and a resumed session finds the results for its idea.

    kind: "research" (the scan and the novelty check) | "council"

Kept in memory for now. A database table (one row per session, idea version
and kind) comes with the database being reachable; the interface stays, and so
do the two rules below (task 2.3.1 carries them into the table).

    expiry     a row not written for KEEP is dropped: by then its session is
               hidden too (store.IDLE_EXPIRY), so process memory stays bounded
    forgotten  a deleted session is remembered for KEEP, and a write for it is
               refused: work that was already running cannot bring its
               results back after the founder deleted it (R173)
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Protocol

KINDS = ("research", "council")
# as long as an idle session stays live (store.IDLE_EXPIRY; not imported, to keep
# this module free of the session code)
KEEP = timedelta(hours=6)


class ResultStore(Protocol):
    name: str

    async def put(self, session_id: str, idea_version: str, kind: str, payload: dict) -> None: ...

    async def get(self, session_id: str, idea_version: str, kind: str) -> dict | None: ...

    async def latest(self, session_id: str, kind: str) -> tuple[str, dict] | None: ...

    async def delete_session(self, session_id: str) -> None: ...

    def forgotten(self, session_id: str) -> bool: ...


class MemoryResults:
    name = "memory"

    def __init__(self) -> None:
        self._rows: dict[tuple[str, str, str], tuple[datetime, str]] = {}
        self._gone: dict[str, datetime] = {}  # deleted session -> when

    async def put(self, session_id: str, idea_version: str, kind: str, payload: dict) -> None:
        if self.forgotten(session_id):
            return  # deleted while the work ran: its results are not kept
        now = datetime.now(UTC)
        for key in [k for k, (at, _) in self._rows.items() if now - at > KEEP]:
            del self._rows[key]
        self._rows[(session_id, idea_version, kind)] = (now, json.dumps(payload, default=str))

    async def get(self, session_id: str, idea_version: str, kind: str) -> dict | None:
        row = self._rows.get((session_id, idea_version, kind))
        return json.loads(row[1]) if row else None

    async def latest(self, session_id: str, kind: str) -> tuple[str, dict] | None:
        rows = [(at, v, doc) for (s, v, k), (at, doc) in self._rows.items()
                if s == session_id and k == kind]  # fmt: skip
        if not rows:
            return None
        _, version, doc = max(rows)
        return version, json.loads(doc)

    async def delete_session(self, session_id: str) -> None:
        """Drop the session's results and refuse any written for it later."""
        self._gone[session_id] = datetime.now(UTC)
        for key in [k for k in self._rows if k[0] == session_id]:
            del self._rows[key]

    def forgotten(self, session_id: str) -> bool:
        now = datetime.now(UTC)
        for sid in [k for k, at in self._gone.items() if now - at > KEEP]:
            del self._gone[sid]
        return session_id in self._gone
