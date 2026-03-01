from sqlalchemy import select

from app.core.db import async_session
from app.models.tables import Project

DEFAULT_PROJECT_ID = "01JDEFAULTPROJECT000000"


async def seed_default_project() -> None:
    async with async_session() as session:
        result = await session.execute(
            select(Project).where(Project.id == DEFAULT_PROJECT_ID)
        )
        if result.scalar_one_or_none() is None:
            session.add(Project(id=DEFAULT_PROJECT_ID, name="Default Project"))
            await session.commit()
