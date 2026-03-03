import functools
from contextvars import ContextVar
from datetime import datetime, timezone

from ulid import ULID

# Module-level context var — holds current run_id
current_run_id: ContextVar[str | None] = ContextVar("current_run_id", default=None)


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
            error_info = None
            token = current_run_id.set(run_id)  # set context for nested calls
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as exc:
                status = "error"
                error_info = {
                    "type": type(exc).__name__,
                    "message": str(exc),
                }
                raise
            finally:
                current_run_id.reset(token)  # restore context
                ended_at = datetime.now(timezone.utc).isoformat()
                finished_payload = {
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
                    "error": error_info,
                }
                events.append(
                    _client._make_event(
                        "run_finished",
                        run_id=run_id,
                        span_id=None,
                        payload=finished_payload,
                    )
                )
                _client.send_events(events)
                _client.flush(run_id=run_id)

        return wrapper
    return decorator
