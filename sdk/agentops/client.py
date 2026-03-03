import atexit
import os
import sys
import threading
from datetime import datetime, timezone
from typing import Callable, Any

from ulid import ULID

from agentops.transport import Transport

FLUSH_INTERVAL = 2.0   # seconds
FLUSH_BATCH_SIZE = 50  # flush when buffer reaches this size
MAX_FIELD_BYTES = 32768  # 32KB max per string field


class AgentOpsClient:
    def __init__(self, api_key: str, endpoint: str, project_id: str | None = None, dev: bool = False):
        self.api_key = api_key
        self.project_id = project_id or "default"
        self.transport = Transport(endpoint=endpoint, api_key=api_key)
        # dev mode: True if dev=True passed, or AGENTOPS_ENV=dev
        self.dev = dev or os.environ.get("AGENTOPS_ENV", "").lower() == "dev"

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

    def _apply_redactor_and_truncation(self, event: dict) -> dict:
        """Apply redaction hook and 32KB truncation to event payload fields."""
        from agentops import _redactor

        payload = event.get("payload")
        if not isinstance(payload, dict):
            return event

        new_payload = dict(payload)
        meta: dict[str, Any] = {}

        for key, value in list(new_payload.items()):
            if key == "_meta":
                continue
            # Apply redactor on string values
            if isinstance(value, str) and _redactor is not None:
                try:
                    value = _redactor(key, value)
                except Exception:
                    pass
            # Apply truncation on string values
            if isinstance(value, str) and len(value) > MAX_FIELD_BYTES:
                original_size = len(value)
                value = value[:MAX_FIELD_BYTES]
                meta[key] = {"truncated": True, "original_size": original_size}
            new_payload[key] = value

        if meta:
            existing_meta = new_payload.get("_meta", {})
            new_payload["_meta"] = {**existing_meta, **meta}

        return {**event, "payload": new_payload}

    def send_events(self, events: list[dict]) -> None:
        """Add events to buffer; flush immediately if batch size exceeded."""
        processed = [self._apply_redactor_and_truncation(e) for e in events]
        with self._lock:
            self._buffer.extend(processed)
            should_flush = len(self._buffer) >= FLUSH_BATCH_SIZE

        if should_flush:
            self._do_flush()

    def flush(self, run_id: str | None = None) -> None:
        """Force-flush all buffered events to the server."""
        self._do_flush()
        if self.dev and run_id is not None:
            print(f"[AgentOps] Trace: http://localhost:3000/runs/{run_id}", file=sys.stderr)

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
