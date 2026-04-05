from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class CreateUserInput:
    name: str
    role: str = "user"


@dataclass(frozen=True)
class UpdateUserInput:
    name: str


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


@dataclass(frozen=True)
class CreateIdentityInput:
    user_id: UUID
    identity_type: str
    identifier: str
    secret_hash: str | None = None
    is_verified: bool = False
