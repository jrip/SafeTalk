from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, DateTime, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.config import Base

if TYPE_CHECKING:
    from app.modules.billing.models import BalanceLedgerEntryModel, UserBalanceModel
    from app.modules.feedback.models import FeedbackModel
    from app.modules.history.models import HistoryRecordModel


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
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
