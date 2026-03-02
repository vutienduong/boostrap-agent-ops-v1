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
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                status = "fail"
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
