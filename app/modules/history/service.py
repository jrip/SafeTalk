from __future__ import annotations

from uuid import UUID

from app.modules.history.interfaces import HistoryInternalService
from app.modules.history.types import HistoryView


class HistoryService(HistoryInternalService):
    def __init__(self) -> None:
        """Сервис History без реализации хранения (на этапе проектирования)."""

    def get_api_history(self, user_id: UUID) -> list[HistoryView]:
        """Внешний метод: получить историю API-запросов пользователя."""
        raise NotImplementedError("History retrieval is mocked at this stage")

    def save_api_request(self, user_id: UUID, request: str, result: str) -> None:
        """Внутренний публичный метод: сохранить запрос к API."""
        raise NotImplementedError("History persistence is mocked at this stage")
