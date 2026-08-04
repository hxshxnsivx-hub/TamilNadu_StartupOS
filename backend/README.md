# Vanigam — Backend

Tamil Nadu StartupOS backend: FastAPI + LangGraph multi-agent services, PostgreSQL (pgvector/PostGIS), Redis, S3.
Managed-API-first: language, embedding, and LLM providers sit behind swappable adapters (self-host can drop in later).

Spec of record: [`.kiro/specs/tamil-nadu-startupos/`](../.kiro/specs/tamil-nadu-startupos/) and [`VANIGAM-MASTER-DOCUMENT.md`](../VANIGAM-MASTER-DOCUMENT.md).

## Layout

```
backend/
├── app/
│   ├── core/        # config, security, logging
│   ├── agents/      # LangGraph orchestrator + swarms
│   ├── services/    # CP-SAT, Graph, Embedding, Translation, Verification (adapters)
│   ├── models/      # Pydantic + SQLAlchemy models
│   ├── routers/     # FastAPI API v1 endpoints
│   └── db/          # engine, session, migrations
├── tests/           # unit / integration / property
├── pyproject.toml   # deps + ruff/black/pytest/mypy config
└── requirements.txt # mirror of runtime deps
```

## Quick start (dev)

```bash
# 1. Create & activate a virtualenv (Python 3.10+)
python -m venv .venv
# Windows:  .venv\Scripts\activate     PowerShell:  .venv\Scripts\Activate.ps1
# Unix:     source .venv/bin/activate

# 2. Install (editable, with dev tooling)
pip install -e ".[dev]"

# 3. Configure environment
cp .env.example .env    # then fill in provider API keys

# 4. Start local infra (Postgres+pgvector+PostGIS, Redis, MinIO) — Task 3
docker compose up -d

# 5. Run migrations — Task 5
alembic upgrade head

# 6. Run the API — Task 4
uvicorn app.main:app --reload
# → http://localhost:8000/health   and   /docs (OpenAPI)
```

## Dev commands

```bash
ruff check .          # lint
black .               # format
mypy app              # types
pytest                # tests
pytest --cov=app      # coverage
```

## Build order (live task list)

Phase 1 critical path: scaffold → app skeleton → DB schema → auth / profile → orchestrator → roadmap swarm → API.
See the session task list and [`tasks.md`](../.kiro/specs/tamil-nadu-startupos/tasks.md).
