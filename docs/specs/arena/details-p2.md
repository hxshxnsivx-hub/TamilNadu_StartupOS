# Arena flags: P2 Platform details

Back to the [weighted table](../ARENA-FLAGS.md).

### R006

**Migration 0003 needs pgvector (dropped feature), blocking later migrations** · weight 94 · Logic flaw · impact 5/5, reach 4/5, confidence 3/3 · flags F-B2-009, F-A2-014

- **Evidence (B2):** backend/app/db/migrations/versions/0003_embeddings.py: op.execute('CREATE EXTENSION IF NOT EXISTS vector') and a Vector(1024) column; 0004 has down_revision 0003. Machine check: service postgresql-x64-18 is running, and 'C:\Program Files\PostgreSQL\18\share\extension\vector.control' does not exist. Only backend/docker/Dockerfile.postgres (postgis + pgvector) provides it. TASKS.md Dropped lists 'pgvector similarity tables' (offline embeddings are hashes).
- **Evidence (A2):** backend/app/db/migrations/versions/0003_embeddings.py:24 runs CREATE EXTENSION IF NOT EXISTS vector and builds an HNSW index, and 0004_agent_sessions.py:18 has down_revision = '0003_embeddings'. TASKS.md:982 (Dropped) removes 'pgvector similarity tables', and no app code reads the Embedding model (grep: only models/__init__.py:10 imports it). pgvector is available only in the custom image backend/docker/Dockerfile.postgres:6. Task 2.1.1 offers 'correct local PostgreSQL credentials' as the unblock, which on a stock PostgreSQL install without pgvector fails at 0003 before agent_sessions is created. .github/workflows/ci.yml has no database step yet, and 5.2.4's 'PostgreSQL service' would also need a pgvector image.

- **Why it matters:** 2.1.1 offers 'correct local PostgreSQL credentials' as the first unblock path. With the credentials fixed, 'alembic upgrade head' still fails at 0003, so agent_sessions is never created and auto mode keeps falling back to memory. The owner would keep fixing credentials for a failure that is really a missing extension, required by a feature the plan has dropped. Building pgvector on Windows needs Visual Studio build tools.
- **Where to build it:** backend/app/db/migrations/versions/0003_embeddings.py (make the extension conditional, or move embeddings off the main chain); docs/runbooks/sessions-not-saved.md; TASKS.md 2.1.1 'Waiting on' text

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Make 0003 conditional: create the vector extension and table only if pg_available_extensions lists vector | A common Alembic pattern with op.get_bind() and a catalog query | free/open source | Plain local PostgreSQL works; Docker keeps embeddings; no history rewrite | Schema differs by machine; the Embedding model must not be used where the table is missing |
| Separate Alembic branch (branch_labels='vector') for embeddings | Alembic's built-in multiple-branch support | free/open source | Main head has no pgvector dependency; embeddings can be opted into | Two heads to manage; CI must test both |
| Document Docker as the only supported database for development | docker-compose already builds postgis+pgvector | free/open source | No code change | Docker Desktop is the other blocked path in 2.1.1; heavy on a home laptop |
| Install pgvector on Windows (prebuilt binaries or build with MSVC) | pgvector publishes Windows build instructions | free/open source | Matches production schema | Manual, needs build tools, must be repeated for each PostgreSQL major version; for a dropped feature |

- **Recommended:** Make 0003 conditional: create the vector extension and table only if pg_available_extensions lists vector. Unblocks 2.1.1 on the database the owner actually has, without rewriting migration history, and matches the plan's decision that pgvector is not on the free path.
- **Ruled out:** Separate branch: right in principle, but two heads is more moving parts than a guard. Docker only: Docker Desktop is the other blocked path. Installing pgvector: manual build work for a dropped feature.

### R029

**Talk page forgets the saved session ID on any resume error, not only 404** · weight 84 · Logic flaw · impact 4/5, reach 4/5, confidence 3/3 · flags F-B5-018, F-B2-027

- **Evidence (B5):** frontend/src/pages/Talk.tsx:120-134 — getSession(id)...catch(() => save(null)) with comment 'expired or gone: start fresh'; save(null) removes the localStorage key (Talk.tsx:51-52). frontend/src/voice/agentClient.ts:88-108 throws the same Error for a network failure, a 500, a 503 or a 404. TASKS 1.1.4 covers replays, 409 and the resume preamble, not this.
- **Evidence (B2):** frontend/src/pages/Talk.tsx:121-135: getSession(id) ... .catch(() => save(null)), with the comment 'expired or gone: start fresh'. frontend/src/voice/agentClient.ts:107-109: any non-OK status or network failure rejects. Step 3 showed that a database error in SqlStore.get surfaces as an uncaught 500 (routers/ideation.py:271-274 catch only the 404 case).

- **Why it matters:** On a dropped 2G connection, a backend restart or a database outage, opening the Talk page erases the only pointer to the conversation; the session still exists (for 90 days once D4 lands) but the anonymous founder can never return to it. A longer lifetime is worthless while a transient error discards the key.
- **Where to build it:** frontend/src/voice/agentClient.ts (typed error with status), frontend/src/pages/Talk.tsx (forget only on 404, otherwise offer retry)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Error class carrying the HTTP status; forget only on 404 | Plain TypeScript: class HttpError extends Error { status } | free/open source | Tiny change, no dependency; network failures keep the key and show a retry | Every caller of json() sees the new type |
| TanStack Query with retry and status-aware handling | Popular React data-fetching library | free/open source | Retries, caching, error states | New dependency for one call; the app does not use it elsewhere |
| Keep a list of recent session ids instead of one | localStorage array with timestamps | free/open source | Founder can pick a past conversation | Does not fix the wrong deletion by itself |

- **Recommended:** Error class carrying the HTTP status; forget only on 404. Fixes the loss with a few lines and fits 1.1.4's 2G work, which edits the same files.
- **Ruled out:** TanStack Query: a dependency for one fetch; recent-ids list: a nice addition but still deletes on transient errors.

### R032

**A failed job is narrated as 'still searching', never reported, and re-run on every turn** · weight 84 · Logic flaw · impact 4/5, reach 4/5, confidence 3/3 · flags F-A2-011

