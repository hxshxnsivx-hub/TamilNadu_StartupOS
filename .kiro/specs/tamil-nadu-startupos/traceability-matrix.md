# Traceability Matrix — Vanigam (Spec v2, construction-ready baseline)

**Date:** 2026-07-17
**Purpose:** one row per capability, proving every requirement is distributed across all four spec artifacts (Requirements → Design → Tasks → Phase) before construction begins.
**Legend:** ✅ present · Req = requirements.md · Dsn = design.md · Tsk = tasks.md · Base = original spec · v1.1 / v2 = addenda.

## 1 · Base capabilities (original spec)

| Capability | Req | Dsn | Tsk | Phase |
|---|---|---|---|---|
| Founder profile + completeness scoring | 1.1 | FounderProfile schema | 1.2, 1.3 | 1 |
| Idea validation & structuring | 1.2 | Roadmap Swarm | 1.7 | 1 |
| Roadmap generation + dependencies | 1.3 | MilestoneGenerator | 1.7 | 1 |
| Scheme annotation on milestones | 1.4 | SchemeAnnotator | 2.5 | 2 |
| Voice interaction (ta/hi/en) | 1.5 | Translation/ASR design | 2.7 | 2 |
| Legal entity validation (MCA21/DPIIT/GST) | 2.1 | Legal_Validator | 2.1 | 2 |
| Document upload + OCR + verification | 2.2 | Document_Verifier | 1.4 | 1 |
| Scheme database + admin | 2.3 | schemes schema | 2.2 | 2 |
| CP-SAT eligibility engine | 2.4 | CPSAT_Boundary | 2.3 | 2 |
| Scheme ranking (5-factor) | 2.5 | Ranker | 2.4 | 2 |
| Application tracking + reminders | 2.6 | applications schema | 2.6 | 2 |
| B2B profiles (4 tiers + BOM) | 3.1 | b2b_profiles schema | 3.1 | 3 |
| Bipartite graph construction | 3.2 | Graph_Engine | 3.2 | 3 |
| CP-SAT B2B matching + allocation | 3.3 | B2B constraint model | 3.3 | 3 |
| Trust scores + decay | 3.4 | TrustCalculator | 3.4 | 3 |
| Collaboration lifecycle | 3.5 | status machine | 3.5 | 3 |
| Funding readiness (6 dimensions) | 4.1 | assessors | 4.2 | 4 |
| Gap analysis + recommendations | 4.2 | GapAnalyzer | 4.3 | 4 |
| Investor database | 4.3 | investors schema | 4.1 | 4 |
| CP-SAT investor matching | 4.4 | investor model | 4.4 | 4 |
| Funding pipeline (Kanban) | 4.5 | pipeline schema | 4.6 | 4 |
| Orchestrator (LangGraph) | 5.1 | state machine | 1.8 | 1 |
| Swarm coordination | 5.2 | supervisors | per-swarm | 1–4 |
| CP-SAT boundary engine | 5.3 | CPSATBoundary API | 2.3 | 2 |
| Graph engine (scaling per solutions §D) | 5.4 | funnel internals | 3.2 | 3 |
| Embedding + translation services | 5.5 | services | 1.5, 1.6 | 1 |
| Data model + encryption + audit | 6.1, 6.2 | schemas | 1.2, 5.4 | 1, 5 |

## 2 · v1.1 capabilities

| Capability | Req | Dsn | Tsk | Phase |
|---|---|---|---|---|
| Experience-based Opportunity Discovery | 1.6 | A1 (opportunity_bank, agents) | 1.10 | 1–2 |
| Canonical Sector Taxonomy | 2.7 | A3 | 2.8 | 2 |
| Product Decomposition + Supply Feasibility Map | 3.6 | A2 (product_decompositions) | 3.7 | 3 |

## 3 · v2 capabilities (hybrid ideology)

