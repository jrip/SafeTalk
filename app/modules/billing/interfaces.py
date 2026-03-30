from __future__ import annotations

from decimal import Decimal
from typing import Protocol
from uuid import UUID

from app.modules.billing.types import BalanceView


class BillingPublicService(Protocol):
    def get_count_tokens(self, user_id: UUID) -> BalanceView:
        """Внешний метод: получить количество доступных токенов."""


class BillingInternalService(BillingPublicService, Protocol):
    def spend_tokens(self, user_id: UUID, count: Decimal, task_id: UUID | None = None) -> BalanceView:
        """Внутренний метод: списать токены (spendTokens)."""
