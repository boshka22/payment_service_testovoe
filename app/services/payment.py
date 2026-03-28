"""Модуль сервисного слоя для работы с платежами."""

import uuid
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import OutboxModel, PaymentModel
from app.enums import OutboxStatus, PaymentStatus
from app.exceptions.payment import PaymentNotFoundError
from app.repositories.outbox import OutboxRepository
from app.repositories.payment import PaymentRepository
from app.schemas.v1.payment import PaymentCreateRequest

__all__ = ['PaymentService']


class PaymentService:
    """Сервис для создания и получения платежей."""

    def __init__(self, session: AsyncSession) -> None:
        """Инициализирует сервис с сессией базы данных.

        Args:
            session: Асинхронная сессия SQLAlchemy.
        """
        self._session = session
        self._payment_repo = PaymentRepository(session=session)
        self._outbox_repo = OutboxRepository(session=session)

    async def create(
        self,
        data: PaymentCreateRequest,
        idempotency_key: str,
    ) -> PaymentModel:
        """Создаёт новый платёж или возвращает существующий при дубликате.

        Args:
            data: Данные для создания платежа.
            idempotency_key: Ключ идемпотентности из заголовка.

        Returns:
            PaymentModel: Созданный или существующий платёж.
        """
        existing = await self._payment_repo.get_by_idempotency_key(idempotency_key)
        if existing:
            return existing

        try:
            payment = PaymentModel(
                idempotency_key=idempotency_key,
                amount=Decimal(str(data.amount)),
                currency=data.currency,
                description=data.description,
                metadata_=data.metadata,
                status=PaymentStatus.PENDING,
                webhook_url=str(data.webhook_url),
            )
            payment = await self._payment_repo.create(payment)

            outbox = OutboxModel(
                payment_id=payment.id_,
                event_type='payment.created',
                payload={
                    'payment_id': str(payment.id_),
                    'amount': str(payment.amount),
                    'currency': payment.currency,
                    'description': payment.description,
                    'webhook_url': payment.webhook_url,
                },
                status=OutboxStatus.PENDING,
                attempts=0,
            )
            await self._outbox_repo.create(outbox)
            await self._session.commit()
            return payment

        except IntegrityError:
            await self._session.rollback()
            existing = await self._payment_repo.get_by_idempotency_key(idempotency_key)
            if existing:
                return existing
            raise

    async def get_by_id(self, payment_id: uuid.UUID) -> PaymentModel:
        """Возвращает платёж по идентификатору.

        Args:
            payment_id: Уникальный идентификатор платежа.

        Raises:
            PaymentNotFoundError: Если платёж не найден.

        Returns:
            PaymentModel: Найденный платёж.
        """
        payment = await self._payment_repo.get_by_id(payment_id)
        if payment is None:
            raise PaymentNotFoundError(payment_id=payment_id)
        return payment
