from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.bootstrap import build_app_container
from app.core.api_models import ErrorResponse
from app.db.database import get_db
from app.modules.users.auth import require_user_id

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


def _can_access_history(c: Any, current_user_id: UUID, target_user_id: UUID) -> bool:
    if current_user_id == target_user_id:
        return True
    return c.users.get_profile(current_user_id).role == "admin"


@router.get(
    "/me",
    response_model=list[HistoryResponse],
    responses={
        401: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
def my_history(c=Depends(_container), current_user_id: UUID = Depends(require_user_id)) -> list[dict[str, Any]]:
    return [asdict(x) for x in c.history.get_api_history(current_user_id)]


@router.get(
    "/{user_id}",
    response_model=list[HistoryResponse],
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
def history(user_id: UUID, c=Depends(_container), current_user_id: UUID = Depends(require_user_id)) -> list[dict[str, Any]]:
    if not _can_access_history(c, current_user_id, user_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return [asdict(x) for x in c.history.get_api_history(user_id)]
