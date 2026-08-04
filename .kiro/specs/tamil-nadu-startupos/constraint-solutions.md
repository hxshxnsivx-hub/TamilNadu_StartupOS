# Constraint Solutions: Tamil Nadu StartupOS (Vanigam)

**Date:** 2026-07-16
**Method:** Five parallel AI research agents, one per constraint cluster, each producing a problem tree (root → sub-problems → solution branches), a recommended solution path mapped onto the existing component interfaces (core design unchanged), and a resource table spanning GitHub repos, papers (IEEE/arXiv/ACM), vendor docs, blogs, case studies, and datasets.

**Constraint register (from the feasibility survey):**

| # | Severity | Constraint | Solved in |
|---|---|---|---|
| 1 | Critical | No public MCA21/DPIIT APIs; Aadhaar OCR legally restricted | §A |
| 2 | Critical | Scheme eligibility data has no live feed | §B |
| 3 | High | Two-tier swarm fan-out: ~15× token cost, latency stacking | §C |
| 4 | High | Graph matching at 100k nodes beyond pure-Python | §D |
| 5 | High | IndicBERT CLS embeddings weak for semantic search | §E |
| 6 | Medium | BLEU ≥ 40 not meaningful for Tamil | §E |
| 7 | Medium | Code-mixed (Tanglish/Hinglish) input degrades models | §E |
| 8 | Managed | LightGCN needs interaction data absent at launch | §D |
| 9 | Managed | DPDP Act obligations for PII + caste category | §A |

---

# §A — Government Verification & DPDP Compliance (Constraints 1 & 9)

## A.1 Problem Tree — Registry/Aadhaar access

- **ROOT: Legal_Validator & Document_Verifier depend on sources with no public API or legal restrictions**
  - **SP1: CIN verification — MCA21 has no public API**
    - Licensed aggregators exposing MCA master data (SurePass, Sandbox.co.in, Zoop, Attestr, Karza/Perfios)
    - Zero-cost local pre-validation: CIN regex `^[LU]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}$` before any paid call
    - DigiLocker pull of Certificate of Incorporation (MCA pushes COI for SPICe+ incorporations)
    - Fallback: manual verification queue against MCA "View Company Master Data" (free, no login)
  - **SP2: DPIIT recognition — no public API**
    - DigiLocker pull of DPIIT Certificate of Recognition (DPIIT is a registered DigiLocker issuer → issuer-authenticated = verified)
    - QR code on every DPIIT certificate resolves to official verification URL — parse, validate host, confirm
    - Startup India "Validate Recognition" lookup page as assisted-review fallback
  - **SP3: GSTIN — GSTN access via GSPs/aggregators**
    - Aggregator GSTIN API (SurePass, Cashfree KYB, Zoop, Sandbox)
    - Free local pre-filter: GSTIN Luhn-mod-36 checksum validation
  - **SP4: Aadhaar — direct OCR/storage violates Aadhaar Act §29 + Offline Verification Regulations 2021**
    - Primary: DigiLocker consent-based Aadhaar fetch via aggregator (Setu returns UIDAI-signed JSON+XML — no image handling)
    - Offline paperless eKYC: user uploads UIDAI ZIP + share code; verify UIDAI signature, parse with pyaadhaar
    - Aadhaar Secure QR scan (UIDAI-signed, masked-number demographics)
    - Mandatory hygiene: mask first 8 digits before storage; keep only last-4 + salted hash
  - **SP5: PAN + community certificates**
    - PAN typed input + aggregator NSDL-backed verify (no OCR needed)
    - Vendor Smart OCR only for capture UX (legal for PAN/community certs; Aadhaar only via vendor masking products)
    - TN community certificate: number check against TN e-District genuineness portal; DigiLocker "Revenue Department, Tamil Nadu" issuer pull

## A.2 Recommended Solution Path

- **Widest single vendor: SurePass** (MCA CIN/DIN, PAN↔CIN↔GST pivots, GST, DigiLocker, Aadhaar offline, Udyam; sandbox; prepaid). **Self-serve alternative: Sandbox.co.in** (public cost calculator, no sales cycle). **DigiLocker specialist: Setu** (cleanest docs, public sandbox `dg-sandbox.setu.co`).
- **Build a `VerificationGateway`** module with a driver interface (`verify_cin`, `verify_gstin`, `verify_dpiit`, `digilocker_pull`, `parse_offline_ekyc`); Legal_Validator and Document_Verifier call the gateway; per-vendor drivers make swaps a config change.
- **Legal_Validator mapping:** local regex/checksum pre-filters → vendor API → cache 30–90 days; DPIIT primary = DigiLocker pull, secondary = QR validation, tertiary = manual queue.
- **Document_Verifier mapping:** remove direct Aadhaar OCR entirely; DigiLocker route or offline eKYC ZIP route; persist only name, DOB, masked number, salted SHA-256 for dedup. PAN via sync verify. Community cert via OCR → e-District check → category flag stored under the caste-consent regime.
- **Day-1 action:** call Setu `GET /api/digilocker/documents` to enumerate the live catalog and confirm docType IDs for DPIIT cert, MCA COI, TN community certificate.

**Effort ≈ 4–6 dev-weeks. Cost at ~1,000 onboardings/month × ~5 checks ≈ ₹25k–75k/month** (PAN ~₹1.5–3, GSTIN ~₹2–5, MCA ~₹5–15, DigiLocker ~₹3–10, Aadhaar offline ~₹2–5 per call). Pre-filters cut paid volume ~10–20%.

## A.3 Problem Tree — DPDP Act (caste + PII)

