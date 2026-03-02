import hashlib

from sqlalchemy import select

from app.core.db import async_session
from app.models.tables import ApiKey, Project

DEFAULT_PROJECT_ID = "01JDEFAULTPROJECT000000"
DEV_API_KEY = "dev_agentops_key_local"
DEV_KEY_ID = "01JDEVAPIKEY000000000000"


def _hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


async def seed_default_project() -> None:
    async with async_session() as session:
        # Seed project
        result = await session.execute(
            select(Project).where(Project.id == DEFAULT_PROJECT_ID)
        )
        if result.scalar_one_or_none() is None:
            session.add(Project(id=DEFAULT_PROJECT_ID, name="Default Project"))

        # Seed dev API key
        result = await session.execute(
            select(ApiKey).where(ApiKey.id == DEV_KEY_ID)
        )
        if result.scalar_one_or_none() is None:
            session.add(
                ApiKey(
                    id=DEV_KEY_ID,
                    project_id=DEFAULT_PROJECT_ID,
                    key_hash=_hash_key(DEV_API_KEY),
                    name="dev",
                )
            )

        await session.commit()
