from agentops.client import AgentOpsClient
from agentops.decorators import track
from agentops.instrumentors.openai import instrument_openai
from agentops.instrumentors.anthropic import instrument_anthropic

_client: AgentOpsClient | None = None


def init(
    api_key: str,
    endpoint: str = "http://localhost:8000",
    project: str | None = None,
) -> None:
    global _client
    _client = AgentOpsClient(api_key=api_key, endpoint=endpoint, project_id=project)


def flush() -> None:
    """Force flush all buffered events."""
    if _client is not None:
        _client.flush()


def prompt_version(key: str, version: str, content: str, meta: dict | None = None) -> None:
    """Register a prompt version with the server (fire-and-forget)."""
    if _client is None:
        return
    from agentops.decorators import current_run_id
    import threading

    def _send():
        try:
            import httpx
            httpx.post(
                f"{_client.transport.endpoint}/v1/prompts",
                params={"project_id": _client.project_id},
                json={"key": key, "version": version, "content": content, "meta": meta},
                headers={"X-AgentOps-Key": _client.api_key},
                timeout=5.0,
            )
        except Exception:
            pass

    threading.Thread(target=_send, daemon=True).start()


__all__ = ["init", "track", "flush", "instrument_openai", "instrument_anthropic", "prompt_version"]
