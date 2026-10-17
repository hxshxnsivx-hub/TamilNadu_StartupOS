# Flag tree: P3 Founder records and privacy

Back to the [flag tree](../FLAG-TREE.md).

## 3.1 Linking conversations to founders

### 3.1.1 Claim an anonymous session on sign-up

#### F-A3-001: Claimed sessions stay open to anyone with the ID: no ownership check on resume/turn/delete

Weight 100 · Missing logic · impact 5/5, reach 5/5, confidence 3/3 · found by A3 · merged as [R001](../arena/details-p3.md#r001)

- **Issue:** Once a session belongs to a signed-in founder (class D, personal), its transcript, facts and roadmap can still be read, continued or deleted by anyone who has the 32-hex ID (shared links, browser history, a shared phone's localStorage key vanigam_talk_session). Attaching user_id without enforcing it gives no protection, and DPDP purpose-limitation fails.
- **Cause:** backend/app/routers/ideation.py:307-345: agent_resume, agent_delete, agent_turn and agent_turn_stream take only session_id, with no Depends(get_current_user) and no comparison with AgentSessionRow.user_id (models/agent_session.py:24). TASKS 3.1.1 'How' only says 'attach user_id to the session'.
- **Resolution:** build it in api/deps.py (an optional-user dependency), routers/ideation.py (_load gains an owner check), agents/store.py; tests in backend/tests using **Optional-user FastAPI dependency plus an owner check in _load**. It closes the hole for every claimed session with a few lines in the existing deps module and a test per endpoint, and leaves the anonymous start untouched.

| Option | Why it is a candidate | Cost | Advantages | Drawbacks |
|---|---|---|---|---|
| Optional-user FastAPI dependency plus an owner check in _load | Uses existing OAuth2PasswordBearer(auto_error=False) in api/deps.py; standard FastAPI pattern | free/open source | Tiny change; anonymous sessions keep working (user_id 'anon'); a claimed session returns 404 to everyone except its owner | Session ID still acts as the anonymous bearer secret until claimed |
| Signed per-session capability token (itsdangerous / HMAC) returned at start | itsdangerous is the Flask/Starlette standard signer; no new infra | free/open source | Protects anonymous sessions too, not only claimed ones | Extra token to store and send from Talk.tsx; more frontend work |
| PostgreSQL row-level security on agent_sessions | Built into PostgreSQL | free/open source | Enforced even if a route forgets the check | Needs per-request SET of a role/GUC through SQLAlchemy; does not cover the Redis live copy |
| Casbin / Oso authorisation library | Mature policy engines with Python bindings | free/open source | Central policy, ready for the programme-manager role (3.2.5.2) | Heavy for a single owner rule |

- **Not chosen, and why:**
  - Signed capability token: right idea for anonymous sessions but more work than the district needs now; can follow later. Row-level security: does not cover the Redis copy and adds per-request session state. Casbin/Oso: a policy engine for one rule.
- **Also found as:** F-B5-021, F-B3-002, F-B1-033

#### F-A3-003: JWT secret defaults to 'change-me' with no startup guard, so tokens can be forged

Weight 100 · Logic flaw · impact 5/5, reach 5/5, confidence 3/3 · found by A3 · merged as [R002](../arena/details-p3.md#r002)

- **Issue:** Once sessions and profiles are tied to users (3.1), anyone who knows the public default can mint an access token for any user_id and read their records. Nothing in TASKS mentions it.
- **Cause:** backend/app/core/config.py:21 secret_key='change-me'; core/security.py:45,65 sign and verify with it; main.py:41 starts in any env. Ran with APP_ENV=production and no SECRET_KEY: settings printed ('production', 'change-me') and decode_token accepted a token I signed with 'change-me' for an arbitrary sub.
- **Resolution:** build it in core/config.py (validator), main.py lifespan using **pydantic model_validator refusing the default or a short key when app_env != development**. Smallest change that makes the insecure default impossible outside development.

| Option | Why it is a candidate | Cost | Advantages | Drawbacks |
|---|---|---|---|---|
| pydantic model_validator refusing the default or a short key when app_env != development | pydantic-settings already loads config | free/open source | Fails fast at boot; one test | Developers must set a key for staging |
| Auto-generate a random key into a local file on first run | secrets.token_urlsafe | free/open source | Zero setup | Multiple workers get different keys unless the file is shared; all tokens die on file loss |
| Asymmetric RS256/EdDSA keys | python-jose supports them | free/open source | Verification key can be shared safely | Key management overhead without a second verifier service |

- **Not chosen, and why:**
  - Auto-generated key: breaks across workers and restarts. Asymmetric keys: no second party verifies tokens, so it adds work without benefit.
- **Also found as:** F-A5-021

#### F-B5-020: Owner stored in three places; SqlStore.save never updates the user_id column

Weight 78 · Logic flaw · impact 4/5, reach 3/5, confidence 3/3 · found by B5 · merged as [R061](../arena/details-p3.md#r061)

- **Issue:** The natural claim (set s.user_id, then save) changes the JSON document but leaves the indexed agent_sessions.user_id at 'anon', so lookups and the delete-by-user of 3.2.4 (B5-05 flag 2) miss every claimed conversation, and the elicitation copy still says 'anon'. A founder's erasure request would leave their conversations behind.
- **Cause:** backend/app/agents/store.py:115-126 — save() updates version, idea_version, private, last_active and data, not user_id; the column is written only at create (store.py:148-152). The owner also lives in the document (agents/ideation.py:118, 148, 178) and in the elicitation state (elicitation/engine.py:117, session.py:86). Every session is created as 'anon' (ideation.py:203; routers/ideation.py:288-293 passes no user).
- **Resolution:** build it in agents/store.py (a claim operation that updates column and document together), agents/ideation.py and elicitation/session.py (one owner field) using **Dedicated store.claim(session_id, user_id) with a conditional UPDATE**. Makes ownership a deliberate, atomic, one-way transition that keeps the column, the document and Redis consistent, which erasure depends on.

| Option | Why it is a candidate | Cost | Advantages | Drawbacks |
|---|---|---|---|---|
| Dedicated store.claim(session_id, user_id) with a conditional UPDATE | SQLAlchemy UPDATE ... WHERE session_id=:id AND user_id='anon' setting column and JSON fields in one statement, plus Redis copy drop | free/open source | Atomic, updates every copy, refuses re-claiming someone else's session, testable | One more store method in three implementations |
| Include user_id in SqlStore.save's values | One-line change | free/open source | Column follows the document on every save | Any save could move ownership; no guard against hijack; elicitation copy still separate |
| Drop the column and query JSONB (data->>'user_id') | PostgreSQL JSONB with an expression index | free/open source | Single source of truth | Loses the plain column the migration and 5.5.5 table split rely on |

- **Not chosen, and why:**
  - Save includes user_id: lets any save rewrite the owner
  - JSONB-only: undoes the indexed column the design and later migrations use.
- **Also found as:** F-A2-005

#### F-B5-021: A claimed session stays open to anyone with its id; no ownership check on routes

Weight 78 · Missing logic · impact 4/5, reach 3/5, confidence 3/3 · found by B5 · merged as [R001](../arena/details-p3.md#r001)

- **Issue:** After a founder signs up and claims a conversation, it remains readable (transcript, facts), writable and deletable by whoever holds the 32-hex id from the browser, logs or a shared device, so linking to an account adds no protection; and without a 'claim only from anon' rule, a second account holding the id can take it over.
- **Cause:** backend/app/routers/ideation.py:270-318 — _load, agent_turn, agent_turn_stream, the snapshot GET and DELETE take only the session id path parameter (_SESSION_ID, line 265); none depends on get_current_user (api/deps.py:18-30). TASKS 3.1.1 How: 'attach user_id to the session at sign-up or sign-in', nothing about access afterwards.
- **Resolution:** build it in routers/ideation.py (an owner check in _load), api/deps.py (optional-user dependency) using **Optional-auth dependency: anon sessions by id, owned sessions need the owner's token**. Protects exactly the sessions that have an owner, without changing the anonymous path, and pairs with the conditional claim above.

| Option | Why it is a candidate | Cost | Advantages | Drawbacks |
|---|---|---|---|---|
| Optional-auth dependency: anon sessions by id, owned sessions need the owner's token | FastAPI dependency returning User \| None (OAuth2PasswordBearer auto_error=False already used via token None check in deps.py) | free/open source | Keeps the low-friction anonymous start; protects claimed sessions; one check in _load | Talk page must send the token once signed in |
| Signed session capability token | itsdangerous or the existing JWT helper issuing a token per session at start | free/open source | Ids alone stop being enough even before sign-up | Larger change to every client call; anonymous resume needs the token stored too |
| Require sign-in for all conversations | Standard authenticated API | free/open source | Simplest rule | Contradicts the low-friction start 3.1.1 exists for (rnd-elicitation §5.3) |

- **Not chosen, and why:**
  - Capability token: a broader redesign than the claim needs; mandatory sign-in: removes the anonymous start the plan wants.
- **Also found as:** F-A3-001, F-B3-002, F-B1-033

#### F-A3-008: agent_sessions.user_id is a free string with no foreign key to users

Weight 74 · Missing structure · impact 3/5, reach 4/5, confidence 3/3 · found by A3 · merged as [R059](../arena/details-p3.md#r059)

- **Issue:** A claimed session can point at a user who no longer exists, and deleting an account leaves its conversations behind unless every erasure path remembers them; the sentinel 'anon' mixes with UUID strings in one column.
- **Cause:** backend/app/models/agent_session.py:24 user_id String(64) nullable=False, default 'anon' (agents/ideation.py:118); migration 0004_agent_sessions.py:27 has no ForeignKey, while users.user_id is a UUID (0002_users.py:27).
- **Resolution:** build it in models/agent_session.py, a new migration (nullable UUID owner with FK ON DELETE CASCADE) using **Nullable UUID owner_id FK to users ON DELETE CASCADE (NULL = anonymous)**. Makes 'one deletion removes all sessions' (SYSTEM-DESIGN §5.4) a database guarantee and gives the ownership check a typed column.

| Option | Why it is a candidate | Cost | Advantages | Drawbacks |
|---|---|---|---|---|
| Nullable UUID owner_id FK to users ON DELETE CASCADE (NULL = anonymous) | SQLAlchemy/Alembic, §5.2 step-wise migration | free/open source | Erasure of the account removes sessions by construction; no sentinel | Migration plus updating store and new_session |
| Keep string column, add CHECK and rely on application delete | No schema change | free/open source | Cheap | Orphans whenever a path is missed |
| Ownership in a separate session_owners link table | Join-table pattern | free/open source | Allows future shared sessions | Extra join on every load for no current need |

- **Not chosen, and why:**
  - String plus CHECK: leaves orphan risk. Link table: complexity without a use case.
- **Also found as:** F-A2-016, F-B5-015

#### F-A3-009: No 'my conversations' list: a founder cannot find past sessions on another device

Weight 74 · Missing function · impact 3/5, reach 4/5, confidence 3/3 · found by A3 · merged as [R096](../arena/details-p3.md#r096)

- **Issue:** The purpose of linking (resume on any device, keep past ideas, delete one of several) fails: on a new phone the founder has no session ID and no way to get it, and 1.1.7's delete control can only reach the current device's session.
- **Cause:** routers/ideation.py:288-345 offers create, get-by-id, delete-by-id and turns only; agent_sessions has an index on user_id (0004_agent_sessions.py:41) that nothing queries. Talk.tsx:44-52 remembers a single session ID per device. SYSTEM-DESIGN §3.2 founder memory includes 'past ideas and decisions' and 'delete one session or all of them'.
- **Resolution:** build it in routers/ideation.py (GET /ideation/agent/sessions for the current user), agents/store.py (list_for_user), Talk.tsx using **GET /ideation/agent/sessions returning id, title, idea_version, last_active for the current user**. Delivers cross-device resume and per-session deletion with one indexed query.

| Option | Why it is a candidate | Cost | Advantages | Drawbacks |
|---|---|---|---|---|
| GET /ideation/agent/sessions returning id, title, idea_version, last_active for the current user | Uses the existing user_id index and store; FastAPI | free/open source | Small; reads only columns, not the JSON document | Needs a short title derived without exposing idea text in logs |
| Store session IDs in the founder profile record | 3.1.2 profile endpoints | free/open source | No new query | Two sources of truth that drift on delete or retention |
| Keyset-paginated list endpoint with filters | Standard API pattern | free/open source | Scales | Overkill: founders have a handful of sessions |

- **Not chosen, and why:**
  - IDs in the profile: duplicates state that the retention job would have to keep in sync. Keyset pagination: unnecessary at this size.

#### F-A3-002: Claim rule unspecified: a shared phone hands founder A's session to founder B

Weight 71 · Missing logic · impact 4/5, reach 3/5, confidence 2/3 · found by A3 · merged as [R117](../arena/details-p3.md#r117)

- **Issue:** Shared family phones are common for the target founders. If the claim runs on every sign-in for whatever session ID is in localStorage, the next person to sign in on that phone silently takes the previous founder's idea and transcript; a claimed session could also be re-claimed and overwritten.
- **Cause:** frontend/src/pages/Talk.tsx:29,44-52 keeps one device-wide key vanigam_talk_session; frontend/src/auth.tsx:53-56 logout clears only tokens. TASKS 3.1.1 says 'attach user_id at sign-up or sign-in' with no condition on the session's current owner.
- **Resolution:** build it in routers/auth.py or a new POST /ideation/agent/sessions/{id}/claim, agents/store.py, Talk.tsx, auth.tsx using **Explicit claim endpoint: only user_id='anon' sessions, founder confirms in the UI**. A conditional update is race-safe and the confirmation is the consent moment for linking a conversation to an identity.

| Option | Why it is a candidate | Cost | Advantages | Drawbacks |
|---|---|---|---|---|
| Explicit claim endpoint: only user_id='anon' sessions, founder confirms in the UI | Plain FastAPI route plus a conditional UPDATE ... WHERE user_id='anon' | free/open source | Atomic, never overwrites an owner; the founder sees 'Keep this conversation in your account?' | One extra tap |
| Auto-claim on sign-in with a freshness window (session created in the last N minutes on this tab) | sessionStorage instead of localStorage for the anon ID | free/open source | No extra tap | Window is a guess; still wrong for quick hand-offs |
| Never claim; copy the anonymous session into a new owned session | Store already serialises sessions as one JSON document (0003) | free/open source | Original anon copy expires on its own | Duplicates personal data; two copies to erase |

- **Not chosen, and why:**
  - Auto-claim with a window: guesses ownership on shared devices. Copy-on-claim: doubles personal data and complicates erasure (3.2.4).

#### F-A2-005: SqlStore.save never updates the user_id column, so a claimed session stays 'anon'

Weight 68 · Missing logic · impact 3/5, reach 3/5, confidence 3/3 · found by A2 · merged as [R061](../arena/details-p3.md#r061)

- **Issue:** Task 3.1.1 plans to 'attach user_id to the session at sign-up or sign-in'. Done the obvious way (set s.user_id, then save), the JSON document gets the ID but the indexed column stays 'anon'. Listing a founder's conversations, erasure by user and retention by user would then all miss the session.
- **Cause:** backend/app/agents/store.py:114-126: the UPDATE sets version, idea_version, private, last_active and data, but not user_id. user_id is written only by _row() at create (148-152). The indexed column (models/agent_session.py:24) is what lookups by founder and erasure by user (3.2.4) will query.
- **Resolution:** build it in backend/app/agents/store.py (SqlStore.save, or a dedicated claim method), together with 3.1.1 using **Dedicated claim(session_id, user_id) with WHERE user_id = 'anon'**. Ownership changes stay rare, guarded and visible, which the audit and erasure work (3.2.3, 3.2.4) depends on.

| Option | Why it is a candidate | Cost | Advantages | Drawbacks |
|---|---|---|---|---|
| Dedicated claim(session_id, user_id) with WHERE user_id = 'anon' | A SQLAlchemy update, the same pattern as save | free/open source | Explicit; cannot take over another founder's session; keeps the column and the JSON in step; bumps the version | A new store method on three implementations |
| Add user_id to the values in the save UPDATE | A one-line change | free/open source | Simplest | Any save could change the owner; nothing stops a session being claimed by someone else |
| Database trigger that copies data->>'user_id' into the column | A PostgreSQL trigger added in a migration | free/open source | The column can never drift from the JSON | Logic hidden in the database; the memory-store tests never exercise it |

- **Not chosen, and why:**
  - Add to save: lets any save change the owner with no guard
  - Trigger: hides behaviour in SQL, and the memory-store tests never run it.
- **Also found as:** F-B5-020

#### F-A2-016: agent_sessions.user_id is a free string ('anon'); it cannot reference users.user_id (UUID)

Weight 68 · Missing structure · impact 3/5, reach 3/5, confidence 3/3 · found by A2 · merged as [R059](../arena/details-p3.md#r059)

- **Issue:** Task 3.2.4's 'delete by user across tables' and 3.1.1's claim step depend on a real link. With a string sentinel, an erasure has to hunt by string match, a typo or a stale ID orphans a founder's transcripts, and 'anon' rows cannot be told apart from rows whose owner was deleted. The schema move in 2.4.1 is the natural moment to fix the type.
- **Cause:** backend/app/db/migrations/versions/0004_agent_sessions.py and models/agent_session.py:24: user_id String(64), NOT NULL, with the sentinel 'anon' (agents/ideation.py:118); no foreign key. backend/app/db/migrations/versions/0002_users.py:26-30: users.user_id is a PGUUID. The types differ, so no foreign key or ON DELETE CASCADE can link sessions to founders.
- **Resolution:** build it in a new migration (with 2.4.1's schemas): agent_sessions.user_id as a nullable UUID FK to users.user_id ON DELETE CASCADE, NULL meaning anonymous; agents/store.py and agents/ideation.py stop using 'anon' using **Nullable UUID foreign key with ON DELETE CASCADE (NULL = anonymous)**. It makes erasure and ownership correct by construction, which the DPDP work in 3.2 depends on, and it can land in the same migration that moves the table into its schema (2.4.1).

| Option | Why it is a candidate | Cost | Advantages | Drawbacks |
|---|---|---|---|---|
| Nullable UUID foreign key with ON DELETE CASCADE (NULL = anonymous) | Standard PostgreSQL referential integrity through an Alembic migration | free/open source | Erasure of a user removes their sessions by construction; the claim (3.1.1) is a guarded UPDATE; indexes still work | A migration to convert existing 'anon' rows to NULL; the JSON copy of user_id must follow |
| Keep the string and add a CHECK (user_id = 'anon' OR it parses as a UUID) | A PostgreSQL CHECK constraint | free/open source | A small migration | Still no cascade; erasure must remember this table |
| A separate session_owners link table | A many-to-one mapping table | free/open source | Leaves agent_sessions untouched | An extra join and table for a plain one-to-many relation |

- **Not chosen, and why:**
  - CHECK on the string: validates the format but still gives no cascade; link table: extra structure with no benefit over a foreign key.
- **Also found as:** F-A3-008, F-B5-015

#### F-B5-022: Browser keeps only the latest session id, so sign-up can claim one conversation at most

Weight 68 · Missing function · impact 3/5, reach 3/5, confidence 3/3 · found by B5 · merged as [R129](../arena/details-p3.md#r129)

- **Issue:** A founder who tried two ideas, or signs up the next day, can claim at most the last conversation, and only within six idle hours today; earlier anonymous conversations become orphans the founder can neither see nor delete, left only to the retention job.
- **Cause:** frontend/src/pages/Talk.tsx:29, 44-52, 331-333 — one localStorage key 'vanigam_talk_session', overwritten when a new conversation starts and removed on any load error (Talk.tsx:134, B5-06 flag 2); no other page reads it (grep SESSION_KEY). Claims also go through store.get, which hides sessions idle over 6 h (store.py:48-49, 95).
- **Resolution:** build it in frontend Talk.tsx (list of recent session ids), the sign-up/sign-in flow in frontend/src/auth.tsx, the claim endpoint (accepts several ids; bypasses the idle hiding) using **Recent-sessions list in localStorage, claimed in one call at sign-in**. Covers the common case (same phone) with no new identifier, and makes the earlier conversations reachable for the founder's own delete.

| Option | Why it is a candidate | Cost | Advantages | Drawbacks |
|---|---|---|---|---|
| Recent-sessions list in localStorage, claimed in one call at sign-in | Small array of {id, started} kept by Talk.tsx; auth.tsx posts it after login | free/open source | Every conversation from that browser follows the founder; no new dependency | Only the same browser; list must be pruned |
| Claim by device id cookie | An anonymous device id set at first visit and stored on each session | free/open source | Finds all sessions from the device server-side | Another identifier to protect and erase; cookie consent considerations |
| Claim only the current session (as planned) | TASKS.md 3.1.1 | free/open source | Simplest | Orphans earlier conversations |

- **Not chosen, and why:**
  - Device id: a new tracking identifier to justify under DPDP; current-session only: leaves orphans the founder cannot erase.

#### F-A3-011: Rate limiter never sees the signed-in user; mobile founders behind one carrier IP share a bucket

Weight 58 · Missing logic · impact 2/5, reach 3/5, confidence 3/3 · found by A3 · merged as [R163](../arena/details-p3.md#r163)

- **Issue:** Indian mobile carriers put many users behind carrier-grade NAT; at a cohort session or incubator Wi-Fi, founders on one IP throttle each other, while the per-user design intent is unused even after sign-in.
- **Cause:** backend/app/core/middleware.py:43 reads request.state.user_id, but nothing sets it (grep for 'state.user_id' finds only this line), so every request is keyed by IP with 100/min (config.py:125).
- **Resolution:** build it in core/middleware.py (decode the bearer token's sub without a DB hit), api/deps.py using **Middleware decodes the Bearer JWT (no DB) and sets request.state.user_id**. One small change that activates per-user limits the middleware already expects.

| Option | Why it is a candidate | Cost | Advantages | Drawbacks |
|---|---|---|---|---|
| Middleware decodes the Bearer JWT (no DB) and sets request.state.user_id | decode_token already exists | free/open source | Makes the existing design work | Anonymous users still keyed by IP |
| Key anonymous traffic by session_id path parameter | Session IDs are in every ideation URL | free/open source | Fair per conversation | Attacker can mint sessions to dodge limits; keep a looser IP cap |
| Redis-backed limiter (limits library) | Redis in stack | free/open source | Shared across workers | Separate concern; not needed to fix the keying |

- **Not chosen, and why:**
  - Per-session keys: easy to evade without an IP cap. Redis limiter: solves multi-worker sharing, not the keying bug.
- **Also found as:** F-A5-008, F-A2-017

#### F-A3-010: Account enumeration: register returns 409 and login skips bcrypt for unknown emails

Weight 51 · Logic flaw · impact 2/5, reach 3/5, confidence 2/3 · found by A3 · merged as [R204](../arena/details-p3.md#r204)

- **Issue:** Anyone can test whether an email is registered with Vanigam, which reveals that a person is a founder in the programme; the code contradicts its own stated intent.
- **Cause:** backend/app/services/auth_service.py:40-42 comments 'Verify even when the user is missing' but `user is None or not verify_password(...)` short-circuits, so unknown emails return without the ~100 ms bcrypt cost; :24-29 register answers EMAIL_TAKEN 409.
- **Resolution:** build it in services/auth_service.py using **Verify against a fixed dummy bcrypt hash when the user is missing; generic register response**. Makes the code do what its comment promises at no cost; register wording can stay helpful until email exists.

| Option | Why it is a candidate | Cost | Advantages | Drawbacks |
|---|---|---|---|---|
| Verify against a fixed dummy bcrypt hash when the user is missing; generic register response | passlib already in use (core/security.py:20) | free/open source | Two-line fix matching the comment | Generic register reply needs email delivery to be fully silent, which is not available offline |
| Rate limit login and register per email and IP | RateLimitMiddleware exists (core/middleware.py) | free/open source | Slows bulk probing | Does not remove the signal |
| slowapi limiter on auth routes | Popular Starlette limiter | free/open source | Per-route limits | New dependency duplicating the existing middleware |

- **Not chosen, and why:**
  - Rate limiting alone: reduces speed, not the leak. slowapi: duplicates existing middleware.

### 3.1.2 Profile and startup records on the server

#### F-B2-013: Founder table requires the full basic tier; partial browser profiles cannot be synced

Weight 84 · Logic flaw · impact 4/5, reach 4/5, confidence 3/3 · found by B2 · merged as [R024](../arena/details-p3.md#r024)

- **Issue:** 3.1.2.2 ('the browser profile syncs to the server') fails with IntegrityError for every founder below 40% completeness, which is exactly the founders who most need their partial answers kept across devices. Two email columns can drift: a founder who changes the sign-in email keeps the old one on the profile, and the unique constraints then block other people.
- **Cause:** backend/app/models/founder.py: name, email (unique), phone (unique), date_of_birth, gender, state, district and city are all nullable=False, with CHECK constraints on email and phone. frontend/src/completeness.ts:5-19: every Founder field is optional, and frontend/src/profileStore.ts:6 starts from an empty founder {}. backend/app/models/user.py also holds email, so Founder.email duplicates User.email.
- **Resolution:** build it in backend/app/models/founder.py and a migration (relax to nullable, enforce completeness in the scorer not the schema); routers /profiles; drop or derive Founder.email from users using **Nullable profile columns; completeness enforced by the scorer, not by NOT NULL**. Lets every draft sync with one shape, keeps the tier rule in the scorer the frontend already mirrors, and is a cheap migration while no real data exists. Take email from users and drop the duplicate column.

| Option | Why it is a candidate | Cost | Advantages | Drawbacks |
|---|---|---|---|---|
| Nullable profile columns; completeness enforced by the scorer, not by NOT NULL | Follows SYSTEM-DESIGN 5.2 'add as nullable, fill in, then constrain'; the scorer already exists (services/completeness.py) | free/open source | Partial drafts sync; one place decides what 'basic' means | Fewer database guarantees; queries must handle NULLs |
| A separate profile_drafts JSONB table until the basic tier is complete | Mirrors the session-document pattern (decision 0003) | free/open source | Keeps the strict Founder table as is | Two shapes of the same profile; a promotion step to maintain |
| Keep the browser as the store until 40%, then create the Founder row | No schema change | free/open source | Trivial | Defeats 'memory across devices' for exactly the incomplete profiles |

- **Not chosen, and why:**
  - Draft table: a second shape plus a promotion step for the same data. Browser until 40%: loses the partial profiles the task exists to keep.
- **Also found as:** F-A3-007

#### F-A3-005: Sign-out leaves profile, consent, journey and session ID on a shared device

Weight 78 · Missing logic · impact 4/5, reach 3/5, confidence 3/3 · found by A3 · merged as [R060](../arena/details-p3.md#r060)

- **Issue:** After 3.1.2 these become the founder's server records with a browser cache; on a shared phone the next user sees caste category and phone of the previous founder, and edits would sync into the wrong account. SYSTEM-DESIGN §2 rule 1 makes the server the source of truth, so clearing the local copy loses nothing.
- **Cause:** frontend/src/auth.tsx:53-56 logout only calls setTokens(null). Personal data stays in localStorage: vanigam_profile (profileStore.ts:3, includes phone, date_of_birth, caste_category per completeness.ts:5-18), vanigam_journey (consent flags), vanigam_pipeline, vanigam_suppliers, vanigam_talk_session.
- **Resolution:** build it in frontend/src/auth.tsx, a small storage module listing every vanigam_* key using **Central key registry and clear-on-logout (and on user change at login)**. Data minimisation on the device with the least code, and it prevents cross-account sync once 3.1.2.2 lands.

| Option | Why it is a candidate | Cost | Advantages | Drawbacks |
|---|---|---|---|---|
| Central key registry and clear-on-logout (and on user change at login) | Plain TypeScript module; keys already prefixed vanigam_ | free/open source | Simple, testable; also guards against syncing A's draft into B's account | New stores must register their key |
| Namespace keys by user_id | Common multi-account pattern | free/open source | Switching back restores drafts | Still leaves personal data on the shared device |
| Move drafts to sessionStorage | Browser built-in | free/open source | Gone when the tab closes | Loses anonymous drafts the design wants kept before sign-up |

- **Not chosen, and why:**
  - Namespaced keys: keeps sensitive fields on a shared phone. sessionStorage: breaks the anonymous start the design relies on.
- **Also found as:** F-B2-018

#### F-B2-014: Self-typed fields and a 'demo' checkbox would be stored as verified, tier 100

Weight 78 · Logic flaw · impact 4/5, reach 3/5, confidence 3/3 · found by B2 · merged as [R069](../arena/details-p3.md#r069)

- **Issue:** Once 3.1.2 persists the score and verified_fields, typed-in data is recorded as verified, and any founder can tick the demo box to become 'investment_ready'. 3.1.2.3 re-runs scheme eligibility on that score, and funding readiness reads the same profile, so founders (and programme views) would see unearned readiness. No document verification exists, and D11 keeps documents out of scope.
- **Cause:** backend/app/services/completeness.py:72 sets verified = list(basic_present), and :83/:86 add the education and startup fields that are present. The 80 tier is labelled 'verified' (:54), and 100 'investment_ready' needs only has_verified_documents (:79). frontend/src/pages/Profile.tsx:256-259 sets docsVerified from a checkbox labelled 'Documents verified (demo)' (i18n.ts:52). The ProfileCompleteness table stores verified_fields (models/profile.py).
- **Resolution:** build it in backend/app/services/completeness.py (verified_fields only for server-verified facts; rename the tiers); routers /profiles (ignore client docsVerified); frontend Profile.tsx (remove or clearly isolate the demo toggle) using **Server ignores client verification flags; verified_fields empty until a real check exists; tiers renamed (basic, standard, complete)**. The only option that never tells a founder or a programme something unverified is verified, and it matches D11 and the no-invented-data rule.

| Option | Why it is a candidate | Cost | Advantages | Drawbacks |
|---|---|---|---|---|
| Server ignores client verification flags; verified_fields empty until a real check exists; tiers renamed (basic, standard, complete) | Server-authoritative pattern; D11 says no documents yet | free/open source | No false claims; small change | The 100 tier is unreachable for now |
| Verify the free fields the platform can check (GSTIN checksum, CIN format, pincode to district) | Public format rules; CHECK constraints already exist for CIN and GSTIN | free/open source | Some honest 'verified' marks offline | A format check is not identity verification; must be labelled as such |
| Keep the demo toggle but store it as demo_only and exclude it from eligibility | Labelled-demo approach (like D9) | free/open source | Keeps the demo screen working | Demo data in real records, against 'no invented data' |

- **Not chosen, and why:**
  - Format checks: worth adding later, but they must not be called verification. Demo flag: keeps invented data in real records.

#### F-A3-004: Refresh token is never used or revocable: 30-min logouts and no server-side sign-out

Weight 74 · Missing logic · impact 3/5, reach 4/5, confidence 3/3 · found by A3 · merged as [R102](../arena/details-p3.md#r102)

- **Issue:** Once the profile syncs to the server (3.1.2.2), a founder is silently signed out every 30 minutes (access_token_expire_minutes, config.py:22) mid-edit. A stolen refresh token stays valid 14 days with no way to revoke it, and 'sign out' on a shared phone does not end the session server-side.
- **Cause:** frontend/src/api.ts:45-66 sends the access token but never calls /auth/refresh on 401 (grep: no 'refresh' call in frontend/src); auth.tsx:38 drops tokens on any /me failure. core/security.py:43 puts a jti in every token but nothing stores or checks it; routers/auth.py has no logout; refresh_token_pair (services/auth_service.py:56-61) reissues without invalidating the old refresh token.
- **Resolution:** build it in frontend/src/api.ts, auth.tsx; services/auth_service.py, routers/auth.py; Redis (already in stack) using **refresh_tokens table in PostgreSQL (hashed jti, revoked_at)**. Works with or without Redis, gives logout and rotation, and is deleted with the user under 3.2.4.1; pair it with a 401-retry in api.ts.

| Option | Why it is a candidate | Cost | Advantages | Drawbacks |
|---|---|---|---|---|
| Rotating refresh tokens with a jti denylist in Redis, plus a 401-retry wrapper in api.ts | Redis already configured (core/redis.py); jti already minted | free/open source | Revocation, logout and reuse detection with existing parts | Needs Redis or a fallback table when Redis is off |
| refresh_tokens table in PostgreSQL (hashed jti, revoked_at) | SQLAlchemy/Alembic already used | free/open source | Durable, works without Redis, fits erasure (delete by user) | One DB write per refresh |
| fastapi-users library | Popular FastAPI auth package | free/open source | Refresh, reset, verify flows prebuilt | Replaces the existing User model and services; large migration |
| httpOnly cookie for the refresh token | Standard web practice | free/open source | Refresh token out of localStorage (XSS) | Needs CSRF handling; complementary rather than a full fix |

- **Not chosen, and why:**
  - Redis denylist: Redis is optional in this app, so revocation would silently vanish when it is off. fastapi-users: rewrites working auth. httpOnly cookie: useful hardening but does not provide revocation by itself.

#### F-A3-007: founders table forces phone, birth date, gender, city as NOT NULL; CRUD on it over-collects

Weight 74 · Logic flaw · impact 3/5, reach 4/5, confidence 3/3 · found by A3 · merged as [R024](../arena/details-p3.md#r024)

- **Issue:** Saving a profile that only has district and sector (what 'never ask twice' needs) fails, so the sync either breaks or the UI must demand DOB, gender and phone before anything is stored: against DPDP data minimisation and the low-friction start. Two email copies drift when one is changed.
- **Cause:** backend/app/models/founder.py:25-33 email, phone (unique), date_of_birth, gender, state, district, city are nullable=False; frontend Founder type (completeness.ts:5-18) has them all optional. users.email (models/user.py:22) and founders.email (founder.py:24) are two unique copies of the same fact. TASKS 3.1.2 says 'CRUD with auth on the existing tables'.
- **Resolution:** build it in models/founder.py, a new Alembic migration, the 3.1.2.1 schemas using **Alembic migration making non-essential columns nullable and dropping founders.email in favour of users.email**. Matches the browser's optional draft, removes the duplicate identity field, and keeps typed columns for eligibility and encryption.

| Option | Why it is a candidate | Cost | Advantages | Drawbacks |
|---|---|---|---|---|
| Alembic migration making non-essential columns nullable and dropping founders.email in favour of users.email | Alembic already used; §5.2 step-wise changes | free/open source | Collect only what a feature needs; one email source | Uniqueness on phone must become a partial unique index |
| Keep the table, split sensitive fields into a separate founder_sensitive table created only on need | Common minimisation pattern | free/open source | Pairs well with field encryption (3.2.2) and consent per purpose | Extra join and model |
| Store the profile as one JSONB document like sessions | Mirrors decision 0003 | free/open source | Matches the browser draft directly | Loses constraints and indexes the eligibility queries use |

- **Not chosen, and why:**
  - Separate sensitive table: worthwhile later with 3.2.2 but does not by itself fix the NOT NULL failures. JSONB document: throws away constraints the schemes code relies on.
- **Also found as:** F-B2-013

#### F-B2-015: The server profile never reaches the conversation; keys and vocabularies do not match

Weight 74 · Missing function · impact 3/5, reach 4/5, confidence 3/3 · found by B2 · merged as [R081](../arena/details-p3.md#r081)

- **Issue:** 3.1.2 promises 'founder memory across devices', but the Talk agent still asks district and sector every time, because nothing maps the server profile to the slot keys. If someone wires it naively, a free-text domain such as 'Agritech' or 'Textiles' lands at 0.95 confidence as a non-enum string. It is then never asked again, yet it does not match the Sector enum used by schemes and cohort (the same silent-string issue found at 2.1.4).
- **Cause:** backend/app/elicitation/engine.py:59 PROFILE_SLOTS = ('district','founder_years','founder_skills','owned_assets','sector'), and :118-120 put any non-empty profile value at confidence 0.95 with Source.PROFILE, unvalidated. frontend/src/voice/agentClient.ts:99-103 startSession sends only name and private, never the profile. The profile model names the sector 'domain' (models/startup.py, String 255) and stage free text, and holds no founder_years, founder_skills or owned_assets. routers/ideation.py:250-251 says profile values are 'never asked again'.
- **Resolution:** build it in backend/app/routers/ideation.py agent_start (load the signed-in founder's profile on the server, not from the client); a profile-to-slot mapper next to elicitation/engine.py that validates against slot enums; 3.1.2 task text using **Server-side mapper: profile row to slot dict, enum-validated, unknown values dropped or at confidence below 0.5**. Delivers the cross-device memory 3.1.2 promises without trusting client input, and turns vocabulary mismatches into a re-ask rather than a frozen wrong value. It also gives D5's mapping a single place to plug in.

| Option | Why it is a candidate | Cost | Advantages | Drawbacks |
|---|---|---|---|---|
| Server-side mapper: profile row to slot dict, enum-validated, unknown values dropped or at confidence below 0.5 | Pure Python next to engine.start; the Slot enums in elicitation/slots.py already exist | free/open source | One trusted source; invalid values get re-asked instead of frozen | Needs auth on the start endpoint to know the founder (3.1.1) |
| Client sends the profile in startSession | The body field already exists (routers/ideation.py:251) | free/open source | Works before 3.1.1 | The client can inject 0.95-confidence values; same vocabulary mismatch |
| Store the profile with slot keys and enums (sector instead of domain) | Align the schema to the elicitation vocabulary | free/open source | No mapping layer | Couples the profile table to the conversation's internal names; waits on D5 |

- **Not chosen, and why:**
  - Client-sent profile: the client can inject 'never ask again' values. Schema renamed to slot keys: ties the founder record to conversation internals and blocks on D5.
- **Also found as:** F-B3-017

#### F-B2-016: Founder and Startup carry soft delete plus unique email/phone/GSTIN, against D12 erasure

Weight 61 · Logic flaw · impact 3/5, reach 3/5, confidence 2/3 · found by B2 · merged as [R167](../arena/details-p3.md#r167)

- **Issue:** If the 3.1.2 CRUD follows the models and soft-deletes, a 'deleted' founder's personal data stays in the table, against DPDP erasure. Their email, phone and GSTIN stay unique, so the same person cannot sign up again. Startups and profile_completeness are not cascaded. Every query must also remember to filter deleted_at.
- **Cause:** backend/app/models/founder.py:18 and startup.py:16 use SoftDeleteMixin (db/base.py:43-44 deleted_at). founders.email and phone are unique, and startups.cin_number, dpiit_number and gstin are unique. Startup's FK is ondelete=CASCADE, which fires only on a hard delete. TASKS D12 recommends erasure.
- **Resolution:** build it in backend/app/models/founder.py, startup.py (drop SoftDeleteMixin in the 3.1.2 migration); routers /profiles DELETE as a hard delete; 3.2.4.1 delete-all-for-user using **Drop SoftDeleteMixin; hard delete with FK cascades (and an audit row without personal data)**. Aligns the schema with the recommended D12 decision before 3.1.2 writes real records, and reuses the cascades already defined.

| Option | Why it is a candidate | Cost | Advantages | Drawbacks |
|---|---|---|---|---|
| Drop SoftDeleteMixin; hard delete with FK cascades (and an audit row without personal data) | Matches D12 and SYSTEM-DESIGN 5.4; the cascades already exist | free/open source | Erasure is real; unique constraints free up; simpler queries | No undo (mitigated by backups for 7 days) |
| Keep soft delete, use partial unique indexes (WHERE deleted_at IS NULL), and purge after N days | Common PostgreSQL pattern | free/open source | An undo window | Personal data kept after the request; contradicts D12's recommendation |
| Anonymise on delete (null personal columns, keep rows) | Pseudonymisation pattern | free/open source | Keeps aggregate counts | NOT NULL columns block it; analytics already rebuild from sessions |

- **Not chosen, and why:**
  - Partial unique plus purge: keeps personal data after an erasure request. Anonymise: conflicts with the NOT NULL columns, and no aggregate depends on these rows.

### 3.1.3 Move the other browser-only state to the server

#### F-B2-017: Journey.tsx and journeyStore.ts share the 'vanigam_journey' key with different shapes

Weight 78 · Logic flaw · impact 4/5, reach 3/5, confidence 3/3 · found by B2 · merged as [R018](../arena/details-p3.md#r018)

- **Issue:** When a founder saves the Journey page, the next loadJourney() (Consent, Ideate) sees no version, returns EMPTY, and loses the per-purpose consent choices and all milestone tracking. When Consent or Ideate saves first, Journey.tsx loads an object without 'facts', and render throws a TypeError on facts.district. 3.1.3.1 'journey and milestone status' would move whichever copy won last, so data is lost before it ever reaches the server.
- **Cause:** frontend/src/journeyStore.ts:21 KEY = 'vanigam_journey' stores {version: 1, entry_mode, reg_subtype, terrain, consent, milestones}, and :70 discards any record whose version is not 1. frontend/src/pages/Journey.tsx:48 uses the same KEY to store {facts, done} with no version (:78), and :66-73 return the parsed object as is. Journey.tsx:154 then uses saved.facts, and :189/:204 index facts[...] and facts.district.
- **Resolution:** build it in frontend/src/pages/Journey.tsx (own key, e.g. 'vanigam_registration_journey', or fold into journeyStore with a version bump and a migration); 3.1.3.1 server shape using **Merge registration facts into journeyStore (version 2) with a migration from both shapes**. 3.1.3 needs one journey record per founder on the server anyway. Merging now gives one shape to sync, and replacing the discard-on-mismatch with a migration stops the silent loss.

| Option | Why it is a candidate | Cost | Advantages | Drawbacks |
|---|---|---|---|---|
| Give Journey.tsx its own versioned key and a one-time rescue of {facts, done} records | Smallest change; follows journeyStore's own versioning comment | free/open source | Ends the collision at once; no behaviour change elsewhere | Two browser records to sync in 3.1.3 |
| Merge registration facts into journeyStore (version 2) with a migration from both shapes | One store per founder route, as journeyStore's header intends | free/open source | One record to move to the server | Needs a migration, not journeyStore's discard rule |
| A typed storage helper with a key registry and zod schemas | zod is a popular TypeScript schema library | free/open source | Prevents any future collision; validates on read | A new dependency and a refactor of six call sites |

- **Not chosen, and why:**
  - Separate key: quickest, but it leaves two records that 3.1.3 must reconcile. zod registry: right in the long run, but more refactor than the bug needs.
- **Also found as:** F-B3-018, F-A3-006

#### F-B2-018: Sign-out keeps the founder's browser data; the next user inherits it and its sync

Weight 78 · Missing logic · impact 4/5, reach 3/5, confidence 3/3 · found by B2 · merged as [R060](../arena/details-p3.md#r060)

- **Issue:** Shared devices (college labs, browsing centres, a family phone) are common for first-time founders. After sign-out, the next person sees the previous founder's profile, caste category, investor pipeline and supplier quotes, and Talk resumes the previous founder's conversation. Once 3.1.1/3.1.2/3.1.3 sync browser state on sign-in, the next user's sign-in would upload the previous founder's data into the new account, a DPDP breach the plan does not mention.
- **Cause:** frontend/src/auth.tsx:53-56: logout() only calls setTokens(null) and setUser(null). The keys vanigam_profile, vanigam_journey, vanigam_pipeline, vanigam_suppliers and vanigam_talk_session (profileStore.ts:3, journeyStore.ts:21, Pipeline.tsx:38, Suppliers.tsx:39, Talk.tsx:29) are not scoped per user and survive. Agent sessions are readable by ID alone (routers/ideation.py:299-302, no auth).
- **Resolution:** build it in frontend/src/auth.tsx (clear or namespace founder keys on logout and on account switch); the 3.1.3 sync (upload anonymous browser state only with an explicit 'this is mine' confirmation) using **Namespace keys by user ID, clear the anonymous namespace on logout, and confirm before claiming it**. It is the only option that handles both the shared-device leak and the sync-into-the-wrong-account case that 3.1.1-3.1.3 create, without discarding a founder's unsynced work.

| Option | Why it is a candidate | Cost | Advantages | Drawbacks |
|---|---|---|---|---|
| Namespace keys by user ID, clear the anonymous namespace on logout, and confirm before claiming it | Standard multi-user client storage practice | free/open source | Fixes both leakage and wrong-account sync; anonymous drafts can still be claimed knowingly | Touches every storage call site |
| Clear all vanigam_* keys on logout | A simple loop over localStorage | free/open source | Trivial, closes the leak | A founder who has not synced yet loses their drafts on sign-out |
| sessionStorage for sensitive fields (caste, finance, session ID) | A browser API; cleared when the tab closes | free/open source | Limits exposure on shared machines | Founders lose state across tabs; does not fix the sync claim |

- **Not chosen, and why:**
  - Clear all on logout: loses unsynced drafts, and an anonymous user's data is still claimed blindly at the next sign-in. sessionStorage: partial, and it breaks multi-tab use.
- **Also found as:** F-A3-005

#### F-A3-006: Journey.tsx and journeyStore.ts write different shapes to the same key vanigam_journey

Weight 77 · Logic flaw · impact 4/5, reach 4/5, confidence 2/3 · found by A3 · merged as [R018](../arena/details-p3.md#r018)

- **Issue:** Visiting /journey after /start or /consent makes Journey render with facts undefined (crash at facts.district); visiting /journey first and then Start or Consent wipes Journey's facts and done steps, and Journey's write wipes the consent flags and milestone status. 3.1.3.1 would migrate whichever shape happens to be there to the server.
- **Cause:** frontend/src/journeyStore.ts:21 KEY='vanigam_journey' stores {version, entry_mode, reg_subtype, consent, milestones}; frontend/src/pages/Journey.tsx:48 uses the same KEY and stores {facts, done} on mount (useEffect at :160-161). journeyStore.loadJourney discards anything without version===1 (:71); Journey.tsx:154 reads saved.facts, which is undefined after Start/Consent wrote the other shape, and :204 reads facts.district.
- **Resolution:** build it in frontend/src/pages/Journey.tsx, journeyStore.ts; the server model in 3.1.3.1 using **Separate keys (vanigam_journey_steps) with a one-time shape-sniffing migration**. Smallest fix that stops the crash and the consent wipe today; the server model in 3.1.3.1 can then define one record cleanly.

| Option | Why it is a candidate | Cost | Advantages | Drawbacks |
|---|---|---|---|---|
| Separate keys (vanigam_journey_steps) with a one-time shape-sniffing migration | Plain TypeScript | free/open source | Fixes both crash and data loss now; tiny | Two local records until 3.1.3 merges them on the server |
| Fold facts and done into the versioned Journey type (VERSION 2) | journeyStore already versions its shape | free/open source | One record, one server table later | Version bump discards existing v1 records per loadJourney's rule |
| zod schema validation on load for every store | zod is the common TS runtime validator | free/open source | Catches any future shape clash | New dependency; does not by itself separate the records |

- **Not chosen, and why:**
  - Folding into VERSION 2: the store's own rule throws away current consent and milestones on upgrade. zod: guards shapes but still leaves two writers fighting over one key.
- **Also found as:** F-B3-018, F-B2-017

#### F-B2-020: Consent page purposes do not match 3.2.1 and promise dropped features (digest, match cards)

Weight 68 · Missing logic · impact 3/5, reach 3/5, confidence 3/3 · found by B2 · merged as [R079](../arena/details-p3.md#r079)

- **Issue:** 3.2.1.2 ('Consent.tsx writes to it') would carry these records to the server. Founders would be recorded as consenting to a digest and partner match cards that do not exist, and there would be no record for the purposes that do run: voice, quality review and cohort. That is consent for the wrong purposes under DPDP. Cohort consent ends up in a third place (the session flag, and the 5.5.1 Talk checkbox), unconnected to this page.
- **Cause:** frontend/src/pages/Consent.tsx:33-65 PURPOSES = core, caste, financial, idea_ip ('masked in partner match cards'), digest ('in-app, then email, then SMS'). The choices are stored in journeyStore.consent (Consent.tsx:85-91). TASKS 3.2.1 lists conversation, voice, quality review, cohort, caste, financial and idea IP. TASKS Dropped removes notifications, digests and SMS, and offering-side B2B profiles. The agent session's cohort_consent is a separate flag (agents/ideation.py:130) that the Talk page never sets (voice/agentClient.ts:103).
- **Resolution:** build it in frontend/src/pages/Consent.tsx (purposes = the 3.2.1 list); journeyStore consent (migrate the ids); 5.5.1 (the Talk checkbox reads and writes the same cohort purpose) using **One shared purpose list (a JSON file read by the frontend and the backend) used by Consent.tsx, 3.2.1 and 5.5.1**. The consent purposes are a legal contract shared by three tasks. One list removes the dropped-feature promises and joins up the cohort consent that today lives in two places.

| Option | Why it is a candidate | Cost | Advantages | Drawbacks |
|---|---|---|---|---|
| One shared purpose list (a JSON file read by the frontend and the backend) used by Consent.tsx, 3.2.1 and 5.5.1 | A single-source-of-truth pattern; the backend already serves reference JSON | free/open source | Purposes cannot drift between screen, table and agent | A small loader on both sides |
| Edit Consent.tsx PURPOSES to the 3.2.1 list by hand | Minimal change | free/open source | Fast | Can drift again |
| Drop the Consent page until 3.2.1 lands | Avoids recording wrong consent | free/open source | No false records | Caste and financial use then has no consent screen at all |

- **Not chosen, and why:**
  - Hand edit: fixes today's list, but it drifts again because nothing ties the copies together. Dropping the page: leaves the protected-class uses (caste, finance) without any consent step.
- **Also found as:** F-B3-006, F-A3-013

#### F-B2-019: No merge or conflict rule for moving browser state to the server (two devices, first sync)

Weight 61 · Missing structure · impact 3/5, reach 3/5, confidence 2/3 · found by B2 · merged as [R169](../arena/details-p3.md#r169)

- **Issue:** At the first sign-in on a second device, the server and the browser both hold a pipeline or quote list. Last write wins, so one device's work silently erases the other's. Time-based local IDs collide across devices, so a merge by ID can overwrite the wrong investor entry. The founder loses the investor contacts or quotes that 3.1.3 exists to protect.
- **Cause:** TASKS 3.1.3 says only 'store each on the founder's record'. frontend/src/pages/Pipeline.tsx:52-66 and Suppliers.tsx:102-110/236-242 save whole arrays with no version or timestamp. Pipeline IDs are 'local-${Date.now()}' (Pipeline.tsx:116), and supplier IDs come from a Date.now() counter (Suppliers.tsx:113-114). journeyStore.ts:70 discards a mismatched record instead of migrating it. By contrast, the session store has version-checked saves (agents/store.py:98-125).
- **Resolution:** build it in the 3.1.3 endpoints (version per record with 409 like the session store); frontend stores (UUID IDs via crypto.randomUUID, updated_at per item); a first-sync merge rule using **Per-record version and updated_at with 409 on conflict, and a union-by-UUID merge at first sync**. It reuses the concurrency rule the platform already trusts for sessions, keeps it in one shape across stores, and makes conflicts visible instead of silent.

| Option | Why it is a candidate | Cost | Advantages | Drawbacks |
|---|---|---|---|---|
| Per-record version and updated_at with 409 on conflict, and a union-by-UUID merge at first sync | Reuses the optimistic-concurrency pattern of decision 0003 and the session store | free/open source | No silent loss; consistent with the existing store | The client must handle a 409 by reloading |
| CRDT sync (Yjs or Automerge) | Mature open-source CRDT libraries | free/open source | Automatic merging, offline-first | Heavy for a few lists; a new storage format on the server |
| Server wins after first sign-in; the browser is a cache only | Simple authoritative-server model | free/open source | Easy to reason about | Edits made offline or before the first sync are lost |
| Last write wins with item timestamps | The common default | free/open source | No conflicts to show | Silent loss when clocks or devices differ |

- **Not chosen, and why:**
  - CRDTs: far heavier than a handful of short lists needs. Server wins: drops offline edits. Last write wins: the silent loss this flag is about.

#### F-A4-020: Pipeline metrics wrong: lost deals count as reaching every stage; first-stage time is lost

Weight 58 · Logic flaw · impact 2/5, reach 3/5, confidence 3/3 · found by A4 · merged as [R186](../arena/details-p3.md#r186)

- **Issue:** A founder reads inflated conversion and zero time-in-stage, so the board says the funnel is healthier and faster than it is. Programme aggregates (5.5.5) will inherit these metrics once the board moves server-side (3.1.3).
- **Cause:** pipeline.py:131-132 _reached treats a terminal entry with no history as having passed all open stages. Ran [closed_lost (no history), initial_contact]: conversion to negotiation and term_sheet 50%. Pipeline.tsx:120 stamps history with new Date().toISOString() ('2026-10-17T10:00:00.000Z'), but pipeline.py:138 uses date.fromisoformat, which raises on that string (checked: 'Invalid isoformat string'), so the first stage's days are dropped (ran: initial_contact avg_days 0.0 after 9 days). STAGE_PROBABILITY (pipeline.py:33-42) gives uncited closing odds that drive 'weighted value'.
- **Resolution:** build it in backend/app/funding/pipeline.py (_reached, _days), Pipeline.tsx (date format), weighted-value labelling using **Parse with datetime.fromisoformat (Python 3.11 accepts 'Z') then take .date(); terminal entries without history count only their terminal stage; label weighted value 'rule of thumb' or drop it**. Three small changes fix the numbers with the standard library and keep old boards loading.

| Option | Why it is a candidate | Cost | Advantages | Drawbacks |
|---|---|---|---|---|
| Parse with datetime.fromisoformat (Python 3.11 accepts 'Z') then take .date(); terminal entries without history count only their terminal stage; label weighted value 'rule of thumb' or drop it | Standard library; small fixes | free/open source | Correct numbers; no dependency | Old entries without history lose inferred stages |
| python-dateutil parser | Widely used date parsing library | free/open source | Accepts any format | Extra dependency for one format the stdlib handles |
| Require history on every entry (422 without it) | Strict contract | free/open source | No inference needed | Breaks existing localStorage boards |

- **Not chosen, and why:**
  - dateutil: unneeded dependency; strict history: breaks saved boards

## 3.2 Consent and protection

### 3.2.1 Consent per purpose

#### F-B3-005: Caste is used in ranking and sent by default, against the consent text

Weight 84 · Logic flaw · impact 4/5, reach 4/5, confidence 3/3 · found by B3 · merged as [R021](../arena/details-p3.md#r021)

- **Issue:** A founder who never consented, or declined caste use, still has a caste value (by default 'sc') driving ranking. The consent record 3.2.1 builds would then misdescribe what the system does, the worst outcome for a DPDP record. Seeing a default of 'sc' is also misleading and arguably offensive.
- **Cause:** Consent.tsx:41-44 promises caste is 'Checked only against reserved-category eligibility rules ... never used for ranking anything else'. But schemes/ranking.py:29-30 adds an 'sc_st' axis from caste_category, and :67-73 and :96 feed it into the likelihood half of the composite sort key, so caste changes the order of eligible schemes. Schemes.tsx:46-49 pre-fills caste_category: 'sc' (and gender 'female') as the default form state, and :75 sends it to /schemes/recommend with no check of journey.consent.caste. grep shows no backend code reads consent at all. 1.4.3 plans to project session slots onto this same scheme profile, which would bypass consent the same way.
- **Resolution:** build it in schemes/ranking.py (_founder_axes), routers/schemes.py (consent gate on input), Schemes.tsx defaults, Consent.tsx wording; the 1.4.3 projection using **Server-side purpose gate: strip protected fields unless consent for that purpose is present**. Consent only means something if the server enforces it, and 1.4.3 will add a second caller that never passes through the browser. Also remove the 'sc'/'female' defaults and keep caste out of the likelihood score unless the founder has consented to it.

| Option | Why it is a candidate | Cost | Advantages | Drawbacks |
|---|---|---|---|---|
| Server-side purpose gate: strip protected fields unless consent for that purpose is present | A FastAPI dependency or a Pydantic validator on RecommendIn; fits the existing stack | free/open source | One enforced rule for every caller (Schemes form, 1.4.3 projection, future screens); the consent record becomes true | Until 3.2.1's table exists, an anonymous caller must send its consent flags with the request |
| Change the consent wording to say caste also affects ranking | Copy change in Consent.tsx | free/open source | Trivial; keeps the ranking | Still sends caste without consent; widens the purpose instead of honouring it |
| Policy engine (Open Policy Agent / Oso) for purpose checks | Mature open-source policy engines | free/open source | Declarative rules, auditable | A new runtime for a handful of rules; heavy for a single-owner project |
| Client-side only: Schemes.tsx omits caste unless journey.consent.caste | A few lines in React | free/open source | Fast | Not enforced: any other client, and the 1.4.3 projection, still bypass it |

- **Not chosen, and why:**
  - Rewording: legalises current behaviour instead of honouring the narrower purpose and still sends unconsented data. Policy engine: an extra service for a few rules, against the simple single-owner stack. Client-only: unenforced, and the 1.4.3 projection bypasses it.
- **Also found as:** F-A3-015

#### F-A3-015: Caste is collected and sent with no consent gate; Schemes page pre-fills 'sc' and 'female'

Weight 84 · Logic flaw · impact 4/5, reach 4/5, confidence 3/3 · found by A3 · merged as [R021](../arena/details-p3.md#r021)

- **Issue:** A founder who never chose shows up as an SC woman: the server receives a protected attribute nobody gave, and rankings favour schemes the founder may not qualify for. Under DPDP, caste is processed without consent for that purpose. Recording consent in 3.2.1 fixes nothing while the screens ignore it.
- **Cause:** frontend/src/pages/Schemes.tsx:46-50 initial state gender 'female', caste_category 'sc', and :75 sends caste_category to /schemes/recommend; schemes/ranking.py:27-30 adds women and sc_st axes from them. Profile.tsx:183 asks for caste without reading journey.consent.caste (Consent.tsx:41-44 defines that purpose). Backend elicitation already treats caste as SENSITIVE_DEFERRED (elicitation/slots.py:365-367).
- **Resolution:** build it in Schemes.tsx (empty defaults), Profile.tsx (gate on consent), schemes router (drop protected fields without a consent claim) using **Empty defaults + UI gate + server drops caste/financial fields unless the consent record allows**. Removing the invented defaults fixes the wrong answers today, and the server check makes consent binding rather than cosmetic.

| Option | Why it is a candidate | Cost | Advantages | Drawbacks |
|---|---|---|---|---|
| Empty defaults + UI gate + server drops caste/financial fields unless the consent record allows | Plain React state and a FastAPI dependency reading 3.2.1's table | free/open source | Defence in both layers; matches SENSITIVE_DEFERRED intent | Server check needs the consent table (anonymous use passes nothing protected) |
| UI-only gate | Frontend change | free/open source | Quick | Server still accepts caste from any client |
| Ask caste only inside the scheme result ('3 more schemes if you share your category') | Just-in-time consent pattern | free/open source | Purpose is visible at the moment of asking | Extra round trip; UI work waits on the theme decision |

- **Not chosen, and why:**
  - UI-only gate: any client can still send caste. Just-in-time prompt: good UX but still needs the server gate, and it waits on the theme decision.
- **Also found as:** F-B3-005

#### F-A3-016: Private mode and voice consent aren't enforced: replies go to Gemini/Sarvam TTS

Weight 78 · Missing logic · impact 4/5, reach 3/5, confidence 3/3 · found by A3 · merged as [R015](../arena/details-p3.md#r015)

- **Issue:** A founder who ticks 'private' is told nothing leaves Vanigam (0004 covers outbound search), yet every spoken reply carrying their idea goes to Google's free tier, which may use the text (0009), or to Sarvam. The server cannot check voice consent or private mode because /speak knows no session. An open /speak also lets anyone spend the free TTS quota.
- **Cause:** frontend/src/pages/Talk.tsx:176 calls speaker.say(ev.data) whenever voice is on, regardless of isPrivate (:128, :379); routers/voice.py:98-121 /speak takes free text with no session_id and no auth, and sends it to gemini_tts.speak (:88) or sarvam.speak (:114). Mentor sentences restate the founder's idea and facts.
- **Resolution:** build it in routers/voice.py (/speak takes session_id and checks private and voice consent), Talk.tsx (no remote voice in private mode; phrasebook or browser speech only) using **Session-scoped /speak: require session_id, refuse remote TTS for private sessions or without voice consent, fall back to phrasebook/browser**. It makes the private promise and voice consent hold on the server using fallbacks that already exist.

| Option | Why it is a candidate | Cost | Advantages | Drawbacks |
|---|---|---|---|---|
| Session-scoped /speak: require session_id, refuse remote TTS for private sessions or without voice consent, fall back to phrasebook/browser | Existing store and phrasebook fallback (voice.py:103-108) | free/open source | Enforced server-side; also limits quota abuse to real sessions | One more parameter on every speak call |
| Frontend-only: disable Gemini/Sarvam voice when private | Talk.tsx flag | free/open source | Trivial | Not enforced; any client can still send text |
| Local TTS (Piper / espeak-ng) for private sessions | Piper is an open-source offline neural TTS with Indian-language voices; espeak-ng widely packaged | free/open source | Private sessions keep speech | New runtime dependency and voice quality varies for Tamil |

- **Not chosen, and why:**
  - Frontend-only: a promise the server doesn't keep. Piper/espeak: a worthwhile later upgrade, but it adds a dependency and does not by itself enforce consent.
- **Also found as:** F-B3-008, F-A1-022

#### F-B3-006: No shared purpose list; screen purposes differ from the plan and the session flag

Weight 74 · Missing structure · impact 3/5, reach 4/5, confidence 3/3 · found by B3 · merged as [R079](../arena/details-p3.md#r079)

- **Issue:** Founders are asked to agree to features that do not exist and are never asked about ones that do (voice, quality review). The same purpose (cohort) is asked in two places and can disagree. When 3.2.1 builds its table, nothing defines the purpose IDs both sides must use.
- **Cause:** Consent.tsx:33-65 offers core, caste, financial, idea_ip and digest. 3.2.1 lists conversation, voice, quality review, cohort, caste, financial and idea IP. Cohort consent lives elsewhere, as share_with_programme on session start (routers/ideation.py:256, agents/ideation.py:205-210), and 5.5.1 adds a second checkbox for it on the Talk page. 'digest' (Consent.tsx:60-63, 'in-app first, then email, then SMS') and 'idea_ip' ('partner match cards', :53-57) describe features listed under Dropped (notifications; matching among platform founders). journeyStore.ts:48-49 keeps consent as a free-form Record<string, boolean>.
- **Resolution:** build it in A purpose registry beside the consent model (backend), exported to the frontend; Consent.tsx; Talk.tsx (5.5.1); journeyStore.ts using **One purpose registry as a Python Enum, published through OpenAPI and used by the generated TS types**. It gives the 3.2.1 table, the server-side gate (previous flag), Consent.tsx and the Talk checkbox one set of IDs that cannot drift. It also forces the drop of 'digest' and 'idea_ip' and the addition of voice and quality review.

| Option | Why it is a candidate | Cost | Advantages | Drawbacks |
|---|---|---|---|---|
| One purpose registry as a Python Enum, published through OpenAPI and used by the generated TS types | FastAPI already emits OpenAPI; openapi-typescript is a mature free generator | free/open source | One list for the backend table, the screens and the gate; renames break the build | Adds a type-generation step to the frontend build |
| A purposes JSON data file read by both sides | Matches the repo's pattern of reference data in Git | free/open source | Wording and IDs reviewed by commit; easy to translate | No compile-time check on the frontend |
| PostgreSQL enum type for purpose | Native PostgreSQL feature with an Alembic migration | free/open source | Database refuses unknown purposes | Waits on 2.1.1; does not reach the frontend; enum changes need migrations |
| Keep free-form strings and document them | Status quo | free/open source | No work | Drift continues, as already seen |

- **Not chosen, and why:**
  - JSON file: no build-time check, so the drift that already happened can recur. PostgreSQL enum: blocked on 2.1.1 and invisible to the frontend. Free-form strings: the cause of the current mismatch.
- **Also found as:** F-A3-013, F-B2-020

#### F-A3-013: Consent page's purposes don't match the design list and it offers a dropped feature

Weight 74 · Missing logic · impact 3/5, reach 4/5, confidence 3/3 · found by A3 · merged as [R079](../arena/details-p3.md#r079)

- **Issue:** 3.2.1.2 'Consent.tsx writes to it' would put a purpose list that matches neither the design nor the code paths into the table: voice and cohort consent have no row, and the founder agrees to a digest that will never exist. Under DPDP, a consent record must say which notice the founder saw. Without a notice version, the record cannot prove informed consent after the wording changes (1.5.4 adds a Gemini notice).
- **Cause:** frontend/src/pages/Consent.tsx:33-65 lists core, caste, financial, idea_ip, digest. SYSTEM-DESIGN §5.4 and TASKS 3.2.1 name conversation, voice, quality review, cohort, caste, financial, idea IP. Voice, quality review and cohort are missing; 'digest' promises 'email, then SMS' although notifications are in Dropped. journeyStore.ts:49 stores only booleans: no time, no notice text or version.
- **Resolution:** build it in a shared purposes definition (backend constant served to the frontend), Consent.tsx, the 3.2.1 table (add notice_version) using **Backend-owned purpose registry (enum + notice text + version) served by GET /consents/purposes**. One definition drives the page, the table and the enforcement checks, and records which notice the founder agreed to.

| Option | Why it is a candidate | Cost | Advantages | Drawbacks |
|---|---|---|---|---|
| Backend-owned purpose registry (enum + notice text + version) served by GET /consents/purposes | FastAPI + Pydantic enum; one source for UI and checks | free/open source | Code paths check the same keys the UI shows; the version is stored with each row | One more endpoint |
| Edit the frontend list by hand to match the design | Direct edit | free/open source | Fastest | Drifts again; backend checks use different strings |
| Consent-management platform (e.g. Klaro, Osano) | Klaro is open source, Osano paid | free/open source (Klaro), paid (Osano) | Ready UI and records | Built for cookie banners, not purpose consent tied to server checks; Osano is paid |

- **Not chosen, and why:**
  - Hand edit: the two sides drift again and checks have no shared keys. Klaro/Osano: cookie-banner tools that don't fit server-side purpose checks
  - Osano breaks the free constraint.
- **Also found as:** F-B3-006, F-B2-020

#### F-B3-007: Consent given in anonymous sessions has no record, no withdrawal, no claim path

Weight 68 · Missing logic · impact 3/5, reach 3/5, confidence 3/3 · found by B3 · merged as [R131](../arena/details-p3.md#r131)

- **Issue:** An anonymous founder who ticked 'share with programme' cannot withdraw except by deleting the whole conversation. There is no proof of when they agreed or to what text. And when they later sign up (3.1.1), the plan says nothing about carrying the session's consent into core.consents, so the two records can disagree.
- **Cause:** 3.2.1 waits on 3.1.1 and keys rows to a founder. But cohort consent is already taken today on anonymous sessions: share_with_programme is set once in new_session (agents/ideation.py:205-210) and stored as cohort_consent (:130, :159). No endpoint changes it after start (routers/ideation.py routes: start, resume, delete, turns, notices only), and nothing stores when it was given or which wording was shown. cohort/programme.py:40 counts it with no time check. 5.5.1 ('When: now') will add the checkbox before 3.2.1 exists.
- **Resolution:** build it in agents/ideation.py (consent events on the session document), routers/ideation.py (a consent update route), the 3.2.1 table design (subject = session or user), 3.1.1 claim step using **Consent events inside the session JSON (purpose, granted/withdrawn, time, notice version), plus a PATCH route; copied into core.consents on claim**. It gives withdrawal and proof today on every store and keeps decision 0003. It also makes the cohort reader check the latest event instead of a boolean fixed at start, and gives 3.1.1 a defined claim step for consent.

| Option | Why it is a candidate | Cost | Advantages | Drawbacks |
|---|---|---|---|---|
| Consent events inside the session JSON (purpose, granted/withdrawn, time, notice version), plus a PATCH route; copied into core.consents on claim | Fits decision 0003 (one JSON document) and works with no database | free/open source | Withdrawal and proof now for anonymous founders; one migration path on sign-up | Two stores until the claim; the copy must be tested |
| core.consents with a nullable user_id and a session_id subject | SQLAlchemy/Alembic table as 3.2.1 plans | free/open source | One table for both kinds of subject | Waits on 2.1.1; nothing to write to on the memory store |
| Defer cohort consent until sign-up (remove it from anonymous sessions) | Plan change: 5.5.1 waits on 3.1.1 | free/open source | Single record keyed to a founder | Programme view stays empty until accounts and the database exist |
| Consent management platform (e.g. a hosted CMP) | Commercial consent tools | paid | Ready-made records and UI | Paid and online; sends founder data to a third party |

- **Not chosen, and why:**
  - Nullable-user table: blocked on 2.1.1, so 5.5.1 would still ship with no record. Deferring cohort consent: empties a built feature for months. Hosted CMP: paid and sends data off the platform, against the free/offline rule and decision 0004.

#### F-A3-014: In-session consents (cohort, private) are set once at start and cannot be withdrawn

Weight 68 · Missing logic · impact 3/5, reach 3/5, confidence 3/3 · found by A3 · merged as [R120](../arena/details-p3.md#r120)

- **Issue:** DPDP requires that withdrawing consent is as easy as giving it. A founder who opted into programme sharing cannot opt out except by deleting the whole conversation. Once 3.2.1 adds a consents table there will be two sources of truth, and the cohort will keep counting a founder who withdrew in the table.
- **Cause:** backend/app/agents/ideation.py:210 sets s.cohort_consent only in new_session; routers/ideation.py:249-257 accepts share_with_programme and private only on POST /sessions; no endpoint changes them later. cohort/programme.py:40 reads s.cohort_consent from the session document, separate from the planned core.consents table.
- **Resolution:** build it in routers/ideation.py (PATCH session consent or consent API), agents/ideation.py, cohort/programme.py reads the consent record using **Consent table is the only source; the session holds a consent_id, and the cohort joins on active consents**. Withdrawal works the moment it is recorded, and the cohort and audit log read one truth.

| Option | Why it is a candidate | Cost | Advantages | Drawbacks |
|---|---|---|---|---|
| Consent table is the only source; the session holds a consent_id, and the cohort joins on active consents | SQLAlchemy join; fits 3.2.1's table | free/open source | Withdrawal takes effect at the next read; one truth | Anonymous sessions need a session-scoped consent row before sign-in |
| PATCH /ideation/agent/sessions/{id} to flip cohort_consent, mirrored into the table | Small FastAPI route | free/open source | Quick, works before 3.2.1 | Two copies to keep in sync |
| Event-sourced consent log (append grant/withdraw events) | Common audit pattern | free/open source | Full history for 3.2.3 | More code to derive current state |

- **Not chosen, and why:**
  - PATCH plus mirror: keeps the split-brain the flag is about. Event sourcing: history is useful, but a row with granted_at/withdrawn_at already gives it for this size.
- **Also found as:** F-B2-008, F-B3-015

### 3.2.2 Field encryption for sensitive columns

#### F-A3-018: Field encryption plan breaks unique and indexed columns; no key or blind-index design

Weight 61 · Missing structure · impact 3/5, reach 3/5, confidence 2/3 · found by A3 · merged as [R166](../arena/details-p3.md#r166)

- **Issue:** Randomised AES-GCM (the safe mode) gives a different ciphertext each time, so the unique constraints stop working (duplicate phones allowed) and lookups by phone or email cannot use the index. Deterministic encryption keeps them but leaks equality and is weak for low-cardinality fields like caste. Without a separate key with rotation, the easy path is reusing secret_key, which ties token signing to data encryption.
- **Cause:** backend/app/models/founder.py:13-15 NOTE says phone, date_of_birth, caste_category get an AES-256 TypeDecorator 'transparent' wrap, but phone is unique=True (:25) and indexed (ix_founders_phone :52), and email is unique and indexed (:24, :51). core/config.py has no encryption-key setting; secret_key (:21) is the only secret. TASKS 3.2.2 says only 'field-level encryption through an ORM type'.
- **Resolution:** build it in a core/crypto.py TypeDecorator, a new ENCRYPTION_KEYS setting, migration adding HMAC blind-index columns for lookup fields using **AES-GCM TypeDecorator (cryptography lib) with key ID prefix + HMAC-SHA256 blind index columns for unique/lookup fields**. The only option that keeps the existing unique and indexed lookups, uses a key separate from JWT signing, and supports rotation, all offline.

| Option | Why it is a candidate | Cost | Advantages | Drawbacks |
|---|---|---|---|---|
| AES-GCM TypeDecorator (cryptography lib) with key ID prefix + HMAC-SHA256 blind index columns for unique/lookup fields | pyca/cryptography is the standard Python crypto library; blind index is the common pattern (CipherSweet) | free/open source | Strong encryption, unique constraints and lookups preserved on the HMAC column, key rotation by key ID | Extra columns and a re-encrypt script for rotation |
| sqlalchemy-utils StringEncryptedType | Popular SQLAlchemy extension | free/open source | Drop-in | Default AES engine is deterministic-ish/ECB-like in older versions; no blind index or key rotation |
| PostgreSQL pgcrypto (pgp_sym_encrypt) | Built-in extension | free/open source | No Python crypto code | Key travels in SQL text and can appear in DB logs; harder with the ORM |
| Cloud KMS envelope encryption | AWS/GCP KMS | paid | Managed keys | Paid and online; violates the free/offline constraint |

- **Not chosen, and why:**
  - sqlalchemy-utils: weak defaults, no blind index or rotation. pgcrypto: keys exposed in SQL and logs. Cloud KMS: paid and online.

### 3.2.4 Erasure and retention

#### F-B5-015: No link from a user to their sessions or founder data; all sessions share 'anon'

Weight 78 · Missing structure · impact 4/5, reach 3/5, confidence 3/3 · found by B5 · merged as [R059](../arena/details-p3.md#r059)

- **Issue:** 'Delete by user across tables' has no relation to follow: deleting a user leaves the founder, profile, startups and documents (the FK points the other way), and sessions are matched only by a free string. A delete-all-for-user run on 'anon' (or on any user before 3.1.1 rewrites old rows) would erase every anonymous founder's conversation.
- **Cause:** backend/app/models/agent_session.py:24 user_id String(64), no ForeignKey; agents/ideation.py:118, 203 default user_id 'anon' and routers/ideation.py never passes a user, so every row today has user_id='anon'. models/user.py:24-28 users.founder_id -> founders ON DELETE SET NULL, while profile.py:24, startup.py:22, document.py:25 cascade from founders, not from users.
- **Resolution:** build it in db/migrations (FK or explicit erasure map), models/agent_session.py, models/user.py, the 3.2.4.1 service using **Explicit erasure service with a table map and a guard on 'anon'**. It must reach non-database copies anyway (next flag), handles the string user_id and sentinel safely, and a metadata test stops new tables being forgotten; nullable FKs can be added later as a second guard.

| Option | Why it is a candidate | Cost | Advantages | Drawbacks |
|---|---|---|---|---|
| Explicit erasure service with a table map and a guard on 'anon' | One function listing every table and its user/founder key, run in one transaction, refusing sentinel ids; tested against the model metadata so a new table without an entry fails CI | free/open source | Works across schemas (2.4.1) and JSON documents; the CI check keeps it complete | Map must be maintained |
| Foreign keys with ON DELETE CASCADE from users | PostgreSQL referential actions via Alembic | free/open source | Database enforces completeness | agent_sessions.user_id is a string with 'anon' rows, so it cannot reference users.user_id (UUID) without a nullable column and data migration; Redis and in-memory copies are outside the database anyway |
| Soft delete flag | August Req 6.1 | free/open source | Reversible | Ruled out by D12 (erasure) |

- **Not chosen, and why:**
  - Cascade FKs alone: impossible on the current string column with 'anon' rows and blind to Redis; soft delete: contradicts D12.
- **Also found as:** F-A3-008, F-A2-016

#### F-B5-016: Erasure outside the app leaves the Redis session copy readable

Weight 78 · Missing logic · impact 4/5, reach 3/5, confidence 3/3 · found by B5 · merged as [R062](../arena/details-p3.md#r062)

- **Issue:** For up to six hours after a retention delete or erasure request, the conversation (transcript and facts) is still returned to anyone holding the session id, and the job board keeps its evidence and panel results in memory indefinitely (B5-04 flag 2). An erasure that is not complete in all copies fails the DPDP request the task exists for.
- **Cause:** Ran scratchpad/arena/b5/erase.py: CachedStore(MemoryStore, fake Redis), create a session, delete the row through the inner store as a nightly/erasure process would -> 'session still readable through the app after erasure: True'. store.py:206-213 serves sess:{id} from Redis before the database, TTL IDLE_EXPIRY 6 h (store.py:198). Only the app's DELETE route drops Redis and calls board.forget (routers/ideation.py:316-318); Redis has no user -> session index.
- **Resolution:** build it in the 3.2.4 erasure service and nightly step: collect session ids from PostgreSQL, then drop sess:{id} in Redis and tell the app process to forget them using **Run erasure and retention inside the app (admin endpoint or in-process task)**. Today the app is one process (decision 0010), so reusing the founder delete path clears database, Redis and job board together; pub/sub can be added when several workers exist.

| Option | Why it is a candidate | Cost | Advantages | Drawbacks |
|---|---|---|---|---|
| Delete through the store plus a Redis 'erased' channel the app listens to | redis-py pub/sub already available; the store's CachedStore.delete drops the copy; the app subscribes and calls board.forget | free/open source | Clears Redis and in-memory results from any process | Needs the app running to receive the message; without Redis, falls back to an admin endpoint |
| Run erasure and retention inside the app (admin endpoint or in-process task) | FastAPI route or lifespan task calling store.delete and board.forget, the same path as the founder's delete | free/open source | One code path for all deletes; reaches memory and Redis | Nightly scheduler must call the app; per-worker memory still needs fan-out with several workers |
| Tombstone key checked on read | Write erased:{id} to Redis/DB; CachedStore.get checks it | free/open source | Robust to stale copies | Extra read per turn; tombstones need their own retention |

- **Not chosen, and why:**
  - Pub/sub first: depends on Redis, which is optional; tombstones: a per-turn read cost to patch a path that should not exist.

#### F-A3-017: Spoken-reply audio cache keeps personal content forever and escapes erasure

Weight 68 · Missing logic · impact 3/5, reach 3/5, confidence 3/3 · found by A3 · merged as [R017](../arena/details-p3.md#r017)

- **Issue:** Audio of sentences naming the founder and restating their idea stays on disk with no expiry. One deletion request (SYSTEM-DESIGN §5.4) cannot find it because the key has no session, so erasure is incomplete. Class D data ends up in an un-catalogued store.
- **Cause:** backend/app/routers/voice.py:67-77 caches each reply's audio in .cache/voice under sha1(model\|voice\|language\|text); :84 and :112 reuse it with path.exists() and no age check; nothing deletes these files. 2.2.5 purges only .cache/research; 3.2.4.1 deletes by user across tables, and these files carry no session or user key.
- **Resolution:** build it in routers/voice.py cache paths, the nightly job (5.4.4), the erasure routine (3.2.4.1) using **Cache only phrasebook/fixed sentences; serve dynamic replies uncached (Cache-Control: no-store)**. Data minimisation by construction: nothing personal is stored, so nothing needs erasing. Fixed sentences carry most of the cache benefit anyway.

| Option | Why it is a candidate | Cost | Advantages | Drawbacks |
|---|---|---|---|---|
| Cache only phrasebook/fixed sentences; serve dynamic replies uncached (Cache-Control: no-store) | Fixed sentences already identified (voice/phrasebook.py) | free/open source | No personal audio at rest at all | Repeat dynamic sentences cost a TTS request again (free-tier quota) |
| Key dynamic audio under .cache/voice/<session_id>/ and delete the folder with the session plus a TTL purge | Same file cache, path change | free/open source | Keeps reuse within a session; erasure finds it | Needs session_id on /speak (see the previous flag) |
| Redis with TTL for dynamic audio | Redis in stack | free/open source | Expiry built in | Audio blobs bloat Redis memory; Redis is optional here |

- **Not chosen, and why:**
  - Per-session folders: workable but keeps personal audio and adds bookkeeping. Redis TTL: wastes memory on audio and disappears when Redis is off.
- **Also found as:** F-B3-011, F-A1-027, F-A5-020

#### F-B5-014: Erasure deletes consents, but retention keeps consents a year after the data

Weight 68 · Logic flaw · impact 3/5, reach 3/5, confidence 3/3 · found by B5 · merged as [R132](../arena/details-p3.md#r132)

- **Issue:** The two rules cannot both run: if erasure deletes the consent rows, the platform loses its proof that past processing was lawful (the reason for the +1 year); if it keeps them, the erasure is incomplete by its own definition. Whoever builds 3.2.4.1 picks one silently, and the nightly job (3.2.4.2) then deletes or keeps them on a different rule.
- **Cause:** SYSTEM-DESIGN.md:187-195 table: Consents 'as long as the data they cover, plus 1 year'; SYSTEM-DESIGN.md:197-198: 'One deletion request removes a founder's sessions, transcripts, documents and consents'. TASKS.md 3.2.4 copies both: Why 'remove ... consents' and How 'consents as long as the data they cover plus one year'.
- **Resolution:** build it in SYSTEM-DESIGN §5.4 (decide the rule), core.consents (3.2.1), delete-all-for-user (3.2.4.1) using **Tombstone consent record after erasure**. The only option that honours both written rules; it is a decision the owner and the 3.2.6 legal review should record before 3.2.4.1 is built.

| Option | Why it is a candidate | Cost | Advantages | Drawbacks |
|---|---|---|---|---|
| Tombstone consent record after erasure | Common DPDP/GDPR practice: keep a minimal record (purpose, given/withdrawn timestamps, erasure timestamp, pseudonymous id) with no personal content, deleted one year later | free/open source | Satisfies both rules: personal data gone, lawful-basis proof kept for the stated year | Needs a pseudonymous id that cannot be linked back; legal review (3.2.6) should confirm |
| Delete consents with everything else | Literal reading of §5.4 line 198 | free/open source | Simplest; nothing left | Loses evidence of consent; contradicts the retention table |
| Keep full consent rows for one year | Literal reading of the retention table | free/open source | Full audit trail | Keeps identifiers after an erasure request |

- **Not chosen, and why:**
  - Delete with everything: breaks the retention rule and the proof it exists for; keep full rows: breaks the erasure rule.

### 3.2.5 Protect the programme cohort endpoint

#### F-B3-001: Caller-chosen session sets defeat the 5-founder floor by differencing

Weight 78 · Logic flaw · impact 4/5, reach 3/5, confidence 3/3 · found by B3 · merged as [R057](../arena/details-p3.md#r057)

- **Issue:** One consenting founder's profile is revealed to whoever holds their session ID. That breaks the privacy promise printed in the response (programme.py:85-88). Auth on the endpoint (3.2.5.1) and a role (3.2.5.2) do not change this: any signed-in user or manager can still choose the set.
- **Cause:** routers/cohort.py:33-41 aggregates whatever session_ids the caller posts. cohort/programme.py:28-35 folds groups under 5 but answers every request. Ran programme_cohort (scratchpad b3_diff.py) on 5 'chennai' sessions plus one target. A target in salem gives {'chennai': 5, 'fewer than 5 each': 1}; a target in chennai gives {'chennai': 6}. So the target's district can be read off, and likewise its sector, stage, capital, novelty type, panel band and open gaps. The base sessions need not be real founders: POST /ideation/agent/sessions (routers/ideation.py:287-296) lets anyone create sessions with share_with_programme=true and answers they choose. Four self-made sessions plus one victim pass the floor.
- **Resolution:** build it in cohort/programme.py, routers/cohort.py; the membership model of 5.5.4 using **Server-owned programme membership**. It removes the root cause (the caller chooses the set) and is what 5.5.4 already intends. With a join code as the enrolment step it need not wait for founder accounts. Membership changes can be applied in nightly batches (5.4.4) so that a single addition cannot be isolated.

| Option | Why it is a candidate | Cost | Advantages | Drawbacks |
|---|---|---|---|---|
| Server-owned programme membership | The standard fix: the server, not the caller, decides the set. Fits SQLAlchemy/Alembic and the planned 5.5.4. | free/open source | No caller-chosen sets, so no differencing. Counts only enrolled, consenting sessions. | Needs a programme table and an enrolment step. Membership changes still allow before/after differencing unless they are applied in batches. |
| Differential privacy noise (OpenDP or IBM diffprivlib) | Mature open-source differential-privacy libraries in Python | free/open source | A formal guarantee against differencing, even with caller-chosen sets | Noisy counts on groups of 5-30 are hard for a programme manager to read. Tracking the privacy budget is new machinery. |
| Query auditing (refuse sets that overlap an earlier query by fewer than 5) | A classic statistical-database defence; small Python code plus Redis | free/open source | Keeps the current paste-IDs API | New self-made sessions get round it. Needs a stored query history. Fragile. |
| Count only sessions created through a programme join code | A small change to AgentStartIn and the session JSON (decision 0003) | free/open source | Can ship now, before 3.1. Self-made sessions only join if the attacker has the code. | A leaked code still lets sessions be planted, so it must be combined with server-owned sets. |

- **Not chosen, and why:**
  - Differential privacy: noise on groups of 5 to 30 makes the bands unreadable for the programme manager the view serves. Query auditing: self-made sessions get round it, and it needs a stored query history. Join code alone: a leaked code still allows planted sessions, so it is the enrolment step, not the defence.
- **Also found as:** F-A3-012, F-B2-006

#### F-B3-002: Session IDs given to a programme are full read, write and delete keys

Weight 78 · Missing logic · impact 4/5, reach 3/5, confidence 3/3 · found by B3 · merged as [R001](../arena/details-p3.md#r001)

- **Issue:** To be counted, a founder must hand the programme the key that lets it read their idea word for word, speak in their conversation or erase it. That is the opposite of 'never a founder's idea or name' (programme.py:3-4). 5.5.1 adds the consent checkbox now, which invites founders to share IDs before 5.5.4 replaces them. 1.1.7's delete control makes the risk worse: anyone with the ID can erase the conversation.
- **Cause:** Cohort.tsx:243-244 has the manager paste founders' session IDs. The same 32-hex ID is the only credential for GET /ideation/agent/sessions/{id} (routers/ideation.py:307-310), which returns the full transcript, known facts and roadmap through snapshot() (agents/ideation.py:226-250). It is also the only credential for DELETE (ideation.py:313-318) and POST turns (ideation.py:322-341). No endpoint checks user_id.
- **Resolution:** build it in routers/cohort.py, agents/ideation.py (AgentSession), routers/ideation.py (AgentStartIn); Cohort.tsx using **Programme join code stored in the session at start**. It removes session IDs from the programme flow entirely and works for anonymous founders today. It ties consent to a named programme instead of 'whoever holds the ID', and it is the natural enrolment step for server-owned membership (previous flag).

| Option | Why it is a candidate | Cost | Advantages | Drawbacks |
|---|---|---|---|---|
| Programme join code stored in the session at start | One field in AgentStartIn and the session JSON. The programme queries by code, never by session ID. | free/open source | The programme never sees a session ID. Works for anonymous sessions now. | Needs a lookup by code (an index or a scan) in the store |
| Derived read-only cohort token (HMAC of session ID with a server secret) | Python hmac stdlib; a common pattern for splitting capabilities | free/open source | Keeps the paste flow. The pasted value grants only aggregation. | Sets are still chosen by the caller (see the differencing flag). Rotating the key invalidates tokens. |
| Owner-bound sessions (user_id checked on every session route) | The existing get_current_user dependency; 3.1.1 plans user_id on sessions | free/open source | Fixes the bearer problem for all routes | Waits on 2.1.1 and 3.1.1. Anonymous founders stay exposed. |
| Signed capability JWT per purpose (python-jose/PyJWT) | core/security.py already issues JWTs | free/open source | Scoped, expiring tokens | More machinery than a join code for the same outcome |

- **Not chosen, and why:**
  - HMAC cohort token: sets are still chosen by the caller, so the differencing leak stays. Owner-bound sessions: right long-term, but they wait on 2.1.1 and 3.1.1 and leave anonymous founders exposed meanwhile. Capability JWT: same result as a join code with more parts to maintain.
- **Also found as:** F-A3-001, F-B5-021, F-B1-033

#### F-A3-012: Programme aggregates leak one founder by differencing two session-ID lists

Weight 78 · Logic flaw · impact 4/5, reach 3/5, confidence 3/3 · found by A3 · merged as [R057](../arena/details-p3.md#r057)

- **Issue:** The design promises that a programme sees founders only in groups of 5 or more (IDEATION §4.2, SYSTEM-DESIGN §2 class F). Anyone who can call the endpoint, including a programme manager once 3.2.5 adds auth, can single out a founder: whether they consented, their district, capital band, stage, progress and panel band. Auth (3.2.5) and membership (5.5.4) do not stop it, because a manager who can edit a batch can still difference.
- **Cause:** backend/app/cohort/programme.py:41 returns founders_sharing exactly, :82 an exact average progress, :83 an exact roadmap count, :31-34 a folded 'fewer than 5 each' count. Ran programme_cohort on 5 Salem sessions (progress 0.5), then on the same 5 plus one target: founders_sharing 5→6 (reveals the target's consent), district {'salem':5}→{'salem':5,'fewer than 5 each':1} (reveals not-Salem), average 0.5→0.57 (target progress ≈0.92, true 0.9). routers/cohort.py:33 lets the caller choose any list of up to 500 IDs.
- **Resolution:** build it in cohort/programme.py, routers/cohort.py; membership in 5.5.4 using **Fixed membership plus rounded or banded outputs (counts rounded to 5, averages as bands, no exact founders_sharing)**. It closes the leak shown in the run with small, deterministic changes that fit the existing bands-not-rankings rule, and it works now, before the analytics schema exists.

| Option | Why it is a candidate | Cost | Advantages | Drawbacks |
|---|---|---|---|---|
| Fixed membership plus rounded or banded outputs (counts rounded to 5, averages as bands, no exact founders_sharing) | Standard statistical disclosure control used by census offices; pure Python | free/open source | Simple, deterministic, matches the 'bands not rankings' rule already in the design | Coarser numbers for programmes |
| Differential privacy noise (OpenDP / diffprivlib) | OpenDP (Harvard) and IBM diffprivlib are mature open-source libraries | free/open source | Formal guarantee against differencing | Needs a privacy budget per programme and gives noisy small counts; heavy for cohorts of 20-50 |
| Query auditing: refuse a list that differs from an earlier one by fewer than 5 sessions | Classic query-set-overlap control | free/open source | Keeps exact numbers | Must store query history; can be dodged with intermediate lists |
| Precomputed nightly aggregates per batch only (analytics schema, 5.5.5) | SYSTEM-DESIGN §2 class F 'rebuilt nightly' | free/open source | No ad hoc lists at all | Waits on 5.5.5 and 5.5.4 |

- **Not chosen, and why:**
  - Differential privacy: correct but overbuilt and noisy for small batches. Query auditing: state to keep and still evadable. Nightly per-batch aggregates: the right end state, but blocked on 5.5.4/5.5.5 and still needs rounding when batch membership changes.
- **Also found as:** F-B3-001, F-B2-006

#### F-B3-004: Programme view silently drops every session idle for over 6 hours

Weight 68 · Logic flaw · impact 3/5, reach 3/5, confidence 3/3 · found by B3 · merged as [R058](../arena/details-p3.md#r058)

- **Issue:** A programme manager who checks a batch the next morning sees 'Fewer than 5 founders agreed' even when 30 agreed. 2.1.3/D4 covers session lifetime for returning founders. It does not cover the effect on aggregates, which in practice count only the last 6 hours of activity. An aggregate read should follow the retention period, not the live-session rule.
- **Cause:** routers/cohort.py:39 reads sessions with store.get. Every store's get returns None for a session idle longer than IDLE_EXPIRY, which is 6 hours (agents/store.py:29; applied at :65, :95 and :213). sessions_found then undercounts with no reason given, and programme_cohort sees fewer than 5 founders and shows nothing (programme.py:42-50).
- **Resolution:** build it in agents/store.py (a read that skips the idle filter), routers/cohort.py, the Cohort.tsx message; the D4 text using **Store read for aggregation that applies retention, not idle expiry**. It gives correct programme counts today on all three stores and depends on neither an owner decision nor the database. The response can also say how many IDs had expired.

| Option | Why it is a candidate | Cost | Advantages | Drawbacks |
|---|---|---|---|---|
| Store read for aggregation that applies retention, not idle expiry | A small method on the existing SessionStore protocol | free/open source | Correct counts now; the rule for the Redis live copy is untouched | Another store method to keep in step across three stores |
| Resolve via D4 (6 h only for the Redis copy) | Already recommended in Owner decisions | free/open source | One rule fixes it for founders and programmes | The memory store (no database) still expires at 6 h. Waits on the owner. |
| Nightly analytics snapshot (5.5.5) | The planned analytics schema | free/open source | Fast, stable aggregates | Waits on 2.1.1 and 2.1.4 |
| Report expired versus unknown IDs in the response | A response field only | free/open source | The manager sees why counts are low | Does not fix the count |

- **Not chosen, and why:**
  - D4 alone: waits on the owner and leaves the memory store at 6 h. Nightly snapshot: blocked on 2.1.1 and 2.1.4. Reporting only: explains the wrong number instead of fixing it.
- **Also found as:** F-B2-005, F-A2-003

#### F-A2-003: Cohort view uses the founder-resume read path and drops sessions idle over 6 hours

Weight 62 · Logic flaw · impact 3/5, reach 2/5, confidence 3/3 · found by A2 · merged as [R058](../arena/details-p3.md#r058)

- **Issue:** A programme manager's aggregates silently count only founders active in the last 6 hours, so 'sessions_found' and the blockers shown are wrong for any batch that is not mid-conversation. Even after D4 (90 days in PostgreSQL), the per-ID loop costs 500 round trips and floods Redis with copies nobody will resume. Task 2.1.3 frames session lifetime only as 'founders can return'; it does not cover the cohort read path.
- **Cause:** backend/app/routers/cohort.py:39-40 loads each programme session with store.get(), one at a time. store.py:48-49, 65, 95 and 213 return None for any session idle more than 6 hours. Probe: a MemoryStore session saved with updated_at 7 h ago returns None from get(). Through CachedStore, every cohort read also copies the session into Redis for 6 hours (store.py:214-216), up to 500 per call, one after another.
- **Resolution:** build it in backend/app/agents/store.py (a get_many method that skips the idle-expiry rule and the Redis fill), backend/app/routers/cohort.py using **Store.get_many with one SELECT ... WHERE session_id IN (...)**. One small method fixes both the wrong counts and the cost, and gives 5.5.5 a clean read interface to replace later.

| Option | Why it is a candidate | Cost | Advantages | Drawbacks |
|---|---|---|---|---|
| Store.get_many with one SELECT ... WHERE session_id IN (...) | SQLAlchemy select with in_(), a primary-key lookup on agent_sessions | free/open source | One query; ignores the live-session idle rule; no Redis pollution; cohort_consent is still checked in code | MemoryStore needs a matching method; retention (3.2.4) becomes the only age limit |
| asyncio.gather over store.get | Standard library | free/open source | Trivial | Keeps the 6-hour drop and the Redis flood; up to 500 concurrent connections against the pool (2.4.3) |
| Redis MGET on sess:* keys | Native Redis multi-get | free/open source | Fast for live sessions | Sees only live copies, which is the bug itself; Redis is optional |
| Analytics tables rebuilt nightly (5.5.5) | Already planned in TASKS 5.5.5 | free/open source | The right long-term shape for cohort queries | Waits on other work and leaves the current endpoint wrong until then |

- **Not chosen, and why:**
  - asyncio.gather: keeps the wrong 6-hour filter and strains the pool
  - Redis MGET: sees only live sessions; nightly analytics tables: correct later, but today's endpoint stays wrong.
- **Also found as:** F-B2-005, F-B3-004

#### F-B3-003: 3.2.5.1 is marked 'now' but its auth needs the PostgreSQL users table

Weight 52 · Logic flaw · impact 2/5, reach 2/5, confidence 3/3 · found by B3 · merged as [R195](../arena/details-p3.md#r195)

- **Issue:** Doing 3.2.5.1 as written makes the Cohort page unusable on any machine without a working database, which is every machine today. The role task also lists no migration step.
- **Cause:** api/deps.py:19-30 get_current_user loads User through the SQLAlchemy session (db/session.py:24-27), and routers/auth.py:24 login needs it too. User (models/user.py:18-37) has no role column for 3.2.5.2. TASKS.md lists 2.1.1 (database) as waiting on the owner, while 3.2.5 says 'When: now for the auth check'.
- **Resolution:** build it in docs/specs/TASKS.md 3.2.5 (When, subtasks); api/deps.py; models/user.py plus a migration using **Interim operator key from settings, compared with secrets.compare_digest**. It closes the endpoint immediately without the database, keeps the feature, and fits the free and offline rule. 3.2.5.2 then replaces it with a role column once 2.1.1 and 3.1 land; add that migration as a subtask.

| Option | Why it is a candidate | Cost | Advantages | Drawbacks |
|---|---|---|---|---|
| Mark 3.2.5.1 waiting on 2.1.1 and add a role migration subtask | A plan-only change, consistent with how P3 is gated | free/open source | An honest order; no interim code | The endpoint stays open until the database lands |
| Interim operator key from settings, compared with secrets.compare_digest | pydantic-settings already loads backend/.env; stdlib secrets | free/open source | Works offline today with no database and closes the open endpoint now | One shared key, replaced by roles later |
| Run PostgreSQL through the existing docker-compose db service | backend/docker-compose.yml already defines it | free/open source | The real auth path | This is the owner action 2.1.1 already waits on |
| Disable /cohort/programme until auth exists | A one-line router change | free/open source | No exposure | Removes a built feature |

- **Not chosen, and why:**
  - Re-marking as waiting: leaves the endpoint open for an unknown time. Docker PostgreSQL: it is itself the blocked owner action. Disabling: throws away a built, tested view.

#### F-A3-019: Programme endpoint loads up to 500 full session documents one at a time

Weight 45 · Optimisation · impact 2/5, reach 2/5, confidence 2/3 · found by A3 · merged as [R210](../arena/details-p3.md#r210)

- **Issue:** Large programmes make one request run 500 round trips and parse 500 transcripts, holding a worker and the pool (2.4.3) for seconds, and every non-consenting founder's full document is read for nothing.
- **Cause:** backend/app/routers/cohort.py:40 awaits store.get(sid) sequentially for each of up to 500 IDs (:33); each SqlStore.get (agents/store.py:86-95) opens a new DB session and parses the whole JSON document, though programme_cohort reads only a few slots and cohort_consent.
- **Resolution:** build it in agents/store.py (get_many), routers/cohort.py using **store.get_many: one SELECT ... WHERE session_id = ANY(:ids) (and Redis MGET), filtering consent before parsing**. One query, bounded memory, and non-consenting documents are never loaded.

| Option | Why it is a candidate | Cost | Advantages | Drawbacks |
|---|---|---|---|---|
| store.get_many: one SELECT ... WHERE session_id = ANY(:ids) (and Redis MGET), filtering consent before parsing | SQLAlchemy in_() and redis-py mget | free/open source | One round trip; skips non-consenting documents | New store method on three backends |
| asyncio.gather over store.get | stdlib | free/open source | Two-line change | 500 concurrent DB sessions exhaust the pool |
| Project the needed fields with JSONB operators in SQL | PostgreSQL JSONB | free/open source | Minimal data transfer | Couples SQL to the document shape before the 5.5.5 split |

- **Not chosen, and why:**
  - gather: overwhelms the connection pool. JSONB projection: ties queries to a document shape that 5.5.5 will change.

