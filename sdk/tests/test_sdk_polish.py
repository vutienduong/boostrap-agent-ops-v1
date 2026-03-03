"""Tests for SDK Polish features (Task 16):
1. Redaction hook
2. Truncation (32KB max per field)
3. Error capture in spans
4. Console trace URL in dev mode
"""
import gzip
import json
import os
import sys

import pytest
from pytest_httpx import HTTPXMock

import agentops


@pytest.fixture(autouse=True)
def reset_client():
    """Reset global client state and redactor between tests."""
    agentops._client = None
    agentops._redactor = None
    yield
    agentops._client = None
    agentops._redactor = None


# ---------------------------------------------------------------------------
# Feature 1: Redaction hook
# ---------------------------------------------------------------------------

class TestRedactionHook:
    def test_set_redactor_stores_function(self):
        """set_redactor stores the provided function."""
        fn = lambda key, value: value
        agentops.set_redactor(fn)
        assert agentops._redactor is fn

    def test_redactor_called_on_event_fields(self, httpx_mock: HTTPXMock):
        """Redactor is applied to every string field in an event payload before sending."""
        httpx_mock.add_response(
            url="http://fakeserver/v1/ingest",
            json={"accepted": 2, "rejected": 0, "errors": []},
        )

        agentops.init(api_key="test_key", endpoint="http://fakeserver")

        redacted_keys = []

        def my_redactor(key, value):
            redacted_keys.append(key)
            if key == "name":
                return "REDACTED"
            return value

        agentops.set_redactor(my_redactor)

        @agentops.track(name="secret_agent")
        def my_func():
            return "done"

        my_func()

        requests = httpx_mock.get_requests()
        assert len(requests) >= 1
        body = json.loads(gzip.decompress(requests[0].content))
        # Find the run_started event and check its name was redacted
        started = next(e for e in body if e["event_type"] == "run_started")
        assert started["payload"]["name"] == "REDACTED"

    def test_redactor_scrubs_sensitive_key(self, httpx_mock: HTTPXMock):
        """Redactor can zero out specific keys like 'api_key'."""
        httpx_mock.add_response(
            url="http://fakeserver/v1/ingest",
            json={"accepted": 2, "rejected": 0, "errors": []},
        )

        agentops.init(api_key="test_key", endpoint="http://fakeserver")

        def scrub_secrets(key, value):
            if key in ("api_key", "password", "secret"):
                return "***"
            return value

        agentops.set_redactor(scrub_secrets)

        # Manually inject a sensitive payload
        agentops._client.send_events([
            agentops._client._make_event(
                "run_started",
                run_id="run-1",
                span_id=None,
                payload={"name": "test", "api_key": "sk-supersecret", "count": 5},
            )
        ])
        agentops.flush()

        requests = httpx_mock.get_requests()
        body = json.loads(gzip.decompress(requests[0].content))
        started = next(e for e in body if e["event_type"] == "run_started")
        assert started["payload"]["api_key"] == "***"
        # Non-sensitive field untouched
        assert started["payload"]["name"] == "test"
        # Non-string (int) field untouched
        assert started["payload"]["count"] == 5


# ---------------------------------------------------------------------------
# Feature 2: Truncation (32KB max per field)
# ---------------------------------------------------------------------------

MAX_FIELD_BYTES = 32768


