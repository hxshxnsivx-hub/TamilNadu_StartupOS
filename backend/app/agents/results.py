"""Results of background work, kept apart from the conversation document.

Evidence, novelty and council results are written by jobs while the founder
keeps talking. Storing them in their own rows, keyed by session, idea version
and kind, means a job never collides with a turn saving the session (no
version conflicts), and a resumed session finds the results for its idea.

    kind: "research" (the scan and the novelty check) | "council"

Kept in memory for now. A database table (one row per session, idea version
and kind) comes with the database being reachable; the interface stays.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Protocol

KINDS = ("research", "council")


class ResultStore(Protocol):
    name: str

    async def put(self, session_id: str, idea_version: str, kind: str, payload: dict) -> None: ...

    async def get(self, session_id: str, idea_version: str, kind: str) -> dict | None: ...

    async def latest(self, session_id: str, kind: str) -> tuple[str, dict] | None: ...

    async def delete_session(self, session_id: str) -> None: ...


class MemoryResults:
    name = "memory"

    def __init__(self) -> None:
        self._rows: dict[tuple[str, str, str], tuple[datetime, str]] = {}

    async def put(self, session_id: str, idea_version: str, kind: str, payload: dict) -> None:
        self._rows[(session_id, idea_version, kind)] = (
            datetime.now(UTC),
            json.dumps(payload, default=str),
        )

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
        for key in [k for k in self._rows if k[0] == session_id]:
            del self._rows[key]
