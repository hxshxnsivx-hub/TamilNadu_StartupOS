# Arena flags: P3 Founder records details

Back to the [weighted table](../ARENA-FLAGS.md).

### R001

**Session ID is a bearer credential: no ownership check on resume/turn/delete, handed to programmes** · weight 100 · Missing logic · impact 5/5, reach 5/5, confidence 3/3 · flags F-A3-001, F-B5-021, F-B3-002, F-B1-033

- **Evidence (A3):** backend/app/routers/ideation.py:307-345: agent_resume, agent_delete, agent_turn and agent_turn_stream take only session_id, with no Depends(get_current_user) and no comparison with AgentSessionRow.user_id (models/agent_session.py:24). TASKS 3.1.1 'How' only says 'attach user_id to the session'.
- **Evidence (B5):** backend/app/routers/ideation.py:270-318 — _load, agent_turn, agent_turn_stream, the snapshot GET and DELETE take only the session id path parameter (_SESSION_ID, line 265); none depends on get_current_user (api/deps.py:18-30). TASKS 3.1.1 How: 'attach user_id to the session at sign-up or sign-in', nothing about access afterwards.
- **Evidence (B3):** Cohort.tsx:243-244 has the manager paste founders' session IDs. The same 32-hex ID is the only credential for GET /ideation/agent/sessions/{id} (routers/ideation.py:307-310), which returns the full transcript, known facts and roadmap through snapshot() (agents/ideation.py:226-250). It is also the only credential for DELETE (ideation.py:313-318) and POST turns (ideation.py:322-341). No endpoint checks user_id.
- **Evidence (B1):** routers/ideation.py:307-320: GET returns the full transcript, evidence and roadmap; DELETE erases the session; POST turns writes; GET notices streams results. All are keyed only by the 32-hex session id, with no user binding (new_session user_id 'anon', agents/ideation.py:203). routers/cohort.py:33-41 takes up to 500 pasted session ids for programme aggregates (TASKS 5.5.4: 'instead of pasted session IDs'). app/main.py:64-71 adds no CORS middleware and the API sets no cookies, so the 'cookie and CORS settings' check in 5.1.6.2 has nothing to test.

