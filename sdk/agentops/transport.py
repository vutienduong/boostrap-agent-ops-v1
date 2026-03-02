import httpx


class Transport:
    def __init__(self, endpoint: str, api_key: str):
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key
        self._client = httpx.Client(timeout=10.0)

    def send(self, events: list[dict]) -> dict:
        resp = self._client.post(
            f"{self.endpoint}/v1/ingest",
            json=events,
            headers={"X-AgentOps-Key": self.api_key},
        )
        resp.raise_for_status()
        return resp.json()
