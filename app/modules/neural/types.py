from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from uuid import UUID


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class RunPredictionInput:
    user_id: UUID
    model_id: UUID
    text: str


@dataclass(frozen=True)
class PredictionView:
    task_id: UUID
    user_id: UUID
    model_id: UUID
    score: Decimal
    is_toxic: bool
    status: TaskStatus
