from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.bootstrap import build_app_container
from app.core.api_models import ErrorResponse
from app.db.database import get_db
from app.modules.billing.routes import BalanceLedgerEntryResponse
from app.modules.users.auth import require_user_id


def _container(session: Session = Depends(get_db)):
    return build_app_container(session)


def _require_admin(c: Any, current_user_id: UUID) -> None:
    me = c.users.get_profile(current_user_id)
    if me.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")


router = APIRouter(prefix="/admin", tags=["admin"])


class AdminUserRowResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    role: str
    allow_negative_balance: bool
    primary_email: str | None
    token_count: Decimal


class AdminStatsResponse(BaseModel):
    users_count: int
    history_records_count: int
    ledger_entries_count: int
    total_tokens_in_balances: Decimal


@router.get(
    "/users",
    response_model=list[AdminUserRowResponse],
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def admin_list_users(
    c=Depends(_container), current_user_id: UUID = Depends(require_user_id)
) -> list[AdminUserRowResponse]:
    _require_admin(c, current_user_id)
    rows = c.users.list_users_admin()
    return [AdminUserRowResponse.model_validate(r) for r in rows]


@router.get(
    "/stats",
    response_model=AdminStatsResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def admin_stats(c=Depends(_container), current_user_id: UUID = Depends(require_user_id)) -> AdminStatsResponse:
    _require_admin(c, current_user_id)
    return AdminStatsResponse(
        users_count=c.users.count_users(),
        history_records_count=c.history.count_all_records(),
        ledger_entries_count=c.billing.count_ledger_entries(),
        total_tokens_in_balances=c.billing.sum_all_balances(),
    )


@router.get(
    "/ledger",
    response_model=list[BalanceLedgerEntryResponse],
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def admin_ledger(
    c=Depends(_container),
    current_user_id: UUID = Depends(require_user_id),
    limit: int = 500,
) -> list[BalanceLedgerEntryResponse]:
    _require_admin(c, current_user_id)
    cap = min(max(limit, 1), 2000)
    return [BalanceLedgerEntryResponse.model_validate(x) for x in c.billing.get_all_ledger(limit=cap)]
