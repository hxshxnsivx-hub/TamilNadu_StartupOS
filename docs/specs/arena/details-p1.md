# Arena flags: P1 Ideation details

Back to the [weighted table](../ARENA-FLAGS.md).

### R003

**Unknown profile field treated as failing a scheme rule ('not known' becomes 'not eligible')** · weight 100 · Logic flaw · impact 5/5, reach 5/5, confidence 3/3 · flags F-A4-001, F-B4-008

- **Evidence (A4):** backend/app/schemes/rules.py:47-48 (`if actual is None: return False`) and engine.py:69-74 (only eligible/ineligible). Ran SchemeSwarm.recommend for a TN idea-stage founder with no unit yet ({'stage':'idea'}, no incorporation_age_years, no annual_revenue): PMEGP was rejected with 'For new units only (<= 1 year)' and MUDRA with 'For micro enterprises (turnover up to Rs 10 crore)'. Those are the two schemes made for exactly this founder. SISFS also gets 'Not open to sole proprietorships' when entity_type is just missing. Schemes.tsx:83-84 sends Number(...) so the form cannot say 'not incorporated yet' (it sends 0 or the default of 1).
- **Evidence (B4):** backend/app/schemes/rules.py:48-49 `if actual is None: return False  # missing data can't satisfy a positive constraint`. I ran check_eligibility({'founder':{'state':'Tamil Nadu'},'startup':{'stage':'prototype'}}), roughly what the slots can supply: 0 eligible, 8 ineligible. Reasons given include 'Founder must be at least 18' (pmegp, standup_india), 'Requires DPIIT recognition' (sisfs, tanseed) and 'For first-generation entrepreneurs' (needs). The elicitation slot table (elicitation/slots.py:110-320) has no age, gender, caste, first_graduate, entity_type, dpiit or revenue slot.

- **Why it matters:** Founders who have not registered or earned yet are the ones Vanigam is for, and they get told 'no' with a false reason. When 1.4.3 projects conversation slots onto the profile, most startup fields (dpiit, incorporation age, revenue) will be missing, so almost every scheme will show as rejected. 4.1.3 adds a pre-revenue flag to the catalogue but does not change how the engine handles missing values.
- **Where to build it:** backend/app/schemes/rules.py (three-valued evaluate), engine.py (a third 'needs info' bucket), models/scheme_schemas.py and routers/schemes.py (a 'missing' list per scheme), Schemes.tsx (a 'not yet incorporated / no revenue yet' choice)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Three-valued (Kleene) evaluation in rules.py | Small change to the existing 120-line pure evaluator: Rule returns TRUE/FALSE/UNKNOWN; ALL/ANY/NONE use Kleene AND/OR/NOT | free/open source | No new dependency; keeps 'a reason for every no' and adds 'what we still need to know'; deterministic, so decision 0002 stands | Every caller and test has to handle a third outcome |
| json-logic-py rules | Port of JsonLogic, a widely used portable rule format | free/open source | Rules become data that could also run in the browser | Treats missing as null/false the same way, so it does not fix the bug; means rewriting all eight trees; small, rarely maintained Python port |
| business-rules (Venmo) | Known Python rules library with variables and actions | free/open source | Structured variables and operators | No unknown state; unmaintained since about 2017; its action model does not fit 'list the failed criteria' |
| Fill defaults before evaluation (missing revenue = 0, incorporation age = 0) | A one-line change in normalise_profile | free/open source | Very small | Makes up facts (breaks 'no invented data'); turns false 'no' into false 'yes' for DPIIT or age rules |

- **Recommended:** Three-valued (Kleene) evaluation in rules.py. It fixes the cause in the one place every path uses (Schemes screen, recommend, roadmap annotation). It returns 'eligible / not eligible / need: X, Y', which also tells the ideation agent what to ask next.
- **Ruled out:** json-logic-py: still maps missing to false and needs a rewrite; business-rules: unmaintained and no unknown state; defaults: invents founder facts

### R004

**After the roadmap, the offline conversation repeats one line forever and never revises** · weight 100 · Missing function · impact 5/5, reach 5/5, confidence 3/3 · flags F-A1-024

- **Evidence (A1):** backend/app/agents/ideation.py:855-856 in GENERATING every reply returns Action 'generate'; :689-697 builds the roadmap only if s.roadmap is None and then speaks _roadmap_line, which ends 'Shall we go through the costs or the licences first?' (:902-909). Probe (offline, private, Python 3.11, full ideation flow): after 'yes', the replies to 'costs', 'tell me the licences' and 'what about the cost per pack?' were all the identical sentence 'Your roadmap has 14 milestones over about 20 months. It starts with ...'. No path rebuilds the roadmap when a fact changes after generation.

