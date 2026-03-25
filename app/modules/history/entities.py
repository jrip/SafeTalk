from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from app.core import now_utc


@dataclass
class HistoryRecord:
    """Plain data model for API request history record."""

    user_id: UUID
    request: str
    result: str
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=now_utc)
