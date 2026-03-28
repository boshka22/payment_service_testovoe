"""Юнит тесты для сервиса платежей."""

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.exceptions.payment import PaymentNotFoundError
from app.services.payment import PaymentService

__all__: list[str] = []


@pytest.fixture
def mock_session() -> AsyncMock:
    """Возвращает мок сессии БД.

    Returns:
        AsyncMock: Мок AsyncSession.
    """
    return AsyncMock()


@pytest.fixture
def payment_service(mock_session: AsyncMock) -> PaymentService:
    """Возвращает экземпляр PaymentService с мок сессией.

    Args:
        mock_session: Мок сессии БД.

    Returns:
        PaymentService: Экземпляр сервиса.
    """
    return PaymentService(session=mock_session)


@pytest.mark.asyncio
async def test_get_by_id_not_found(payment_service: PaymentService) -> None:
    """Проверяет что PaymentNotFoundError выбрасывается если платёж не найден."""
    payment_id = uuid.uuid4()

    with patch.object(
        payment_service._payment_repo,
        'get_by_id',
        new=AsyncMock(return_value=None),
    ):
        with pytest.raises(PaymentNotFoundError) as exc:
            await payment_service.get_by_id(payment_id=payment_id)

    assert exc.value.payment_id == payment_id


@pytest.mark.asyncio
async def test_create_returns_existing_on_duplicate(
    payment_service: PaymentService,
) -> None:
    """Проверяет что при дубликате idempotency_key возвращается существующий платёж."""
    existing_payment = MagicMock()
    existing_payment.id_ = uuid.uuid4()

    request = MagicMock()
    request.amount = Decimal('100.00')
    request.currency = 'RUB'
    request.description = 'Test'
    request.metadata = {}
    request.webhook_url = 'https://example.com/webhook'

    with patch.object(
        payment_service._payment_repo,
        'get_by_idempotency_key',
        new=AsyncMock(return_value=existing_payment),
    ):
        result = await payment_service.create(
            data=request,
            idempotency_key='existing-key',
        )

    assert result == existing_payment
