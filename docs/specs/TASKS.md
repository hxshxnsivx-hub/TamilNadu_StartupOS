# Vanigam build plan: hybrid task tree

**Date:** 2026-10-17
**Status:** draft (for owner review)
**Replaces as the working list:** `.kiro/specs/tamil-nadu-startupos/tasks.md` (August). That file
stays as history; work is picked from this one.

**Built from:** the October design (`IDEATION-PIPELINE-DESIGN.md`, `SYSTEM-DESIGN.md`,
`docs/decisions/0001`–`0010`, `docs/BACKLOG.md`, `docs/runbooks/`, `docs/eval/report.md`) and the
August spec (`.kiro/specs/tamil-nadu-startupos/` requirements, design, constraint solutions,
v2 integration plan, feasibility survey, traceability matrix, task list), plus the 2026-10-02 gap
analysis. Every item was checked against the code at `d5d3157`.

Three sources are not in git; they exist only untracked in the main checkout:
`.kiro/specs/tamil-nadu-startupos/rnd-elicitation.md`, `.kiro/specs/tamil-nadu-startupos/ideation-redesign.md`
and `ANALYSIS-END-TO-END.md` (the gap analysis).

## How this file works

**The five-finger rule.** An item is in this plan only if all five questions have a clear answer
that fits the current constraints:

| Finger | Question |
|---|---|
| **Why** | What problem does it solve today? |
| **Where** | Which module, screen, data file or document? |
| **How** | What is the mechanism? |
| **When** | Which phase, what it depends on, what triggers it at runtime? |
| **What for** | The outcome for the founder or the system |

