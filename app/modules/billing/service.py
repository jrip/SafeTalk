from __future__ import annotations

from decimal import Decimal
from typing import Dict
from uuid import UUID

from app.modules.billing.entities import BalanceState, DebitTransaction, Transaction
from app.modules.billing.interfaces import BillingInternalService
from app.modules.billing.types import BalanceView


class BillingService(BillingInternalService):
    """Сервис учета расхода токенов."""

    def __init__(self) -> None:
        """Сервис Billing с mock-состоянием без реального хранилища."""
        self._mock_balances: Dict[UUID, BalanceState] = {}

    def get_count_tokens(self, user_id: UUID) -> BalanceView:
        """Внешний метод: получить текущий баланс токенов."""
        state = self._mock_balances.get(
            user_id,
            BalanceState(user_id=user_id, token_count=Decimal("0")),
        )
        return BalanceView(user_id=state.user_id, token_count=state.token_count)

    def spend_tokens(self, user_id: UUID, count: Decimal, task_id: UUID | None = None) -> BalanceView:
        """Внутренний метод: списать токены за ML-задачу или внутреннюю операцию."""
        state = self._mock_balances.get(
            user_id,
            BalanceState(user_id=user_id, token_count=Decimal("0")),
        )
        tx = DebitTransaction(user_id=user_id, amount=count, task_id=task_id)
        updated = self._apply_transaction(state, tx)
        return BalanceView(user_id=updated.user_id, token_count=updated.token_count)

    def _apply_transaction(self, state: BalanceState, tx: Transaction) -> BalanceState:
        """Единая точка применения транзакции к балансу (полиморфизм)."""
        updated = tx.apply(state)
        self._mock_balances[updated.user_id] = updated
        return updated