- **Evidence (A2):** backend/app/agents/jobs.py:88-92: wait() returns False both for RUNNING and for FAILED. backend/app/agents/ideation.py:665-670 and 391-393 treat False as 'still searching' and say SEARCHING ('I will tell you what I find', line 452); _convene (409-411) turns a failed panel into PANEL_BUSY ('still looking at it', line 453). Board.notify runs only on success (jobs.py:75-79), so the notices stream never reports a failure. Board.start replaces a FAILED job (line 72), so each later turn starts it again. Probe (scratchpad/a2/probe4.py): a job raising TimeoutError gave wait -> False, state 'failed', 0 notices; after 4 turns the work had run 4 times. Combined with A2-02 flag 1 (one source's timeout fails the whole scan), this path is common.

- **Why it matters:** The founder is promised evidence that never comes, and the Talk screen's 'started' tool chips never resolve. Each turn waits research_wait_s (3 s) again and spends the shared free source budget re-running a search that already failed, with no backoff and no honest 'I could not search this time' (SYSTEM-DESIGN §9, decision 0005 honesty).
- **Where to build it:** backend/app/agents/jobs.py (a distinct failed state for callers, a failure notice, retry backoff per session and kind), backend/app/agents/ideation.py (narrate the failure once), backend/app/routers/ideation.py (notices: a 'failed' event)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Board.wait returns the state; failure notice; retry after a backoff | Small change inside the existing Board (decision 0010); the state is already computed by Job.state | free/open source | Callers can say 'I could not search this time' once; the screen gets a failed notice; Board.start refuses a re-run until a backoff (for example 2 min, doubling) unless the idea version changed | Callers in ideation.py must handle three outcomes instead of two |
| tenacity retry inside the job, then fail | tenacity is already a dependency | free/open source | Recovers from short blips without involving the turn | Does not fix the misleading narration or the missing notice; retries spend the budget |
| arq or RQ job library with built-in retry and failure states | Mature Redis-backed job queues for Python (arq is asyncio-native) | free/open source | Retries, failure records and result expiry come built in, and it fits 2.3.1's Redis queue | Needs Redis, which is optional here; a larger change than the bug needs today |

- **Recommended:** Board.wait returns the state; failure notice; retry after a backoff. It fixes the false promise and the budget burn now, inside the job board that decision 0010 chose, and the same three-state contract carries over when 2.3.1 moves jobs to a Redis queue.
- **Ruled out:** tenacity in the job: leaves the founder misled and the screen hanging; arq/RQ: right for 2.3.1 later, but it needs Redis, which must stay optional, so it cannot be the fix for the offline baseline.

### R045

**One source's network error fails the whole evidence scan, not just that source** · weight 84 · Logic flaw · impact 4/5, reach 4/5, confidence 3/3 · flags F-A2-006

- **Evidence (A2):** backend/app/research/sources.py:174: _get_json calls client.get() with no try, so httpx.ReadTimeout or ConnectError propagates out of papers/projects/trials/patents. backend/app/research/scan.py:234 and 243 and backend/app/research/novelty.py:83, 95 and 162 use asyncio.gather without return_exceptions, and scan.py has only a finally (257). Probe (scratchpad/a2/probe3.py): with a client whose GitHub call raises ReadTimeout and every other source answering 200, sources.projects raised ReadTimeout and scan.scan(...) raised ReadTimeout. In agents/ideation.py:369-382 the research job then fails as a whole: no scan, no novelty.

- **Why it matters:** SYSTEM-DESIGN §9 says that when a research source fails, the other sources still work and the founder hears 'I could not search papers this time'. P2's 'Already built' line claims that source-outage handling exists. In fact one slow GitHub or ClinicalTrials response throws away the OpenAlex results already fetched, and the founder gets no evidence and no novelty check for that idea version. A timed-out request is also not counted as a failure anywhere, so the next turn repeats it.
- **Where to build it:** backend/app/research/sources.py (_get_json returns a status for transport errors), backend/app/research/scan.py and novelty.py (gather), plus a test in backend/tests/unit

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Catch httpx.TransportError in _get_json and return a status | httpx exception hierarchy; matches the existing (status, data) contract that every source already maps to SourceResult 'error' | free/open source | One place fixes every source, including the novelty counts; existing 'error' notes then reach the founder as §9 describes | Must pick a pseudo-status (for example 599) and keep it out of the cache |
| asyncio.gather(return_exceptions=True) in scan and novelty | Standard library | free/open source | Isolates sources at the call site | Five call sites to change, and each must turn an exception into a SourceResult; easy to miss one |
| asyncio.TaskGroup with per-task wrappers | Python 3.11+ structured concurrency | free/open source | Clear cancellation semantics | A TaskGroup cancels its siblings on the first error unless every task is wrapped, so it is the same work as the first option, done in more places |
| tenacity retry around client.get | tenacity>=8.4 is already a dependency | free/open source | Rides out one-off timeouts | Retries spend the shared free daily budget; the final failure still has to be caught |

- **Recommended:** Catch httpx.TransportError in _get_json and return a status. It fixes every source and every caller in one place, keeps the existing status contract, and spends no extra free budget.
- **Ruled out:** gather(return_exceptions=True): five call sites and easy to miss one; TaskGroup: still needs per-task wrapping, so more code for the same result; tenacity: burns the free budget and still needs the catch.

### R058

**Programme cohort aggregates use store.get and drop sessions idle over 6 hours** · weight 78 · Logic flaw · impact 4/5, reach 3/5, confidence 3/3 · flags F-B2-005, F-B3-004, F-A2-003

- **Evidence (B2):** backend/app/routers/cohort.py:40 loads sessions with store.get. backend/app/agents/store.py:46-47 _expired (IDLE_EXPIRY = 6 h, :29) returns None for older sessions in MemoryStore:64, SqlStore:95 and CachedStore:228. Probe (scratchpad arena/b2probe2.py): 6 consenting sessions last active 7 hours ago give 0 found and shown=False.
- **Evidence (B3):** routers/cohort.py:39 reads sessions with store.get. Every store's get returns None for a session idle longer than IDLE_EXPIRY, which is 6 hours (agents/store.py:29; applied at :65, :95 and :213). sessions_found then undercounts with no reason given, and programme_cohort sees fewer than 5 founders and shows nothing (programme.py:42-50).
- **Evidence (A2):** backend/app/routers/cohort.py:39-40 loads each programme session with store.get(), one at a time. store.py:48-49, 65, 95 and 213 return None for any session idle more than 6 hours. Probe: a MemoryStore session saved with updated_at 7 h ago returns None from get(). Through CachedStore, every cohort read also copies the session into Redis for 6 hours (store.py:214-216), up to 500 per call, one after another.

- **Why it matters:** A programme manager looking at yesterday's batch sees 'fewer than 5 founders agreed', even when all of them did. 2.1.3 frames the 6-hour rule as a resume problem for founders, but the cohort view (5.5.3) and a nightly rebuild (5.5.5.2) that reuses the store reader would be empty almost always. That is a wrong answer, not a missing feature.
- **Where to build it:** backend/app/agents/store.py (a reader for analytics that skips the live-session expiry but keeps retention); routers/cohort.py; the 5.5.5.2 rebuild script

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Separate store method list_for_analytics(ids or since) without idle expiry | Small change to the existing SessionStore protocol; the same decode path | free/open source | Live-session expiry stays where D4 puts it (Redis copy); analytics sees all retained sessions | Two read paths to keep consistent (decode and upgrade must be shared) |
| Resolve D4 first (expiry only on the Redis copy) and keep store.get | The plan's recommendation for D4 | free/open source | No new method | Blocked on an owner decision; MemoryStore still expires, so offline development stays wrong |
| Rebuild reads agent_sessions with SQL directly (SELECT data WHERE last_active > retention) | SQLAlchemy Core; a set-based nightly job | free/open source | Fast, one query for the batch | Bypasses the decode/upgrade function unless it calls it explicitly; no memory-store equivalent |

- **Recommended:** Separate store method list_for_analytics(ids or since) without idle expiry. Fixes the view now without waiting on D4, keeps the 2.1.4 decode and upgrade in one place, and works on the memory store too.
- **Ruled out:** Waiting on D4: blocks a wrong answer on an owner decision, and the memory store would still hide sessions. Direct SQL: skips the format upgrade that step 2.1.4 needs on every read, and has no offline path.

### R059

**agent_sessions.user_id is a free string with no FK to users; no user-to-sessions link** · weight 78 · Missing structure · impact 4/5, reach 3/5, confidence 3/3 · flags F-A3-008, F-A2-016, F-B5-015

- **Evidence (A3):** backend/app/models/agent_session.py:24 user_id String(64) nullable=False, default 'anon' (agents/ideation.py:118); migration 0004_agent_sessions.py:27 has no ForeignKey, while users.user_id is a UUID (0002_users.py:27).
- **Evidence (A2):** backend/app/db/migrations/versions/0004_agent_sessions.py and models/agent_session.py:24: user_id String(64), NOT NULL, with the sentinel 'anon' (agents/ideation.py:118); no foreign key. backend/app/db/migrations/versions/0002_users.py:26-30: users.user_id is a PGUUID. The types differ, so no foreign key or ON DELETE CASCADE can link sessions to founders.
- **Evidence (B5):** backend/app/models/agent_session.py:24 user_id String(64), no ForeignKey; agents/ideation.py:118, 203 default user_id 'anon' and routers/ideation.py never passes a user, so every row today has user_id='anon'. models/user.py:24-28 users.founder_id -> founders ON DELETE SET NULL, while profile.py:24, startup.py:22, document.py:25 cascade from founders, not from users.

- **Why it matters:** 'Delete by user across tables' has no relation to follow: deleting a user leaves the founder, profile, startups and documents (the FK points the other way), and sessions are matched only by a free string. A delete-all-for-user run on 'anon' (or on any user before 3.1.1 rewrites old rows) would erase every anonymous founder's conversation.
- **Where to build it:** db/migrations (FK or explicit erasure map), models/agent_session.py, models/user.py, the 3.2.4.1 service

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Explicit erasure service with a table map and a guard on 'anon' | One function listing every table and its user/founder key, run in one transaction, refusing sentinel ids; tested against the model metadata so a new table without an entry fails CI | free/open source | Works across schemas (2.4.1) and JSON documents; the CI check keeps it complete | Map must be maintained |
| Foreign keys with ON DELETE CASCADE from users | PostgreSQL referential actions via Alembic | free/open source | Database enforces completeness | agent_sessions.user_id is a string with 'anon' rows, so it cannot reference users.user_id (UUID) without a nullable column and data migration; Redis and in-memory copies are outside the database anyway |
| Soft delete flag | August Req 6.1 | free/open source | Reversible | Ruled out by D12 (erasure) |

- **Recommended:** Explicit erasure service with a table map and a guard on 'anon'. It must reach non-database copies anyway (next flag), handles the string user_id and sentinel safely, and a metadata test stops new tables being forgotten; nullable FKs can be added later as a second guard.
- **Ruled out:** Cascade FKs alone: impossible on the current string column with 'anon' rows and blind to Redis; soft delete: contradicts D12.

### R061

**SqlStore.save never updates user_id; claimed session stays 'anon'** · weight 78 · Logic flaw · impact 4/5, reach 3/5, confidence 3/3 · flags F-B5-020, F-A2-005

- **Evidence (B5):** backend/app/agents/store.py:115-126 — save() updates version, idea_version, private, last_active and data, not user_id; the column is written only at create (store.py:148-152). The owner also lives in the document (agents/ideation.py:118, 148, 178) and in the elicitation state (elicitation/engine.py:117, session.py:86). Every session is created as 'anon' (ideation.py:203; routers/ideation.py:288-293 passes no user).
- **Evidence (A2):** backend/app/agents/store.py:114-126: the UPDATE sets version, idea_version, private, last_active and data, but not user_id. user_id is written only by _row() at create (148-152). The indexed column (models/agent_session.py:24) is what lookups by founder and erasure by user (3.2.4) will query.

- **Why it matters:** The natural claim (set s.user_id, then save) changes the JSON document but leaves the indexed agent_sessions.user_id at 'anon', so lookups and the delete-by-user of 3.2.4 (B5-05 flag 2) miss every claimed conversation, and the elicitation copy still says 'anon'. A founder's erasure request would leave their conversations behind.
- **Where to build it:** agents/store.py (a claim operation that updates column and document together), agents/ideation.py and elicitation/session.py (one owner field)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Dedicated store.claim(session_id, user_id) with a conditional UPDATE | SQLAlchemy UPDATE ... WHERE session_id=:id AND user_id='anon' setting column and JSON fields in one statement, plus Redis copy drop | free/open source | Atomic, updates every copy, refuses re-claiming someone else's session, testable | One more store method in three implementations |
| Include user_id in SqlStore.save's values | One-line change | free/open source | Column follows the document on every save | Any save could move ownership; no guard against hijack; elicitation copy still separate |
| Drop the column and query JSONB (data->>'user_id') | PostgreSQL JSONB with an expression index | free/open source | Single source of truth | Loses the plain column the migration and 5.5.5 table split rely on |

- **Recommended:** Dedicated store.claim(session_id, user_id) with a conditional UPDATE. Makes ownership a deliberate, atomic, one-way transition that keeps the column, the document and Redis consistent, which erasure depends on.
- **Ruled out:** Save includes user_id: lets any save rewrite the owner; JSONB-only: undoes the indexed column the design and later migrations use.

### R071

**The 2.1.1 integration test skips on any setup error and bypasses migrations** · weight 78 · Logic flaw · impact 4/5, reach 3/5, confidence 3/3 · flags F-B2-010

- **Evidence (B2):** backend/tests/integration/test_agent_store.py:22-29: SELECT 1 and Base.metadata.create_all (all models, including Embedding with a Vector column, app/models/__init__.py:10) are in one try, and any exception becomes pytest.skip('database unavailable'). The same pattern is in tests/integration/test_auth_api.py:27. The test uses the app engine (app/db/session.py:14, the developer database), not a test database.

- **Why it matters:** On the local PostgreSQL 18, correct credentials still make create_all fail on 'type vector does not exist', and the test reports a skip, which reads as 'no database'. 2.1.1.2 ('the database integration test passes') can never pass or fail honestly there. Because the test builds tables with create_all instead of the migrations, a pass would not prove migration 0004 matches the model either. Run against a fresh developer database before 'alembic upgrade', it creates every table without alembic_version, so the next upgrade fails at 0002 with DuplicateTable.
- **Where to build it:** backend/tests/integration/ (a conftest with a dedicated test database that runs 'alembic upgrade head'); skip only on connection errors

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| conftest fixture: dedicated test DB, alembic upgrade head, skip only on connection refused | Standard pytest + Alembic practice (alembic.command.upgrade from a fixture) | free/open source | Tests the real migration chain; a schema error fails loudly; the dev data is untouched | Needs a second database name and a CREATE DATABASE right |
| testcontainers-python with the project's Postgres image | Popular library; disposable container per run | free/open source | Clean, reproducible, matches the Docker image | Needs Docker, the blocked path on this machine |
| pytest-postgresql (spawns a temporary local server) | Mature pytest plugin using the installed binaries | free/open source | No Docker; uses the PostgreSQL 18 already installed | Still lacks pgvector unless 0003 is made conditional; Windows path setup |
| Keep create_all but narrow the except to OperationalError | Minimal change | free/open source | Honest failure on schema errors | Still does not test the migrations, and still writes to the dev database |

- **Recommended:** conftest fixture: dedicated test DB, alembic upgrade head, skip only on connection refused. Makes 2.1.1.2 mean what it says (the migrations produce a working store), works on the installed PostgreSQL once 0003 is guarded, and shares setup with the CI round trip planned in 5.2.4.
- **Ruled out:** testcontainers: depends on Docker, which is blocked here. pytest-postgresql: workable but more setup on Windows for the same result. Narrowed except: honest, but it still skips the migrations and pollutes the dev database.

### R073

**Under D4, CachedStore re-hides a session it just loaded: resume works, next turn 404s** · weight 78 · Logic flaw · impact 4/5, reach 3/5, confidence 3/3 · flags F-B5-017

- **Evidence (B5):** Ran scratchpad/arena/b5/lifetime.py: inner store without idle hiding (as D4 asks for PostgreSQL), CachedStore with a fake Redis, session updated_at 10 h ago -> 'first read (resume): True \| second read (the turn): False'. store.py:211-213 returns None when the Redis copy is _expired without falling back to the database; store.py:214-216 copies a database hit into Redis with a fresh 6 h TTL but the old updated_at.

- **Why it matters:** Implementing 2.1.3.1 the obvious way (drop _expired from SqlStore only) lets the Talk page resume a 10-hour-old conversation and then answer the founder's first turn with 'Session not found or expired' (routers/ideation.py:272-274). The bug appears only with Redis on, so tests on MemoryStore miss it.
- **Where to build it:** agents/store.py (CachedStore.get, _expired), tests with the fake Redis

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Expiry only by Redis TTL in CachedStore; database rule separate | Let the Redis key's own TTL express the 6 h copy lifetime and remove the updated_at check from the cache layer; SqlStore applies the retention rule | free/open source | One clock per layer; a cache miss always falls through to the truth | Must also change MemoryStore so tests mirror deployment |
| Fall through to the database when the copy looks expired | Treat an expired copy as a miss: drop it and read inner | free/open source | Minimal change | Keeps a redundant check and an extra round trip per turn for old sessions |
| Make the lifetime a store policy object shared by all three stores | Strategy pattern: one Lifetime(hide_after, layer) used by Memory, Sql and Cached stores | free/open source | Single place to apply D4 and the saved-idea exception (2.1.3.2) | More structure for a two-rule decision |

- **Recommended:** Expiry only by Redis TTL in CachedStore; database rule separate. Matches D4's wording ('6 h for the Redis copy, 90 days in PostgreSQL') literally and makes the proven failure impossible; add the script's scenario as a test.
- **Ruled out:** Fall-through: patches the symptom and keeps two clocks in the cache layer; policy object: more structure than one decision needs.

### R075

**Database outage after startup gives 500s instead of an in-memory fallback** · weight 77 · Missing logic · impact 4/5, reach 4/5, confidence 2/3 · flags F-A2-002, F-B2-012

- **Evidence (A2):** SYSTEM-DESIGN.md:315 (§9) says that when PostgreSQL fails, conversations are held in memory and the founder sees 'This conversation can't be saved right now'. In the code, backend/app/agents/store.py:236-249 checks the database once (auto mode) and keeps that choice for the life of the process. SqlStore.get/save/create (86-131) have no error handling, and backend/app/core/errors.py:96-103 turns any OperationalError into a generic 500 'An unexpected error occurred'. The 'saved' flag (routers/ideation.py:303) is computed only when the session starts.
- **Evidence (B2):** backend/app/agents/store.py:270-283: the store is chosen once per process; after that, SqlStore.get/save (:85-125) raise asyncpg or SQLAlchemy errors uncaught. backend/app/routers/ideation.py:271-285 (_load/_save) catch only VersionConflict. The P2 'Already built' line claims failure handling for Redis, model and source outages (SYSTEM-DESIGN 9) but not the database. Conversely, if the database is down at the first conversation, memory is chosen until restart (runbook sessions-not-saved.md).

- **Why it matters:** If PostgreSQL restarts or drops connections during the day, every live founder's next turn fails with a generic error and the conversation cannot be reached. That is worse than the degraded mode the design promises, and the Talk page keeps saying the conversation is saved.
- **Where to build it:** backend/app/agents/store.py (a wrapper around SqlStore), backend/app/routers/ideation.py ('saved' on each turn), docs/runbooks/sessions-not-saved.md

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| FallbackStore wrapper with a small hand-rolled circuit breaker | Implements the same Protocol as the existing stores and degrades the same way core/redis.py already does | free/open source | On a database error it keeps the session in a MemoryStore, reports 'saved: false' for that turn, re-checks the database every N seconds, and writes held sessions back through the version check | Write-back must handle version conflicts; memory copies are per worker |
| tenacity retry, then 503 with Retry-After | tenacity>=8.4 is already in requirements.txt | free/open source | Very small; rides out short blips | Does not deliver the §9 behaviour; a long outage still stops every conversation |
| aiobreaker or pybreaker library | Mature circuit-breaker libraries for Python | free/open source | Tested breaker states | A new dependency for a few lines of state, and the memory fallback still has to be written by hand |
| Hold the session in the Redis copy while the database is down | CachedStore already keeps a Redis copy | free/open source | Survives a restart of one worker | Breaks the rule that nothing is stored only in Redis (core/redis.py:3); no help when Redis is absent |

- **Recommended:** FallbackStore wrapper with a small hand-rolled circuit breaker. It delivers exactly what SYSTEM-DESIGN §9 promises, reuses MemoryStore and the version check, and adds no dependency.
- **Ruled out:** tenacity retry: only hides short blips, and long outages still fail; aiobreaker/pybreaker: adds a dependency, and the fallback is still hand-written; Redis holding: breaks the 'nothing only in Redis' rule and does nothing without Redis.

### R083

**'Saved' is sent only at start, and when true it hides the 6-hour idle expiry** · weight 74 · Logic flaw · impact 3/5, reach 4/5, confidence 3/3 · flags F-B2-028

- **Evidence (B2):** backend/app/routers/ideation.py:303 returns 'saved' only from agent_start. agent.snapshot (resume, routers/ideation.py:306-309) has no 'saved' field, so Talk.tsx:62 stays null after a resume and the banner (:409-411) never shows. The banner text says only 'not being saved (no database); it will be lost on restart'. backend/app/agents/store.py:29/46-47: even in PostgreSQL the session is gone after 6 idle hours.

- **Why it matters:** After a resume the founder gets no persistence signal at all, even on the memory store. With 2.1.2's fix, 'saved: true' shows no warning, yet the conversation (and the roadmap a founder will track, step 6) disappears the next day. The founder is misled either way, and 2.1.3 (D4) may change the rule again with nothing tying the message to it.
- **Where to build it:** backend/app/routers/ideation.py (return 'saved' and 'kept_until' in both start and snapshot, computed from the store and the lifetime rule); frontend Talk.tsx banner text from that value; tests

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Return {saved, kept_until} on start and resume, derived from the store's durability and the lifetime constant | Small API addition; IDLE_EXPIRY already exists as one constant | free/open source | An honest banner that follows D4 automatically | A frontend change and a schema change in agentClient types |
| Add 'saved' to the snapshot only | The minimal fix | free/open source | Fixes the missing banner on resume | Still silent about the 6-hour loss |
| Static banner text explaining the idle limit | Copy-only change | free/open source | Trivial | Drifts when D4 changes the rule |

- **Recommended:** Return {saved, kept_until} on start and resume, derived from the store's durability and the lifetime constant. Tells the founder the truth in both entry paths and stays correct when D4 lands, because it comes from the same constant the store enforces.
- **Ruled out:** Snapshot only: half the truth. Static text: drifts from the rule it describes.

### R098

**No single-flight without Redis, although the app runs as one process by default** · weight 74 · Missing logic · impact 3/5, reach 4/5, confidence 3/3 · flags F-B5-006

- **Evidence (B5):** Ran scratchpad/arena/b5/dup.py (httpx.MockTransport, set_redis(None)): 10 concurrent sources.paper_count calls for the same query -> 'concurrent same-key requests sent: 10'. sources.py:167-175 checks the cache then fetches with no coordination. TASKS.md 2.2.1 How: 'without Redis, no lock'. Redis is optional (core/redis.py:3-5) and jobs run in-process, one server (agents/jobs.py:20-21, decision 0010).

- **Why it matters:** The ten-sessions case 2.2.1 exists for happens inside one process today, so the planned Redis-only lock does nothing in the default free setup; each duplicate also increments budget:{source}:{date} (sources.py:146-161), so 5.4.2 would report ten requests of budget for one logical search and RESEARCH_DAILY_LIMIT trips ten times faster.
- **Where to build it:** research/sources.py (_get_json), with the Redis lock as the cross-process layer on top

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| In-process single-flight map of asyncio futures | Standard asyncio pattern (dict key -> Future/Task) in a few lines; no dependency | free/open source | Covers the actual deployment; waiters get the result with zero extra requests or budget; composes with a Redis lock for several workers | Per process only; must remove the entry on failure so the next caller retries |
| aiocache with a lock decorator | Maintained asyncio cache library with in-memory and Redis backends and RedLock/OptimisticLock helpers | free/open source | Lock and cache in one abstraction for both modes | Replaces the hand-written two-layer Cache and its key scheme; larger change than the task |
| Redis SET NX lock only (as planned) | TASKS.md 2.2.1 design | free/open source | Works across workers | Does nothing when Redis is off, which is the default; costs a round trip even in one process |
| Job-board level dedupe by query | agents/jobs.py already dedupes by (session, kind) | free/open source | Reuses existing structure | Keys by session, not by request; two sessions with the same query still fetch twice, and novelty/scan share keys below job level |

- **Recommended:** In-process single-flight map of asyncio futures. Fixes the duplicate fetches in the setup that actually runs, with no dependency, and the Redis lock can wrap it later for several workers.
- **Ruled out:** aiocache: rewrites the existing cache for a coordination problem; Redis-only lock: inactive in the default free setup; job-board dedupe: wrong key, sessions differ while requests match.

### R108

**The fact-check gate logs every dropped model sentence verbatim; the request ID is client-controlled** · weight 74 · Logic flaw · impact 3/5, reach 4/5, confidence 3/3 · flags F-A2-015

- **Evidence (A2):** backend/app/agents/ideation.py:472: log.info('grounding.dropped', sentence=sentence). The sentence is model output written from the founder's idea, slots and evidence, and it is logged at INFO in every environment (core/logging.py renders all fields to JSON on stdout). backend/app/core/middleware.py:23 takes x-request-id from the client without a length or character check, echoes it in a response header (26) and puts it in error bodies (errors.py:54), and it is the ID that 2.4.2.1 plans to bind into every log line.

- **Why it matters:** Task 2.4.2 frames the gap as 'nothing checks'; in fact there is a concrete leak today. Each sentence the gate drops carries the founder's idea content into the logs (DPDP, SYSTEM-DESIGN §2 rule 3). A privacy test that 'runs a turn' will miss it unless the turn makes the gate drop something. Binding an unchecked client header into every log line also lets anyone inject arbitrary text or very long values into the logs.
- **Where to build it:** backend/app/agents/ideation.py (log the reasons and a sentence hash, not the sentence), backend/app/core/middleware.py (accept x-request-id only if it matches a short UUID or token pattern), the 2.4.2.2 test (force a dropped sentence)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Log problem codes plus a short hash of the sentence; validate x-request-id with a regex | hashlib and re from the standard library; structlog already in use | free/open source | Keeps the signal operators need (how often and why sentences are dropped); no founder text; IDs stay safe to bind | Debugging a specific drop needs the session document, which already holds out['dropped'] |
| A structlog processor that redacts known text fields (sentence, text, idea, reply) | structlog processors are designed for this | free/open source | A safety net for future log calls too | Denylist-based, so a new field name slips through; does not cover the request ID |
| Log the sentence only at DEBUG | Logging levels | free/open source | One-word change | DEBUG gets switched on while chasing a bug, and then the text leaks again |

- **Recommended:** Log problem codes plus a short hash of the sentence; validate x-request-id with a regex. It removes the leak at its source and makes the request ID safe before 2.4.2.1 binds it everywhere. A redaction processor can still be added as a second layer.
- **Ruled out:** Redaction processor alone: a denylist misses new fields and leaves the header issue; DEBUG level: leaks again whenever someone debugs.

### R114

**Redis copy is written without a version guard: a deleted session can come back** · weight 72 · Logic flaw · impact 4/5, reach 2/5, confidence 3/3 · flags F-A2-001

- **Evidence (A2):** backend/app/agents/store.py:206-217 and 231-233. CachedStore.get fills Redis (_put) after reading the database, and delete() drops the Redis key BEFORE deleting the row, so a read already in flight puts the old copy back. Probe (scratchpad/a2/probe.py, CachedStore over a MemoryStore with 50 ms read latency, run from backend/): delete returned True, and get() still returned the session from Redis afterwards. The same unguarded _put (store.py:195-200) lets a slow read overwrite a newer copy written by a concurrent save, which gives a spurious 409 on the next turn.

- **Why it matters:** After a founder deletes a conversation (1.1.7) or an erasure request runs (3.2.4), the transcript stays readable through GET /ideation/agent/sessions/{id} and the cohort endpoint for up to 6 hours. That breaks the erasure promise (SYSTEM-DESIGN §3.2, DPDP). In the stale-overwrite case, a normal turn becomes a 409 and a reload.
- **Where to build it:** backend/app/agents/store.py (CachedStore._put, get, delete), backend/tests/unit/test_redis_layer.py

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Lua compare-and-set put plus a tombstone | redis-py register_script; redis>=5.0 is already a dependency; this is the standard Redis pattern for version-guarded writes | free/open source | One atomic script writes sess:{id} only when there is no tombstone and the stored version is lower. delete() deletes the row first, then writes sess:gone:{id} with a 6 h TTL. Fixes both races in one round trip. | A small Lua script to maintain; the FakeRedis used in tests needs an eval stub |
| Reorder delete (delete the row, then drop the key) | Minimal change to the existing class | free/open source | A few lines | Still racy: a read that started before the row delete can finish after the drop. Does not fix the stale overwrite. |
| WATCH/MULTI optimistic transaction | redis-py pipeline with watch, a documented Redis feature | free/open source | No Lua | Retry loops in Python and more round trips per read; awkward with the async pipeline |
| Write-only cache (fill Redis on save and create only, never on read) | A cache-aside variant that removes the read-fill path | free/open source | Removes the resurrect path for reads | A save racing a delete can still recreate the key; lower hit rate after a restart |

- **Recommended:** Lua compare-and-set put plus a tombstone. It is the only option that closes both the delete-resurrect race and the stale-overwrite race atomically, in one network round trip, using a library already installed.
- **Ruled out:** Reorder: narrows the window but does not close it, and leaves the stale overwrite; WATCH/MULTI: the same guarantee, but with retry loops and more round trips; Write-only cache: a concurrent save can still bring back a deleted session.

### R115

**Migration 0001 builds tables from live ORM models; migration CI lacks drift check** · weight 71 · Logic flaw · impact 4/5, reach 3/5, confidence 2/3 · flags F-B2-011, F-A5-017

- **Evidence (B2):** backend/app/db/migrations/versions/0001_initial.py:15 imports app.models.Base and :31-32 run Base.metadata.create_all(tables=['founders','startups','documents','profile_completeness'], checkfirst=True); its docstring says this keeps it from drifting. SYSTEM-DESIGN 5.2: each change is an explicit migration.
- **Evidence (A5):** backend/app/db/migrations/versions/0003_embeddings.py:24 runs CREATE EXTENSION vector; local compose builds docker/Dockerfile.postgres (PostGIS + pgvector), which a GitHub Actions services: entry cannot build, and the stock postgres image has no pgvector. 0001_initial.py:27-33 creates founders/startups/documents/profile_completeness with Base.metadata.create_all from the current ORM, so after any model change a fresh database gets the new shape from 0001 and a later add-column migration fails. No alembic check (model vs migrations) exists; nothing under backend/tests references alembic.

- **Why it matters:** When 3.1.2 (or 3.2.2's encrypted columns) adds a column to Founder or Startup with its own add_column migration, a fresh database running 'upgrade head' creates the new column in 0001 and then fails in the later migration with DuplicateColumn. Old databases and fresh ones also end up with different histories. The 5.2.4 CI round trip and every new machine (including the 2.1.1 path) would break the first time those models change.
- **Where to build it:** backend/app/db/migrations/versions/0001_initial.py (freeze it to explicit op.create_table for the four tables as they are today)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Freeze 0001 into explicit op.create_table calls (generated once from today's metadata) | Alembic's recommended practice; 0002-0004 already use explicit ops | free/open source | History stays fixed; --sql offline mode works; no behaviour change for existing databases | Edits a released migration (safe here: no production database yet) |
| New squashed baseline migration and alembic stamp for existing databases | A common squash pattern | free/open source | A clean start | Every existing dev database must be stamped by hand |
| Leave 0001 and add a CI check that fresh upgrade head equals the models (alembic check) | Alembic 1.9+ 'alembic check' command | free/open source | Catches the break in CI | Detects, does not prevent; the first 3.1.2 migration still fails |

- **Recommended:** Freeze 0001 into explicit op.create_table calls (generated once from today's metadata). No production database exists yet, so freezing is free now and costly later. It aligns 0001 with the explicit-operations rule and with the other three migrations.
- **Ruled out:** Squash and stamp: manual stamping on each machine for no added benefit. A CI check alone: reports the breakage but does not stop 3.1.2's first migration from failing.

### R122

**OpenAlex API key is part of the cache key; adding/rotating it empties the cache** · weight 68 · Logic flaw · impact 3/5, reach 3/5, confidence 3/3 · flags F-B5-003, F-A2-007

- **Evidence (B5):** backend/app/research/sources.py:167 builds the cache key from the full params, and papers() (209) and paper_count() (260) put api_key into params. Cache._hash (60-61) hashes it, so the secret never shows, but every entry cached without a key (or with an old key) misses once OPENALEX_API_KEY is set or rotated.
- **Evidence (A2):** backend/app/research/sources.py:208 and 260 put api_key into params; _get_json builds the cache key from those params (sources.py:167: key = 'GET {url} {params}'). Probe (scratchpad/a2/probe2.py): the same query fetched without and then with api_key made 2 network calls; the second missed the cache.

- **Why it matters:** The moment the owner adds the key that 2.2.6 and 5.6.2 wait for, every cached search misses for up to research_cache_days and is fetched again; nightly warming done with one key is lost when the key rotates. 5.4.2's hit-rate counter would show a collapse that is caused by configuration, not traffic.
- **Where to build it:** research/sources.py (_get_json key construction)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Strip credential params before building the key | A fixed set of secret param names (api_key) removed in _get_json; same approach the code already uses for GitHub, whose token is a header and not in the key | free/open source | One-line change; cache survives adding or rotating keys; consistent across sources | A keyed and unkeyed response may differ in rate limits but not in content, so no real downside |
| Send the OpenAlex key as a header or mailto instead of a param | OpenAlex accepts identification outside the search terms | free/open source | Removes the secret from URLs and logs as well | Depends on OpenAlex accepting the key that way; still needs a test |
| Key by a normalised query (source + query + per_page + sort) | Explicit key builders per connector | free/open source | Fully controlled keys, matches the rs:{source}:{hash} design in 2.2.2 | More code per connector |

- **Recommended:** Strip credential params before building the key. Fixes the invalidation and the hit-rate distortion with the least code, and can land with 2.2.2's key alignment.
- **Ruled out:** Header transport: depends on provider behaviour not yet verified; per-connector key builders: more code for the same effect, better done only if 2.2.2 rewrites keys anyway.

### R137

**No policy for a session document that fails to decode; one bad doc breaks /programme** · weight 68 · Missing logic · impact 3/5, reach 3/5, confidence 3/3 · flags F-B2-001

- **Evidence (B2):** backend/app/agents/ideation.py:168 ElicitationSession.model_validate(d['elicitation']) and :192 d['updated_at'] raise on any old or invalid shape. backend/app/agents/store.py:60-64, 90-95 and 225-228 call from_dict with no guard. backend/app/routers/cohort.py:40 loads up to 500 sessions in one comprehension. Probe (scratchpad arena/b2probe.py, Python 3.11): a stored doc with slot confidence 1.5 makes MemoryStore.get raise pydantic ValidationError.

- **Why it matters:** Once the format changes, an upgrader that misses a case fails the request with a 500, not a 404 or a 'cannot resume' message. On /programme, one bad session among a cohort's IDs fails the whole aggregate. The founder loses resume and the programme manager gets nothing.
- **Where to build it:** backend/app/agents/store.py (one decode helper used by all three stores); backend/app/agents/ideation.py (upgrade function); routers/ideation.py _load (410 or 'cannot be resumed'); routers/cohort.py (skip and count undecodable sessions)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Central decode() with try/except, a log event and skip/410 | Plain Python pattern; fits the existing structlog agent_store.* events | free/open source | Small, one place, no dependency; /programme can report sessions_unreadable | Bad rows stay until retention removes them |
| Quarantine column or table (decode_error, quarantined_at) | Dead-letter pattern; an Alembic migration on agent_sessions | free/open source | Operators can find and repair broken sessions; fits a runbook | Needs the database (2.1.1) and a migration; adds a write on the read path |
| Whole session as a Pydantic model with lenient validators | Pydantic v2 already models elicitation | free/open source | One schema; coercion and defaults are declarative | Leniency hides real corruption; large refactor of the dataclass |
| jsonschema validation before from_dict | Mature library; 5.2.1 already plans schemas for reference data | free/open source | Explicit documented contract for 5.3.1 | Duplicates the Pydantic model; detects but does not recover |

- **Recommended:** Central decode() with try/except, a log event and skip/410. Closes both the 500 and the all-or-nothing /programme failure in one small helper. It works offline on the memory store and leaves room to add quarantine later.
- **Ruled out:** Quarantine: needs PostgreSQL (waiting on 2.1.1) and is more than is needed now. Lenient Pydantic: hides corruption, and the refactor is out of proportion. jsonschema: a second schema next to Pydantic, with no recovery.

### R148

**Warmed keys won't match founder searches: cache keys are exact query strings** · weight 68 · Logic flaw · impact 3/5, reach 3/5, confidence 3/3 · flags F-B5-009

- **Evidence (B5):** Ran build_queries (backend/app/research/terms.py:318-339) on registry fields: banana_value_added label -> 'banana value-added products', summary -> 'chips flour', trend_query -> 'banana flour processing'; founder sentences 'I want to make banana flour from waste bananas for bakeries' -> 'banana flour waste' and 'banana flour unit selling to bakeries in Trichy' -> 'banana flour'. sources.py:167 keys the cache on the exact URL+params; scan.py:211 also lets model-written queries override; novelty.paper_count uses different params (per_page 1, select id; sources.py:260) from papers() (per_page 25), so they never share an entry. Registry domains carry only trend_query, no per-source research queries (domains.json keys).

- **Why it matters:** A warming run over 240 domains would fill the cache with keys founders almost never request, so 'common ideas answer from cache instantly' does not happen while the requests still cost budget; 5.4.2's hit rate would show it, but only after the spend.
- **Where to build it:** scripts/ nightly warming step, research/sources.py (cache keying), research/scan.py

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Refresh-ahead of keys founders actually requested | Record each cache key's request params and last-hit time (Redis sorted set or the disk cache's JSON) and re-fetch popular entries shortly before expiry | free/open source | Warms exactly what founders ask; no query guessing; budget spent only on proven demand | Needs the request params stored next to the hashed key; cold start for never-seen ideas |
| Domain evidence pack served by registry match | The registry already matches an idea to a domain; store a precomputed scan per domain (like signals.json) and show it as domain context while the live search runs | free/open source | Instant, query-independent evidence for known domains; reviewed in Git like other reference data | Domain-level, not idea-level, evidence; must be labelled as such |
| Normalise queries before keying (sorted, lower-cased terms) | Canonical key form is a standard cache technique | free/open source | Raises hit rate for reordered terms | Does not make 'banana flour waste' equal 'banana flour processing'; OpenAlex ranking can depend on order |
| Warm with build_queries(trend_query) as planned | TASKS.md 2.2.6 How | free/open source | Simple script | Proven key mismatch above |

- **Recommended:** Refresh-ahead of keys founders actually requested. Uses demand the system already sees, so every warmed request is one a founder is likely to repeat; the domain pack can follow as a separate reference-data item.
- **Ruled out:** Domain pack: useful but a different feature (domain context, not cache warming); normalisation: cannot bridge different words; planned warming: the test shows its keys miss.

### R153

**No global limit on concurrent jobs: panel bursts of 7 model calls per session hit free-tier limits** · weight 67 · Missing logic · impact 3/5, reach 4/5, confidence 2/3 · flags F-A2-013

- **Evidence (A2):** backend/app/agents/council/__init__.py:57-63 fires all seats at once (seven per panel run) through the judge provider; backend/app/agents/jobs.py:81 starts every job immediately with no semaphore or queue across sessions, and each research job opens its own httpx client (ideation.py:372). Seat failures fall back to rules silently (council/__init__.py:66-76). The turn's own wording calls share the Gemini provider, and ideation.py:801-803 counts each failure on the Gemini breaker (Breaker('gemini'), providers.py:423; threshold 3 in 60 s, cooldown 300 s, services/breaker.py:20). No setting limits model calls per minute (grep of providers.py and config.py).

- **Why it matters:** Gemini's free tier caps requests per minute. Two or three founders reaching the panel in the same minute send many parallel seat calls, so most seats fall back to rules, and any turn-wording call caught in the same burst gets 429s. Three of those open the Gemini breaker for 5 minutes for every founder, and the conversation drops to the slow local model or plain templates. Unconstrained research jobs also burst against the source budgets that 2.2.1 tries to protect.
- **Where to build it:** backend/app/agents/jobs.py (a concurrency limit per kind), backend/app/agents/providers.py (a per-provider rate limiter that seats and turns share, with turns taking priority)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| asyncio.Semaphore per job kind plus a token-bucket limiter per provider | Standard library, in-process like the job board; a token bucket is a few lines | free/open source | Panel seats queue instead of failing; turn calls can reserve tokens first; no dependency | Per process only; several workers need the Redis version (2.3.1) |
| aiolimiter library | A small, popular asyncio leaky-bucket rate limiter | free/open source | Tested limiter | A new dependency for what a few lines give; still per process |
| Redis-based limiter (for example a GCRA or token bucket in a Lua script) | Redis is already in the stack | free/open source | Shared across workers | Redis is optional; needs a local fallback anyway |
| Run panel seats one after another | A trivial change | free/open source | Fewest calls per second | The panel becomes about seven times slower for everyone, even when the limits are not near |

- **Recommended:** asyncio.Semaphore per job kind plus a token-bucket limiter per provider. It keeps the panel parallel when there is room, protects live turns from panel bursts, needs no dependency, and fits the in-process board until 2.3.1 adds a shared queue.
- **Ruled out:** aiolimiter: a dependency for a few lines; Redis limiter: Redis must stay optional, so it can only be a later layer; serial seats: slows every panel to avoid a peak-time problem.

### R160

**Disk cache writes are not atomic, and a truncated file raises instead of missing** · weight 62 · Missing logic · impact 3/5, reach 2/5, confidence 3/3 · flags F-A2-009

- **Evidence (A2):** backend/app/research/sources.py:72-74: put() writes the file in place with write_text; get() (66-70) runs json.loads with no error handling, and aget does not catch it (only Redis errors are caught). Probe (scratchpad/a2/probe2.py): a truncated cache file made Cache.aget raise JSONDecodeError. Combined with the first flag, that exception fails the whole scan, and it keeps failing every time until the file is 7 days old.

- **Why it matters:** A crash, a full disk, or two workers writing the same hash (more likely on Windows, where an open file can block a writer) leaves a half-written file. Every founder whose query hashes to it then loses the whole evidence scan for up to a week, with no log line naming the file.
- **Where to build it:** backend/app/research/sources.py (Cache.get, Cache.put)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Write to a temp file and os.replace, and treat unreadable files as a miss (delete them) | The standard library atomic-rename pattern, atomic on NTFS and POSIX | free/open source | No dependency; corrupt entries heal themselves on the next fetch | Temp files need cleaning up if the process dies mid-write (2.2.5's purge can do it) |
| diskcache library (SQLite-backed) | A mature, popular pure-Python disk cache with expiry built in | free/open source | Atomicity, expiry and size limits (would also cover 2.2.5) | A new dependency and a migration of the existing .cache/research files |
| portalocker file locks around read and write | A cross-platform file-locking library | free/open source | Stops concurrent writers | Does not help with crash truncation; adds lock waits on reads |

- **Recommended:** Write to a temp file and os.replace, and treat unreadable files as a miss (delete them). It fixes both truncation and concurrent writes in a few lines of standard library code, and 2.2.5's purge can sweep stray temp files.
- **Ruled out:** diskcache: a reasonable choice, but a new dependency and a data migration for a small fix; portalocker: does not cover crashes and slows reads.

### R161

**Older code silently drops newer fields on load-then-save (rollback, Redis copy)** · weight 62 · Logic flaw · impact 3/5, reach 2/5, confidence 3/3 · flags F-B2-002

- **Evidence (B2):** backend/app/agents/ideation.py:144-193: from_dict reads a fixed key list and to_dict writes the same list, so unknown keys vanish. Probe: from_dict({..., 'saved': True, 'format': 2}).to_dict() has no 'saved' key. backend/app/agents/store.py:184-189 keeps a 6-hour Redis copy written by whichever release served the last turn.

- **Why it matters:** 2.1.4 plans only old-to-new upgrade-on-read. Suppose a release adds a field (for example the 'saved' flag of 2.1.3.2) and is then rolled back, or two workers run different releases during a deploy. The older code loads the document and saves it back without the field. A founder's saved idea quietly loses its retention protection, and the version check cannot catch it because the save is legitimate.
- **Where to build it:** backend/app/agents/ideation.py (a FORMAT constant; from_dict refuses a format newer than the code); backend/app/agents/store.py (refuse to save when format > FORMAT)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Format guard: refuse to load or save a newer format than the code knows | Standard schema-version reader rule (Avro and Protobuf compatibility rules, Django migration checks) | free/open source | A few lines; turns silent loss into a visible 409/503 during a mixed deploy | During a rollback, newer sessions are unavailable until the roll forward |
| Preserve unknown keys (carry an extras dict through from_dict/to_dict) | Protobuf unknown-field preservation; easy with **rest in Python | free/open source | Rollback stays usable and no bytes are lost | Old code still acts wrongly on fields it ignores (retention ignoring 'saved') |
| Documented expand/contract deploy discipline only | Common migration practice, in line with SYSTEM-DESIGN 5.2 | free/open source | No code | Relies on people; nothing enforces it |
| Pydantic model with extra='allow' | Pydantic v2 already used | free/open source | Keeps extras automatically | Needs a dataclass-to-Pydantic refactor; same blind-old-code issue |

- **Recommended:** Format guard: refuse to load or save a newer format than the code knows. The format field that 2.1.4 adds is exactly what makes this check possible. Refusing is the only option that guarantees no silent loss of safety-relevant fields such as 'saved' or consent.
- **Ruled out:** Preserving keys: keeps the bytes, but old code still makes retention or consent decisions without the field. Process only: not enforced. Pydantic extra='allow': a big refactor with the same blind-old-code issue.

### R163

**Rate limiter is per process, keyed by IP not user, and never evicts keys** · weight 61 · Missing logic · impact 3/5, reach 3/5, confidence 2/3 · flags F-A5-008, F-A3-011, F-A2-017

- **Evidence (A5):** backend/app/core/middleware.py:41-47 keys by request.state.user_id, but nothing in backend/app sets request.state.user_id (grep), so every request is keyed by client IP; _per_client (middleware.py:37) is a defaultdict never pruned of idle keys; limits are in-process (core/config.py:125-126: 100/min per client, 1000/min global), so behind a proxy or shared NAT all founders share one key, ten busy clients exhaust the global cap for everyone, and a research turn costs the same as a cheap GET.
- **Evidence (A3):** backend/app/core/middleware.py:43 reads request.state.user_id, but nothing sets it (grep for 'state.user_id' finds only this line), so every request is keyed by IP with 100/min (config.py:125).
- **Evidence (A2):** backend/app/core/middleware.py:30-72: the limits sit in in-process dicts and deques. _per_client is a defaultdict, and a key is never removed once its deque empties (so it grows by one entry for every IP ever seen). The key is request.client.host when there is no user (46-47), with no forwarded-header handling, and the docstring (3-5) defers the shared version to an August 'Task 5.5' that the new plan does not carry. The limits come from config.py:125-126 (100 per client and 1000 global per minute). SYSTEM-DESIGN §4 lists 'rate limits' in Redis (L1, line 111). No task in TASKS.md covers rate limiting.

- **Why it matters:** On a college network or behind a reverse proxy founders lock each other out with 429s, memory grows per new IP, and free upstream research quotas are not protected per turn. 5.1.6 tests injection and CORS but not abuse limits.
- **Where to build it:** backend/app/core/middleware.py, backend/tests (security), Redis already in the stack

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Redis window per session id with route cost | Redis is already a dependency (core/redis.py); INCR with TTL is the standard pattern | free/open source | Shared across workers, memory bounded by TTL, can weight conversation turns | Needs the in-memory fallback when Redis is off |
| slowapi | Popular Starlette/FastAPI port of Flask-Limiter with Redis storage | free/open source | Per-route decorators, documented | Extra dependency; the key function still needs the session id |
| Fix in place: prune idle keys, trust X-Forwarded-For from a configured proxy | Small edits to the existing middleware | free/open source | No new dependency | Still per process; limits multiply by worker count |
| Reverse-proxy limiting (nginx limit_req) | Mature, free | free/open source | Off the app | Hosting undecided; not testable in the repo |

- **Recommended:** Redis window per session id with route cost. Uses the existing Redis and session id, works across workers, bounded memory, and keeps the current in-process limiter (with pruning) as the no-Redis fallback.
- **Ruled out:** slowapi: an extra dependency for what INCR+EXPIRE does; Fix in place: still per process and multiplied by workers; nginx limit_req: depends on the undecided hosting.

### R165

**Enum renames (D5 sector list) leave dead strings in old sessions and shift idea_version** · weight 61 · Missing logic · impact 3/5, reach 3/5, confidence 2/3 · flags F-B2-003

- **Evidence (B2):** backend/app/agents/ideation.py:169-173 restores enum members under contextlib.suppress(ValueError), so an unknown value stays a bare str. Probe: sector 'agritech_old' reloads as str with no warning. ideation.py:57 CORE_SLOTS includes 'sector', and :137-142 hash those values into idea_version. idea_version keys job results (backend/app/agents/results.py:26-47) and the agent_sessions.idea_version column (store.py:117).

- **Why it matters:** 4.1.2 replaces the 12-sector enum with the StartupTN list but says nothing about stored sessions. Old sessions keep sector strings that no longer exist, and these filled-but-invalid values feed matching and the programme's sector bands. If the 2.1.4 upgrader maps them, every affected session's idea_version changes: finished background results (scan, council) are orphaned and recomputed against the free source budget, and the row column stays stale until the next save.
- **Where to build it:** backend/app/agents/ideation.py (the upgrade step for format N+1 maps old enum values through the 4.1.2 mapping); idea_version (hash a canonical sector code, or re-key results from the old to the new idea_version)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Versioned upgrade step using the 4.1.2 mapping, re-keying results | The upgrade chain 2.1.4 already plans, plus the mapping 4.1.2 produces anyway | free/open source | Old sessions become valid; results are kept by copying them under the new idea_version | The result store must support re-keying (in memory today, a table after 2.3.1) |
| Hash a stable canonical code, not the label, in idea_version | Decouples identity from vocabulary | free/open source | Future renames never move idea versions | Changes every hash once, which needs a one-time migration |
| Mark unmapped values low-confidence so the question is asked again | The existing 0.5 filled floor in elicitation/session.py | free/open source | The founder corrects it naturally; nothing is guessed | Re-asks returning founders a question they already answered |
| Leave the strings and log a warning | Status quo | free/open source | Trivial | Invalid sectors keep flowing into cohort and matching |

- **Recommended:** Versioned upgrade step using the 4.1.2 mapping, re-keying results. Connects the two tasks that will otherwise collide. Founders are not asked again, and no free source budget is spent recomputing results that are still valid.
- **Ruled out:** Canonical-code hash: right in the long run, but it changes every hash once, which is the cost being avoided; do it together with the mapping or not at all. Re-ask: annoys returning founders when a mapping exists. Status quo: invalid data reaches the cohort bands.

### R178

**Warming has no founder reserve in the shared daily cap and refetches a 7-day cache** · weight 61 · Missing logic · impact 3/5, reach 3/5, confidence 2/3 · flags F-B5-010

- **Evidence (B5):** sources.py:146-161 — one cap per source per UTC day (time.gmtime, sources.py:119-120), shared by every caller; TASKS.md 2.2.6 'under the budget cap'. Cache TTL is research_cache_days=7 (config.py:116; sources.py:57, 68). 240 registry domains (domains.json + batch2 + batch3); papers() alone makes 3 OpenAlex requests (sources.py:211-230), patents 2 EPO searches (sources.py:482).

- **Why it matters:** 'Under the cap' lets warming use the whole cap; a run after 05:30 IST (00:00 UTC) spends the day founders are about to use, and they get 'not searched'. Re-warming every night entries still valid for 7 days spends roughly 6 of 7 nights' requests for nothing (on the order of 240 x 3 OpenAlex calls a night).
- **Where to build it:** nightly warming step (scripts/), research/sources.py (_over_budget with a caller class), core/config.py

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Warming share of the cap plus warm-only-if-expiring | A second limit (e.g. WARM_SHARE of the per-source cap) checked against the same budget:{source}:{date} counter, and a TTL check (Redis TTL / file mtime) before each fetch | free/open source | Founders keep a guaranteed share; no refetch of fresh entries; reuses existing counter | Needs a known per-source cap (see B5-01 flag 1) |
| Run warming just before the UTC reset | Budget resets at midnight UTC (runbook research-budget.md); spend leftover budget late in the UTC day (~03:00-05:00 IST) | free/open source | Uses budget that would otherwise expire unused | Still needs a stop rule so a busy day's tail is not consumed |
| Separate key for warming | Free OpenAlex key, which 2.2.6 already waits for | free tier | Separate budget from founders | Only if a second free key is acceptable under OpenAlex terms; same key for both is the likely case |

- **Recommended:** Warming share of the cap plus warm-only-if-expiring. Guarantees founders' searches regardless of schedule and removes the 6-in-7 wasted refetches, with the counter that already exists.
- **Ruled out:** Timing alone: no protection on busy days; separate key: uncertain under the provider's terms and does not stop the refetch waste.

### R180

**A disk-cache hit copied to Redis gets a fresh full TTL, so data can stay stale for twice as long** · weight 58 · Logic flaw · impact 2/5, reach 3/5, confidence 3/3 · flags F-A2-008

- **Evidence (A2):** backend/app/research/sources.py:84-86: on a disk hit, aget writes the response to Redis with ex=self.ttl (research_cache_days in full) whatever the file's age. Probe (scratchpad/a2/probe2.py): a disk entry 6.9 days old was copied into Redis with a TTL of 7.0 days.

- **Why it matters:** The research_cache_days rule ('responses are cached for N days', sources.py:10) is broken: an answer fetched almost a week ago can be served for nearly another week, so founders see paper and project counts up to about 14 days old while the design and runbook say 7.
- **Where to build it:** backend/app/research/sources.py (Cache.aget)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Copy with the remaining TTL (ttl minus file age) | The file mtime is already read in Cache.get | free/open source | Exact rule, a two-line change | Cache.get has to return the age as well as the value |
| Store fetched_at inside the cached JSON and check it on every read | A self-describing cache entry | free/open source | The age survives copies between layers and is visible to operators | Changes the cache format; old entries need handling |
| Do not copy disk hits into Redis | Removes the path | free/open source | Simplest | Other workers lose the shared hit that the copy exists for |

- **Recommended:** Copy with the remaining TTL (ttl minus file age). It restores the documented lifetime with the smallest change and keeps the cross-worker benefit of the copy.
- **Ruled out:** fetched_at in JSON: a format change for the same result; no copy: loses the shared hit for other workers.

### R181

**Durability is inferred from a store-name string, and no test asserts the flag** · weight 58 · Missing structure · impact 2/5, reach 3/5, confidence 3/3 · flags F-B2-029

- **Evidence (B2):** backend/app/routers/ideation.py:303 'saved': store.name == 'database'. backend/app/agents/store.py:182 CachedStore.name = f'{inner.name}+redis'. The SessionStore protocol (store.py:36-46) has only a name, no durability attribute. grep over backend/tests finds no assertion on 'saved'.

- **Why it matters:** 2.1.2's proposed fix (startswith 'database') is string matching on a display name. Any future wrapper (a metrics or retry wrapper, for example 'retry+database') breaks it again silently, and with no test the banner regression returns unnoticed, as it did with the Redis wrapper.
- **Where to build it:** backend/app/agents/store.py (a durable: bool on the protocol; CachedStore delegates to inner.durable); routers/ideation.py; tests/api/test_ideation_api.py (assert saved for memory, database and cached stores)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| durable attribute on SessionStore, delegated by wrappers, and API tests for each store | An explicit capability on the existing Protocol | free/open source | Robust to new wrappers; testable with the fake Redis | Touches each store class (three, small) |
| startswith('database') as the plan says, plus a test | The plan's fix | free/open source | One line | Breaks on any wrapper that prefixes its name |
| isinstance check that unwraps CachedStore to SqlStore | Type inspection | free/open source | No protocol change | Couples the router to store internals |

- **Recommended:** durable attribute on SessionStore, delegated by wrappers, and API tests for each store. Makes durability a property the store declares rather than a name the router parses, and the tests stop this regression from recurring.
- **Ruled out:** startswith: repeats the same class of bug with the next wrapper. isinstance unwrap: leaks store internals into the router.

### R193

**Upgrade-on-read leaves mixed formats in PostgreSQL; the 5.5.5 split has no backfill** · weight 55 · Missing structure · impact 3/5, reach 2/5, confidence 2/3 · flags F-B2-004

- **Evidence (B2):** backend/app/agents/store.py:85-95: SqlStore.get upgrades only in memory, and the row is rewritten only by save() (:98-125). The agent_sessions model (backend/app/models/agent_session.py:20-32) has no format column, so nothing shows which rows are on which format. TASKS.md 5.5.5.1 says only 'split session documents into tables by migration'.

- **Why it matters:** Sessions nobody reopens, which is most of them given the 6-hour expiry, stay in their original format forever. The table-split migration would then have to import app upgrade code into Alembic, which breaks when that code later changes, or re-implement every format. A missed format silently drops cohort data or fails a production migration, and production migrations only go forward (SYSTEM-DESIGN 5.2).
- **Where to build it:** backend/db/migrations (a queryable format column); scripts/ (an idempotent upgrade-all backfill run before 5.5.5.1); backend/app/agents/ideation.py (keep the upgrade function pure and importable)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Format column plus an idempotent upgrade-all script before the split | Expand/contract with backfill, matching SYSTEM-DESIGN 5.2 'add, fill in, then constrain' | free/open source | The split sees one format; progress is queryable (WHERE format < N) | One more migration and one more script |
| Alembic data migration with a frozen copy of the upgrader | Common Alembic data-migration practice | free/open source | Self-contained and reproducible | Duplicated code; large JSONB rewrites inside a migration transaction |
| PostgreSQL jsonb_set SQL per format step | Native PostgreSQL, no app code | free/open source | Fast and set-based | Nested enum mapping is awkward in SQL; cannot be tested on the offline memory store |
| Nightly job lazily upgrades stale rows | Fits the planned nightly job (5.4.4) | free/open source | No big-bang rewrite | The split must still wait for completion, which cannot be known without the column |

- **Recommended:** Format column plus an idempotent upgrade-all script before the split. Reuses the one upgrade function the app already trusts and follows the documented add/fill/constrain rule. It gives 5.5.5 a checkable precondition: no rows below the current format.
- **Ruled out:** Frozen Alembic copy: duplicates the upgrader and rewrites large JSONB inside a transaction. jsonb SQL: a poor fit for nested enum mapping and untestable offline. Nightly lazy backfill: without the column you cannot know when it is done, so it is option 1 with a delay.

### R198

**EPO 'no hits' (404) answers are never cached, so empty searches repeat** · weight 52 · Optimisation · impact 2/5, reach 2/5, confidence 3/3 · flags F-B5-008

- **Evidence (B5):** Ran scratchpad/arena/b5/dup.py: three sequential _get_json calls to EPO_SEARCH answering 404 -> 'sequential 404 repeats sent: 3'. sources.py:176-183 caches only 200; epo_patents treats 404 as 'none found' (sources.py:485-486), a valid answer.

- **Why it matters:** Novel or narrow ideas, the ones where 'no patents' matters most, hit EPO again on every scan and every lock waiter, using EPO's ~10 searches/minute fair-use and the daily counter for an answer already known.
- **Where to build it:** research/sources.py (_get_json: allow per-source cacheable statuses)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Cache 404 as an empty result for EPO | One condition in _get_json keyed on source; same TTL or a shorter one | free/open source | Removes repeat calls; works for lock waiters too | A newly published patent is missed until the entry expires (same as positive caching) |
| Generic negative cache with short TTL for all non-200 'definitive' statuses | Common HTTP caching practice (RFC 9111 allows caching 404) | free/open source | Covers future sources | Risk of caching transient errors if the status list is wrong |
| hishel HTTP cache for httpx | Maintained RFC 9111 cache transport for httpx | free/open source | Standard semantics, storage backends | Duplicates the custom Redis/disk cache; EPO responses lack cache headers, so needs forcing anyway |

- **Recommended:** Cache 404 as an empty result for EPO. Smallest change, proven by the test, aligned with how epo_patents already reads 404.
- **Ruled out:** Generic negative cache: wider risk of caching transient failures; hishel: a second cache layer beside the existing one.

### R203

**30 s lock expires before the 60 s fetch; failed holder leaves waiters to stampede** · weight 51 · Logic flaw · impact 2/5, reach 3/5, confidence 2/3 · flags F-B5-007

- **Evidence (B5):** TASKS.md 2.2.1: 'Redis lock:{key} (30 seconds)'. scan.py:214 and novelty.py:81 create httpx.AsyncClient(timeout=60); papers() makes three sequential requests (sources.py:211-230). _get_json caches only status 200 (sources.py:176-180); 429/5xx return without writing anything.

- **Why it matters:** A slow OpenAlex answer outlives the lock, so a second worker fetches anyway and the first may then delete the second's lock if release is a plain DEL. When the holder gets a 429 or error, nothing lands in the cache, so every waiter wakes, misses and fetches; unless waiters re-run the pause and budget checks after waiting, they hit the source that just said 429 and extend its Retry-After.
- **Where to build it:** research/sources.py (_get_json order: cache -> lock -> pause -> budget -> fetch; waiters re-check cache then pause), core/redis.py

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Token lock with TTL above the request timeout and compare-and-delete release | Documented Redis single-instance lock pattern: SET key token NX PX, release by a Lua script comparing the token | free/open source | Lock outlives the fetch; no wrong release; small code | Lua script to maintain; TTL must track the client timeout setting |
| redis-py Lock (redis.asyncio.lock.Lock) | Built into the redis client already in use, token-based with extend() | free/open source | Correct release semantics out of the box; blocking_timeout for waiters | Waiters poll; still need the TTL and the post-failure re-check logic |
| Short negative marker after failure | The code already writes rs:neg:{source} for 429 pauses (sources.py:143) | free/open source | Waiters see the failure and stop instead of refetching | Only covers the failure side, not the TTL bug |

- **Recommended:** redis-py Lock (redis.asyncio.lock.Lock). Already a dependency, token-safe release, and timeout set from the httpx timeout; combine with waiters re-checking cache and the existing pause key after the wait.
- **Ruled out:** Hand-written Lua lock: reimplements what redis-py ships; negative marker alone: leaves the lock expiring mid-fetch.

### R208

**Reference caches depend on each other across datasets; a per-loader clear leaves mixed versions** · weight 51 · Missing structure · impact 2/5, reach 3/5, confidence 2/3 · flags F-A2-010

- **Evidence (A2):** backend/app/ecosystem/index.py:53-58: the cached get_ecosystem() is built from get_branch_index() (banking dataset), so it bakes branch counts per PIN into the ecosystem object. About 25 @lru_cache loaders are spread across modules (grep: banking/branches.py:105, banking/catalogue.py:44, ecosystem/match.py:111 and 116, funding/investors.py:142, journey/engine.py:33, cohort/reference.py:30 and others), and there is no list of which dataset each one reads.

- **Why it matters:** Task 2.2.3 says 'a new version clears that loader's cache'. If the banking dataset changes, clearing only the banking loader leaves get_ecosystem serving the old branch counts until a restart, so founders see branch and zone figures that disagree between screens. Without a registry, whoever builds 2.2.3 must find every loader by hand, and new loaders will be missed.
- **Where to build it:** a small module beside backend/app/core/redis.py (for example core/datasets.py) that registers each loader with the datasets it reads; used by 2.2.3 and by the ETags in 2.2.4

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Dataset registry decorator: @dataset_cache('banking', 'ecosystem') wrapping lru_cache | Plain Python; keeps the existing lru_cache behaviour | free/open source | One call clears every loader that reads a dataset; the same registry gives 2.2.4 its ETag version and lists the datasets for operators | Touches every loader once |
| Clear all reference caches when any dataset version changes | functools cache_clear on a list | free/open source | Simplest, and never leaves mixed versions | Every update reparses about 11 MB of JSON per worker, even for a small schemes change |
| cachetools with a version-keyed cache (key includes dataset versions) | A widely used caching library | free/open source | A changed version automatically gives a new entry | A new dependency; old entries hold memory until evicted |

- **Recommended:** Dataset registry decorator: @dataset_cache('banking', 'ecosystem') wrapping lru_cache. It makes the dependencies explicit, so 2.2.3 clears exactly the right caches and 2.2.4 gets its version from the same place.
- **Ruled out:** Clear all: correct but reparses everything on every small data change; cachetools versioned keys: a new dependency, and memory grows across versions.

