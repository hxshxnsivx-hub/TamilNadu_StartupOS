# VANIGAM — Tamil Nadu StartupOS
## The Complete End-to-End Project Document

**Version:** 1.0 · **Compiled:** 2026-07-16
**Sources:** requirements.md · design.md · tasks.md · feasibility-survey.md · constraint-solutions.md · multi-agent research (5 feasibility agents + 5 solution agents)

---

## How to read this document

| Section | Answers |
|---|---|
| §1 The Idea | WHAT is Vanigam and WHY does it exist |
| §2 Core Ideology | The six principles everything is built on |
| §3 The Four Categories | WHAT founders get (the product) |
| §4 Unified Architecture | HOW the system is structured, layer by layer |
| §5 Core Mechanisms | HOW each engine works internally |
| §6 Scheme Catalogue | Every major & minor scheme the platform serves |
| §7 Platform & Website Registry | Every external portal, vendor, and model we integrate |
| §8 Phase-by-Phase Construction | WHEN and HOW each part gets built — every step with What/Why/How/When |
| §9 End-to-End Message Lifecycle | HOW one founder message travels the whole system |
| §10 Constraints & Solutions | The 9 known risks and how each is solved |
| §11 Team, Timeline, Cost | WHO builds it and what it costs |
| §12 Testing, Correctness, Deployment | HOW we prove it works and run it |

---

# §1 · THE IDEA

**WHAT:** Vanigam (வணிகம், "commerce") is a multi-agent AI operating system for startup founders in Tamil Nadu. One conversational platform carries a founder from raw idea → registered company → funded, supplied, growing business. It speaks English, Tamil, and Hindi — by text and voice.

**WHY:** Founders in Tamil Nadu — especially first-generation, rural, and vernacular-speaking founders — face four disconnected mazes:
1. *"Is my idea viable and what do I do first?"* — no structured guidance.
2. *"Which of the 100+ government schemes am I actually eligible for?"* — eligibility rules are scattered across dozens of portals in legal English; founders miss deadlines or waste months on schemes they were never eligible for.
3. *"Where do I find a trustworthy supplier/partner?"* — B2B discovery is informal and trust-blind.
4. *"Am I ready for investors, and which investors fit me?"* — readiness is opaque and investor targeting is guesswork.

