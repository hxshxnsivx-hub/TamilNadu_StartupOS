# Arena flags: P4 Founder tools details

Back to the [weighted table](../ARENA-FLAGS.md).

### R008

**Stage words differ across modules: revenue founders score 0 and match no investor** · weight 94 · Logic flaw · impact 5/5, reach 4/5, confidence 3/3 · flags F-A4-015

- **Evidence (A4):** Funding.tsx:25 offers idea, poc, prototype, mvp, revenue, growth, scale. readiness.py:22 _STAGE_SCORE knows 'launched' and 'scaling' instead, so revenue and growth give product-stage 0 (ran: idea 10, mvp 35, revenue 0, growth 0). With the same full profile, mvp scores 84 'Highly Ready' and revenue 77, and both are told 'Ship an MVP with the core feature set'. investors.py:131-137 maps investor stages to idea..mvp, seed, series_a..scale, with no 'revenue'. Ran match_investors for stage 'revenue', 5,000 users, Rs 5L a month, readiness 80: 0 eligible, each rejected with 'Invests at mvp, prototype, seed, series_a - not revenue'. Schemes use yet another list (seed.py _META: revenue, growth). 4.1.2/D5 covers only sectors.

- **Why it matters:** The more progress a founder has made, the worse Vanigam treats them: a selling business scores below a prototype and is shown no investors at all.
- **Where to build it:** A shared stage module (e.g. app/core/stages.py) used by readiness.py, investors.py, investor_match.py, schemes/seed.py, elicitation slots and the frontend STAGE lists

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Canonical Stage enum with explicit mappings and a coverage test | The same pattern 4.1.2 plans for sectors; Python Enum and Pydantic Literal | free/open source | One meaning of stage; a test fails when any module meets an unmapped value | Touches five modules and the frontend |
| Per-module alias tables (revenue -> launched, growth -> scaling) | Small local dictionaries | free/open source | Fast fix | The vocabularies stay split and the next new word breaks again |
| Ordinal stage index (0..n) instead of names | Comparable numbers | free/open source | Allows 'at or after' rules | Loses the meaning of words like 'seed' and 'series_a' that investors publish |

- **Recommended:** Canonical Stage enum with explicit mappings and a coverage test. It fixes all three wrong answers at once and matches the plan's own approach for sectors. Add it to 4.1.2 or make it a sibling task.
- **Ruled out:** Alias tables: patches symptoms, the drift stays; ordinal index: throws away investor-published stage names

### R012

**Funding screen sends invented answers (IP, retention, unit economics) into readiness** · weight 90 · Logic flaw · impact 4/5, reach 5/5, confidence 3/3 · flags F-A4-016

- **Evidence (A4):** Funding.tsx:76-92 hard-codes 'richer defaults so a complete founder profile scores realistically': has_ip true, retention_rate 60, partnerships 2, runway_months 12, revenue_growth_pct 20, has_unit_economics, has_projections, is_compliant, has_cap_table, has_domain_expertise, has_clear_problem, has_differentiation all true, and feature/deck completeness 80. readiness.py:3-4 says missing inputs score low. These defaults supply most of the financial, pitch and legal points (e.g. legal 80 with only is_registered and dpiit set by the founder), and the overall score then gates investors (investor_match.py:279).

- **Why it matters:** The readiness band and the investor list come mostly from answers the founder never gave, which breaks 'no invented data'. 4.3.1 makes traction fairer but would be added on top of invented numbers.
- **Where to build it:** frontend/src/pages/Funding.tsx (ask or omit the fields), funding/readiness.py (per-dimension coverage, 'not assessed')

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Send only founder-given fields; readiness reports per-dimension coverage and marks thin dimensions 'not assessed' | Same idea as the three-valued scheme engine (A4-01): unknown is not zero and not yes | free/open source | Honest score; tells the founder what to answer next | Scores drop for founders who skip questions |
| Ask every field on the form | Plain inputs | free/open source | Complete data | Long form on 2G phones; low-literacy founders drop off |
| Fill fields from the ideation session's slots (1.4.3-style projection) | The conversation already collects stage, team and traction facts | free/open source | No repeated questions | Covers only some fields; still needs the 'not assessed' state |

- **Recommended:** Send only founder-given fields; readiness reports per-dimension coverage and marks thin dimensions 'not assessed'. It removes the invented inputs and works with both the form and the slot projection. Slot projection can feed it later.
- **Ruled out:** Full form: hurts the target users; slot projection alone: partial and still needs an unknown state

### R020

**/supply matches and gaps come from invented seed suppliers** · weight 84 · Logic flaw · impact 4/5, reach 4/5, confidence 3/3 · flags F-A4-010, F-B4-005

- **Evidence (A4):** routers/b2b.py:254-257 /decompose calls build_supply_map, which calls match_demand(demand) with no supply list (decompose.py:176), which defaults to SEED_SUPPLY (matching.py:75). Supply.tsx:328-345 renders those as matches: name, district, 'trust 85', price. seed.py:1-6 says these are invented and 'never offered to founders as suppliers'. 'gap' (decompose.py:177) means 'no invented supplier' and ignores the real nearby_makers in the same response. The gap guidance is a hard-coded, uncited CLUSTERS map in Supply.tsx:41-50, matched by substring, and the 'Invite a vendor for this line' button (Supply.tsx:321) has no handler.
- **Evidence (B4):** backend/app/b2b/decompose.py:96 sets gap = no match in match_demand(), which reads SEED_SUPPLY (b2b/matching.py:71-76, b2b/seed.py). routers/b2b.py:79-99 returns that gap next to the real nearby_makers from suppliers_for(). frontend/src/pages/Supply.tsx:115-122 shows 'N matched' from those seed matches (route /supply, App.tsx:119). I ran build_supply_map for 'jasmine garland', 'herbal tea', 'knitwear from tiruppur' and 'leather sandals': each became one 'packaging' line with gap=False and 2 seed matches. decompose() only emits categories the seed already has. TASKS 4.2.1 names only /b2b and B2B.tsx, not /supply or /decompose.

- **Why it matters:** Founders see invented companies with invented prices and trust scores as real matches, which breaks 'no invented data'. 4.2.1 would fix /b2b and leave /supply doing the same thing.
- **Where to build it:** backend/app/b2b/decompose.py and routers/b2b.py (drop match_demand from /decompose; gap = no directory company), Supply.tsx (show nearby_makers; remove or cite CLUSTERS; wire or remove the button)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Directory-only supply map: nearby_makers become the matches, gap = directory total 0 | suppliers_for already returns real MCA companies for each line | free/open source | Real data only; one source for /supply, /suppliers and /b2b | No price or trust columns until the founder adds quotes |
| Keep match_demand but pass the founder's quotes (from Suppliers' saved state) | Reuses the 40/30/20/10 scorer | free/open source | Price-aware when quotes exist | Quotes live in another screen's localStorage until 3.1.3 |
| Label seed matches 'example' | Minimal change | free/open source | Quick | Still shows invented data to founders; D9 shows the owner prefers 'not fetched' to labelled demos |

- **Recommended:** Directory-only supply map: nearby_makers become the matches, gap = directory total 0. It removes the invented data from founder paths now, uses data already in the response, and makes 4.2.2's cited clusters the only gap guidance.
- **Ruled out:** Quote-fed scoring: depends on 3.1.3 moving quotes server-side; 'example' label: still invented data in front of founders

### R027

**Sector/extractor keyword cues match bare substrings inside words** · weight 84 · Logic flaw · impact 4/5, reach 4/5, confidence 3/3 · flags F-B4-001, F-A5-002

