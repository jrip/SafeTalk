from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from app.modules.billing.interfaces import BillingInternalService
from app.modules.billing.types import BalanceLedgerEntryView, BalanceView


class BillingController:
    def __init__(self, service: BillingInternalService) -> None:
        self._service = service

    def get_available_tokens(self, user_id: UUID) -> BalanceView:
        """Получить количество доступных токенов."""
        return self._service.get_count_tokens(user_id)

    def get_ledger_history(self, user_id: UUID) -> list[BalanceLedgerEntryView]:
        """Журнал пополнений и списаний пользователя (новые сверху)."""
        return self._service.get_ledger_history(user_id)

    def add_tokens(self, user_id: UUID, count: Decimal, task_id: UUID | None = None) -> BalanceView:
        """Пополнить баланс."""
        return self._service.add_tokens(user_id, count, task_id=task_id)

    def spend_tokens(self, user_id: UUID, count: Decimal, task_id: UUID | None = None) -> BalanceView:
        """Списать токены."""
        return self._service.spend_tokens(user_id, count, task_id=task_id)
