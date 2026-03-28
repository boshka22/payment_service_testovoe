"""Модуль FastAPI приложения платёжного сервиса."""

import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.v1.payments import router as payments_router
from app.exceptions.payment import PaymentNotFoundError, WebhookDeliveryError
from app.middleware.auth import APIKeyMiddleware
from app.workers.outbox_worker import OutboxWorker

__all__ = ['app']

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Управляет жизненным циклом приложения.

    Запускает OutboxWorker при старте.
    Останавливает воркер при завершении.

    Args:
        _app: Экземпляр FastAPI приложения (не используется напрямую).

    Yields:
        None: Передаёт управление приложению.
    """
    worker = OutboxWorker()
    task = asyncio.create_task(worker.start())
    logger.info('Payment service started')

    yield

    worker.stop()
    task.cancel()
    logger.info('Payment service stopped')


app = FastAPI(
    title='Payment Service API',
    description='Асинхронный сервис процессинга платежей',
    version='1.0.0',
    lifespan=lifespan,
    openapi_tags=[
        {'name': 'payments', 'description': 'Операции с платежами'},
        {'name': 'system', 'description': 'Системные эндпоинты'},
    ],
)

app.add_middleware(APIKeyMiddleware)
app.include_router(payments_router, prefix='/api/v1')


def custom_openapi() -> dict:
    """Генерирует кастомную OpenAPI схему с поддержкой X-API-Key.

    Returns:
        dict: OpenAPI схема с SecurityScheme для X-API-Key.
    """
    if app.openapi_schema:
        return app.openapi_schema

    from fastapi.openapi.utils import get_openapi

    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    schema['components']['securitySchemes'] = {
        'X-API-Key': {
            'type': 'apiKey',
            'in': 'header',
            'name': 'X-API-Key',
        },
    }

    for path in schema['paths'].values():
        for method in path.values():
            method['security'] = [{'X-API-Key': []}]

    app.openapi_schema = schema
    return schema


app.openapi = custom_openapi  # type: ignore[method-assign]


@app.exception_handler(PaymentNotFoundError)
async def payment_not_found_handler(
    _request: Request,
    exc: PaymentNotFoundError,
) -> JSONResponse:
    """Обрабатывает исключение PaymentNotFoundError.

    Args:
        _request: Входящий запрос (не используется).
        exc: Исключение платёж не найден.

    Returns:
        JSONResponse: Ответ с кодом 404.
    """
    return JSONResponse(
        status_code=404,
        content={'detail': str(exc)},
    )


@app.exception_handler(WebhookDeliveryError)
async def webhook_delivery_handler(
    _request: Request,
    exc: WebhookDeliveryError,
) -> JSONResponse:
    """Обрабатывает исключение WebhookDeliveryError.

    Args:
        _request: Входящий запрос (не используется).
        exc: Исключение ошибки доставки webhook.

    Returns:
        JSONResponse: Ответ с кодом 502.
    """
    return JSONResponse(
        status_code=502,
        content={'detail': str(exc)},
    )


@app.exception_handler(Exception)
async def global_exception_handler(
    _request: Request,
    exc: Exception,
) -> JSONResponse:
    """Глобальный обработчик непредвиденных исключений.

    Args:
        _request: Входящий запрос (не используется).
        exc: Непредвиденное исключение.

    Returns:
        JSONResponse: Ответ с кодом 500.
    """
    logger.error(f'Unhandled exception: {exc}')
    return JSONResponse(
        status_code=500,
        content={'detail': 'Internal server error.'},
    )


@app.get('/health', tags=['system'])
async def health() -> dict:
    """Проверяет работоспособность сервиса.

    Returns:
        dict: Статус сервиса.
    """
    return {'status': 'ok', 'service': 'Payment Service'}


if __name__ == '__main__':
    uvicorn.run('app.main:app', host='0.0.0.0', port=8000, reload=True)
