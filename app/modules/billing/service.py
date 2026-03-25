from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from app.modules.billing.interfaces import BillingInternalService
from app.modules.billing.types import BalanceView


class BillingService(BillingInternalService):
    """Сервис учета расхода токенов."""

    def __init__(self) -> None:
        """Сервис Billing без реализации хранения (на этапе проектирования)."""

    def get_count_tokens(self, user_id: UUID) -> BalanceView:
        """Внешний метод: получить текущий баланс токенов."""
        raise NotImplementedError("Balance lookup is mocked at this stage")

    def spend_tokens(self, user_id: UUID, count: Decimal, task_id: UUID | None = None) -> BalanceView:
        """Внутренний метод: списать токены за ML-задачу или внутреннюю операцию."""
        raise NotImplementedError("Token spending is mocked at this stage")
