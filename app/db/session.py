from __future__ import annotations

"""Подключение к БД и фабрика sqlalchemy.orm.Session (не путать с auth_sessions / логином)."""

import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


def _normalize_database_url(url: str) -> str:
    if url.startswith("postgresql://") and not url.startswith("postgresql+psycopg"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def get_database_url() -> str:
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        return "sqlite:///./app.db"
    return _normalize_database_url(url)


_engine = None


def get_engine():
    global _engine
    if _engine is None:
        url = get_database_url()
        echo = os.environ.get("SQL_ECHO", "").lower() in ("1", "true", "yes")
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
