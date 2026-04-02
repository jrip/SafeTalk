from __future__ import annotations

from decimal import Decimal
from typing import Protocol
from uuid import UUID

from app.modules.billing.entities import BalanceState
from app.modules.billing.types import BalanceView


class BillingPublicService(Protocol):
    def get_count_tokens(self, user_id: UUID) -> BalanceView:
        """Внешний метод: получить количество доступных токенов."""

    def add_tokens(
        self,
        user_id: UUID,
        count: Decimal,
        task_id: UUID | None = None,
        *,
        commit: bool = True,
    ) -> BalanceView:
        """Пополнить баланс токенов."""


class BillingInternalService(BillingPublicService, Protocol):
    def load_balance_state_for_update(self, user_id: UUID) -> BalanceState:
        """Баланс и флаг allow_negative под блокировкой строки кошелька."""

    def spend_tokens(
        self,
        user_id: UUID,
        count: Decimal,
        task_id: UUID | None = None,
        *,
        commit: bool = True,
        locked_state: BalanceState | None = None,
    ) -> BalanceView:
        """Списать токены. При locked_state повторный SELECT не выполняется (уже под FOR UPDATE)."""
