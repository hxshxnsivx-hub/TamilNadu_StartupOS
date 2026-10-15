# V2 Integration Plan — Lost Gems & Adopted Group-C Modules

**Date:** 2026-07-17
**Scope:** Full integration of Group B (P-24…P-43) plus three Group-C adoptions (P-44 vernacular news board, P-46 investor web-intelligence, P-47 risk scenario simulator) from `ideology-comparison.md` into the project phases and architecture.
**Structure per item:** tree-of-distribution checklist → working mechanism → phase alignment → spec placement.
**New phase created:** Phase 6 — Living Intelligence Layer (for the items no existing phase can host).

---

# PART 1 · TREE-OF-DISTRIBUTION BREAKDOWN (all 23 items)

## ── Aligned to PHASE 1 (Foundation & Ideation) ──

### P-34 · Three Entry Modes + Category-2 Sub-Typing
**Tree:**
- [ ] P-34.1 Entry-mode selector: `idea | domain-only | intent-only(experience)` at C1 onboarding
- [ ] P-34.2 Route `idea` → IdeaExtractor (existing); `domain-only` → Opportunity Bank filtered by domain; `intent-only` → ExperienceProfiler (v1.1) full flow
- [ ] P-34.3 Category-2 sub-typing on registration check: `2A registered+product | 2B registered+no-product | 2C idea-worker+no-company`
- [ ] P-34.4 2B flow: legal entity verified first (schemes unlock day-1) → then routed into C1 idea/opportunity discovery
- [ ] P-34.5 2C flow: idea refinement → fast-tracked registration checklist
- [ ] P-34.6 Orchestrator intent labels extended: `entry_mode`, `registration_subtype` in ConversationState

**Mechanism:** one branching question pair ("Do you have an idea?" / "Do you have a registered startup? Does it have a product?") sets two enum fields on the profile; LangGraph conditional edges route on them; every downstream swarm reads the same two fields — no duplicated flows, only entry-point lattice.
**Phase:** 1 (extends Tasks 1.8, 1.10) · **Spec:** Req 1.6 amendment + new Req 1.7.

### P-29 · Terrain/Persona Roadmap Modes
**Tree:**
- [ ] P-29.1 Terrain enum: `urban_tech | rural_micro | academic_spinoff | deep_tech`
- [ ] P-29.2 Terrain classifier: rule-first (district type + domain + education signals), founder-overridable
- [ ] P-29.3 Four roadmap template families (milestone sets, timeline multipliers, scheme-emphasis differ per terrain)
- [ ] P-29.4 MilestoneGenerator takes `terrain` as generation parameter
- [ ] P-29.5 Terrain-specific scheme emphasis (rural_micro → UYEGP/PMEGP weighting; deep_tech → NIDHI/TN Deep Tech)

**Mechanism:** terrain is a profile attribute set at onboarding (auto-suggested, user-confirmed). The RoadmapSupervisor selects the matching template family; the SchemeAnnotator receives terrain as a ranking bias input. Templates are versioned data (YAML), not code.
**Phase:** 1–2 (extends Task 1.7) · **Spec:** Req 1.3 amendment.

### P-41 · Semantic Peer Discovery + Live-Demo Homepage + Gamified Tiers
**Tree:**
- [ ] P-41.1 "Find startups like mine": pgvector similarity over startup-domain embeddings, top-k peers with similarity chips
- [ ] P-41.2 Consent gate: startups opt in to discoverability (DPDP purpose)
- [ ] P-41.3 Homepage live-demo widget: anonymous mini-profile (4 fields) → real-time top-3 scheme match preview → signup CTA
- [ ] P-41.4 Ecosystem stat tiles on homepage (startups on platform, schemes tracked, ₹ facilitated)
- [ ] P-41.5 Gamified completeness: progress ring, tier badges (Basic→Investment-Ready), "next unlock" hint per tier

