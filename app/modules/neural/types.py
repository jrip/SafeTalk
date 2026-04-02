from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from uuid import UUID


@dataclass(frozen=True)
class MlModelMeta:
    """Срез полей каталога ML-моделей, нужный для биллинга задачи."""

    id: UUID
    price_per_character: Decimal
    is_active: bool


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


@dataclass(frozen=True)
class CreateBatchTaskInput:
    user_id: UUID
    model_id: UUID
    dialogs: list[str]


@dataclass(frozen=True)
class BatchTaskView:
    batch_task_id: UUID
    user_id: UUID
    model_id: UUID
    status: TaskStatus
    total_dialogs: int


@dataclass(frozen=True)
class BatchTaskResultView:
    batch_task_id: UUID
    status: TaskStatus
    results: list[PredictionView]


@dataclass(frozen=True)
class CreatePredictionTaskView:
    """Результат постановки ML-задачи (инференс — отдельно, по очереди)."""

    task_id: UUID
    user_id: UUID
    model_id: UUID
    status: TaskStatus
    charged_tokens: Decimal
