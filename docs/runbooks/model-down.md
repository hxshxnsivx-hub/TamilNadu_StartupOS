# The model provider is down or refusing

## How you notice

- Streamed turns end with an `error` event ("turn failed: HTTPStatusError").
- Non-streamed turns return 500.
- Replies have switched to the plain templated wording (only if the key was removed).

## What to check

1. Is `ANTHROPIC_API_KEY` set and valid? A 401 means the key is wrong or revoked.
2. Are `LLM_MODEL_MAIN` (default `claude-sonnet-5-5`) and `LLM_MODEL_FAST` (default
   `claude-haiku-4-5-20251001`, used by the review panel) models the key can use? A 404 means
   a model name is wrong.
3. 429 or 529: rate limited or overloaded; it should pass.

## What happens on its own

A turn whose model call fails finishes on the offline path (templated replies from the same
evidence), and the turn's `done` event says `"model": "offline (model failed)"`. Three failures
within a minute open a circuit breaker for five minutes: turns go straight to the offline path
without trying the model, so founders do not wait on calls likely to fail. One successful call
closes it. The log shows `breaker.open` and `model.failed_turn_offline`.

## What to do

- Wrong key or model: fix the environment variable and restart. The breaker keeps opening until
  you do.
- Provider outage: nothing is required; the breaker handles it. To stay offline deliberately,
  remove `ANTHROPIC_API_KEY` and restart.

## Confirm

A streamed turn ends with a `done` event and no `error`.
