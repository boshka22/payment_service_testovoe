"""Модуль базового репозитория."""

from typing import Generic, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

__all__ = ['BaseRepository']

ModelT = TypeVar('ModelT')


class BaseRepository(Generic[ModelT]):
    """Базовый репозиторий с общими операциями для всех моделей.

    Attributes:
        _session: Асинхронная сессия SQLAlchemy.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Инициализирует репозиторий с сессией базы данных.

        Args:
            session: Асинхронная сессия SQLAlchemy.
        """
        self._session = session

    async def _save(self, model: ModelT) -> ModelT:
        """Сохраняет модель в БД и обновляет её из БД.

        Args:
            model: Модель для сохранения.

        Returns:
            ModelT: Сохранённая и обновлённая модель.
        """
        self._session.add(model)  # type: ignore[arg-type]
        await self._session.flush()
        await self._session.refresh(model)  # type: ignore[arg-type]
        return model