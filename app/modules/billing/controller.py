from __future__ import annotations

from uuid import UUID

from app.modules.billing.interfaces import BillingPublicService
from app.modules.billing.types import BalanceView


class BillingController:
    def __init__(self, service: BillingPublicService) -> None:
        self._service = service

    def get_available_tokens(self, user_id: UUID) -> BalanceView:
        """Получить количество доступных токенов."""
        return self._service.get_count_tokens(user_id)
