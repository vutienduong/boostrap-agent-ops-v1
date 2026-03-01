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


@pytest.mark.asyncio
async def test_ingest_normalizes_run(client: AsyncClient):
    """After run_started + run_finished, a Run row should exist."""
    events = [
        {
            "schema_version": "1.0",
            "event_id": "01JEVT0002",
            "event_type": "run_started",
            "timestamp": "2026-03-01T12:00:00Z",
            "project": {"id": "proj_test"},
            "sdk": {"name": "agentops-python", "version": "0.1.0"},
            "context": {"trace_id": "t1", "run_id": "01JRUN0002", "span_id": None},
            "payload": {"name": "my_agent", "tags": {}, "input": {}},
        },
        {
            "schema_version": "1.0",
            "event_id": "01JEVT0003",
            "event_type": "run_finished",
            "timestamp": "2026-03-01T12:00:03Z",
            "project": {"id": "proj_test"},
            "sdk": {"name": "agentops-python", "version": "0.1.0"},
            "context": {"trace_id": "t1", "run_id": "01JRUN0002", "span_id": None},
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
                "output": {"result": "done"},
            },
        },
    ]
    resp = await client.post("/v1/ingest", json=events)
    assert resp.status_code == 200
    assert resp.json()["accepted"] == 2
