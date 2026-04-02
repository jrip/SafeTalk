from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.core import NotFoundError, ValidationError
from app.modules.billing.interfaces import BillingInternalService
from app.modules.history.interfaces import HistoryInternalService
from app.modules.neural.entities import MLTask
from app.modules.neural.interfaces import NeuralInternalService
from app.modules.neural.ports import MlModelCatalog, MlTaskStore
from app.modules.neural.types import (
    BatchTaskResultView,
    BatchTaskView,
    CreateBatchTaskInput,
    CreatePredictionTaskView,
    PredictionView,
    RunPredictionInput,
    TaskStatus,
)


class NeuralService(NeuralInternalService):
    def __init__(
        self,
        session: Session,
        billing: BillingInternalService,
        ml_models: MlModelCatalog,
        history: HistoryInternalService,
        ml_tasks: MlTaskStore,
    ) -> None:
        self._session = session
        self._billing = billing
        self._ml_models = ml_models
        self._history = history
        self._ml_tasks = ml_tasks

    def create_prediction_task(self, payload: RunPredictionInput) -> CreatePredictionTaskView:
        text = payload.text
        if not text or not text.strip():
            raise ValidationError("Task text cannot be empty")

        meta = self._ml_models.get_model_meta(payload.model_id)
        if meta is None or not meta.is_active:
            raise NotFoundError("ML model not found or inactive")

        task = MLTask(user_id=payload.user_id, model_id=payload.model_id, text=text)
        char_count = Decimal(len(text))
        charge = char_count * meta.price_per_character

        state = self._billing.load_balance_state_for_update(payload.user_id)
        if charge > 0:
            self._billing.spend_tokens(
                payload.user_id,
                charge,
                task_id=task.id,
                commit=False,
                locked_state=state,
            )

        # TODO: поставить задачу в очередь (например RabbitMQ) и воркером вызвать инференс модели.

        self._ml_tasks.insert_pending(task, charge)
        self._history.save_api_request(
            payload.user_id,
            text,
            "PENDING",
            ml_model_id=payload.model_id,
            ml_task_id=task.id,
            tokens_charged=charge,
            commit=False,
        )
        self._session.commit()

        return CreatePredictionTaskView(
            task_id=task.id,
            user_id=payload.user_id,
            model_id=payload.model_id,
            status=TaskStatus.PENDING,
            charged_tokens=charge,
        )

    def get_toxicity(self, payload: RunPredictionInput) -> PredictionView:
        raise NotImplementedError("Neural processing is mocked at this stage")

    def create_batch_task(self, payload: CreateBatchTaskInput) -> BatchTaskView:
        raise NotImplementedError("Batch task creation is mocked at this stage")

    def get_batch_task_result(self, batch_task_id: UUID) -> BatchTaskResultView:
        raise NotImplementedError("Batch task result is mocked at this stage")
