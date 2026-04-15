from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.orm import Session

from app.bootstrap import build_app_container
from app.core.api_models import ErrorResponse
from app.db.database import get_db
from app.modules.users.auth import require_user_id

router = APIRouter(prefix="/balance", tags=["balance"])


class TopUpRequest(BaseModel):
    """Тело POST /balance/{user_id}/topup — сколько токенов зачислить."""

    amount: Decimal = Field(
        gt=0,
        description="Сколько токенов добавить (в Swagger — в блоке Request body, JSON).",
        json_schema_extra={"example": "1000"},
    )


class BalanceResponse(BaseModel):
    user_id: UUID
    token_count: Decimal


class BalanceLedgerEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    user_id: UUID
    kind: str
    amount: Decimal
    task_id: UUID | None
    created_at: datetime


def _container(session: Session = Depends(get_db)):
    return build_app_container(session)


def _as_json(payload: Any) -> dict[str, Any]:
    return asdict(payload)


def _can_access_balance(c: Any, current_user_id: UUID, target_user_id: UUID) -> bool:
    if current_user_id == target_user_id:
        return True
    return c.users.get_profile(current_user_id).role == "admin"


@router.get(
    "/me",
    response_model=BalanceResponse,
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
def get_my_balance(c=Depends(_container), current_user_id: UUID = Depends(require_user_id)) -> dict[str, Any]:
    return _as_json(c.billing.get_count_tokens(current_user_id))


@router.get(
    "/me/ledger",
    response_model=list[BalanceLedgerEntryResponse],
    responses={
        401: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
def get_my_ledger(c=Depends(_container), current_user_id: UUID = Depends(require_user_id)) -> list[dict[str, Any]]:
    return [asdict(x) for x in c.billing.get_ledger_history(current_user_id)]


@router.post(
    "/me/topup",
    response_model=BalanceResponse,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"model": ErrorResponse},
        400: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
def topup_me(
    payload: TopUpRequest,
    c=Depends(_container),
    current_user_id: UUID = Depends(require_user_id),
) -> dict[str, Any]:
    """Демо-пополнение без эквайринга (личный кабинет, ТЗ)."""
    return _as_json(c.billing.add_tokens(current_user_id, payload.amount))


@router.get(
    "/{user_id}",
    response_model=BalanceResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
def get_balance(user_id: UUID, c=Depends(_container), current_user_id: UUID = Depends(require_user_id)) -> dict[str, Any]:
    if not _can_access_balance(c, current_user_id, user_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return _as_json(c.billing.get_count_tokens(user_id))


@router.get(
    "/{user_id}/ledger",
    response_model=list[BalanceLedgerEntryResponse],
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
def ledger(user_id: UUID, c=Depends(_container), current_user_id: UUID = Depends(require_user_id)) -> list[dict[str, Any]]:
    if not _can_access_balance(c, current_user_id, user_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return [asdict(x) for x in c.billing.get_ledger_history(user_id)]
