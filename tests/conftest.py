"""Конфигурация pytest — фикстуры для всех тестов."""

import os
import sys
from collections.abc import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer

from app.core.database import Base, get_session
from app.main import app

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

API_KEY = 'secret-api-key'


@pytest.fixture(scope='session')
def postgres_container() -> Generator[PostgresContainer, None, None]:
    """Поднимает PostgreSQL контейнер на время тестовой сессии.

    Yields:
        PostgresContainer: Запущенный контейнер PostgreSQL.
    """
    with PostgresContainer('postgres:16-alpine') as postgres:
        yield postgres


@pytest.fixture(scope='session')
def test_database_url(postgres_container: PostgresContainer) -> str:
    """Возвращает URL тестовой базы данных.

    Args:
        postgres_container: Запущенный контейнер PostgreSQL.

    Returns:
        str: URL подключения к тестовой БД.
    """
    return postgres_container.get_connection_url().replace(
        'postgresql+psycopg2',
        'postgresql+asyncpg',
    )


@pytest_asyncio.fixture(scope='session')
async def setup_database(
    test_database_url: str,
) -> AsyncGenerator[None, None]:
    """Создаёт таблицы перед тестами и удаляет после.

    Args:
        test_database_url: URL подключения к тестовой БД.

    Yields:
        None: Передаёт управление тестам.
    """
    engine = create_async_engine(test_database_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def session(
    test_database_url: str,
    setup_database: None,
) -> AsyncGenerator[AsyncSession, None]:
    """Создаёт тестовую сессию БД с откатом после каждого теста.

    Args:
        test_database_url: URL подключения к тестовой БД.
        setup_database: Фикстура создания таблиц.

    Yields:
        AsyncSession: Тестовая сессия базы данных.
    """
    engine = create_async_engine(test_database_url, echo=False)
    session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_maker() as s:
        yield s
        await s.rollback()
    await engine.dispose()


@pytest_asyncio.fixture
async def client(session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Создаёт тестовый HTTP клиент с подменой сессии БД.

    Args:
        session: Тестовая сессия базы данных.

    Yields:
        AsyncClient: Тестовый HTTP клиент.
    """

    async def override_get_session() -> AsyncGenerator[AsyncSession, None]:
        yield session

    app.dependency_overrides[get_session] = override_get_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url='http://test',
        headers={'X-API-Key': API_KEY},
    ) as c:
        yield c

    app.dependency_overrides.clear()
