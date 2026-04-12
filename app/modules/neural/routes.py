from __future__ import annotations

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
from app.modules.neural.types import RunPredictionInput
from app.modules.users.auth import require_user_id

router = APIRouter(prefix="/predict", tags=["predict"])


class PredictRequest(BaseModel):
    model_id: UUID
    text: str = Field(min_length=1)


class CreatePredictTaskResponse(BaseModel):
    """Ответ POST /predict по ТЗ: только идентификатор созданной задачи."""

    task_id: UUID


class MlModelCatalogItemResponse(BaseModel):
    id: UUID
    slug: str
    name: str
    description: str
    price_per_character: Decimal
    is_default: bool


class PredictTaskDetailResponse(BaseModel):
    task_id: UUID
    user_id: UUID
    model_id: UUID
    text: str
    status: str
    charged_tokens: Decimal
    created_at: datetime
    completed_at: datetime | None = None
    result_summary: str | None = None
    is_toxic: bool | None = None
    toxicity_probability: Decimal | None = None
    toxicity_breakdown: dict[str, float] | None = None


def _container(session: Session = Depends(get_db)):
    return build_app_container(session)


@router.get(
    "/models",
    response_model=list[MlModelCatalogItemResponse],
    responses={
        401: {"model": ErrorResponse},
    },
)
def list_ml_models(
    c=Depends(_container),
    _current_user_id: UUID = Depends(require_user_id),
) -> list[dict[str, Any]]:
    items = c.neural.list_catalog_models()
    return [
        {
            "id": m.id,
            "slug": m.slug,
            "name": m.name,
            "description": m.description,
            "price_per_character": m.price_per_character,
            "is_default": m.is_default,
        }
        for m in items
    ]


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
        "completed_at": detail.completed_at,
        "result_summary": detail.result_summary,
        "is_toxic": detail.is_toxic,
        "toxicity_probability": detail.toxicity_probability,
        "toxicity_breakdown": detail.toxicity_breakdown,
    }


@router.post(
    "",
    response_model=CreatePredictTaskResponse,
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
    return {"task_id": task.task_id}