- **Why it matters:** Once a session belongs to a signed-in founder (class D, personal), its transcript, facts and roadmap can still be read, continued or deleted by anyone who has the 32-hex ID (shared links, browser history, a shared phone's localStorage key vanigam_talk_session). Attaching user_id without enforcing it gives no protection, and DPDP purpose-limitation fails.
- **Where to build it:** api/deps.py (an optional-user dependency), routers/ideation.py (_load gains an owner check), agents/store.py; tests in backend/tests

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Optional-user FastAPI dependency plus an owner check in _load | Uses existing OAuth2PasswordBearer(auto_error=False) in api/deps.py; standard FastAPI pattern | free/open source | Tiny change; anonymous sessions keep working (user_id 'anon'); a claimed session returns 404 to everyone except its owner | Session ID still acts as the anonymous bearer secret until claimed |
| Signed per-session capability token (itsdangerous / HMAC) returned at start | itsdangerous is the Flask/Starlette standard signer; no new infra | free/open source | Protects anonymous sessions too, not only claimed ones | Extra token to store and send from Talk.tsx; more frontend work |
| PostgreSQL row-level security on agent_sessions | Built into PostgreSQL | free/open source | Enforced even if a route forgets the check | Needs per-request SET of a role/GUC through SQLAlchemy; does not cover the Redis live copy |
| Casbin / Oso authorisation library | Mature policy engines with Python bindings | free/open source | Central policy, ready for the programme-manager role (3.2.5.2) | Heavy for a single owner rule |

- **Recommended:** Optional-user FastAPI dependency plus an owner check in _load. It closes the hole for every claimed session with a few lines in the existing deps module and a test per endpoint, and leaves the anonymous start untouched.
- **Ruled out:** Signed capability token: right idea for anonymous sessions but more work than the district needs now; can follow later. Row-level security: does not cover the Redis copy and adds per-request session state. Casbin/Oso: a policy engine for one rule.

### R002

**JWT secret defaults to 'change-me' with no startup guard** · weight 100 · Logic flaw · impact 5/5, reach 5/5, confidence 3/3 · flags F-A3-003, F-A5-021

- **Evidence (A3):** backend/app/core/config.py:21 secret_key='change-me'; core/security.py:45,65 sign and verify with it; main.py:41 starts in any env. Ran with APP_ENV=production and no SECRET_KEY: settings printed ('production', 'change-me') and decode_token accepted a token I signed with 'change-me' for an arbitrary sub.
- **Evidence (A5):** backend/app/core/config.py:21 secret_key = 'change-me'; core/security.py:45,65 sign and verify JWTs with it; config.py:140 is_production is defined but used nowhere (grep). docs/runbooks/rotate-key.md lists ANTHROPIC, OPENALEX, PATENTSVIEW, GITHUB and the database password, not SECRET_KEY; 5.3.2.2 adds Gemini, EPO and Sarvam only.

- **Why it matters:** Once sessions and profiles are tied to users (3.1), anyone who knows the public default can mint an access token for any user_id and read their records. Nothing in TASKS mentions it.
- **Where to build it:** core/config.py (validator), main.py lifespan

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| pydantic model_validator refusing the default or a short key when app_env != development | pydantic-settings already loads config | free/open source | Fails fast at boot; one test | Developers must set a key for staging |
| Auto-generate a random key into a local file on first run | secrets.token_urlsafe | free/open source | Zero setup | Multiple workers get different keys unless the file is shared; all tokens die on file loss |
| Asymmetric RS256/EdDSA keys | python-jose supports them | free/open source | Verification key can be shared safely | Key management overhead without a second verifier service |

- **Recommended:** pydantic model_validator refusing the default or a short key when app_env != development. Smallest change that makes the insecure default impossible outside development.
- **Ruled out:** Auto-generated key: breaks across workers and restarts. Asymmetric keys: no second party verifies tokens, so it adds work without benefit.

### R021

**Caste collected, sent by default and used in ranking without a consent gate** · weight 84 · Logic flaw · impact 4/5, reach 4/5, confidence 3/3 · flags F-B3-005, F-A3-015

- **Evidence (B3):** Consent.tsx:41-44 promises caste is 'Checked only against reserved-category eligibility rules ... never used for ranking anything else'. But schemes/ranking.py:29-30 adds an 'sc_st' axis from caste_category, and :67-73 and :96 feed it into the likelihood half of the composite sort key, so caste changes the order of eligible schemes. Schemes.tsx:46-49 pre-fills caste_category: 'sc' (and gender 'female') as the default form state, and :75 sends it to /schemes/recommend with no check of journey.consent.caste. grep shows no backend code reads consent at all. 1.4.3 plans to project session slots onto this same scheme profile, which would bypass consent the same way.
- **Evidence (A3):** frontend/src/pages/Schemes.tsx:46-50 initial state gender 'female', caste_category 'sc', and :75 sends caste_category to /schemes/recommend; schemes/ranking.py:27-30 adds women and sc_st axes from them. Profile.tsx:183 asks for caste without reading journey.consent.caste (Consent.tsx:41-44 defines that purpose). Backend elicitation already treats caste as SENSITIVE_DEFERRED (elicitation/slots.py:365-367).

- **Why it matters:** A founder who never consented, or declined caste use, still has a caste value (by default 'sc') driving ranking. The consent record 3.2.1 builds would then misdescribe what the system does, the worst outcome for a DPDP record. Seeing a default of 'sc' is also misleading and arguably offensive.
- **Where to build it:** schemes/ranking.py (_founder_axes), routers/schemes.py (consent gate on input), Schemes.tsx defaults, Consent.tsx wording; the 1.4.3 projection

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Server-side purpose gate: strip protected fields unless consent for that purpose is present | A FastAPI dependency or a Pydantic validator on RecommendIn; fits the existing stack | free/open source | One enforced rule for every caller (Schemes form, 1.4.3 projection, future screens); the consent record becomes true | Until 3.2.1's table exists, an anonymous caller must send its consent flags with the request |
| Change the consent wording to say caste also affects ranking | Copy change in Consent.tsx | free/open source | Trivial; keeps the ranking | Still sends caste without consent; widens the purpose instead of honouring it |
| Policy engine (Open Policy Agent / Oso) for purpose checks | Mature open-source policy engines | free/open source | Declarative rules, auditable | A new runtime for a handful of rules; heavy for a single-owner project |
| Client-side only: Schemes.tsx omits caste unless journey.consent.caste | A few lines in React | free/open source | Fast | Not enforced: any other client, and the 1.4.3 projection, still bypass it |

- **Recommended:** Server-side purpose gate: strip protected fields unless consent for that purpose is present. Consent only means something if the server enforces it, and 1.4.3 will add a second caller that never passes through the browser. Also remove the 'sc'/'female' defaults and keep caste out of the likelihood score unless the founder has consented to it.
- **Ruled out:** Rewording: legalises current behaviour instead of honouring the narrower purpose and still sends unconsented data. Policy engine: an extra service for a few rules, against the simple single-owner stack. Client-only: unenforced, and the 1.4.3 projection bypasses it.

### R024

**Founder table forces full basic tier NOT NULL; partial profiles can't sync** · weight 84 · Logic flaw · impact 4/5, reach 4/5, confidence 3/3 · flags F-A3-007, F-B2-013

- **Evidence (A3):** backend/app/models/founder.py:25-33 email, phone (unique), date_of_birth, gender, state, district, city are nullable=False; frontend Founder type (completeness.ts:5-18) has them all optional. users.email (models/user.py:22) and founders.email (founder.py:24) are two unique copies of the same fact. TASKS 3.1.2 says 'CRUD with auth on the existing tables'.
- **Evidence (B2):** backend/app/models/founder.py: name, email (unique), phone (unique), date_of_birth, gender, state, district and city are all nullable=False, with CHECK constraints on email and phone. frontend/src/completeness.ts:5-19: every Founder field is optional, and frontend/src/profileStore.ts:6 starts from an empty founder {}. backend/app/models/user.py also holds email, so Founder.email duplicates User.email.

- **Why it matters:** 3.1.2.2 ('the browser profile syncs to the server') fails with IntegrityError for every founder below 40% completeness, which is exactly the founders who most need their partial answers kept across devices. Two email columns can drift: a founder who changes the sign-in email keeps the old one on the profile, and the unique constraints then block other people.
- **Where to build it:** backend/app/models/founder.py and a migration (relax to nullable, enforce completeness in the scorer not the schema); routers /profiles; drop or derive Founder.email from users

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Nullable profile columns; completeness enforced by the scorer, not by NOT NULL | Follows SYSTEM-DESIGN 5.2 'add as nullable, fill in, then constrain'; the scorer already exists (services/completeness.py) | free/open source | Partial drafts sync; one place decides what 'basic' means | Fewer database guarantees; queries must handle NULLs |
| A separate profile_drafts JSONB table until the basic tier is complete | Mirrors the session-document pattern (decision 0003) | free/open source | Keeps the strict Founder table as is | Two shapes of the same profile; a promotion step to maintain |
| Keep the browser as the store until 40%, then create the Founder row | No schema change | free/open source | Trivial | Defeats 'memory across devices' for exactly the incomplete profiles |

- **Recommended:** Nullable profile columns; completeness enforced by the scorer, not by NOT NULL. Lets every draft sync with one shape, keeps the tier rule in the scorer the frontend already mirrors, and is a cheap migration while no real data exists. Take email from users and drop the duplicate column.
- **Ruled out:** Draft table: a second shape plus a promotion step for the same data. Browser until 40%: loses the partial profiles the task exists to keep.

### R057

**Differencing two caller-chosen session-ID lists defeats the 5-founder floor** · weight 78 · Logic flaw · impact 4/5, reach 3/5, confidence 3/3 · flags F-B3-001, F-A3-012, F-B2-006

- **Evidence (B3):** routers/cohort.py:33-41 aggregates whatever session_ids the caller posts. cohort/programme.py:28-35 folds groups under 5 but answers every request. Ran programme_cohort (scratchpad b3_diff.py) on 5 'chennai' sessions plus one target. A target in salem gives {'chennai': 5, 'fewer than 5 each': 1}; a target in chennai gives {'chennai': 6}. So the target's district can be read off, and likewise its sector, stage, capital, novelty type, panel band and open gaps. The base sessions need not be real founders: POST /ideation/agent/sessions (routers/ideation.py:287-296) lets anyone create sessions with share_with_programme=true and answers they choose. Four self-made sessions plus one victim pass the floor.
- **Evidence (A3):** backend/app/cohort/programme.py:41 returns founders_sharing exactly, :82 an exact average progress, :83 an exact roadmap count, :31-34 a folded 'fewer than 5 each' count. Ran programme_cohort on 5 Salem sessions (progress 0.5), then on the same 5 plus one target: founders_sharing 5→6 (reveals the target's consent), district {'salem':5}→{'salem':5,'fewer than 5 each':1} (reveals not-Salem), average 0.5→0.57 (target progress ≈0.92, true 0.9). routers/cohort.py:33 lets the caller choose any list of up to 500 IDs.
- **Evidence (B2):** backend/app/cohort/programme.py:28-35 shows exact counts for any group of 5 or more and folds only smaller groups; each dimension is computed independently (:62-82). Probe (b2probe2.py): 5 Chennai founders give {'chennai': 5}; adding one target ID gives {'chennai': 5, 'fewer than 5 each': 1}, so the target is not in Chennai. Symmetrically, with 5 Salem founders the target in Salem shows as salem: 6. backend/app/routers/cohort.py:36 accepts any 1-500 IDs from the caller.

- **Why it matters:** One consenting founder's profile is revealed to whoever holds their session ID. That breaks the privacy promise printed in the response (programme.py:85-88). Auth on the endpoint (3.2.5.1) and a role (3.2.5.2) do not change this: any signed-in user or manager can still choose the set.
- **Where to build it:** cohort/programme.py, routers/cohort.py; the membership model of 5.5.4

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Server-owned programme membership | The standard fix: the server, not the caller, decides the set. Fits SQLAlchemy/Alembic and the planned 5.5.4. | free/open source | No caller-chosen sets, so no differencing. Counts only enrolled, consenting sessions. | Needs a programme table and an enrolment step. Membership changes still allow before/after differencing unless they are applied in batches. |
| Differential privacy noise (OpenDP or IBM diffprivlib) | Mature open-source differential-privacy libraries in Python | free/open source | A formal guarantee against differencing, even with caller-chosen sets | Noisy counts on groups of 5-30 are hard for a programme manager to read. Tracking the privacy budget is new machinery. |
| Query auditing (refuse sets that overlap an earlier query by fewer than 5) | A classic statistical-database defence; small Python code plus Redis | free/open source | Keeps the current paste-IDs API | New self-made sessions get round it. Needs a stored query history. Fragile. |
| Count only sessions created through a programme join code | A small change to AgentStartIn and the session JSON (decision 0003) | free/open source | Can ship now, before 3.1. Self-made sessions only join if the attacker has the code. | A leaked code still lets sessions be planted, so it must be combined with server-owned sets. |

- **Recommended:** Server-owned programme membership. It removes the root cause (the caller chooses the set) and is what 5.5.4 already intends. With a join code as the enrolment step it need not wait for founder accounts. Membership changes can be applied in nightly batches (5.4.4) so that a single addition cannot be isolated.
- **Ruled out:** Differential privacy: noise on groups of 5 to 30 makes the bands unreadable for the programme manager the view serves. Query auditing: self-made sessions get round it, and it needs a stored query history. Join code alone: a leaked code still allows planted sessions, so it is the enrolment step, not the defence.

### R060

**Sign-out leaves founder's browser data (profile, consent, journey, session) for next user** · weight 78 · Missing logic · impact 4/5, reach 3/5, confidence 3/3 · flags F-A3-005, F-B2-018

- **Evidence (A3):** frontend/src/auth.tsx:53-56 logout only calls setTokens(null). Personal data stays in localStorage: vanigam_profile (profileStore.ts:3, includes phone, date_of_birth, caste_category per completeness.ts:5-18), vanigam_journey (consent flags), vanigam_pipeline, vanigam_suppliers, vanigam_talk_session.
- **Evidence (B2):** frontend/src/auth.tsx:53-56: logout() only calls setTokens(null) and setUser(null). The keys vanigam_profile, vanigam_journey, vanigam_pipeline, vanigam_suppliers and vanigam_talk_session (profileStore.ts:3, journeyStore.ts:21, Pipeline.tsx:38, Suppliers.tsx:39, Talk.tsx:29) are not scoped per user and survive. Agent sessions are readable by ID alone (routers/ideation.py:299-302, no auth).

- **Why it matters:** Shared devices (college labs, browsing centres, a family phone) are common for first-time founders. After sign-out, the next person sees the previous founder's profile, caste category, investor pipeline and supplier quotes, and Talk resumes the previous founder's conversation. Once 3.1.1/3.1.2/3.1.3 sync browser state on sign-in, the next user's sign-in would upload the previous founder's data into the new account, a DPDP breach the plan does not mention.
- **Where to build it:** frontend/src/auth.tsx (clear or namespace founder keys on logout and on account switch); the 3.1.3 sync (upload anonymous browser state only with an explicit 'this is mine' confirmation)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Namespace keys by user ID, clear the anonymous namespace on logout, and confirm before claiming it | Standard multi-user client storage practice | free/open source | Fixes both leakage and wrong-account sync; anonymous drafts can still be claimed knowingly | Touches every storage call site |
| Clear all vanigam_* keys on logout | A simple loop over localStorage | free/open source | Trivial, closes the leak | A founder who has not synced yet loses their drafts on sign-out |
| sessionStorage for sensitive fields (caste, finance, session ID) | A browser API; cleared when the tab closes | free/open source | Limits exposure on shared machines | Founders lose state across tabs; does not fix the sync claim |

- **Recommended:** Namespace keys by user ID, clear the anonymous namespace on logout, and confirm before claiming it. It is the only option that handles both the shared-device leak and the sync-into-the-wrong-account case that 3.1.1-3.1.3 create, without discarding a founder's unsynced work.
- **Ruled out:** Clear all on logout: loses unsynced drafts, and an anonymous user's data is still claimed blindly at the next sign-in. sessionStorage: partial, and it breaks multi-tab use.

### R062

**Erasure outside the app leaves the Redis session copy readable** · weight 78 · Missing logic · impact 4/5, reach 3/5, confidence 3/3 · flags F-B5-016

- **Evidence (B5):** Ran scratchpad/arena/b5/erase.py: CachedStore(MemoryStore, fake Redis), create a session, delete the row through the inner store as a nightly/erasure process would -> 'session still readable through the app after erasure: True'. store.py:206-213 serves sess:{id} from Redis before the database, TTL IDLE_EXPIRY 6 h (store.py:198). Only the app's DELETE route drops Redis and calls board.forget (routers/ideation.py:316-318); Redis has no user -> session index.

- **Why it matters:** For up to six hours after a retention delete or erasure request, the conversation (transcript and facts) is still returned to anyone holding the session id, and the job board keeps its evidence and panel results in memory indefinitely (B5-04 flag 2). An erasure that is not complete in all copies fails the DPDP request the task exists for.
- **Where to build it:** the 3.2.4 erasure service and nightly step: collect session ids from PostgreSQL, then drop sess:{id} in Redis and tell the app process to forget them

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Delete through the store plus a Redis 'erased' channel the app listens to | redis-py pub/sub already available; the store's CachedStore.delete drops the copy; the app subscribes and calls board.forget | free/open source | Clears Redis and in-memory results from any process | Needs the app running to receive the message; without Redis, falls back to an admin endpoint |
| Run erasure and retention inside the app (admin endpoint or in-process task) | FastAPI route or lifespan task calling store.delete and board.forget, the same path as the founder's delete | free/open source | One code path for all deletes; reaches memory and Redis | Nightly scheduler must call the app; per-worker memory still needs fan-out with several workers |
| Tombstone key checked on read | Write erased:{id} to Redis/DB; CachedStore.get checks it | free/open source | Robust to stale copies | Extra read per turn; tombstones need their own retention |

- **Recommended:** Run erasure and retention inside the app (admin endpoint or in-process task). Today the app is one process (decision 0010), so reusing the founder delete path clears database, Redis and job board together; pub/sub can be added when several workers exist.
- **Ruled out:** Pub/sub first: depends on Redis, which is optional; tombstones: a per-turn read cost to patch a path that should not exist.

### R069

**Self-typed fields and a 'demo' checkbox would be stored as verified, tier 100** · weight 78 · Logic flaw · impact 4/5, reach 3/5, confidence 3/3 · flags F-B2-014

- **Evidence (B2):** backend/app/services/completeness.py:72 sets verified = list(basic_present), and :83/:86 add the education and startup fields that are present. The 80 tier is labelled 'verified' (:54), and 100 'investment_ready' needs only has_verified_documents (:79). frontend/src/pages/Profile.tsx:256-259 sets docsVerified from a checkbox labelled 'Documents verified (demo)' (i18n.ts:52). The ProfileCompleteness table stores verified_fields (models/profile.py).

- **Why it matters:** Once 3.1.2 persists the score and verified_fields, typed-in data is recorded as verified, and any founder can tick the demo box to become 'investment_ready'. 3.1.2.3 re-runs scheme eligibility on that score, and funding readiness reads the same profile, so founders (and programme views) would see unearned readiness. No document verification exists, and D11 keeps documents out of scope.
- **Where to build it:** backend/app/services/completeness.py (verified_fields only for server-verified facts; rename the tiers); routers /profiles (ignore client docsVerified); frontend Profile.tsx (remove or clearly isolate the demo toggle)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Server ignores client verification flags; verified_fields empty until a real check exists; tiers renamed (basic, standard, complete) | Server-authoritative pattern; D11 says no documents yet | free/open source | No false claims; small change | The 100 tier is unreachable for now |
| Verify the free fields the platform can check (GSTIN checksum, CIN format, pincode to district) | Public format rules; CHECK constraints already exist for CIN and GSTIN | free/open source | Some honest 'verified' marks offline | A format check is not identity verification; must be labelled as such |
| Keep the demo toggle but store it as demo_only and exclude it from eligibility | Labelled-demo approach (like D9) | free/open source | Keeps the demo screen working | Demo data in real records, against 'no invented data' |

- **Recommended:** Server ignores client verification flags; verified_fields empty until a real check exists; tiers renamed (basic, standard, complete). The only option that never tells a founder or a programme something unverified is verified, and it matches D11 and the no-invented-data rule.
- **Ruled out:** Format checks: worth adding later, but they must not be called verification. Demo flag: keeps invented data in real records.

### R079

**Consent page purposes don't match the design list and promise dropped features** · weight 74 · Missing structure · impact 3/5, reach 4/5, confidence 3/3 · flags F-B3-006, F-A3-013, F-B2-020

- **Evidence (B3):** Consent.tsx:33-65 offers core, caste, financial, idea_ip and digest. 3.2.1 lists conversation, voice, quality review, cohort, caste, financial and idea IP. Cohort consent lives elsewhere, as share_with_programme on session start (routers/ideation.py:256, agents/ideation.py:205-210), and 5.5.1 adds a second checkbox for it on the Talk page. 'digest' (Consent.tsx:60-63, 'in-app first, then email, then SMS') and 'idea_ip' ('partner match cards', :53-57) describe features listed under Dropped (notifications; matching among platform founders). journeyStore.ts:48-49 keeps consent as a free-form Record<string, boolean>.
- **Evidence (A3):** frontend/src/pages/Consent.tsx:33-65 lists core, caste, financial, idea_ip, digest. SYSTEM-DESIGN §5.4 and TASKS 3.2.1 name conversation, voice, quality review, cohort, caste, financial, idea IP. Voice, quality review and cohort are missing; 'digest' promises 'email, then SMS' although notifications are in Dropped. journeyStore.ts:49 stores only booleans: no time, no notice text or version.
- **Evidence (B2):** frontend/src/pages/Consent.tsx:33-65 PURPOSES = core, caste, financial, idea_ip ('masked in partner match cards'), digest ('in-app, then email, then SMS'). The choices are stored in journeyStore.consent (Consent.tsx:85-91). TASKS 3.2.1 lists conversation, voice, quality review, cohort, caste, financial and idea IP. TASKS Dropped removes notifications, digests and SMS, and offering-side B2B profiles. The agent session's cohort_consent is a separate flag (agents/ideation.py:130) that the Talk page never sets (voice/agentClient.ts:103).

- **Why it matters:** Founders are asked to agree to features that do not exist and are never asked about ones that do (voice, quality review). The same purpose (cohort) is asked in two places and can disagree. When 3.2.1 builds its table, nothing defines the purpose IDs both sides must use.
- **Where to build it:** A purpose registry beside the consent model (backend), exported to the frontend; Consent.tsx; Talk.tsx (5.5.1); journeyStore.ts

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| One purpose registry as a Python Enum, published through OpenAPI and used by the generated TS types | FastAPI already emits OpenAPI; openapi-typescript is a mature free generator | free/open source | One list for the backend table, the screens and the gate; renames break the build | Adds a type-generation step to the frontend build |
| A purposes JSON data file read by both sides | Matches the repo's pattern of reference data in Git | free/open source | Wording and IDs reviewed by commit; easy to translate | No compile-time check on the frontend |
| PostgreSQL enum type for purpose | Native PostgreSQL feature with an Alembic migration | free/open source | Database refuses unknown purposes | Waits on 2.1.1; does not reach the frontend; enum changes need migrations |
| Keep free-form strings and document them | Status quo | free/open source | No work | Drift continues, as already seen |

- **Recommended:** One purpose registry as a Python Enum, published through OpenAPI and used by the generated TS types. It gives the 3.2.1 table, the server-side gate (previous flag), Consent.tsx and the Talk checkbox one set of IDs that cannot drift. It also forces the drop of 'digest' and 'idea_ip' and the addition of voice and quality review.
- **Ruled out:** JSON file: no build-time check, so the drift that already happened can recur. PostgreSQL enum: blocked on 2.1.1 and invisible to the frontend. Free-form strings: the cause of the current mismatch.

### R096

**No 'my conversations' list: a founder cannot find past sessions on another device** · weight 74 · Missing function · impact 3/5, reach 4/5, confidence 3/3 · flags F-A3-009

- **Evidence (A3):** routers/ideation.py:288-345 offers create, get-by-id, delete-by-id and turns only; agent_sessions has an index on user_id (0004_agent_sessions.py:41) that nothing queries. Talk.tsx:44-52 remembers a single session ID per device. SYSTEM-DESIGN §3.2 founder memory includes 'past ideas and decisions' and 'delete one session or all of them'.

- **Why it matters:** The purpose of linking (resume on any device, keep past ideas, delete one of several) fails: on a new phone the founder has no session ID and no way to get it, and 1.1.7's delete control can only reach the current device's session.
- **Where to build it:** routers/ideation.py (GET /ideation/agent/sessions for the current user), agents/store.py (list_for_user), Talk.tsx

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| GET /ideation/agent/sessions returning id, title, idea_version, last_active for the current user | Uses the existing user_id index and store; FastAPI | free/open source | Small; reads only columns, not the JSON document | Needs a short title derived without exposing idea text in logs |
| Store session IDs in the founder profile record | 3.1.2 profile endpoints | free/open source | No new query | Two sources of truth that drift on delete or retention |
| Keyset-paginated list endpoint with filters | Standard API pattern | free/open source | Scales | Overkill: founders have a handful of sessions |

- **Recommended:** GET /ideation/agent/sessions returning id, title, idea_version, last_active for the current user. Delivers cross-device resume and per-session deletion with one indexed query.
- **Ruled out:** IDs in the profile: duplicates state that the retention job would have to keep in sync. Keyset pagination: unnecessary at this size.

### R102

**Refresh token is never used or revocable: 30-min logouts and no server-side sign-out** · weight 74 · Missing logic · impact 3/5, reach 4/5, confidence 3/3 · flags F-A3-004

- **Evidence (A3):** frontend/src/api.ts:45-66 sends the access token but never calls /auth/refresh on 401 (grep: no 'refresh' call in frontend/src); auth.tsx:38 drops tokens on any /me failure. core/security.py:43 puts a jti in every token but nothing stores or checks it; routers/auth.py has no logout; refresh_token_pair (services/auth_service.py:56-61) reissues without invalidating the old refresh token.

- **Why it matters:** Once the profile syncs to the server (3.1.2.2), a founder is silently signed out every 30 minutes (access_token_expire_minutes, config.py:22) mid-edit. A stolen refresh token stays valid 14 days with no way to revoke it, and 'sign out' on a shared phone does not end the session server-side.
- **Where to build it:** frontend/src/api.ts, auth.tsx; services/auth_service.py, routers/auth.py; Redis (already in stack)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Rotating refresh tokens with a jti denylist in Redis, plus a 401-retry wrapper in api.ts | Redis already configured (core/redis.py); jti already minted | free/open source | Revocation, logout and reuse detection with existing parts | Needs Redis or a fallback table when Redis is off |
| refresh_tokens table in PostgreSQL (hashed jti, revoked_at) | SQLAlchemy/Alembic already used | free/open source | Durable, works without Redis, fits erasure (delete by user) | One DB write per refresh |
| fastapi-users library | Popular FastAPI auth package | free/open source | Refresh, reset, verify flows prebuilt | Replaces the existing User model and services; large migration |
| httpOnly cookie for the refresh token | Standard web practice | free/open source | Refresh token out of localStorage (XSS) | Needs CSRF handling; complementary rather than a full fix |

- **Recommended:** refresh_tokens table in PostgreSQL (hashed jti, revoked_at). Works with or without Redis, gives logout and rotation, and is deleted with the user under 3.2.4.1; pair it with a 401-retry in api.ts.
- **Ruled out:** Redis denylist: Redis is optional in this app, so revocation would silently vanish when it is off. fastapi-users: rewrites working auth. httpOnly cookie: useful hardening but does not provide revocation by itself.

### R117

**Claim rule unspecified: a shared phone hands founder A's session to founder B** · weight 71 · Missing logic · impact 4/5, reach 3/5, confidence 2/3 · flags F-A3-002

- **Evidence (A3):** frontend/src/pages/Talk.tsx:29,44-52 keeps one device-wide key vanigam_talk_session; frontend/src/auth.tsx:53-56 logout clears only tokens. TASKS 3.1.1 says 'attach user_id at sign-up or sign-in' with no condition on the session's current owner.

- **Why it matters:** Shared family phones are common for the target founders. If the claim runs on every sign-in for whatever session ID is in localStorage, the next person to sign in on that phone silently takes the previous founder's idea and transcript; a claimed session could also be re-claimed and overwritten.
- **Where to build it:** routers/auth.py or a new POST /ideation/agent/sessions/{id}/claim, agents/store.py, Talk.tsx, auth.tsx

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Explicit claim endpoint: only user_id='anon' sessions, founder confirms in the UI | Plain FastAPI route plus a conditional UPDATE ... WHERE user_id='anon' | free/open source | Atomic, never overwrites an owner; the founder sees 'Keep this conversation in your account?' | One extra tap |
| Auto-claim on sign-in with a freshness window (session created in the last N minutes on this tab) | sessionStorage instead of localStorage for the anon ID | free/open source | No extra tap | Window is a guess; still wrong for quick hand-offs |
| Never claim; copy the anonymous session into a new owned session | Store already serialises sessions as one JSON document (0003) | free/open source | Original anon copy expires on its own | Duplicates personal data; two copies to erase |

- **Recommended:** Explicit claim endpoint: only user_id='anon' sessions, founder confirms in the UI. A conditional update is race-safe and the confirmation is the consent moment for linking a conversation to an identity.
- **Ruled out:** Auto-claim with a window: guesses ownership on shared devices. Copy-on-claim: doubles personal data and complicates erasure (3.2.4).

### R120

**In-session consents (cohort, private) set once at start; cannot be seen or withdrawn** · weight 68 · Missing logic · impact 3/5, reach 3/5, confidence 3/3 · flags F-B2-008, F-A3-014, F-B3-015

- **Evidence (B2):** backend/app/agents/ideation.py:130 cohort_consent lives only inside the JSON document and is set only at creation (:210, from routers/ideation.py:256/294). No route changes it afterwards (grep: no other writer). backend/app/cohort/programme.py:40 filters on it. TASKS 3.2.1 plans a core.consents table 'with time and withdrawal' that nothing ties to this flag.
- **Evidence (A3):** backend/app/agents/ideation.py:210 sets s.cohort_consent only in new_session; routers/ideation.py:249-257 accepts share_with_programme and private only on POST /sessions; no endpoint changes them later. cohort/programme.py:40 reads s.cohort_consent from the session document, separate from the planned core.consents table.
- **Evidence (B3):** cohort_consent is saved in to_dict (agents/ideation.py:159) but left out of snapshot() (:236-250), and the frontend Snapshot type has no such field (agentClient.ts:67-76). Talk.tsx:121-134 restores private mode from the snapshot (:128) but has nothing for consent. 5.5.1's How is 'a consent checkbox at session start'. No route changes the flag later (step 2). The request comment promises 'their incubator or programme' (routers/ideation.py:253-254), but the session holds no programme, so the checkbox cannot name one.

- **Why it matters:** A founder who returns sees no sign of whether they agreed to share and has no way to withdraw short of deleting the conversation. They are asked to agree to an unnamed programme, which is not a specific, informed consent under DPDP.
- **Where to build it:** agents/ideation.py (snapshot), agentClient.ts (Snapshot, startSession), Talk.tsx (shown on resume, changeable), the consent event route from step 2

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Return the consent state and programme name in the snapshot; show it as a toggle on the Talk page that calls the consent-event route | One field in snapshot(), one in the TS type, and the PATCH route recommended at 3.2.1 | free/open source | Visible, changeable, tied to a named programme | Depends on the consent route and join code landing together |
| Ask again at every resume | UI only | free/open source | No new route | Nags the founder; the answer still cannot be stored without a route |
| Move cohort consent to Consent.tsx only | The existing per-purpose screen | free/open source | One consent place | Consent.tsx stores only in the browser; the server-side session flag would no longer be set |
| Leave start-only as planned | Plan as written | free/open source | Smallest change | No visibility, no withdrawal, no named programme |

- **Recommended:** Return the consent state and programme name in the snapshot; show it as a toggle on the Talk page that calls the consent-event route. It turns 5.5.1 from a one-way switch into a consent the founder can see and withdraw. It reuses the consent events and join code from steps 1 and 2, so the cohort reader honours the latest choice.
- **Ruled out:** Re-asking: annoying and still unstorable. Consent.tsx only: browser-only storage, so the server could never honour it. Start-only: fails visibility, withdrawal and specificity.

### R129

**Browser keeps only the latest session id, so sign-up can claim one conversation at most** · weight 68 · Missing function · impact 3/5, reach 3/5, confidence 3/3 · flags F-B5-022

- **Evidence (B5):** frontend/src/pages/Talk.tsx:29, 44-52, 331-333 — one localStorage key 'vanigam_talk_session', overwritten when a new conversation starts and removed on any load error (Talk.tsx:134, B5-06 flag 2); no other page reads it (grep SESSION_KEY). Claims also go through store.get, which hides sessions idle over 6 h (store.py:48-49, 95).

- **Why it matters:** A founder who tried two ideas, or signs up the next day, can claim at most the last conversation, and only within six idle hours today; earlier anonymous conversations become orphans the founder can neither see nor delete, left only to the retention job.
- **Where to build it:** frontend Talk.tsx (list of recent session ids), the sign-up/sign-in flow in frontend/src/auth.tsx, the claim endpoint (accepts several ids; bypasses the idle hiding)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Recent-sessions list in localStorage, claimed in one call at sign-in | Small array of {id, started} kept by Talk.tsx; auth.tsx posts it after login | free/open source | Every conversation from that browser follows the founder; no new dependency | Only the same browser; list must be pruned |
| Claim by device id cookie | An anonymous device id set at first visit and stored on each session | free/open source | Finds all sessions from the device server-side | Another identifier to protect and erase; cookie consent considerations |
| Claim only the current session (as planned) | TASKS.md 3.1.1 | free/open source | Simplest | Orphans earlier conversations |

- **Recommended:** Recent-sessions list in localStorage, claimed in one call at sign-in. Covers the common case (same phone) with no new identifier, and makes the earlier conversations reachable for the founder's own delete.
- **Ruled out:** Device id: a new tracking identifier to justify under DPDP; current-session only: leaves orphans the founder cannot erase.

### R131

**Consent given in anonymous sessions has no record, no withdrawal, no claim path** · weight 68 · Missing logic · impact 3/5, reach 3/5, confidence 3/3 · flags F-B3-007

- **Evidence (B3):** 3.2.1 waits on 3.1.1 and keys rows to a founder. But cohort consent is already taken today on anonymous sessions: share_with_programme is set once in new_session (agents/ideation.py:205-210) and stored as cohort_consent (:130, :159). No endpoint changes it after start (routers/ideation.py routes: start, resume, delete, turns, notices only), and nothing stores when it was given or which wording was shown. cohort/programme.py:40 counts it with no time check. 5.5.1 ('When: now') will add the checkbox before 3.2.1 exists.

- **Why it matters:** An anonymous founder who ticked 'share with programme' cannot withdraw except by deleting the whole conversation. There is no proof of when they agreed or to what text. And when they later sign up (3.1.1), the plan says nothing about carrying the session's consent into core.consents, so the two records can disagree.
- **Where to build it:** agents/ideation.py (consent events on the session document), routers/ideation.py (a consent update route), the 3.2.1 table design (subject = session or user), 3.1.1 claim step

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Consent events inside the session JSON (purpose, granted/withdrawn, time, notice version), plus a PATCH route; copied into core.consents on claim | Fits decision 0003 (one JSON document) and works with no database | free/open source | Withdrawal and proof now for anonymous founders; one migration path on sign-up | Two stores until the claim; the copy must be tested |
| core.consents with a nullable user_id and a session_id subject | SQLAlchemy/Alembic table as 3.2.1 plans | free/open source | One table for both kinds of subject | Waits on 2.1.1; nothing to write to on the memory store |
| Defer cohort consent until sign-up (remove it from anonymous sessions) | Plan change: 5.5.1 waits on 3.1.1 | free/open source | Single record keyed to a founder | Programme view stays empty until accounts and the database exist |
| Consent management platform (e.g. a hosted CMP) | Commercial consent tools | paid | Ready-made records and UI | Paid and online; sends founder data to a third party |

- **Recommended:** Consent events inside the session JSON (purpose, granted/withdrawn, time, notice version), plus a PATCH route; copied into core.consents on claim. It gives withdrawal and proof today on every store and keeps decision 0003. It also makes the cohort reader check the latest event instead of a boolean fixed at start, and gives 3.1.1 a defined claim step for consent.
- **Ruled out:** Nullable-user table: blocked on 2.1.1, so 5.5.1 would still ship with no record. Deferring cohort consent: empties a built feature for months. Hosted CMP: paid and sends data off the platform, against the free/offline rule and decision 0004.

### R132

**Erasure deletes consents, but retention keeps consents a year after the data** · weight 68 · Logic flaw · impact 3/5, reach 3/5, confidence 3/3 · flags F-B5-014

- **Evidence (B5):** SYSTEM-DESIGN.md:187-195 table: Consents 'as long as the data they cover, plus 1 year'; SYSTEM-DESIGN.md:197-198: 'One deletion request removes a founder's sessions, transcripts, documents and consents'. TASKS.md 3.2.4 copies both: Why 'remove ... consents' and How 'consents as long as the data they cover plus one year'.

- **Why it matters:** The two rules cannot both run: if erasure deletes the consent rows, the platform loses its proof that past processing was lawful (the reason for the +1 year); if it keeps them, the erasure is incomplete by its own definition. Whoever builds 3.2.4.1 picks one silently, and the nightly job (3.2.4.2) then deletes or keeps them on a different rule.
- **Where to build it:** SYSTEM-DESIGN §5.4 (decide the rule), core.consents (3.2.1), delete-all-for-user (3.2.4.1)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Tombstone consent record after erasure | Common DPDP/GDPR practice: keep a minimal record (purpose, given/withdrawn timestamps, erasure timestamp, pseudonymous id) with no personal content, deleted one year later | free/open source | Satisfies both rules: personal data gone, lawful-basis proof kept for the stated year | Needs a pseudonymous id that cannot be linked back; legal review (3.2.6) should confirm |
| Delete consents with everything else | Literal reading of §5.4 line 198 | free/open source | Simplest; nothing left | Loses evidence of consent; contradicts the retention table |
| Keep full consent rows for one year | Literal reading of the retention table | free/open source | Full audit trail | Keeps identifiers after an erasure request |

- **Recommended:** Tombstone consent record after erasure. The only option that honours both written rules; it is a decision the owner and the 3.2.6 legal review should record before 3.2.4.1 is built.
- **Ruled out:** Delete with everything: breaks the retention rule and the proof it exists for; keep full rows: breaks the erasure rule.

### R166

**Field encryption plan breaks unique and indexed columns; no key or blind-index design** · weight 61 · Missing structure · impact 3/5, reach 3/5, confidence 2/3 · flags F-A3-018

- **Evidence (A3):** backend/app/models/founder.py:13-15 NOTE says phone, date_of_birth, caste_category get an AES-256 TypeDecorator 'transparent' wrap, but phone is unique=True (:25) and indexed (ix_founders_phone :52), and email is unique and indexed (:24, :51). core/config.py has no encryption-key setting; secret_key (:21) is the only secret. TASKS 3.2.2 says only 'field-level encryption through an ORM type'.

- **Why it matters:** Randomised AES-GCM (the safe mode) gives a different ciphertext each time, so the unique constraints stop working (duplicate phones allowed) and lookups by phone or email cannot use the index. Deterministic encryption keeps them but leaks equality and is weak for low-cardinality fields like caste. Without a separate key with rotation, the easy path is reusing secret_key, which ties token signing to data encryption.
- **Where to build it:** a core/crypto.py TypeDecorator, a new ENCRYPTION_KEYS setting, migration adding HMAC blind-index columns for lookup fields

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| AES-GCM TypeDecorator (cryptography lib) with key ID prefix + HMAC-SHA256 blind index columns for unique/lookup fields | pyca/cryptography is the standard Python crypto library; blind index is the common pattern (CipherSweet) | free/open source | Strong encryption, unique constraints and lookups preserved on the HMAC column, key rotation by key ID | Extra columns and a re-encrypt script for rotation |
| sqlalchemy-utils StringEncryptedType | Popular SQLAlchemy extension | free/open source | Drop-in | Default AES engine is deterministic-ish/ECB-like in older versions; no blind index or key rotation |
| PostgreSQL pgcrypto (pgp_sym_encrypt) | Built-in extension | free/open source | No Python crypto code | Key travels in SQL text and can appear in DB logs; harder with the ORM |
| Cloud KMS envelope encryption | AWS/GCP KMS | paid | Managed keys | Paid and online; violates the free/offline constraint |

- **Recommended:** AES-GCM TypeDecorator (cryptography lib) with key ID prefix + HMAC-SHA256 blind index columns for unique/lookup fields. The only option that keeps the existing unique and indexed lookups, uses a key separate from JWT signing, and supports rotation, all offline.
- **Ruled out:** sqlalchemy-utils: weak defaults, no blind index or rotation. pgcrypto: keys exposed in SQL and logs. Cloud KMS: paid and online.

### R167

**Founder and Startup carry soft delete plus unique email/phone/GSTIN, against D12 erasure** · weight 61 · Logic flaw · impact 3/5, reach 3/5, confidence 2/3 · flags F-B2-016

- **Evidence (B2):** backend/app/models/founder.py:18 and startup.py:16 use SoftDeleteMixin (db/base.py:43-44 deleted_at). founders.email and phone are unique, and startups.cin_number, dpiit_number and gstin are unique. Startup's FK is ondelete=CASCADE, which fires only on a hard delete. TASKS D12 recommends erasure.

- **Why it matters:** If the 3.1.2 CRUD follows the models and soft-deletes, a 'deleted' founder's personal data stays in the table, against DPDP erasure. Their email, phone and GSTIN stay unique, so the same person cannot sign up again. Startups and profile_completeness are not cascaded. Every query must also remember to filter deleted_at.
- **Where to build it:** backend/app/models/founder.py, startup.py (drop SoftDeleteMixin in the 3.1.2 migration); routers /profiles DELETE as a hard delete; 3.2.4.1 delete-all-for-user

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Drop SoftDeleteMixin; hard delete with FK cascades (and an audit row without personal data) | Matches D12 and SYSTEM-DESIGN 5.4; the cascades already exist | free/open source | Erasure is real; unique constraints free up; simpler queries | No undo (mitigated by backups for 7 days) |
| Keep soft delete, use partial unique indexes (WHERE deleted_at IS NULL), and purge after N days | Common PostgreSQL pattern | free/open source | An undo window | Personal data kept after the request; contradicts D12's recommendation |
| Anonymise on delete (null personal columns, keep rows) | Pseudonymisation pattern | free/open source | Keeps aggregate counts | NOT NULL columns block it; analytics already rebuild from sessions |

- **Recommended:** Drop SoftDeleteMixin; hard delete with FK cascades (and an audit row without personal data). Aligns the schema with the recommended D12 decision before 3.1.2 writes real records, and reuses the cascades already defined.
- **Ruled out:** Partial unique plus purge: keeps personal data after an erasure request. Anonymise: conflicts with the NOT NULL columns, and no aggregate depends on these rows.

### R169

**No merge or conflict rule for moving browser state to the server (two devices, first sync)** · weight 61 · Missing structure · impact 3/5, reach 3/5, confidence 2/3 · flags F-B2-019

- **Evidence (B2):** TASKS 3.1.3 says only 'store each on the founder's record'. frontend/src/pages/Pipeline.tsx:52-66 and Suppliers.tsx:102-110/236-242 save whole arrays with no version or timestamp. Pipeline IDs are 'local-${Date.now()}' (Pipeline.tsx:116), and supplier IDs come from a Date.now() counter (Suppliers.tsx:113-114). journeyStore.ts:70 discards a mismatched record instead of migrating it. By contrast, the session store has version-checked saves (agents/store.py:98-125).

- **Why it matters:** At the first sign-in on a second device, the server and the browser both hold a pipeline or quote list. Last write wins, so one device's work silently erases the other's. Time-based local IDs collide across devices, so a merge by ID can overwrite the wrong investor entry. The founder loses the investor contacts or quotes that 3.1.3 exists to protect.
- **Where to build it:** the 3.1.3 endpoints (version per record with 409 like the session store); frontend stores (UUID IDs via crypto.randomUUID, updated_at per item); a first-sync merge rule

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Per-record version and updated_at with 409 on conflict, and a union-by-UUID merge at first sync | Reuses the optimistic-concurrency pattern of decision 0003 and the session store | free/open source | No silent loss; consistent with the existing store | The client must handle a 409 by reloading |
| CRDT sync (Yjs or Automerge) | Mature open-source CRDT libraries | free/open source | Automatic merging, offline-first | Heavy for a few lists; a new storage format on the server |
| Server wins after first sign-in; the browser is a cache only | Simple authoritative-server model | free/open source | Easy to reason about | Edits made offline or before the first sync are lost |
| Last write wins with item timestamps | The common default | free/open source | No conflicts to show | Silent loss when clocks or devices differ |

- **Recommended:** Per-record version and updated_at with 409 on conflict, and a union-by-UUID merge at first sync. It reuses the concurrency rule the platform already trusts for sessions, keeps it in one shape across stores, and makes conflicts visible instead of silent.
- **Ruled out:** CRDTs: far heavier than a handful of short lists needs. Server wins: drops offline edits. Last write wins: the silent loss this flag is about.

### R195

**3.2.5.1 is marked 'now' but its auth needs the PostgreSQL users table** · weight 52 · Logic flaw · impact 2/5, reach 2/5, confidence 3/3 · flags F-B3-003

- **Evidence (B3):** api/deps.py:19-30 get_current_user loads User through the SQLAlchemy session (db/session.py:24-27), and routers/auth.py:24 login needs it too. User (models/user.py:18-37) has no role column for 3.2.5.2. TASKS.md lists 2.1.1 (database) as waiting on the owner, while 3.2.5 says 'When: now for the auth check'.

- **Why it matters:** Doing 3.2.5.1 as written makes the Cohort page unusable on any machine without a working database, which is every machine today. The role task also lists no migration step.
- **Where to build it:** docs/specs/TASKS.md 3.2.5 (When, subtasks); api/deps.py; models/user.py plus a migration

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Mark 3.2.5.1 waiting on 2.1.1 and add a role migration subtask | A plan-only change, consistent with how P3 is gated | free/open source | An honest order; no interim code | The endpoint stays open until the database lands |
| Interim operator key from settings, compared with secrets.compare_digest | pydantic-settings already loads backend/.env; stdlib secrets | free/open source | Works offline today with no database and closes the open endpoint now | One shared key, replaced by roles later |
| Run PostgreSQL through the existing docker-compose db service | backend/docker-compose.yml already defines it | free/open source | The real auth path | This is the owner action 2.1.1 already waits on |
| Disable /cohort/programme until auth exists | A one-line router change | free/open source | No exposure | Removes a built feature |

- **Recommended:** Interim operator key from settings, compared with secrets.compare_digest. It closes the endpoint immediately without the database, keeps the feature, and fits the free and offline rule. 3.2.5.2 then replaces it with a role column once 2.1.1 and 3.1 land; add that migration as a subtask.
- **Ruled out:** Re-marking as waiting: leaves the endpoint open for an unknown time. Docker PostgreSQL: it is itself the blocked owner action. Disabling: throws away a built, tested view.

### R204

**Account enumeration: register returns 409 and login skips bcrypt for unknown emails** · weight 51 · Logic flaw · impact 2/5, reach 3/5, confidence 2/3 · flags F-A3-010

- **Evidence (A3):** backend/app/services/auth_service.py:40-42 comments 'Verify even when the user is missing' but `user is None or not verify_password(...)` short-circuits, so unknown emails return without the ~100 ms bcrypt cost; :24-29 register answers EMAIL_TAKEN 409.

- **Why it matters:** Anyone can test whether an email is registered with Vanigam, which reveals that a person is a founder in the programme; the code contradicts its own stated intent.
- **Where to build it:** services/auth_service.py

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Verify against a fixed dummy bcrypt hash when the user is missing; generic register response | passlib already in use (core/security.py:20) | free/open source | Two-line fix matching the comment | Generic register reply needs email delivery to be fully silent, which is not available offline |
| Rate limit login and register per email and IP | RateLimitMiddleware exists (core/middleware.py) | free/open source | Slows bulk probing | Does not remove the signal |
| slowapi limiter on auth routes | Popular Starlette limiter | free/open source | Per-route limits | New dependency duplicating the existing middleware |

- **Recommended:** Verify against a fixed dummy bcrypt hash when the user is missing; generic register response. Makes the code do what its comment promises at no cost; register wording can stay helpful until email exists.
- **Ruled out:** Rate limiting alone: reduces speed, not the leak. slowapi: duplicates existing middleware.

### R210

**Programme endpoint loads up to 500 full session documents one at a time** · weight 45 · Optimisation · impact 2/5, reach 2/5, confidence 2/3 · flags F-A3-019

- **Evidence (A3):** backend/app/routers/cohort.py:40 awaits store.get(sid) sequentially for each of up to 500 IDs (:33); each SqlStore.get (agents/store.py:86-95) opens a new DB session and parses the whole JSON document, though programme_cohort reads only a few slots and cohort_consent.

- **Why it matters:** Large programmes make one request run 500 round trips and parse 500 transcripts, holding a worker and the pool (2.4.3) for seconds, and every non-consenting founder's full document is read for nothing.
- **Where to build it:** agents/store.py (get_many), routers/cohort.py

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| store.get_many: one SELECT ... WHERE session_id = ANY(:ids) (and Redis MGET), filtering consent before parsing | SQLAlchemy in_() and redis-py mget | free/open source | One round trip; skips non-consenting documents | New store method on three backends |
| asyncio.gather over store.get | stdlib | free/open source | Two-line change | 500 concurrent DB sessions exhaust the pool |
| Project the needed fields with JSONB operators in SQL | PostgreSQL JSONB | free/open source | Minimal data transfer | Couples SQL to the document shape before the 5.5.5 split |

- **Recommended:** store.get_many: one SELECT ... WHERE session_id = ANY(:ids) (and Redis MGET), filtering consent before parsing. One query, bounded memory, and non-consenting documents are never loaded.
- **Ruled out:** gather: overwhelms the connection pool. JSONB projection: ties queries to a document shape that 5.5.5 will change.

