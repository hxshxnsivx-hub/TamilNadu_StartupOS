# Flag tree: P2 Platform

Back to the [flag tree](../FLAG-TREE.md).

## 2.1 Session store

### 2.1.1 Sessions saved in PostgreSQL for real

#### F-B2-009: Migration 0003 needs pgvector, absent on the local PostgreSQL 18, so 0004 never applies

Weight 94 · Logic flaw · impact 5/5, reach 4/5, confidence 3/3 · found by B2 · merged as [R006](../arena/details-p2.md#r006)

- **Issue:** 2.1.1 offers 'correct local PostgreSQL credentials' as the first unblock path. With the credentials fixed, 'alembic upgrade head' still fails at 0003, so agent_sessions is never created and auto mode keeps falling back to memory. The owner would keep fixing credentials for a failure that is really a missing extension, required by a feature the plan has dropped. Building pgvector on Windows needs Visual Studio build tools.
- **Cause:** backend/app/db/migrations/versions/0003_embeddings.py: op.execute('CREATE EXTENSION IF NOT EXISTS vector') and a Vector(1024) column; 0004 has down_revision 0003. Machine check: service postgresql-x64-18 is running, and 'C:\Program Files\PostgreSQL\18\share\extension\vector.control' does not exist. Only backend/docker/Dockerfile.postgres (postgis + pgvector) provides it. TASKS.md Dropped lists 'pgvector similarity tables' (offline embeddings are hashes).
- **Resolution:** build it in backend/app/db/migrations/versions/0003_embeddings.py (make the extension conditional, or move embeddings off the main chain); docs/runbooks/sessions-not-saved.md; TASKS.md 2.1.1 'Waiting on' text using **Make 0003 conditional: create the vector extension and table only if pg_available_extensions lists vector**. Unblocks 2.1.1 on the database the owner actually has, without rewriting migration history, and matches the plan's decision that pgvector is not on the free path.

| Option | Why it is a candidate | Cost | Advantages | Drawbacks |
|---|---|---|---|---|
| Make 0003 conditional: create the vector extension and table only if pg_available_extensions lists vector | A common Alembic pattern with op.get_bind() and a catalog query | free/open source | Plain local PostgreSQL works; Docker keeps embeddings; no history rewrite | Schema differs by machine; the Embedding model must not be used where the table is missing |
| Separate Alembic branch (branch_labels='vector') for embeddings | Alembic's built-in multiple-branch support | free/open source | Main head has no pgvector dependency; embeddings can be opted into | Two heads to manage; CI must test both |
| Document Docker as the only supported database for development | docker-compose already builds postgis+pgvector | free/open source | No code change | Docker Desktop is the other blocked path in 2.1.1; heavy on a home laptop |
| Install pgvector on Windows (prebuilt binaries or build with MSVC) | pgvector publishes Windows build instructions | free/open source | Matches production schema | Manual, needs build tools, must be repeated for each PostgreSQL major version; for a dropped feature |

- **Not chosen, and why:**
  - Separate branch: right in principle, but two heads is more moving parts than a guard. Docker only: Docker Desktop is the other blocked path. Installing pgvector: manual build work for a dropped feature.
- **Also found as:** F-A2-014

#### F-B2-010: The 2.1.1 integration test skips on any setup error and bypasses migrations

Weight 78 · Logic flaw · impact 4/5, reach 3/5, confidence 3/3 · found by B2 · merged as [R071](../arena/details-p2.md#r071)

- **Issue:** On the local PostgreSQL 18, correct credentials still make create_all fail on 'type vector does not exist', and the test reports a skip, which reads as 'no database'. 2.1.1.2 ('the database integration test passes') can never pass or fail honestly there. Because the test builds tables with create_all instead of the migrations, a pass would not prove migration 0004 matches the model either. Run against a fresh developer database before 'alembic upgrade', it creates every table without alembic_version, so the next upgrade fails at 0002 with DuplicateTable.
- **Cause:** backend/tests/integration/test_agent_store.py:22-29: SELECT 1 and Base.metadata.create_all (all models, including Embedding with a Vector column, app/models/__init__.py:10) are in one try, and any exception becomes pytest.skip('database unavailable'). The same pattern is in tests/integration/test_auth_api.py:27. The test uses the app engine (app/db/session.py:14, the developer database), not a test database.
- **Resolution:** build it in backend/tests/integration/ (a conftest with a dedicated test database that runs 'alembic upgrade head'); skip only on connection errors using **conftest fixture: dedicated test DB, alembic upgrade head, skip only on connection refused**. Makes 2.1.1.2 mean what it says (the migrations produce a working store), works on the installed PostgreSQL once 0003 is guarded, and shares setup with the CI round trip planned in 5.2.4.

| Option | Why it is a candidate | Cost | Advantages | Drawbacks |
|---|---|---|---|---|
| conftest fixture: dedicated test DB, alembic upgrade head, skip only on connection refused | Standard pytest + Alembic practice (alembic.command.upgrade from a fixture) | free/open source | Tests the real migration chain; a schema error fails loudly; the dev data is untouched | Needs a second database name and a CREATE DATABASE right |
| testcontainers-python with the project's Postgres image | Popular library; disposable container per run | free/open source | Clean, reproducible, matches the Docker image | Needs Docker, the blocked path on this machine |
| pytest-postgresql (spawns a temporary local server) | Mature pytest plugin using the installed binaries | free/open source | No Docker; uses the PostgreSQL 18 already installed | Still lacks pgvector unless 0003 is made conditional; Windows path setup |
| Keep create_all but narrow the except to OperationalError | Minimal change | free/open source | Honest failure on schema errors | Still does not test the migrations, and still writes to the dev database |

- **Not chosen, and why:**
  - testcontainers: depends on Docker, which is blocked here. pytest-postgresql: workable but more setup on Windows for the same result. Narrowed except: honest, but it still skips the migrations and pollutes the dev database.

#### F-A2-002: Database outage after startup gives 500s instead of the designed in-memory fallback

Weight 77 · Missing logic · impact 4/5, reach 4/5, confidence 2/3 · found by A2 · merged as [R075](../arena/details-p2.md#r075)

- **Issue:** If PostgreSQL restarts or drops connections during the day, every live founder's next turn fails with a generic error and the conversation cannot be reached. That is worse than the degraded mode the design promises, and the Talk page keeps saying the conversation is saved.
- **Cause:** SYSTEM-DESIGN.md:315 (§9) says that when PostgreSQL fails, conversations are held in memory and the founder sees 'This conversation can't be saved right now'. In the code, backend/app/agents/store.py:236-249 checks the database once (auto mode) and keeps that choice for the life of the process. SqlStore.get/save/create (86-131) have no error handling, and backend/app/core/errors.py:96-103 turns any OperationalError into a generic 500 'An unexpected error occurred'. The 'saved' flag (routers/ideation.py:303) is computed only when the session starts.
- **Resolution:** build it in backend/app/agents/store.py (a wrapper around SqlStore), backend/app/routers/ideation.py ('saved' on each turn), docs/runbooks/sessions-not-saved.md using **FallbackStore wrapper with a small hand-rolled circuit breaker**. It delivers exactly what SYSTEM-DESIGN §9 promises, reuses MemoryStore and the version check, and adds no dependency.

| Option | Why it is a candidate | Cost | Advantages | Drawbacks |
|---|---|---|---|---|
| FallbackStore wrapper with a small hand-rolled circuit breaker | Implements the same Protocol as the existing stores and degrades the same way core/redis.py already does | free/open source | On a database error it keeps the session in a MemoryStore, reports 'saved: false' for that turn, re-checks the database every N seconds, and writes held sessions back through the version check | Write-back must handle version conflicts; memory copies are per worker |
| tenacity retry, then 503 with Retry-After | tenacity>=8.4 is already in requirements.txt | free/open source | Very small; rides out short blips | Does not deliver the §9 behaviour; a long outage still stops every conversation |
| aiobreaker or pybreaker library | Mature circuit-breaker libraries for Python | free/open source | Tested breaker states | A new dependency for a few lines of state, and the memory fallback still has to be written by hand |
| Hold the session in the Redis copy while the database is down | CachedStore already keeps a Redis copy | free/open source | Survives a restart of one worker | Breaks the rule that nothing is stored only in Redis (core/redis.py:3); no help when Redis is absent |

- **Not chosen, and why:**
  - tenacity retry: only hides short blips, and long outages still fail; aiobreaker/pybreaker: adds a dependency, and the fallback is still hand-written
  - Redis holding: breaks the 'nothing only in Redis' rule and does nothing without Redis.
- **Also found as:** F-B2-012

#### F-B2-011: Migration 0001 builds tables from live ORM models, so later model changes break upgrades

Weight 71 · Logic flaw · impact 4/5, reach 3/5, confidence 2/3 · found by B2 · merged as [R115](../arena/details-p2.md#r115)

- **Issue:** When 3.1.2 (or 3.2.2's encrypted columns) adds a column to Founder or Startup with its own add_column migration, a fresh database running 'upgrade head' creates the new column in 0001 and then fails in the later migration with DuplicateColumn. Old databases and fresh ones also end up with different histories. The 5.2.4 CI round trip and every new machine (including the 2.1.1 path) would break the first time those models change.
- **Cause:** backend/app/db/migrations/versions/0001_initial.py:15 imports app.models.Base and :31-32 run Base.metadata.create_all(tables=['founders','startups','documents','profile_completeness'], checkfirst=True); its docstring says this keeps it from drifting. SYSTEM-DESIGN 5.2: each change is an explicit migration.
- **Resolution:** build it in backend/app/db/migrations/versions/0001_initial.py (freeze it to explicit op.create_table for the four tables as they are today) using **Freeze 0001 into explicit op.create_table calls (generated once from today's metadata)**. No production database exists yet, so freezing is free now and costly later. It aligns 0001 with the explicit-operations rule and with the other three migrations.

| Option | Why it is a candidate | Cost | Advantages | Drawbacks |
|---|---|---|---|---|
| Freeze 0001 into explicit op.create_table calls (generated once from today's metadata) | Alembic's recommended practice; 0002-0004 already use explicit ops | free/open source | History stays fixed; --sql offline mode works; no behaviour change for existing databases | Edits a released migration (safe here: no production database yet) |
| New squashed baseline migration and alembic stamp for existing databases | A common squash pattern | free/open source | A clean start | Every existing dev database must be stamped by hand |
| Leave 0001 and add a CI check that fresh upgrade head equals the models (alembic check) | Alembic 1.9+ 'alembic check' command | free/open source | Catches the break in CI | Detects, does not prevent; the first 3.1.2 migration still fails |

- **Not chosen, and why:**
  - Squash and stamp: manual stamping on each machine for no added benefit. A CI check alone: reports the breakage but does not stop 3.1.2's first migration from failing.
- **Also found as:** F-A5-017

#### F-A2-014: Migration 0003 needs pgvector, a dropped feature, and it blocks the agent_sessions migration

Weight 71 · Missing logic · impact 4/5, reach 3/5, confidence 2/3 · found by A2 · merged as [R006](../arena/details-p2.md#r006)

- **Issue:** The owner's first route to saving conversations (local PostgreSQL) fails with 'extension vector is not available', and the runbook sessions-not-saved.md only says to run 'alembic upgrade head'. A dropped feature becomes a hard dependency of the core one, and the same trap waits for CI (5.2.4) and the backend container (2.4.4).
- **Cause:** backend/app/db/migrations/versions/0003_embeddings.py:24 runs CREATE EXTENSION IF NOT EXISTS vector and builds an HNSW index, and 0004_agent_sessions.py:18 has down_revision = '0003_embeddings'. TASKS.md:982 (Dropped) removes 'pgvector similarity tables', and no app code reads the Embedding model (grep: only models/__init__.py:10 imports it). pgvector is available only in the custom image backend/docker/Dockerfile.postgres:6. Task 2.1.1 offers 'correct local PostgreSQL credentials' as the unblock, which on a stock PostgreSQL install without pgvector fails at 0003 before agent_sessions is created. .github/workflows/ci.yml has no database step yet, and 5.2.4's 'PostgreSQL service' would also need a pgvector image.
- **Resolution:** build it in backend/app/db/migrations/versions/0003_embeddings.py (or a new migration), docs/runbooks/sessions-not-saved.md, the 5.2.4 CI service image using **Make 0003 conditional: create the extension and table only if pg_available_extensions lists 'vector'**. It unblocks 2.1.1 on any free local PostgreSQL today without rewriting history, and a later cleanup migration can drop the table for good once the owner confirms the Dropped decision.

| Option | Why it is a candidate | Cost | Advantages | Drawbacks |
|---|---|---|---|---|
| Make 0003 conditional: create the extension and table only if pg_available_extensions lists 'vector' | Alembic migrations are plain Python; checking pg_available_extensions is a standard PostgreSQL query | free/open source | Works on stock and custom PostgreSQL; keeps the revision chain unchanged for any database already at head | The schema differs by machine; downgrade must use IF EXISTS |
| New migration 0005 dropping embeddings, and remove pgvector from 0003 | Follows the Dropped decision; 'production migrations only go forward' (SYSTEM-DESIGN §5.2) allows editing only because nothing is deployed yet | free/open source | Removes the dead table and the pgvector dependency completely | Editing 0003 rewrites history for anyone who already ran it (only the Docker database, if at all) |
| Document pgvector as a requirement (Docker only) | The custom image already has it | free/open source | No code change | Keeps a dropped feature as a blocker; on Windows, pgvector must be built from source |
| Reorder 0004 to come before 0003 | Alembic down_revision edits | free/open source | agent_sessions applies first | upgrade head still fails at 0003, and reordering confuses any database already stamped |

- **Not chosen, and why:**
  - Drop and edit 0003: cleaner, but it edits a migration that may already be applied; document-only: keeps the blocker, which is the problem; reorder: head still fails, and it adds confusion.
- **Also found as:** F-B2-009

#### F-B2-012: A database outage after start gives 500s mid-conversation; no fallback like Redis has

Weight 61 · Missing logic · impact 3/5, reach 3/5, confidence 2/3 · found by B2 · merged as [R075](../arena/details-p2.md#r075)

- **Issue:** Once 2.1.1 makes PostgreSQL the truth, a database restart or a pool exhaustion (2.4.3) makes every turn fail with a raw 500 and the founder's last reply is lost. The opposite case is sticky: a database that was briefly down at boot leaves the whole process on memory, so 'saved: true' never comes back without a manual restart.
- **Cause:** backend/app/agents/store.py:270-283: the store is chosen once per process; after that, SqlStore.get/save (:85-125) raise asyncpg or SQLAlchemy errors uncaught. backend/app/routers/ideation.py:271-285 (_load/_save) catch only VersionConflict. The P2 'Already built' line claims failure handling for Redis, model and source outages (SYSTEM-DESIGN 9) but not the database. Conversely, if the database is down at the first conversation, memory is chosen until restart (runbook sessions-not-saved.md).
- **Resolution:** build it in backend/app/agents/store.py (catch database errors, retry once, then a 503 with a clear message); routers/ideation.py; the runbook using **Catch SQLAlchemy OperationalError/DBAPIError in the store, retry once, answer 503 'try again'**. Gives the same kind of honest failure the Redis, model and source paths already have, with no new dependency and no risk of diverging copies.

| Option | Why it is a candidate | Cost | Advantages | Drawbacks |
|---|---|---|---|---|
| Catch SQLAlchemy OperationalError/DBAPIError in the store, retry once, answer 503 'try again' | Plain SQLAlchemy exception classes; pool_pre_ping already on | free/open source | An honest message; nothing is silently lost; small | The founder's turn must be retried by the client |
| Re-check database readiness periodically in auto mode and swap the store back | A health-check loop in the existing get_store | free/open source | Recovers 'saved' without a restart | Sessions created in memory meanwhile must be migrated or lost |
| tenacity retry decorator on store calls | A popular Python retry library | free/open source | Configurable backoff | A new dependency for one call site; retries add latency to a streamed turn |
| Write-behind to Redis when the database is down | The CachedStore already holds a copy | free/open source | Turns keep working | Redis is optional and not backed up (SYSTEM-DESIGN 5.5); version checks get complex |

- **Not chosen, and why:**
  - Periodic re-check: useful later, but sessions created in memory in the meantime have to be reconciled. tenacity: a new dependency for a single retry. Write-behind: Redis is optional and unbacked, so it cannot be the fallback truth.
- **Also found as:** F-A2-002

### 2.1.2 Fix the "saved" flag when Redis is on

#### F-B2-027: Talk forgets the session ID on any resume error, so a brief outage loses the conversation

Weight 78 · Logic flaw · impact 4/5, reach 3/5, confidence 3/3 · found by B2 · merged as [R029](../arena/details-p2.md#r029)

- **Issue:** When the database or backend restarts, or Wi-Fi drops during page load, the Talk page deletes the only pointer the anonymous founder has to their conversation, although the session is still safe in PostgreSQL. 2.1.2 makes the banner say 'saved' more often, so founders will trust it, and then lose the conversation to a transient error.
- **Cause:** frontend/src/pages/Talk.tsx:121-135: getSession(id) ... .catch(() => save(null)), with the comment 'expired or gone: start fresh'. frontend/src/voice/agentClient.ts:107-109: any non-OK status or network failure rejects. Step 3 showed that a database error in SqlStore.get surfaces as an uncaught 500 (routers/ideation.py:271-274 catch only the 404 case).
- **Resolution:** build it in frontend/src/pages/Talk.tsx (clear the stored ID only on 404; on 5xx or network error keep it and offer 'try again'); backend 503 on database errors (step 3 flag) using **Clear only on 404; keep the ID and show a retry notice on 5xx or network errors**. It is the minimal change that makes 'saved' true from the founder's point of view, and it fits the 503 'try again' answer recommended for database outages in step 3.

| Option | Why it is a candidate | Cost | Advantages | Drawbacks |
|---|---|---|---|---|
| Clear only on 404; keep the ID and show a retry notice on 5xx or network errors | A status check in the existing json() helper; standard error handling | free/open source | A few lines; no lost conversations | A stale ID lingers if the backend keeps failing (harmless) |
| Exponential-backoff retry before giving up | A common client pattern | free/open source | Recovers from short blips automatically | Still ends in deletion after the retries unless combined with option 1 |
| Keep a list of recent session IDs (not just one) in storage | localStorage array | free/open source | The founder can reopen older conversations | Bigger change; shared-device leakage (step 5) gets worse without namespacing |

- **Not chosen, and why:**
  - Backoff alone: still deletes after retries. A list of recent IDs: a new feature that widens the shared-device exposure flagged at 3.1.3.
- **Also found as:** F-B5-018

#### F-B2-028: 'Saved' is sent only at start, and when true it hides the 6-hour idle expiry

Weight 74 · Logic flaw · impact 3/5, reach 4/5, confidence 3/3 · found by B2 · merged as [R083](../arena/details-p2.md#r083)

- **Issue:** After a resume the founder gets no persistence signal at all, even on the memory store. With 2.1.2's fix, 'saved: true' shows no warning, yet the conversation (and the roadmap a founder will track, step 6) disappears the next day. The founder is misled either way, and 2.1.3 (D4) may change the rule again with nothing tying the message to it.
- **Cause:** backend/app/routers/ideation.py:303 returns 'saved' only from agent_start. agent.snapshot (resume, routers/ideation.py:306-309) has no 'saved' field, so Talk.tsx:62 stays null after a resume and the banner (:409-411) never shows. The banner text says only 'not being saved (no database); it will be lost on restart'. backend/app/agents/store.py:29/46-47: even in PostgreSQL the session is gone after 6 idle hours.
- **Resolution:** build it in backend/app/routers/ideation.py (return 'saved' and 'kept_until' in both start and snapshot, computed from the store and the lifetime rule); frontend Talk.tsx banner text from that value; tests using **Return {saved, kept_until} on start and resume, derived from the store's durability and the lifetime constant**. Tells the founder the truth in both entry paths and stays correct when D4 lands, because it comes from the same constant the store enforces.

| Option | Why it is a candidate | Cost | Advantages | Drawbacks |
|---|---|---|---|---|
| Return {saved, kept_until} on start and resume, derived from the store's durability and the lifetime constant | Small API addition; IDLE_EXPIRY already exists as one constant | free/open source | An honest banner that follows D4 automatically | A frontend change and a schema change in agentClient types |
| Add 'saved' to the snapshot only | The minimal fix | free/open source | Fixes the missing banner on resume | Still silent about the 6-hour loss |
| Static banner text explaining the idle limit | Copy-only change | free/open source | Trivial | Drifts when D4 changes the rule |

- **Not chosen, and why:**
  - Snapshot only: half the truth. Static text: drifts from the rule it describes.

#### F-B2-029: Durability is inferred from a store-name string, and no test asserts the flag

Weight 58 · Missing structure · impact 2/5, reach 3/5, confidence 3/3 · found by B2 · merged as [R181](../arena/details-p2.md#r181)

- **Issue:** 2.1.2's proposed fix (startswith 'database') is string matching on a display name. Any future wrapper (a metrics or retry wrapper, for example 'retry+database') breaks it again silently, and with no test the banner regression returns unnoticed, as it did with the Redis wrapper.
- **Cause:** backend/app/routers/ideation.py:303 'saved': store.name == 'database'. backend/app/agents/store.py:182 CachedStore.name = f'{inner.name}+redis'. The SessionStore protocol (store.py:36-46) has only a name, no durability attribute. grep over backend/tests finds no assertion on 'saved'.
- **Resolution:** build it in backend/app/agents/store.py (a durable: bool on the protocol; CachedStore delegates to inner.durable); routers/ideation.py; tests/api/test_ideation_api.py (assert saved for memory, database and cached stores) using **durable attribute on SessionStore, delegated by wrappers, and API tests for each store**. Makes durability a property the store declares rather than a name the router parses, and the tests stop this regression from recurring.

| Option | Why it is a candidate | Cost | Advantages | Drawbacks |
|---|---|---|---|---|
| durable attribute on SessionStore, delegated by wrappers, and API tests for each store | An explicit capability on the existing Protocol | free/open source | Robust to new wrappers; testable with the fake Redis | Touches each store class (three, small) |
| startswith('database') as the plan says, plus a test | The plan's fix | free/open source | One line | Breaks on any wrapper that prefixes its name |
| isinstance check that unwraps CachedStore to SqlStore | Type inspection | free/open source | No protocol change | Couples the router to store internals |

- **Not chosen, and why:**
  - startswith: repeats the same class of bug with the next wrapper. isinstance unwrap: leaks store internals into the router.

### 2.1.3 One rule for session lifetime (D4)

#### F-B5-018: Talk page forgets the saved session on any error, not only on 404

Weight 84 · Logic flaw · impact 4/5, reach 4/5, confidence 3/3 · found by B5 · merged as [R029](../arena/details-p2.md#r029)

- **Issue:** On a dropped 2G connection, a backend restart or a database outage, opening the Talk page erases the only pointer to the conversation; the session still exists (for 90 days once D4 lands) but the anonymous founder can never return to it. A longer lifetime is worthless while a transient error discards the key.
- **Cause:** frontend/src/pages/Talk.tsx:120-134 — getSession(id)...catch(() => save(null)) with comment 'expired or gone: start fresh'; save(null) removes the localStorage key (Talk.tsx:51-52). frontend/src/voice/agentClient.ts:88-108 throws the same Error for a network failure, a 500, a 503 or a 404. TASKS 1.1.4 covers replays, 409 and the resume preamble, not this.
- **Resolution:** build it in frontend/src/voice/agentClient.ts (typed error with status), frontend/src/pages/Talk.tsx (forget only on 404, otherwise offer retry) using **Error class carrying the HTTP status; forget only on 404**. Fixes the loss with a few lines and fits 1.1.4's 2G work, which edits the same files.

| Option | Why it is a candidate | Cost | Advantages | Drawbacks |
|---|---|---|---|---|
| Error class carrying the HTTP status; forget only on 404 | Plain TypeScript: class HttpError extends Error { status } | free/open source | Tiny change, no dependency; network failures keep the key and show a retry | Every caller of json() sees the new type |
| TanStack Query with retry and status-aware handling | Popular React data-fetching library | free/open source | Retries, caching, error states | New dependency for one call; the app does not use it elsewhere |
| Keep a list of recent session ids instead of one | localStorage array with timestamps | free/open source | Founder can pick a past conversation | Does not fix the wrong deletion by itself |

- **Not chosen, and why:**
  - TanStack Query: a dependency for one fetch; recent-ids list: a nice addition but still deletes on transient errors.
- **Also found as:** F-B2-027

#### F-B5-017: Under D4, CachedStore re-hides a session it just loaded: resume works, next turn 404s

Weight 78 · Logic flaw · impact 4/5, reach 3/5, confidence 3/3 · found by B5 · merged as [R073](../arena/details-p2.md#r073)

- **Issue:** Implementing 2.1.3.1 the obvious way (drop _expired from SqlStore only) lets the Talk page resume a 10-hour-old conversation and then answer the founder's first turn with 'Session not found or expired' (routers/ideation.py:272-274). The bug appears only with Redis on, so tests on MemoryStore miss it.
- **Cause:** Ran scratchpad/arena/b5/lifetime.py: inner store without idle hiding (as D4 asks for PostgreSQL), CachedStore with a fake Redis, session updated_at 10 h ago -> 'first read (resume): True \| second read (the turn): False'. store.py:211-213 returns None when the Redis copy is _expired without falling back to the database; store.py:214-216 copies a database hit into Redis with a fresh 6 h TTL but the old updated_at.
- **Resolution:** build it in agents/store.py (CachedStore.get, _expired), tests with the fake Redis using **Expiry only by Redis TTL in CachedStore; database rule separate**. Matches D4's wording ('6 h for the Redis copy, 90 days in PostgreSQL') literally and makes the proven failure impossible; add the script's scenario as a test.

| Option | Why it is a candidate | Cost | Advantages | Drawbacks |
|---|---|---|---|---|
| Expiry only by Redis TTL in CachedStore; database rule separate | Let the Redis key's own TTL express the 6 h copy lifetime and remove the updated_at check from the cache layer; SqlStore applies the retention rule | free/open source | One clock per layer; a cache miss always falls through to the truth | Must also change MemoryStore so tests mirror deployment |
| Fall through to the database when the copy looks expired | Treat an expired copy as a miss: drop it and read inner | free/open source | Minimal change | Keeps a redundant check and an extra round trip per turn for old sessions |
| Make the lifetime a store policy object shared by all three stores | Strategy pattern: one Lifetime(hide_after, layer) used by Memory, Sql and Cached stores | free/open source | Single place to apply D4 and the saved-idea exception (2.1.3.2) | More structure for a two-rule decision |

- **Not chosen, and why:**
  - Fall-through: patches the symptom and keeps two clocks in the cache layer; policy object: more structure than one decision needs.

#### F-A2-004: Memory store and per-session turn locks grow forever

Weight 58 · Optimisation · impact 2/5, reach 3/5, confidence 3/3 · found by A2 · merged as [R179](../arena/details-p2.md#r179)

- **Issue:** A long-running offline or demo server keeps the full text of every conversation ever started in RAM, and a deleted conversation's lock entry survives. Memory grows without limit, and expired founder text is kept longer than the 6-hour rule allows.
- **Cause:** backend/app/agents/store.py:58-65: MemoryStore._docs is never pruned; get() hides expired sessions but keeps them (probe: a 7 h-idle session was still in _docs). backend/app/routers/ideation.py:268: _turn_locks gains one asyncio.Lock per session through setdefault (lines 322 and 336), and nothing removes it, not even agent_delete (313-319). AGENT_STORE=auto falls back to MemoryStore whenever the database is not ready (store.py:245), which is the state today while 2.1.1 waits.
- **Resolution:** build it in backend/app/agents/store.py (MemoryStore), backend/app/routers/ideation.py (_turn_locks) using **Lazy sweep on create, plus lock cleanup on release and on delete**. It bounds memory with no new dependency and no background task, and it also applies the expiry rule to founder text held in RAM.

| Option | Why it is a candidate | Cost | Advantages | Drawbacks |
|---|---|---|---|---|
| Lazy sweep on create, plus lock cleanup on release and on delete | A few lines in existing code; no dependency | free/open source | Sweeps expired documents at most once a minute when a session is created; drops a lock when it is released with no waiters, and on delete | The sweep is O(n) when it runs (n is small offline) |
| cachetools.TTLCache | Widely used Python cache library | free/open source | Ready-made TTL eviction | A new dependency; its TTL resets only on write, so it needs care to match the updated_at rule |
| weakref.WeakValueDictionary for the locks | Standard library | free/open source | A lock disappears when no request holds it | Fixes the locks only, not the stored documents |
| Background asyncio task that sweeps every few minutes | Standard library, started from the app lifespan hook | free/open source | Predictable timing | Another lifecycle to start and stop, including in tests |

- **Not chosen, and why:**
  - cachetools: a dependency for a few lines of code
  - WeakValueDictionary: covers the locks only; background task: an extra lifecycle for no gain at this size.
- **Also found as:** F-B5-019, F-A1-011

#### F-B5-019: Expired sessions and turn locks stay in process memory forever

Weight 58 · Missing logic · impact 2/5, reach 3/5, confidence 3/3 · found by B5 · merged as [R179](../arena/details-p2.md#r179)

- **Issue:** Without the database, every conversation's transcript and facts remain in memory after they are 'expired' (held but unreachable, and never subject to retention), and any client can grow _turn_locks without bound by posting turns to random 32-hex ids. Together with the job board (B5-04 flag 2) the process grows until restart.
- **Cause:** backend/app/agents/store.py:60-65 MemoryStore.get returns None for an expired session but never removes it from _docs; MemoryStore is the automatic fallback when the database is unreachable (store.py:245), i.e. today. backend/app/routers/ideation.py:268, 324, 337 create an asyncio.Lock in _turn_locks for every session id before _load, including unknown ids that then 404; nothing removes entries.
- **Resolution:** build it in agents/store.py (MemoryStore expiry pop and sweep), routers/ideation.py (lock only after a successful load; drop when idle) using **Pop on expired read plus the in-process sweep from B5-04**. The same sweep already recommended for the job board covers the store and the locks, applying the lifetime rule 2.1.3 decides in one place.

| Option | Why it is a candidate | Cost | Advantages | Drawbacks |
|---|---|---|---|---|
| Pop on expired read plus the in-process sweep from B5-04 | One periodic asyncio task in the lifespan clearing MemoryStore, board and _turn_locks entries idle past the lifetime | free/open source | One mechanism for all in-process per-session state; no dependency | Lock removal must skip locks currently held |
| WeakValueDictionary for locks | Python stdlib weakref | free/open source | Locks vanish when no request holds them | Does not cover MemoryStore or the board |
| cachetools.TTLCache for MemoryStore | Popular caching library | free/open source | Automatic expiry | Expiry by insert time unless customised; new dependency |

- **Not chosen, and why:**
  - WeakValueDictionary: fixes only the locks
  - TTLCache: insert-time expiry does not match idle expiry and adds a dependency.
- **Also found as:** F-A2-004, F-A1-011

### 2.1.4 Session format version

#### F-B2-001: No policy for a session document that fails to decode; one bad doc breaks /programme

Weight 68 · Missing logic · impact 3/5, reach 3/5, confidence 3/3 · found by B2 · merged as [R137](../arena/details-p2.md#r137)

- **Issue:** Once the format changes, an upgrader that misses a case fails the request with a 500, not a 404 or a 'cannot resume' message. On /programme, one bad session among a cohort's IDs fails the whole aggregate. The founder loses resume and the programme manager gets nothing.
- **Cause:** backend/app/agents/ideation.py:168 ElicitationSession.model_validate(d['elicitation']) and :192 d['updated_at'] raise on any old or invalid shape. backend/app/agents/store.py:60-64, 90-95 and 225-228 call from_dict with no guard. backend/app/routers/cohort.py:40 loads up to 500 sessions in one comprehension. Probe (scratchpad arena/b2probe.py, Python 3.11): a stored doc with slot confidence 1.5 makes MemoryStore.get raise pydantic ValidationError.
- **Resolution:** build it in backend/app/agents/store.py (one decode helper used by all three stores); backend/app/agents/ideation.py (upgrade function); routers/ideation.py _load (410 or 'cannot be resumed'); routers/cohort.py (skip and count undecodable sessions) using **Central decode() with try/except, a log event and skip/410**. Closes both the 500 and the all-or-nothing /programme failure in one small helper. It works offline on the memory store and leaves room to add quarantine later.

| Option | Why it is a candidate | Cost | Advantages | Drawbacks |
|---|---|---|---|---|
| Central decode() with try/except, a log event and skip/410 | Plain Python pattern; fits the existing structlog agent_store.* events | free/open source | Small, one place, no dependency; /programme can report sessions_unreadable | Bad rows stay until retention removes them |
| Quarantine column or table (decode_error, quarantined_at) | Dead-letter pattern; an Alembic migration on agent_sessions | free/open source | Operators can find and repair broken sessions; fits a runbook | Needs the database (2.1.1) and a migration; adds a write on the read path |
| Whole session as a Pydantic model with lenient validators | Pydantic v2 already models elicitation | free/open source | One schema; coercion and defaults are declarative | Leniency hides real corruption; large refactor of the dataclass |
| jsonschema validation before from_dict | Mature library; 5.2.1 already plans schemas for reference data | free/open source | Explicit documented contract for 5.3.1 | Duplicates the Pydantic model; detects but does not recover |

- **Not chosen, and why:**
  - Quarantine: needs PostgreSQL (waiting on 2.1.1) and is more than is needed now. Lenient Pydantic: hides corruption, and the refactor is out of proportion. jsonschema: a second schema next to Pydantic, with no recovery.

#### F-B2-002: Older code silently drops newer fields on load-then-save (rollback, Redis copy)

Weight 62 · Logic flaw · impact 3/5, reach 2/5, confidence 3/3 · found by B2 · merged as [R161](../arena/details-p2.md#r161)

- **Issue:** 2.1.4 plans only old-to-new upgrade-on-read. Suppose a release adds a field (for example the 'saved' flag of 2.1.3.2) and is then rolled back, or two workers run different releases during a deploy. The older code loads the document and saves it back without the field. A founder's saved idea quietly loses its retention protection, and the version check cannot catch it because the save is legitimate.
- **Cause:** backend/app/agents/ideation.py:144-193: from_dict reads a fixed key list and to_dict writes the same list, so unknown keys vanish. Probe: from_dict({..., 'saved': True, 'format': 2}).to_dict() has no 'saved' key. backend/app/agents/store.py:184-189 keeps a 6-hour Redis copy written by whichever release served the last turn.
- **Resolution:** build it in backend/app/agents/ideation.py (a FORMAT constant; from_dict refuses a format newer than the code); backend/app/agents/store.py (refuse to save when format > FORMAT) using **Format guard: refuse to load or save a newer format than the code knows**. The format field that 2.1.4 adds is exactly what makes this check possible. Refusing is the only option that guarantees no silent loss of safety-relevant fields such as 'saved' or consent.

| Option | Why it is a candidate | Cost | Advantages | Drawbacks |
|---|---|---|---|---|
| Format guard: refuse to load or save a newer format than the code knows | Standard schema-version reader rule (Avro and Protobuf compatibility rules, Django migration checks) | free/open source | A few lines; turns silent loss into a visible 409/503 during a mixed deploy | During a rollback, newer sessions are unavailable until the roll forward |
| Preserve unknown keys (carry an extras dict through from_dict/to_dict) | Protobuf unknown-field preservation; easy with **rest in Python | free/open source | Rollback stays usable and no bytes are lost | Old code still acts wrongly on fields it ignores (retention ignoring 'saved') |
| Documented expand/contract deploy discipline only | Common migration practice, in line with SYSTEM-DESIGN 5.2 | free/open source | No code | Relies on people; nothing enforces it |
| Pydantic model with extra='allow' | Pydantic v2 already used | free/open source | Keeps extras automatically | Needs a dataclass-to-Pydantic refactor; same blind-old-code issue |

- **Not chosen, and why:**
  - Preserving keys: keeps the bytes, but old code still makes retention or consent decisions without the field. Process only: not enforced. Pydantic extra='allow': a big refactor with the same blind-old-code issue.

#### F-B2-003: Enum renames (D5 sector list) leave dead strings in old sessions and shift idea_version

Weight 61 · Missing logic · impact 3/5, reach 3/5, confidence 2/3 · found by B2 · merged as [R165](../arena/details-p2.md#r165)

- **Issue:** 4.1.2 replaces the 12-sector enum with the StartupTN list but says nothing about stored sessions. Old sessions keep sector strings that no longer exist, and these filled-but-invalid values feed matching and the programme's sector bands. If the 2.1.4 upgrader maps them, every affected session's idea_version changes: finished background results (scan, council) are orphaned and recomputed against the free source budget, and the row column stays stale until the next save.
- **Cause:** backend/app/agents/ideation.py:169-173 restores enum members under contextlib.suppress(ValueError), so an unknown value stays a bare str. Probe: sector 'agritech_old' reloads as str with no warning. ideation.py:57 CORE_SLOTS includes 'sector', and :137-142 hash those values into idea_version. idea_version keys job results (backend/app/agents/results.py:26-47) and the agent_sessions.idea_version column (store.py:117).
- **Resolution:** build it in backend/app/agents/ideation.py (the upgrade step for format N+1 maps old enum values through the 4.1.2 mapping); idea_version (hash a canonical sector code, or re-key results from the old to the new idea_version) using **Versioned upgrade step using the 4.1.2 mapping, re-keying results**. Connects the two tasks that will otherwise collide. Founders are not asked again, and no free source budget is spent recomputing results that are still valid.

| Option | Why it is a candidate | Cost | Advantages | Drawbacks |
|---|---|---|---|---|
| Versioned upgrade step using the 4.1.2 mapping, re-keying results | The upgrade chain 2.1.4 already plans, plus the mapping 4.1.2 produces anyway | free/open source | Old sessions become valid; results are kept by copying them under the new idea_version | The result store must support re-keying (in memory today, a table after 2.3.1) |
| Hash a stable canonical code, not the label, in idea_version | Decouples identity from vocabulary | free/open source | Future renames never move idea versions | Changes every hash once, which needs a one-time migration |
| Mark unmapped values low-confidence so the question is asked again | The existing 0.5 filled floor in elicitation/session.py | free/open source | The founder corrects it naturally; nothing is guessed | Re-asks returning founders a question they already answered |
| Leave the strings and log a warning | Status quo | free/open source | Trivial | Invalid sectors keep flowing into cohort and matching |

- **Not chosen, and why:**
  - Canonical-code hash: right in the long run, but it changes every hash once, which is the cost being avoided; do it together with the mapping or not at all. Re-ask: annoys returning founders when a mapping exists. Status quo: invalid data reaches the cohort bands.

#### F-B2-004: Upgrade-on-read leaves mixed formats in PostgreSQL; the 5.5.5 split has no backfill

Weight 55 · Missing structure · impact 3/5, reach 2/5, confidence 2/3 · found by B2 · merged as [R193](../arena/details-p2.md#r193)

- **Issue:** Sessions nobody reopens, which is most of them given the 6-hour expiry, stay in their original format forever. The table-split migration would then have to import app upgrade code into Alembic, which breaks when that code later changes, or re-implement every format. A missed format silently drops cohort data or fails a production migration, and production migrations only go forward (SYSTEM-DESIGN 5.2).
- **Cause:** backend/app/agents/store.py:85-95: SqlStore.get upgrades only in memory, and the row is rewritten only by save() (:98-125). The agent_sessions model (backend/app/models/agent_session.py:20-32) has no format column, so nothing shows which rows are on which format. TASKS.md 5.5.5.1 says only 'split session documents into tables by migration'.
- **Resolution:** build it in backend/db/migrations (a queryable format column); scripts/ (an idempotent upgrade-all backfill run before 5.5.5.1); backend/app/agents/ideation.py (keep the upgrade function pure and importable) using **Format column plus an idempotent upgrade-all script before the split**. Reuses the one upgrade function the app already trusts and follows the documented add/fill/constrain rule. It gives 5.5.5 a checkable precondition: no rows below the current format.

| Option | Why it is a candidate | Cost | Advantages | Drawbacks |
|---|---|---|---|---|
| Format column plus an idempotent upgrade-all script before the split | Expand/contract with backfill, matching SYSTEM-DESIGN 5.2 'add, fill in, then constrain' | free/open source | The split sees one format; progress is queryable (WHERE format < N) | One more migration and one more script |
| Alembic data migration with a frozen copy of the upgrader | Common Alembic data-migration practice | free/open source | Self-contained and reproducible | Duplicated code; large JSONB rewrites inside a migration transaction |
| PostgreSQL jsonb_set SQL per format step | Native PostgreSQL, no app code | free/open source | Fast and set-based | Nested enum mapping is awkward in SQL; cannot be tested on the offline memory store |
| Nightly job lazily upgrades stale rows | Fits the planned nightly job (5.4.4) | free/open source | No big-bang rewrite | The split must still wait for completion, which cannot be known without the column |

- **Not chosen, and why:**
  - Frozen Alembic copy: duplicates the upgrader and rewrites large JSONB inside a transaction. jsonb SQL: a poor fit for nested enum mapping and untestable offline. Nightly lazy backfill: without the column you cannot know when it is done, so it is option 1 with a delay.

## 2.2 Caching rules

### 2.2.1 One fetch per key at a time

#### F-B5-006: No single-flight without Redis, although the app runs as one process by default

Weight 74 · Missing logic · impact 3/5, reach 4/5, confidence 3/3 · found by B5 · merged as [R098](../arena/details-p2.md#r098)

- **Issue:** The ten-sessions case 2.2.1 exists for happens inside one process today, so the planned Redis-only lock does nothing in the default free setup; each duplicate also increments budget:{source}:{date} (sources.py:146-161), so 5.4.2 would report ten requests of budget for one logical search and RESEARCH_DAILY_LIMIT trips ten times faster.
- **Cause:** Ran scratchpad/arena/b5/dup.py (httpx.MockTransport, set_redis(None)): 10 concurrent sources.paper_count calls for the same query -> 'concurrent same-key requests sent: 10'. sources.py:167-175 checks the cache then fetches with no coordination. TASKS.md 2.2.1 How: 'without Redis, no lock'. Redis is optional (core/redis.py:3-5) and jobs run in-process, one server (agents/jobs.py:20-21, decision 0010).
- **Resolution:** build it in research/sources.py (_get_json), with the Redis lock as the cross-process layer on top using **In-process single-flight map of asyncio futures**. Fixes the duplicate fetches in the setup that actually runs, with no dependency, and the Redis lock can wrap it later for several workers.

| Option | Why it is a candidate | Cost | Advantages | Drawbacks |
|---|---|---|---|---|
| In-process single-flight map of asyncio futures | Standard asyncio pattern (dict key -> Future/Task) in a few lines; no dependency | free/open source | Covers the actual deployment; waiters get the result with zero extra requests or budget; composes with a Redis lock for several workers | Per process only; must remove the entry on failure so the next caller retries |
| aiocache with a lock decorator | Maintained asyncio cache library with in-memory and Redis backends and RedLock/OptimisticLock helpers | free/open source | Lock and cache in one abstraction for both modes | Replaces the hand-written two-layer Cache and its key scheme; larger change than the task |
| Redis SET NX lock only (as planned) | TASKS.md 2.2.1 design | free/open source | Works across workers | Does nothing when Redis is off, which is the default; costs a round trip even in one process |
| Job-board level dedupe by query | agents/jobs.py already dedupes by (session, kind) | free/open source | Reuses existing structure | Keys by session, not by request; two sessions with the same query still fetch twice, and novelty/scan share keys below job level |

- **Not chosen, and why:**
  - aiocache: rewrites the existing cache for a coordination problem
  - Redis-only lock: inactive in the default free setup; job-board dedupe: wrong key, sessions differ while requests match.

#### F-A2-007: OpenAlex API key is part of the cache key, so adding or rotating it empties the cache

Weight 68 · Logic flaw · impact 3/5, reach 3/5, confidence 3/3 · found by A2 · merged as [R122](../arena/details-p2.md#r122)

- **Issue:** Adding OPENALEX_API_KEY is the plan's own unblock for cache warming (2.2.6) and for the free budget, but on the day it is added every cached response (7 days of founders' searches) becomes unreachable, and the shared budget is spent again on queries already answered. Every key rotation (5.3.2.2) does the same. The planned 2.2.1 lock:{key} would inherit the same key and the same split.
- **Cause:** backend/app/research/sources.py:208 and 260 put api_key into params; _get_json builds the cache key from those params (sources.py:167: key = 'GET {url} {params}'). Probe (scratchpad/a2/probe2.py): the same query fetched without and then with api_key made 2 network calls; the second missed the cache.
- **Resolution:** build it in backend/app/research/sources.py (_get_json key building), backend/tests/unit/test_redis_layer.py using **Strip credential params (api_key, mailto) before hashing the key**. The smallest change; it keeps the existing two-layer cache and makes 2.2.1's lock keys and 2.2.6's warming reuse the same entries founders created.

| Option | Why it is a candidate | Cost | Advantages | Drawbacks |
|---|---|---|---|---|
| Strip credential params (api_key, mailto) before hashing the key | A few lines in _get_json; a common practice in HTTP caches (vary only on what changes the response) | free/open source | Cache and lock keys survive adding or rotating the key; the key still never appears in Redis | Needs a small list of credential parameter names to maintain |
| Send the OpenAlex key as a header instead of a parameter | Headers are already left out of the key (GitHub token, EPO bearer) | free/open source | No key-building change | OpenAlex documents api_key as a query parameter; relying on header support is not proven |
| requests-cache / hishel HTTP cache layer | Mature HTTP caching libraries; hishel supports httpx | free/open source | Configurable key matching (ignored_parameters) | A second cache beside the existing Redis/disk Cache, and it does not know the budget or pause logic |

- **Not chosen, and why:**
  - Header: OpenAlex does not document header auth, so it is unproven; hishel/requests-cache: duplicates the existing cache and bypasses the budget and pause rules.
- **Also found as:** F-B5-003

#### F-B5-008: EPO 'no hits' (404) answers are never cached, so empty searches repeat

Weight 52 · Optimisation · impact 2/5, reach 2/5, confidence 3/3 · found by B5 · merged as [R198](../arena/details-p2.md#r198)

- **Issue:** Novel or narrow ideas, the ones where 'no patents' matters most, hit EPO again on every scan and every lock waiter, using EPO's ~10 searches/minute fair-use and the daily counter for an answer already known.
- **Cause:** Ran scratchpad/arena/b5/dup.py: three sequential _get_json calls to EPO_SEARCH answering 404 -> 'sequential 404 repeats sent: 3'. sources.py:176-183 caches only 200; epo_patents treats 404 as 'none found' (sources.py:485-486), a valid answer.
- **Resolution:** build it in research/sources.py (_get_json: allow per-source cacheable statuses) using **Cache 404 as an empty result for EPO**. Smallest change, proven by the test, aligned with how epo_patents already reads 404.

| Option | Why it is a candidate | Cost | Advantages | Drawbacks |
|---|---|---|---|---|
| Cache 404 as an empty result for EPO | One condition in _get_json keyed on source; same TTL or a shorter one | free/open source | Removes repeat calls; works for lock waiters too | A newly published patent is missed until the entry expires (same as positive caching) |
| Generic negative cache with short TTL for all non-200 'definitive' statuses | Common HTTP caching practice (RFC 9111 allows caching 404) | free/open source | Covers future sources | Risk of caching transient errors if the status list is wrong |
| hishel HTTP cache for httpx | Maintained RFC 9111 cache transport for httpx | free/open source | Standard semantics, storage backends | Duplicates the custom Redis/disk cache; EPO responses lack cache headers, so needs forcing anyway |

- **Not chosen, and why:**
  - Generic negative cache: wider risk of caching transient failures; hishel: a second cache layer beside the existing one.

#### F-B5-007: 30 s lock expires before the 60 s fetch; failed holder leaves waiters to stampede

Weight 51 · Logic flaw · impact 2/5, reach 3/5, confidence 2/3 · found by B5 · merged as [R203](../arena/details-p2.md#r203)

- **Issue:** A slow OpenAlex answer outlives the lock, so a second worker fetches anyway and the first may then delete the second's lock if release is a plain DEL. When the holder gets a 429 or error, nothing lands in the cache, so every waiter wakes, misses and fetches; unless waiters re-run the pause and budget checks after waiting, they hit the source that just said 429 and extend its Retry-After.
- **Cause:** TASKS.md 2.2.1: 'Redis lock:{key} (30 seconds)'. scan.py:214 and novelty.py:81 create httpx.AsyncClient(timeout=60); papers() makes three sequential requests (sources.py:211-230). _get_json caches only status 200 (sources.py:176-180); 429/5xx return without writing anything.
- **Resolution:** build it in research/sources.py (_get_json order: cache -> lock -> pause -> budget -> fetch; waiters re-check cache then pause), core/redis.py using **redis-py Lock (redis.asyncio.lock.Lock)**. Already a dependency, token-safe release, and timeout set from the httpx timeout; combine with waiters re-checking cache and the existing pause key after the wait.

| Option | Why it is a candidate | Cost | Advantages | Drawbacks |
|---|---|---|---|---|
| Token lock with TTL above the request timeout and compare-and-delete release | Documented Redis single-instance lock pattern: SET key token NX PX, release by a Lua script comparing the token | free/open source | Lock outlives the fetch; no wrong release; small code | Lua script to maintain; TTL must track the client timeout setting |
| redis-py Lock (redis.asyncio.lock.Lock) | Built into the redis client already in use, token-based with extend() | free/open source | Correct release semantics out of the box; blocking_timeout for waiters | Waiters poll; still need the TTL and the post-failure re-check logic |
| Short negative marker after failure | The code already writes rs:neg:{source} for 429 pauses (sources.py:143) | free/open source | Waiters see the failure and stop instead of refetching | Only covers the failure side, not the TTL bug |

- **Not chosen, and why:**
  - Hand-written Lua lock: reimplements what redis-py ships; negative marker alone: leaves the lock expiring mid-fetch.

### 2.2.3 Reference data reloads without a restart

#### F-A2-010: Reference caches depend on each other across datasets; a per-loader clear leaves mixed versions

Weight 51 · Missing structure · impact 2/5, reach 3/5, confidence 2/3 · found by A2 · merged as [R208](../arena/details-p2.md#r208)

- **Issue:** Task 2.2.3 says 'a new version clears that loader's cache'. If the banking dataset changes, clearing only the banking loader leaves get_ecosystem serving the old branch counts until a restart, so founders see branch and zone figures that disagree between screens. Without a registry, whoever builds 2.2.3 must find every loader by hand, and new loaders will be missed.
- **Cause:** backend/app/ecosystem/index.py:53-58: the cached get_ecosystem() is built from get_branch_index() (banking dataset), so it bakes branch counts per PIN into the ecosystem object. About 25 @lru_cache loaders are spread across modules (grep: banking/branches.py:105, banking/catalogue.py:44, ecosystem/match.py:111 and 116, funding/investors.py:142, journey/engine.py:33, cohort/reference.py:30 and others), and there is no list of which dataset each one reads.
- **Resolution:** build it in a small module beside backend/app/core/redis.py (for example core/datasets.py) that registers each loader with the datasets it reads; used by 2.2.3 and by the ETags in 2.2.4 using **Dataset registry decorator: @dataset_cache('banking', 'ecosystem') wrapping lru_cache**. It makes the dependencies explicit, so 2.2.3 clears exactly the right caches and 2.2.4 gets its version from the same place.

| Option | Why it is a candidate | Cost | Advantages | Drawbacks |
|---|---|---|---|---|
| Dataset registry decorator: @dataset_cache('banking', 'ecosystem') wrapping lru_cache | Plain Python; keeps the existing lru_cache behaviour | free/open source | One call clears every loader that reads a dataset; the same registry gives 2.2.4 its ETag version and lists the datasets for operators | Touches every loader once |
| Clear all reference caches when any dataset version changes | functools cache_clear on a list | free/open source | Simplest, and never leaves mixed versions | Every update reparses about 11 MB of JSON per worker, even for a small schemes change |
| cachetools with a version-keyed cache (key includes dataset versions) | A widely used caching library | free/open source | A changed version automatically gives a new entry | A new dependency; old entries hold memory until evicted |

- **Not chosen, and why:**
  - Clear all: correct but reparses everything on every small data change; cachetools versioned keys: a new dependency, and memory grows across versions.

### 2.2.5 Clear expired research cache files

#### F-A2-009: Disk cache writes are not atomic, and a truncated file raises instead of missing

Weight 62 · Missing logic · impact 3/5, reach 2/5, confidence 3/3 · found by A2 · merged as [R160](../arena/details-p2.md#r160)

- **Issue:** A crash, a full disk, or two workers writing the same hash (more likely on Windows, where an open file can block a writer) leaves a half-written file. Every founder whose query hashes to it then loses the whole evidence scan for up to a week, with no log line naming the file.
- **Cause:** backend/app/research/sources.py:72-74: put() writes the file in place with write_text; get() (66-70) runs json.loads with no error handling, and aget does not catch it (only Redis errors are caught). Probe (scratchpad/a2/probe2.py): a truncated cache file made Cache.aget raise JSONDecodeError. Combined with the first flag, that exception fails the whole scan, and it keeps failing every time until the file is 7 days old.
- **Resolution:** build it in backend/app/research/sources.py (Cache.get, Cache.put) using **Write to a temp file and os.replace, and treat unreadable files as a miss (delete them)**. It fixes both truncation and concurrent writes in a few lines of standard library code, and 2.2.5's purge can sweep stray temp files.

| Option | Why it is a candidate | Cost | Advantages | Drawbacks |
|---|---|---|---|---|
| Write to a temp file and os.replace, and treat unreadable files as a miss (delete them) | The standard library atomic-rename pattern, atomic on NTFS and POSIX | free/open source | No dependency; corrupt entries heal themselves on the next fetch | Temp files need cleaning up if the process dies mid-write (2.2.5's purge can do it) |
| diskcache library (SQLite-backed) | A mature, popular pure-Python disk cache with expiry built in | free/open source | Atomicity, expiry and size limits (would also cover 2.2.5) | A new dependency and a migration of the existing .cache/research files |
| portalocker file locks around read and write | A cross-platform file-locking library | free/open source | Stops concurrent writers | Does not help with crash truncation; adds lock waits on reads |

- **Not chosen, and why:**
  - diskcache: a reasonable choice, but a new dependency and a data migration for a small fix; portalocker: does not cover crashes and slows reads.

#### F-A2-008: A disk-cache hit copied to Redis gets a fresh full TTL, so data can stay stale for twice as long

Weight 58 · Logic flaw · impact 2/5, reach 3/5, confidence 3/3 · found by A2 · merged as [R180](../arena/details-p2.md#r180)

- **Issue:** The research_cache_days rule ('responses are cached for N days', sources.py:10) is broken: an answer fetched almost a week ago can be served for nearly another week, so founders see paper and project counts up to about 14 days old while the design and runbook say 7.
- **Cause:** backend/app/research/sources.py:84-86: on a disk hit, aget writes the response to Redis with ex=self.ttl (research_cache_days in full) whatever the file's age. Probe (scratchpad/a2/probe2.py): a disk entry 6.9 days old was copied into Redis with a TTL of 7.0 days.
- **Resolution:** build it in backend/app/research/sources.py (Cache.aget) using **Copy with the remaining TTL (ttl minus file age)**. It restores the documented lifetime with the smallest change and keeps the cross-worker benefit of the copy.

| Option | Why it is a candidate | Cost | Advantages | Drawbacks |
|---|---|---|---|---|
| Copy with the remaining TTL (ttl minus file age) | The file mtime is already read in Cache.get | free/open source | Exact rule, a two-line change | Cache.get has to return the age as well as the value |
| Store fetched_at inside the cached JSON and check it on every read | A self-describing cache entry | free/open source | The age survives copies between layers and is visible to operators | Changes the cache format; old entries need handling |
| Do not copy disk hits into Redis | Removes the path | free/open source | Simplest | Other workers lose the shared hit that the copy exists for |

- **Not chosen, and why:**
  - fetched_at in JSON: a format change for the same result; no copy: loses the shared hit for other workers.

### 2.2.6 Nightly cache warming for registry domains

#### F-B5-009: Warmed keys won't match founder searches: cache keys are exact query strings

Weight 68 · Logic flaw · impact 3/5, reach 3/5, confidence 3/3 · found by B5 · merged as [R148](../arena/details-p2.md#r148)

- **Issue:** A warming run over 240 domains would fill the cache with keys founders almost never request, so 'common ideas answer from cache instantly' does not happen while the requests still cost budget; 5.4.2's hit rate would show it, but only after the spend.
- **Cause:** Ran build_queries (backend/app/research/terms.py:318-339) on registry fields: banana_value_added label -> 'banana value-added products', summary -> 'chips flour', trend_query -> 'banana flour processing'; founder sentences 'I want to make banana flour from waste bananas for bakeries' -> 'banana flour waste' and 'banana flour unit selling to bakeries in Trichy' -> 'banana flour'. sources.py:167 keys the cache on the exact URL+params; scan.py:211 also lets model-written queries override; novelty.paper_count uses different params (per_page 1, select id; sources.py:260) from papers() (per_page 25), so they never share an entry. Registry domains carry only trend_query, no per-source research queries (domains.json keys).
- **Resolution:** build it in scripts/ nightly warming step, research/sources.py (cache keying), research/scan.py using **Refresh-ahead of keys founders actually requested**. Uses demand the system already sees, so every warmed request is one a founder is likely to repeat; the domain pack can follow as a separate reference-data item.

| Option | Why it is a candidate | Cost | Advantages | Drawbacks |
|---|---|---|---|---|
| Refresh-ahead of keys founders actually requested | Record each cache key's request params and last-hit time (Redis sorted set or the disk cache's JSON) and re-fetch popular entries shortly before expiry | free/open source | Warms exactly what founders ask; no query guessing; budget spent only on proven demand | Needs the request params stored next to the hashed key; cold start for never-seen ideas |
| Domain evidence pack served by registry match | The registry already matches an idea to a domain; store a precomputed scan per domain (like signals.json) and show it as domain context while the live search runs | free/open source | Instant, query-independent evidence for known domains; reviewed in Git like other reference data | Domain-level, not idea-level, evidence; must be labelled as such |
| Normalise queries before keying (sorted, lower-cased terms) | Canonical key form is a standard cache technique | free/open source | Raises hit rate for reordered terms | Does not make 'banana flour waste' equal 'banana flour processing'; OpenAlex ranking can depend on order |
| Warm with build_queries(trend_query) as planned | TASKS.md 2.2.6 How | free/open source | Simple script | Proven key mismatch above |

- **Not chosen, and why:**
  - Domain pack: useful but a different feature (domain context, not cache warming); normalisation: cannot bridge different words; planned warming: the test shows its keys miss.

#### F-B5-010: Warming has no founder reserve in the shared daily cap and refetches a 7-day cache

Weight 61 · Missing logic · impact 3/5, reach 3/5, confidence 2/3 · found by B5 · merged as [R178](../arena/details-p2.md#r178)

- **Issue:** 'Under the cap' lets warming use the whole cap; a run after 05:30 IST (00:00 UTC) spends the day founders are about to use, and they get 'not searched'. Re-warming every night entries still valid for 7 days spends roughly 6 of 7 nights' requests for nothing (on the order of 240 x 3 OpenAlex calls a night).
- **Cause:** sources.py:146-161 — one cap per source per UTC day (time.gmtime, sources.py:119-120), shared by every caller; TASKS.md 2.2.6 'under the budget cap'. Cache TTL is research_cache_days=7 (config.py:116; sources.py:57, 68). 240 registry domains (domains.json + batch2 + batch3); papers() alone makes 3 OpenAlex requests (sources.py:211-230), patents 2 EPO searches (sources.py:482).
- **Resolution:** build it in nightly warming step (scripts/), research/sources.py (_over_budget with a caller class), core/config.py using **Warming share of the cap plus warm-only-if-expiring**. Guarantees founders' searches regardless of schedule and removes the 6-in-7 wasted refetches, with the counter that already exists.

| Option | Why it is a candidate | Cost | Advantages | Drawbacks |
|---|---|---|---|---|
| Warming share of the cap plus warm-only-if-expiring | A second limit (e.g. WARM_SHARE of the per-source cap) checked against the same budget:{source}:{date} counter, and a TTL check (Redis TTL / file mtime) before each fetch | free/open source | Founders keep a guaranteed share; no refetch of fresh entries; reuses existing counter | Needs a known per-source cap (see B5-01 flag 1) |
| Run warming just before the UTC reset | Budget resets at midnight UTC (runbook research-budget.md); spend leftover budget late in the UTC day (~03:00-05:00 IST) | free/open source | Uses budget that would otherwise expire unused | Still needs a stop rule so a busy day's tail is not consumed |
| Separate key for warming | Free OpenAlex key, which 2.2.6 already waits for | free tier | Separate budget from founders | Only if a second free key is acceptable under OpenAlex terms; same key for both is the likely case |

- **Not chosen, and why:**
  - Timing alone: no protection on busy days; separate key: uncertain under the provider's terms and does not stop the refetch waste.

### (no plan task) 

#### F-A2-006: One source's network error fails the whole evidence scan, not just that source

Weight 84 · Logic flaw · impact 4/5, reach 4/5, confidence 3/3 · found by A2 · merged as [R045](../arena/details-p2.md#r045)

- **Issue:** SYSTEM-DESIGN §9 says that when a research source fails, the other sources still work and the founder hears 'I could not search papers this time'. P2's 'Already built' line claims that source-outage handling exists. In fact one slow GitHub or ClinicalTrials response throws away the OpenAlex results already fetched, and the founder gets no evidence and no novelty check for that idea version. A timed-out request is also not counted as a failure anywhere, so the next turn repeats it.
- **Cause:** backend/app/research/sources.py:174: _get_json calls client.get() with no try, so httpx.ReadTimeout or ConnectError propagates out of papers/projects/trials/patents. backend/app/research/scan.py:234 and 243 and backend/app/research/novelty.py:83, 95 and 162 use asyncio.gather without return_exceptions, and scan.py has only a finally (257). Probe (scratchpad/a2/probe3.py): with a client whose GitHub call raises ReadTimeout and every other source answering 200, sources.projects raised ReadTimeout and scan.scan(...) raised ReadTimeout. In agents/ideation.py:369-382 the research job then fails as a whole: no scan, no novelty.
- **Resolution:** build it in backend/app/research/sources.py (_get_json returns a status for transport errors), backend/app/research/scan.py and novelty.py (gather), plus a test in backend/tests/unit using **Catch httpx.TransportError in _get_json and return a status**. It fixes every source and every caller in one place, keeps the existing status contract, and spends no extra free budget.

| Option | Why it is a candidate | Cost | Advantages | Drawbacks |
|---|---|---|---|---|
| Catch httpx.TransportError in _get_json and return a status | httpx exception hierarchy; matches the existing (status, data) contract that every source already maps to SourceResult 'error' | free/open source | One place fixes every source, including the novelty counts; existing 'error' notes then reach the founder as §9 describes | Must pick a pseudo-status (for example 599) and keep it out of the cache |
| asyncio.gather(return_exceptions=True) in scan and novelty | Standard library | free/open source | Isolates sources at the call site | Five call sites to change, and each must turn an exception into a SourceResult; easy to miss one |
| asyncio.TaskGroup with per-task wrappers | Python 3.11+ structured concurrency | free/open source | Clear cancellation semantics | A TaskGroup cancels its siblings on the first error unless every task is wrapped, so it is the same work as the first option, done in more places |
| tenacity retry around client.get | tenacity>=8.4 is already a dependency | free/open source | Rides out one-off timeouts | Retries spend the shared free daily budget; the final failure still has to be caught |

- **Not chosen, and why:**
  - gather(return_exceptions=True): five call sites and easy to miss one
  - TaskGroup: still needs per-task wrapping, so more code for the same result; tenacity: burns the free budget and still needs the catch.

## 2.3 Background jobs

### 2.3.1 Durable results and a shared queue

#### F-A2-011: A failed job is narrated as 'still searching', never reported, and re-run on every turn

Weight 84 · Logic flaw · impact 4/5, reach 4/5, confidence 3/3 · found by A2 · merged as [R032](../arena/details-p2.md#r032)

- **Issue:** The founder is promised evidence that never comes, and the Talk screen's 'started' tool chips never resolve. Each turn waits research_wait_s (3 s) again and spends the shared free source budget re-running a search that already failed, with no backoff and no honest 'I could not search this time' (SYSTEM-DESIGN §9, decision 0005 honesty).
- **Cause:** backend/app/agents/jobs.py:88-92: wait() returns False both for RUNNING and for FAILED. backend/app/agents/ideation.py:665-670 and 391-393 treat False as 'still searching' and say SEARCHING ('I will tell you what I find', line 452); _convene (409-411) turns a failed panel into PANEL_BUSY ('still looking at it', line 453). Board.notify runs only on success (jobs.py:75-79), so the notices stream never reports a failure. Board.start replaces a FAILED job (line 72), so each later turn starts it again. Probe (scratchpad/a2/probe4.py): a job raising TimeoutError gave wait -> False, state 'failed', 0 notices; after 4 turns the work had run 4 times. Combined with A2-02 flag 1 (one source's timeout fails the whole scan), this path is common.
- **Resolution:** build it in backend/app/agents/jobs.py (a distinct failed state for callers, a failure notice, retry backoff per session and kind), backend/app/agents/ideation.py (narrate the failure once), backend/app/routers/ideation.py (notices: a 'failed' event) using **Board.wait returns the state; failure notice; retry after a backoff**. It fixes the false promise and the budget burn now, inside the job board that decision 0010 chose, and the same three-state contract carries over when 2.3.1 moves jobs to a Redis queue.

| Option | Why it is a candidate | Cost | Advantages | Drawbacks |
|---|---|---|---|---|
| Board.wait returns the state; failure notice; retry after a backoff | Small change inside the existing Board (decision 0010); the state is already computed by Job.state | free/open source | Callers can say 'I could not search this time' once; the screen gets a failed notice; Board.start refuses a re-run until a backoff (for example 2 min, doubling) unless the idea version changed | Callers in ideation.py must handle three outcomes instead of two |
| tenacity retry inside the job, then fail | tenacity is already a dependency | free/open source | Recovers from short blips without involving the turn | Does not fix the misleading narration or the missing notice; retries spend the budget |
| arq or RQ job library with built-in retry and failure states | Mature Redis-backed job queues for Python (arq is asyncio-native) | free/open source | Retries, failure records and result expiry come built in, and it fits 2.3.1's Redis queue | Needs Redis, which is optional here; a larger change than the bug needs today |

- **Not chosen, and why:**
  - tenacity in the job: leaves the founder misled and the screen hanging; arq/RQ: right for 2.3.1 later, but it needs Redis, which must stay optional, so it cannot be the fix for the offline baseline.

#### F-A2-012: Job results and job entries are never expired; the planned results table has no retention

Weight 68 · Missing logic · impact 3/5, reach 3/5, confidence 3/3 · found by A2 · merged as [R078](../arena/details-p2.md#r078)

- **Issue:** Process memory grows with every conversation, and evidence tied to a founder's idea outlives both the 6-hour rule and an explicit delete. Once 2.3.1 makes results durable, they will escape the retention job and erasure unless they are named, which is a DPDP gap.
- **Cause:** backend/app/agents/jobs.py:58-60 and backend/app/agents/results.py:39: Board.jobs and MemoryResults._rows are pruned only by Board.forget on an explicit delete (jobs.py:117-124). Probe (scratchpad/a2/probe4.py): after 1000 sessions each ran one job, 1000 jobs and 1000 results (full scans with idea-derived queries) were still held. Sessions are hidden after 6 idle hours (store.py:29), but their results stay for the life of the process. A turn already in progress when DELETE arrives (agent_delete does not take _turn_locks, routers/ideation.py:313-319) can call board.start after forget(), leaving results for a deleted session. Task 2.3.1 adds a results table, but 3.2.4's retention and erasure list names 'sessions, transcripts, documents and consents', not results.
- **Resolution:** build it in backend/app/agents/jobs.py and results.py (expiry), backend/app/routers/ideation.py (delete takes the turn lock), and the 2.3.1 table (ON DELETE CASCADE to agent_sessions, listed in 3.2.4) using **Expire results with the session: FK with ON DELETE CASCADE in 2.3.1, plus an in-memory sweep by last access**. Results then follow the session's lifetime by construction, so erasure and retention cannot miss them, and memory is bounded before the table exists.

| Option | Why it is a candidate | Cost | Advantages | Drawbacks |
|---|---|---|---|---|
| Expire results with the session: FK with ON DELETE CASCADE in 2.3.1, plus an in-memory sweep by last access | PostgreSQL foreign keys (Alembic migration) plus a few lines in MemoryResults | free/open source | Erasure and retention of sessions automatically remove results; memory stays bounded today; delete takes the turn lock to close the late-start race | The results table needs the session row to exist first (true for every caller) |
| Redis keys with TTL for results | Redis is already used for live sessions | free/open source | Expiry for free | Redis is optional, and results would then live only in Redis, against the 'nothing only in Redis' rule |
| Nightly retention job deletes old result rows | The planned nightly job (5.4.4, 3.2.4.2) | free/open source | One place for all retention | Does not cover an explicit delete; leaves the in-memory growth today |

- **Not chosen, and why:**
  - Redis TTL: breaks the 'nothing only in Redis' rule and does nothing without Redis; nightly job only: misses explicit deletes and leaves memory growth until it exists.
- **Also found as:** F-B5-012, F-A1-015, F-A5-029

#### F-A2-013: No global limit on concurrent jobs: panel bursts of 7 model calls per session hit free-tier limits

Weight 67 · Missing logic · impact 3/5, reach 4/5, confidence 2/3 · found by A2 · merged as [R153](../arena/details-p2.md#r153)

- **Issue:** Gemini's free tier caps requests per minute. Two or three founders reaching the panel in the same minute send many parallel seat calls, so most seats fall back to rules, and any turn-wording call caught in the same burst gets 429s. Three of those open the Gemini breaker for 5 minutes for every founder, and the conversation drops to the slow local model or plain templates. Unconstrained research jobs also burst against the source budgets that 2.2.1 tries to protect.
- **Cause:** backend/app/agents/council/__init__.py:57-63 fires all seats at once (seven per panel run) through the judge provider; backend/app/agents/jobs.py:81 starts every job immediately with no semaphore or queue across sessions, and each research job opens its own httpx client (ideation.py:372). Seat failures fall back to rules silently (council/__init__.py:66-76). The turn's own wording calls share the Gemini provider, and ideation.py:801-803 counts each failure on the Gemini breaker (Breaker('gemini'), providers.py:423; threshold 3 in 60 s, cooldown 300 s, services/breaker.py:20). No setting limits model calls per minute (grep of providers.py and config.py).
- **Resolution:** build it in backend/app/agents/jobs.py (a concurrency limit per kind), backend/app/agents/providers.py (a per-provider rate limiter that seats and turns share, with turns taking priority) using **asyncio.Semaphore per job kind plus a token-bucket limiter per provider**. It keeps the panel parallel when there is room, protects live turns from panel bursts, needs no dependency, and fits the in-process board until 2.3.1 adds a shared queue.

| Option | Why it is a candidate | Cost | Advantages | Drawbacks |
|---|---|---|---|---|
| asyncio.Semaphore per job kind plus a token-bucket limiter per provider | Standard library, in-process like the job board; a token bucket is a few lines | free/open source | Panel seats queue instead of failing; turn calls can reserve tokens first; no dependency | Per process only; several workers need the Redis version (2.3.1) |
| aiolimiter library | A small, popular asyncio leaky-bucket rate limiter | free/open source | Tested limiter | A new dependency for what a few lines give; still per process |
| Redis-based limiter (for example a GCRA or token bucket in a Lua script) | Redis is already in the stack | free/open source | Shared across workers | Redis is optional; needs a local fallback anyway |
| Run panel seats one after another | A trivial change | free/open source | Fewest calls per second | The panel becomes about seven times slower for everyone, even when the limits are not near |

- **Not chosen, and why:**
  - aiolimiter: a dependency for a few lines
  - Redis limiter: Redis must stay optional, so it can only be a later layer; serial seats: slows every panel to avoid a peak-time problem.

## 2.4 Database layout and logs

### 2.4.2 Logs carry IDs and never idea text

#### F-A2-015: The fact-check gate logs every dropped model sentence verbatim; the request ID is client-controlled

Weight 74 · Logic flaw · impact 3/5, reach 4/5, confidence 3/3 · found by A2 · merged as [R108](../arena/details-p2.md#r108)

- **Issue:** Task 2.4.2 frames the gap as 'nothing checks'; in fact there is a concrete leak today. Each sentence the gate drops carries the founder's idea content into the logs (DPDP, SYSTEM-DESIGN §2 rule 3). A privacy test that 'runs a turn' will miss it unless the turn makes the gate drop something. Binding an unchecked client header into every log line also lets anyone inject arbitrary text or very long values into the logs.
- **Cause:** backend/app/agents/ideation.py:472: log.info('grounding.dropped', sentence=sentence). The sentence is model output written from the founder's idea, slots and evidence, and it is logged at INFO in every environment (core/logging.py renders all fields to JSON on stdout). backend/app/core/middleware.py:23 takes x-request-id from the client without a length or character check, echoes it in a response header (26) and puts it in error bodies (errors.py:54), and it is the ID that 2.4.2.1 plans to bind into every log line.
- **Resolution:** build it in backend/app/agents/ideation.py (log the reasons and a sentence hash, not the sentence), backend/app/core/middleware.py (accept x-request-id only if it matches a short UUID or token pattern), the 2.4.2.2 test (force a dropped sentence) using **Log problem codes plus a short hash of the sentence; validate x-request-id with a regex**. It removes the leak at its source and makes the request ID safe before 2.4.2.1 binds it everywhere. A redaction processor can still be added as a second layer.

| Option | Why it is a candidate | Cost | Advantages | Drawbacks |
|---|---|---|---|---|
| Log problem codes plus a short hash of the sentence; validate x-request-id with a regex | hashlib and re from the standard library; structlog already in use | free/open source | Keeps the signal operators need (how often and why sentences are dropped); no founder text; IDs stay safe to bind | Debugging a specific drop needs the session document, which already holds out['dropped'] |
| A structlog processor that redacts known text fields (sentence, text, idea, reply) | structlog processors are designed for this | free/open source | A safety net for future log calls too | Denylist-based, so a new field name slips through; does not cover the request ID |
| Log the sentence only at DEBUG | Logging levels | free/open source | One-word change | DEBUG gets switched on while chasing a bug, and then the text leaks again |

- **Not chosen, and why:**
  - Redaction processor alone: a denylist misses new fields and leaves the header issue
  - DEBUG level: leaks again whenever someone debugs.

### 2.4.3 Database connection pool per worker

#### F-A2-017: Rate limiter is per process, keyed by client IP, and keeps every key forever

Weight 58 · Missing logic · impact 2/5, reach 3/5, confidence 3/3 · found by A2 · merged as [R163](../arena/details-p2.md#r163)

- **Issue:** With several workers (2.4.3), each worker allows the full limit, so the real ceiling is workers times the limit. Behind a reverse proxy every founder shares one IP bucket, so one busy incubator batch locks everyone out at 100 requests a minute, and the long SSE turn and notice streams each count. The per-IP dict also grows without limit.
- **Cause:** backend/app/core/middleware.py:30-72: the limits sit in in-process dicts and deques. _per_client is a defaultdict, and a key is never removed once its deque empties (so it grows by one entry for every IP ever seen). The key is request.client.host when there is no user (46-47), with no forwarded-header handling, and the docstring (3-5) defers the shared version to an August 'Task 5.5' that the new plan does not carry. The limits come from config.py:125-126 (100 per client and 1000 global per minute). SYSTEM-DESIGN §4 lists 'rate limits' in Redis (L1, line 111). No task in TASKS.md covers rate limiting.
- **Resolution:** build it in backend/app/core/middleware.py (key pruning, trusted-proxy handling, an optional Redis counter like research/sources.py _over_budget), a new task beside 2.4.3 using **Prune empty keys, honour X-Forwarded-For only from configured trusted proxies, and use a Redis INCR+EXPIRE window when Redis is up**. It fixes the memory growth and the shared-bucket risk with patterns already in the codebase, and it keeps the offline single-process baseline working.

| Option | Why it is a candidate | Cost | Advantages | Drawbacks |
|---|---|---|---|---|
| Prune empty keys, honour X-Forwarded-For only from configured trusted proxies, and use a Redis INCR+EXPIRE window when Redis is up | Reuses the existing in-process limiter plus the Redis counter pattern already in research/sources.py:146-161; Uvicorn's --forwarded-allow-ips handles the proxy headers | free/open source | Bounded memory, correct client keys, a shared limit across workers, and it still works without Redis | A fixed window is coarser than a sliding one |
| slowapi (limits library) with a Redis or memory backend | A popular FastAPI and Starlette rate-limit extension | free/open source | Ready-made, with per-route limits | A new dependency; its decorator style changes the routers |
| Rate-limit in a reverse proxy (nginx limit_req) | The standard production pattern | free/open source | Off the app's CPU | There is no hosting or proxy decision yet (TASKS: a hosting decision); does not help local or single-machine runs |

- **Not chosen, and why:**
  - slowapi: a new dependency and a router refactor for the same behaviour; reverse proxy: waits on a hosting decision that has not been made.
- **Also found as:** F-A5-008, F-A3-011

