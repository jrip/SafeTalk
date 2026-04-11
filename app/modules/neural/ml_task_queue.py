from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any
from uuid import UUID

import pika
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.exceptions import DomainError
from app.core.settings import get_settings
from app.db.database import SessionLocal
from app.modules.history.service import HistoryService
from app.modules.history.storage_sqlalchemy import SqlAlchemyHistoryStore
from app.bootstrap import build_user_and_billing
from app.modules.neural.models import MlPredictionTaskModel
from app.modules.neural.storage_sqlalchemy import SqlAlchemyMlTaskStore
from app.modules.neural.types import TaskStatus

logger = logging.getLogger(__name__)


class MlTaskCompleteFailedError(DomainError):
    pass


class MlTaskMessageRejectedError(Exception):
    """Сообщение очереди не согласуется с задачей в БД — обработку нужно повторить или снять по политике."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class MlTaskAlreadyDoneError(Exception):
    """Задача в БД уже не в PENDING — дубликат доставки, повторно писать не нужно."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class MlPredictionFeatures(BaseModel):
    text: str = Field(min_length=1)


class MlPredictionQueuePayload(BaseModel):
    task_id: UUID
    features: MlPredictionFeatures
    model: UUID
    timestamp: datetime


def publish_ml_prediction_payload(payload: dict[str, Any]) -> None:
    settings = get_settings()
    url = settings.rabbitmq_url
    if not url:
        raise RuntimeError("Broker URL is not configured (RABBITMQ_HOST)")
    queue = settings.RABBITMQ_QUEUE_NAME
    body = json.dumps(payload, default=str).encode("utf-8")
    params = pika.URLParameters(url)
    conn = pika.BlockingConnection(params)
    try:
        ch = conn.channel()
        ch.queue_declare(queue=queue, durable=True)
        ch.basic_publish(
            exchange="",
            routing_key=queue,
            body=body,
            properties=pika.BasicProperties(
                content_type="application/json",
                delivery_mode=2,
            ),
        )
        tid = payload.get("task_id")
        logger.info(
            "в очередь RabbitMQ отправлено сообщение: очередь=%s task_id=%s размер_тела=%s байт",
            queue,
            tid,
            len(body),
        )
    finally:
        conn.close()


def complete_ml_task_from_queue_message(
    msg: MlPredictionQueuePayload,
    *,
    worker_id: str | None = None,
) -> None:
    db = SessionLocal()
    wid = worker_id or "неизвестен"
    try:
        _complete_in_session(db, msg, worker_id=worker_id)
        db.commit()
        logger.info(
            "транзакция БД зафиксирована, задача обработана: task_id=%s worker_id=%s",
            msg.task_id,
            wid,
        )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _complete_in_session(
    db: Session,
    msg: MlPredictionQueuePayload,
    *,
    worker_id: str | None = None,
) -> None:
    from app.modules.neural.service import _mock_toxicity_summary

    wid = worker_id or "неизвестен"
    logger.info(
        "начало обработки ML-задачи из очереди: worker_id=%s task_id=%s model=%s ts=%s длина_текста=%s",
        wid,
        msg.task_id,
        msg.model,
        msg.timestamp,
        len(msg.features.text),
    )

    row = db.get(MlPredictionTaskModel, msg.task_id)
    if row is None:
        logger.error(
            "задача в БД не найдена (сообщение нельзя считать выполненным): worker_id=%s task_id=%s",
            wid,
            msg.task_id,
        )
        raise MlTaskMessageRejectedError(
            f"задача не найдена в БД: task_id={msg.task_id}",
        )
    if row.status != TaskStatus.PENDING.value:
        logger.info(
            "задача уже не в статусе PENDING — дубликат доставки, запись в БД не меняем: "
            "worker_id=%s task_id=%s status=%s",
            wid,
            msg.task_id,
            row.status,
        )
        raise MlTaskAlreadyDoneError(
            f"задача уже обработана, status={row.status!r}",
        )

    if row.model_id != msg.model:
        logger.error(
            "несовпадение model_id в сообщении и в БД: worker_id=%s task_id=%s в_сообщении=%s в_бд=%s",
            wid,
            msg.task_id,
            msg.model,
            row.model_id,
        )
        raise MlTaskMessageRejectedError(
            f"несовпадение model_id: в сообщении {msg.model}, в БД {row.model_id}",
        )

    if msg.features.text != row.text:
        logger.error(
            "несовпадение текста в сообщении и в строке задачи: worker_id=%s task_id=%s",
            wid,
            msg.task_id,
        )
        raise MlTaskMessageRejectedError("несовпадение текста задачи с сообщением в очереди")

    result_summary = _mock_toxicity_summary(row.text)
    logger.info(
        "mock-предсказание выполнено: worker_id=%s task_id=%s результат=%s статус=success",
        wid,
        msg.task_id,
        result_summary,
    )

    ml_store = SqlAlchemyMlTaskStore(db)
    done_at = ml_store.complete_task(msg.task_id, result_summary)
    if done_at is None:
        logger.error(
            "complete_task не обновил строку: worker_id=%s task_id=%s user_id=%s",
            wid,
            msg.task_id,
            row.user_id,
        )
        raise MlTaskCompleteFailedError(f"ml_prediction_tasks row missing: {msg.task_id}")
    row_after = db.get(MlPredictionTaskModel, msg.task_id)
    if row_after is not None and row_after.charged_tokens > 0:
        _, billing = build_user_and_billing(db)
        billing.spend_tokens(
            row_after.user_id,
            row_after.charged_tokens,
            task_id=row_after.id,
            commit=False,
            force_allow_negative=True,
        )
        logger.info(
            "списание токенов после ML: worker_id=%s task_id=%s user_id=%s токенов=%s",
            wid,
            msg.task_id,
            row_after.user_id,
            row_after.charged_tokens,
        )

    history_store = SqlAlchemyHistoryStore(db)
    history = HistoryService(history_store, db)
    history.update_result_for_ml_task(
        row.user_id,
        msg.task_id,
        result_summary,
        tokens_charged=row.charged_tokens,
        commit=False,
    )
    logger.info(
        "история и результат записаны в сессию (до commit): worker_id=%s task_id=%s completed_at=%s",
        wid,
        msg.task_id,
        done_at,
    )
