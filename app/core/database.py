"""Модуль подключения к базе данных."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

__all__ = ['Base', 'get_session']

engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_size=10,
    max_overflow=20,
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Базовый класс для всех моделей SQLAlchemy."""
    pass


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Создаёт и возвращает асинхронную сессию базы данных.

    Yields:
        AsyncSession: Асинхронная сессия для работы с БД.
    """
    async with async_session_maker() as session:
        yield session