from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ulid import ULID

from app.core.auth import require_api_key
from app.core.db import get_db
from app.models.schemas import (
    PromptVersionCreate,
    PromptVersionListResponse,
    PromptVersionResponse,
)
from app.models.tables import ApiKey, PromptVersion

router = APIRouter(prefix="/v1", tags=["prompts"])


@router.post("/prompts", response_model=PromptVersionResponse, status_code=201)
async def create_prompt_version(
    body: PromptVersionCreate,
    project_id: str = Query(...),
    session: AsyncSession = Depends(get_db),
    _api_key: ApiKey = Depends(require_api_key),
):
    pv = PromptVersion(
        id=str(ULID()),
        project_id=project_id,
        key=body.key,
        version=body.version,
        content=body.content,
        meta=body.meta,
    )
    session.add(pv)
    await session.commit()
    await session.refresh(pv)
    return PromptVersionResponse(
        id=pv.id,
        project_id=pv.project_id,
        key=pv.key,
        version=pv.version,
        content=pv.content,
        meta=pv.meta,
        created_at=pv.created_at,
    )


@router.get("/prompts", response_model=PromptVersionListResponse)
async def list_prompt_versions(
    project_id: str = Query(...),
    key: str | None = Query(None),
    session: AsyncSession = Depends(get_db),
    _api_key: ApiKey = Depends(require_api_key),
):
    query = (
        select(PromptVersion)
        .where(PromptVersion.project_id == project_id)
        .order_by(PromptVersion.key, PromptVersion.created_at.desc())
    )
    if key:
        query = query.where(PromptVersion.key == key)

    result = await session.execute(query)
    versions = result.scalars().all()

    return PromptVersionListResponse(
        versions=[
            PromptVersionResponse(
                id=pv.id,
                project_id=pv.project_id,
                key=pv.key,
                version=pv.version,
                content=pv.content,
                meta=pv.meta,
                created_at=pv.created_at,
            )
            for pv in versions
        ]
    )


@router.get("/prompts/{prompt_id}", response_model=PromptVersionResponse)
async def get_prompt_version(
    prompt_id: str,
    session: AsyncSession = Depends(get_db),
    _api_key: ApiKey = Depends(require_api_key),
):
    result = await session.execute(
        select(PromptVersion).where(PromptVersion.id == prompt_id)
    )
    pv = result.scalar_one_or_none()
    if not pv:
        raise HTTPException(status_code=404, detail="Prompt version not found")
    return PromptVersionResponse(
        id=pv.id,
        project_id=pv.project_id,
        key=pv.key,
        version=pv.version,
        content=pv.content,
        meta=pv.meta,
        created_at=pv.created_at,
    )
