from dateutil.parser import isoparse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tables import Run, Span


async def normalize_event(session: AsyncSession, event: dict) -> None:
    event_type = event["event_type"]
    ctx = event["context"]
    payload = event.get("payload", {})
    timestamp = event.get("timestamp")

    if event_type == "run_started":
        run = Run(
            id=ctx["run_id"],
            project_id=event["project"]["id"],
            name=payload.get("name"),
            status="running",
            started_at=timestamp,
            tags=payload.get("tags"),
            input_json=payload.get("input"),
        )
        session.add(run)

    elif event_type == "run_finished":
        result = await session.execute(select(Run).where(Run.id == ctx["run_id"]))
        run = result.scalar_one_or_none()
        if run:
            run.status = payload.get("status", "success")
            run.ended_at = timestamp
            timing = payload.get("timing", {})
            if timing.get("started_at") and timing.get("ended_at"):
                start = isoparse(timing["started_at"])
                end = isoparse(timing["ended_at"])
                run.duration_ms = int((end - start).total_seconds() * 1000)
            summary = payload.get("summary", {})
            run.total_prompt_tokens = summary.get("total_prompt_tokens", 0)
            run.total_completion_tokens = summary.get("total_completion_tokens", 0)
            run.total_cost_usd = summary.get("total_cost_usd", 0.0)
            run.output_json = payload.get("output")

    elif event_type == "span_started":
        attrs = payload.get("attributes", {})
        span = Span(
            id=ctx["span_id"],
            run_id=ctx["run_id"],
            parent_span_id=payload.get("parent_span_id"),
            type=payload.get("type", "custom"),
            name=payload.get("name", "unknown"),
            started_at=timestamp,
            status="running",
            model=attrs.get("model"),
            input_json=payload.get("input"),
        )
        session.add(span)

    elif event_type == "span_finished":
        result = await session.execute(select(Span).where(Span.id == ctx["span_id"]))
        span = result.scalar_one_or_none()
        if span:
            span.status = payload.get("status", "success")
            timing = payload.get("timing", {})
            if timing.get("started_at"):
                span.started_at = isoparse(timing["started_at"])
            if timing.get("ended_at"):
                span.ended_at = isoparse(timing["ended_at"])
            if timing.get("started_at") and timing.get("ended_at"):
                start = isoparse(timing["started_at"])
                end = isoparse(timing["ended_at"])
                span.duration_ms = int((end - start).total_seconds() * 1000)
            usage = payload.get("usage", {})
            span.tokens_prompt = usage.get("prompt_tokens", 0)
            span.tokens_completion = usage.get("completion_tokens", 0)
            cost = payload.get("cost", {})
            span.cost_usd = cost.get("value", 0.0)
            span.output_json = payload.get("output")
            span.error_json = payload.get("error")

    await session.commit()
