# 0007. The review panel meets inside the turn, at three moments, until background jobs exist

**Status:** Accepted · **Date:** 2026-10-10 · Superseded in part by [0010](0010-background-jobs-with-a-short-wait.md) (2026-10-14)

## Context

The design runs the seven-seat review panel in the background (decision 0001), but the
background job runner (Phase 2b) is not built. The panel still needs to reach the founder, its
question needs to reach the question engine, and its objections need to reach the roadmap.

## Decision

The panel meets inside a turn only where waiting is acceptable:

1. **The founder asks for a view** ("what do you think?", "will it work?"). They asked, so a
   few seconds is expected. If nothing changed since the last run, the reply says so in one line
   instead of repeating the brief, and the open question stays open.
2. **Right before the roadmap**, which the founder is already waiting for.
3. **Without a model, right after the novelty check**: rule-based seats take milliseconds.

With a model, Claude also has an `ask_council` tool. The panel's question becomes a dynamic
question in the question engine (asked after any re-asked question, at most three per session,
inside the limit of seven). Its cited objections raise the matching roadmap risks by one level
with the seat's reason; its cited blockers become gates listed before the roadmap.

Model seats run only while the model is allowed: a key is set, the circuit breaker is closed,
and the session is under `SESSION_TOKEN_BUDGET`. Otherwise the seats run on rules.

## Options considered

- **Wait for background jobs:** the panel would stay unused until then.
- **Run the panel on every turn:** seconds of delay and seven model calls per turn.

## Consequences

- With a model, an opinion request or the roadmap turn takes a few seconds longer.
- When background jobs exist, moments 1 and 2 can read a result that is already there.
