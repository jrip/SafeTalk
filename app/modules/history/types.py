from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True)
class CreateHistoryInput:
    user_id: UUID
    request: str
    result: str
    ml_model_id: UUID | None = None
    ml_task_id: UUID | None = None
    tokens_charged: Decimal | None = None


@dataclass(frozen=True)
class HistoryView:
    id: UUID
    user_id: UUID
    request: str
    result: str
    created_at: datetime
    ml_model_id: UUID | None = None
    ml_task_id: UUID | None = None
    tokens_charged: Decimal | None = None
