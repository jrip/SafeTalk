from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID


@dataclass(frozen=True)
class MlModelMeta:
    """Срез полей каталога ML-моделей, нужный для биллинга задачи."""

    id: UUID
    price_per_character: Decimal
    is_active: bool


@dataclass(frozen=True)
class MlModelCatalogItemView:
    """Публичное описание модели для REST (каталог)."""

    id: UUID
    slug: str
    name: str
    description: str
    price_per_character: Decimal
    is_default: bool


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
    task_id: UUID
    user_id: UUID
    model_id: UUID
    text: str
    status: TaskStatus
    charged_tokens: Decimal
    result_summary: str | None = None
    completed_at: datetime | None = None
    is_toxic: bool | None = None
    toxicity_probability: Decimal | None = None
    toxicity_breakdown: dict[str, float] | None = None


@dataclass(frozen=True)
class MlTaskDetailView:
    task_id: UUID
    user_id: UUID
    model_id: UUID
    text: str
    status: TaskStatus
    charged_tokens: Decimal
    created_at: datetime
    completed_at: datetime | None
    result_summary: str | None
    is_toxic: bool | None = None
    toxicity_probability: Decimal | None = None
    toxicity_breakdown: dict[str, float] | None = None
