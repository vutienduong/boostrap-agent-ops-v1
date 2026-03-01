# AgentOps Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build AgentOps — a dev-first AI agent observability tool with trace, cost, replay, and prompt versioning.

**Architecture:** Monorepo with 3 packages: Python SDK (`sdk/`), FastAPI backend (`server/`), Next.js dashboard (`dashboard/`). Postgres for storage, Redis+Arq for background workers. Full vertical slice approach — thin end-to-end first, then thicken.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy 2.0, Alembic, Arq, Pydantic v2, Next.js 14 (App Router), TypeScript, Tailwind CSS, Docker Compose, pytest, Vitest.

**Design doc:** `docs/plans/2026-03-02-agentops-implementation-design.md`
**PRD:** `docs/prd.md`
**Architecture reference:** `docs/mvp-architect.md`

---

# SLICE 1 — "Hello Trace" (prove the full loop)

## Task 1: Project Scaffolding + Docker Compose

**Files:**
- Create: `docker-compose.yml`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `server/requirements.txt`
- Create: `server/Dockerfile`
- Create: `server/app/__init__.py`
- Create: `server/app/main.py`
- Create: `dashboard/package.json`
- Create: `dashboard/Dockerfile`
- Create: `sdk/setup.py`
- Create: `sdk/agentops/__init__.py`

**Step 1: Create `.gitignore`**

```gitignore
__pycache__/
*.pyc
.env
*.egg-info/
dist/
build/
node_modules/
.next/
.pytest_cache/
venv/
.venv/
```

**Step 2: Create `.env.example`**

```env
DATABASE_URL=postgresql+asyncpg://agentops:agentops@localhost:5432/agentops
POSTGRES_USER=agentops
POSTGRES_PASSWORD=agentops
POSTGRES_DB=agentops
API_HOST=0.0.0.0
API_PORT=8000
DASHBOARD_URL=http://localhost:3000
API_URL=http://localhost:8000
```

**Step 3: Create `docker-compose.yml`**

```yaml
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-agentops}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-agentops}
      POSTGRES_DB: ${POSTGRES_DB:-agentops}
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  api:
    build: ./server
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql+asyncpg://agentops:agentops@postgres:5432/agentops
    depends_on:
      - postgres
    volumes:
      - ./server:/app

  dashboard:
    build: ./dashboard
    ports:
      - "3000:3000"
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:8000
    depends_on:
      - api
    volumes:
      - ./dashboard:/app
      - /app/node_modules

volumes:
  pgdata:
```

**Step 4: Create `server/requirements.txt`**

```
fastapi==0.115.6
uvicorn[standard]==0.34.0
sqlalchemy[asyncio]==2.0.36
asyncpg==0.30.0
alembic==1.14.1
pydantic==2.10.4
pydantic-settings==2.7.1
python-ulid==3.0.0
httpx==0.28.1
pytest==8.3.4
pytest-asyncio==0.25.0
```

**Step 5: Create `server/Dockerfile`**

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

**Step 6: Create `server/app/__init__.py`** (empty)

**Step 7: Create `server/app/main.py`**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="AgentOps", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}
```

**Step 8: Create `sdk/agentops/__init__.py`** (empty placeholder)

**Step 9: Create `sdk/setup.py`**

```python
from setuptools import setup, find_packages

setup(
    name="agentops",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "httpx>=0.28.0",
        "python-ulid>=3.0.0",
    ],
    python_requires=">=3.10",
)
```

**Step 10: Scaffold Next.js dashboard**

Run:
```bash
cd dashboard && npx create-next-app@latest . --typescript --tailwind --eslint --app --src-dir --no-import-alias
```

**Step 11: Create `dashboard/Dockerfile`**

```dockerfile
FROM node:20-slim
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install
COPY . .
CMD ["npm", "run", "dev"]
```

**Step 12: Verify Docker Compose starts**

Run: `docker compose up --build -d && docker compose ps`
Expected: 3 services running (postgres, api, dashboard)

Run: `curl http://localhost:8000/health`
Expected: `{"status":"ok"}`

**Step 13: Commit**

```bash
git add -A
git commit -m "feat: project scaffolding with Docker Compose

FastAPI server, Next.js dashboard, Python SDK skeleton, Postgres.
All services start via docker compose up."
```

---

## Task 2: Database Schema + Alembic Migrations

**Files:**
- Create: `server/alembic.ini`
- Create: `server/alembic/env.py`
- Create: `server/app/core/__init__.py`
- Create: `server/app/core/config.py`
- Create: `server/app/core/db.py`
- Create: `server/app/models/__init__.py`
- Create: `server/app/models/tables.py`

**Step 1: Create `server/app/core/config.py`**

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://agentops:agentops@localhost:5432/agentops"
    sync_database_url: str = "postgresql://agentops:agentops@localhost:5432/agentops"

    class Config:
        env_file = ".env"


settings = Settings()
```

**Step 2: Create `server/app/core/db.py`**

```python
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session() as session:
        yield session
```

**Step 3: Create `server/app/models/tables.py`**

Define all Slice 1 tables: `projects`, `raw_events`, `runs`, `spans`.

```python
import datetime
from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    runs: Mapped[list["Run"]] = relationship(back_populates="project")


