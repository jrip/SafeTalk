from __future__ import annotations

"""Подключение к БД и фабрика sqlalchemy.orm.Session (не путать с auth_sessions / логином)."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.settings import get_settings


def _normalize_database_url(url: str) -> str:
    if url.startswith("postgresql://") and not url.startswith("postgresql+psycopg"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def get_database_url() -> str:
    return _normalize_database_url(get_settings().database_url)


_engine = None


def get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        url = get_database_url()
        echo = settings.sql_echo
        if url.startswith("sqlite"):
            _engine = create_engine(url, echo=echo, connect_args={"check_same_thread": False})
        else:
            _engine = create_engine(url, echo=echo, pool_pre_ping=True)
    return _engine


engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Выдаёт сессию на HTTP-запрос. Коммит — в сервисах после успешной бизнес-операции."""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
