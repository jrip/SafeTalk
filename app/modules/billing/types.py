from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True)
class BalanceView:
    user_id: UUID
    token_count: Decimal


@dataclass(frozen=True)
class SpendTokensInput:
    user_id: UUID
    count: Decimal
    task_id: UUID | None = None
