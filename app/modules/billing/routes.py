from __future__ import annotations

from dataclasses import asdict
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.bootstrap import build_app_container
from app.db.database import get_db

router = APIRouter(prefix="/balance", tags=["balance"])


class TopUpRequest(BaseModel):
    amount: Decimal = Field(gt=0)


class SpendRequest(BaseModel):
    amount: Decimal = Field(gt=0)


def _container(session: Session = Depends(get_db)):
    return build_app_container(session)


def _as_json(payload: Any) -> dict[str, Any]:
    return asdict(payload)


@router.get("/{user_id}")
def get_balance(user_id: UUID, c=Depends(_container)) -> dict[str, Any]:
    return _as_json(c.billing.get_count_tokens(user_id))


@router.post("/{user_id}/topup")
def topup(user_id: UUID, payload: TopUpRequest, c=Depends(_container)) -> dict[str, Any]:
    return _as_json(c.billing.add_tokens(user_id, payload.amount))


@router.post("/{user_id}/spend")
def spend(user_id: UUID, payload: SpendRequest, c=Depends(_container)) -> dict[str, Any]:
    return _as_json(c.billing.spend_tokens(user_id, payload.amount))


@router.get("/{user_id}/ledger")
def ledger(user_id: UUID, c=Depends(_container)) -> list[dict[str, Any]]:
    return [asdict(x) for x in c.billing.get_ledger_history(user_id)]
