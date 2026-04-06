from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

# Один файл: `app/.env` (тот же путь, что в docker-compose `env_file: app/.env`).
_APP_DIR = Path(__file__).resolve().parents[1]
_ENV_FILE = _APP_DIR / ".env"
_ENV_FILES = (str(_ENV_FILE),) if _ENV_FILE.is_file() else ()


class Settings(BaseSettings):
    DB_HOST: Optional[str] = None
    DB_PORT: Optional[int] = None
    DB_USER: Optional[str] = None
    DB_PASS: Optional[str] = None
    DB_NAME: Optional[str] = None

    @property
    def DATABASE_URL_asyncpg(self) -> str:
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def DATABASE_URL_psycopg(self) -> str:
        return f"postgresql+psycopg://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    model_config = SettingsConfigDict(env_file=_ENV_FILES or None)


class AppSettings(Settings):
    """Расширение под приложение: опциональная строка URL, echo SQL, RabbitMQ."""

    database_url: Optional[str] = None
    sql_echo: bool = False

    RABBITMQ_HOST: Optional[str] = None
    RABBITMQ_PORT: Optional[int] = None
    RABBITMQ_USER: Optional[str] = None
    RABBITMQ_PASS: Optional[str] = None
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_WEBHOOK_SECRET_TOKEN: Optional[str] = None
    email_verification_ttl_seconds: int = 3600
    email_verification_max_attempts: int = 10

    model_config = SettingsConfigDict(
        env_file=_ENV_FILES or None,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def rabbitmq_url(self) -> Optional[str]:
        """Строка подключения к брокеру; если RABBITMQ_HOST не задан — None."""
        if not self.RABBITMQ_HOST:
            return None
        port = self.RABBITMQ_PORT if self.RABBITMQ_PORT is not None else 5672
        user = self.RABBITMQ_USER or "guest"
        password = self.RABBITMQ_PASS if self.RABBITMQ_PASS is not None else "guest"
        return f"amqp://{user}:{password}@{self.RABBITMQ_HOST}:{port}/"

    @property
    def sqlalchemy_database_url(self) -> str:
        raw = (self.database_url or "").strip()
        if raw:
            if raw.startswith("sqlite"):
                return raw
            if raw.startswith("postgresql://") and not raw.startswith("postgresql+psycopg"):
                return raw.replace("postgresql://", "postgresql+psycopg://", 1)
            return raw
        if self.DB_HOST and self.DB_USER and self.DB_NAME:
            return self.DATABASE_URL_psycopg
        return "sqlite:///./app.db"


@lru_cache()
def get_settings() -> AppSettings:
    return AppSettings()


def validate_settings() -> AppSettings:
    return get_settings()
