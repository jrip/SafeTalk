from __future__ import annotations

from uuid import UUID

from app.modules.history.interfaces import HistoryPublicService
from app.modules.history.types import HistoryView


class HistoryController:
    def __init__(self, service: HistoryPublicService) -> None:
        self._service = service

    def get_user_history(self, user_id: UUID) -> list[HistoryView]:
        """Получить историю запросов к API для пользователя."""
        return self._service.get_api_history(user_id)
