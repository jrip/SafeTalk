from __future__ import annotations

from dataclasses import asdict
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.orm import Session

from app.bootstrap import build_app_container
from app.core.api_models import ErrorResponse
from app.db.database import get_db
from app.modules.billing.routes import BalanceLedgerEntryResponse, BalanceResponse, TopUpRequest
from app.modules.users.auth import require_user_id
from app.modules.users.types import PatchUserInput


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
    admins_count: int
    last_registration_at: str | None
    total_credits: Decimal
    total_debits: Decimal
    positive_balances_sum: Decimal
    ml_tasks_total: int
    ml_tasks_pending: int
    ml_tasks_completed: int


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


class AdminUserProfileResponse(BaseModel):
    """Тело ответа GET/PATCH `/admin/users/{user_id}` — как публичный профиль, но только для админа."""

    id: UUID
    name: str
    role: str
    allow_negative_balance: bool
    identities: list[str]


class AdminPatchUserRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    allow_negative_balance: bool | None = None

    @model_validator(mode="after")
    def at_least_one_field(self) -> AdminPatchUserRequest:
        if self.name is None and self.allow_negative_balance is None:
            raise ValueError("At least one of name, allow_negative_balance must be set")
        return self


class AdminSpendRequest(BaseModel):
    amount: Decimal = Field(gt=0, json_schema_extra={"example": "10"})


def _user_profile_dict(c: Any, user_id: UUID) -> dict[str, Any]:
    user = c.users.get_profile(user_id)
    identities = c.users.get_identities(user_id)
    data = asdict(user)
    data["identities"] = [f"{i.identity_type}:{i.identifier}" for i in identities]
    return data


@router.get(
    "/users/{user_id}",
    response_model=AdminUserProfileResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def admin_get_user(
    user_id: UUID,
    c=Depends(_container),
    current_user_id: UUID = Depends(require_user_id),
) -> dict[str, Any]:
    _require_admin(c, current_user_id)
    return _user_profile_dict(c, user_id)


@router.patch(
    "/users/{user_id}",
    response_model=AdminUserProfileResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        400: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
def admin_patch_user(
    user_id: UUID,
    payload: AdminPatchUserRequest,
    c=Depends(_container),
    current_user_id: UUID = Depends(require_user_id),
) -> dict[str, Any]:
    _require_admin(c, current_user_id)
    updated = c.users.admin_patch_user(
        user_id,
        PatchUserInput(name=payload.name, allow_negative_balance=payload.allow_negative_balance),
    )
    data = asdict(updated)
    data["identities"] = [f"{i.identity_type}:{i.identifier}" for i in c.users.get_identities(user_id)]
    return data


@router.post(
    "/users/{user_id}/topup",
    response_model=BalanceResponse,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
def admin_topup_user(
    user_id: UUID,
    payload: TopUpRequest,
    c=Depends(_container),
    current_user_id: UUID = Depends(require_user_id),
) -> dict[str, Any]:
    _require_admin(c, current_user_id)
    return asdict(c.billing.add_tokens(user_id, payload.amount))


@router.post(
    "/users/{user_id}/spend",
    response_model=BalanceResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
def admin_spend_user(
    user_id: UUID,
    payload: AdminSpendRequest,
    c=Depends(_container),
    current_user_id: UUID = Depends(require_user_id),
) -> dict[str, Any]:
    _require_admin(c, current_user_id)
    return asdict(c.billing.spend_tokens(user_id, payload.amount))


@router.get(
    "/stats",
    response_model=AdminStatsResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def admin_stats(c=Depends(_container), current_user_id: UUID = Depends(require_user_id)) -> AdminStatsResponse:
    _require_admin(c, current_user_id)
    last_reg = c.users.get_latest_registration_at()
    return AdminStatsResponse(
        users_count=c.users.count_users(),
        admins_count=c.users.count_admins(),
        last_registration_at=last_reg.isoformat() if last_reg is not None else None,
        total_credits=c.billing.sum_credits(),
        total_debits=c.billing.sum_debits(),
        positive_balances_sum=c.billing.sum_positive_balances(),
        ml_tasks_total=c.neural.count_tasks_all(),
        ml_tasks_pending=c.neural.count_tasks_pending(),
        ml_tasks_completed=c.neural.count_tasks_completed(),
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
