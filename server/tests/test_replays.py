import pytest
from httpx import AsyncClient
import json
import gzip

# Reuse the full-run events from test_runs
EVENTS_FULL_RUN = [
    {
        "schema_version": "1.0",
        "event_id": "r_evt_1",
        "event_type": "run_started",
        "timestamp": "2026-03-01T12:00:00Z",
        "project": {"id": "proj_test"},
        "sdk": {"name": "agentops-python", "version": "0.1.0"},
        "context": {"trace_id": "t_r1", "run_id": "01JREPLAY_SRC000001", "span_id": None},
        "payload": {"name": "replay_source_agent", "tags": {}, "input": {}},
    },
    {
        "schema_version": "1.0",
        "event_id": "r_evt_2",
        "event_type": "run_finished",
        "timestamp": "2026-03-01T12:00:05Z",
        "project": {"id": "proj_test"},
        "sdk": {"name": "agentops-python", "version": "0.1.0"},
        "context": {"trace_id": "t_r1", "run_id": "01JREPLAY_SRC000001", "span_id": None},
        "payload": {
            "status": "success",
            "timing": {
                "started_at": "2026-03-01T12:00:00Z",
                "ended_at": "2026-03-01T12:00:05Z",
            },
            "summary": {"total_prompt_tokens": 0, "total_completion_tokens": 0, "total_cost_usd": 0.0},
            "output": {},
        },
    },
]


@pytest.mark.asyncio
async def test_create_replay_returns_queued(client: AsyncClient):
    # Ingest a source run first
    body = gzip.compress(json.dumps(EVENTS_FULL_RUN).encode())
    await client.post(
        "/v1/ingest",
        content=body,
        headers={"Content-Type": "application/json", "Content-Encoding": "gzip"},
    )

    # Create replay
    resp = await client.post(
        "/v1/replays",
        json={
            "source_run_id": "01JREPLAY_SRC000001",
            "mode": "llm_only",
            "overrides": {"model": "gpt-4o-mini", "temperature": 0.5},
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["source_run_id"] == "01JREPLAY_SRC000001"
    assert data["status"] in ("queued", "running", "done")
    assert data["mode"] == "llm_only"
    replay_id = data["id"]

    # Get replay status
    resp = await client.get(f"/v1/replays/{replay_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == replay_id


@pytest.mark.asyncio
async def test_get_replay_not_found(client: AsyncClient):
    resp = await client.get("/v1/replays/01JNONEXISTENT0000000000")
    assert resp.status_code == 404
