from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.billing.entities import BalanceState, CreditTransaction, DebitTransaction, Transaction
from app.modules.billing.interfaces import BillingInternalService
from app.modules.billing.ports import BalanceStore
from app.modules.billing.types import BalanceLedgerEntryView, BalanceView
from app.modules.users.interfaces import UsersPublicService


class BillingService(BillingInternalService):
    """Сервис учёта токенов; баланс и журнал в таблицах billing.*."""

    def __init__(self, users: UsersPublicService, balance: BalanceStore, session: Session) -> None:
        self._users = users
        self._balance = balance
        self._session = session

    def _balance_state(self, user_id: UUID) -> BalanceState:
        profile = self._users.get_profile(user_id)
        token_count, updated_at = self._balance.load_wallet(user_id)
        return BalanceState(
            user_id=user_id,
            token_count=token_count,
            allow_negative_balance=profile.allow_negative_balance,
            updated_at=updated_at,
        )

    def get_count_tokens(self, user_id: UUID) -> BalanceView:
        state = self._balance_state(user_id)
        return BalanceView(user_id=state.user_id, token_count=state.token_count)

    def get_ledger_history(self, user_id: UUID) -> list[BalanceLedgerEntryView]:
        self._users.get_profile(user_id)
        return self._balance.list_ledger_for_user(user_id)

    def load_balance_state_for_update(self, user_id: UUID) -> BalanceState:
        profile = self._users.get_profile(user_id)
        token_count, updated_at = self._balance.load_wallet_for_update(user_id)
        return BalanceState(
            user_id=user_id,
            token_count=token_count,
            allow_negative_balance=profile.allow_negative_balance,
            updated_at=updated_at,
        )

    def add_tokens(
        self,
        user_id: UUID,
        count: Decimal,
        task_id: UUID | None = None,
        *,
        commit: bool = True,
    ) -> BalanceView:
        state = self._balance_state(user_id)
        tx = CreditTransaction(user_id=user_id, amount=count, task_id=task_id)
        updated = self._apply_transaction(state, tx)
        if commit:
            self._session.commit()
        return BalanceView(user_id=updated.user_id, token_count=updated.token_count)

    def spend_tokens(
        self,
        user_id: UUID,
        count: Decimal,
        task_id: UUID | None = None,
        *,
        commit: bool = True,
        locked_state: BalanceState | None = None,
    ) -> BalanceView:
        state = locked_state if locked_state is not None else self._balance_state(user_id)
        if state.user_id != user_id:
            raise ValueError("locked_state.user_id does not match user_id")
        tx = DebitTransaction(user_id=user_id, amount=count, task_id=task_id)
        updated = self._apply_transaction(state, tx)
        if commit:
            self._session.commit()
        return BalanceView(user_id=updated.user_id, token_count=updated.token_count)

    def _apply_transaction(self, state: BalanceState, tx: Transaction) -> BalanceState:
        updated = tx.apply(state)
        self._balance.persist_after_transaction(updated, tx)
        return updated
