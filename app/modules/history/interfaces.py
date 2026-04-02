from __future__ import annotations

from decimal import Decimal
from typing import Protocol
from uuid import UUID

from app.modules.history.types import HistoryView


class HistoryPublicService(Protocol):
    def get_api_history(self, user_id: UUID) -> list[HistoryView]:
        """Внешний метод: получить историю запросов к API."""


class HistoryInternalService(HistoryPublicService, Protocol):
    def save_api_request(
        self,
        user_id: UUID,
        request: str,
        result: str,
        *,
        ml_model_id: UUID | None = None,
        ml_task_id: UUID | None = None,
        tokens_charged: Decimal | None = None,
        commit: bool = True,
    ) -> None:
        """Внутренний публичный метод: сохранить запрос к API."""
