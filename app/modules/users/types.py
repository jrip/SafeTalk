from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True)
class CreateUserInput:
    name: str
    role: str = "user"


@dataclass(frozen=True)
class UpdateUserInput:
    name: str


@dataclass(frozen=True)
class PatchUserInput:
    """Частичное обновление пользователя (только админская ручка PATCH /admin/users/{id})."""

    name: str | None = None
    allow_negative_balance: bool | None = None


@dataclass(frozen=True)
class AuthInput:
    identity_type: str
    identifier: str
    password_hash: str


@dataclass(frozen=True)
class AuthTokenView:
    access_token: str


@dataclass(frozen=True)
class UserView:
    id: UUID
    name: str
    role: str = "user"
    allow_negative_balance: bool = False


@dataclass(frozen=True)
class UserIdentityView:
    user_id: UUID
    identity_type: str
    identifier: str
    is_verified: bool
    secret_hash: str | None = None
    verification_code_hash: str | None = None
    verification_expires_at: datetime | None = None
    verification_attempts_left: int | None = None


@dataclass(frozen=True)
class AdminUserListRow:
    """Строка списка пользователей для админки."""

    id: UUID
    name: str
    role: str
    allow_negative_balance: bool
    primary_email: str | None
    token_count: Decimal


@dataclass(frozen=True)
class CreateIdentityInput:
    user_id: UUID
    identity_type: str
    identifier: str
    secret_hash: str | None = None
    is_verified: bool = False
