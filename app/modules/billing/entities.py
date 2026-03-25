from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from app.core import InsufficientBalanceError, ValidationError, now_utc


@dataclass(frozen=True)
class BalanceState:
    """Balance aggregate used by transaction polymorphism."""

    user_id: UUID
    token_count: Decimal
    allow_negative_balance: bool = False
    updated_at: datetime = field(default_factory=now_utc)


@dataclass
class Transaction(ABC):
    """Base transaction with polymorphic apply behavior."""

    user_id: UUID
    amount: Decimal
    task_id: UUID | None = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=now_utc)

    @abstractmethod
    def apply(self, state: BalanceState) -> BalanceState:
        raise NotImplementedError


@dataclass
class DebitTransaction(Transaction):
    """Debit operation for token balance."""

    def apply(self, state: BalanceState) -> BalanceState:
        if self.amount <= 0:
            raise ValidationError("Debit amount must be positive")
        new_count = state.token_count - self.amount
        if not state.allow_negative_balance and new_count < 0:
            raise InsufficientBalanceError("Insufficient token balance")
        return BalanceState(
            user_id=state.user_id,
            token_count=new_count,
            allow_negative_balance=state.allow_negative_balance,
            updated_at=self.created_at,
        )


@dataclass
class CreditTransaction(Transaction):
    """Credit operation for token balance."""

    def apply(self, state: BalanceState) -> BalanceState:
        if self.amount <= 0:
            raise ValidationError("Credit amount must be positive")
        return BalanceState(
            user_id=state.user_id,
            token_count=state.token_count + self.amount,
            allow_negative_balance=state.allow_negative_balance,
            updated_at=self.created_at,
        )
