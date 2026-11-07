# Vanigam — Live Demo Runbook (for 10 Nov)

The project runs **fully offline and free** — no API keys, no database, no Redis.
When Postgres/Redis are absent the app logs a warning and falls back to an
in-memory store; this is expected and safe for a demo.

Verified working end-to-end (offline, via the API): health, ideation
conversation (reply + evidence + roadmap + novelty), scheme eligibility
(eligible / "we need to know" / ineligible), funding readiness and investor
matching, pipeline. 500+ backend tests pass.

---

## 1. One-time setup

```bash
cd frontend
npm install
```

(The Python backend dependencies are already installed in your environment —
the test suite runs. If on a fresh machine: `cd backend && pip install -e .`)

## 2. Start the two servers

Open **two terminals**.

Terminal A — backend (port 8000):

```bash
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Terminal B — frontend (port 5173):

```bash
cd frontend
npm run dev
```

Then open **http://localhost:5173** in a browser. The frontend proxies `/api`
and `/health` to the backend automatically (see `frontend/vite.config.ts`), so
there is nothing else to configure.

> In the Claude Code desktop app you can instead launch the saved configs
> **vanigam-backend** and **vanigam-frontend** (from `.claude/launch.json`).

## 3. The demo path (click-through)

1. **Home** (`/`) — open the app; one line on what Vanigam does.
2. **Ideate** (`/ideate`) or **Talk** (`/talk`) — type a real idea, e.g.
   *"a solar-powered cold box for small vegetable vendors in Salem"*.
   - The agent replies, scans prior art, and shows evidence, a novelty read and
     a draft roadmap. (All offline — it uses rule-based fallbacks, so it works
     with no API key.)
   - Show that it **asks one question at a time** and handles corrections
     ("actually I'm in Salem, not Erode") and negation ("no customers yet").
3. **Schemes** (`/schemes`) — recommend schemes for the founder. Show the three
   honest groups: **eligible**, **"We need to know"** (schemes that depend on a
   fact you haven't given — it asks instead of refusing), and **not a fit** with
   a real reason each.
4. **Funding** (`/funding`) — readiness across six dimensions with **coverage**
   (it says "not enough answers" rather than scoring you zero), a gap plan whose
   impact is the real rubric change, and investor matching with
   **eligible / check-with-investor / not-a-fit** and a "why" on each fit.
5. **Pipeline** (`/pipeline`) — move an investor through stages; metrics
   (conversion, time-in-stage, value by stage) update honestly.

Other live screens: Journey, Cohort, B2B, Supply, Suppliers, Intel.

## 4. Talking points (what makes it credible)

- **Never a false "no".** Eligibility is three-valued: an unknown fact becomes a
  question, never an invented refusal.
- **A reason for every answer.** Ineligible schemes and investors always say why.
- **Offline-first.** No paid API; it degrades gracefully instead of breaking.
- **Deterministic core.** Scoring, matching and eligibility are plain code and
  fully tested, so the same input always gives the same answer on stage.

## 5. If something misbehaves on the day

- **Port already in use** → change `--port 8000` and the matching target in
  `frontend/vite.config.ts`, or kill the old process.
- **A turn feels slow (~3 s)** → that is the research job waiting for an absent
  Redis to time out; it still completes. Harmless for a demo.
- **Blank screen** → make sure *both* servers are running and you opened
  `localhost:5173` (the frontend), not `:8000` (the API).
- **"database_unavailable" / "redis.unavailable" in the backend log** → expected
  and handled; the app uses an in-memory store.
