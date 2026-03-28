"""Модуль воркера для публикации событий из outbox в RabbitMQ."""

import asyncio
import json
import logging
from typing import Any

from aio_pika import DeliveryMode, Message, connect_robust

from app.core.config import settings
from app.core.database import async_session_maker
from app.repositories.outbox import OutboxRepository

__all__ = ['OutboxWorker']

logger = logging.getLogger(__name__)


class OutboxWorker:
    """Воркер для опроса outbox таблицы и публикации событий в RabbitMQ.

    Работает как бесконечный цикл с интервалом poll_interval секунд.
    При успешной публикации помечает событие как processed.
    При ошибке — помечает как failed.
    """

    def __init__(self) -> None:
        self._running = False

    async def start(self) -> None:
        """Запускает бесконечный цикл опроса outbox."""
        self._running = True
        logger.info('OutboxWorker started')

        connection = await connect_robust(settings.rabbitmq_url)

        async with connection:
            channel = await connection.channel()
            exchange = await channel.declare_exchange(
                'payments',
                durable=True,
            )

            while self._running:
                try:
                    await self._process_pending(exchange)
                except Exception as e:
                    logger.error(f'OutboxWorker error: {e}')

                await asyncio.sleep(settings.outbox_poll_interval)

    async def _process_pending(self, exchange: Any) -> None:
        """Обрабатывает необработанные события из outbox.

        Args:
            exchange: RabbitMQ exchange для публикации.
        """
        async with async_session_maker() as session:
            repo = OutboxRepository(session=session)
            events = await repo.get_pending(limit=100)

            for event in events:
                try:
                    message = Message(
                        body=json.dumps(event.payload).encode(),
                        delivery_mode=DeliveryMode.PERSISTENT,
                        content_type='application/json',
                    )
                    await exchange.publish(
                        message,
                        routing_key='payments.new',
                    )
                    await repo.mark_processed(event.id_)
                    logger.info(f'Published event {event.id_} for payment {event.payment_id}')
                except Exception as e:
                    await repo.mark_failed(event.id_)
                    logger.error(f'Failed to publish event {event.id_}: {e}')

            await session.commit()

    def stop(self) -> None:
        """Останавливает воркер."""
        self._running = False
        logger.info('OutboxWorker stopped')
