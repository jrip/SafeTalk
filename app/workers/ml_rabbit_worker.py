from __future__ import annotations

import json
import logging
import os
import socket
import sys
import time
from json import JSONDecodeError
from typing import Any

import pika
from pydantic import ValidationError
from pika.channel import Channel
from pika.spec import Basic, BasicProperties

from app.core.settings import get_settings
from app.modules.neural.ml_task_queue import (
    MlPredictionQueuePayload,
    MlTaskAlreadyDoneError,
    MlTaskCompleteFailedError,
    MlTaskMessageRejectedError,
    complete_ml_task_from_queue_message,
)

logger = logging.getLogger(__name__)

# Остаток «пропусков» ack при ошибке (только если ml_worker_skip_errors и limit >= 1).
_failure_ack_budget_remaining: int | None = None


def _worker_id() -> str:
    manual = (os.environ.get("ML_WORKER_ID") or "").strip()
    if manual:
        return manual
    return f"{socket.gethostname()}-{os.getpid()}"


def _init_failure_budget_from_settings() -> None:
    global _failure_ack_budget_remaining
    s = get_settings()
    if s.ml_worker_skip_errors and s.ml_worker_skip_errors_limit >= 1:
        _failure_ack_budget_remaining = s.ml_worker_skip_errors_limit
    else:
        _failure_ack_budget_remaining = None


def _reload_failure_budget() -> None:
    global _failure_ack_budget_remaining
    s = get_settings()
    if s.ml_worker_skip_errors and s.ml_worker_skip_errors_limit >= 1:
        _failure_ack_budget_remaining = s.ml_worker_skip_errors_limit


def _failure_detail(exc: Exception) -> str:
    if isinstance(exc, (MlTaskMessageRejectedError, MlTaskAlreadyDoneError)):
        return exc.reason
    return str(exc)


def _apply_delivery_failure_policy(
    ch: Channel,
    delivery_tag: int,
    worker_id: str,
    exc: Exception,
    *,
    context: str,
) -> None:
    s = get_settings()
    skip = s.ml_worker_skip_errors
    limit = s.ml_worker_skip_errors_limit

    if not skip:
        if isinstance(exc, (MlTaskMessageRejectedError, MlTaskCompleteFailedError)):
            logger.error(
                "ошибка обработки сообщения (%s), политика: пауза 5 с, nack+requeue. worker_id=%s delivery_tag=%s причина=%s",
                context,
                worker_id,
                delivery_tag,
                _failure_detail(exc),
            )
        else:
            logger.exception(
                "ошибка обработки сообщения (%s), политика: пауза 5 с, nack+requeue. worker_id=%s delivery_tag=%s",
                context,
                worker_id,
                delivery_tag,
            )
        time.sleep(5)
        ch.basic_nack(delivery_tag=delivery_tag, requeue=True)
        return

    if limit == -1:
        if isinstance(exc, (MlTaskMessageRejectedError, MlTaskCompleteFailedError)):
            logger.error(
                "ошибка обработки (%s), политика: пропуск всех ошибок — ack. worker_id=%s delivery_tag=%s причина=%s",
                context,
                worker_id,
                delivery_tag,
                _failure_detail(exc),
            )
        else:
            logger.exception(
                "ошибка обработки (%s), политика: пропуск всех ошибок — ack. worker_id=%s delivery_tag=%s",
                context,
                worker_id,
                delivery_tag,
            )
        ch.basic_ack(delivery_tag=delivery_tag)
        return

    if limit >= 1:
        global _failure_ack_budget_remaining
        if _failure_ack_budget_remaining is None:
            _failure_ack_budget_remaining = limit
        if _failure_ack_budget_remaining > 0:
            _failure_ack_budget_remaining -= 1
            if isinstance(exc, (MlTaskMessageRejectedError, MlTaskCompleteFailedError)):
                logger.error(
                    "ошибка обработки (%s), политика: ack (пропуск ошибок), осталось пропусков=%s. "
                    "worker_id=%s delivery_tag=%s причина=%s",
                    context,
                    _failure_ack_budget_remaining,
                    worker_id,
                    delivery_tag,
                    _failure_detail(exc),
                )
            else:
                logger.exception(
                    "ошибка обработки (%s), политика: ack (пропуск ошибок), осталось пропусков=%s. "
                    "worker_id=%s delivery_tag=%s",
                    context,
                    _failure_ack_budget_remaining,
                    worker_id,
                    delivery_tag,
                )
            ch.basic_ack(delivery_tag=delivery_tag)
            return

    if isinstance(exc, (MlTaskMessageRejectedError, MlTaskCompleteFailedError)):
        logger.error(
            "ошибка обработки (%s), бюджет пропусков исчерпан: пауза 5 с, nack+requeue. worker_id=%s delivery_tag=%s причина=%s",
            context,
            worker_id,
            delivery_tag,
            _failure_detail(exc),
        )
    else:
        logger.exception(
            "ошибка обработки (%s), бюджет пропусков исчерпан: пауза 5 с, nack+requeue. worker_id=%s delivery_tag=%s",
            context,
            worker_id,
            delivery_tag,
        )
    time.sleep(5)
    ch.basic_nack(delivery_tag=delivery_tag, requeue=True)


