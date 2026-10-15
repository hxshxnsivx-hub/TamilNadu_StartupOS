# 0001. Two lanes: a fast conversation and a slow council

**Status:** Accepted · **Date:** 2026-10-08

## Context

A voice conversation needs the first word within about a second. Judging an idea well, by
searching prior art and weighing it from several angles, takes several seconds or more.

## Decision

Split the work. The **fast lane** answers every turn from what the session already knows. The
**slow lane** (evidence search, and later the advocate council) runs in the background at key
moments and writes its results to the session; the fast lane brings them in on a later turn.

## Options considered

- **One agent that does everything per turn:** simplest, but 5–60 seconds of silence per turn.
- **Council on every turn:** best judgement, unusable latency and cost.

## Consequences

- The founder is never kept waiting for analysis.
- Results must be tagged with the idea version they were made for, so a verdict on an earlier
  version of the idea is never spoken.
- More moving parts: the session state is the single place both lanes read and write.
