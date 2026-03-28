"""Модуль кастомных исключений для платёжного сервиса."""

import uuid

__all__ = [
    'PaymentNotFoundError',
    'PaymentAlreadyExistsError',
    'WebhookDeliveryError',
]


class PaymentNotFoundError(Exception):
    """Исключение: платёж не найден.

    Attributes:
        payment_id: Идентификатор не найденного платежа.
    """

    def __init__(self, payment_id: uuid.UUID) -> None:
        self.payment_id = payment_id
        super().__init__(f'Payment {payment_id} not found.')


class PaymentAlreadyExistsError(Exception):
    """Исключение: платёж с таким idempotency_key уже существует.

    Attributes:
        idempotency_key: Ключ идемпотентности дубликата.
    """

    def __init__(self, idempotency_key: str) -> None:
        self.idempotency_key = idempotency_key
        super().__init__(f'Payment with idempotency key {idempotency_key} already exists.')


class WebhookDeliveryError(Exception):
    """Исключение: не удалось доставить webhook после всех попыток.

    Attributes:
        url: URL webhook который не ответил.
        attempts: Количество выполненных попыток.
    """

    def __init__(self, url: str, attempts: int) -> None:
        self.url = url
        self.attempts = attempts
        super().__init__(f'Failed to deliver webhook to {url} after {attempts} attempts.')