from __future__ import annotations

import logging
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.core import NotFoundError, ValidationError, now_utc
from app.modules.billing.service import BillingService
from app.modules.history.service import HistoryService
from app.core.settings import get_settings
from app.modules.neural.entities import MLTask
from app.modules.neural.models import MlPredictionTaskModel
from app.modules.neural.ml_task_queue import (
    MlPredictionFeatures,
    MlPredictionQueuePayload,
    MlTaskCompleteFailedError,
    publish_ml_prediction_payload,
)
from app.ml_models.constants import ML_MODEL_TOXIC_LITE_ID
from app.modules.neural.storage_sqlalchemy import SqlAlchemyMlModelCatalog, SqlAlchemyMlTaskStore
from app.modules.neural.toxicity_pipeline import toxicity_predict
from app.modules.neural.types import (
    BatchTaskResultView,
    BatchTaskView,
    CreateBatchTaskInput,
    CreatePredictionTaskView,
    MlModelCatalogItemView,
    MlTaskDetailView,
    PredictionView,
    RunPredictionInput,
    TaskStatus,
)


logger = logging.getLogger(__name__)


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

        if payload.model_id == ML_MODEL_TOXIC_LITE_ID:
            raise ValidationError(
                "Модель «Toxicity lite» пока не поддерживается API; выберите основную модель токсичности.",
            )

        task = MLTask(user_id=payload.user_id, model_id=payload.model_id, text=text)
        char_count = Decimal(len(text))
        charge = char_count * meta.price_per_character

        self._ml_tasks.insert_pending(task, charge)
        self._history.save_api_request(
            payload.user_id,
            text,
            "PENDING",
            ml_model_id=payload.model_id,
            ml_task_id=task.id,
            tokens_charged=None,
            commit=False,
        )

        settings = get_settings()
        if settings.rabbitmq_url:
            qmsg = MlPredictionQueuePayload(
                task_id=task.id,
                features=MlPredictionFeatures(text=text),
                model=payload.model_id,
                timestamp=now_utc().replace(microsecond=0),
            )
            publish_ml_prediction_payload(qmsg.model_dump(mode="json"))
            self._session.commit()
            return CreatePredictionTaskView(
                task_id=task.id,
                user_id=payload.user_id,
                model_id=payload.model_id,
                text=text,
                status=TaskStatus.PENDING,
                charged_tokens=charge,
                result_summary=None,
                completed_at=None,
                is_toxic=None,
                toxicity_probability=None,
                toxicity_breakdown=None,
            )

        outcome = toxicity_predict(text, model_id=payload.model_id)
        done_at = self._ml_tasks.complete_task(task.id, outcome)
        if done_at is None:
            logger.error(
                "complete_task returned no row (task_id=%s user_id=%s)",
                task.id,
                payload.user_id,
            )
            raise MlTaskCompleteFailedError(f"ml_prediction_tasks row missing: {task.id}")
        row = self._session.get(MlPredictionTaskModel, task.id)
        if row is not None and row.charged_tokens > 0:
            self._billing.spend_tokens(
                row.user_id,
                row.charged_tokens,
                task_id=row.id,
                commit=False,
                force_allow_negative=True,
            )
        self._history.update_result_for_ml_task(
            payload.user_id,
            task.id,
            outcome.summary,
            tokens_charged=charge,
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
            result_summary=outcome.summary,
            completed_at=done_at,
            is_toxic=outcome.is_toxic,
            toxicity_probability=Decimal(str(round(outcome.toxicity_probability, 8))),
            toxicity_breakdown=outcome.breakdown,
        )

    def get_task_for_user(self, user_id: UUID, task_id: UUID) -> MlTaskDetailView:
        row = self._session.get(MlPredictionTaskModel, task_id)
        if row is None or row.user_id != user_id:
            raise NotFoundError("Task not found")
        try:
            st = TaskStatus(row.status)
        except ValueError:
            st = TaskStatus.PENDING
        bd = row.toxicity_breakdown
        if bd is not None and not isinstance(bd, dict):
            bd = None
        return MlTaskDetailView(
            task_id=row.id,
            user_id=row.user_id,
            model_id=row.model_id,
            text=row.text,
            status=st,
            charged_tokens=row.charged_tokens,
            created_at=row.created_at,
            completed_at=row.completed_at,
            result_summary=row.result_summary,
            is_toxic=row.is_toxic,
            toxicity_probability=row.toxicity_probability,
            toxicity_breakdown=bd,
        )

    def get_default_model_id(self) -> UUID:
        meta = self._ml_models.get_default_model_meta()
        if meta is None:
            raise NotFoundError("No active ML model configured")
        return meta.id

    def list_catalog_models(self) -> list[MlModelCatalogItemView]:
        return self._ml_models.list_active_catalog_items()

    def get_toxicity(self, payload: RunPredictionInput) -> PredictionView:
        raise NotImplementedError("Neural processing is mocked at this stage")

    def create_batch_task(self, payload: CreateBatchTaskInput) -> BatchTaskView:
        raise NotImplementedError("Batch task creation is mocked at this stage")

    def get_batch_task_result(self, batch_task_id: UUID) -> BatchTaskResultView:
        raise NotImplementedError("Batch task result is mocked at this stage")
