# Payment Service

Асинхронный микросервис для обработки платежей. Принимает запросы на оплату, обрабатывает их через эмуляцию платёжного шлюза и уведомляет клиента через webhook.

## Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI (API)                           │
│         POST /payments      GET /payments/{id}               │
└──────────────────────────┬──────────────────────────────────┘
                           │
                    PaymentService
                           │
          ┌────────────────┴────────────────┐
          │                                 │
    PaymentRepository                 OutboxRepository
          │                                 │
          └────────────────┬────────────────┘
                           │
                       PostgreSQL
                           │
                    OutboxWorker (polling)
                           │
                       RabbitMQ
                       payments exchange
                           │
                    ┌──────┴──────┐
                    │             │
               payments.new   payments.dead
               (Consumer)      (DLQ)
                    │
              обработка платежа
              обновление статуса
              webhook с retry
```

## Ключевые паттерны

**Outbox Pattern** — Payment и Outbox запись создаются в одной транзакции. Это гарантирует что событие не потеряется даже при падении сервиса между созданием платежа и публикацией в очередь.

**Idempotency Key** — повторный запрос с тем же ключом возвращает существующий платёж без создания дубликата.

**Dead Letter Queue** — сообщения которые не удалось обработать после 3 попыток автоматически уходят в `payments.dead` через механизм RabbitMQ `x-dead-letter-exchange`.

**Retry с экспоненциальной задержкой** — webhook отправляется до 3 раз с задержками 2 и 4 секунды.

## Стек

- **Python 3.11**
- **FastAPI** — REST API
- **FastStream + aio-pika** — RabbitMQ consumer
- **SQLAlchemy 2.0 async** — ORM
- **PostgreSQL 16** — основная БД
- **RabbitMQ 3.13** — брокер сообщений
- **Alembic** — миграции БД
- **httpx** — HTTP клиент для webhook
- **Docker + docker-compose** — контейнеризация
- **Ruff + mypy** — линтеры
- **pytest + testcontainers** — тесты

## Быстрый старт

### Требования

- Docker
- Docker Compose

### Установка

```bash
git clone https://github.com/boshka22/payment_service_testovoe
```

Создай `.env` файл:

```env
API_KEY=secret-api-key

POSTGRES_DB=payment_service
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/payment_service

RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest
RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/
```

Запусти:

```bash
docker-compose up --build
```

При старте API контейнер автоматически применяет миграции через `entrypoint.sh`.

## Эндпоинты

| Метод | Путь | Описание |
|-------|------|----------|
| `POST` | `/api/v1/payments` | Создание платежа |
| `GET` | `/api/v1/payments/{payment_id}` | Получение информации о платеже |
| `GET` | `/health` | Проверка работоспособности |

Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)

RabbitMQ Management: [http://localhost:15672](http://localhost:15672) (guest/guest)

## Аутентификация

Все эндпоинты (кроме `/health`) требуют заголовок:

```
X-API-Key: secret-api-key
```

В Swagger UI нажми кнопку **Authorize** и введи ключ.

## Создание платежа

**Запрос:**

```bash
curl -X POST http://localhost:8000/api/v1/payments \
  -H 'X-API-Key: secret-api-key' \
  -H 'Idempotency-Key: unique-key-123' \
  -H 'Content-Type: application/json' \
  -d '{
    "amount": 1000.00,
    "currency": "RUB",
    "description": "Оплата заказа #42",
    "metadata": {"order_id": "42"},
    "webhook_url": "https://your-service.com/webhook"
  }'
```

**Ответ (202 Accepted):**

```json
{
  "payment_id": "ba30ce80-18df-4954-b615-301de763a085",
  "status": "pending",
  "created_at": "2026-03-28T12:41:18.456419Z"
}
```

## Получение платежа

```bash
curl http://localhost:8000/api/v1/payments/ba30ce80-18df-4954-b615-301de763a085 \
  -H 'X-API-Key: secret-api-key'
