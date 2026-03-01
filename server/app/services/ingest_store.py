from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from ulid import ULID

from app.models.tables import RawEvent


async def store_raw_events(
    session: AsyncSession, events: list[dict]
) -> tuple[int, int, list[str]]:
    accepted = 0
    rejected = 0
    errors: list[str] = []

    for event in events:
        try:
            raw = RawEvent(
                id=str(ULID()),
                project_id=event["project"]["id"],
                received_at=datetime.now(timezone.utc),
                event_type=event["event_type"],
                run_id=event["context"]["run_id"],
                span_id=event["context"].get("span_id"),
                trace_id=event["context"].get("trace_id"),
                payload=event.get("payload", {}),
                sdk_name=event.get("sdk", {}).get("name"),
                sdk_version=event.get("sdk", {}).get("version"),
            )
            session.add(raw)
            accepted += 1
        except Exception as e:
            rejected += 1
            errors.append(str(e))

    await session.commit()
    return accepted, rejected, errors