- **ROOT: Platform processes PII incl. caste category with DPDP-grade consent, retention, and security duties**
  - **SP1: DPDP has NO "sensitive data" category — caste protection must be self-imposed**
    - Separate standalone consent purpose for caste (own purpose ID, notice text, withdrawal toggle)
    - Purpose limitation: caste used ONLY for scheme eligibility; never analytics/ML
    - Store derived eligibility flag, not certificate scan, where possible; encrypt the field
  - **SP2: Consent architecture (DPDP Rules 2025)**
    - Internal consent-artifact service (do NOT register as a Consent Manager — needs India inc. + ₹2cr net worth; just be interoperable)
    - DEPA/ORGANS artifact design (Sahamati/iSPIRT specs)
    - Bilingual (English + Tamil) standalone notice: itemised data, per-purpose, withdrawal, DPB complaint channel
    - Consent records retained ≥7 years — append-only `consent_events` table
  - **SP3: Retention & erasure**
    - Retention schedule per data class; nightly purge scheduler (pg_cron/Celery beat); withdrawal triggers immediate erasure pipeline
  - **SP4: Security safeguards**
    - Application-level AES-256-GCM envelope encryption (DEK/KEK) as SQLAlchemy TypeDecorator for caste, masked Aadhaar, DOB
    - HMAC blind index for encrypted-field lookups
    - Append-only hash-chained audit log of every access to caste/KYC fields; breach-notification runbook

**Effort ≈ 4–6 dev-weeks + ₹50k–1.5L one-time legal review.** Synergy: every DigiLocker pull is itself a DPDP consent event — log it in `consent_events` for one unified evidence trail.

## A.4 Key Resources

| Resource | Type | URL | Gives us |
|---|---|---|---|
| Setu DigiLocker quickstart | Docs | https://docs.setu.co/data/digilocker/quickstart | Exact endpoints + sandbox |
| SurePass MCA APIs | Vendor | https://surepass.io/mca-data-apis-cin-din/ | Widest single-vendor surface |
| Sandbox.co.in KYC + cost calculator | Vendor | https://developer.sandbox.co.in/api-reference/kyc/overview | Self-serve APIs, transparent pricing |
| Cashfree Secure ID | Vendor | https://www.cashfree.com/docs/secure-id/introduction | Smart OCR + Aadhaar-masking product |
| pyaadhaar | GitHub | https://github.com/tanmoysrt/pyaadhaar | Secure QR + offline eKYC XML decoding |
| Aadhaar_OCR (masking) | GitHub | https://github.com/rohanrao619/Aadhaar_OCR | Masking pipeline reference |
| Verhoeff validator | GitHub | https://github.com/NikhilPanwar/aadharCardValidatorAndGenerator | Aadhaar checksum |
| GSTIN checksum | GitHub | https://github.com/tk120404/gst | Free pre-filter logic |
| digilocker_python_sdk / digimocker | GitHub | https://github.com/shriharishastry/digilocker_python_sdk , https://github.com/dkp1903/digimocker | OAuth wrapper + CI mock |
| TN e-District Verify | Gov | https://tnedistrict.tn.gov.in/tneda/VerifyCerti.xhtml | Community-cert genuineness check |
| Razorpay BVS blog | Blog | https://engineering.razorpay.com/customer-onboarding-at-razorpay-optimising-identity-verification-4a64a7f28b5a | Industrial gateway blueprint (85% instant onboarding) |
| UIDAI Offline Verification Regs 2021 | Legal | https://uidai.gov.in/images/The_Aadhaar_Authentication_and_Offline_Verifications_Regulations_2021.pdf | Legal basis for the eKYC route |
| DPDP Rules 2025 Rule 4 | Legal | https://www.dpdpa.in/dpdpa_rules_2025/Rule_4.htm | CM registration conditions |
| iSPIRT DEPA / Sahamati standards | GitHub | https://github.com/iSPIRT/DEPA , https://github.com/Sahamati/account-aggregator-standards | Consent-artifact JSON schemas |
| sovio-id consent demo | GitHub | https://github.com/sovio-id/consent-management-demo | DPDP consent reference implementation |
| Crunchy Data encryption guidebook | Blog | https://www.crunchydata.com/blog/data-encryption-in-postgres-a-guidebook | DEK/KEK envelope pattern |
| NLS IJLT caste-data paper | Paper | https://forum.nls.ac.in/ijlt-blog-post/removing-the-category-of-sensitive-personal-data-under-the-dpdpa-heightening-data-principal-vulnerability/ | DPIA citation for heightened caste protection |

---

# §B — Scheme Data Pipeline (Constraint 2)

**Central finding:** nobody has a live feed because none exists — Haqdarshak (7,000+ schemes) uses a human research team; mRelief's policy team watches sources and hands changes to engineers; myScheme is manually curated by NeGD. The winning pattern everywhere: **automated watching + LLM-assisted structuring + human sign-off**. Goal: one curator at ~4–6 hrs/week, not a research team.

## B.1 Problem Tree

