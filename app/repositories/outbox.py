"""Модуль репозитория для работы с outbox таблицей."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select

from app.database.models import OutboxModel
from app.enums import OutboxStatus
from app.repositories.base import BaseRepository

__all__ = ['OutboxRepository']


class OutboxRepository(BaseRepository[OutboxModel]):
    """Репозиторий для записи и получения событий из outbox."""

    async def create(self, outbox: OutboxModel) -> OutboxModel:
        """Создаёт новую запись в outbox.

        Args:
            outbox: Модель outbox для сохранения.

        Returns:
            OutboxModel: Сохранённая модель.
        """
        return await self._save(outbox)

    async def get_pending(self, limit: int = 100) -> list[OutboxModel]:
        """Возвращает необработанные события из outbox.

        Args:
            limit: Максимальное количество записей.

        Returns:
            list[OutboxModel]: Список необработанных событий.
        """
        query = (
            select(OutboxModel)
            .where(OutboxModel.status == OutboxStatus.PENDING)
            .order_by(OutboxModel.created_at)
            .limit(limit)
        )
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def mark_processed(self, outbox_id: uuid.UUID) -> None:
        """Помечает событие как обработанное.

        Args:
            outbox_id: Идентификатор события.
        """
        outbox = await self._session.get(OutboxModel, outbox_id)
        if outbox:
            outbox.status = OutboxStatus.PROCESSED
            outbox.processed_at = datetime.now(UTC)
            await self._session.flush()

    async def mark_failed(self, outbox_id: uuid.UUID) -> None:
        """Помечает событие как проваленное и увеличивает счётчик попыток.

        Args:
            outbox_id: Идентификатор события.
        """
        outbox = await self._session.get(OutboxModel, outbox_id)
        if outbox:
            outbox.status = OutboxStatus.FAILED
            outbox.attempts += 1
            await self._session.flush()
