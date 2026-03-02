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


__all__ = ["init", "track", "flush", "instrument_openai", "instrument_anthropic"]
