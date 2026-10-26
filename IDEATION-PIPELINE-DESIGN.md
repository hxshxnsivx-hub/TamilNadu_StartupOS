# Vanigam ideation pipeline: end-to-end design

**Date:** 2026-10-08
**Status:** design. This document says *what* the pipeline does and *why*. It holds no
implementation detail beyond naming the module each stage lives in; build steps live in the
[Ideation Council Build Spec](https://claude.ai/artifact/Qn8smJvnJw6bD2KYE6FSG7).

**Builds on, and does not replace:**

- the elicitation state machine (`backend/app/elicitation`, rnd-elicitation §5.2): NEW → ELICITING ⇄
  AWAITING_ANSWER → CONFIRMING → GENERATING → COMPLETE;
- the two-lane architecture and the 15 properties on the
  [architecture dashboard](https://claude.ai/artifact/R8ugAvKSMA9Trp6MZz1MGe);
- the domain-aware planner and registry (`backend/app/planner`) and the prior-art scan
  (`backend/app/research`).

Two stages are new here: the **novelty check** (with *how to add novelty*) and **cohort analysis**.

---

## 1. The pipeline as one conversation

The founder experiences a single conversation. Underneath, each turn moves the idea through
stages. Stages are not screens: several can happen in one turn, and the slow ones run in the
background while the conversation continues.

| # | Stage | What the founder experiences | Decided by | Lane | Module |
|---|---|---|---|---|---|
| S0 | Open | Greeted by name; profile facts are never asked | code | fast | `agents/ideation` |
| S1 | Understand | Words become facts, each checked against its slot's type; a wrong-type answer is caught and routed; a correction said in passing sticks | code | fast | `elicitation` |
| S2 | Ask | One question per turn, the what before anything else, at most seven questions (re-asks are free), never a skipped one again | code picks, model words | fast | `elicitation/selector` |
| S3 | Evidence | "Let me look at what exists": papers, trials, projects, patents, local startups | code | slow | `research` |
| S4 | Novelty check | Which parts exist, which are rare, which combinations are rare | code | slow | `research/novelty` (new) |
| S5 | Add novelty | Two or three concrete ways to stand out, each tied to a gap | code proposes, council ranks | slow | `research/novelty`, council |
| S6 | Council | Seven advocates judge; one disagreement comes back as a question | model judges, code votes | slow | `agents/council` (Phase 2) |
| S7 | Confirm | The objective is restated in plain words, each fact labelled with where it came from and each gap with what will be assumed; the reply is read for corrections first (locked as founder-given, one question refunded), then for yes or no | code | fast | `elicitation/engine` |
| S8 | Roadmap | Milestones, costs, licences, risks for the chosen variant | code | slow | `planner` |
| S9 | Cohort | How the idea sits among similar startups, and among founders in the same programme | code | offline | `cohort` (Phase 5) |

**Fast lane** = must finish inside the voice budget (about 1 s to first word).
**Slow lane** = background job; results enter the conversation on a later turn.
**Offline** = batch analysis, not part of a live turn.

### 1.1 What every turn does

Every turn of the agent follows one grammar, in this order:

1. **Acknowledge** what the founder said, using their words.
2. **At most one evidence point**, only if something new has arrived since the last turn
   (evidence, novelty map, council verdict). Spoken in one or two sentences; the rest goes to
   the screen.
3. **One question**, normally the question engine's choice.

This keeps a long analysis from arriving as one monologue. A novelty map, for example, is
spread over two or three turns: *what exists* → *where the gap is* → *one way to stand out*.

### 1.2 The conversation stream

A turn is delivered as a stream of events so the voice can start before the reply is finished.

| Event | Carries | Used by |
|---|---|---|
| `ack` | the turn was received, the action chosen (ask, confirm, generate) | orb state → thinking |
| `sentence` | one fact-checked sentence of the reply | speech, captions |
| `tool` | a tool started or finished | screen status line |
| `evidence` | the compact evidence or novelty map, when new | evidence panel |
| `done` | full reply, next question, known facts, tools used | screen, logs |
| `error` | a `code` (`conflict`: changed elsewhere, reload; `failed`) and what failed | screen |

Only `sentence` events are spoken, and only after the fact check (§3.2).

On a weak connection (task 1.1.4): a turn is saved only when `done` is sent, so a stream that
ends without `done` was not applied, and the screen sends it again with the same
`client_turn_id`. The session keeps its last turn's ack, sentences and `done`; a retry of that
turn replays them instead of running it twice. The snapshot carries the pending action (what
the founder is being asked), results that finished while nobody listened, and after 30 minutes
away a short preamble that repeats the pending question without spending the question budget.

---

## 2. Novelty: what it means here

### 2.1 Definition

Vanigam never says an idea is "new" or "unique". It can only say what was and was not found,
in which sources, on which date. Novelty is therefore **relative to the sources searched** and is
assessed at three levels:

| Level | Question | Evidence |
|---|---|---|
| **Element** | Does each part of the idea exist on its own? | papers, projects, trials per element |
| **Combination** | Do the parts exist *together*? | papers and projects matching both parts at once |
| **Context** | Does it exist here: in India, in Tamil Nadu, for this user group, at this price? | India-affiliated papers, TN startups, registry |

The most common real novelty for a Tamil Nadu founder is not a new invention. It is a **known
part used in a rare combination**, or a **known solution brought to a context that lacks it**.
The design makes both visible.

### 2.2 The novelty check (S4)

Inputs: the idea, its elements (two to six parts, from the founder or split by the model),
and the evidence pack.

1. **Element map.** Each element is labelled from paper counts (already built):
   crowded (≥ 5,000, or ≥ 1,000 with ≥ 50 projects), active (≥ 300), sparse (> 0),
   nothing found, or not searched. Elements are what is built: who is served ("farmers",
   "physically challenged") is left to the re-target lever, and a part that only restates
   another more broadly ("solar" beside "solar inverters") is dropped. A zero on a single
   name is labelled *not searched well* (the literature uses another name), not a gap.
2. **Combination map.** For each pair of elements, search both together. Rarity of the pair:

   `rarity = pair_count / min(count_a, count_b)`

   A pair is a **gap** when both elements are active or crowded on their own, the pair has
   fewer than 300 papers, and either the rarity is below 2% or the pair count is under 30.
   "Both parts are well studied; together they are rare." The absolute limit matters: 1,118
   papers is not rare even when it is 1.5% of a field of 74,000. The number of elements is
   capped at 6, so at most 15 pair searches, all cached. Each part is searched as its technical
   names joined by OR, with multi-word names in quotes; OpenAlex reads a space as AND, so a pair
   is both parts' searches side by side.
3. **Context map.** For the whole idea: share of matching papers with an Indian institution;
   matching TN startups; matching registry domains. **Context gap** when the idea is active
   globally but India's share is under 5% and none of the startups searched matches. The
   startups searched are named with the claim (today the 654 on the Tamil Nadu Startup Map in
   Chennai, Coimbatore and Madurai); a failed lookup makes no claim.
4. **Novelty statement.** One of these types, with the evidence that supports it:

   | Type | Meaning | Typical wording |
   |---|---|---|
   | `combination` | known parts, rare together | "EEG spellers and nurse-call systems are both well studied; I found very little that joins them." |
   | `context` | exists elsewhere, rare here | "This exists abroad; I found almost nothing from India, and none of the 654 startups on the Tamil Nadu Startup Map in Chennai, Coimbatore and Madurai does it." |
   | `element` | one part is sparse | "Medication requests by brain signal is the rare part." |
   | `crowded` | every part crowded, every pair and the context counted | "This space is busy; the edge has to come from cost, users or the business model." |
   | `active` | parts well studied but not all crowded, every pair counted | "Each part is actively studied, and the combinations I counted are studied too." |
   | `unclear` | too little was searched: papers not searched, one part only, a pair not counted, or no part the vocabulary knows | "I could search only one part on its own, so I can't say how new the idea is as a whole." |

   Every statement carries the caveat: *not found in these sources is not proof of novelty;
   have a patent attorney search before filing.*

### 2.3 How to add novelty (S5)

From the novelty map, code proposes **levers**. Each lever must point to the gap that justifies
it; a lever with no supporting gap is not offered.

| Lever | Offered when | Example |
|---|---|---|
| **Combine** | a combination gap exists | add nurse-call integration to an EEG speller |
| **Localise** | a context gap exists | Tamil-language interface, TN hospital workflow, rural power and network |
| **Re-target** | papers name one user group, the founder's beneficiary is another | ICU patients instead of ALS patients at home |
| **Cost-down** | a deep pack or costing shows a lever | consumer EEG instead of clinical-grade, with the accuracy trade-off stated |
| **Business model** | crowded technology, sparse delivery | a service for hospitals rather than a device sale; scheme-backed rollout |
| **Regulatory route** | the idea is a medical device or clinical product: a health word or trials, plus a device or clinical signal (`terms.is_health_product`, shared with the panel) | start as a communication aid, then a medical device |

The novelty check keeps each lever as its kind and the facts behind it (the pair and its count,
the India share, who is served, the trials, the domain with a cost pack). The words are chosen
when the lever is said (`research/levers.py`), from the founder's sector and the one matched
registry domain that the scan, the panel and the roadmap share: a food brand hears "local tastes
and shop routines", a health device "hospital and clinic routines". A sector answered after the
search rewords the lever with no new search; the numbers still come only from the facts.

The council's prior-art and customer seats rank the levers (Phase 2). Until then they are
ranked by gap strength. The founder chooses; a chosen lever becomes a new idea version.

---

## 3. Fixing the disadvantages: the design decisions

Every disadvantage on the dashboard has a fix in the build spec. This section records the
design decision for the Phase 1 fixes, and the new disadvantages that come with novelty and
cohort analysis.

### 3.1 Answer check (question engine)

**Problem:** a reply is stored in the asked slot even when it does not fit ("Chennai" stored as
the stage).
**Decision:** each slot declares what a valid answer looks like. A reply that does not fit the
asked slot is offered to the extractor instead (so "Chennai" becomes the district), the
question stays open, and it is asked once more, acknowledging the fact just learned. After two
misses the question is dropped for good. A direct, valid answer still always beats an earlier
guess (unchanged rule).

**Question order and fact safety (task 1.1.3).**
- *Order.* Until the idea is known (problem or solution), only WHAT questions are asked, so
  capital is never asked before what it is for. Then required slots, then the WHY finger (any of
  why now, what is different, motivation; a pitch that already said why is not asked), then
  enrichment, and enrichment only before the first restatement. The choice is greedy by value;
  the CP-SAT solver runs only when a burden budget binds.
- *Budget.* Seven questions, counted as questions: a re-ask, a request for a view and a reply to
  the restatement do not use it; a correction gives one back.
- *Three bands.* Known (0.60 and up) is a fact; confirm (0.50 to 0.60) is not asked but said
  back as "I assumed"; below 0.50 is asked.
- *Every value is typed.* Extractor, profile, answer and model note all pass the slot's type
  check before they are stored; a value that fits no slot is rejected.
- *Model notes.* A noted text fact, skill, asset or district must be in the founder's words.
  The tool reply says truthfully whether the note was recorded, kept the earlier value, or is
  disputed: two inferences that disagree drop below the confirm band, so the founder is asked.
- *Negation and corrections.* "No customers yet" is not revenue; "Salem, not Erode" is Salem;
  "I live in Salem but sell in Coimbatore" is Salem. "Sorry, actually ..." makes a changed fact
  the founder's answer.

### 3.2 Fact check before speech (conversation engine)

**Problem:** the model may say a number, scheme, trial or project that is not in the session.
**Decision:** before a sentence is spoken, every number, scheme name and evidence identifier in
it must exist in the session (evidence, known facts, roadmap). A failing sentence is dropped,
not corrected. Novelty words ("unique", "first of its kind", "no one has done") are replaced
with the standard caveat. If every sentence fails, the templated reply is used. The check is a
pure function: no model call, so it can sit on the voice path.

### 3.3 No idea text leaves the platform (evidence)

**Problem:** when the lexicon finds no technical term, the query builder falls back to the
founder's own sentence, which is then sent to OpenAlex, GitHub and the other sources.
**Decision:** outgoing queries contain only lexicon terms, technical terms and research-field
words; never the founder's sentence, names, places or numbers. If nothing safe remains, that
source is reported as *not searched (nothing safe to send)*. A session can be **private**: no
external source is called, and coverage says so.

### 3.4 Sessions saved (session state)

**Problem:** conversations live in memory and vanish on restart.
**Decision:** a store interface with two implementations: memory (tests, offline dev) and
database (default when a database is configured). Saved per session: the elicitation session
(facts with source and confidence, turns, skipped questions), the agent's message history, the
current evidence, roadmap, privacy flag and idea version, as one JSON document per session
(decision [0003](docs/decisions/0003-sessions-as-json-document.md)). Writes check a version
number so two writers cannot overwrite each other silently. Sessions expire after six hours
idle, as now: an expired session answers 410 (still stored, and deletable from the Talk page),
an unknown or deleted one 404. When no database is available, conversations are kept in memory and the start
response says `saved: false`.

### 3.5 Streamed replies (conversation engine)

**Problem:** the reply arrives only when complete, so speech cannot start early.
**Decision:** a streaming endpoint emits the events in §1.2. The reply is split into sentences
as it streams; each sentence passes the fact check before being sent. The existing
non-streaming endpoint stays for text clients and tests. Without a model key, the templated
reply is streamed sentence by sentence through the same path.

### 3.6 New disadvantages from novelty and cohort analysis

| Disadvantage | Fix |
|---|---|
| Pair searches multiply calls (15 pairs) | Cap at 6 elements; pairs run in the slow lane, cached seven days, and only after the element map |
| Search counts are noisy, so "rare" can be a wording artefact | Use technical terms per element; require both a low ratio and a low absolute count; show counts, not just labels |
| India share depends on affiliation data, which is incomplete | Label it "India-affiliated papers"; treat it as a hint and pair it with the TN startup check |
| Levers can sound generic | A lever is offered only with the gap that justifies it, named in the sentence |
| Founders may over-read a gap as a guarantee | The caveat travels with every novelty statement; the council's devil's advocate tests each lever |
| Cohort data is personal and commercially sensitive | Founder consent per session; cohort views show aggregates only, never a group smaller than 5; no idea text in cohort views |
| Cohort comparisons can shame weaker founders | Show bands and next steps, not rankings of named founders |

---

## 4. Cohort analysis (S9)

Two meanings, both needed:

1. **Reference cohort: similar startups and projects.** Where does this idea sit among the TN
   startups, open projects and trial sponsors that look like it: their stage, district, funding
   route and age? Built from the ecosystem data, the TN Startup Map and the evidence pack.
   Output: "Five similar startups in Tamil Nadu, three in Chennai, mostly at prototype stage;
   none has gone past a pilot."
2. **Programme cohort: founders going through the same programme** (an incubator batch, a
   TANSEED round, a college cell). Aggregates their sessions for the programme manager:
   categories and districts, crowded-versus-gap mix, the most common blockers and risks, scheme
   fit and readiness bands. Built from saved sessions, so it depends on §3.4, and only from
   sessions whose founders consented.

Cohort analysis is offline: it never runs inside a live turn.

---

## 5. Phases

| Phase | Scope | Depends on |
|---|---|---|
| **1** | answer check · fact check · no idea text leaves · sessions saved · streamed replies | — |
| **1b** | novelty check (element, combination, context maps) and levers, spoken over turns. *Done 2026-10-09; until Phase 2's background jobs, it runs in the same turn as the evidence search* | 1 |
| **2** | council: seven seats, vote, synthesis, scheduler; council ranks levers. *Council done 2026-10-10 (2a), wired in 2d: it meets inside the turn when the founder asks for a view, before the roadmap, and (without a model, in milliseconds) right after the novelty check; its question joins the question engine and its objections raise roadmap risks. Background jobs (2b) done 2026-10-14: research and the panel run on a job board; a turn waits briefly, else the result enters a later turn (decision 0010). Lever ranking done 2026-10-26 (task 1.3.1): every lever reaches the panel by a stable id, the seats score them, the vote orders them and the narrator speaks the top three; the panel waits for finished research, model seats answer in one call, and a private session is judged by rule seats only.* | 1, 1b |
| **3** | voice and orb | 1 (streaming) |
| **4** | Indian patents, registry growth, weight tuning, evaluation | 2 |
| **5** | cohort analysis: reference cohort, then programme cohort | 1 (saved sessions), 1b |

## 6. Phase 1 is done when

- Answering "Chennai" to the stage question fills the district, leaves the stage open and asks
  again once; a second wrong answer drops the question.
- No spoken sentence contains a number, scheme or evidence ID absent from the session, across
  the test turns, including turns built to provoke one; novelty words never reach speech.
- No outgoing search query contains a word from the founder's text that is not a lexicon or
  field term; a private session makes no external call.
- A session survives a server restart and resumes at the same question; concurrent writes do
  not silently overwrite each other.
- The streaming endpoint emits `ack`, then fact-checked `sentence` events, then `done`, with and
  without a model key.
