from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import now_utc
from app.modules.billing.entities import BalanceState, CreditTransaction, DebitTransaction, Transaction
from app.modules.billing.models import BalanceLedgerEntryModel, UserBalanceModel
from app.modules.billing.ports import BalanceStore
from app.modules.billing.types import BalanceLedgerEntryView


class SqlAlchemyBalanceStore(BalanceStore):
    def __init__(self, session: Session) -> None:
        self._session = session

    def ensure_wallet(self, user_id: UUID) -> None:
        if self._session.get(UserBalanceModel, user_id) is not None:
            return
        self._session.add(UserBalanceModel(user_id=user_id, token_count=Decimal("0")))
        self._session.flush()

    def load_wallet(self, user_id: UUID) -> tuple[Decimal, datetime]:
        bal = self._session.get(UserBalanceModel, user_id)
        if bal is None:
            return Decimal("0"), now_utc()
        return bal.token_count, bal.updated_at

    def load_wallet_for_update(self, user_id: UUID) -> tuple[Decimal, datetime]:
        self.ensure_wallet(user_id)
        bal = self._session.get(UserBalanceModel, user_id, with_for_update=True)
        if bal is None:
            return Decimal("0"), now_utc()
        return bal.token_count, bal.updated_at

    def persist_after_transaction(self, state: BalanceState, tx: Transaction) -> None:
        bal = self._session.get(UserBalanceModel, state.user_id)
        if bal is None:
            bal = UserBalanceModel(user_id=state.user_id, token_count=state.token_count, updated_at=state.updated_at)
            self._session.add(bal)
        else:
            bal.token_count = state.token_count
            bal.updated_at = state.updated_at

        if isinstance(tx, DebitTransaction):
            kind = "debit"
        elif isinstance(tx, CreditTransaction):
            kind = "credit"
        else:
            raise TypeError(f"Unsupported transaction type: {type(tx)!r}")

        self._session.add(
            BalanceLedgerEntryModel(
                id=tx.id,
                user_id=tx.user_id,
                kind=kind,
                amount=tx.amount,
                task_id=tx.task_id,
                created_at=tx.created_at,
            )
        )
        self._session.flush()

    def list_ledger_for_user(self, user_id: UUID) -> list[BalanceLedgerEntryView]:
        stmt = (
            select(BalanceLedgerEntryModel)
            .where(BalanceLedgerEntryModel.user_id == user_id)
            .order_by(BalanceLedgerEntryModel.created_at.desc(), BalanceLedgerEntryModel.id.desc())
        )
        rows = self._session.scalars(stmt).all()
        return [
            BalanceLedgerEntryView(
                id=r.id,
                user_id=r.user_id,
                kind=r.kind,
                amount=r.amount,
                task_id=r.task_id,
                created_at=r.created_at,
            )
            for r in rows
        ]

    def list_ledger_for_user(self, user_id: UUID) -> list[BalanceLedgerEntryView]:
        stmt = (
            select(BalanceLedgerEntryModel)
            .where(BalanceLedgerEntryModel.user_id == user_id)
            .order_by(BalanceLedgerEntryModel.created_at.desc(), BalanceLedgerEntryModel.id.desc())
        )
        rows = self._session.scalars(stmt).all()
        return [
            BalanceLedgerEntryView(
                id=r.id,
                user_id=r.user_id,
                kind=r.kind,
                amount=r.amount,
                task_id=r.task_id,
                created_at=r.created_at,
            )
            for r in rows
        ]