class RawEvent(Base):
    __tablename__ = "raw_events"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(26), ForeignKey("projects.id"))
    received_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    event_type: Mapped[str] = mapped_column(String(50))
    run_id: Mapped[str] = mapped_column(String(26), index=True)
    span_id: Mapped[str | None] = mapped_column(String(26), nullable=True)
    trace_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    payload: Mapped[dict] = mapped_column(JSONB)
    sdk_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    sdk_version: Mapped[str | None] = mapped_column(String(20), nullable=True)


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(26), ForeignKey("projects.id"))
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="running")
    started_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ended_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_cost_usd: Mapped[float] = mapped_column(default=0.0)
    tags: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    input_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    output_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    project: Mapped["Project"] = relationship(back_populates="runs")
    spans: Mapped[list["Span"]] = relationship(back_populates="run")

    __table_args__ = (
        Index("ix_runs_project_started", "project_id", "started_at"),
    )


class Span(Base):
    __tablename__ = "spans"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(26), ForeignKey("runs.id"))
    parent_span_id: Mapped[str | None] = mapped_column(String(26), nullable=True)
    type: Mapped[str] = mapped_column(String(20))  # llm, tool, retrieval, custom
    name: Mapped[str] = mapped_column(String(255))
    started_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ended_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="running")
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tokens_prompt: Mapped[int] = mapped_column(Integer, default=0)
    tokens_completion: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(default=0.0)
    input_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    output_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    run: Mapped["Run"] = relationship(back_populates="spans")

    __table_args__ = (
        Index("ix_spans_run_started", "run_id", "started_at"),
    )
```

**Step 4: Initialize Alembic**

Run:
```bash
cd server && pip install -r requirements.txt && alembic init alembic
```

**Step 5: Configure `server/alembic/env.py`**

Replace target_metadata with:
```python
from app.core.config import settings
from app.core.db import Base
from app.models.tables import Project, RawEvent, Run, Span  # noqa: F401

target_metadata = Base.metadata
```

Set `sqlalchemy.url` in `alembic.ini` to:
```
sqlalchemy.url = postgresql://agentops:agentops@localhost:5432/agentops
```

**Step 6: Generate and run migration**

Run:
```bash
cd server && alembic revision --autogenerate -m "initial schema" && alembic upgrade head
```

**Step 7: Seed a default project**

Create `server/app/core/seed.py`:
```python
from ulid import ULID
from sqlalchemy import select
from app.core.db import async_session
from app.models.tables import Project

DEFAULT_PROJECT_ID = "01JDEFAULTPROJECT000000000"


async def seed_default_project():
    async with async_session() as session:
        result = await session.execute(
            select(Project).where(Project.id == DEFAULT_PROJECT_ID)
        )
        if result.scalar_one_or_none() is None:
            session.add(Project(id=DEFAULT_PROJECT_ID, name="Default Project"))
            await session.commit()
```

Add startup event in `server/app/main.py`:
```python
from contextlib import asynccontextmanager
from app.core.seed import seed_default_project

@asynccontextmanager
async def lifespan(app: FastAPI):
    await seed_default_project()
    yield

app = FastAPI(title="AgentOps", version="0.1.0", lifespan=lifespan)
```

**Step 8: Verify migration works**

Run: `cd server && alembic upgrade head`
Expected: tables created, no errors

**Step 9: Commit**

```bash
git add server/alembic.ini server/alembic/ server/app/core/ server/app/models/
git commit -m "feat: database schema with Alembic migrations

Tables: projects, raw_events, runs, spans.
SQLAlchemy 2.0 async models with ULID primary keys."
```

---

## Task 3: Ingest API Endpoint

**Files:**
- Create: `server/app/models/__init__.py`
- Create: `server/app/models/schemas.py`
- Create: `server/app/api/__init__.py`
- Create: `server/app/api/ingest.py`
- Create: `server/app/services/__init__.py`
- Create: `server/app/services/ingest_store.py`
- Create: `server/app/services/normalizer.py`
- Test: `server/tests/test_ingest.py`

**Step 1: Write the failing test**

Create `server/tests/conftest.py`:
```python
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.db import Base, get_db
from app.main import app

TEST_DB_URL = "postgresql+asyncpg://agentops:agentops@localhost:5432/agentops_test"
test_engine = create_async_engine(TEST_DB_URL)
test_session = async_sessionmaker(test_engine, expire_on_commit=False)


