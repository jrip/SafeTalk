from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import Optional

from pydantic import Field, field_validator


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

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- SafeTalk: тот же `.env`, см. docker-compose / DATABASE_URL ---
    database_url: Optional[str] = Field(default=None)
    sql_echo: bool = Field(default=False)
    rabbitmq_url: Optional[str] = Field(default=None)

    @field_validator("database_url", mode="before")
    @classmethod
    def _empty_database_url_to_none(cls, v: object) -> Optional[str]:
        if v is None:
            return None
        if isinstance(v, str) and not v.strip():
            return None
        return v if isinstance(v, str) else str(v)

    @field_validator("sql_echo", mode="before")
    @classmethod
    def _coerce_sql_echo(cls, v: object) -> bool:
        if isinstance(v, str):
            return v.strip().lower() in ("1", "true", "yes", "on")
        return bool(v)

    @property
    def sqlalchemy_database_url(self) -> str:
        if self.DB_HOST and self.DB_USER and self.DB_NAME:
            return self.DATABASE_URL_psycopg
        raw = (self.database_url or "").strip()
        if not raw:
            return "sqlite:///./app.db"
        if raw.startswith("sqlite"):
            return raw
        if raw.startswith("postgresql+asyncpg://"):
            return raw.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
        if raw.startswith("postgresql://") and not raw.startswith("postgresql+psycopg"):
            return raw.replace("postgresql://", "postgresql+psycopg://", 1)
        return raw


@lru_cache()
def get_settings() -> Settings:
    return Settings()


def validate_settings() -> Settings:
    return get_settings()
