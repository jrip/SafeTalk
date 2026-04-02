from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.bootstrap import AppContainer, build_app_container
from app.db.base import Base
from app.db.session import engine, get_db
import app.db.registry  # noqa: F401 — регистрация таблиц в metadata


def _init_db_schema_and_seed() -> None:
    Base.metadata.create_all(bind=engine)
    from app.db.seed import run_seed
    from app.db.session import SessionLocal

    session = SessionLocal()
    try:
        run_seed(session)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await asyncio.to_thread(_init_db_schema_and_seed)
    yield


app = FastAPI(title="SafeTalk", lifespan=lifespan)


def get_app_container(session: Session = Depends(get_db)) -> AppContainer:
    return build_app_container(session)


@app.get("/health")
def health() -> dict[str, str]:
    _ = os.environ.get("DATABASE_URL", "")
    return {"status": "ok"}


@app.get("/health/db")
def health_db(session: Session = Depends(get_db)) -> dict[str, str]:
    session.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}
