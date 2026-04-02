from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.bootstrap import AppContainer, build_app_container
from app.core.settings import validate_settings
from app.db.config import Base  # подгружает модели в Base.metadata
from app.db.database import SessionLocal, engine, get_db
from app.db.seed import run_seed


def _init_db_schema_and_seed() -> None:
    Base.metadata.create_all(bind=engine)

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
    validate_settings()
    await asyncio.to_thread(_init_db_schema_and_seed)
    yield


app = FastAPI(title="SafeTalk", lifespan=lifespan)


def get_app_container(session: Session = Depends(get_db)) -> AppContainer:
    return build_app_container(session)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/db")
def health_db(session: Session = Depends(get_db)) -> dict[str, str]:
    session.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}
