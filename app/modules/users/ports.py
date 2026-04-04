from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.modules.users.entities import User


class UserStore(Protocol):
    def get_by_id(self, user_id: UUID) -> User | None: ...

    def get_by_email(self, email: str) -> User | None: ...

    def add(self, user: User) -> None: ...

    def save(self, user: User) -> None: ...
