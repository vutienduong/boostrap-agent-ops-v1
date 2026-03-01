# AgentOps Implementation Design

**Date:** 2026-03-02
**Stack:** FastAPI (Python) + Next.js (React) + Postgres + Redis/Arq
**Deployment:** Docker Compose (local-first, deploy later)
**Strategy:** Full vertical slice — thin end-to-end layers, then thicken

---

## Slice 1 — "Hello Trace" (prove the full loop)

Goal: SDK sends events -> server stores them -> dashboard shows trace timeline.

### Python SDK (minimal)
- `agentops.init(api_key, project="...")` — configure endpoint + credentials
- `@agentops.track(name="my_agent")` decorator — creates run, emits `run_started`/`run_finished`
- Manual `span()` context manager for wrapping calls
- Synchronous flush (no async buffering yet)
- Generates `run_id` and `span_id` as ULIDs
- Event format follows the contract in `docs/mvp-architect.md` (envelope + payload)

### FastAPI Backend
- `POST /v1/ingest` — accepts JSON array of events, validates, stores to `raw_events`
- `GET /v1/runs?project_id=...&limit=50&cursor=...` — list runs, cursor pagination
- `GET /v1/runs/{run_id}` — run detail with nested spans
- Inline normalizer: on ingest, immediately upsert `runs` and `spans` tables (no worker yet)
- No auth in slice 1 (hardcoded project for simplicity)

### Postgres (Alembic migrations)
- `raw_events` — append-only, stores full event JSON
- `projects` — id, name, created_at (seed one default project)
- `runs` — id (ULID), project_id, name, status, started_at, ended_at, duration_ms, total_prompt_tokens, total_completion_tokens, total_cost_usd, tags (jsonb)
- `spans` — id, run_id, parent_span_id, type, name, started_at, ended_at, duration_ms, status, model, tokens_prompt, tokens_completion, cost_usd, input_json, output_json, error_json

### Next.js Dashboard
- Runs list page: table with name, status, duration, cost, timestamp
- Run detail page: spans timeline (vertical list showing type, name, model, tokens, latency, status)
- Expand span to see input/output JSON
- Fetches from FastAPI backend (CORS configured)

### Docker Compose
- `postgres:16` container
- `api` container (FastAPI + uvicorn)
- `dashboard` container (Next.js dev server)
- Shared network, `.env` for config

### Deliverable
Run a Python script with `@agentops.track()`, see the trace appear in the dashboard.

---

## Slice 2 — "Real Pipeline" (production-like data flow)

Goal: Async SDK, background worker, LLM provider instrumentation, cost tracking.

### SDK Enhancements
- Async event buffering: flush every 1-3s or when buffer hits N events
- gzip compression for `POST /v1/ingest`
- `agentops.openai_client(client)` — wraps OpenAI client, auto-emits LLM spans with model/usage
- `agentops.anthropic_client(client)` — wraps Anthropic client, same
- Context propagation via `contextvars` so spans auto-attach to current run

### Backend Enhancements
- Redis + Arq worker container added to Docker Compose
- Ingest endpoint writes to `raw_events` only (fast path)
- Arq worker: polls raw_events, normalizes into `runs`/`spans` (upsert)
- Cost computation: map model + tokens to USD using pricing table
- `GET /v1/metrics/cost?project_id=...&from=...&to=...&group_by=day|model` endpoint
- API key auth middleware: `X-AgentOps-Key` header, lookup against `api_keys` table (hashed)

### Dashboard Enhancements
- Cost dashboard page: daily cost chart, model breakdown
- Filter runs by date range, status
- Show cost per run in runs list

### New Tables
- `api_keys` — id, project_id, key_hash, name, created_at, revoked_at

### Deliverable
Instrument a real OpenAI/Anthropic call, see spans with accurate token counts and cost in dashboard.

---

## Slice 3 — "Dev Value" (features that make it worth paying for)

Goal: Prompt versioning, replay, polish.

### Prompt Versioning
- `POST /v1/prompts` — create prompt version (key, version, content)
- `GET /v1/prompts?project_id=...&key=...` — list versions
- `GET /v1/prompts/{id}` — get content
- SDK helper: `agentops.prompt_version(key, version, content_hash)` — links run to prompt version
- Dashboard: prompt versions list, content diff between versions

### Replay (LLM-only)
- `POST /v1/replays` — create replay from source run with overrides (model, temperature)
- `GET /v1/replays/{id}` — status + link to new run
- Replay runner service: loads source run's LLM spans, re-executes with overrides via provider SDK, stores as new run
- Tool spans displayed but skipped/mocked
- Dashboard: replay trigger button on run detail, side-by-side output comparison

### SDK Polish
- Basic redaction hook: `agentops.set_redactor(fn)` — user-defined function to mask sensitive data
- Truncation: inline payload max 32KB, set `truncated: true`
- Error capture: exception info in span error field
- Console trace URL output in local dev mode

### New Tables
- `prompt_versions` — id, project_id, key, version, content, meta (jsonb), created_at
- `replays` — id, source_run_id, new_run_id, mode, overrides (jsonb), status, created_at

### Deliverable
Full MVP: dev installs SDK, adds 10 lines, sees traces + cost, can version prompts, can replay a run with different model and compare outputs.

---

## Repo Structure (Monorepo)

```
boostrap-agent-ops-v1/
  docs/                    # PRD, architecture, plans
  server/                  # FastAPI backend
    app/
      main.py
      api/
        ingest.py
        runs.py
        prompts.py
        replays.py
        metrics.py
      core/
        config.py
        auth.py
        db.py
      models/
        tables.py          # SQLAlchemy models
        schemas.py         # Pydantic request/response
      services/
        ingest_store.py
        normalizer.py
        cost.py
        replay_runner.py
      workers/
        worker.py          # Arq tasks
    alembic/
    tests/
    requirements.txt
    Dockerfile
  sdk/                     # Python SDK
    agentops/
      __init__.py
      client.py
      decorators.py
      transport.py
      instrumentors/
        openai.py
        anthropic.py
    tests/
    setup.py
  dashboard/               # Next.js frontend
    src/
      app/                 # App Router pages
      components/
      lib/                 # API client, utils
    package.json
    Dockerfile
  docker-compose.yml
  .env.example
```

---

## Key Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| ID generation | ULID | Sortable, globally unique, URL-safe |
| Event storage | Append-only raw_events + derived tables | Allows reprocessing, audit trail |
| Slice 1 normalizer | Inline (on ingest) | No Redis dependency initially |
| SDK context | Python contextvars | Async-safe, no global state |
| Dashboard routing | Next.js App Router | Modern, supports SSR if needed later |
| ORM | SQLAlchemy 2.0 + Alembic | Standard, well-supported |
| API serialization | Pydantic v2 | Fast, native FastAPI integration |
| Auth (slice 2+) | API key hash in DB | Simple, no JWT complexity for MVP |