@pytest.fixture(autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client():
    async def override_get_db():
        async with test_session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
    app.dependency_overrides.clear()
```

Create `server/tests/test_ingest.py`:
```python
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_ingest_accepts_events(client: AsyncClient):
    events = [
        {
            "schema_version": "1.0",
            "event_id": "01JEVT0001",
            "event_type": "run_started",
            "timestamp": "2026-03-01T12:00:00Z",
            "project": {"id": "proj_test"},
            "sdk": {"name": "agentops-python", "version": "0.1.0"},
            "context": {"trace_id": "trace_1", "run_id": "01JRUN0001", "span_id": None},
            "payload": {"name": "test_agent", "tags": {}, "input": {}},
        }
    ]
    resp = await client.post("/v1/ingest", json=events)
    assert resp.status_code == 200
    data = resp.json()
    assert data["accepted"] == 1
    assert data["rejected"] == 0
```

**Step 2: Run test to verify it fails**

Run: `cd server && pytest tests/test_ingest.py -v`
Expected: FAIL (404 — route doesn't exist)

**Step 3: Create Pydantic schemas `server/app/models/schemas.py`**

```python
from datetime import datetime
from pydantic import BaseModel


class EventContext(BaseModel):
    trace_id: str | None = None
    run_id: str
    span_id: str | None = None


class EventSDK(BaseModel):
    name: str
    version: str


class EventProject(BaseModel):
    id: str
    environment: str | None = None


class IngestEvent(BaseModel):
    schema_version: str = "1.0"
    event_id: str
    event_type: str
    timestamp: datetime
    project: EventProject
    sdk: EventSDK
    context: EventContext
    payload: dict


class IngestResponse(BaseModel):
    accepted: int
    rejected: int
    errors: list[str] = []


class SpanResponse(BaseModel):
    id: str
    run_id: str
    parent_span_id: str | None
    type: str
    name: str
    started_at: datetime | None
    ended_at: datetime | None
    duration_ms: int | None
    status: str
    model: str | None
    tokens_prompt: int
    tokens_completion: int
    cost_usd: float
    input_json: dict | None
    output_json: dict | None
    error_json: dict | None


class RunSummary(BaseModel):
    id: str
    project_id: str
    name: str | None
    status: str
    started_at: datetime | None
    ended_at: datetime | None
    duration_ms: int | None
    total_prompt_tokens: int
    total_completion_tokens: int
    total_cost_usd: float
    tags: dict | None


class RunDetail(RunSummary):
    spans: list[SpanResponse] = []
    input_json: dict | None = None
    output_json: dict | None = None


class RunListResponse(BaseModel):
    runs: list[RunSummary]
    cursor: str | None = None
```

**Step 4: Create ingest store `server/app/services/ingest_store.py`**

```python
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from ulid import ULID

from app.models.tables import RawEvent


async def store_raw_events(
    session: AsyncSession, events: list[dict]
) -> tuple[int, int, list[str]]:
    accepted = 0
    rejected = 0
    errors: list[str] = []

    for event in events:
        try:
            raw = RawEvent(
                id=str(ULID()),
                project_id=event["project"]["id"],
                received_at=datetime.now(timezone.utc),
                event_type=event["event_type"],
                run_id=event["context"]["run_id"],
                span_id=event["context"].get("span_id"),
                trace_id=event["context"].get("trace_id"),
                payload=event.get("payload", {}),
                sdk_name=event.get("sdk", {}).get("name"),
                sdk_version=event.get("sdk", {}).get("version"),
            )
            session.add(raw)
            accepted += 1
        except Exception as e:
            rejected += 1
            errors.append(str(e))

    await session.commit()
    return accepted, rejected, errors
```

**Step 5: Create inline normalizer `server/app/services/normalizer.py`**

```python
from datetime import datetime
from dateutil.parser import isoparse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tables import Run, Span


async def normalize_event(session: AsyncSession, event: dict) -> None:
    event_type = event["event_type"]
    ctx = event["context"]
    payload = event.get("payload", {})
    timestamp = event.get("timestamp")

    if event_type == "run_started":
        run = Run(
            id=ctx["run_id"],
            project_id=event["project"]["id"],
            name=payload.get("name"),
            status="running",
            started_at=timestamp,
            tags=payload.get("tags"),
            input_json=payload.get("input"),
        )
        session.add(run)

    elif event_type == "run_finished":
        result = await session.execute(
            select(Run).where(Run.id == ctx["run_id"])
        )
        run = result.scalar_one_or_none()
        if run:
            run.status = payload.get("status", "success")
            run.ended_at = timestamp
            timing = payload.get("timing", {})
            if timing.get("started_at") and timing.get("ended_at"):
                start = isoparse(timing["started_at"])
                end = isoparse(timing["ended_at"])
                run.duration_ms = int((end - start).total_seconds() * 1000)
            summary = payload.get("summary", {})
            run.total_prompt_tokens = summary.get("total_prompt_tokens", 0)
            run.total_completion_tokens = summary.get("total_completion_tokens", 0)
            run.total_cost_usd = summary.get("total_cost_usd", 0.0)
            run.output_json = payload.get("output")

    elif event_type == "span_started":
        attrs = payload.get("attributes", {})
        span = Span(
            id=ctx["span_id"],
            run_id=ctx["run_id"],
            parent_span_id=payload.get("parent_span_id"),
            type=payload.get("type", "custom"),
            name=payload.get("name", "unknown"),
            started_at=timestamp,
            status="running",
            model=attrs.get("model"),
            input_json=payload.get("input"),
        )
        session.add(span)

    elif event_type == "span_finished":
        result = await session.execute(
            select(Span).where(Span.id == ctx["span_id"])
        )
        span = result.scalar_one_or_none()
        if span:
            span.status = payload.get("status", "success")
            timing = payload.get("timing", {})
            if timing.get("started_at"):
                span.started_at = isoparse(timing["started_at"])
            if timing.get("ended_at"):
                span.ended_at = isoparse(timing["ended_at"])
            if timing.get("started_at") and timing.get("ended_at"):
                start = isoparse(timing["started_at"])
                end = isoparse(timing["ended_at"])
                span.duration_ms = int((end - start).total_seconds() * 1000)
            usage = payload.get("usage", {})
            span.tokens_prompt = usage.get("prompt_tokens", 0)
            span.tokens_completion = usage.get("completion_tokens", 0)
            cost = payload.get("cost", {})
            span.cost_usd = cost.get("value", 0.0)
            span.output_json = payload.get("output")
            span.error_json = payload.get("error")

    await session.commit()
```

**Step 6: Create ingest API `server/app/api/ingest.py`**

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.schemas import IngestEvent, IngestResponse
from app.services.ingest_store import store_raw_events
from app.services.normalizer import normalize_event

router = APIRouter(prefix="/v1", tags=["ingest"])


@router.post("/ingest", response_model=IngestResponse)
async def ingest_events(
    events: list[IngestEvent],
    session: AsyncSession = Depends(get_db),
):
    raw_dicts = [e.model_dump(mode="json") for e in events]

    accepted, rejected, errors = await store_raw_events(session, raw_dicts)

    for raw in raw_dicts:
        try:
            await normalize_event(session, raw)
        except Exception:
            pass  # normalization failure shouldn't block ingest

    return IngestResponse(accepted=accepted, rejected=rejected, errors=errors)
```

**Step 7: Register router in `server/app/main.py`**

Add:
```python
from app.api.ingest import router as ingest_router
app.include_router(ingest_router)
```

**Step 8: Run test to verify it passes**

Run: `cd server && pytest tests/test_ingest.py -v`
Expected: PASS

**Step 9: Commit**

```bash
git add server/app/api/ server/app/services/ server/app/models/schemas.py server/tests/
git commit -m "feat: ingest API endpoint with inline normalizer

POST /v1/ingest accepts event batches, stores raw_events,
normalizes into runs/spans tables inline."
```

---

## Task 4: Query API Endpoints (Runs List + Detail)

**Files:**
- Create: `server/app/api/runs.py`
- Test: `server/tests/test_runs.py`

**Step 1: Write failing tests**

Create `server/tests/test_runs.py`:
```python
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


EVENTS_FULL_RUN = [
    {
        "schema_version": "1.0",
        "event_id": "evt_1",
        "event_type": "run_started",
        "timestamp": "2026-03-01T12:00:00Z",
        "project": {"id": "proj_test"},
        "sdk": {"name": "agentops-python", "version": "0.1.0"},
        "context": {"trace_id": "t1", "run_id": "01JRUN0001", "span_id": None},
        "payload": {"name": "test_agent", "tags": {"env": "test"}, "input": {"q": "hi"}},
    },
    {
        "schema_version": "1.0",
        "event_id": "evt_2",
        "event_type": "span_started",
        "timestamp": "2026-03-01T12:00:01Z",
        "project": {"id": "proj_test"},
        "sdk": {"name": "agentops-python", "version": "0.1.0"},
        "context": {"trace_id": "t1", "run_id": "01JRUN0001", "span_id": "01JSPAN001"},
        "payload": {
            "parent_span_id": None,
            "type": "llm",
            "name": "call_claude",
            "attributes": {"model": "claude-3-5-sonnet", "temperature": 0.2},
            "input": {"inline": {"messages": [{"role": "user", "content": "hi"}]}},
        },
    },
    {
        "schema_version": "1.0",
        "event_id": "evt_3",
        "event_type": "span_finished",
        "timestamp": "2026-03-01T12:00:02Z",
        "project": {"id": "proj_test"},
        "sdk": {"name": "agentops-python", "version": "0.1.0"},
        "context": {"trace_id": "t1", "run_id": "01JRUN0001", "span_id": "01JSPAN001"},
        "payload": {
            "status": "success",
            "timing": {
                "started_at": "2026-03-01T12:00:01Z",
                "ended_at": "2026-03-01T12:00:02Z",
            },
            "usage": {"prompt_tokens": 100, "completion_tokens": 50},
            "cost": {"currency": "USD", "value": 0.005},
            "output": {"inline": {"text": "Hello!"}},
            "error": None,
        },
    },
    {
        "schema_version": "1.0",
        "event_id": "evt_4",
        "event_type": "run_finished",
        "timestamp": "2026-03-01T12:00:03Z",
        "project": {"id": "proj_test"},
        "sdk": {"name": "agentops-python", "version": "0.1.0"},
        "context": {"trace_id": "t1", "run_id": "01JRUN0001", "span_id": None},
        "payload": {
            "status": "success",
            "timing": {
                "started_at": "2026-03-01T12:00:00Z",
                "ended_at": "2026-03-01T12:00:03Z",
            },
            "summary": {
                "total_prompt_tokens": 100,
                "total_completion_tokens": 50,
                "total_cost_usd": 0.005,
            },
            "output": {"inline": {"result": "done"}},
        },
    },
]


@pytest.mark.asyncio
async def test_list_runs(client: AsyncClient):
    await client.post("/v1/ingest", json=EVENTS_FULL_RUN)

    resp = await client.get("/v1/runs", params={"project_id": "proj_test"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["runs"]) == 1
    assert data["runs"][0]["name"] == "test_agent"
    assert data["runs"][0]["status"] == "success"


@pytest.mark.asyncio
async def test_get_run_detail(client: AsyncClient):
    await client.post("/v1/ingest", json=EVENTS_FULL_RUN)

    resp = await client.get("/v1/runs/01JRUN0001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "01JRUN0001"
    assert len(data["spans"]) == 1
    assert data["spans"][0]["type"] == "llm"
    assert data["spans"][0]["model"] == "claude-3-5-sonnet"
    assert data["spans"][0]["tokens_prompt"] == 100
```

**Step 2: Run test to verify it fails**

Run: `cd server && pytest tests/test_runs.py -v`
Expected: FAIL (404)

**Step 3: Create `server/app/api/runs.py`**

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.db import get_db
from app.models.schemas import RunDetail, RunListResponse, RunSummary, SpanResponse
from app.models.tables import Run, Span

router = APIRouter(prefix="/v1", tags=["runs"])


@router.get("/runs", response_model=RunListResponse)
async def list_runs(
    project_id: str = Query(...),
    limit: int = Query(50, le=100),
    cursor: str | None = Query(None),
    session: AsyncSession = Depends(get_db),
):
    query = (
        select(Run)
        .where(Run.project_id == project_id)
        .order_by(Run.started_at.desc().nullslast(), Run.id.desc())
        .limit(limit + 1)
    )
    if cursor:
        query = query.where(Run.id < cursor)

    result = await session.execute(query)
    runs = list(result.scalars().all())

    next_cursor = None
    if len(runs) > limit:
        next_cursor = runs[limit].id
        runs = runs[:limit]

    return RunListResponse(
        runs=[
            RunSummary(
                id=r.id,
                project_id=r.project_id,
                name=r.name,
                status=r.status,
                started_at=r.started_at,
                ended_at=r.ended_at,
                duration_ms=r.duration_ms,
                total_prompt_tokens=r.total_prompt_tokens,
                total_completion_tokens=r.total_completion_tokens,
                total_cost_usd=r.total_cost_usd,
                tags=r.tags,
            )
            for r in runs
        ],
        cursor=next_cursor,
    )


@router.get("/runs/{run_id}", response_model=RunDetail)
async def get_run(
    run_id: str,
    session: AsyncSession = Depends(get_db),
):
    result = await session.execute(
        select(Run).options(selectinload(Run.spans)).where(Run.id == run_id)
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    return RunDetail(
        id=run.id,
        project_id=run.project_id,
        name=run.name,
        status=run.status,
        started_at=run.started_at,
        ended_at=run.ended_at,
        duration_ms=run.duration_ms,
        total_prompt_tokens=run.total_prompt_tokens,
        total_completion_tokens=run.total_completion_tokens,
        total_cost_usd=run.total_cost_usd,
        tags=run.tags,
        input_json=run.input_json,
        output_json=run.output_json,
        spans=[
            SpanResponse(
                id=s.id,
                run_id=s.run_id,
                parent_span_id=s.parent_span_id,
                type=s.type,
                name=s.name,
                started_at=s.started_at,
                ended_at=s.ended_at,
                duration_ms=s.duration_ms,
                status=s.status,
                model=s.model,
                tokens_prompt=s.tokens_prompt,
                tokens_completion=s.tokens_completion,
                cost_usd=s.cost_usd,
                input_json=s.input_json,
                output_json=s.output_json,
                error_json=s.error_json,
            )
            for s in sorted(run.spans, key=lambda s: s.started_at or s.id)
        ],
    )
```

**Step 4: Register router in `server/app/main.py`**

```python
from app.api.runs import router as runs_router
app.include_router(runs_router)
```

**Step 5: Run test to verify it passes**

Run: `cd server && pytest tests/test_runs.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add server/app/api/runs.py server/tests/test_runs.py server/app/main.py
git commit -m "feat: runs list and detail query endpoints

GET /v1/runs with cursor pagination, GET /v1/runs/{id} with spans."
```

---

## Task 5: Python SDK (Minimal)

**Files:**
- Create: `sdk/agentops/__init__.py`
- Create: `sdk/agentops/client.py`
- Create: `sdk/agentops/decorators.py`
- Create: `sdk/agentops/transport.py`
- Test: `sdk/tests/test_sdk.py`

**Step 1: Write failing test**

Create `sdk/tests/conftest.py`:
```python
import pytest
```

Create `sdk/tests/test_sdk.py`:
```python
import agentops


def test_init_creates_client():
    agentops.init(api_key="test_key", endpoint="http://localhost:8000")
    assert agentops._client is not None
    assert agentops._client.api_key == "test_key"


def test_track_decorator_sends_events(httpx_mock):
    """Track decorator should emit run_started + run_finished."""
    httpx_mock.add_response(
        url="http://localhost:8000/v1/ingest",
        json={"accepted": 2, "rejected": 0, "errors": []},
    )

    agentops.init(api_key="test_key", endpoint="http://localhost:8000")

    @agentops.track(name="my_agent")
    def my_func(x):
        return x * 2

    result = my_func(5)
    assert result == 10

    requests = httpx_mock.get_requests()
    assert len(requests) >= 1
    events = requests[-1].content
    # Events should contain run_started and run_finished
    import json
    body = json.loads(events)
    event_types = [e["event_type"] for e in body]
    assert "run_started" in event_types
    assert "run_finished" in event_types
```

**Step 2: Run test to verify it fails**

Run: `cd sdk && pip install -e ".[dev]" && pytest tests/test_sdk.py -v`
Expected: FAIL

**Step 3: Create `sdk/agentops/transport.py`**

```python
import httpx


class Transport:
    def __init__(self, endpoint: str, api_key: str):
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key
        self._client = httpx.Client(timeout=10.0)

    def send(self, events: list[dict]) -> dict:
        resp = self._client.post(
            f"{self.endpoint}/v1/ingest",
            json=events,
            headers={"X-AgentOps-Key": self.api_key},
        )
        resp.raise_for_status()
        return resp.json()
```

**Step 4: Create `sdk/agentops/client.py`**

```python
from datetime import datetime, timezone
from ulid import ULID

from agentops.transport import Transport


class AgentOpsClient:
    def __init__(self, api_key: str, endpoint: str, project_id: str | None = None):
        self.api_key = api_key
        self.project_id = project_id or "default"
        self.transport = Transport(endpoint=endpoint, api_key=api_key)

    def _make_event(self, event_type: str, run_id: str, span_id: str | None, payload: dict) -> dict:
        return {
            "schema_version": "1.0",
            "event_id": str(ULID()),
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "project": {"id": self.project_id},
            "sdk": {"name": "agentops-python", "version": "0.1.0"},
            "context": {
                "trace_id": run_id,
                "run_id": run_id,
                "span_id": span_id,
            },
            "payload": payload,
        }

    def send_events(self, events: list[dict]) -> None:
        try:
            self.transport.send(events)
        except Exception:
            pass  # fail silently in SDK — don't break user's app
```

**Step 5: Create `sdk/agentops/decorators.py`**

```python
import functools
from datetime import datetime, timezone
from ulid import ULID


def track(name: str | None = None):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            from agentops import _client

            if _client is None:
                return func(*args, **kwargs)

            run_id = str(ULID())
            run_name = name or func.__name__
            started_at = datetime.now(timezone.utc).isoformat()

            events = []

            events.append(
                _client._make_event(
                    "run_started",
                    run_id=run_id,
                    span_id=None,
                    payload={"name": run_name, "tags": {}, "input": {}},
                )
            )

            status = "success"
            error = None
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                status = "fail"
                error = str(e)
                raise
            finally:
                ended_at = datetime.now(timezone.utc).isoformat()
                events.append(
                    _client._make_event(
                        "run_finished",
                        run_id=run_id,
                        span_id=None,
                        payload={
                            "status": status,
                            "timing": {
                                "started_at": started_at,
                                "ended_at": ended_at,
                            },
                            "summary": {
                                "total_prompt_tokens": 0,
                                "total_completion_tokens": 0,
                                "total_cost_usd": 0.0,
                            },
                            "output": {},
                        },
                    )
                )
                _client.send_events(events)

        return wrapper
    return decorator
```

**Step 6: Create `sdk/agentops/__init__.py`**

```python
from agentops.client import AgentOpsClient
from agentops.decorators import track

_client: AgentOpsClient | None = None


def init(api_key: str, endpoint: str = "http://localhost:8000", project: str | None = None):
    global _client
    _client = AgentOpsClient(api_key=api_key, endpoint=endpoint, project_id=project)


__all__ = ["init", "track"]
```

**Step 7: Update `sdk/setup.py` with test deps**

```python
setup(
    name="agentops",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "httpx>=0.28.0",
        "python-ulid>=3.0.0",
    ],
    extras_require={
        "dev": ["pytest", "pytest-httpx"],
    },
    python_requires=">=3.10",
)
```

**Step 8: Run test to verify it passes**

Run: `cd sdk && pip install -e ".[dev]" && pytest tests/test_sdk.py -v`
Expected: PASS

**Step 9: Commit**

```bash
git add sdk/
git commit -m "feat: minimal Python SDK with track decorator

agentops.init() + @agentops.track() sends run_started/run_finished
to server via synchronous HTTP."
```

---

## Task 6: Next.js Dashboard — Runs List + Detail Pages

**Files:**
- Create: `dashboard/src/lib/api.ts`
- Create: `dashboard/src/app/page.tsx` (runs list)
- Create: `dashboard/src/app/runs/[runId]/page.tsx` (run detail)
- Create: `dashboard/src/components/runs-table.tsx`
- Create: `dashboard/src/components/span-timeline.tsx`

**Step 1: Create API client `dashboard/src/lib/api.ts`**

```typescript
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface RunSummary {
  id: string;
  project_id: string;
  name: string | null;
  status: string;
  started_at: string | null;
  ended_at: string | null;
  duration_ms: number | null;
  total_prompt_tokens: number;
  total_completion_tokens: number;
  total_cost_usd: number;
  tags: Record<string, string> | null;
}

export interface Span {
  id: string;
  run_id: string;
  parent_span_id: string | null;
  type: string;
  name: string;
  started_at: string | null;
  ended_at: string | null;
  duration_ms: number | null;
  status: string;
  model: string | null;
  tokens_prompt: number;
  tokens_completion: number;
  cost_usd: number;
  input_json: Record<string, unknown> | null;
  output_json: Record<string, unknown> | null;
  error_json: Record<string, unknown> | null;
}

export interface RunDetail extends RunSummary {
  spans: Span[];
  input_json: Record<string, unknown> | null;
  output_json: Record<string, unknown> | null;
}

export async function fetchRuns(projectId: string): Promise<{ runs: RunSummary[]; cursor: string | null }> {
  const res = await fetch(`${API_URL}/v1/runs?project_id=${projectId}`);
  if (!res.ok) throw new Error("Failed to fetch runs");
  return res.json();
}

export async function fetchRun(runId: string): Promise<RunDetail> {
  const res = await fetch(`${API_URL}/v1/runs/${runId}`);
  if (!res.ok) throw new Error("Failed to fetch run");
  return res.json();
}
```

**Step 2: Create runs table component `dashboard/src/components/runs-table.tsx`**

```tsx
"use client";

import Link from "next/link";
import { RunSummary } from "@/lib/api";

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    success: "bg-green-100 text-green-800",
    fail: "bg-red-100 text-red-800",
    running: "bg-yellow-100 text-yellow-800",
  };
  return (
    <span className={`px-2 py-1 rounded text-xs font-medium ${colors[status] || "bg-gray-100 text-gray-800"}`}>
      {status}
    </span>
  );
}

