# AgentOps

Sentry for AI agents. Trace execution, track cost, replay runs, and version prompts — in 10 lines of code.

Built for AI SaaS teams (2–20 engineers) using OpenAI or Anthropic SDKs who need visibility into what their agents are actually doing in production.

---

## Quick Start

```bash
pip install agentops
```

```python
import agentops

agentops.init(api_key="your-api-key")

@agentops.track(name="research-agent")
def run_agent(query: str):
    # your agent logic here
    response = openai_client.chat.completions.create(...)
    return response

run_agent("Summarize recent AI papers")
```

That's it. The run appears in the dashboard with a full span timeline, token counts, cost, and latency.

---

## Features (MVP)

- **Trace** — span timeline for every agent run: LLM calls, tool calls, latency, status
- **Cost** — token usage and USD cost per run, per model, per day
- **Replay** — re-run LLM spans against a different model or temperature; compare outputs side-by-side
- **Prompt Versioning** — store and diff prompt versions; link each run to the prompt that produced it

---

## Running Locally

**Prerequisites:** Docker, Python 3.11+, Node 18+

```bash
# 1. Start Postgres (and all backing services)
docker compose up -d

# 2. Run DB migrations
cd server && alembic upgrade head

# 3. Start the API server
cd server && DATABASE_URL="postgresql+asyncpg://agentops:agentops@localhost:5432/agentops" \
  uvicorn app.main:app --reload

# 4. Start the dashboard
cd dashboard && npm run dev   # http://localhost:3000
```

Run the end-to-end smoke test:

```bash
python examples/hello_trace.py
```

---

## Project Structure

```
boostrap-agent-ops-v1/
  sdk/          # Python SDK (pip install agentops)
  server/       # FastAPI backend + Arq background worker
  dashboard/    # React/Next.js frontend
  docs/         # PRD and architecture docs
  examples/     # Smoke tests and usage examples
```

**Key server directories:**

```
server/app/
  api/          # ingest, runs, prompts, replays, metrics endpoints
  models/       # SQLAlchemy tables, Pydantic schemas
  services/     # ingest_store, normalizer, cost, replay_runner
  workers/      # Arq background worker
```

---

## Development

See [CLAUDE.md](./CLAUDE.md) for the full command reference including how to run tests, install the SDK in dev mode, and build the dashboard.
