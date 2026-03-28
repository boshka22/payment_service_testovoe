"""Модуль эндпоинтов для работы с платежами."""

import uuid

from fastapi import APIRouter, Depends, Header, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.schemas.v1.payment import (
    PaymentCreateRequest,
    PaymentCreateResponse,
    PaymentDetailResponse,
)
from app.services.payment import PaymentService

__all__ = ['router']

router = APIRouter(prefix='/payments', tags=['payments'])


def get_payment_service(
    session: AsyncSession = Depends(get_session),
) -> PaymentService:
    """Возвращает экземпляр PaymentService с сессией БД.

    Args:
        session: Асинхронная сессия SQLAlchemy из dependency injection.

    Returns:
        PaymentService: Экземпляр сервиса платежей.
    """
    return PaymentService(session=session)


@router.post(
    path='',
    summary='Создание платежа',
    description='Создаёт новый платёж и публикует событие в очередь.',
    response_model=PaymentCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        202: {'description': 'Платёж принят в обработку'},
        400: {'description': 'Некорректные данные'},
        401: {'description': 'Неверный API ключ'},
    },
)
async def create_payment(
    data: PaymentCreateRequest,
    idempotency_key: str = Header(alias='Idempotency-Key'),
    service: PaymentService = Depends(get_payment_service),
) -> PaymentCreateResponse:
    """Создаёт новый платёж.

    Если платёж с таким Idempotency-Key уже существует — возвращает его (200).

    Args:
        data: Данные для создания платежа.
        idempotency_key: Уникальный ключ для защиты от дублей.
        service: Экземпляр PaymentService из dependency injection.

    Returns:
        PaymentCreateResponse: Данные созданного платежа.
    """
    payment = await service.create(data=data, idempotency_key=idempotency_key)
    return PaymentCreateResponse(
        payment_id=payment.id_,
        status=payment.status,
        created_at=payment.created_at,
    )


@router.get(
    path='/{payment_id}',
    summary='Получение информации о платеже',
    description='Возвращает детальную информацию о платеже по ID.',
    response_model=PaymentDetailResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {'description': 'Детальная информация о платеже'},
        401: {'description': 'Неверный API ключ'},
        404: {'description': 'Платёж не найден'},
    },
)
async def get_payment(
    payment_id: uuid.UUID = Path(description='UUID платежа'),
    service: PaymentService = Depends(get_payment_service),
) -> PaymentDetailResponse:
    """Возвращает детальную информацию о платеже.

    Args:
        payment_id: Уникальный идентификатор платежа.
        service: Экземпляр PaymentService из dependency injection.

    Returns:
        PaymentDetailResponse: Детальная информация о платеже.
    """
    payment = await service.get_by_id(payment_id=payment_id)
    return PaymentDetailResponse(
        payment_id=payment.id_,
        amount=payment.amount,
        currency=payment.currency,
        description=payment.description,
        metadata=payment.metadata_,
        status=payment.status,
        webhook_url=payment.webhook_url,
        created_at=payment.created_at,
        processed_at=payment.processed_at,
    )
