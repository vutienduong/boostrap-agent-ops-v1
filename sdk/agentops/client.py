from datetime import datetime, timezone

from ulid import ULID

from agentops.transport import Transport


class AgentOpsClient:
    def __init__(self, api_key: str, endpoint: str, project_id: str | None = None):
        self.api_key = api_key
        self.project_id = project_id or "default"
        self.transport = Transport(endpoint=endpoint, api_key=api_key)

    def _make_event(
        self, event_type: str, run_id: str, span_id: str | None, payload: dict
    ) -> dict:
        return {
            "schema_version": "1.0",
            "event_id": str(ULID()),
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "project": {"id": self.project_id},
            "sdk": {"name": "agentops-python", "version": "0.1.0"},
            "context": {
                "trace_id": run_id,
                "run_id": run_id,
                "span_id": span_id,
            },
            "payload": payload,
        }

    def send_events(self, events: list[dict]) -> None:
        try:
            self.transport.send(events)
        except Exception:
            pass  # fail silently — never break the user's app
