from __future__ import annotations

from dataclasses import asdict
import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.bootstrap import build_app_container
from app.core import ValidationError
from app.core.api_models import ErrorResponse
from app.db.database import get_db
from app.modules.users.auth import (
    get_email_verification_status,
    issue_access_token,
    issue_email_verification,
    require_user_id,
    verify_email_code,
)
from app.modules.users.types import AuthInput, CreateUserInput, UpdateUserInput

router = APIRouter(prefix="/auth", tags=["auth"])
users_router = APIRouter(prefix="/users", tags=["users"])
log = logging.getLogger(__name__)


class RegisterRequest(BaseModel):
    login: str
    password: str = Field(min_length=1)
    name: str = Field(min_length=1)


class LoginRequest(BaseModel):
    login: str
    password: str = Field(min_length=1)


class VerifyEmailRequest(BaseModel):
    login: str
    code: str = Field(min_length=1, max_length=32)


class UpdateMeRequest(BaseModel):
    name: str = Field(min_length=1)


class UserResponse(BaseModel):
    id: UUID
    name: str
    role: str
    allow_negative_balance: bool
    identities: list[str]


class AuthTokenResponse(BaseModel):
    access_token: str


class VerifyEmailResponse(BaseModel):
    status: str
    attempts_left: int
    expires_in_seconds: int


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
    if not payload.login.strip():
        raise ValidationError("Login cannot be empty")
    if "@" not in payload.login or "." not in payload.login:
        raise ValidationError("Email format is invalid")
    user = c.users.register(
        CreateUserInput(
            name=payload.name,
        )
    )
    c.users.register_email_identity(user.id, payload.login, payload.password)
    verification_code = issue_email_verification(user.id, payload.login)
    log.info(
        "registration mock email sent to login=%s; pending verification code=%s (future: real email provider)",
        payload.login,
        verification_code,
    )
    identities = c.users.get_identities(user.id)
    data = _as_json(user)
    data["identities"] = [f"{i.identity_type}:{i.identifier}" for i in identities]
    return data


@router.post(
    "/verify-email",
    response_model=VerifyEmailResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
def verify_email(payload: VerifyEmailRequest, c=Depends(_container)) -> dict[str, Any]:
    identity = c.users.get_email_identity(payload.login)
    if identity is None:
        raise ValidationError("User not found")
    verified_user_id = verify_email_code(payload.login, payload.code)
    if verified_user_id is None or verified_user_id != identity.user_id:
        status_info = get_email_verification_status(payload.login)
        if status_info["attempts_left"] <= 0 or status_info["expires_in_seconds"] <= 0:
            raise ValidationError("Verification code expired or attempts exceeded. Please register again.")
        raise ValidationError(
            f"Invalid verification code. Attempts left: {status_info['attempts_left']}, "
            f"expires in: {status_info['expires_in_seconds']}s"
        )
    c.users.verify_email_identity(payload.login)
    return {"status": "verified", "attempts_left": 0, "expires_in_seconds": 0}


@router.post(
    "/login",
    response_model=AuthTokenResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
def login(payload: LoginRequest, c=Depends(_container)) -> dict[str, Any]:
    auth_view = c.users.get_auth_token(
        AuthInput(identity_type="email", identifier=payload.login, password_hash=payload.password)
    )
    token = issue_access_token(UUID(auth_view.access_token))
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
    user = c.users.get_profile(user_id)
    identities = c.users.get_identities(user_id)
    data = _as_json(user)
    data["identities"] = [f"{i.identity_type}:{i.identifier}" for i in identities]
    return data


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
    identities = c.users.get_identities(user_id)
    data = _as_json(updated)
    data["identities"] = [f"{i.identity_type}:{i.identifier}" for i in identities]
    return data
