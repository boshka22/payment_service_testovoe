"""Модуль middleware для аутентификации по API ключу."""

from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings

__all__ = ['APIKeyMiddleware']

EXCLUDED_PATHS = {'/health', '/docs', '/openapi.json', '/redoc'}


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Middleware для проверки статического API ключа в заголовке X-API-Key.

    Пропускает запросы к служебным эндпоинтам без проверки.
    """

    async def dispatch(self, request: Request, call_next: Any) -> Any:
        """Проверяет наличие и корректность API ключа.

        Args:
            request: Входящий HTTP запрос.
            call_next: Следующий обработчик в цепочке middleware.

        Returns:
            Response: HTTP ответ — либо 401 либо результат следующего обработчика.
        """
        if request.url.path in EXCLUDED_PATHS:
            return await call_next(request)

        api_key = request.headers.get('X-API-Key')
        if api_key != settings.api_key:
            return JSONResponse(
                status_code=401,
                content={'detail': 'Invalid or missing API key.'},
            )

        return await call_next(request)
