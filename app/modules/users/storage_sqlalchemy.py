from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import NotFoundError
from app.modules.users.entities import User
from app.modules.users.models import UserModel
from app.modules.users.ports import UserStore


def _user_from_model(row: UserModel) -> User:
    return User(
        id=row.id,
        email=row.email,
        password_hash=row.password_hash,
        name=row.name,
        role=row.role,
        allow_negative_balance=row.allow_negative_balance,
    )


def _user_to_model(user: User) -> UserModel:
    return UserModel(
        id=user.id,
        email=user.email,
        password_hash=user.password_hash,
        name=user.name,
        role=user.role,
        allow_negative_balance=user.allow_negative_balance,
    )


class SqlAlchemyUserStore(UserStore):
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, user_id: UUID) -> User | None:
        row = self._session.get(UserModel, user_id)
        return _user_from_model(row) if row else None

    def get_by_email(self, email: str) -> User | None:
        row = self._session.scalar(select(UserModel).where(UserModel.email == email.strip().lower()))
        return _user_from_model(row) if row else None

    def add(self, user: User) -> None:
        self._session.add(_user_to_model(user))
        self._session.flush()

    def save(self, user: User) -> None:
        row = self._session.get(UserModel, user.id)
        if row is None:
            raise NotFoundError("User not found")
        row.email = user.email
        row.password_hash = user.password_hash
        row.name = user.name
        row.role = user.role
        row.allow_negative_balance = user.allow_negative_balance
