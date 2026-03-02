import gzip
import json

import pytest
from httpx import AsyncClient

EVENTS = [
    {
        "schema_version": "1.0",
        "event_id": "m_evt_1",
        "event_type": "run_started",
        "timestamp": "2026-03-01T10:00:00Z",
        "project": {"id": "proj_test"},
        "sdk": {"name": "agentops-python", "version": "0.1.0"},
        "context": {"trace_id": "t1", "run_id": "01JMRUN001", "span_id": None},
        "payload": {"name": "cost_agent", "tags": {}, "input": {}},
    },
    {
        "schema_version": "1.0",
        "event_id": "m_evt_2",
        "event_type": "run_finished",
        "timestamp": "2026-03-01T10:00:05Z",
        "project": {"id": "proj_test"},
        "sdk": {"name": "agentops-python", "version": "0.1.0"},
        "context": {"trace_id": "t1", "run_id": "01JMRUN001", "span_id": None},
        "payload": {
            "status": "success",
            "timing": {
                "started_at": "2026-03-01T10:00:00Z",
                "ended_at": "2026-03-01T10:00:05Z",
            },
            "summary": {
                "total_prompt_tokens": 500,
                "total_completion_tokens": 200,
                "total_cost_usd": 0.025,
            },
            "output": {},
        },
    },
]


@pytest.mark.asyncio
async def test_cost_metrics_returns_totals(client: AsyncClient):
    # Ingest the run events via gzip
    body = gzip.compress(json.dumps(EVENTS).encode())
    await client.post(
        "/v1/ingest",
        content=body,
        headers={"Content-Type": "application/json", "Content-Encoding": "gzip"},
    )

    resp = await client.get(
        "/v1/metrics/cost",
        params={"project_id": "proj_test"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_cost_usd"] == pytest.approx(0.025, abs=0.001)
    assert data["total_prompt_tokens"] == 500
    assert data["total_completion_tokens"] == 200
    assert len(data["by_day"]) >= 1


@pytest.mark.asyncio
async def test_cost_metrics_empty_project(client: AsyncClient):
    resp = await client.get(
        "/v1/metrics/cost",
        params={"project_id": "proj_test"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_cost_usd"] == 0.0
