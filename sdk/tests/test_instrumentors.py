"""Tests for OpenAI and Anthropic instrumentors."""
import json
import gzip
from unittest.mock import MagicMock

import pytest
from pytest_httpx import HTTPXMock

import agentops
from agentops.instrumentors.openai import instrument_openai
from agentops.instrumentors.anthropic import instrument_anthropic


@pytest.fixture(autouse=True)
def reset_client():
    agentops._client = None
    yield
    agentops._client = None


def _parse_request(request) -> list[dict]:
    body = request.content
    # requests from transport are gzip-compressed
    try:
        body = gzip.decompress(body)
    except Exception:
        pass
    return json.loads(body)


def test_openai_instrumentor_emits_span(httpx_mock: HTTPXMock):
    """instrument_openai wraps client and emits llm spans."""
    httpx_mock.add_response(
        url="http://fakeserver/v1/ingest",
        json={"accepted": 4, "rejected": 0, "errors": []},
    )

    agentops.init(api_key="key", endpoint="http://fakeserver")

    # Mock OpenAI client
    mock_response = MagicMock()
    mock_response.usage.prompt_tokens = 10
    mock_response.usage.completion_tokens = 5
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Hello!"

    mock_openai = MagicMock()
    mock_openai.chat.completions.create.return_value = mock_response

    client = instrument_openai(mock_openai)

    @agentops.track(name="openai_test")
    def run_agent():
        return client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "hi"}],
        )

    run_agent()
    agentops.flush()

    requests = httpx_mock.get_requests()
    all_events = []
    for req in requests:
        all_events.extend(_parse_request(req))

    event_types = [e["event_type"] for e in all_events]
    assert "run_started" in event_types
    assert "span_started" in event_types
    assert "span_finished" in event_types
    assert "run_finished" in event_types

    span_finished = next(e for e in all_events if e["event_type"] == "span_finished")
    assert span_finished["payload"]["usage"]["prompt_tokens"] == 10
    assert span_finished["payload"]["usage"]["completion_tokens"] == 5
    assert span_finished["payload"]["status"] == "success"


def test_anthropic_instrumentor_emits_span(httpx_mock: HTTPXMock):
    """instrument_anthropic wraps client and emits llm spans."""
    httpx_mock.add_response(
        url="http://fakeserver/v1/ingest",
        json={"accepted": 4, "rejected": 0, "errors": []},
    )

    agentops.init(api_key="key", endpoint="http://fakeserver")

    # Mock Anthropic client
    mock_response = MagicMock()
    mock_response.usage.input_tokens = 20
    mock_response.usage.output_tokens = 8
    mock_response.content = [MagicMock()]
    mock_response.content[0].text = "Hello from Claude!"

    mock_anthropic = MagicMock()
    mock_anthropic.messages.create.return_value = mock_response

    client = instrument_anthropic(mock_anthropic)

    @agentops.track(name="anthropic_test")
    def run_agent():
        return client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=100,
            messages=[{"role": "user", "content": "hi"}],
        )

    run_agent()
    agentops.flush()

    requests = httpx_mock.get_requests()
    all_events = []
    for req in requests:
        all_events.extend(_parse_request(req))

    event_types = [e["event_type"] for e in all_events]
    assert "span_started" in event_types
    assert "span_finished" in event_types

    span_finished = next(e for e in all_events if e["event_type"] == "span_finished")
    assert span_finished["payload"]["usage"]["prompt_tokens"] == 20
    assert span_finished["payload"]["usage"]["completion_tokens"] == 8


def test_instrumentor_outside_track_does_not_crash(httpx_mock: HTTPXMock):
    """Instrumentor called outside @track (no run_id) should pass through without emitting spans."""
    agentops.init(api_key="key", endpoint="http://fakeserver")

    mock_response = MagicMock()
    mock_response.usage.prompt_tokens = 5
    mock_response.usage.completion_tokens = 3
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "hi"

    mock_openai = MagicMock()
    mock_openai.chat.completions.create.return_value = mock_response

    client = instrument_openai(mock_openai)
    # No @track wrapper — run_id context is None
    result = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "hi"}],
    )
    # Should not have called the ingest server
    assert len(httpx_mock.get_requests()) == 0
