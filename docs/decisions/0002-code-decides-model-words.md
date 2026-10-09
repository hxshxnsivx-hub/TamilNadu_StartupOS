# 0002. Code decides; the model words

**Status:** Accepted · **Date:** 2026-10-08

## Context

A language model asked to run an ideation conversation will ask too many questions, repeat
ones already answered, and judge inconsistently from one session to the next.

## Decision

Deterministic code makes the decisions: which question to ask (`app/elicitation`), when to
stop, whether a reply answers the question, how votes combine, what the roadmap contains
(`app/planner`). The model phrases those decisions and judges within limits the code sets.

## Options considered

- **Let the model drive:** more flexible, but untestable and unpredictable.
- **No model at all:** fully predictable, but stiff, and blind to ideas outside the registry.

## Consequences

- The decisions are unit-tested like any other code.
- The product still works with no model key (the templated path).
- Ideas outside the fixed questions need dynamic questions from the scan and council (Phase 2).
