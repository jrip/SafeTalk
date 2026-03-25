from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from app.core import now_utc


@dataclass
class Feedback:
    """Plain data model for feedback on prediction result."""

    history_id: UUID
    user_id: UUID
    is_toxic: bool
    comment: str = ""
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=now_utc)
