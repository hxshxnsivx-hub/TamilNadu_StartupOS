# 0010. Slow work runs as background jobs; a turn waits for it only briefly

**Status:** Accepted · **Date:** 2026-10-14 · Supersedes 0007 in part

## Context

The prior-art search can take 20 seconds or more on a new idea, and a review panel on a free
model is seven calls. Inside a spoken turn that is long silence. The design always meant these
to be the slow lane (decision 0001), but until now they ran inside the turn (decision 0007).

## Decision

- **A job board** (`app/agents/jobs.py`) runs the research (search and novelty check) and the
  review panel as asyncio tasks in the server process. A job works on a snapshot of the session,
  never on the session itself, so it cannot collide with a turn saving it. One job of a kind runs
  per session at a time; the search runs once per conversation, as before.
- **A short wait, not a new behaviour:** a turn waits for research up to `RESEARCH_WAIT_S`
  (3 s), for the panel after research up to `COUNCIL_WAIT_S` (1.5 s), and for the panel the
  founder asked for, or the roadmap needs, up to `OPINION_WAIT_S` (12 s). Work that finishes
  in time (a cached search, rule seats) is used in the turn exactly as before.
- **Otherwise the mentor says so once and moves on:** "Let me look up what already exists for
  this; I will tell you what I find." and the question; or "The review panel is still looking
  at it". Every turn starts by taking in work that has finished since; the first reply after
  it leads with the finding. A model is told what is new and not to run those tools again.
- **The screen hears first:** `GET /ideation/agent/sessions/{id}/notices` streams `evidence`,
  `novelty` and `council` the moment a job finishes; the Talk page fills its panels from it.
- **Deleting a conversation** cancels its jobs and drops their results.
- **Update 2026-10-21 (task 1.2.3):** jobs and results are kept by session, research key and
  kind. The research key is a hash of what the search would send (public terms, queries,
  registry domain, the public words of who it is for, the health signals, private mode), so the
  search runs again only when that changes, not on every new slot; a job for older inputs is
  cancelled, and its result, if it lands, is never read or spoken.

## Options considered

- **A Redis queue with separate workers** (SYSTEM-DESIGN.md §7): needed for several servers;
  not needed for one, and Redis is optional here. The board's interface is kept small so a
  queue can replace it.
- **Always reply first, research later:** a cached search would then also be delayed by a turn.

## Consequences

- Jobs live in the server process: a restart loses running jobs (the next turn starts the
  search again) and results that no turn took in yet. Several server processes would each have
  their own board; the database-backed result store and the queue come with that.
- A model's own `scan_prior_art` call goes through the same board (added 2026-10-14): if the
  search outlasts the wait, the tool answers "still running", the model says it is looking and
  asks its question, and the next turn tells it the results have arrived.
