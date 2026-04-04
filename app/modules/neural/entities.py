from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from app.core import now_utc
from app.modules.neural.types import TaskStatus


@dataclass
class MLModel:
    """Plain data model for ML model metadata."""

    name: str
    description: str
    price_per_character: Decimal
    id: UUID = field(default_factory=uuid4)


@dataclass
class MLTask:
    """Plain data model for ML task."""

    user_id: UUID
    model_id: UUID
    text: str
    id: UUID = field(default_factory=uuid4)
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=now_utc)


@dataclass
class PredictionResult:
    """Plain data model for toxicity prediction result."""

    task_id: UUID
    score: Decimal
    is_toxic: bool
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=now_utc)