- **Evidence (B4):** backend/app/elicitation/extract.py:50-70 (_SECTOR_CUES) matched by _first_cue (`any(n in low ...)`, first dict-order hit wins); extract() at :202 emits sector at confidence 0.90. Ran extract(): 'Of course I want to sell jasmine garlands' -> EDUCATION ('course'); 'A microprocessor trainer kit for colleges' -> AGRI ('crop' inside 'microprocessor'); 'A workshop that repairs looms' -> RETAIL ('shop'); 'Carbon credit tracking for solar rooftops' -> FINANCE ('credit').
- **Evidence (A5):** backend/app/elicitation/extract.py:186-190 _first_cue uses any(n in low for n in needles) (plain substring); cues at extract.py:66 and :74 include 'app'. Ran extract(): the banana_trichy idea ('...unit in Tiruchirappalli...') -> product_form=software; 'we will happily serve customers' -> sector=it_services, product_form=software; 'a soap unit for apparel stores' -> product_form=software. Eval replay shows banana_trichy ends with product_form=software.

- **Why it matters:** TASKS 4.1.2.2 only tests recall (every sector has a cue). Precision is untested: a wrong sector at 0.90 is never asked, so the founder is silently routed to the wrong schemes (planner/registry.py rules), panel weights (agents/council/vote.py:33-45), timeline multiplier (planner/roadmap.py K_DOMAIN) and cohort. Generating more cues from a bigger canonical list with the same substring matcher multiplies collisions.
- **Where to build it:** backend/app/elicitation/extract.py (matcher); the 4.1.2 canonical taxonomy module (cue source); tests/elicitation (negative cases)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Word-boundary regex cues compiled from the canonical module | ecosystem/taxonomy.py already uses compiled re patterns with word boundaries; stdlib, zero dependencies | free/open source | Fixes the 'course', 'crop', 'shop' collisions; one matcher for both vocabularies; deterministic offline | Stems ('manufactur', 'weav') need explicit prefix patterns; still keyword level |
| Token lexicon with a simple suffix stemmer, scoring all sectors | Pure Python in the style of extract.py; scores instead of first match | free/open source | Handles inflections, ranks candidates, can lower confidence on ties so the stopping rule asks | More code; needs a tie rule |
| spaCy PhraseMatcher on lemmas | Mature NLP library with offline models | free/open source | Robust tokenisation and lemmatisation | About 50 MB model and a heavy dependency for one slot; no help for Tamil cues |
| Free model classification (Gemini then Ollama, 0009) | Existing optional model chain | free tier | Understands context | Code must decide slot values (0002); not available on the offline baseline |

- **Recommended:** Word-boundary regex cues compiled from the canonical module. Reuses the pattern already in ecosystem/taxonomy.py, removes the proven collisions, and lets 4.1.2.2 add a negative-case set (quality-set ideas plus known traps must not hit a wrong sector).
- **Ruled out:** Token scorer: better but more than needed until regexes fail the quality set; spaCy: heavy dependency for one slot and English only; model classification: violates code-decides (0002) and the offline baseline.

### R028

**Supplier directory covers only 3 districts; others get A-Z order with no notice** · weight 84 · Missing logic · impact 4/5, reach 4/5, confidence 3/3 · flags F-B4-006, F-A4-012

- **Evidence (B4):** Ecosystem file _meta: 19,512 companies placed (pilot chennai, coimbatore, madurai) of 78,689 active; 247 PINs. backend/app/b2b/directory.py:109-115 sorts by rank, same district, km (9999 when the PIN is unknown), then name. Ran suppliers_for('yarn', district='tiruppur') and suppliers_for('yarn', pin='641604'): km None for all; the top results are 'A.S.S. Mills' (chennai) then Coimbatore firms, alphabetical. The response has no note that the founder's district is outside coverage.
- **Evidence (A4):** ecosystem_3d.json _meta.districts = ['chennai','coimbatore','madurai']; company_stats: 78,689 active TN companies, 19,512 kept; pins has 247 entries, all in those 3 districts. Ran suppliers_for('yarn', pin='641601', district='tiruppur'): 1,199 results, all Chennai or Coimbatore, km None, sorted alphabetically (directory.py:359-366), and the note says nothing about coverage. Not in TASKS (4.2.2 covers clusters for unmatched lines, 5.6 covers the registry).

- **Why it matters:** A Tiruppur, Salem or Erode founder (the textile heartland) is shown Chennai mills about 450 km away ahead of neighbouring Coimbatore, and is not told the list is incomplete for their district. 4.2.2's cluster fallback only fires on 'no match', but here there are always matches, just irrelevant ones.
- **Where to build it:** backend/app/b2b/directory.py (ranking and coverage note); district centroid data in ecosystem/data

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| District centroid table (38 TN districts, from OSM or the India Post data already used) as a km fallback, plus a coverage flag in the response | PIN centres already come from OSM and India Post; the haversine _km already exists | free/open source | Coimbatore ranks above Chennai for Tiruppur; honest 'outside coverage' note can trigger the 4.2.2 cluster hint | Needs a small curated centroid file |
| District adjacency list | Simple static graph | free/open source | No coordinates needed | Coarse; no ordering beyond neighbours |
| Extend company placement to all districts (geocode the 51,584 unplaced) | Data already in the MCA file | free/open source | Real coverage statewide | Large data job; free geocoders such as Nominatim are rate-limited; belongs to the registry work, not this task |
| Paid geocoding API | Google or Mapbox geocoding | paid | Fast and accurate | Violates free and offline |

- **Recommended:** District centroid table (38 TN districts, from OSM or the India Post data already used) as a km fallback, plus a coverage flag in the response. A cheap fix that makes distance meaningful everywhere and gives 4.2.2 a second trigger ('outside coverage') for the cluster hint.
- **Ruled out:** Adjacency list: too coarse to rank; statewide geocoding: right long-term but a separate, rate-limited data job; paid geocoding: not free.

### R037

**Engine ranks closed or ended schemes as eligible; it never reads open/closed status** · weight 84 · Missing logic · impact 4/5, reach 4/5, confidence 3/3 · flags F-A4-003

- **Evidence (A4):** schemes/models.py:20-36 Scheme has no status field. funding_catalogue.json: sisfs status 'closed' ('Applications closed 31 May 2026; no successor cycle notified'), standup_india status 'revamping' ('Ended March 2025'), tanseed 'between_calls'. seed.py still returns all three. In the run, Stand-Up India is ranked joint first for an SC woman with likelihood 80. TANSEED closing dates also disagree: seed.py:85 says '20 December 2025', the catalogue says '30 Jan 2026'.

- **Why it matters:** A founder is told to apply to a scheme that has closed and gets 'matches your idea stage'. 5.2.2 only fails CI when a date is old; it does not stop a known-closed scheme being recommended, and the Schemes screen never sees the catalogue's status.
- **Where to build it:** schemes/models.py (status, status_note, checked_on), seed.py or a loader joining catalogue status by id, ranking.py (filter or demote non-active), SchemeOut and Schemes.tsx (show the status)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Status joined from funding_catalogue.json by scheme id at load | The catalogue already has a curated status vocabulary (active, cohort, between_calls, closed, revamping...) and the same ids | free/open source | One status source; no duplicate data; ready for 4.1.1 | Seed ids must match catalogue ids (they do for all eight today) |
| Status field typed on each seed Scheme | Mirrors last_verified | free/open source | Simple | Third copy of a fast-changing fact; drifts like the TANSEED dates already did |
| Live check of each scheme page | httpx with selectolax | free/open source | Always current | Government-page scraping is undecided (D10); breaks offline |

