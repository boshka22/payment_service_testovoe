"""Точка входа для consumer контейнера."""

import asyncio
import logging

import aio_pika

from app.consumer.payment_consumer import broker
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def declare_dead_letter_infrastructure() -> None:
    """Объявляет DLQ exchange и очередь в RabbitMQ."""
    connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    async with connection:
        channel = await connection.channel()
        dead_exchange = await channel.declare_exchange(
            'payments.dead',
            aio_pika.ExchangeType.DIRECT,
            durable=True,
        )
        dead_queue = await channel.declare_queue(
            'payments.dead',
            durable=True,
        )
        await dead_queue.bind(dead_exchange, routing_key='payments.dead')
        logger.info('DLQ infrastructure declared')


async def main() -> None:
    """Запускает FastStream consumer."""
    logger.info('Starting payment consumer...')
    await declare_dead_letter_infrastructure()
    async with broker:
        await broker.start()
        logger.info('Consumer started, waiting for messages...')
        await asyncio.Future()


if __name__ == '__main__':
    asyncio.run(main())
