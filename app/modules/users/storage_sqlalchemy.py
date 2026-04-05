from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import NotFoundError
from app.modules.users.entities import User
from app.modules.users.models import UserIdentityModel, UserModel
from app.modules.users.types import CreateIdentityInput, UserIdentityView


def _user_from_model(row: UserModel) -> User:
    return User(
        id=row.id,
        name=row.name,
        role=row.role,
        allow_negative_balance=row.allow_negative_balance,
    )


def _user_to_model(user: User) -> UserModel:
    return UserModel(
        id=user.id,
        name=user.name,
        role=user.role,
        allow_negative_balance=user.allow_negative_balance,
    )


def _identity_view_from_model(row: UserIdentityModel) -> UserIdentityView:
    return UserIdentityView(
        user_id=row.user_id,
        identity_type=row.identity_type,
        identifier=row.identifier,
        is_verified=row.is_verified,
        secret_hash=row.secret_hash,
        verification_code_hash=row.verification_code_hash,
        verification_expires_at=row.verification_expires_at,
        verification_attempts_left=row.verification_attempts_left,
    )


class SqlAlchemyUserStore:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, user_id: UUID) -> User | None:
        row = self._session.get(UserModel, user_id)
        return _user_from_model(row) if row else None

    def add(self, user: User) -> None:
        self._session.add(_user_to_model(user))
        self._session.flush()

    def save(self, user: User) -> None:
        row = self._session.get(UserModel, user.id)
        if row is None:
            raise NotFoundError("User not found")
        row.name = user.name
        row.role = user.role
        row.allow_negative_balance = user.allow_negative_balance

    def get_identity(self, identity_type: str, identifier: str) -> UserIdentityView | None:
        row = self._session.scalar(
            select(UserIdentityModel).where(
                UserIdentityModel.identity_type == identity_type,
                UserIdentityModel.identifier == identifier.strip().lower(),
            )
        )
        return _identity_view_from_model(row) if row else None

    def add_identity(self, payload: CreateIdentityInput) -> UserIdentityView:
        row = UserIdentityModel(
            user_id=payload.user_id,
            identity_type=payload.identity_type,
            identifier=payload.identifier.strip().lower(),
            secret_hash=payload.secret_hash,
            is_verified=payload.is_verified,
        )
        self._session.add(row)
        self._session.flush()
        return _identity_view_from_model(row)

    def verify_identity(self, identity_type: str, identifier: str) -> None:
        row = self._session.scalar(
            select(UserIdentityModel).where(
                UserIdentityModel.identity_type == identity_type,
                UserIdentityModel.identifier == identifier.strip().lower(),
            )
        )
        if row is None:
            raise NotFoundError("Identity not found")
        row.is_verified = True
        row.verification_code_hash = None
        row.verification_expires_at = None
        row.verification_attempts_left = None

    def get_identities_by_user(self, user_id: UUID) -> list[UserIdentityView]:
        rows = self._session.scalars(select(UserIdentityModel).where(UserIdentityModel.user_id == user_id)).all()
        return [_identity_view_from_model(row) for row in rows]

    def set_identity_verification(
        self,
        identity_type: str,
        identifier: str,
        code_hash: str,
        expires_at: datetime,
        attempts_left: int,
    ) -> None:
        row = self._session.scalar(
            select(UserIdentityModel).where(
                UserIdentityModel.identity_type == identity_type,
                UserIdentityModel.identifier == identifier.strip().lower(),
            )
        )
        if row is None:
            raise NotFoundError("Identity not found")
        row.verification_code_hash = code_hash
        row.verification_expires_at = expires_at
        row.verification_attempts_left = attempts_left

    def clear_identity_verification(self, identity_type: str, identifier: str) -> None:
        row = self._session.scalar(
            select(UserIdentityModel).where(
                UserIdentityModel.identity_type == identity_type,
                UserIdentityModel.identifier == identifier.strip().lower(),
            )
        )
        if row is None:
            raise NotFoundError("Identity not found")
        row.verification_code_hash = None
        row.verification_expires_at = None
        row.verification_attempts_left = None

    def decrement_identity_attempt(self, identity_type: str, identifier: str) -> int:
        row = self._session.scalar(
            select(UserIdentityModel).where(
                UserIdentityModel.identity_type == identity_type,
                UserIdentityModel.identifier == identifier.strip().lower(),
            )
        )
        if row is None:
            raise NotFoundError("Identity not found")
        current = row.verification_attempts_left or 0
        next_value = max(0, current - 1)
        row.verification_attempts_left = next_value
        return next_value