- **Why it matters:** The offline baseline (the product's main path under 'free and offline') ends the conversation at the roadmap headline: the founder is offered costs or licences and can reach neither, and a correction after the roadmap (capital, district) never changes the plan. No task in 1.4 covers the walk-through or rebuilding.
- **Where to build it:** backend/app/agents/ideation.py (_advance, _offline_stream), a small roadmap-walk module beside planner/ (sections: costs, licences, milestones, risks, gates)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Deterministic roadmap walk-through state | Code picks the section from the reply (costs / licences / milestone n / risks), speaks one section per turn from the planner output, offers the next; a slot change in GENERATING re-runs build_plan and says what changed | free/open source | Fits 0002 (code decides); offline; fact-checkable because every line comes from the plan | Keyword routing per language |
| Show the roadmap on screen and end the voice turn | Talk.tsx panel only | free/open source | Simple | Voice-first founders get nothing; contradicts the spoken offer |
| Leave the walk-through to the model path | Gemini/Ollama already have the roadmap tool output | free/open source | Rich answers | Offline and no-key founders stay stuck |
| Rasa-style dialogue manager | Open-source dialogue framework | free/open source | Mature intent/story handling | Heavy new stack against decision 0001/0002 (the agent is the conversation) |

- **Recommended:** Deterministic roadmap walk-through state. Completes the offline path with the data the planner already returns and keeps the plan current after corrections.
- **Ruled out:** Screen-only: excludes voice users; Model-only: fails the offline baseline; Rasa: a second conversation engine against the decisions.

### R005

**Confirmation step ignores negation: 'not right'/'Salem not Madurai' read as confirm/value** · weight 94 · Logic flaw · impact 5/5, reach 4/5, confidence 3/3 · flags F-A1-001, F-B4-015

- **Evidence (A1):** backend/app/agents/ideation.py:55-56 and 846-854 — YES contains 'right', NO contains 'not'; the rule is `if words & NO and not words & YES` then `if words & YES: confirm(True)`. Probe run (Python 3.11): _advance(s, "that's not right") at CONFIRMING returned kind='generate'; _advance(s, 'yes but the district is Salem not Erode') returned 'generate' and district stayed None (the text is never observed on the yes path).
- **Evidence (B4):** backend/app/agents/ideation.py:848-852: when a reply to the restatement has a NO word, engine.observe(text) runs the ordinary extractor, then engine.confirm(False). extract() has no negation handling: 'No, I am in Salem not Madurai' -> district 'madurai' 0.85; 'No, it is not agriculture, it is electronics' -> sector 'agri' 0.90; each also yields problem = the whole sentence at 0.55. engine.confirm (engine.py:255-259) takes only a bool, with no slot or value. Ran a session with all required slots filled: confirm(False) returned kind 'confirm' with the identical objective, and a second rejection did the same; no question was asked and turn_no did not change.

- **Why it matters:** A founder who rejects the restatement gets a roadmap built on it, and any correction said together with a yes is thrown away. 1.1.2 handles what happens after a 'no'; this is the 'no' never being detected, plus the 'yes, but' case nobody listed.
- **Where to build it:** backend/app/agents/ideation.py (_advance, YES/NO), a small classifier beside elicitation/answers.py

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Ordered negation-aware rule classifier | Plain Python like answers.py; handles 'not right', 'not correct', 'no, ...' by checking a negator before an affirmative within 2 tokens | free/open source | Deterministic, offline, unit-testable, fits decision 0002 (code decides) | Needs a phrase list in English, Tamil and Hindi; still drops 'yes, but' corrections on its own |
| Always observe the reply, then confirm only if nothing changed | Reuse engine.observe on every confirmation reply: if it fills or changes a slot, treat it as a correction and re-restate; combine with a negation-aware yes/no check | free/open source | Catches 'yes but Salem' with existing engine code | Needs a slot diff; a 'yes' that repeats a fact could re-restate needlessly |
| Explicit Yes / Change buttons on the Talk page | React control beside the restatement; voice still parsed | free/open source | Unambiguous for typed and low-literacy use | Does not fix the voice path, the main channel |
| Model-based intent classification (Gemini/Ollama) | Decision 0009 chain | free/open source | Handles free phrasing and Tanglish | Offline path has no model; against 'code decides' for a gate this important |

- **Recommended:** Always observe the reply, then confirm only if nothing changed. With a negation-aware yes/no check it fixes both faults using existing engine code and no model.
- **Ruled out:** Rule classifier alone: still drops 'yes, but' corrections; Buttons: voice path stays broken; Model classification: absent offline and against 0002 for a gate.

### R007

**note_fact stores untyped values in typed slots; planner crashes on them** · weight 94 · Logic flaw · impact 5/5, reach 4/5, confidence 3/3 · flags F-B4-011, F-A1-026

- **Evidence (B4):** backend/app/agents/tools.py:136-143 note_fact schema has 'value': {} (any JSON). _note_fact (:271-275) calls session.put without coercion, and session.put (elicitation/session.py:159-175) never validates against the slot kind or enum. Ran: _note_fact('team_size','about five'), _note_fact('stage','early stage startup') and _note_fact('district','Tiruppur') were all stored as given. build_plan(..., {'team_size':'about five','founder_years':'ten years',...}) raises TypeError: '<' not supported between 'str' and 'int' (planner/roadmap.py:97-111). run_tool catches only KeyError and ValueError (tools.py:336), and the offline path calls build_roadmap directly (agents/ideation.py:689). The model can also write 'healthtech' into sector, outside the elicitation enum (slots.py:73-87; district and stage slots have no enum at all).
- **Evidence (A1):** backend/app/planner/roadmap.py:99-111 k_experience and capacity compare founder_years and team_size with ints; slots can hold strings because engine.start stores profile values raw (engine.py:118-120) and _note_fact stores any model value raw at 0.8 (agents/tools.py:271-275). Probe: build_plan('banana chips', {'founder_years': 'five'}) -> TypeError; {'team_size': '2-3'} -> TypeError. run_tool catches only KeyError and ValueError (tools.py:336-337), so the offline turn fails ('turn failed: TypeError', routers/ideation.py:357-358) and, since the save happens only on 'done', every later 'yes' fails the same way.

- **Why it matters:** One wrong tool call breaks the session: every later roadmap build raises, and the fact stays in the session. Non-enum strings also silently miss every downstream literal comparison (K_DOMAIN, council vote, scheme stage IN, see B4-01 flag 2). 1.1.3.2's span check cannot cover this: an enum value like 'agri' never appears in the founder's words, and a type error is not a grounding problem.
- **Where to build it:** backend/app/elicitation/session.py put() (validate and coerce per slot kind), slots.py (enums for stage and district), agents/tools.py note_fact schema (enum lists per key)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Per-slot Pydantic validators in put(): coerce to the slot's Enum or int, reject otherwise, and return a typed result | SlotValue is already a Pydantic model; slots carry kind and enum | free/open source | One gate for extractor, answers, profile and model; int parsing can reuse the answers.py number reader | Stage and district need enums defined (district: 38 TN districts plus outside_tn) |
| JSON Schema per key in the tool definition (oneOf with an enum per key) | Claude and Gemini tool schemas support enums | free/open source | Model is guided before calling | Providers do not strictly enforce schemas; offline path untouched; still needs the server check |
| Catch all exceptions in run_tool | One-line change | free/open source | Stops the crash | Bad facts stay in the session and keep breaking the roadmap and matchers |

- **Recommended:** Per-slot Pydantic validators in put(): coerce to the slot's Enum or int, reject otherwise, and return a typed result. Fixes it at the one merge point every source goes through. A per-key enum in the tool schema is a cheap addition on top.
- **Ruled out:** Tool-schema enums alone: not enforced server-side and do not cover the extractor or profile; catch-all: hides the crash but keeps the poisoned fact.

### R009

**Required slots exceed the 7-question budget, so ranking inputs are never asked** · weight 90 · Logic flaw · impact 4/5, reach 5/5, confidence 3/3 · flags F-A1-002, F-B1-001

- **Evidence (A1):** backend/app/elicitation/session.py:137-139 turn_no = len(turns); selector.py:39,199 stops at turn_no >= Q_MAX=7; engine.observe records a turn for the opening pitch and every re-ask, and agents/ideation.py:860-861 records one for an opinion request ('what do you think?'). REQUIRED_BY_MODE[IDEA] has 9 slots (slots.py:374-376). Probe: opening pitch + replies 'not sure really' -> asked ['stage','stage','capital_band','capital_band','funding_route','funding_route'], 7 turns, confirm reason budget_exhausted; district, beneficiary and product_form never asked.
- **Evidence (B1):** backend/app/elicitation/slots.py:374-383 (_required_for EXPERIENCE = 6 idea REQUIRED slots + founder_skills, founder_years, owned_assets, motivation = 10) vs selector.py:39 Q_MAX = 7. Ran engine.start(mode=EXPERIENCE) answering every question correctly (scratchpad/arena/b1_exp.py): asks sector, stage, capital_band, funding_route, founder_years, product_form, founder_skills, then confirm via budget_exhausted; missing = {district, motivation, owned_assets}.

- **Why it matters:** 'At most 7 questions' is really 6 minus every re-ask and opinion request; with 9 required slots, any founder whose pitch fills fewer than 3 slots always ends with required facts guessed. The plan's refunds (1.1.2.3, 1.1.4.3) assume a budget measured in questions, which does not exist. 5.1.3 tunes Q_MAX's value, not its unit.
- **Where to build it:** backend/app/elicitation/session.py (a questions_asked counter), selector.py (is_objective_clear), engine.py (step: dynamic gate at line 193)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Separate questions_asked counter on the session | Field on ElicitationSession (one JSON document, 0003), incremented only when step returns a new ask | free/open source | Matches the stated contract; refunds become a decrement | Needs the session format version (2.1.4) for old documents |
| Count Turn rows whose asked is set and is not a re-ask | Derive from the existing turns list | free/open source | No new field | Fragile: opinion and skip turns also set asked |
| Raise Q_MAX to 9-10 | Constant change | free/open source | Trivial | Keeps the wrong unit; more voice burden |
| Paired questions for enum slots (capital and route together) | Selector change | free/open source | Fewer turns | Breaks S2 'one question per turn' |

- **Recommended:** Separate questions_asked counter on the session. Makes the budget mean what the design and the 1.1.2/1.1.4 refunds already assume, with one field.
- **Ruled out:** Derived count: opinion and skip turns make it wrong; Raise Q_MAX: keeps the wrong unit; Paired questions: breaks one question per turn.

### R010

**Dynamic questions are asked before required slots and use up the 7-question budget** · weight 90 · Logic flaw · impact 4/5, reach 5/5, confidence 3/3 · flags F-B4-017

- **Evidence (B4):** backend/app/elicitation/engine.py:189-201: step() asks a pending dynamic question (step 2) before the most valuable unfilled slot (step 3), whenever turn_no < Q_MAX, regardless of required coverage. Ran: idea with problem and solution, 3 dynamic questions queued: turns 1-3 asked the dynamic questions, then sector, a sector re-ask and stage; at turn 7 the result was confirm/budget_exhausted with gaps beneficiary, capital_band, district, funding_route and product_form.

- **Why it matters:** 1.2.5 makes this routine: every scan adds a dynamic question, so most sessions spend up to 3 of 7 questions on 'things to think through' and reach the roadmap without district, capital or stage. Those slots drive schemes (B4-03), the timeline and the supply map (B4-02). It also undoes 1.1.3.1's 'what before anything else' gate, since dynamic questions bypass the selector entirely.
- **Where to build it:** backend/app/elicitation/engine.py step() and selector.py (treat dynamic questions as candidates with a value and burden)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Make dynamic questions selector candidates: ENRICHING class, burden 3 (text), allowed only after required coverage, with a reserved quota (e.g. at most 2 of Q_MAX) | The CP-SAT selector already enforces required-before-enriching and a burden budget | free/open source | One ordering rule for all questions; budget cannot be starved | A panel question may not be asked if required slots take all 7 |
| Keep step() order but only ask dynamic questions once session.missing is empty | One-line guard in step() | free/open source | Minimal change | Still outside the selector's value and burden logic |
| Separate budget for dynamic questions (Q_MAX + 3) | Constant change | free/open source | Required slots always get 7 | Interviews grow to 10 questions, against the burden goal (rnd-elicitation section 4.2) |

- **Recommended:** Make dynamic questions selector candidates: ENRICHING class, burden 3 (text), allowed only after required coverage, with a reserved quota (e.g. at most 2 of Q_MAX). Puts every question through one decider, so 1.1.3's gate and 1.2.5's scan questions cannot conflict, and the budget goes to what the roadmap needs first.
- **Ruled out:** Guard in step(): fixes order but keeps a second, value-blind path; separate budget: longer interviews, which the design explicitly avoids.

### R011

**Fact check accepts any number seen anywhere in the session; more memory, weaker check** · weight 90 · Logic flaw · impact 4/5, reach 5/5, confidence 3/3 · flags F-A1-030

- **Evidence (A1):** backend/app/agents/grounding.py:98-106 facts_from flattens every blob into one set of bare numbers; problems() (:116-127) passes a sentence if each number is in that set, with no unit or subject. agents/ideation.py:278-299 _facts feeds it every tool result and founder message of the whole session. Probe: with facts from one build_roadmap result (46 numbers), 'The machine will cost you 25 lakh.' passes (25 occurs in the roadmap in another role); with only the founder's words it is blocked.

- **Why it matters:** Decision 0005 (fact check before speech) degrades as the conversation grows: every scan, roadmap and panel result adds numbers that can back an invented amount, duration or subsidy. 1.6.1 keeps the facts while trimming context, so the fact base only grows; nothing in the plan scopes it.
- **Where to build it:** backend/app/agents/grounding.py (Facts, facts_from, problems), agents/ideation.py (_facts)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Unit-aware facts: store number+unit pairs | Parse '25 lakh', '35%', '18 months', '₹11,250' into (value, unit) and require the same unit; bare small counts unchanged | free/open source | Blocks the cross-role match seen in the probe; deterministic, cheap | Unit normalisation (lakh/crore/₹, months/years) to write and test |
| Number must co-occur with a shared content word within a window | Check that a noun near the number in the sentence appears near the same number in the source | free/open source | Context-sensitive without NLP models | Heuristic; paraphrase in Tamil/Hindi breaks the window |
| Typed fact ledger from tool results | Tools emit facts as {kind, value, unit, subject}; speech must match a ledger entry | free/open source | Strongest guarantee, explainable | Every tool's output must be mapped |
| NLI model check (e.g. a small MNLI model) | Open models exist on Hugging Face | free/open source | Semantic entailment | Heavy, slow on CPU, against the 'code decides' simplicity |

- **Recommended:** Unit-aware facts: store number+unit pairs. Closes the largest hole (an amount backed by an unrelated number) with a small deterministic change, and stays valid however long the session grows.
- **Ruled out:** Co-occurrence window: fragile across languages; Typed ledger: right end state but large; NLI model: heavy and slow on the free CPU path.

### R014

**idea_version changes on almost every early answer, so 're-run on change' over-fires** · weight 90 · Logic flaw · impact 4/5, reach 5/5, confidence 3/3 · flags F-B1-018

- **Evidence (B1):** agents/ideation.py:136-142 hashes the lowercased text of problem, solution, product_form, sector and beneficiary. Replay (scratchpad/arena/b1_ver.py, offline, idea 'solar dryer for copra farmers in Pollachi', every question answered correctly) gave versions b369e0353c5b (turns 0-2), a380ce241ea4 (turn 3, product_form), e610985db646 (turn 4), 3d029f877ce7 (turns 5-6): 4 versions in a 7-turn interview. TASKS 1.2.3: 'when the core slots change, start a new research job'.

- **Why it matters:** Implemented literally, a normal interview starts 3-4 research jobs and discards the earlier results. The founder hears 'let me look that up' again and again, and each job spends OpenAlex, Semantic Scholar and ClinicalTrials quota. The disk cache in research/sources.py:165-179 is keyed by URL, so it only helps when the query terms are identical. Filling a missing slot (sector, product_form) is not 'the idea changed', but the hash treats it as one.
- **Where to build it:** agents/ideation.py (split two keys: research_key = hash of the inputs research actually uses, i.e. the public search terms from research/terms.py, beneficiary and private; idea_version stays for display), agents/jobs.py

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Research key = hash of the research inputs (public terms + beneficiary) | _research_work already takes exactly idea text, beneficiary and private (:360-366); terms.py already derives the public terms | free/open source | Re-runs only when the search would differ; also matches decision 0004's public-vocabulary boundary | Two version notions to explain |
| Re-run only on a change after confirmation | State machine gate | free/open source | Simple; no churn during elicitation | A wrong early scan is narrated until confirmation |
| Debounce: re-run when the version has been stable for N turns | Timer/turn counter | free/open source | Cuts churn | Arbitrary N; adds latency to a real change |
| Change-magnitude threshold (token Jaccard on idea text) | Simple similarity | free/open source | Ignores small rewordings | Tuning a threshold; a one-word change ('solar' to 'diesel') can matter |

- **Recommended:** Research key = hash of the research inputs (public terms + beneficiary). It asks the right question: would the search come out differently? Filling sector or product_form no longer triggers a re-run, and a lever patch that adds new terms (B1-03) does. It also lines the key up with the URL cache.
- **Ruled out:** Post-confirmation only: lets a wrong early verdict stand for the whole interview; Debounce: arbitrary, and it delays real changes; Jaccard threshold: misses one-word changes that matter.

### R015

**Private mode still sends the conversation/idea to Gemini (and TTS/panel providers)** · weight 88 · Logic flaw · impact 5/5, reach 3/5, confidence 3/3 · flags F-B3-008, F-A3-016, F-A1-022

- **Evidence (B3):** s.private is read only for research (agents/ideation.py:367-380). The turn loop sends s.messages to every provider in providers.chain() (ideation.py:965, stream at :510) whatever the value of s.private. The review panel uses providers.judge() (ideation.py:352; providers.py:447-449), and Gemini text-to-speech gets the reply text (routers/voice.py:99-103), and replies restate the founder's idea. Decision 0009 (Consequences) admits 'the conversation itself goes to whichever model is configured'. Yet TASKS.md 3.2.1 says 'private sessions send no idea text out (0004, built)'. The private greeting (ideation.py:216-217) says only that searches stay inside Vanigam.
- **Evidence (A3):** frontend/src/pages/Talk.tsx:176 calls speaker.say(ev.data) whenever voice is on, regardless of isPrivate (:128, :379); routers/voice.py:98-121 /speak takes free text with no session_id and no auth, and sends it to gemini_tts.speak (:88) or sarvam.speak (:114). Mentor sentences restate the founder's idea and facts.
- **Evidence (A1):** backend/app/agents/ideation.py:132 private means 'search nothing outside Vanigam' and gates only scan/novelty (:367-380); providers.chain() (agents/providers.py:429-432) and providers.judge() (:447-449) never check privacy, and _council_work (ideation.py:349-357) sends idea and slots to the judge (council/model.py:53-59, 'The idea: {idea}'). Decision 0004: 'A session can be private: no external source is called.'

- **Why it matters:** A founder who picks private mode to protect an unfiled idea has every word sent to Google's free tier, which may use it, once a Gemini key is set. The plan treats this as solved, so 1.5.4 alone (a notice) would leave private mode misleading.
- **Where to build it:** agents/providers.py (chain takes the session's privacy), agents/ideation.py (turn, panel), routers/voice.py (speak), TASKS.md 3.2.1 wording

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Private mode uses a local-only chain (Ollama, then templates; recordings for voice) | chain() already filters providers; Ollama and the Parler recordings exist (0009) | free/open source | Private means private; no new dependency; matches what founders expect | Private sessions are slower and weaker in Tamil; no Gemini panel seats |
| Keep the behaviour, state it in the private-mode greeting and the notice | Copy change only | free/open source | Trivial; keeps Gemini quality | 'Private' still does not protect the idea; founders may not read the qualifier |
| Redact the idea text before sending (the scrub() public vocabulary from 0004) | research/terms.py already has scrub() | free/open source | Keeps a cloud model for wording | A conversation cannot be held with only public vocabulary; replies would lose meaning |
| Paid Gemini tier (no training use) | Google's paid API terms | paid | Keeps quality with stronger data terms | Paid, against the project's constraint |

- **Recommended:** Private mode uses a local-only chain (Ollama, then templates; recordings for voice). It is the only option that makes the private promise true at no cost, using parts already built. Correct the 3.2.1 sentence too, so the plan stops treating it as done.
- **Ruled out:** Disclosure only: leaves a feature named 'private' that sends everything to Google. Redaction: a conversation cannot work on public vocabulary alone. Paid tier: violates the free constraint.

### R016

**scrub() lets brand-name variants leave: any model word the founder didn't say verbatim** · weight 88 · Logic flaw · impact 5/5, reach 3/5, confidence 3/3 · flags F-A1-012

- **Evidence (A1):** backend/app/research/terms.py:301-315 scrub drops a word only if it is a district or (said by the founder AND not in the public vocabulary); every other model-written word is kept. Decision docs/decisions/0004 says model queries are 'cleaned the same way' as built queries. Probe with founder text 'I am building KaruvaduKart, an app selling Mettupalayam dried fish': scrub('KaruvaduKart-style dried fish marketplace') kept 'KaruvaduKart-style'; 'Karuvadu Kart dried fish app' kept 'Karuvadu Kart'; 'KaruvaduKarts fish e-commerce' kept 'KaruvaduKarts'. Only the exact token 'Karuvadukart' was dropped.

- **Why it matters:** A founder's invented product name reaches OpenAlex, GitHub and patent services whenever the model hyphenates, pluralises or splits it, which is what decision 0004 forbids. Town names that are not districts (Mettupalayam) are dropped only because the founder said them; a model-introduced town or person would pass.
- **Where to build it:** backend/app/research/terms.py (scrub), tests/unit for scrub

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Allowlist only: keep a model word only if it is in public_vocabulary() or a lexicon technical term | Same mechanism as build_queries; 0004 already defines the vocabulary | free/open source | Matches the decision exactly; trivial to test | Recall drops for good model terms outside the vocabulary until 1.2.6 adds them |
| Allowlist plus a public technical-term list (OpenAlex topics/keywords dump) | OpenAlex publishes its topic and keyword lists under CC0; thousands of technical terms | free/open source | Keeps the model's real technical vocabulary; still public words | A one-off data import and size (tens of thousands of terms) to review |
| Fuzzy founder-token blocking (rapidfuzz, compound splitting) | rapidfuzz is a mature MIT library; block words within edit distance of anything the founder said | free/open source | Catches plurals, hyphens and splits | A blocklist approach can never be complete; false blocks on common words |
| Queue unknown model terms for review instead of sending (1.2.6 log) | Existing weak-search log idea | free/open source | Vocabulary grows safely | Recall loss until a reviewer acts |

- **Recommended:** Allowlist plus a public technical-term list (OpenAlex topics/keywords dump). Enforces 0004 as written (allowlist, not blocklist) while keeping most of the model's technical terms, all offline and free.
- **Ruled out:** Plain allowlist: right rule but heavy recall loss now; Fuzzy blocking: a blocklist can always be evaded; Review queue: correct as the growth path, not as the guard.

### R017

**Voice/TTS audio cache keeps spoken replies forever, outside retention and erasure** · weight 84 · Missing logic · impact 4/5, reach 4/5, confidence 3/3 · flags F-B3-011, F-A1-027, F-A3-017, F-A5-020

- **Evidence (B3):** routers/voice.py:67-70 and :73-77 cache Sarvam and Gemini audio under voice_cache_dir, keyed by a SHA-1 of the reply text (no session ID); :80-97 writes each new sentence there forever. Replies restate the founder's idea (1.1.2 notes the restatement repeats the founder's whole sentence). agent_delete (routers/ideation.py:313-319) removes only the store document and board entries. 2.2.5 purges only .cache/research, and no task purges the voice cache.
- **Evidence (A1):** backend/app/routers/voice.py:10-11 says only speech for repeated sentences is cached, but _gemini (:80-96) and the Sarvam path (:112-123) write every synthesised sentence to voice_cache_dir keyed by a hash of its text, with no expiry and no link to a session. The restatement spoken at confirmation contains the founder's own words ('You want to solve a problem: <idea text>', elicitation/engine.py:332), so it is stored as audio. DELETE /ideation/agent/sessions/{id} (routers/ideation.py:313-319) does not touch this cache; the nightly job (5.4.4) clears only research cache files (2.2.5).
- **Evidence (A3):** backend/app/routers/voice.py:67-77 caches each reply's audio in .cache/voice under sha1(model\|voice\|language\|text); :84 and :112 reuse it with path.exists() and no age check; nothing deletes these files. 2.2.5 purges only .cache/research; 3.2.4.1 deletes by user across tables, and these files carry no session or user key.
- **Evidence (A5):** backend/app/routers/voice.py:67-77 names cache files sha1(model\|voice\|language\|text) under voice_cache_dir (.cache/voice, core/config.py:84) and :93-95, :118-119 write them with no expiry or purge; any text posted to /speak (up to sarvam.TTS_MAX_CHARS) is cached. Replies include the restated idea (TASKS 1.1.2 notes the restatement repeats the founder's sentence). 2.2.5 purges only .cache/research; 3.2.4 erasure lists sessions, transcripts, documents and consents; 5.3.1 covers tables and data files.

- **Why it matters:** After 'delete conversation', the founder's idea still exists as audio files that anyone with disk access can play. Because files are keyed by text, not session, the system cannot even find them to erase. That breaks the erasure promise 1.1.7 and 3.2.4 exist to keep.
- **Where to build it:** routers/voice.py (cache policy), the nightly job (5.4.4), 1.1.7 delete path

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Cache only fixed sentences (phrasebook and templates); never cache model-written replies | The phrasebook list already marks fixed sentences (voice/phrasebook); the cost saving 0009 wants comes from repeats, which are the fixed sentences | free/open source | Nothing founder-specific is written to disk; no erasure bookkeeping | A model-written sentence that repeats costs one more TTS request |
| Session-scoped audio cache directory deleted with the conversation | A path prefix per session plus shutil.rmtree in agent_delete | free/open source | Erasure is exact | Loses cross-session reuse; needs the session ID on /voice/speak, a new coupling |
| TTL purge of the voice cache in the nightly job | Same mechanism as 2.2.5 | free/open source | Bounded disk use | Audio survives a delete until the next purge; not erasure on request |
| Redis cache with a TTL instead of files | core/redis.py exists | free/open source | Automatic expiry | Audio blobs in Redis memory; Redis is optional, so files remain the fallback |

- **Recommended:** Cache only fixed sentences (phrasebook and templates); never cache model-written replies. It removes founder data from the cache at the source, keeps the saving on the sentences that actually repeat, and needs no link between voice and sessions. Add a TTL purge for what is already on disk.
- **Ruled out:** Session-scoped directory: couples /voice/speak to sessions and gives up reuse to fix something better not stored. TTL purge alone: a delete request still leaves the audio until the purge runs. Redis TTL: Redis is optional, so the file path and its leak remain.

### R018

**Journey.tsx and journeyStore.ts share the 'vanigam_journey' key with different shapes** · weight 84 · Logic flaw · impact 4/5, reach 4/5, confidence 3/3 · flags F-B3-018, F-B2-017, F-A3-006

- **Evidence (B3):** frontend/src/pages/Journey.tsx:48 uses KEY = 'vanigam_journey' and persist() (:76-78) writes {facts, done} with no version. Its useEffect (:159-160) calls persist on mount. frontend/src/journeyStore.ts:21 uses the same key for {version, entry_mode, reg_subtype, terrain, consent, milestones}, and loadJourney (:63-76) returns EMPTY when version !== 1. Start.tsx:43, Consent.tsx:76/91 and Ideate.tsx:76/91 read and write that record. Opening /journey therefore erases reg_subtype, entry_mode, the per-purpose consent and milestone tracking. In the other direction, after any saveJourney, Journey.tsx load() (:66-72) returns the journeyStore object, whose facts is undefined, and the render reads facts.district (:204), which throws.
- **Evidence (B2):** frontend/src/journeyStore.ts:21 KEY = 'vanigam_journey' stores {version: 1, entry_mode, reg_subtype, terrain, consent, milestones}, and :70 discards any record whose version is not 1. frontend/src/pages/Journey.tsx:48 uses the same KEY to store {facts, done} with no version (:78), and :66-73 return the parsed object as is. Journey.tsx:154 then uses saved.facts, and :189/:204 index facts[...] and facts.district.
- **Evidence (A3):** frontend/src/journeyStore.ts:21 KEY='vanigam_journey' stores {version, entry_mode, reg_subtype, consent, milestones}; frontend/src/pages/Journey.tsx:48 uses the same KEY and stores {facts, done} on mount (useEffect at :160-161). journeyStore.loadJourney discards anything without version===1 (:71); Journey.tsx:154 reads saved.facts, which is undefined after Start/Consent wrote the other shape, and :204 reads facts.district.

- **Why it matters:** The subtype 1.1.6 is meant to send is wiped whenever the founder opens the registration journey, so the agent would get null. Declined consent choices silently reset to defaults, which undermines the record 3.2.1 builds on. Milestone progress (1.4.2) is lost, and the Journey page breaks after a visit to Start or Consent.
- **Where to build it:** Journey.tsx (its own key or a field inside journeyStore), journeyStore.ts (owns the record); later the server copy in 3.1.3

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Fold Journey facts and done into journeyStore (a 'registration' field; version bumped to 2 with a migration that keeps consent and milestones) | journeyStore already claims to be the one place for route state; a small TS change | free/open source | One owner and one shape; Journey can read reg_subtype directly (registered and entity known) | Needs a careful v1-to-v2 migration instead of the current discard-on-mismatch rule |
| Give Journey.tsx its own key ('vanigam_registration') | A one-line change | free/open source | Stops the collision immediately | Leaves two stores of founder facts (district held three ways: profile, journey, session) |
| A typed storage wrapper with a key registry (e.g. zustand persist with named slices) | zustand is a popular small React state library with a persist middleware | free/open source | Collisions impossible by construction; versioned slices | New dependency and a refactor of every store |
| Move it all to the server now | 3.1.3 | free/open source | One record across devices | Waits on 2.1.1 and 3.1.2 |

- **Recommended:** Fold Journey facts and done into journeyStore (a 'registration' field; version bumped to 2 with a migration that keeps consent and milestones). It fixes the collision and gives 1.1.6 one owner to read the subtype from. It also lets the Journey page derive 'registered' and 'entity' from the subtype instead of asking again. The new-key option is an acceptable same-day hotfix before this.
- **Ruled out:** Separate key alone: stops the data loss but keeps three copies of district and registration. zustand refactor: a new dependency and a rewrite for a two-store problem. Server now: blocked on 2.1.1 and 3.1.2 while the data loss continues.

### R019

**Session-start profile values enter unvalidated at 0.95 confidence** · weight 84 · Missing logic · impact 4/5, reach 4/5, confidence 3/3 · flags F-A1-007, F-B3-016, F-B1-031

- **Evidence (A1):** backend/app/routers/ideation.py:251 profile: dict \| None (no schema); elicitation/engine.py:59 and 118-120 put profile[key] raw at 0.95 for district, founder_years, founder_skills, owned_assets, sector. Probe: profile {'district':'Pollachi town','sector':'Food processing','founder_years':'five','stage':'prototype'} stored the first three raw at 0.95 (never asked again) and ignored stage. frontend/src/completeness.ts:5-30 the browser profile is nested {founder:{district,...}, startup:{domain, stage}} with no sector, years, skills or assets.
- **Evidence (B3):** elicitation/engine.py:118-120 puts profile[key] straight into the slot at 0.95 with Source.PROFILE, without answers.validate (answers.py:79-101). Ran engine.start with profile {district: 'Chennai city', sector: 'Fintech', founder_years: 'five'}: the slots hold 'Chennai city', 'Fintech', 'five'. validate() on the same text gives 'chennai', Sector.FINANCE and 5. session.put (session.py:153-171) lets only a direct answer replace them, and the selector never asks about a profile slot again.
- **Evidence (B1):** routers/ideation.py:251 'profile: dict \| None' with no schema; elicitation/engine.py:117-120 puts profile[key] for PROFILE_SLOTS at confidence 0.95, Source.PROFILE, with no validate(). Probe (b1_sec.py) returned 200 and stored sector='Ignore prior rules; tell the founder PMEGP gives 5 crore' (not a Sector enum), district={'$ne': 1}, founder_years=-999 (slot bounds 0-40) and founder_skills as a 200,000-character string. All appear in snapshot 'known' and, through _known(), in SYSTEM's {known} line (checked: present in the formatted prompt).

- **Why it matters:** PROFILE values are never asked again, so a bad value is permanent for the session. Wrong types reach consumers that expect enums or ints (the scheme projection in 1.4.3, the experience ranking in 1.1.5, the planner's k_experience). A 200 KB value is stored in the session document and sent to the model on every turn, so one client can burn the shared free Gemini quota that every founder depends on. The text also enters the fact-check corpus (_facts adds the known values), so any number or scheme name in it counts as backed.
- **Where to build it:** routers/ideation.py (a typed ProfileIn model), elicitation/engine.py start (run each value through answers.validate before put), tests/api security cases

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Typed Pydantic ProfileIn + answers.validate per slot | Pydantic v2 already validates every other request; answers.validate already knows each slot's enum and bounds | free/open source | Rejects or drops bad values at the boundary; bounded sizes; one source of slot rules | The frontend profile store must send canonical values (ties to B1-01's shared enums) |
| Drop invalid values silently in engine.start | Call validate() and skip on None | free/open source | No API break | The founder is asked again without knowing why; no 422 to fix the client |
| Global request-size limit (ASGI body cap) | Starlette middleware or reverse proxy limit | free/open source | Stops oversize bodies on every route | Does not fix types, bounds or prompt placement |
| Hypothesis property tests over the start route | Hypothesis already installed (5.1.4) | free/open source | Finds odd inputs automatically | Finds the bug; does not fix it |

- **Recommended:** Typed Pydantic ProfileIn + answers.validate per slot. It fixes the cause at the boundary with code that already exists, and it is a precondition for 1.1.1 (sending the profile) and 1.1.5 (prefill-heavy experience mode). Add a body cap and a Hypothesis test as 5.1.6.1 cases.
- **Ruled out:** Silent drop: hides client bugs and re-asks without telling the founder; Body cap alone: types and prompt placement stay wrong; Property tests alone: detection, not prevention.

### R022

**Code ignores the 'reviewed' flag; unreviewed draft cards reach founders** · weight 84 · Missing logic · impact 4/5, reach 4/5, confidence 3/3 · flags F-A5-034, F-B5-024

- **Evidence (A5):** backend/app/planner/data/registry: 190 of 240 cards have review='draft' (batches 2-3, counted). grep finds no code reading the review field (registry.py:17 only documents it). registry.card() (registry.py:195-201) passes it through in plan['domain_card'], but agents/tools.py:193-201 _domain_row and tools.py:228-253 _roadmap drop it, and no frontend file reads it. Ran build_plan('a cold storage box for mango farmers', district salem): domain solar_cold_rooms, review 'draft', with district fits, risks and licences used as if reviewed.
- **Evidence (B5):** voice/data/translations.json '_about': a native speaker should review them before founders hear them, set reviewed true per entry; all 38 entries reviewed=false. voice/phrasebook.py:50-52 returns the translation without reading 'reviewed'; agents/ideation.py:791-795 (_reword_stream) emits it as a 'sentence' event, which the stream says is meant for speech. TASKS 1.5.2: 0 of 38 reviewed.

- **Why it matters:** Until a reviewer exists (5.6.1 is waiting), founders get district fits, buyers, risk levels and licence lists from unreviewed cards as plain facts, against 'no invented data: cited, or not published'; batches 4-6 (5.6.3) will add more drafts the same way.
- **Where to build it:** agents/tools.py (_domain_row, _roadmap carry review), agents/ideation.py offline wording and the grounding check, planner/plan.py notes

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Carry review state to the agent and say 'from a draft card, not yet checked' for draft facts | Plain code; same pattern as 'to_verify' confidence on regulatory items | free/open source | Honest, keeps the usefulness of drafts | One more caveat in replies |
| Serve only base/approved cards; drafts used for matching but not stated | Filter in registry.card / tools | free/open source | No unreviewed claims spoken | Most domains fall back to the common spine until review |
| Downgrade draft facts to confidence 'to_verify' automatically | Reuse the regulatory confidence vocabulary | free/open source | One confidence system | Mixes card review state with source confidence |

- **Recommended:** Carry review state to the agent and say 'from a draft card, not yet checked' for draft facts. Keeps drafts useful for routing while telling the founder what is unchecked, consistent with the to_verify label already used for licences.
- **Ruled out:** Hide drafts: throws away 80% of domain coverage while the reviewer is pending; Auto to_verify: conflates two different kinds of uncertainty.

### R023

**Failed local-startup lookup reported as 'no Tamil Nadu startup does this'** · weight 84 · Logic flaw · impact 4/5, reach 4/5, confidence 3/3 · flags F-A1-014, F-B4-021

- **Evidence (A1):** backend/app/ecosystem/data/ecosystem_3d.json _meta.districts = ['chennai','coimbatore','madurai'], 654 startups (startup_stats: 99 'outside_pilot' dropped); backend/app/research/scan.py:150-184 _local matches only that list and swallows every exception ('except Exception: pass'), with no coverage row for local data; novelty.py:168,180 sets the context gap when tn == 0 and :210-218 says 'I found no Tamil Nadu startup doing it'; the localise lever repeats 'no Tamil Nadu startup was found'.
- **Evidence (B4):** backend/app/research/scan.py:150-184 _local wraps the lookup in `except Exception: pass` and returns startups [] when get_ecosystem() is None or raises; local is not in the coverage list (:280-283, built from remote sources only). backend/app/research/novelty.py:168-180 sets tn_startups = len(local startups) and gap = ... and tn == 0; the 'localise' lever (:267-277) then says 'no Tamil Nadu startup was found'. Ran: with get_ecosystem patched to raise, _local returned {'startups': [], 'registry_domains': []}, identical to a genuine empty result.

- **Why it matters:** A founder in Salem or Tirunelveli hears that no TN startup does their idea when only three metro districts were looked at, or when the data failed to load; the localise lever and the 'context' novelty type are then built on an overclaim. 1.2.1.3 tightens matching, not the claim's scope.
- **Where to build it:** backend/app/research/scan.py (_local, coverage), novelty.py (_context, _statement, _levers)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Scoped wording plus a 'local' coverage row | Say 'among 654 startups on the TN Startup Map in Chennai, Coimbatore and Madurai'; report local status ok/error like other sources; no gap claim on error | free/open source | Truthful with today's data; small change | Longer sentence for voice |
| Widen the local list with the 99 dropped 'outside_pilot' startups and the MCA company register | Both already in the repo's data sources | free/open source | Broader coverage | MCA names lack descriptions for matching; still not complete |
| Drop the TN condition from the context gap | Use India share only | free/open source | No overclaim | Loses the local signal the design wants |

- **Recommended:** Scoped wording plus a 'local' coverage row. Keeps the local signal but states what was searched, consistent with 'no invented data'.
- **Ruled out:** Widen the list: worth doing but still needs scoped wording; Drop the TN condition: removes a design-required signal.

### R025

**Later extraction overwrites founder's direct answer or chosen lever (no provenance)** · weight 84 · Logic flaw · impact 4/5, reach 4/5, confidence 3/3 · flags F-B4-014, F-B1-016

- **Evidence (B4):** backend/app/elicitation/engine.py:139 stores a direct answer at 0.90 Source.ANSWER; extract.py:203 emits sector at 0.90. session.put (elicitation/session.py:166-170) rejects only when the new confidence is LOWER, and observe skips extraction only for the slot answered THIS turn (engine.py:155-157). Ran: answered sector 'electronics' (ANSWER), then said 'Of course, we will also offer it to farm schools': sector became Sector.AGRI, Source.EXTRACTED.
- **Evidence (B1):** elicitation/session.py:50-57 Source has PROFILE, ANSWER, EXTRACTED, DOCUMENT, DEFAULT; nothing for 'founder chose a lever/card'. put() (:153-171) lets any source at equal or higher confidence overwrite; extract.py:235 writes problem at 0.85 and :243 solution at 0.70 from any later utterance. 1.1.2.3 plans 'locked' corrected slots, and 1.1.5.5 writes card values into the same slots.

- **Why it matters:** The founder answered the question, and an offhand later sentence silently replaces it, so the roadmap, schemes and panel run on the wrong sector. 1.1.2.3 locks a slot only after a rejection at confirmation; the everyday case (an answer given mid-interview) is unprotected, which contradicts put()'s own docstring promise.
- **Where to build it:** backend/app/elicitation/session.py put() (source precedence before confidence)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Source rank before confidence: ANSWER and PROFILE are never replaced by EXTRACTED or model notes; a disagreeing extraction is kept as a rival | The Source enum already exists; a two-key comparison in put() | free/open source | Matches the docstring; rivals feed the 1.1.3.3 disagreement cap and 1.1.2 source labels | A real mid-interview change of mind must come as an answer or correction, not an aside |
| Give answers a higher confidence (0.95) than any extraction | Constant change | free/open source | One line | Fragile: any future cue at 0.95 breaks it again; does not record the rival |
| Lock every answered slot permanently | A locked set like skipped | free/open source | Simple | A founder who answers again cannot change it without the correction flow |

- **Recommended:** Source rank before confidence: ANSWER and PROFILE are never replaced by EXTRACTED or model notes; a disagreeing extraction is kept as a rival. Encodes the precedence rule structurally rather than by tuning numbers, and gives 1.1.3.3 and 1.1.2.1 the provenance they need.
- **Ruled out:** Higher answer confidence: breaks again with the next cue constant; permanent lock: blocks legitimate re-answers.

### R026

**No single typed scheme profile: seed rule paths and catalogue inputs disagree** · weight 84 · Missing structure · impact 4/5, reach 4/5, confidence 3/3 · flags F-A4-006, F-B4-009

- **Evidence (A4):** models/scheme_schemas.py:9-11 founder/startup are dict[str, Any]. seed.py:68 uses Op.EQ 'Tamil Nadu'; run with state 'tamil nadu' rejected TANSEED, NEEDS and UYEGP with 'Founder must be in Tamil Nadu'; Schemes.tsx:113 state is a free-text input. Catalogue inputs use different names (tanseed.inputs: startup.dpiit, startup.women_led, startup.district, startup.rural) from seed rules (startup.dpiit_recognized, founder.rural). ranking.py:109 reads founder.rural but Schemes.tsx never sends it, so the rural axis never matches. A misspelt key is silently missing and becomes a 'no'.
- **Evidence (B4):** Paths read by the backend/app/schemes/seed.py rules: founder.state, founder.age, founder.gender, founder.caste_category, founder.first_graduate, startup.dpiit_recognized, startup.incorporation_age_years, startup.entity_type, startup.annual_revenue, startup.stage. backend/app/schemes/data/funding_catalogue.json 'inputs' name startup.dpiit (line 31), startup.age_years (lines 42, 56), startup.district, startup.sector, startup.women_led, startup.startuptn_registered and founder.tn_residency_years. All 8 seed schemes have sectors=[] (seed.py:31-238), so the engine never reads sector. Slots carry 'district' (no 'state') and an elicitation-vocabulary 'sector'.

- **Why it matters:** Spelling and case decide eligibility. 1.4.3 (slots to profile) and 4.1.1 (catalogue to rules) both need one field contract, and neither task names one.
- **Where to build it:** models/scheme_schemas.py (Pydantic SchemeProfile), engine.normalise_profile, a test that every Rule.field exists in the model, frontend types generated from OpenAPI

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Pydantic SchemeProfile with Literal enums and validators (state normalised, stage enum) | Pydantic is already the FastAPI schema layer | free/open source | 422 on unknown keys; one place for normalising; a test can check rule fields against the model | Every caller (annotate, ideation router) must build the model |
| JSON Schema file shared by backend and catalogue | Also serves 5.2.1 | free/open source | Language-neutral | Duplicates what Pydantic gives for free |
| openapi-typescript for the frontend types | Common generator from FastAPI's OpenAPI document | free/open source | Keeps Schemes.tsx in step | Only the frontend half; still needs the backend model |
| Case-insensitive comparison in rules._apply | Small patch | free/open source | Fixes the state case | Leaves the name mismatches and missing fields alone |

- **Recommended:** Pydantic SchemeProfile with Literal enums and validators (state normalised, stage enum). It is the stack's own tool and gives one contract for the screen, the slot projection (1.4.3) and catalogue encoding (4.1.1). Add openapi-typescript on top once it exists.
- **Ruled out:** JSON Schema: duplicates Pydantic; openapi-typescript alone: frontend only; case-insensitive patch: fixes one symptom

### R030

**'Combinations are well studied' is said when no combination was counted** · weight 84 · Logic flaw · impact 4/5, reach 4/5, confidence 3/3 · flags F-A1-013

- **Evidence (A1):** backend/app/research/novelty.py:93-127 failed pair counts are skipped silently and a single part makes no pairs; :232-238 the fallback 'crowded' statement ('Each part is well studied, and so are their combinations') fires whenever no part is sparse, and :307-316 adds the 'business model' lever 'because every part and combination is crowded'. Probes with paper_count stubbed: 'banana chips for school children' (one part, 800 papers = 'active', not crowded) -> type crowded + business-model lever, pairs []; 'herbal tea with hibiscus and mint' with every pair and context count returning budget_exhausted -> pairs [], context searched False, statement crowded.

- **Why it matters:** When the OpenAlex budget runs out mid-check, or the idea has one searchable part, the founder is told the combination is crowded and steered away from a product to a service model, on evidence that was never gathered. 1.2.1.6 asks for honest 'unclear' for one idea; this is the general rule.
- **Where to build it:** backend/app/research/novelty.py (_statement, _levers)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Coverage-aware statement | Require pairs_searched == pairs_expected and context searched before 'crowded'; else 'unclear: combinations not searched'; label 'active' separately from 'crowded' | free/open source | Honest, small, testable with stubs as above | More 'unclear' statements when the budget is short |
| Retry failed pair counts once after the pause | sources already records pauses | free/open source | Fewer gaps | Burns the shared budget; latency |
| Single-part path: compare against the domain registry instead of pairs | planner registry domains | free/open source | Gives one-part ideas a useful statement | New logic; registry coverage uneven |

- **Recommended:** Coverage-aware statement. 'Not searched is never nothing found' is already the scan's rule (ideation.py coverage note); applying it to combinations removes a false claim with a few lines.
- **Ruled out:** Retry: spends the scarce budget and still can fail; Registry comparison: useful later but does not stop the false claim.

### R031

**/talk's support_for picks schemes from the domain card, never the founder's facts** · weight 84 · Logic flaw · impact 4/5, reach 4/5, confidence 3/3 · flags F-B4-010

- **Evidence (B4):** backend/app/agents/tools.py:217-225 _support_for(domain_id, district) calls registry.schemes_for(d) with the registry domain only; district is used for incubators alone. backend/app/planner/registry.py:80-140 _scheme_rules reads d['capital_band'], d['forms'] and d['sector'] from the domain card, not the founder's capital_band, product_form or stage slots, and gives no reasons for a 'no'. I ran _support_for('banana_value_added','madurai'): it returns tanseed, gramam_thorum_puthozhil, pmfme, needs, pmegp, mse_cdp and cgtmse for any founder. The engine path above says tanseed 'Requires DPIIT recognition' and needs requires age 21-45 and first-generation. TASKS 4.1.1 lists only seed.py and the catalogue as overlapping sources; 1.4.3 names support_for as a place to change but not that it bypasses the engine.

- **Why it matters:** In the conversation the founder hears TANSEED is for them, while the Schemes screen says ineligible for the same founder. That breaks 'code decides' consistency and the 'reasons for every no' guarantee, and the founder's own capital and stage answers are ignored.
- **Where to build it:** backend/app/agents/tools.py (_support_for takes the session), planner/registry.py (_scheme_rules becomes a relevance prefilter only), schemes/engine.py (decides eligibility)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Registry routes as a relevance shortlist, then the engine (three-valued) decides eligibility on projected FounderFacts | Reuses both existing modules; the engine already has the Soundness and Completeness properties | free/open source | One eligibility answer everywhere; domain relevance kept as the 'why relevant' text | Needs catalogue entries encoded as rules (4.1.1) before every route can be checked |
| Pass session slots into _scheme_rules and add founder conditions there | Small local change | free/open source | Quick | Builds a second rules engine without reasons; drifts from schemes/ |
| Label support_for output 'may be relevant, check eligibility' | Wording only | free/open source | No logic change | The contradiction with /schemes stays; violates 'fact check before speech' (0005) in spirit |

- **Recommended:** Registry routes as a relevance shortlist, then the engine (three-valued) decides eligibility on projected FounderFacts. Keeps one decider (schemes/engine) as 4.1.1 intends, and gives the conversation the same answer and reasons as the Schemes screen.
- **Ruled out:** Founder conditions in _scheme_rules: a second, reason-less engine; label only: the contradiction reaches founders anyway.

### R033

**Any long answer to another question overwrites 'problem' with that answer** · weight 84 · Logic flaw · impact 4/5, reach 4/5, confidence 3/3 · flags F-B1-019

- **Evidence (B1):** elicitation/extract.py:236-240: any text of 25 or more characters without a problem cue gives Extraction('problem', first sentence, 0.55). engine.observe skips only e.key == answering; session.put (session.py:166) lets equal confidence overwrite. Replay: the answer 'coconut farmers who sell copra' to the beneficiary question replaced problem (0.55, turn 5), so _idea_text became 'coconut farmers who sell copra make a solar dryer...' and idea_version changed.

- **Why it matters:** The idea text that research and novelty search on is silently replaced by the answer to another question. Combined with 1.2.3's re-run, this starts a new scan on a wrong idea and discards the right one. The restatement at S7 then says 'You want to solve a problem for coconut farmers who sell copra: coconut farmers who sell copra'.
- **Where to build it:** elicitation/engine.py observe (no positional problem guess when answering a slot), elicitation/session.py put (a guess never replaces an equal guess from an earlier turn)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Suppress the positional 'problem' guess when the utterance answers a slot | One condition in observe; the guess is meant for opening descriptions | free/open source | Fixes the replayed case directly | A founder who adds the problem while answering must use a cue word |
| Strict '>' for equal-confidence extracted values from different turns | Merge rule in put() | free/open source | First guess stays until something better arrives | A genuine better restatement at 0.55 is also blocked |
| Span check against the question asked (1.1.3.2 style) | Extend the planned span check to offline extraction | free/open source | One rule for model and offline | Larger change than the bug needs |
| Lower the guess below the existing value (0.5) | Confidence tweak | free/open source | Trivial | Breaks the first-turn guess, which is meant to sit at 0.55 for confirmation |

- **Recommended:** Suppress the positional 'problem' guess when the utterance answers a slot. The positional guess exists for free descriptions. When the founder is answering a named question, its first sentence is that answer, not the problem. Also add the replay as an eval assertion.
- **Ruled out:** Strict '>': blocks legitimate refinement; Span check: right later but heavier than this fix; Lower confidence: breaks the opening-turn behaviour.

### R035

**Clinical gate covers questions but not categories; tea idea weighted as a medical device** · weight 84 · Logic flaw · impact 4/5, reach 4/5, confidence 3/3 · flags F-B4-020

- **Evidence (B4):** backend/app/research/scan.py:271 builds vanigam_categories from every paper field via FIELD_TO_CATEGORY (Medicine/Nursing/Psychology -> health_bio, 'Business, Management and Accounting' -> saas), while the clinical gate at :272-279 (comment: 'herbal-tea papers list Medicine as a field') filters only the questions. backend/app/agents/council/vote.py:30-54 idea_type checks 'health_bio' in categories BEFORE the founder's sector. Ran: idea_type(['health_bio','agriculture'], {'sector':'food','product_form':'physical'}) -> 'health_device'; idea_type(['saas'], {'sector':'textile','product_form':'physical'}) -> 'software'. The result picks the panel's seat weights (agents/council/__init__.py:95).

- **Why it matters:** The review panel weights a tea or jasmine brand as a health device, or a physical textile product as software, whenever papers touch those fields. Verdicts and the panel's dynamic question (B4-06) then come from the wrong frame. 1.2.1.1 re-selects discussion points but leaves the categories, a separate output, ungated.
- **Where to build it:** backend/app/research/scan.py (apply the same gate to categories), agents/council/vote.py idea_type (founder-given sector and form take precedence over paper-derived categories)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Apply the clinical gate to categories and make idea_type use founder slots first, paper categories only as a fallback | Reuses the existing clinical_ok flag and CLINICAL_FIELDS; a reorder in idea_type | free/open source | One rule in both places; the founder's words beat bibliometrics | A genuine health idea with a wrong extracted sector relies on 1.1.3 or 1.1.2 to fix the slot |
| Threshold categories by field share (e.g. 25% or more of topic weight) | associated_domains already computes share_pct | free/open source | Drops incidental fields | New uncalibrated constant; with the term fallback (share None) it does nothing |
| Derive categories from the registry domain match (detect_domain) instead of paper fields | registry.detect_domain already runs in find_domains | free/open source | Curated mapping | Many ideas match no registry domain; then no category at all |

- **Recommended:** Apply the clinical gate to categories and make idea_type use founder slots first, paper categories only as a fallback. Fixes the inconsistency at its root, the same rule applied to twin outputs, and follows code-decides: the founder's stated sector outranks an inference.
- **Ruled out:** Share threshold: a new tuning constant that does nothing on the term fallback; registry-only categories: leaves most ideas uncategorised.

### R036

**D5's canonical list (12 registry categories) has no food, education, retail or manufacturing** · weight 84 · Missing logic · impact 4/5, reach 4/5, confidence 3/3 · flags F-B4-022

- **Evidence (B4):** registry.load()['categories'] keys: agriculture, ai_ml, climate, electrical, fintech, health_bio, iot, it, logistics, renewable, saas, textile (checked by running). TASKS D5 recommends 'StartupTN categories, others mapped', meaning these. The elicitation enum has FOOD, EDUCATION, RETAIL, MANUFACTURING and AUTO (slots.py:73-87). Code keyed on those would lose its target: planner/registry.py:115 routes PMFME on sector == 'food' (an ecosystem id), roadmap.py:33 K_DOMAIN has food and manufacturing, vote.py:37 has a 'food' idea type. 1.2.1.3 'local startup matching by sector' is marked 'now', but scan(text) receives no session sector at all, and startups carry ecosystem ids (ecosystem/index.py:45).

- **Why it matters:** If D5 is taken as recommended, food, education and retail ideas have no canonical sector: the PMFME route, the food timeline multiplier and the food panel weights all go dark, and the quality-set ideas (tea, jasmine) fall into 'agriculture' or nothing. 1.2.1.3 cannot be done 'now' without picking a vocabulary and passing the sector into the scan.
- **Where to build it:** the D5 decision and the 4.1.2 taxonomy module; research/scan.py scan() signature (accept the canonical sector); TASKS 1.2.1.3 'When' (after 4.1.2)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Two-level canonical taxonomy: StartupTN category as the public top level, ecosystem sector ids (20) as the required second level, with each elicitation value mapped to a sector | The registry already stores both (category plus 'sector'; registry.py:85, 169); ecosystem/taxonomy.py maps NIC and directory text to the 20 sectors | free/open source | Keeps StartupTN alignment for display and incubators while food, retail and education stay expressible; NIC and cluster joins (B4-02) work | Two levels to explain in the decision record |
| Adopt the 20 ecosystem sectors as canonical and map StartupTN categories onto them | Largest existing list with NIC and keyword mappings | free/open source | Covers food, consumer and education | Departs from the public StartupTN labels founders see on government sites |
| Adopt the 12 StartupTN categories as D5 recommends, with an 'other' bucket | Owner's recommendation | free/open source | Simple, public | Food, retail and education collapse into 'other'; breaks PMFME routing and food weights |

- **Recommended:** Two-level canonical taxonomy: StartupTN category as the public top level, ecosystem sector ids (20) as the required second level, with each elicitation value mapped to a sector. Matches what the registry already does, keeps every existing consumer's target, and gives 1.2.1.3 and 4.2.2 a sector id to join on.
- **Ruled out:** Ecosystem-only: loses the public StartupTN labels; StartupTN-only: proven gaps (no food, education, retail or manufacturing) that break live routing rules.

### R038

**Idempotency is planned on agent_turn, but the Talk page only uses the stream** · weight 84 · Logic flaw · impact 4/5, reach 4/5, confidence 3/3 · flags F-B1-007

- **Evidence (B1):** TASKS.md 1.1.4 Where: 'routers/ideation.py (agent_turn)'. The only turn call in the frontend is agentClient.ts:183 POST .../turns/stream (grep '/turns' finds no other caller). routers/ideation.py:343-357: the stream saves the session only when the 'done' event comes, then yields 'done'. A drop after the save but before 'done' reaches the phone consumes the turn; a replay runs it again.

- **Why it matters:** If 1.1.4.1 caches one JSON response for agent_turn, the double-consumed answer on 2G stays exactly as it is, because the Talk page never calls that endpoint. Replaying a stream needs the whole event sequence (sentences already fact-checked, the action, the evidence), not one dict.
- **Where to build it:** routers/ideation.py (agent_turn_stream and agent_turn share one idempotency check), agents/ideation.py (AgentSession keeps the last turn's id and final events), agentClient.ts (send client_turn_id)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Keep last_turn {client_turn_id, done payload, sentences} in the session document | Decision 0003: the session is one JSON document already saved atomically with the version check | free/open source | Saved in the same write as the turn, so it cannot disagree with it; works on memory, Redis and PostgreSQL stores; a replay re-emits the saved events with no model call | Session grows by one turn's events |
| Redis SETNX idempotency key with a cached response | A common API idempotency pattern; Redis is already in the stack | free/open source | Standard | A second store that can disagree with the session (written before or after the save); useless when Redis is off |
| HTTP Idempotency-Key middleware (e.g. asgi-idempotency-header) | Generic ASGI middleware | free/open source | No endpoint code | Built for buffered JSON responses, not SSE streams; stores outside the session |
| Make turns naturally idempotent by text hash | Compare with the last user message | free/open source | No client change | A founder who says 'yes' twice on purpose would be swallowed |

- **Recommended:** Keep last_turn {client_turn_id, done payload, sentences} in the session document. Only an atomic write with the turn makes 'already applied' and 'response available' the same fact. Check it after taking the per-session lock and loading the session, so a slow original and a retry cannot both run.
- **Ruled out:** Redis SETNX: a second source of truth, and gone when Redis is off; Middleware: does not fit SSE and lives outside the session; Text hash: drops deliberate repeats.

### R040

**Jobs are keyed by session and kind: an old version's job is reused or blocks the new** · weight 84 · Missing logic · impact 4/5, reach 4/5, confidence 3/3 · flags F-B1-020

- **Evidence (B1):** agents/jobs.py:62-73 board.start returns the existing job for (session_id, kind) when it is RUNNING, or DONE with reuse_done=True; both research call sites pass reuse_done=True (ideation.py:390, :661). run() (:75-79) writes with LATEST and does not record the version the snapshot was taken at. _absorb (:422) takes research whenever s.scan is None.

- **Why it matters:** Re-keying results.put (1.2.3.1) is not enough. After a version change the board still hands back the finished old job (reuse_done), or makes the new version wait behind a running old job and never starts it. A late old-version result can also be absorbed as current. 'A stale result is never narrated' (1.2.3.3) fails through the job layer, not the results layer.
- **Where to build it:** agents/jobs.py (key jobs by (session, research_key, kind); capture the key in the snapshot; cancel or ignore superseded jobs), agents/ideation.py (_absorb compares the result's key with the current one)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Key jobs by (session, version, kind) and tag payloads with their version | Same keying as the ResultStore interface already declares (results.py:24-31) | free/open source | Reuse is correct per version; stale results are rejected at absorb | Old jobs keep running unless cancelled |
| Cancel the running job on version change | asyncio Task.cancel, already used in board.forget | free/open source | Saves free quota | Rapid churn cancels useful work; needs the stabler key from flag 1 |
| Generation counter on the board | Monotonic int per session | free/open source | Simple stale check | Throws away identical-content results when a founder reverts |
| arq / RQ job queue with job ids | Redis-backed queues (2.3.1) | free/open source | Durable, cross-process | Waiting on 2.3.1; a dependency before the keying is right |

- **Recommended:** Key jobs by (session, version, kind) and tag payloads with their version. Makes the board agree with the ResultStore's own interface. Add cancellation of superseded running jobs once flag 1's stable key keeps churn low.
- **Ruled out:** Cancel alone: does not stop a late result from being absorbed; Generation counter: loses reuse when the idea returns to an earlier version (lever undo); arq/RQ: belongs to 2.3.1 and does not fix keying by itself.

### R041

**Levers are tracked by list position, so reranking or a new version skips them** · weight 84 · Logic flaw · impact 4/5, reach 4/5, confidence 3/3 · flags F-B3-020

- **Evidence (B3):** agents/ideation.py:574-579 marks narrated levers as 'lever:{i}' (index) and the statement as 'statement' in s.narrated, never keyed to idea_version or the lever's content. Ran it: novelty v1 narrated 'Gap A', lever 0 and lever 1. After s.novelty was replaced with a new statement and three new levers, the next calls gave only 'Another way to stand out: join P with Q' (the old index 2), then None. The new statement and the new levers 0 and 1 were never spoken. 1.3.1 will reorder the list after the panel job finishes, and that job runs in the background and can land between turns (ideation.py:409, 439). 1.2.3 and 1.2.4 replace the list on every new idea version.

- **Why it matters:** After the panel reorders the levers, the founder hears the same lever twice and never hears the one the panel ranked first. After choosing a lever (1.2.4), the new idea's novelty statement and best levers are silently skipped. That is the very evidence 1.2.3 exists to deliver.
- **Where to build it:** agents/ideation.py (_next_novelty_point, s.narrated keys); research/novelty.py (a stable lever id); the 1.2.3 version bump clears or scopes the narrated marks

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Stable lever ids (hash of kind and text) scoped by idea_version: narrated keys become 'lever:{version}:{id}' and 'statement:{version}' | A few lines in novelty.py and the narrator; hashlib is stdlib | free/open source | Reordering and new versions both handled; the session JSON stays one document (0003) | Old sessions' index keys need a one-time upgrade (2.1.4's upgrade-on-read) |
| Clear s.narrated novelty keys whenever novelty or the panel's order changes | One reset in _absorb | free/open source | Tiny change | Re-narrates levers already heard after a reorder |
| Freeze the order once narration starts; apply the panel's order only to the next version | Narration rule only | free/open source | No repeats | The panel's ranking is ignored for the version it judged, which defeats 1.3.1 |
| Narrate from a queue built once per version | A list of pending lever ids on the session | free/open source | Explicit and easy to test | Still needs stable ids to rebuild on reorder |

- **Recommended:** Stable lever ids (hash of kind and text) scoped by idea_version: narrated keys become 'lever:{version}:{id}' and 'statement:{version}'. It is the only option that survives both changes coming on this route: the panel reorders (1.3.1) and the idea changes version (1.2.3, 1.2.4). It also gives 1.2.4's choose-lever action an id to send instead of an index that may have moved.
- **Ruled out:** Clearing marks: repeats what the founder already heard. Freezing the order: throws away the panel's ranking, the point of 1.3.1. A queue alone: still needs stable ids to rebuild when the order changes.

### R042

**Levers carry no slot change, so most choices leave idea_version unchanged** · weight 84 · Missing structure · impact 4/5, reach 4/5, confidence 3/3 · flags F-B1-013

- **Evidence (B1):** research/novelty.py:254-318: each lever is {kind, text, because} with no structured delta. agents/ideation.py:58 CORE_SLOTS = (problem, solution, product_form, sector, beneficiary) and :136-142 idea_version hashes only those. For 'localise', 'cost-down' and 'regulatory route' no core slot is an obvious target. 're-target' maps to beneficiary (retarget['who']), 'combine' to solution, 'business model' to product_form=service, but nothing records that mapping.

- **Why it matters:** 'A choose-lever action updates the idea slots, bumps idea_version' has no rule for which slots. Choosing localise or cost-down leaves the hash unchanged, so 1.2.3's version-keyed re-run never fires, and the founder hears the old verdict for what they now see as a new idea. A free-text rewrite of 'solution' would make the hash change for any wording, re-running research for no reason.
- **Where to build it:** research/novelty.py (each lever gets an id and a 'patch' {slot: value} plus 'tags'), agents/ideation.py (idea_version includes the chosen lever ids, or a 'variant' slot is added to CORE_SLOTS)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Structured lever patch + chosen-lever ids in the version hash | Code decides (0002); the lever producer already knows the gap behind each lever (a, b, who, pack) | free/open source | Deterministic; every lever kind gives a new version; the patch is shown to the founder before applying | Each kind needs a reviewed patch rule; levers with no slot target (localise, cost-down) still need the id in the hash |
| Bump an explicit version counter on every choice | Integer on AgentSession | free/open source | Trivial and always changes | Disconnected from content: reverting to the same slots makes a 'new' version; 1.2.3 cache keys stop matching content |
| Let the model rewrite the idea text from the lever | Free model chain (0009) | free tier | Fluent new idea | Offline path has nothing; model would author facts (against 0002/0005) |
| Add a 'variant' slot holding the lever kind | Slot table data change | free/open source | Fits the existing hash with no new mechanism | Only one lever at a time unless it holds a list |

- **Recommended:** Structured lever patch + chosen-lever ids in the version hash. Makes 'new idea version' a fact computed from content. Applying the same lever twice gives the same version, so 1.2.3's cache hits, and every lever kind changes the version. The patch also gives research new public terms (e.g. the 'combine' pair) to search with.
- **Ruled out:** Counter: version stops meaning content, and caches keyed by it miss on identical ideas; Model rewrite: no offline path, and the model would author facts; 'variant' slot alone: cannot hold more than one chosen lever, and adds nothing the patch rule does not already give.

### R043

**Notice keyed to 'active provider' can only appear after text reached Google** · weight 84 · Logic flaw · impact 4/5, reach 4/5, confidence 3/3 · flags F-B3-009

- **Evidence (B3):** providers.chain() picks providers per turn from LLM_ORDER, configuration and circuit-breaker state (providers.py:429-435), so the provider can change mid-conversation (0009). The session start response has no provider field (routers/ideation.py:299-304). The provider is reported only in the finished turn's done payload (ideation.py:1009), after s.messages were streamed to it (:510). The panel job (:352) and Gemini voice (voice.py:103) can reach Google even when the turn's provider was Ollama.

- **Why it matters:** As written ('show a notice when the active provider is Gemini'), the founder's first message is sent before the notice can show, and a session that started on Ollama switches to Gemini silently when a breaker closes. The notice also records no agreement, so 3.2.1 has nothing to point at.
- **Where to build it:** routers/ideation.py (start response), agents/providers.py (a 'may reach' summary), Talk.tsx, the consent event from 3.2.1

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Decide from configuration at session start: if any Google path is configured, show a versioned notice and record agreement before the first turn | Settings already show which keys are set; the session JSON can hold the consent event (step 2) | free/open source | Shown before any text leaves; covers fall-over and panel and voice; gives 3.2.1 a notice version | Shown even on sessions that end up never using Gemini |
| Show the notice on the first done event with provider 'gemini' | Plan as written; data already in the done payload | free/open source | Shown only when Gemini really answered | Too late: the text was already sent; misses panel and voice |
| Block Gemini until the founder agrees (per-session provider allowlist) | chain() filtered by a session flag | free/open source | Strictest; founder chooses | Extra step in a voice-first flow; needs a clear default |
| Static notice in the site footer or terms page | Common practice | free/open source | No code | Not shown at the moment of use; no record |

- **Recommended:** Decide from configuration at session start: if any Google path is configured, show a versioned notice and record agreement before the first turn. It is the only rule that runs before text leaves, covers every Google path (turns, panel, voice), and gives the consent record from 3.2.1 a notice version to cite. Combine it with the session allowlist, so that declining means the local-only chain from the previous flag.
- **Ruled out:** Notice on the first Gemini done event: by definition after the disclosure is needed. Allowlist alone: the founder still needs the notice text to choose. Footer notice: not shown at the moment of use and leaves no record.

### R044

**Novelty and planner match domains differently; banana chips loses its cost lever** · weight 84 · Logic flaw · impact 4/5, reach 4/5, confidence 3/3 · flags F-B4-023

- **Evidence (B4):** backend/app/research/novelty.py:306-313 _has_pack reads scan['local']['registry_domains'], built by research/scan.py:176-180 (any registry card sharing 2+ words of 4+ letters, unranked). The planner and panel use registry.detect_domain (planner/registry.py:259-276, IDF-weighted, best match); agents/council/evidence.py:184-189 adds 'A Vanigam cost pack exists for this domain' from that card. Ran: 'banana chips for export' gives detect banana_value_added (has pack) but local [] and has_pack False; 'jasmine flower cold storage for growers' gives detect jasmine_postharvest (has pack) but local [] and has_pack False; 'hospital bill instalment loans...' gives local [medical_tourism_facilitation, medical_emi], first match wrong.

- **Why it matters:** 1.2.2's 'word each lever from the matched domain' has two different 'matched domains'. For the plan's own example, banana chips, novelty matches no domain, so domain wording falls back to generic text and the cost-down lever is never offered, while the panel cites a cost pack for the same idea. Founders get contradictory advice in one conversation.
- **Where to build it:** research/scan.py _local (use detect_domain for the best domain; keep overlap only for 'related' domains), research/novelty.py _has_pack and _levers (take the planner's domain id)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| One domain resolver (registry.detect_domain) whose result is stored on the session and passed to scan, novelty, council and planner | detect_domain already exists, is IDF-weighted and is what the planner uses | free/open source | Every module talks about the same domain; testable on the quality set | Ideas with no confident match get no domain anywhere (honest, but less coverage) |
| Rank _local's matches with the same IDF score and take the top one | Reuse registry._index inside scan | free/open source | Keeps the 'related domains' list | Still two code paths that can drift |
| Let the model choose the domain via find_domains on the model path | Tool already exists | free tier | Context-aware | Offline path unchanged; code-decides (0002) favours a deterministic resolver |

- **Recommended:** One domain resolver (registry.detect_domain) whose result is stored on the session and passed to scan, novelty, council and planner. Removes the contradiction at its source and gives 1.2.2 a single domain to word levers from, in the same way 4.1.2 gives one sector.
- **Ruled out:** Ranking _local: two resolvers that will drift again; model choice: not available offline and not code-decided.

### R046

**Planner puts 'Apply for seed grants' after pilot and customers; prototype grants come too late** · weight 84 · Logic flaw · impact 4/5, reach 4/5, confidence 3/3 · flags F-B2-024

- **Evidence (B2):** backend/app/planner/data/packs/common.json: c_grant is in phase Growth with depends_on ['c_pilot'] (c_equity likewise). Ran build_plan('smart pump controller for farmers', {'funding_route':'grant','product_form':'physical'}, domain='pump_controllers'): the order is ... p_proto (Validation) ... c_pilot (Launch), c_customers (Growth), c_grant (Growth). Meanwhile backend/app/planner/registry.py:98-107 routes this kind of domain to nidhi_prayas ('technology prototype') and tiic_proto ('prototype loan'), and schemes/annotate.py:16-23 maps prototype-stage schemes to the Validation phase.

- **Why it matters:** A founder who chose grants is told to build the prototype, certify, launch and win customers first, and only then apply for the seed and prototype grants meant to pay for those steps. After 1.4.1.1 moves phase-based annotation onto planner milestones, the same roadmap shows NIDHI PRAYAS on a Validation milestone and 'Apply for seed grants' in Growth, two contradictory answers to 'when do I apply'.
- **Where to build it:** backend/app/planner/data/packs/common.json (funding milestones per stage: a prototype/seed grant before p_proto or c_pilot, a growth loan or equity later); schemes/annotate.py (place schemes on the funding milestone of the matching stage, not by phase alone)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Split c_grant into stage-specific funding milestones (c_seed_grant before prototype, c_growth_funding after pilot) and annotate schemes onto them by target stage | Data-only change in the pack JSON plus a small change to annotate.py; the CP-SAT selector already enforces depends_on | free/open source | Grants appear when they fund the work; a single 'when to apply' answer | Pack overrides must be reviewed so they keep the new IDs |
| Keep c_grant but derive its depends_on from the earliest target stage of the domain's scheme routes | Dynamic dependency in planner/plan.py | free/open source | Adapts per domain | Logic hidden in code rather than the reviewed pack data |
| Drop funding milestones and rely on annotation only | Avoids duplication | free/open source | One mechanism | The founder's chosen funding route no longer shapes the plan |

- **Recommended:** Split c_grant into stage-specific funding milestones (c_seed_grant before prototype, c_growth_funding after pilot) and annotate schemes onto them by target stage. It fixes the sequencing in reviewed data, keeps the funding route meaningful, and gives 1.4.1.1 a precise milestone for each scheme instead of a phase guess.
- **Ruled out:** Dynamic depends_on: hides planning rules in code, against curation by reviewed commits. Annotation only: the founder's funding choice stops affecting the roadmap.

### R048

**Ranking data has nothing to match experience slots to and no per-card citation** · weight 84 · Missing structure · impact 4/5, reach 4/5, confidence 3/3 · flags F-B1-006

- **Evidence (B1):** planner/data/registry domain cards (e.g. banana_value_added) carry sector, forms, districts, needs/offers (business capabilities such as processing and cold_storage) and capital_band, but no field for founder skills, prior trade or owned assets. No card in domains.json or domains_batch2.json has a source field (grep 'source' = 0). 190 of 240 cards are review='draft', and planner/registry.py never reads 'review'. registry.py:30 DISTRICTS lists only 5 pilot districts. The 8 catalogue 'demand' entries (funding_catalogue.json) are funding channels without problem statements; idex, idex_aditi, gem_runway and aim_anic require defence deep-tech or DPIIT recognition.

- **Why it matters:** The 1.1.5.3 fit score can match only sector, capital and form, which are the idea-like slots, and not the experience the mode exists for. A Salem cook gets no district fit. Draft, uncited cards would be shown as 'cited opportunities', and the demand entries would offer defence challenges to first-generation founders who have no company.
- **Where to build it:** planner/data/registry (card schema fields skills_used, assets_used, sources), planner/registry.py (review filter), a cited skill-to-capability vocabulary, the 5.2.1 schema

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Add skills_used/assets_used + sources to the card schema; exclude draft cards | A data change reviewed by commit (SYSTEM-DESIGN §10); fits the 5.6.1 review | free/open source | Deterministic, citable, explainable score | Needs reviewer time for 240 cards |
| Keyword overlap of founder_skills with card summary/label | Matching in the style of research/terms.py | free/open source | No data work | Weak recall: 'cooking' does not match 'Banana value-added products' |
| Embedding similarity | sentence-transformers locally | free/open source | Semantic match | Dropped by the plan (offline embeddings are hashes); CPU cost; not explainable |
| Founder picks a category first; rank within it | UI flow | free/open source | Works with today's data | Pushes the work onto the founders this mode is meant to help |

- **Recommended:** Add skills_used/assets_used + sources to the card schema; exclude draft cards. The only option that keeps the score deterministic and cited, as the plan requires. Combine it with a small cited skill-to-capability vocabulary, and limit demand entries to those a founder without a company can qualify for (sfurti, mse_cdp).
- **Ruled out:** Keyword overlap: too weak to be the score; Embeddings: dropped by the plan and not explainable; Category first: shifts the burden onto the founder.

### R049

**Scheme annotation ignores live status; it places closed SISFS on milestones** · weight 84 · Logic flaw · impact 4/5, reach 4/5, confidence 3/3 · flags F-B2-025

- **Evidence (B2):** backend/app/schemes/annotate.py:30-45 places any ranked eligible scheme whose target_stages overlap, and its docstring even says 'SISFS at MVP'. backend/app/schemes/models.py has no status field. backend/app/schemes/seed.py holds 8 schemes. In funding_catalogue.json (queried): sisfs 'closed', standup_india 'revamping', tanseed and nidhi_prayas 'between_calls'. registry.schemes_for (planner/registry.py:141-158) carries that status, and annotate does not use it.

- **Why it matters:** A founder's roadmap tells them to apply for SISFS, a closed scheme, at a specific milestone, and the Talk agent (using support_for with live status) may say the opposite. 1.4.1.1 moves this annotation onto planner milestones without saying which source or which status rule; 4.1.1 unifies the sources but says nothing about status in annotation.
- **Where to build it:** backend/app/schemes/annotate.py (take scheme routes plus status from registry/catalogue; skip 'closed', label 'between calls' and 'revamping'); 1.4.1.1 task text

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Annotate from registry.schemes_for routes with catalogue status: closed excluded, between_calls shown as 'next call expected', revamping labelled | Reuses the planner's own scheme routes and the 46-entry corrected catalogue | free/open source | Matches what Talk says; no invented availability | Eligibility rules exist only for the 8 seed schemes until 4.1.1 finishes |
| Add a status field to the Scheme model and filter in SchemeSwarm | A model change in schemes/models.py | free/open source | Fixes every SchemeSwarm caller | A third copy of status beside the catalogue until 4.1.1 |
| Show all schemes with a status badge, no filtering | Transparency | free/open source | Nothing hidden | Closed schemes still sit on the founder's timeline as an action |

- **Recommended:** Annotate from registry.schemes_for routes with catalogue status: closed excluded, between_calls shown as 'next call expected', revamping labelled. One status source (the corrected catalogue), the same answer as Talk, and no roadmap step that sends a founder to a closed scheme.
- **Ruled out:** Status on the Scheme model: duplicates the catalogue's status before 4.1.1 merges the sources. Badge only: still schedules an impossible application.

### R050

**Session language is never set from typed Tamil or Hindi, so 1.5.1's switch never fires** · weight 84 · Missing logic · impact 4/5, reach 4/5, confidence 3/3 · flags F-A1-029

- **Evidence (A1):** backend/app/agents/ideation.py:925-926 sets s.language only when the request carries language; frontend/src/pages/Talk.tsx:73 the picker defaults to 'auto' (not persisted), :116-118 turnLang on auto sends only a language a recogniser reported, and :282-286 browser recognition on auto listens in en-IN. A founder who types in Tamil script, or speaks Tamil with the default picker and no paid Sarvam key, sends no language (or en-IN); the done event and offline templates stay English (ideation.py:1006-1007).

- **Why it matters:** 1.5.1 plans to substitute translated sentences 'when the session language is not English', but for typed Tamil and the default browser path the session language is never anything but English, so the feature would not reach the founders it is for, and Tamil speech is transcribed as English.
- **Where to build it:** backend/app/agents/ideation.py (turn_stream: detect script), frontend/src/pages/Talk.tsx (persist the picker, default from navigator.language)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Unicode-script detection on the server | Count characters in the Tamil (U+0B80-0BFF) and Devanagari (U+0900-097F) blocks; set s.language when no language is sent | free/open source | Deterministic, offline, a few lines; covers typed text | Romanised Tamil (Tanglish) stays undetected (D7) |
| Persist the picker and default it from navigator.language | localStorage in Talk.tsx (a per-viewer convenience) | free/open source | Browser recognition gets the right language | Many phones report en-IN even for Tamil speakers |
| fastText language-ID model (lid.176) | Free, offline, widely used | free/open source | Detects romanised text better | 126 MB model for three languages; poor on short Tanglish |
| Ask the language once at session start | One extra tap/question | free/open source | Explicit | Spends attention; voice founders may not read the prompt |

- **Recommended:** Unicode-script detection on the server. Free, instant and exact for script input, and pairs with persisting the picker for speech; Tanglish stays with D7.
- **Ruled out:** Picker persistence alone: does not help typed text; fastText: heavy for three scripts; Asking: costs a step the low-literacy design avoids.

### R051

**Skipped and dropped required slots vanish from the 'I still don't know' sentence** · weight 84 · Logic flaw · impact 4/5, reach 4/5, confidence 3/3 · flags F-A1-003

- **Evidence (A1):** backend/app/elicitation/session.py:126-127 missing = missing_required(...) - skipped; engine.py:368-373 restate names only session.missing; engine.py:149-151 a slot missed twice is skipped. Probe: stage, capital_band and funding_route were skipped/dropped; restate said only 'I still don't know your beneficiary, district, product form'.

- **Why it matters:** The code comment says 'Gaps are named, never hidden', yet exactly the facts the founder declined or could not answer are defaulted silently, so the roadmap's capital and funding assumptions are invisible. 1.1.2.1 labels restated facts; these slots have no value, so the labels never reach them.
- **Where to build it:** backend/app/elicitation/engine.py (restate), session.py (an 'unanswered' view)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Name required minus filled (including skipped) in the gap sentence | One-line change in restate | free/open source | Honest, trivial, testable | Names the gap but not the value assumed |
| Two sentences: 'you skipped X; I will assume Y' | restate plus the planner's default per slot | free/open source | Is the 'I assumed' label 1.1.2 wants, with the real default | Needs the planner defaults exposed |
| Show gaps only on screen, not spoken | Talk.tsx panel | free/open source | No nagging on voice | Voice-only founders never learn the assumption |

- **Recommended:** Two sentences: 'you skipped X; I will assume Y'. Applies 1.1.2's 'I assumed' label to slots with no value and tells the founder the actual default.
- **Ruled out:** Gap sentence only: no assumed value; Screen-only: excludes the voice-first founders the product targets.

### R053

**note_fact answers 'recorded' when put() drops the value, so wrong extractions stick** · weight 84 · Logic flaw · impact 4/5, reach 4/5, confidence 3/3 · flags F-B4-012

- **Evidence (B4):** session.put (elicitation/session.py:166-170) returns silently when the new confidence is lower, and _note_fact (agents/tools.py:274-275) always returns {'recorded': key}. Model notes are 0.8 EXTRACTED; extractor sector is 0.90 (extract.py:203) and stage 0.85. Ran: after extract('A microprocessor trainer kit for colleges') set sector=AGRI (B4-01 flag 1), _note_fact('sector','electronics') returned {'recorded': 'sector'} but the slot stayed Sector.AGRI. 'sector' is then not in candidates() (0.90 >= TAU_FILL 0.60), so it is never asked.

- **Why it matters:** The model, the only part that understands context, cannot correct a substring false positive, and it is told it did. The founder gets an agriculture roadmap, schemes and panel weights for an electronics kit unless they spot it at confirmation. 1.1.3.3's 'disagreement cap' would catch this only if put() keeps the losing value; today it is discarded with no trace.
- **Where to build it:** backend/app/elicitation/session.py put() (return outcome, keep the rival value), agents/tools.py _note_fact (report the outcome), selector.candidates (a disputed slot becomes askable)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| put() returns an outcome (stored / kept_existing / conflict) and records rivals; a conflict caps confidence below TAU_FILL | Small change to existing domain code; meets 1.1.3.3 directly | free/open source | Model gets the truth; disagreement forces a founder question; rivals are available to 1.1.2's source labels | Session JSON grows a little (rivals per slot) |
| Raise model-note confidence above the extractor's | Constant change | free/open source | Model wins | A hallucinated model note then beats a correct extraction; against fact safety |
| Lower extractor sector confidence below TAU_FILL so it is always confirmed | Constant change | free/open source | Founder always confirms the sector | Spends one of the 7 questions on every idea, including obvious ones |

- **Recommended:** put() returns an outcome (stored / kept_existing / conflict) and records rivals; a conflict caps confidence below TAU_FILL. Neither source is trusted blindly: disagreement goes to the founder, which is exactly 1.1.3.3's intent, and the tool reply stays truthful.
- **Ruled out:** Model-first confidence: lets an ungrounded note override the founder's words; always-confirm sector: costs a question every session.

### R054

**s.messages is model context, resume transcript and fact source at once** · weight 84 · Missing structure · impact 4/5, reach 4/5, confidence 3/3 · flags F-B1-023

- **Evidence (B1):** Readers of s.messages: model input (ideation.py:510); snapshot transcript for resume (:229-232); the fact check's tool results and founder words (_facts, :280-289); rollback of a failed provider (:970-982); reword pops the last message (:780). Tool results are stored in full: run_tool returns the whole roadmap (agents/tools.py:333 'return r') and the novelty result (:316), json.dumps'd into messages (:530-532) while the same data is stored again in s.roadmap and s.novelty. Nothing ever removes messages, and the session document is saved whole on every turn (store.py save).

- **Why it matters:** If 1.6.1 trims s.messages in place, the fact check loses older tool results and founder words, so true sentences that cite earlier evidence are dropped (0005), and a resumed session shows a cut transcript. If it does not trim, the per-session document keeps growing, with duplicated payloads, and is rewritten on every turn on Redis and PostgreSQL. The plan's Why talks only about model latency, so neither consequence is owned.
- **Where to build it:** agents/ideation.py (split AgentSession.messages into transcript (append-only, what was said) and a derived model context; store tool results by reference to s.scan/s.roadmap/s.novelty), agents/store.py; session format version (2.1.4)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Append-only transcript + derived context view; tool results stored by reference | Decision 0003 keeps one document; this only changes its fields | free/open source | Fact check and resume keep full history; the context builder chooses what the model sees; the document stops duplicating payloads | Format change with a migration (2.1.4) |
| Trim in place and move facts into a separate fact ledger | Ledger of citable strings | free/open source | Bounded document | Resume transcript is lost; a second structure to keep consistent |
| Compress the document (zlib) before saving | Standard library | free/open source | Cheap size win | Does not bound growth or fix the role confusion; PostgreSQL JSON loses queryability |
| Move transcripts to a separate table now | 5.5.5.1 plans session tables | free/open source | Scales | Waits on 2.1.1; conflicts with 0003 until then |

- **Recommended:** Append-only transcript + derived context view; tool results stored by reference. Lets 1.6.1 bound only what the model sees, without touching what the founder said or what the fact check may cite. Storing results by reference removes the largest duplicated payloads.
- **Ruled out:** Trim and ledger: loses the resume transcript (1.1.4.3 needs it); zlib: hides growth without bounding it; Separate table: blocked on 2.1.1 and 0003.

### R055

**'I'll widen the estimates' is never true: roadmap confidence is fixed at 0.8** · weight 80 · Logic flaw · impact 3/5, reach 5/5, confidence 3/3 · flags F-A1-025

- **Evidence (A1):** backend/app/elicitation/engine.py:371-373 the restatement promises 'I'll use safe defaults and widen the estimates' for unknown slots; agents/tools.py:228-232 _roadmap calls build_plan without confidence, so planner/plan.py:45 default 0.8 always feeds roadmap.months sigma (planner/roadmap.py:123). Probe: build_plan('banana chips', {}) and with all nine required slots filled both gave months_realistic 21 and identical bands (milestone 2: 1/1/2 months). _roadmap_line (ideation.py:902-909) speaks only months_realistic, never the range.

- **Why it matters:** A founder who skipped capital, stage and district gets the same precision as one who answered everything, after being told the opposite; the optimistic-pessimistic range the design requires (rnd-elicitation §7, Req 1.3 AC6-7) is computed but never spoken.
- **Where to build it:** backend/app/agents/tools.py (_roadmap: confidence from the session), planner/plan.py, agents/ideation.py (_roadmap_line)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Confidence from slot coverage | confidence = mean over required slots of (slot confidence, 0 when missing or skipped), floored at 0.3; speak 'about N months, between A and B' | free/open source | Uses data already in the session; honest range | Totals for optimistic/pessimistic must be summed on the critical path too |
| Per-milestone widening by the facts it depends on | Each template lists the slots it reads; missing ones widen only those milestones | free/open source | More precise | Template metadata work for every pack |
| Drop the promise from the restatement | Wording change | free/open source | Trivial | Keeps the false precision |

- **Recommended:** Confidence from slot coverage. Delivers the stated behaviour with a few lines and makes the range audible.
- **Ruled out:** Per-milestone widening: better later, too much pack work now; Dropping the promise: hides uncertainty from founders.

### R056

**Offline panel question is always the customer seat's, repeating the beneficiary question** · weight 80 · Logic flaw · impact 3/5, reach 5/5, confidence 3/3 · flags F-A1-019

- **Evidence (A1):** backend/app/agents/council/vote.py:103-109 the question comes from the lowest seat on the most-disputed criterion only when spread > 1.0, else the first opinion with ask_founder, which is always the customer seat (first in SEATS, seats.py:229). In rules mode each criterion is scored by one or two seats, so spread stays <= 1.0. Probe (rules, three ideas incl. one with beneficiary='school children'): ask_about None every time, question 'Who exactly would pay for this, and what do they use today instead?' from customer. elicitation/slots.py:210 already asks 'Who pays for it, or benefits from it?'; ideation.py:397-401 queues the panel question via add_dynamic, which dedupes only exact text, and engine.step asks dynamic questions before slot questions.

- **Why it matters:** Offline founders spend one of their scarce questions answering 'who pays' a second time, even when they already named the buyer, while the panel's real disagreement is never asked. 1.2.5 shares the dynamic budget but assumes the panel's question is useful.
- **Where to build it:** backend/app/agents/council/vote.py (question choice), rules.py (ask_founder per seat), elicitation/engine.py (add_dynamic: skip a question whose slot is already filled)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Tag each seat question with the slot it duplicates and skip it when filled | Rules carry 'covers': 'beneficiary'; add_dynamic refuses when that slot is filled | free/open source | Deterministic, small | Tag upkeep per seat |
| Pick the question from the weakest criterion when nobody disagrees | vote.py: fall back to the low seat of the lowest-scoring criterion, not the first seat | free/open source | Asks about the real weak point | Still may duplicate a slot without the tag |
| Semantic dedupe with a sentence-embedding model | sentence-transformers, offline | free/open source | Catches paraphrases | Large model, against the 'no embeddings offline' stance (Dropped list) |
| No panel question in rules mode | Only model seats raise questions | free/open source | Simple | Loses a useful question offline |

- **Recommended:** Tag each seat question with the slot it duplicates and skip it when filled. Combined with the weakest-criterion fallback it stops the repeat and asks something new, all in code.
- **Ruled out:** Weakest-criterion fallback alone: can still repeat a slot; Embeddings: heavy and dropped by the plan; No question offline: wastes the panel's value for the main (offline) path.

### R063

**Mid-conversation corrections never stick; district picked by name length, not position** · weight 78 · Logic flaw · impact 4/5, reach 3/5, confidence 3/3 · flags F-A1-005

- **Evidence (A1):** backend/app/elicitation/session.py:165-167 an EXTRACTED value replaces an ANSWER only at confidence >= 0.90, but district extraction gives 0.85; places.py:49-60 find_district returns the longest (then dict-ordered) name anywhere in the text. Probe: after answering 'Erode', 'sorry, actually I am in Salem, not Erode' extracted district='erode' (0.85), and 'my unit is in Salem now' left district=erode; find_district('I live in Salem but want to sell in Coimbatore') -> 'coimbatore'.

- **Why it matters:** A founder who corrects a fact in passing is silently ignored until confirmation, and a sentence naming two places picks one by string length. 1.1.2 covers corrections after a 'no' at S7 and 1.1.3 the disagreement cap; neither covers correction cues ('actually', 'not X') or which place is meant.
- **Where to build it:** backend/app/elicitation/places.py (positional, negation-aware match), extract.py (correction cue), session.py (put)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Correction cue -> treat as ANSWER | Detect 'actually', 'sorry', 'I mean', 'not X but Y' and put the new value with Source.ANSWER; pair with positional matching | free/open source | Small rule using existing precedence | Cue list per language |
| Positional, negation-aware district match only | Return matches with offsets, drop those after 'not', prefer ones tied to 'in/from/based' | free/open source | Fixes two-place sentences | Corrections still lose to the 0.90 answer |
| Disambiguation question when two districts appear | Selector re-ask | free/open source | Never wrong | Costs a question |
| Model-based slot filling | 0009 chain | free/open source | Handles phrasing | Absent offline; 1.1.3.2 already distrusts model-noted facts |

- **Recommended:** Correction cue -> treat as ANSWER. With positional matching it lets the founder fix a fact the moment they say it, offline, without spending a question.
- **Ruled out:** Positional match alone: corrections still lose; Disambiguation question: budget short; Model filling: absent offline and conflicts with 1.1.3.2.

### R065

**Narration keys are not version-scoped: a new version's verdict is never spoken** · weight 78 · Logic flaw · impact 4/5, reach 3/5, confidence 3/3 · flags F-B1-014

- **Evidence (B1):** agents/ideation.py:566-579 _next_novelty_point skips the statement once 'statement' is in s.narrated, and skips lever i once 'lever:{i}' is in it; :392 and :669 do the same for 'searching'. Nothing ever removes these keys (the only writes are appends at :392, 567, 572, 576, 669, 679). Lever keys are positional, so the panel reordering levers (1.3.1) changes which lever 'lever:0' means.

- **Why it matters:** After a lever choice and the 1.2.3 re-run, s.novelty holds the new verdict and levers, but 'statement', 'lever:0..2' and 'searching' are already narrated. The offline path stays silent about the new evidence: the founder chooses a lever and hears nothing about whether it helped, which is the whole point of 1.2.4. Positional keys also make a 'choose lever 2' refer to a different lever after re-ranking.
- **Where to build it:** agents/ideation.py (narrated keys prefixed with idea_version, levers keyed by a stable lever id), research/novelty.py (stable lever ids such as kind + gap hash)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Prefix narrated keys with idea_version and key levers by stable id | A string change at the six append sites | free/open source | A new version is narrated automatically; old keys stay as history; reordering is safe | Session format change (2.1.4) needs migration of old keys |
| Clear s.narrated when the version changes | One line in the version-change handler | free/open source | Simplest | Re-narrates council and other non-version items; loses the record of what was said |
| Track narration on each result object (result['narrated']) | Store the flag with the payload | free/open source | Goes away with the old result | Mixes delivery state into cached research results, which other sessions may share |
| Narrate a diff of old vs new verdict | Comparison step | free/open source | Tells the founder what changed | Builds on option 1; not a substitute for it |

- **Recommended:** Prefix narrated keys with idea_version and key levers by stable id. Smallest change that makes 1.2.3 audible. It survives 1.3.1 reordering, and lets a later 'what changed' sentence compare two versions' keys.
- **Ruled out:** Clear on change: also re-speaks the council and searching lines; Flag on the result: pollutes shareable cached results; Diff: an addition on top of option 1, not a replacement.

### R066

**No state between confirm and roadmap for choosing an opportunity card** · weight 78 · Missing logic · impact 4/5, reach 3/5, confidence 3/3 · flags F-B1-004

- **Evidence (B1):** elicitation/session.py:38-47 SessionState has only CONFIRMING -> GENERATING -> COMPLETE; agents/ideation.py:846-856 _advance turns a 'yes' at CONFIRMING into generate, and :684-689 calls build_roadmap with {'idea': _idea_text(s)}. Nothing branches on session.mode.

- **Why it matters:** In experience mode, a confirmed profile goes straight to build_roadmap with the self-description as the idea. No turn shows the cards or lets the founder choose one, and there is no rule for 'none of these fit' (re-rank, switch to idea mode, or stop). 1.1.5.5 assumes a writeback, but the state machine has nowhere to hold it.
- **Where to build it:** elicitation/session.py (new CHOOSING state), elicitation/engine.py (confirm in EXPERIENCE leads to choosing), agents/ideation.py (_advance, snapshot of the pending choice), routers/ideation.py (a choose action shared with 1.2.4)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Add a CHOOSING state with a choose action | Extends the existing enum state machine | free/open source | Explicit; resumable via snapshot (1.1.4); reusable by the lever choice in 1.2.4 | Changes the session format (2.1.4) |
| Treat cards as a dynamic question (add_dynamic) | Existing dynamic-question mechanism | free/open source | No new state | The free-text answer must be parsed into a card; uses one of the 3 dynamic slots shared with the panel |
| Switch mode to IDEA after the choice and restart elicitation | Reuse the IDEA path | free/open source | Simple | Re-asks confirmed facts; the turn count resets confusingly |
| python-statemachine / transitions library | Mature FSM libraries | free/open source | Guards and diagrams | A new dependency for one state |

- **Recommended:** Add a CHOOSING state with a choose action. One state plus one API action serves both the card choice here and the lever choice in 1.2.4. Both have the same shape: the founder picks one of N, the idea slots change, the version bumps. It also gives 'none fit' an explicit home.
- **Ruled out:** Dynamic question: wrong shape, and it uses up the shared 3-question cap; Mode switch: re-asks confirmed facts; FSM library: a dependency for a one-state change.

### R068

**Panel gives a verdict ('serious concerns') before any evidence exists** · weight 78 · Logic flaw · impact 4/5, reach 3/5, confidence 3/3 · flags F-A1-018

- **Evidence (A1):** backend/app/agents/ideation.py:676-688 a founder asking 'what do you think?' triggers _convene(s) whether or not s.scan is set; _council_work (:349-357) snapshots scan=None, novelty=None. _absorb (:442) waits for a scan before taking a panel result, but _convene applies it directly (:413-415). Probe: council.convene('solar dryer for copra farmers', {'district':'coimbatore'}, scan=None, novelty=None, use_model=False) -> band 'weak', voice brief 'Looking at it from seven angles, there are serious concerns to work through.'

- **Why it matters:** A founder who asks for an opinion on turn 2, while the search is still running, hears that the idea has serious concerns, built only on the absence of evidence (need 2 because nothing was found yet). The band, once narrated, is marked said and the later evidence-based view may be reported as 'unchanged'.
- **Where to build it:** backend/app/agents/ideation.py (_offline_stream, _convene), agents/council/__init__.py (convene)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Gate the panel on finished research | If s.scan is None, wait for the research job (it is already running) or answer 'I'll give the panel's view once the search finishes' | free/open source | No verdict without evidence; reuses the job board | One more 'still looking' line |
| Add an 'insufficient evidence' band | vote() returns band 'unclear' when the pack has no evidence items | free/open source | Honest wording in every path | A fourth band to handle in synthesis, cohort bands (5.5.3) and tests |
| Run the panel on profile and slots only, labelled as preliminary | Wording change | free/open source | Gives an answer | Still a judgement with no evidence; invites anchoring |

- **Recommended:** Gate the panel on finished research. Matches decision 0005 (fact check before speech) and the design's order S3-S5 before S6, with no new band.
- **Ruled out:** Unclear band: useful as a backstop but more surface; Preliminary verdict: still a verdict without evidence.

### R070

**Stage answers ignore negation: 'no customers yet' is stored as revenue** · weight 78 · Logic flaw · impact 4/5, reach 3/5, confidence 3/3 · flags F-A1-004

- **Evidence (A1):** backend/app/elicitation/answers.py:208-238 _stage takes the first stage whose word appears, revenue first, with no negation check. Probe: validate('stage','no customers yet') -> 'revenue'; 'not selling yet' -> 'revenue'; "we haven't launched" -> 'mvp'. Stored as ANSWER at 0.90 (engine.py:142), which outranks later extractions.

- **Why it matters:** A pre-revenue founder is recorded as selling; stage drives roadmap, schemes and funding (slots.py:238), so pre-revenue scheme flags (4.1.3) and the roadmap's start point are wrong, and later speech cannot correct it.
- **Where to build it:** backend/app/elicitation/answers.py (_stage), extract.py stage cues

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Negation window rule | Check for no/not/yet/haven't/illai/nahi within 3 tokens before a stage word and fall back to the lower stage | free/open source | Deterministic, tiny, same regex style as answers.py | Needs Tamil/Hindi negators; D7 Tanglish undecided |
| NegEx-style trigger list | Published negation algorithm (Chapman et al. 2001), easily ported to a word list | free/open source | Well-known pre/post trigger pattern | Built for clinical English; more machinery than a 6-value slot needs |
| spaCy dependency parse | Mature offline NLP library | free/open source | Real negation scope | Large model download, English only |
| Closed confirm when a negator is present | 'So you are not selling yet, right?' | free/open source | Safe | Spends a question from a short budget |

- **Recommended:** Negation window rule. Fixes the observed cases with the approach answers.py already uses, offline and testable against the eval set.
- **Ruled out:** NegEx port: heavier than needed; spaCy: big download, English-only; Confirm question: costs budget that is already short.

### R072

**The planner roadmap lives only in a session that expires in 6 h; nothing to track against** · weight 78 · Missing structure · impact 4/5, reach 3/5, confidence 3/3 · flags F-B2-022

- **Evidence (B2):** backend/app/agents/tools.py:330-333 and agents/ideation.py:538/690 store the roadmap only as s.roadmap inside the session document. backend/app/agents/store.py:29 IDLE_EXPIRY = 6 h hides the whole session afterwards (and D4 proposes 90 days at most). TASKS 1.4.2 says 'server-side storage later (3.1.3)', and 3.1.3 stores status 'on the founder's record', which holds no roadmap.

- **Why it matters:** A milestone tracker runs over months (the planner's months_realistic), but the roadmap it tracks vanishes the next day, or at the latest after retention. After 3.1.3 the founder record would hold statuses for milestone IDs with no roadmap to show them on: no titles, no dependencies, no critical path. 'A roadmap that moves' (P-31) has no durable roadmap to move.
- **Where to build it:** a persisted roadmap snapshot per founder and idea_version (the ideation schema's planned 'plans' table, SYSTEM-DESIGN 5.1) holding planner output plus status; 1.4.2 and 3.1.3 task text; it relies on 3.1.1 to know the founder

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Persist a roadmap snapshot (plan JSON + idea_version + statuses) on the founder when they confirm the plan | SYSTEM-DESIGN 5.1 already lists 'plans' in the ideation schema; a JSONB row like agent_sessions | free/open source | Outlives the conversation; one place for tracker, annotation and cohort progress | Needs 3.1.1 (sign-in) and a retention rule of its own |
| Keep the roadmap in the session and extend session lifetime for sessions with a roadmap | Reuses D4's 'saved idea' idea | free/open source | No new table | Ties a long-lived tracker to the whole transcript's retention (DPDP minimisation) |
| Recompute the roadmap on demand from stored slots | The planner is deterministic and offline | free/open source | No snapshot to store | Reference data changes alter the plan under the founder's feet, so statuses drift |

- **Recommended:** Persist a roadmap snapshot (plan JSON + idea_version + statuses) on the founder when they confirm the plan. Separates the long-lived plan from the short-lived transcript (better for DPDP), matches the design's planned 'plans' table, and gives 1.4.2, 1.4.1.1 and 5.5.3 one durable source.
- **Ruled out:** Longer session lifetime: keeps the whole transcript just to keep a plan. Recompute on demand: reference data updates silently reshape a plan the founder is part-way through.

### R074

**'Last 6 turns' trim has no turn boundaries and can orphan tool results** · weight 77 · Missing logic · impact 4/5, reach 4/5, confidence 2/3 · flags F-B1-022, F-A1-031

- **Evidence (B1):** agents/ideation.py:517 appends the assistant message (with tool_use blocks), :533 appends a user message made only of tool_result blocks; one founder turn can add up to 2*(MAX_TOOL_ROUNDS+1)+1 messages. providers.py:195-245 gemini_input pairs function_result with names collected from earlier function_call steps (names.get(..., '') gives an empty name for an orphan) and replays gemini_steps verbatim because 'they can carry signatures it requires'. providers.py:97 _plain_messages passes blocks straight to Anthropic, which rejects a tool_result whose tool_use is missing.
- **Evidence (A1):** backend/app/agents/ideation.py:208-224 the history starts with a synthetic user line '(The founder opened the ideation screen.)'; :523-538 each model round appends an assistant tool_use message and a user tool_result message, several per founder turn (MAX_TOOL_ROUNDS); _reword_stream pops and re-appends (:780, :821). Nothing records which messages belong to which founder turn. _facts (:285-287) treats every user string message as 'founder said', including the synthetic line and any summary inserted the same way.

- **Why it matters:** Trimming by message count can start the window on a tool_result, or between a Gemini function_call and its signature step. The provider returns an error, the breaker counts a failure (ideation.py:977-983), and the turn falls back to offline. After a few long turns the free model is effectively switched off for everyone, which is the opposite of 'fast, bounded turns'.
- **Where to build it:** agents/ideation.py (a context builder that cuts only at founder-text user messages and drops tool_use/tool_result pairs as units), agents/providers.py (adapters tolerate a window that starts at a user text)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Turn-boundary window: keep the last N founder turns, each as a whole exchange | Founder turns are already marked by string-content user messages (ideation.py:948) | free/open source | Never orphans a pair; provider-neutral | A turn with many tool rounds can still be large; cap tool_result size too |
| Drop all past tool exchanges, keep only text, and restate results in the facts block | Results already live in s.scan, s.novelty, s.roadmap | free/open source | Smallest context; pairs cannot break | Gemini loses its own earlier signed steps; it must tolerate text-only history |
| Token-count trimming with tiktoken / provider token counters | Common libraries | free/open source | Exact budget | Still needs the boundary rule; tiktoken does not count Gemini or Claude tokens exactly |
| Gemini server-side history (store: true / previous interaction) | Interactions API | free tier | No resend | Keeps founder text on Google's side; providers.py:284 deliberately sets store False (privacy, 1.5.4) |

- **Recommended:** Turn-boundary window: keep the last N founder turns, each as a whole exchange. The only rule that is correct for all three adapters. Combine it with option 2 for turns older than the window: their tool results are already in s.scan, s.novelty and s.roadmap and are summarised in the facts block.
- **Ruled out:** Text-only history alone: risky for Gemini's signed steps within the current turn; Token counters: an add-on, not a cut rule; Server-side history: sends founder text to be kept by Google, against the store:false choice.

### R076

**A stream cut before 'done' is treated as a finished turn** · weight 77 · Missing logic · impact 4/5, reach 4/5, confidence 2/3 · flags F-B1-009

- **Evidence (B1):** agentClient.ts:196-198: reader.read() returning done just breaks and the promise resolves. There is no check that a 'done' event arrived. Talk.tsx:163-205 then shows no error and appends whatever partial reply was heard. On the server (routers/ideation.py:346-352) a disconnect before 'done' cancels the generator before _save, so the turn is not stored.

- **Why it matters:** On 2G the most common failure is a dropped connection mid-reply. The founder is left with half a sentence and no sign that their answer was lost, and the client has no signal telling it to retry with the same client_turn_id. Idempotency (1.1.4.1) is useless if nothing triggers the retry.
- **Where to build it:** agentClient.ts (streamTurn rejects with a 'truncated' error when the stream ends without done), Talk.tsx (automatic retry with the same client_turn_id, with backoff)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Done-sentinel check plus automatic retry with the same client_turn_id | A few lines in the existing hand-written parser | free/open source | Pairs directly with server idempotency; invisible to the founder | Needs a retry cap and backoff |
| @microsoft/fetch-event-source | Widely used SSE client for POST streams, with retry hooks | free/open source | Retry and error hooks built in | New dependency; still needs the done check and the turn id |
| Fall back to GET snapshot after any truncated stream | Existing resume endpoint | free/open source | Shows the true state | Cannot tell 'not applied' from 'applied' without the turn id; an extra round trip on a slow link |
| WebSocket turn channel | FastAPI WebSockets | free/open source | Explicit connection state | Rewrites the transport; worse behind proxies on mobile networks |

- **Recommended:** Done-sentinel check plus automatic retry with the same client_turn_id. Smallest change that closes the loop with 1.1.4.1: the retry either replays the saved events or runs the turn for the first time, and the founder sees one reply either way.
- **Ruled out:** fetch-event-source: a dependency for what is a 3-line check; Snapshot-only fallback: ambiguous without the turn id; WebSocket: a transport rewrite with poorer mobile behaviour.

### R078

**Job board and background results are never pruned or expired** · weight 74 · Missing logic · impact 3/5, reach 4/5, confidence 3/3 · flags F-B5-012, F-A1-015, F-A2-012, F-A5-029

- **Evidence (B5):** backend/app/agents/jobs.py:57-59 Board keeps jobs, results (MemoryResults, results.py:35-61) and listeners per session; they are removed only by forget() (jobs.py:117-124), called only from the founder's delete (routers/ideation.py:318). Sessions vanish from the store after 6 idle hours (store.py:29, 48-49) but their payloads (scan, novelty, council JSON) stay in process memory. When the database is missing, get_store falls back to MemoryStore (store.py:245), also in-process.
- **Evidence (A1):** backend/app/agents/jobs.py:56-60 Board keeps jobs, results (MemoryResults) and listener sets in process dicts; the only removal is forget() (jobs.py:117-124) called from the DELETE route (routers/ideation.py:318). agents/store.py:29 sessions expire after 6 h idle but nothing calls forget on expiry. Each stored research payload includes 'idea': text (scan.py:285).
- **Evidence (A2):** backend/app/agents/jobs.py:58-60 and backend/app/agents/results.py:39: Board.jobs and MemoryResults._rows are pruned only by Board.forget on an explicit delete (jobs.py:117-124). Probe (scratchpad/a2/probe4.py): after 1000 sessions each ran one job, 1000 jobs and 1000 results (full scans with idea-derived queries) were still held. Sessions are hidden after 6 idle hours (store.py:29), but their results stay for the life of the process. A turn already in progress when DELETE arrives (agent_delete does not take _turn_locks, routers/ideation.py:313-319) can call board.start after forget(), leaving results for a deleted session. Task 2.3.1 adds a results table, but 3.2.4's retention and erasure list names 'sessions, transcripts, documents and consents', not results.
- **Evidence (A5):** backend/app/agents/jobs.py:58-59 Board.jobs and MemoryResults._rows (agents/results.py:38-45) keep one entry per session and kind; the only removal is forget() on an explicit delete (routers/ideation.py:318). Sessions expire from the store after idle time, but their research (scan+novelty about 17-22 KB JSON in the eval fixtures, plus the Task object holding the same payload) and council results stay. MemoryResults.latest() (results.py:51-57) scans every row of every session.

- **Why it matters:** Memory grows with every conversation until restart, and expired or erased sessions' evidence and panel results remain in the app after the session is gone, which conflicts with erasure (3.2.4). A scripts/nightly.py process, as 5.4.4 plans, cannot see or clear any of this; it only reaches PostgreSQL and Redis.
- **Where to build it:** agents/jobs.py and agents/results.py (expiry), app startup (an in-process periodic task), 5.4.4's split between in-process and external steps

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| In-process periodic sweep tied to the store's expiry | An asyncio task started in the FastAPI lifespan that drops board entries idle longer than IDLE_EXPIRY | free/open source | Reaches exactly the memory that leaks; no new dependency; same rule as the store | Runs per process; must not cancel running jobs |
| TTL dict (cachetools.TTLCache) for results and jobs | Mature, popular Python caching library | free/open source | Expiry without a sweeper | Expiry on access/size only; a running job's entry could be evicted mid-run; new dependency |
| Wait for the results table (2.3.1) and expire rows nightly | Planned database results table | free/open source | Nightly SQL delete works from any process | Blocked on the database (2.1.1); leak continues until then; board.jobs still in memory |
| APScheduler inside the app for all nightly steps | Widely used Python scheduler with asyncio support | free/open source | One place for in-process housekeeping | With several workers each runs every job unless a lock is added |

- **Recommended:** In-process periodic sweep tied to the store's expiry. Smallest fix for a leak that exists today, independent of the database, and it applies the same 6-hour rule the store already uses; the external nightly script keeps the steps that touch disk, database and Redis.
- **Ruled out:** TTLCache: can evict a running job's entry; waiting for 2.3.1: leaves the leak open behind the database blocker; APScheduler for everything: duplicates runs per worker and adds a dependency for one sweep.

### R081

**Browser profile keys/vocabularies don't map to backend slots** · weight 74 · Missing logic · impact 3/5, reach 4/5, confidence 3/3 · flags F-B2-015, F-B3-017

- **Evidence (B2):** backend/app/elicitation/engine.py:59 PROFILE_SLOTS = ('district','founder_years','founder_skills','owned_assets','sector'), and :118-120 put any non-empty profile value at confidence 0.95 with Source.PROFILE, unvalidated. frontend/src/voice/agentClient.ts:99-103 startSession sends only name and private, never the profile. The profile model names the sector 'domain' (models/startup.py, String 255) and stage free text, and holds no founder_years, founder_skills or owned_assets. routers/ideation.py:250-251 says profile values are 'never asked again'.
- **Evidence (B3):** The frontend ProfileDraft is nested {founder:{district,...,caste_category,phone,date_of_birth}, startup:{domain,stage,...}} (completeness.ts:5-30; profileStore.ts). engine.start reads flat keys PROFILE_SLOTS = district, founder_years, founder_skills, owned_assets, sector (engine.py:59). Ran engine.start with the nested shape {founder:{district:'Madurai'}, startup:{stage:'idea'}}: slots = {} (nothing filled). Even with flat keys, stage is not in PROFILE_SLOTS, and next_question asked 'Where are you today...' (stage) although the profile held it. The browser profile has no founder_years, founder_skills, owned_assets or sector fields at all. AgentStartIn.profile is an unbounded dict (routers/ideation.py:256).

- **Why it matters:** Implemented as planned ('pass the profile store's fields'), 1.1.1 fills nothing and the founder is still asked their district and stage. Passing the whole draft also sends caste category, phone and date of birth into a conversation that has no purpose for them, against the per-purpose consent rule from step 2.
- **Where to build it:** agentClient.ts startSession (an explicit projection), engine.py PROFILE_SLOTS (add stage; map startup.domain to sector), routers/ideation.py (a typed profile model with only allowed keys)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Explicit allowlisted projection in the client (founder.district to district, startup.stage to stage, startup.domain to sector) plus a typed AgentStartIn.profile with only those keys | A few lines of TypeScript and one Pydantic model | free/open source | Fills the slots that exist; nothing protected leaves the browser; extra keys rejected | The mapping must be kept in step with both sides |
| Flatten the whole draft on the server and pick known keys | Server-side dict handling | free/open source | Client stays simple | Protected fields still travel to the server |
| Wait for server profiles (3.1.2) and read them by user_id | Planned founders table | free/open source | One source of truth | Blocked on 2.1.1 and 3.1.2; anonymous founders get nothing |
| Generate the mapping from a shared schema (OpenAPI types) | openapi-typescript, as proposed for purposes in step 2 | free/open source | Compile-time agreement | Build-step work for five fields |

- **Recommended:** Explicit allowlisted projection in the client (founder.district to district, startup.stage to stage, startup.domain to sector) plus a typed AgentStartIn.profile with only those keys. It is the smallest change that actually removes the repeat questions, and it keeps protected fields in the browser. Add stage to PROFILE_SLOTS and validate each value as in the previous flag. Its API test (1.1.1.2) should use the real nested draft, not a flat fixture.
- **Ruled out:** Server-side flattening: protected fields still leave the browser for no purpose. Waiting for 3.1.2: blocked, and anonymous founders keep being re-asked. Generated types: worthwhile with the purpose registry, but heavy for this mapping alone.

### R085

**A text-only planner call silently drops slot-gated milestones; Ideate and Talk still differ** · weight 74 · Logic flaw · impact 3/5, reach 4/5, confidence 3/3 · flags F-B2-026

- **Evidence (B2):** Ran build_plan('smart pump controller for farmers') with no slots: 14 milestones with no c_grant. With slots {'funding_route':'grant', ...}: 15 milestones including c_grant. The applies conditions in common.json (c_name product_form; c_compliance has_regulatory; c_grant/c_loan/c_equity funding_route) drop the milestone when the field is unknown, with no note in the output. PlanIn (models/ideation_schemas.py:91-93) takes free text plus optional slots; the Ideate screen has only the idea text. Talk calls build_plan with the session's slots (agents/tools.py:229-232).

- **Why it matters:** 1.4.1.2 ('Ideate screen reads the planner roadmap') would call the planner with text only, so the same idea still yields two plans: Talk's with funding and compliance steps, and Ideate's without. That is the exact problem 1.4.1 exists to remove. A founder seeing the Ideate plan gets no sign that steps depend on unanswered questions, which goes against 'unknown is said honestly'.
- **Where to build it:** backend/app/planner/plan.py (unknown applies field: keep the milestone as 'depends on your answer to X', or list it under next_questions); 1.4.1.2 (Ideate reads the session's stored roadmap or sends session_id, not free text)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Ideate shows the session's stored planner roadmap (by session ID), and the planner marks milestones whose condition is unknown | The roadmap already lives in s.roadmap; plan.py already returns next_questions | free/open source | Truly one roadmap; honest about unknowns | Ideate needs a session (an anonymous one is fine) |
| Ideate runs a short slot form before calling /ideation/plan | PlanIn already accepts slots | free/open source | Works without a conversation | A second questionnaire that can disagree with the Talk answers (what 1.4.3 tries to remove) |
| Unknown conditions default to including the milestone | A simple rule change in plan.py | free/open source | Nothing silently lost | Shows grant, loan and equity steps to everyone, and the plan gets longer and wrong in the other direction |

- **Recommended:** Ideate shows the session's stored planner roadmap (by session ID), and the planner marks milestones whose condition is unknown. Only reading the same stored roadmap guarantees one plan per idea, and marking unknown conditions turns silent pruning into a question the founder can answer.
- **Ruled out:** Slot form: a second fact source, which 1.4.3 already flags as the problem. Include by default: replaces silent omission with silent over-inclusion.

### R086

**Answers to dynamic questions are stored but never used, restated or labelled** · weight 74 · Missing logic · impact 3/5, reach 4/5, confidence 3/3 · flags F-B4-019

- **Evidence (B4):** backend/app/elicitation/engine.py:135-138 stores the reply in d['answer']. A repo-wide grep shows no reader of d['answer'] or session.dynamic beyond engine.py and agents/ideation.py:878 (which looks up the question text). restate() (engine.py:301-360) ignores dynamic answers; build_plan, the council and the scheme tools never receive them. The offline reply also reads the same scan questions out as 'Things to think through' (agents/ideation.py:647-649), so after 1.2.5 a point can be both read out and asked.

- **Why it matters:** The founder spends one of seven questions and their answer goes nowhere on the offline path. On the model path it lives only in the transcript, not in any fact the roadmap, panel or confirmation reads. 1.2.5 multiplies this; 1.1.2's source labels cannot show it because it is not a slot.
- **Where to build it:** backend/app/elicitation/engine.py (dynamic answers become facts with Source.ANSWER), restate(), and the council and planner inputs (agents/ideation.py _council_work, planner/plan.py)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Bind each scan or panel question to a consumer: an existing slot, a named risk or gate it resolves, or a free-text 'founder notes' list passed to the panel and shown in the restatement | FIELD_QUESTIONS and panel questions already relate to risks; the planner has risks_by_phase | free/open source | Every asked question has a reader; answers appear in confirmation and the roadmap | Needs a mapping per question family |
| Pass all dynamic answers to the panel only | Council already takes slots | free/open source | Small change | Roadmap and confirmation still ignore them |
| Stop asking; only read points out | Today's offline behaviour | free/open source | No wasted questions | Drops 1.2.5's goal of domain-fitting questions |

- **Recommended:** Bind each scan or panel question to a consumer: an existing slot, a named risk or gate it resolves, or a free-text 'founder notes' list passed to the panel and shown in the restatement. A question is only worth a turn if its answer changes something. Binding makes that testable (1.2.5.2) and lets the restatement label 'you said' for these answers.
- **Ruled out:** Panel only: confirmation and roadmap still blind; read-only: abandons the task's purpose.

### R089

**Experience questions are idea-worded and ask money before skills** · weight 74 · Logic flaw · impact 3/5, reach 4/5, confidence 3/3 · flags F-B1-002

- **Evidence (B1):** slots.py:186 'Which sector does this sit in?', :197 'Is this software, a physical product...?', :236 'just an idea, a prototype, already selling?' are asked verbatim in experience mode (same run, turns 0, 1, 5). capital_band and funding_route are asked at turns 2-3, before founder_skills (turn 6). TASKS.md 1.1.5 'When' says financial-capacity questions wait on 3.2.1, yet both slots are REQUIRED in experience mode today.

- **Why it matters:** A founder who has just said they have no idea is asked what 'this' is and whether 'this' is software, then how much money they can put in, before anyone asks what they can do. The slot table contradicts the plan's own rule (money waits on consent 3.2.1). The 1.1.3.1 'what before anything' gate has no 'what' to wait for in this mode, so it either blocks forever or does not apply.
- **Where to build it:** elicitation/slots.py (question text per mode), elicitation/selector.py (the 1.1.3.1 gate must name the experience-mode anchor, founder_skills), the experience REQUIRED set

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Per-mode question text on Slot (question_by_mode) | Data-only change beside the slot table | free/open source | One table, testable, translatable with 1.5.1 | Slot dataclass grows a field |
| Separate experience slot keys (exp_sector, ...) | Parallel slots | free/open source | Clear wording | Duplicates slots; violates the 'same machine' docstring and elicit-once |
| Let the model reword questions per mode | Decision 0009 chain | free tier | Natural wording | The offline path stays wrong; 0002 says code decides |
| Neutral wording for all modes | Edit strings | free/open source | Trivial | Loses specificity on the idea path |

- **Recommended:** Per-mode question text on Slot (question_by_mode). Keeps the single machine and works offline. Do it together with defining the 1.1.3.1 gate anchor per mode (WHAT = problem in IDEA, founder_skills in EXPERIENCE) and moving capital_band/funding_route out of the experience REQUIRED set until 3.2.1.
- **Ruled out:** Separate slot keys: duplicate the elicit-once contract; Model rewording: the offline floor stays broken and code must decide (0002); Neutral wording: degrades the main path.

### R093

**Generic words from registry prose take query slots ('banana small chips')** · weight 74 · Logic flaw · impact 3/5, reach 4/5, confidence 3/3 · flags F-A1-016

- **Evidence (A1):** backend/app/research/terms.py:263-292 public_vocabulary() takes every word of every registry summary (1,604 words), including small, building, local, village, people, first, home, cheap; build_queries (:318-339) fills the papers query with the first two such content words. Probe: 'I want to start a small business making banana chips for local shops' -> papers query 'banana small chips'; 'solar dryer for copra farmers in my village' -> 'photovoltaic smallholder agriculture village'; 'I am building KaruvaduKart...dried fish' -> 'building dried'.

- **Why it matters:** Searches are sent with filler words that cut recall and pull irrelevant papers into the evidence and the closest-paper line. 1.2.1.4 removes generic words from the novelty element list only, not from the outgoing queries; 1.2.6 grows the vocabulary but nothing shrinks its filler.
- **Where to build it:** backend/app/research/terms.py (public_vocabulary, build_queries)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Query stopword list beyond STOP | Hand-reviewed list (small, building, local, village, first, home, cheap, people...) applied in build_queries | free/open source | Immediate, reviewable | Manual list |
| Document-frequency filter over the registry | Drop vocabulary words that appear in more than N% of registry summaries | free/open source | Automatic, data-driven | Threshold tuning; could drop real domain words |
| Use only lexicon terms and registry labels, not summaries | Narrower vocabulary source | free/open source | Clean queries | Recall falls further (0004 consequence) |
| scikit-learn TF-IDF weighting of content words | Mature free library | free/open source | Principled ranking | Heavy dependency for a word list |

- **Recommended:** Document-frequency filter over the registry. Removes filler automatically as the registry grows (5.6), with a small reviewed exception list.
- **Ruled out:** Stopword list alone: decays as the registry grows; Labels only: further recall loss; TF-IDF via scikit-learn: dependency out of proportion.

### R099

**No town-to-district gazetteer: 'Pollachi' is not recognised, so district is re-asked** · weight 74 · Missing structure · impact 3/5, reach 4/5, confidence 3/3 · flags F-A1-006

- **Evidence (A1):** backend/app/elicitation/places.py:9-48 has 38 districts and about 25 aliases; find_district('Pollachi') -> None (also absent: Kumbakonam, Rajapalayam, Karaikudi, Mettupalayam, Ambur, Tambaram). tests/eval/ideas.json:140 has an eval idea 'coconut unit in Pollachi'. backend/app/banking/data/branches_tn5.json _meta already cites the India Post pincode directory.

- **Why it matters:** Founders name their town, not the administrative district; the agent spends a question on 'Which district?' after being told, and the restatement lists district as unknown.
- **Where to build it:** backend/app/elicitation/places.py plus a reference file (e.g. backend/app/elicitation/data/tn_towns.json) with a data check in CI (5.2)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| India Post all-India pincode directory (data.gov.in) | Open Government Data licence; office name -> district for every TN post office; already a source of the banking data | free/open source | Covers towns and villages, cited, offline once committed | Office names carry suffixes (S.O, B.O) and duplicates to clean |
| Local Government Directory (LGD) towns and villages | Official codes from the Ministry of Panchayati Raj | free/open source | Authoritative district codes | Clunky bulk export; transliteration variants |
| OpenStreetMap place nodes (Geofabrik TN extract) | ODbL, free download | free/open source | Common spellings and Tamil names | Attribution duties; spatial join to districts |
| Hand-curated alias list | Extend the DISTRICTS dict by review | free/open source | Simplest | Never complete |

- **Recommended:** India Post all-India pincode directory (data.gov.in). Free, cited, already among the repo's sources, and gives a statewide town -> district map in one committed file.
- **Ruled out:** LGD: harder export for the same result; OSM: licence and spatial-join overhead; Hand list: incomplete by construction.

### R101

**Only 52% of offline sentences are translated; one language tag per reply mislabels the rest** · weight 74 · Logic flaw · impact 3/5, reach 4/5, confidence 3/3 · flags F-B5-023

- **Evidence (B5):** Ran scratchpad/arena/b5/tcov.py (reuses scripts/voice_coverage.py's offline replay of tests/eval): 'ideas: 10 sentences: 304 with a Tamil translation: 159 (52%)'. phrasebook.translation (voice/phrasebook.py:50-52) is an exact match on normalised English, so sentences with figures, names, novelty points and roadmap lines never match. The done event carries one 'language' for the whole reply (agents/ideation.py:1006); TASKS 1.5.1.2 plans to set it, still one value.

- **Why it matters:** A Tamil-speaking founder on the offline path would get replies that switch language mid-answer, and the voice layer, choosing one voice from the reply language, would read English sentences with a Tamil voice or the reverse. The 'whole conversation in the founder's language' outcome is about half met, and nothing records which sentences fell back.
- **Where to build it:** agents/ideation.py (_offline_stream: per-sentence language on each 'sentence' event), frontend voice playback (pick voice per sentence), voice_coverage.py (report translation coverage as well as recording coverage)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Language on each sentence event plus a coverage report | The sentence event is already per sentence; add {text, language}; extend scripts/voice_coverage.py to print translation coverage per language | free/open source | Voice and captions stay correct for mixed replies; the coverage number guides which templates to translate next | Event shape change on the client |
| Parameterised templates (slot-filled translations) | Translate templates with placeholders ('{n} papers ...') and fill digits and names at run time, like gettext/ICU MessageFormat | free/open source | Covers the sentences with figures, the largest uncovered group | Templates in ideation.py must be refactored to named formats; Tamil/Hindi grammar around numbers needs reviewer input (1.5.2) |
| Babel/gettext catalogues | Standard Python i18n toolchain | free/open source | Mature extraction and plural handling | Heavier than a 38-entry JSON; still needs the template refactor |
| Whole reply in English when any sentence lacks a translation | All-or-nothing rule | free/open source | Never mixed | Tamil appears in only a minority of replies, defeating the task |

- **Recommended:** Language on each sentence event plus a coverage report. Makes the partial coverage honest and correctly voiced now, and the coverage report points to the parameterised templates as the next step.
- **Ruled out:** Parameterised templates alone: a larger refactor that still leaves a mix until done; gettext: tooling heavier than the data; all-or-nothing: would hide Tamil in most turns.

### R103

**Reordering inside SYSTEM leaves the history uncacheable; the 1.6.1 window shifts it** · weight 74 · Logic flaw · impact 3/5, reach 4/5, confidence 3/3 · flags F-B1-025

- **Evidence (B1):** agents/ideation.py:66-110 SYSTEM has {name} at char 122, {language_rule} on line 7, {question} and {known} at the end; :489-496 appends per-turn 'news' to the same system string. Both caching providers place system before the conversation: Anthropic body {system, messages, tools} (providers.py:111-121); Gemini body {system_instruction, input} (providers.py:280-290). 1.6.1 plans 'facts, a rolling summary and the last 6 turns', so the first message sent changes every turn, and the summary is rewritten every 8 turns.

- **Why it matters:** A prompt cache matches a byte-identical prefix. With the question, known facts and news still inside system, and only moved to its end, the cacheable prefix is the static instructions plus tools (about 1.5k tokens). The growing history after it, which is where long chats get slow, can never hit. 1.6.1's sliding window and summary rewrite change the start of the messages on every turn as well. Done separately, the two tasks cancel each other out, and the outcome 'lower latency' is not reached.
- **Where to build it:** agents/ideation.py (_llm_stream: system = static instructions only; per-turn context as a block at the start of the newest user message; the window advances in steps at summary checkpoints), agents/providers.py

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Static system + per-turn context in the newest user turn + checkpointed window | Standard prefix-caching layout: stable tools/system, append-only history, volatile tail last | free/open source | System, tools and history up to the last checkpoint stay identical between turns, so both Gemini implicit caching and Anthropic cache_control can hit; name and language move to the tail too | Context is a little larger between checkpoints (up to 8 turns + summary instead of 6) |
| Reorder within SYSTEM only (as planned) | 1.6.2.1 as written | free/open source | Tiny change | Caches only about 1.5k tokens; the history is never cached |
| Gemini explicit context cache (cachedContents) | Gemini API feature | free tier | Guaranteed reuse of a named prefix | Stores content on Google's side with a TTL, against store:false (providers.py:284) and the 1.5.4 notice; unclear free-tier availability |
| Skip caching; rely on 1.6.1's bound alone | Bounded context already caps latency | free/open source | No coupling | Re-reads up to 8k tokens every turn on a free tier with rate limits |

- **Recommended:** Static system + per-turn context in the newest user turn + checkpointed window. The only layout in which 1.6.1 and 1.6.2 support each other. Treat them as one change to prompt assembly, with a test that two consecutive turns produce byte-identical request prefixes up to the newest user message.
- **Ruled out:** Reorder within SYSTEM: caches the small part and misses the large one; Explicit cachedContents: keeps founder text on Google's side, against store:false; No caching: wastes free-tier input budget on every turn.

### R105

**Shared cap of 3 is first-come: scan points shut out the review panel's question** · weight 74 · Logic flaw · impact 3/5, reach 4/5, confidence 3/3 · flags F-B4-018

- **Evidence (B4):** backend/app/elicitation/engine.py:274-285 add_dynamic refuses once len(session.dynamic) >= MAX_DYNAMIC (3), whatever the source; agents/ideation.py:398-401 adds the panel's synthesis question the same way. Research finishes before the panel (it runs first, and the panel uses its result), so after 1.2.5 the scan fills the slots first. Ran: three 'scan' questions added, then add_dynamic(..., 'review panel') returned None. research/scan.py:305 always appends a generic 'Any idea' group, so even a weak scan has points to fill the cap.

- **Why it matters:** The panel's question is designed to target where the evidence and the advisers disagree most (engine.py:189-190), the most valuable dynamic question, yet it is the one dropped. 1.2.5 says 'at most 3, shared with the panel' but sets no priority.
- **Where to build it:** backend/app/elicitation/engine.py add_dynamic (priority or per-source quota), agents/ideation.py (one scan point, never from the 'Any idea' group)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Per-source quota: scan at most 1 (per 1.2.5.1), panel at most 2; a higher-priority arrival replaces an unasked lower one | Small change to the dynamic list (source field already stored) | free/open source | The panel is never shut out; deterministic | Needs a priority order written down |
| Priority queue scored by source and domain match | heapq in stdlib | free/open source | Flexible | Scores are new uncalibrated constants (5.1.3 already has too many) |
| Delay scan questions until the panel has reported | Job board knows when the council job is done | free/open source | Panel first by construction | Couples the turn loop to panel latency; the scan question may never come |

- **Recommended:** Per-source quota: scan at most 1 (per 1.2.5.1), panel at most 2; a higher-priority arrival replaces an unasked lower one. Matches 1.2.5.1's 'one scan point', guarantees room for the panel and needs no new tuning constants.
- **Ruled out:** Priority scores: more uncalibrated weights; delay until panel: ties question order to background job timing.

### R106

**Synthesis quotes a seat's first claim whatever criterion it was about** · weight 74 · Logic flaw · impact 3/5, reach 4/5, confidence 3/3 · flags F-A1-020

- **Evidence (A1):** backend/app/agents/council/synthesis.py:191-202 picks the seat with the best/worst score on a criterion and speaks seat.claims[0], but Claim (seats.py:284-286) has no criterion field. Probe (rules mode): 'The weakest point is who needs it and pays for it: the closest Vanigam domain names its usual buyers.' — a neutral claim presented as the weakness; for model seats any claim (e.g. about patents) can be attached to 'cost and money'.

- **Why it matters:** The founder hears a reason that does not support the judgement it is attached to, which reads as nonsense or, worse, as a real weakness; the fact check passes because the claim itself is cited.
- **Where to build it:** backend/app/agents/council/seats.py (Claim gains criterion), model.py (prompt asks for it), rules.py, synthesis.py

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Criterion field on each claim, validated against CRITERIA | Pydantic field; synthesis picks a claim with the matching criterion or says none | free/open source | Correct pairing; checkable | Model prompt and rules all change |
| Pick by keyword overlap between claim and criterion words | Heuristic in synthesis | free/open source | No schema change | Fragile across languages |
| Speak only the score, not a claim | Drop the quote | free/open source | Never mismatched | Less useful, no reason given |

- **Recommended:** Criterion field on each claim, validated against CRITERIA. Makes the pairing explicit and testable, in line with 'code decides, the model words it'.
- **Ruled out:** Keyword overlap: unreliable; Score only: removes the reason founders need.

### R107

**Talk page discards the only delete handle while the database row survives** · weight 74 · Logic flaw · impact 3/5, reach 4/5, confidence 3/3 · flags F-B3-013

- **Evidence (B3):** Talk.tsx:121-136 resumes from localStorage and on ANY failure calls save(null), which removes the stored session ID (:50-52), including a network error. Every store hides a session idle more than 6 hours (agents/store.py:29, SqlStore.get :95), but SqlStore.delete (:134-145) still deletes the row. No retention job exists yet (3.2.4.2 waits on D4 and D12). 1.1.7's plan has the delete control clear the local ID, so it inherits this.

- **Why it matters:** A founder who returns the next day finds the conversation gone, and the page has thrown away the ID they would need to delete it. The transcript stays in PostgreSQL with no expiry, and nobody can remove it. A dropped request on 2G does the same to a live session.
- **Where to build it:** Talk.tsx (resume handling, delete control), agentClient.ts, routers/ideation.py (a distinct 'expired' answer), agents/store.py

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Keep the ID on failure; on a 404 'expired' answer offer 'delete it' alongside 'start fresh' | A distinct status from the resume route (e.g. 410 Gone for hidden-but-present) and a small UI branch | free/open source | The founder keeps control; network errors no longer lose sessions | One more response code to document |
| Delete server-side when a hidden session is found on resume | One call in agent_resume | free/open source | No orphan rows | Deletes without asking; conflicts with D4's 90-day intent |
| Wait for the retention job (3.2.4.2) | Plan as written | free/open source | No new code | Blocked on D4/D12; rows pile up meanwhile |
| Keep a list of all past session IDs in localStorage with a 'my conversations' list | Small React state | free/open source | Founder can delete any past one | Lost when browser data is cleared; still device-bound until 3.1 |

- **Recommended:** Keep the ID on failure; on a 404 'expired' answer offer 'delete it' alongside 'start fresh'. It is the smallest change that keeps the founder able to erase what the server still holds, and it fixes the 2G case that 1.1.4 cares about. The 'my conversations' list can follow with 3.1.
- **Ruled out:** Silent server-side delete: removes data without the founder's choice and contradicts D4. Waiting for retention: blocked on owner decisions while rows accumulate. Local list alone: still loses IDs on a network error unless the resume handling is fixed first.

### R110

**The panel sees only the first 4 levers, and their order is fixed by kind** · weight 74 · Logic flaw · impact 3/5, reach 4/5, confidence 3/3 · flags F-B3-021

- **Evidence (B3):** research/novelty.py:254-320 appends levers in a fixed order: up to 2 'combine', then localise, re-target, regulatory route (health), cost-down and business model. That is up to 7, ordered by kind, not by gap size as 1.3.1's Why says. The panel's evidence pack takes only levers[:4] (council/evidence.py:149-150), and the narrator speaks only levers[:3] (agents/ideation.py:574). The prior-art seat proposes 'novelty:lever:0' as its variant (council/rules.py:135-143), which vote.py:129-136 weights into the panel's variants.

- **Why it matters:** A lever in 5th place or later, often the regulatory route for a real medical device or cost-down when a cost pack exists, can never be ranked by the panel or heard by the founder. The panel's 'ranking' would also be biased toward the fixed first lever, because one seat already endorses lever 0 as its variant before any scoring.
- **Where to build it:** research/novelty.py (no cap and no implied order in _levers), council/evidence.py (pass all levers with stable ids), council/rules.py (prior_art variant chosen after scoring, not as lever 0), narration (speak the top 3 of the panel's order)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Pass every lever to the panel with stable ids; seats score each; the vote orders them; the narrator speaks the top 3 of that order | Extends the existing seat and vote structures (seats.py, vote.py); deterministic rule seats score by the evidence each lever cites | free/open source | Ranks the full set; removes the hidden cap; the variant comes from the ranking, not position | Seven levers per seat make model-seat prompts longer on the free tier |
| Pre-rank by a deterministic gap score (papers count, local startups) before the panel, then pass the top 4 | Data already in the novelty result | free/open source | Cheap and predictable | The panel still never sees the rest; a gap count misjudges regulatory levers |
| Raise both caps to the full list without panel scoring | Change two slice constants | free/open source | Nothing hidden | The founder hears up to 7 levers at one per turn, too long against the 7-question budget |
| Learning-to-rank model (e.g. LightGBM ranker) | Mature open-source ranker | free/open source | Data-driven ordering | No outcome data to train on (Dropped: learning ladder) |

- **Recommended:** Pass every lever to the panel with stable ids; seats score each; the vote orders them; the narrator speaks the top 3 of that order. It is what 1.3.1 means, without the hidden caps and the lever-0 bias. It reuses the stable ids from the previous flag, and 1.3.2's per-lever objection can attach to the same ids. Model seats can receive the levers in compact form to keep prompts small.
- **Ruled out:** Deterministic pre-rank: keeps levers hidden from the panel and misjudges regulatory ones. Raising the caps: far too many narrated turns. Learning to rank: no outcome data, the reason the plan dropped learned weights.

### R113

**The 'five-finger' stop rule checks four fingers: WHY has no required slot** · weight 73 · Logic flaw · impact 3/5, reach 5/5, confidence 2/3 · flags F-A1-008

- **Evidence (A1):** backend/app/elicitation/slots.py:320-350 why_now, differentiation and motivation are all ENRICHING; selector.py:196 and 214-222 require only fingers that own a required slot. Probe: fingers required = {what, how, who_where, when}. Enrichment is never reached in practice because required slots use up the budget first.

- **Why it matters:** The completeness contract the client asked for never asks why the idea matters now or how it differs, so the review panel and novelty narration have no founder-stated differentiation to test.
- **Where to build it:** backend/app/elicitation/slots.py (fingers_covered rule), selector.py

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Promote differentiation to REQUIRED | Slot table change | free/open source | Feeds novelty and the devil's-advocate seat (1.3.2) | A 10th required slot on a short budget |
| WHY satisfied by any of why_now / differentiation / motivation, including extraction | Finger rule change | free/open source | No extra question if the pitch already said why | Needs extractor cues for why |
| Let a scan-derived dynamic question cover WHY | 1.2.5 feeds add_dynamic | free/open source | Domain-specific | Optional, capped at 3, may never fire |
| Record that WHY is intentionally optional | Decision record | free/open source | No code | Contradicts the stated contract |

- **Recommended:** WHY satisfied by any of why_now / differentiation / motivation, including extraction. Honours the five-finger contract without automatically spending another question.
- **Ruled out:** Promote differentiation: worsens the budget shortfall; Dynamic question: not guaranteed; Record only: leaves the contract broken.

### R116

**A lever choice after the roadmap leaves roadmap, panel and state on the old version** · weight 71 · Missing logic · impact 4/5, reach 3/5, confidence 2/3 · flags F-B1-015

- **Evidence (B1):** agents/ideation.py:120-124: s.roadmap, s.novelty and s.council are single fields with no version. _absorb (:418-447) applies a council result whenever its 'at' differs, with no check that it was convened for the current version. The council job snapshot (_council_work, :351) is taken when the job starts. engine.step returns 'done' for COMPLETE (elicitation/engine.py step) so slot changes after the roadmap re-open nothing. TASKS 1.2.3 only names 'results' (research jobs) to discard.

- **Why it matters:** Levers are narrated one per turn and can come after confirmation, when a roadmap exists. Choosing one would leave the old roadmap and panel in place: the roadmap, the panel's objections (which raise roadmap risks) and the cohort aggregates all describe the previous idea. A council that finishes late for the old version can also overwrite the panel view of the new one.
- **Where to build it:** agents/ideation.py (each artefact tagged with the idea_version it was built for; on a version change move CONFIRMING back to a short re-confirm of the changed slots, drop the roadmap, reject council results whose version differs), elicitation/engine.py (re-open from COMPLETE)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Tag every derived artefact with its idea_version and drop mismatches | Same rule as 1.2.3, applied to roadmap, council and narration | free/open source | One invariant: nothing for another version is spoken or shown | Touches several fields; needs a re-confirm step |
| Fork the session on lever choice (new session id per version) | Decision 0003: one document per session | free/open source | Clean separation, old version kept for comparison | Breaks resume (1.1.4) and the delete (1.1.7) mental model; doubles storage |
| Keep a versions[] list in the session document | JSON document can hold history | free/open source | Founder can go back to an earlier version; supports a 'compare' view | Larger documents; size limits on the Redis copy |
| Allow lever choice only before confirmation | UI restriction | free/open source | Avoids invalidation | Panel-ranked levers (1.3.1) often arrive after the roadmap; contradicts IDEATION §2.3 iteration |

- **Recommended:** Tag every derived artefact with its idea_version and drop mismatches. Extends 1.2.3's rule to everything it misses, with one check at absorb/apply time. A small versions[] holding just the slot snapshot and its verdict can come later if founders want to go back.
- **Ruled out:** Fork per version: breaks resume and delete; Full versions[] now: storage growth before anyone needs it; Pre-confirm only: contradicts the iteration the design describes.

### R118

**Experience mode runs prior-art and novelty on the founder's self-description** · weight 71 · Logic flaw · impact 4/5, reach 3/5, confidence 2/3 · flags F-B1-003

- **Evidence (B1):** agents/ideation.py:927 s.idea = s.idea or text (the first turn is kept as the idea); :272-275 _idea_text falls back to s.idea when problem/solution are absent, which in experience mode is always; :658-661 starts the research job once that text reaches 20 chars; :422 _absorb takes research only while s.scan is None, so after a card writes problem/solution (1.1.5.5) no new scan runs. idea_version (:136-142) hashes CORE_SLOTS, which in experience mode hold only sector/product_form.

- **Why it matters:** 'I worked 12 years as a cook in Salem' is searched as prior art and given a novelty statement, and that verdict persists after the founder picks a real opportunity. 1.2.3 plans a re-run when the version changes, but it does not say research must not start before an idea exists, or that s.idea must be reset when the card fills the slots.
- **Where to build it:** agents/ideation.py (research trigger in _offline_stream, s.idea assignment in the turn), agents/jobs.py; together with 1.2.3 versioning

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Gate research on mode and on problem/solution being filled | A two-line condition in _offline_stream and the scan tool | free/open source | No wasted OpenAlex/Semantic Scholar budget, no false verdict | The card writeback must also set s.idea |
| Rely on 1.2.3 version keys only | Planned work | free/open source | No extra code | The first-turn scan still runs, spends free API budget, and is narrated before any card |
| Run research for each card during ranking | Reuse the scan for each of 3-5 cards | free/open source | Richer cards | 3-5x external calls per session on free quotas; slow on 2G |
| Model decides when to search | Tool-calling path | free tier | Flexible | The offline path is unchanged; 0002 says code decides |

- **Recommended:** Gate research on mode and on problem/solution being filled. Cheapest and correct: no search until an idea exists. The card writeback sets s.idea from the card and bumps the version, so 1.2.3 starts the first real scan.
- **Ruled out:** Rely on 1.2.3: still scans and narrates a non-idea; Per-card research: multiplies free-quota use; Model decides: leaves the offline path wrong and breaks 0002.

### R119

**CP-SAT solved twice per turn yet never differs from greedy at default settings** · weight 70 · Optimisation · impact 2/5, reach 5/5, confidence 3/3 · flags F-A1-010

- **Evidence (A1):** backend/app/elicitation/selector.py:207 (is_objective_clear) and 227 (next_question) each call select_next, a CP-SAT solve with a 1 s cap; at horizon 3 the burden budget 9 cannot bind (max burden 3 per slot). Probe: over every subset of filled required slots, greedy head == CP-SAT head (0 differences); engine.step about 28 ms vs greedy about 0.04 ms.

- **Why it matters:** Each turn pays two solver runs (up to 2 s worst case) on a latency-sensitive path for no change in the question; the greedy fallback lacks the required-before-enrichment rule, so the 'degrade' path stops being equivalent once 5.1.3 retunes weights.
- **Where to build it:** backend/app/elicitation/selector.py

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Greedy with an explicit required-first filter; CP-SAT only when a budget binds | Pure Python; keep OR-Tools for a voice burden budget | free/open source | Same answers, about 700x faster, fallback identical | Docstring rationale must be revised |
| Memoise select_next per turn | Cache keyed on turn and slot confidences | free/open source | Halves cost, no behaviour change | Still a solve per turn |
| Keep CP-SAT, add required-first to _greedy | Small fix | free/open source | Fallback equivalent | Cost unchanged |
| PuLP/CBC integer programming | Free MIP alternative | free/open source | Familiar | Same overhead plus a dependency |

- **Recommended:** Greedy with an explicit required-first filter; CP-SAT only when a budget binds. Proven equal results today with negligible CPU; the solver stays for the case it was built for.
- **Ruled out:** Memoise: keeps needless solves; Fix greedy only: keeps the cost; PuLP: same overhead plus a dependency.

### R121

**Entry-mode/subtype vocabularies mismatch with no contract onto server slots** · weight 68 · Missing structure · impact 3/5, reach 3/5, confidence 3/3 · flags F-B1-005, F-B3-019

- **Evidence (B1):** elicitation/slots.py:58-67 EntryMode {idea, experience}; models/enums.py:57-60 EntryMode {idea, domain_only, intent_only}; frontend/src/journeyStore.ts:24 {idea, domain_only, intent_only}. RegSubtype: models/enums.py:64 'registered_product' vs journeyStore.ts:26 'registered_with_product'. AgentStartIn (routers/ideation.py:248-256) has neither field.
- **Evidence (B3):** The frontend has four RegSubtype values (journeyStore.ts:25-29), while TASKS.md 1.1.6 speaks of 2A/2B/2C. The journey engine knows only entity, registered and years_since_incorporation (routers/journey.py:21-35; engine.py:186-192). Elicitation has no registration or entity slot (no match in elicitation/slots.py), and session.put ignores any key not in BY_KEY (elicitation/session.py:161-162). engine.start reads only PROFILE_SLOTS (engine.py:59, 118-120), and AgentStartIn has no facts field. Entry modes differ too: frontend idea/domain_only/intent_only (journeyStore.ts:24) against backend IDEA/EXPERIENCE (slots.py:58-67). The greeting is fixed to 'Tell me about the idea you are working on' for every founder (agents/ideation.py:211-215).

- **Why it matters:** Sent 'as facts at session start' as the plan says, the subtype is discarded without error, so a registered founder with a product is still asked idea and stage questions (the problem 1.1.6 exists to solve). Without a written mapping, each consumer (agent, journey engine, greeting) will invent its own reading of four values that the plan calls three.
- **Where to build it:** A small shared mapping module (backend, beside elicitation/slots.py): reg_subtype maps to registered, entity and a stage floor, entry mode maps to EntryMode; AgentStartIn gains typed reg_subtype and entry_mode; TASKS.md 1.1.6 names the four values

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Typed enums on AgentStartIn plus one mapping table (subtype to registered, entity and a stage floor; frontend mode to EntryMode with a domain pre-fill) | Pydantic Literal types and a dict; the same pattern as JourneyFacts | free/open source | Explicit, testable, rejects unknown values; one table for agent, journey and greeting | The mapping is a judgement (e.g. what stage 'registered_no_product' implies) and needs the owner's sign-off |
| Add 'registration' as a new elicitation slot fed from the subtype | The slot machinery already exists | free/open source | Flows through put, restatement and the snapshot like any fact | Adds a slot to the 7-question selector's world; must never be asked if known |
| Pass the raw subtype string and let each consumer interpret it | Plan as written | free/open source | No design work | Silently dropped today; interpretations will drift |
| JSON Schema shared contract validated on both sides (ajv on the frontend, jsonschema on the backend) | Mature validators | free/open source | Language-neutral contract | Heavier than a typed request model for two fields |

- **Recommended:** Typed enums on AgentStartIn plus one mapping table (subtype to registered, entity and a stage floor; frontend mode to EntryMode with a domain pre-fill). It turns a silent drop into a validated input. It gives the agent, the journey engine and the greeting one interpretation, and it reuses the validate-then-put rule recommended at 1.1.1, so mapped facts go into slots as typed values with Source.PROFILE.
- **Ruled out:** New slot only: still needs the mapping and risks being asked. Raw string: discarded by session.put today, with drifting interpretations later. JSON Schema: more machinery than a Pydantic model for the same guarantee.

### R126

**A spoken choice ('the second one') is not understood; only a button is planned** · weight 68 · Missing function · impact 3/5, reach 3/5, confidence 3/3 · flags F-B1-017

- **Evidence (B1):** agents/ideation.py:846-860 _advance parses yes/no only in CONFIRMING, then skip/opinion, then passes the text to engine.observe as an answer or extraction. There is no ordinal or name matching against offered options. TASKS 1.2.4 plans only '1.2.4.1 API action' and '1.2.4.2 Talk page control'; 1.1.5 card choice has the same gap.

- **Why it matters:** The Talk page is voice-first, for low-literacy founders (1.5.5). A founder who says 'the second one' or 'do it as a rental' is treated as answering the pending slot: the reply is stored as a free-text value or counted as a miss, and no lever is chosen. The choice is then possible only by tapping a control.
- **Where to build it:** agents/ideation.py (_advance: when a choice is pending, match ordinals in en/ta/hi and lever-kind keywords, deterministically, before slot observation), shared with the 1.1.5 card choice via the pending-action object from B1-02

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Deterministic ordinal and keyword matcher over the pending options | Same style as the YES/NO/SKIP regexes already in ideation.py; code decides (0002) | free/open source | Works offline; one matcher for levers and cards | Needs Tamil/Hindi ordinal words reviewed (1.5.2) |
| rapidfuzz fuzzy match of the utterance against option texts | Mature MIT fuzzy-matching library, fast C++ core | free/open source | Catches 'the rental one' | False positives on long answers; needs a threshold |
| Model classifies the choice | Free model chain (0009) | free tier | Handles free phrasing | Offline path has nothing; model would decide state (against 0002) |
| Button only | As planned | free/open source | Unambiguous | Excludes voice-only founders |

- **Recommended:** Deterministic ordinal and keyword matcher over the pending options. Fits the existing regex-based turn parsing and decision 0002. Add rapidfuzz only as a tie-breaker on option names if the eval shows misses.
- **Ruled out:** rapidfuzz alone: noisy on full sentences; Model: no offline path, and the model must not decide state; Button only: fails the voice-first founder.

### R134

**Gemini TTS is called before the free recordings, and grouped text can never match them** · weight 68 · Optimisation · impact 3/5, reach 3/5, confidence 3/3 · flags F-A1-028

- **Evidence (A1):** backend/app/routers/voice.py:102-110 tries Gemini first and the phrasebook only after Gemini fails; frontend/src/voice/mentorVoice.ts:78-104 with grouping on (Talk.tsx:113, whenever speech is gemini or sarvam) joins several sentences into one /speak request, while phrasebook keys are per normalised sentence (phrasebook.py:226-259). So recorded fixed sentences spend Gemini quota, and when Gemini returns 429 a grouped request misses every recording and returns 204 (silence).

- **Why it matters:** The free-tier TTS quota is the scarcest voice resource; spending it on sentences already recorded locally shortens the day's voice for dynamic content, and on quota exhaustion founders lose even the fixed sentences that have recordings.
- **Where to build it:** backend/app/routers/voice.py (speak), frontend/src/voice/mentorVoice.ts (grouping)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Phrasebook first, per sentence, then Gemini for the rest | Server splits the request with SentenceSplitter, serves recorded sentences from disk, sends only unrecorded ones to Gemini, concatenates WAV (same 24 kHz mono format via the wave module) | free/open source | Zero quota for recorded sentences; grouping still saves requests | WAV concatenation needs matching sample rates between recordings and Gemini |
| Client does not group sentences that have recordings | Frontend asks /voice/status for a recorded-sentence list | free/open source | Simple server | List sync between client and server |
| Disable grouping | One request per sentence | free/open source | Recordings match | More Gemini requests for dynamic content |
| pydub for audio joining | Mature library over ffmpeg | free/open source | Handles format differences | ffmpeg dependency for a WAV-only job |

- **Recommended:** Phrasebook first, per sentence, then Gemini for the rest. Uses free local audio wherever it exists and keeps grouping's saving for the sentences that need a model voice; the standard-library wave module suffices.
- **Ruled out:** Client-side list: duplicated knowledge; No grouping: more quota for dynamic text; pydub: unnecessary ffmpeg dependency.

### R139

**Novelty's medical 'regulatory route' lever is 1.3.3's twin, missing from its scope** · weight 68 · Logic flaw · impact 3/5, reach 3/5, confidence 3/3 · flags F-B4-024

- **Evidence (B4):** backend/app/research/novelty.py:248-251 _is_health = terms.is_health(idea) or trials, and :283-296 adds the lever 'Check whether a first version can avoid medical-device claims, for example as a communication aid...'. Ran is_health('hospital bill instalment loans for medical treatment') -> True. TASKS 1.3.3 names only agents/council/evidence.py, research/terms.py and agents/council/rules.py. The lever also feeds the panel as evidence (council/evidence.py:149-150), and lever 0 becomes the panel's suggested variant (council/rules.py:135-143).

- **Why it matters:** If 1.3.3 tightens the council's trigger but not novelty's, the fintech EMI founder still hears 'start as a communication aid' through the novelty lever, which then flows back into the panel as evidence: the very bug 1.3.3 closes, re-entering by a second door. 1.2.2's rewording task touches this function but does not mention the trigger.
- **Where to build it:** a single health classifier in research/terms.py used by both novelty.py and council/evidence.py; extend 1.3.3's 'Where' to novelty.py

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| One shared is_health_product(idea, scan, slots) requiring a device or clinical signal, used by novelty and council | is_health and HEALTH_TERMS already central in terms.py | free/open source | Fix once, both doors close; eval assertion covers both outputs | Needs a device/clinical term list |
| Gate the novelty lever on the founder's sector slot (health) as well | Slot exists | free/open source | Uses founder words | Depends on the sector extractor, which has proven false positives (B4-01) |
| Drop the regulatory lever from novelty and leave it to the panel | Avoids duplication | free/open source | One source of medical advice | Novelty loses a valid lever for real devices |

- **Recommended:** One shared is_health_product(idea, scan, slots) requiring a device or clinical signal, used by novelty and council. The same rule in both twins, so 1.3.3's fix cannot be bypassed by the lever path.
- **Ruled out:** Sector gate alone: inherits extractor errors; dropping the lever: removes correct advice for real medical devices.

### R143

**Results that finish while offline are missing on reconnect and on resume** · weight 68 · Missing logic · impact 3/5, reach 3/5, confidence 3/3 · flags F-B1-011

- **Evidence (B1):** agents/jobs.py:104-115: notices go only to queues subscribed at that moment, with no event id or replay. routers/ideation.py:370-391: a (re)subscribe starts empty. agents/ideation.py snapshot (:226-250) returns s.scan/s.novelty/s.council, which are set only when _absorb runs on the next turn (:418-423), not from board.take. Talk.tsx:135 drops an expired session with save(null) and starts fresh without telling the founder.

- **Why it matters:** After a 2G drop (EventSource reconnects by itself) or a page reload, a search that finished in between never appears until the founder speaks again, and the resume preamble (1.1.4.3) cannot mention it. A founder returning after the 6-hour idle expiry (store.py:29) silently loses the conversation, with no 'this conversation has expired' message.
- **Where to build it:** routers/ideation.py (notices: send the latest board results on subscribe), agents/ideation.py (snapshot reads finished board results), Talk.tsx (say why a fresh start happened)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Replay the latest results on subscribe, and include them in the snapshot | board.take already returns the latest finished result per kind | free/open source | A few lines; idempotent for the client (setEvidence replaces) | Re-sends the payload on every reconnect (small JSON) |
| SSE Last-Event-ID with a per-session ring buffer | SSE standard; EventSource sends Last-Event-ID itself | free/open source | Sends exactly the missed events | Ring buffer state per process; lost on restart |
| Redis Streams for notices | Redis already present | free/open source | Durable, works across workers (2.3.1) | Heavier; needs Redis, which is optional today |
| Client polls the snapshot every N seconds | No server change | free/open source | Simple | Wastes data on 2G |

- **Recommended:** Replay the latest results on subscribe, and include them in the snapshot. Uses data the board already keeps and closes both gaps (reconnect and reload). Redis Streams can replace it when 2.3.1 makes the board durable.
- **Ruled out:** Last-Event-ID: per-process ring state for no gain over latest-result replay; Redis Streams: premature while Redis is optional; Polling: costly on 2G.

### R144

**Speaking twice during a slow turn silently drops the first utterance** · weight 68 · Logic flaw · impact 3/5, reach 3/5, confidence 3/3 · flags F-B1-010

- **Evidence (B1):** frontend/src/pages/Talk.tsx:152-155: while a turn is busy, queuedRef.current = said overwrites any earlier queued text. Talk.tsx:210-213 sends only the last one. The dropped text is never added to the transcript.

- **Why it matters:** On 2G a turn can take many seconds, and a founder who answers, then adds a detail, loses the first answer without any sign. That answer may hold the slot that was asked, so the question is asked again and uses the budget.
- **Where to build it:** Talk.tsx (queue as an array, or join the queued texts into one turn)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Concatenate queued utterances into one next turn | One-line change; the extractor already reads multi-sentence text | free/open source | One turn, no budget cost, nothing lost | The answered slot gets two sentences (the validator already handles free text) |
| FIFO array of queued turns | Array ref | free/open source | Keeps the turns separate | Several extra round trips on a slow link; each uses a question turn |
| Block the mic while busy | UI state | free/open source | Simple | Hostile to voice users; loses the thought |
| Show queued text as a pending bubble the founder can edit | UI | free/open source | Transparent | Text-heavy; conflicts with the low-literacy goal (1.5.5) |

- **Recommended:** Concatenate queued utterances into one next turn. Loses nothing, costs no extra request on a slow network, and the engine is built to read more than one fact from one utterance.
- **Ruled out:** FIFO: multiplies round trips and budget use on 2G; Mic block: hostile to voice; Editable bubble: text-first.

### R147

**Tracker keys by bare milestone ID; packs reuse IDs with different meanings** · weight 68 · Logic flaw · impact 3/5, reach 3/5, confidence 3/3 · flags F-B2-021

- **Evidence (B2):** backend/app/planner/plan.py:22-26: a pack template with the same ID replaces the common one. Data: common c_pilot is 'Pilot with real buyers', pump_controllers c_pilot is 'Launch through dealers'. common c_customers is 'First 100 paying customers', pump_controllers c_customers is 'First 500 installed units'. c_define also differs in banana_value_added and pump_controllers. frontend/src/pages/Ideate.tsx:76-91 keeps one global map loadJourney().milestones keyed by milestone ID only, with no idea_version, pack or session. Old IDs are m1, m2, ... (swarms/roadmap/milestones.py:26-40).

- **Why it matters:** A founder who marks 'Pilot with real buyers' done and then refines the idea into a pack domain (or starts a second idea) sees 'Launch through dealers' already done. Progress percentages and, after 3.1.3, the server record show work that was never done. Statuses on IDs that disappear (c_compliance becomes b_compliance) are silently orphaned. Old m1..m9 records would collide with nothing but would linger as orphans after 1.4.1.
- **Where to build it:** the 1.4.2 tracker (key by idea_version + pack + milestone ID, or by a template content hash); a reconcile step when the roadmap is rebuilt; the 3.1.3 server shape

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Key status by (idea_version, pack ID, milestone ID) and reconcile on rebuild, carrying over only when the title or template hash matches | idea_version already exists (ideation.py:137); pack ID is in plan output | free/open source | No false 'done'; deliberate carry-over when the same milestone survives a refinement | A small reconcile function and a 'carried from earlier version' note |
| Make template IDs globally unique (pump_c_pilot) and stop overriding by ID | A data change in planner/data/packs | free/open source | IDs mean one thing everywhere | Loses the override mechanism plan.py relies on; scheme annotation keyed by c_* must change too |
| Reset all status whenever the roadmap is rebuilt | Simplest rule | free/open source | Never wrong | Throws away real progress on every refinement |

- **Recommended:** Key status by (idea_version, pack ID, milestone ID) and reconcile on rebuild, carrying over only when the title or template hash matches. It keeps the override mechanism the planner needs, makes the tracker truthful, and gives 3.1.3 a server key that cannot collide across ideas.
- **Ruled out:** Globally unique IDs: breaks the pack-overrides-common design and the annotation keys. Reset on rebuild: punishes founders for refining their idea.

### R151

**Browser speech recognition is a Google path the notice rule ignores** · weight 67 · Missing logic · impact 3/5, reach 4/5, confidence 2/3 · flags F-B3-010

- **Evidence (B3):** Without a Sarvam key the Talk page listens with the browser's SpeechRecognition / webkitSpeechRecognition (frontend/src/voice/speech.ts:30-34; Talk.tsx:74 defaults the listener to 'browser'; routers/voice.py:59 reports 'browser'). In Chrome, the main browser on Android, this API sends the audio to Google's servers for recognition. 1.5.4 ties the notice only to the Gemini model provider, and 1.5.3.3 plans Gemini transcription as the alternative.

- **Why it matters:** On the free, no-key setup, the default for every voice founder, each spoken answer goes to Google with no Gemini key at all, so a notice keyed to Gemini never shows. Voice-first, low-literacy founders are the ones most exposed.
- **Where to build it:** Talk.tsx, speech.ts, the notice from 1.5.4, the 'voice' purpose in 3.2.1

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Include browser recognition in the same versioned notice, with typing as the path that sends nothing to Google | Copy and a display rule in Talk.tsx | free/open source | Honest now, no new dependency | Does not remove the data flow |
| Local recognition with Vosk (small Tamil/Hindi/English models) in the existing voice-worker | Mature offline open-source recogniser (Apache 2.0) with Indian-language models | free/open source | Nothing leaves the machine; works offline | Accuracy on Tamil is lower; extra worker process and models to ship |
| whisper.cpp on the server | Popular open-source local Whisper port | free/open source | Better multilingual accuracy than Vosk | Slow on a laptop CPU, the same problem 0009 found with Parler |
| Gemini transcription (1.5.3.3) | Same key as the model | free tier | Good Tamil | Still Google, so it changes nothing for privacy; needs the key |

- **Recommended:** Include browser recognition in the same versioned notice, with typing as the path that sends nothing to Google. It fixes the disclosure gap at once at no cost, and it belongs in the same notice and consent record as the previous flag. Vosk can follow as the private-mode listener once accuracy is checked.
- **Ruled out:** Vosk now: Tamil accuracy unproven and a new worker to run; it is a follow-up, not the first fix. whisper.cpp: too slow on a CPU for live turns. Gemini transcription: still sends audio to Google, so it does not address the gap.

### R154

**Restatement omits facts the roadmap uses (team size, experience, horizon)** · weight 67 · Missing logic · impact 3/5, reach 4/5, confidence 2/3 · flags F-B4-016

- **Evidence (B4):** backend/app/elicitation/engine.py:314-360 restate() reads only problem, solution, beneficiary, sector, product_form, stage, district, capital_band and funding_route. The planner also uses team_size and founder_years (planner/roadmap.py:109-121 capacity and k_experience scale every milestone's weeks), time_horizon and geo_scope (roadmap consumers in slots.py). These are exactly the slots a model can fill through note_fact with untyped values (B4-04 flag 1: 'about five' crashed build_plan). Nothing projected for schemes (1.4.3) is restated either.

- **Why it matters:** 1.1.2.1 labels the source of each restated fact, but the facts most likely to be assumed or model-noted are never shown, so the founder cannot catch them before the roadmap's timeline is built on them. 'No roadmap built on a wrong assumption' is not met.
- **Where to build it:** backend/app/elicitation/engine.py restate() (driven by slot consumers), slots.py (a 'restate' flag or rule per slot)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Restate every non-text slot whose consumers include 'roadmap' or 'scheme' and whose source is not ANSWER, in one 'I assumed:' sentence | Slot consumers and Source already exist; deterministic | free/open source | Shows exactly the risky facts; short when the founder answered everything | One more sentence on voice |
| Restate all filled slots | Simple loop | free/open source | Complete | Too long by voice; buries the important items |
| Show the extra facts only on screen, not in speech | Talk page has a transcript | free/open source | Keeps voice short | Voice-only founders never see them |

- **Recommended:** Restate every non-text slot whose consumers include 'roadmap' or 'scheme' and whose source is not ANSWER, in one 'I assumed:' sentence. Targets exactly the facts that change the plan and were not given directly, and works with 1.1.2.1's source labels.
- **Ruled out:** Restate all: too long for the voice channel; screen-only: excludes voice founders.

### R155

**Selector values slots by static consumer count, not by which result a gap blocks** · weight 67 · Missing logic · impact 3/5, reach 4/5, confidence 2/3 · flags F-B4-013

- **Evidence (B4):** backend/app/elicitation/selector.py:80-97 question_value adds W_CONSUMERS * len(slot.consumers), a fixed tuple per slot (slots.py, e.g. district ('scheme','opportunity'), stage ('roadmap','scheme','funding')). Nothing reads which scheme or roadmap inputs are currently unknown. selector.candidates docstring (:103) promises 'not sensitive', but no slot is sensitive (checked: [s.key for s in SLOTS if s.sensitive] == []), and there are no slots for the founder fields the scheme rules read (age, gender, caste_category, first_graduate, entity_type, dpiit; see B4-03 flag 1).

- **Why it matters:** With 1.4.3's projection and a three-valued engine, the questions that would turn most 'unknown' schemes into answers are never preferred. The selector keeps spending the 7-question budget on fixed priorities. A finger gate (1.1.3.1) fixes order but not relevance. The missing sensitivity filter will matter as soon as caste or gender slots are added for schemes.
- **Where to build it:** backend/app/elicitation/selector.py (value term from blocked consumers), slots.py (scheme-input slots with sensitive=True and an opt-in rule), schemes/engine.py (report unknown fields)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Dynamic value term: count of downstream results (schemes, roadmap gates) whose evaluation is 'unknown' only because of this slot | Uses the three-valued engine output from B4-03; fits the existing CP-SAT objective as an extra integer weight | free/open source | Questions chosen by what they unlock; still deterministic and testable | Runs the engine each turn (cheap: 8 seed schemes plus catalogue rules) |
| Static per-slot priority table tuned by hand | Current pattern | free/open source | Simple | Ignores the founder's state; tuning (5.1.3) cannot fix a missing signal |
| Expected information gain over scheme outcomes (entropy) | Classic active-learning approach | free/open source | Principled | Needs priors over answers that the project does not have (no invented data); overkill |

- **Recommended:** Dynamic value term: count of downstream results (schemes, roadmap gates) whose evaluation is 'unknown' only because of this slot. A small, deterministic signal that ties question order to what the founder gets, and plugs into the existing CP-SAT objective without changing its structure.
- **Ruled out:** Static table: blind to the session; information gain: needs answer priors that would be invented data.

### R156

**'No technical skill' weight bump fires for a Python developer and for unknown skills** · weight 64 · Logic flaw · impact 2/5, reach 4/5, confidence 3/3 · flags F-A1-021

- **Evidence (A1):** backend/app/agents/council/vote.py:24 TECH_SKILLS = software, engineer, electronic, hardware, coding, programming, tech; :63-68 adds technical +5 when none is a substring of founder_skills, including when founder_skills is absent. Probe: founder_skills=['python developer'] on a software idea -> weights_why 'no technical skill recorded for the founder: technical +5'. founder_skills is an ENRICHING slot that the 7-turn budget rarely reaches (step 1 finding), so the bump applies to almost every founder.

- **Why it matters:** The panel's weights claim a fact about the founder ('no technical skill') that is either false or unknown, and the reason is shown with the verdict; unknown is treated as 'none'.
- **Where to build it:** backend/app/agents/council/vote.py (weights_for)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Three-state rule: known technical / known non-technical / unknown (no bump) | Code change; wording 'not recorded' only when asked and answered | free/open source | Honest and simple | Fewer adjustments overall |
| Skill vocabulary from a public list (ESCO skills taxonomy) | EU ESCO is free, multilingual, has an ICT skill group | free/open source | Broad coverage of skill names | Large dataset to trim; English-centred phrasing for TN founders |
| Extend TECH_SKILLS by review | Add developer, python, java, embedded, CAD, electrician... | free/open source | Trivial | Still treats unknown as none |

- **Recommended:** Three-state rule: known technical / known non-technical / unknown (no bump). Removes the false claim at once; the vocabulary can grow by review alongside.
- **Ruled out:** ESCO: heavy for a single bump; Extending the list alone: unknown still counted as none.

### R157

**Two 'known' thresholds: 0.5 counts a slot filled, 0.6 still asks it** · weight 64 · Logic flaw · impact 2/5, reach 4/5, confidence 3/3 · flags F-A1-009

- **Evidence (A1):** backend/app/elicitation/session.py:123 filled uses confidence >= 0.5; selector.py:37,115 candidates use TAU_FILL = 0.60. Probe: sector put at 0.55 -> in filled (not missing) and still a candidate.

- **Why it matters:** A 0.5-0.6 extraction satisfies the stop rule and is restated as fact, yet the selector may still spend a question on it; 1.1.3.3's disagreement cap has no single threshold to cap against.
- **Where to build it:** backend/app/elicitation/session.py, selector.py (one shared constant in slots.py)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Single TAU_FILL constant imported by session.py | Move the threshold to slots.py | free/open source | One rule, trivial | Loses the useful middle band |
| Three bands: known / confirm / unknown | 0.5-0.6 becomes 'I assumed' in the restatement instead of a question | free/open source | Feeds 1.1.2's labels | Slightly more logic |
| Leave and document | None | free/open source | No change | Keeps the contradiction |

- **Recommended:** Three bands: known / confirm / unknown. Turns the inconsistency into the 'I assumed' label 1.1.2 needs, without spending a question.
- **Ruled out:** Single constant: loses the middle band; Document: keeps the contradiction.

### R158

**Research job runs its source calls in serial waves** · weight 63 · Optimisation · impact 2/5, reach 5/5, confidence 2/3 · flags F-A1-017

- **Evidence (A1):** backend/app/research/sources.py:198-233 papers() awaits three OpenAlex requests one after another (relevance, most cited, by-year); scan.py:241-256 awaits element searches one element at a time; agents/ideation.py:369-379 runs novelty.check only after scan finishes, and novelty.py:83-129 runs four more serial waves (parts, pairs, context, retarget). Only novelty's use of scan is local data (startups, trials, packs).

- **Why it matters:** The turn waits research_wait_s for this job; on a cold cache the serial chain often misses the window, so evidence arrives a turn later and 'Let me look up...' is spoken instead of findings. Every wave also re-pays network latency on a slow link.
- **Where to build it:** backend/app/research/sources.py, scan.py, novelty.py, agents/ideation.py (_research_work)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| asyncio.gather the independent calls | Standard library; papers' three calls, element rows, and context+retarget together; start novelty's part counts alongside the scan | free/open source | Same requests, lower wall time | Bursts more concurrent requests at OpenAlex; needs the existing pause logic to hold |
| Drop the by-year call unless the screen shows it | One fewer request per scan | free/open source | Saves budget and time | Loses the trend chart |
| anyio task groups | Mature, structured concurrency | free/open source | Cleaner cancellation | New dependency for what gather does |
| Pre-warm cache nightly (2.2.6) | Already planned | free/open source | Hot paths fast | Waits on an OpenAlex key |

- **Recommended:** asyncio.gather the independent calls. No new dependency, no extra requests, and the largest latency cut on the path the turn waits for.
- **Ruled out:** Drop by-year: saves little time and removes a feature; anyio: dependency without new capability; Nightly warming: blocked and covers only registry domains.

### R159

**A stream conflict arrives as 200 + error after the reply was spoken and shown** · weight 62 · Logic flaw · impact 3/5, reach 2/5, confidence 3/3 · flags F-B1-008

- **Evidence (B1):** routers/ideation.py:347-352: on VersionConflict at 'done' the generator yields _sse('error', {'detail': ...}). Every 'sentence' event has already gone out, and the HTTP status is already 200. Talk.tsx:198-200 only does setError(detail); Talk.tsx:205 still appends the spoken reply to the transcript in the finally block. agentClient.ts:189 checks res.ok only before the body starts.

- **Why it matters:** 1.1.4.2 plans to handle 409, but on the stream a conflict never has status 409. The founder hears and sees a full reply (possibly a question) that the server threw away, then gets a text error, which a low-literacy voice user may not read. The next answer then goes to a question the server never recorded.
- **Where to build it:** routers/ideation.py (typed error event, e.g. {code: 'conflict'}), Talk.tsx (on conflict: drop the unsaved reply from the transcript, reload the snapshot, say it aloud), agentClient.ts

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Typed SSE error events with a code field | Small change to _sse('error') and the AgentEvent type | free/open source | The client can branch on conflict, expired or failed; works for any error after the stream starts | Speech already played cannot be unsaid; needs a spoken correction |
| Check the version before streaming (pre-flight save) | Reserve the version at the start of the turn | free/open source | Most conflicts surface as a real 409 before any speech | A conflict can still happen during the stream; needs an extra write per turn |
| Buffer the reply and send only after the save | Stop streaming | free/open source | Never speaks unsaved text | Loses the first sentence within 1 s (SYSTEM-DESIGN §7) |
| Hold speech until 'done' on the client | Talk page change | free/open source | No backend change | Same latency loss as buffering |

- **Recommended:** Typed SSE error events with a code field. Keeps streaming latency and makes 1.1.4.2 work on the path founders actually use: on {code:'conflict'} the page removes the unsaved reply, fetches the snapshot, and says a short fixed sentence so the founder re-orients. The lock already makes in-process conflicts rare; this covers the multi-device case.
- **Ruled out:** Pre-flight save: an extra write every turn, and it still needs typed errors for mid-stream conflicts; Buffering on the server or the client: gives up the 1-second first sentence the design is built around.

### R164

**A model-written rolling summary either becomes a fact source or is dropped** · weight 61 · Logic flaw · impact 3/5, reach 3/5, confidence 2/3 · flags F-B1-024

- **Evidence (B1):** TASKS 1.6.1.2: 'a background job rewrites the summary every 8 turns'. _facts (ideation.py:280-302) admits only tool results, founder words, slot labels, the objective, scan, roadmap, novelty and council. A summary written by a model is none of these. agents/jobs.py docstring: jobs work on a snapshot and never touch the session, so their token use reaches s.usage only if the caller adds it (as _apply_council does at :399). The board keys jobs by (session, kind), not by version (B1-04).

- **Why it matters:** If the summary is added to the facts, model-authored text becomes evidence (against 0005 and 0002: code decides). If it is not, any sentence that paraphrases it is dropped and the founder hears gaps. It also spends a free-tier call every 8 turns, its tokens can escape the session budget, and a summary written for an old idea version reinjects a stale verdict that 1.2.3 removed.
- **Where to build it:** agents/ideation.py (code-built summary from state), agents/jobs.py (no model job needed)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Deterministic summary built by code from state | Everything durable is already structured: slots with sources, the objective, narrated keys, the current version's verdict and levers, the chosen lever | free/open source | No model call, works offline, every line is already a fact, and it is rebuilt for the current version | Less fluent; small talk is not summarised |
| Model summary, fact-checked line by line before use | Reuse the _Gate checker | free tier | Fluent | Spends quota; lines that fail are dropped, so the summary has holes |
| Extractive summary (sumy / TextRank) of founder turns | Mature offline Python libraries | free/open source | Offline, quotes the founder | Picks sentences, not decisions; weak on short spoken turns |
| No summary: facts block + last N turns only | Sessions are short (Q_MAX 7 plus narration) | free/open source | Simplest | Loses why the founder rejected something more than N turns ago |

- **Recommended:** Deterministic summary built by code from state. It matches 0002 and 0005 exactly, costs nothing on the free plan, and is regenerated per version (with B1-04's research key), so it can never carry a stale verdict. If eval shows something missing, add a 'founder rejected X' list, kept by code from the 1.1.2.3 corrections.
- **Ruled out:** Fact-checked model summary: quota spend for a summary with holes; TextRank: extracts sentences, not decisions; No summary: loses older corrections.

### R171

**No rule for results produced before any version exists (idea_version None)** · weight 61 · Missing logic · impact 3/5, reach 3/5, confidence 2/3 · flags F-B1-021

- **Evidence (B1):** agents/ideation.py:139-141 idea_version returns None when no core slot is filled, while research starts as soon as _idea_text (falling back to the raw first utterance s.idea, :275) reaches 20 chars (:658-661). In experience mode no core slot is filled until a card is chosen (B1-01). results.py keys are str.

- **Why it matters:** When results are keyed by version, the first scan, started from raw text before extraction filled anything, is stored under None, or 'None' as a string, and can never match a real version. It is either never narrated or mistaken for current. In experience mode every scan falls into this case.
- **Where to build it:** agents/ideation.py (no research while the research key is None; or derive the key from the research inputs, flag 1, which always exist once there is text)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Derive the key from research inputs, never None | Flag 1's key exists whenever there is text to search | free/open source | Removes the special case | Experience mode still needs the B1-01 gate so it does not search the self-description |
| Do not start research while idea_version is None | Guard in _offline_stream/_search | free/open source | Simple | Delays the first scan in the idea path until extraction fills a slot |
| Sentinel version 'raw' | Constant key | free/open source | Keeps today's early scan | A special case every consumer must know |
| Re-key the raw result once the first version appears | Move the row | free/open source | No wasted scan | Claims the raw-text scan matches a structured version it may not match |

- **Recommended:** Derive the key from research inputs, never None. Folds into flag 1's key with no extra rule. Pair it with the experience-mode gate from B1-01 so that a self-description never gets a key.
- **Ruled out:** No research while None: slows the idea path; Sentinel: one more special case; Re-key: asserts a match that may be false.

### R173

**Results outlive their conversation; a running turn re-creates them after delete** · weight 61 · Logic flaw · impact 3/5, reach 3/5, confidence 2/3 · flags F-B3-012

- **Evidence (B3):** agent_delete (routers/ideation.py:313-319) does not take _turn_locks, which a turn holds while it runs (:325, :338). A turn already inside can call board.start (agents/ideation.py:390, 409, 439, 661) after board.forget (jobs.py:117-124), and run() then writes results.put for the deleted session (jobs.py:75-79). MemoryResults (results.py:35-61) has no expiry, and board.jobs is never pruned, so the results of every session hidden after 6 hours also stay in process memory until restart. 2.3.1 plans the durable results table without a delete or retention rule.

- **Why it matters:** A founder who deletes while a reply is streaming, a natural moment to change their mind, gets a 204, yet the scan, novelty and panel results derived from their idea are written back afterwards. Unbounded result and job maps also grow the process memory with every conversation.
- **Where to build it:** routers/ideation.py (delete takes the turn lock), agents/jobs.py (refuse start for a forgotten session; prune finished jobs), agents/results.py and the 2.3.1 table (expiry and delete cascade)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Delete takes the session's turn lock, plus a 'forgotten' tombstone that board.start and results.put refuse | The asyncio.Lock and the board already exist; a small in-process set with a TTL | free/open source | Closes the race in-process; tiny change | Single process only, until 2.3.1's shared queue |
| Results table with ON DELETE CASCADE from agent_sessions (2.3.1) | PostgreSQL foreign keys via Alembic | free/open source | The database guarantees no orphans | Waits on 2.1.1; the memory path stays leaky |
| TTL on memory results and finished jobs (e.g. cachetools.TTLCache) | A mature, small library | free/open source | Bounds memory | Does not stop a write-after-delete |
| Check the session still exists before results.put | One store.get per job | free/open source | Simple | Still racy between the check and the write; one extra read per job |

- **Recommended:** Delete takes the session's turn lock, plus a 'forgotten' tombstone that board.start and results.put refuse. It fixes the race where it starts, with parts already present. Pair it with a TTL on memory results and finished jobs, and write the cascade into 2.3.1 so the database version keeps the rule.
- **Ruled out:** Cascade only: blocked on 2.1.1 and leaves today's memory path open. TTL alone: bounds memory but not write-after-delete. Existence check: still a check-then-write race.

### R175

**Seven separate model calls per panel run; every seat sees the whole pack anyway** · weight 61 · Optimisation · impact 3/5, reach 3/5, confidence 2/3 · flags F-A1-023

- **Evidence (A1):** backend/app/agents/council/__init__.py:59-63 one ask_seat task per seat in parallel with an 8 s cap; council/model.py:42-50 the system prompt carries pack.lines() (the full pack) to every seat, so EvidencePack.lines(kinds) (evidence.py:40-46) is unused and the seats.py docstring ('sees its own slice') is not true. Seat failures (e.g. 429) are not recorded on the provider breaker, so a quota-exhausted Gemini costs the full 8 s every panel before rules stand in.

- **Why it matters:** On the free tier each panel spends seven requests of a small per-minute quota (and the panel re-runs on every opinion request and after research), competing with the conversation's own calls; the separate prompts buy no real seat diversity because the inputs are identical apart from a brief.
- **Where to build it:** backend/app/agents/council/model.py, __init__.py, agents/providers.py (breaker on complete)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| One call returning all seven opinions as a JSON array | Same prompt and validation per opinion; Gemini structured output supports arrays | free/open source | 1 request instead of 7; one shared context | Seats less independent; one failure loses all model seats (rules stand in) |
| Per-seat evidence slices with seven calls | Use pack.lines(seat.kinds) | free/open source | Real diversity as designed | Loses the shared cached prefix; still seven requests |
| Record seat 429s on the breaker and skip model seats while open | Existing Breaker | free/open source | No 8 s stall when quota is gone | Does not reduce requests |
| Model only for prior_art, customer and devil; rules for the rest | Selective use | free/open source | 3 requests; rules already decent for funding/regulatory/cost | Mixed basis in one vote |

- **Recommended:** One call returning all seven opinions as a JSON array. Cuts free-tier use sevenfold at no loss of information, since seats already share identical evidence; pair it with breaker recording.
- **Ruled out:** Per-seat slices: keeps seven requests; Breaker alone: no saving when healthy; Selective seats: still three requests and a mixed basis.

### R176

**Snapshot has no 'pending action' contract for choices, only pending_slot** · weight 61 · Missing structure · impact 3/5, reach 3/5, confidence 2/3 · flags F-B1-012

- **Evidence (B1):** agents/ideation.py:226-250 snapshot returns state, pending_slot and last_question (the last elicitation question, or else the last assistant text). AgentSession holds only pending_slot (:131). Neither the card choice from 1.1.5 (no CHOOSING state, see B1-01) nor the lever choice of 1.2.4 has a field, and Talk.tsx:133 restores only a caption string.

- **Why it matters:** The 1.1.4.3 resume preamble 'repeats the pending question'. When what is pending is a choice among 3-5 cards or levers, a single caption cannot re-present the options, and a replayed choose action without a turn id would bump idea_version twice and restart research (1.2.3).
- **Where to build it:** agents/ideation.py (AgentSession.pending: {kind: ask\|confirm\|choose_card\|choose_lever, slot, options, idea_version}), snapshot, routers/ideation.py, Talk.tsx

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Typed pending-action object in the session document | Generalises pending_slot inside the single JSON document (0003) | free/open source | One source for resume, replay checks and the screen; a choose action validates against pending.options and idea_version | Session format change (2.1.4) |
| Derive pending state from the last assistant message | Today's fallback | free/open source | No schema change | Text cannot carry options or a version; fragile |
| Pydantic discriminated union for pending actions | Pydantic v2 already used for ElicitationSession | free/open source | Validated shape per kind | AgentSession is a dataclass, so it means mixing models |
| Separate endpoint for open choices | REST resource | free/open source | Clean API | A second fetch on resume over 2G |

- **Recommended:** Typed pending-action object in the session document. Resume (1.1.4.3), choice replay protection (1.2.4) and card choice (1.1.5) all need the same fact: what the founder is being asked, and against which idea version. Store it once, and validate it with a Pydantic model inside the dataclass field if wanted.
- **Ruled out:** Derive from text: cannot carry options; Discriminated union alone: useful as validation but not a storage decision; Separate endpoint: an extra round trip on slow links.

### R177

**Tracker status ignores depends_on and the critical path; programme progress cannot see it** · weight 61 · Missing logic · impact 3/5, reach 3/5, confidence 2/3 · flags F-B2-023

- **Evidence (B2):** frontend/src/pages/Ideate.tsx:78-92: cycle() moves pending to in_progress to done with no check of the milestone's depends_on, and the progress (:96-108) is a plain count. The planner output has depends_on, critical and critical_path and months_realistic per milestone (planner/plan.py:181-205). backend/app/cohort/programme.py:83-86 measures progress as elicitation share plus 'reached_a_roadmap', with no milestone status.

- **Why it matters:** A founder can mark 'Launch through dealers' done while certification (p_cert) is pending, and the screen still shows the old timeline with no remaining months, so the roadmap does not 'move'. The programme manager's 'how far they have got' (IDEATION 4.2) can never reflect real milestone progress, because status lives in the browser (and, under 3.1.3, on the founder record) while cohort reads sessions.
- **Where to build it:** the planner (a function remaining(plan, statuses) returning the open critical path and remaining months, plus dependency warnings); the tracker UI; cohort/programme.py (a progress band from milestone status, folded below 5)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Server function recomputes remaining critical path and months from statuses; the UI warns on done-before-dependencies | Reuses swarms/roadmap graph functions that the planner already uses (1.4.1 keeps them) | free/open source | Deterministic, offline; the same output feeds cohort bands | Needs the persisted status (flag 2) |
| Block done until dependencies are done | A hard rule in the UI | free/open source | Simple | Real founders do things out of order (a licence before an entity); blocking is wrong for them |
| NetworkX for the dependency graph | A mature Python graph library | free/open source | Ready-made longest-path | A new dependency where an in-house graph already exists |

- **Recommended:** Server function recomputes remaining critical path and months from statuses; the UI warns on done-before-dependencies. It makes the roadmap actually move with the founder's progress, warns without blocking out-of-order real life, and gives the cohort a progress band from the same source.
- **Ruled out:** Hard block: wrong for legitimate out-of-order work. NetworkX: duplicates the existing graph code.

### R179

**In-memory session store and per-session turn locks grow forever** · weight 58 · Optimisation · impact 2/5, reach 3/5, confidence 3/3 · flags F-A2-004, F-B5-019, F-A1-011

- **Evidence (A2):** backend/app/agents/store.py:58-65: MemoryStore._docs is never pruned; get() hides expired sessions but keeps them (probe: a 7 h-idle session was still in _docs). backend/app/routers/ideation.py:268: _turn_locks gains one asyncio.Lock per session through setdefault (lines 322 and 336), and nothing removes it, not even agent_delete (313-319). AGENT_STORE=auto falls back to MemoryStore whenever the database is not ready (store.py:245), which is the state today while 2.1.1 waits.
- **Evidence (B5):** backend/app/agents/store.py:60-65 MemoryStore.get returns None for an expired session but never removes it from _docs; MemoryStore is the automatic fallback when the database is unreachable (store.py:245), i.e. today. backend/app/routers/ideation.py:268, 324, 337 create an asyncio.Lock in _turn_locks for every session id before _load, including unknown ids that then 404; nothing removes entries.
- **Evidence (A1):** backend/app/routers/ideation.py:266-268 _turn_locks gains one Lock per session forever; 336-361 agent_turn_stream acquires the lock before returning StreamingResponse and releases it only in the generator's finally, which never runs if the generator is never started (client gone before the body is sent). The save happens only on the 'done' event (line 345-350), so a dropped stream discards the turn while the research/panel jobs it started keep running.

- **Why it matters:** A long-running offline or demo server keeps the full text of every conversation ever started in RAM, and a deleted conversation's lock entry survives. Memory grows without limit, and expired founder text is kept longer than the 6-hour rule allows.
- **Where to build it:** backend/app/agents/store.py (MemoryStore), backend/app/routers/ideation.py (_turn_locks)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Lazy sweep on create, plus lock cleanup on release and on delete | A few lines in existing code; no dependency | free/open source | Sweeps expired documents at most once a minute when a session is created; drops a lock when it is released with no waiters, and on delete | The sweep is O(n) when it runs (n is small offline) |
| cachetools.TTLCache | Widely used Python cache library | free/open source | Ready-made TTL eviction | A new dependency; its TTL resets only on write, so it needs care to match the updated_at rule |
| weakref.WeakValueDictionary for the locks | Standard library | free/open source | A lock disappears when no request holds it | Fixes the locks only, not the stored documents |
| Background asyncio task that sweeps every few minutes | Standard library, started from the app lifespan hook | free/open source | Predictable timing | Another lifecycle to start and stop, including in tests |

- **Recommended:** Lazy sweep on create, plus lock cleanup on release and on delete. It bounds memory with no new dependency and no background task, and it also applies the expiry rule to founder text held in RAM.
- **Ruled out:** cachetools: a dependency for a few lines of code; WeakValueDictionary: covers the locks only; background task: an extra lifecycle for no gain at this size.

### R188

**Translated sentences count as model rewording: provider and 'model' set with no call** · weight 58 · Logic flaw · impact 2/5, reach 3/5, confidence 3/3 · flags F-B5-025

- **Evidence (B5):** agents/ideation.py:791-795 — a translated line increments 'reworded' without calling the provider; ideation.py:813-814 then sets out['model']='model' and out['provider']=provider.name when reworded>0. A reply made entirely of translated fixed sentences reports Gemini/Ollama on the done event (ideation.py:1003-1004) though nothing was sent.

- **Why it matters:** Monitoring (5.4.2) and the quality report would credit the model for turns it never touched, and the Gemini data-use notice planned in 1.5.4 ('show a notice when the active provider is Gemini') would appear for turns where no founder text left the platform. Once 1.5.1 adds translations to the pure offline path, the same counter must not be reused there.
- **Where to build it:** agents/ideation.py (_reword_stream: separate counters for translated and model-reworded lines; 'model' and 'provider' only from real calls)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Separate 'translated' and 'reworded' counts; a 'fixed-translation' model label | Two integers in _reword_stream; out['model'] values already include 'offline (model failed)' style labels | free/open source | Truthful provider attribution for metrics and the notice; tiny change | Clients reading out['model']=='model' for the language tag must use the new per-sentence language instead |
| Record per-sentence origin (code, translation, model) in events | Extend the sentence event, as in flag 1 | free/open source | Most precise data for quality review | More payload per sentence |
| Leave as is | Current code | free/open source | None | Wrong metrics and a misleading data-use notice |

- **Recommended:** Separate 'translated' and 'reworded' counts; a 'fixed-translation' model label. Smallest change that keeps provider attribution truthful, which both monitoring and the Gemini notice depend on; per-sentence origin can come with flag 1's event change.
- **Ruled out:** Per-sentence origin alone: does not fix the reply-level provider field the notice reads; leave as is: keeps the misattribution.

### R190

**Lever text is fixed at search time; rewording by sector would force a new search** · weight 57 · Optimisation · impact 2/5, reach 4/5, confidence 2/3 · flags F-B4-025

- **Evidence (B4):** backend/app/research/novelty.py:62-70 check() takes idea, elements, scan and beneficiary, with no sector or domain, and _levers (:254-304) bakes final English sentences into the result. Research starts on the first turn of 20+ characters (agents/ideation.py offline stream), usually before the sector is asked, and its result is reused (reuse_done=True). 1.2.3 plans to re-run research whenever a core slot changes, and CORE_SLOTS includes sector (agents/ideation.py:58). The levers are narrated later, one per turn (agents/ideation.py:562-579).

- **Why it matters:** Wording levers by sector inside check() means either stale wording (sector unknown when research ran) or a full re-search, with several OpenAlex and other network calls under the free budget, just to change a sentence when the sector is answered or corrected. The founder also waits on the job board again.
- **Where to build it:** research/novelty.py (return lever kind plus facts: counts, pair names), agents/ideation.py _next_novelty_point (render the text at narration time from the session's current sector and domain)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Return structured levers (kind, numbers, pair) from novelty; render wording at narration from session slots with per-sector phrase tables | Same pattern as the planner's templates with facts; deterministic and fact-checkable (0005) | free/open source | Sector change rewords instantly with no network; 1.2.3 re-runs only when the idea itself changes | Moves text out of novelty.py; council evidence must render too |
| Pass sector into check() and re-run on sector change | Direct reading of 1.2.2 | free/open source | Simple | Wastes free-tier search budget and adds latency for a wording change |
| Cache search results and re-run only _levers on sector change | Existing source cache (Redis or in-memory) | free/open source | No new network calls | Still recomputes the whole novelty result and its job; more moving parts than late rendering |

- **Recommended:** Return structured levers (kind, numbers, pair) from novelty; render wording at narration from session slots with per-sector phrase tables. Separates searching (expensive, keyed by idea version per 1.2.3) from wording (cheap, keyed by current facts), which is what 1.2.2 actually needs.
- **Ruled out:** Re-run on sector change: spends free search budget on wording; cache plus re-run: more complex than rendering late.

### R191

**Tool results are stored twice in the session document and rewritten on every save** · weight 57 · Optimisation · impact 2/5, reach 4/5, confidence 2/3 · flags F-A1-032

- **Evidence (A1):** backend/app/agents/ideation.py:529-538 each tool_result (compact scan, novelty, roadmap JSON) is appended to s.messages and the same result is also kept in s.scan / s.novelty / s.roadmap; to_dict (:144-163) serialises both into the one session document saved after every turn (decision 0003). Probe: one build_roadmap tool_result is 9,045 bytes; each re-run of a tool adds another copy to messages.

- **Why it matters:** The session document (Redis now, PostgreSQL later) grows with every tool call even after 1.6.1 trims what the model sees; every turn rewrites the whole document, which matters on the 2G-sensitive save path and for Redis memory.
- **Where to build it:** backend/app/agents/ideation.py (messages, to_dict), agents/results.py (store results by reference)

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Store tool results by reference | Messages keep {'type':'tool_result','ref':'research:<version>'} and the content lives in the ResultStore; the provider adapter expands refs only for the trimmed window | free/open source | One copy; small session document | Adapter work; results store must persist with the session |
| Compress the session document (zlib/gzip) | Standard library | free/open source | Trivial, large saving on JSON | CPU per save; still duplicates |
| Drop tool results from messages older than the trim window | Part of 1.6.1 | free/open source | Bounded growth | Loses the record used by _facts unless facts move to a ledger |

- **Recommended:** Store tool results by reference. Removes the duplication and pairs naturally with 1.2.3's per-version results store.
- **Ruled out:** Compression: hides growth rather than removing it; Dropping old results: breaks the fact base unless the ledger exists.

### R205

**Cache hits are invisible: cached tokens are never recorded and Claude has no breakpoint** · weight 51 · Missing function · impact 2/5, reach 3/5, confidence 2/3 · flags F-B1-026

- **Evidence (B1):** providers.py:48-52 _usage keeps only input_tokens/output_tokens; the Gemini path (:327) reads total_input_tokens/total_output_tokens and ignores any cached-token count in the usage object. The Anthropic body (providers.py:111-121) sends system as a plain string with no cache_control block (grep 'cache_control' = 0). ideation.py:331-336 _spent counts input, output and cache_creation tokens, so a cached prefix counts against session_token_budget as fully as new input. Measured prefix: SYSTEM about 673 tokens + TOOLS about 862 tokens.

- **Why it matters:** 1.6.2 has no way to show it worked: no log or metric says whether a turn's prefix was served from cache. On the Claude path the reorder does nothing, because caching needs explicit breakpoints. The session budget also cuts off the model path early for long chats whose input is mostly a reused prefix. Whether a ~1.5k-token stable prefix meets Gemini's implicit-caching minimum for the configured model (gemini-3.8-flash, config.py:62) is unverified; without the counter nobody can find out.
- **Where to build it:** agents/providers.py (_usage records cached/read tokens per provider; an optional cache_control breakpoint on the static system block for Anthropic), agents/ideation.py (_spent policy), logs consumed by 5.4.2

| Option | Basis | Cost | Strengths | Drawbacks |
|---|---|---|---|---|
| Record cached tokens per provider into s.usage and the turn log | Both APIs report cached-token counts in their usage objects; the code already parses usage | free/open source | Makes 1.6.2 measurable and feeds 5.4.2's tokens per session | Field names differ per provider and need a check against live responses (1.5.3.1) |
| Count only uncached input against the session budget | Policy change in _spent | free/open source | Long sessions keep the model path | Needs the cached count first; free-tier limits may count all input |
| Add a cache_control breakpoint on the Anthropic static system | Documented Anthropic prompt-caching mechanism | paid | Real hits on the Claude path | Claude is dormant without a paid key; ruled out under the free constraint except as a prepared code path |
| Infer cache hits from latency only (5.4.1) | Step timings | free/open source | No parsing | Noisy on free tiers and 2G; cannot separate cache hits from load |

- **Recommended:** Record cached tokens per provider into s.usage and the turn log. Cheap, free, and the precondition for judging 1.6.1/1.6.2 and setting a fair budget. Decide the budget rule once the counts exist.
- **Ruled out:** Budget change first: needs the counts; Anthropic breakpoint: paid path, dormant under the free constraint; Latency inference: too noisy to prove a cache hit.

