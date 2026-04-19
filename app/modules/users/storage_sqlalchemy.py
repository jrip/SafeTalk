from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core import NotFoundError
from app.modules.users.entities import User
from app.modules.users.models import (
    PasswordResetAttemptModel,
    PasswordResetTokenModel,
    UserIdentityModel,
    UserModel,
)
from app.modules.users.types import CreateIdentityInput, UserIdentityView


def _as_utc_aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


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

    def list_all(self) -> list[User]:
        rows = self._session.scalars(select(UserModel).order_by(UserModel.created_at.desc())).all()
        return [_user_from_model(row) for row in rows]

    def count_all(self) -> int:
        return int(self._session.scalar(select(func.count()).select_from(UserModel)) or 0)

    def count_admins(self) -> int:
        return int(
            self._session.scalar(select(func.count()).select_from(UserModel).where(UserModel.role == "admin")) or 0
        )

    def latest_registered_at(self) -> datetime | None:
        return self._session.scalar(select(func.max(UserModel.created_at)))

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

    def record_password_reset_attempt(self, email_normalized: str) -> None:
        self._session.add(
            PasswordResetAttemptModel(
                email_normalized=email_normalized,
            )
        )

    def count_password_reset_attempts_by_email(self, email_normalized: str, since: datetime) -> int:
        return int(
            self._session.scalar(
                select(func.count())
                .select_from(PasswordResetAttemptModel)
                .where(
                    PasswordResetAttemptModel.email_normalized == email_normalized,
                    PasswordResetAttemptModel.created_at >= since,
                )
            )
            or 0
        )

    def invalidate_unused_password_reset_tokens(self, user_id: UUID) -> None:
        self._session.execute(
            delete(PasswordResetTokenModel).where(
                PasswordResetTokenModel.user_id == user_id,
                PasswordResetTokenModel.used_at.is_(None),
            )
        )

    def insert_password_reset_token(self, user_id: UUID, token_hash: str, expires_at: datetime) -> None:
        self._session.add(
            PasswordResetTokenModel(
                user_id=user_id,
                token_hash=token_hash,
                expires_at=expires_at,
            )
        )

    def try_consume_password_reset_token(self, token_hash: str, now: datetime) -> UUID | None:
        row = self._session.scalar(
            select(PasswordResetTokenModel).where(PasswordResetTokenModel.token_hash == token_hash)
        )
        if row is None:
            return None
        if row.used_at is not None:
            return None
        if _as_utc_aware(row.expires_at) < _as_utc_aware(now):
            return None
        row.used_at = now
        return row.user_id

    def set_email_identity_password_hash(self, user_id: UUID, new_hash: str) -> None:
        row = self._session.scalar(
            select(UserIdentityModel).where(
                UserIdentityModel.user_id == user_id,
                UserIdentityModel.identity_type == "email",
            )
        )
        if row is None:
            raise NotFoundError("Email identity not found")
        row.secret_hash = new_hash