class TestTruncation:
    def test_short_string_not_truncated(self, httpx_mock: HTTPXMock):
        """Strings under 32KB pass through unchanged."""
        httpx_mock.add_response(
            url="http://fakeserver/v1/ingest",
            json={"accepted": 1, "rejected": 0, "errors": []},
        )

        agentops.init(api_key="test_key", endpoint="http://fakeserver")

        short_val = "hello world"
        agentops._client.send_events([
            agentops._client._make_event(
                "run_started",
                run_id="run-1",
                span_id=None,
                payload={"name": short_val},
            )
        ])
        agentops.flush()

        requests = httpx_mock.get_requests()
        body = json.loads(gzip.decompress(requests[0].content))
        started = next(e for e in body if e["event_type"] == "run_started")
        assert started["payload"]["name"] == short_val
        # No _meta truncation info
        assert "_meta" not in started["payload"] or "name" not in started["payload"].get("_meta", {})

    def test_long_string_truncated(self, httpx_mock: HTTPXMock):
        """Strings exceeding 32KB are truncated to 32768 chars."""
        httpx_mock.add_response(
            url="http://fakeserver/v1/ingest",
            json={"accepted": 1, "rejected": 0, "errors": []},
        )

        agentops.init(api_key="test_key", endpoint="http://fakeserver")

        long_val = "x" * (MAX_FIELD_BYTES + 1000)
        agentops._client.send_events([
            agentops._client._make_event(
                "run_started",
                run_id="run-1",
                span_id=None,
                payload={"name": "ok", "content": long_val},
            )
        ])
        agentops.flush()

        requests = httpx_mock.get_requests()
        body = json.loads(gzip.decompress(requests[0].content))
        started = next(e for e in body if e["event_type"] == "run_started")

        # Value truncated to exactly MAX_FIELD_BYTES chars
        assert len(started["payload"]["content"]) == MAX_FIELD_BYTES

        # _meta records the truncation
        assert "_meta" in started["payload"]
        assert "content" in started["payload"]["_meta"]
        assert started["payload"]["_meta"]["content"]["truncated"] is True
        assert started["payload"]["_meta"]["content"]["original_size"] == len(long_val)

        # Untouched short field
        assert started["payload"]["name"] == "ok"

    def test_multiple_long_fields_all_truncated(self, httpx_mock: HTTPXMock):
        """Multiple oversized fields are all truncated, each recorded in _meta."""
        httpx_mock.add_response(
            url="http://fakeserver/v1/ingest",
            json={"accepted": 1, "rejected": 0, "errors": []},
        )

        agentops.init(api_key="test_key", endpoint="http://fakeserver")

        big_a = "a" * (MAX_FIELD_BYTES + 500)
        big_b = "b" * (MAX_FIELD_BYTES + 2000)
        agentops._client.send_events([
            agentops._client._make_event(
                "run_started",
                run_id="run-1",
                span_id=None,
                payload={"field_a": big_a, "field_b": big_b},
            )
        ])
        agentops.flush()

        requests = httpx_mock.get_requests()
        body = json.loads(gzip.decompress(requests[0].content))
        started = next(e for e in body if e["event_type"] == "run_started")

        assert len(started["payload"]["field_a"]) == MAX_FIELD_BYTES
        assert len(started["payload"]["field_b"]) == MAX_FIELD_BYTES
        assert started["payload"]["_meta"]["field_a"]["original_size"] == len(big_a)
        assert started["payload"]["_meta"]["field_b"]["original_size"] == len(big_b)


# ---------------------------------------------------------------------------
# Feature 3: Error capture in spans
# ---------------------------------------------------------------------------

class TestErrorCaptureInSpans:
    def test_exception_sets_error_status_and_error_field(self, httpx_mock: HTTPXMock):
        """When @track function raises, run_finished has status='error' and error dict."""
        httpx_mock.add_response(
            url="http://fakeserver/v1/ingest",
            json={"accepted": 2, "rejected": 0, "errors": []},
        )

        agentops.init(api_key="test_key", endpoint="http://fakeserver")

        @agentops.track(name="failing_agent")
        def bad_func():
            raise RuntimeError("something went wrong")

        with pytest.raises(RuntimeError):
            bad_func()

        requests = httpx_mock.get_requests()
        body = json.loads(gzip.decompress(requests[0].content))
        finished = next(e for e in body if e["event_type"] == "run_finished")

        assert finished["payload"]["status"] == "error"
        assert "error" in finished["payload"]
        assert finished["payload"]["error"]["type"] == "RuntimeError"
        assert finished["payload"]["error"]["message"] == "something went wrong"

    def test_exception_type_captured_correctly(self, httpx_mock: HTTPXMock):
        """Exception class name is captured in error.type."""
        httpx_mock.add_response(
            url="http://fakeserver/v1/ingest",
            json={"accepted": 2, "rejected": 0, "errors": []},
        )

        agentops.init(api_key="test_key", endpoint="http://fakeserver")

        @agentops.track(name="val_agent")
        def val_func():
            raise ValueError("bad value")

        with pytest.raises(ValueError):
            val_func()

        requests = httpx_mock.get_requests()
        body = json.loads(gzip.decompress(requests[0].content))
        finished = next(e for e in body if e["event_type"] == "run_finished")

        assert finished["payload"]["status"] == "error"
        assert finished["payload"]["error"]["type"] == "ValueError"
        assert finished["payload"]["error"]["message"] == "bad value"

    def test_success_has_no_error_field(self, httpx_mock: HTTPXMock):
        """Successful runs do not have an error field in run_finished."""
        httpx_mock.add_response(
            url="http://fakeserver/v1/ingest",
            json={"accepted": 2, "rejected": 0, "errors": []},
        )

        agentops.init(api_key="test_key", endpoint="http://fakeserver")

        @agentops.track(name="good_agent")
        def good_func():
            return 42

        good_func()

        requests = httpx_mock.get_requests()
        body = json.loads(gzip.decompress(requests[0].content))
        finished = next(e for e in body if e["event_type"] == "run_finished")

        assert finished["payload"]["status"] == "success"
        assert finished["payload"].get("error") is None


