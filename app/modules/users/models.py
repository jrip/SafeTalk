from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Uuid, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.config import Base

if TYPE_CHECKING:
    from app.modules.billing.models import BalanceLedgerEntryModel, UserBalanceModel
    from app.modules.feedback.models import FeedbackModel
    from app.modules.history.models import HistoryRecordModel


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(64), nullable=False, default="user")
    allow_negative_balance: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    balance: Mapped[UserBalanceModel | None] = relationship(
        "UserBalanceModel",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    ledger_entries: Mapped[list[BalanceLedgerEntryModel]] = relationship(
        "BalanceLedgerEntryModel",
        back_populates="user",
        passive_deletes=True,
    )
    history_records: Mapped[list[HistoryRecordModel]] = relationship(
        "HistoryRecordModel",
        back_populates="user",
        passive_deletes=True,
    )
    feedback_items: Mapped[list[FeedbackModel]] = relationship(
        "FeedbackModel",
        back_populates="user",
        passive_deletes=True,
    )
    identities: Mapped[list[UserIdentityModel]] = relationship(
        "UserIdentityModel",
        back_populates="user",
        passive_deletes=True,
        cascade="all, delete-orphan",
    )


class UserIdentityModel(Base):
    __tablename__ = "user_identities"
    __table_args__ = (
        UniqueConstraint("identity_type", "identifier", name="uq_user_identities_type_identifier"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    identity_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    identifier: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    secret_hash: Mapped[str | None] = mapped_column(String(512), nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    verification_code_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    verification_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verification_attempts_left: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user: Mapped[UserModel] = relationship("UserModel", back_populates="identities")


class PasswordResetAttemptModel(Base):
    """Учёт запросов сброса пароля для rate limit (по email)."""

    __tablename__ = "password_reset_attempts"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email_normalized: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class PasswordResetTokenModel(Base):
    """Одноразовый токен сброса пароля (в БД только SHA-256 от raw token)."""

    __tablename__ = "password_reset_tokens"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
