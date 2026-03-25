from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class CreateFeedbackInput:
    history_id: UUID
    user_id: UUID
    is_toxic: bool
    comment: str = ""


@dataclass(frozen=True)
class FeedbackView:
    id: UUID
    history_id: UUID
    user_id: UUID
    is_toxic: bool
    comment: str
    created_at: datetime
