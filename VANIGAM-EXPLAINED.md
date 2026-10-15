# VANIGAM — The Complete Explanation
### Tamil Nadu StartupOS · explained end-to-end, phase by phase, task by task

**Version 1.0 · 2026-07-19**
This document exists so you can *explain* the project to anyone — a judge, an investor, a professor, a teammate. Part A–E explain the whole system. Part F breaks every phase into its tasks, and answers **What / Where / Why / How / When** for each, plus its **mechanism, workflow, tech stack and algorithm**.

---

## How to read this

| Part | Answers |
|---|---|
| **A** | What is Vanigam, in one page |
| **B** | What it actually does — as points |
| **C** | Who uses it and for what (utilization) |
| **D** | How it works, end to end (one request's journey) |
| **E** | The core engines and their algorithms |
| **F** | **Phase 1 → 6**, each broken into tasks with W/W/W/H/W |
| **G** | Master tech stack, glossary, build status |

---

# PART A · THE PROJECT AT A GLANCE

**What it is.** Vanigam (வணிகம், "commerce") is a multi-agent AI operating system for startup founders in Tamil Nadu. One conversational platform carries a person from *"I have nothing but experience"* → *registered company* → *funded, supplied, growing business* — in English, Tamil or Hindi, by text or voice.

**Why it exists.** A founder faces four locked doors, and the keys are scattered across forty government portals in legal English:
1. *What do I build?* — no map.
2. *Which scheme actually funds me?* — buried eligibility rules; months wasted on wrong applications.
3. *Who can I trust to supply me?* — sourcing is word-of-mouth.
4. *Am I investor-ready, and for whom?* — pure guesswork.

Fragments exist (Startup India, myScheme, IndiaMART, AngelList). **Nothing unites them with caste/gender/merit-aware scheme logic, a startup-context B2B network, and Tamil-first voice access.** The gap is the synthesis.

**Where it runs.** A FastAPI backend on PostgreSQL (+pgvector +PostGIS), Redis and S3, with LangGraph agent swarms and an OR-Tools constraint engine; delivered as a web PWA that works offline and on 2G.

**When it ships.** Six phases. MVP in 22–32 weeks; Phase 6 (Living Intelligence) post-MVP to ~week 40.

**The one-sentence thesis.**
> Every recommendation — scheme, supplier or investor — is *proven* valid before the founder sees it, and every rejection names its exact reason, in the founder's own language.

---

# PART B · WHAT IT DOES — as points

1. **Builds a founder profile** from forms, uploaded documents, and AI inference — and scores its completeness at 40 / 60 / 80 / 100%, unlocking features as it grows.
2. **Generates startup opportunities for people with no idea** — from their work experience, skills, capital and district.
3. **Validates and structures an idea** into problem, solution, market, value proposition, differentiation — with a 0–100 feasibility score.
4. **Produces a roadmap** of 5–15 milestones with dependencies, a critical path, and three timeline estimates — shaped by *terrain* (urban tech / rural micro / academic / deep-tech).
5. **Verifies legal identity** — CIN, DPIIT recognition, GSTIN — through licensed KYC channels and DigiLocker.
6. **Reads and verifies documents** via OCR — PAN, community certificate, incorporation, mark sheets — with confidence gating and manual-review fallback.
7. **Proves scheme eligibility** across 100+ central, Tamil Nadu and bank schemes — no false positives, and a named reason for every rejection.
8. **Ranks eligible schemes** by relevance *and* by this founder's real likelihood of approval.
9. **Annotates the roadmap** with the 3–5 schemes that apply at each milestone — so the founder knows *when* to apply for *which* money.
10. **Tracks applications** through In Progress → Submitted → Under Review → Approved → Disbursed, with deadline reminders.
11. **Decomposes a product** into its raw materials, components, services and machinery — even if the founder never wrote a Bill of Materials.
12. **Matches B2B partners** on a weighted bipartite graph — specification, price, capacity, geography — filtered to only feasible, capacity-respecting allocations.
13. **Scores partner trust** from real collaboration feedback with 6-month-half-life decay, and feeds it back into matching.
14. **Manages collaborations** from proposal to completion — documents, messaging, metrics, closing feedback.
15. **Assesses funding readiness** across six dimensions (Team, Product, Traction, Financial, Pitch, Legal) with a spider chart.
16. **Generates a gap-fix plan** — 3–5 actions per weak dimension, ranked by impact ÷ effort.
17. **Matches investors** whose hard rules the startup actually satisfies, then **sequences the money** as a strategy (grant → prototype → VC) with anti-double-dipping and over-raise guards.
18. **Accepts proxy traction** — LOIs, pilots, hackathon wins, publications — so pre-revenue founders aren't excluded.
19. **Re-versions roadmaps automatically** when a government scheme's rules change, and notifies the founder.
20. **Speaks Tamil, Hindi and English** — text and voice — and tolerates Tanglish/Hinglish code-mixing.
21. **Works offline and on 2G**, with SMS fallback for deadline alerts.
22. **Explains itself always** — which constraints were met, which failed, and what to do next.

---

# PART C · UTILIZATION — who uses it, for what

| User | Enters at | Uses it to | Gets |
|---|---|---|---|
| **Experience-only person** (weaver, farmer, IT professional) | Category 1, "intent-only" mode | Discover *what business to start* | 3–5 ranked opportunities with capital band + eligible schemes → a roadmap |
| **Idea-stage founder** (student, first-timer) | Category 1, "idea" mode | Validate and plan | Structured concept, feasibility score, milestone roadmap with scheme annotations |
| **Registered startup with a product** (2A) | Category 2 | Find money, stay compliant | Proven-eligible ranked schemes, application tracking, deadline alerts |
| **Registered but product-less** (2B) | Category 2 → 1 | Find a direction while already incorporated | Schemes unlocked day-one + discovery flow |
| **Manufacturing / hardware startup** | Category 3 | Source materials, find partners | Product decomposition → Supply Feasibility Map → capacity-valid matches with trust scores |
| **Service startup** | Category 3 (Tier 2) | Trade services, sometimes by barter | Barter-compatible matches |
| **Funding-stage startup** | Category 4 | Become and prove investable | Readiness score, gap plan, constraint-matched investors, sequenced funding strategy, pipeline |
| **Scheme curator** (internal) | Admin | Keep scheme data true | Monitored sources, LLM-drafted diffs, PR review, freshness SLA |
| **Investor-relations manager** (internal) | Admin | Maintain investor data | Curated, cited, staleness-tracked investor records |
| **StartupTN / ecosystem partner** | Analytics | Measure impact | Schemes applied/approved, collaborations formed, funding raised |

---

# PART D · HOW IT WORKS — one message, end to end

Every interaction follows seven stages. This is the single most useful thing to memorise when explaining the system.

1. **Capture & normalise.** Voice is transcribed (re-ask below the confidence threshold); the script is detected; romanised Tanglish is transliterated to Tamil; non-English is translated to English with domain terms protected.
2. **Classify & route.** A confidence cascade labels the intent (Profile / Idea / Scheme / B2B / Funding …). Above threshold it routes to the owning swarm; below it, one clarifying question. Guardrails screen for PII and prompt injection.
3. **Decompose & dispatch.** The swarm supervisor splits the task across sub-agents — parallel where independent, sequential where dependent — with retries and backoff.
4. **Prove, match, verify.** The deterministic engines run: the rules layer decides eligibility, CP-SAT optimises allocations and portfolios, the graph funnel returns ranked partners, registries confirm identity.
5. **Persist & cache.** Results, state and audit records to PostgreSQL; vectors to pgvector; hot data to Redis; documents encrypted in S3.
6. **Aggregate & validate.** The supervisor merges sub-agent output, checks completeness, and attaches explanations (constraints met and violated, by name).
7. **Respond in the founder's language.** Translated back with glossary restored; rendered as text, roadmap, scheme cards, match lists, Kanban, or speech. The context stack keeps the task resumable for 30 minutes.

**Economics:** ~60% of turns are simple (answered by a small model directly), ~30% engage one swarm, ~10% several — blended **≈ ₹3.4 per turn** with caching and routing, versus ≈ ₹27 naive.

---

# PART E · THE CORE ENGINES & THEIR ALGORITHMS

### E1 · Central Orchestrator (LangGraph)
- **Mechanism:** a state machine whose nodes are conversation states and whose conditional edges route to swarms. `ConversationState` holds user, session, messages, intent, entities, active swarm, entry mode, context stack, language.
- **Algorithm — confidence cascade routing:** keyword filter → embedding router → fine-tuned IndicBERT classifier → LLM fallback when confidence < 0.5. Auto-route above 0.8. This clears >80% intent accuracy cheaply.
- **Why this way:** a single classifier is fragile on code-mixed and out-of-distribution input; the cascade is 65× cheaper than calling an LLM every turn.

### E2 · Eligibility — the rules layer (not the solver)
- **Mechanism:** scheme eligibility is **deterministic predicate evaluation**, not search. Every input is known, so a decision table / rule-tree evaluates it in microseconds.
- **Algorithm:** `eligible(scheme) = combinator(rules[])` where each rule is `{field, operator, value}` over the profile; compound rules use AND/OR/NOT groups. Failing predicates are returned verbatim as the rejection reason.
- **Why:** a constraint solver searches over *unknowns* — there are none here. Rules are faster, auditable by scheme officers, and give "why not" for free.

### E3 · CP-SAT Boundary (OR-Tools) — where the solver *does* earn its place
- **Used for:** B2B allocation (capacity, minimum orders, soft geographic penalties), investor **portfolio** validity (mutual exclusion between schemes that cannot be combined, over-raise ceiling).
- **Algorithm:** boolean/integer decision variables + hard constraints + soft constraints with penalties; objective maximises Σ(match quality) − penalties. Infeasible models relax soft constraints iteratively and report what was relaxed.
- **Why:** these *are* combinatorial optimisation problems with genuine unknowns.

### E4 · Graph Engine — the three-stage matching funnel
- **Mechanism:** never touch the whole graph. Narrow, then score, then optimise.
- **Algorithm:**
  1. **Block** (5–20 ms): SQL on tier/domain/sector + PostGIS `ST_DWithin` radius + capacity > 0 → 100k candidates become ~2–5k.
  2. **Score** (5–15 ms): pgvector HNSW top-200 on specification embeddings, then vectorised composite weight
     `w = 0.40·spec_similarity + 0.30·price_fit + 0.20·capacity_fit + 0.10·geo_proximity`, weights configurable per sector, trust adjusting ±20%.
  3. **Allocate** (batch, async): scipy `min_weight_full_bipartite_matching` (LAPJVsp) for 1:1, OR-Tools min-cost-flow for capacity-constrained many-to-one, CP-SAT for rich constraints.
- **Result:** point queries ≈ **30 ms p50** against a 1 s budget.

### E5 · Trust Score
- **Algorithm:** `trust = 0.25·delivery + 0.30·quality + 0.20·communication + 0.15·pricing + 0.10·overall`, normalised 0–100, aggregated across collaborations with **exponential decay, 6-month half-life**; new startups initialise at 50; anomalous feedback flagged.

### E6 · Readiness & Ranking
- **Readiness:** six rubric-scored dimensions → `0.20·Team + 0.20·Product + 0.25·Traction + 0.15·Financial + 0.10·Pitch + 0.10·Legal`; banded Not Ready / Developing / Ready / Highly Ready at 40/60/80.
- **Scheme relevance:** `0.30·funding-match + 0.25·stage + 0.20·domain-fit(embedding) + 0.15·deadline-urgency + 0.10·success-rate`.
- **Approval likelihood:** preference-axis match × historical success rate × profile strength − competition proxy.
- **Investor fit:** `0.30·sector + 0.25·stage + 0.20·traction + 0.15·geography + 0.10·track-record`.

### E7 · Roadmap generation
- **Algorithm:** milestones are a DAG. **Topological sort** orders them; the **longest path** through the DAG is the critical path. Timelines are estimated three ways (optimistic/realistic/pessimistic) conditioned on domain, complexity and founder experience.

### E8 · Language stack
- **Embeddings:** BGE-M3 (1024-dim, multilingual, retrieval-trained) behind the `EmbeddingService` interface; IndicBERT retained *only* as the intent classifier.
- **Translation:** IndicTrans2 with **glossary placeholder masking** — domain terms are replaced by sentinels, translated, then restored and validated.
- **Code-mixing:** Unicode script check → IndicLID (romanised Indic detection) → IndicXlit transliteration with a protect-list → LLM fallback below confidence.
- **Quality gates:** Tamil is measured with **chrF++ ≥ 50 and COMET ≥ 0.75**, not BLEU (BLEU under-scores agglutinative Tamil); glossary hit-rate ≥ 90%.

### E9 · Verification
- **Mechanism:** a `VerificationGateway` with swappable vendor drivers. Aadhaar is **never** OCR'd — identity flows through DigiLocker consent or offline eKYC, storing only a masked number and salted hash. CIN/GSTIN get free regex/checksum pre-filters before any paid API call. Circuit breakers + exponential backoff protect every external call.

---

# PART F · PHASE-BY-PHASE BREAKDOWN

> Format per task — **What · Why · Where · How · When**, then **Workflow**, **Tech**, **Algorithm**.

---

## PHASE 1 — FOUNDATION & IDEATION
**Goal:** the platform can hold a founder, understand three languages, and turn an idea (or bare experience) into a roadmap.
**Weeks:** 1–8 · **Category:** 1 · **Exit:** a founder registers, builds a profile to 40–100%, describes an idea or experience in Tamil, and receives a milestone roadmap.
**Why this phase is first:** every later phase consumes these primitives, and Category 1 is the only pillar with **zero external-registry dependency** — so value ships before any vendor contract exists.

### Task 1.1 — Project setup & infrastructure ✅ built
- **What** Python project skeleton + PostgreSQL 16 (pgvector, PostGIS), Redis, MinIO, structured JSON logging.
- **Why** Nothing runs without state, cache, object storage and observability.
- **Where** `backend/`, `docker-compose.yml`, `app/core/config.py`, `app/core/logging.py`.
- **How** Docker Compose brings up the three services; Pydantic-Settings reads a typed `.env`; a JSON formatter writes to stdout and file.
- **When** Week 1, no dependencies — the true starting point.
- **Workflow:** define dependencies → compose services → health-check each → typed settings → logging.
- **Tech:** Python 3.11, Docker Compose, PostgreSQL 16 + pgvector + PostGIS, Redis 7, MinIO, Pydantic-Settings.
- **Algorithm:** none (infrastructure).

### Task 1.2 — Founder & startup schema ✅ built
- **What** `founders`, `startups`, `documents`, `profile_completeness` tables with constraints, indexes, soft deletes; Alembic baseline migration.
- **Why** The data contract every swarm reads; integrity is enforced at the lowest layer so no agent can corrupt it.
- **Where** `app/models/*.py`, `app/db/migrations/versions/0001_initial.py`.
- **How** SQLAlchemy 2.0 declarative models with CHECK constraints (email/phone/CIN format, non-negative revenue), unique keys on email/phone/CIN/DPIIT/GSTIN, FK cascades, and indexes on the fields swarms filter by.
- **When** Week 1–2, after 1.1.
- **Workflow:** model → constraints → indexes → migration → verify DDL.
- **Tech:** SQLAlchemy 2.0 (async), Alembic, PostgreSQL.
- **Algorithm:** none; relational integrity rules. *(Verified: 4 tables, 8 CHECKs, 4 FKs, 11 indexes.)*

### Task 1.3 — Profile Swarm & CompletenessScorer ✅ built
- **What** Agents that collect profile data, verify it, and score completeness at 40/60/80/100%.
- **Why** Completeness *gates* scheme eligibility — a richer profile unlocks more money, so the score is a motivator, not bureaucracy.
- **Where** `app/services/completeness.py`, `app/swarms/profile/`.
- **How** Cumulative tiers: 40 = basic demographics, 60 = + education, 80 = + startup details, 100 = + a verified document. A tier is only reached when every lower tier is satisfied.
- **When** Weeks 2–3, after 1.2.
- **Workflow:** collect → verify → score → emit missing-fields for the *next* tier only → score change triggers scheme re-evaluation.
- **Tech:** Pydantic v2, LangGraph supervisor, pytest.
- **Algorithm:** monotone tier gate — `basic → +education → +startup → +docs`, each conditional on the previous. Returns `{score, tier, missing_fields, verified_fields}`. *(7 unit tests, incl. "verified docs without startup details must not jump to 100".)*

### Task 1.4 — Document Verifier (OCR)
- **What** Upload → OCR → field extraction → authenticity check → profile update.
- **Why** Verified documents turn *claimed* eligibility into *provable* eligibility (First-Graduate, caste category need documentary proof).
- **Where** `app/services/documents/`, S3 storage.
- **How** Cloud OCR primary with local fallback; confidence <80% on a critical field flags manual review; name matching at ≥90% similarity using **transliteration-aware** normalisation (a Tamil-script name vs a Latin one must be normalised before comparison, or legitimate users are rejected).
- **When** Weeks 3–4, after 1.1 and 1.3.
- **Workflow:** upload to encrypted S3 → OCR → classify document type → extract fields → validate → update profile → or queue for human review.
- **Tech:** Google Document AI / vision-LLM (cloud), Tesseract (fallback), boto3/MinIO, encrypted S3.
- **Algorithm:** confidence-gated extraction + fuzzy name match with script normalisation; graceful degradation chain (cloud → local → human).

### Task 1.5 — Translation Service
- **What** en ↔ ta ↔ hi translation that never mangles domain terms.
- **Why** Tamil-first is the moat; "funding" or "DPIIT" turning to garbage destroys trust.
- **Where** `app/services/translation.py`.
- **How** **Glossary placeholder masking**: domain terms → non-splitting sentinel tokens → translate → restore in target language → validate restoration (reordering in Tamil/Hindi can drop a placeholder).
- **When** Weeks 2–4, parallel (needs only Redis).
- **Workflow:** detect language → mask glossary → translate → restore → validate → cache by (hash, src, tgt) for 7 days.
- **Tech:** IndicTrans2 (1B for quality / 200M distilled for latency) or a managed Indic API; Redis cache; sacreBLEU + COMET in CI.
- **Algorithm:** sentinel masking + restoration validation. **Quality gate: chrF++ ≥ 50, COMET ≥ 0.75, glossary hit-rate ≥ 90%** (not BLEU, for Tamil).

### Task 1.6 — Embedding Service
- **What** Multilingual sentence embeddings for semantic search, domain fit, spec similarity, sector alignment.
- **Why** One service, three consumers (schemes, B2B, investors) — semantic meaning is the connective tissue.
- **Where** `app/services/embeddings.py`, pgvector tables.
- **How** BGE-M3 (1024-dim) served via a CPU-friendly inference server; query/passage asymmetry handled *inside* the interface so callers can't get it wrong; Redis cache 7-day TTL; HNSW indexes in pgvector.
- **When** Weeks 2–4, parallel.
- **Workflow:** `embed(text, kind=query|passage)` → normalise → cache → store/query pgvector.
- **Tech:** BGE-M3, sentence-transformers / text-embeddings-inference (ONNX int8), pgvector HNSW, Redis.
- **Algorithm:** cosine similarity on L2-normalised vectors; ANN retrieval via HNSW. Target p95 ≤ 100 ms per query embed.

### Task 1.7 — Roadmap Swarm
- **What** Idea → structured concept → feasibility score → 5–15 sequenced milestones with a critical path.
- **Why** This is Category 1 — the first thing an idea-stage founder needs, and the spine that Phase 2 hangs scheme annotations on.
- **Where** `app/swarms/roadmap/`.
- **How** Four sub-agents in sequence: IdeaExtractor → FeasibilityAnalyzer → MilestoneGenerator → dependency resolver. Missing concept elements trigger clarifying questions rather than guesses.
- **When** Weeks 4–6, after 1.5.
- **Workflow:** translate → extract (problem/solution/market/value/differentiation) → score feasibility → generate milestones per phase → topologically sort → mark critical path → persist.
- **Tech:** LangGraph, LLM for extraction/generation, PostgreSQL.
- **Algorithm:** **topological sort** for dependency order; **longest-path** through the DAG for the critical path; three-point timeline estimation (optimistic/realistic/pessimistic) conditioned on domain, complexity and experience.

### Task 1.8 — Central Orchestrator
- **What** The LangGraph state machine that makes five swarms feel like one assistant.
- **Why** Without it, the founder must know which tool to open; with it, they just talk.
- **Where** `app/orchestrator/`.
- **How** Nodes per conversation state; conditional edges route on classified intent; a **context stack** lets a founder pause a roadmap to ask about schemes and return; sessions idle 30 minutes suspend with saved state (Postgres checkpointer).
- **When** Weeks 5–7, after 1.3 and 1.7 exist to route to.
- **Workflow:** message → normalise → classify → route → swarm → aggregate → respond → checkpoint.
- **Tech:** LangGraph + PostgresSaver, IndicBERT classifier, guardrails, Langfuse tracing.
- **Algorithm:** confidence-cascade intent classification (see E1); stack-based context switching; parallel fan-out via LangGraph `Send` so swarm wall-time = max(sub-agent), not sum.

### Task 1.9 — API v1
- **What** `/auth`, `/profiles`, `/startups`, `/ideation` endpoints with validation, uniform errors, rate limiting.
- **Why** The contract the frontend builds against; uniform errors and limits from day one avoid retrofitting security.
- **Where** `app/api/v1/`.
- **How** FastAPI routers per domain; Pydantic request/response models (422 on validation failure); a standardized `ErrorResponse` envelope with `request_id` and recovery `suggestions`; 100 req/min/user.
- **When** Weeks 6–8, after 1.3/1.7/1.8.
- **Workflow:** request → auth → validate → orchestrator/service → serialise → error middleware wraps failures.
- **Tech:** FastAPI, Pydantic v2, JWT + bcrypt, slowapi/Redis rate limiting.
- **Algorithm:** none; JWT with refresh rotation and RBAC.

### Task 1.10 — Experience-based Opportunity Discovery *(v1.1)*
- **What** The "I have experience, not an idea" path — the entry that serves Selvi the weaver.
- **Why** The first-generation founder that TN schemes exist for often has **no idea at all**; without this they cannot even enter the platform.
- **Where** `app/swarms/roadmap/experience.py`, `opportunity_bank` table.
- **How** `ExperienceProfiler` collects sector, years, roles, skills, capital, assets, district, risk appetite (financial data under separate consent + encryption). `OpportunityGenerator` ranks a curated Opportunity Bank against it.
- **When** Weeks 6–8; scheme pre-check completes in Phase 2.
- **Workflow:** profile → match bank → CP-SAT/rules scheme pre-check → cited web research for demand → rank → 3–5 opportunity cards → selection pre-fills the idea pipeline.
- **Tech:** embeddings, rules layer, curated Opportunity Bank (same editorial pipeline as schemes).
- **Algorithm:** `fit = 0.35·experience-match(embedding) + 0.25·capital-feasibility + 0.20·scheme-availability + 0.10·market-demand + 0.10·location-fit`.

### Tasks 1.11–1.13 — Entry lattice, Terrain modes, Peer discovery *(v2)*
- **1.11 Entry lattice — What** three entry modes (idea / domain-only / intent-only) × three registration subtypes (2A registered+product, 2B registered-but-product-less, 2C idea-worker-no-company). **Why** "incorporated but empty" is a real and ignored Indian case. **How** two enum fields set by two questions; LangGraph conditional edges route on them. **When** Week 6–8.
- **1.12 Terrain modes — What** roadmap templates differ by terrain (urban_tech / rural_micro / academic_spinoff / deep_tech). **Why** one journey template does not fit Bharat. **How** a rules-based classifier (district × domain × education), founder-overridable; versioned YAML template families; the annotator biases scheme emphasis per terrain. **Algorithm:** classification → template selection → parameterised generation.
- **1.13 Peer discovery & live demo — What** "find startups like mine", a homepage live-eligibility widget, gamified tier badges. **Why** near-free reuse of existing embeddings, and the widget proves value before signup. **How** consent-gated pgvector ANN; an ephemeral, rules-only, non-persisted eligibility preview.

---

## PHASE 2 — REGISTERED STARTUP & SCHEMES
**Goal:** prove who a startup is, and prove which money it can get.
**Weeks:** 9–14 · **Category:** 2 · **Exit:** a verified startup receives a ranked, proven-eligible scheme list in <10 s with plain-language reasons, and roadmap milestones carry scheme cards.
**Why second:** it is the flagship value and it feeds Category 1's annotations — but it needs Phase 1's profiles, embeddings and translation first.

### Task 2.1 — Legal Validation Service
- **What** CIN, DPIIT and GSTIN verification.
- **Why** Most schemes require a registered entity; verification is what unlocks them.
- **Where** `app/services/verification/` (`VerificationGateway` + vendor drivers).
- **How** Free local regex/checksum pre-filter → licensed aggregator API → cache 30–90 days. DPIIT via DigiLocker issuer-authenticated certificate pull, QR validation, or a manual queue. **No public MCA/DPIIT API exists** — this is why the gateway abstracts vendors.
- **When** Weeks 9–11, after 1.2.
- **Workflow:** validate format → check cache → call vendor (circuit-breaker protected) → update `verification_status` → unlock gated schemes.
- **Tech:** Setu / SurePass / Sandbox / IDfy drivers, DigiLocker OAuth, httpx, circuit breaker.
- **Algorithm:** CIN regex `^[LUF]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}$`; GSTIN Luhn-mod-36 checksum; exponential backoff 1s/2s/4s ×3; circuit opens after 5 failures for 60 s.

### Task 2.2 — Scheme database & curation pipeline
- **What** The scheme corpus **and** the machine that keeps it true.
- **Why** There is **no live government feed**. Stale rules give wrong advice, which is worse than none. So the database is an owned editorial asset.
- **Where** `schemes` + `scheme_changelog` tables; a git-based scheme-data repo.
- **How** Source registry → nightly git-scraping + changedetection.io monitors → LLM extraction against a strict JSON Schema with a self-refinement pass → **GitHub PR review by a named curator** → merge → sync to Postgres → tiered freshness SLA (T1 30 days, T2 90 days). `last_verified_at` is shown in the UI.
- **When** Weeks 9–12; curation then runs forever at ~4–7 h/week.
- **Workflow:** monitor → detect diff → LLM drafts a field-level diff with quoted sources and confidence → curator approves → CI validates → publish → re-queue on SLA.
- **Tech:** changedetection.io, GitHub Actions, Playwright, LLM extraction, Pydantic/jsonschema, Alembic.
- **Algorithm:** JSON-Schema-constrained extraction with judge-and-repair loop; `unmodelled_text` is preserved verbatim rather than silently dropped — the key honesty mechanism.

### Task 2.3 — Eligibility engine (rules layer + CP-SAT boundary)
- **What** The component that decides who qualifies for what.
- **Why** This is the ideology's core promise: **no false positives, and a named reason for every rejection**.
- **Where** `app/services/eligibility/`, `app/services/cpsat/`.
- **How** Eligibility is **deterministic rule evaluation** (all inputs known → nothing to search). CP-SAT is reserved for genuinely combinatorial questions (which *combination* of schemes can be stacked, allocations, portfolios).
- **When** Weeks 9–11, parallel to 2.1 (pure library work).
- **Workflow:** load rules → evaluate predicates over the profile → collect failures → return eligible set + per-scheme reasons.
- **Tech:** OR-Tools CP-SAT (combinatorial paths), plain Python/JSON-logic rules (eligibility), Hypothesis for property tests.
- **Algorithm:** `eligible = combinator(rule_i(profile))` with AND/OR/NOT groups; property-based tests assert every returned scheme satisfies every rule. Solver timeouts: 10 s interactive, 60 s batch.

### Task 2.4 — Scheme Swarm
- **What** Retrieval → eligibility → ranking → explanation.
- **Why** Eligibility says *can*; ranking says *what first*; explanation says *why* — all three are needed for trust.
- **Where** `app/swarms/scheme/`.
- **How** Retriever filters by type/deadline/amount; EligibilityChecker calls the rules layer; Ranker computes relevance; the v2 likelihood scorer adds approval probability; Explainer writes the reasons in the founder's language.
- **When** Weeks 11–13, after 2.2, 2.3, 1.6.
- **Workflow:** retrieve (parallel) → evaluate → rank → explain → render cards.
- **Tech:** LangGraph, embeddings for domain fit, LLM for explanation only (never for the decision).
- **Algorithm:** relevance = 0.30 funding-match + 0.25 stage + 0.20 domain-fit + 0.15 deadline-urgency + 0.10 success-rate; likelihood = preference-axis match × success rate × profile strength − competition proxy.

### Task 2.5 — Milestone scheme annotation
- **What** Attaches the top 3–5 applicable schemes to each roadmap milestone.
- **Why** It answers *when* to apply, not just *whether* — connecting Category 1 to Category 2.
- **How** For each milestone, phase + funding-need context is passed to the Scheme Swarm; results stored in a junction table; a completeness-score increase re-triggers annotation.
- **When** Week 13, after 1.7 + 2.4.
- **Algorithm:** per-milestone scoped ranking with phase-fit bias (e.g. SISFS at Validation/MVP, NEEDS at manufacturing setup, TANSEED at prototype).

### Task 2.6 — Scheme API & application tracking
- **What** `/schemes`, `/schemes/eligibility`, application CRUD, deadline reminders (7 days and 1 day).
- **Why** Closes the loop from "eligible" to "applied" to "disbursed".
- **Algorithm:** status state machine In Progress → Submitted → Under Review → Approved/Rejected → Disbursed; scheduled reminder job; aggregate statistics.

### Task 2.7 — Hindi & voice expansion
- **What** Hindi locale, dynamic scheme translation, Tamil/Hindi speech in and out, simplified low-literacy UX.
- **Why** Voice + simplicity is the actual moat — raised from P2 to P0 priority for this reason.
- **How** India-tuned ASR (IndicConformer / Saaras class) beats stock Whisper on Tamil; the confidence threshold is re-derived empirically per engine; the `NormalizationService` handles Tanglish.
- **Algorithm:** script check → IndicLID → IndicXlit transliteration with protect-list → LLM fallback below confidence, capped at ~15% of turns.

### Tasks 2.8–2.16 — the v2 layer
| Task | What | Why | Algorithm / mechanism |
|---|---|---|---|
| **2.8 Sector taxonomy** | 21+ canonical sectors tagging every scheme/opportunity/profile | Guarantees no sector falls outside coverage | CI flags any major sector lacking a central *or* TN scheme |
| **2.9 Likelihood scorer** | Rank by real approval chance | Eligibility is binary; priority is personal | preference-axis match × success rate × strength − competition |
| **2.10 Roadmap re-versioner** | Re-annotate issued roadmaps when a scheme changes | Guidance must never go stale silently | event on `scheme_changelog` → dependency index → scoped re-run → new version + diff + notification |
| **2.11 Milestone tracker + QR** | Stateful milestones with proof attachments; PDFs carry a QR to live progress | Turns a static deliverable into a living one; proofs double as investor evidence | signed read-only token → live page |
| **2.12 Problem-statements board** | Public board of government/corporate challenges, each linked to the schemes that fund solving it | "Problem + money in one card" | Opportunity Bank with `type=challenge` + `linked_scheme_ids` |
| **2.13 Alerts & checkers** | New-scheme alerts, document-readiness checklist, deadline tracker | Cheap surfaces on data we already hold | batch rules-eval on profile snapshots; set-difference of required vs verified docs |
| **2.14 Offline / 2G ladder** | PWA offline shell, low-bandwidth variants, SMS fallback | Rural founders lack bandwidth, not ambition | service-worker cache + write-behind sync queue |
| **2.15 Governance** | Review queue, human QA sampling, admin override with audit | Some decisions must have a human | overrides append an exception with mandatory reason + hash-chained audit; solver state never mutated |
| **2.16 Idea-stage IP consent** | Separate consent purpose + masking for unregistered ideas | Idea-stage founders share IP before they're protected | consent artifact + masked match cards until mutual accept |

---

## PHASE 3 — B2B COLLABORATION ENGINE
**Goal:** demand meets supply, feasibly and trustworthily.
**Weeks:** 15–20 · **Category:** 3 · **Exit:** a Bill of Materials (or just a product name) produces ranked, capacity-feasible supplier matches in <1 s, and accepted matches run a tracked lifecycle ending in trust-updating feedback.
**Why third:** a marketplace needs a population of verified startups — which Phases 1–2 create. It also reuses the Phase-2 solver foundation.

### Task 3.1 — B2B schema
- **What** Profiles across four tiers (T1 raw materials with BOM, T2 services, T3 tech/API, T4 co-development), collaborations, feedback, trust scores.
- **Why** Capacity fields (max volume, min order, lead time, service area) are what make a match *feasible*, not merely similar.
- **When** Week 15, after 1.2.

### Task 3.2 — Graph Engine
- **What** The bipartite demand↔supply graph and its matching.
- **Why** Global optimisation beats greedy per-user lists.
- **How** The three-stage funnel (E4). NetworkX is retained only for ≤500-node test parity — the production path uses SQL blocking, pgvector ANN, and C-backed solvers, because pure-Python blossom matching at 100k nodes is O(n³) and would take days.
- **When** Weeks 15–17, after 3.1 + 1.6.
- **Algorithm:** blocking → HNSW top-K → vectorised composite weight → scipy LAPJVsp / min-cost-flow. **~30 ms p50 point query.**

### Task 3.3 — CP-SAT allocation
- **What** Capacity-respecting allocation across matched partners.
- **Why** Similarity finds candidates; only constraint solving guarantees a supplier isn't over-committed and minimum orders are honoured.
- **How** Runs on the *shortlist* asynchronously (30 s–5 min cadence) with warm starts — never in the interactive path.
- **Algorithm:** decision vars `match[d][s]`, `allocation[d][s]`; capacity upper/lower bounds; demand satisfaction; soft penalties (inter-state 50, exclusivity 100); objective = Σ match·weight − penalties; iterative relaxation on infeasibility with a report of what was relaxed.

### Task 3.4 — B2B Swarm
- **What** BOMParser → GraphMatcher → ConstraintOptimizer → TrustCalculator.
- **Why** Founders describe needs in prose ("500 food-grade pouches monthly under ₹8/unit"), not structured records.
- **Algorithm:** trust weighting adjusts edge weights ±20% at >80 / <30; feedback deviating from history is flagged for fraud review.

### Task 3.5 — Collaboration lifecycle
- **What** Proposed → Accepted → Active → On Hold → Completed / Terminated, with documents, messaging, metrics, reminders.
- **Why** Matching without lifecycle is a directory. Lifecycle generates the feedback that improves future matching — the raw data for Phase 5's learning ladder.

### Task 3.6 — Product decomposition & Supply Feasibility Map *(v1.1)*
- **What** Give a product name, spec sheet or uploaded file → get its full requirement tree → get matched vendors per line.
- **Why** Most early founders **don't know their own BOM** — this removes that prerequisite entirely.
- **How** `ProductDecomposer` parses input (OCR reused for files) and drafts raw materials, components, sub-assemblies, services and machinery with quantities and standards, augmented by cited web research on comparable products. **The draft is human-confirmed before any matching** — generated BOMs never auto-commit. `SupplyMapper` then matches each confirmed line, flags gaps, and suggests TN industrial clusters (Coimbatore pumps, Tiruppur knitwear, Ambur leather, Sivakasi printing, Hosur electronics) for unmatched lines.
- **Algorithm:** LLM decomposition with source citation → human confirmation gate → per-line graph matching → gap detection → "invite vendor" demand logging.

### Tasks 3.7–3.11 — API and v2 layer
- **3.7 B2B API** — profiles, matches, collaborations, feedback; responses carry per-component scores for transparency.
- **3.8 Joint cluster-scheme alerts** — when two matched startups share a district and sector, a scoped eligibility run over joint-flagged schemes (SFURTI/CDP/AIM consortium) notifies **both** with a co-application card. *No other platform does this.*
- **3.9 SignalEngine** — dual-signal suggestions (explicit requests + AI-inferred needs) pushed via capped weekly digests; every push is constraint-checked before sending.
- **3.10 Sector-adaptive weights** — the 40/30/20/10 vector becomes per-sector config (AgriTech weights geography; HealthTech weights compliance); learned adjustments require human approval.
- **3.11 Barter mode** — `payment_mode ∈ {cash, barter, either}` with a compatibility constraint; culturally accurate for early-stage India.

---

## PHASE 4 — FUNDING NAVIGATOR & INVESTOR READINESS
**Goal:** know if you're ready, know exactly what to fix, know who to talk to, in what order.
**Weeks:** 21–26 · **Category:** 4 · **Exit:** a spider-chart readiness score with a prioritised gap plan; investor matches that satisfy every hard constraint and readiness gate; a pipeline tracked to Closed Won/Lost.
**Why fourth:** readiness consumes everything before it — legal status (P2), product/traction (P1), even B2B collaboration quality (P3).

### Task 4.1 — Investor database
- **What** Investors with ticket ranges, stages, sectors, geography, thesis, traction thresholds, exclusions, availability.
- **Why** Match quality is bounded by data quality; **hard** preferences (constraints) are stored separately from **soft** fit (ranking).
- **How** Manual curation of public sources + StartupTN/TANFUND and angel-network partnerships; paid data licences deliberately deferred.

### Task 4.2 — Readiness engine
- **What** Six dimensions scored 0–100 and combined.
- **Why** Investors reject the overwhelming majority of pitches; knowing *which dimension* is weak converts rejection into a work plan.
- **How** Explicit rubrics per dimension (e.g. Product = stage 20/40/60/80/100 + features + architecture + IP); assessors run in **parallel**; the Legal dimension reads Phase-2 verification directly.
- **Algorithm:** weighted mean `0.20/0.20/0.25/0.15/0.10/0.10`; banded at 40/60/80.

### Task 4.3 — Gap analysis
- **What** 3–5 concrete actions per dimension scoring below 60.
- **Why** A score without actions is a judgment, not a service.
- **Algorithm:** impact (Low 1–3 / Med 4–7 / High 8+ points) ÷ effort (1–2 / 3–6 / 7+ weeks), sorted by ratio — "what to do Monday morning".

### Task 4.4 — CP-SAT investor matching
- **What** Constraint-filtered investor set, then ranked.
- **Why** Every surfaced investor starts the conversation already qualified; readiness gates stop founders burning bridges too early.
- **Algorithm:** hard constraints — ticket window, stage membership, sector membership, traction thresholds, exclusions, availability, readiness ≥60 (Seed) / ≥70 (Series A+). Then fit = 0.30 sector + 0.25 stage + 0.20 traction + 0.15 geography + 0.10 track record. If the feasible set is empty, report the most-violated constraints as improvement targets.

### Tasks 4.5–4.12 — Swarm, pipeline and the v2 layer
- **4.5 Funding Swarm** — ReadinessAssessor → GapAnalyzer → InvestorMatcher → PipelineManager under one supervisor.
- **4.6 Pipeline** — 8-status Kanban (Initial Contact → … → Term Sheet → Closed Won/Lost), interaction logging, reminders (24 h before, 2 days after), conversion metrics, document organisation per investor.
- **4.7 Funding API** — readiness, matching, pipeline endpoints carrying dimension scores, gap actions, fit scores and constraint diagnostics.
- **4.8 Portfolio anti-conflict *(v2)*** — **Why:** some schemes legally cannot be combined, and over-raising for your stage kills credibility. **Algorithm:** `eligible[a] + eligible[b] ≤ 1` for each conflicting pair from a curated conflict matrix, plus a soft `total_ask ≤ ceiling(stage, burn)` with explanation. This turns a route *list* into a valid route *portfolio*.
- **4.9 Pathway sequencer *(v2)*** — **What:** a dated strategy, not a list. **Algorithm:** topological ordering over route prerequisites plus decision-latency and disbursement metadata → "use the grant to reach prototype, then approach pre-seed" → merged into the living roadmap.
- **4.10 Proxy traction *(v2)*** — LOIs, pilots, hackathon wins, publications, waitlists accepted as typed evidence; routes flagged `accepts_pre_revenue` restrict matching correctly; the gap analyser recommends *which proxy evidence to create next*.
- **4.11 B2B-traction feed *(v2)*** — completed collaborations and recurring orders materialise nightly as `platform_verified` evidence, weighted above self-declared. The pillars become one organism with a single join.
- **4.12 Investor web-intelligence *(v2)*** — ToS-compliant allowlisted sources only, curator-reviewed, every field storing `source_url` + `retrieved_at` and rendering **"driven from web — [source, date]"**, re-verified on a 90-day SLA.

---

## PHASE 5 — OPTIMIZATION, LEARNING & HARDENING
**Goal:** make it fast, safe, self-improving and production-grade.
**Weeks:** 27–32 · **Cross-cutting** · **Exit:** p95 targets met under load, zero critical pen-test findings, zero-downtime deploys.
**Why late:** you harden and teach a system after its full shape exists.

| Task | What / Why | How / Algorithm |
|---|---|---|
| **5.1 Learning ladder** | Hand-tuned weights are a start, not an end — but GNNs on sparse data are *worse* than heuristics | **Stage 0** heuristic (launch, with propensity logging) → **Stage 1** contextual bandit at ~1k outcomes (10% exploration, de-biases the data) → **Stage 2** LightFM hybrid at ~5–10k (metadata embeddings handle new startups) → **Stage 3** LightGCN only at ≥50k interactions **and** a 10-core covering ≥30% of nodes **and** a ≥5% Recall@20 win in shadow mode |
| **5.2 Analytics** | The platform's public value proof and the government-partnership story | Aggregations over operational tables: schemes applied/approved, collaborations formed, funding raised, engagement |
| **5.3 Agent evaluation** | Multi-agent quality decays silently without measurement | Intent accuracy tracking, swarm latency, solver solve-times and infeasibility rates, user feedback, alerting on degradation |
| **5.4 Security hardening** | Identity documents + caste data = maximum sensitivity; DPDP penalties reach ₹250 Cr | AES-256-GCM envelope encryption via a SQLAlchemy TypeDecorator, HMAC blind indexes for lookups, TLS 1.3, RBAC, hash-chained audit log, external pen test |
| **5.5 Performance** | Targets: p95 <500 ms eligibility, <1000 ms matching, 1000 rps | Locust load tests → EXPLAIN ANALYZE → indexes → connection pooling → response caching → solver tuning → horizontal scaling |
| **5.6 Deployment** | 99.9% uptime is a practice, not a wish | Docker → managed PaaS while small → Kubernetes with blue-green, Prometheus/Grafana, ELK, cross-region backups, rehearsed DR drill |
| **5.7 Documentation** | Team scaling and founder self-service both depend on it | OpenAPI at `/docs`, setup guide (<1 h to running), architecture docs, bilingual user guides |
| **5.8 Synthetic-founder simulation *(v2)*** | Rules must be tested against *people*, not just unit cases | Hypothesis generates a synthetic population across caste/gender/district/education/stage; every scheme-rule PR replays it and posts the **eligibility diff** as a PR comment; fairness monitors watch outcome rates per demographic slice |

---

## PHASE 6 — LIVING INTELLIGENCE LAYER *(post-MVP)*
**Goal:** the platform stops being a tool and becomes a companion that watches the world for you.
**Weeks:** 33–40 · **Exit:** vernacular news board live in three languages with sources; every external fact cited and dated; what-if returns fallback plans in <30 s.
**Why last:** these need live external data and *mature* constraint models — the simulator is only cheap because the models already exist.

| Task | What | Why | How / Algorithm |
|---|---|---|---|
| **6.1 Vernacular news board** | Tamil/Hindi/English startup-news intelligence from Tamil business media + national startup media + official feeds | Would be **India's first vernacular startup-news aggregation** | Source registry → RSS-first crawlers → batch LLM summarisation → IndicTrans2 into ta/hi/en → sector tagging → **cited** board with an agent-status strip; scheme-change news links to the roadmap re-versioner |
| **6.2 Investor crawler ops** | Continuous, cited investor intelligence | Investor data decays | Allowlisted sources, curator review, 90-day staleness SLA |
| **6.3 What-if risk simulator** | "What if my scheme is rejected? funding delayed? round fails?" | Founders need contingency, not just plans | **Because eligibility, funding and allocation are already deterministic models, a what-if is literally the same solve with perturbed inputs** — then a baseline-vs-scenario diff plus a fallback plan via the gap/sequencer machinery. Clearly labelled hypothetical; never mutates live data |
| **6.4 Competitor intelligence** | "3 startups like yours raised TANSEED + an angel round" | A retention and motivation surface | Peer-embedding join over the cited funding corpus; k-anonymity (k ≥ 5) for platform-sourced entries; never enters the constraint path |

---

# PART G · MASTER TECH STACK, GLOSSARY, STATUS

### G1 · Tech stack by layer

| Layer | Technology | Used for |
|---|---|---|
| **API** | FastAPI, Pydantic v2, JWT+bcrypt | Endpoints, validation, auth |
| **Agents** | LangGraph (+PostgresSaver), Langfuse | Orchestrator, five swarms, tracing |
| **Optimisation** | OR-Tools CP-SAT, scipy sparse bipartite matching, OR-Tools min-cost-flow | Allocation, portfolios, matching |
| **Rules** | Plain-Python / JSON-logic decision tables | Scheme eligibility (deterministic) |
| **Language** | BGE-M3, IndicTrans2, IndicBERT, IndicLID, IndicXlit, IndicConformer/Saaras | Embeddings, translation, intent, code-mix, speech |
| **Data** | PostgreSQL 16 + pgvector + PostGIS, Redis, S3/MinIO | Records, vectors, geo, cache, documents |
| **Verification** | DigiLocker + KYC aggregators (Setu/SurePass/Sandbox/IDfy) | CIN, DPIIT, GSTIN, PAN, eKYC |
| **Frontend** | React PWA, i18n, offline service worker | Web, low-literacy UX, 2G mode |
| **Quality** | pytest, Hypothesis, sacreBLEU/COMET, Locust, ruff/black | Unit, property, MT, load, lint |
| **Ops** | Docker, GitHub Actions, Kubernetes, Prometheus/Grafana, ELK | Build, CI/CD, deploy, monitor |

### G2 · Glossary
**Swarm** — a supervisor agent plus its specialist sub-agents for one domain. **CP-SAT Boundary** — the constraint engine that guarantees no recommendation violates a hard rule. **Completeness tier** — 40/60/80/100% profile score that gates features. **Terrain** — the roadmap template family (urban tech / rural micro / academic / deep-tech). **Trust score** — 0–100 partner reliability from decayed feedback. **Proxy traction** — non-revenue evidence (LOIs, pilots) accepted for pre-revenue founders. **Living roadmap** — a roadmap that re-versions itself when policy changes. **Opportunity Bank** — the curated corpus of problem statements matched to experience.

### G3 · Current build status (Phase 1)
| # | Task | State |
|---|---|---|
| 1 | Repo scaffold & tooling | ✅ built |
| 2 | Test + CI baseline | ✅ built |
| 3 | Local infra (docker-compose) | ✅ built |
| 4 | FastAPI skeleton + config + logging | ✅ built |
| 5 | DB schema + Alembic migration | ✅ built & verified |
| 6 | Auth (JWT) | ▢ next |
| 7 | Profile models + CompletenessScorer | ✅ built, 7 tests |
| 8–12 | Embeddings · Translation · Orchestrator · Roadmap Swarm · API | ▢ pending |
| P2–P6 | Phase epics | ▢ dependency-chained |

**Gates green:** ruff ✓ · black ✓ · pytest **11/11** ✓

### G4 · Companion documents
`VANIGAM-MASTER-DOCUMENT.md` (blueprint) · `requirements.md` · `design.md` · `tasks.md` · `feasibility-survey.md` (A–Z research) · `constraint-solutions.md` (9 risks solved) · `ideology-comparison.md` · `v2-integration-plan.md` · `traceability-matrix.md` · the blueprint dashboard, one-pager and painted-scroll artifacts.

---

*If you can explain Part A, Part B's first ten points, Part D's seven stages, and why eligibility uses rules while matching uses a solver — you can explain Vanigam to anyone.*