- **Recommended:** Status joined from funding_catalogue.json by scheme id at load. It uses the curated, cited status that already exists and moves toward 'one scheme source'. Non-active schemes move to a separate 'not open now' group with the status note, not mixed in with open ones.
- **Ruled out:** Per-seed field: another copy that drifts; live check: blocked by D10 and not offline

### R039

**Invented readiness gate of 60 blocks every idea and prototype founder from pre-seed investors** · weight 84 · Logic flaw · impact 4/5, reach 4/5, confidence 3/3 · flags F-A4-017

- **Evidence (A4):** investor_match.py:220-221 readiness_gate returns 60 for every stage that is not late, applied as a hard rule at line 279. No investor in the data publishes such a score. Real data has 3 investors at idea/poc and 15 at prototype (investors.py _STAGES pre_seed/seed). Ran: idea founder with readiness 35 gives 0 eligible (21 rejected with 'Readiness must be >= 60 for this stage'); prototype founder with 45 gives 0; mvp with 65 gives 5.

- **Why it matters:** The pre-seed investors who exist for idea-stage founders are hidden behind a made-up threshold. 4.3.1 (proxy traction) raises scores a little but keeps the gate, so most idea-stage founders still see nobody.
- **Where to build it:** backend/app/funding/investor_match.py (_violations, _fit)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Readiness as a soft ranking factor plus advice, not a hard constraint | The code already treats geography as soft (line 248) | free/open source | Only published investor criteria stay hard; founders still see their gaps | Longer eligible lists |
| Per-investor-stage gate (none for pre-seed, higher for series A+) | Keeps a gate where diligence is heavier | free/open source | Fixes the idea-stage case | The numbers are still invented |
| Keep the gate, lower it to 40 | One constant | free/open source | Trivial | Still invented and still arbitrary |

- **Recommended:** Readiness as a soft ranking factor plus advice, not a hard constraint. Hard constraints should be what investors publish (stage, sector, ticket). A readiness number Vanigam made up should rank, not exclude.
- **Ruled out:** Per-stage gate: still invented thresholds; lowering it: arbitrary

### R047

**Planner sector fact mixes vocabularies; K_DOMAIN misses registry ids like healthtech** · weight 84 · Logic flaw · impact 4/5, reach 4/5, confidence 3/3 · flags F-B4-002

- **Evidence (B4):** backend/app/planner/plan.py:97 sets facts['sector'] to the slot sector (elicitation enum: 'health', 'agri', 'it_services') or else the pack/registry sector (ecosystem ids; registry categories carry 'agritech', 'healthtech', 'saas', 'deeptech', 'fintech', 'cleantech', 'textiles', 'electronics', 'logistics' - checked by loading registry). backend/app/planner/roadmap.py:33 K_DOMAIN = {'food','health','electronics','manufacturing'} (elicitation ids) used at :118, so a health idea whose sector came from the registry gets 1.0 instead of 1.25. backend/app/planner/registry.py:96-115 scheme rules and :169 incubator match test ecosystem ids; backend/app/agents/council/vote.py:35-45 tests elicitation ids ('health', 'agri', 'it_services'). backend/app/routers/cohort.py:21 accepts any ^[a-z_]+$ sector, and cohort/reference.py:78 then silently finds zero companies for an elicitation id like 'agri'.

- **Why it matters:** The same idea gets a different timeline, scheme list or panel weighting depending on which vocabulary supplied 'sector'. TASKS 4.1.2 names the three vocabularies to merge but not the literal consumers; adopting StartupTN categories (D5) would silently break every literal comparison above, since a mismatched string just evaluates False with no error.
- **Where to build it:** the 4.1.2 taxonomy module plus planner/plan.py, planner/roadmap.py, planner/registry.py, agents/council/vote.py, funding/investor_match.py, cohort/reference.py and routers/cohort.py

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Canonical str Enum, consumers compare against members, plus a test banning sector string literals | Python Enum already used (slots.Sector); ruff/mypy in the stack; an AST or grep test is a few lines of pytest | free/open source | Renames fail loudly; one to_canonical() normaliser at every entry point; gives 4.1.2.1 a consumer checklist | Touches many modules in one migration |
| normalise_sector() at boundaries only (plan facts, cohort router, vote) | Minimal adapter pattern | free/open source | Small diff | Literals stay scattered; the next consumer repeats the bug |
| Pydantic Literal or Enum validation on facts and API inputs | Pydantic v2 already backs the FastAPI routers | free/open source | Rejects unknown ids at the API edge (cohort ReferenceIn today) | Does not reach in-process dict lookups such as K_DOMAIN.get() |

- **Recommended:** Canonical str Enum, consumers compare against members, plus a test banning sector string literals. Turns today's silent False comparisons into import or type errors and makes the migration checkable; pair with Pydantic validation at the API edge.
- **Ruled out:** Boundary normaliser only: leaves literals that drift again; Pydantic alone: misses internal lookups like K_DOMAIN and registry rules.

### R064

**NEEDS and UYEGP age rules contradict the catalogue: wrong 'no' and wrong 'yes'** · weight 78 · Logic flaw · impact 4/5, reach 3/5, confidence 3/3 · flags F-A4-002

- **Evidence (A4):** seed.py:183-188 NEEDS age BETWEEN [21,45] for everyone; funding_catalogue.json needs.eligibility (confidence 'official', msmetamilnadu.tn.gov.in/needs.php) says 'Age 21-45; up to 55 for women, BC/MBC/SC/ST, ex-servicemen, transgender, differently abled'. seed.py:210-215 UYEGP BETWEEN [18,45] for everyone; the catalogue says 18-35 general, 18-45 special. Run results: a 50-year-old SC woman is rejected from NEEDS; a 40-year-old general-category man is returned ELIGIBLE for UYEGP. The engine docstring (engine.py:3-4) promises a scheme is returned eligible only if it is truly eligible. Also, special category in TN means BC/MBC, but Schemes.tsx:24 offers only general/obc/sc/st/ews.

- **Why it matters:** A founder is sent to a District Industries Centre for a subsidy they cannot get, or never hears about NEEDS (up to Rs 75L subsidy) that they qualify for. The seed and the catalogue were checked eleven days apart and disagree, and nothing tests that they agree.
- **Where to build it:** backend/app/schemes/seed.py (category-aware ANY groups), the profile enum for caste/special category (add bc, mbc, ex_servicemen, differently_abled, transgender), a new tests/unit/test_seed_matches_catalogue.py

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Category-aware rule groups plus a seed-vs-catalogue consistency test | Uses the existing ANY/ALL combinators; a pytest test parses both data sets by shared id | free/open source | Exact to the published rule; the test catches the next drift | The special-category list must be modelled as a profile field |
| Generate rule trees from structured catalogue fields (age_general, age_special) | Makes the catalogue the single source, as 4.1.1 wants | free/open source | One edit point | The catalogue eligibility field is free text today; needs a schema first (5.2.1) |
| Use the widest band and add an unmodelled note | What the code does now | free/open source | No new field | Breaks soundness: it says yes to people who are not eligible |
| Hypothesis property test only | Hypothesis is the standard Python property-testing library (already planned in 5.1.4) | free/open source | Finds edge ages automatically | Checks consistency with itself, not with the published rule; needs an oracle anyway |

