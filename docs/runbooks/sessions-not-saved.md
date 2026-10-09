# Conversations are not being saved

## How you notice

- `POST /api/v1/ideation/agent/sessions` returns `"saved": false`.
- The log shows `agent_store.database_unavailable` and then `agent_store.selected store=memory`.
- Conversations disappear after a restart.

## Why it happens

With `AGENT_STORE=auto`, the app checks once, at the first conversation, that the database
answers and that the `agent_sessions` table exists. If either check fails, it keeps
conversations in memory instead of failing.

## What to check

1. Is PostgreSQL running and reachable with the configured credentials
   (`DATABASE_URL`, or `POSTGRES_HOST`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`)?
2. Has the migration run? From `backend/`:

   ```bash
   alembic current
   ```

   It should show `0004_agent_sessions (head)`.

## What to do

- Missing migration, from `backend/`:

  ```bash
  alembic upgrade head
  ```

- Wrong credentials: fix the environment variables, then restart the app. The store is chosen
  once per process, so a restart is needed after the database is fixed.
- To fail loudly instead of falling back, set `AGENT_STORE=database`.

## Confirm

Start a conversation: the response shows `"saved": true`. Restart the app and
`GET /api/v1/ideation/agent/sessions/{id}` still returns it.
