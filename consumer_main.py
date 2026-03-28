"""Точка входа для consumer контейнера."""

import asyncio
import logging

from app.consumer.payment_consumer import broker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main() -> None:
    """Запускает FastStream consumer."""
    logger.info('Starting payment consumer...')
    async with broker:
        await broker.start()
        logger.info('Consumer started, waiting for messages...')
        await asyncio.Future()


if __name__ == '__main__':
    asyncio.run(main())