```

**Ответ (200 OK):**

```json
{
  "payment_id": "ba30ce80-18df-4954-b615-301de763a085",
  "amount": "1000.00",
  "currency": "RUB",
  "description": "Оплата заказа #42",
  "metadata": {"order_id": "42"},
  "status": "succeeded",
  "webhook_url": "https://your-service.com/webhook",
  "created_at": "2026-03-28T12:41:18.456419Z",
  "processed_at": "2026-03-28T12:41:23.123456Z"
}
```

## Webhook уведомление

После обработки платежа сервис отправляет POST запрос на `webhook_url`:

```json
{
  "payment_id": "ba30ce80-18df-4954-b615-301de763a085",
  "status": "succeeded"
}
```

При ошибке доставки — 3 попытки с задержками 2 и 4 секунды. После исчерпания попыток сообщение уходит в DLQ.

## Idempotency Key

Повторный запрос с тем же `Idempotency-Key` возвращает существующий платёж без создания дубликата:

```bash
# Первый запрос — создаёт платёж
curl -X POST http://localhost:8000/api/v1/payments \
  -H 'Idempotency-Key: unique-key-123' ...
# → payment_id: ba30ce80-...

# Повторный запрос — возвращает тот же платёж
curl -X POST http://localhost:8000/api/v1/payments \
  -H 'Idempotency-Key: unique-key-123' ...
# → payment_id: ba30ce80-... (тот же!)
```

## Структура проекта

```
payment_service/
├── app/
│   ├── api/
│   │   └── v1/
│   │       └── payments.py       # роутеры
│   ├── consumer/
│   │   └── payment_consumer.py   # FastStream consumer
│   ├── core/
│   │   ├── config.py             # настройки
│   │   └── database.py           # подключение к БД
│   ├── database/
│   │   └── models.py             # SQLAlchemy модели
│   ├── enums.py                  # PaymentStatus, Currency, OutboxStatus
│   ├── exceptions/
│   │   └── payment.py            # кастомные исключения
│   ├── middleware/
│   │   └── auth.py               # APIKeyMiddleware
│   ├── repositories/
│   │   ├── base.py               # базовый репозиторий
│   │   ├── payment.py            # CRUD платежей
│   │   └── outbox.py             # CRUD outbox
│   ├── schemas/
│   │   └── v1/
│   │       └── payment.py        # Pydantic схемы
│   ├── services/
│   │   └── payment.py            # бизнес-логика
│   ├── workers/
│   │   └── outbox_worker.py      # Outbox polling worker
│   └── main.py                   # FastAPI приложение
├── alembic/
│   └── versions/                 # миграции БД
├── tests/
│   ├── unit/
│   │   └── test_payment_service.py
│   └── integration/
│       ├── test_api.py
│       └── test_repository.py (TODO)
├── consumer_main.py              # точка входа consumer
├── entrypoint.sh                 # миграции + запуск API
├── docker-compose.yml
├── Dockerfile.api
├── Dockerfile.consumer
├── pyproject.toml
└── requirements.txt
```

## Разработка

### Запуск тестов

```bash
# Все тесты (testcontainers автоматически поднимет PostgreSQL)
pytest tests/ -v

# Только юнит тесты
pytest tests/unit/ -v
```

### Линтеры

```bash
ruff check app/
ruff format app/
mypy app/
```

### Pre-commit хуки

```bash
pre-commit install
pre-commit run --all-files
```

### Миграции

```bash
# Создать новую миграцию
docker exec -it payment_service_api alembic revision --autogenerate -m "description"

# Скопировать файл локально
docker cp payment_service_api:/app/alembic/versions/<id>_description.py ./alembic/versions/

# Применить миграции
docker exec -it payment_service_api alembic upgrade head

# Откатить последнюю миграцию
docker exec -it payment_service_api alembic downgrade -1
```

## Статусы платежа

| Статус | Описание |
|--------|----------|
| `pending` | Платёж создан, ожидает обработки |
| `succeeded` | Платёж успешно обработан |
| `failed` | Платёж отклонён платёжным шлюзом |

## Коды ответов

| Код | Описание |
|-----|----------|
| `202` | Платёж принят в обработку |
| `200` | Успешный запрос |
| `400` | Некорректные данные |
| `401` | Неверный или отсутствующий API ключ |
| `404` | Платёж не найден |
| `500` | Внутренняя ошибка сервера |
