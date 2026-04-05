from __future__ import annotations

from dataclasses import asdict
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.bootstrap import build_app_container
from app.core.api_models import ErrorResponse
from app.db.database import get_db
from app.modules.neural.types import RunPredictionInput

router = APIRouter(prefix="/predict", tags=["predict"])


class PredictRequest(BaseModel):
    user_id: UUID
    model_id: UUID
    text: str = Field(min_length=1)


class PredictTaskResponse(BaseModel):
    task_id: UUID
    user_id: UUID
    model_id: UUID
    text: str
    status: str
    charged_tokens: Decimal


def _container(session: Session = Depends(get_db)):
    return build_app_container(session)


def _as_json(payload: Any) -> dict[str, Any]:
    return asdict(payload)


@router.post(
    "",
    response_model=PredictTaskResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
def predict(payload: PredictRequest, c=Depends(_container)) -> dict[str, Any]:
    task = c.neural.create_prediction_task(
        RunPredictionInput(
            user_id=payload.user_id,
            model_id=payload.model_id,
            text=payload.text,
        )
    )
    return _as_json(task)
