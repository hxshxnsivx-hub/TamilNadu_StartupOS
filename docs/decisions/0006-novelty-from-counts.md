# 0006. Novelty is judged from search counts at three levels

**Status:** Accepted · **Date:** 2026-10-09

## Context

Founders ask whether their idea is new. A model asked directly will guess, and will often say
"unique". What Vanigam can actually observe is how much published work matches each part of an
idea, the parts together, and the idea in India.

## Decision

`app/research/novelty.py` counts OpenAlex works at three levels: each **element**, each
**pair** of elements, and the idea's two best-studied parts worldwide versus India-affiliated
(the **context**). Fixed thresholds turn counts into gaps: a part is active at 300 papers and
crowded at 5,000; a pair is rare when both parts are active, the pair has under 300 papers,
and it is under 2% of the smaller part or under 30 papers; India is under-represented below 5%
with no Tamil Nadu startup found. One statement is chosen (combination, context, element,
crowded, or unclear), and levers are offered only when a gap supports them, each with its
reason. Every statement carries the caveat that not found is not proof of novelty.

Without a model, the statement and up to three levers are spoken one per turn after the
evidence turn; with a model, it calls `check_novelty` and is told to do the same.

## Options considered

- **Ask the model whether the idea is novel:** fluent, unfounded, and inconsistent.
- **Embedding similarity to papers:** finds near neighbours, but gives no countable "rare
  combination" and needs an index of the literature.
- **Patent claim analysis:** the right test for patentability, but needs patent data Vanigam
  does not have yet (Indian patents are Phase 4) and an attorney's judgement.

## Consequences

- Cheap: one count request per part, pair and context, cached seven days. At most 6 parts,
  15 pairs.
- Counts depend on wording; a rare pair can be an artefact of terms. The statement shows the
  numbers so a founder can judge, and the thresholds are listed in every result.
- India-affiliated counts depend on affiliation data, which is incomplete; it is treated as a
  hint and paired with the Tamil Nadu startup check.