- **ROOT: Scheme eligibility data goes stale silently — wrong deadlines/amounts/criteria destroy trust and cause failed applications**
  - **SP1: Acquisition — data scattered and unstructured**
    - Seed from existing scrapes: `shrijayan/gov_myscheme` (723 schemes, Apache-2.0), Kaggle dumps, OpenNyAI scrape
    - Scrape myScheme's own per-scheme JSON (Next.js page API + sitemap); `rules.myscheme.gov.in` proves criteria are internally structured
    - Canonical-source registry: 1–3 official `source_urls` per scheme (page, guidelines PDF, portal)
  - **SP2: Change detection — pages/PDFs change without notice**
    - Self-hosted changedetection.io (XPath/JSONPath monitors, notifications)
    - Git-scraping (Simon Willison pattern): nightly GitHub Action commits fetched pages; git diff = free change history + audit trail
    - Push channels where they exist: PIB RSS, StartupTN newsletter, DPIIT notifications. Precedent: CivicDataLab scraped 81M eCourts records — Indian gov sites are scrapeable with patience
  - **SP3: Structuring — eligibility prose → machine-checkable JSONB**
    - LLM extraction against strict JSON Schema with validation-retry loop
    - De Jure-style iterative self-refinement (extract → LLM-judge → repair; arXiv 2604.02276)
    - Rules-as-Code vocabulary modeled on OpenFisca/PolicyEngine parameter files (no OpenFisca-India exists — in-house dialect justified)
  - **SP4: Trust — LLMs and scrapes err; users make money decisions**
    - Named curator + review queue; nothing goes live unreviewed
    - `last_verified_at` stamp in UI + "verify on official page" deep link
    - Cross-source consistency checks (disagreement ⇒ flag)
  - **SP5: Freshness governance**
    - Tiered re-verification SLA (T1: 30 days, T2: 90 days)
    - Staleness dashboard + weekly digest
    - Git repo of per-scheme YAML is source of truth; DB is a build artifact

## B.2 Recommended Pipeline

```
SOURCES ──► MONITORS ──► LLM EXTRACTION ──► HUMAN REVIEW ──► VERSIONED PUBLISH ──► FRESHNESS SLA
(registry)  (detect)     (structure)        (GitHub PR)      (git → Postgres)      (re-queue)
```

- **Stage 0:** `sources.yaml` per scheme: official URLs, monitoring selector, tier. Seed list from myScheme scrape + Startup India + StartupTN/MSME-TN.
- **Stage 1:** git-scraper repo (nightly Actions; Playwright for JS pages) + changedetection.io on high-value pages (TANSEED window, SISFS portal).
- **Stage 2:** on change: page/PDF → markdown → LLM with target JSON Schema → Pydantic validation → one self-refinement pass → **draft diff** with per-field confidence and quoted source spans.
- **Stage 3:** extraction bot opens a **GitHub PR** (one YAML per scheme); named curator reviews field-level diff with source quotes; CI validates schema, funding-range sanity, deadline-in-future, dead links. PR review IS the editorial workflow.
- **Stage 4:** merge → sync job upserts Postgres; git history = versioning; monthly release tags.
- **Stage 5:** scheduled job re-queues schemes past their SLA even without detected change; Datasette/Metabase staleness dashboard.

**Schema additions** (keeps existing `schemes` table): `source_urls TEXT[]`, `last_verified_at`, `verified_by`, `verification_tier`, `data_version` (git SHA), `review_status`, plus a `scheme_changelog` table. The `eligibility_criteria` JSONB gets a pinned shape: `rules[]` (field/op/value/source_quote/confidence) + `combinator` compile directly to CP-SAT; `unmodelled_text` is surfaced verbatim by the Explainer instead of silently dropped — **the single most important honesty mechanism**.

**Effort:** initial ≈ 130–190 h (~4–6 weeks, 1 engineer + part-time curator; the irreducible cost is 60–90 h first-pass human verification of 80–100 schemes). **Steady state ≈ 4–7 h/week** for one named curator. Expect 3–4× alert spikes in budget season (Feb); bank schemes change via circulars — subscribe to RBI/SIDBI newsletters.

## B.3 Key Resources

| Resource | Type | URL | Gives us |
|---|---|---|---|
| shrijayan/gov_myscheme | Dataset | https://huggingface.co/datasets/shrijayan/gov_myscheme | 723-scheme seed corpus (Apache-2.0) |
| myScheme + eligibility engine | Site | https://www.myscheme.gov.in/ , https://rules.myscheme.in/ | Canonical aggregator; structured criteria exist per scheme |
| APISetu myScheme collection | Docs | https://directory.apisetu.gov.in/api-collection/myscheme | Official (limited) APIs — register anyway |
| Startup India schemes + state policies | Docs | https://www.startupindia.gov.in/content/sih/en/government-schemes.html | Authoritative central list |
| StartupTN / TANFUND / MSME-TN | Docs | https://startuptn.in/ , https://www.tanfund.in/ | Primary TN monitor targets |
| changedetection.io | GitHub | https://github.com/dgtlmoon/changedetection.io | Core monitoring layer |
| Git scraping (Willison) | Blog | https://simonwillison.net/tags/git/ | Zero-cost monitor + audit trail pattern |
| De Jure self-refinement | Paper | https://arxiv.org/html/2604.02276 | The Stage-2 extraction loop (≥90% via judge-repair) |
| Beeck Center AI Rules-as-Code | Report | https://beeckcenter.georgetown.edu/report/ai-powered-rules-as-code-experiments-with-public-benefits-policy/ | Evidence-based guardrails: assistive only, human in loop |
| OpenFisca / openfisca-aotearoa / PolicyEngine | Docs/GitHub | https://openfisca.org/en/ , https://github.com/policyengine | Parameter-file format + PR-reviewed country packages as workflow blueprint |
| mRelief case study | Case study | https://digitalgovernmenthub.org/publications/mrelief/ | The maintenance playbook we adopt |
| Haqdarshak | Precedent | https://www.haqdarshak.com/ | Validates editorial-asset strategy at 7,000-scheme scale |
| Indus Action + IDinsight | Case study | https://www.idinsight.org/article/using-algorithms-to-match-elibible-people-to-social-benefits-in-india/ | Eligibility engines under incomplete data |
| CivicDataLab / DataMeet | GitHub | https://github.com/CivicDataLab , https://github.com/datameet | Indian gov-scraping precedents + community to hire from |
| Datasette / Dolt | Docs/GitHub | https://datasette.io/ , https://github.com/dolthub/dolt | Curator dashboard; git-for-data upgrade path |

