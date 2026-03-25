from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

@dataclass(frozen=True)
class CreateUserInput:
    email: str
    password_hash: str
    name: str


@dataclass(frozen=True)
class UpdateUserInput:
    name: str


@dataclass(frozen=True)
class AuthInput:
    email: str
    password_hash: str


@dataclass(frozen=True)
class AuthTokenView:
    access_token: str


@dataclass(frozen=True)
class UserView:
    id: UUID
    email: str
    name: str
