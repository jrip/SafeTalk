from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.config import Base

if TYPE_CHECKING:
    from app.modules.history.models import HistoryRecordModel


class MlModelModel(Base):
    """Каталог ML-моделей (метаданные; инференс — в воркере/очереди)."""

    __tablename__ = "ml_models"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    version: Mapped[str] = mapped_column(String(64), nullable=False, default="1")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    price_per_character: Mapped[Decimal] = mapped_column(
        Numeric(24, 8), nullable=False, default=Decimal("0")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    history_records: Mapped[list[HistoryRecordModel]] = relationship(
        "HistoryRecordModel",
        back_populates="ml_model",
        passive_deletes=True,
    )


class MlPredictionTaskModel(Base):
    """Поставленная пользователем задача на инференс (очередь / воркер — отдельно)."""

    __tablename__ = "ml_prediction_tasks"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    model_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("ml_models.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    result_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    charged_tokens: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    history_records: Mapped[list[HistoryRecordModel]] = relationship(
        "HistoryRecordModel",
        back_populates="ml_prediction_task",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        preview = self.text if len(self.text) <= 48 else f"{self.text[:45]}…"
        return (
            f"MlTask(id={self.id}, model_id={self.model_id}, status={self.status!r}, "
            f"charged={self.charged_tokens}, text={preview!r})"
        )