---

# §C — Economical Swarm (Constraint 3)

**Goal:** keep the swarm architecture; cut ~15× token cost and 4.4s→24.4s latency stacking to economical levels.

## C.1 Problem Tree

- **ROOT: Every user turn re-pays the full swarm — ~15× tokens, ~6× latency vs a single agent**
  - **SP1: Redundant token spend**
    - **Provider prompt caching** (biggest single lever, ~90% off repeated prefixes): Anthropic `cache_control` — reads ≈ 0.1× input price, writes 1.25× (5-min TTL) / 2× (1-hr); prefix order `tools → system → messages`; any byte change invalidates everything after. Min cacheable prefix is model-dependent (1024–4096 tokens) — pad thin agent prompts or they silently never cache. OpenAI caches automatically ≥1024 tokens (~50–75% off). **Fan-out gotcha:** a cache entry is readable only after the first response starts streaming — fire 1 sub-agent, await first token, then fire the remaining N−1. Pre-warm with a `max_tokens: 0` request at boot.
    - **Semantic/response caching:** GPTCache (reference design; MIT, unmaintained since Aug 2024), Redis LangCache (managed; ~70% hit rate, 70–90% spend reduction in case data), or one-line LangChain `RedisSemanticCache`. Cache stateless scheme-FAQ answers only (sim ≥0.9); never personalized outputs.
    - **Context discipline:** supervisors pass task specs + IDs, not transcripts; sub-agents return structured JSON, not prose. AgentPrune (arXiv 2410.02506): pruning the message-passing graph cuts 28–73% of tokens at comparable quality. LangGraph mechanics: `trim_messages`, reducers keeping `messages[-k:]`, summarization node, per-subgraph private state.
    - **Batch API for offline jobs:** Anthropic/OpenAI batch = 50% off all tokens; move scheme re-annotation, nightly readiness re-scoring, match refresh there (batches also support prompt caching).
  - **SP2: Wrong-size model doing the work**
    - Heuristic + small-model routing first (one day of work): regex shortlist → Haiku classifier with cached prompt emitting `{route, confidence}` (~$0.001/turn). Routes: SIMPLE / SINGLE_SWARM / MULTI_SWARM.
    - Learned routers when traffic justifies: RouteLLM (85% cost cut at 95% GPT-4 quality; Apache-2.0 drop-in), NotDiamond/Martian/OpenRouter for multi-provider.
    - Confidence cascades: FrugalGPT (up to 98% cost cut matching GPT-4) / AutoMix pattern — sub-agent runs on Haiku with self-verification; `confidence < 0.7` → single retry on Sonnet (~15–20% escalation expected).
  - **SP3: Latency stacks because hops are serial**
    - LangGraph `Send` API = dynamic map-reduce: all sub-agents of a swarm run in one superstep — wall time = max(sub-agent), not sum. Parallelize only independent sub-agents.
    - Stream tokens (`stream_mode="messages"`) → TTFT ~1–2s even on 10s turns; stream supervisor progress events during fan-out.
    - Thin supervisors: structured-output plans only (strict JSON, `max_tokens ≤ 500`); orchestrator answers SIMPLE turns itself; collapse one-step plans into direct calls.
    - Checkpointing (`PostgresSaver`): resume state per thread — never recompute; failures resume from the failed node.
  - **SP4: No visibility → can't tune**
    - Tracing: **Langfuse** (OSS self-host, free — recommended) vs LangSmith (deepest LangGraph integration, ~$39/user/mo Plus) vs Helicone (proxy + built-in caching) vs Arize Phoenix (OTel-native OSS).
    - Budget guards: per-turn token budget in graph state, recursion limits per swarm, alert when `cache_read = 0` (silent invalidator detector).

## C.2 Recommended Reference Configuration

| Role | Model | Settings |
|---|---|---|
| Router / intent classifier | Haiku | cached system prompt, strict JSON, `max_tokens: 256` |
| Central orchestrator | Sonnet | streaming; answers SIMPLE turns itself |
| Swarm supervisors ×5 | Haiku (Profile/Scheme), Sonnet (B2B/Roadmap/Funding planning) | plan-only output, `max_tokens: 500` |
| Sub-agents (~20) | Haiku default; cascade to Sonnet on `confidence < 0.7` | tool-use, JSON results, no prose |
| Explainer / final synthesis | Sonnet | streamed |
| Offline jobs | Haiku/Sonnet via Batch API | 50% off |

**Caching layers in request order:** L0 exact-match Redis (TTL 10 min) → L1 semantic cache for stateless scheme/FAQ intents (target 30%+ hit rate) → L2 provider prompt cache (frozen per-agent prefixes; 1-hr TTL on the scheme-corpus block; staggered fan-out) → L3 nightly Batch precompute.

**Routing mix assumption:** ~60% SIMPLE → Haiku direct; ~30% SINGLE_SWARM; ~10% MULTI_SWARM. Never fan out to all 5 swarms.

