from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from app.modules.billing.entities import BalanceState, Transaction
from app.modules.billing.types import BalanceLedgerEntryView


class BalanceStore(Protocol):
    def ensure_wallet(self, user_id: UUID) -> None:
        """Создать строку баланса с нулём, если ещё нет (идемпотентно)."""

    def load_wallet(self, user_id: UUID) -> tuple[Decimal, datetime]:
        """Сумма на кошельке и updated_at; если строки нет — ноль и текущее время."""

    def load_wallet_for_update(self, user_id: UUID) -> tuple[Decimal, datetime]:
        """Кошелёк под блокировкой строки (вызвать после ensure_wallet)."""

    def persist_after_transaction(self, state: BalanceState, tx: Transaction) -> None:
        """Сохранить новый баланс и записать операцию в журнал."""

    def list_ledger_for_user(self, user_id: UUID) -> list[BalanceLedgerEntryView]:
        """Все записи журнала пользователя, новые операции первыми."""
