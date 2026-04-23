from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
import hashlib
import logging
import secrets
from uuid import UUID

import bcrypt
from sqlalchemy.orm import Session

from app.core import NotFoundError, ValidationError
from app.core.settings import get_settings
from app.modules.billing.storage_sqlalchemy import SqlAlchemyBalanceStore
from app.modules.users.entities import User
from app.modules.users.storage_sqlalchemy import SqlAlchemyUserStore
from app.modules.users.token_store import revoke_access_tokens_for_user
from app.modules.users.types import (
    AdminUserListRow,
    AuthInput,
    AuthTokenView,
    CreateIdentityInput,
    CreateUserInput,
    PatchUserInput,
    UpdateUserInput,
    UserIdentityView,
    UserView,
)


log = logging.getLogger(__name__)


def hash_password(plain: str) -> str:
    """Bcrypt для поля secret_hash в БД."""
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(plain: str, stored: str | None) -> bool:
    if not plain or stored is None:
        return False
    if not stored.startswith(("$2a$", "$2b$", "$2y$")):
        return False
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), stored.encode("utf-8"))
    except ValueError:
        return False


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

    def register_email_identity(self, user_id: UUID, login: str, password: str) -> UserIdentityView:
        normalized_login = login.strip().lower()
        if self._users.get_identity("email", normalized_login):
            raise ValidationError("Login already registered")
        identity = self._users.add_identity(
            CreateIdentityInput(
                user_id=user_id,
                identity_type="email",
                identifier=normalized_login,
                secret_hash=hash_password(password),
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

    def start_email_verification(self, login: str) -> str:
        identity = self.get_email_identity(login)
        if identity is None:
            raise NotFoundError("User not found")
        settings = get_settings()
        code = secrets.token_hex(3).upper()
        code_hash = hashlib.sha256(code.encode("utf-8")).hexdigest()
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=settings.email_verification_ttl_seconds)
        self._users.set_identity_verification(
            "email",
            login,
            code_hash=code_hash,
            expires_at=expires_at,
            attempts_left=settings.email_verification_max_attempts,
        )
        self._session.commit()
        return code

    def verify_email_code(self, login: str, code: str) -> None:
        identity = self.get_email_identity(login)
        if identity is None:
            raise NotFoundError("User not found")

        if identity.verification_code_hash is None or identity.verification_expires_at is None:
            raise ValidationError("No active verification request. Please register again.")

        now = datetime.now(timezone.utc)
        expires_at = identity.verification_expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if now > expires_at:
            self._users.clear_identity_verification("email", login)
            self._session.commit()
            raise ValidationError("Verification code expired. Please register again.")

        submitted_hash = hashlib.sha256(code.strip().upper().encode("utf-8")).hexdigest()
        if submitted_hash != identity.verification_code_hash:
            attempts_left = self._users.decrement_identity_attempt("email", login)
            if attempts_left <= 0:
                self._users.clear_identity_verification("email", login)
                self._session.commit()
                raise ValidationError("Verification attempts exceeded. Please register again.")
            self._session.commit()
            expires_in = max(0, int((expires_at - now).total_seconds()))
            raise ValidationError(f"Invalid verification code. Attempts left: {attempts_left}, expires in: {expires_in}s")

        self._users.verify_identity("email", login)
        self._session.commit()

    def get_auth_token(self, payload: AuthInput) -> AuthTokenView:
        identity_type = payload.identity_type.strip().lower()
        identifier = payload.identifier.strip().lower()
        identity = self._users.get_identity(identity_type, identifier)
        if identity is None:
            raise ValidationError("Нет такого пользователя или неверный пароль")
        if identity_type == "email":
            if not identity.is_verified:
                raise ValidationError("Email is not verified")
            if identity.secret_hash is None:
                raise ValidationError("Нет такого пользователя или неверный пароль")
            if not verify_password(payload.password_hash, identity.secret_hash):
                raise ValidationError("Нет такого пользователя или неверный пароль")
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

    def count_users(self) -> int:
        return self._users.count_all()

    def count_admins(self) -> int:
        return self._users.count_admins()

    def get_latest_registration_at(self) -> datetime | None:
        return self._users.latest_registered_at()

    def list_users_admin(self) -> list[AdminUserListRow]:
        users = self._users.list_all()
        rows: list[AdminUserListRow] = []
        for u in users:
            identities = self._users.get_identities_by_user(u.id)
            primary_email = next((i.identifier for i in identities if i.identity_type == "email"), None)
            token_count, _ = self._balance.load_wallet(u.id)
            rows.append(
                AdminUserListRow(
                    id=u.id,
                    name=u.name,
                    role=u.role,
                    allow_negative_balance=u.allow_negative_balance,
                    primary_email=primary_email,
                    token_count=token_count,
                )
            )
        return rows

    def update_profile(self, user_id: UUID, payload: UpdateUserInput) -> UserView:
        user = self._users.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User not found")
        new_name = self.normalize_name(payload.name)
        updated = replace(user, name=new_name)
        self._users.save(updated)
        self._session.commit()
        return self._to_user_view(updated)

    def request_password_reset(self, login: str) -> None:
        """Запрос ссылки сброса: одинаковый исход снаружи; письмо только при валидном verified email+пароле."""
        settings = get_settings()
        email_norm = login.strip().lower()
        if not email_norm or "@" not in email_norm or "." not in email_norm.split("@")[-1]:
            return

        now = datetime.now(timezone.utc)
        self._users.record_password_reset_attempt(email_norm)
        self._session.commit()

        window_start = now - timedelta(hours=1)
        if self._users.count_password_reset_attempts_by_email(email_norm, window_start) > settings.password_reset_max_per_email_per_hour:
            return

        identity = self._users.get_identity("email", email_norm)
        if identity is None or not identity.is_verified or identity.secret_hash is None:
            return

        self._users.invalidate_unused_password_reset_tokens(identity.user_id)
        raw = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        expires_at = now + timedelta(seconds=settings.password_reset_ttl_seconds)
        self._users.insert_password_reset_token(identity.user_id, token_hash, expires_at)

        base = (settings.password_reset_public_base_url or "").strip().rstrip("/")
        if base:
            reset_link = f"{base}/reset-password?token={raw}"
        else:
            reset_link = f"/reset-password?token={raw}"
        log.info(
            "password reset link (configure real email provider in production): login=%s link=%s",
            email_norm,
            reset_link,
        )
        self._session.commit()

    def complete_password_reset(self, token: str, new_password: str) -> None:
        if len(new_password) < 8:
            raise ValidationError("Password must be at least 8 characters")
        raw = token.strip()
        if not raw:
            raise ValidationError("Invalid or expired reset link")
        token_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        now = datetime.now(timezone.utc)
        user_id = self._users.try_consume_password_reset_token(token_hash, now)
        if user_id is None:
            raise ValidationError("Invalid or expired reset link")
        try:
            self._users.set_email_identity_password_hash(user_id, hash_password(new_password))
            revoke_access_tokens_for_user(user_id)
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise

    def admin_patch_user(self, user_id: UUID, payload: PatchUserInput) -> UserView:
        """Частичное обновление профиля вызывается только из админских HTTP-ручек."""
        if payload.name is None and payload.allow_negative_balance is None:
            raise ValidationError("No fields to update")
        user = self._users.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User not found")
        new_name = user.name if payload.name is None else self.normalize_name(payload.name)
        new_allow = (
            user.allow_negative_balance
            if payload.allow_negative_balance is None
            else payload.allow_negative_balance
        )
        updated = replace(user, name=new_name, allow_negative_balance=new_allow)
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

