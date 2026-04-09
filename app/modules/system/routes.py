from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.api_models import ErrorResponse
from app.db.database import get_db

router = APIRouter(tags=["system"])


@router.get("/health", responses={500: {"model": ErrorResponse}})
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/db", responses={500: {"model": ErrorResponse}})
def health_db(session: Session = Depends(get_db)) -> dict[str, str]:
    session.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}
