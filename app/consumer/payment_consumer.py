"""Модуль consumer для обработки платежей из RabbitMQ."""

import asyncio
import logging
import random
import uuid
from datetime import UTC, datetime

import httpx
from faststream.rabbit import ExchangeType, RabbitBroker, RabbitExchange, RabbitQueue

from app.core.config import settings
from app.core.database import async_session_maker
from app.enums import PaymentStatus
from app.exceptions.payment import WebhookDeliveryError
from app.repositories.payment import PaymentRepository

__all__ = ['broker']

logger = logging.getLogger(__name__)

broker = RabbitBroker(settings.rabbitmq_url)

dead_exchange = RabbitExchange(
    'payments.dead',
    durable=True,
    type=ExchangeType.DIRECT,
)

dead_queue = RabbitQueue(
    'payments.dead',
    durable=True,
    routing_key='payments.dead',
)


payments_exchange = RabbitExchange('payments', durable=True)
payments_queue = RabbitQueue(
    'payments.new',
    durable=True,
    arguments={
        'x-dead-letter-exchange': 'payments.dead',
        'x-dead-letter-routing-key': 'payments.dead',
    },
)


@broker.subscriber(payments_queue, payments_exchange)
async def process_payment(payload: dict) -> None:
    """Обрабатывает платёж из очереди.

    Эмулирует обработку (2-5 сек, 90% успех / 10% ошибка),
    обновляет статус в БД и отправляет webhook с retry логикой.

    Args:
        payload: Данные платежа из очереди.
    """
    payment_id = uuid.UUID(payload['payment_id'])
    webhook_url = payload['webhook_url']

    logger.info(f'Processing payment {payment_id}')

    await asyncio.sleep(random.uniform(2, 5))
    is_success = random.random() < 0.9
    status = PaymentStatus.SUCCEEDED if is_success else PaymentStatus.FAILED

    # TODO: для продакшена статус обновлять только после успешной доставки webhook
    # или вынести webhook доставку в отдельную очередь чтобы избежать
    # повторной обработки платежа при NACK после неудачного webhook
    async with async_session_maker() as session:
        repo = PaymentRepository(session=session)
        await repo.update_status(
            payment_id=payment_id, status=status, processed_at=datetime.now(UTC)
        )
        await session.commit()

    logger.info(f'Payment {payment_id} status updated to {status}')

    await _send_webhook_with_retry(
        url=webhook_url,
        payload={
            'payment_id': str(payment_id),
            'status': str(status),
        },
    )


async def _send_webhook_with_retry(url: str, payload: dict) -> None:
    """Отправляет webhook уведомление с экспоненциальным retry.

    Args:
        url: URL для отправки webhook.
        payload: Данные для отправки.

    Raises:
        WebhookDeliveryError: Если все попытки исчерпаны.
    """
    async with httpx.AsyncClient() as client:
        for attempt in range(settings.webhook_max_attempts):
            try:
                response = await client.post(
                    url,
                    json=payload,
                    timeout=settings.webhook_timeout,
                )
                if response.is_success:
                    logger.info(f'Webhook delivered to {url} on attempt {attempt + 1}')
                    return
                logger.warning(
                    f'Webhook attempt {attempt + 1} failed: status {response.status_code}',
                )
            except (httpx.RequestError, httpx.TimeoutException) as e:
                logger.warning(f'Webhook attempt {attempt + 1} error: {e}')

            if attempt < settings.webhook_max_attempts - 1:
                delay = 2 ** (attempt + 1)
                logger.info(f'Retrying webhook in {delay}s...')
                await asyncio.sleep(delay)

    raise WebhookDeliveryError(url=url, attempts=settings.webhook_max_attempts)
