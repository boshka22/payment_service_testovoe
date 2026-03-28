"""Интеграционные тесты для эндпоинтов платёжного сервиса."""

import uuid

import pytest
from httpx import AsyncClient

__all__: list[str] = []


@pytest.mark.asyncio
async def test_health(client: AsyncClient) -> None:
    """Проверяет что health эндпоинт доступен без API ключа."""
    response = await client.get('/health')
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'


@pytest.mark.asyncio
async def test_create_payment_unauthorized() -> None:
    """Проверяет что запрос без API ключа возвращает 401."""
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url='http://test',
    ) as c:
        response = await c.post(
            '/api/v1/payments',
            json={
                'amount': '100.00',
                'currency': 'RUB',
                'description': 'Test payment',
                'webhook_url': 'https://example.com/webhook',
            },
            headers={'Idempotency-Key': str(uuid.uuid4())},
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_payment_not_found(client: AsyncClient) -> None:
    """Проверяет что несуществующий платёж возвращает 404."""
    response = await client.get(f'/api/v1/payments/{uuid.uuid4()}')
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_payment_success(client: AsyncClient) -> None:
    """Проверяет успешное создание платежа."""
    response = await client.post(
        '/api/v1/payments',
        json={
            'amount': '100.00',
            'currency': 'RUB',
            'description': 'Test payment',
            'webhook_url': 'https://example.com/webhook',
        },
        headers={'Idempotency-Key': str(uuid.uuid4())},
    )

    assert response.status_code == 202
    data = response.json()
    assert 'payment_id' in data
    assert data['status'] == 'pending'


@pytest.mark.asyncio
async def test_create_payment_idempotency(client: AsyncClient) -> None:
    """Проверяет что повторный запрос с тем же ключом возвращает тот же платёж."""
    idempotency_key = str(uuid.uuid4())
    payload = {
        'amount': '100.00',
        'currency': 'RUB',
        'description': 'Test payment',
        'webhook_url': 'https://example.com/webhook',
    }
    headers = {'Idempotency-Key': idempotency_key}

    response1 = await client.post('/api/v1/payments', json=payload, headers=headers)
    response2 = await client.post('/api/v1/payments', json=payload, headers=headers)

    assert response1.status_code == 202
    assert response2.status_code == 202
    assert response1.json()['payment_id'] == response2.json()['payment_id']


@pytest.mark.asyncio
async def test_create_payment_invalid_currency(client: AsyncClient) -> None:
    """Проверяет что неверная валюта возвращает 422."""
    response = await client.post(
        '/api/v1/payments',
        json={
            'amount': '100.00',
            'currency': 'INVALID',
            'description': 'Test',
            'webhook_url': 'https://example.com/webhook',
        },
        headers={'Idempotency-Key': str(uuid.uuid4())},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_payment_negative_amount(client: AsyncClient) -> None:
    """Проверяет что отрицательная сумма возвращает 422."""
    response = await client.post(
        '/api/v1/payments',
        json={
            'amount': '-100.00',
            'currency': 'RUB',
            'description': 'Test',
            'webhook_url': 'https://example.com/webhook',
        },
        headers={'Idempotency-Key': str(uuid.uuid4())},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_payment_missing_idempotency_key(client: AsyncClient) -> None:
    """Проверяет что отсутствие Idempotency-Key возвращает 422."""
    response = await client.post(
        '/api/v1/payments',
        json={
            'amount': '100.00',
            'currency': 'RUB',
            'description': 'Test',
            'webhook_url': 'https://example.com/webhook',
        },
    )
    assert response.status_code == 422
