from __future__ import annotations

from dataclasses import asdict
import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.bootstrap import build_app_container
from app.core.api_models import ErrorResponse
from app.core import ValidationError
from app.db.database import get_db
from app.modules.users.auth import issue_access_token, require_user_id
from app.modules.users.types import AuthInput, CreateUserInput, UpdateUserInput

router = APIRouter(prefix="/auth", tags=["auth"])
users_router = APIRouter(prefix="/users", tags=["users"])
log = logging.getLogger(__name__)


class RegisterRequest(BaseModel):
    email: str
    password: str = Field(min_length=1)
    name: str = Field(min_length=1)


class LoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=1)


class UpdateMeRequest(BaseModel):
    name: str = Field(min_length=1)


class UserResponse(BaseModel):
    id: UUID
    email: str
    name: str
    role: str
    allow_negative_balance: bool


class AuthTokenResponse(BaseModel):
    access_token: str


def _container(session: Session = Depends(get_db)):
    return build_app_container(session)


def _as_json(payload: Any) -> dict[str, Any]:
    return asdict(payload)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
def register(payload: RegisterRequest, c=Depends(_container)) -> dict[str, Any]:
    if "@" not in payload.email or "." not in payload.email:
        raise ValidationError("Email format is invalid")
    user = c.users.register(
        CreateUserInput(
            email=payload.email,
            password_hash=payload.password,
            name=payload.name,
        )
    )
    verification_code = f"{user.id.hex[:6].upper()}"
    log.info(
        "registration mock email sent to %s; pending verification code=%s",
        user.email,
        verification_code,
    )
    return _as_json(user)


@router.post(
    "/login",
    response_model=AuthTokenResponse,
    responses={
        501: {"model": ErrorResponse},
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
def login(payload: LoginRequest, c=Depends(_container)) -> dict[str, Any]:
    auth_view = c.users.get_auth_token(AuthInput(email=payload.email, password_hash=payload.password))
    user = c.users.get_profile(UUID(auth_view.access_token))
    token = issue_access_token(user.id)
    return {"access_token": token}


@users_router.get(
    "/{user_id}",
    response_model=UserResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
def get_user(user_id: UUID, c=Depends(_container), current_user_id: UUID = Depends(require_user_id)) -> dict[str, Any]:
    if current_user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return _as_json(c.users.get_profile(user_id))


@users_router.patch(
    "/{user_id}",
    response_model=UserResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        400: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
def update_user(
    user_id: UUID,
    payload: UpdateMeRequest,
    c=Depends(_container),
    current_user_id: UUID = Depends(require_user_id),
) -> dict[str, Any]:
    if current_user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    updated = c.users.update_profile(user_id, UpdateUserInput(name=payload.name))
    return _as_json(updated)
