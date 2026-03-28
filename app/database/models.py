"""Модуль моделей базы данных."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.enums import Currency, OutboxStatus, PaymentStatus

__all__ = ['PaymentModel', 'OutboxModel']


class PaymentModel(Base):
    """Модель таблицы платежей.

    Attributes:
        id_: Уникальный идентификатор платежа (UUID).
        idempotency_key: Ключ идемпотентности для защиты от дублей.
        amount: Сумма платежа.
        currency: Валюта платежа.
        description: Описание платежа.
        metadata_: Дополнительные метаданные в JSON.
        status: Статус платежа.
        webhook_url: URL для уведомления о результате.
        created_at: Дата и время создания.
        processed_at: Дата и время обработки.
    """

    __tablename__ = 'payments'

    id_: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    idempotency_key: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=18, scale=2),
        nullable=False,
    )
    currency: Mapped[Currency] = mapped_column(
        SAEnum(Currency, name='currency_enum'),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    status: Mapped[PaymentStatus] = mapped_column(
        SAEnum(PaymentStatus, name='payment_status_enum'),
        nullable=False,
        default=PaymentStatus.PENDING,
    )
    webhook_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    outbox: Mapped[list['OutboxModel']] = relationship(
        'OutboxModel',
        back_populates='payment',
    )


class OutboxModel(Base):
    """Модель таблицы outbox для гарантированной доставки событий.

    Attributes:
        id_: Уникальный идентификатор записи.
        payment_id: Идентификатор связанного платежа.
        event_type: Тип события.
        payload: Данные события в JSON.
        status: Статус обработки.
        attempts: Количество попыток публикации.
        created_at: Дата и время создания.
        processed_at: Дата и время обработки.
    """

    __tablename__ = 'outbox'

    id_: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    payment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('payments.id_'),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[OutboxStatus] = mapped_column(
        SAEnum(OutboxStatus, name='outbox_status_enum'),
        nullable=False,
        default=OutboxStatus.PENDING,
    )
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    payment: Mapped['PaymentModel'] = relationship(
        'PaymentModel',
        back_populates='outbox',
    )
