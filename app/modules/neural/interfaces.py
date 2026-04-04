from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.modules.neural.types import (
    BatchTaskResultView,
    BatchTaskView,
    CreateBatchTaskInput,
    CreatePredictionTaskView,
    PredictionView,
    RunPredictionInput,
)


class NeuralPublicService(Protocol):
    def get_toxicity(self, payload: RunPredictionInput) -> PredictionView:
        """Внешний метод: получить токсичность диалога."""

    def create_prediction_task(self, payload: RunPredictionInput) -> CreatePredictionTaskView:
        """Создать задачу на предикт: биллинг по длине текста, без запуска модели (очередь — позже)."""

    def create_batch_task(self, payload: CreateBatchTaskInput) -> BatchTaskView:
        """Внешний метод: создать задачу на анализ пачки диалогов."""

    def get_batch_task_result(self, batch_task_id: UUID) -> BatchTaskResultView:
        """Внешний метод: получить результат batch-задачи."""


class NeuralInternalService(NeuralPublicService, Protocol):
    pass
