from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from app.core import now_utc


@dataclass
class Transaction:
    """Plain data model for billing transaction."""

    user_id: UUID
    amount: Decimal
    task_id: UUID | None = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=now_utc)


@dataclass
class DebitTransaction(Transaction):
    """Plain debit transaction model."""


@dataclass
class CreditTransaction(Transaction):
    """Plain credit transaction model."""
