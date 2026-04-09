from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.bootstrap import build_app_container
from app.core.api_models import ErrorResponse
from app.db.database import get_db
from app.modules.neural.types import RunPredictionInput, TaskStatus
from app.modules.users.auth import require_user_id

router = APIRouter(prefix="/predict", tags=["predict"])


class PredictRequest(BaseModel):
    model_id: UUID
    text: str = Field(min_length=1)


class PredictTaskResponse(BaseModel):
    task_id: UUID
    user_id: UUID
    model_id: UUID
    text: str
    status: str
    charged_tokens: Decimal
    result_summary: str | None = None


class PredictTaskDetailResponse(BaseModel):
    task_id: UUID
    user_id: UUID
    model_id: UUID
    text: str
    status: str
    charged_tokens: Decimal
    created_at: datetime
    result_summary: str | None = None


def _container(session: Session = Depends(get_db)):
    return build_app_container(session)


def _as_json(payload: Any) -> dict[str, Any]:
    return asdict(payload)


def _task_view_to_predict_response(task: Any) -> dict[str, Any]:
    return {
        "task_id": task.task_id,
        "user_id": task.user_id,
        "model_id": task.model_id,
        "text": task.text,
        "status": task.status.value if isinstance(task.status, TaskStatus) else str(task.status),
        "charged_tokens": task.charged_tokens,
        "result_summary": task.result_summary,
    }


@router.get(
    "/{task_id}",
    response_model=PredictTaskDetailResponse,
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
def get_prediction_task(
    task_id: UUID,
    c=Depends(_container),
    current_user_id: UUID = Depends(require_user_id),
) -> dict[str, Any]:
    detail = c.neural.get_task_for_user(current_user_id, task_id)
    return {
        "task_id": detail.task_id,
        "user_id": detail.user_id,
        "model_id": detail.model_id,
        "text": detail.text,
        "status": detail.status.value,
        "charged_tokens": detail.charged_tokens,
        "created_at": detail.created_at,
        "result_summary": detail.result_summary,
    }


@router.post(
    "",
    response_model=PredictTaskResponse,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"model": ErrorResponse},
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
def predict(payload: PredictRequest, c=Depends(_container), current_user_id: UUID = Depends(require_user_id)) -> dict[str, Any]:
    task = c.neural.create_prediction_task(
        RunPredictionInput(
            user_id=current_user_id,
            model_id=payload.model_id,
            text=payload.text,
        )
    )
    return _task_view_to_predict_response(task)
