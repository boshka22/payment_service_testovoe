"""Модуль репозитория для работы с outbox таблицей."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select

from app.database.models import OutboxModel
from app.enums import OutboxStatus
from app.repositories.base import BaseRepository

__all__ = ['OutboxRepository']

MAX_ATTEMPTS = 3


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

        Возвращает PENDING события и FAILED события с attempts < MAX_ATTEMPTS.
        Это гарантирует что временно упавшие события будут повторно обработаны.

        Args:
            limit: Максимальное количество записей.

        Returns:
            list[OutboxModel]: Список необработанных событий.
        """
        query = (
            select(OutboxModel)
            .where(
                OutboxModel.status.in_([OutboxStatus.PENDING, OutboxStatus.FAILED]),
                OutboxModel.attempts < MAX_ATTEMPTS,
            )
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

        Если attempts >= MAX_ATTEMPTS событие остаётся FAILED навсегда
        и больше не будет обработано через get_pending.

        Args:
            outbox_id: Идентификатор события.
        """
        outbox = await self._session.get(OutboxModel, outbox_id)
        if outbox:
            outbox.attempts += 1
            outbox.status = OutboxStatus.FAILED
            await self._session.flush()
