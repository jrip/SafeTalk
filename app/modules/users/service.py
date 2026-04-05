from __future__ import annotations

from dataclasses import replace
from uuid import UUID

from sqlalchemy.orm import Session

from app.core import NotFoundError, ValidationError
from app.modules.billing.storage_sqlalchemy import SqlAlchemyBalanceStore
from app.modules.users.entities import User
from app.modules.users.storage_sqlalchemy import SqlAlchemyUserStore
from app.modules.users.types import (
    AuthInput,
    AuthTokenView,
    CreateIdentityInput,
    CreateUserInput,
    UpdateUserInput,
    UserIdentityView,
    UserView,
)


class UserService:
    def __init__(self, users: SqlAlchemyUserStore, balance: SqlAlchemyBalanceStore, session: Session) -> None:
        self._users = users
        self._balance = balance
        self._session = session

    def register(self, payload: CreateUserInput) -> UserView:
        name = self.normalize_name(payload.name)
        user = User(
            name=name,
            role=payload.role,
        )
        self._users.add(user)
        self._balance.ensure_wallet(user.id)
        return self._to_user_view(user)

    def register_email_identity(self, user_id: UUID, login: str, password_hash: str) -> UserIdentityView:
        normalized_login = login.strip().lower()
        if self._users.get_identity("email", normalized_login):
            raise ValidationError("Login already registered")
        identity = self._users.add_identity(
            CreateIdentityInput(
                user_id=user_id,
                identity_type="email",
                identifier=normalized_login,
                secret_hash=password_hash,
                is_verified=False,
            )
        )
        self._session.commit()
        return identity

    def register_telegram_identity(self, user_id: UUID, telegram_id: int) -> UserIdentityView:
        identifier = f"telegram:{telegram_id}"
        existing = self._users.get_identity("telegram", identifier)
        if existing:
            return existing
        identity = self._users.add_identity(
            CreateIdentityInput(
                user_id=user_id,
                identity_type="telegram",
                identifier=identifier,
                secret_hash=None,
                is_verified=True,
            )
        )
        self._session.commit()
        return identity

    def find_telegram_identity(self, telegram_id: int) -> UserIdentityView | None:
        return self._users.get_identity("telegram", f"telegram:{telegram_id}")

    def verify_email_identity(self, login: str) -> None:
        self._users.verify_identity("email", login)
        self._session.commit()

    def get_auth_token(self, payload: AuthInput) -> AuthTokenView:
        identity_type = payload.identity_type.strip().lower()
        identifier = payload.identifier.strip().lower()
        identity = self._users.get_identity(identity_type, identifier)
        if identity is None:
            raise NotFoundError("User not found")
        if identity_type == "email":
            if not identity.is_verified:
                raise ValidationError("Email is not verified")
            if identity.secret_hash is None:
                raise ValidationError("Invalid credentials")
            if not self.is_password_match(identity.secret_hash, payload.password_hash):
                raise ValidationError("Invalid credentials")
        return AuthTokenView(access_token=str(identity.user_id))

    def get_email_identity(self, login: str) -> UserIdentityView | None:
        return self._users.get_identity("email", login)

    def get_identities(self, user_id: UUID) -> list[UserIdentityView]:
        return self._users.get_identities_by_user(user_id)

    def get_profile(self, user_id: UUID) -> UserView:
        user = self._users.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User not found")
        return self._to_user_view(user)

    def update_profile(self, user_id: UUID, payload: UpdateUserInput) -> UserView:
        user = self._users.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User not found")
        new_name = self.normalize_name(payload.name)
        updated = replace(user, name=new_name)
        self._users.save(updated)
        self._session.commit()
        return self._to_user_view(updated)

    def _to_user_view(self, user: User) -> UserView:
        return UserView(
            id=user.id,
            name=user.name,
            role=user.role,
            allow_negative_balance=user.allow_negative_balance,
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