| P-ref | Capability | Req (v2 addendum) | Dsn (v2 addendum) | Tsk (v2 addendum) | Phase |
|---|---|---|---|---|---|
| P-34 | Entry lattice + Cat-2 sub-typing | 1.7 | B1 | 1.11 | 1 |
| P-29 | Terrain roadmap modes | 1.3-am | B1 | 1.12 | 1–2 |
| P-41 | Peer discovery · live-demo · gamified tiers | 1.8 | B2 | 1.13 | 1–2 |
| P-24 | Approval-likelihood ranking | 2.5-am | B3 | 2.9 | 2 |
| P-30 | Roadmap re-versioning on policy change | 2.9 | B4 | 2.10 | 2 |
| P-31 | Milestone tracker + proofs + QR living PDF | 1.9 | B5 | 2.11 | 2 |
| P-33 | Problem-statements live board | 1.6-am | B6 | 2.12 | 2 |
| P-40a–c | Scheme alerts · doc-readiness · deadline tracker | 2.6-am | B7 | 2.13 | 2–4 |
| P-39 | Offline/2G accessibility ladder | 1.5/2.7-am | B8 | 2.14 | 2 |
| P-37 | Review queue + admin override (HITL) | 5.6 | B14 | 2.15 | 2+ |
| P-42 | Idea-stage IP consent | 6.1-am | B15 | 2.16 | 2 |
| P-25 | Joint cluster-scheme co-application | 3.8 | B11 | 3.8 | 3 |
| P-26 | SignalEngine (dual-signal + digests) | 5.7 | B12 | 3.9 | 3–4 |
| P-36 | Sector-adaptive match weights | 3.2-am | B13 | 3.10 | 3 |
| P-43 | Barter/skill-swap mode (T2) | 3.1-am | B13 | 3.11 | 3 |
| P-27 | Portfolio anti-conflict constraints | 4.4-am | B10 | 4.8 | 4 |
| P-35 | Funding pathway sequencer | 4.8 | B10 | 4.9 | 4 |
| P-28 | Proxy-traction framework | 4.1-am | B9 | 4.10 | 4 |
| P-32 | B2B-verified traction feed | 4.1-am | B9 | 4.11 | 4 |
| P-46 | Investor web-intelligence (cited) | 4.3-am + 6.4 | B16 | 4.12, 6.2 | 4 + 6 |
| P-38 | Synthetic-founder simulation | 5.3-am | B17 | 5.8 | 5 (CI from 2) |
| P-44 | Vernacular news intelligence board | 6.5 | B16 | 6.1 | 6 |
| P-47 | What-if risk simulator | 6.6 | B16 | 6.3 | 6 |
| P-40d | Competitor intelligence | 6.7 | B16 | 6.4 | 6 |

## 4 · Constraint solutions (cross-cutting, from constraint-solutions.md)

| Constraint | Solution artifact | Bound to |
|---|---|---|
| Govt APIs / Aadhaar | VerificationGateway + KYC aggregator + DigiLocker | Legal_Validator, Document_Verifier (Tasks 2.1, 1.4) |
| Scheme staleness | Editorial pipeline (monitors → LLM → PR → SLA) | Task 2.2; feeds P-30, P-33, P-40 |
| Swarm cost/latency | Caching + routing + Send parallelism + tracing | Tasks 1.8, 5.3 |
| Graph scale | Blocking → ANN → C-backed solvers funnel | Task 3.2 internals |
| Embeddings | BGE-M3 swap behind interface | Task 1.6 |
| Tamil MT metrics | chrF++/COMET + glossary hit-rate gates | Task 1.5 CI |
| Code-mixing | NormalizationService + LLM fallback | Task 2.7 |
| GNN cold start | Score-provider ladder, data-gated | Task 5.1 |
| DPDP + caste | Consent purposes + encryption + audit | Tasks 1.2, 5.4, 2.16 |

## 5 · Coverage verdict

- **Requirements:** 28 base + 3 (v1.1) + 20 stubs (v2) — all present in requirements.md. ✅
- **Design:** base components + A1–A3 (v1.1) + B1–B17 (v2) — all present in design.md. ✅
- **Tasks:** 180+ base + 1.10/2.8/3.7 (v1.1) + 21 v2 tasks incl. Phase 6 block — all present in tasks.md. ✅
- **No orphans:** every v2 requirement stub has a design section and a task; every task traces to a requirement.
- **Documents map:** requirements.md · design.md · tasks.md · feasibility-survey.md · constraint-solutions.md · ideology-comparison.md · v2-integration-plan.md · VANIGAM-MASTER-DOCUMENT.md · this matrix · dashboard artifact.

**Status: SPEC BASELINE FROZEN — ready for project construction (Phase 1, Task 1.1).**
