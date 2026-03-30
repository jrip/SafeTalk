from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class CreateHistoryInput:
    user_id: UUID
    request: str
    result: str


@dataclass(frozen=True)
class HistoryView:
    id: UUID
    user_id: UUID
    request: str
    result: str
    created_at: datetime
