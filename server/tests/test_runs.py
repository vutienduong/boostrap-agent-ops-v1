import pytest
from httpx import AsyncClient

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
async def test_ingest_full_run(client: AsyncClient):
    resp = await client.post("/v1/ingest", json=EVENTS_FULL_RUN)
    assert resp.status_code == 200
    data = resp.json()
    assert data["accepted"] == 4
    assert data["rejected"] == 0


@pytest.mark.asyncio
async def test_list_runs(client: AsyncClient):
    # Ingest the full run first
    ingest_resp = await client.post("/v1/ingest", json=EVENTS_FULL_RUN)
    assert ingest_resp.status_code == 200

    # List runs for the test project
    resp = await client.get("/v1/runs", params={"project_id": "proj_test"})
    assert resp.status_code == 200
    data = resp.json()

    assert "runs" in data
    assert len(data["runs"]) >= 1

    run_ids = [r["id"] for r in data["runs"]]
    assert "01JRUN0001" in run_ids

    run = next(r for r in data["runs"] if r["id"] == "01JRUN0001")
    assert run["project_id"] == "proj_test"
    assert run["name"] == "test_agent"
    assert run["status"] == "success"
    assert run["total_prompt_tokens"] == 100
    assert run["total_completion_tokens"] == 50
    assert abs(run["total_cost_usd"] - 0.005) < 1e-9


@pytest.mark.asyncio
async def test_get_run_detail_with_spans(client: AsyncClient):
    # Ingest the full run first
    ingest_resp = await client.post("/v1/ingest", json=EVENTS_FULL_RUN)
    assert ingest_resp.status_code == 200

    # Fetch run detail
    resp = await client.get("/v1/runs/01JRUN0001")
    assert resp.status_code == 200
    data = resp.json()

    assert data["id"] == "01JRUN0001"
    assert data["project_id"] == "proj_test"
    assert data["name"] == "test_agent"
    assert data["status"] == "success"

    assert "spans" in data
    assert len(data["spans"]) == 1

    span = data["spans"][0]
    assert span["id"] == "01JSPAN001"
    assert span["run_id"] == "01JRUN0001"
    assert span["type"] == "llm"
    assert span["name"] == "call_claude"
    assert span["status"] == "success"
    assert span["tokens_prompt"] == 100
    assert span["tokens_completion"] == 50
    assert abs(span["cost_usd"] - 0.005) < 1e-9


@pytest.mark.asyncio
async def test_get_run_not_found(client: AsyncClient):
    resp = await client.get("/v1/runs/nonexistent_run_id")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Run not found"
