from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import Optional

from pydantic import Field


class Settings(BaseSettings):
    DB_HOST: Optional[str] = None
    DB_PORT: Optional[int] = None
    DB_USER: Optional[str] = None
    DB_PASS: Optional[str] = None
    DB_NAME: Optional[str] = None

    @property
    def DATABASE_URL_asyncpg(self):
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def DATABASE_URL_psycopg(self):
        return f"postgresql+psycopg://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    model_config = SettingsConfigDict(env_file=".env")


class AppSettings(Settings):
    """Поля приложения (DATABASE_URL для Docker/SQLite, echo, RabbitMQ). Блок выше — как на уроке."""

    database_url: Optional[str] = Field(default=None)
    sql_echo: bool = Field(default=False)
    rabbitmq_url: Optional[str] = Field(default=None)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def sqlalchemy_database_url(self) -> str:
        if self.DB_HOST and self.DB_USER and self.DB_NAME:
            return self.DATABASE_URL_psycopg
        raw = (self.database_url or "").strip()
        if not raw:
            return "sqlite:///./app.db"
        if raw.startswith("sqlite"):
            return raw
        if raw.startswith("postgresql://") and not raw.startswith("postgresql+psycopg"):
            return raw.replace("postgresql://", "postgresql+psycopg://", 1)
        return raw


@lru_cache()
def get_settings() -> AppSettings:
    return AppSettings()


def validate_settings() -> AppSettings:
    return get_settings()
