from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Numeric, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.config import Base

if TYPE_CHECKING:
    from app.modules.feedback.models import FeedbackModel
    from app.modules.neural.models import MlModelModel, MlPredictionTaskModel
    from app.modules.users.models import UserModel


class HistoryRecordModel(Base):
    __tablename__ = "history_records"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ml_model_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("ml_models.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    ml_task_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("ml_prediction_tasks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    request: Mapped[str] = mapped_column(Text, nullable=False)
    result: Mapped[str] = mapped_column(Text, nullable=False)
    tokens_charged: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user: Mapped[UserModel] = relationship("UserModel", back_populates="history_records")
    ml_model: Mapped[MlModelModel | None] = relationship("MlModelModel", back_populates="history_records")
    ml_prediction_task: Mapped[MlPredictionTaskModel | None] = relationship(
        "MlPredictionTaskModel",
        back_populates="history_records",
    )
    feedback_items: Mapped[list[FeedbackModel]] = relationship(
        "FeedbackModel",
        back_populates="history_record",
        passive_deletes=True,
    )
