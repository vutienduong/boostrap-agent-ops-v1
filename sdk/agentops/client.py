import atexit
import threading
from datetime import datetime, timezone

from ulid import ULID

from agentops.transport import Transport

FLUSH_INTERVAL = 2.0   # seconds
FLUSH_BATCH_SIZE = 50  # flush when buffer reaches this size


class AgentOpsClient:
    def __init__(self, api_key: str, endpoint: str, project_id: str | None = None):
        self.api_key = api_key
        self.project_id = project_id or "default"
        self.transport = Transport(endpoint=endpoint, api_key=api_key)

        self._buffer: list[dict] = []
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._flush_thread = threading.Thread(target=self._flush_loop, daemon=True)
        self._flush_thread.start()
        atexit.register(self.flush)

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
        """Add events to buffer; flush immediately if batch size exceeded."""
        with self._lock:
            self._buffer.extend(events)
            should_flush = len(self._buffer) >= FLUSH_BATCH_SIZE

        if should_flush:
            self._do_flush()

    def flush(self) -> None:
        """Force-flush all buffered events to the server."""
        self._do_flush()

    def _do_flush(self) -> None:
        with self._lock:
            if not self._buffer:
                return
            batch = self._buffer[:]
            self._buffer.clear()

        try:
            self.transport.send(batch)
        except Exception:
            pass  # fail silently — never break the user's app

    def _flush_loop(self) -> None:
        while not self._stop_event.wait(timeout=FLUSH_INTERVAL):
            self._do_flush()

    def shutdown(self) -> None:
        self._stop_event.set()
        self._flush_thread.join(timeout=5.0)
        self._do_flush()
