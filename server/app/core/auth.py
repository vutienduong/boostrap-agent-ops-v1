import hashlib
import secrets

from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.tables import ApiKey

API_KEY_HEADER = APIKeyHeader(name="X-AgentOps-Key", auto_error=False)

DEV_KEY = "dev_agentops_key_local"  # only for local dev / tests


def hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


async def require_api_key(
    api_key: str | None = Security(API_KEY_HEADER),
    session: AsyncSession = Depends(get_db),
) -> ApiKey:
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing X-AgentOps-Key header")

    key_hash = hash_key(api_key)
    result = await session.execute(
        select(ApiKey).where(
            ApiKey.key_hash == key_hash,
            ApiKey.revoked_at.is_(None),
        )
    )
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=401, detail="Invalid or revoked API key")

    return record
