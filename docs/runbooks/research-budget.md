# A research source's budget is used up

## How you notice

- A scan's coverage shows `budget_exhausted` for papers (OpenAlex) or projects (GitHub).
- The agent says "I could not search papers this time."
- The weekly job `build_domain_signals.py` stops with "OpenAlex daily budget used up", keeping
  the previous signals.

## Why it happens

Without a key, OpenAlex gives a small daily budget shared by everyone on the same network, and
GitHub limits unauthenticated searches. A large job (the weekly signals refresh, or many new
ideas in one day) can use it up. OpenAlex then answers 429 with a `Retry-After` of many hours.

## What to do

1. Add free keys to `backend/.env`: `OPENALEX_API_KEY`, `GITHUB_TOKEN`
   (and `PATENTSVIEW_API_KEY` for patents). Restart the app.
2. If there is no key yet, wait for the reset (OpenAlex resets at midnight UTC, 05:30 IST).
   Do not retry in a loop.
3. Cached results (7 days, `.cache/research`) keep working meanwhile.

## Confirm

A new scan shows `ok` for papers in its coverage.
