from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_api_key
from app.core.db import get_db
from app.models.schemas import CostByDay, CostByModel, CostMetricsResponse
from app.models.tables import ApiKey, Run, Span

router = APIRouter(prefix="/v1", tags=["metrics"])


@router.get("/metrics/cost", response_model=CostMetricsResponse)
async def get_cost_metrics(
    project_id: str = Query(...),
    from_date: str | None = Query(None, alias="from"),
    to_date: str | None = Query(None, alias="to"),
    session: AsyncSession = Depends(get_db),
    _api_key: ApiKey = Depends(require_api_key),
):
    # Base run filter
    run_filter = [Run.project_id == project_id]
    if from_date:
        run_filter.append(Run.started_at >= datetime.fromisoformat(from_date).replace(tzinfo=timezone.utc))
    if to_date:
        run_filter.append(Run.started_at <= datetime.fromisoformat(to_date).replace(tzinfo=timezone.utc))

    # Totals from runs table
    totals = await session.execute(
        select(
            func.coalesce(func.sum(Run.total_cost_usd), 0).label("total_cost"),
            func.coalesce(func.sum(Run.total_prompt_tokens), 0).label("total_prompt"),
            func.coalesce(func.sum(Run.total_completion_tokens), 0).label("total_completion"),
        ).where(*run_filter)
    )
    row = totals.one()
    total_cost = float(row.total_cost)
    total_prompt = int(row.total_prompt)
    total_completion = int(row.total_completion)

    # Cost by day
    day_rows = await session.execute(
        select(
            func.date(Run.started_at).label("day"),
            func.coalesce(func.sum(Run.total_cost_usd), 0).label("cost"),
            func.coalesce(func.sum(Run.total_prompt_tokens), 0).label("prompt_tokens"),
            func.coalesce(func.sum(Run.total_completion_tokens), 0).label("completion_tokens"),
            func.count(Run.id).label("run_count"),
        )
        .where(*run_filter)
        .group_by(func.date(Run.started_at))
        .order_by(func.date(Run.started_at))
    )
    by_day = [
        CostByDay(
            date=str(r.day),
            cost_usd=float(r.cost),
            prompt_tokens=int(r.prompt_tokens),
            completion_tokens=int(r.completion_tokens),
            run_count=int(r.run_count),
        )
        for r in day_rows
    ]

    # Cost by model — from spans
    span_filter = [
        Span.run_id.in_(
            select(Run.id).where(*run_filter)
        ),
        Span.model.isnot(None),
        Span.type == "llm",
    ]
    model_rows = await session.execute(
        select(
            Span.model,
            func.coalesce(func.sum(Span.cost_usd), 0).label("cost"),
            func.coalesce(func.sum(Span.tokens_prompt), 0).label("prompt_tokens"),
            func.coalesce(func.sum(Span.tokens_completion), 0).label("completion_tokens"),
            func.count(Span.id).label("span_count"),
        )
        .where(*span_filter)
        .group_by(Span.model)
        .order_by(func.sum(Span.cost_usd).desc())
    )
    by_model = [
        CostByModel(
            model=r.model,
            cost_usd=float(r.cost),
            prompt_tokens=int(r.prompt_tokens),
            completion_tokens=int(r.completion_tokens),
            span_count=int(r.span_count),
        )
        for r in model_rows
    ]

    return CostMetricsResponse(
        total_cost_usd=total_cost,
        total_prompt_tokens=total_prompt,
        total_completion_tokens=total_completion,
        by_day=by_day,
        by_model=by_model,
    )
