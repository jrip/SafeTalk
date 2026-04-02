from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.neural.entities import MLTask
from app.modules.neural.models import MlModelModel, MlPredictionTaskModel
from app.modules.neural.ports import MlModelCatalog, MlTaskStore
from app.modules.neural.types import MlModelMeta


class SqlAlchemyMlModelCatalog(MlModelCatalog):
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


class SqlAlchemyMlTaskStore(MlTaskStore):
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
