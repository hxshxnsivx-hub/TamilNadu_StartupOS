"""Background work for a conversation: the slow lane (IDEATION-PIPELINE-DESIGN.md §1).

The prior-art search, the novelty check and the review panel take seconds to
tens of seconds; a spoken turn should not. Each runs as a job, and the turn
waits for it only briefly:

    finished in time (cached search, rule seats)  ->  the turn uses it now, as before
    still running                                 ->  the mentor says it is looking,
                                                      asks its question, and the
                                                      result enters a later turn

A job works on a snapshot (idea text, known facts, privacy), never on the live
session, so it cannot collide with a turn saving the session. Jobs and results
are kept by session, version and kind (R040): the version is the session's
research key, a hash of what the search would send (ideation.research_key), so
the board hands back a finished job only for the same inputs, a new version
never waits behind an old one, and a late result for an old version is stored
under its own key, where no turn reads it. Starting a new version cancels the
old version's running job of that kind (its results would never be used, and
the free search budget is small). The search runs again only when its inputs
change (R014); the panel runs again when asked.

Listeners (the Talk screen) get a notice when a job finishes, so the panels
fill in before the next turn.

A deleted conversation is forgotten: its jobs are cancelled, its results
dropped, and no job starts or stores results for it afterwards (R173). Finished
jobs are pruned after KEEP, like their results.

Jobs run in this process (asyncio tasks): enough for one server. A Redis
queue with separate workers is the step after this (SYSTEM-DESIGN.md §7).
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.agents.results import KEEP, MemoryResults
from app.core.logging import get_logger

log = get_logger("jobs")

KINDS = ("research", "council")
DONE, RUNNING, FAILED = "done", "running", "failed"
LATEST = "latest"
GONE = "gone"  # the notice that ends a deleted conversation's stream


@dataclass
class Job:
    session_id: str
    kind: str
    task: asyncio.Future
    version: str = LATEST
    started: datetime = field(default_factory=lambda: datetime.now(UTC))
    finished: datetime | None = None

    @property
    def state(self) -> str:
        if not self.task.done():
            return RUNNING
        return FAILED if self.task.cancelled() or self.task.exception() else DONE


class Board:
    def __init__(self) -> None:
        # (session, version, kind) -> the latest job for that version
        self.jobs: dict[tuple[str, str, str], Job] = {}
        self.current: dict[tuple[str, str], str] = {}  # (session, kind) -> newest version
        self.results = MemoryResults()
        self.listeners: dict[str, set[asyncio.Queue]] = {}

    def start(
        self,
        session_id: str,
        kind: str,
        work: Callable[[], Awaitable[dict]],
        reuse_done: bool = False,
        version: str = LATEST,
    ) -> Job:
        """Start `work` for this version, unless a job of this kind is already
        running for the session and version (or, with `reuse_done`, has already
        finished): that job is returned instead. A running job of another version
        is cancelled: it was for inputs the conversation has moved on from.

        For a deleted conversation nothing runs: the job returned has already
        failed, so a caller waiting on it carries on without a result."""
        loop = asyncio.get_running_loop()
        if self.results.forgotten(session_id):
            refused = loop.create_future()
            refused.cancel()
            return Job(session_id, kind, refused, version)
        self._prune()
        self.current[(session_id, kind)] = version
        current = self.jobs.get((session_id, version, kind))
        if current and (current.state == RUNNING or (reuse_done and current.state == DONE)):
            return current
        for (sid, v, k), old in list(self.jobs.items()):
            if sid == session_id and k == kind and v != version and old.state == RUNNING:
                old.task.cancel()
                log.info("job.superseded", kind=kind, session=session_id)

        async def run() -> dict:
            payload = await work()
            if not self.results.forgotten(session_id):
                await self.results.put(session_id, version, kind, payload)
                if self.current.get((session_id, kind)) == version:  # not a stale version
                    self.notify(session_id, kind, payload)
            return payload

        task = loop.create_task(run(), name=f"{kind}:{session_id}")
        job = Job(session_id, kind, task, version)
        task.add_done_callback(lambda t: _finished(job, t))
        self.jobs[(session_id, version, kind)] = job
        log.info("job.started", kind=kind, session=session_id)
        return job

    def _prune(self) -> None:
        """Drop jobs that finished more than KEEP ago (their results go too)."""
        now = datetime.now(UTC)
        old = [k for k, j in self.jobs.items() if j.finished and now - j.finished > KEEP]
        for key in old:
            del self.jobs[key]
        live = {sid for sid, _, _ in self.jobs}
        for key in [k for k in self.current if k[0] not in live]:
            del self.current[key]

    async def wait(self, job: Job, seconds: float) -> bool:
        """True when the job finished (successfully) within `seconds`."""
        if job.state == RUNNING:
            await asyncio.wait({job.task}, timeout=seconds)
        return job.state == DONE

    def running(self, session_id: str, kind: str, version: str = LATEST) -> Job | None:
        job = self.jobs.get((session_id, version, kind))
        return job if job and job.state == RUNNING else None

    def retire(self, session_id: str, version: str) -> None:
        """The session's inputs are now `version`, for every kind: running jobs of
        other versions are cancelled, and a result one of them still delivers is
        stored apart and never announced (the research key changed, task 1.2.3)."""
        if self.results.forgotten(session_id):
            return
        for kind in KINDS:
            self.current[(session_id, kind)] = version
        for (sid, v, k), job in list(self.jobs.items()):
            if sid == session_id and v != version and job.state == RUNNING:
                job.task.cancel()
                log.info("job.superseded", kind=k, session=session_id)

    def superseded(self, session_id: str, kind: str, version: str) -> bool:
        """A job of this kind is still running for another version of the session."""
        return any(
            sid == session_id and k == kind and v != version and j.state == RUNNING
            for (sid, v, k), j in self.jobs.items()
        )

    async def take(self, session_id: str, kind: str, version: str = LATEST) -> dict | None:
        """The finished result of this kind for this version, if there is one."""
        return await self.results.get(session_id, version, kind)

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
        """The conversation was deleted: stop its jobs, drop its results, refuse
        any later start or result for it, and end its notice streams."""
        await self.results.delete_session(session_id)  # first: refuses from here on
        for key in [k for k in self.jobs if k[0] == session_id]:
            job = self.jobs.pop(key)
            if job.state == RUNNING:
                job.task.cancel()
        for kind in KINDS:
            self.current.pop((session_id, kind), None)
        for q in self.listeners.pop(session_id, ()):
            if q.full():  # the end notice matters more than an old one
                q.get_nowait()
            q.put_nowait({"kind": GONE, "payload": None})


def _finished(job: Job, task: asyncio.Future) -> None:
    job.finished = datetime.now(UTC)
    if not task.cancelled() and (exc := task.exception()):
        log.warning("job.failed", kind=job.kind, error=type(exc).__name__)


board = Board()
