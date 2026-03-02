import hashlib
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.db import Base, get_db
from app.main import app
from app.models.tables import ApiKey, Project

TEST_DB_URL = "postgresql+asyncpg://agentops:agentops@localhost:5432/agentops_test"

DEV_API_KEY = "dev_agentops_key_local"
DEV_KEY_HASH = hashlib.sha256(DEV_API_KEY.encode()).hexdigest()
DEV_KEY_ID = "01JDEVAPIKEY000000000000"
TEST_PROJECT_ID = "proj_test"


@pytest.fixture(autouse=True)
async def setup_db():
    engine = create_async_engine(TEST_DB_URL)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed the test project required by FK constraint
    async with session_factory() as session:
        project = Project(id=TEST_PROJECT_ID, name="Test Project")
        session.add(project)
        await session.flush()
        # Seed dev API key (project must exist first due to FK)
        api_key = ApiKey(
            id=DEV_KEY_ID,
            project_id=TEST_PROJECT_ID,
            key_hash=DEV_KEY_HASH,
            name="dev",
        )
        session.add(api_key)
        await session.commit()

    yield session_factory

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture(autouse=True)
def mock_redis():
    """Mock Redis/arq pool so tests fall back to inline normalization."""
    async def _raise(*args, **kwargs):
        raise ConnectionError("Redis not available in tests")

    with patch("app.api.ingest.get_arq_pool", side_effect=_raise):
        yield


@pytest.fixture
async def client(setup_db):
    session_factory = setup_db

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-AgentOps-Key": DEV_API_KEY},
    ) as c:
        yield c
    app.dependency_overrides.clear()