**Cost per user-turn (₹87/$):**
- Naive baseline (all Sonnet, no cache, full chain ≈ 74K in / 5.6K out): **≈ $0.31 ≈ ₹27/turn**
- SIMPLE turn: **≈ ₹0.29** (30% of these ≈ ₹0 via semantic cache)
- SINGLE_SWARM: **≈ ₹6.4** · MULTI_SWARM: **≈ ₹13**
- **Blended ≈ ₹3.4/turn → at 10K turns/month ≈ ₹34K vs ₹2.7L naive (~87% / ≈8× reduction)**

**Latency:** simple turns 24.4s → ~2–3s; full-swarm wall time → ~10–12s via `Send` parallelism; perceived TTFT → ~1–2s via streaming.

**Build order:** (1) Langfuse tracing + cost logging — measure first; (2) prompt-cache hygiene; (3) `Send` parallelism + streaming; (4) Haiku router + SIMPLE short-circuit; (5) Haiku sub-agents with cascade; (6) semantic cache on scheme FAQs; (7) Batch API nightly jobs; (8) RouteLLM once real traffic exists.

## C.3 Key Resources

| Resource | Type | URL | Gives us |
|---|---|---|---|
| Anthropic prompt caching | Docs | https://platform.claude.com/docs/en/build-with-claude/prompt-caching | `cache_control` mechanics, 0.1×/1.25×/2× multipliers |
| OpenAI prompt caching | Docs | https://platform.openai.com/docs/guides/prompt-caching | Automatic ≥1024-token caching |
| RouteLLM | GitHub/Paper | https://github.com/lm-sys/RouteLLM , https://arxiv.org/abs/2406.18665 | 85% cost cut @ 95% quality; drop-in client |
| FrugalGPT | Paper | https://arxiv.org/abs/2305.05176 | Cascade blueprint (up to 98% cost cut) |
| AutoMix | Paper | https://arxiv.org/abs/2310.12963 | Self-verification cascade |
| AgentPrune | Paper | https://arxiv.org/abs/2410.02506 | 28–73% token cut by pruning agent communication |
| GPTCache / Redis LangCache | GitHub/Product | https://github.com/zilliztech/GPTCache , https://redis.io/langcache/ | Semantic-cache design + managed option (~70% hit rate) |
| LangGraph Send / persistence / streaming | Docs | https://langchain-ai.github.io/langgraph/how-tos/graph-api/ | Parallel fan-out, checkpointing, token streaming |
| Built with LangGraph | Blog | https://www.langchain.com/built-with-langgraph | Production case studies (Klarna, Replit, LinkedIn, Uber) |
| Anthropic Message Batches | Docs | https://platform.claude.com/docs/en/build-with-claude/batch-processing | 50% discount for offline jobs |
| Langfuse / Helicone / Phoenix | GitHub | https://github.com/langfuse/langfuse , https://github.com/Helicone/helicone , https://github.com/Arize-ai/phoenix | OSS tracing + cost dashboards |

---

# §D — Graph Matching at Scale + GNN Cold Start (Constraints 4 & 8)

## D.1 Problem Tree — 100k-node matching

- **ROOT: NetworkX pure-Python O(n³) blossom cannot serve 100k nodes / 1M edges at <1s**
  - **SP1: Solver too slow**
    - C/Rust-backed bipartite solvers: `scipy.sparse.csgraph.min_weight_full_bipartite_matching` (LAPJVsp, sparse CSR — the right primitive), `scipy.optimize.linear_sum_assignment` (dense shortlists), rustworkx (3–100× over NetworkX, only if non-bipartite ever needed), OR-Tools `LinearSumAssignment` and `SimpleMinCostFlow` ("often faster than MIP or CP-SAT")
    - C++ frameworks (graph-tool/igraph/NetworKit): overkill — scipy already ships the needed kernel
    - GPU cuGraph Hungarian: defer until ~10⁶-edge dense subproblems
  - **SP2: Even a fast solver must not see the whole graph**
    - Attribute blocking by tier/domain/material (entity-resolution blocking literature: Papadakis et al., ACM CSUR 2020)
    - ANN pre-filter on spec embeddings: pgvector HNSW (filtered queries ~70ms at 10M vectors → single-digit ms at our 100k) or FAISS (p95 0.42ms at 10M)
    - Geo pre-filter: PostGIS `ST_DWithin` + GiST = ms-scale radius filters
    - Precedent: DoorDash DeepRed, Uber batched matching, Instacart minute-cadence re-solve — all use candidate-generation → scoring → small optimization funnels
  - **SP3: Point queries vs global allocation are different problems**
    - Point query: blocking + ANN + vectorized scoring — no combinatorial solver at all
    - Batch allocation: solver only on the union of shortlists, async batch cadence (seconds–minutes)

## D.2 Recommended Architecture

Keep `GraphEngine` as the interface; three-stage funnel inside:

1. **Blocking (SQL, ~5–20 ms):** one Postgres query — exact blocks (domain/category/tier) + PostGIS geo-radius + capacity > 0. 100k → ~2–5k candidates.
2. **ANN + scoring (~5–15 ms):** pgvector HNSW top-K (K=200) within the blocked set, then vectorized NumPy composite weight (0.4/0.3/0.2/0.1). **Point queries return here: ~20–50 ms total — 20–50× inside the <1s budget.**
3. **Assignment (batch only):** sparse biadjacency over union of shortlists →
   - pure 1:1 → scipy LAPJVsp (tens of ms at 1,000×5,000 with ~200k finite entries)
   - capacity-constrained many-to-one → OR-Tools `SimpleMinCostFlow` (**default allocation path**)
   - rich constraints (MOQ, exclusivity, splits) → same shortlist edge set to `CPSAT_Boundary`, `max_time_in_seconds=5–10`, async cadence 30s–5min, warm-start via `AddHint` from previous batch.

