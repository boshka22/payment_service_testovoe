"""Модуль Pydantic схем для эндпоинтов платёжного сервиса."""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.enums import Currency

__all__ = [
    'PaymentCreateRequest',
    'PaymentCreateResponse',
    'PaymentDetailResponse',
]


class PaymentCreateRequest(BaseModel):
    """Схема запроса на создание платежа.

    Attributes:
        amount: Сумма платежа. Должна быть положительной.
        currency: Валюта платежа (RUB, USD, EUR).
        description: Описание платежа.
        metadata: Дополнительные метаданные.
        webhook_url: URL для уведомления о результате.
    """

    amount: Decimal = Field(gt=0, decimal_places=2, description='Сумма платежа')
    currency: Currency = Field(description='Валюта: RUB, USD, EUR')
    description: str = Field(min_length=1, max_length=500)
    metadata: dict = Field(default_factory=dict)
    webhook_url: HttpUrl = Field(description='URL для webhook уведомления')


class PaymentCreateResponse(BaseModel):
    """Схема ответа на создание платежа (202 Accepted).

    Attributes:
        payment_id: Уникальный идентификатор созданного платежа.
        status: Текущий статус платежа.
        created_at: Дата и время создания.
    """

    payment_id: uuid.UUID
    status: str
    created_at: datetime


class PaymentDetailResponse(BaseModel):
    """Схема детальной информации о платеже.

    Attributes:
        payment_id: Уникальный идентификатор платежа.
        amount: Сумма платежа.
        currency: Валюта платежа.
        description: Описание платежа.
        metadata: Дополнительные метаданные.
        status: Текущий статус платежа.
        webhook_url: URL для webhook уведомления.
        created_at: Дата и время создания.
        processed_at: Дата и время обработки.
    """

    model_config = ConfigDict(from_attributes=True)

    payment_id: uuid.UUID
    amount: Decimal
    currency: str
    description: str
    metadata: dict
    status: str
    webhook_url: str
    created_at: datetime
    processed_at: datetime | None = None
