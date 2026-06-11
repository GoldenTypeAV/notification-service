import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from testcontainers.postgres import PostgresContainer

import src.shared.database as database
from src.shared.models.base import Base
# Импорт моделей, чтобы их таблицы попали в Base.metadata.
from src.shared.models import notification, subscriber  # noqa: F401


@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:17", driver="asyncpg") as pg:
        yield pg


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def engine(postgres_container):
    eng = create_async_engine(postgres_container.get_connection_url())
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture(loop_scope="session")
async def session_factory(engine, monkeypatch):
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    # Воркер и API должны работать с тестовой БД.
    monkeypatch.setattr(database, "AsyncSessionLocal", maker)
    import src.worker.main as worker_main
    monkeypatch.setattr(worker_main, "AsyncSessionLocal", maker, raising=False)
    return maker


@pytest_asyncio.fixture(loop_scope="session")
async def db_session(session_factory):
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture(loop_scope="session")
async def client(db_session):
    from src.api.main import app
    from src.shared.database import get_db

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