def _on_message(
    ch: Channel,
    method: Basic.Deliver,
    _properties: BasicProperties,
    body: bytes,
    *,
    worker_id: str,
) -> None:
    delivery_tag = method.delivery_tag
    try:
        logger.info(
            "получено сообщение из RabbitMQ: worker_id=%s delivery_tag=%s размер_тела=%s байт",
            worker_id,
            delivery_tag,
            len(body),
        )
        data: Any = json.loads(body.decode("utf-8"))
        msg = MlPredictionQueuePayload.model_validate(data)
        logger.info(
            "тело сообщения прошло валидацию: worker_id=%s task_id=%s model=%s timestamp=%s",
            worker_id,
            msg.task_id,
            msg.model,
            msg.timestamp,
        )
        complete_ml_task_from_queue_message(msg, worker_id=worker_id)
        _reload_failure_budget()
        logger.info(
            "обработка сообщения завершена, отправляем ack: worker_id=%s task_id=%s model=%s",
            worker_id,
            msg.task_id,
            msg.model,
        )
        ch.basic_ack(delivery_tag=delivery_tag)
    except MlTaskAlreadyDoneError as exc:
        logger.info(
            "дубликат доставки, задача уже не в PENDING — ack без изменения БД: worker_id=%s delivery_tag=%s %s",
            worker_id,
            delivery_tag,
            exc.reason,
        )
        _reload_failure_budget()
        ch.basic_ack(delivery_tag=delivery_tag)
    except MlTaskMessageRejectedError as exc:
        logger.error(
            "сообщение отклонено проверками согласованности с БД: worker_id=%s delivery_tag=%s %s",
            worker_id,
            delivery_tag,
            exc.reason,
        )
        _apply_delivery_failure_policy(
            ch,
            delivery_tag,
            worker_id,
            exc,
            context="отклонено проверками",
        )
    except MlTaskCompleteFailedError as exc:
        logger.error(
            "инвариант завершения задачи: worker_id=%s delivery_tag=%s %s",
            worker_id,
            delivery_tag,
            str(exc),
        )
        _apply_delivery_failure_policy(
            ch,
            delivery_tag,
            worker_id,
            exc,
            context="complete_task не обновил строку",
        )
    except (ValidationError, JSONDecodeError) as exc:
        logger.exception(
            "некорректное JSON-тело сообщения в очереди: worker_id=%s delivery_tag=%s",
            worker_id,
            delivery_tag,
        )
        _apply_delivery_failure_policy(
            ch,
            delivery_tag,
            worker_id,
            exc,
            context="некорректное тело сообщения",
        )
    except Exception as exc:
        logger.exception(
            "непредвиденная ошибка воркера: worker_id=%s delivery_tag=%s",
            worker_id,
            delivery_tag,
        )
        _apply_delivery_failure_policy(
            ch,
            delivery_tag,
            worker_id,
            exc,
            context="непредвиденная ошибка",
        )


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    settings = get_settings()
    url = settings.rabbitmq_url
    if not url:
        logger.error("не задан URL RabbitMQ (rabbitmq_url), воркер не может стартовать")
        sys.exit(1)

    worker_id = _worker_id()
    queue_name = settings.RABBITMQ_QUEUE_NAME
    _init_failure_budget_from_settings()
    logger.info(
        "политика ошибок воркера: skip_errors=%s limit=%s",
        settings.ml_worker_skip_errors,
        settings.ml_worker_skip_errors_limit,
    )

    params = pika.URLParameters(url)
    connection = pika.BlockingConnection(params)
    channel = connection.channel()
    channel.queue_declare(queue=queue_name, durable=True)
    channel.basic_qos(prefetch_count=1)

    channel.basic_consume(
        queue=queue_name,
        on_message_callback=lambda ch, method, props, body: _on_message(
            ch, method, props, body, worker_id=worker_id
        ),
        auto_ack=False,
    )
    logger.info(
        "воркер подписан на очередь: worker_id=%s очередь=%s prefetch=1",
        worker_id,
        queue_name,
    )
    channel.start_consuming()


if __name__ == "__main__":
    main()
