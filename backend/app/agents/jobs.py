"""Background work for a conversation: the slow lane (IDEATION-PIPELINE-DESIGN.md §1).

The prior-art search, the novelty check and the review panel take seconds to
tens of seconds; a spoken turn should not. Each runs as a job, and the turn
waits for it only briefly:

    finished in time (cached search, rule seats)  ->  the turn uses it now, as before
    still running                                 ->  the mentor says it is looking,
                                                      asks its question, and the
                                                      result enters a later turn

A job works on a snapshot (idea text, known facts, privacy), never on the live
session, so it cannot collide with a turn saving the session. Its latest result
is kept by session and kind; the next turn takes it in. The search runs once
per conversation, as before; the panel runs again when asked.

Listeners (the Talk screen) get a notice when a job finishes, so the panels
fill in before the next turn.

Jobs run in this process (asyncio tasks): enough for one server. A Redis
queue with separate workers is the step after this (SYSTEM-DESIGN.md §7).
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.agents.results import MemoryResults
from app.core.logging import get_logger

log = get_logger("jobs")

KINDS = ("research", "council")
DONE, RUNNING, FAILED = "done", "running", "failed"
LATEST = "latest"


@dataclass
class Job:
    session_id: str
    kind: str
    task: asyncio.Task
    started: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def state(self) -> str:
        if not self.task.done():
            return RUNNING
        return FAILED if self.task.cancelled() or self.task.exception() else DONE


class Board:
    def __init__(self) -> None:
        self.jobs: dict[tuple[str, str], Job] = {}  # (session, kind) -> the latest job
        self.results = MemoryResults()
        self.listeners: dict[str, set[asyncio.Queue]] = {}

    def start(
        self,
        session_id: str,
        kind: str,
        work: Callable[[], Awaitable[dict]],
        reuse_done: bool = False,
    ) -> Job:
        """Start `work`, unless a job of this kind is already running for the session
        (or, with `reuse_done`, has already finished): that job is returned instead."""
        current = self.jobs.get((session_id, kind))
        if current and (current.state == RUNNING or (reuse_done and current.state == DONE)):
            return current

        async def run() -> dict:
            payload = await work()
            await self.results.put(session_id, LATEST, kind, payload)
            self.notify(session_id, kind, payload)
            return payload

        task = asyncio.get_running_loop().create_task(run(), name=f"{kind}:{session_id}")
        task.add_done_callback(lambda t: _log_failure(t, kind))
        job = Job(session_id, kind, task)
        self.jobs[(session_id, kind)] = job
        log.info("job.started", kind=kind, session=session_id)
        return job

    async def wait(self, job: Job, seconds: float) -> bool:
        """True when the job finished (successfully) within `seconds`."""
        if job.state == RUNNING:
            await asyncio.wait({job.task}, timeout=seconds)
        return job.state == DONE

    def running(self, session_id: str, kind: str) -> Job | None:
        job = self.jobs.get((session_id, kind))
        return job if job and job.state == RUNNING else None

    async def take(self, session_id: str, kind: str) -> dict | None:
        """The latest finished result of this kind, if there is one."""
        return await self.results.get(session_id, LATEST, kind)

    # ---- notices for the screen ------------------------------------------------

    def subscribe(self, session_id: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=20)
        self.listeners.setdefault(session_id, set()).add(q)
        return q

    def unsubscribe(self, session_id: str, q: asyncio.Queue) -> None:
        self.listeners.get(session_id, set()).discard(q)

    def notify(self, session_id: str, kind: str, payload: Any) -> None:
        for q in list(self.listeners.get(session_id, ())):
            if not q.full():
                q.put_nowait({"kind": kind, "payload": payload})

    async def forget(self, session_id: str) -> None:
        """The conversation was deleted: stop its jobs and drop its results."""
        for kind in KINDS:
            job = self.jobs.pop((session_id, kind), None)
            if job and job.state == RUNNING:
                job.task.cancel()
        await self.results.delete_session(session_id)
        self.listeners.pop(session_id, None)


def _log_failure(task: asyncio.Task, kind: str) -> None:
    if not task.cancelled() and (exc := task.exception()):
        log.warning("job.failed", kind=kind, error=type(exc).__name__)


board = Board()
