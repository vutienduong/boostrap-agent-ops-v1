import asyncio

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ulid import ULID

from app.core.auth import require_api_key
from app.core.db import get_db, async_session
from app.models.schemas import ReplayCreate, ReplayResponse
from app.models.tables import ApiKey, Replay
from app.services.replay_runner import execute_replay

router = APIRouter(prefix="/v1", tags=["replays"])


async def _run_replay_bg(replay_id: str) -> None:
    """Run replay in a background task with its own DB session."""
    async with async_session() as session:
        await execute_replay(session, replay_id)


@router.post("/replays", response_model=ReplayResponse, status_code=201)
async def create_replay(
    body: ReplayCreate,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db),
    _api_key: ApiKey = Depends(require_api_key),
):
    replay = Replay(
        id=str(ULID()),
        source_run_id=body.source_run_id,
        mode=body.mode,
        overrides=body.overrides,
        status="queued",
    )
    session.add(replay)
    await session.commit()
    await session.refresh(replay)

    # Run in background (non-blocking)
    background_tasks.add_task(_run_replay_bg, replay.id)

    return ReplayResponse(
        id=replay.id,
        source_run_id=replay.source_run_id,
        new_run_id=replay.new_run_id,
        mode=replay.mode,
        overrides=replay.overrides,
        status=replay.status,
        created_at=replay.created_at,
    )


@router.get("/replays/{replay_id}", response_model=ReplayResponse)
async def get_replay(
    replay_id: str,
    session: AsyncSession = Depends(get_db),
    _api_key: ApiKey = Depends(require_api_key),
):
    result = await session.execute(select(Replay).where(Replay.id == replay_id))
    replay = result.scalar_one_or_none()
    if not replay:
        raise HTTPException(status_code=404, detail="Replay not found")

    return ReplayResponse(
        id=replay.id,
        source_run_id=replay.source_run_id,
        new_run_id=replay.new_run_id,
        mode=replay.mode,
        overrides=replay.overrides,
        status=replay.status,
        created_at=replay.created_at,
    )
