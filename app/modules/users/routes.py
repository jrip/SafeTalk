from __future__ import annotations

from dataclasses import asdict
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.bootstrap import build_app_container
from app.db.database import get_db
from app.modules.users.types import AuthInput, CreateUserInput, UpdateUserInput

router = APIRouter(prefix="/auth", tags=["auth"])
users_router = APIRouter(prefix="/users", tags=["users"])


class RegisterRequest(BaseModel):
    email: str
    password: str = Field(min_length=1)
    name: str = Field(min_length=1)


class LoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=1)


class UpdateMeRequest(BaseModel):
    name: str = Field(min_length=1)


def _container(session: Session = Depends(get_db)):
    return build_app_container(session)


def _as_json(payload: Any) -> dict[str, Any]:
    return asdict(payload)


@router.post("/register")
def register(payload: RegisterRequest, c=Depends(_container)) -> dict[str, Any]:
    user = c.users.register(
        CreateUserInput(
            email=payload.email,
            password_hash=payload.password,
            name=payload.name,
        )
    )
    return _as_json(user)


@router.post("/login")
def login(payload: LoginRequest, c=Depends(_container)) -> dict[str, Any]:
    try:
        token = c.users.get_auth_token(AuthInput(email=payload.email, password_hash=payload.password))
        return _as_json(token)
    except NotImplementedError as e:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(e)) from e


@users_router.get("/{user_id}")
def get_user(user_id: UUID, c=Depends(_container)) -> dict[str, Any]:
    return _as_json(c.users.get_profile(user_id))


@users_router.patch("/{user_id}")
def update_user(user_id: UUID, payload: UpdateMeRequest, c=Depends(_container)) -> dict[str, Any]:
    updated = c.users.update_profile(user_id, UpdateUserInput(name=payload.name))
    return _as_json(updated)
