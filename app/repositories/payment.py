"""Модуль репозитория для работы с платежами."""

import uuid
from datetime import datetime

from sqlalchemy import select

from app.database.models import PaymentModel
from app.enums import PaymentStatus
from app.repositories.base import BaseRepository

__all__ = ['PaymentRepository']


class PaymentRepository(BaseRepository[PaymentModel]):
    """Репозиторий для записи и получения платежей из БД."""

    async def create(self, payment: PaymentModel) -> PaymentModel:
        """Создаёт новый платёж в базе данных.

        Args:
            payment: Модель платежа для сохранения.

        Returns:
            PaymentModel: Сохранённая модель платежа.
        """
        return await self._save(payment)

    async def get_by_id(self, payment_id: uuid.UUID) -> PaymentModel | None:
        """Возвращает платёж по идентификатору.

        Args:
            payment_id: Уникальный идентификатор платежа.

        Returns:
            PaymentModel | None: Найденная модель или None.
        """
        query = select(PaymentModel).where(PaymentModel.id_ == payment_id)
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_idempotency_key(self, key: str) -> PaymentModel | None:
        """Возвращает платёж по ключу идемпотентности.

        Args:
            key: Ключ идемпотентности.

        Returns:
            PaymentModel | None: Найденная модель или None.
        """
        query = select(PaymentModel).where(PaymentModel.idempotency_key == key)
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def update_status(
        self,
        payment_id: uuid.UUID,
        status: PaymentStatus,
        processed_at: datetime | None = None,
    ) -> PaymentModel | None:
        """Обновляет статус платежа.

        Args:
            payment_id: Идентификатор платежа.
            status: Новый статус из PaymentStatus enum.
            processed_at: Время обработки.

        Returns:
            PaymentModel | None: Обновлённая модель или None.
        """
        payment = await self.get_by_id(payment_id)
        if payment is None:
            return None

        payment.status = status
        if processed_at:
            payment.processed_at = processed_at

        await self._session.flush()
        await self._session.refresh(payment)
        return payment