Existing platforms cover fragments (StartupTN's portal for state programs, myScheme for discovery, private tools for fundraising) but nothing serves the whole journey, and **nothing serves it in Tamil, voice-first, for low-literacy users** — that gap is Vanigam's reason to exist.

**WHO it serves:** aspiring founders (idea stage), registered startups (DPIIT/CIN/GST holders), B2B-seeking manufacturers and service startups, and funding-stage startups — plus scheme administrators and investor-relations managers on the back office side.

**WHEN:** built over 5 phases, 22–32 weeks to full MVP (see §8 and §11).

**The one-sentence thesis:** *Every recommendation Vanigam makes — scheme, partner, or investor — is proven against hard constraints before the founder ever sees it, and every rejection comes with the exact reason, in the founder's own language.*

---

# §2 · CORE IDEOLOGY — Six Principles

### 2.1 Constraint-First
- **What:** Hard rules (age, caste category, entity type, revenue caps, capacity limits, ticket sizes) are enforced by a dedicated constraint engine — the **CPSAT_Boundary** (Google OR-Tools CP-SAT).
- **Why:** Similarity-based recommenders can surface schemes a founder is legally ineligible for; that wastes months and destroys trust. Constraint solving guarantees no false positives.
- **How:** Every scheme/investor/match decision becomes a constraint model — boolean variables with hard constraints; only satisfying assignments are shown. Violated constraints are reported by name ("age > 35", "entity not registered").

### 2.2 Multi-Agent Swarms
- **What:** A **LangGraph Central Orchestrator** (state machine) routes each conversation turn to one of five specialist swarms — **Profile, Scheme, B2B, Roadmap, Funding** — each a supervisor agent coordinating ~4 sub-agents.
- **Why:** The five domains are genuinely distinct bodies of knowledge; decomposition lets each swarm own its tools, prompts, and data, and lets independent sub-tasks run in parallel.
- **How:** Intent classification (IndicBERT, ≥0.75 confidence) → conditional edges route to the owning swarm → supervisor decomposes → sub-agents execute (parallel where independent, sequential where dependent) → supervisor aggregates and validates → orchestrator responds. Swarms message each other through the orchestrator (e.g., Roadmap Swarm asks Scheme Swarm to annotate milestones).

### 2.3 Graph-Native Matching
- **What:** B2B demand and supply live as two sides of a weighted **bipartite graph** (NetworkX interface).
- **Why:** Matching is a market-wide optimization problem, not a per-user search; graph matching optimizes globally instead of greedily.
- **How:** Edge weight = 40% specification similarity (embeddings) + 30% price compatibility + 20% capacity alignment + 10% geographic proximity. Top-k queries for discovery; maximum-weight matching + CP-SAT allocation for capacity-respecting assignments.

### 2.4 Multilingual Intelligence
- **What:** Native English/Tamil/Hindi across text and voice.
- **Why:** The underserved founder types in Tamil or Tanglish and may prefer speaking to typing; translation-as-afterthought fails them.
- **How:** IndicTrans2 translation with a startup-domain glossary (placeholder masking preserves terms like "DPIIT", "funding"); multilingual embeddings for semantic search; ASR for voice input with confidence gating; TTS for voice output; a normalization front-end for code-mixed (Tanglish/Hinglish) input.

### 2.5 Industrial-Grade
- **What:** PostgreSQL 15+ (+pgvector), Redis caching, encrypted S3 document storage, JWT/RBAC auth, rate limiting, circuit breakers, structured audit logs, 99.9% uptime target, p95 < 500 ms eligibility / < 1000 ms matching.
- **Why:** Founders trust the platform with identity documents and business data; a government-adjacent product cannot be a fragile demo.
- **How:** Layered architecture (§4), retries with exponential backoff, graceful degradation with fallbacks, ACID transactions, soft deletes, monitoring (Prometheus/Grafana) — built progressively across phases, hardened in Phase 5.

### 2.6 Verified Trust
- **What:** Legal identity is verified against real registries (MCA21/DPIIT/GST); documents pass OCR + authenticity checks; B2B partners carry **Trust Scores** (0–100) from real collaboration feedback.
- **Why:** A marketplace without verification fills with ghosts; schemes requiring registered entities need proof, not claims.
- **How:** A `VerificationGateway` routes checks through licensed KYC aggregators + DigiLocker (§7.2, §10.1); trust scores are weighted feedback averages with 6-month-half-life exponential decay, adjusting match edge weights ±20%.

---

# §3 · THE FOUR CATEGORIES (the product)

### C1 — Ideation & Roadmap (dual entry: idea OR experience)
- **What:** Two entry modes. **"I have an idea"**: founder describes it (voice/text, any of 3 languages) → structured concept (problem, solution, market, value proposition, differentiation) → feasibility score (0–100) → a roadmap of 5–15 milestones across phases (Ideation → Validation → MVP → Launch → Growth → Scale) with dependencies, critical path, resource estimates, and optimistic/realistic/pessimistic timelines — each milestone annotated with the top 3–5 schemes applicable at that stage. **"I have experience, no idea"** *(Opportunity Discovery, Req 1.6)*: a user with only work experience (agriculture, IT/ITES, textiles, manufacturing…) gives a structured Experience Profile — age, education, caste category, district, sector + years + roles + skills, financial capacity (optionally evidenced by bank statement under separate consent), owned assets, preferred sectors, risk appetite — and the platform *generates* 3–5 ranked startup opportunities they are personally fit to pursue, each card showing why-you-fit, capital band vs their capacity, available scheme support (pre-checked via CP-SAT: NEEDS/UYEGP for first-gen TN founders, PMEGP, Stand-Up India…), and a competition snapshot; the chosen opportunity then flows into the same validation → roadmap pipeline.
- **Why:** Turns a vague idea into an executable plan — and turns *no idea at all* into one. The experience-only entrepreneur (the farmer with 15 years of agri knowledge, the IT professional wanting out) is exactly the underserved first-generation founder TN schemes target.
- **Mechanism:** Roadmap Swarm (ExperienceProfiler → OpportunityGenerator → IdeaExtractor → FeasibilityAnalyzer → MilestoneGenerator → SchemeAnnotator) + a curated, editorially-maintained **Opportunity Bank** (TN sector reports, StartupTN challenges, government problem statements — same curation pipeline as schemes) + web research with cited sources + Translation Service + Scheme Swarm.
- **Built in:** Phase 1 (Task 1.10; annotations and scheme pre-checks wired in Phase 2).

### C2 — Registered Startup Journey
- **What:** Verify CIN, DPIIT number, GSTIN; upload documents (Aadhaar-equivalent via DigiLocker, PAN, community certificate, incorporation certificate, mark sheets, bank statements) through OCR + authenticity checks; receive **solver-proven** scheme recommendations ranked by a 5-factor relevance score; track applications from In Progress → Disbursed with deadline reminders.
- **Why:** Registered founders unlock the bulk of schemes but drown in eligibility fine print; the platform reads the fine print for them, provably.
- **Mechanism:** Legal Validator + Document Verifier + CPSAT_Boundary + Scheme Swarm (Retriever → EligibilityChecker → Ranker → Explainer).
- **Built in:** Phase 2.

### C3 — B2B Collaboration Hub (with Product Decomposition & Supply Feasibility Map)
- **What:** Startups post needs/offers across four tiers — **T1 Raw Materials** (with a structured Bill of Materials), **T2 Services** (legal/accounting/marketing/HR/logistics), **T3 Tech & APIs**, **T4 Co-development** — and get globally optimized, capacity-feasible partner matches with trust scores; then manage the collaboration lifecycle (Proposed → Accepted → Active → Completed/Terminated) with document sharing, messaging, metrics, and closing feedback. **Plus (Req 3.6):** a startup/vendor that only knows its *product* — provided as a name, description, spec sheet, or uploaded file — gets an AI **end-to-end product decomposition**: the ProductDecomposer breaks the product into required raw materials, components, sub-assemblies, services, and machinery (with quantities, units, and quality standards), augmented by web research on comparable-product BOMs with cited sources; after the startup confirms/edits the draft (human-in-the-loop), the SupplyMapper builds a **Supply Feasibility Map** — a tree from product → components → matched on-platform vendors (match score, price band, capacity, distance, trust), with unmatched lines flagged as gaps and enriched by web research suggesting external supplier categories and TN industrial clusters (Coimbatore pumps/motors, Tiruppur knitwear, Ambur–Ranipet leather, Sivakasi printing, Hosur electronics); every gap offers an "invite vendor" action that logs unmet demand for onboarding prioritization.
- **Why:** Reliable supply chains are the #1 operational blocker for manufacturing startups — and most early founders don't *know* their full BOM; decomposition removes that prerequisite, and the feasibility map shows at a glance whether the product can actually be sourced from the ecosystem.
- **Mechanism:** B2B Swarm (ProductDecomposer → BOMParser → GraphMatcher → ConstraintOptimizer → TrustCalculator → SupplyMapper) + Graph Engine + CPSAT_Boundary + Document Verifier (file OCR) + web research with citations.
- **Built in:** Phase 3 (Task 3.7).

### C4 — Funding & Investor Readiness
- **What:** A six-dimension readiness assessment — **Team 20% · Product 20% · Traction 25% · Financial 15% · Pitch 10% · Legal 10%** — producing a 0–100 score, a spider chart, a readiness class (Not Ready / Developing / Ready / Highly Ready), gap actions ranked by impact-to-effort; then CP-SAT investor matching (ticket size, stage, sector, traction thresholds, exclusions, readiness gates: ≥60 for Seed, ≥70 for Series A+) and a Kanban pipeline (Initial Contact → … → Term Sheet → Closed Won/Lost) with reminders and conversion metrics.
- **Why:** Founders pitch too early to the wrong investors; readiness scoring plus constraint-filtered targeting concentrates effort where it can convert.
- **Mechanism:** Funding Swarm (ReadinessAssessor → GapAnalyzer → InvestorMatcher → PipelineManager) + CPSAT_Boundary + Embedding Service.
- **Built in:** Phase 4.

---

# §4 · UNIFIED ARCHITECTURE

All phases build into this single structure:

```
┌─────────────────────────────────────────────────────────────────┐
│  PRESENTATION      Web UI (React, i18n) │ Mobile (low-literacy  │
│                    UX) │ Voice (ASR in / TTS out)               │
├─────────────────────────────────────────────────────────────────┤
│  GATEWAY & AUTH    FastAPI /api/v1 │ JWT + bcrypt + RBAC │      │
│                    Rate limiting (100/min/user) │ Validation    │
├─────────────────────────────────────────────────────────────────┤
│  CENTRAL ORCHESTRATOR (LangGraph state machine)                 │
│    Intent classifier (IndicBERT, conf ≥0.75) │ Context stack    │
│    (pause/resume, 30-min suspension) │ Guardrails (PII,         │
│    injection) │ Conditional edges → swarms                      │
├─────────────────────────────────────────────────────────────────┤
│  SPECIALIST SWARMS (supervisor + sub-agents each)               │
│   Profile │ Roadmap │ Scheme │ B2B │ Funding                    │
├─────────────────────────────────────────────────────────────────┤
│  CORE SERVICES                                                  │
│   CPSAT_Boundary (OR-Tools) │ Graph_Engine (bipartite)          │
│   Embedding_Service (multilingual vectors) │ Translation_Service│
│   (IndicTrans2 + glossary) │ Document_Verifier (OCR + checks)   │
│   Legal_Validator (MCA21/DPIIT/GST via VerificationGateway)     │
├─────────────────────────────────────────────────────────────────┤
│  DATA LAYER   PostgreSQL + pgvector (primary + vectors)         │
│               Redis (embeddings, sessions, semantic cache)      │
│               S3/MinIO (encrypted documents, access-logged)     │
└─────────────────────────────────────────────────────────────────┘
```

**Why layered:** each layer has one responsibility and a clean interface below it, so any component's *internals* can be upgraded (e.g., a faster matcher inside Graph_Engine, a different vendor inside Legal_Validator) without touching the layers above — this is exactly how the constraint solutions in §10 preserve the design.

**How data flows:** requests enter through the gateway, the orchestrator classifies and routes, swarms decompose and call core services, services read/write the data layer, results aggregate back up, and the response is translated to the founder's language on the way out (full lifecycle in §9).

---

# §5 · CORE MECHANISMS (how each engine works)

### 5.1 Central Orchestrator — LangGraph state machine
- **What:** The conversation brain. Nodes: greeting, intent_recognition, profile_collection, idea_discussion, scheme_discovery, b2b_matching, funding_assessment, clarification, error_handling.
- **How:** `ConversationState` (user_id, session_id, messages, current_intent, extracted_entities, active_swarm, context_stack, language_preference) persists via a Postgres checkpointer. Intent classification is multi-label with a 0.75 confidence threshold — below it, a clarification node asks one targeted question. The **context stack** lets a founder pause a roadmap discussion, ask a scheme question, and return. Sessions idle 30 minutes are suspended with saved state. Guardrails screen inputs for prompt injection and outputs for PII leakage.
- **When used:** every single turn.

### 5.2 CPSAT_Boundary — the constraint engine
- **What:** A unified API over OR-Tools CP-SAT: `create_model`, `add_bool_var`, `add_int_var`, `add_constraint`, `add_soft_constraint(penalty)`, `set_objective`, `solve(timeout)`, `compute_iis`.
- **How, per use case:**
  - *Scheme eligibility:* one BoolVar per scheme; hard constraints on age range, gender, caste category, first-graduate status, entity type, domain, stage, revenue range, employee count, verified documents; compound rules like "First_Graduate AND (SC OR ST OR OBC)" via auxiliary booleans. Feasibility problem — output is the set of eligible schemes plus, per ineligible scheme, its violated constraints.
  - *B2B allocation:* `match[d][s]` BoolVars + `allocation[d][s]` IntVars; capacity upper/lower bounds, demand satisfaction, minimum order quantities, spec-similarity ≥0.7, price ≤ budget, distance limits; soft penalties (inter-state 50 pts, exclusivity 100 pts); objective maximizes Σ match·edge_weight − penalties. Infeasible models relax soft constraints iteratively and report what was relaxed.
  - *Investor matching:* BoolVar per investor; ticket-size window, stage/sector membership, availability, traction thresholds, exclusions, readiness gates. Feasible set is then ranked (§5.7).
- **Timeouts:** 10 s interactive, 60 s batch. Models cached; all constructions and infeasibilities logged.
- **When used:** Phases 2 (schemes), 3 (B2B), 4 (investors).

### 5.3 Graph_Engine — bipartite matching
- **What:** Demand and supply nodes with weighted edges; operations: add/remove node/edge, update weight, top-k neighbors, maximum-weight matching, persistence to Postgres adjacency tables (`b2b_graph_nodes`, `b2b_graph_edges`).
- **How (production internals, per §10.4):** a three-stage funnel — (1) SQL blocking by tier/domain + PostGIS geo-radius + capacity > 0 cuts 100k nodes to ~2–5k candidates in 5–20 ms; (2) pgvector HNSW top-200 on spec embeddings + vectorized composite scoring in 5–15 ms (point queries return here, ~30 ms total); (3) batch allocation on the shortlist union via scipy LAPJVsp (1:1), OR-Tools min-cost-flow (capacity default), or CP-SAT (rich constraints), async every 30 s–5 min with warm starts.
- **Trust coupling:** partners with Trust Score > 80 get +20% edge weight; < 30 get −20%.

### 5.4 Embedding_Service — semantic understanding
- **What:** Multilingual sentence embeddings for spec similarity, domain fit, sector alignment, and semantic search over pgvector.
- **How:** `embed(text, kind=query|passage)` and `embed_batch(≤100)`; Redis cache keyed by text-hash+language, 7-day TTL; pgvector tables with HNSW/IVFFlat indexes for scheme and startup-domain embeddings; cosine similarity ≥0.7 = "high similarity". Production model: a retrieval-trained multilingual encoder (BGE-M3 class) behind the interface; IndicBERT remains the *intent classifier* only (§10.5).

### 5.5 Translation_Service — multilingual pipeline
- **What:** en↔ta↔hi translation preserving startup terminology.
- **How:** IndicTrans2 models; the **glossary placeholder trick** — domain terms ("funding" → நிதியளிப்பு, "scheme" → திட்டம், etc.) are masked with sentinel tokens, the sentence is translated, terms are restored in the target language, and a post-check validates restoration. A `NormalizationService` front-end handles code-mixed input: Unicode-block script check → romanized-Indic language ID → transliteration to native script with a protect-list (English terms like "GST" stay Latin) → low-confidence turns fall back to a code-mix-native LLM (§10.7). Quality is gated on chrF++/COMET + glossary hit-rate, not raw BLEU for Tamil (§10.6).

### 5.6 Document_Verifier & Legal_Validator — trust machinery
- **What:** Document ingestion (PDF/JPG/PNG ≤10 MB) → OCR → field extraction → authenticity checks → profile updates; registry verification of CIN/DPIIT/GSTIN.
- **How:** both call a **VerificationGateway** with swappable vendor drivers (§7.2): identity documents flow through DigiLocker consent-based fetch or offline eKYC (never raw Aadhaar OCR — masked storage only); PAN/GST verified by API against NSDL/GSTN-backed vendors; CIN via aggregator MCA master data with free regex/checksum pre-filters; community certificates checked against the TN e-District genuineness portal. OCR confidence <80% on a critical field flags manual review; extracted names match profiles at ≥90% similarity with transliteration-aware normalization. Retries use exponential backoff (1s/2s/4s, 3 attempts); each external registry sits behind a circuit breaker (opens after 5 failures, 60 s cooldown). Cloud OCR fails over to local OCR; unreadable documents route to a manual-review queue.

### 5.7 Opportunity Discovery & Product Decomposition (v1.1 mechanisms)
- **ExperienceProfiler → OpportunityGenerator** *(Roadmap Swarm)*: structured Experience Profile (financial-capacity fields protected at the caste-data class — separate consent, encrypted) → ranked against the curated **Opportunity Bank** with `fit = 0.35·experience-match (embeddings) + 0.25·capital-feasibility + 0.20·scheme-availability (CP-SAT pre-check) + 0.10·market-demand (cited web research) + 0.10·location-fit` → 3–5 opportunity cards → selection pre-fills the standard idea pipeline. The Opportunity Bank is maintained by the same editorial pipeline as schemes (sources → monitors → LLM extraction → curator review → last-verified stamps).
- **ProductDecomposer → SupplyMapper** *(B2B Swarm)*: product input (text/spec/file via OCR) → draft BOM with per-line confidence + source citations → **human confirmation** (drafts never auto-commit) → per-line Graph Engine matching → Supply Feasibility Map (tree with scores/gaps) → gaps trigger external web research (supplier categories, TN industrial clusters) and "invite vendor" demand logging → confirmed lines enter standard T1 matching + CP-SAT allocation.
- **Sector Taxonomy** *(cross-cutting)*: one canonical, versioned taxonomy (≥21 sectors: agritech, food processing, textiles, leather, automotive/EV, electronics/ESDM, IT/ITES, fintech, healthtech, pharma/biotech, renewables, aerospace/defense, tourism, handicrafts, blue economy, construction, logistics, edtech, media/gaming, retail/D2C, circular economy) tags every scheme, opportunity, and B2B profile; scheme-curation CI flags sectors lacking central or TN scheme coverage.

### 5.8 Ranking mechanisms (post-constraint)
- **Scheme relevance:** funding-amount match 30% + stage alignment 25% + domain fit (embeddings) 20% + deadline urgency 15% + historical success rate 10%.
- **Investor fit:** sector alignment 30% + stage 25% + traction match 20% + geographic proximity 15% + track record 10%.
- **Trust Score:** delivery 25% + quality 30% + communication 20% + pricing 15% + overall 10%, normalized 0–100, aggregated with 6-month-half-life decay; new startups start at 50; anomalous feedback patterns are flagged for fraud review.
- **Readiness:** per-dimension rubrics (e.g., Product Maturity: stage 20/40/60/80/100 + features 0–20 + architecture 0–20 + IP 0–20), weighted overall, classed at 40/60/80 boundaries.

---

# §6 · SCHEME CATALOGUE — major & minor schemes the platform serves

> **Freshness rule (§10.2):** amounts and windows below are **indicative** and change with government notifications. In production every scheme row carries `source_urls`, `last_verified_at`, and a curator sign-off; the UI always shows the verification stamp and links to the official page. Verify before relying.

### 6.1 Central Government — flagship startup schemes

| Scheme | Type | What it gives (indicative) | Who it's for | Official platform |
|---|---|---|---|---|
| **SISFS** — Startup India Seed Fund Scheme | Grant + convertible | Up to ~₹20 L validation grant; up to ~₹50 L via convertible debenture through incubators | DPIIT-recognized startups ≤2 yrs, not >₹10 L from other central schemes | seedfund.startupindia.gov.in |
| **FFS** — Fund of Funds for Startups | Indirect equity | ₹10,000 Cr corpus via SIDBI into SEBI-registered AIFs that invest in startups | Startups raising from FFS-backed VC funds | sidbivcf.in / startupindia.gov.in |
| **CGSS** — Credit Guarantee Scheme for Startups | Credit guarantee | Collateral-free loan guarantee (up to ~₹10 Cr ceiling per borrower) | DPIIT-recognized startups borrowing from member institutions | ncgtc.in |
| **MUDRA (PMMY)** | Loan | Shishu ≤₹50k · Kishore ≤₹5 L · Tarun ≤₹10 L (Tarun Plus up to ₹20 L for repeat borrowers) | Micro/small non-farm enterprises | mudra.org.in / jansamarth.in |
| **Stand-Up India** | Loan | ₹10 L – ₹1 Cr composite loan | SC/ST and/or women entrepreneurs, greenfield enterprises | standupmitra.in |
| **PMEGP** | Subsidy-linked loan | 15–35% margin-money subsidy on projects (mfg up to ~₹50 L, services up to ~₹20 L); higher % for SC/ST/OBC/women/rural | New micro-enterprises | kviconline.gov.in/pmegpeportal |
| **CGTMSE** | Credit guarantee | Guarantee cover on collateral-free MSE loans (ceiling ~₹5 Cr) | Micro & small enterprises | cgtmse.in |

### 6.2 Central — innovation & sector programs (minor/targeted)

| Scheme | What it gives | Who | Platform |
|---|---|---|---|
| **NIDHI** (DST) — PRAYAS/SSP/EIR/Accelerator | Prototyping grants (~₹10 L PRAYAS), seed support via TBIs, EIR fellowships | Tech/science startups in incubators | nidhi.dst.gov.in |
| **AIM / Atal Incubation Centres** | Incubation + grant support to AICs hosting startups | Startups in AIC network | aim.gov.in |
| **SAMRIDH** (MeitY) | Accelerator matching up to ~₹40 L with selected accelerators | Software-product startups | meity.gov.in |
| **GENESIS** (MeitY) | Tier-II/III startup support (successor to TIDE 2.0) | Deep-tech startups outside metros | meity.gov.in |
| **ASPIRE** (MSME) | Rural/agro-industry incubation support | Agro-rural enterprises | aspire.msme.gov.in |
| **MSME Champions / ZED / Design** | Certification subsidies, design support, IP reimbursement | Registered MSMEs (Udyam) | champions.gov.in |

### 6.3 Tamil Nadu State — the home-turf depth (our differentiator)

| Scheme | Type | What it gives (indicative) | Who | Platform |
|---|---|---|---|---|
| **TANSEED** (StartupTN) | Equity-free grant | Up to ~₹10–15 L per cohort edition | TN-registered, StartupTN-recognized early-stage startups | startuptn.in / tanfund.in |
| **TANFUND** | Co-investment / facilitation | Digital portal matching TN startups to SIDBI-fund-of-funds partners & investors; runs TANSEED end-to-end | TN startups raising | tanfund.in |
| **NEEDS** — New Entrepreneur-cum-Enterprise Development Scheme | Capital subsidy + soft loan | 25% capital subsidy (cap ~₹75 L) on projects up to ~₹5 Cr + 3% interest subvention; EDP training | First-generation TN entrepreneurs 21–45 (relaxations for special categories) | msmeonline.tn.gov.in |
| **UYEGP** — Unemployed Youth Employment Generation Programme | Subsidy-linked loan | 25% subsidy (caps ~₹2.5 L) on projects: mfg ≤₹10 L, service ≤₹3 L, trade ≤₹1 L | TN unemployed youth, income-capped households | msmeonline.tn.gov.in |
| **TN SC/ST Startup Fund** | Equity/grant support | Dedicated corpus for SC/ST founders (linked to TANSIM) | TN SC/ST founders | startuptn.in |
| **TANSIM programs** (StartupTN umbrella) | Recognition, mentoring, hubs | StartupTN recognition, regional hubs, women/rural/student tracks, global market access | TN startup ecosystem | startuptn.in |

### 6.4 Banking / institutional (minor but high-volume)

| Scheme | What | Platform |
|---|---|---|
| **SIDBI direct lending** (SMILE, Speed Plus etc.) | Term loans for MSMEs/startups | sidbi.in |
| **Bank startup products** (SBI, Canara, IOB startup branches in TN) | Working capital, term loans via CGTMSE cover | Respective bank portals / jansamarth.in |
| **NABARD agri-startup support** | Agri/rural venture support | nabard.org |

**How the catalogue is used mechanically:** every scheme's eligibility prose is converted to structured `eligibility_criteria` JSONB rules (field/operator/value + AND/OR/NOT groups + `unmodelled_text` kept verbatim for the Explainer). CP-SAT consumes the rules; the Ranker scores relevance; annotations attach schemes to roadmap milestones by phase fit (e.g., SISFS at Validation/MVP milestones, NEEDS at manufacturing-setup milestones, TANSEED at prototype milestones).

**Sector coverage guarantee (Req 2.7):** every scheme is tagged against the canonical Sector Taxonomy (§5.7) spanning all sectors present in the TN startup ecosystem — agriculture & agritech, food processing, textiles, leather, automotive/EV, electronics/ESDM, IT/ITES, fintech, healthtech, pharma/biotech, renewables, aerospace/defense, tourism, handicrafts, blue economy, construction, logistics, edtech, media/gaming, retail/D2C, circular economy — and the curation pipeline's CI flags any major sector lacking either a central or a Tamil Nadu scheme row, so coverage gaps surface to the curator instead of silently existing.

---

# §7 · PLATFORM & WEBSITE REGISTRY — everything we integrate with

### 7.1 Government portals (data & verification sources)

| Platform | URL | What we use it for | How | When (phase) |
|---|---|---|---|---|
| **myScheme** | myscheme.gov.in (+ rules.myscheme.in) | Seed + cross-check for central scheme catalogue | Scrape structured page JSON; monitor for changes | 2 |
| **Startup India** | startupindia.gov.in | DPIIT scheme list, state policies, "Validate Recognition" lookup | Source registry + assisted verification fallback | 2 |
| **StartupTN** | startuptn.in | TN scheme depth, TANSEED windows, recognition; partnership target | Monitored source; potential official distribution channel | 2+ |
| **TANFUND** | tanfund.in | TANSEED workflow reality, TN investor pipeline context | Monitored source | 2, 4 |
| **MSME Tamil Nadu** | msmetamilnadu.tn.gov.in / msmeonline.tn.gov.in | NEEDS, UYEGP details & application flow | Monitored source | 2 |
| **MCA21** | mca.gov.in | Company master data (CIN) — no public API | Via aggregator API; free manual master-data view as fallback | 2 |
| **GST portal / GSTN** | gst.gov.in (developer.gst.gov.in) | GSTIN validity, filing status | Via GSP/aggregator API; free checksum pre-filter | 2 |
| **DigiLocker / API Setu** | digilocker.gov.in / apisetu.gov.in | Consent-based pulls: Aadhaar (signed XML), PAN, DPIIT certificate, MCA COI, TN community certificate | Aggregator-mediated OAuth consent flow | 2 |
| **TN e-District** | tnedistrict.tn.gov.in | Community/income/nativity certificate genuineness check | Certificate-number verification page | 2 |
| **data.gov.in** | data.gov.in | DPIIT-recognized startup datasets (discovery only, stale snapshots) | Periodic import | 2 |
| **PIB / RBI / SIDBI newsletters** | pib.gov.in etc. | Change signals for scheme/bank-circular updates | RSS/newsletter monitoring into the curation pipeline | 2+ |
| **UIDAI** | uidai.gov.in | Offline eKYC ZIP format, Secure QR spec, masking rules (legal basis) | Compliance reference + offline eKYC verification | 2 |

### 7.2 Commercial verification vendors (the VerificationGateway drivers)

| Vendor | URL | Products we'd use | Why chosen | When |
|---|---|---|---|---|
| **Setu** | setu.co / docs.setu.co | DigiLocker flow (cleanest docs + public sandbox), PAN verify | DigiLocker specialist | 2 |
| **SurePass** | surepass.io | MCA CIN/DIN, PAN↔CIN↔GST pivots, GST, Aadhaar offline, Udyam | Widest single-vendor surface, prepaid | 2 |
| **Sandbox.co.in** | sandbox.co.in | MCA/GST/PAN/DigiLocker/Aadhaar-offline | Self-serve, transparent public pricing | 2 |
| **Cashfree Secure ID** | cashfree.com | Smart OCR + Aadhaar-masking product, KYB | Compliant OCR path | 2 |
| **IDfy / Signzy / Zoop** | idfy.com / signzy.com / zoop.one | Alternates: async task APIs, OCR+masking, cheap GSTIN | Driver redundancy — vendor swap = config change | 2 |
| ~₹25k–75k/month at 1,000 onboardings × ~5 checks; free regex/checksum pre-filters cut paid calls 10–20% | | | | |

### 7.3 AI models & ML platforms

| Asset | Source | Role | When |
|---|---|---|---|
| **IndicTrans2** (AI4Bharat, MIT) | github.com/AI4Bharat/IndicTrans2 | en↔ta↔hi translation (1B quality / 200M distilled latency) | 1 |
| **IndicBERT** (ai4bharat) | huggingface.co/ai4bharat/indic-bert | Intent classification (fine-tuned head) — classification only | 1 |
| **BGE-M3** (BAAI, MIT) | huggingface.co/BAAI/bge-m3 | Semantic-search embeddings (1024-dim) behind Embedding_Service | 1 |
| **IndicSBERT / mE5** (L3Cube / intfloat) | huggingface.co | A/B alternates for embeddings | 1 |
| **Whisper / IndicConformer / Saaras** | openai / AI4Bharat / sarvam.ai | Tamil-Hindi ASR (India-tuned preferred), confidence-gated | 2 (voice) |
| **IndicLID + IndicXlit** (AI4Bharat) | github.com/AI4Bharat | Romanized-Indic detection + Tanglish→Tamil transliteration | 2 |
| **Sarvam-M / Tamil-Llama** | huggingface.co/sarvamai/sarvam-m, abhinand/tamil-llama-7b-instruct-v0.2 | Code-mix-native LLM fallback (≤15% of turns) | 2 |
| **Claude / GPT-class LLMs** | Anthropic/OpenAI APIs | Agent reasoning tiers: small model for routing/sub-agents, larger for synthesis; prompt caching + batch APIs | 1–5 |
| **OR-Tools CP-SAT** | developers.google.com/optimization | Constraint engine | 2–4 |
| **NetworkX / scipy / OR-Tools flow** | networkx.org / scipy.org | Graph interface / production matchers | 3 |
| **LightFM → LightGCN (PyG)** | github.com/lyst/lightfm, pytorch-geometric | Learning-loop ladder, data-gated | 5 |
| **sacreBLEU chrF++ / COMET** | github.com/mjpost/sacrebleu, Unbabel/wmt22-comet-da | MT quality gates | 1–2 |
| **Tesseract / Google Document AI** | — | OCR (cloud primary, local fallback) | 1–2 |

### 7.4 Infrastructure & tooling platforms

| Platform | Role | When |
|---|---|---|
| **PostgreSQL 15 + pgvector (+PostGIS)** | Primary data, vectors, geo-blocking | 1 |
| **Redis** | Embedding/session cache, semantic response cache, rate limiting | 1 |
| **S3 / MinIO** | Encrypted document storage with access logging | 1 |
| **LangGraph (+ Postgres checkpointer)** | Orchestrator + swarms, Send-API parallelism, streaming | 1 |
| **Langfuse (OSS)** | Agent tracing + cost-per-turn dashboards | 1 |
| **changedetection.io + GitHub Actions git-scraping** | Scheme-source monitoring | 2 |
| **Alembic / Pydantic / FastAPI** | Migrations, validation, API | 1 |
| **Docker → Kubernetes, GitHub Actions CI/CD** | Packaging, orchestration, deploys (blue-green) | 1 dev / 5 prod |
| **Prometheus + Grafana, ELK/CloudWatch** | Metrics, alerting, log aggregation | 5 |
| **Locust** | Load testing (1000 rps, p95 targets) | 5 |
| **Hypothesis + pytest** | Property-based + unit/integration testing | all |

---

# §8 · PHASE-BY-PHASE CONSTRUCTION (every step: What / Why / How / When)

> Effort key: XS <4h · S 4–8h · M 1–2d · L 3–5d · XL 1–2w. Priority: P0 critical → P3 low.
> "When" = position inside the phase window and its dependency trigger.

---

## PHASE 1 — Foundation & Ideation (Weeks 1–8, Category C1)

**What:** infrastructure, core schemas, the two language services, the first two swarms (Profile, Roadmap), the orchestrator, and the first API surface.
**Why first:** every other phase consumes these primitives; C1 is also the only category deliverable with zero external-registry dependencies — value ships without waiting on vendors.
**Exit criteria:** a founder can register, build a profile (40→100% completeness), describe an idea in ta/en/hi, and receive a structured roadmap through the orchestrator.

| Step | What | Why | How | When |
|---|---|---|---|---|
| 1.1 Infrastructure | Postgres 15+pgvector, Redis, S3/MinIO buckets, JSON structured logging | Nothing runs without state, cache, files, and observability | Docker-compose dev stack; pgvector `CREATE EXTENSION`; Redis persistence + pooling; MinIO bucket policies; JSON log formatter to stdout+files | Week 1, day 1 — no dependencies |
| 1.2 Founder/startup schema | `founders`, `startups`, `documents`, `profile_completeness` tables + Alembic migrations + indexes | The data contract every swarm reads; constraints (email/phone regex, CIN format, positive values) enforce integrity at the bottom layer | SQL DDL from design.md with soft-delete columns, FK cascades, unique constraints on email/phone/CIN/DPIIT/GSTIN; Alembic up/down scripts; indexes on email, phone, location, domain, stage | Week 1–2, after 1.1 |
| 1.3 Profile Swarm | Pydantic models; CompletenessScorer (40% demographics / 60% +education / 80% +startup / 100% +verified docs); DataCollector (multilingual field prompts); ProfileSupervisor (LangGraph) | Profile completeness gates scheme eligibility — richer profile → more schemes unlock; the scorer's re-evaluation trigger keeps recommendations current | Sequential flow collect → verify → score; parallel doc processing; score-change event triggers Scheme Swarm re-run (wired in Phase 2) | Weeks 2–3, after 1.2 |
| 1.4 Document Verifier | S3 upload/signed URLs; OCR integration (cloud primary, Tesseract fallback); DocumentProcessor (type ID + field extraction); validation logic; low-confidence manual-review path | Verified documents are what turn claimed eligibility into provable eligibility (First_Graduate, caste category need documentary proof) | Confidence gate: <80% on a critical field → founder review; name match ≥90% (transliteration-aware); Aadhaar-class documents route through the compliant DigiLocker path per §10.1 — never raw OCR | Weeks 3–4, after 1.1.4 + 1.3 |
| 1.5 Translation Service | IndicTrans2 load (1B/200M); `translate()` all pairs; domain glossary; placeholder-preserving translation; Redis caching; eval harness | Tamil-first is the moat; glossary preservation stops "funding"→garbled; caching keeps latency/cost flat on repeated content | Mask glossary terms with non-splitting sentinels → translate → restore → validate restoration; cache by (text-hash, src, tgt) 7-day TTL; quality gates chrF++/COMET per §10.6 | Weeks 2–4, parallel to 1.3 (needs only 1.1 Redis) |
| 1.6 Embedding Service | Model load; `embed`/`embed_batch`; cosine similarity; Redis cache; `scheme_embeddings` + `startup_domain_embeddings` pgvector tables + indexes | Semantic similarity powers scheme domain-fit, B2B spec matching, investor sector alignment — one service, three consumers | Retrieval-trained multilingual model (BGE-M3 class) with query/passage handling inside the interface; HNSW indexes; version-stamped vectors for future migrations | Weeks 2–4, parallel (needs 1.1) |
| 1.7 Roadmap Swarm | IdeaExtractor (problem/solution/market/value-prop); FeasibilityAnalyzer (market, competition, complexity, regulatory → 0–100); MilestoneGenerator (5–15 milestones, phases, deliverables, timelines ×3 estimates); dependency resolution (topological sort + critical path); RoadmapSupervisor; roadmap/milestone tables | This is C1 — the first thing an idea-stage founder actually needs; milestone structure is also the anchor scheme annotations attach to in Phase 2 | Sequential pipeline extract → feasibility → milestones → dependencies; missing concept elements trigger clarifying questions; timelines conditioned on domain, complexity, founder experience | Weeks 4–6, after 1.5 (translation of idea input) |
| 1.8 Central Orchestrator | ConversationState TypedDict; intent classifier; LangGraph nodes + conditional edges; context stack; 30-min timeout suspension; integration tests | The router that makes five swarms feel like one assistant; context stack = founders can interleave tasks naturally | Confidence-cascade routing (keyword → embedding → fine-tuned classifier → LLM fallback <0.5) per §10; Postgres checkpointer for suspension/resume; guardrails on both edges | Weeks 5–7, after 1.3 + 1.7 exist to route to |
| 1.9 API v1 | /auth (register/login/refresh, JWT+bcrypt), /profiles, /startups, /ideation endpoints; Pydantic validation; error middleware (standard ErrorResponse); rate limiting; integration tests | The contract the frontend builds against; uniform errors + rate limits from day one prevent retrofitting security | FastAPI routers per domain; 422 on validation; 100 req/min/user + 1000/min global; 80% test coverage gate | Weeks 6–8, after 1.3/1.7/1.8 |
| 1.10 Opportunity Discovery *(v1.1)* | `opportunity_bank` + `experience_profiles` tables; 30–50 seeded opportunities across TN priority sectors; ExperienceProfiler intake agent; OpportunityGenerator (35/25/20/10/10 fit ranking + cited web research); dual-mode ideation entry in the orchestrator | Serves the experience-only, no-idea user — the first-generation founder TN schemes explicitly target; without this path they can't even enter the platform | Financial-capacity intake under separate DPDP consent + encryption; scheme pre-check stubs until CP-SAT lands in Phase 2, then live; selected opportunity pre-fills the idea pipeline | Weeks 6–8, after 1.6 + 1.7 (scheme pre-check completes in Phase 2) |

---

## PHASE 2 — Registered Startup & Schemes (Weeks 9–14, Category C2)

**What:** legal verification, the scheme database + curation pipeline, the CP-SAT eligibility engine, the Scheme Swarm, roadmap annotation, and Hindi expansion.
**Why second:** it's the flagship value (provable scheme eligibility) and it feeds C1 (annotations); it needs Phase 1's profile + embedding + translation primitives.
**Exit criteria:** a verified startup gets a ranked, solver-proven scheme list with plain-language reasons in <10 s, and roadmap milestones carry scheme cards.

| Step | What | Why | How | When |
|---|---|---|---|---|
| 2.1 Legal Validation Service | VerificationGateway + vendor drivers; CIN/DPIIT/GSTIN checks; retry + circuit breaker; verification_status updates | Schemes requiring registered entities unlock only on *proof*; the gateway pattern isolates vendor risk (swap = config) | Per §10.1: free regex/checksum pre-filters → SurePass/Sandbox/Setu APIs → cache 30–90d; DPIIT via DigiLocker pull, QR check, manual queue; day-1 catalog discovery call to enumerate pullable doc types | Weeks 9–11, after 1.2 (needs startup rows) |
| 2.2 Scheme DB + curation pipeline | `schemes` (+JSONB criteria), `scheme_benefits`, `scheme_applications` tables; versioning; seeds (SISFS, FFS, PMEGP, MUDRA, Stand-Up India, TANSEED + §6 catalogue); admin API; **and** the editorial pipeline: source registry → git-scraping + changedetection.io monitors → LLM extraction with self-refinement → curator PR review → sync → freshness SLA | No live government feed exists (§10.2) — the DB is an owned editorial asset; the pipeline automates everything except final judgment, keeping one curator at 4–7 h/wk | JSONB rule shape (field/op/value/source_quote/confidence + combinator + unmodelled_text) compiles straight into CP-SAT; `last_verified_at` shown in UI; tiered SLA T1 30d / T2 90d | Weeks 9–12; seeding first, pipeline hardening continuous |
| 2.3 CP-SAT Boundary | CPSATBoundary class; demographic/education/startup/document constraint encoders; compound AND/OR/NOT; violated-constraint analysis; unit + property-based tests (Hypothesis) | The ideology's core promise — recommendations that are constraint-proven, rejections that name their reason | BoolVar per scheme; constraint templates per criterion type; rule-level "why ineligible" reporting (deterministic, free); solver timeout 10 s interactive; 90%+ test coverage | Weeks 9–11, parallel to 2.1 (pure library work, no dependencies) |
| 2.4 Scheme Swarm | SchemeRetriever (filters), EligibilityChecker (→CP-SAT), Ranker (5-factor §5.7), domain-fit via embeddings, Explainer (natural-language reasons), SchemeSupervisor | Constraint filtering says *can*; ranking says *should first*; explanation says *why/why not* — all three are needed for founder trust | Parallel retrieval + eligibility; sequential rank → explain; Explainer surfaces `unmodelled_text` criteria verbatim so nothing is silently dropped | Weeks 11–13, after 2.2 + 2.3 + 1.6 |
| 2.5 Milestone annotation | SchemeAnnotator agent; Roadmap↔Scheme swarm messaging; `milestone_scheme_annotations` junction table; re-annotation on completeness increase | Connects C1 to C2: the roadmap tells founders *when* each scheme becomes relevant (SISFS at MVP, NEEDS at factory setup) | Per milestone: phase/funding-need context → Scheme Swarm → top 3–5 with relevance scores; completeness-score events trigger re-runs | Week 13, after 1.7 + 2.4 |
| 2.6 Scheme API | GET /schemes (+filters), GET /schemes/{id}, POST /schemes/eligibility, application CRUD, deadline reminders (7d + 1d) | Application tracking closes the loop — from "eligible" to "applied" to "disbursed", with aggregate stats | Status machine In Progress→Submitted→Under Review→Approved/Rejected→Disbursed; scheduled reminder job; dashboard aggregates | Weeks 13–14, after 2.4 |
| 2.7 Hindi + voice expansion | Hindi i18n locale; dynamic scheme-description translation; Hindi/Tamil ASR voice input; TTS output; simplified low-literacy UX | Voice + simple UX is the actual moat (§1); raised from the original P2 because it serves the core audience | India-tuned ASR (IndicConformer/Saaras class) with empirically re-derived confidence threshold; icon-first large-type UI; `NormalizationService` for code-mixed input per §10.7 | Weeks 12–14, parallel (needs 1.5) |
| 2.8 Sector Taxonomy *(v1.1)* | Canonical versioned `sector_taxonomy` (≥21 sectors); tagging of all schemes/opportunities/B2B profiles; coverage-gap CI check in scheme curation | Guarantees every TN + central scheme sector is represented and nothing (agritech to circular economy) falls outside classification — the "all available sectors" guarantee | Admin-extendable without code changes; curator flagged when a major sector lacks central or TN scheme rows | Week 12, after 2.2 |

---

## PHASE 3 — B2B Collaboration Engine (Weeks 15–20, Category C3)

**What:** B2B profiles across 4 tiers, the graph matching engine, CP-SAT allocation, the B2B Swarm, lifecycle management, and B2B APIs.
**Why third:** matching needs a population of verified startups (Phases 1–2) to be liquid; the graph + CP-SAT machinery reuses the Phase 2 solver foundation.
**Exit criteria:** a BOM produces ranked, capacity-feasible supplier matches in <1 s point-query latency; accepted matches run a tracked lifecycle ending in trust-updating feedback.

| Step | What | Why | How | When |
|---|---|---|---|---|
| 3.1 B2B schema | `b2b_profiles` (T1 BOM items, T2 services, T3 tech/API, T4 co-dev fields), `b2b_collaborations`, `collaboration_feedback`, `trust_scores` tables | Four tiers have different data shapes; capacity fields (max volume, min order, lead time, service area) are what make matching *feasible* not just similar | JSONB BOM items (name/spec/qty/UoM/standards/price-range); tier + intent (Seeking/Offering/Both) discriminators | Week 15, after 1.2 |
| 3.2 Graph Engine | Node/edge tables; GraphEngine class; edge-weight computation (40/30/20/10); spec similarity via embeddings; max-weight matching; top-k; persistence; incremental updates | Global optimization beats greedy lists; persisted adjacency makes the graph durable and incrementally updatable | Production internals per §10.4: SQL blocking (tier/domain/PostGIS geo/capacity) → pgvector HNSW top-200 → vectorized scoring (~30 ms point queries); batch matching via scipy/min-cost-flow; NetworkX retained for test parity | Weeks 15–17, after 3.1 + 1.6 |
| 3.3 CP-SAT B2B model | match/allocation variables; capacity upper/lower bounds; demand satisfaction; spec ≥0.7 + price + geo constraints; soft penalties (inter-state 50, exclusivity 100); maximize quality − penalties; relaxation reporting | Similarity finds candidates; only constraint solving guarantees a supplier isn't over-committed and minimum orders are honored | Solver runs on the *shortlist* asynchronously (30 s–5 min cadence) with AddHint warm starts, never in the interactive path | Weeks 16–18, after 2.3 + 3.2 |
| 3.4 B2B Swarm | BOMParser (NL → structured BOM); GraphMatcher; ConstraintOptimizer; TrustCalculator (weighted 5-dimension feedback, 6-mo half-life decay, init 50); B2BSupervisor | Founders describe needs in prose ("I need 500 food-grade pouches monthly under ₹8/unit") — the swarm turns prose into an optimized, trust-adjusted match list | Sequential BOM → match → optimize; trust modifies edge weights ±20% at >80/<30; fraud-pattern deviation flags | Weeks 17–19, after 3.2 + 3.3 |
| 3.5 Lifecycle management | Status machine (Proposed→Accepted→Active→On Hold→Completed/Terminated); document sharing; partner messaging; metrics (orders, value, delivery time, incidents); automated reminders; feedback trigger on close | Matching without lifecycle is a directory; lifecycle + feedback is what generates the trust signal that improves future matching (the §10.8 learning ladder's raw data) | Status-change notifications + logs; completion triggers 5-dimension feedback collection; export for accounting | Weeks 18–20, after 3.1 + 3.4 |
| 3.6 B2B API | Profile CRUD, POST /b2b/matches, collaboration CRUD + status, feedback submission, listings | External contract for C3 | Match responses carry per-component scores (spec/price/capacity/geo) + trust + distance for transparency | Weeks 19–20, after 3.4 + 3.5 |
| 3.7 Product Decomposition & Supply Map *(v1.1)* | `product_decompositions` table; ProductDecomposer (text/spec/file → draft BOM with citations); human-in-the-loop confirmation UI; SupplyMapper (per-line matches, gap detection, TN-cluster suggestions via web research); Supply Feasibility Map API; invite-vendor demand logging | Most early founders don't know their full BOM — decomposition removes the prerequisite; the map answers "can this product actually be sourced here?" and gap logging tells us which vendors to recruit next | Drafts never auto-commit; confirmed lines flow into standard T1 matching + CP-SAT allocation; OCR reuse from 1.4; all external findings cited | Weeks 17–20, after 3.2 + 3.4 |

---

## PHASE 4 — Funding Navigator & Investor Readiness (Weeks 21–26, Category C4)

**What:** investor database, six-dimension readiness engine, gap analysis, CP-SAT investor matching, Funding Swarm, pipeline management, funding APIs.
**Why fourth:** readiness scoring consumes everything before it — verified legal status (P2), traction/product data (P1 profiles), even B2B partnership quality (P3) feeds the Traction dimension.
**Exit criteria:** a startup sees its spider chart + prioritized gap actions; matches respect all investor hard constraints and readiness gates; the pipeline tracks to Closed Won/Lost.

| Step | What | Why | How | When |
|---|---|---|---|---|
| 4.1 Investor schema + seeds | `investors` (ticket range, stages, sectors, geography, thesis, portfolio metrics, evaluation thresholds, exclusions, availability), `funding_pipeline`, `readiness_assessments` tables; seed investors | Matching quality is bounded by database quality; structure captures *hard* preferences (constraints) separately from *soft* fit (ranking) | Seed via manual curation of public sources + StartupTN/TANFUND and angel-network partnerships (paid data licenses deferred per feasibility survey); admin interface for IR managers | Week 21, after 1.2 |
| 4.2 Readiness engine | Six assessors with explicit rubrics (Team: experience 0–20 + completeness 0–15 + expertise 0–15 + advisors 0–10; Product: stage 20–100 + features + architecture + IP; Traction: users + revenue + retention + partnerships + validation; Financial: burn + growth + unit economics + projections; Pitch: deck completeness + clarity + market + differentiation; Legal: registration + DPIIT + IP + compliance + cap table); weighted overall; 4-class banding | Investors reject 95%+ of pitches; knowing *which dimension* is weak converts rejection into a work plan | Assessors run in parallel (asyncio.gather); Legal dimension reads Phase 2 verification results directly | Weeks 21–23, after 2.1 |
| 4.3 Gap analysis | GapAnalyzer (dimensions <60); 3–5 recommendations per gap with per-dimension playbooks; impact (1–3/4–7/8+ pts) and effort (1–2/3–6/7+ wks) estimates; impact÷effort prioritization; progress tracking | A score without actions is a judgment, not a service; impact-to-effort ordering tells founders what to do *Monday morning* | Recommendation templates per dimension (add co-founder, file DPIIT, run pilot, extend runway…) parameterized by the startup's actual data; founders mark In Progress/Completed and watch the score move | Weeks 22–24, after 4.2 |
| 4.4 CP-SAT investor matching | matched[i] BoolVars; ticket/stage/sector/availability/traction/exclusion constraints; readiness gates (Seed ≥60, Series A+ ≥70); post-solve fit ranking (§5.7); no-match diagnosis | Warm targeting: every surfaced investor has *zero* hard-constraint violations, so conversations start qualified; gates stop founders burning bridges too early | Feasibility solve → rank by weighted fit (embedding thesis-alignment for sector); if empty, report most-violated constraints as improvement targets | Weeks 23–24, after 2.3 + 4.1 + 4.2 |
| 4.5 Funding Swarm | ReadinessAssessor, GapAnalyzer, InvestorMatcher, PipelineManager under FundingSupervisor | One conversational surface over the whole funding journey — "am I ready?" → "what do I fix?" → "who do I talk to?" → "where does each conversation stand?" | Parallel dimension assessment → sequential gap → matching → pipeline ops | Weeks 24–25, after 4.2–4.4 |
| 4.6 Pipeline management | 8-status machine (Initial Contact → Pitch Scheduled → Pitch Delivered → Due Diligence → Term Sheet → Negotiation → Closed Won/Lost); interaction logging; reminders (24h pre-meeting, 2d follow-up); metrics (conversion by stage, time-in-stage, pipeline value); Kanban API; document organization (decks, models, DD docs, term sheets per investor) | Fundraising is a multi-month multi-thread process; founders lose deals to dropped follow-ups, and Closed-Lost reasons are the platform's own learning data | Kanban board visualization; Closed Won records amount/valuation/equity; Closed Lost records reason + notes | Weeks 24–26, after 4.1 |
| 4.7 Funding API | POST/GET readiness, POST /funding/investors/match, investor listings + filters, pipeline CRUD + metrics | External contract for C4 | Responses carry dimension scores, gap actions, fit scores, and constraint diagnostics | Week 26, after 4.5 + 4.6 |

---

## PHASE 5 — Optimization, Learning & Hardening (Weeks 27–32, cross-cutting)

**What:** the learning loop, analytics, continuous agent evaluation, security hardening, performance work, production deployment, documentation.
**Why last:** learning needs accumulated data; hardening and load-testing need the full surface to exist; deployment maturity gates public scale, not development.
**Exit criteria:** p95 targets met under load; zero critical pen-test findings; zero-downtime deploys; dashboards live.

| Step | What | Why | How | When |
|---|---|---|---|---|
| 5.1 Learning loop | Match-outcome logging; score-provider ladder — heuristic (launch) → VW contextual bandit (~1k outcomes) → LightFM hybrid (~5–10k) → LightGCN (PyG) gated on ≥50k interactions + 10-core density + shadow-eval win; A/B framework; Precision@K/Recall@K/NDCG | Hand-tuned weights are a good start, not an end; but GNNs on sparse data are worse than heuristics — hence the data-gated ladder (§10.8) | Propensity logging from day 1; all learned scorers run offline; serving stays a dot product on the shortlist | Data-gated, not calendar-gated; instrumentation ships with Phase 3 |
| 5.2 Analytics dashboard | Scheme metrics (applied/approved/funding received), B2B metrics (collaborations/success/value), funding metrics (rounds/conversion/time-to-close), engagement; /analytics APIs; visualizations | The platform's public value proof — and the government-partnership story ("₹X Cr facilitated") | Aggregation queries over operational tables; trend/funnel/distribution charts | Weeks 27–29 |
| 5.3 Agent evaluation | Intent-accuracy tracking (predicted vs actual); swarm latency monitoring; CP-SAT solve-time + infeasibility-rate tracking; user feedback (thumbs + text); automated rule tuning; degradation alerting | Multi-agent quality decays silently without measurement; the cost budget (§10.3) holds only if traced | Langfuse traces + cost-per-turn dashboards from Phase 1 feed this; alert thresholds on accuracy/latency/error spikes | Weeks 27–30 |
| 5.4 Security hardening | SQLi/XSS/CSRF protections verified; AES-256 field encryption (phone, DOB, caste, CIN, GSTIN) with envelope keys; TLS 1.3; RBAC; hash-chained audit logging; external pen test; DPDP consent architecture finalization (§10.9) | Identity documents + caste data = maximum-sensitivity payload; DPDP penalties reach ₹250 Cr; trust is the product | Encryption as SQLAlchemy TypeDecorator + blind indexes; separate caste-consent purpose with bilingual notices; retention scheduler; consent_events ≥7 yrs | Weeks 28–31 (consent schema earlier, in Phase 2) |
| 5.5 Performance | Locust load tests; EXPLAIN ANALYZE + index tuning; connection pooling; API response caching (1–5 min TTL); CP-SAT parameter tuning + model caching; embedding batch/cache optimization; stress tests 2×/5×/10×; horizontal scaling | Targets: p95 <500 ms eligibility, <1000 ms matching, 1000 rps sustained, <0.1% errors | Baseline → optimize hot paths → re-test; scale-out API replicas behind LB | Weeks 29–31 |
| 5.6 Deployment | Dockerfiles + compose (dev since Phase 1); Kubernetes prod cluster; CI/CD (GitHub Actions: test → build → deploy on merge); Prometheus/Grafana + PagerDuty; ELK/CloudWatch logs; automated backups + cross-region DR; blue-green deploys; DR drill | 99.9% uptime is an ops practice, not a wish | Progressive: containers day 1, K8s + full observability when real traffic warrants (per feasibility guidance) | Weeks 30–32 |
| 5.7 Documentation | OpenAPI/Swagger at /docs; developer setup guide (<1 h to running); architecture docs; user guides per category (with screenshots); video tutorials; troubleshooting + FAQ | Team scaling and founder self-service both depend on it | Docs-as-code alongside the repo; bilingual user guides (en/ta) | Weeks 30–32 |

---

# §9 · END-TO-END MESSAGE LIFECYCLE (the mechanism in motion)

Every founder interaction follows seven stages:

1. **Capture & normalize** *(Presentation → NormalizationService → Translation)* — Voice is transcribed (re-ask below confidence threshold); script/language detected; Tanglish transliterated to Tamil with glossary protect-list; non-English translated to English with terms preserved.
2. **Classify & route** *(Orchestrator)* — cascade router labels the intent; ≥0.75 routes to the owning swarm, below it a clarification question; guardrails screen the turn.
3. **Decompose & dispatch** *(Swarm supervisor)* — task split across sub-agents; parallel where independent (LangGraph Send), sequential where dependent; retries with exponential backoff (3 attempts → escalate).
4. **Prove, match, verify** *(Core services)* — CP-SAT solves eligibility/allocation; Graph Engine returns weighted candidates; embeddings score semantic fit; Legal Validator / Document Verifier confirm identity claims via the VerificationGateway.
5. **Persist & cache** *(Data layer)* — results and audit records to Postgres; vectors to pgvector; session state and hot embeddings to Redis; documents encrypted in S3.
6. **Aggregate & validate** *(Supervisor → Orchestrator)* — outputs merged, checked for completeness/consistency, explanations attached (constraints met and violated, by name).
7. **Respond in the founder's language** *(Translation → Presentation)* — glossary-restored translation back to Tamil/Hindi; rendered as text, roadmap timeline, scheme cards, match lists, Kanban board, or speech. Context stack keeps the task resumable for 30 minutes.

**Economics of a turn (§10.3):** ~60% of turns are simple (answered by the small-model tier directly, ~₹0.3), ~30% engage one swarm (~₹6.4), ~10% engage several (~₹13) — blended ≈ ₹3.4/turn with prompt caching, semantic caching, and parallel fan-out, versus ≈ ₹27 naive.

---

# §10 · CONSTRAINTS & SOLUTIONS (the 9 known risks, each solved)

Full problem trees and resource tables: `.kiro/specs/tamil-nadu-startupos/constraint-solutions.md`.

| # | Constraint | Solution (design interfaces unchanged) |
|---|---|---|
| 10.1 | **No MCA21/DPIIT public APIs; Aadhaar OCR restricted** (Critical) | `VerificationGateway` + licensed KYC aggregator drivers (SurePass/Sandbox/Setu) + DigiLocker consent pulls + offline eKYC; zero direct Aadhaar OCR; masked storage only. 4–6 wks; ~₹25k–75k/mo at 1k onboardings. |
| 10.2 | **Scheme data staleness** (Critical) | Owned editorial pipeline: source registry → git-scraping + changedetection.io → LLM extraction with self-refinement → curator GitHub-PR review → versioned publish → tiered freshness SLA with UI-visible `last_verified_at`. One curator, 4–7 h/wk steady state. |
| 10.3 | **Swarm cost/latency (~15×, 4.4→24.4 s)** (High) | Prompt-cache hygiene, semantic caching on FAQs, small-model router + sub-agents with confidence cascade, LangGraph Send parallelism, token streaming, thin supervisors, Batch API for offline jobs, Langfuse tracing. ₹27 → ₹3.4/turn (~87%); simple turns 2–3 s. |
| 10.4 | **100k-node matching impossible in pure Python** (High) | Three-stage funnel: SQL/PostGIS blocking → pgvector ANN → C-backed solvers (scipy LAPJVsp / OR-Tools min-cost-flow / CP-SAT) on shortlists only, async batch cadence. Point queries ~30 ms p50. |
| 10.5 | **IndicBERT embeddings weak for retrieval** (High) | BGE-M3 (1024-dim) behind the same EmbeddingService interface; parallel-column pgvector migration; golden-set gated cutover; IndicBERT retained for intent classification only. |
| 10.6 | **BLEU ≥ 40 meaningless for Tamil** (Medium) | Metric matrix: en↔ta gated on chrF++ ≥ 50 + COMET ≥ 0.75 + glossary stem-match hit-rate ≥ 90% (IN22/FLORES + in-domain set); BLEU retained for Hindi. |
| 10.7 | **Tanglish/Hinglish degrades native-script models** (Medium) | `NormalizationService`: Unicode script check → IndicLID → IndicXlit transliteration with protect-list → code-mix-native LLM fallback (Sarvam-M / Tamil-Llama) capped ~15% of turns; every fallback logged to grow the corpus. |
| 10.8 | **LightGCN cold start** (Managed) | Score-provider ladder: heuristic (launch) → VW contextual bandit (~1k outcomes) → LightFM hybrid (~5–10k) → LightGCN only at ≥50k interactions + 10-core density + shadow-eval win. Nothing blocks launch. |
| 10.9 | **DPDP Act + caste data** (Managed) | Separate caste-consent purpose (bilingual notice, own withdrawal), AES-256-GCM field encryption + blind indexes, hash-chained access audit, retention scheduler, ≥7-yr consent records; DigiLocker pulls double as consent events. 4–6 wks + legal review. |

---

# §11 · TEAM, TIMELINE, COST

**Timeline (full as-designed build):**

| Phase | Window | Duration |
|---|---|---|
| 1 Foundation & Ideation | Weeks 1–8 | 6–8 wks |
| 2 Registered Startup & Schemes | Weeks 9–14 | 4–6 wks |
| 3 B2B Engine | Weeks 15–20 | 4–6 wks |
| 4 Funding Navigator | Weeks 21–26 | 4–6 wks |
| 5 Optimization & Hardening | Weeks 27–32 | 4–6 wks |
| **Total** | | **22–32 weeks** |

**Team (7–9):** 2–3 backend engineers (Python/FastAPI/Postgres) · 1–2 ML engineers (LangGraph/Indic models/OR-Tools) · 1 frontend engineer (React, multilingual/low-literacy UI) · 1 DevOps · 1 QA · 1 technical writer — **plus the named scheme-data curator** (part-time, §10.2), non-negotiable.

**Cost bands (from the feasibility survey):** full as-specced build ₹2.5–4.5 Cr/yr fully loaded. Leaner phased variants exist (managed-API-first ₹40–90 L/yr; single-pillar MVP ₹8–25 L — see `feasibility-survey.md` §B) — the phase order above is compatible with starting lean and internalizing later. Operating costs at early scale: LLM ≈ ₹34k/mo at 10k turns (§10.3), verification ≈ ₹25k–75k/mo at 1k onboardings (§10.1), infra low tens of thousands ₹/mo on managed PaaS before K8s.

---

# §12 · TESTING, CORRECTNESS & DEPLOYMENT

**Correctness properties (what we can actually promise):**
- *Eligibility soundness:* a scheme returned as eligible satisfies **all** encoded constraints (no false positives) — verified by unit tests per constraint type and property-based tests (Hypothesis) asserting every returned scheme satisfies every rule.
- *Eligibility completeness:* every excluded scheme has ≥1 named violated constraint — the "why not" is deterministic.
- *Matching optimality:* returned allocations maximize the stated objective subject to stated constraints — verified against brute force on small fixtures. (Honest framing: optimal **w.r.t. an explicit, auditable objective** — not a claim about business truth.)
- *Data invariants:* completeness-score consistency, trust ∈ [0,100], graph bipartiteness, referential integrity — enforced by checks + FK constraints.

**Test strategy:** 80%+ unit coverage on business logic (90%+ on CP-SAT); integration tests for registry flows and end-to-end scheme matching; property-based tests for constraint logic; MT quality gates (chrF++/COMET/glossary hit-rate) in CI; golden-set retrieval gates for embeddings; Locust load tests (p95 <500 ms eligibility / <1000 ms matching, 1000 rps); OWASP security tests (SQLi/XSS/CSRF/authz).

**Error handling:** standardized `ErrorResponse` (code, message, details, request_id, suggestions); domain errors (CPSAT_INFEASIBLE with most-common violations + improvement suggestions, OCR_LOW_CONFIDENCE, TRANSLATION_FAILED with fallback); retries with exponential backoff; circuit breakers on all external registries; graceful degradation (cloud OCR → local OCR → manual review).

**Deployment:** Docker from day 1 → managed PaaS while traffic is small → Kubernetes with blue-green deploys, Prometheus/Grafana + PagerDuty, ELK logs, automated cross-region backups, and a rehearsed DR drill when scale justifies (Phase 5). ACID transactions with automatic rollback; soft deletes everywhere; audit logs on all founder/startup mutations.

---

## Related documents in this repository

| File | Contents |
|---|---|
| `.kiro/specs/tamil-nadu-startupos/requirements.md` | Full EARS-style acceptance criteria (28 requirements) |
| `.kiro/specs/tamil-nadu-startupos/design.md` | Complete technical design: interfaces, schemas, API bodies, code |
| `.kiro/specs/tamil-nadu-startupos/tasks.md` | 180+ granular tasks with efforts and dependencies |
| `.kiro/specs/tamil-nadu-startupos/feasibility-survey.md` | A–Z feasibility research (26 dimensions, 5 research agents) |
| `.kiro/specs/tamil-nadu-startupos/constraint-solutions.md` | Full problem trees + resource tables for all 9 constraints |
| Blueprint dashboard (artifact) | Interactive visual version of this document |

*— End of master document —*
