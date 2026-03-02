import json

import pytest
from pytest_httpx import HTTPXMock

import agentops


@pytest.fixture(autouse=True)
def reset_client():
    """Reset global client state between tests."""
    agentops._client = None
    yield
    agentops._client = None


def test_init_creates_client():
    agentops.init(api_key="test_key", endpoint="http://localhost:8000")
    assert agentops._client is not None
    assert agentops._client.api_key == "test_key"


def test_track_decorator_sends_events(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="http://fakeserver/v1/ingest",
        json={"accepted": 2, "rejected": 0, "errors": []},
    )

    agentops.init(api_key="test_key", endpoint="http://fakeserver")

    @agentops.track(name="my_agent")
    def my_func(x):
        return x * 2

    result = my_func(5)
    assert result == 10

    requests = httpx_mock.get_requests()
    assert len(requests) == 1

    body = json.loads(requests[0].content)
    event_types = [e["event_type"] for e in body]
    assert "run_started" in event_types
    assert "run_finished" in event_types


def test_track_decorator_sends_fail_status_on_exception(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="http://fakeserver/v1/ingest",
        json={"accepted": 2, "rejected": 0, "errors": []},
    )

    agentops.init(api_key="test_key", endpoint="http://fakeserver")

    @agentops.track(name="failing_agent")
    def failing_func():
        raise ValueError("boom")

    with pytest.raises(ValueError):
        failing_func()

    requests = httpx_mock.get_requests()
    body = json.loads(requests[0].content)
    finished = next(e for e in body if e["event_type"] == "run_finished")
    assert finished["payload"]["status"] == "fail"


def test_track_without_init_runs_normally():
    """If init() not called, the decorated function still runs."""
    agentops._client = None

    @agentops.track(name="no_init")
    def plain_func():
        return 42

    assert plain_func() == 42