Keep NetworkX for test parity on ≤500-node fixtures. **Realistic latency: point query p50 ≈ 30 ms, p99 ≤ 150 ms; batch allocation 1–10 s async.**

## D.3 Problem Tree — LightGCN cold start

- **ROOT: Phase-5 LightGCN needs match-outcome interactions that are zero at launch**
  - **SP1: No signal at day 0** → ship heuristic composite as a legitimate content-based recommender (`Scorer.v0`); first learned model = LightFM hybrid (metadata embeddings generalize to brand-new startups)
  - **SP2: Early data biased by what we show** → Vowpal Wabbit contextual bandit (`--cb_explore_adf`) re-ranker over the top-20 shortlist with 10% exploration; log propensities from day 1
  - **SP3: When to graduate?** → LightGCN benchmarks all use ≥1M interactions after 10-core filtering; gate on graph density, not calendar
  - **SP4: Implementation** → PyTorch Geometric `LightGCN`, RecBole for shadow-eval harness, gusye1234 reference repo

## D.4 Score-Provider Ladder (behind `GraphEngine.score_edges()`)

| Stage | Trigger | Scorer |
|---|---|---|
| 0 (launch) | 0 interactions | Heuristic composite + full instrumentation (impressions, contacts, outcomes, propensities) |
| 1 | ~1,000 outcomes | + VW contextual-bandit re-ranker (sub-ms scoring, 10% exploration) |
| 2 | ~5,000–10,000 outcomes | LightFM (WARP loss; features = sector/tier/district/materials/embedding-cluster); blend α·LightFM + (1−α)·heuristic via A/B |
| 3 (gate) | ALL of: ≥50k–100k interactions; 10-core covers ≥30% of active nodes; LightGCN beats LightFM by ≥5% Recall@20 in shadow | LightGCN (PyG), LightFM fallback for out-of-core nodes |

Realistically the Stage-3 gate is 12–24 months post-launch — which is why the constraint is "Managed": nothing blocks launch. All learned scorers run offline/batch; online serving stays a dot product over ≤200 candidates.

## D.5 Key Resources

| Resource | Type | URL | Gives us |
|---|---|---|---|
| scipy min_weight_full_bipartite_matching | Docs | https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.csgraph.min_weight_full_bipartite_matching.html | The exact GraphEngine backend |
| berhane/LAP-solvers | GitHub | https://github.com/berhane/LAP-solvers | Benchmarks to 16,384×16,384 proving C-backed scale |
| gatagat/lap | GitHub | https://github.com/gatagat/lap | Fastest LAPJV/LAPMOD if scipy bottlenecks |
| rustworkx | Docs/Paper | https://www.rustworkx.org/benchmarks.html , https://arxiv.org/pdf/2110.15221 | 3–100× NetworkX; migration guide |
| OR-Tools min-cost-flow assignment | Docs | https://developers.google.com/optimization/flow/assignment_min_cost_flow | Default capacity-constrained allocation |
| Papadakis et al. blocking survey | Paper | https://dl.acm.org/doi/abs/10.1145/3377455 | Taxonomy for the blocking layer |
| DoorDash DeepRed | Blog | https://careersatdoordash.com/blog/using-ml-and-optimization-to-solve-doordashs-dispatch-problem/ | Funnel precedent; solver 10× faster than Hungarian |
| Uber Marketplace Matching | Blog | https://www.uber.com/us/en/marketplace/matching/ | Batched bipartite windows |
| Instacart × Gurobi | Blog | https://www.gurobi.com/case_studies/instacart-delivering-optimal-shopping-experiences/ | Minute-cadence re-solving |
| pgvector | GitHub | https://github.com/pgvector/pgvector | HNSW in Postgres; 0.8.0 filtered-search gains |
| PostGIS indexing | Blog | https://www.crunchydata.com/blog/postgis-performance-indexing-and-explain | ms-scale geo filters |
| lyst/lightfm + paper | GitHub/Paper | https://github.com/lyst/lightfm , https://arxiv.org/pdf/1507.08439 | Stage-2 hybrid model + cold-start theory |
| VW contextual bandits | Docs | https://vowpalwabbit.org/docs/vowpal_wabbit/python/9.0.1/tutorials/python_Contextual_bandits_and_Vowpal_Wabbit.html | Stage-1 bandit recipe (+ warm-start wiki) |
| LightGCN paper + PyG + RecBole | Paper/Docs | https://arxiv.org/abs/2002.02126 , https://pytorch-geometric.readthedocs.io/en/2.5.2/generated/torch_geometric.nn.models.LightGCN.html | Phase-5 target + graduation-gate anchor (≥1M interactions, 10-core) |
| Supplier recommendation in procurement | Paper | https://arxiv.org/html/2403.01301v1 | Validates metadata-first B2B cold start |
| Turing Institute procurement recommenders | Project | https://www.turing.ac.uk/research/research-projects/network-based-recommender-systems-public-procurement | Closest academic analogue to Vanigam's B2B graph |
| Bandit + centralized matching | Paper | https://arxiv.org/pdf/2105.02589 | Stage-1 bandit + Stage-3 allocation composition |

---

# §E — Indic NLP Fixes (Constraints 5, 6, 7)

## E.1 Problem Tree — Embedding swap (Constraint 5)