Items that failed the rule are listed in [Dropped](#dropped-and-why), each with its reason, so
nothing from the sources is silently lost.

**Current constraints** every task must respect:

- Free and offline. No paid API or hosting. Deterministic offline paths are the baseline; free
  models (Gemini free tier, then Ollama, decision 0009) are optional extras. Paid integrations
  already built (Claude, Sarvam, Cohere) stay dormant until a key appears.
- The ideation agent is the conversation: code decides, the model words it (0001, 0002, 0007,
  0010). Fact check before speech (0005). Only public vocabulary leaves the platform (0004).
  Sessions are one JSON document (0003).
- No invented data: real, cited sources, or "not published".
- Documentation changes with the code, in the same pull request (SYSTEM-DESIGN §6.2).

**Numbering.** Phase `N` → subphase `N.M` → task `N.M.T` → subtask `N.M.T.S`. Tasks within a
subphase run in order; subtasks within a task run in order.

**Markers.**

| Marker | Meaning |
|---|---|
| `[ ]` | open (includes partly built; the note says what is missing) |
| `[x]` | done (built work is summarised in each section's "Already built" line instead) |
| `[w]` | waiting on an owner action, key or reviewer, named in the note |
| `[d]` | needs an owner decision first, named as `Dn` (see [Owner decisions](#owner-decisions)) |

## The tree

```
P1 Ideation conversation .................. IDEATION-PIPELINE-DESIGN, decisions 0001-0010
├─ 1.1 Turn loop and questions ............ S0-S2, S7
├─ 1.2 Evidence and novelty ............... S3-S5
├─ 1.3 Review panel ....................... S6
├─ 1.4 Roadmap ............................ S8
├─ 1.5 Voice and language ................. Phase 3, 0008, 0009
└─ 1.6 Working memory ..................... SYSTEM-DESIGN §3.2-3.3
P2 Platform ............................... SYSTEM-DESIGN §2-5, §7, §9
├─ 2.1 Session store
├─ 2.2 Caching rules
├─ 2.3 Background jobs
└─ 2.4 Database layout and logs
P3 Founder records and privacy ............ SYSTEM-DESIGN class E, §5.4; August Req 1.1, 6.1
├─ 3.1 Linking conversations to founders
└─ 3.2 Consent and protection
P4 Founder tools beyond ideation .......... August Req 2-4 that still fit (see D8)
├─ 4.1 Schemes
├─ 4.2 Suppliers
├─ 4.3 Funding
└─ 4.4 News
P5 Quality, operations and cohort ......... SYSTEM-DESIGN §6, §8, §11 Ph4-5; IDEATION Ph4-5
├─ 5.1 Evaluation and tuning
├─ 5.2 Data checks in CI
├─ 5.3 Documentation
├─ 5.4 Monitoring
├─ 5.5 Cohort analysis
├─ 5.6 Reference data growth
└─ 5.7 Code cleanup
```

---

## P1 Ideation conversation

**Already built:** answer check and wrong-type routing (S1), one question per turn with at most
7 (S2), evidence scan (S3), novelty check (S4), levers narrated one per turn (S5), the seven-seat
review panel with vote and synthesis (S6), confirmation (S7), the planner roadmap with costs,
licences and risks (S8), streamed fact-checked replies, private sessions, the job board
(decision 0010), the Talk page with the orb and recorded voice, and the free model chain
(0009). Phase 1 "done when" criteria 1, 2, 3 and 5 pass; criterion 4 waits on the database
(task 2.1.1).

### 1.1 Turn loop and questions

#### 1.1.1 `[ ]` Send the founder's profile into the conversation
- **Why:** the Talk page asks for facts the profile already holds, wasting the 7-question budget.
- **Where:** `frontend/src/voice/agentClient.ts` (`startSession`), `Talk.tsx`; backend already accepts `profile`.
- **How:** pass the profile store's fields as `profile` when the session starts.
- **When:** now; at session start.
- **What for:** "never ask twice" (SYSTEM-DESIGN §3.2; IDEATION S0).
- `1.1.1.1` Send `profile` from `startSession`.
- `1.1.1.2` API test: a profile field is never asked.

#### 1.1.2 `[ ]` Confirmation that shows where each fact came from, and corrections that stick
- **Why:** at S7 the founder cannot see what was assumed, and saying "no" only re-opens questioning.
- **Where:** `elicitation/engine.py` (`restate`, `confirm`), `elicitation/session.py`.
- **How:** label each restated fact ("you said", "from your profile", "I assumed"); restate the problem in short form, not the founder's whole sentence; a corrected fact is locked as founder-given and the question budget is refunded by one.
- **When:** now; at confirmation.
- **What for:** no roadmap built on a wrong assumption (rnd-elicitation §4.3, §6.4; eval transcripts repeat the whole sentence as "the problem").
- `1.1.2.1` Source label per slot in the restatement.
- `1.1.2.2` Short restatement of the problem.
- `1.1.2.3` Rejection locks the corrected slot and refunds one question.
- `1.1.2.4` Tests.

#### 1.1.3 `[ ]` Question order and fact safety
- **Why:** capital can be asked before the idea is known; a model can record a fact the founder never said.
- **Where:** `elicitation/selector.py`, `agents/tools.py` (`note_fact`), `elicitation/session.py` (`put`).
- **How:** a "what before anything else" gate on candidate questions; reject model-noted facts whose text span is not in the founder's words; cap confidence when sources disagree so the founder is asked.
- **When:** now; every turn.
- **What for:** a humane order and grounded facts (rnd-elicitation §3.4, §6.3, §6.4).
- `1.1.3.1` Finger gate in the selector.
- `1.1.3.2` Span check on `note_fact`.
- `1.1.3.3` Disagreement cap in the merge.
- `1.1.3.4` Tests.

#### 1.1.4 `[ ]` Safe on a 2G connection
- **Why:** a replayed answer after a dropped response is consumed twice; a conflict shows a raw error; a resumed session has no re-orientation.
- **Where:** `routers/ideation.py` (`agent_turn`), `Talk.tsx`, `agents/ideation.py` (`snapshot`).
- **How:** optional `client_turn_id` returns the same response on replay; the Talk page offers reload on 409; a resume after a long gap repeats the pending question first.
- **When:** now.
- **What for:** conversations survive bad networks (rnd-elicitation §5.4; decision 0003).
- `1.1.4.1` `client_turn_id` idempotency.
- `1.1.4.2` 409 handling in the Talk page.
- `1.1.4.3` Resume preamble that repeats the pending question without charging the budget.

#### 1.1.5 `[ ]` Entry for founders with experience but no idea
- **Why:** a large share of founders arrive with skills, not an idea; `EntryMode.EXPERIENCE` exists but no endpoint can start it, and `/start` sends them to `/schemes`.
- **Where:** `routers/ideation.py` (`AgentStartIn`), `agents/ideation.py`, `elicitation/slots.py`, `frontend/src/pages/Start.tsx`, a new ranking module beside `planner/registry.py`.
- **How:** start the session in experience mode; rank registry domains and the catalogue's `demand` entries against the experience slots with a deterministic fit score; show three to five cited opportunity cards with a scheme pre-check (rules layer); a chosen card fills the idea slots and the normal flow continues.
- **When:** after 1.1.1; reuses S1-S8. The ranking (1.1.5.3) waits on the sector taxonomy (4.1.2, decision D5). Financial-capacity questions wait on 3.2.1.
- **What for:** a path in for first-generation founders (August Req 1.6; ideation-redesign §6 step 7).
- `1.1.5.1` Entry mode on session start.
- `1.1.5.2` `/start` routes no-idea founders to the experience conversation; a `domain_only` founder starts it with the domain pre-filled and the ranking filtered by that domain (August P-34.1-2).
- `1.1.5.3` Opportunity ranking from registry and catalogue (cited only; no embedding weight while embeddings are offline hashes).
- `1.1.5.4` Scheme pre-check on each card.
- `1.1.5.5` Chosen card writes back into the idea slots.

#### 1.1.6 `[ ]` Registered-startup subtype reaches the agent
- **Why:** a registered founder (2A/2B/2C) is asked idea questions they have already answered; the subtype lives only in the browser.
- **Where:** `frontend/src/journeyStore.ts`, `journey/engine.py`, agent greeting.
- **How:** send the subtype as facts at session start; the journey engine and greeting use it.
- **When:** with 1.1.5.1.
- **What for:** the right path per founder (August P-34.3-6).
- `1.1.6.1` Send `reg_subtype` and entry mode at session start.
- `1.1.6.2` Greeting and journey use them.

#### 1.1.7 `[ ]` The founder can delete a conversation
- **Why:** `DELETE /ideation/agent/sessions/{id}` exists, but the Talk page offers no way to call it.
- **Where:** `Talk.tsx`, `agentClient.ts`.
- **How:** a delete control that calls the endpoint and clears the local session ID.
- **When:** now; "delete all" follows with founder records (3.2.4.1).
- **What for:** erasure the founder controls (SYSTEM-DESIGN §3.2).
- `1.1.7.1` Delete control.

### 1.2 Evidence and novelty

#### 1.2.1 `[ ]` Fix the relevance faults the quality set shows
- **Why:** current replays still name irrelevant papers and startups, ask off-domain "things to think through", and treat generic words as novelty elements; this undermines trust.
- **Where:** `research/scan.py`, `research/sources.py`, `research/terms.py`, `research/novelty.py`.
- **How:** choose discussion points from the matched domain and pack; name a closest paper only when its overlap with the query is strong; tighten local-startup matching by sector and terms; exclude beneficiary and generic words from novelty elements; treat a zero count on a single hyphenated word as "not searched well".
- **When:** now; in the research job.
- **What for:** credible evidence (transcripts in docs/eval/report.md and a replay of current code; IDEATION §3.6 r2).
- `1.2.1.1` Discussion points from the matched domain.
- `1.2.1.2` Closest-paper relevance threshold.
- `1.2.1.3` Local startup matching by sector and terms.
- `1.2.1.4` Generic and beneficiary words out of the element list.
- `1.2.1.5` Hyphen normalisation and the zero-count rule.
- `1.2.1.6` Find why the medical-EMI idea gets no novelty statement; say "unclear" honestly when that is the cause.
- `1.2.1.7` Eval assertions for each fix.

#### 1.2.2 `[ ]` Levers worded for the founder's domain
- **Why:** the localise lever says "local hospital or market routines" for banana chips and t-shirts.
- **Where:** `research/novelty.py` (`_levers`).
- **How:** word each lever from the matched domain and sector.
- **When:** now.
- **What for:** relevant advice (IDEATION §3.6 r4).
- `1.2.2.1` Domain-aware lever text.
- `1.2.2.2` Test across three sectors.

#### 1.2.3 `[ ]` Results tied to the idea version
- **Why:** research runs once per conversation and is never re-run when the idea changes, so an old verdict can be spoken (decision 0001 requires the opposite).
- **Where:** `agents/jobs.py`, `agents/results.py`, `agents/ideation.py` (`_absorb`).
- **How:** key results by `idea_version` instead of `LATEST`; when the core slots change, start a new research job and discard results for the old version.
- **When:** before 1.2.4.
- **What for:** evidence that matches the idea being discussed.
- `1.2.3.1` Key results by idea version.
- `1.2.3.2` Re-run research when the version changes.
- `1.2.3.3` Test: a stale result is never narrated.

#### 1.2.4 `[ ]` The founder chooses a lever, and it becomes a new idea version
- **Why:** levers are listed read-only; the idea cannot evolve inside the conversation.
- **Where:** `routers/ideation.py`, `agents/ideation.py`, `Talk.tsx`.
- **How:** a choose-lever action updates the idea slots, bumps `idea_version` and re-runs research (1.2.3).
- **When:** after 1.2.3 and 1.3.1.
- **What for:** an iterated idea with its own evidence (IDEATION §2.3).
- `1.2.4.1` API action.
- `1.2.4.2` Talk page control.
- `1.2.4.3` Test of the version bump and re-run.

#### 1.2.5 `[ ]` Scan discussion points become questions
- **Why:** for ideas outside the fixed questions, the scan's points are read out but never asked.
- **Where:** `agents/ideation.py`, `elicitation/engine.py` (`add_dynamic`).
- **How:** feed the best scan point into the dynamic questions (at most 3, shared with the panel).
- **When:** after 1.2.1.1.
- **What for:** questions that fit the domain (decision 0002 consequence).
- `1.2.5.1` Feed one scan point to `add_dynamic`.
- `1.2.5.2` Test.

#### 1.2.6 `[ ]` Grow the public vocabulary from weak searches
- **Why:** words like "dryer" and "copra" are not in the lexicon, so searches lose recall.
- **Where:** `research/terms.py`, logs.
- **How:** log, by public term and count only (no founder text), searches that had few or no safe terms; a reviewer adds terms by commit.
- **When:** ongoing.
- **What for:** better recall without leaking ideas (decision 0004 consequence).
- `1.2.6.1` Weak-search log event with no idea text.
- `1.2.6.2` Review step in the runbook.

#### 1.2.7 `[w]` Patents in every search
- **Waiting on:** owner registering free EPO OPS keys (`EPO_OPS_KEY`, `EPO_OPS_SECRET`).
- Code and tests exist (`research/sources.py`, `tests/unit/test_patents_epo.py`). Every eval transcript says "I could not search patents this time".
- `1.2.7.1` Live check of the request format once keys are set.

### 1.3 Review panel

#### 1.3.1 `[ ]` The panel ranks the levers
- **Why:** levers are ordered only by gap size; the design asks the prior-art and customer seats to rank them.
- **Where:** `agents/council/`, `research/novelty.py`, narration in `agents/ideation.py`.
- **How:** seats score each lever; the vote orders them before narration.
- **When:** after the panel job; before 1.2.4.
- **What for:** best lever first (IDEATION §2.3, Phase 2).
- `1.3.1.1` Lever scoring in the seats.
- `1.3.1.2` Narration uses the panel's order.

#### 1.3.2 `[ ]` The devil's-advocate seat tests each lever
- **Why:** a founder can read a gap as a guarantee.
- **Where:** `agents/council/rules.py`, `synthesis.py`.
- **How:** one objection per lever from the devil seat, carried into the synthesis.
- **When:** with 1.3.1.
- **What for:** calibrated expectations (IDEATION §3.6 r5).
- `1.3.2.1` Per-lever objection.
- `1.3.2.2` Test.

#### 1.3.3 `[ ]` Stop medical advice for non-medical ideas
- **Why:** a hospital-instalment fintech idea is told to "start as a communication aid without medical claims".
- **Where:** `agents/council/evidence.py` (`pack.health = is_health(idea) or trials`), `research/terms.py` (`HEALTH_TERMS`), `agents/council/rules.py`.
- **How:** the health flag fires on any health keyword (the word "medical" is enough); require a device or clinical signal before the health variant.
- **When:** now.
- **What for:** correct variants (docs/eval/report.md, medical_emi).
- `1.3.3.1` Tighten the trigger.
- `1.3.3.2` Eval assertion.

### 1.4 Roadmap

#### 1.4.1 `[d]` One roadmap path (D3)
- **Why:** `/ideate` still builds the old placeholder roadmap (`swarms/roadmap`, `/ideation/roadmap`); `/talk` builds the planner roadmap. The same idea gets two different plans, and scheme annotation only runs on the old one.
- **Where:** `routers/ideation.py`, `frontend/src/pages/Ideate.tsx`, `schemes/annotate.py`, `planner/`.
- **How:** point the Ideate screen at the planner output; move scheme annotation onto planner milestones; keep the graph functions in `swarms/roadmap/milestones.py` that the planner uses; retire the placeholder extraction and fixed feasibility score.
- **When:** after decision D3.
- **What for:** one plan, with schemes placed on milestones (August Req 1.4; gap analysis D1, D8).
- `1.4.1.1` Scheme annotation on planner milestones.
- `1.4.1.2` Ideate screen reads the planner roadmap.
- `1.4.1.3` Retire `/ideation/roadmap`'s placeholder path and its tests.

#### 1.4.2 `[ ]` Milestone tracker on the planner roadmap
- **Why:** the tracker works only on the old roadmap, in the browser.
- **Where:** roadmap screen; server-side storage later (3.1.3).
- **How:** three states per planner milestone (not started, in progress, done).
- **When:** after 1.4.1; server-side after 3.1.
- **What for:** a roadmap that moves (August P-31).
- `1.4.2.1` Tracker on planner milestones.

#### 1.4.3 `[ ]` One fact store feeds the roadmap and the schemes
- **Why:** `/schemes/recommend` takes a separate profile, so the founder can be asked the same thing twice.
- **Where:** `agents/tools.py` (`support_for`), `schemes/engine.py`.
- **How:** project the session's slots onto the scheme profile.
- **When:** now.
- **What for:** consistency (ideation-redesign §4.2.2).
- `1.4.3.1` Slot-to-profile projection.
- `1.4.3.2` Test.

### 1.5 Voice and language

#### 1.5.1 `[ ]` Offline replies in Tamil and Hindi
- **Why:** the 38 translated fixed sentences are used only when a model rewords; the pure offline path is English only.
- **Where:** `agents/ideation.py` (`_offline_stream`), `voice/data/translations.json`.
- **How:** when the session language is not English, substitute the translated sentence; titles and names stay English.
- **When:** now; speaking them to founders waits on 1.5.2.
- **What for:** the whole conversation in the founder's language (BACKLOG free fix 2).
- `1.5.1.1` Use translations in the offline path.
- `1.5.1.2` Language set on the done event.
- `1.5.1.3` Test.

#### 1.5.2 `[w]` Native-speaker review of the Tamil and Hindi sentences
- **Waiting on:** a Tamil and a Hindi speaker (0 of 38 reviewed in each). Set `reviewed` per entry.
- `1.5.2.1` `[ ]` After review, record the sentences into the phrasebook (`python -m app.voice.phrasebook`, then `voice-worker/record_phrases.py`); without a Gemini key, recordings are the only free way to speak them (BACKLOG; decision 0009).

#### 1.5.3 `[w]` Gemini free tier live
- **Waiting on:** `GEMINI_API_KEY` in `backend/.env`. Provider chain, Gemini voice and caching are built (0009).
- `1.5.3.1` Live check.
- `1.5.3.2` Choose the Gemini voices.
- `1.5.3.3` `[ ]` Gemini transcription behind `/voice/transcribe` (today Sarvam only, else the browser).

#### 1.5.4 `[ ]` Tell founders that Google's free tier may use their text
- **Why:** decision 0009 requires this notice before any pilot; none exists.
- **Where:** `Talk.tsx` or `Consent.tsx`.
- **How:** show a notice when the active provider is Gemini.
- **When:** before any pilot.
- **What for:** honest data use.
- `1.5.4.1` Notice text and display rule.

#### 1.5.5 `[w]` Low-literacy design of the Talk page
- **Waiting on:** the owner's decision on the uncommitted frontend theme removal.
- **Why:** voice-first, plain-language use is the product's differentiator for low-literacy founders (feasibility survey U; August task 2.7.5).
- **How:** large controls, icons with spoken labels, no text-only steps, on the Talk page.
- `1.5.5.1` Low-literacy pass on the Talk page.

### 1.6 Working memory

#### 1.6.1 `[ ]` Bounded working memory
- **Why:** the full message history goes to the model every turn; long chats get slow on free tiers.
- **Where:** `agents/providers.py`, `agents/ideation.py`, `agents/jobs.py`.
- **How:** send the facts, a rolling summary and the last 6 turns (about 8,000 tokens); a background job rewrites the summary every 8 turns.
- **When:** model paths only.
- **What for:** fast, bounded turns (SYSTEM-DESIGN §3.2, Phase 2).
- `1.6.1.1` Trim to facts plus last 6 turns.
- `1.6.1.2` Rolling summary job.

#### 1.6.2 `[ ]` Stable prompt prefix
- **Why:** the conversation prompt puts the current question and known facts inside the fixed part, so provider caching never hits.
- **Where:** `agents/ideation.py` (`SYSTEM`), `agents/providers.py`.
- **How:** stable instructions first, per-turn parts after.
- **When:** keyed or Gemini paths.
- **What for:** lower latency (SYSTEM-DESIGN §3.3).
- `1.6.2.1` Reorder the prompt.

---

## P2 Platform

**Already built:** the session store with version-checked saves and 409 (decision 0003, migration
0004); the Redis layer for live sessions, research cache, source pauses and daily caps, all
optional (SYSTEM-DESIGN Phase 2); the in-process job board (0010); failure handling for Redis,
model and source outages (§9).

### 2.1 Session store

#### 2.1.1 `[w]` Sessions saved in PostgreSQL for real
- **Waiting on:** correct local PostgreSQL credentials in `backend/.env` (or Docker Desktop running `docker compose up -d db`).
- `2.1.1.1` Apply migration 0004.
- `2.1.1.2` The database integration test passes (IDEATION "done when" 4).

#### 2.1.2 `[ ]` Fix the "saved" flag when Redis is on
- **Why:** `routers/ideation.py` reports `saved: false` whenever Redis fronts the database, because the store names itself `database+redis`; the Talk page then wrongly says the conversation is not being saved.
- **Where:** `routers/ideation.py`, `docs/runbooks/sessions-not-saved.md`.
- **How:** treat any store name starting with `database` as saved.
- **When:** now.
- **What for:** a truthful banner.
- `2.1.2.1` Fix and test.

#### 2.1.3 `[d]` One rule for session lifetime (D4)
- **Why:** the store hides a session after 6 idle hours even in PostgreSQL, while the design keeps conversations 90 days.
- **Where:** `agents/store.py`, SYSTEM-DESIGN §4.2, §5.4.
- **How:** 6 hours applies to the Redis live copy only; PostgreSQL keeps the session for the retention period, then the retention job deletes it (3.2.4).
- **When:** after D4.
- **What for:** founders can return to a conversation.
- `2.1.3.1` Apply the decided rule in the store.
- `2.1.3.2` `[w]` "Save this idea" (waits on 3.1.1 and D4): a saved flag on the session, a control on the Talk page, and a retention rule that skips saved sessions (SYSTEM-DESIGN §5.4).

#### 2.1.4 `[ ]` Session format version
- **Why:** old session documents must stay readable as the format changes.
- **Where:** `agents/ideation.py` (`to_dict`, `from_dict`).
- **How:** a `format` field and an upgrade-on-read function.
- **When:** before the table split (5.5.5).
- **What for:** safe evolution (SYSTEM-DESIGN §5.3).
- `2.1.4.1` Field and upgrade function, with a test.

### 2.2 Caching rules

#### 2.2.1 `[ ]` One fetch per key at a time
- **Why:** ten sessions asking the same new query make ten fetches and burn the free source budget.
- **Where:** `research/sources.py`, `core/redis.py`.
- **How:** a Redis `lock:{key}` (30 seconds); others wait briefly for the result; without Redis, no lock.
- **When:** now.
- **What for:** stays within OpenAlex and GitHub free limits (SYSTEM-DESIGN §4.2-4.3).
- `2.2.1.1` Lock and wait.
- `2.2.1.2` Test with the fake Redis.

#### 2.2.2 `[ ]` Redis keys match the design
- **Why:** the code uses `rs:{hash}` and `rs:neg:{source}`; the design says `rs:{source}:{hash}` and `rs:neg:{source}:{hash}`.
- **Where:** `research/sources.py`, SYSTEM-DESIGN §4.2, `docs/runbooks/research-budget.md`.
- **How:** change the code or the document so they agree, and keep the runbook in step.
- **When:** now.
- **What for:** operators read the same keys the code writes.
- `2.2.2.1` Align, in one pull request.

#### 2.2.3 `[ ]` Reference data reloads without a restart
- **Why:** a harvested dataset changes only on deploy.
- **Where:** data loaders, `core/redis.py`.
- **How:** a `ver:{dataset}` key checked about once a minute; a new version clears that loader's cache.
- **When:** with Redis.
- **What for:** fresh data without redeploying (SYSTEM-DESIGN §3.1).
- `2.2.3.1` Version key and cache clear.

#### 2.2.4 `[ ]` ETags on reference lists
- **Why:** the screens download the registry, domain and scheme lists every time.
- **Where:** routers serving those lists.
- **How:** `ETag` set to the data version; answer 304 on a match.
- **When:** after 2.2.3.
- **What for:** faster screens on slow connections (SYSTEM-DESIGN §4.1).
- `2.2.4.1` ETag support.

#### 2.2.5 `[ ]` Clear expired research cache files
- **Why:** expired files in `.cache/research` are ignored but never deleted.
- **Where:** `research/` cache.
- **How:** a purge function, run by the nightly job.
- **When:** lands together with the nightly job (5.4.4).
- **What for:** bounded disk use (SYSTEM-DESIGN §5.4).
- `2.2.5.1` Purge function.

#### 2.2.6 `[w]` Nightly cache warming for registry domains
- **Waiting on:** a free OpenAlex key. Warming inside the shared free daily budget would use up the searches founders need live (`docs/runbooks/research-budget.md`).
- **Why:** common ideas could answer from cache instantly.
- **Where:** `scripts/`, the nightly job (5.4.4).
- **How:** run each registry domain's research queries nightly under the budget cap.
- **When:** after 2.2.1 and the key.
- **What for:** instant evidence for known domains (SYSTEM-DESIGN §4.3).
- `2.2.6.1` Warming script under the budget cap.

### 2.3 Background jobs

#### 2.3.1 `[w]` Durable results and a shared queue
- **Waiting on:** the database (2.1.1).
- **Why:** a restart loses running jobs, and several server processes cannot share them.
- **How:** a results table keyed by session, idea version and kind; a Redis queue (decision 0010).
- `2.3.1.1` Results table and migration.
- `2.3.1.2` Redis queue.

### 2.4 Database layout and logs

#### 2.4.1 `[ ]` New tables go in their schema
- **Why:** per-class access and retention need `core`, `ideation`, `knowledge` and `analytics` schemas; `agent_sessions` sits in the default schema.
- **Where:** `db/migrations`.
- **How:** every new table is created in its class's schema.
- **When:** from the next migration.
- **What for:** clean retention (SYSTEM-DESIGN §5.1).
- `2.4.1.1` Schemas created in the next migration.
- `2.4.1.2` Index sessions by idea version when something first queries by it (user and last-activity indexes exist; SYSTEM-DESIGN §5.6).

#### 2.4.2 `[ ]` Logs carry IDs and never idea text
- **Why:** the request ID is set but not bound into log lines, and nothing checks that logs hold no founder text.
- **Where:** `core/logging.py`, `core/middleware.py`.
- **How:** bind request and session IDs into the log context; a test that runs a turn and checks no idea text appears in the logs.
- **When:** now.
- **What for:** DPDP compliance (SYSTEM-DESIGN §2 rule 3, §8).
- `2.4.2.1` Bind IDs.
- `2.4.2.2` Log privacy test.

#### 2.4.3 `[ ]` Database connection pool per worker
- **Why:** nothing sizes the pool, so several workers can exceed the database's connection limit.
- **Where:** `db/session.py`, settings.
- **How:** set `pool_size` and `max_overflow` per worker so that workers × pool stays under the limit.
- **When:** now; matters once more than one worker runs.
- **What for:** no connection exhaustion (SYSTEM-DESIGN §5.6; August task 5.5.4).
- `2.4.3.1` Pool settings with a documented formula.

#### 2.4.4 `[ ]` Container image for the app
- **Why:** only PostgreSQL has a Dockerfile; the backend cannot be started the same way on every machine.
- **Where:** `backend/Dockerfile`, `backend/docker-compose.yml` (already runs PostgreSQL, Redis and an unused MinIO service; see 5.7.1.6).
- **How:** a backend image added to the existing compose stack.
- **When:** now.
- **What for:** one command to run the whole stack locally, free (August task 5.6.1).
- `2.4.4.1` Backend Dockerfile and compose service.

---

## P3 Founder records and privacy

Depends on the database (2.1.1). Conversations are anonymous today, so consent and founder
records start when conversations link to signed-in founders (SYSTEM-DESIGN §11, Phase 1 note).

### 3.1 Linking conversations to founders

#### 3.1.1 `[w]` Claim an anonymous session on sign-up
- **Waiting on:** 2.1.1.
- **Why:** a founder starts before registering; the session must follow them.
- **Where:** `agents/store.py`, `routers/auth.py`.
- **How:** attach `user_id` to the session at sign-up or sign-in.
- **What for:** low-friction start (rnd-elicitation §5.3).
- `3.1.1.1` Claim on sign-up.

#### 3.1.2 `[w]` Profile and startup records on the server
- **Waiting on:** 2.1.1.
- **Why:** the profile lives only in the browser; the `founders` and `startups` tables exist but nothing reads or writes them.
- **Where:** `routers/` (`/profiles`, `/startups`), `models/`, `profileStore.ts`.
- **How:** CRUD with auth on the existing tables; the browser store syncs to them; a completeness change re-runs scheme eligibility; a fact corrected in conversation is offered back to the profile and written only on agreement.
- **What for:** founder memory across devices (SYSTEM-DESIGN class E, §3.2; August Req 1.1, 6.1).
- `3.1.2.1` `/profiles` and `/startups` endpoints.
- `3.1.2.2` Browser profile syncs to the server.
- `3.1.2.3` Re-run eligibility on completeness change.
- `3.1.2.4` Write-back of corrected facts on agreement.

#### 3.1.3 `[w]` Move the other browser-only state to the server
- **Waiting on:** 3.1.2.
- **Why:** journey, funding pipeline, milestone status and supplier quotes are lost when the browser is cleared.
- **How:** store each on the founder's record.
- `3.1.3.1` Journey and milestone status.
- `3.1.3.2` Funding pipeline.
- `3.1.3.3` Supplier quotes.

### 3.2 Consent and protection

#### 3.2.1 `[w]` Consent per purpose
- **Waiting on:** 3.1.1.
- **Why:** consent is recorded only in the browser; DPDP needs a record per purpose.
- **Where:** a `core.consents` table, `Consent.tsx`.
- **How:** one row per purpose (conversation, voice, quality review, cohort, caste category, financial capacity, idea IP (August P-42.1)), with time and withdrawal. The rest of P-42 is covered elsewhere: private sessions send no idea text out (0004, built); idea fields are encrypted with 3.2.2; the data-use notice is 1.5.4.
- **What for:** lawful use (SYSTEM-DESIGN §5.4; constraint solutions §A.3).
- `3.2.1.1` Table and migration.
- `3.2.1.2` `Consent.tsx` writes to it.

#### 3.2.2 `[w]` Field encryption for sensitive columns
- **Waiting on:** 3.1.2, and before any real founder data.
- **Why:** caste category, financial capacity and idea fields are stored as plain columns.
- **How:** field-level encryption through an ORM type.
- `3.2.2.1` Encrypted column type and migration.

#### 3.2.3 `[w]` Access audit log
- **Waiting on:** 3.2.1.
- **Why:** reads of protected fields need a trail.
- **How:** append-only audit table.
- `3.2.3.1` Audit table and writes.

#### 3.2.4 `[w]` Erasure and retention
- **Waiting on:** 3.1.1 and D4, D12.
- **Why:** one erasure request must remove a founder's sessions, transcripts, documents and consents; old data must expire.
- **How:** delete by user across tables; a nightly job deletes sessions past retention, consents as long as the data they cover plus one year (SYSTEM-DESIGN §5.4), logs after 30 days.
- `3.2.4.1` Delete-all-for-user.
- `3.2.4.2` Nightly retention job.

#### 3.2.5 `[ ]` Protect the programme cohort endpoint
- **Why:** `/api/v1/cohort/programme` has no auth; anyone with session IDs can call it.
- **Where:** `routers/cohort.py`, `api/deps.py`, `frontend/src/pages/Cohort.tsx` (calls the endpoint without a token today).
- **How:** a programme-manager role on the token; until roles exist, require an authenticated user, and make the Cohort page sign in and send the token.
- **When:** now for the auth check; the role after 3.1.
- **What for:** consenting founders' aggregates stay with the programme.
- `3.2.5.1` Require auth, and send the token from the Cohort page.
- `3.2.5.2` Programme-manager role.

#### 3.2.6 `[w]` Legal review before a pilot
- **Waiting on:** owner. A one-time DPDP review and a named grievance officer (constraint solutions §A.3; feasibility survey P).

---

## P4 Founder tools beyond ideation

The October documents do not cover these screens. They stay because each attaches to code that
exists and needs nothing ruled out. Confirm their scope in D8.

### 4.1 Schemes

**Already built:** cited rule trees with reasons for every "no" (`schemes/seed.py`,
`rules.py`, `engine.py`), ranking with approval likelihood (August P-24), the funding catalogue of 46 entries
corrected against official sources, bank scheme rails, and the registration check gateway with
free format and checksum pre-filters (`verification/`; paid lookups stay dormant).

#### 4.1.1 `[ ]` One scheme source
- **Why:** `schemes/seed.py` rule trees and `schemes/data/funding_catalogue.json` describe overlapping schemes; catalogue eligibility is "not yet encoded as engine rules".
- **Where:** `schemes/`.
- **How:** encode each confirmed catalogue entry as a rule tree; show the criteria that are not encoded, verbatim, next to the result.
- **When:** now; each entry confirmed on its official page.
- **What for:** real, cited schemes everywhere (constraint solutions §B.2).
- `4.1.1.1` Encode catalogue entries as rules, one per commit.
- `4.1.1.2` Show unencoded criteria with each result.

#### 4.1.2 `[d]` One sector taxonomy (D5)
- **Why:** three vocabularies exist (`elicitation/slots.py` with 12 sectors, `ecosystem/taxonomy.py`, the StartupTN categories in the registry); a missing sector makes a question unanswerable.
- **Where:** one taxonomy module.
- **How:** pick the canonical list; map the others to it; generate the extractor's sector cues from it; test that every sector has a cue (the quality set shows the sector question asked even for tea, jasmine and knitwear).
- **When:** after D5; before 1.1.5.3.
- **What for:** one meaning of "sector" (August Req 2.7; rnd-elicitation §6.5).
- `4.1.2.1` Canonical module and mappings.
- `4.1.2.2` Generated cues and coverage test.

#### 4.1.3 `[ ]` Pre-revenue flags
- **Why:** pre-revenue founders are routed to schemes and investors that will not take them.
- **Where:** catalogue fields.
- **How:** a cited "accepts pre-revenue" flag per route.
- **When:** with 4.1.1.
- **What for:** correct routing (August P-28.3, P-28.5).
- `4.1.3.1` Flag and filter.

#### 4.1.4 `[w]` Application tracking
- **Waiting on:** 3.1.2.
- **Why:** founders juggle several applications.
- **How:** per-founder application records with statuses.
- `4.1.4.1` Records and statuses.

#### 4.1.5 `[w]` Scheme filters and the homepage eligibility check
- **Waiting on:** the owner's decision on the uncommitted frontend theme removal.
- `4.1.5.1` Filter by type and amount on the Schemes screen.
- `4.1.5.2` Four-field eligibility check on the home page using `/schemes/recommend` (nothing stored; August P-41.3).

### 4.2 Suppliers

**Already built:** bill-of-materials draft, real companies from the MCA directory, quote-based
CP-SAT order splitting, supplier scoring and pairing (`b2b/`).

#### 4.2.1 `[w]` The old `/b2b` screen stops using invented suppliers
- **Waiting on:** owner's decision on the uncommitted `B2B.tsx`.
- **Why:** `/b2b` still ranks the example suppliers in `b2b/seed.py`.
- **How:** use the directory and the founder's quotes, as `/suppliers` does.
- `4.2.1.1` Switch the screen and remove the seed from founder paths.

#### 4.2.2 `[ ]` Cited clusters for unmatched lines
- **Why:** a bill-of-materials line with no matching company gets no guidance.
- **Where:** `b2b/directory.py`.
- **How:** map the line to a cited Tamil Nadu industrial cluster or NIC code.
- **When:** after 4.1.2, so clusters map to the canonical sectors.
- **What for:** honest gap guidance (August Req 3.6).
- `4.2.2.1` Cited cluster mapping.

### 4.3 Funding

**Already built:** readiness on six dimensions, gap analysis, matching against the real Tamil Nadu
investors, the pipeline stage machine.

#### 4.3.1 `[ ]` Proxy traction in readiness
- **Why:** pre-revenue founders score zero on traction even with letters of intent or pilots.
- **Where:** `funding/readiness.py`.
- **How:** typed, self-declared evidence (LOI, pilot, waitlist) with a weight per type.
- **When:** now.
- **What for:** fair readiness (August P-28).
- `4.3.1.1` Evidence types and weights.
- `4.3.1.2` Tests.

#### 4.3.2 `[w]` Track progress on recommendations
- **Waiting on:** 3.1.2.
- `4.3.2.1` Mark a recommendation in progress or done, per founder.

### 4.4 News

**Already built:** allowlisted RSS pipeline with own summaries and links back (`news/pipeline.py`; August P-44).

#### 4.4.1 `[d]` What the news board shows offline (D9)
- **Why:** the offline corpus is synthetic (`news/fixtures.py`, labelled demo); live fetching is refused until each source's robots rules are checked.
- **Where:** `news/`, `routers/news.py`, `Intel.tsx`.
- **How:** per D9, either show only live allowlisted sources and say "not fetched" otherwise, or keep the labelled demo.
- **When:** after D9.
- **What for:** founders never mistake demo items for real news.
- `4.4.1.1` Apply D9.
- `4.4.1.2` `[w]` Verify each allowlisted source's robots rules (owner).

---

## P5 Quality, operations and cohort

### 5.1 Evaluation and tuning

**Already built:** the quality set of 10 offline ideas (`tests/eval`, `scripts/eval_report.py`),
dropped-sentence counts (0005).

#### 5.1.1 `[ ]` Keep the quality report current
- **Why:** `docs/eval/report.md` dates from 2026-10-10 and lacks a check the runner now has.
- **Where:** `scripts/eval_report.py`, `docs/eval/report.md`.
- **How:** regenerate it, and regenerate it in every pull request that changes the conversation.
- **When:** now, then ongoing.
- **What for:** status anyone can trust.
- `5.1.1.1` Regenerate.
- `5.1.1.2` CI check that the report matches the runner.

#### 5.1.2 `[ ]` Evaluate the model path too
- **Why:** the quality set covers only the offline path; meaning-level checks were left to evaluation (0005).
- **Where:** `tests/eval`.
- **How:** replay the 10 ideas through a free model (Ollama locally) with recorded answers; add meaning-level checks.
- **When:** after 1.5.3 for Gemini; Ollama now.
- **What for:** the model path meets the same bar.
- `5.1.2.1` Model-path replay.
- `5.1.2.2` Meaning-level checks.

#### 5.1.3 `[ ]` Tune the weights
- **Why:** the panel's vote weights and the question selector's constants are uncalibrated priors.
- **Where:** `agents/council/data/council_weights.json`, `elicitation/selector.py`.
- **How:** log slot order, questions asked, completion and corrections (no idea text); tune against the quality set and those logs.
- **When:** after 5.1.2.
- **What for:** shorter interviews and better verdicts (IDEATION Phase 4).
- `5.1.3.1` Anonymous interview statistics.
- `5.1.3.2` Tuning run and report.

#### 5.1.4 `[ ]` Property tests
- **Why:** `tests/property/` is empty although Hypothesis is installed; a scheme rule change can affect founders unseen.
- **Where:** `tests/property/`.
- **How:** generated founder profiles check rule soundness and completeness and the planner's 5-15 milestones; a replay shows who a rule change affects before merge, broken down by district, sector and category so a change that hurts one group shows up (P-38 fairness slices).
- **When:** after 4.1.2.
- **What for:** safe rule edits (August P-38).
- `5.1.4.1` Rule soundness and completeness properties.
- `5.1.4.2` Planner milestone-count property.
- `5.1.4.3` Rule-change replay in CI.

#### 5.1.5 `[ ]` Coverage threshold in CI
- **Why:** CI measures coverage but never fails on it.
- **Where:** `.github/workflows/ci.yml`.
- **How:** `--cov-fail-under` at today's level.
- **When:** now.
- **What for:** no silent drop in tested code (August design: 80% coverage target).
- `5.1.5.1` Add the threshold.

#### 5.1.6 `[ ]` Security tests
- **Why:** nothing tests injection, cross-site scripting or forged requests against the API.
- **Where:** `backend/tests/` (security), `core/middleware.py`.
- **How:** tests that send injection and script payloads to each input-taking route and check they are rejected or escaped; check cookie and CORS settings against forged requests.
- **When:** now.
- **What for:** no basic web vulnerabilities before a pilot (August tasks 5.4.1-5.4.3).
- `5.1.6.1` Injection and script-payload tests.
- `5.1.6.2` Forged-request and CORS checks.

### 5.2 Data checks in CI

#### 5.2.1 `[ ]` JSON schema for every reference data file
- **Why:** a malformed data file reaches founders.
- **Where:** schemas beside each class A file; `ci.yml`.
- **How:** CI validates each file against its schema.
- **When:** SYSTEM-DESIGN Phase 4.
- **What for:** correct reference data (§5.3).
- `5.2.1.1` Schemas.
- `5.2.1.2` CI step.

#### 5.2.2 `[ ]` Freshness gate
- **Why:** an open scheme unchecked for months may be closed.
- **Where:** scheme data, `ci.yml`.
- **How:** one date field name (`checked_on`) across files; CI fails when an open scheme is unchecked for 30 days.
- **When:** after 5.2.1.
- **What for:** truthful schemes (§5.3).
- `5.2.2.1` Unify the date field.
- `5.2.2.2` CI gate.

#### 5.2.3 `[ ]` Guard harvests that shrink
- **Why:** a broken scrape can wipe a dataset.
- **Where:** `scripts/check_*.py`, `build_domain_signals.py`.
- **How:** a result more than 20% smaller than the last is held for review, not written.
- **When:** weekly job.
- **What for:** data safety (§5.3, §9).
- `5.2.3.1` Shrink guard.
- `5.2.3.2` Runbook "a harvest returned suspiciously little".

#### 5.2.4 `[ ]` Migrations tested in CI
- **Why:** a broken migration is found only on someone's machine.
- **Where:** `ci.yml` with a PostgreSQL service.
- **How:** empty database, migrate up, down one, up again.
- **When:** now (CI has its own database; not blocked by local credentials).
- **What for:** safe schema changes (§5.2).
- `5.2.4.1` PostgreSQL service and the round trip.

### 5.3 Documentation

#### 5.3.1 `[ ]` Data dictionary
- **Why:** there is no record of each table and data file's owner, class, source and refresh.
- **Where:** `docs/data/`, generated from models and schemas where possible.
- **How:** a generator plus a CI check that every migration and data file has an entry, and that links between documents resolve.
- **When:** SYSTEM-DESIGN Phase 4.
- **What for:** documentation that matches the code (§6).
- `5.3.1.1` Generator and entries.
- `5.3.1.2` CI entry and link checks.

#### 5.3.2 `[ ]` Runbooks brought up to date
- **Why:** model-down covers only Anthropic; rotate-key misses the Gemini, EPO and Sarvam keys; the README says Redis is unused.
- **Where:** `docs/runbooks/`.
- **How:** rewrite each against the current code and config.
- **When:** now.
- **What for:** an operator can fix an outage from the runbook alone (SYSTEM-DESIGN §6.1).
- `5.3.2.1` Model-down: the Gemini then Ollama chain and the real log names.
- `5.3.2.2` Rotate-key: full key list.
- `5.3.2.3` Redis loss runbook; README corrected.
- `5.3.2.4` `[w]` Restore the database (waits on backups, which wait on a hosting decision).

#### 5.3.3 `[d]` Records and claims that match the code (D1)
- **Why:** scheme and investor eligibility use rules, not CP-SAT, but `PROJECT_SUMMARY.md` and the August spec claim "mathematically proven"; there is no decision record; some design documents use statuses outside draft, accepted or superseded; BACKLOG still describes the rejected browser voice and the old model adapter location.
- **Where:** `docs/decisions/`, `PROJECT_SUMMARY.md`, root design documents, `docs/BACKLOG.md`.
- **How:** edit each document to match the code; supersede, never rewrite, accepted decisions.
- **When:** 5.3.3.1 after D1; the rest now.
- **What for:** documents a reader can trust (SYSTEM-DESIGN §6.2; feasibility survey X).
- `5.3.3.1` Decision record for the eligibility engine (after D1).
- `5.3.3.2` Reword the "mathematically proven" claims.
- `5.3.3.3` Design document statuses use draft, accepted or superseded.
- `5.3.3.4` BACKLOG: remove browser-voice fix 1 and the stale text (superseded by 0009); free fix 3 is done; the "Pushing `feature/bank-loan-routing`" row is done (pushed; `origin/feature/bank-loan-routing` exists).
- `5.3.3.5` `docs/decisions/README.md` lists 0007 as superseded in part by 0010.

#### 5.3.4 `[ ]` API reference exported on each release
- **Why:** the API reference exists only at the running server's `/docs`.
- **Where:** `docs/api/`, a release step.
- **How:** export FastAPI's OpenAPI document on each release.
- **When:** at each release.
- **What for:** a reference that survives without a running server (SYSTEM-DESIGN §6.1; August task 5.7.1).
- `5.3.4.1` Export script and release step.

#### 5.3.5 `[ ]` Move the root design documents into `docs/`
- **Why:** design documents sit at the repo root while every new kind lives in `docs/`.
- **Where:** repo root to `docs/`.
- **How:** move all root design documents and fix links, in one pull request.
- **When:** last, in one separate change, so links break only once (§6.2).
- **What for:** one documentation home.
- `5.3.5.1` Move and fix links.

### 5.4 Monitoring

#### 5.4.1 `[ ]` Step timings
- **Why:** nothing measures whether the first sentence arrives within 1 second.
- **Where:** `core/middleware.py`, `agents/ideation.py`.
- **How:** record per-step durations; report median and p95.
- **When:** now.
- **What for:** visible latency (SYSTEM-DESIGN §7, §8).
- `5.4.1.1` Timings in logs.

#### 5.4.2 `[ ]` Cache hit rates and budgets
- **Why:** nobody can see whether caches work or how close a source is to its free daily limit.
- **Where:** `core/redis.py`, `research/sources.py`, `agents/ideation.py`.
- **How:** counters for hits and misses per cache layer; daily requests per source; tokens per session (already counted in `s.usage`).
- **When:** now.
- **What for:** spot budget trouble before founders do (SYSTEM-DESIGN §8).
- `5.4.2.1` Hit and miss counters per layer.
- `5.4.2.2` Budget use per source per day, tokens per session.

#### 5.4.3 `[ ]` Monitoring page
- **Why:** SYSTEM-DESIGN Phase 4 asks for one dashboard.
- **Where:** a backend endpoint and a frontend page.
- **How:** a page reading 5.4.1 and 5.4.2 (free; no paid monitoring).
- **When:** after 5.4.1 and 5.4.2.
- **What for:** one place to see latency, caches and budgets.
- `5.4.3.1` Dashboard.
- `5.4.3.2` `[w]` Alerts (waits on a hosting decision).

#### 5.4.4 `[ ]` Nightly job
- **Why:** cache purge, cache warming, retention deletes and cohort rebuild all need a nightly run.
- **Where:** one script (`scripts/nightly.py`) started by a scheduler on the machine where the app runs (the OS scheduler, or an in-process scheduler); it must see the app's `.cache/research`, PostgreSQL and Redis, which a GitHub Actions runner cannot. GitHub Actions stays for the weekly harvests that commit data.
- **How:** one scheduled run that calls each step; a failed step does not stop the others.
- **When:** lands together with 2.2.5; gains 2.2.6, 3.2.4.2 and 5.5.5.2 as they land.
- **What for:** housekeeping without manual work (SYSTEM-DESIGN §7).
- `5.4.4.1` Nightly script and its scheduler entry, running 2.2.5.

### 5.5 Cohort analysis

**Already built:** reference cohort from the TN Startup Map and MCA data; programme aggregates
(district, sector, stage, capital, novelty type, panel band, open gaps, progress) with groups of
at least 5, bands not rankings (IDEATION §4). Partly built: see 5.5.3.

#### 5.5.1 `[ ]` Consent control on the Talk page
- **Why:** consent is always false, so the programme view is always empty.
- **Where:** `Talk.tsx`, `agentClient.ts` (`share_with_programme`).
- **How:** a consent checkbox at session start.
- **When:** now.
- **What for:** programme aggregates from consenting founders (IDEATION §3.6 r6).
- `5.5.1.1` Checkbox and request field.

#### 5.5.2 `[ ]` Reference cohort from the session's own evidence
- **Why:** open projects, trial sponsors and funding route are not used.
- **Where:** `cohort/reference.py`.
- **How:** add the session scan's projects and trial sponsors, and the funding route, to the match.
- **When:** now.
- **What for:** "5 similar in Tamil Nadu, none past pilot" (IDEATION §4.1).
- `5.5.2.1` Evidence-fed matching.

#### 5.5.3 `[ ]` Programme aggregates the design asks for
- **Why:** the programme view lacks the most common blockers and risks, scheme fit and readiness bands.
- **Where:** `cohort/programme.py`, `Cohort.tsx`.
- **How:** add roadmap risks and blockers, scheme-fit bands and readiness bands to the aggregates, still folded below 5.
- **When:** now.
- **What for:** a programme manager sees where the batch is stuck (IDEATION §4.2).
- `5.5.3.1` Risks and blockers.
- `5.5.3.2` Scheme-fit and readiness bands.

#### 5.5.4 `[w]` Programme membership
- **Waiting on:** 3.1 and 3.2.1.
- `5.5.4.1` Who belongs to which batch, instead of pasted session IDs.

#### 5.5.5 `[w]` Session tables, analytics schema, nightly rebuild
- **Waiting on:** 2.1.1 and 2.1.4.
- Also covers the August analytics and impact dashboard (task 5.2): scheme, supplier and funding metrics come from these tables.
- `5.5.5.1` Split session documents into tables by migration.
- `5.5.5.2` `analytics` schema and nightly rebuild.

### 5.6 Reference data growth

#### 5.6.1 `[w]` Review the 190 draft registry cards
- **Waiting on:** a reviewer who knows the districts.

#### 5.6.2 `[w]` Research signals for batches 2 and 3
- **Waiting on:** the weekly job within OpenAlex's free budget, or a free OpenAlex key.

#### 5.6.3 `[w]` Registry batches 4 to 6
- **Waiting on:** 5.6.1.

#### 5.6.4 `[w]` Weekly jobs open pull requests
- **Waiting on:** the owner enabling "Allow GitHub Actions to create and approve pull requests".

### 5.7 Code cleanup

#### 5.7.1 `[d]` Remove code the current design does not use (D2, D6)
- **Why:** unused code misleads readers and the gap analysis.
- **Where:** the files listed below.
- **How:** delete each with its tests and references, one commit per item.
- **When:** each after its decision or dependency.
- **What for:** the code reads as what the product does.
- `5.7.1.1` `app/orchestrator/` and `/orchestrator/route` (after D2).
- `5.7.1.2` `services/llm.py` (no callers; models live in `agents/providers.py`).
- `5.7.1.3` `services/translation.py` (after D6).
- `5.7.1.4` `payment_mode` (shown on the old `/b2b` screen but never constrained; after 4.2.1).
- `5.7.1.5` Frontend `classifyTerrain` (never sent), with the terrain confirmation step in `Start.tsx` and the `terrain` fields in `journeyStore.ts`; do it with 1.1.5.2, which edits the same screen.
- `5.7.1.6` The unused `minio` service in `backend/docker-compose.yml` and its settings (object storage only if files are ever kept; D11).

---

## Owner decisions

| # | Decision | Sources that disagree | Recommendation |
|---|---|---|---|
| D1 | Scheme and investor eligibility: rules or CP-SAT | August spec and master document say CP-SAT; the code, Vanigam-Explained E2 and feasibility survey C say rules | Rules; write the decision record and fix the claims (5.3.3) |
| D2 | `app/orchestrator` and `/orchestrator/route` | August task 1.8 wants an intent router; decisions 0001 and 0002 make the agent the conversation; nothing calls the route | Remove (5.7.1.1); the parked work is on `wip/1.8-orchestrator` |
| D3 | `/ideate` and its placeholder roadmap | Gap analysis D8 fixes `/ideate`; the October design centres `/talk` | One roadmap from the planner (1.4.1) |
| D4 | Session lifetime, and keeping a saved idea | `agents/store.py`: 6 h idle; SYSTEM-DESIGN §5.4: 90 days, longer "only if the founder saves the idea"; rnd-elicitation: 30 days | 6 h for the Redis copy, 90 days in PostgreSQL; a saved idea is kept until the founder deletes it (needs 3.1) |
| D5 | Canonical sector list | elicitation enum (12), ecosystem taxonomy, StartupTN categories | StartupTN categories, others mapped |
| D6 | `services/translation.py` (paid Sarvam provider, no caller) | August translation plan versus decision 0009 | Remove; keep the glossary if a free path uses it |
| D7 | Offline Tanglish | ideation-redesign makes Tanglish first-class; offline extraction is English with a few Tamil cues; 0009 relies on a model | Decide whether a free offline floor is in scope; no task until decided |
| D8 | Scope of schemes, suppliers, funding and news screens | October documents cover only ideation and the platform | Keep P4 as written |
| D9 | Synthetic news fixtures | "No invented data" versus a labelled demo | Live allowlisted sources only; "not fetched" otherwise |
| D10 | Scraping government pages | constraint solutions §B suggests it; feasibility survey R says do not | Keep hand curation and the weekly checks of organisations' own sites; no task until decided |
| D11 | Document upload and OCR | SYSTEM-DESIGN class E lists documents; the August document/OCR requirements fail on cost and law (see Dropped) | Out of scope until a free OCR path and a legal reason exist; no task until decided |
| D12 | Soft delete versus erasure | August Req 6.1 wants soft deletes; SYSTEM-DESIGN §3.2, §5.4 want erasure on request | Erasure |
| D13 | Work on branch `phase/1` | Redis caches for translation and embeddings were built and reviewed there, but no current source asks for them (translation has no caller, see D6; offline embeddings are cheaper to compute than to fetch); its `tasks.md` audit targets the old list | Do not merge; delete `phase/1` (see Dropped) |

## Waiting on the owner

| Action | Unblocks |
|---|---|
| Correct PostgreSQL credentials in `backend/.env`, or Docker Desktop running | 2.1.1, then 2.3.1, P3, 5.5.4, 5.5.5 |
| `GEMINI_API_KEY` | 1.5.3, 5.1.2 (Gemini) |
| Free EPO OPS registration | 1.2.7 |
| A free OpenAlex key | 2.2.6, 5.6.2 |
| Checking each news source's robots rules | 4.4.1.2 |
| A Tamil and a Hindi reviewer | 1.5.2 |
| Decision on the uncommitted frontend theme removal | 1.5.5, 4.1.5 and all screen styling |
| Decision on the uncommitted `B2B.tsx` | 4.2.1 |
| A district-aware registry reviewer | 5.6.1, 5.6.3 |
| GitHub setting for Actions pull requests | 5.6.4 |
| A hosting decision | backups, restore runbook (5.3.2.4), alerts (5.4.3.2), TLS |
| DPDP legal review | 3.2.6, any pilot |
| Decisions D1-D13 | the `[d]` tasks |

## Dropped, and why

Every item below comes from the August spec, the task list or the gap analysis and failed the
five-finger rule under the current constraints.

| Dropped | Source | Reason |
|---|---|---|
| LangGraph orchestrator, intent classifier, context stack, swarm supervisors | Req 5.1-5.2; design; tasks 1.8, 1.3.4, 1.7.5, 3.4, 4.5 | The agent is the conversation; code decides (0001, 0002) |
| CP-SAT for scheme and investor eligibility; unified CP-SAT boundary with IIS | Req 1.4, 2.4, 4.4, 5.3; tasks 2.3, 4.4 | Eligibility is rule evaluation (D1); CP-SAT kept where it earns its place: planner, question selector, order splitting |
| IndicBERT, IndicTrans2, BLEU/chrF++/COMET gates, BGE-M3, IndicLID | Req 1.5, 5.5; design; constraint solutions §E; tasks 1.5.1, 1.6.1 | Paid or GPU; replaced by free models and pre-translated sentences (0009) |
| Translate-before-processing | Req 1.2 AC1; rnd-elicitation §6.5 | The model works in the founder's language (0009) |
| Feasibility score 0-100 | Req 1.2 AC5-6; rnd-elicitation §7.6 | Replaced by the novelty statement and panel bands (0006) |
| Aadhaar OCR, cloud OCR, document authenticity, encrypted S3 documents | Req 1.1 AC7-8, 2.2; tasks 1.4 | Aadhaar OCR by a private platform is unlawful; cloud OCR is paid (D11) |
| Paid KYC aggregators, DigiLocker, live MCA21/DPIIT/GST lookups, "Verified" unlocks | Req 2.1; constraint solutions §A | Paid or partner-gated; the free gateway and pre-filters stay |
| Scheme and investor databases in PostgreSQL, versioning tables, admin interfaces | Req 2.3, 4.3, 6.2; tasks 2.2, 4.1 | Reference data lives in Git with reviewed commits (SYSTEM-DESIGN §2, §10) |
| Applicant counts, success rates, investor portfolio values, exits | Req 2.3, 4.3 | Not published; no invented data |
| Embedding-weighted ranking and pgvector similarity tables | Req 2.5, 1.6; design | Offline embeddings are hashes; no real model on the free path |
| Offering-side B2B profiles, bipartite graph store, trust from feedback, collaboration lifecycle, barter, joint co-application, B2B traction | Req 3.1-3.5; tasks 3.1, 3.5; P-25, P-32, P-43 | Needs supplier liquidity on the platform that does not exist |
| GNN / LightGCN, learning ladder, sector-adaptive weights from outcomes, approval-outcome recalibration | tasks 5.1; P-36; P-24.4 | No outcome data. Curated per-sector weight presets (P-36.1-3) fold into weight tuning (5.1.3), which tunes against the quality set |
| "Find startups like mine" among platform founders, with discoverability consent | tasks 1.13; P-41.1-2 | No population of platform founders to match against; the reference cohort over public TN startup data covers "who else" (IDEATION §4.1, already built) |
| Notifications: reminders, alerts, digests, SMS, IVR, deadline tracker | Req 2.6, 4.5; P-26, P-39, P-40.1, P-40.3 | No notification channel; SMS and IVR are paid; deadlines are not reliably published. The document-readiness checker (P-40.2) is covered for registrations by the journey engine (already built); document checks wait on D11 |
| PWA service worker and 2G mode | P-39 | Offline need is met by deterministic server paths (0002); not in the October design |
| Review queue and admin override, LLM extraction crawlers, curator SLA dashboard | P-37, P-46; constraint solutions §B | Curation is by reviewed Git commits; weekly scripts open pull requests |
| Roadmap re-versioning on scheme change, QR living PDF and share tokens | P-30, P-31 | New event subsystem and public hosting; not in the October design |
| Portfolio conflict checks, pathway sequencer, what-if simulator, competitor intelligence | P-27, P-35, P-47, P-40d | New datasets and models; the reference cohort covers "who else" |
| Terrain modes and template families | P-29 | Superseded by domain packs and the registry |
| Stat tiles, gamified tiers, live demo widget styling, all visual, art, monument and motion references | P-41.4-5; `.kiro` visual references | Theme stripped 2026-10-02; styling waits on the owner |
| Kubernetes, blue-green deploys, PagerDuty, ELK, Langfuse, external pen test, Locust load targets | tasks 5.5, 5.6; master document §2.5, §7.4 | Paid hosting or premature; SYSTEM-DESIGN §8-9 cover monitoring and failure |
| Logging every user message | Req 5.1 AC8 | Logs hold no idea text (SYSTEM-DESIGN §2 rule 3) |
| 30-minute session timeout, `elicitation_sessions` tables, 202 polling state | tasks 1.8.6; rnd-elicitation §5 | Sessions as one JSON document, streaming and notices (0003, 0010) |
| Semantic response cache, batch API, model cascades and routers | constraint solutions §C | Paid; provider order is fixed by 0009 |
| Logging and aggregation stacks; S3 setup | tasks 1.1.5, 1.1.4 | Stdout JSON logs suffice; object storage only if files are ever kept (SYSTEM-DESIGN Phase 3) |
| Team, budget and per-turn cost plans | master document §9, §11 | Single owner, zero budget |
| "Spec baseline frozen" | traceability matrix §5 | This file is the trace now |
| Redis caches for translation and embeddings (built on `phase/1`) | tasks 1.5.5, 1.6.4 | Translation has no caller (D6); offline embeddings are hashes, cheaper than a cache round trip; Cohere is paid (D13) |
| User-satisfaction thumbs feedback | tasks 5.3.4 | Not in the October design; quality is measured by the quality set (5.1) |
| Developer and user guides, FAQ, video | tasks 5.7.2, 5.7.4, 5.7.5, 5.7.7 | Not one of the documentation kinds in SYSTEM-DESIGN §6.1; the API reference is kept (5.3.4). Architecture documentation (task 5.7.3) is the design documents, already written and moved by 5.3.5; the troubleshooting guide (task 5.7.6) is the runbooks (5.3.2) |
| Problem-statements live board | tasks 2.12; P-33 | Needs a curated bank of challenge entries and extraction curation that the October design does not have; the catalogue's `demand` entries feed the experience path instead (1.1.5.3) |
| Encryption at rest and TLS as build tasks | tasks 5.4.4-5.4.5 | Field encryption is 3.2.2; disk encryption and TLS belong to hosting (waiting on a hosting decision) |
