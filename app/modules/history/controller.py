from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from app.modules.history.interfaces import HistoryInternalService
from app.modules.history.types import HistoryView


class HistoryController:
    def __init__(self, service: HistoryInternalService) -> None:
        self._service = service

    def get_user_history(self, user_id: UUID) -> list[HistoryView]:
        """Получить историю запросов к API для пользователя."""
        return self._service.get_api_history(user_id)

    def save_api_request(
        self,
        user_id: UUID,
        request: str,
        result: str,
        *,
        ml_model_id: UUID | None = None,
        ml_task_id: UUID | None = None,
        tokens_charged: Decimal | None = None,
    ) -> None:
        """Сохранить запись истории (вызывается из других модулей при обработке API)."""
        self._service.save_api_request(
            user_id,
            request,
            result,
            ml_model_id=ml_model_id,
            ml_task_id=ml_task_id,
            tokens_charged=tokens_charged,
        )
