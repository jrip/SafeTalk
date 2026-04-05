from __future__ import annotations

from dataclasses import asdict
import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.bootstrap import build_app_container
from app.core import NotFoundError, ValidationError
from app.core.api_models import ErrorResponse
from app.db.database import get_db
from app.modules.users.auth import issue_access_token
from app.modules.users.types import CreateUserInput

router = APIRouter(prefix="/telegram", tags=["telegram"])
log = logging.getLogger(__name__)


class TelegramRegisterRequest(BaseModel):
    telegram_id: int = Field(gt=0)
    username: str | None = None
    name: str | None = None


class TelegramBindEmailRequest(BaseModel):
    telegram_id: int = Field(gt=0)
    login: str
    password: str = Field(min_length=1)


class TelegramCompleteRequest(BaseModel):
    telegram_id: int = Field(gt=0)


class UserResponse(BaseModel):
    id: UUID
    name: str
    role: str
    allow_negative_balance: bool
    identities: list[str]


class TelegramRegisterResponse(BaseModel):
    user: UserResponse
    status: str
    created: bool


class TelegramCompleteResponse(BaseModel):
    user: UserResponse
    access_token: str


def _container(session: Session = Depends(get_db)):
    return build_app_container(session)


def _as_json(payload: Any) -> dict[str, Any]:
    return asdict(payload)


def _has_verified_email(identities: list[Any]) -> bool:
    for identity in identities:
        if identity.identity_type == "email" and identity.is_verified:
            return True
    return False


@router.post(
    "/register",
    response_model=TelegramRegisterResponse,
    responses={
        400: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
def register_telegram(payload: TelegramRegisterRequest, c=Depends(_container)) -> dict[str, Any]:
    display_name = (payload.name or payload.username or f"tg_{payload.telegram_id}").strip()
    if not display_name:
        raise ValidationError("Telegram display name cannot be empty")

    identity = c.users.find_telegram_identity(payload.telegram_id)
    created = identity is None
    if identity is None:
        user = c.users.register(CreateUserInput(name=display_name))
        c.users.register_telegram_identity(user.id, payload.telegram_id)
    else:
        user = c.users.get_profile(identity.user_id)

    identities = c.users.get_identities(user.id)
    user_data = _as_json(user)
    user_data["identities"] = [f"{i.identity_type}:{i.identifier}" for i in identities]
    status_value = "ready" if _has_verified_email(identities) else "need_email"
    return {
        "user": user_data,
        "status": status_value,
        "created": created,
    }


@router.post(
    "/bind-email",
    response_model=TelegramRegisterResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
def bind_email(payload: TelegramBindEmailRequest, c=Depends(_container)) -> dict[str, Any]:
    if "@" not in payload.login or "." not in payload.login:
        raise ValidationError("Email format is invalid")

    identity = c.users.find_telegram_identity(payload.telegram_id)
    if identity is None:
        raise NotFoundError("Telegram identity not found")

    user = c.users.get_profile(identity.user_id)
    existing_email_identity = c.users.get_email_identity(payload.login)
    if existing_email_identity is None:
        c.users.register_email_identity(user.id, payload.login, payload.password)
    elif existing_email_identity.user_id != user.id:
        raise ValidationError("Email already linked to another user")

    verification_code = c.users.start_email_verification(payload.login)
    log.info(
        "telegram email verification sent to login=%s; code=%s (future: real email provider)",
        payload.login,
        verification_code,
    )
    identities = c.users.get_identities(user.id)
    user_data = _as_json(user)
    user_data["identities"] = [f"{i.identity_type}:{i.identifier}" for i in identities]
    return {
        "user": user_data,
        "status": "need_verification",
        "created": False,
    }


@router.post(
    "/complete",
    response_model=TelegramCompleteResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
def complete_telegram_auth(payload: TelegramCompleteRequest, c=Depends(_container)) -> dict[str, Any]:
    identity = c.users.find_telegram_identity(payload.telegram_id)
    if identity is None:
        raise NotFoundError("Telegram identity not found")

    user = c.users.get_profile(identity.user_id)
    identities = c.users.get_identities(user.id)
    if not _has_verified_email(identities):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email must be verified before entering Telegram menu",
        )

    token = issue_access_token(user.id)
    user_data = _as_json(user)
    user_data["identities"] = [f"{i.identity_type}:{i.identifier}" for i in identities]
    return {
        "user": user_data,
        "access_token": token,
    }
