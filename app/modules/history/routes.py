from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.bootstrap import build_app_container
from app.core.api_models import ErrorResponse
from app.db.database import get_db

router = APIRouter(prefix="/history", tags=["history"])


def _container(session: Session = Depends(get_db)):
    return build_app_container(session)


class HistoryResponse(BaseModel):
    id: UUID
    user_id: UUID
    request: str
    result: str
    created_at: datetime
    ml_model_id: UUID | None = None
    ml_task_id: UUID | None = None
    tokens_charged: Decimal | None = None


@router.get(
    "/{user_id}",
    response_model=list[HistoryResponse],
    responses={
        404: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
def history(user_id: UUID, c=Depends(_container)) -> list[dict[str, Any]]:
    return [asdict(x) for x in c.history.get_api_history(user_id)]