- **Recommended:** Category-aware rule groups plus a seed-vs-catalogue consistency test. It fixes both wrong answers now with the engine as it is, and the test stops the two scheme sources drifting apart until 4.1.1 merges them.
- **Ruled out:** Generate from catalogue: blocked until the catalogue has structured fields (5.2.1); widest band: the current bug; Hypothesis alone: has no published rule to compare against

### R067

**Order split leaves any item over Rs 1 lakh a unit unbought, with a false reason** · weight 78 · Logic flaw · impact 4/5, reach 3/5, confidence 3/3 · flags F-A4-008

- **Evidence (A4):** backend/app/b2b/allocate.py:87 SHORT_PENALTY = 10_000_000 per unit, but unit cost is in paise (allocate.py:127), so the penalty is only Rs 1,00,000. The docstring at line 87 says placing demand always beats leaving it unmet. Ran allocate([Line('l1','machinery',2)], [supplier at Rs 2,50,000, capacity 5]): splits [], unmet 2, why_unmet ['capacity is taken by your other lines'], which is false since there is no other line.

- **Why it matters:** A founder buying machinery, a cold-room or any capital item gets an empty plan and a made-up explanation. The minimiser prefers 'short' whenever price plus penalties is more than Rs 1 lakh a unit.
- **Where to build it:** backend/app/b2b/allocate.py (objective), _why_unmet

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Lexicographic solve: first maximise placed units, then minimise cost with placement fixed | Standard two-stage CP-SAT pattern (solve, add the optimum as a constraint, re-solve); OR-Tools is already in the stack | free/open source | Correct for any price scale; no magic constant | Two solves (each tiny, under 20 lines and 100 quotes) |
| Penalty derived from the data: (max unit price + max penalty) * 100 + 1 | Big-M chosen from the inputs | free/open source | One solve; small change | Large coefficients can slow CP-SAT or overflow with huge quantities (up to 10^7 units allowed) |
| Hard constraint short == 0, with fallback to the current model if infeasible | Feasibility first | free/open source | Simple when supply is enough | Still needs the penalty model for the shortfall case |

- **Recommended:** Lexicographic solve: first maximise placed units, then minimise cost with placement fixed. It encodes the stated rule (placement first) exactly, whatever the price, and the models are small enough that a second solve costs milliseconds.
- **Ruled out:** Data-derived big-M: fragile at the allowed 10^7 quantities; hard constraint: needs the penalty model anyway for real shortfalls

### R080

**BOM category keyword matching misfires on substrings** · weight 74 · Logic flaw · impact 3/5, reach 4/5, confidence 3/3 · flags F-A4-011, F-B4-007

- **Evidence (A4):** decompose.py:150-155 matches substrings, first match wins. Ran decompose(): 'patriot flags' and 'smartphone case' give pcb, sensor, packaging ('iot' and 'smart' inside words); 'food processing machinery' gives pump, packaging; 'solar powered cold storage unit' (the Supply.tsx:61 default), 'tea', 'jasmine garland', 'coir mats', 'organic fertiliser' all give ['packaging'] only. The ideation quality set already uses tea, jasmine and knitwear (TASKS 4.1.2).
- **Evidence (B4):** backend/app/b2b/directory.py:24-43 CATEGORY_NIC needs exact keys ('natural dye' -> known False, 'No activity codes mapped'); routers/b2b.py:103 DirectoryIn.category is free text; b2b/decompose.py:32-66 _TEMPLATES uses substring cues with first match. Ran: 'smartphone stand furniture' -> pcb + sensor lines ('smart'); 'knitwear from tiruppur' and 'leather sandals' -> packaging only (no 'knit' or 'leather' cue, though CATEGORY_NIC has leather and garments). TASKS 4.1.2 lists three vocabularies, not this one or the frontend CLUSTERS keys.

- **Why it matters:** A founder confirms a draft that leaves out every real input, or sources PCBs for a flag. Because only 'packaging' is found, the supply map looks complete when it is not.
- **Where to build it:** backend/app/b2b/decompose.py (templates and matching), linked to the canonical sector list (4.1.2)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Word-boundary token matching plus templates keyed to the canonical sectors, with an 'unknown product: add lines yourself' result instead of the packaging default | Deterministic offline baseline (decision 0002); regex \b or token sets | free/open source | No false hits; honest when unknown; testable | Templates need curating per sector |
| Free-model draft (Gemini then Ollama, decision 0009), validated so only known CATEGORY_NIC keys are kept | The provider chain already exists in agents/providers.py | free tier | Covers long-tail products | Optional path only; offline result still needs the deterministic floor |
| rapidfuzz fuzzy matching of product to templates | Popular, fast MIT library | free/open source | Tolerates spelling | Fuzzy matching makes false hits like 'iot' in 'patriot' more likely, not less |
| spaCy noun-phrase extraction | Mature NLP library | free/open source | Better parsing of product descriptions | Heavy model download; English only; still needs a product-to-BOM map |

- **Recommended:** Word-boundary token matching plus templates keyed to the canonical sectors, with an 'unknown product: add lines yourself' result instead of the packaging default. It fixes the false hits and the false completeness offline. The free-model draft can be added on top later, filtered to known categories.
- **Ruled out:** Model draft alone: not offline; rapidfuzz: makes false hits more likely; spaCy: heavy and still needs the map

### R084

**'Something to act on' fires on funding-round news and on deadlines that have passed** · weight 74 · Logic flaw · impact 3/5, reach 4/5, confidence 3/3 · flags F-A4-022

- **Evidence (A4):** pipeline.py:130-145 and 248-253 match substrings such as 'funding', 'launch', 'apply' and 'application' anywhere in the text. Ran: 'Agritech startup raises Rs 50 crore in Series B funding' is tagged 'something to act on'. 'Applications for TANSEED closed on 20 September' (published yesterday) scores 67 with 'something to act on', 'official source' and 'published in the last 48 hours', the top-scoring pattern. The design note (sources.py:11-12) says a founder acts on scheme deadlines from this board.

- **Why it matters:** Founders are pushed toward closed calls and other companies' funding rounds as if they were opportunities. Actionability is 15% of the score and also appears as a visible reason.
- **Where to build it:** backend/app/news/pipeline.py (_actionability), optionally the source focus tags

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Phrase patterns with negation and date check: 'apply by / last date / applications open', demoted by 'closed / ended / extended till <past date>', with dates read by dateparser | dateparser is a widely used free library that reads English and Tamil dates | free/open source | Catches passed deadlines; fewer false 'act' tags | Pattern list needs upkeep; adds a dependency |
| Regex patterns only (stdlib re), no date reading | No dependency | free/open source | Simple | Cannot tell a past deadline from a future one |
| Act only on government-tier items whose focus includes 'schemes' | Uses existing source metadata | free/open source | Removes trade-press false hits | Misses real calls reported by newspapers; still tags closed calls |
| Free-model classification (Gemini then Ollama, 0009) | Existing provider chain | free tier | Handles wording variety | Not offline; a model must not decide a fact the founder acts on (0002) |

- **Recommended:** Phrase patterns with negation and date check: 'apply by / last date / applications open', demoted by 'closed / ended / extended till <past date>', with dates read by dateparser. It is deterministic and offline, and it is the only option that catches a passed deadline, which is the costly mistake for a founder.
- **Ruled out:** Regex only: cannot see that a date has passed; government-only: misses real calls and still tags closed ones; model: not offline and decides a fact, against 0002

### R090