- **ROOT: pgvector semantic search returns poor neighbors — IndicBERT CLS vectors were never trained for retrieval**
  - **SP1: Wrong training objective** (MLM-only → anisotropic CLS vectors)
    - Swap to a contrastively-trained retrieval model behind the same `EmbeddingService` interface: **BAAI/bge-m3** (primary — 1024-dim dense, 8192-token ctx, 100+ langs, MIT, no query prefix needed), `intfloat/multilingual-e5-large-instruct` (alt; strongest published Indic aggregate on MMTEB ≈66.4, needs query instruction prefix), `Alibaba-NLP/gte-multilingual-base` (768-dim CPU-lean alt), `l3cube-pune/indic-sentence-similarity-sbert` (Indic-specialist A/B baseline)
    - Keep IndicBERT ONLY for intent classification (its actual strength) — it exits the retrieval path entirely
  - **SP2: Dimension change breaks pgvector schema** (768 → 1024; no valid cast)
    - Parallel-column zero-downtime migration: add `vector(1024)` → batch backfill → dual-write → HNSW index `CONCURRENTLY` → flip behind flag → validate → drop old
    - `halfvec(1024)` + HNSW to halve index size if RAM-bound
  - **SP3: CPU serving cost** → HF text-embeddings-inference server (ONNX x86, batching) or sentence-transformers `backend="onnx"` + int8 quantization (prebuilt `gpahal/bge-m3-onnx-int8`)
  - **SP4: Query/passage asymmetry** → encode prompt handling inside `embed(text, kind=query|passage)` so callers can't get it wrong
  - **SP5: No Tamil retrieval gold set** → build a 150–300-pair in-domain golden set (founder questions → scheme docs in ta/en/hi + Tanglish); gate migration on Recall@10 / nDCG@10 deltas

**Targets:** golden-set Recall@10 ≥ 0.85, nDCG@10 ≥ 0.65 for Tamil (expect +15–30 nDCG points over IndicBERT-CLS); cross-lingual en-query→ta-doc Recall@10 ≥ 0.75; p95 ≤ 100 ms/query embed on 4 vCPU int8 ONNX.

## E.2 Problem Tree — Tamil MT evaluation (Constraint 6)

- **ROOT: word-level BLEU punishes valid Tamil morphology (one Tamil word ≈ an English phrase) — a "BLEU ≥ 40" gate is unreachable/uninformative for en↔ta**
  - **SP1: Metric–language mismatch** → **chrF++** via sacreBLEU (`-m chrf --chrf-word-order 2`; the metric AI4Bharat itself uses) + **COMET** (`Unbabel/wmt22-comet-da`, Apache-2.0) + Indic-COMET (AI4Bharat, tuned on Indian-language MQM); IndicMT-Eval (ACL 2023) shows string metrics correlate poorly with humans for Indic while COMET correlates best. Keep BLEU ≥ 40 for en↔hi only.
  - **SP2: No standard test data in the pipeline** → IN22-Gen (1,024) + IN22-Conv (1,503 conversational — matches chat use case; CC-BY-4.0) + FLORES-200 + a 200–300-sentence in-domain startup/regulatory set translated once
  - **SP3: Glossary compliance unmeasured** → glossary hit-rate with **morphological stem-matching** (match Tamil stem inside suffixed forms), per the WMT Terminology Shared Task pattern
  - **SP4: Runtime gating without references** → `wmt22-cometkiwi-da` is CC-BY-NC-SA (non-commercial) — internal monitoring only; gate releases with COMET-DA on referenced batches

**Targets (realistic):** en→ta chrF++ ≥ 50 on IN22/FLORES (IndicTrans2-1B publishes mid-50s); en→ta COMET-DA ≥ 0.75; glossary hit-rate ≥ 90% (stem-match); en↔hi keeps BLEU ≥ 40 + chrF++ ≥ 55. Context for the docs: SOTA en→ta BLEU is typically 25–35 — which is precisely why the 40 gate was wrong.

## E.3 Problem Tree — Code-mixing (Constraint 7)

- **ROOT: users type romanized/code-mixed Tamil ("naan oru startup start pannalama?") that native-script models weren't trained on**
  - **SP1: Detecting romanized Indic** → Unicode-block check first (free); Latin-script text → **AI4Bharat IndicLID** (47-class incl. `ta-rom`/`hi-rom`; trained on Bhasha-Abhijnaanam)
  - **SP2: Roman → native script** → **AI4Bharat IndicXlit** (trained on Aksharantar 26M pairs; +15% over baseline on Dakshina); token-level pass keeps English/glossary terms ("GST", "funding") Latin via protect-list. Avoid libindic/indic-trans (AGPL-3.0 — SaaS license risk).
  - **SP3: When normalization fails** → LLM fallback: Sarvam-M (`sarvamai/sarvam-m`, code-mix-native, API + open weights) or self-hosted `abhinand/tamil-llama-7b-instruct-v0.2` (GGUF for CPU); log low-confidence turns to grow a Tanglish corpus
  - **SP4: No Tanglish eval data** → DravidianCodeMix (~44k Tanglish comments, CC-BY-4.0), Dakshina (transliteration gold), L3Cube HingCorpus/HingBERT (Hinglish side)

**Pipeline:** script check → (Latin) IndicLID → (ta-rom/hi-rom, p≥0.8) protect-list + IndicXlit → existing pipeline; low confidence (LID p<0.8 OR intent softmax <0.6) → LLM fallback that both answers and emits the normalized form for logging. Insert as a `NormalizationService` in front of intent classification and translation; store raw + normalized; index normalized in pgvector; cap fallback at ~15% of turns with alerting.

**Targets:** romanized LID ≥ 85% on the 3-way subset; transliteration ≥ 70% top-1 / ≥ 90% top-3 on Dakshina Tamil; Tanglish intent accuracy within 5 points of native-Tamil; fallback rate ≤ 15%.

