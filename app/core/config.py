"""Модуль конфигурации приложения."""

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

__all__ = ['settings']

load_dotenv()


class Settings(BaseSettings):
    """Настройки приложения из переменных окружения.

    Attributes:
        api_key: Статический API ключ для X-API-Key заголовка.
        database_url: URL подключения к PostgreSQL.
        rabbitmq_url: URL подключения к RabbitMQ.
        postgres_db: Имя базы данных.
        postgres_user: Пользователь БД.
        postgres_password: Пароль БД.
        webhook_timeout: Таймаут запроса к webhook в секундах.
        webhook_max_attempts: Максимальное количество попыток webhook.
        outbox_poll_interval: Интервал опроса outbox в секундах.
    """

    api_key: str
    database_url: str
    rabbitmq_url: str
    postgres_db: str
    postgres_user: str
    postgres_password: str
    webhook_timeout: int = 10
    webhook_max_attempts: int = 3
    outbox_poll_interval: int = 1

    class Config:
        env_file = '.env'


settings = Settings()