**Mechanism:** peer discovery is one ANN query over embeddings that already exist (Task 1.6) filtered by consent flag. The homepage widget calls the rules-layer eligibility check on an ephemeral profile (no storage, no LLM) — cheap, deterministic, instant proof-of-value. Gamification is pure UI over the existing 40/60/80/100 score.
**Phase:** 1–2 (extends Tasks 1.6, 1.9 + frontend) · **Spec:** new Req 1.8.

## ── Aligned to PHASE 2 (Registered Startup & Schemes) ──

### P-24 · Approval-Likelihood Ranking
**Tree:**
- [ ] P-24.1 Likelihood model v0: heuristic score from (scheme priority-category match × profile strength on that scheme's preference axes × historical success rate × competition proxy)
- [ ] P-24.2 Add `likelihood_score` alongside `relevance_score` on scheme cards ("Strong fit — schemes like this favor first-graduate rural founders")
- [ ] P-24.3 Ranking toggle: sort by relevance | likelihood
- [ ] P-24.4 Data hooks: log application outcomes → recalibrate weights (feeds Phase-5 learning)

**Mechanism:** after CP-SAT returns the *eligible* set (binary, unchanged), a second scorer estimates approval probability using scheme preference signals (many schemes formally prefer categories: women-led, SC/ST, first-graduate, rural) matched against the founder's profile plus curated success-rate data. Explainer states the likelihood rationale. No LLM in the score.
**Phase:** 2 (extends Task 2.4 Ranker) · **Spec:** Req 2.5 amendment.

### P-30 · Roadmap Re-Versioning on Policy Change
**Tree:**
- [ ] P-30.1 Roadmap↔scheme dependency index (which issued roadmaps reference which scheme IDs)
- [ ] P-30.2 Hook on `scheme_changelog` events (curation pipeline already writes it)
- [ ] P-30.3 Impact analyzer: does the change affect eligibility/amount/deadline referenced by the roadmap?
- [ ] P-30.4 Re-version: create roadmap vN+1 with changed annotations diffed and highlighted
- [ ] P-30.5 Founder notification in preferred language ("TANSEED window changed — your roadmap was updated")

**Mechanism:** event-driven: scheme-curation merge → changelog row → async job queries the dependency index → affected roadmaps re-annotated (Scheme Swarm re-run scoped to changed schemes only) → new version stored, old kept, diff rendered → notification. Cost is near-zero because re-annotation is scoped.
**Phase:** 2 (extends Tasks 2.2, 2.5) · **Spec:** new Req 2.9.

### P-31 · Milestone Tracker + Proof Attachments + QR Living PDF
**Tree:**
- [ ] P-31.1 `milestone_progress` table: status, dates, proof attachments (S3 refs), notes
- [ ] P-31.2 Proof upload per milestone (deck, photos, pilot contracts, LOIs) via existing Document_Verifier path
- [ ] P-31.3 Progress analytics: % complete, on-track vs timeline estimates
- [ ] P-31.4 Signed share link + QR embedded in every exported roadmap PDF → live read-only progress page
- [ ] P-31.5 Proofs feed C4: milestone evidence auto-registers as readiness evidence (see P-32)

**Mechanism:** the roadmap stops being a static artifact: milestones are stateful rows; the PDF's QR encodes a tokenized read-only URL rendered from live data. Proof files reuse the encrypted S3 + OCR infrastructure.
**Phase:** 2 (extends Task 1.7 output + Task 2.6) · **Spec:** new Req 1.9.

### P-33 · Problem-Statements Live Board
**Tree:**
- [ ] P-33.1 Board UI over Opportunity Bank entries typed `challenge` (StartupTN sector challenges, Startup India Grand Challenge, AMRUT, AIM, corporate CSR challenges)
- [ ] P-33.2 Each card: problem + deadline + **linked funding** (schemes eligible to finance solving it) — "problem + money in one card"
- [ ] P-33.3 Freshness: same curation pipeline (monitors + LLM extraction + curator PR) — challenges are just another source type
- [ ] P-33.4 "Adopt this problem" → seeds the C1 opportunity→roadmap flow
- [ ] P-33.5 Filter by sector taxonomy, district, capital band

**Mechanism:** zero new backend concepts — the Opportunity Bank (v1.1) gains a `type=challenge` discriminator and a `linked_scheme_ids` join surfaced as a public board; adoption routes into the existing pipeline.
**Phase:** 2 (extends Tasks 1.10, 2.2) · **Spec:** Req 1.6 amendment.

### P-40 · Scheme Alerts · Doc-Readiness Checker · Deadline Tracker (+ Competitor Intel → Phase 6)
**Tree:**
- [ ] P-40.1 New-scheme alerts: curation-pipeline merge events matched against stored founder profiles → "a new scheme you're likely eligible for"
- [ ] P-40.2 Document-readiness checker: per target scheme, diff required-docs vs verified-docs → checklist with upload CTAs
- [ ] P-40.3 Deadline tracker: unified calendar of scheme windows + application milestones (extends existing 7d/1d reminders to a visual tracker)
- [ ] P-40.4 Competitor intelligence ("what similar startups got funded for") → **Phase 6** (needs external data feed)

**Mechanism:** P-40.1 runs the rules-layer eligibility check for the *new scheme only* against profile snapshots (cheap batch). P-40.2 is a set-difference over data the platform already holds. P-40.3 is a view. All three ride on existing infrastructure.
**Phase:** 2–4 · **Spec:** Req 2.6 amendment.

### P-39 · Rural Accessibility Ladder (offline/2G)
**Tree:**
- [ ] P-39.1 PWA with offline shell + cached roadmap/scheme cards (read your roadmap with no signal)
- [ ] P-39.2 Low-bandwidth mode: no images, SMS-size payloads, deferred sync queue for form inputs
- [ ] P-39.3 Voice-first paths function on 2G (compressed audio upload, async transcription)
- [ ] P-39.4 Feature-phone consideration: IVR/SMS notification fallback for deadline alerts
- [ ] P-39.5 Performance budget: p95 first-load < 3s on 2G for core screens

**Mechanism:** service-worker-cached PWA with a sync queue; server renders low-bandwidth variants keyed by a client hint; notifications degrade SMS-ward. This is a UX/infrastructure principle enforced from Phase 2 onward, not a bolt-on.
**Phase:** 2 (with the low-literacy UX work, Task 2.7) · **Spec:** Req 1.5/2.7 amendment.

### P-37 · Human-in-the-Loop Governance
**Tree:**
- [ ] P-37.1 Manual-verification queue for critical documents (community/DPIIT certificates) — already partially specced; formalize SLAs
- [ ] P-37.2 Optional human QA sampling on funding recommendations (early releases: N% reviewed before display)
- [ ] P-37.3 Admin console: update scheme rules, approve/flag B2B partners, deactivate opportunities
- [ ] P-37.4 Solver-decision override: admin can override a constraint outcome with mandatory reason → hash-chained audit entry
- [ ] P-37.5 Escalation path from any swarm ("route to human") when confidence gates fail repeatedly

**Mechanism:** a review-queue service (rows: artifact, reason, assignee, decision, audit link) shared by documents, recommendations, and overrides; the CP-SAT boundary stays authoritative — overrides are logged exceptions, never silent edits.
**Phase:** 2 onward (extends admin surfaces in Tasks 2.2.7, 5.4) · **Spec:** new Req 5.6.

### P-42 · Idea-Stage IP Consent
**Tree:**
- [ ] P-42.1 New DPDP consent purpose: `unregistered_idea_sharing` (own notice, own withdrawal)
- [ ] P-42.2 Encrypted storage class for idea descriptions pre-registration
- [ ] P-42.3 Mandatory disclaimer + consent screen before undocumented/ideation B2B flows
- [ ] P-42.4 Visibility controls: idea details masked in peer discovery/matching until mutual accept

**Mechanism:** extends the existing consent-artifact architecture (constraint-solution §A) with one more purpose + a masking rule in match-card rendering.
**Phase:** 2 (with DPDP consent schema) · **Spec:** Req 6.1 amendment.

## ── Aligned to PHASE 3 (B2B Engine) ──

### P-25 · Joint Cluster-Scheme Co-Application Alerts
**Tree:**
- [ ] P-25.1 Tag cluster/consortium schemes in the scheme DB (`supports_joint_application: true` — SFURTI, CDP, AIM consortium grants)
- [ ] P-25.2 Post-match hook: for each accepted/high-score B2B match, check shared district/sector → run joint eligibility (both profiles) against cluster schemes
- [ ] P-25.3 Dual notification with a shared "co-application card" (scheme, why both qualify, steps)
- [ ] P-25.4 Track co-applications in the applications table (`joint_with` field)

**Mechanism:** a scoped CP-SAT run with a two-profile conjunction over the cluster-scheme subset, triggered by match events. Output routes through the existing Explainer for the "why you both qualify" text.
**Phase:** 3 (joins Scheme Swarm × B2B Swarm) · **Spec:** new Req 3.8.

### P-26 · Proactive Suggestion Engine (dual-signal + digests)
**Tree:**
- [ ] P-26.1 Inferred-needs extractor: profile/BOM/roadmap-phase signals → unstated needs (hardware startup, no firmware partner → suggest T3 match)
- [ ] P-26.2 Event triggers: roadmap phase change, profile update, new supply-node onboarding → candidate suggestions
- [ ] P-26.3 Weekly digest job: top-3 opportunities (matches, schemes, challenges) per founder, ranked, deduped, capped
- [ ] P-26.4 Suggestion feedback loop: accept/dismiss signals logged (feeds Phase-5 learning + digest tuning)
- [ ] P-26.5 Channel routing: in-app, email, SMS-fallback (per P-39), respecting notification preferences

**Mechanism:** a `SignalEngine` service consuming platform events; suggestion candidates are generated by the same matching/eligibility engines run in cheap scoped batches (Batch API, §10.3 economics), stored in a suggestions table, delivered by digest scheduler. Push, not poll — but every push is constraint-checked before send.
**Phase:** 3–4 (new cross-cutting service, first consumers B2B + schemes) · **Spec:** new Req 5.7.

### P-36 · Domain-Adaptive Match Weights
**Tree:**
- [ ] P-36.1 Weight config table: per sector-taxonomy entry, the 4-component edge weights (default 40/30/20/10)
- [ ] P-36.2 Curated presets: AgriTech (geo-heavy), HealthTech/Defence (compliance/trust-heavy), EdTech (tech-tier-heavy)
- [ ] P-36.3 Admin-editable, versioned (same governance as scheme rules)
- [ ] P-36.4 Graph Engine reads weights by demand-node sector at scoring time
- [ ] P-36.5 Phase-5 hook: learned weight suggestions surface to admin for approval (never auto-applied)

**Mechanism:** the composite scorer's weight vector becomes a lookup by sector instead of a constant; one small table + cache. Learning proposes, humans approve (P-37 governance).
**Phase:** 3 (extends Task 3.2.3) · **Spec:** Req 3.2 amendment.

### P-43 · Barter/Skill-Swap Flag (T2)
**Tree:**
- [ ] P-43.1 `payment_mode` on T2 profiles: `cash | barter | either`
- [ ] P-43.2 Hard constraint: barter-only matches barter-or-either
- [ ] P-43.3 Barter match card shows offered↔needed service pairing
- [ ] P-43.4 Collaboration lifecycle supports non-monetary value recording (for trust scoring)

**Mechanism:** one enum + one CP-SAT compatibility constraint + card rendering; trust scoring already handles per-dimension feedback so barter deals rate normally.
**Phase:** 3 (extends Tasks 3.1, 3.3) · **Spec:** Req 3.1 amendment.

## ── Aligned to PHASE 4 (Funding Navigator) ──

### P-27 · Anti-Conflict Funding Constraints
**Tree:**
- [ ] P-27.1 Scheme-combination conflict matrix in scheme DB (`conflicts_with: [scheme_ids]`, `same_fy_exclusive: bool`) — curated from scheme guidelines
- [ ] P-27.2 CP-SAT: mutual-exclusion constraints across the *portfolio* of recommended routes (not per-scheme)
- [ ] P-27.3 Over-raise sanity: `total_ask ≤ stage_runway_ceiling(stage, burn)` soft constraint with explanation
- [ ] P-27.4 Explainer covers conflicts ("SISFS and TANSEED cannot be combined in the same FY — sequenced instead")

**Mechanism:** the investor/funding model gains portfolio-level constraints: `eligible[a] + eligible[b] ≤ 1` for conflicting pairs, and a stage-parameterized raise ceiling. Turns route *lists* into valid route *portfolios* — the enabling machinery for P-35.
**Phase:** 4 (extends Task 4.4) · **Spec:** Req 4.4 amendment.

### P-35 · Funding Pathway Sequencing
**Tree:**
- [ ] P-35.1 Route metadata: typical decision latency, disbursement time, stage prerequisites, dilution type
- [ ] P-35.2 Sequencer: order the feasible portfolio into a timeline (grant → prototype milestone → pre-seed) respecting conflicts (P-27) and prerequisites
- [ ] P-35.3 Bank-pathway explainers: step-by-step "before you visit the bank" checklists per loan scheme
- [ ] P-35.4 Sequenced plan rendered as a funding-timeline view + merged into the roadmap (C1×C4)

**Mechanism:** post-CP-SAT ordering pass: a small scheduling model (or deterministic topological ordering over prerequisites + latencies) converts the feasible set into a dated strategy; output joins the milestone tracker so funding steps live inside the same living roadmap.
**Phase:** 4 (extends Tasks 4.4, 4.5) · **Spec:** new Req 4.8.

### P-28 · Traction Substitute Framework
**Tree:**
- [ ] P-28.1 Proxy-evidence taxonomy: LOIs, pilots, hackathon wins, publications, waitlists, platform B2B orders
- [ ] P-28.2 Evidence intake via Document_Verifier (upload + parse + verify where possible)
- [ ] P-28.3 Scheme/investor flags: `accepts_pre_revenue: bool`, `accepted_proxy_types: []`
- [ ] P-28.4 Traction dimension scorer accepts proxy signals with type-specific weights
- [ ] P-28.5 Matching restricted correctly: pre-revenue founders → only routes flagged pre-revenue-friendly (TANSEED, AIM PRAYAS, TIIC Proto)

**Mechanism:** the readiness Traction assessor gains a proxy-signal input channel; CP-SAT gains a `pre_revenue_ok` compatibility constraint; the gap analyzer recommends *which proxy evidence to create next* — rejection-as-roadmap applied to traction.
**Phase:** 4 (extends Tasks 4.2, 4.4) · **Spec:** Req 4.1 amendment.

### P-32 · B2B Traction → Readiness Feed
**Tree:**
- [ ] P-32.1 Metric pipe: completed collaborations, recurring orders, transaction value, on-time rate → traction evidence records
- [ ] P-32.2 Consent: founder approves platform-metrics sharing into readiness/investor materials
- [ ] P-32.3 Traction assessor ingests platform-verified B2B metrics (higher trust weight than self-declared)
- [ ] P-32.4 Investor-facing "platform-verified traction" badge on readiness reports

**Mechanism:** a nightly job materializes collaboration metrics into the evidence store with `source=platform_verified`; the readiness scorer weights verified evidence above claims. The pillars become one organism with one join.
**Phase:** 4 (consumes Phase-3 data; extends Task 4.2) · **Spec:** Req 4.1 amendment.

### P-46 · Investor Web-Intelligence (adapted — cited, not scraped-blind)
**Tree:**
- [ ] P-46.1 Source policy: ToS-compliant public sources only (SEBI AIF registry, Startup India Investor Connect, fund websites, press announcements, StartupTN/TANFUND partner lists) — no LinkedIn/AngelList scraping
- [ ] P-46.2 Research agents: scheduled crawl of policy-approved sources → structured investor-fact drafts (thesis, cheque size, stage, recent deals)
- [ ] P-46.3 **Provenance mandate: every web-derived field stores `source_url` + `retrieved_at` and renders "driven from web — [source, date]" on the card, exactly as quoted**
- [ ] P-46.4 Curator review queue (same PR-style governance as schemes) before facts go live
- [ ] P-46.5 Zero-extra-founder-input preserved: matching uses the existing profile only
- [ ] P-46.6 Staleness SLA: web-derived investor facts re-verified every 90 days or flagged stale

**Mechanism:** the scheme-curation pipeline pattern (monitors → LLM extraction → human review → versioned publish) cloned for investor data, with a hard source-policy allowlist and per-field provenance rendered in the UI. Platform data and web-derived data are visually distinguished — founders always see where a fact came from.
**Phase:** 4 seed + Phase 6 continuous · **Spec:** Req 4.3 amendment + new Req 6.4 (phase-6 crawler).

## ── Aligned to PHASE 5 (Optimization & Hardening) ──

### P-38 · Synthetic-Founder Simulation Testing
**Tree:**
- [ ] P-38.1 Founder-profile generator: parameterized synthetic profiles across caste/gender/district/education/stage/sector distributions
- [ ] P-38.2 Golden-path suites: expected scheme sets per canonical profile (verified manually once)
- [ ] P-38.3 Regression harness: every scheme-rule change replays the synthetic population → diff of eligibility outcomes → surfaced in the curation PR
- [ ] P-38.4 Fairness lens: outcome distributions across demographic slices monitored for unintended skew
- [ ] P-38.5 Extend to matching/funding: synthetic B2B populations and funding portfolios stress the solvers

**Mechanism:** a pytest-harness generating N synthetic founders (Hypothesis strategies already specced) run against the rules layer and solvers in CI; eligibility diffs attach to curation PRs so the curator sees *who is affected* by a rule change before merging.
**Phase:** 5 (extends Task 5.3; harness starts Phase 2 CI) · **Spec:** Req 5.3 amendment (testing strategy).

## ── NEW PHASE 6 · LIVING INTELLIGENCE LAYER (Weeks 33–40, post-MVP) ──

**Why a new phase:** P-44, P-47, P-40d, and continuous P-46 all require *external-content operations* (news, market data, continuous crawling) or *mature constraint models* (simulation) that don't exist until Phases 1–5 are live. Grouping them keeps MVP scope honest while giving the deferred gems a real home with real tasks.

### P-44 · Vernacular Startup-News Intelligence Board
**Tree:**
- [ ] P-44.1 Source registry: Tamil business media (Dinamalar business, Vikatan Business, Hindu Tamil business) + English startup media (YourStory, Inc42, Entrackr) + official feeds (PIB, StartupTN, DPIIT announcements)
- [ ] P-44.2 Crawler agents on the git-scraping/changedetection pattern; RSS-first where available
- [ ] P-44.3 Summarizer: LLM condenses each item; IndicTrans2 renders Tamil/Hindi/English variants; glossary preserved
- [ ] P-44.4 **Provenance: every card links the original article — "driven from web — [outlet, date]"**
- [ ] P-44.5 Relevance routing: news tagged by sector taxonomy + scheme references → founders see *their* news; scheme-change news cross-links to P-30 roadmap re-versioning
- [ ] P-44.6 Editorial guardrail: automated summaries labeled as summaries; corrections workflow; no synthetic news
- [ ] P-44.7 Agent-status strip (the chat's "news channel" vision): board shows which source agents ran and when

**Mechanism:** a fourth editorial pipeline (after schemes, opportunities, investors) — crawl → summarize → translate → tag → publish, fully cited. Positioned as India's first vernacular startup-news aggregation; cost-controlled by RSS-first sourcing and batch summarization.
**Phase:** 6 · **Spec:** new Req 6.5.

### P-47 · Risk Scenario Simulator (What-If Engine)
**Tree:**
- [ ] P-47.1 Scenario taxonomy: scheme rejected · funding delayed N months · round fails · key supplier lost · deadline missed
- [ ] P-47.2 Simulation core: re-run the founder's constraint models (funding portfolio, roadmap timeline, B2B allocation) with the scenario's perturbation applied
- [ ] P-47.3 Fallback generator: for each broken path, compute surviving feasible routes (alternate schemes, bootstrapping via B2B cash-flow, revised timeline)
- [ ] P-47.4 Comparison view: baseline vs scenario, with the gap roadmap (P-30/P-35 machinery) rendering "what you'd do next"
- [ ] P-47.5 Guardrails: simulations clearly labeled hypothetical; no live-data mutation; results in founder's language

**Mechanism:** because eligibility, funding, and allocation are already deterministic constraint models, a what-if is literally the same solve with modified inputs — the simulator is a *thin orchestration* over existing engines plus a diff renderer. This is why it waits for Phase 6: it needs those models stable.
**Phase:** 6 · **Spec:** new Req 6.6.

### P-40d · Competitor Intelligence ("what similar startups got funded for")
**Tree:**
- [ ] P-40d.1 Data basis: platform outcomes (consented, anonymized) + cited public funding announcements (from P-44's crawl)
- [ ] P-40d.2 Similarity join: founder's domain embedding → similar funded startups → schemes/investors/amounts, with sources
- [ ] P-40d.3 Card: "3 startups like yours received TANSEED + angel round in the last year — [sources]"
- [ ] P-40d.4 Privacy: platform-sourced entries aggregated/anonymized below k-threshold

**Mechanism:** reuses P-44's cited news corpus + peer-discovery embeddings; a retention/motivation surface, not a decision engine — never enters the constraint path.
**Phase:** 6 · **Spec:** new Req 6.7.

### P-46 (continuous) · Investor Web-Intelligence crawler — see Phase-4 entry; the scheduled re-crawl + staleness SLA operates here.

---

# PART 2 · PER-PHASE ARCHITECTURE MODIFICATIONS

### Phase 1 (revised) — Foundation & Ideation
```
Entry Lattice (NEW P-34): [idea | domain-only | intent-only] × [2A | 2B | 2C]
        │
Profile Swarm ──── Terrain Classifier (NEW P-29) ── terrain ∈ {urban_tech, rural_micro, academic, deep_tech}
        │
Roadmap Swarm: ExperienceProfiler → OpportunityGenerator → IdeaExtractor → Feasibility
        → MilestoneGenerator(terrain templates NEW) → dependency/critical-path
        │
Embedding Svc ──── Peer Discovery endpoint (NEW P-41.1, consent-gated)
API v1 ─────────── + homepage live-demo eligibility endpoint (NEW P-41.3, ephemeral, rules-only)
UI ──────────────── gamified tier progress (NEW P-41.5)
```

### Phase 2 (revised) — Registered Startup & Schemes
```
Scheme DB + curation pipeline
   ├── + challenge-type Opportunity entries → Problem-Statements Live Board (NEW P-33)
   ├── + cluster-scheme tags (P-25 prep) · + conflict matrix (P-27 prep) · + pre-revenue flags (P-28 prep)
   └── changelog events ──► Roadmap Re-Versioner (NEW P-30) ──► founder notification
Scheme Swarm: Retriever → EligibilityChecker → Ranker(+ Likelihood Scorer NEW P-24) → Explainer
Alerts & Trackers (NEW P-40a–c): new-scheme alerts · doc-readiness checker · deadline tracker
Milestone Tracker + proofs + QR living PDF (NEW P-31)
Governance: Review-Queue service + admin override w/ audit (NEW P-37); IP-consent purpose (NEW P-42)
UX: low-literacy + offline/2G PWA ladder (NEW P-39)
```

### Phase 3 (revised) — B2B Engine
```
Graph Engine: blocking → ANN → scoring [weights ← per-sector config (NEW P-36)]
B2B profiles: + payment_mode barter flag (NEW P-43)
CP-SAT allocation: + barter-compatibility constraint
Match events ──► Joint Cluster-Scheme Checker (NEW P-25) ──► dual co-application cards
SignalEngine (NEW P-26): inferred-needs extractor · event triggers · weekly digest scheduler
                          (constraint-checked pushes; accept/dismiss telemetry)
```

### Phase 4 (revised) — Funding Navigator
```
Readiness engine: Traction assessor + proxy signals (NEW P-28) + platform-verified B2B metrics (NEW P-32)
CP-SAT funding model: + portfolio mutual-exclusion & over-raise constraints (NEW P-27)
        ↓ feasible portfolio
Pathway Sequencer (NEW P-35): dated strategy grant→prototype→VC + bank pathways
Investor DB: + web-intelligence ingestion, cited & curator-reviewed (NEW P-46) — "driven from web [source, date]"
Funding plan merges into living roadmap (P-31/P-35 join)
```

### Phase 5 (revised) — Optimization & Hardening
```
+ Synthetic-Founder Simulation Harness (NEW P-38): synthetic populations in CI,
  eligibility-diff on every rule PR, fairness-slice monitoring
+ suggestion/likelihood telemetry feeds learning ladder (P-24.4, P-26.4)
(existing: learning loop, analytics, security, performance, deployment, docs)
```

### Phase 6 (NEW) — Living Intelligence Layer (Weeks 33–40)
```
News Intelligence (P-44): source registry → crawler agents → summarize → translate → tag → cited board
Investor crawler continuous ops (P-46): re-crawl + 90-day staleness SLA
What-If Simulator (P-47): scenario taxonomy → perturbed constraint re-solves → fallback plans → diff view
Competitor Intelligence (P-40d): cited funding corpus × peer embeddings → anonymized insight cards
All four ride the shared provenance rule: every external fact renders its source and retrieval date.
```

---

# PART 3 · REVISED UNIFIED ARCHITECTURE (v2)

```
┌────────────────────────────────────────────────────────────────────────┐
│ PRESENTATION   Web (PWA offline/2G · low-literacy · gamified tiers)    │
│                Mobile · Voice · Live-demo homepage · News Board(P6)    │
│                Problem-Statements Board · Living-roadmap QR pages      │
├────────────────────────────────────────────────────────────────────────┤
│ GATEWAY & AUTH  FastAPI · JWT/RBAC · rate limits · consent middleware  │
│                 (+ idea-IP purpose)                                    │
├────────────────────────────────────────────────────────────────────────┤
│ ORCHESTRATOR   LangGraph · intent cascade · entry-mode lattice ·       │
│                context stack · guardrails                              │
├────────────────────────────────────────────────────────────────────────┤
│ SWARMS   Profile · Roadmap(+terrain, +opportunity) · Scheme(+likelihood)│
│          B2B(+decomposer/supply-map) · Funding(+sequencer)             │
├────────────────────────────────────────────────────────────────────────┤
│ LIVING-INTELLIGENCE SERVICES (v2)                                      │
│   SignalEngine (dual-signal suggestions · digests · alerts)            │
│   Roadmap Re-Versioner (policy-change propagation)                     │
│   Joint-Scheme Checker (B2B×Scheme fusion)                             │
│   What-If Simulator (P6) · News/Investor/Competitor Intelligence (P6,  │
│   cited web-derived data) · Review-Queue & Admin-Override (governance) │
├────────────────────────────────────────────────────────────────────────┤
│ CORE SERVICES  CPSAT_Boundary(+portfolio conflicts) · Graph Engine     │
│   (+sector weights) · Embeddings(+peer discovery) · Translation ·      │
│   Document Verifier(+proof/proxy evidence) · Legal Validator ·         │
│   Milestone Tracker · Simulation Harness (CI)                          │
├────────────────────────────────────────────────────────────────────────┤
│ DATA   PostgreSQL+pgvector(+PostGIS) · Redis · S3 · editorial repos    │
│        (schemes · opportunities/challenges · investors · news) — all   │
│        versioned, cited, curator-reviewed                              │
└────────────────────────────────────────────────────────────────────────┘
```

**Timeline impact:** Phases 1–5 absorb the in-phase additions with ~+1 week each (most items ride existing infrastructure); Phase 6 adds 6–8 weeks post-MVP. Revised total: 22–32 weeks to MVP (unchanged) + Phase 6 to week ~40.