## E.4 Cross-cutting integration

One composed request path: **script/LID router → transliteration normalizer → IndicBERT intent (unchanged) → IndicTrans2 gated by chrF++/COMET/glossary metrics → BGE-M3 1024-dim embeddings in pgvector → LLM fallback on low aggregate confidence.** Every stage emits a confidence score; min-confidence drives the fallback; all low-confidence turns feed the in-domain eval corpora.

## E.5 Key Resources

| Resource | Type | URL | Gives us |
|---|---|---|---|
| BGE-M3 | Model | https://huggingface.co/BAAI/bge-m3 | Primary embedding model (1024-dim, MIT) |
| multilingual-e5-large-instruct | Paper/Model | https://arxiv.org/pdf/2402.05672 | Alt model + prompt format |
| MMTEB | Paper | https://arxiv.org/pdf/2502.13595 | Indic-subset scores justifying the choice |
| IndicRAGSuite | Paper | https://arxiv.org/pdf/2506.01615 | Indian-language RAG benchmark incl. Tamil |
| L3Cube IndicSBERT | Paper/Model | https://arxiv.org/pdf/2304.11434 , https://huggingface.co/l3cube-pune/indic-sentence-similarity-sbert | Indic baseline checkpoints |
| text-embeddings-inference | GitHub | https://github.com/huggingface/text-embeddings-inference | Production CPU embedding server |
| pgvector migration writeups | Blog | https://www.nite07.com/en/posts/honcho-embedding-dimensions/ | Parallel-column dimension migration pattern |
| IndicTrans2 repo (+ IN22, metric scripts) | GitHub | https://github.com/AI4Bharat/IndicTrans2 | `compute_metrics.sh`, `compute_comet_score.sh`, metric archives |
| IndicMT-Eval | GitHub/Paper | https://github.com/AI4Bharat/IndicMT-Eval , https://aclanthology.org/2023.acl-long.795/ | Evidence BLEU fails for Indic; Indic-COMET checkpoints |
| wmt22-comet-da / COMET | Model/GitHub | https://huggingface.co/Unbabel/wmt22-comet-da , https://github.com/Unbabel/COMET | Apache-2.0 semantic MT metric |
| sacreBLEU | GitHub | https://github.com/mjpost/sacrebleu | chrF++ implementation |
| IndicLID + Bhasha-Abhijnaanam | GitHub/Paper/Dataset | https://github.com/AI4Bharat/IndicLID , https://arxiv.org/abs/2305.15814 | Romanized-Indic language ID |
| IndicXlit + Aksharantar | GitHub/Paper/Dataset | https://github.com/AI4Bharat/IndicXlit , https://arxiv.org/abs/2205.03018 | Roman→native transliteration |
| Dakshina | Dataset | https://github.com/google-research-datasets/dakshina | Transliteration eval gold (Tamil) |
| DravidianCodeMix | Paper/Dataset | https://arxiv.org/abs/2106.09460 | ~44k Tanglish corpus (CC-BY-4.0) |
| L3Cube code-mixed NLP | GitHub | https://github.com/l3cube-pune/code-mixed-nlp | HingCorpus/HingBERT (Hinglish) |
| Tamil-Llama | GitHub/Model | https://github.com/abhinand5/tamil-llama , https://huggingface.co/abhinand/tamil-llama-7b-instruct-v0.2 | Self-hostable Tamil LLM fallback |
| Sarvam-M | Model | https://huggingface.co/sarvamai/sarvam-m | Code-mix-native fallback (API + open weights) |

---

# Summary — All 9 Constraints Solved

| # | Constraint | Solution in one line | Effort |
|---|---|---|---|
| 1 | No MCA21/DPIIT APIs; Aadhaar restricted | `VerificationGateway` + KYC aggregator drivers + DigiLocker/offline-eKYC; zero direct Aadhaar OCR | 4–6 wks |
| 2 | Scheme data staleness | Git-scraping + changedetection.io → LLM extraction with self-refine → GitHub-PR review → versioned publish + SLA | 4–6 wks + 4–7 h/wk |
| 3 | Swarm cost/latency | Prompt-cache hygiene + Haiku router/sub-agents with cascade + `Send` parallelism + streaming + semantic cache + Batch API → ₹27 → ₹3.4/turn (~87% cut) | build order of 8 steps |
| 4 | 100k-node graph matching | Blocking (SQL/PostGIS) → pgvector ANN → scipy LAPJVsp / min-cost-flow / CP-SAT on shortlists → ~30 ms point queries | inside Phase 3 |
| 5 | IndicBERT embeddings | Swap to BGE-M3 1024-dim behind same interface; parallel-column pgvector migration; IndicBERT keeps intent only | 1–2 wks |
| 6 | Tamil BLEU target | chrF++ ≥ 50 + COMET ≥ 0.75 + glossary stem-match hit-rate ≥ 90%; BLEU stays for Hindi | eval harness, days |
| 7 | Code-mixing | `NormalizationService`: IndicLID → IndicXlit → protect-list; Sarvam-M/Tamil-Llama fallback ≤ 15% of turns | 1–2 wks |
| 8 | LightGCN cold start | Score-provider ladder: heuristic → VW bandit (1k) → LightFM (5–10k) → LightGCN gated on ≥50k + 10-core + shadow win | staged, data-gated |
| 9 | DPDP + caste data | Separate caste-consent purpose, AES-GCM field encryption, hash-chained audit, retention scheduler; DigiLocker pulls double as consent events | 4–6 wks |
