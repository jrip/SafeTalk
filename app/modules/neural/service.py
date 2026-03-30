from __future__ import annotations

from uuid import UUID

from app.modules.neural.interfaces import NeuralInternalService
from app.modules.neural.types import (
    BatchTaskResultView,
    BatchTaskView,
    CreateBatchTaskInput,
    PredictionView,
    RunPredictionInput,
)


class NeuralService(NeuralInternalService):
    def __init__(self) -> None:
        """Сервис Neural без реализации хранения и ML-раннера."""

    def get_toxicity(self, payload: RunPredictionInput) -> PredictionView:
        """Внешний/внутренний метод: получить токсичность диалога."""
        raise NotImplementedError("Neural processing is mocked at this stage")

    def create_batch_task(self, payload: CreateBatchTaskInput) -> BatchTaskView:
        """Внешний/внутренний метод: создать задачу на анализ пачки диалогов."""
        raise NotImplementedError("Batch task creation is mocked at this stage")

    def get_batch_task_result(self, batch_task_id: UUID) -> BatchTaskResultView:
        """Внешний/внутренний метод: получить результат batch-задачи."""
        raise NotImplementedError("Batch task result is mocked at this stage")
