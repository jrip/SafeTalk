from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core import now_utc
from app.ml_models.outcomes import ToxicityPrediction
from app.modules.neural.entities import MLTask
from app.modules.neural.models import MlModelModel, MlPredictionTaskModel
from app.modules.neural.types import MlModelCatalogItemView, MlModelMeta, TaskStatus


class SqlAlchemyMlModelCatalog:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_model_meta(self, model_id: UUID) -> MlModelMeta | None:
        row = self._session.get(MlModelModel, model_id)
        if row is None:
            return None
        return MlModelMeta(
            id=row.id,
            price_per_character=row.price_per_character,
            is_active=row.is_active,
        )

    def get_default_model_meta(self) -> MlModelMeta | None:
        row = self._session.scalar(
            select(MlModelModel).where(MlModelModel.is_default.is_(True), MlModelModel.is_active.is_(True))
        )
        if row is None:
            row = self._session.scalar(select(MlModelModel).where(MlModelModel.is_active.is_(True)))
        if row is None:
            return None
        return MlModelMeta(
            id=row.id,
            price_per_character=row.price_per_character,
            is_active=row.is_active,
        )

    def list_active_catalog_items(self) -> list[MlModelCatalogItemView]:
        rows = self._session.scalars(
            select(MlModelModel)
            .where(MlModelModel.is_active.is_(True))
            .order_by(MlModelModel.is_default.desc(), MlModelModel.name.asc())
        ).all()
        return [
            MlModelCatalogItemView(
                id=r.id,
                slug=r.slug,
                name=r.name,
                description=r.description,
                price_per_character=r.price_per_character,
                is_default=r.is_default,
            )
            for r in rows
        ]


class SqlAlchemyMlTaskStore:
    def __init__(self, session: Session) -> None:
        self._session = session

    def insert_pending(self, task: MLTask, charged_tokens: Decimal) -> None:
        self._session.add(
            MlPredictionTaskModel(
                id=task.id,
                user_id=task.user_id,
                model_id=task.model_id,
                text=task.text,
                status=task.status.value,
                charged_tokens=charged_tokens,
            )
        )
        self._session.flush()

    def complete_task(self, task_id: UUID, outcome: ToxicityPrediction) -> datetime | None:
        row = self._session.get(MlPredictionTaskModel, task_id)
        if row is None:
            return None
        done_at = now_utc()
        row.status = TaskStatus.COMPLETED.value
        row.result_summary = outcome.summary
        row.is_toxic = outcome.is_toxic
        row.toxicity_probability = Decimal(str(round(outcome.toxicity_probability, 8)))
        row.toxicity_breakdown = outcome.breakdown
        row.completed_at = done_at
        self._session.flush()
        return done_at

    def count_all(self) -> int:
        return int(self._session.scalar(select(func.count()).select_from(MlPredictionTaskModel)) or 0)

    def count_by_status(self, status: TaskStatus) -> int:
        return int(
            self._session.scalar(
                select(func.count()).select_from(MlPredictionTaskModel).where(MlPredictionTaskModel.status == status.value)
            )
            or 0
        )
