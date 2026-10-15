# 0005. Fact check every model sentence before it is spoken

**Status:** Accepted · **Date:** 2026-10-09

## Context

A model can state a number, scheme or trial that no source in the session supports, and can
call an idea "unique". Spoken aloud, such a claim is hard for a founder to check.

## Decision

The reply streams sentence by sentence; each sentence the model wrote passes `gate()` in
`app/agents/grounding.py` before it is sent. A sentence is dropped if it has a number, scheme or
trial ID that does not appear in the session (tool results, what the founder said, known facts,
the objective, the roadmap). Novelty words are replaced, once, by the standard caveat. If every
sentence is dropped, the engine's question is asked on its own. Templated text is built from the
session by code and is not re-checked.

Allowances: bare counts up to 12 pass; scheme acronyms match only in capitals (NEEDS the scheme,
not "needs" the verb).

## Options considered

- **A second model checks the reply:** catches more, adds a full model call to every turn.
- **Ask the model to cite:** it can cite wrongly.

## Consequences

- No model call on the voice path; well under a millisecond per sentence.
- It checks that figures exist in the session, not that they are used correctly: "23 papers"
  passes if 23 appears anywhere. Meaning-level checks are left to the council and evaluation.
- Dropped sentences are counted in each turn's `done` event and logged, for review.
