"""
Arq background worker.

Run with:
    arq app.workers.worker.WorkerSettings
"""
from arq import ArqRedis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import async_session
from app.services.normalizer import normalize_event


async def normalize_run_events(ctx: dict, run_id: str) -> None:
    """Normalize all raw_events for a given run_id into runs/spans tables."""
    from sqlalchemy import select
    from app.models.tables import RawEvent

    async with async_session() as session:
        result = await session.execute(
            select(RawEvent)
            .where(RawEvent.run_id == run_id)
            .order_by(RawEvent.received_at)
        )
        raw_events = result.scalars().all()

        for raw in raw_events:
            event_dict = {
                "event_type": raw.event_type,
                "context": {
                    "run_id": raw.run_id,
                    "span_id": raw.span_id,
                    "trace_id": raw.trace_id,
                },
                "project": {"id": raw.project_id},
                "payload": raw.payload,
                "timestamp": raw.received_at.isoformat(),
            }
            try:
                await normalize_event(session, event_dict)
            except Exception:
                pass


class WorkerSettings:
    functions = [normalize_run_events]
    redis_settings_from_url = settings.redis_url
    max_jobs = 10
    job_timeout = 30
