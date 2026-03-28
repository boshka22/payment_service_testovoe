"""Модуль перечислений (enums) для платёжного сервиса."""

from enum import StrEnum

__all__ = [
    'PaymentStatus',
    'Currency',
    'OutboxStatus',
]


class PaymentStatus(StrEnum):
    """Статусы платежа."""

    PENDING = 'pending'
    SUCCEEDED = 'succeeded'
    FAILED = 'failed'


class Currency(StrEnum):
    """Поддерживаемые валюты."""

    RUB = 'RUB'
    USD = 'USD'
    EUR = 'EUR'


class OutboxStatus(StrEnum):
    """Статусы записи в outbox."""

    PENDING = 'pending'
    PROCESSED = 'processed'
    FAILED = 'failed'