"""
OpenAI client instrumentor.

Usage:
    import agentops
    from openai import OpenAI

    agentops.init(api_key="...")
    client = agentops.instrument_openai(OpenAI())
    # Now all client.chat.completions.create calls are auto-traced
"""
from datetime import datetime, timezone
from typing import Any

from ulid import ULID

# Pricing per 1M tokens (USD) — approximate, update as needed
OPENAI_PRICING: dict[str, dict[str, float]] = {
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-4": {"input": 30.00, "output": 60.00},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    "o1": {"input": 15.00, "output": 60.00},
    "o1-mini": {"input": 3.00, "output": 12.00},
}


def _estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    pricing = OPENAI_PRICING.get(model, {"input": 0.0, "output": 0.0})
    return (prompt_tokens * pricing["input"] + completion_tokens * pricing["output"]) / 1_000_000


class _InstrumentedCompletions:
    def __init__(self, original_completions: Any):
        self._original = original_completions

    def create(self, *args: Any, **kwargs: Any) -> Any:
        from agentops import _client
        from agentops.decorators import current_run_id

        run_id = current_run_id.get()

        if _client is None or run_id is None:
            return self._original.create(*args, **kwargs)

        span_id = str(ULID())
        model = kwargs.get("model", "unknown")
        messages = kwargs.get("messages", [])
        started_at = datetime.now(timezone.utc).isoformat()

        _client.send_events([
            _client._make_event(
                "span_started",
                run_id=run_id,
                span_id=span_id,
                payload={
                    "parent_span_id": None,
                    "type": "llm",
                    "name": f"openai/{model}",
                    "attributes": {"provider": "openai", "model": model},
                    "input": {"inline": {"messages": messages}, "truncated": False},
                },
            )
        ])

        status = "success"
        error_info = None
        response = None
        try:
            response = self._original.create(*args, **kwargs)
            return response
        except Exception as e:
            status = "fail"
            error_info = {"message": str(e), "type": type(e).__name__}
            raise
        finally:
            ended_at = datetime.now(timezone.utc).isoformat()
            prompt_tokens = 0
            completion_tokens = 0
            output_text = None

            if response is not None:
                usage = getattr(response, "usage", None)
                if usage:
                    prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
                    completion_tokens = getattr(usage, "completion_tokens", 0) or 0
                choices = getattr(response, "choices", [])
                if choices:
                    msg = getattr(choices[0], "message", None)
                    if msg:
                        output_text = getattr(msg, "content", None)

            cost = _estimate_cost(model, prompt_tokens, completion_tokens)

            _client.send_events([
                _client._make_event(
                    "span_finished",
                    run_id=run_id,
                    span_id=span_id,
                    payload={
                        "status": status,
                        "timing": {"started_at": started_at, "ended_at": ended_at},
                        "usage": {
                            "prompt_tokens": prompt_tokens,
                            "completion_tokens": completion_tokens,
                        },
                        "cost": {"currency": "USD", "value": cost},
                        "output": {"inline": {"text": output_text}, "truncated": False},
                        "error": error_info,
                    },
                )
            ])


class _InstrumentedChat:
    def __init__(self, original_chat: Any):
        self._original = original_chat
        self.completions = _InstrumentedCompletions(original_chat.completions)


class InstrumentedOpenAIClient:
    """Wraps an OpenAI client to auto-emit AgentOps spans."""

    def __init__(self, client: Any):
        self._client = client
        self.chat = _InstrumentedChat(client.chat)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._client, name)


def instrument_openai(client: Any) -> "InstrumentedOpenAIClient":
    """Wrap an OpenAI client instance to auto-trace all chat completion calls."""
    return InstrumentedOpenAIClient(client)
