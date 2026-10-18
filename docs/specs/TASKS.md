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

**Arena findings (2026-10-17):** subtasks that carry an `R` number come from the logic arena run ([ARENA-FLAGS.md](ARENA-FLAGS.md)): evidence, the free stack options weighed, the recommendation and what was ruled out are in its details files. They are listed under the task they belong to, heaviest first.

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
- `1.1.1.3` `[ ]` [R019](arena/details-p1.md#r019) (weight 84) Session-start profile values enter unvalidated at 0.95 confidence. Fix: Typed Pydantic ProfileIn + answers.validate per slot.

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
- `1.1.2.5` `[ ]` [R005](arena/details-p1.md#r005) (weight 94) Confirmation step ignores negation: 'not right'/'Salem not Madurai' read as confirm/value. Fix: Always observe the reply, then confirm only if nothing changed.
- `1.1.2.6` `[ ]` [R025](arena/details-p1.md#r025) (weight 84) Later extraction overwrites founder's direct answer or chosen lever (no provenance). Fix: Source rank before confidence: ANSWER and PROFILE are never replaced by EXTRACTED or model notes; a disagreeing extraction is kept as a rival.
- `1.1.2.7` `[ ]` [R051](arena/details-p1.md#r051) (weight 84) Skipped and dropped required slots vanish from the 'I still don't know' sentence. Fix: Two sentences: 'you skipped X; I will assume Y'.
- `1.1.2.8` `[ ]` [R154](arena/details-p1.md#r154) (weight 67) Restatement omits facts the roadmap uses (team size, experience, horizon). Fix: Restate every non-text slot whose consumers include 'roadmap' or 'scheme' and whose source is not ANSWER, in one 'I assumed:' sentence.

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
- `1.1.3.5` `[ ]` [R007](arena/details-p1.md#r007) (weight 94) note_fact stores untyped values in typed slots; planner crashes on them. Fix: Per-slot Pydantic validators in put(): coerce to the slot's Enum or int, reject otherwise, and return a typed result.
- `1.1.3.6` `[ ]` [R009](arena/details-p1.md#r009) (weight 90) Required slots exceed the 7-question budget, so ranking inputs are never asked. Fix: Separate questions_asked counter on the session.
- `1.1.3.7` `[ ]` [R053](arena/details-p1.md#r053) (weight 84) note_fact answers 'recorded' when put() drops the value, so wrong extractions stick. Fix: put() returns an outcome (stored / kept_existing / conflict) and records rivals; a conflict caps confidence below TAU_FILL.
- `1.1.3.8` `[ ]` [R070](arena/details-p1.md#r070) (weight 78) Stage answers ignore negation: 'no customers yet' is stored as revenue. Fix: Negation window rule.
- `1.1.3.9` `[ ]` [R063](arena/details-p1.md#r063) (weight 78) Mid-conversation corrections never stick; district picked by name length, not position. Fix: Correction cue -> treat as ANSWER.
- `1.1.3.10` `[ ]` [R099](arena/details-p1.md#r099) (weight 74) No town-to-district gazetteer: 'Pollachi' is not recognised, so district is re-asked. Fix: India Post all-India pincode directory (data.gov.in).
- `1.1.3.11` `[ ]` [R113](arena/details-p1.md#r113) (weight 73) The 'five-finger' stop rule checks four fingers: WHY has no required slot. Fix: WHY satisfied by any of why_now / differentiation / motivation, including extraction.
- `1.1.3.12` `[ ]` [R119](arena/details-p1.md#r119) (weight 70) CP-SAT solved twice per turn yet never differs from greedy at default settings. Fix: Greedy with an explicit required-first filter; CP-SAT only when a budget binds.
- `1.1.3.13` `[ ]` [R155](arena/details-p1.md#r155) (weight 67) Selector values slots by static consumer count, not by which result a gap blocks. Fix: Dynamic value term: count of downstream results (schemes, roadmap gates) whose evaluation is 'unknown' only because of this slot.
- `1.1.3.14` `[ ]` [R157](arena/details-p1.md#r157) (weight 64) Two 'known' thresholds: 0.5 counts a slot filled, 0.6 still asks it. Fix: Three bands: known / confirm / unknown.

#### 1.1.4 `[ ]` Safe on a 2G connection
- **Why:** a replayed answer after a dropped response is consumed twice; a conflict shows a raw error; a resumed session has no re-orientation.
- **Where:** `routers/ideation.py` (`agent_turn`), `Talk.tsx`, `agents/ideation.py` (`snapshot`).
- **How:** optional `client_turn_id` returns the same response on replay; the Talk page offers reload on 409; a resume after a long gap repeats the pending question first.
- **When:** now.
- **What for:** conversations survive bad networks (rnd-elicitation §5.4; decision 0003).
- `1.1.4.1` `client_turn_id` idempotency.
- `1.1.4.2` 409 handling in the Talk page.
- `1.1.4.3` Resume preamble that repeats the pending question without charging the budget.
- `1.1.4.4` `[ ]` [R038](arena/details-p1.md#r038) (weight 84) Idempotency is planned on agent_turn, but the Talk page only uses the stream. Fix: Keep last_turn {client_turn_id, done payload, sentences} in the session document.
- `1.1.4.5` `[ ]` [R076](arena/details-p1.md#r076) (weight 77) A stream cut before 'done' is treated as a finished turn. Fix: Done-sentinel check plus automatic retry with the same client_turn_id.
- `1.1.4.6` `[ ]` [R144](arena/details-p1.md#r144) (weight 68) Speaking twice during a slow turn silently drops the first utterance. Fix: Concatenate queued utterances into one next turn.
- `1.1.4.7` `[ ]` [R143](arena/details-p1.md#r143) (weight 68) Results that finish while offline are missing on reconnect and on resume. Fix: Replay the latest results on subscribe, and include them in the snapshot.
- `1.1.4.8` `[ ]` [R159](arena/details-p1.md#r159) (weight 62) A stream conflict arrives as 200 + error after the reply was spoken and shown. Fix: Typed SSE error events with a code field.
- `1.1.4.9` `[ ]` [R176](arena/details-p1.md#r176) (weight 61) Snapshot has no 'pending action' contract for choices, only pending_slot. Fix: Typed pending-action object in the session document.

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
- `1.1.5.6` `[ ]` [R048](arena/details-p1.md#r048) (weight 84) Ranking data has nothing to match experience slots to and no per-card citation. Fix: Add skills_used/assets_used + sources to the card schema; exclude draft cards.
- `1.1.5.7` `[ ]` [R066](arena/details-p1.md#r066) (weight 78) No state between confirm and roadmap for choosing an opportunity card. Fix: Add a CHOOSING state with a choose action.
- `1.1.5.8` `[ ]` [R089](arena/details-p1.md#r089) (weight 74) Experience questions are idea-worded and ask money before skills. Fix: Per-mode question text on Slot (question_by_mode).
- `1.1.5.9` `[ ]` [R118](arena/details-p1.md#r118) (weight 71) Experience mode runs prior-art and novelty on the founder's self-description. Fix: Gate research on mode and on problem/solution being filled.
- `1.1.5.10` `[ ]` [R121](arena/details-p1.md#r121) (weight 68) Entry-mode/subtype vocabularies mismatch with no contract onto server slots. Fix: Typed enums on AgentStartIn plus one mapping table (subtype to registered, entity and a stage floor; frontend mode to EntryMode with a domain pre-fill).

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
- `1.1.7.2` `[ ]` [R107](arena/details-p1.md#r107) (weight 74) Talk page discards the only delete handle while the database row survives. Fix: Keep the ID on failure; on a 404 'expired' answer offer 'delete it' alongside 'start fresh'.
- `1.1.7.3` `[ ]` [R114](arena/details-p2.md#r114) (weight 72) Redis copy is written without a version guard: a deleted session can come back. Fix: Lua compare-and-set put plus a tombstone.
- `1.1.7.4` `[ ]` [R173](arena/details-p1.md#r173) (weight 61) Results outlive their conversation; a running turn re-creates them after delete. Fix: Delete takes the session's turn lock, plus a 'forgotten' tombstone that board.start and results.put refuse.

#### 1.1.8 `[x]` One stage vocabulary and whole-word cues
- **Why:** stage words differ between modules (revenue founders score zero) and keyword cues match inside words ('app' in Tiruchirappalli).
- **Where:** `elicitation/extract.py`, `elicitation/slots.py`, `funding/`, `ecosystem/`.
- **How:** one Stage enum with explicit mappings and a coverage test; cues compiled as word-boundary patterns. Sector cues follow D5 later.
- **When:** now; the sector list itself waits on D5 (4.1.2).
- **What for:** facts read correctly from what founders say.
- `1.1.8.1` `[x]` [R008](arena/details-p4.md#r008) (weight 94) Stage words differ across modules: revenue founders score 0 and match no investor. Fix: Canonical Stage enum with explicit mappings and a coverage test.
- `1.1.8.2` `[x]` [R027](arena/details-p4.md#r027) (weight 84) Sector/extractor keyword cues match bare substrings inside words. Fix: Word-boundary regex cues compiled from the canonical module.

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
- `1.2.1.8` `[ ]` [R023](arena/details-p1.md#r023) (weight 84) Failed local-startup lookup reported as 'no Tamil Nadu startup does this'. Fix: Scoped wording plus a 'local' coverage row.
- `1.2.1.9` `[ ]` [R045](arena/details-p2.md#r045) (weight 84) One source's network error fails the whole evidence scan, not just that source. Fix: Catch httpx.TransportError in _get_json and return a status.
- `1.2.1.10` `[ ]` [R030](arena/details-p1.md#r030) (weight 84) 'Combinations are well studied' is said when no combination was counted. Fix: Coverage-aware statement.
- `1.2.1.11` `[ ]` [R035](arena/details-p1.md#r035) (weight 84) Clinical gate covers questions but not categories; tea idea weighted as a medical device. Fix: Apply the clinical gate to categories and make idea_type use founder slots first, paper categories only as a fallback.
- `1.2.1.12` `[ ]` [R093](arena/details-p1.md#r093) (weight 74) Generic words from registry prose take query slots ('banana small chips'). Fix: Document-frequency filter over the registry.

#### 1.2.2 `[ ]` Levers worded for the founder's domain
- **Why:** the localise lever says "local hospital or market routines" for banana chips and t-shirts.
- **Where:** `research/novelty.py` (`_levers`).
- **How:** word each lever from the matched domain and sector.
- **When:** now.
- **What for:** relevant advice (IDEATION §3.6 r4).
- `1.2.2.1` Domain-aware lever text.
- `1.2.2.2` Test across three sectors.
- `1.2.2.3` `[ ]` [R044](arena/details-p1.md#r044) (weight 84) Novelty and planner match domains differently; banana chips loses its cost lever. Fix: One domain resolver (registry.detect_domain) whose result is stored on the session and passed to scan, novelty, council and planner.
- `1.2.2.4` `[ ]` [R139](arena/details-p1.md#r139) (weight 68) Novelty's medical 'regulatory route' lever is 1.3.3's twin, missing from its scope. Fix: One shared is_health_product(idea, scan, slots) requiring a device or clinical signal, used by novelty and council.
- `1.2.2.5` `[ ]` [R190](arena/details-p1.md#r190) (weight 57) Lever text is fixed at search time; rewording by sector would force a new search. Fix: Return structured levers (kind, numbers, pair) from novelty; render wording at narration from session slots with per-sector phrase tables.

#### 1.2.3 `[ ]` Results tied to the idea version
- **Why:** research runs once per conversation and is never re-run when the idea changes, so an old verdict can be spoken (decision 0001 requires the opposite).
- **Where:** `agents/jobs.py`, `agents/results.py`, `agents/ideation.py` (`_absorb`).
- **How:** key results by `idea_version` instead of `LATEST`; when the core slots change, start a new research job and discard results for the old version.
- **When:** before 1.2.4.
- **What for:** evidence that matches the idea being discussed.
- `1.2.3.1` Key results by idea version.
- `1.2.3.2` Re-run research when the version changes.
- `1.2.3.3` Test: a stale result is never narrated.
- `1.2.3.4` `[ ]` [R014](arena/details-p1.md#r014) (weight 90) idea_version changes on almost every early answer, so 're-run on change' over-fires. Fix: Research key = hash of the research inputs (public terms + beneficiary).
- `1.2.3.5` `[ ]` [R033](arena/details-p1.md#r033) (weight 84) Any long answer to another question overwrites 'problem' with that answer. Fix: Suppress the positional 'problem' guess when the utterance answers a slot.
- `1.2.3.6` `[ ]` [R040](arena/details-p1.md#r040) (weight 84) Jobs are keyed by session and kind: an old version's job is reused or blocks the new. Fix: Key jobs by (session, version, kind) and tag payloads with their version.
- `1.2.3.7` `[ ]` [R158](arena/details-p1.md#r158) (weight 63) Research job runs its source calls in serial waves. Fix: asyncio.gather the independent calls.
- `1.2.3.8` `[ ]` [R171](arena/details-p1.md#r171) (weight 61) No rule for results produced before any version exists (idea_version None). Fix: Derive the key from research inputs, never None.

#### 1.2.4 `[ ]` The founder chooses a lever, and it becomes a new idea version
- **Why:** levers are listed read-only; the idea cannot evolve inside the conversation.
- **Where:** `routers/ideation.py`, `agents/ideation.py`, `Talk.tsx`.
- **How:** a choose-lever action updates the idea slots, bumps `idea_version` and re-runs research (1.2.3).
- **When:** after 1.2.3 and 1.3.1.
- **What for:** an iterated idea with its own evidence (IDEATION §2.3).
- `1.2.4.1` API action.
- `1.2.4.2` Talk page control.
- `1.2.4.3` Test of the version bump and re-run.
- `1.2.4.4` `[ ]` [R042](arena/details-p1.md#r042) (weight 84) Levers carry no slot change, so most choices leave idea_version unchanged. Fix: Structured lever patch + chosen-lever ids in the version hash.
- `1.2.4.5` `[ ]` [R065](arena/details-p1.md#r065) (weight 78) Narration keys are not version-scoped: a new version's verdict is never spoken. Fix: Prefix narrated keys with idea_version and key levers by stable id.
- `1.2.4.6` `[ ]` [R116](arena/details-p1.md#r116) (weight 71) A lever choice after the roadmap leaves roadmap, panel and state on the old version. Fix: Tag every derived artefact with its idea_version and drop mismatches.
- `1.2.4.7` `[ ]` [R126](arena/details-p1.md#r126) (weight 68) A spoken choice ('the second one') is not understood; only a button is planned. Fix: Deterministic ordinal and keyword matcher over the pending options.

#### 1.2.5 `[ ]` Scan discussion points become questions
- **Why:** for ideas outside the fixed questions, the scan's points are read out but never asked.
- **Where:** `agents/ideation.py`, `elicitation/engine.py` (`add_dynamic`).
- **How:** feed the best scan point into the dynamic questions (at most 3, shared with the panel).
- **When:** after 1.2.1.1.
- **What for:** questions that fit the domain (decision 0002 consequence).
- `1.2.5.1` Feed one scan point to `add_dynamic`.
- `1.2.5.2` Test.
- `1.2.5.3` `[ ]` [R010](arena/details-p1.md#r010) (weight 90) Dynamic questions are asked before required slots and use up the 7-question budget. Fix: Make dynamic questions selector candidates: ENRICHING class, burden 3 (text), allowed only after required coverage, with a reserved quota (e.g. at most 2 of Q_MAX).
- `1.2.5.4` `[ ]` [R105](arena/details-p1.md#r105) (weight 74) Shared cap of 3 is first-come: scan points shut out the review panel's question. Fix: Per-source quota: scan at most 1 (per 1.2.5.1), panel at most 2; a higher-priority arrival replaces an unasked lower one.
- `1.2.5.5` `[ ]` [R086](arena/details-p1.md#r086) (weight 74) Answers to dynamic questions are stored but never used, restated or labelled. Fix: Bind each scan or panel question to a consumer: an existing slot, a named risk or gate it resolves, or a free-text 'founder notes' list passed to the panel and shown in the restatement.

#### 1.2.6 `[ ]` Grow the public vocabulary from weak searches
- **Why:** words like "dryer" and "copra" are not in the lexicon, so searches lose recall.
- **Where:** `research/terms.py`, logs.
- **How:** log, by public term and count only (no founder text), searches that had few or no safe terms; a reviewer adds terms by commit.
- **When:** ongoing.
- **What for:** better recall without leaking ideas (decision 0004 consequence).
- `1.2.6.1` Weak-search log event with no idea text.
- `1.2.6.2` Review step in the runbook.
- `1.2.6.3` `[ ]` [R016](arena/details-p1.md#r016) (weight 88) scrub() lets brand-name variants leave: any model word the founder didn't say verbatim. Fix: Allowlist plus a public technical-term list (OpenAlex topics/keywords dump).

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
- `1.3.1.3` `[ ]` [R041](arena/details-p1.md#r041) (weight 84) Levers are tracked by list position, so reranking or a new version skips them. Fix: Stable lever ids (hash of kind and text) scoped by idea_version: narrated keys become 'lever:{version}:{id}' and 'statement:{version}'.
- `1.3.1.4` `[ ]` [R056](arena/details-p1.md#r056) (weight 80) Offline panel question is always the customer seat's, repeating the beneficiary question. Fix: Tag each seat question with the slot it duplicates and skip it when filled.
- `1.3.1.5` `[ ]` [R068](arena/details-p1.md#r068) (weight 78) Panel gives a verdict ('serious concerns') before any evidence exists. Fix: Gate the panel on finished research.
- `1.3.1.6` `[ ]` [R106](arena/details-p1.md#r106) (weight 74) Synthesis quotes a seat's first claim whatever criterion it was about. Fix: Criterion field on each claim, validated against CRITERIA.
- `1.3.1.7` `[ ]` [R110](arena/details-p1.md#r110) (weight 74) The panel sees only the first 4 levers, and their order is fixed by kind. Fix: Pass every lever to the panel with stable ids; seats score each; the vote orders them; the narrator speaks the top 3 of that order.
- `1.3.1.8` `[ ]` [R156](arena/details-p1.md#r156) (weight 64) 'No technical skill' weight bump fires for a Python developer and for unknown skills. Fix: Three-state rule: known technical / known non-technical / unknown (no bump).
- `1.3.1.9` `[ ]` [R175](arena/details-p1.md#r175) (weight 61) Seven separate model calls per panel run; every seat sees the whole pack anyway. Fix: One call returning all seven opinions as a JSON array.

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
- `1.4.1.4` `[ ]` [R085](arena/details-p1.md#r085) (weight 74) A text-only planner call silently drops slot-gated milestones; Ideate and Talk still differ. Fix: Ideate shows the session's stored planner roadmap (by session ID), and the planner marks milestones whose condition is unknown.

#### 1.4.2 `[ ]` Milestone tracker on the planner roadmap
- **Why:** the tracker works only on the old roadmap, in the browser.
- **Where:** roadmap screen; server-side storage later (3.1.3).
- **How:** three states per planner milestone (not started, in progress, done).
- **When:** after 1.4.1; server-side after 3.1.
- **What for:** a roadmap that moves (August P-31).
- `1.4.2.1` Tracker on planner milestones.
- `1.4.2.2` `[ ]` [R072](arena/details-p1.md#r072) (weight 78) The planner roadmap lives only in a session that expires in 6 h; nothing to track against. Fix: Persist a roadmap snapshot (plan JSON + idea_version + statuses) on the founder when they confirm the plan.
- `1.4.2.3` `[ ]` [R147](arena/details-p1.md#r147) (weight 68) Tracker keys by bare milestone ID; packs reuse IDs with different meanings. Fix: Key status by (idea_version, pack ID, milestone ID) and reconcile on rebuild, carrying over only when the title or template hash matches.
- `1.4.2.4` `[ ]` [R177](arena/details-p1.md#r177) (weight 61) Tracker status ignores depends_on and the critical path; programme progress cannot see it. Fix: Server function recomputes remaining critical path and months from statuses; the UI warns on done-before-dependencies.

#### 1.4.3 `[ ]` One fact store feeds the roadmap and the schemes
- **Why:** `/schemes/recommend` takes a separate profile, so the founder can be asked the same thing twice.
- **Where:** `agents/tools.py` (`support_for`), `schemes/engine.py`.
- **How:** project the session's slots onto the scheme profile.
- **When:** now.
- **What for:** consistency (ideation-redesign §4.2.2).
- `1.4.3.1` Slot-to-profile projection.
- `1.4.3.2` Test.
- `1.4.3.3` `[ ]` [R026](arena/details-p1.md#r026) (weight 84) No single typed scheme profile: seed rule paths and catalogue inputs disagree. Fix: Pydantic SchemeProfile with Literal enums and validators (state normalised, stage enum).
- `1.4.3.4` `[ ]` [R031](arena/details-p1.md#r031) (weight 84) /talk's support_for picks schemes from the domain card, never the founder's facts. Fix: Registry routes as a relevance shortlist, then the engine (three-valued) decides eligibility on projected FounderFacts.

#### 1.4.4 `[ ]` Planner fixes that do not wait on D3
- **Why:** the planner roadmap has faults whichever screen shows it: grants come after customers, closed schemes appear, confidence is fixed, and the conversation stalls after the roadmap.
- **Where:** `planner/`, `schemes/annotate.py`, `agents/ideation.py`.
- **How:** stage-specific funding milestones, live scheme status, confidence from slot coverage, and a roadmap walk-through state.
- **When:** now; 1.4.1 (one roadmap path) still waits on D3.
- **What for:** a roadmap that is right and that the founder can talk through.
- `1.4.4.1` `[ ]` [R004](arena/details-p1.md#r004) (weight 100) After the roadmap, the offline conversation repeats one line forever and never revises. Fix: Deterministic roadmap walk-through state.
- `1.4.4.2` `[ ]` [R046](arena/details-p1.md#r046) (weight 84) Planner puts 'Apply for seed grants' after pilot and customers; prototype grants come too late. Fix: Split c_grant into stage-specific funding milestones (c_seed_grant before prototype, c_growth_funding after pilot) and annotate schemes onto them by target stage.
- `1.4.4.3` `[ ]` [R049](arena/details-p1.md#r049) (weight 84) Scheme annotation ignores live status; it places closed SISFS on milestones. Fix: Annotate from registry.schemes_for routes with catalogue status: closed excluded, between_calls shown as 'next call expected', revamping labelled.
- `1.4.4.4` `[ ]` [R055](arena/details-p1.md#r055) (weight 80) 'I'll widen the estimates' is never true: roadmap confidence is fixed at 0.8. Fix: Confidence from slot coverage.

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
- `1.5.1.4` `[ ]` [R050](arena/details-p1.md#r050) (weight 84) Session language is never set from typed Tamil or Hindi, so 1.5.1's switch never fires. Fix: Unicode-script detection on the server.
- `1.5.1.5` `[ ]` [R101](arena/details-p1.md#r101) (weight 74) Only 52% of offline sentences are translated; one language tag per reply mislabels the rest. Fix: Language on each sentence event plus a coverage report.
- `1.5.1.6` `[ ]` [R188](arena/details-p1.md#r188) (weight 58) Translated sentences count as model rewording: provider and 'model' set with no call. Fix: Separate 'translated' and 'reworded' counts; a 'fixed-translation' model label.

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
- `1.5.4.2` `[ ]` [R015](arena/details-p1.md#r015) (weight 88) Private mode still sends the conversation/idea to Gemini (and TTS/panel providers). Fix: Private mode uses a local-only chain (Ollama, then templates; recordings for voice).
- `1.5.4.3` `[ ]` [R043](arena/details-p1.md#r043) (weight 84) Notice keyed to 'active provider' can only appear after text reached Google. Fix: Decide from configuration at session start: if any Google path is configured, show a versioned notice and record agreement before the first turn.
- `1.5.4.4` `[ ]` [R151](arena/details-p1.md#r151) (weight 67) Browser speech recognition is a Google path the notice rule ignores. Fix: Include browser recognition in the same versioned notice, with typing as the path that sends nothing to Google.

#### 1.5.5 `[w]` Low-literacy design of the Talk page
- **Waiting on:** the owner's decision on the uncommitted frontend theme removal.
- **Why:** voice-first, plain-language use is the product's differentiator for low-literacy founders (feasibility survey U; August task 2.7.5).
- **How:** large controls, icons with spoken labels, no text-only steps, on the Talk page.
- `1.5.5.1` Low-literacy pass on the Talk page.

#### 1.5.6 `[ ]` Free voice first, and no personal audio kept
- **Why:** Gemini voice is tried before the free recordings, and the voice cache keeps audio of every reply, including the founder's idea, forever.
- **Where:** `routers/voice.py`, `voice/`, `frontend/src/voice/mentorVoice.ts`.
- **How:** phrasebook first per sentence, then Gemini; cache only fixed sentences, never model-written replies.
- **When:** now (no key needed to reorder or to stop caching).
- **What for:** free voice by default and no personal data left on disk.
- `1.5.6.1` `[ ]` [R134](arena/details-p1.md#r134) (weight 68) Gemini TTS is called before the free recordings, and grouped text can never match them. Fix: Phrasebook first, per sentence, then Gemini for the rest.
- `1.5.6.2` `[ ]` [R017](arena/details-p1.md#r017) (weight 84) Voice/TTS audio cache keeps spoken replies forever, outside retention and erasure. Fix: Cache only fixed sentences (phrasebook and templates); never cache model-written replies.

### 1.6 Working memory

#### 1.6.1 `[ ]` Bounded working memory
- **Why:** the full message history goes to the model every turn; long chats get slow on free tiers.
- **Where:** `agents/providers.py`, `agents/ideation.py`, `agents/jobs.py`.
- **How:** send the facts, a rolling summary and the last 6 turns (about 8,000 tokens); a background job rewrites the summary every 8 turns.
- **When:** model paths only.
- **What for:** fast, bounded turns (SYSTEM-DESIGN §3.2, Phase 2).
- `1.6.1.1` Trim to facts plus last 6 turns.
- `1.6.1.2` Rolling summary job.
- `1.6.1.3` `[ ]` [R011](arena/details-p1.md#r011) (weight 90) Fact check accepts any number seen anywhere in the session; more memory, weaker check. Fix: Unit-aware facts: store number+unit pairs.
- `1.6.1.4` `[ ]` [R054](arena/details-p1.md#r054) (weight 84) s.messages is model context, resume transcript and fact source at once. Fix: Append-only transcript + derived context view; tool results stored by reference.
- `1.6.1.5` `[ ]` [R074](arena/details-p1.md#r074) (weight 77) 'Last 6 turns' trim has no turn boundaries and can orphan tool results. Fix: Turn-boundary window: keep the last N founder turns, each as a whole exchange.
- `1.6.1.6` `[ ]` [R164](arena/details-p1.md#r164) (weight 61) A model-written rolling summary either becomes a fact source or is dropped. Fix: Deterministic summary built by code from state.
- `1.6.1.7` `[ ]` [R191](arena/details-p1.md#r191) (weight 57) Tool results are stored twice in the session document and rewritten on every save. Fix: Store tool results by reference.

#### 1.6.2 `[ ]` Stable prompt prefix
- **Why:** the conversation prompt puts the current question and known facts inside the fixed part, so provider caching never hits.
- **Where:** `agents/ideation.py` (`SYSTEM`), `agents/providers.py`.
- **How:** stable instructions first, per-turn parts after.
- **When:** keyed or Gemini paths.
- **What for:** lower latency (SYSTEM-DESIGN §3.3).
- `1.6.2.1` Reorder the prompt.
- `1.6.2.2` `[ ]` [R103](arena/details-p1.md#r103) (weight 74) Reordering inside SYSTEM leaves the history uncacheable; the 1.6.1 window shifts it. Fix: Static system + per-turn context in the newest user turn + checkpointed window.
- `1.6.2.3` `[ ]` [R205](arena/details-p1.md#r205) (weight 51) Cache hits are invisible: cached tokens are never recorded and Claude has no breakpoint. Fix: Record cached tokens per provider into s.usage and the turn log.

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
- `2.1.1.3` `[ ]` [R071](arena/details-p2.md#r071) (weight 78) The 2.1.1 integration test skips on any setup error and bypasses migrations. Fix: conftest fixture: dedicated test DB, alembic upgrade head, skip only on connection refused.

#### 2.1.2 `[ ]` Fix the "saved" flag when Redis is on
- **Why:** `routers/ideation.py` reports `saved: false` whenever Redis fronts the database, because the store names itself `database+redis`; the Talk page then wrongly says the conversation is not being saved.
- **Where:** `routers/ideation.py`, `docs/runbooks/sessions-not-saved.md`.
- **How:** treat any store name starting with `database` as saved.
- **When:** now.
- **What for:** a truthful banner.
- `2.1.2.1` Fix and test.
- `2.1.2.2` `[ ]` [R083](arena/details-p2.md#r083) (weight 74) 'Saved' is sent only at start, and when true it hides the 6-hour idle expiry. Fix: Return {saved, kept_until} on start and resume, derived from the store's durability and the lifetime constant.
- `2.1.2.3` `[ ]` [R181](arena/details-p2.md#r181) (weight 58) Durability is inferred from a store-name string, and no test asserts the flag. Fix: durable attribute on SessionStore, delegated by wrappers, and API tests for each store.

#### 2.1.3 `[d]` One rule for session lifetime (D4)
- **Why:** the store hides a session after 6 idle hours even in PostgreSQL, while the design keeps conversations 90 days.
- **Where:** `agents/store.py`, SYSTEM-DESIGN §4.2, §5.4.
- **How:** 6 hours applies to the Redis live copy only; PostgreSQL keeps the session for the retention period, then the retention job deletes it (3.2.4).
- **When:** after D4.
- **What for:** founders can return to a conversation.
- `2.1.3.1` Apply the decided rule in the store.
- `2.1.3.2` `[w]` "Save this idea" (waits on 3.1.1 and D4): a saved flag on the session, a control on the Talk page, and a retention rule that skips saved sessions (SYSTEM-DESIGN §5.4).
- `2.1.3.3` `[ ]` [R073](arena/details-p2.md#r073) (weight 78) Under D4, CachedStore re-hides a session it just loaded: resume works, next turn 404s. Fix: Expiry only by Redis TTL in CachedStore; database rule separate.

#### 2.1.4 `[ ]` Session format version
- **Why:** old session documents must stay readable as the format changes.
- **Where:** `agents/ideation.py` (`to_dict`, `from_dict`).
- **How:** a `format` field and an upgrade-on-read function.
- **When:** before the table split (5.5.5).
- **What for:** safe evolution (SYSTEM-DESIGN §5.3).
- `2.1.4.1` Field and upgrade function, with a test.
- `2.1.4.2` `[ ]` [R137](arena/details-p2.md#r137) (weight 68) No policy for a session document that fails to decode; one bad doc breaks /programme. Fix: Central decode() with try/except, a log event and skip/410.
- `2.1.4.3` `[ ]` [R161](arena/details-p2.md#r161) (weight 62) Older code silently drops newer fields on load-then-save (rollback, Redis copy). Fix: Format guard: refuse to load or save a newer format than the code knows.
- `2.1.4.4` `[ ]` [R165](arena/details-p2.md#r165) (weight 61) Enum renames (D5 sector list) leave dead strings in old sessions and shift idea_version. Fix: Versioned upgrade step using the 4.1.2 mapping, re-keying results.
- `2.1.4.5` `[ ]` [R193](arena/details-p2.md#r193) (weight 55) Upgrade-on-read leaves mixed formats in PostgreSQL; the 5.5.5 split has no backfill. Fix: Format column plus an idempotent upgrade-all script before the split.

#### 2.1.5 `[ ]` Store and migrations that survive a missing database feature or an outage
- **Why:** migration 0003 needs pgvector, which the local PostgreSQL 18 lacks, so later migrations never apply; a database outage after start gives errors instead of the in-memory fallback.
- **Where:** `db/migrations/versions/0003_*.py`, `agents/store.py`.
- **How:** make 0003 conditional on the vector extension being available; wrap the store in a fallback with a small breaker.
- **When:** now; verified with `alembic upgrade --sql` and the fake store, then live once 2.1.1 unblocks.
- **What for:** the database can be brought up on this machine, and conversations survive an outage.
- `2.1.5.1` `[ ]` [R006](arena/details-p2.md#r006) (weight 94) Migration 0003 needs pgvector (dropped feature), blocking later migrations. Fix: Make 0003 conditional: create the vector extension and table only if pg_available_extensions lists vector.
- `2.1.5.2` `[ ]` [R075](arena/details-p2.md#r075) (weight 77) Database outage after startup gives 500s instead of an in-memory fallback. Fix: FallbackStore wrapper with a small hand-rolled circuit breaker.

#### 2.1.6 `[ ]` Session handling fixes that do not wait on D4
- **Why:** the Talk page forgets a session on any error, the programme cohort drops sessions idle over 6 hours, and in-memory sessions and locks grow forever.
- **Where:** `frontend/src/pages/Talk.tsx`, `agents/store.py`, `cohort/programme.py`.
- **How:** forget only on 404; a separate analytics read without idle expiry; a lazy sweep of expired sessions and locks.
- **When:** now.
- **What for:** conversations are not lost by accident and memory stays bounded.
- `2.1.6.1` `[ ]` [R029](arena/details-p2.md#r029) (weight 84) Talk page forgets the saved session ID on any resume error, not only 404. Fix: Error class carrying the HTTP status; forget only on 404.
- `2.1.6.2` `[ ]` [R058](arena/details-p2.md#r058) (weight 78) Programme cohort aggregates use store.get and drop sessions idle over 6 hours. Fix: Separate store method list_for_analytics(ids or since) without idle expiry.
- `2.1.6.3` `[ ]` [R179](arena/details-p1.md#r179) (weight 58) In-memory session store and per-session turn locks grow forever. Fix: Lazy sweep on create, plus lock cleanup on release and on delete.

### 2.2 Caching rules

#### 2.2.1 `[ ]` One fetch per key at a time
- **Why:** ten sessions asking the same new query make ten fetches and burn the free source budget.
- **Where:** `research/sources.py`, `core/redis.py`.
- **How:** a Redis `lock:{key}` (30 seconds); others wait briefly for the result; without Redis, no lock.
- **When:** now.
- **What for:** stays within OpenAlex and GitHub free limits (SYSTEM-DESIGN §4.2-4.3).
- `2.2.1.1` Lock and wait.
- `2.2.1.2` Test with the fake Redis.
- `2.2.1.3` `[ ]` [R098](arena/details-p2.md#r098) (weight 74) No single-flight without Redis, although the app runs as one process by default. Fix: In-process single-flight map of asyncio futures.
- `2.2.1.4` `[ ]` [R198](arena/details-p2.md#r198) (weight 52) EPO 'no hits' (404) answers are never cached, so empty searches repeat. Fix: Cache 404 as an empty result for EPO.
- `2.2.1.5` `[ ]` [R203](arena/details-p2.md#r203) (weight 51) 30 s lock expires before the 60 s fetch; failed holder leaves waiters to stampede. Fix: redis-py Lock (redis.asyncio.lock.Lock).

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
- `2.2.3.2` `[ ]` [R208](arena/details-p2.md#r208) (weight 51) Reference caches depend on each other across datasets; a per-loader clear leaves mixed versions. Fix: Dataset registry decorator: @dataset_cache('banking', 'ecosystem') wrapping lru_cache.

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
- `2.2.5.2` `[ ]` [R160](arena/details-p2.md#r160) (weight 62) Disk cache writes are not atomic, and a truncated file raises instead of missing. Fix: Write to a temp file and os.replace, and treat unreadable files as a miss (delete them).
- `2.2.5.3` `[ ]` [R180](arena/details-p2.md#r180) (weight 58) A disk-cache hit copied to Redis gets a fresh full TTL, so data can stay stale for twice as long. Fix: Copy with the remaining TTL (ttl minus file age).

#### 2.2.6 `[w]` Nightly cache warming for registry domains
- **Waiting on:** a free OpenAlex key. Warming inside the shared free daily budget would use up the searches founders need live (`docs/runbooks/research-budget.md`).
- **Why:** common ideas could answer from cache instantly.
- **Where:** `scripts/`, the nightly job (5.4.4).
- **How:** run each registry domain's research queries nightly under the budget cap.
- **When:** after 2.2.1 and the key.
- **What for:** instant evidence for known domains (SYSTEM-DESIGN §4.3).
- `2.2.6.1` Warming script under the budget cap.
- `2.2.6.2` `[ ]` [R148](arena/details-p2.md#r148) (weight 68) Warmed keys won't match founder searches: cache keys are exact query strings. Fix: Refresh-ahead of keys founders actually requested.
- `2.2.6.3` `[ ]` [R178](arena/details-p2.md#r178) (weight 61) Warming has no founder reserve in the shared daily cap and refetches a 7-day cache. Fix: Warming share of the cap plus warm-only-if-expiring.

#### 2.2.7 `[ ]` Research cache keys without credentials
- **Why:** the OpenAlex key is part of the cache key, so adding or rotating it empties the cache.
- **Where:** `research/sources.py`.
- **How:** strip credential parameters before building the key.
- **When:** now.
- **What for:** the free research budget is not wasted after a key change.
- `2.2.7.1` `[ ]` [R122](arena/details-p2.md#r122) (weight 68) OpenAlex API key is part of the cache key; adding/rotating it empties the cache. Fix: Strip credential params before building the key.

### 2.3 Background jobs

#### 2.3.1 `[w]` Durable results and a shared queue
- **Waiting on:** the database (2.1.1).
- **Why:** a restart loses running jobs, and several server processes cannot share them.
- **How:** a results table keyed by session, idea version and kind; a Redis queue (decision 0010).
- `2.3.1.1` Results table and migration.
- `2.3.1.2` Redis queue.

#### 2.3.2 `[ ]` Job board correctness in one process
- **Why:** a failed job is narrated as 'still searching' and re-run every turn, jobs are never pruned, and panel bursts can exceed free-tier limits.
- **Where:** `agents/jobs.py`, `agents/results.py`, `agents/ideation.py`.
- **How:** return the job state from waits and say once that it failed, with a backoff; a periodic sweep; a semaphore per job kind.
- **When:** now; the durable queue (2.3.1) still waits on the database.
- **What for:** honest progress messages and stable memory and model use.
- `2.3.2.1` `[ ]` [R032](arena/details-p2.md#r032) (weight 84) A failed job is narrated as 'still searching', never reported, and re-run on every turn. Fix: Board.wait returns the state; failure notice; retry after a backoff.
- `2.3.2.2` `[ ]` [R078](arena/details-p1.md#r078) (weight 74) Job board and background results are never pruned or expired. Fix: In-process periodic sweep tied to the store's expiry.
- `2.3.2.3` `[ ]` [R153](arena/details-p2.md#r153) (weight 67) No global limit on concurrent jobs: panel bursts of 7 model calls per session hit free-tier limits. Fix: asyncio.Semaphore per job kind plus a token-bucket limiter per provider.

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
- `2.4.2.3` `[ ]` [R108](arena/details-p2.md#r108) (weight 74) The fact-check gate logs every dropped model sentence verbatim; the request ID is client-controlled. Fix: Log problem codes plus a short hash of the sentence; validate x-request-id with a regex.

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
- `3.1.1.2` `[ ]` [R001](arena/details-p3.md#r001) (weight 100) Session ID is a bearer credential: no ownership check on resume/turn/delete, handed to programmes. Fix: Optional-user FastAPI dependency plus an owner check in _load.
- `3.1.1.3` `[ ]` [R061](arena/details-p2.md#r061) (weight 78) SqlStore.save never updates user_id; claimed session stays 'anon'. Fix: Dedicated store.claim(session_id, user_id) with a conditional UPDATE.
- `3.1.1.4` `[ ]` [R059](arena/details-p2.md#r059) (weight 78) agent_sessions.user_id is a free string with no FK to users; no user-to-sessions link. Fix: Explicit erasure service with a table map and a guard on 'anon'.
- `3.1.1.5` `[ ]` [R096](arena/details-p3.md#r096) (weight 74) No 'my conversations' list: a founder cannot find past sessions on another device. Fix: GET /ideation/agent/sessions returning id, title, idea_version, last_active for the current user.
- `3.1.1.6` `[ ]` [R117](arena/details-p3.md#r117) (weight 71) Claim rule unspecified: a shared phone hands founder A's session to founder B. Fix: Explicit claim endpoint: only user_id='anon' sessions, founder confirms in the UI.
- `3.1.1.7` `[ ]` [R129](arena/details-p3.md#r129) (weight 68) Browser keeps only the latest session id, so sign-up can claim one conversation at most. Fix: Recent-sessions list in localStorage, claimed in one call at sign-in.

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
- `3.1.2.5` `[ ]` [R024](arena/details-p3.md#r024) (weight 84) Founder table forces full basic tier NOT NULL; partial profiles can't sync. Fix: Nullable profile columns; completeness enforced by the scorer, not by NOT NULL.
- `3.1.2.6` `[ ]` [R069](arena/details-p3.md#r069) (weight 78) Self-typed fields and a 'demo' checkbox would be stored as verified, tier 100. Fix: Server ignores client verification flags; verified_fields empty until a real check exists; tiers renamed (basic, standard, complete).
- `3.1.2.7` `[ ]` [R102](arena/details-p3.md#r102) (weight 74) Refresh token is never used or revocable: 30-min logouts and no server-side sign-out. Fix: refresh_tokens table in PostgreSQL (hashed jti, revoked_at).
- `3.1.2.8` `[ ]` [R167](arena/details-p3.md#r167) (weight 61) Founder and Startup carry soft delete plus unique email/phone/GSTIN, against D12 erasure. Fix: Drop SoftDeleteMixin; hard delete with FK cascades (and an audit row without personal data).

#### 3.1.3 `[w]` Move the other browser-only state to the server
- **Waiting on:** 3.1.2.
- **Why:** journey, funding pipeline, milestone status and supplier quotes are lost when the browser is cleared.
- **How:** store each on the founder's record.
- `3.1.3.1` Journey and milestone status.
- `3.1.3.2` Funding pipeline.
- `3.1.3.3` Supplier quotes.
- `3.1.3.4` `[ ]` [R169](arena/details-p3.md#r169) (weight 61) No merge or conflict rule for moving browser state to the server (two devices, first sync). Fix: Per-record version and updated_at with 409 on conflict, and a union-by-UUID merge at first sync.

#### 3.1.4 `[ ]` Auth hardening that needs no database
- **Why:** the JWT secret defaults to 'change-me' with no guard, and the login and register routes reveal which emails have accounts.
- **Where:** `core/config.py`, `routers/auth.py`.
- **How:** refuse the default or a short secret outside development; constant-time login with a dummy hash and a generic register reply.
- **When:** now (unit-tested without a database).
- **What for:** tokens cannot be forged and accounts cannot be listed.
- `3.1.4.1` `[ ]` [R002](arena/details-p3.md#r002) (weight 100) JWT secret defaults to 'change-me' with no startup guard. Fix: pydantic model_validator refusing the default or a short key when app_env != development.
- `3.1.4.2` `[ ]` [R204](arena/details-p3.md#r204) (weight 51) Account enumeration: register returns 409 and login skips bcrypt for unknown emails. Fix: Verify against a fixed dummy bcrypt hash when the user is missing; generic register response.

#### 3.1.5 `[ ]` Browser state that is safe and consistent
- **Why:** sign-out leaves the founder's data for the next person, two modules write different shapes to one storage key, and the browser profile does not map onto the backend's facts.
- **Where:** `frontend/src/profileStore.ts`, `journeyStore.ts`, `pages/Journey.tsx`, `voice/agentClient.ts`.
- **How:** namespace browser keys and clear on sign-out; one journey store; an explicit profile-to-slot projection (used by 1.1.1).
- **When:** now.
- **What for:** shared phones are safe and the profile reaches the conversation correctly.
- `3.1.5.1` `[ ]` [R060](arena/details-p3.md#r060) (weight 78) Sign-out leaves founder's browser data (profile, consent, journey, session) for next user. Fix: Namespace keys by user ID, clear the anonymous namespace on logout, and confirm before claiming it.
- `3.1.5.2` `[ ]` [R018](arena/details-p1.md#r018) (weight 84) Journey.tsx and journeyStore.ts share the 'vanigam_journey' key with different shapes. Fix: Fold Journey facts and done into journeyStore (a 'registration' field; version bumped to 2 with a migration that keeps consent and milestones).
- `3.1.5.3` `[ ]` [R081](arena/details-p1.md#r081) (weight 74) Browser profile keys/vocabularies don't map to backend slots. Fix: Explicit allowlisted projection in the client (founder.district to district, startup.stage to stage, startup.domain to sector) plus a typed AgentStartIn.profile with only those keys.

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
- `3.2.2.2` `[ ]` [R166](arena/details-p3.md#r166) (weight 61) Field encryption plan breaks unique and indexed columns; no key or blind-index design. Fix: AES-GCM TypeDecorator (cryptography lib) with key ID prefix + HMAC-SHA256 blind index columns for unique/lookup fields.

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
- `3.2.4.3` `[ ]` [R062](arena/details-p3.md#r062) (weight 78) Erasure outside the app leaves the Redis session copy readable. Fix: Run erasure and retention inside the app (admin endpoint or in-process task).
- `3.2.4.4` `[ ]` [R132](arena/details-p3.md#r132) (weight 68) Erasure deletes consents, but retention keeps consents a year after the data. Fix: Tombstone consent record after erasure.

#### 3.2.5 `[ ]` Protect the programme cohort endpoint
- **Why:** `/api/v1/cohort/programme` has no auth; anyone with session IDs can call it.
- **Where:** `routers/cohort.py`, `api/deps.py`, `frontend/src/pages/Cohort.tsx` (calls the endpoint without a token today).
- **How:** a programme-manager role on the token; until roles exist, require an authenticated user, and make the Cohort page sign in and send the token.
- **When:** now for the auth check; the role after 3.1.
- **What for:** consenting founders' aggregates stay with the programme.
- `3.2.5.1` Require auth, and send the token from the Cohort page.
- `3.2.5.2` Programme-manager role.
- `3.2.5.3` `[ ]` [R057](arena/details-p3.md#r057) (weight 78) Differencing two caller-chosen session-ID lists defeats the 5-founder floor. Fix: Server-owned programme membership.
- `3.2.5.4` `[ ]` [R195](arena/details-p3.md#r195) (weight 52) 3.2.5.1 is marked 'now' but its auth needs the PostgreSQL users table. Fix: Interim operator key from settings, compared with secrets.compare_digest.
- `3.2.5.5` `[ ]` [R210](arena/details-p3.md#r210) (weight 45) Programme endpoint loads up to 500 full session documents one at a time. Fix: store.get_many: one SELECT ... WHERE session_id = ANY(:ids) (and Redis MGET), filtering consent before parsing.

#### 3.2.6 `[w]` Legal review before a pilot
- **Waiting on:** owner. A one-time DPDP review and a named grievance officer (constraint solutions §A.3; feasibility survey P).

#### 3.2.7 `[ ]` Consent recorded in the session until the consent table exists
- **Why:** caste is collected and used in ranking with no consent gate, the consent screen's purposes differ from the design, and in-session consents can be neither seen nor withdrawn.
- **Where:** `agents/ideation.py`, `schemes/`, `pages/Consent.tsx`, `pages/Talk.tsx`.
- **How:** one purpose list as an enum; consent events kept in the session document; protected fields stripped unless their purpose is granted; consent shown and withdrawable in the snapshot.
- **When:** now; moves into the consent table with 3.2.1 later.
- **What for:** lawful use of protected data from today.
- `3.2.7.1` `[ ]` [R021](arena/details-p3.md#r021) (weight 84) Caste collected, sent by default and used in ranking without a consent gate. Fix: Server-side purpose gate: strip protected fields unless consent for that purpose is present.
- `3.2.7.2` `[ ]` [R079](arena/details-p3.md#r079) (weight 74) Consent page purposes don't match the design list and promise dropped features. Fix: One purpose registry as a Python Enum, published through OpenAPI and used by the generated TS types.
- `3.2.7.3` `[ ]` [R120](arena/details-p3.md#r120) (weight 68) In-session consents (cohort, private) set once at start; cannot be seen or withdrawn. Fix: Return the consent state and programme name in the snapshot; show it as a toggle on the Talk page that calls the consent-event route.
- `3.2.7.4` `[ ]` [R131](arena/details-p3.md#r131) (weight 68) Consent given in anonymous sessions has no record, no withdrawal, no claim path. Fix: Consent events inside the session JSON (purpose, granted/withdrawn, time, notice version), plus a PATCH route; copied into core.consents on claim.

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
- `4.1.1.3` `[ ]` [R003](arena/details-p1.md#r003) (weight 100) Unknown profile field treated as failing a scheme rule ('not known' becomes 'not eligible'). Fix: Three-valued (Kleene) evaluation in rules.py.
- `4.1.1.4` `[ ]` [R037](arena/details-p4.md#r037) (weight 84) Engine ranks closed or ended schemes as eligible; it never reads open/closed status. Fix: Status joined from funding_catalogue.json by scheme id at load.
- `4.1.1.5` `[ ]` [R064](arena/details-p4.md#r064) (weight 78) NEEDS and UYEGP age rules contradict the catalogue: wrong 'no' and wrong 'yes'. Fix: Category-aware rule groups plus a seed-vs-catalogue consistency test.
- `4.1.1.6` `[ ]` [R111](arena/details-p4.md#r111) (weight 74) Unencoded criteria already returned by the API are never shown on the Schemes screen. Fix: Render the notes under each scheme as 'Also check'.
- `4.1.1.7` `[ ]` [R145](arena/details-p4.md#r145) (weight 68) TANSEED is called a 'non-dilutive grant' though StartupTN takes a 3% stake. Fix: Explicit `dilutive: bool` (and equity %) on Scheme, used in the reason.

#### 4.1.2 `[d]` One sector taxonomy (D5)
- **Why:** three vocabularies exist (`elicitation/slots.py` with 12 sectors, `ecosystem/taxonomy.py`, the StartupTN categories in the registry); a missing sector makes a question unanswerable.
- **Where:** one taxonomy module.
- **How:** pick the canonical list; map the others to it; generate the extractor's sector cues from it; test that every sector has a cue (the quality set shows the sector question asked even for tea, jasmine and knitwear).
- **When:** after D5; before 1.1.5.3.
- **What for:** one meaning of "sector" (August Req 2.7; rnd-elicitation §6.5).
- `4.1.2.1` Canonical module and mappings.
- `4.1.2.2` Generated cues and coverage test.
- `4.1.2.3` `[ ]` [R047](arena/details-p4.md#r047) (weight 84) Planner sector fact mixes vocabularies; K_DOMAIN misses registry ids like healthtech. Fix: Canonical str Enum, consumers compare against members, plus a test banning sector string literals.
- `4.1.2.4` `[ ]` [R036](arena/details-p1.md#r036) (weight 84) D5's canonical list (12 registry categories) has no food, education, retail or manufacturing. Fix: Two-level canonical taxonomy: StartupTN category as the public top level, ecosystem sector ids (20) as the required second level, with each elicitation value mapped to a sector.
- `4.1.2.5` `[ ]` [R168](arena/details-p4.md#r168) (weight 61) Founder sector is single-valued while matchers are multi-sector; no rule for mixed ideas. Fix: Primary sector slot plus a derived secondary list from all cue hits.

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

#### 4.1.6 `[ ]` Funding fit compares like with like
- **Why:** funding fit compares the founder's need with benefit caps, loan sizes and project costs as if they were the same amount.
- **Where:** `schemes/`, `funding_catalogue.json` fields.
- **How:** separate project range and benefit fields; fit against the project range.
- **When:** now.
- **What for:** fit scores that mean something.
- `4.1.6.1` `[ ]` [R091](arena/details-p4.md#r091) (weight 74) Funding fit compares the founder's need with mixed amounts (benefit cap, loan size, project). Fix: Separate project range and benefit fields; fit against the project range, show the benefit.

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
- `4.2.2.2` `[ ]` [R028](arena/details-p4.md#r028) (weight 84) Supplier directory covers only 3 districts; others get A-Z order with no notice. Fix: District centroid table (38 TN districts, from OSM or the India Post data already used) as a km fallback, plus a coverage flag in the response.
- `4.2.2.3` `[ ]` [R080](arena/details-p4.md#r080) (weight 74) BOM category keyword matching misfires on substrings. Fix: Word-boundary token matching plus templates keyed to the canonical sectors, with an 'unknown product: add lines yourself' result instead of the packaging default.
- `4.2.2.4` `[ ]` [R125](arena/details-p4.md#r125) (weight 68) A cluster map already exists, uncited, in Supply.tsx; 4.2.2 would create a second owner. Fix: Cited JSON data file in backend (b2b/data/clusters.json) keyed by canonical category or NIC prefix, returned with each line.

#### 4.2.3 `[ ]` Make the order split and supplier scoring correct
- **Why:** the CP-SAT order split and supplier scoring give wrong or unexplained results on ordinary inputs (arena findings below).
- **Where:** `b2b/allocate.py`, `b2b/matching.py`, `routers/b2b.py`.
- **How:** validate inputs, scale penalties to price, and explain every unmet line.
- **When:** now; before 4.2.1 switches `/b2b` to real suppliers.
- **What for:** an order plan a founder can trust and act on.
- `4.2.3.1` `[ ]` [R067](arena/details-p4.md#r067) (weight 78) Order split leaves any item over Rs 1 lakh a unit unbought, with a false reason. Fix: Lexicographic solve: first maximise placed units, then minimise cost with placement fixed.
- `4.2.3.2` `[ ]` [R090](arena/details-p4.md#r090) (weight 74) Flat Rs 2 'far' penalty ignores price scale and picks a 2.5x dearer supplier. Fix: Founder-entered landed cost (price including delivery) on each quote.
- `4.2.3.3` `[ ]` [R149](arena/details-p4.md#r149) (weight 68) When a supplier's minimum order is above the need, the line is just 'unmet'. Fix: Post-solve suggestion only: for unmet lines, list the cheapest MOQ purchase.
- `4.2.3.4` `[ ]` [R197](arena/details-p4.md#r197) (weight 52) Allocate/pair inputs unvalidated: duplicate IDs drop units, categories case-sensitive. Fix: Pydantic model validators: unique ids, category Literal from CATEGORY_NIC keys, lowercased.
- `4.2.3.5` `[ ]` [R020](arena/details-p4.md#r020) (weight 84) /supply matches and gaps come from invented seed suppliers. Fix: Directory-only supply map: nearby_makers become the matches, gap = directory total 0.

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
- `4.3.1.3` `[ ]` [R012](arena/details-p4.md#r012) (weight 90) Funding screen sends invented answers (IP, retention, unit economics) into readiness. Fix: Send only founder-given fields; readiness reports per-dimension coverage and marks thin dimensions 'not assessed'.
- `4.3.1.4` `[ ]` [R039](arena/details-p4.md#r039) (weight 84) Invented readiness gate of 60 blocks every idea and prototype founder from pre-seed investors. Fix: Readiness as a soft ranking factor plus advice, not a hard constraint.

#### 4.3.2 `[w]` Track progress on recommendations
- **Waiting on:** 3.1.2.
- `4.3.2.1` Mark a recommendation in progress or done, per founder.

#### 4.3.3 `[ ]` Investor matching treats unpublished facts as unknown
- **Why:** an investor whose stage or sector is not published is treated as a 'no', and the fit score is mostly constants.
- **Where:** `funding/investor_match.py`, `ecosystem/match.py`.
- **How:** three-valued checks (yes, no, not published) and a fit score built only from published signals.
- **When:** now.
- **What for:** founders are not steered away from investors on missing data.
- `4.3.3.1` `[ ]` [R112](arena/details-p4.md#r112) (weight 74) Unpublished investor stage or sector means 'no'; fit score is built mostly from constants. Fix: Three-valued constraints with a 'check with the investor' group, and fit only from varying terms (sector specialist, stage-list position, traction margin, thesis keyword overlap).

#### 4.3.4 `[ ]` Funding calculations that are correct
- **Why:** the gap plan ignores what the founder already has, and pipeline metrics count lost deals as reaching every stage.
- **Where:** `funding/gaps.py`, `funding/pipeline.py`.
- **How:** counterfactual re-scoring per action; stage counts from actual transitions with proper timestamps.
- **When:** now.
- **What for:** next steps and pipeline numbers a founder can trust.
- `4.3.4.1` `[ ]` [R092](arena/details-p4.md#r092) (weight 74) Gap plan ignores what the founder already has; its impact points disagree with the rubric. Fix: Counterfactual re-score: each action names the input it changes; impact = score_readiness(after) - score_readiness(before).
- `4.3.4.2` `[ ]` [R186](arena/details-p4.md#r186) (weight 58) Pipeline metrics wrong: lost deals count as reaching every stage; first-stage time is lost. Fix: Parse with datetime.fromisoformat (Python 3.11 accepts 'Z') then take .date(); terminal entries without history count only their terminal stage; label weighted value 'rule of thumb' or drop it.

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
- `4.4.1.3` `[ ]` [R094](arena/details-p4.md#r094) (weight 74) Intel calls the synthetic corpus 'cached'; personalisation and language are never used. Fix: Label 'demo' when provider is fixture; send profile fields; boost items in the founder's language.

#### 4.4.2 `[ ]` A news board that does not break or mislead
- **Why:** one malformed article crashes the board, and 'something to act on' fires on old deadlines and funding-round news.
- **Where:** `news/`, `routers/news.py`, `Intel.tsx`.
- **How:** tolerate unknown sources, normalise dates at fetch, and gate 'act on' by date and item type.
- **When:** after D9.
- **What for:** a board founders can rely on.
- `4.4.2.1` `[ ]` [R100](arena/details-p4.md#r100) (weight 74) One article from an unknown source crashes the whole board (KeyError in dedupe). Fix: Drop unattributable articles before dedupe.
- `4.4.2.2` `[ ]` [R084](arena/details-p4.md#r084) (weight 74) 'Something to act on' fires on funding-round news and on deadlines that have passed. Fix: Phrase patterns with negation and date check: 'apply by / last date / applications open', demoted by 'closed / ended / extended till <past date>', with dates read by dateparser.
- `4.4.2.3` `[ ]` [R097](arena/details-p4.md#r097) (weight 74) No date normalisation at the fetch boundary: RSS dates get recency 0. Fix: feedparser in the live fetcher, normalising published_parsed to ISO in _clamp.
- `4.4.2.4` `[ ]` [R200](arena/details-p4.md#r200) (weight 52) Redirect guard accepts any listed domain, even ones whose robots rules are unchecked. Fix: Guard against fetchable sources and https only, plus urllib.robotparser checked at fetch time (cached daily).
- `4.4.2.5` `[ ]` [R152](arena/details-p4.md#r152) (weight 67) News board fetches on every request; no stored corpus or refresh schedule. Fix: Scheduled refresh (every few hours) writing the ranked-input corpus to Redis with a file fallback, with ETag/Last-Modified kept per source.

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
- `5.1.1.3` `[ ]` [R088](arena/details-p5.md#r088) (weight 74) Eval replays the finished scan, so scan's own logic and the categories check test nothing. Fix: Record per-source results, replay sources.
- `5.1.1.4` `[ ]` [R104](arena/details-p5.md#r104) (weight 74) Runner answers 'skip' to unscripted questions; the payer question is skipped in all 10. Fix: 'Unscripted question' check.
- `5.1.1.5` `[ ]` [R136](arena/details-p5.md#r136) (weight 68) No degraded-research fixtures: the 'papers not searched' path is never evaluated. Fix: Degraded variants generated from existing fixtures.
- `5.1.1.6` `[ ]` [R196](arena/details-p5.md#r196) (weight 52) 5.1.1.2 'report matches runner' cannot be a diff: the report embeds a run timestamp. Fix: --check mode comparing all but the header.

#### 5.1.2 `[ ]` Evaluate the model path too
- **Why:** the quality set covers only the offline path; meaning-level checks were left to evaluation (0005).
- **Where:** `tests/eval`.
- **How:** replay the 10 ideas through a free model (Ollama locally) with recorded answers; add meaning-level checks.
- **When:** after 1.5.3 for Gemini; Ollama now.
- **What for:** the model path meets the same bar.
- `5.1.2.1` Model-path replay.
- `5.1.2.2` Meaning-level checks.
- `5.1.2.3` `[ ]` [R206](arena/details-p5.md#r206) (weight 51) Eval checks a re-built plan, not the roadmap the founder was given. Fix: Check s.roadmap directly.

#### 5.1.3 `[ ]` Tune the weights
- **Why:** the panel's vote weights and the question selector's constants are uncalibrated priors.
- **Where:** `agents/council/data/council_weights.json`, `elicitation/selector.py`.
- **How:** log slot order, questions asked, completion and corrections (no idea text); tune against the quality set and those logs.
- **When:** after 5.1.2.
- **What for:** shorter interviews and better verdicts (IDEATION Phase 4).
- `5.1.3.1` Anonymous interview statistics.
- `5.1.3.2` Tuning run and report.
- `5.1.3.3` `[ ]` [R013](arena/details-p5.md#r013) (weight 90) Panel idea type checks health_bio first: 7 of 10 eval ideas get the wrong weight row. Fix: Map registry domain / deep pack to idea type.

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
- `5.1.5.2` `[ ]` [R209](arena/details-p5.md#r209) (weight 45) Coverage gate will ignore scripts/ that rewrite reference data; they have no tests. Fix: Unit tests for each script's parse/merge functions with saved samples.

#### 5.1.6 `[ ]` Security tests
- **Why:** nothing tests injection, cross-site scripting or forged requests against the API.
- **Where:** `backend/tests/` (security), `core/middleware.py`.
- **How:** tests that send injection and script payloads to each input-taking route and check they are rejected or escaped; check cookie and CORS settings against forged requests.
- **When:** now.
- **What for:** no basic web vulnerabilities before a pilot (August tasks 5.4.1-5.4.3).
- `5.1.6.1` Injection and script-payload tests.
- `5.1.6.2` Forged-request and CORS checks.
- `5.1.6.3` `[ ]` [R133](arena/details-p5.md#r133) (weight 68) Founder-supplied name and profile are placed in the system prompt (prompt injection). Fix: Move founder data out of system into a delimited data block + name charset rule.
- `5.1.6.4` `[ ]` [R163](arena/details-p2.md#r163) (weight 61) Rate limiter is per process, keyed by IP not user, and never evicts keys. Fix: Redis window per session id with route cost.

#### 5.1.7 `[ ]` Dead-code checks and frontend CI
- **Why:** nothing in CI catches dead code or type errors, and the frontend has no CI at all.
- **Where:** `.github/workflows/ci.yml`.
- **How:** a frontend job (type check and unused-code check) and a backend dead-code check.
- **When:** now.
- **What for:** regressions caught before merge.
- `5.1.7.1` `[ ]` [R184](arena/details-p5.md#r184) (weight 58) No dead-code or type check in CI, and the frontend has no CI at all. Fix: Frontend CI job: tsc --noEmit + knip; backend: vulture with a whitelist.

### 5.2 Data checks in CI

#### 5.2.1 `[ ]` JSON schema for every reference data file
- **Why:** a malformed data file reaches founders.
- **Where:** schemas beside each class A file; `ci.yml`.
- **How:** CI validates each file against its schema.
- **When:** SYSTEM-DESIGN Phase 4.
- **What for:** correct reference data (§5.3).
- `5.2.1.1` Schemas.
- `5.2.1.2` CI step.
- `5.2.1.3` `[ ]` [R077](arena/details-p5.md#r077) (weight 77) Weekly data PRs opened with GITHUB_TOKEN will not trigger ci.yml, so data checks skip them. Fix: Reusable workflow (workflow_call) shared by ci.yml and weekly-checks.yml.
- `5.2.1.4` `[ ]` [R141](arena/details-p5.md#r141) (weight 68) Pack prices and regulatory items carry no checked date, so no freshness rule can reach them. Fix: checked_on + source per price and regulatory item, required by JSON Schema.
- `5.2.1.5` `[ ]` [R162](arena/details-p5.md#r162) (weight 62) Registry 'ids unique across batches' test is a tautology; duplicates overwrite silently. Fix: Raise on duplicate id in load() and test the raw lists.

#### 5.2.2 `[ ]` Freshness gate
- **Why:** an open scheme unchecked for months may be closed.
- **Where:** scheme data, `ci.yml`.
- **How:** one date field name (`checked_on`) across files; CI fails when an open scheme is unchecked for 30 days.
- **When:** after 5.2.1.
- **What for:** truthful schemes (§5.3).
- `5.2.2.1` Unify the date field.
- `5.2.2.2` CI gate.
- `5.2.2.3` `[ ]` [R135](arena/details-p5.md#r135) (weight 68) Investor pitch routes never go stale, unlike incubator intake (14 days). Fix: Shared staleness helper with per-dataset max age.
- `5.2.2.4` `[ ]` [R124](arena/details-p5.md#r124) (weight 68) A clock-based CI gate turns unrelated PRs red; catalogue has only a file-level date. Fix: Per-entry checked_on + scheduled freshness job that opens an issue.

#### 5.2.3 `[ ]` Guard harvests that shrink
- **Why:** a broken scrape can wipe a dataset.
- **Where:** `scripts/check_*.py`, `build_domain_signals.py`.
- **How:** a result more than 20% smaller than the last is held for review, not written.
- **When:** weekly job.
- **What for:** data safety (§5.3, §9).
- `5.2.3.1` Shrink guard.
- `5.2.3.2` Runbook "a harvest returned suspiciously little".
- `5.2.3.3` `[ ]` [R128](arena/details-p5.md#r128) (weight 68) An OpenAlex budget exit fails the weekly job and throws away intake and investor checks. Fix: continue-on-error on each data step + PR step with if: always().
- `5.2.3.4` `[ ]` [R123](arena/details-p5.md#r123) (weight 68) A 20% size guard misses the real harvest failure: 'unreachable' overwrites good records. Fix: Carry forward the last good record on transient failure.

#### 5.2.4 `[ ]` Migrations tested in CI
- **Why:** a broken migration is found only on someone's machine.
- **Where:** `ci.yml` with a PostgreSQL service.
- **How:** empty database, migrate up, down one, up again.
- **When:** now (CI has its own database; not blocked by local credentials).
- **What for:** safe schema changes (§5.2).
- `5.2.4.1` PostgreSQL service and the round trip.
- `5.2.4.2` `[ ]` [R115](arena/details-p2.md#r115) (weight 71) Migration 0001 builds tables from live ORM models; migration CI lacks drift check. Fix: Freeze 0001 into explicit op.create_table calls (generated once from today's metadata).

### 5.3 Documentation

#### 5.3.1 `[ ]` Data dictionary
- **Why:** there is no record of each table and data file's owner, class, source and refresh.
- **Where:** `docs/data/`, generated from models and schemas where possible.
- **How:** a generator plus a CI check that every migration and data file has an entry, and that links between documents resolve.
- **When:** SYSTEM-DESIGN Phase 4.
- **What for:** documentation that matches the code (§6).
- `5.3.1.1` Generator and entries.
- `5.3.1.2` CI entry and link checks.
- `5.3.1.3` `[ ]` [R130](arena/details-p5.md#r130) (weight 68) Code cites 'build spec' sections that live only in private claude.ai artifacts. Fix: Export the build spec and dashboard to Markdown in docs/specs/.
- `5.3.1.4` `[ ]` [R194](arena/details-p5.md#r194) (weight 52) .env.example lacks 8 settings and nothing checks it against config.py. Fix: Generate .env.example from Settings with field descriptions.
- `5.3.1.5` `[ ]` [R202](arena/details-p5.md#r202) (weight 52) Stale root docs outside 5.3.3, and the link check would miss code-path references. Fix: Extend the link check to backticked repo paths.

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
- `5.3.2.5` `[ ]` [R201](arena/details-p5.md#r201) (weight 52) Runbook log names are not checked against code; one already does not exist. Fix: Test that every `a.b` log name in runbooks appears in backend/app.

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
- `5.3.4.2` `[ ]` [R127](arena/details-p5.md#r127) (weight 68) An OpenAPI export would omit the core contract: agent routes untyped, stream events unspecified. Fix: Pydantic models for responses and a discriminated union for stream events, exported in the OpenAPI document.

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
- `5.4.1.2` `[ ]` [R095](arena/details-p5.md#r095) (weight 74) Middleware timing ends at response headers; for SSE turns it misses the first sentence. Fix: In-generator step marks with time.perf_counter, one structured log line per turn.
- `5.4.1.3` `[ ]` [R109](arena/details-p5.md#r109) (weight 74) The offline turn waits up to 3 s (+1.5 s) for jobs before its first sentence. Fix: Speak a fixed reflection/acknowledgement sentence before waiting.
- `5.4.1.4` `[ ]` [R150](arena/details-p5.md#r150) (weight 67) No store to compute median/p95 timings; only stdout logs. Fix: Fixed-bucket histograms and counters in Redis (HINCRBY per minute bucket).
- `5.4.1.5` `[ ]` [R172](arena/details-p5.md#r172) (weight 61) Per-IP rate limit counts every TTS and reconnect call; a 429 silently kills notices. Fix: Key the limiter by session id on agent and voice routes, with an IP cap as backstop.
- `5.4.1.6` `[ ]` [R183](arena/details-p5.md#r183) (weight 58) Jobs log start and failure but not finish, so the 0010 wait budgets cannot be tuned. Fix: job.done event with seconds and an in_time counter from wait().

#### 5.4.2 `[ ]` Cache hit rates and budgets
- **Why:** nobody can see whether caches work or how close a source is to its free daily limit.
- **Where:** `core/redis.py`, `research/sources.py`, `agents/ideation.py`.
- **How:** counters for hits and misses per cache layer; daily requests per source; tokens per session (already counted in `s.usage`).
- **When:** now.
- **What for:** spot budget trouble before founders do (SYSTEM-DESIGN §8).
- `5.4.2.1` Hit and miss counters per layer.
- `5.4.2.2` Budget use per source per day, tokens per session.
- `5.4.2.3` `[ ]` [R082](arena/details-p5.md#r082) (weight 74) Budget alert at 80% has no per-source limit to measure against. Fix: Per-source limit table in settings.
- `5.4.2.4` `[ ]` [R140](arena/details-p5.md#r140) (weight 68) Own cap, 429 pause and real exhaustion all report 'add OPENALEX_API_KEY'. Fix: Reason enum on the internal result.
- `5.4.2.5` `[ ]` [R174](arena/details-p5.md#r174) (weight 61) Session token budget counts local Ollama tokens and has no per-provider split. Fix: Usage keyed by provider plus a daily per-provider Redis counter.
- `5.4.2.6` `[ ]` [R187](arena/details-p5.md#r187) (weight 58) Redis unavailability is memoised for the process; layer counters can't tell 'off' from 'cold'. Fix: Re-probe on a timer plus an 'L1 live' gauge.

#### 5.4.3 `[ ]` Monitoring page
- **Why:** SYSTEM-DESIGN Phase 4 asks for one dashboard.
- **Where:** a backend endpoint and a frontend page.
- **How:** a page reading 5.4.1 and 5.4.2 (free; no paid monitoring).
- **When:** after 5.4.1 and 5.4.2.
- **What for:** one place to see latency, caches and budgets.
- `5.4.3.1` Dashboard.
- `5.4.3.2` `[w]` Alerts (waits on a hosting decision).
- `5.4.3.3` `[ ]` [R138](arena/details-p5.md#r138) (weight 68) No view of which degraded mode is active: breakers, store, Redis, research pauses. Fix: Status endpoint aggregating breaker states, store name, Redis ping, rs:neg keys, model provider in use.

#### 5.4.4 `[ ]` Nightly job
- **Why:** cache purge, cache warming, retention deletes and cohort rebuild all need a nightly run.
- **Where:** one script (`scripts/nightly.py`) started by a scheduler on the machine where the app runs (the OS scheduler, or an in-process scheduler); it must see the app's `.cache/research`, PostgreSQL and Redis, which a GitHub Actions runner cannot. GitHub Actions stays for the weekly harvests that commit data.
- **How:** one scheduled run that calls each step; a failed step does not stop the others.
- **When:** lands together with 2.2.5; gains 2.2.6, 3.2.4.2 and 5.5.5.2 as they land.
- **What for:** housekeeping without manual work (SYSTEM-DESIGN §7).
- `5.4.4.1` Nightly script and its scheduler entry, running 2.2.5.
- `5.4.4.2` `[ ]` [R034](arena/details-p5.md#r034) (weight 84) Cache dir and .env are CWD-relative; a root scripts/ job purges the wrong cache. Fix: Resolve paths against the package directory in Settings.
- `5.4.4.3` `[ ]` [R192](arena/details-p5.md#r192) (weight 55) An in-process nightly scheduler runs once per worker; there is no run lock. Fix: OS scheduler only (cron / Windows Task Scheduler) calling scripts/nightly.py.
- `5.4.4.4` `[ ]` [R207](arena/details-p5.md#r207) (weight 51) No run record: missed nights, overlapping runs and 'failing twice' go unseen. Fix: Per-step run ledger with a run lock.

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
- `5.5.1.2` `[ ]` [R146](arena/details-p5.md#r146) (weight 68) The 5-founder floor counts sessions, so one founder can count several times. Fix: One enrolment per founder per programme: the join code (step 1) issues an enrolment token kept in the browser and sent on every new session; aggregates use the latest session per enrolment.

#### 5.5.2 `[ ]` Reference cohort from the session's own evidence
- **Why:** open projects, trial sponsors and funding route are not used.
- **Where:** `cohort/reference.py`.
- **How:** add the session scan's projects and trial sponsors, and the funding route, to the match.
- **When:** now.
- **What for:** "5 similar in Tamil Nadu, none past pilot" (IDEATION §4.1).
- `5.5.2.1` Evidence-fed matching.
- `5.5.2.2` `[ ]` [R052](arena/details-p5.md#r052) (weight 84) Two TN-startup matchers disagree: Talk says 'no TN startup', Cohort page lists 20. Fix: Single matcher function used by scan and cohort, result stored on the session.
- `5.5.2.3` `[ ]` [R142](arena/details-p5.md#r142) (weight 68) Reference cohort counts filler words as matches, inflating 'N similar startups'. Fix: Require an anchor term with idf above a threshold, and reuse research/terms.py GENERIC.

#### 5.5.3 `[ ]` Programme aggregates the design asks for
- **Why:** the programme view lacks the most common blockers and risks, scheme fit and readiness bands.
- **Where:** `cohort/programme.py`, `Cohort.tsx`.
- **How:** add roadmap risks and blockers, scheme-fit bands and readiness bands to the aggregates, still folded below 5.
- **When:** now.
- **What for:** a programme manager sees where the batch is stuck (IDEATION §4.2).
- `5.5.3.1` Risks and blockers.
- `5.5.3.2` Scheme-fit and readiness bands.
- `5.5.3.3` `[ ]` [R199](arena/details-p5.md#r199) (weight 52) Programme view breaks its own 'groups under 5 are folded' rule for roadmap counts. Fix: Route every count through _grouped / a band helper, plus a Hypothesis test that no output count is 1-4.

#### 5.5.4 `[w]` Programme membership
- **Waiting on:** 3.1 and 3.2.1.
- `5.5.4.1` Who belongs to which batch, instead of pasted session IDs.

#### 5.5.5 `[w]` Session tables, analytics schema, nightly rebuild
- **Waiting on:** 2.1.1 and 2.1.4.
- Also covers the August analytics and impact dashboard (task 5.2): scheme, supplier and funding metrics come from these tables.
- `5.5.5.1` Split session documents into tables by migration.
- `5.5.5.2` `analytics` schema and nightly rebuild.
- `5.5.5.3` `[ ]` [R170](arena/details-p5.md#r170) (weight 61) No rule for keeping split session tables in step with the live JSON document. Fix: Tables as a derived projection rebuilt nightly from the JSON (JSON stays the truth).

### 5.6 Reference data growth

#### 5.6.1 `[w]` Review the 190 draft registry cards
- **Waiting on:** a reviewer who knows the districts.

#### 5.6.2 `[w]` Research signals for batches 2 and 3
- **Waiting on:** the weekly job within OpenAlex's free budget, or a free OpenAlex key.

#### 5.6.3 `[w]` Registry batches 4 to 6
- **Waiting on:** 5.6.1.

#### 5.6.4 `[w]` Weekly jobs open pull requests
- **Waiting on:** the owner enabling "Allow GitHub Actions to create and approve pull requests".

#### 5.6.5 `[ ]` Reference data that says what it is, and lighter weekly jobs
- **Why:** draft registry cards reach founders unlabelled, 'approved' needs no reviewer, districts outside the data are not flagged, the weekly signals job refetches complete years, and weekly pull requests pile up.
- **Where:** `planner/registry.py`, `agents/ideation.py`, registry data, `scripts/`, `.github/workflows/weekly-checks.yml`.
- **How:** carry review state to the conversation and say 'draft' aloud; record reviewer, date and checklist; a 'not covered yet' state for districts; incremental fetches; one fixed branch for weekly pull requests.
- **When:** now; the reviews themselves wait on a reviewer (5.6.1).
- **What for:** founders know what is checked, and the jobs stay within free limits.
- `5.6.5.1` `[ ]` [R022](arena/details-p1.md#r022) (weight 84) Code ignores the 'reviewed' flag; unreviewed draft cards reach founders. Fix: Carry review state to the agent and say 'from a draft card, not yet checked' for draft facts.
- `5.6.5.2` `[ ]` [R185](arena/details-p5.md#r185) (weight 58) No review provenance on cards: 'approved' can be set with no reviewer, date or checklist. Fix: reviewed_by, reviewed_on and checklist results on each approved card, required by test/schema.
- `5.6.5.3` `[ ]` [R087](arena/details-p5.md#r087) (weight 74) Elicitation accepts 38 districts but reference data covers 5, with no plan to grow it. Fix: 'Not covered yet' state for districts outside the data, plus a 5.6 task to add districts by founder demand.
- `5.6.5.4` `[ ]` [R189](arena/details-p5.md#r189) (weight 58) Weekly signals job re-fetches five complete past years for every domain each week. Fix: Incremental: fetch only domains missing or older than N months, oldest first, within a per-run cap.
- `5.6.5.5` `[ ]` [R211](arena/details-p5.md#r211) (weight 45) Weekly job opens a new dated PR each week; unmerged ones pile up and a rerun fails. Fix: peter-evans/create-pull-request with a fixed branch.

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
- `5.7.1.7` `[ ]` [R182](arena/details-p5.md#r182) (weight 58) Five ORM tables nobody reads or writes, one needing pgvector, are missing from 5.7.1. Fix: Drop embeddings and documents (migration + models), delete models/schemas.py and Terrain, keep founders/startups for 3.1.2 reshaped.
- `5.7.1.8` `[ ]` [R213](arena/details-p5.md#r213) (weight 42) Removing services/llm.py leaves orphan settings that still advertise OpenAI. Fix: Delete the three settings and their .env.example lines in the 5.7.1.2 change.
- `5.7.1.9` `[ ]` [R212](arena/details-p5.md#r212) (weight 42) After 1.4.1 the planner still imports from app/swarms, a package the design dropped. Fix: Move the graph functions into planner/graph.py with 1.4.1.3, delete app/swarms.

---

## Owner decisions

| # | Decision | Sources that disagree | Recommendation |
|---|---|---|---|
| D1 | Scheme and investor eligibility: rules or CP-SAT | August spec and master document say CP-SAT; the code, Vanigam-Explained E2 and feasibility survey C say rules | Rules; write the decision record and fix the claims (5.3.3) |
| D2 | `app/orchestrator` and `/orchestrator/route` | August task 1.8 wants an intent router; decisions 0001 and 0002 make the agent the conversation; nothing calls the route | Remove (5.7.1.1); the parked work is on `wip/1.8-orchestrator` |
| D3 | `/ideate` and its placeholder roadmap | Gap analysis D8 fixes `/ideate`; the October design centres `/talk` | One roadmap from the planner (1.4.1) |
| D4 | Session lifetime, and keeping a saved idea | `agents/store.py`: 6 h idle; SYSTEM-DESIGN §5.4: 90 days, longer "only if the founder saves the idea"; rnd-elicitation: 30 days | PostgreSQL keeps a session for 90 days of inactivity; the Redis copy expires by its own 6 h TTL only, and the store never re-hides a session it has just loaded (corrected by arena [R073](arena/details-p2.md#r073)); a saved idea is kept until the founder deletes it (needs 3.1) |
| D5 | Canonical sector list | elicitation enum (12), ecosystem taxonomy, StartupTN categories | Two levels: StartupTN categories as the public top level, the 20 ecosystem sectors as the required second level, with every elicitation value mapped to a sector. The StartupTN list alone has no food, education, retail or manufacturing (corrected by arena [R036](arena/details-p1.md#r036)) |
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
