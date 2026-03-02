# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AgentOps is a dev-first AI agent observability tool ("Sentry for AI agents"). It helps AI startups trace agent execution, track cost/token usage, replay runs for debugging, and compare prompt/model changes.

Target: AI SaaS founders (2-20 engineers) using OpenAI/Anthropic SDKs. Not enterprise.

## Architecture

**Product = 4 capabilities:** Trace, Cost, Replay (LLM-only), Prompt Versioning.

### Components
- **Python SDK** (`agentops-python`): `@track()` decorator, OpenAI/Anthropic client wrappers, async event batching, context propagation via `contextvars`
- **FastAPI backend**: Ingestion API, query endpoints, replay runner
- **Postgres**: Raw events (append-only) + derived tables (runs, spans, prompt_versions, replays)
- **Redis + Arq**: Background worker for event normalization and replay execution
- **React/Next.js dashboard**: Trace timeline, cost view, prompt versions, replay trigger
- **Object storage (S3/R2)**: Large payloads (>32KB)

### Data Flow
```
SDK → POST /v1/ingest (ndjson/gzip) → raw_events table → Arq worker normalizes → runs/spans tables → Dashboard queries
Replay: Dashboard → POST /v1/replays → worker re-executes LLM spans with overrides → new run stored
```

### Server Repo Structure
```
agentops-server/
  app/
    main.py
    api/         # ingest, runs, prompts, replays, metrics
    core/        # config, auth, db, ulid
    models/      # SQLAlchemy tables, Pydantic schemas
    services/    # ingest_store, normalizer, cost, replay_runner
    workers/     # Arq background worker
  alembic/
  tests/
```

### Key API Endpoints
- `POST /v1/ingest` - Batch event ingestion (auth via `X-AgentOps-Key` header)
- `GET /v1/runs` - List runs (cursor pagination with ULID)
- `GET /v1/runs/{run_id}` - Run detail with spans timeline
- `POST /v1/prompts` - Create prompt version
- `POST /v1/replays` - Trigger LLM-only replay with model/temp overrides
- `GET /v1/metrics/cost` - Cost breakdown by day/model/run_name

### Data Model (Postgres)
Core tables: `raw_events`, `projects`, `api_keys`, `runs`, `spans`, `prompt_versions`, `replays`. API keys stored as hashes only. Run/span IDs use ULIDs.

### Event Schema (SDK → Server)
Four event types: `run_started`, `span_started`, `span_finished`, `run_finished`. Inline payload max 32KB per event (SDK truncates + sets `truncated: true`).

## Design Principles
- Bootstrap/ship-fast mindset: no microservices, no enterprise features (RBAC, SOC2, policy engine)
- SDK-first DX: 10-line integration, `pip install agentops`
- Append-only raw events, derived tables built by worker
- Replay is LLM-only in v1 (tool spans displayed but skipped/mocked)
- No queue initially (Postgres append + worker), add Arq/Redis when needed

## Reference Docs
- `docs/prd.md` - Full PRD with use cases, pricing, and success metrics
- `docs/mvp-architect.md` - Architecture details, data model, event contracts, API surface, and 2-week sprint plan

## Development Commands

| Command | Purpose |
|---------|---------|
| `docker compose up -d` | Start Postgres (and all services) |
| `cd server && alembic upgrade head` | Run DB migrations |
| `cd server && DATABASE_URL="postgresql+asyncpg://agentops:agentops@localhost:5432/agentops" uvicorn app.main:app --reload` | Run API server locally |
| `cd server && pytest -v` | Run server tests |
| `cd sdk && pip install -e ".[dev]"` | Install SDK in dev mode |
| `cd sdk && pytest -v` | Run SDK tests |
| `cd dashboard && npm run dev` | Start dashboard (http://localhost:3000) |
| `cd dashboard && npm run build` | Build/type-check dashboard |
| `python examples/hello_trace.py` | Run end-to-end smoke test |
