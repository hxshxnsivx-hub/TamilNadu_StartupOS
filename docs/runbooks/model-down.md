# The model provider is down or refusing

## How you notice

- Streamed turns end with an `error` event ("turn failed: HTTPStatusError").
- Non-streamed turns return 500.
- Replies have switched to the plain templated wording (only if the key was removed).

## What to check

1. Is `ANTHROPIC_API_KEY` set and valid? A 401 means the key is wrong or revoked.
2. Is `LLM_MODEL_MAIN` a model the key can use? A 404 means the model name is wrong. The
   default `claude-sonnet-5` may not be valid; set `LLM_MODEL_MAIN=claude-sonnet-5-5`.
3. 429 or 529: rate limited or overloaded; it should pass.

## What to do

- Wrong key or model: fix the environment variable and restart.
- Provider outage: remove `ANTHROPIC_API_KEY` and restart. Conversations continue on the offline
  path, with templated replies built from the same evidence. Restore the key when the provider
  recovers.

Automatic fallback during an outage (a circuit breaker) is planned for Phase 2 (build spec 14.1).

## Confirm

A streamed turn ends with a `done` event and no `error`.