**Flat Rs 2 'far' penalty ignores price scale and picks a 2.5x dearer supplier** · weight 74 · Logic flaw · impact 3/5, reach 4/5, confidence 3/3 · flags F-A4-009

- **Evidence (A4):** allocate.py:88-89 FAR_PENALTY = 2 and TRUST_BONUS = 1 rupees per unit, added at allocate.py:128-131 whatever the unit price. 'Far' means a district-string mismatch only, although directory.py computes km. Ran: 1,000 beads, Chennai supplier at Rs 1.00 versus Madurai (buyer's district) at Rs 2.50 gives all 1,000 units from Madurai, Rs 2,500 instead of Rs 1,000. For a Rs 50,000 item the same Rs 2 does nothing.

- **Why it matters:** Low-cost lines (packaging, labels, beads) are bought at several times the price. High-value lines ignore distance and trust completely. The 'rules' block in the response presents this as a reasoned preference.
- **Where to build it:** backend/app/b2b/allocate.py cost terms; QuoteIn (an optional delivery cost per unit)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Relative penalties: far = p% of unit price (or distance-based freight from km), trust = q% | Scales with the item; km already exists in directory.py | free/open source | Same behaviour for cheap and dear items; can be explained ('5% for distance') | The percentages are a tuning choice to document |
| Founder-entered landed cost (price including delivery) on each quote | Quotes in practice include freight terms | free/open source | Uses real numbers, not a rule of thumb (no invented data) | One more field for founders to fill in |
| Drop the distance and trust terms; minimise price only | Simplest objective | free/open source | Transparent | Loses the local-first preference the design wants |

- **Recommended:** Founder-entered landed cost (price including delivery) on each quote. It replaces a guessed constant with the founder's real number, fits 'no invented data', and falls back to a small relative penalty when left blank.
- **Ruled out:** Relative penalties alone: still a guess about freight; price-only: drops a stated preference

### R091

**Funding fit compares the founder's need with mixed amounts (benefit cap, loan size, project)** · weight 74 · Logic flaw · impact 3/5, reach 4/5, confidence 3/3 · flags F-A4-005

- **Evidence (A4):** ranking.py:130-140 compares funding_need with min_funding/max_funding. Those mean different things per scheme: PMEGP max 1,750,000 is the subsidy (seed.py:96 '35% of a Rs 50L project'), NEEDS 7,500,000 is the subsidy cap on a Rs 5 Cr project, CGTMSE 100,000,000 is the guaranteed loan, SISFS 2,000,000 is the grant with the Rs 50L debt left out. The catalogue's amount_min/max use other values again (needs 1,000,000-50,000,000 = project cost; cgtmse 50,000,000). Run: a Rs 40L need 'fits your funding need' for NEEDS (a 25% subsidy gives about Rs 10L) and scores PMEGP lower although a Rs 40L project is inside PMEGP's limit.

- **Why it matters:** 'Fits your funding need' and the relevance score are wrong in both directions, and the planned amount filter (4.1.5.1) would inherit the confusion.
- **Where to build it:** schemes/models.py (project_min/project_max, benefit_max, benefit_rate), ranking.py _funding_fit, catalogue fields

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Separate project range and benefit fields; fit against the project range, show the benefit | Matches how subsidy schemes are published (percentage of a project, with a cap) | free/open source | Correct unit; can say 'about Rs X of your Rs Y' | Every entry needs its fields curated and cited |
| Estimate benefit = min(rate * need, cap) and compare it with need | Simple arithmetic on published rates | free/open source | Gives founders a number | Rates vary by category and place (PMEGP 15-35%); needs those inputs |
| Drop funding fit from relevance | Removes the wrong signal | free/open source | Trivial | Loses 'which schemes cover my size' |

- **Recommended:** Separate project range and benefit fields; fit against the project range, show the benefit. One clear unit per field fixes both the score and the future filter, and the estimate option can be added on top later.
- **Ruled out:** Benefit estimate alone: needs per-category rates that are not modelled yet; dropping fit: loses a real ranking signal

### R092

**Gap plan ignores what the founder already has; its impact points disagree with the rubric** · weight 74 · Logic flaw · impact 3/5, reach 4/5, confidence 3/3 · flags F-A4-018

- **Evidence (A4):** gaps.py:193-200 adds the whole playbook for any dimension under 60, without checking inputs. Ran: an mvp or revenue founder with product 55/20 is told 'Ship an MVP with the core feature set'. The fixed impact_points (gaps.py:143-174) do not follow readiness.py: 'Register the entity' claims 8 points, but is_registered adds 30 to legal, which is weighted 0.10, so 3 overall points; 'Apply for DPIIT recognition' claims 5 against 2; 'Add a co-founder' claims 8 against about 1.6 (team_size +1 gives +8 team x 0.20). The list is ordered by these numbers (ratio, line 199).

- **Why it matters:** Founders get advice for steps already done and a priority order built on wrong numbers. 4.3.2 would then track progress on the wrong recommendations.
- **Where to build it:** backend/app/funding/gaps.py (playbook entries tied to rubric inputs)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Counterfactual re-score: each action names the input it changes; impact = score_readiness(after) - score_readiness(before) | The rubric is a pure function, so the simulation is exact and cheap | free/open source | Correct points; actions already done drop out automatically | Each playbook action needs an input mapping |
| Precondition per action (skip 'Register the entity' if is_registered) | Simple guard per row | free/open source | Removes the stale advice | Impact numbers stay wrong |
| Remove impact points; order by dimension gap only | Simplest | free/open source | No false precision | Loses the 'highest leverage first' ordering |

- **Recommended:** Counterfactual re-score: each action names the input it changes; impact = score_readiness(after) - score_readiness(before). It fixes both faults with the existing pure scorer and stays deterministic. A property test can check that impact equals the score change.
- **Ruled out:** Preconditions alone: keeps wrong impact numbers; removing impact: loses the ordering the design asks for

### R094

**Intel calls the synthetic corpus 'cached'; personalisation and language are never used** · weight 74 · Logic flaw · impact 3/5, reach 4/5, confidence 3/3 · flags F-A4-025

- **Evidence (A4):** Intel.tsx:53 shows status 'live' or 'cached', so the fixture demo is shown as 'cached', which suggests real news stored earlier. Intel.tsx:37 sends only {limit: 24}, no founder sector, district or stage, so pipeline.py:222-245 personalisation never applies. routers/news.py:435-436 sets ctx.language, but rank() never reads it, and fixtures include Tamil ('ta') items and Tamil sources (dinamalar, dinamani).

- **Why it matters:** 4.4.1's aim is that founders never mistake demo items for real news, and the main label says the opposite. Every founder gets the same order, and Tamil readers get no language preference.
- **Where to build it:** frontend/src/pages/Intel.tsx (status label, founder context from the journey/profile store), backend/app/news/pipeline.py (language boost or filter)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Label 'demo' when provider is fixture; send profile fields; boost items in the founder's language | is_live and provider are already in the response; the profile exists in journeyStore | free/open source | Small changes; uses existing data | Profile comes from the browser until 3.1.2 |
| Filter to the founder's language only | Simple rule | free/open source | Clean board for Tamil readers | Hides official English-only scheme notices |
| Server reads the founder context from the session | Sessions hold the slots | free/open source | No duplicate profile | Needs a session id on the Intel page |

- **Recommended:** Label 'demo' when provider is fixture; send profile fields; boost items in the founder's language. It fixes the misleading label whatever D9 decides, and switches on ranking features that are already built.
- **Ruled out:** Language filter: hides official English notices; session read: needs session plumbing the Intel page lacks

### R097

**No date normalisation at the fetch boundary: RSS dates get recency 0** · weight 74 · Missing structure · impact 3/5, reach 4/5, confidence 3/3 · flags F-A4-023

- **Evidence (A4):** models.py:16 says RawArticle.published is an 'ISO date', but nothing enforces it. fetch.py:74-86 _clamp only trims the extract. pipeline.py:194-199 returns 999 days old for any non-ISO date. Ran an RSS-style 'Fri, 17 Oct 2026 08:00:00 GMT' item: recency 0, no '48 hours' reason, score 48. RSS 2.0 pubDate uses this RFC 822 form, so once HttpNewsFetcher is written every live item will rank as stale.

- **Why it matters:** When D9 picks live sources, the board will sort live news as if it were a month old and push fresh deadlines below demo-era items. HttpNewsFetcher is still unwritten (fetch.py:55-65), and nobody has specified this contract for it.
- **Where to build it:** backend/app/news/fetch.py (_clamp or a normalise step), the future HttpNewsFetcher

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| feedparser in the live fetcher, normalising published_parsed to ISO in _clamp | The standard Python RSS/Atom parser for over 15 years; parses RFC 822 and ISO 8601 dates | free/open source | Handles the feed formats and dates in one library | One dependency |
| email.utils.parsedate_to_datetime (stdlib) with an ISO fallback | Standard library RFC 2822 parser | free/open source | No dependency | Feed parsing still has to be written by hand |
| python-dateutil parser | Popular general date parser | free/open source | Accepts almost any format | Too lenient: guesses ambiguous dates silently |

- **Recommended:** feedparser in the live fetcher, normalising published_parsed to ISO in _clamp. The live fetcher needs a feed parser anyway. feedparser solves dates as part of that, and normalising in _clamp enforces the contract for any provider.
- **Ruled out:** stdlib only: leaves feed parsing hand-written; dateutil: silent guesses on ambiguous dates

### R100

**One article from an unknown source crashes the whole board (KeyError in dedupe)** · weight 74 · Logic flaw · impact 3/5, reach 4/5, confidence 3/3 · flags F-A4-021

- **Evidence (A4):** news/pipeline.py:273 indexes BY_ID[art.source_id] during dedupe, before the attribution guard at pipeline.py:283 (BY_ID.get, 'never serve an item we cannot attribute'). Ran rank() with a startuptn item and a near-duplicate from source 'unknown': KeyError 'unknown', so /news/board returns 500.

- **Why it matters:** When live fetching starts (or a source is removed from the list while items are cached), one stray item takes down the founder's whole news board instead of being dropped.
- **Where to build it:** backend/app/news/pipeline.py rank()

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Drop unattributable articles before dedupe | Move the existing guard to the top of rank() | free/open source | One-line fix; keeps the stated rule | None of note |
| BY_ID.get with a default trust in dedupe | Defensive lookup | free/open source | No crash | An unknown source can still win as the canonical item, then gets dropped and takes its duplicates with it |
| Validate source_id in the fetcher boundary (_clamp) | Enforce at the provider edge like the extract cap | free/open source | Bad data never enters the pipeline | rank() stays fragile for other callers |

- **Recommended:** Drop unattributable articles before dedupe. It is the smallest change, enforces the module's own attribution rule first, and avoids the lost-duplicate edge case. Add a regression test.
- **Ruled out:** get-with-default: can lose real duplicates; boundary-only check: rank() still crashes for other inputs

### R111

**Unencoded criteria already returned by the API are never shown on the Schemes screen** · weight 74 · Missing function · impact 3/5, reach 4/5, confidence 3/3 · flags F-A4-007

- **Evidence (A4):** routers/schemes.py:35 and scheme_schemas.py:26 return unmodelled_notes (e.g. SISFS 'Indian promoters must hold at least 51%', UYEGP 'Family income up to Rs 5 lakh'); grep of frontend/src/pages/Schemes.tsx and api.ts for 'unmodelled' or 'notes' finds nothing.

- **Why it matters:** A founder sees 'eligible' with no sign of the income, education or ownership conditions that may rule them out. 4.1.1.2 plans this for catalogue criteria, but the seed's notes, which already exist, are not shown either.
- **Where to build it:** frontend/src/pages/Schemes.tsx and api.ts (RecommendOut type)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Render the notes under each scheme as 'Also check' | Plain list in the existing Reasons component | free/open source | No backend change; meaning only, no styling (fits the unstyled baseline) | Lengthens each card |
| Collapsed <details> per scheme | Native HTML | free/open source | Short cards | Founders on phones may never open it |
| Turn notes into yes/no questions the founder answers | Would fold into the three-valued engine | free/open source | Moves criteria into rules | That is 4.1.1.1's work, not a display fix |

- **Recommended:** Render the notes under each scheme as 'Also check'. Smallest change that shows the founder the conditions now; it does not depend on the theme decision because it adds text, not styling.
- **Ruled out:** Collapsed details: easy to miss; question form: belongs to 4.1.1.1

### R112

**Unpublished investor stage or sector means 'no'; fit score is built mostly from constants** · weight 74 · Missing logic · impact 3/5, reach 4/5, confidence 3/3 · flags F-A4-019

- **Evidence (A4):** Of 36 real investors, 12 have no stages and 10 no sectors; investor_match.py:259-264 rejects them with 'Investment stage not published' or 'Sectors not published', even though investors.py:4-6 says unknowns stay unknown (only the ticket follows that). _fit (investor_match.py:284-306): stage is always 100, geography always 100 for TN founders (investors.py:168 sets geographies ['Tamil Nadu'] for all), track always 60 (track_record_known False), so 60% of the weight is constant. Ran mvp agritech: NativeLead 96, then four investors tied at 90.

- **Why it matters:** Real TN investors who might fund the founder are shown as 'no', and the 'fit' order the founder sees carries almost no information.
- **Where to build it:** backend/app/funding/investor_match.py (an 'unknown: ask them' bucket; fit terms with real variation)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Three-valued constraints with a 'check with the investor' group, and fit only from varying terms (sector specialist, stage-list position, traction margin, thesis keyword overlap) | Same three-valued pattern recommended for schemes (A4-01); thesis text already in the data | free/open source | Honest grouping; fit that ranks | Thesis overlap needs the canonical sectors (4.1.2) |
| BM25 over investor thesis text (rank_bm25) | Small, popular pure-Python library | free/open source | Uses the richest field in the data | Text similarity on 36 short summaries is noisy |
| Curate missing stages and sectors from investors' own sites | Weekly checks of organisations' own sites are allowed (D10 recommendation) | free/open source | Better data | Curation effort; does not fix the logic |

- **Recommended:** Three-valued constraints with a 'check with the investor' group, and fit only from varying terms (sector specialist, stage-list position, traction margin, thesis keyword overlap). It fixes the logic now with the existing data. Curation can fill gaps over time without code changes.
- **Ruled out:** BM25: noisy on tiny texts and adds a dependency; curation alone: leaves unknown as 'no'

### R125

**A cluster map already exists, uncited, in Supply.tsx; 4.2.2 would create a second owner** · weight 68 · Missing structure · impact 3/5, reach 3/5, confidence 3/3 · flags F-B4-004

- **Evidence (B4):** frontend/src/pages/Supply.tsx:39-55 hard-codes CLUSTERS (pump->Coimbatore, yarn/dye->Tiruppur, leather->Ambur-Ranipet, printing/packaging->Sivakasi, pcb/sensor->Hosur) with no source URL, matched by category.includes(key). Supply.tsx:318-319 says 'The nearest place to look is <cluster>' whatever the founder's district (the form defaults to Madurai). TASKS 4.2.2 puts the mapping in b2b/directory.py and never mentions this copy.

- **Why it matters:** After 4.2.2 the founder may see two cluster answers, a cited backend one and an uncited frontend one, and they can disagree. The frontend copy breaks 'no invented data' (no citation) and calls a fixed place 'nearest', which is wrong for a Madurai founder sent to Hosur.
- **Where to build it:** backend b2b cluster data file (Git-curated, cited) served through /b2b/decompose and /b2b/directory; remove CLUSTERS from Supply.tsx

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Cited JSON data file in backend (b2b/data/clusters.json) keyed by canonical category or NIC prefix, returned with each line | Matches the repo's reference-data-in-Git rule (SYSTEM-DESIGN section 2, as in schemes/data/funding_catalogue.json) | free/open source | One owner; each cluster carries source_url and districts; distance can be computed from cluster district centroids | Needs curation of sources (MSME-DI / TN industries cluster lists) |
| Keep frontend constant but add citations | Smallest diff | free/open source | Quick | Logic stays in the UI; /suppliers and the roadmap cannot reuse it; violates code-decides layering |
| Derive clusters from the MCA company file via the ecosystem zone location quotients (ecosystem/zones.py) | Data already in repo; LQ is already computed for sector zones | free/open source | Data-driven, cited to MCA | Company file covers only Chennai, Coimbatore and Madurai, so it cannot find Tiruppur, Sivakasi, Ambur or Hosur |

- **Recommended:** Cited JSON data file in backend (b2b/data/clusters.json) keyed by canonical category or NIC prefix, returned with each line. Gives 4.2.2 one cited source and lets the server choose the nearest cluster by district. The frontend copy goes in the same pull request.
- **Ruled out:** Frontend constant with citations: leaves domain logic in the screen and unusable elsewhere; LQ-derived clusters: the company data does not cover the districts where the clusters actually are.

### R145

**TANSEED is called a 'non-dilutive grant' though StartupTN takes a 3% stake** · weight 68 · Logic flaw · impact 3/5, reach 3/5, confidence 3/3 · flags F-A4-004

- **Evidence (A4):** ranking.py:168-169 adds 'non-dilutive grant' for any SchemeType.GRANT. seed.py:61 TANSEED type=GRANT, while seed.py:78 benefits and catalogue tanseed.benefit say 'StartupTN takes a 3% stake'. TANSEED stage rule seed.py:70-75 also lets in 'idea', but the catalogue eligibility says 'Prototype or MVP showing technology-led innovation' and 'Private Limited company or LLP'.

- **Why it matters:** A founder gives up equity they were told they would keep. Idea-stage founders are sent to a call they will be screened out of.
- **Where to build it:** schemes/models.py (dilutive flag or an equity_linked_grant type), ranking.py reason text, seed.py TANSEED stage and entity rules

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Explicit `dilutive: bool` (and equity %) on Scheme, used in the reason | A small dataclass field that keeps the reason text honest | free/open source | Works for any future equity-linked grant (the catalogue has investor channels too) | One more field to curate |
| New SchemeType.EQUITY_GRANT | Extends the existing enum | free/open source | Type carries the meaning | Frontend filters by type (4.1.5.1) would need the new value |
| Drop the 'non-dilutive' wording | Simplest | free/open source | Removes the false claim | Loses useful information for true grants |

- **Recommended:** Explicit `dilutive: bool` (and equity %) on Scheme, used in the reason. It is accurate and needs no change to the type filter. The TANSEED stage rule should be fixed in the same commit, against the catalogue.
- **Ruled out:** New type: spreads into the filters and frontend; dropping the wording: loses a real signal

### R149

**When a supplier's minimum order is above the need, the line is just 'unmet'** · weight 68 · Missing logic · impact 3/5, reach 3/5, confidence 3/3 · flags F-A4-013

- **Evidence (A4):** allocate.py:123-125 caps x at the line quantity, so a supplier whose min_order is above the quantity can never be used. Ran a 100-unit need against a supplier with MOQ 200 at Rs 100: unmet 100, reason 'minimum order above your quantity'. No option to buy the MOQ is offered.

- **Why it matters:** Small first-batch founders are exactly the ones below MOQs. The real choice is to buy 200 for Rs 20,000 or find another supplier, and the plan hides it.
- **Where to build it:** backend/app/b2b/allocate.py (optional over-order variable), response 'alternatives'

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Allow over-ordering up to the MOQ with the excess cost in the objective, reported as 'buy N, extra Rs X' | One extra integer variable per (line, supplier) in the existing CP-SAT model | free/open source | Shows the real trade-off | Needs a rule for when over-buying beats a shortfall |
| Post-solve suggestion only: for unmet lines, list the cheapest MOQ purchase | Plain arithmetic after the solve | free/open source | No model change | Ignores capacity shared with other lines |
| Leave as is | Current behaviour | free/open source | None | Leaves the founder stuck |

- **Recommended:** Post-solve suggestion only: for unmet lines, list the cheapest MOQ purchase. It is cheap, keeps the solver's 'never buy more than asked' rule, and gives the founder the missing option. Move it into the model later if founders use it.
- **Ruled out:** Over-order variable: needs a policy decision on buying extra; leave as is: no answer for the founder

### R152

**News board fetches on every request; no stored corpus or refresh schedule** · weight 67 · Optimisation · impact 3/5, reach 4/5, confidence 2/3 · flags F-A4-024

- **Evidence (A4):** routers/news.py:431-432 calls fetcher.fetch() on each POST /news/board. fetch.py:48 lists conditional GETs and backoff as required, but there is nowhere to keep ETags or the corpus. Intel.tsx:37 and 95 call the board on page load. TASKS 2.2 caching rules and 5.4.4 nightly job do not mention news.

- **Why it matters:** When live, every founder page view would hit eleven publishers. That breaks the polite crawl the code itself requires, risks bans, and makes a 2G page wait on remote feeds.
- **Where to build it:** backend/app/news/ (a corpus store and refresher), routers/news.py (read only from the store), scripts/nightly.py or a scheduled refresh (5.4.4)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Scheduled refresh (every few hours) writing the ranked-input corpus to Redis with a file fallback, with ETag/Last-Modified kept per source | Redis is in the stack; 5.4.4 plans a scheduler on the app host | free/open source | One fetch per source per interval; board answers from memory; works offline from the last corpus | Needs the scheduler from 5.4.4 |
| hishel HTTP cache for httpx | RFC 9111 caching transport for httpx | free/open source | Conditional GETs handled for you | Still fetches on the request path; first request per interval is slow |
| In-process TTL cache (cachetools) | Popular small library | free/open source | Very simple | Per worker, so N workers fetch N times; lost on restart |

- **Recommended:** Scheduled refresh (every few hours) writing the ranked-input corpus to Redis with a file fallback, with ETag/Last-Modified kept per source. It takes publisher traffic off the request path, matches the polite-crawl rules already written in fetch.py, and reuses Redis and the planned nightly scheduler.
- **Ruled out:** hishel: keeps fetching on the request path; cachetools: per worker and lost on restart

### R168

**Founder sector is single-valued while matchers are multi-sector; no rule for mixed ideas** · weight 61 · Missing logic · impact 3/5, reach 3/5, confidence 2/3 · flags F-B4-003

- **Evidence (B4):** backend/app/elicitation/slots.py:189 sector is one enum value chosen by first dict-order cue; backend/app/ecosystem/taxonomy.py sectors_in returns a list and ecosystem/match.py:161,229,241,263 match on f.sectors (list). Ran: 'A loan app for dairy farmers' -> elicitation AGRI only, and sectors_in -> ['agritech'] ('loan' is in elicitation finance cues but not in the ecosystem fintech regex); 'Solar cold storage for fish markets' -> elicitation no sector, sectors_in -> ['cleantech']. The two cue sets disagree term by term.

- **Why it matters:** Agri-fintech, health-IoT and similar ideas lose their second sector, so matchers that support several sectors get one arbitrary one. D5 chooses a list but not cardinality or precedence, and the plan's coverage test does not check that the cue sets agree.
- **Where to build it:** the 4.1.2 taxonomy module; elicitation/slots.py slot definition; ecosystem/match.py founder profile

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Primary sector slot plus a derived secondary list from all cue hits | Keeps the slot machine single-valued (selector unchanged) while exposing every hit | free/open source | Matchers use the list; questions stay simple; ties lower confidence so the primary is confirmed | Needs a precedence rule for the primary |
| Make sector a multi-select slot | Elicitation engine already handles enum slots | free/open source | Founder states every sector | Reworks selector, stopping rule and confirmation wording |
| Keep a single value; confirm when cues hit two sectors | Existing CONFIRMING state (elicitation/engine.py:222) | free/open source | No schema change; founder resolves ambiguity | Still drops the secondary sector downstream |

- **Recommended:** Primary sector slot plus a derived secondary list from all cue hits. Preserves the one-question flow and selector constants while letting multi-sector matchers use every hit.
- **Ruled out:** Multi-select slot: reworks selector and wording for a small gain; confirm-only: keeps losing the second sector for matching.

### R186

**Pipeline metrics wrong: lost deals count as reaching every stage; first-stage time is lost** · weight 58 · Logic flaw · impact 2/5, reach 3/5, confidence 3/3 · flags F-A4-020

- **Evidence (A4):** pipeline.py:131-132 _reached treats a terminal entry with no history as having passed all open stages. Ran [closed_lost (no history), initial_contact]: conversion to negotiation and term_sheet 50%. Pipeline.tsx:120 stamps history with new Date().toISOString() ('2026-10-17T10:00:00.000Z'), but pipeline.py:138 uses date.fromisoformat, which raises on that string (checked: 'Invalid isoformat string'), so the first stage's days are dropped (ran: initial_contact avg_days 0.0 after 9 days). STAGE_PROBABILITY (pipeline.py:33-42) gives uncited closing odds that drive 'weighted value'.

- **Why it matters:** A founder reads inflated conversion and zero time-in-stage, so the board says the funnel is healthier and faster than it is. Programme aggregates (5.5.5) will inherit these metrics once the board moves server-side (3.1.3).
- **Where to build it:** backend/app/funding/pipeline.py (_reached, _days), Pipeline.tsx (date format), weighted-value labelling

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Parse with datetime.fromisoformat (Python 3.11 accepts 'Z') then take .date(); terminal entries without history count only their terminal stage; label weighted value 'rule of thumb' or drop it | Standard library; small fixes | free/open source | Correct numbers; no dependency | Old entries without history lose inferred stages |
| python-dateutil parser | Widely used date parsing library | free/open source | Accepts any format | Extra dependency for one format the stdlib handles |
| Require history on every entry (422 without it) | Strict contract | free/open source | No inference needed | Breaks existing localStorage boards |

- **Recommended:** Parse with datetime.fromisoformat (Python 3.11 accepts 'Z') then take .date(); terminal entries without history count only their terminal stage; label weighted value 'rule of thumb' or drop it. Three small changes fix the numbers with the standard library and keep old boards loading.
- **Ruled out:** dateutil: unneeded dependency; strict history: breaks saved boards

### R197

**Allocate/pair inputs unvalidated: duplicate IDs drop units, categories case-sensitive** · weight 52 · Missing structure · impact 2/5, reach 2/5, confidence 3/3 · flags F-A4-014

- **Evidence (A4):** routers/b2b.py:299-325 QuoteIn and LineIn have no uniqueness or category validation. allocate.py:122-123 keys variables by (line.id, supplier.id) and line 150 builds by_id. Ran two quotes both with id 'a' (50 units each) for a 100-unit line: unmet 0 but the splits show 50 units, total_cost Rs 4,500, so 50 units vanish from the report. A quote with category 'Yarn' against line 'yarn' gives unmet 100, 'no supplier with known prices'. /match lowercases category (b2b.py:238), /allocate and /pair do not.

- **Why it matters:** The API returns plans whose splits do not add up to the quantity. Suppliers.tsx avoids this today (newId, a category select), but the API is public and 3.1.3 or other clients will call it.
- **Where to build it:** routers/b2b.py (Pydantic validators), allocate.py (keys by index)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Pydantic model validators: unique ids, category Literal from CATEGORY_NIC keys, lowercased | Pydantic is the existing schema layer | free/open source | 422 with a clear message; one category vocabulary | Category list must follow 4.1.2 |
| Key solver variables by list index internally | Removes reliance on caller ids | free/open source | Duplicate ids can no longer corrupt the model | Output is still ambiguous for the caller |
| Hypothesis property test: sum of splits + unmet == quantity | Standard property-testing library, planned in 5.1.4 | free/open source | Catches this class of bug | Detects the bug; does not fix it |

- **Recommended:** Pydantic model validators: unique ids, category Literal from CATEGORY_NIC keys, lowercased. It rejects bad input at the edge in the stack's own idiom. Add the Hypothesis invariant to 5.1.4 alongside it.
- **Ruled out:** Index keys alone: the caller still cannot tell which duplicate got the units; property test alone: detects, does not prevent

### R200

**Redirect guard accepts any listed domain, even ones whose robots rules are unchecked** · weight 52 · Missing logic · impact 2/5, reach 2/5, confidence 3/3 · flags F-A4-026

- **Evidence (A4):** sources.py is_allowlisted compares the host against all SOURCES, not fetchable_sources(), and ignores the URL scheme. fetch.py:67-71 guard() uses it 'after every redirect'. A redirect from a verified feed to another listed publisher whose robots_ok is False, or to plain http, would be followed. robots_ok is a static flag; nothing re-reads robots.txt at fetch time.

- **Why it matters:** The owner's robots check (4.4.1.2) is a one-time flag that the live crawler can get around through redirects, and it goes stale if a publisher changes its rules. That is the legal risk the allowlist exists to prevent.
- **Where to build it:** backend/app/news/sources.py (is_fetchable_url), fetch.py guard and the future HttpNewsFetcher

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Guard against fetchable sources and https only, plus urllib.robotparser checked at fetch time (cached daily) | Standard library robots parser | free/open source | No dependency; enforces the rule each time | stdlib parser lacks some extensions (e.g. wildcards per Google spec) |
| protego robots parser | Scrapy's maintained, spec-complete robots.txt parser | free/open source | Handles wildcards and crawl-delay | Extra dependency |
| Keep the static flag, tighten only the guard | Minimal change | free/open source | Fixes the redirect hole | Robots changes go unnoticed |

- **Recommended:** Guard against fetchable sources and https only, plus urllib.robotparser checked at fetch time (cached daily). It closes the redirect hole and keeps the robots check current with the standard library. Switch to protego only if a source uses rules the stdlib misreads.
- **Ruled out:** protego: a dependency not yet needed; static flag only: robots changes go unseen

