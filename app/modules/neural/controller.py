from __future__ import annotations

from uuid import UUID

from app.modules.neural.interfaces import NeuralPublicService
from app.modules.neural.types import (
    BatchTaskResultView,
    BatchTaskView,
    CreateBatchTaskInput,
    CreatePredictionTaskView,
    PredictionView,
    RunPredictionInput,
)


class NeuralController:
    def __init__(self, service: NeuralPublicService) -> None:
        self._service = service

    def get_toxicity(self, payload: RunPredictionInput) -> PredictionView:
        """Получить токсичность одного диалога."""
        return self._service.get_toxicity(payload)

    def create_prediction_task(self, payload: RunPredictionInput) -> CreatePredictionTaskView:
        """Создать ML-задачу: проверка баланса, списание по числу символов."""
        return self._service.create_prediction_task(payload)

    def create_batch_task(self, payload: CreateBatchTaskInput) -> BatchTaskView:
        """Создать задачу на анализ пачки диалогов."""
        return self._service.create_batch_task(payload)

    def get_batch_task_result(self, batch_task_id: UUID) -> BatchTaskResultView:
        """Получить результат batch-задачи по идентификатору."""
        return self._service.get_batch_task_result(batch_task_id)
