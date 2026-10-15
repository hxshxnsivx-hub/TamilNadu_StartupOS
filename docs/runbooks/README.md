# Runbooks

What to do when something goes wrong. Each runbook: how you notice, what to check, what to do,
how to confirm it is fixed. Add one after any incident that needed more than a minute's thought.

| Runbook | When |
|---|---|
| [Conversations are not being saved](sessions-not-saved.md) | `saved: false` when a conversation starts; sessions lost on restart |
| [A research source's budget is used up](research-budget.md) | coverage says `budget_exhausted`; the weekly signals job stops |
| [The model provider is down or refusing](model-down.md) | replies turn templated; `error` events in streams |
| [Rotate an API key](rotate-key.md) | a key leaked, expired or is being replaced |

Not written yet, because the systems do not exist yet: database restore (no backups are
configured yet, SYSTEM-DESIGN.md §5.5) and Redis loss (Redis is not in use yet).
