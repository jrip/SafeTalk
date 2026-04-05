from __future__ import annotations

from dataclasses import replace
from uuid import UUID

from sqlalchemy.orm import Session

from app.core import NotFoundError, ValidationError
from app.modules.billing.storage_sqlalchemy import SqlAlchemyBalanceStore
from app.modules.users.entities import User
from app.modules.users.storage_sqlalchemy import SqlAlchemyUserStore
from app.modules.users.types import AuthInput, AuthTokenView, CreateUserInput, UpdateUserInput, UserView


class UserService:
    def __init__(self, users: SqlAlchemyUserStore, balance: SqlAlchemyBalanceStore, session: Session) -> None:
        self._users = users
        self._balance = balance
        self._session = session

    def register(self, payload: CreateUserInput) -> UserView:
        email = payload.email.strip().lower()
        if self._users.get_by_email(email):
            raise ValidationError("Email already registered")
        name = self.normalize_name(payload.name)
        user = User(
            email=email,
            password_hash=payload.password_hash,
            name=name,
            role=payload.role,
        )
        self._users.add(user)
        self._balance.ensure_wallet(user.id)
        self._session.commit()
        return UserView(
            id=user.id,
            email=user.email,
            name=user.name,
            role=user.role,
            allow_negative_balance=user.allow_negative_balance,
        )

    def get_auth_token(self, payload: AuthInput) -> AuthTokenView:
        email = payload.email.strip().lower()
        user = self._users.get_by_email(email)
        if user is None:
            raise NotFoundError("User not found")
        if not self.is_password_match(user.password_hash, payload.password_hash):
            raise ValidationError("Invalid credentials")
        return AuthTokenView(access_token=str(user.id))

    def get_profile(self, user_id: UUID) -> UserView:
        user = self._users.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User not found")
        return UserView(
            id=user.id,
            email=user.email,
            name=user.name,
            role=user.role,
            allow_negative_balance=user.allow_negative_balance,
        )

    def update_profile(self, user_id: UUID, payload: UpdateUserInput) -> UserView:
        user = self._users.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User not found")
        new_name = self.normalize_name(payload.name)
        updated = replace(user, name=new_name)
        self._users.save(updated)
        self._session.commit()
        return UserView(
            id=updated.id,
            email=updated.email,
            name=updated.name,
            role=updated.role,
            allow_negative_balance=updated.allow_negative_balance,
        )

    @staticmethod
    def normalize_name(name: str) -> str:
        normalized = name.strip()
        if not normalized:
            raise ValidationError("User name cannot be empty")
        return normalized

    @staticmethod
    def is_password_match(stored_hash: str, incoming_hash: str) -> bool:
        return stored_hash == incoming_hash