# ---------------------------------------------------------------------------
# Feature 4: Console trace URL
# ---------------------------------------------------------------------------

class TestConsoleTraceURL:
    def test_dev_mode_prints_trace_url_to_stderr(self, httpx_mock: HTTPXMock, capsys):
        """In dev mode, flush() prints trace URL to stderr."""
        httpx_mock.add_response(
            url="http://fakeserver/v1/ingest",
            json={"accepted": 2, "rejected": 0, "errors": []},
        )

        agentops.init(api_key="test_key", endpoint="http://fakeserver", dev=True)

        @agentops.track(name="dev_agent")
        def dev_func():
            return "ok"

        dev_func()

        captured = capsys.readouterr()
        assert "[AgentOps] Trace:" in captured.err
        assert "http://localhost:3000/runs/" in captured.err

    def test_non_dev_mode_no_trace_url(self, httpx_mock: HTTPXMock, capsys):
        """In non-dev mode, flush() does NOT print a trace URL."""
        httpx_mock.add_response(
            url="http://fakeserver/v1/ingest",
            json={"accepted": 2, "rejected": 0, "errors": []},
        )

        agentops.init(api_key="test_key", endpoint="http://fakeserver")

        @agentops.track(name="prod_agent")
        def prod_func():
            return "ok"

        prod_func()

        captured = capsys.readouterr()
        assert "[AgentOps] Trace:" not in captured.err
        assert "[AgentOps] Trace:" not in captured.out

    def test_dev_mode_via_env_var(self, httpx_mock: HTTPXMock, capsys, monkeypatch):
        """AGENTOPS_ENV=dev triggers trace URL printing."""
        httpx_mock.add_response(
            url="http://fakeserver/v1/ingest",
            json={"accepted": 2, "rejected": 0, "errors": []},
        )

        monkeypatch.setenv("AGENTOPS_ENV", "dev")
        agentops.init(api_key="test_key", endpoint="http://fakeserver")

        @agentops.track(name="env_dev_agent")
        def env_func():
            return "ok"

        env_func()

        captured = capsys.readouterr()
        assert "[AgentOps] Trace:" in captured.err
        assert "http://localhost:3000/runs/" in captured.err

    def test_dev_mode_trace_url_contains_run_id(self, httpx_mock: HTTPXMock, capsys):
        """Trace URL contains the actual run_id."""
        httpx_mock.add_response(
            url="http://fakeserver/v1/ingest",
            json={"accepted": 2, "rejected": 0, "errors": []},
        )

        agentops.init(api_key="test_key", endpoint="http://fakeserver", dev=True)

        @agentops.track(name="id_agent")
        def id_func():
            return "ok"

        id_func()

        # Get the run_id from the events sent
        requests = httpx_mock.get_requests()
        body = json.loads(gzip.decompress(requests[0].content))
        started = next(e for e in body if e["event_type"] == "run_started")
        run_id = started["context"]["run_id"]

        captured = capsys.readouterr()
        assert run_id in captured.err
