from __future__ import annotations

from decimal import Decimal
from typing import Protocol
from uuid import UUID

from app.modules.history.entities import HistoryRecord
from app.modules.history.types import HistoryView


class HistoryStore(Protocol):
    def list_for_user(self, user_id: UUID) -> list[HistoryView]: ...

    def append(
        self,
        user_id: UUID,
        request: str,
        result: str,
        *,
        ml_model_id: UUID | None = None,
        ml_task_id: UUID | None = None,
        tokens_charged: Decimal | None = None,
    ) -> None: ...

    def get_own_record(self, user_id: UUID, record_id: UUID) -> HistoryRecord | None: ...
