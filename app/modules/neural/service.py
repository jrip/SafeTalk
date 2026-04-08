from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.core import NotFoundError, ValidationError
from app.modules.billing.service import BillingService
from app.modules.history.service import HistoryService
from app.modules.neural.entities import MLTask
from app.modules.neural.models import MlPredictionTaskModel
from app.modules.neural.storage_sqlalchemy import SqlAlchemyMlModelCatalog, SqlAlchemyMlTaskStore
from app.modules.neural.types import (
    BatchTaskResultView,
    BatchTaskView,
    CreateBatchTaskInput,
    CreatePredictionTaskView,
    MlTaskDetailView,
    PredictionView,
    RunPredictionInput,
    TaskStatus,
)


def _mock_toxicity_summary(text: str) -> str:
    normalized = text.strip() or " "
    # Детерминированный «скор» 0.10 … 0.99 для демо без реальной модели.
    bucket = abs(hash(normalized)) % 9000
    score = Decimal(bucket) / Decimal(10000) + Decimal("0.10")
    score = score.quantize(Decimal("0.001"))
    is_toxic = score >= Decimal("0.5")
    label = "toxic" if is_toxic else "ok"
    return f"toxicity: {score}; label: {label}"


class NeuralService:
    def __init__(
        self,
        session: Session,
        billing: BillingService,
        ml_models: SqlAlchemyMlModelCatalog,
        history: HistoryService,
        ml_tasks: SqlAlchemyMlTaskStore,
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

        # Синхронный мок-инференс; позже — очередь (RabbitMQ) и воркер.

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

        result_summary = _mock_toxicity_summary(text)
        self._ml_tasks.complete_task(task.id, result_summary)
        self._history.update_result_for_ml_task(
            payload.user_id,
            task.id,
            result_summary,
            commit=False,
        )

        self._session.commit()

        return CreatePredictionTaskView(
            task_id=task.id,
            user_id=payload.user_id,
            model_id=payload.model_id,
            text=text,
            status=TaskStatus.COMPLETED,
            charged_tokens=charge,
            result_summary=result_summary,
        )

    def get_task_for_user(self, user_id: UUID, task_id: UUID) -> MlTaskDetailView:
        row = self._session.get(MlPredictionTaskModel, task_id)
        if row is None or row.user_id != user_id:
            raise NotFoundError("Task not found")
        try:
            st = TaskStatus(row.status)
        except ValueError:
            st = TaskStatus.PENDING
        return MlTaskDetailView(
            task_id=row.id,
            user_id=row.user_id,
            model_id=row.model_id,
            text=row.text,
            status=st,
            charged_tokens=row.charged_tokens,
            created_at=row.created_at,
            result_summary=row.result_summary,
        )

    def get_default_model_id(self) -> UUID:
        meta = self._ml_models.get_default_model_meta()
        if meta is None:
            raise NotFoundError("No active ML model configured")
        return meta.id

    def get_toxicity(self, payload: RunPredictionInput) -> PredictionView:
        raise NotImplementedError("Neural processing is mocked at this stage")

    def create_batch_task(self, payload: CreateBatchTaskInput) -> BatchTaskView:
        raise NotImplementedError("Batch task creation is mocked at this stage")

    def get_batch_task_result(self, batch_task_id: UUID) -> BatchTaskResultView:
        raise NotImplementedError("Batch task result is mocked at this stage")
