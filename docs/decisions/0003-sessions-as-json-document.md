# 0003. A conversation is saved as one JSON document

**Status:** Accepted · **Date:** 2026-10-09

## Context

Conversations lived only in server memory and were lost on restart. They must be saved, read
back quickly on every turn, and protected against two writers overwriting each other.

## Decision

Table `agent_sessions` (migration `0004_agent_sessions`): one row per conversation with the
session ID, user, a `version` number, the idea version, the privacy flag, last activity, and the
whole session as JSON. A save carries the version it loaded and is refused if the row moved on
(`VersionConflict`, returned to the client as 409). `AGENT_STORE=auto` uses the database when it
answers and the table exists, otherwise memory with a warning; the start response reports
`saved: true|false`.

## Options considered

- **Normalised tables from the start** (turns, facts, evidence, verdicts): easy to query, but
  every turn becomes many writes, and the shape is still changing.
- **Redis only:** fast, but a cache must never be the only copy of founder data.

## Consequences

- One read and one write per turn.
- Querying inside sessions (cohort analysis, Phase 5) needs a later migration that splits the
  document into tables.
- The document carries enum values as text; they are restored to enum members on load.
