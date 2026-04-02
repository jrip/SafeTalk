from __future__ import annotations

from decimal import Decimal
from typing import Protocol
from uuid import UUID

from app.modules.neural.entities import MLTask
from app.modules.neural.types import MlModelMeta


class MlModelCatalog(Protocol):
    def get_model_meta(self, model_id: UUID) -> MlModelMeta | None: ...


class MlTaskStore(Protocol):
    def insert_pending(self, task: MLTask, charged_tokens: Decimal) -> None:
        """Добавить строку задачи (статус pending); без commit."""
