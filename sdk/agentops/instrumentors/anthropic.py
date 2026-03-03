"""
Anthropic client instrumentor.

Usage:
    import agentops
    import anthropic

    agentops.init(api_key="...")
    client = agentops.instrument_anthropic(anthropic.Anthropic())
    # Now all client.messages.create calls are auto-traced
"""
from datetime import datetime, timezone
from typing import Any

from ulid import ULID

# Pricing per 1M tokens (USD) — approximate
ANTHROPIC_PRICING: dict[str, dict[str, float]] = {
    "claude-opus-4-5": {"input": 15.00, "output": 75.00},
    "claude-sonnet-4-5": {"input": 3.00, "output": 15.00},
    "claude-haiku-4-5": {"input": 0.80, "output": 4.00},
    "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
    "claude-3-5-haiku-20241022": {"input": 0.80, "output": 4.00},
    "claude-3-opus-20240229": {"input": 15.00, "output": 75.00},
    "claude-3-sonnet-20240229": {"input": 3.00, "output": 15.00},
    "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
}


def _estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    # Normalize model name (strip date suffixes for lookup)
    base = model.split("-2")[0]  # e.g. "claude-3-5-sonnet" from "claude-3-5-sonnet-20241022"
    pricing = ANTHROPIC_PRICING.get(model) or ANTHROPIC_PRICING.get(base, {"input": 0.0, "output": 0.0})
    return (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1_000_000


class _InstrumentedMessages:
    def __init__(self, original_messages: Any):
        self._original = original_messages

    def create(self, *args: Any, **kwargs: Any) -> Any:
        from agentops import _client
        from agentops.decorators import current_run_id

        run_id = current_run_id.get()

        if _client is None or run_id is None:
            return self._original.create(*args, **kwargs)

        span_id = str(ULID())
        model = kwargs.get("model", "unknown")
        messages = kwargs.get("messages", [])
        system = kwargs.get("system")
        started_at = datetime.now(timezone.utc).isoformat()

        input_payload: dict[str, Any] = {"messages": messages}
        if system:
            input_payload["system"] = system

        _client.send_events([
            _client._make_event(
                "span_started",
                run_id=run_id,
                span_id=span_id,
                payload={
                    "parent_span_id": None,
                    "type": "llm",
                    "name": f"anthropic/{model}",
                    "attributes": {"provider": "anthropic", "model": model},
                    "input": {"inline": input_payload, "truncated": False},
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
            input_tokens = 0
            output_tokens = 0
            output_text = None

            if response is not None:
                usage = getattr(response, "usage", None)
                if usage:
                    input_tokens = getattr(usage, "input_tokens", 0) or 0
                    output_tokens = getattr(usage, "output_tokens", 0) or 0
                content = getattr(response, "content", [])
                if content:
                    first = content[0]
                    output_text = getattr(first, "text", None)

            cost = _estimate_cost(model, input_tokens, output_tokens)

            _client.send_events([
                _client._make_event(
                    "span_finished",
                    run_id=run_id,
                    span_id=span_id,
                    payload={
                        "status": status,
                        "timing": {"started_at": started_at, "ended_at": ended_at},
                        "usage": {
                            "prompt_tokens": input_tokens,
                            "completion_tokens": output_tokens,
                        },
                        "cost": {"currency": "USD", "value": cost},
                        "output": {"inline": {"text": output_text}, "truncated": False},
                        "error": error_info,
                    },
                )
            ])


class InstrumentedAnthropicClient:
    """Wraps an Anthropic client to auto-emit AgentOps spans."""

    def __init__(self, client: Any):
        self._client = client
        self.messages = _InstrumentedMessages(client.messages)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._client, name)


def instrument_anthropic(client: Any) -> "InstrumentedAnthropicClient":
    """Wrap an Anthropic client instance to auto-trace all messages.create calls."""
    return InstrumentedAnthropicClient(client)
