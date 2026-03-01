from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.db import get_db
from app.models.schemas import RunDetail, RunListResponse, RunSummary, SpanResponse
from app.models.tables import Run, Span

router = APIRouter(prefix="/v1", tags=["runs"])


@router.get("/runs", response_model=RunListResponse)
async def list_runs(
    project_id: str = Query(...),
    limit: int = Query(50, le=100),
    cursor: str | None = Query(None),
    session: AsyncSession = Depends(get_db),
):
    query = (
        select(Run)
        .where(Run.project_id == project_id)
        .order_by(Run.started_at.desc().nullslast(), Run.id.desc())
        .limit(limit + 1)
    )
    if cursor:
        query = query.where(Run.id < cursor)

    result = await session.execute(query)
    runs = list(result.scalars().all())

    next_cursor = None
    if len(runs) > limit:
        next_cursor = runs[limit].id
        runs = runs[:limit]

    return RunListResponse(
        runs=[
            RunSummary(
                id=r.id,
                project_id=r.project_id,
                name=r.name,
                status=r.status,
                started_at=r.started_at,
                ended_at=r.ended_at,
                duration_ms=r.duration_ms,
                total_prompt_tokens=r.total_prompt_tokens,
                total_completion_tokens=r.total_completion_tokens,
                total_cost_usd=r.total_cost_usd,
                tags=r.tags,
            )
            for r in runs
        ],
        cursor=next_cursor,
    )


@router.get("/runs/{run_id}", response_model=RunDetail)
async def get_run(
    run_id: str,
    session: AsyncSession = Depends(get_db),
):
    result = await session.execute(
        select(Run).options(selectinload(Run.spans)).where(Run.id == run_id)
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    return RunDetail(
        id=run.id,
        project_id=run.project_id,
        name=run.name,
        status=run.status,
        started_at=run.started_at,
        ended_at=run.ended_at,
        duration_ms=run.duration_ms,
        total_prompt_tokens=run.total_prompt_tokens,
        total_completion_tokens=run.total_completion_tokens,
        total_cost_usd=run.total_cost_usd,
        tags=run.tags,
        input_json=run.input_json,
        output_json=run.output_json,
        spans=[
            SpanResponse(
                id=s.id,
                run_id=s.run_id,
                parent_span_id=s.parent_span_id,
                type=s.type,
                name=s.name,
                started_at=s.started_at,
                ended_at=s.ended_at,
                duration_ms=s.duration_ms,
                status=s.status,
                model=s.model,
                tokens_prompt=s.tokens_prompt,
                tokens_completion=s.tokens_completion,
                cost_usd=s.cost_usd,
                input_json=s.input_json,
                output_json=s.output_json,
                error_json=s.error_json,
            )
            for s in sorted(run.spans, key=lambda s: s.started_at or s.id)
        ],
    )