export function RunsTable({ runs }: { runs: RunSummary[] }) {
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="border-b text-left text-gray-500">
          <th className="py-3 px-4">Name</th>
          <th className="py-3 px-4">Status</th>
          <th className="py-3 px-4">Duration</th>
          <th className="py-3 px-4">Tokens</th>
          <th className="py-3 px-4">Cost</th>
          <th className="py-3 px-4">Started</th>
        </tr>
      </thead>
      <tbody>
        {runs.map((run) => (
          <tr key={run.id} className="border-b hover:bg-gray-50">
            <td className="py-3 px-4">
              <Link href={`/runs/${run.id}`} className="text-blue-600 hover:underline">
                {run.name || run.id}
              </Link>
            </td>
            <td className="py-3 px-4"><StatusBadge status={run.status} /></td>
            <td className="py-3 px-4">{run.duration_ms ? `${run.duration_ms}ms` : "—"}</td>
            <td className="py-3 px-4">{run.total_prompt_tokens + run.total_completion_tokens}</td>
            <td className="py-3 px-4">${run.total_cost_usd.toFixed(4)}</td>
            <td className="py-3 px-4">{run.started_at ? new Date(run.started_at).toLocaleString() : "—"}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
```

**Step 3: Create span timeline `dashboard/src/components/span-timeline.tsx`**

```tsx
"use client";

import { useState } from "react";
import { Span } from "@/lib/api";

function SpanRow({ span }: { span: Span }) {
  const [expanded, setExpanded] = useState(false);
  const typeColors: Record<string, string> = {
    llm: "border-l-blue-500",
    tool: "border-l-orange-500",
    retrieval: "border-l-purple-500",
    custom: "border-l-gray-500",
  };

  return (
    <div className={`border-l-4 ${typeColors[span.type] || "border-l-gray-300"} bg-white rounded shadow-sm mb-2`}>
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full text-left px-4 py-3 flex items-center justify-between hover:bg-gray-50"
      >
        <div className="flex items-center gap-3">
          <span className="text-xs font-mono bg-gray-100 px-2 py-0.5 rounded">{span.type}</span>
          <span className="font-medium">{span.name}</span>
          {span.model && <span className="text-xs text-gray-500">{span.model}</span>}
        </div>
        <div className="flex items-center gap-4 text-xs text-gray-500">
          <span>{span.tokens_prompt + span.tokens_completion} tokens</span>
          <span>{span.duration_ms ? `${span.duration_ms}ms` : "—"}</span>
          <span className={span.status === "success" ? "text-green-600" : "text-red-600"}>
            {span.status}
          </span>
        </div>
      </button>
      {expanded && (
        <div className="px-4 pb-4 border-t">
          {span.input_json && (
            <div className="mt-2">
              <p className="text-xs font-semibold text-gray-500 mb-1">Input</p>
              <pre className="text-xs bg-gray-50 p-2 rounded overflow-auto max-h-48">
                {JSON.stringify(span.input_json, null, 2)}
              </pre>
            </div>
          )}
          {span.output_json && (
            <div className="mt-2">
              <p className="text-xs font-semibold text-gray-500 mb-1">Output</p>
              <pre className="text-xs bg-gray-50 p-2 rounded overflow-auto max-h-48">
                {JSON.stringify(span.output_json, null, 2)}
              </pre>
            </div>
          )}
          {span.error_json && (
            <div className="mt-2">
              <p className="text-xs font-semibold text-red-500 mb-1">Error</p>
              <pre className="text-xs bg-red-50 p-2 rounded overflow-auto max-h-48">
                {JSON.stringify(span.error_json, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function SpanTimeline({ spans }: { spans: Span[] }) {
  return (
    <div className="space-y-1">
      {spans.map((span) => (
        <SpanRow key={span.id} span={span} />
      ))}
    </div>
  );
}
```

**Step 4: Create runs list page `dashboard/src/app/page.tsx`**

```tsx
"use client";

import { useEffect, useState } from "react";
import { fetchRuns, RunSummary } from "@/lib/api";
import { RunsTable } from "@/components/runs-table";

const PROJECT_ID = "proj_test"; // hardcoded for Slice 1

export default function HomePage() {
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchRuns(PROJECT_ID)
      .then((data) => setRuns(data.runs))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  return (
    <main className="max-w-6xl mx-auto p-8">
      <h1 className="text-2xl font-bold mb-6">Agent Runs</h1>
      {loading ? (
        <p className="text-gray-500">Loading...</p>
      ) : runs.length === 0 ? (
        <p className="text-gray-500">No runs yet. Send events via the SDK to get started.</p>
      ) : (
        <RunsTable runs={runs} />
      )}
    </main>
  );
}
```

**Step 5: Create run detail page `dashboard/src/app/runs/[runId]/page.tsx`**

```tsx
"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { fetchRun, RunDetail } from "@/lib/api";
import { SpanTimeline } from "@/components/span-timeline";

export default function RunDetailPage() {
  const params = useParams();
  const runId = params.runId as string;
  const [run, setRun] = useState<RunDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchRun(runId)
      .then(setRun)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [runId]);

  if (loading) return <p className="p-8 text-gray-500">Loading...</p>;
  if (!run) return <p className="p-8 text-red-500">Run not found</p>;

  return (
    <main className="max-w-6xl mx-auto p-8">
      <Link href="/" className="text-blue-600 hover:underline text-sm">&larr; Back to runs</Link>
      <div className="mt-4 mb-6">
        <h1 className="text-2xl font-bold">{run.name || run.id}</h1>
        <div className="flex gap-4 mt-2 text-sm text-gray-500">
          <span>Status: <strong className={run.status === "success" ? "text-green-600" : "text-red-600"}>{run.status}</strong></span>
          <span>Duration: {run.duration_ms ? `${run.duration_ms}ms` : "—"}</span>
          <span>Tokens: {run.total_prompt_tokens + run.total_completion_tokens}</span>
          <span>Cost: ${run.total_cost_usd.toFixed(4)}</span>
        </div>
      </div>

      <h2 className="text-lg font-semibold mb-3">Spans Timeline</h2>
      {run.spans.length === 0 ? (
        <p className="text-gray-500">No spans recorded.</p>
      ) : (
        <SpanTimeline spans={run.spans} />
      )}
    </main>
  );
}
```

**Step 6: Verify dashboard loads**

Run: `cd dashboard && npm run dev`
Visit: `http://localhost:3000`
Expected: Page loads with "No runs yet" message

**Step 7: Commit**

```bash
git add dashboard/src/
git commit -m "feat: dashboard with runs list and detail pages

Runs table with status, duration, tokens, cost.
Run detail with expandable span timeline showing input/output."
```

---

## Task 7: End-to-End Integration Test

**Files:**
- Create: `examples/hello_trace.py`

**Step 1: Create example script `examples/hello_trace.py`**

```python
"""
End-to-end test: SDK -> Server -> Dashboard.
Requires: docker compose up (postgres + api)
"""
import agentops
import time

agentops.init(api_key="test_key", endpoint="http://localhost:8000", project="proj_test")


@agentops.track(name="hello_agent")
def hello_agent():
    time.sleep(0.1)  # simulate work
    return "Hello from AgentOps!"


if __name__ == "__main__":
    result = hello_agent()
    print(f"Result: {result}")
    print("Check http://localhost:3000 to see the trace!")
```

**Step 2: Run the full stack**

Run: `docker compose up -d && cd server && alembic upgrade head`

**Step 3: Run the example**

Run: `cd sdk && pip install -e . && cd ../examples && python hello_trace.py`
Expected: "Result: Hello from AgentOps!" + trace visible at `http://localhost:3000`

**Step 4: Verify in dashboard**

Visit: `http://localhost:3000`
Expected: One run "hello_agent" appears, click to see detail with spans timeline.

**Step 5: Commit**

```bash
git add examples/
git commit -m "feat: hello_trace example proving full SDK->server->dashboard loop"
```

---

# SLICE 2 — "Real Pipeline" (summary, implement after Slice 1 is solid)

### Task 8: Async SDK Buffering
- Add event buffer in `sdk/agentops/client.py` — flush every 2s or 50 events
- Background thread for flush
- gzip compression in transport

### Task 9: Redis + Arq Worker
- Add `redis` service to `docker-compose.yml`
- Create `server/app/workers/worker.py` with Arq
- Move normalization from inline to Arq task
- Ingest endpoint only writes raw_events (fast path)

### Task 10: OpenAI Instrumentor
- Create `sdk/agentops/instrumentors/openai.py`
- Wrap `client.chat.completions.create` to emit span_started/span_finished
- Capture model, tokens, cost from response

### Task 11: Anthropic Instrumentor
- Create `sdk/agentops/instrumentors/anthropic.py`
- Wrap `client.messages.create` to emit spans
- Capture model, input/output tokens, cost

### Task 12: API Key Auth
- Create `api_keys` table + migration
- Middleware to validate `X-AgentOps-Key` header (hash lookup)
- Key generation endpoint (or seed script)

### Task 13: Cost Metrics Endpoint + Dashboard
- `GET /v1/metrics/cost` with group_by (day, model)
- Aggregate query on runs/spans tables
- Dashboard cost page with chart (use recharts or similar)

---

# SLICE 3 — "Dev Value" (summary, implement after Slice 2)

### Task 14: Prompt Versioning
- `prompt_versions` table + migration
- CRUD endpoints: POST/GET /v1/prompts
- SDK helper: `agentops.prompt_version(key, version, content_hash)`
- Dashboard: prompts list, version diff view

### Task 15: Replay (LLM-only)
- `replays` table + migration
- `POST /v1/replays` — queue replay job
- Replay runner: load source spans, re-execute LLM calls with overrides
- `GET /v1/replays/{id}` — status
- Dashboard: replay button on run detail, side-by-side compare view

### Task 16: SDK Polish
- Redaction hook: `agentops.set_redactor(fn)`
- Truncation: 32KB max inline payload
- Error capture in spans
- Console trace URL in dev mode

---

# Quick Reference

| Command | Purpose |
|---------|---------|
| `docker compose up -d` | Start all services |
| `docker compose down` | Stop all services |
| `cd server && alembic upgrade head` | Run migrations |
| `cd server && pytest -v` | Run server tests |
| `cd sdk && pytest -v` | Run SDK tests |
| `cd dashboard && npm run dev` | Start dashboard dev server |
| `cd sdk && pip install -e .` | Install SDK locally |
