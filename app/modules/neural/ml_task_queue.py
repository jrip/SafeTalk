from __future__ import annotations

import json
import logging
import time
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

_TEXT_PREVIEW_MAX = 500


def text_preview_for_log(text: str, max_len: int = _TEXT_PREVIEW_MAX) -> str:
    """Укороченный фрагмент для логов (без заливки консоли целым диалогом)."""
    t = text.replace("\n", " ↵ ")
    if len(t) <= max_len:
        return t
    return t[: max_len - 1] + "…"


def _settings_fingerprint() -> str:
    """Без паролей: чтобы в логах сироты сразу видеть, в какую БД/Rabbit смотрит воркер."""
    s = get_settings()
    explicit_db_url = bool((s.database_url or "").strip())
    return (
        f"db_host={s.DB_HOST!r} db_port={s.DB_PORT!r} db_name={s.DB_NAME!r} "
        f"explicit_database_url={explicit_db_url} rabbit_host={s.RABBITMQ_HOST!r} "
        f"queue={s.RABBITMQ_QUEUE_NAME!r}"
    )


class MlTaskCompleteFailedError(DomainError):
    pass


class MlTaskMessageRejectedError(Exception):
    """Сообщение очереди не согласуется с задачей в БД — обработку нужно повторить или снять по политике."""

    def __init__(self, reason: str, *, requeue_message: bool = True) -> None:
        super().__init__(reason)
        self.reason = reason
        self.requeue_message = requeue_message


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
    from app.modules.neural.toxicity_pipeline import toxicity_predict

    wid = worker_id or "неизвестен"
    logger.info(
        "%s",
        json.dumps(
            {
                "event": "ml_queue_session_start",
                "worker_id": wid,
                "task_id": str(msg.task_id),
                "model": str(msg.model),
                "timestamp": msg.timestamp.isoformat(),
                "text_len": len(msg.features.text),
                "text_preview": text_preview_for_log(msg.features.text),
            },
            ensure_ascii=False,
            default=str,
        ),
    )

    row = db.get(MlPredictionTaskModel, msg.task_id)
    if row is None:
        logger.warning(
            "сирота ML: в БД нет строки ml_prediction_tasks для task_id=%s (воркер %s). "
            "На «чистом» стеке чаще всего это гонка API: сообщение ушло в Rabbit до commit транзакции "
            "(Postgres READ COMMITTED — другая сессия не видит строку); в сервисе порядок исправлен на commit→publish. "
            "Реже: один Rabbit на два разных Postgres, или только БД сбросили, а очередь — нет. "
            "Ack без requeue. [%s]",
            msg.task_id,
            wid,
            _settings_fingerprint(),
        )
        raise MlTaskMessageRejectedError(
            f"задача не найдена в БД: task_id={msg.task_id}",
            requeue_message=False,
        )
    if row.status != TaskStatus.PENDING.value:
        logger.info(
            "%s",
            json.dumps(
                {
                    "task_id": str(msg.task_id),
                    "prediction": None,
                    "worker_id": wid,
                    "status": "duplicate_delivery",
                    "detail": "задача уже не PENDING, БД не меняем",
                    "db_task_status": row.status,
                },
                ensure_ascii=False,
            ),
        )
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

    t_neural = time.monotonic()
    logger.info(
        "%s",
        json.dumps(
            {
                "event": "neural_inference_start",
                "worker_id": wid,
                "task_id": str(msg.task_id),
                "user_id": str(row.user_id),
                "model_id": str(row.model_id),
                "db_status": row.status,
                "charged_tokens": str(row.charged_tokens),
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "queue_timestamp": msg.timestamp.isoformat(),
                "text_len": len(row.text),
                "text_preview": text_preview_for_log(row.text),
            },
            ensure_ascii=False,
            default=str,
        ),
    )
    outcome = toxicity_predict(row.text, model_id=row.model_id)
    inference_seconds = time.monotonic() - t_neural
    time.sleep(1.0)
    neural_phase_seconds = time.monotonic() - t_neural
    logger.info(
        "%s",
        json.dumps(
            {
                "event": "neural_inference_finished",
                "worker_id": wid,
                "task_id": str(msg.task_id),
                "user_id": str(row.user_id),
                "model_id": str(row.model_id),
                "inference_seconds": round(inference_seconds, 4),
                "emulated_post_inference_sleep_seconds": 1.0,
                "total_neural_phase_seconds": round(neural_phase_seconds, 4),
                "is_toxic": outcome.is_toxic,
                "toxicity_probability": float(outcome.toxicity_probability)
                if outcome.toxicity_probability is not None
                else None,
                "breakdown": outcome.breakdown,
                "summary_preview": text_preview_for_log(outcome.summary or "", max_len=600),
            },
            ensure_ascii=False,
            default=str,
        ),
    )

    ml_store = SqlAlchemyMlTaskStore(db)
    done_at = ml_store.complete_task(msg.task_id, outcome)
    if done_at is None:
        logger.error(
            "complete_task не обновил строку: worker_id=%s task_id=%s user_id=%s",
            wid,
            msg.task_id,
            row.user_id,
        )
        raise MlTaskCompleteFailedError(f"ml_prediction_tasks row missing: {msg.task_id}")
    row_after = db.get(MlPredictionTaskModel, msg.task_id)
    logger.info(
        "%s",
        json.dumps(
            {
                "task_id": str(msg.task_id),
                "prediction": outcome.toxicity_probability,
                "worker_id": wid,
                "status": "success",
                "is_toxic": outcome.is_toxic,
                "toxicity_probability": outcome.toxicity_probability,
                "breakdown": outcome.breakdown,
                "summary": outcome.summary,
                "model_id": str(msg.model),
                "db_task_status": row_after.status if row_after else None,
                "db_is_toxic": row_after.is_toxic if row_after else None,
                "db_toxicity_probability": float(row_after.toxicity_probability)
                if row_after and row_after.toxicity_probability is not None
                else None,
                "db_toxicity_breakdown": row_after.toxicity_breakdown if row_after else None,
                "completed_at": done_at.isoformat(),
            },
            ensure_ascii=False,
            default=str,
        ),
    )
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
        outcome.summary,
        tokens_charged=row.charged_tokens,
        commit=False,
    )
    logger.info(
        "история и результат записаны в сессию (до commit): worker_id=%s task_id=%s completed_at=%s",
        wid,
        msg.task_id,
        done_at,
    )
